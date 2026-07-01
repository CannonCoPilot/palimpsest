"""collections_sweep — the recall-dial sweep over a collection, with a resumable run journal (C6c).

Assembler beside ``collections_probe`` (C6b) / ``collections_masking`` (C5): it walks every member pair
of a collection, reduces each member to the recall dial's primitive (paragraph token-shingles for the
token/word family; chunk embedding vectors for the embedding family), calls
``analysis.candidate_gen`` to prune the O(N×M) chunk-pair space at the chosen recall mode, and records
each pair's result to a **lightweight run journal** under ``workspace/collections/{id}/sweeps/``.

Run-persistence decision (Sir, 2026-06-30): a JSON sidecar for resumability, *not* a general job
scheduler. The ``run_id`` is content-addressed from the collection + members + mode + metric (no
wall-clock), so re-invoking the same sweep re-opens the same journal and **skips member pairs already
marked done** — resume-after-interruption for free. A full persistent job DB is the deferred later-phase
feature for when corpus-scale multi-stage sweeps outgrow this sidecar.

Honesty carried from the dial: every pair reports ``n_pairs_total / n_candidates / n_pruned`` and an
empirical ``estimated_recall`` — a pruned pair count is never silent. Embedding sweeps are gated by the
C1 metric-congruence contract (reusing the C6b gate), so a mixed-space corpus fails loud, never a silent
cross-space sweep.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from palimpsest import collections as col_store
from palimpsest.analysis import candidate_gen as cg
from palimpsest.corpus_graph import corpus_graph_dir

ProgressCb = Callable[[int, int, str], None]

_SHINGLE_K = 3           # word-shingle length for the token/word family
_RECALL_SAMPLE_STRIDE = 8  # oracle sample density for the empirical recall estimate
_RECALL_TOP_N = 3


def sweeps_dir(workspace: Path, collection_id: str) -> Path:
    return corpus_graph_dir(workspace, collection_id) / "sweeps"


def sweep_run_id(collection_id: str, members: list[str], mode: str, metric: str, force_exhaustive: bool) -> str:
    """Content-addressed, wall-clock-free run id: identical sweep params → identical id → same journal →
    automatic resume. Members are sorted so member order never forks a run."""
    payload = "|".join([collection_id, ",".join(sorted(members)), mode, metric, str(force_exhaustive)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def sweep_journal_path(workspace: Path, collection_id: str, run_id: str) -> Path:
    return sweeps_dir(workspace, collection_id) / f"{run_id}.json"


def read_sweep_journal(workspace: Path, collection_id: str, run_id: str) -> dict[str, Any] | None:
    path = sweep_journal_path(workspace, collection_id, run_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_journal(path: Path, journal: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(journal, indent=2, ensure_ascii=False), encoding="utf-8")


def _pair_key(a: str, b: str) -> str:
    return f"{a}\x00{b}"


# ── member → dial primitive reductions ────────────────────────────────────────────────────────────

def _paragraph_shingles(workspace: Path, project_id: str) -> list[set[int]]:
    """Each member paragraph reduced to a set of hashed word-shingles (the token/word dial primitive).
    Short paragraphs fall back to their token set so they still participate."""
    from palimpsest.analysis.textstats import TOKEN_RE
    from palimpsest.project import Project

    project = Project.load(workspace / project_id)
    out: list[set[int]] = []
    for _s, _e, text in project.paragraphs():
        toks = TOKEN_RE.findall(text.lower())
        if len(toks) >= _SHINGLE_K:
            grams = {" ".join(toks[i:i + _SHINGLE_K]) for i in range(len(toks) - _SHINGLE_K + 1)}
        else:
            grams = set(toks)
        out.append({int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big") for g in grams})
    return out


def _member_vectors(workspace: Path, project_id: str, embedding_label: str | None):
    import numpy as np

    from palimpsest.collections_ops import member_embedding_layer
    from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

    layer = member_embedding_layer(workspace, project_id, embedding_label)
    if layer is None:
        raise ValueError(f"member {project_id!r} has no embedding layer for an embedding sweep")
    db = workspace / project_id / "cache" / f"embeddings_{layer.label}.db"
    if not db.exists():
        raise FileNotFoundError(f"embedding store missing at {db}")
    store = SqliteVecStore.open_existing(db)
    try:
        return np.array(store.get_all_vectors(), dtype=np.float32)
    finally:
        store.close()


def _candidates_for_pair(
    metric: str, plan: dict, prim_a: Any, prim_b: Any
) -> tuple[list[tuple[int, int]], set[tuple[int, int]] | None]:
    """Generate candidate pairs + the recall oracle for one member pair, dispatched by metric family."""
    if plan["dense"]:
        return [], None
    if cg_metric_needs_embedding(metric):
        pairs = cg.ann_candidate_pairs(prim_a, prim_b, plan["depth"])
        oracle = cg.exact_top_pairs_cosine(
            prim_a, prim_b, sample_stride=_RECALL_SAMPLE_STRIDE, top_n=_RECALL_TOP_N)
    else:
        num_perm = plan["bands"] * 4  # 4 rows per band
        sig_a = cg.minhash_signatures(prim_a, num_perm)
        sig_b = cg.minhash_signatures(prim_b, num_perm)
        pairs = cg.lsh_candidate_pairs(sig_a, sig_b, plan["bands"])
        oracle = cg.exact_top_pairs_jaccard(
            prim_a, prim_b, sample_stride=_RECALL_SAMPLE_STRIDE, top_n=_RECALL_TOP_N)
    return pairs, oracle


def cg_metric_needs_embedding(metric: str) -> bool:
    from palimpsest.collections_ops import metric_needs_embedding

    return metric_needs_embedding(metric)


def _pair_sizes(metric: str, prim_a: Any, prim_b: Any) -> tuple[int, int]:
    if cg_metric_needs_embedding(metric):
        return int(prim_a.shape[0]), int(prim_b.shape[0])
    return len(prim_a), len(prim_b)


def sweep_pairwise(
    workspace: Path,
    collection_id: str,
    *,
    metric: str = "word_overlap",
    mode: str = "high-recall",
    force_exhaustive: bool = False,
    embedding_label: str | None = None,
    dense_threshold: int = cg.DENSE_PAIR_THRESHOLD,
    resume: bool = True,
    progress_cb: ProgressCb | None = None,
) -> dict[str, Any]:
    """Sweep every member pair with the recall dial, journaled + resumable (C6c, FR-35).

    Embedding metrics are congruence-gated (fail-loud on a mixed-space corpus). Each member pair is
    planned (exhaustive for small spaces or ``force_exhaustive``, else candidate-generated at ``mode``),
    its candidates + empirical recall recorded to the journal, and (when ``resume``) pairs already marked
    done are skipped. ``progress_cb(done, total, label)`` fires per pair for staged %-progress."""
    col = col_store.get_collection(workspace, collection_id)
    if col is None:
        raise KeyError(collection_id)
    members: list[str] = col.get("project_ids", [])
    if len(members) < 2:
        raise ValueError(f"collection {collection_id!r} needs >= 2 members to sweep")

    # Embedding sweeps: enforce the C1 metric-congruence contract up front (fail-loud, never mixed-space).
    if cg_metric_needs_embedding(metric):
        from palimpsest.collections_probe import _gate_congruent_cohort

        _gate_congruent_cohort(workspace, collection_id, metric, embedding_label)

    run_id = sweep_run_id(collection_id, members, mode, metric, force_exhaustive)
    path = sweep_journal_path(workspace, collection_id, run_id)
    journal = read_sweep_journal(workspace, collection_id, run_id) if resume else None
    if journal is None:
        journal = {
            "run_id": run_id, "collection_id": collection_id, "metric": metric,
            "mode": mode, "force_exhaustive": force_exhaustive, "members": members,
            "dense_threshold": dense_threshold, "pairs": {},
        }

    ordered = sorted(members)
    member_pairs = [(ordered[i], ordered[j]) for i in range(len(ordered)) for j in range(i + 1, len(ordered))]
    total = len(member_pairs)

    prim_cache: dict[str, Any] = {}

    def primitive(pid: str) -> Any:
        if pid not in prim_cache:
            prim_cache[pid] = (
                _member_vectors(workspace, pid, embedding_label)
                if cg_metric_needs_embedding(metric)
                else _paragraph_shingles(workspace, pid)
            )
        return prim_cache[pid]

    done = 0
    for a, b in member_pairs:
        key = _pair_key(a, b)
        if resume and journal["pairs"].get(key, {}).get("done"):
            done += 1
            if progress_cb:
                progress_cb(done, total, f"{a} vs {b} (cached)")
            continue

        prim_a, prim_b = primitive(a), primitive(b)
        n_a, n_b = _pair_sizes(metric, prim_a, prim_b)
        plan = cg.plan_sweep(n_a, n_b, mode, force_exhaustive=force_exhaustive, dense_threshold=dense_threshold)
        pairs, oracle = _candidates_for_pair(metric, plan, prim_a, prim_b)
        summary = cg.summarize_candidates(n_a, n_b, pairs, oracle, dense=plan["dense"])

        journal["pairs"][key] = {
            "a": a, "b": b, "plan": plan, **summary,
            "candidates": pairs if not plan["dense"] else None,
            "done": True,
        }
        _write_journal(path, journal)  # checkpoint after every pair → interruption loses at most one pair
        done += 1
        if progress_cb:
            progress_cb(done, total, f"{a} vs {b}")

    journal["progress"] = {"pairs_total": total, "pairs_done": done}
    _write_journal(path, journal)
    return _summarize_run(journal)


def _summarize_run(journal: dict[str, Any]) -> dict[str, Any]:
    """A compact roll-up of a journal for the API/CLI: per-run totals + per-pair headline numbers,
    without echoing the (potentially large) candidate index lists."""
    pairs = journal.get("pairs", {})
    total_pairs = sum(p["n_pairs_total"] for p in pairs.values())
    total_cand = sum(p["n_candidates"] for p in pairs.values())
    recalls = [p["estimated_recall"] for p in pairs.values() if p.get("estimated_recall") is not None]
    return {
        "run_id": journal["run_id"],
        "collection_id": journal["collection_id"],
        "metric": journal["metric"],
        "mode": journal["mode"],
        "force_exhaustive": journal["force_exhaustive"],
        "members": journal["members"],
        "n_member_pairs": len(pairs),
        "n_pairs_total": total_pairs,
        "n_candidates": total_cand,
        "n_pruned": total_pairs - total_cand,
        "prune_fraction": round((total_pairs - total_cand) / total_pairs, 4) if total_pairs else 0.0,
        "mean_estimated_recall": round(sum(recalls) / len(recalls), 4) if recalls else None,
        "pairs": [
            {k: v.get(k) for k in (
                "a", "b", "n_pairs_total", "n_candidates", "n_pruned",
                "prune_fraction", "estimated_recall", "dense")}
            for v in pairs.values()
        ],
    }


# ── run/version manager (C7, FR-35) ────────────────────────────────────────────────────────────────

def _run_headline(journal: dict[str, Any]) -> dict[str, Any]:
    """A one-line-per-run summary for the run manager list: the roll-up headline numbers plus progress,
    without the per-pair detail (fetch the full journal via ``read_sweep_journal`` for that)."""
    roll = _summarize_run(journal)
    roll.pop("pairs", None)
    roll["progress"] = journal.get("progress", {"pairs_total": 0, "pairs_done": 0})
    return roll


def list_sweep_runs(workspace: Path, collection_id: str) -> list[dict[str, Any]]:
    """Every persisted sweep run for a collection, as compact headlines (C7 run/version manager).
    Ordered by run_id for a stable listing; a corrupt/partial journal is skipped rather than failing the
    whole list."""
    d = sweeps_dir(workspace, collection_id)
    if not d.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(d.glob("*.json")):
        try:
            journal = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        out.append(_run_headline(journal))
    return out


def delete_sweep_run(workspace: Path, collection_id: str, run_id: str) -> bool:
    """Delete a sweep run's journal (C7 run/version manager). Returns False if the run does not exist.
    Sweeps are recomputable candidate-gen artifacts — deleting one discards only its cached journal, never
    any ground-truth data."""
    path = sweep_journal_path(workspace, collection_id, run_id)
    if not path.exists():
        return False
    path.unlink()
    return True
