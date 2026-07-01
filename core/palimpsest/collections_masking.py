"""Cross-text masking, corpus repeats, tracks & liftover — the C5 assembler (FR-29, FR-30, FR-42).

This composes existing leaves into collection-scoped operations; the genuinely new machinery lives in
the leaves (``alignment.liftover.AlignmentMap`` for cross-text projection) and the primitives are
reused verbatim so the cross-text features can never drift from their single-text ancestors:

* **Corpus repeats** generalise Wave-0 ``repeats`` (``tracks.repeats``) from *within one text* to
  *across members*: a phrase recurring in ``>= min_members`` distinct members. The tokeniser,
  normaliser, stopword set and span-merge are imported from ``tracks.repeats`` unchanged — only the
  cross-member tally is new (it must be; within-text counting can't see a once-per-member phrase).
* **Low correspondence** is read straight off the C3 corpus graph: a *singleton* component is a passage
  that aligned to no other member, so its member char-span is the low-correspondence region — no new
  detection.
* **Cross-text mask** = corpus-repeat ∪ low-correspondence per member, delivered as original-coordinate
  intervals through the existing ``Project.analysis_view(extra_masked=...)`` channel, so a masked run
  reuses the whole masking/OffsetMap pipeline and demonstrably changes a downstream alignment.
* **Cross-text track** annotates each root-frame passage with how conserved it is across the corpus —
  a pure transform over the C3 graph's ``project_to_root`` output (root char span + member set per
  component), rendered as a lane on the root lens. Collection-scoped (kept in the collection tier, not
  the root project's per-project registry), so collection membership never leaks into project state.
* **Liftover** projects one member's mask/annotation intervals onto another member's coordinate frame
  across their stored alignment via ``AlignmentMap``, persisted as a new *additive* run version
  (FR-41 non-destructive; nothing on the target is overwritten).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from palimpsest.alignment.liftover import AlignmentMap
from palimpsest.alignment.records import comparison_dir, read_alignment_records
from palimpsest.collections import get_collection
from palimpsest.collections_ops import append_run_version, is_stale
from palimpsest.corpus_graph import project_to_root, read_corpus_graph
from palimpsest.project import Project
from palimpsest.tracks.repeats import (
    STOPWORDS,
    _WORD_RE,
    _merge_spans,
    _normalise,
    DEFAULT_MAX_PHRASE_LEN,
    EXACT_REPEAT_MIN_WORDS,
)

Span = tuple[int, int]


# ── corpus repeats (cross-member) ─────────────────────────────────────────────────────────────────

def _member_phrases(normalised: list[str], min_words: int, max_ngram: int) -> set[str]:
    """The distinct content n-grams (length ``min_words..max_ngram``) present in one member's tokens.

    Distinct — not occurrence-counted — because corpus-repeat membership is *does this phrase appear in
    this member at all*, tallied across members afterwards. All-stopword grams are skipped, matching the
    single-text path's filter so the two features agree on what a phrase is."""
    phrases: set[str] = set()
    for n in range(min_words, max_ngram + 1):
        for start in range(len(normalised) - n + 1):
            gram = normalised[start:start + n]
            if all(w in STOPWORDS or not w for w in gram):
                continue
            key = " ".join(gram)
            if key.strip():
                phrases.add(key)
    return phrases


def _phrase_intervals(text: str, phrases: set[str]) -> list[Span]:
    """Character intervals in ``text`` covered by any phrase in ``phrases`` (merged, disjoint).

    Same occurrence→span mapping as ``tracks.repeats.detect_repeats``, reusing the shared tokeniser and
    normaliser so the coordinates match the single-text path exactly."""
    if not phrases:
        return []
    tokens = list(_WORD_RE.finditer(text))
    normalised = _normalise([t.group() for t in tokens])
    spans: list[Span] = []
    for phrase in phrases:
        ptoks = phrase.split()
        plen = len(ptoks)
        for start in range(len(normalised) - plen + 1):
            if normalised[start:start + plen] == ptoks:
                spans.append((tokens[start].start(), tokens[start + plen - 1].end()))
    return _merge_spans(spans)


