"""RQA track — Recurrence Quantification Analysis (RR, DET, LAM) in sliding windows."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial.distance import cdist
from sklearn.feature_extraction.text import TfidfVectorizer

from palimpsest.formats.signals import SignalManifest, write_signal
from palimpsest.project import Project

logger = logging.getLogger(__name__)

RQA_THRESHOLD = 0.3
RQA_MIN_LINE = 2
WINDOW_WORDS = 100
WINDOW_OVERLAP = 50
TFIDF_MAX_FEATURES = 500


def _extract_windows(
    paras: list[tuple[int, int, str]],
    window_words: int = WINDOW_WORDS,
    overlap_words: int = WINDOW_OVERLAP,
) -> list[list[int]]:
    """Returns lists of paragraph indices per window, sized by word count."""
    if overlap_words >= window_words:
        raise ValueError(
            f"overlap_words ({overlap_words}) must be < window_words ({window_words})"
        )
    word_counts = [len(text.split()) for _, _, text in paras]
    cumulative = np.cumsum([0] + word_counts)
    n_words = int(cumulative[-1])
    step = window_words - overlap_words

    windows: list[list[int]] = []
    word_pos = 0
    while word_pos < n_words:
        win_end = word_pos + window_words
        para_start = int(np.searchsorted(cumulative, word_pos, side="right")) - 1
        para_end = int(np.searchsorted(cumulative, win_end, side="right")) - 1
        para_end = min(para_end, len(paras) - 1)
        para_start = max(para_start, 0)
        windows.append(list(range(para_start, para_end + 1)))
        word_pos += step

    return windows


def _compute_det(rec: np.ndarray, n: int, min_line: int) -> float:
    """Determinism: fraction of recurrent points on diagonal lines >= min_line."""
    total_rec = int(rec.sum())
    if total_rec == 0:
        return 0.0
    on_diag = 0
    for d in range(-(n - 1), n):
        diag = np.diagonal(rec, offset=d)
        run = 0
        for val in diag:
            if val:
                run += 1
            else:
                if run >= min_line:
                    on_diag += run
                run = 0
        if run >= min_line:
            on_diag += run
    return on_diag / total_rec


def _compute_lam(rec: np.ndarray, n: int, min_line: int) -> float:
    """Laminarity: fraction of recurrent points on vertical lines >= min_line."""
    total_rec = int(rec.sum())
    if total_rec == 0:
        return 0.0
    on_vert = 0
    for j in range(n):
        run = 0
        for i in range(n):
            if rec[i, j]:
                run += 1
            else:
                if run >= min_line:
                    on_vert += run
                run = 0
        if run >= min_line:
            on_vert += run
    return on_vert / total_rec


def _compute_rqa_for_window(
    state_vectors: np.ndarray,
    threshold: float = RQA_THRESHOLD,
    min_line: int = RQA_MIN_LINE,
) -> tuple[float, float, float]:
    """Compute RR, DET, LAM for a set of state vectors."""
    n = len(state_vectors)
    if n < 2:
        return 0.0, 0.0, 0.0

    distances = cdist(state_vectors, state_vectors, metric="cosine")
    rec = (distances < threshold).astype(np.int8)
    np.fill_diagonal(rec, 0)

    total = n * n - n
    rr = float(rec.sum()) / total if total > 0 else 0.0
    det = _compute_det(rec, n, min_line)
    lam = _compute_lam(rec, n, min_line)
    return rr, det, lam


class RQATrack:
    @property
    def name(self) -> str:
        return "rqa"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.rqa"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Project) -> Path:
        paras = project.paragraphs()
        if len(paras) < 2:
            metrics = np.zeros((1, 3), dtype=np.float32)
        else:
            windows = _extract_windows(paras)

            # Try embeddings first, fall back to TF-IDF
            embeddings_db = project.path / "cache" / "embeddings.db"
            state_source = "tfidf"
            all_vecs_arr = np.zeros((len(paras), 1), dtype=np.float32)

            if embeddings_db.exists():
                from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

                store = SqliteVecStore.open_existing(embeddings_db)
                all_vecs = store.get_all_vectors()
                store.close()
                if all_vecs and len(all_vecs) >= len(paras):
                    state_source = "embeddings"
                    all_vecs_arr = np.array(all_vecs, dtype=np.float32)

            if state_source == "tfidf":
                texts = [text for _, _, text in paras]
                vectorizer = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES)
                tfidf_matrix = vectorizer.fit_transform(texts).toarray()
                all_vecs_arr = tfidf_matrix.astype(np.float32)

            metrics_list: list[tuple[float, float, float]] = []
            for window_indices in windows:
                vecs = all_vecs_arr[window_indices]
                rr, det, lam = _compute_rqa_for_window(vecs)
                metrics_list.append((rr, det, lam))

            metrics = np.array(metrics_list, dtype=np.float32)

        n_windows = len(metrics)
        sha = project.metadata.reference_sha256

        manifest = SignalManifest(
            type="vector",
            name="rqa",
            source=f"rqa_{state_source}/0.1",
            reference_sha256=sha,
            dimensions=[n_windows, 3],
            data_file="rqa.bin",
            metadata={
                "metrics": ["RR", "DET", "LAM"],
                "threshold": RQA_THRESHOLD,
                "min_line": RQA_MIN_LINE,
                "window_words": WINDOW_WORDS,
                "window_overlap": WINDOW_OVERLAP,
                "state_vector_source": state_source,
                "n_windows": n_windows,
            },
        )

        signals_dir = project.path / "signals"
        write_signal(signals_dir, metrics, manifest)
        return signals_dir / "rqa.json"

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "rqa",
            "bodyType": "signal",
            "colorScheme": {
                "primary": "#F59E0B",
                "secondary": "#D97706",
                "scale": ["#FFFBEB", "#F59E0B", "#92400E"],
            },
            "dedicatedView": "bar_chart",
        }

    def parameters(self) -> dict[str, Any]:
        return {
            "rqa.threshold": RQA_THRESHOLD,
            "rqa.min_line": RQA_MIN_LINE,
            "rqa.window_words": WINDOW_WORDS,
            "rqa.window_overlap": WINDOW_OVERLAP,
        }
