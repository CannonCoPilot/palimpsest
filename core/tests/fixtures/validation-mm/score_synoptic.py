"""Score cross-book synoptic detection against the committed synoptic oracle.

The Matthew-Mark validation collection exists to answer one question empirically: does the
tooling reliably distinguish *translated-shared-source* (the same gospel in two translations —
should align end-to-end / cluster as one core per book) from *shared-content* (Matthew vs Mark —
synoptic parallels that share stories but not wording, and must NOT collapse the two books into
one homology core)? Until now that judgement was eyeball-only. This module turns the committed
`synoptic-ground-truth.json` oracle into precision/recall.

The oracle labels every Matthew<->Mark relationship: `shared_pericopes` (TP — a correct analysis
LINKS them cross-book) and `matthew_unique` ∪ `mark_unique` (TN — a correct analysis leaves them
unlinked). Each 6-way member is a verse-paragraphed Matthew+Mark subtext, so `tracks/verses.jsonl`
gives paragraph_index -> (book, chapter, verse) directly (one verse per paragraph; line index ==
paragraph index). Cross-book alignment edges (a Matthew paragraph in member A aligned to a Mark
paragraph in member B, across translations) are the pipeline's synoptic detections.

Two scores are reported:
  - synoptic detection: pooled recall over the shared pericopes, a TN false-link rate over the
    unique passages, and record-level precision (cross-book edges landing on shared vs unique
    material).
  - over-merge structure: the corpus-graph core/shell/singleton counts at a given
    ``edge_min_score``, and whether Matthew and Mark separate into distinct cores — the score-based
    homology gate the identity gate alone could not achieve.

Run against a locally-built collection (text bodies are gitignored, so this is a CLI, not a CI
test; the logic is unit-tested on synthetic data in tests/test_synoptic_scorer.py):

    core/.venv/bin/python core/tests/fixtures/validation-mm/score_synoptic.py matthew-mark-6way
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from palimpsest.alignment.records import comparison_dir, read_alignment_records
from palimpsest.collections import get_collection

ORACLE_PATH = Path(__file__).parent / "synoptic-ground-truth.json"


# ---------------------------------------------------------------------------- oracle refs

def _vnum(tok: str) -> int:
    """Verse number, ignoring a scholarly letter suffix like ``6a`` / ``16b``."""
    return int("".join(ch for ch in tok if ch.isdigit()))


def parse_ref(ref: str) -> list[tuple[int, int]]:
    """Parse an oracle verse ref into a list of (chapter, verse) pairs.

    Handles ``"3:1-6"`` (verse range within a chapter), ``"10:42"`` (single verse), the
    cross-chapter form ``"26:1-27:2"``, and verse letter-suffixes (``"3:16a"``). A same-chapter
    range is expanded inclusively; a cross-chapter range keeps its endpoints."""
    ref = ref.strip()
    if "-" not in ref:
        c, v = ref.split(":")
        return [(int(c), _vnum(v))]
    lo, hi = ref.split("-", 1)
    c_lo_s, v_lo_s = lo.split(":")
    c_lo, v_lo = int(c_lo_s), _vnum(v_lo_s)
    if ":" in hi:  # cross-chapter "27:2"
        c_hi_s, v_hi_s = hi.split(":")
        c_hi, v_hi = int(c_hi_s), _vnum(v_hi_s)
    else:  # same-chapter "6"
        c_hi, v_hi = c_lo, _vnum(hi)
    if c_lo == c_hi:
        return [(c_lo, v) for v in range(v_lo, v_hi + 1)]
    return [(c_lo, v_lo), (c_hi, v_hi)]


# ---------------------------------------------------------------------- member verse geometry

@dataclass
class MemberGeometry:
    """paragraph_index -> book, and (book, chapter, verse) -> paragraph_index, for one member."""
    para_book: list[str]                       # para_book[i] = book of paragraph i
    verse_para: dict[tuple[str, int, int], int]  # (book, chapter, verse) -> paragraph index

    def paras_for(self, book: str, refs: list[tuple[int, int]]) -> set[int]:
        return {self.verse_para[(book, c, v)] for (c, v) in refs if (book, c, v) in self.verse_para}

    def majority_book(self, start: int, end: int) -> str | None:
        books = [self.para_book[i] for i in range(start, min(end, len(self.para_book)))]
        if not books:
            return None
        return max(set(books), key=books.count)


def load_member_geometry(member_dir: Path) -> MemberGeometry:
    """Read tracks/verses.jsonl; line index is the paragraph index (one verse per paragraph)."""
    recs = [
        json.loads(line)
        for line in (member_dir / "tracks" / "verses.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    para_book = [r["b"] for r in recs]
    verse_para = {(r["b"], int(r["c"]), int(r["v"])): i for i, r in enumerate(recs)}
    return MemberGeometry(para_book=para_book, verse_para=verse_para)


# ---------------------------------------------------------------------------- scoring core

@dataclass
class SynopticScore:
    total_shared: int
    detected_shared: int
    total_unique: int
    unique_falsely_linked: int
    crossbook_records: int
    crossbook_hits_shared: int   # cross-book records landing on shared-pericope material both sides
    crossbook_on_unique: int     # cross-book records with an endpoint in a unique region

    @property
    def recall(self) -> float:
        return self.detected_shared / self.total_shared if self.total_shared else 0.0

    @property
    def precision(self) -> float:
        denom = self.crossbook_hits_shared + self.crossbook_on_unique
        return self.crossbook_hits_shared / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def tn_false_link_rate(self) -> float:
        return self.unique_falsely_linked / self.total_unique if self.total_unique else 0.0


def _overlaps(a_start: int, a_end: int, paras: set[int]) -> bool:
    """Does the half-open paragraph span [a_start, a_end) touch any paragraph in ``paras``?"""
    return any(a_start <= p < a_end for p in paras)


def score_synoptic(
    shared: list[dict], m_unique: list[dict], k_unique: list[dict],
    geoms: dict[str, MemberGeometry],
    pair_records: dict[tuple[str, str], list],
) -> SynopticScore:
    """Compute synoptic detection precision/recall.

    ``geoms`` maps member_id -> MemberGeometry; ``pair_records`` maps an unordered member pair
    (a, b) -> the list of alignment records with .query_id/.query_start/.query_end/.target_id/... .
    Detection is pooled across pairs: a shared pericope counts as recalled if ANY pair links its
    Matthew paragraphs (in one member) to its Mark paragraphs (in the other), either orientation."""
    # Pre-resolve each pericope's Matthew/Mark paragraph sets per member.
    def refs_of(p: dict, book_key: str) -> list[tuple[int, int]]:
        return parse_ref(p[book_key]) if p.get(book_key) else []

    # Recall: pool detection across pairs.
    detected = 0
    for p in shared:
        mt_refs, mk_refs = refs_of(p, "matthew"), refs_of(p, "mark")
        hit = False
        for (a, b), recs in pair_records.items():
            ga, gb = geoms[a], geoms[b]
            a_mt, a_mk = ga.paras_for("Matthew", mt_refs), ga.paras_for("Mark", mk_refs)
            b_mt, b_mk = gb.paras_for("Matthew", mt_refs), gb.paras_for("Mark", mk_refs)
            for r in recs:
                # orient the record so q-side is member a
                if r.query_id == a:
                    qs, qe, ts, te = r.query_start, r.query_end, r.target_start, r.target_end
                else:
                    qs, qe, ts, te = r.target_start, r.target_end, r.query_start, r.query_end
                linked = (
                    (_overlaps(qs, qe, a_mt) and _overlaps(ts, te, b_mk)) or
                    (_overlaps(qs, qe, a_mk) and _overlaps(ts, te, b_mt))
                )
                if linked:
                    hit = True
                    break
            if hit:
                break
        detected += hit

    # Build unique-region paragraph sets per member for TN scoring.
    def unique_paras(entries: list[dict], book: str) -> dict[str, set[int]]:
        out: dict[str, set[int]] = {}
        for mid, g in geoms.items():
            s: set[int] = set()
            for e in entries:
                s |= g.paras_for(book, parse_ref(e[book.lower()]))
            out[mid] = s
        return out

    mt_uniq_paras = unique_paras(m_unique, "Matthew")
    mk_uniq_paras = unique_paras(k_unique, "Mark")

    # Record-level precision + TN false-link rate.
    crossbook = hits_shared = on_unique = 0
    shared_mt_all: dict[str, set[int]] = {mid: set() for mid in geoms}
    shared_mk_all: dict[str, set[int]] = {mid: set() for mid in geoms}
    for p in shared:
        for mid, g in geoms.items():
            shared_mt_all[mid] |= g.paras_for("Matthew", refs_of(p, "matthew"))
            shared_mk_all[mid] |= g.paras_for("Mark", refs_of(p, "mark"))

    for recs in pair_records.values():
        for r in recs:
            qid, tid = r.query_id, r.target_id
            gq, gt = geoms[qid], geoms[tid]
            qbook = gq.majority_book(r.query_start, r.query_end)
            tbook = gt.majority_book(r.target_start, r.target_end)
            if qbook is None or tbook is None or qbook == tbook:
                continue  # same-book (translation) edge — not a synoptic detection
            crossbook += 1
            # shared both sides?
            q_shared = _overlaps(r.query_start, r.query_end,
                                 shared_mt_all[qid] if qbook == "Matthew" else shared_mk_all[qid])
            t_shared = _overlaps(r.target_start, r.target_end,
                                 shared_mt_all[tid] if tbook == "Matthew" else shared_mk_all[tid])
            if q_shared and t_shared:
                hits_shared += 1
            q_uniq = _overlaps(r.query_start, r.query_end,
                               mt_uniq_paras[qid] if qbook == "Matthew" else mk_uniq_paras[qid])
            t_uniq = _overlaps(r.target_start, r.target_end,
                               mt_uniq_paras[tid] if tbook == "Matthew" else mk_uniq_paras[tid])
            if q_uniq or t_uniq:
                on_unique += 1

    # TN passage-level: how many unique pericopes get any cross-book link.
    total_unique = len(m_unique) + len(k_unique)
    falsely_linked = _count_unique_linked(m_unique, k_unique, geoms, pair_records)

    return SynopticScore(
        total_shared=len(shared), detected_shared=detected,
        total_unique=total_unique, unique_falsely_linked=falsely_linked,
        crossbook_records=crossbook, crossbook_hits_shared=hits_shared,
        crossbook_on_unique=on_unique,
    )


def _count_unique_linked(m_unique, k_unique, geoms, pair_records) -> int:
    """A unique pericope is 'falsely linked' if some cross-book record touches its paragraphs on the
    unique side while its other side lands in the opposite book (a spurious synoptic claim)."""
    n = 0
    for entries, book in ((m_unique, "Matthew"), (k_unique, "Mark")):
        other = "Mark" if book == "Matthew" else "Matthew"
        for e in entries:
            linked = False
            for recs in pair_records.values():
                for r in recs:
                    gq, gt = geoms[r.query_id], geoms[r.target_id]
                    qb = gq.majority_book(r.query_start, r.query_end)
                    tb = gt.majority_book(r.target_start, r.target_end)
                    if qb == book and tb == other:
                        if _overlaps(r.query_start, r.query_end, gq.paras_for(book, parse_ref(e[book.lower()]))):
                            linked = True
                            break
                    if tb == book and qb == other:
                        if _overlaps(r.target_start, r.target_end, gt.paras_for(book, parse_ref(e[book.lower()]))):
                            linked = True
                            break
                if linked:
                    break
            n += linked
    return n


# ------------------------------------------------------------------------ collection loading

def load_pair_records(workspace: Path, member_ids: list[str]) -> dict[tuple[str, str], list]:
    """For every unordered member pair, locate its comparison dir (either order) and read records."""
    out: dict[tuple[str, str], list] = {}
    for a, b in combinations(member_ids, 2):
        for q, t in ((a, b), (b, a)):
            d = comparison_dir(workspace, q, t)
            if (d / "alignment.jsonl").exists():
                out[(a, b)] = read_alignment_records(d / "alignment.jsonl")
                break
    return out


def core_structure(workspace: Path, collection_id: str, edge_min_score: float) -> dict:
    """Build the corpus graph at a given score gate and summarise its pangenome structure, plus
    whether Matthew and Mark separate into distinct cores (the over-merge check)."""
    from palimpsest.corpus_graph import build_corpus_graph
    g = build_corpus_graph(workspace, collection_id, edge_min_score=edge_min_score)
    by_class: dict[str, int] = {}
    for c in g.components:
        by_class[c.classification] = by_class.get(c.classification, 0) + 1
    multi = [c for c in g.components if len(c.members) >= 2]  # backbone components (core or shell)
    spans_all = any(len(c.members) == len(g.members) for c in multi)
    return {
        "edge_min_score": edge_min_score,
        "components": len(g.components),
        "by_class": by_class,
        "backbone_member_counts": sorted((len(c.members) for c in multi), reverse=True),
        "spans_all_members": spans_all,   # True == the over-merge (one component conflates both books)
        "weak_edges": sum(1 for e in g.edges if e.get("weak")),
        "total_edges": len(g.edges),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Score synoptic cross-book detection against the oracle.")
    ap.add_argument("collection_id")
    ap.add_argument("--workspace", default=".scratch/validation-mm", type=Path)
    ap.add_argument("--min-score", type=float, default=None,
                    help="also report the corpus-graph structure at this edge_min_score gate")
    args = ap.parse_args()

    oracle = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    shared = oracle["shared_pericopes"]
    m_unique, k_unique = oracle["matthew_unique"], oracle["mark_unique"]

    col = get_collection(args.workspace, args.collection_id)
    if col is None:
        print(f"collection not found: {args.collection_id} in {args.workspace}")
        return 1
    member_ids = col["project_ids"]

    geoms = {mid: load_member_geometry(args.workspace / mid) for mid in member_ids}
    pair_records = load_pair_records(args.workspace, member_ids)

    def report(subset: list[dict], label: str) -> None:
        s = score_synoptic(subset, m_unique, k_unique, geoms, pair_records)
        print(f"\n[{label}]  shared={s.total_shared}")
        print(f"  recall           : {s.recall:.3f}  ({s.detected_shared}/{s.total_shared} shared pericopes linked cross-book)")
        print(f"  precision        : {s.precision:.3f}  ({s.crossbook_hits_shared} shared-hits / {s.crossbook_hits_shared + s.crossbook_on_unique} classified cross-book records)")
        print(f"  F1               : {s.f1:.3f}")
        print(f"  TN false-link    : {s.tn_false_link_rate:.3f}  ({s.unique_falsely_linked}/{s.total_unique} unique passages spuriously cross-linked)")
        print(f"  cross-book edges : {s.crossbook_records}")

    print(f"=== synoptic detection · {args.collection_id} · {len(member_ids)} members · "
          f"{len(pair_records)} aligned pairs ===")
    report(shared, "all confidence")
    report([p for p in shared if p.get("confidence") == "high"], "high confidence only")

    if args.min_score is not None:
        print("\n=== over-merge structure (score gate sweep) ===")
        print("  distinct source texts should form separate per-book backbones; NO single component")
        print(f"  should span all {len(member_ids)} members (that would conflate the books).")
        gates = sorted({0.0, 2.0, 5.0, 8.0, args.min_score, 20.0, 50.0})
        for gate in gates:
            st = core_structure(args.workspace, args.collection_id, gate)
            verdict = "OVER-MERGED" if st["spans_all_members"] else "split by book"
            print(f"  edge_min_score={gate:<6}: {st['by_class']}  backbones={st['backbone_member_counts']}  "
                  f"weak={st['weak_edges']}/{st['total_edges']}  [{verdict}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
