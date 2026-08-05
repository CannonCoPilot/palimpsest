# -*- coding: utf-8 -*-
"""SCORE THE GENESIS 1 PAGE MODEL — the re-runnable harness the page model did not have.

The per-source page model (`gen1_pagemodel.py`) was measured once, by hand, and the result (25 of 31 verses at
>=3/4 support, up from 14) lived only in a status document. That is not a measurement anyone can defend: the
six remaining verses each need a targeted repair, and a repair that cannot be re-scored is a guess. This module
is the missing arm — it turns the page model's word boxes into `stored_page`-shaped input, runs the SAME
localizer the live pipeline runs, and scores every verse of Genesis 1 against all four references.

WHY THE LINES ARE REBUILT RATHER THAN PASSED THROUGH. `verse_locate.best_spans` reads `page["lines"]` and
rebuilds the body through `verse_geom.build_body_tokmap`, so the page model's contribution has to arrive AS
lines. kraken's own lines are the wrong unit here — it interleaves the annotation column with the body, so a
kraken line can hold words from both columns. The rows this module emits are the page model's own visual rows:
column-filtered first, then regrouped by y, so a row is one printed line of scripture and nothing else.

Usage:  ../ocr-venv/bin/python gen1_pagemodel_eval.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_pagemodel as PM                    # noqa: E402
import qc_audit as QC                          # noqa: E402
import ref_renumber as RR                      # noqa: E402
import verse_locate                            # noqa: E402
import verse_seg as VS                         # noqa: E402
from char_identity import evaluate_locus        # noqa: E402

REFS = ("s_dismas", "odr_com", "sabates_a", "madueke_b")
WITS = {"S1": "archive-ot1-1609", "S3": "pdf-S03a",
        "S9": "archive-holiebible-ot1", "S6": "jp2-S06"}
BAR = 0.90
# The locus under test. Set once by an entry point's --book/--chapter and read by every helper here, by
# gen1_matrix and by gen1_r3, so the three cannot drift onto different chapters mid-run.
BOOK = "genesis"
CHAPTER = 1


def set_locus(book: str, chapter: int) -> None:
    global BOOK, CHAPTER
    BOOK, CHAPTER = book, chapter
    PM.CHAPTER = chapter
# The archaic references. Support is counted on these two because they print the readings the DR prints;
# sabates_a/janvier are modern-spelling and score the same page lower for reasons that are not OCR quality.
ARCHAIC = ("s_dismas", "odr_com")


def book_lexicon(book: str | None = None) -> set[str]:
    """The archaic vocabulary of the whole book, used only to detect a word broken at the measure.

    Built from the two archaic references over EVERY chapter, not the chapter under test, and consumed by a
    rule that can only ever join two fragments that are both already non-words. It carries no information
    about which words belong to which verse, so it cannot flatter a per-verse score the way an answer key
    would."""
    book = book or BOOK
    lex: set[str] = set()
    for r in ARCHAIC:
        for k, txt in RR.load_corrected(r).items():
            if k.startswith(f"scripture/{book}/"):
                lex.update(filter(None, (PM._bare(t) for t in (txt or "").split())))
    return lex


def page_lines(ocr_dir: str, page_index: int, pd: dict, lex: set[str] | None = None) -> list[dict]:
    """The page model's assembled rows as body lines, carrying each row's own pixel extent."""
    return [{"text": " ".join(ts), "conf": 1.0, "role": "body",
             "bbox": (min(w["x0"] for w in r), min(w["y0"] for w in r),
                      max(w["x1"] for w in r), max(w["y1"] for w in r))}
            for ts, r in PM.row_tokens(ocr_dir, page_index, pd, lex)]


def _locate(lines: list[dict], page_px, label: str) -> dict[int, dict]:
    if not lines:
        return {}
    page = {"page_px": tuple(page_px), "lines": lines, "page_index": 0,
            "n_body": len(lines), "n_lines": len(lines),
            "r2_body": " ".join(l["text"] for l in lines)}
    try:
        return verse_locate.best_spans(page, BOOK, CHAPTER) or {}
    except Exception as e:                                      # noqa: BLE001
        print(f"  ! {label}: {type(e).__name__}: {e}", file=sys.stderr)
        return {}


def witness_spans(ocr_dir: str, pages: dict, lex: set[str] | None = None,
                  chapter_stream: bool = True) -> dict[int, dict]:
    """Best-fitting span per verse across this witness's Genesis 1 leaves.

    A VERSE IS NOT BOUNDED BY A LEAF, so the localizer is offered the chapter as one stream as well as leaf by
    leaf, and each verse keeps whichever span fits janvier better. gen 1:12 is the case that forces it: the
    words `And the earth brought forth` are the last line of `archive-ot1-1609` p21 and the rest of the verse
    is the first line of p22, so no per-page call can ever see the whole of it — which is also the structural
    reason the handoff's "all-fail verses are BOUNDARY verses" finding holds (verse-1-of-chapter 4.8x,
    neighbour-on-another-page 2.7x). Running BOTH and selecting on the gold-free janvier fit is the same
    hybrid discipline `best_spans` already uses to choose between its two segmenters."""
    best: dict[int, dict] = {}
    janv = VS.chapter_verses(BOOK, CHAPTER, VS.JANVIER) or {}
    ordered = sorted(pages.items(), key=lambda kv: int(kv[0]))
    cands: list[tuple[str, dict]] = []
    for pi, pd in ordered:
        lines = page_lines(ocr_dir, int(pi), pd, lex)
        if lines:
            cands.append((f"p{pi}", _locate(lines, pd["page_px"], f"{ocr_dir} p{pi}")))
    if chapter_stream and len(cands) > 1:
        flat, px = [], ordered[0][1]["page_px"]
        for pi, pd in ordered:
            flat += page_lines(ocr_dir, int(pi), pd, lex)
        cands.append(("chapter", _locate(flat, px, f"{ocr_dir} chapter")))

    for label, spans in cands:
        for v, sp in spans.items():
            t = (sp or {}).get("text") or ""
            if not t.strip():
                continue
            f = verse_locate.janvier_fit(t, janv.get(v))
            if v not in best or f > best[v]["fit"]:
                best[v] = {"text": t, "fit": f, "from": label}
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="genesis")
    ap.add_argument("--chapter", type=int, default=1)
    ap.add_argument("--json", default=str(HERE / "gen1-pagemodel-eval.json"))
    ap.add_argument("--no-lexicon", action="store_true",
                    help="disable the lexicon-evidenced rejoin of a break whose hyphen the recognizer lost")
    a = ap.parse_args()

    set_locus(a.book, a.chapter)
    wb = PM.load(BOOK, CHAPTER)
    lex = None if a.no_lexicon else book_lexicon()
    refs = {n: RR.load_corrected(n, trim=(BOOK, CHAPTER)) for n in REFS}
    janv = VS.chapter_verses(BOOK, CHAPTER, VS.JANVIER) or {}
    got = {s: witness_spans(od, wb.get(od, {}), lex) for s, od in WITS.items()}

    rows = []
    for v in sorted(janv):
        for s in WITS:
            t = (got[s].get(v) or {}).get("text", "")
            sc = {}
            for r in REFS:
                ref = refs[r].get(f"scripture/{BOOK}/{CHAPTER}/{v}")
                sc[r] = round(evaluate_locus(t, ref, ref)["archaic_id"], 3) if (t and ref) else None
            rows.append({"verse": v, "wit": s, "score": sc, "n_tok": len(t.split()),
                         "fit": (got[s].get(v) or {}).get("fit"), "text": t})
    Path(a.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1))

    print(f"=== GENESIS 1 — PER-SOURCE PAGE MODEL, all four references (bar {BAR}) ===\n")
    for r in REFS:
        xs = [x["score"][r] for x in rows if x["score"][r] is not None]
        print(f"{r:>10}  mean {statistics.mean(xs):.3f}   pass {sum(1 for x in xs if x >= BAR):3d}/{len(xs):3d}")

    print(f"\n{'v':>3} {'sup':>4}  {'S1':>5} {'S3':>5} {'S9':>5} {'S6':>5}   (best archaic score per witness)")
    sup = {}
    for v in sorted(janv):
        k = {x["wit"]: x for x in rows if x["verse"] == v}
        sup[v] = sum(1 for s in WITS if max((k[s]["score"][r] or 0) for r in ARCHAIC) >= BAR)
        cells = " ".join(f"{max((k[s]['score'][r] or 0) for r in ARCHAIC):5.3f}" for s in WITS)
        print(f"{v:>3} {sup[v]:>4}  {cells}{'   <-- BELOW 3/4' if sup[v] < 3 else ''}")
    print(f"\nverses at >=3/4 support: {sum(1 for v in sup if sup[v] >= 3)}/{len(sup)}"
          f"   at 4/4: {sum(1 for v in sup if sup[v] == 4)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
