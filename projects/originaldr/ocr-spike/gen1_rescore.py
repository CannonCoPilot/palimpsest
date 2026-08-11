# -*- coding: utf-8 -*-
"""GENESIS 1, RESCORED — every verse of every witness against all four references, classified by cause.

WHY ONE CHAPTER, EXHAUSTIVELY (Sir, 2026-07-28). Genesis 1 is the worst chapter in the book for all four
witnesses at once, which by the book-audit's control logic makes it vertical. Scoring 31 verses × 4 witnesses
against all 4 references — instead of the single governing one — separates causes that the pass/fail bit
merges, because a verse can fail for reasons that live in completely different layers and look identical from
the gate.

THE FOUR REFERENCES. Archaic: `s_dismas` (preeminent) and `odr_com` (backfill). Modern: `sabates_a` (also the
janvier grid the spans are cut on) and `madueke_b`. A verse scored against all four exposes the case the
governing gate cannot: **the witnesses and the modern references agree, and the archaic reference is the
outlier.** Genesis 1:25 is exactly that — four witnesses at 0.93–0.97 modern, all failing on an s_dismas
reading at 0.75, which is not a misalignment (offset 0 scores best) but a divergent reading.

CLASSES, decided in this order — the first that applies wins, because they are not independent and the
earliest is the one worth fixing:

  L4-SHORT     the span is under half the reference length — the localizer found almost nothing
  L4-LONG      the span is over 1.5× — it swallowed a neighbour, an argument, or a facing column
  V3-APPARATUS the span carries an interleaved annotation fragment (a soft-hyphen break mid-verse, or a
               run that matches no reference and is not archaic spelling)
  V6-REF       the witnesses and both modern references agree; the archaic reference is the outlier
  V5-RECOG     none of the above — the words are there and misrecognised, which is recognizer territory
  PASS         at or above the bar

Usage:  python gen1_rescore.py [--book genesis] [--chapter 1]
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import book_audit as BA                      # noqa: E402
import corpus_localize as CL                 # noqa: E402  # Gate 0f route to the localization artefact
import qc_audit as QC                        # noqa: E402
import verse_seg as VS                       # noqa: E402
from char_identity import evaluate_locus     # noqa: E402

REF_NAMES = ("s_dismas", "odr_com", "sabates_a", "madueke_b")
BAR = 0.90


def _score(got: str, ref: str | None):
    if not got or not ref:
        return None
    return round(evaluate_locus(got, ref, ref)["archaic_id"], 4)


def rescore(book: str, chapter: int) -> dict:
    wits = BA.witnesses_for_book(book)
    refs = {n: QC.load_reads_verse(n) for n in REF_NAMES}
    aud = json.loads((HERE / "coverage-audit-verse.json").read_text())["verses"]
    loc = {s: CL.load_verses(d) for s, d in wits.items()}      # R9.2c: through Gate 0f, not around it
    cv = VS.chapter_verses(book, chapter, VS.JANVIER) or {}

    verses, klass = [], collections.Counter()
    for v in sorted(cv):
        key = f"scripture/{book}/{chapter}/{v}"
        a = aud.get(key) or {}
        ref_len = len((refs["odr_com"].get(key) or refs["sabates_a"].get(key) or "").split())
        row = {"verse": v, "ref_tokens": ref_len, "witnesses": {}}
        for s in wits:
            st = (a.get("sources", {}).get(s) or {})
            rec = loc[s].get(f"{book}/{chapter}/{v}") or {}
            got = rec.get("text") or ""
            sc = {n: _score(got, refs[n].get(key)) for n in REF_NAMES}
            ratio = (len(got.split()) / ref_len) if ref_len else None
            modern = [sc[n] for n in ("sabates_a", "madueke_b") if sc[n] is not None]
            passed = bool(st.get("passed"))
            if passed:
                k = "PASS"
            elif not st.get("localized"):
                k = "L4-MISS"
            elif ratio is not None and ratio < 0.5:
                k = "L4-SHORT"
            elif ratio is not None and ratio > 1.5:
                k = "L4-LONG"
            elif "¬" in got and (max(modern) if modern else 0) < BAR:
                k = "V3-APPARATUS"
            elif modern and min(modern) >= BAR:
                k = "V6-REF"
            else:
                k = "V5-RECOG"
            klass[k] += 1
            row["witnesses"][s] = {"scores": sc, "passed": passed, "localized": bool(st.get("localized")),
                                   "tokens": len(got.split()), "length_ratio": round(ratio, 3) if ratio else None,
                                   "page": rec.get("page"), "class": k}
        sup = sum(1 for s in wits if row["witnesses"][s]["passed"])
        row["support"] = sup
        verses.append(row)

    # the class the governing gate cannot see: witnesses + modern agree, archaic is the outlier
    ref_outliers = []
    for r in verses:
        mods, arcs = [], []
        for s in wits:
            sc = r["witnesses"][s]["scores"]
            mods += [sc[n] for n in ("sabates_a", "madueke_b") if sc[n] is not None]
            arcs += [sc[n] for n in ("s_dismas",) if sc[n] is not None]
        if mods and arcs and statistics.mean(mods) >= BAR and statistics.mean(arcs) < BAR and r["support"] == 0:
            ref_outliers.append(r["verse"])

    return {"book": book, "chapter": chapter, "references": list(REF_NAMES), "witnesses": wits,
            "bar": BAR, "verses": verses, "classes": dict(klass),
            "archaic_reference_outliers": ref_outliers,
            "support_hist": dict(collections.Counter(r["support"] for r in verses))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="genesis")
    ap.add_argument("--chapter", type=int, default=1)
    a = ap.parse_args(argv)
    r = rescore(a.book, a.chapter)
    (HERE / f"gen-rescore-{a.book}-{a.chapter}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
    tot = sum(r["classes"].values())
    print(f"=== {a.book.upper()} {a.chapter} RESCORED — {len(r['verses'])} verses × {len(r['witnesses'])} witnesses "
          f"= {tot} source-verses, against {len(REF_NAMES)} references ===\n")
    print("cause of failure (first applicable wins):")
    for k in ("PASS", "L4-MISS", "L4-SHORT", "L4-LONG", "V3-APPARATUS", "V6-REF", "V5-RECOG"):
        n = r["classes"].get(k, 0)
        if n:
            print(f"   {k:<14} {n:>4}  ({100*n/tot:>5.1f}%)")
    print(f"\nsupport histogram (witnesses passing per verse): {dict(sorted(r['support_hist'].items()))}")
    print(f"archaic-reference outliers (witnesses+modern agree, archaic dissents): {r['archaic_reference_outliers']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
