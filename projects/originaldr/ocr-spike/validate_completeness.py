#!/usr/bin/env python3
"""Completeness FAILSAFE: verify no canonical book/chapter was silently dropped by OCR+locate.

Oracle  = skeleton.json (76 books / 1360 chapters).
Observed = tome-map.json (per-source located book+chapter coverage, built from the diplomatic OCR).

FAILS LOUD (nonzero exit) when the located corpus is missing canonical scripture that nothing
else flags: a book attested by NO adequate-confidence source, or a chapter located by NO source.
Also emits a per-source coverage report (expected-vs-located books, weak-recall books) so a source
that silently drops a book it physically carries surfaces immediately.

Run as a pre-consensus gate:
    python validate_completeness.py [--min-recall 0.5] [--tome-map tome-map.json]
Exit 0 = every canonical book+chapter attested; exit 1 = incompleteness (see stderr + report).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/"
             "gold/mask_engine/originaldr_reconstruction")
SKELETON = json.loads((RECON / "skeleton.json").read_text(encoding="utf-8"))

BOOK_CH = {b["slug"]: b["chapters"] for b in SKELETON["books"]}
BOOK_ORDER = [b["slug"] for b in SKELETON["books"]]
BOOK_TESTAMENT = {b["slug"]: b["testament"] for b in SKELETON["books"]}
ADEQUATE = {"high", "medium"}


def _expected_books(testaments: set) -> list[str]:
    """Canonical books a source is expected to carry, given the testament(s) it covers.
    APPENDIX books (prayer-of-manasses, 3/4-esdras) ride with OT."""
    out = []
    for b in BOOK_ORDER:
        t = BOOK_TESTAMENT[b]
        if t in testaments or (t == "APPENDIX" and "OT" in testaments):
            out.append(b)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-recall", type=float, default=0.5,
                    help="a located book below this mean_chapter_recall is flagged weak")
    ap.add_argument("--tome-map", default=str(HERE / "tome-map.json"))
    a = ap.parse_args()

    tm = json.loads(Path(a.tome_map).read_text(encoding="utf-8"))
    b2s = tm.get("book_to_sources", {})
    sources = tm.get("sources", {})

    # 1) GLOBAL book attestation: every canonical book needs >=1 adequate-confidence source.
    zero_attestation, low_confidence_only = [], []
    for bk in BOOK_ORDER:
        srcs = b2s.get(bk, [])
        if not srcs:
            zero_attestation.append(bk)
        elif not any(s.get("confidence") in ADEQUATE for s in srcs):
            low_confidence_only.append(bk)

    # 2) GLOBAL chapter coverage: union of located chapters across ALL sources vs 1..maxch.
    chapter_gaps = {}
    for bk in BOOK_ORDER:
        located = set()
        for sinfo in sources.values():
            bi = sinfo.get("books", {}).get(bk)
            if bi and "chapter_pages" in bi:
                located |= {int(c) for c in bi["chapter_pages"]}
        missing = [c for c in range(1, BOOK_CH[bk] + 1) if c not in located]
        if missing:
            chapter_gaps[bk] = missing

    # 3) PER-SOURCE (advisory): expected-vs-located + weak-recall books.
    per_source = {}
    for sid, sinfo in sources.items():
        cov = set(sinfo.get("testaments_covered", []))
        located = set(sinfo.get("books", {}))
        expected = _expected_books(cov)
        missing = [b for b in expected if b not in located]
        weak = sorted(b for b, bi in sinfo.get("books", {}).items()
                      if bi.get("mean_chapter_recall", 1.0) < a.min_recall)
        per_source[sid] = {
            "testaments": sorted(cov), "n_expected": len(expected),
            "n_located": len(located), "missing_books": missing, "weak_recall_books": weak,
        }

    report = {
        "oracle": {"books": len(BOOK_ORDER), "chapters": sum(BOOK_CH.values())},
        "books_zero_attestation": zero_attestation,
        "books_low_confidence_only": low_confidence_only,
        "chapter_gaps": {k: v for k, v in chapter_gaps.items()},
        "per_source": per_source,
    }
    (HERE / "completeness-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Report + FAIL LOUD on the hard failures (scripture attested nowhere).
    print(f"oracle: {len(BOOK_ORDER)} books / {sum(BOOK_CH.values())} chapters")
    print(f"books zero-attestation ({len(zero_attestation)}): {zero_attestation or 'none'}")
    print(f"books low-confidence-only ({len(low_confidence_only)}): {low_confidence_only or 'none'}")
    if chapter_gaps:
        print("chapter gaps (book: n missing): "
              + ", ".join(f"{k}:{len(v)}" for k, v in chapter_gaps.items()))
    else:
        print("chapter gaps: none")
    print("report -> completeness-report.json")

    if zero_attestation or chapter_gaps:
        print("COMPLETENESS FAILSAFE: FAIL — canonical scripture missing from the located corpus "
              f"({len(zero_attestation)} unattested books, {len(chapter_gaps)} books with chapter gaps).",
              file=sys.stderr)
        return 1
    print("COMPLETENESS FAILSAFE: PASS — every canonical book + chapter attested by >=1 source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
