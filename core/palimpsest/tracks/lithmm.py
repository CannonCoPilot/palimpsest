"""LitHMM track — multivariate Hidden Markov Model passage state discovery.

Uses Gaussian HMM on feature vectors assembled from existing Base tracks.
Auto-generates interpretable state descriptions from feature distributions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler

from palimpsest.annotation.model import Annotation, Body, Creator, Target, TextPositionSelector
from palimpsest.atomic import atomic_write_text
from palimpsest.project import Project
from palimpsest.tracks.params import InsufficientCorpusError, Param, ParameterizedTrack

logger = logging.getLogger(__name__)

DEFAULT_N_STATES = 10
FEATURE_NAMES = [
    "lexical_density",
    "dialogue_ratio",
    "entity_density",
    "sentiment_volatility",
    "sentence_length_var",
    "topic_entropy",
]


def _build_feature_matrix(project: Project) -> np.ndarray:
    """Assemble per-paragraph feature vectors from existing tracks."""
    from palimpsest.annotation.serializer import read_track

    paras = project.paragraphs()
    n = len(paras)
    features = np.zeros((n, 6), dtype=np.float64)

    lex_path = project.path / "tracks" / "lexical.jsonl"
    if lex_path.exists():
        for ann in read_track(lex_path):
            i = project.find_paragraph(ann.target.selector.start)
            if i < n:
                features[i, 0] = float(ann.body.extra.get("palimpsest:ttr", 0))

    dial_path = project.path / "tracks" / "dialogue.jsonl"
    if dial_path.exists():
        for ann in read_track(dial_path):
            i = project.find_paragraph(ann.target.selector.start)
            if i < n:
                features[i, 1] += 1.0

    ent_path = project.path / "tracks" / "entities.jsonl"
    if ent_path.exists():
        for ann in read_track(ent_path):
            i = project.find_paragraph(ann.target.selector.start)
            if i < n:
                features[i, 2] += 1.0

    sent_path = project.path / "tracks" / "sentiment.jsonl"
    if sent_path.exists():
        para_sentiments: dict[int, list[float]] = {}
        for ann in read_track(sent_path):
            i = project.find_paragraph(ann.target.selector.start)
            if i < n:
                val = float(ann.body.extra.get("palimpsest:valence", 0))
                para_sentiments.setdefault(i, []).append(val)
        for i, vals in para_sentiments.items():
            if len(vals) > 1:
                features[i, 3] = float(np.std(vals))

    seg_path = project.path / "tracks" / "segments.jsonl"
    if seg_path.exists():
        para_sent_lengths: dict[int, list[int]] = {}
        for ann in read_track(seg_path):
            if ann.body.extra.get("palimpsest:segmentType") != "sentence":
                continue
            sel = ann.target.selector
            sent_len = sel.end - sel.start
            i = project.find_paragraph(sel.start)
            if i < n:
                para_sent_lengths.setdefault(i, []).append(sent_len)
        for i, lens in para_sent_lengths.items():
            if len(lens) > 1:
                features[i, 4] = float(np.std(lens))

    topics_dist_path = project.path / "signals" / "topics_dist.json"
    topics_dist_bin = project.path / "signals" / "topics_dist.bin"
    if topics_dist_path.exists() and topics_dist_bin.exists():
        import json as _json
        dist_meta = _json.loads(topics_dist_path.read_text())
        dims = dist_meta.get("dimensions", [])
        if len(dims) == 2:
            n_paras_t, n_topics = dims
            dist = np.fromfile(str(topics_dist_bin), dtype=np.float32).reshape(n_paras_t, n_topics)
            for i in range(min(n, n_paras_t)):
                row = dist[i]
                row_sum = row.sum()
                if row_sum > 1e-10:
                    p = row / row_sum
                    features[i, 5] = float(-np.sum(p * np.log(p + 1e-10)))

    return features


def _describe_state(
    state_idx: int,
    means: np.ndarray,
    global_means: np.ndarray,
    global_stds: np.ndarray,
) -> str:
    """Auto-generate an interpretable state description from feature distributions."""
    descriptors: list[str] = []
    for j, name in enumerate(FEATURE_NAMES):
        if global_stds[j] < 1e-6:
            continue
        z = (means[j] - global_means[j]) / global_stds[j]
        if z > 0.8:
            descriptors.append(f"high {name.replace('_', ' ')}")
        elif z < -0.8:
            descriptors.append(f"low {name.replace('_', ' ')}")

    if not descriptors:
        return f"State {state_idx}: average across all features"

    return f"State {state_idx}: {', '.join(descriptors)}"


class LitHMMExtractor(ParameterizedTrack):
    """Multivariate HMM passage state discovery."""

    PARAMS = (
        Param("n_states", int, default=DEFAULT_N_STATES, min=2, max=20,
              help="number of latent passage states (2..20 keeps the HMM well-posed)"),
        # Declared (not hidden) algorithm constants — reported and disk-recorded, locked until exposed.
        Param("n_iter", int, default=100, locked=True, help="HMM fit iteration cap"),
        Param("random_state", int, default=42, locked=True, help="RNG seed (reproducibility)"),
        Param("n_init", int, default=10, locked=True, help="KMeans-fallback restarts"),
    )

    def __init__(self, n_states: int | None = None) -> None:
        super().__init__()
        # Constructor convenience (used by tests / direct callers): seed the raw param so it flows
        # through the same validation path as an API-supplied value.
        if n_states is not None:
            self._raw_params["n_states"] = n_states

    @property
    def name(self) -> str:
        return "lithmm"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["sentiment", "lexical", "dialogue", "entities", "topics", "syntax"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.lithmm_state"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Project) -> list[Annotation]:
        features = _build_feature_matrix(project)
        n_paras = features.shape[0]

        if n_paras < 4:
            raise InsufficientCorpusError(
                f"LitHMM state discovery needs at least 4 paragraphs, got {n_paras}"
            )

        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        cfg = self.resolved_params()
        random_state = cfg["random_state"]
        n_iter = cfg["n_iter"]
        n_init = cfg["n_init"]
        # Clamp the state count to a feasible value for the actual paragraph count, then record the
        # EFFECTIVE value (record-effective policy, §2.3): disk reports what ran plus `n_states_requested`
        # when it differs, so the clamp is transparent rather than a silent shrink (finding A2).
        n_states = min(cfg["n_states"], max(2, n_paras // 2))
        self.record_effective("n_states", n_states)

        used_hmm = False
        try:
            from hmmlearn.hmm import GaussianHMM  # type: ignore[import-untyped]
            model = GaussianHMM(
                n_components=n_states,
                covariance_type="diag",
                n_iter=n_iter,
                random_state=random_state,
            )
            model.fit(features_scaled)
            labels = model.predict(features_scaled)
            posteriors = model.predict_proba(features_scaled)
            state_means = model.means_
            used_hmm = True
        except ImportError:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_states, random_state=random_state, n_init=n_init)
            labels = kmeans.fit_predict(features_scaled)
            posteriors = np.zeros((n_paras, n_states))
            posteriors[np.arange(n_paras), labels] = 1.0
            state_means = kmeans.cluster_centers_
        except (ValueError, RuntimeError) as exc:
            logger.warning("HMM fitting failed (%s), falling back to KMeans", exc)
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_states, random_state=random_state, n_init=n_init)
            labels = kmeans.fit_predict(features_scaled)
            posteriors = np.zeros((n_paras, n_states))
            posteriors[np.arange(n_paras), labels] = 1.0
            state_means = kmeans.cluster_centers_

        global_means = features_scaled.mean(axis=0)
        global_stds = features_scaled.std(axis=0)

        state_descriptions: dict[str, str] = {}
        for s in range(n_states):
            state_descriptions[str(s)] = _describe_state(
                s, state_means[s], global_means, global_stds
            )

        method_label = "GaussianHMM" if used_hmm else "KMeans-fallback"
        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)
        lithmm_meta: dict[str, Any] = {
            "n_states": n_states,
            "state_descriptions": state_descriptions,
            "state_means": {str(s): state_means[s].tolist() for s in range(n_states)},
            "feature_names": FEATURE_NAMES,
            "method": method_label,
            # KMeans posteriors are one-hot hard assignments, not probabilities — flag it so a consumer
            # never renders a fabricated 1.0 as a probabilistic confidence (§5/B5b).
            "posterior_type": "probabilistic" if used_hmm else "hard-assignment",
        }
        if cfg["n_states"] != n_states:
            lithmm_meta["n_states_requested"] = cfg["n_states"]
            lithmm_meta["clamped"] = ["n_states"]
        atomic_write_text(signals_dir / "lithmm_meta.json", json.dumps(lithmm_meta, indent=2))

        paras = project.paragraphs()
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        annotations: list[Annotation] = []

        for i, (para_start, para_end, _) in enumerate(paras):
            state = int(labels[i])
            posterior = posteriors[i].tolist()

            ann = Annotation(
                body=Body(
                    type="palimpsest:LitHMMAnnotation",
                    purpose="classifying",
                    value=state_descriptions.get(str(state), f"State {state}"),
                    lfo_type="signal.lithmm_state",
                    extra={
                        "palimpsest:stateId": state,
                        "palimpsest:statePosterior": [round(p, 4) for p in posterior],
                        "palimpsest:stateDescription": state_descriptions.get(str(state), ""),
                        # Caveat travels WITH the data (§5): the UI must know whether the posterior is
                        # a real HMM probability or a one-hot KMeans hard assignment before displaying it.
                        "palimpsest:method": method_label,
                        "palimpsest:posteriorType": "probabilistic" if used_hmm else "hard-assignment",
                    },
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=para_start, end=para_end),
                ),
                creator=Creator(name="palimpsest-lithmm/0.1"),
                confidence=round(float(max(posterior)), 4),
                evidence_level="E5",
                project_id=project.metadata.id,
                track_name="lithmm",
            )
            annotations.append(ann)

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "lithmm",
            "bodyType": "palimpsest:LitHMMAnnotation",
            "colorScheme": {
                "primary": "#16a085",
                "secondary": "#1abc9c",
                "scale": [f"hsl({i * 360 // DEFAULT_N_STATES}, 65%, 55%)"
                          for i in range(DEFAULT_N_STATES)],
            },
            "textViewRendering": "color-band",
            "overviewBarRendering": {"type": "state-band", "n_states": DEFAULT_N_STATES},
        }