def corpus_repeats(
    workspace: Path,
    collection_id: str,
    *,
    min_words: int = EXACT_REPEAT_MIN_WORDS,
    max_phrase_len: int = DEFAULT_MAX_PHRASE_LEN,
    min_members: int = 2,
) -> dict[str, Any]:
    """Phrases recurring across ``>= min_members`` members of a collection, with per-member intervals.

    Returns ``{collection_id, members, min_members, phrases: [str], phrase_members: {phrase: count},
    intervals: {member: [[s, e], ...]}, summary}``. Intervals are original-coordinate character spans
    ready to feed ``Project.analysis_view(extra_masked=...)`` or a signal layer's ``segment_offsets``."""
    collection = get_collection(workspace, collection_id)
    if collection is None:
        raise ValueError(f"Collection not found: {collection_id}")
    members: list[str] = list(collection.get("project_ids", []))
    if len(members) < 2:
        raise ValueError("Corpus repeats need at least 2 members")

    member_texts: dict[str, str] = {}
    member_phrase_sets: dict[str, set[str]] = {}
    for m in members:
        text = Project.load(workspace / m).reference_text()
        member_texts[m] = text
        words = [t.group() for t in _WORD_RE.finditer(text)]
        if len(words) < min_words:
            member_phrase_sets[m] = set()
            continue
        max_ngram = min(max_phrase_len, len(words) // 2)
        member_phrase_sets[m] = _member_phrases(_normalise(words), min_words, max_ngram)

    # Tally distinct members per phrase; a corpus repeat recurs in >= min_members of them.
    phrase_members: dict[str, int] = {}
    for phrases in member_phrase_sets.values():
        for p in phrases:
            phrase_members[p] = phrase_members.get(p, 0) + 1
    corpus_phrases = {p for p, c in phrase_members.items() if c >= min_members}

    intervals: dict[str, list[list[int]]] = {}
    for m in members:
        member_hits = corpus_phrases & member_phrase_sets[m]
        spans = _phrase_intervals(member_texts[m], member_hits)
        intervals[m] = [[s, e] for s, e in spans]

    return {
        "collection_id": collection_id,
        "members": members,
        "min_members": min_members,
        "phrases": sorted(corpus_phrases),
        "phrase_members": {p: phrase_members[p] for p in sorted(corpus_phrases)},
        "intervals": intervals,
        "summary": {
            "phrase_count": len(corpus_phrases),
            "masked_chars": {m: sum(e - s for s, e in intervals[m]) for m in members},
        },
    }


# ── low correspondence (from the corpus graph's singletons) ──────────────────────────────────────

def low_correspondence_intervals(workspace: Path, collection_id: str) -> dict[str, list[list[int]]]:
    """Per-member character spans that aligned to no other member — the corpus graph's singleton nodes.

    Requires the corpus graph to have been built (C3). Nodes without character spans (a member whose
    ``metadata.json`` couldn't be loaded to attach char spans) are skipped, not guessed."""
    graph = read_corpus_graph(workspace, collection_id)
    if graph is None:
        raise ValueError(f"No corpus graph for {collection_id} — build it first (C3)")
    node_by_id = {n.id: n for n in graph.nodes}
    per_member: dict[str, list[Span]] = {m: [] for m in graph.members}
    for comp in graph.components:
        if comp.classification != "singleton":
            continue
        for nid in comp.node_ids:
            node = node_by_id.get(nid)
            if node is None or node.char_start is None or node.char_end is None:
                continue
            per_member.setdefault(node.member, []).append((node.char_start, node.char_end))
    return {m: [[s, e] for s, e in _merge_spans(spans)] for m, spans in per_member.items()}


# ── cross-text mask ──────────────────────────────────────────────────────────────────────────────

def cross_text_mask(
    workspace: Path,
    collection_id: str,
    member: str,
    *,
    include_repeats: bool = True,
    include_low_correspondence: bool = True,
    min_words: int = EXACT_REPEAT_MIN_WORDS,
    max_phrase_len: int = DEFAULT_MAX_PHRASE_LEN,
    min_members: int = 2,
) -> dict[str, Any]:
    """The cross-text mask intervals for one member: corpus-repeat ∪ low-correspondence.

    Returns ``{member, intervals: [[s, e]], sources: {repeats, low_correspondence}, masked_chars}``.
    ``intervals`` are original-coordinate, merged and disjoint — ready for ``extra_masked``."""
    repeat_spans: list[Span] = []
    low_spans: list[Span] = []
    if include_repeats:
        cr = corpus_repeats(
            workspace, collection_id,
            min_words=min_words, max_phrase_len=max_phrase_len, min_members=min_members,
        )
        repeat_spans = [(s, e) for s, e in cr["intervals"].get(member, [])]
    if include_low_correspondence:
        low = low_correspondence_intervals(workspace, collection_id)
        low_spans = [(s, e) for s, e in low.get(member, [])]
    merged = _merge_spans(repeat_spans + low_spans)
    return {
        "member": member,
        "intervals": [[s, e] for s, e in merged],
        "sources": {
            "repeats": [[s, e] for s, e in _merge_spans(repeat_spans)],
            "low_correspondence": [[s, e] for s, e in _merge_spans(low_spans)],
        },
        "masked_chars": sum(e - s for s, e in merged),
    }


def masked_cross_similarity(
    project_a: Project,
    project_b: Project,
    *,
    mask_a: list[Span] | None = None,
    mask_b: list[Span] | None = None,
    metric: str = "word_overlap",
) -> Any:
    """Cross-similarity matrix with each member's cross-text mask excised before comparison.

    The mechanism behind done-criterion 2 (a cross-text mask *changes* a downstream alignment): masking
    a member with ``analysis_view(extra_masked=...)`` alters its paragraph token-sets, so the matrix
    differs from the unmasked run. Reuses the existing compute path — no new similarity maths."""
    from palimpsest.alignment.cross_similarity import compute_cross_similarity, compute_word_overlap

    view_a = project_a.analysis_view(extra_masked=list(mask_a))[0] if mask_a else project_a
    view_b = project_b.analysis_view(extra_masked=list(mask_b))[0] if mask_b else project_b
    if metric == "word_overlap":
        matrix, _ = compute_word_overlap(view_a, view_b)
    else:
        matrix, _ = compute_cross_similarity(view_a, view_b, metric=metric)
    return matrix


# ── cross-text track on the root lens ────────────────────────────────────────────────────────────

def cross_text_track(
    workspace: Path,
    collection_id: str,
    root: str,
    *,
    kind: str = "conservation",
) -> dict[str, Any]:
    """A cross-text similarity track expressed on the ``root`` member's coordinate frame.

    Each in-root passage (a graph component present in the root) is annotated with its *conservation* —
    the fraction of members whose text corresponds there (core → 1.0, shell → partial, root-only → 1/N).
    A pure read of the C3 graph's ``project_to_root`` output: the root char spans and member sets are
    already computed, so no new coordinate math enters. Returns root-frame ``segment_offsets`` + a
    per-segment scalar in [0, 1] plus a ``rendering`` descriptor shaped for a lane, so the frontend
    draws it on the root lens the same way ordinary segment tracks are drawn (FR-13 shape).

    Raises ``ValueError`` if the corpus graph is missing or ``root`` is not a member.
    """
    graph = read_corpus_graph(workspace, collection_id)
    if graph is None:
        raise ValueError(f"No corpus graph for {collection_id} — build it first (C3)")
    proj = project_to_root(graph, root)  # raises ValueError if root is not a member
    total = len(graph.members)
    segments: list[dict[str, Any]] = []
    for row in proj["components"]:
        rs = row.get("root_span")
        if not row.get("in_root") or rs is None:
            continue
        member_count = len(row["members"])
        segments.append({
            "component": row["component"],
            "classification": row["classification"],
            "char_start": rs["char_start"],
            "char_end": rs["char_end"],
            "para_start": rs["para_start"],
            "para_end": rs["para_end"],
            "member_count": member_count,
            "conservation": member_count / total if total else 0.0,
            "members": row["members"],
        })
    segments.sort(key=lambda s: (s["char_start"], s["char_end"]))
    return {
        "collection_id": collection_id,
        "root": root,
        "kind": kind,
        "member_total": total,
        "segment_offsets": [[s["char_start"], s["char_end"]] for s in segments],
        "values": [s["conservation"] for s in segments],
        "segments": segments,
        "rendering": {"track_view": "root-conservation-lane", "encoding": "heat", "domain": [0.0, 1.0]},
    }


def write_cross_text_track(
    workspace: Path, collection_id: str, track: dict[str, Any]
) -> Path:
    """Persist a cross-text track under the collection tier (workspace/collections/{id}/, OQ-6)."""
    path = workspace / "collections" / collection_id / "tracks" / f"{track['kind']}_{track['root']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(track, indent=2), encoding="utf-8")
    return path


# ── liftover (project a member's intervals onto another via their alignment) ─────────────────────

def _find_pair(workspace: Path, a: str, b: str) -> tuple[Path, str, str] | None:
    """Locate a stored comparison for the unordered pair ``{a, b}`` → (dir, query_id, target_id)."""
    for q, t in ((a, b), (b, a)):
        d = comparison_dir(workspace, q, t)
        if (d / "alignment.jsonl").exists() and (d / "metadata.json").exists():
            meta = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
            return d, meta.get("query_id", q), meta.get("target_id", t)
    return None


def _para_spans(workspace: Path, member: str) -> list[Span]:
    return [(s, e) for s, e, _ in Project.load(workspace / member).paragraphs()]


def lift_intervals_across(
    workspace: Path,
    source_id: str,
    target_id: str,
    intervals: list[Span],
) -> dict[str, Any]:
    """Project ``source_id``'s intervals onto ``target_id``'s coordinate frame via their alignment.

    Returns ``{source_id, target_id, lifted: [[s, e]], dropped: [[s, e]], comparison}``. ``dropped``
    are source intervals that touched no aligned block (reported, never silent — principles §4.1).
    Raises ``ValueError`` if no alignment exists for the pair."""
    found = _find_pair(workspace, source_id, target_id)
    if found is None:
        raise ValueError(f"No alignment stored for pair {{{source_id}, {target_id}}}")
    comp_dir, query_id, target = found
    records = read_alignment_records(comp_dir / "alignment.jsonl")
    query_spans = _para_spans(workspace, query_id)
    target_spans = _para_spans(workspace, target)
    # Orient the map so source_id is the projection source regardless of which axis owns it.
    if source_id == query_id:
        amap = AlignmentMap.from_records(records, query_spans, target_spans, source="query")
    else:
        amap = AlignmentMap.from_records(records, target_spans, query_spans, source="target")
    lifted, dropped = amap.lift_intervals([(s, e) for s, e in intervals])
    return {
        "source_id": source_id,
        "target_id": target_id,
        "lifted": [[s, e] for s, e in lifted],
        "dropped": [[s, e] for s, e in dropped],
        "comparison": comp_dir.name,
    }


@dataclass(frozen=True)
class LiftedTrack:
    source_id: str
    target_id: str
    kind: str
    lifted: list[list[int]]
    dropped: list[list[int]]


def _liftover_versions_path(workspace: Path, collection_id: str, target_id: str, kind: str) -> Path:
    return workspace / "collections" / collection_id / "liftover" / target_id / f"{kind}.versions.json"


def persist_lifted_track(
    workspace: Path,
    collection_id: str,
    result: dict[str, Any],
    *,
    kind: str = "mask",
) -> dict[str, Any]:
    """Persist a liftover result on the target as a NEW additive run version (FR-41 non-destructive).

    Nothing already on the target is touched: each lift appends a version keyed by a content identity
    (source, target, kind, lifted spans), so re-lifting identical inputs is idempotent while a changed
    source produces a fresh version. Returns the appended version record."""
    identity = _lift_identity(result, kind)
    versions_path = _liftover_versions_path(workspace, collection_id, result["target_id"], kind)
    payload_path = versions_path.parent / f"{kind}.{identity}.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(
        json.dumps(
            {
                "source_id": result["source_id"],
                "target_id": result["target_id"],
                "kind": kind,
                "lifted": result["lifted"],
                "dropped": result["dropped"],
                "comparison": result.get("comparison"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return append_run_version(
        versions_path,
        identity,
        metadata={
            "source_id": result["source_id"],
            "target_id": result["target_id"],
            "kind": kind,
            "lifted_spans": len(result["lifted"]),
            "dropped_spans": len(result["dropped"]),
            "payload": payload_path.name,
        },
    )


def _lift_identity(result: dict[str, Any], kind: str) -> str:
    import hashlib

    key = json.dumps(
        [kind, result["source_id"], result["target_id"], result["lifted"]],
        sort_keys=True,
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def lifted_track_is_stale(
    workspace: Path,
    collection_id: str,
    result: dict[str, Any],
    *,
    kind: str = "mask",
) -> bool:
    """Whether the current lift differs from the latest persisted version (FR-28 staleness)."""
    versions_path = _liftover_versions_path(workspace, collection_id, result["target_id"], kind)
    return is_stale(versions_path, _lift_identity(result, kind))
