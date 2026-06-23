"""Boundary detection track — HMM Viterbi-style domain finder over self-similarity.

Aggregates evidence from multiple similarity metrics and window sizes to find
structurally coherent "boxes" (internally similar passages) bounded by
"stripes" (low-similarity transition intervals).

Algorithm:
1. Load all available self-similarity matrices (all metrics × all chunk sizes)
2. Compute directionality index (DI) for each matrix
3. Aggregate DI signals into a consensus feature vector per chunk position
4. Run a 3-state HMM via Viterbi: {inside-domain, boundary, transition}
5. Extract domain intervals and boundary positions
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.annotation.model import Annotation, Body, Creator, Target, TextPositionSelector
from palimpsest.project import Project
from palimpsest.tracks.params import Param, ParameterizedTrack

logger = logging.getLogger(__name__)

# 3-state boundary HMM — previously hidden inside _viterbi_boundary, now named module constants so
# they can be reported in parameters() (finding: HMM emission/transition matrices were output-affecting
# but invisible). States: 0=inside-domain, 1=boundary, 2=transition.
HMM_N_STATES = 3
HMM_STATE_MEANS = [-0.5, 1.5, 0.3]
HMM_STATE_VARS = [0.8, 0.8, 0.5]
HMM_TRANSITION_MATRIX = [
    [0.90, 0.03, 0.07],  # inside → inside/boundary/transition
    [0.20, 0.30, 0.50],  # boundary → inside/boundary/transition
    [0.40, 0.10, 0.50],  # transition → inside/boundary/transition
]
HMM_INITIAL_PROBS = [0.7, 0.1, 0.2]
MIN_DOMAIN_LENGTH = 3
DEFAULT_BOUNDARY_CONFIDENCE = 0.7


def _directionality_index(matrix: np.ndarray, window: int = 5) -> np.ndarray:
    """Compute directionality index: bias between upstream and downstream similarity."""
    n = matrix.shape[0]
    di = np.zeros(n, dtype=np.float64)
    for i in range(n):
        up = matrix[i, max(0, i - window):i].sum() if i > 0 else 0
        down = matrix[i, i + 1:min(n, i + window + 1)].sum() if i < n - 1 else 0
        total = up + down
        if total > 1e-8:
            di[i] = (down - up) / total
    return di


def _insulation_score(matrix: np.ndarray, window: int = 5) -> np.ndarray:
    """Insulation score: mean similarity in a sliding square along the diagonal.
    Low values indicate boundaries (the region doesn't interact with its neighbors)."""
    n = matrix.shape[0]
    ins = np.zeros(n, dtype=np.float64)
    for i in range(n):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        block = matrix[lo:hi, lo:hi]
        ins[i] = block.mean() if block.size > 0 else 0.0
    return ins


def _aggregate_signals(
    signals_dir: Path,
    reference_n: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Load all available self-similarity matrices and compute aggregate features.
    Returns (feature_matrix of shape [max_n, n_features], sources_info)."""
    metrics = ("cosine", "jaccard", "word_overlap", "edit_distance")
    features: list[np.ndarray] = []
    sources: list[dict[str, Any]] = []

    # Scan per-chunk-size directories
    cs_dirs: list[tuple[int, Path]] = []
    for entry in signals_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("self_similarity_cs"):
            try:
                cs = int(entry.name.replace("self_similarity_cs", ""))
                cs_dirs.append((cs, entry))
            except ValueError:
                pass

    # Also try flat files (legacy)
    if not cs_dirs:
        cs_dirs.append((0, signals_dir))

    for cs, cs_dir in sorted(cs_dirs):
        for metric in metrics:
            if cs > 0:
                bin_path = cs_dir / f"{metric}.bin"
            else:
                bin_path = cs_dir / f"self_similarity_{metric}.bin"

            if not bin_path.exists():
                continue

            data = np.fromfile(str(bin_path), dtype=np.float32)
            n = int(np.sqrt(len(data)))
            if n * n != len(data) or n < 5:
                continue

            matrix = data.reshape(n, n)
            di = _directionality_index(matrix, window=max(3, n // 50))
            ins = _insulation_score(matrix, window=max(3, n // 50))

            # Resample to reference_n if chunk sizes differ
            if n != reference_n and reference_n > 0:
                x_old = np.linspace(0, 1, n)
                x_new = np.linspace(0, 1, reference_n)
                di = np.interp(x_new, x_old, di)
                ins = np.interp(x_new, x_old, ins)

            features.append(di)
            features.append(ins)
            sources.append({"metric": metric, "chunk_size": cs, "n": n, "signal": "DI"})
            sources.append({"metric": metric, "chunk_size": cs, "n": n, "signal": "insulation"})
            logger.info("Boundary detection: loaded %s (cs=%d, n=%d)", metric, cs, n)

    if not features:
        return np.zeros((reference_n, 0)), sources

    return np.column_stack(features), sources


def _viterbi_boundary(features: np.ndarray) -> np.ndarray:
    """3-state HMM Viterbi for boundary detection.

    States: 0=inside-domain (high insulation, low |DI|),
            1=boundary (low insulation, high |DI| magnitude),
            2=transition (moderate)

    Returns state sequence of length n.
    """
    n, d = features.shape
    if n == 0 or d == 0:
        return np.zeros(n, dtype=int)

    # Normalize features
    means = features.mean(axis=0, keepdims=True)
    stds = features.std(axis=0, keepdims=True)
    stds = np.where(stds > 1e-8, stds, 1.0)
    z = (features - means) / stds

    # Compute per-position boundary evidence
    # DI features (odd indices): high |value| = boundary
    # Insulation features (even indices): low value = boundary
    n_signals = d // 2
    boundary_evidence = np.zeros(n)
    for k in range(n_signals):
        di_col = z[:, 2 * k] if 2 * k < d else np.zeros(n)
        ins_col = z[:, 2 * k + 1] if 2 * k + 1 < d else np.zeros(n)
        boundary_evidence += np.abs(di_col) - ins_col

    boundary_evidence /= max(n_signals, 1)

    # 3-state HMM: inside(0), boundary(1), transition(2) — parameters now named module constants.
    n_states = HMM_N_STATES
    # Emission: Gaussian approximation from boundary_evidence
    state_means = np.array(HMM_STATE_MEANS)
    state_vars = np.array(HMM_STATE_VARS)

    # Transition matrix: domains are sticky, boundaries are rare
    log_trans = np.log(np.array(HMM_TRANSITION_MATRIX))

    # Initial probabilities
    log_pi = np.log(np.array(HMM_INITIAL_PROBS))

    # Log emission probabilities
    def log_emit(obs: float, state: int) -> float:
        diff = obs - state_means[state]
        return -0.5 * (diff ** 2) / state_vars[state] - 0.5 * np.log(2 * np.pi * state_vars[state])

    # Viterbi
    V = np.full((n, n_states), -np.inf)
    B = np.zeros((n, n_states), dtype=int)

    for s in range(n_states):
        V[0, s] = log_pi[s] + log_emit(boundary_evidence[0], s)

    for t in range(1, n):
        for s in range(n_states):
            emit = log_emit(boundary_evidence[t], s)
            candidates = V[t - 1, :] + log_trans[:, s]
            best_prev = int(np.argmax(candidates))
            V[t, s] = candidates[best_prev] + emit
            B[t, s] = best_prev

    # Backtrack
    states = np.zeros(n, dtype=int)
    states[-1] = int(np.argmax(V[-1, :]))
    for t in range(n - 2, -1, -1):
        states[t] = B[t + 1, states[t + 1]]

    return states


def _extract_domains(
    states: np.ndarray, min_length: int = MIN_DOMAIN_LENGTH
) -> list[dict[str, Any]]:
    """Extract domain intervals from Viterbi state sequence."""
    n = len(states)
    if n == 0:
        return []

    domains: list[dict[str, Any]] = []
    boundaries: list[int] = []

    # Find contiguous runs of state 0 (inside-domain)
    current_start: int | None = None
    for i in range(n):
        if states[i] == 0:
            if current_start is None:
                current_start = i
        else:
            if current_start is not None:
                domains.append({
                    "start": current_start,
                    "end": i,
                    "length": i - current_start,
                    "type": "domain",
                })
                current_start = None
            if states[i] == 1:
                boundaries.append(i)

    if current_start is not None:
        domains.append({
            "start": current_start,
            "end": n,
            "length": n - current_start,
            "type": "domain",
        })

    # Filter out very small domains
    domains = [d for d in domains if d["length"] >= min_length]

    return domains


class BoundaryDetectionTrack(ParameterizedTrack):
    """HMM-based boundary detection from multi-metric self-similarity matrices."""

    PARAMS = (
        Param("min_domain_length", int, default=MIN_DOMAIN_LENGTH, min=1, max=100,
              help="minimum chunk length for a detected domain to be kept"),
        Param("boundary_confidence", float, default=DEFAULT_BOUNDARY_CONFIDENCE, locked=True,
              help="fixed confidence assigned to each boundary-point annotation"),
    )

    @property
    def name(self) -> str:
        return "boundary_detection"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["self_similarity"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.text_domain", "signal.text_boundary"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project: Project) -> list[Annotation]:
        signals_dir = project.path / "signals"
        sim_json = signals_dir / "self_similarity.json"

        if not sim_json.exists():
            raise FileNotFoundError("Self-similarity not computed yet.")

        cfg = self.resolved_params()
        min_domain_length = cfg["min_domain_length"]
        boundary_confidence = cfg["boundary_confidence"]

        manifest = json.loads(sim_json.read_text())
        reference_n = manifest.get("dimensions", [0, 0])[0]

        features, sources = _aggregate_signals(signals_dir, reference_n)
        logger.info(
            "Boundary detection: %d features from %d signal sources, reference n=%d",
            features.shape[1] if features.ndim == 2 else 0, len(sources), reference_n,
        )

        if features.shape[1] == 0:
            logger.warning("No self-similarity signals found for boundary detection")
            return []

        states = _viterbi_boundary(features)
        domains = _extract_domains(states, min_domain_length)
        logger.info("Boundary detection: found %d domains", len(domains))

        # Map chunk indices back to character positions
        segment_offsets = manifest.get("segment_offsets", [])
        paras = project.paragraphs()
        source_urn = f"urn:palimpsest:{project.metadata.id}"

        annotations: list[Annotation] = []

        for i, domain in enumerate(domains):
            cs = domain["start"]
            ce = min(domain["end"] - 1, len(segment_offsets) - 1)
            if cs >= len(segment_offsets) or ce < 0:
                continue

            char_start = segment_offsets[cs][0]
            char_end = segment_offsets[ce][1]

            ann = Annotation(
                body=Body(
                    type="palimpsest:TextDomainAnnotation",
                    purpose="classifying",
                    value=f"Domain {i + 1}",
                    lfo_type="signal.text_domain",
                    extra={
                        "palimpsest:domainIndex": i,
                        "palimpsest:chunkStart": domain["start"],
                        "palimpsest:chunkEnd": domain["end"],
                        "palimpsest:chunkLength": domain["length"],
                        "palimpsest:nSources": len(sources),
                    },
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=char_start, end=char_end),
                ),
                creator=Creator(name="palimpsest-boundary-detection/0.1"),
                confidence=min(0.5 + domain["length"] / 50, 0.95),
                evidence_level="E4",
                project_id=project.metadata.id,
                track_name="boundary_detection",
            )
            annotations.append(ann)

        # Also emit boundary point annotations
        for i in range(len(states)):
            if states[i] == 1 and i < len(segment_offsets):
                char_pos = segment_offsets[i][0]
                ann = Annotation(
                    body=Body(
                        type="palimpsest:TextBoundaryAnnotation",
                        purpose="classifying",
                        value="Boundary",
                        lfo_type="signal.text_boundary",
                        extra={
                            "palimpsest:chunkIndex": i,
                            "palimpsest:boundaryEvidence": "hmm_viterbi",
                        },
                    ),
                    target=Target(
                        source=source_urn,
                        selector=TextPositionSelector(
                            start=char_pos,
                            end=segment_offsets[min(i, len(segment_offsets) - 1)][1],
                        ),
                    ),
                    creator=Creator(name="palimpsest-boundary-detection/0.1"),
                    confidence=boundary_confidence,
                    evidence_level="E4",
                    project_id=project.metadata.id,
                    track_name="boundary_detection",
                )
                annotations.append(ann)

        # Write domain metadata
        boundary_meta = {
            "n_domains": len(domains),
            "n_boundaries": sum(1 for s in states if s == 1),
            "n_sources": len(sources),
            "sources": sources,
            "domains": domains,
            "state_counts": {
                "inside": int((states == 0).sum()),
                "boundary": int((states == 1).sum()),
                "transition": int((states == 2).sum()),
            },
        }
        (signals_dir / "boundary_detection_meta.json").write_text(
            json.dumps(boundary_meta, indent=2), encoding="utf-8",
        )

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "boundary_detection",
            "bodyType": "palimpsest:TextDomainAnnotation",
            "colorScheme": {
                "primary": "#8b5cf6",
                "secondary": "#a78bfa",
                "scale": {"domain": "#8b5cf6", "boundary": "#f59e0b"},
            },
            "textViewRendering": "bracket",
        }

    def parameters(self) -> dict[str, Any]:
        # Extend the rail's tunable-param view with the structural method labels and the (locked-by-
        # nature) HMM emission/transition matrices, so the matrices that shape every boundary are
        # reported in provenance instead of staying hidden inside _viterbi_boundary.
        return {
            **super().parameters(),
            "boundary_detection.method": "hmm_viterbi_aggregate",
            "boundary_detection.states": HMM_N_STATES,
            "boundary_detection.evidence": "multi-metric multi-resolution",
            "boundary_detection.hmm_state_means": HMM_STATE_MEANS,
            "boundary_detection.hmm_state_vars": HMM_STATE_VARS,
            "boundary_detection.hmm_transition_matrix": HMM_TRANSITION_MATRIX,
            "boundary_detection.hmm_initial_probs": HMM_INITIAL_PROBS,
        }
