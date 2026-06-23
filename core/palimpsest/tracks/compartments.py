"""Thematic compartments track — A/B decomposition + TAD-like domain detection.

Adapted from Hi-C genomic compartment analysis (Lieberman-Aiden 2009):
- A/B compartments from first eigenvector of correlation matrix
- Domain boundaries from directionality index + HMM segmentation
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np

from palimpsest.annotation.model import Annotation, Body, Creator, Target, TextPositionSelector
from palimpsest.project import Project
from palimpsest.tracks.params import Param, ParameterizedTrack

logger = logging.getLogger(__name__)

DEFAULT_DI_WINDOW = 5
DEFAULT_DOMAIN_THRESHOLD = 0.3
DEFAULT_DOMAIN_CONFIDENCE = 0.70


def _compute_compartments(sim_matrix: np.ndarray) -> np.ndarray:
    """Compute A/B compartments via first eigenvector of the correlation matrix."""
    n = sim_matrix.shape[0]
    if n < 3:
        return np.zeros(n)

    row_means = sim_matrix.mean(axis=1, keepdims=True)
    col_means = sim_matrix.mean(axis=0, keepdims=True)
    grand_mean = sim_matrix.mean()
    obs_exp = sim_matrix - row_means - col_means + grand_mean

    try:
        eigenvalues, eigenvectors = np.linalg.eigh(obs_exp)
        first_pc = eigenvectors[:, -1]
    except np.linalg.LinAlgError as exc:
        # A failed eigendecomposition is a failed analysis, not a result. Returning np.zeros here
        # classified every paragraph as compartment "A" at confidence 0 — a non-convergence
        # masquerading as data (finding B5). Raise so it surfaces through the G5 failed-job path.
        raise ValueError(
            f"compartment eigendecomposition failed on the {n}x{n} similarity matrix: {exc}"
        ) from exc

    return first_pc


def _compute_directionality_index(sim_matrix: np.ndarray, window: int = 5) -> np.ndarray:
    """Compute directionality index (DI) for domain boundary detection.

    DI measures the bias between upstream and downstream interaction
    frequencies at each position (Dixon et al. 2012).
    """
    n = sim_matrix.shape[0]
    di = np.zeros(n)

    for i in range(n):
        upstream_start = max(0, i - window)
        downstream_end = min(n, i + window + 1)

        upstream = sim_matrix[i, upstream_start:i].sum() if i > 0 else 0
        downstream = sim_matrix[i, i + 1:downstream_end].sum() if i < n - 1 else 0

        total = upstream + downstream
        if total > 0:
            di[i] = (downstream - upstream) / total

    return di


def _detect_domains(di: np.ndarray, threshold: float = 0.3) -> list[tuple[int, int]]:
    """Detect domain boundaries from sign changes in the directionality index."""
    n = len(di)
    if n < 2:
        return [(0, n)]

    boundaries = [0]
    for i in range(1, n):
        if abs(di[i] - di[i - 1]) > threshold:
            boundaries.append(i)
    boundaries.append(n)

    domains = []
    for i in range(len(boundaries) - 1):
        domains.append((boundaries[i], boundaries[i + 1]))

    return domains


class CompartmentsExtractor(ParameterizedTrack):
    """Thematic compartment and domain detection from self-similarity matrix."""

    PARAMS = (
        Param("di_window", int, default=DEFAULT_DI_WINDOW, min=1, max=50,
              help="half-width (in paragraphs) of the directionality-index window"),
        Param("domain_threshold", float, default=DEFAULT_DOMAIN_THRESHOLD, min=0.0, max=2.0,
              help="directionality-index jump that marks a domain boundary"),
        Param("domain_confidence", float, default=DEFAULT_DOMAIN_CONFIDENCE, locked=True,
              help="fixed confidence assigned to each detected domain span"),
    )

    @property
    def name(self) -> str:
        return "compartments"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["self_similarity"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.compartment", "signal.domain_boundary"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Project) -> list[Annotation]:
        sim_bin = project.path / "signals" / "self_similarity.bin"
        sim_json = project.path / "signals" / "self_similarity.json"

        if not sim_bin.exists() or not sim_json.exists():
            raise FileNotFoundError(
                "Self-similarity matrix not computed. "
                "Run `palimpsest analyze` with embeddings available first."
            )

        meta = json.loads(sim_json.read_text())
        dims = meta.get("dimensions", [])
        if len(dims) != 2 or dims[0] != dims[1]:
            raise ValueError(f"Expected square matrix dimensions, got {dims}")

        n = dims[0]
        matrix = np.fromfile(str(sim_bin), dtype=np.float32).reshape(n, n)

        cfg = self.resolved_params()
        domain_confidence = cfg["domain_confidence"]

        compartment_values = _compute_compartments(matrix)
        di = _compute_directionality_index(matrix, window=cfg["di_window"])
        domains = _detect_domains(di, threshold=cfg["domain_threshold"])

        paras = project.paragraphs()
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        annotations: list[Annotation] = []

        for i, (para_start, para_end, _) in enumerate(paras):
            if i >= n:
                break
            comp_val = float(compartment_values[i])
            comp_label = "A" if comp_val >= 0 else "B"

            ann = Annotation(
                body=Body(
                    type="palimpsest:CompartmentAnnotation",
                    purpose="classifying",
                    value=comp_label,
                    lfo_type="signal.compartment",
                    extra={
                        "palimpsest:compartment": comp_label,
                        "palimpsest:eigenvalue": round(comp_val, 4),
                        "palimpsest:directionalityIndex": round(float(di[i]), 4),
                    },
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=para_start, end=para_end),
                ),
                creator=Creator(name="palimpsest-compartments/0.1"),
                confidence=min(abs(comp_val) * 2, 1.0),
                evidence_level="E5",
                project_id=project.metadata.id,
                track_name="compartments",
            )
            annotations.append(ann)

        for domain_start, domain_end in domains:
            if domain_start >= len(paras) or domain_end > len(paras):
                continue
            para_s = paras[domain_start][0]
            para_e = paras[min(domain_end, len(paras)) - 1][1]

            ann = Annotation(
                body=Body(
                    type="palimpsest:DomainAnnotation",
                    purpose="describing",
                    value=f"Domain {domain_start}-{domain_end}",
                    lfo_type="signal.domain_boundary",
                    extra={
                        "palimpsest:domainStart": domain_start,
                        "palimpsest:domainEnd": domain_end,
                        "palimpsest:domainSize": domain_end - domain_start,
                    },
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=para_s, end=para_e),
                ),
                creator=Creator(name="palimpsest-compartments/0.1"),
                confidence=domain_confidence,
                evidence_level="E5",
                project_id=project.metadata.id,
                track_name="compartments",
            )
            annotations.append(ann)

        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)
        compartments_meta = {
            "n_paragraphs": n,
            "n_domains": len(domains),
            "a_count": sum(1 for v in compartment_values if v >= 0),
            "b_count": sum(1 for v in compartment_values if v < 0),
            "domains": domains,
        }
        (signals_dir / "compartments_meta.json").write_text(
            json.dumps(compartments_meta, indent=2), encoding="utf-8"
        )

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "compartments",
            "bodyType": "palimpsest:CompartmentAnnotation",
            "colorScheme": {
                "primary": "#c0392b",
                "secondary": "#e74c3c",
                "scale": {"A": "#e74c3c", "B": "#3498db"},
            },
            "textViewRendering": "color-band",
            "overviewBarRendering": {"type": "ab-band"},
        }

    def parameters(self) -> dict[str, Any]:
        # Extend the rail's effective-param view with the structural method labels (which algorithm
        # produces the signal) so provenance keeps reporting them alongside the tunable knobs.
        return {
            **super().parameters(),
            "compartments.method": "eigenvector_decomposition",
            "compartments.domain_detection": "directionality_index",
        }
