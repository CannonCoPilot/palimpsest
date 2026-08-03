# -*- coding: utf-8 -*-
"""THE FULL GENESIS 1 MATRIX — every verse x every source x every reference, laid out by SOURCE.

The target (Sir, 2026-07-29): every verse of every source's OCR must match the corresponding verse in EACH of
the four reference witnesses above 0.90, with the best approaching 1.00. That is 31 verses x 4 sources x 4
references = **496 cells**, and the work is now cell by cell. This module is the board it is played on: it
prints one block per source so a source's own failures read together, then the exact list of open cells in
work order, then the residual diff for each so the next fix is chosen from evidence rather than from a hunch.

Read the blocks by SOURCE, not by verse. S6 is the 1635 second edition against three copies of the 1609 first
edition, so its shortfalls are a different kind of thing from S1/S3/S9's — sometimes genuine edition
divergence, which is a collation fact and not an OCR defect.

Usage:  ../ocr-venv/bin/python gen1_matrix.py [--bar 0.90] [--open-only] [--html OUT]
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_pagemodel as PM                    # noqa: E402
import gen1_pagemodel_eval as EV               # noqa: E402
import ref_renumber as RR                      # noqa: E402
import verse_seg as VS                         # noqa: E402
from char_identity import evaluate_locus        # noqa: E402

REFS = EV.REFS
WITS = EV.WITS
SRC_NOTE = {"S1": "1609 1st ed (archive-ot1-1609)", "S3": "1609 1st ed (pdf-S03a)",
            "S9": "1609 1st ed (archive-holiebible-ot1)", "S6": "1635 2nd ed (jp2-S06)"}

# EACH REFERENCE IS SCORED WITH ITS OWN ARM. `char_identity.evaluate_locus` computes two identities from two
# different normalizations: `archaic_id` (via `fold_archaic`, which PRESERVES the archaic orthography) and
# `modern_id` (via `fold_modern`, which folds it away). `s_dismas` and `odr_com` print the readings the DR
# prints, so they are archaic-arm references. `sabates_a` (janvier) and `madueke_b` are MODERN-SPELLING, so
# scoring them on the archaic arm charges a faithful transcription for every `heauen`/`heaven`,
# `likenes`/`likeness`, `kinde`/`kind` — differences of edition, not of recognition. That is the wrong arm for
# them, and it was costing ~0.05 per cell across the board.
ARM = {"s_dismas": "archaic_id", "odr_com": "archaic_id",
       "sabates_a": "modern_id", "madueke_b": "modern_id"}


def r3_store() -> Path:
    """One adoption store per chapter; Genesis 1 keeps its historical filename."""
    return (HERE / ".gen1-r3-adopted.json") if (EV.BOOK, EV.CHAPTER) == ("genesis", 1) \
        else HERE / f".r3-adopted-{EV.BOOK}-{EV.CHAPTER}.json"


def build(use_r3: bool = True) -> dict:
    wb = PM.load(EV.BOOK, EV.CHAPTER)
    lex = EV.book_lexicon()
    refs = {n: RR.load_corrected(n, trim=(EV.BOOK, EV.CHAPTER)) for n in REFS}
    janv = VS.chapter_verses(EV.BOOK, EV.CHAPTER, VS.JANVIER) or {}
    got = {s: EV.witness_spans(od, wb.get(od, {}), lex) for s, od in WITS.items()}
    # RUNG-3 RESCUES ARE OVERLAID AND LABELLED, NEVER BLENDED. `gen1_r3.py` writes only the re-reads that beat
    # the incumbent AND cleared the bar; this shows them as `r3` in the provenance column so the matrix always
    # distinguishes what the page model read from what the vision model re-read. `--no-r3` ablates the overlay.
    store = r3_store()
    r3 = json.loads(store.read_text()) if (use_r3 and store.exists()) else {}
    cells = {}
    for s in WITS:
        for v in sorted(janv):
            sp = got[s].get(v) or {}
            t = sp.get("text", "")
            if f"{s}:{v}" in r3:
                # THE OVERLAY MUST GO THROUGH THE APPARATUS FILTER, NOT JUST THE ADOPTION. `clean_tokens` is
                # "the ONE place that decision is made, so the Rung-3 overlay goes through it too" — but it was
                # applied when the adoption was WRITTEN, and the store is append-only, so every later
                # improvement to the filter stopped at the adopted cells. Genesis 8:14/S1 kept `In ii: the
                # ſecond moneth ... dried. †` and sat at 0.8625 after `ii:` had been recognised as a marginal
                # cross-reference: the fix reached every cell in the book except the ones a model had re-read.
                # Filtering at overlay time makes the store self-correcting — the text is re-cleaned by
                # whatever the filter knows today, and no adoption can carry an apparatus token forward.
                t = " ".join(PM.clean_tokens(r3[f"{s}:{v}"]["text"].split()))
                sp = {**sp, "from": "r3", "text": t}
            sc = {}
            for r in REFS:
                ref = refs[r].get(f"scripture/{EV.BOOK}/{EV.CHAPTER}/{v}")
                sc[r] = round(evaluate_locus(t, ref, ref)[ARM[r]], 3) if (t and ref) else None
            cells[(s, v)] = {"text": t, "score": sc, "from": sp.get("from"), "fit": sp.get("fit")}
    # `janvier` is returned as well as `refs` because it is the SEGMENTATION the whole matrix is cut on (the
    # verse set is `sorted(janv)`), so anything rendering a verse beside its sources needs the text the cut
    # came from. It is not a fifth reference and must never be scored as one.
    return {"cells": cells, "refs": refs, "verses": sorted(janv), "janvier": janv}


def word_diff(got: str, ref: str, limit: int = 12) -> str:
    """The tokens the transcript misses or adds against this reference — the actual residual, not a number."""
    a, b = [PM._bare(t) for t in got.split()], [PM._bare(t) for t in ref.split()]
    a, b = [t for t in a if t], [t for t in b if t]
    miss, extra = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            extra += a[i1:i2]
        if tag in ("replace", "insert"):
            miss += b[j1:j2]
    out = []
    if miss:
        out.append("missing " + " ".join(miss[:limit]) + ("…" if len(miss) > limit else ""))
    if extra:
        out.append("spurious " + " ".join(extra[:limit]) + ("…" if len(extra) > limit else ""))
    return " | ".join(out) or "—"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bar", type=float, default=0.90)
    ap.add_argument("--book", default="genesis")
    ap.add_argument("--chapter", type=int, default=1)
    ap.add_argument("--open-only", action="store_true")
    ap.add_argument("--json", default=str(HERE / "gen1-matrix.json"))
    ap.add_argument("--no-r3", action="store_true", help="ablate the Rung-3 overlay (pure page model)")
    a = ap.parse_args()

    EV.set_locus(a.book, a.chapter)
    M = build(use_r3=not a.no_r3)
    cells, refs, verses = M["cells"], M["refs"], M["verses"]
    hdr = "  v  | " + " ".join(f"{r[:9]:>9}" for r in REFS) + " |  min   from"

    print(f"=== {EV.BOOK.upper()} {EV.CHAPTER} — FULL MATRIX, {len(verses)} verses x {len(WITS)} sources x {len(REFS)} references "
          f"= {len(verses) * len(WITS) * len(REFS)} cells (bar {a.bar}) ===")

    open_cells = []
    for s in WITS:
        print(f"\n{'-' * 78}\n### SOURCE {s} — {SRC_NOTE[s]}\n{hdr}")
        for v in verses:
            c = cells[(s, v)]
            vals = [c["score"][r] for r in REFS]
            lo = min([x for x in vals if x is not None] or [0.0])
            if a.open_only and lo >= a.bar:
                continue
            mark = "" if lo >= a.bar else "   <-- OPEN"
            print(f" {v:>3} | " + " ".join(f"{(x if x is not None else 0):9.3f}" for x in vals)
                  + f" | {lo:5.3f}  {str(c['from'] or '-'):>7}{mark}")
            for r in REFS:
                if (c["score"][r] or 0) < a.bar:
                    open_cells.append({"src": s, "verse": v, "ref": r, "score": c["score"][r],
                                       "diff": word_diff(c["text"], refs[r].get(f"scripture/{EV.BOOK}/{EV.CHAPTER}/{v}") or "")})

    print(f"\n{'=' * 78}\n=== SUMMARY ===")
    print(f"{'':>4}" + "".join(f"{r[:9]:>11}" for r in REFS) + f"{'ALL4':>8}")
    for s in WITS:
        row = []
        for r in REFS:
            n = sum(1 for v in verses if (cells[(s, v)]["score"][r] or 0) >= a.bar)
            row.append(f"{n:>7}/{len(verses)}")
        all4 = sum(1 for v in verses if all((cells[(s, v)]["score"][r] or 0) >= a.bar for r in REFS))
        print(f"{s:>4}" + "".join(f"{x:>11}" for x in row) + f"{all4:>5}/{len(verses)}")
    tot = len(verses) * len(WITS) * len(REFS)
    passing = tot - len(open_cells)
    print(f"\ncells at or above {a.bar}: {passing}/{tot} = {passing / tot:.1%}")
    means = {r: statistics.mean([cells[(s, v)]["score"][r] or 0 for s in WITS for v in verses]) for r in REFS}
    print("means: " + "  ".join(f"{r} {means[r]:.3f}" for r in REFS))

    print(f"\n=== {len(open_cells)} OPEN CELLS — work list ===")
    by_sv = collections.Counter((c["src"], c["verse"]) for c in open_cells)
    for (s, v), n in sorted(by_sv.items(), key=lambda kv: (-kv[1], kv[0])):
        rs = [c for c in open_cells if c["src"] == s and c["verse"] == v]
        print(f"\n  {s} v{v}  ({n}/4 refs open, worst {min(c['score'] or 0 for c in rs):.3f})")
        print(f"     {rs[0]['diff'][:150]}")

    Path(a.json).write_text(json.dumps(
        {"cells": [{"src": s, "verse": v, **{k: val for k, val in c.items() if k != "score"},
                    "score": c["score"]} for (s, v), c in cells.items()],
         "open": open_cells}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
