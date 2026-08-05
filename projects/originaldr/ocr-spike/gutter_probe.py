#!/usr/bin/env python
"""gutter_probe.py — does THIS leaf have a separable right-hand annotation column, and where is it? (2026-07-31)

WHY THIS EXISTS, AND WHY IT IS NOT A NINTH APPARATUS SPLIT. Four geometric apparatus separations are pinned
dead (§13 Q50): the word-x threshold, intra-line gap ratios, the widest-gap right edge, and the per-leaf median
left edge. Every one of them failed the same way — it sought ONE rule that would decide, on every leaf, which
words are apparatus. That question has no geometric answer, because on most leaves the columns genuinely
overlap: chapter 5's S9 x-histogram is FLAT from x100 to x1900.

This tool asks a strictly smaller question, and REFUSES to answer when the answer would be a guess:

    on this ONE leaf, is there an x at which NO body row is truncated and NO margin word survives?

It is a detector, not a separator. It reports SEPARABLE only when the two populations are actually disjoint,
and OVERLAP (with the offending rows) otherwise. On an OVERLAP leaf the correct action is to do nothing
geometric — that leaf's failures belong to R2/R3, which is where Q50 says S6's excess actually lives.

HOW THE TWO POPULATIONS ARE IDENTIFIED WITHOUT ASSUMING THE ANSWER. A margin column is not "words that are far
right"; it is a run of SHORT ROWS whose left edges AGREE down the page. So:

  * a MARGIN ROW is a row lying wholly right of `--probe` (default: the witness band's midpoint), and
  * the column's left edge is the minimum x0 over those rows,
  * the BODY is every other row, and its right edge is the maximum x1 over them.

If body_max_x1 < margin_min_x0 the leaf is SEPARABLE and the gutter is that interval; the recommended bound is
its MIDPOINT, expressed as a fraction of page width — chosen so the bound is right for the reason it is right
rather than by tying on a scoreboard. A sweep must still confirm it (CHAPTER-WORKFLOW Phase 3, "sweep, don't
guess"), and the token diff must still be read before adoption (§13 Q47).

Rows ABOVE the chapter's `chapter_open_y` are excluded, because that matter is not scripture and its geometry
should not vote on the body's bound.

    ../ocr-venv/bin/python gutter_probe.py --chapter 15 --source S6
    ../ocr-venv/bin/python gutter_probe.py --chapter 3 --source S6 --examples 4
"""
from __future__ import annotations

import argparse
import json
import pathlib

import gen1_pagemodel as PM

HERE = pathlib.Path(__file__).resolve().parent

# A margin column must have at least this many rows whose left edges agree within COL_TOL px. Below that it
# is not a column, it is a coincidence — see the `17.Ther-` note in probe_leaf.
MIN_COL_ROWS = 4
COL_TOL = 60

SOURCES = {
    "S1": "archive-ot1-1609",
    "S3": "pdf-S03a",
    "S6": "jp2-S06",
    "S9": "archive-holiebible-ot1",
}


def probe_leaf(od: str, page: str, pg: dict, cut_frac: float, probe_frac: float):
    """Return a verdict dict for one leaf. Pure geometry — reads no reference and no score."""
    W, H = pg["page_px"]
    cut = cut_frac * H
    probe_x = probe_frac * W

    rows = []
    for ln in pg["lines"]:
        ws = [w for w in ln["words"] if w["y0"] >= cut]
        if ws:
            rows.append(ws)
    if not rows:
        return {"page": page, "verdict": "EMPTY", "n_rows": 0}

    # A MARGIN ROW IS NOT MERELY A ROW THAT SITS FAR RIGHT — it must belong to a COLUMN, i.e. its left edge
    # must AGREE with other such rows down the page. Without this the probe misfires on a short body line near
    # the page foot: `jp2-S06` p74's last row is `17.Ther-` at x1490-1653, the hyphenated opening of verse 17,
    # which lies wholly right of any sane probe and is scripture. Counting it as margin reported the leaf
    # OVERLAP and would have suppressed a bound that is in fact correct. Require a cluster of `min_rows`.
    # The membership test is deliberately ONE-SIDED. A narrow column indents freely — `.and odde` opens at
    # x1746 where the column's own left edge is x1673 — so an upper bound on the left edge wrongly ejects real
    # margin rows and reports the leaf OVERLAP. What a column will NOT do is start well LEFT of its own edge.
    # So: reject candidates left of (median - COL_TOL), keep everything at or right of it.
    cand = [ws for ws in rows if min(w["x0"] for w in ws) >= probe_x]
    col: list = []
    if len(cand) >= MIN_COL_ROWS:
        lefts = sorted(min(w["x0"] for w in ws) for ws in cand)
        med = lefts[len(lefts) // 2]
        keep = [ws for ws in cand if min(w["x0"] for w in ws) >= med - COL_TOL]
        if len(keep) >= MIN_COL_ROWS:
            col = keep
    colids = {id(ws) for ws in col}
    body = [ws for ws in rows if id(ws) not in colids]

    out = {"page": page, "n_rows": len(rows), "n_margin": len(col), "n_body": len(body),
           "W": W, "H": H}
    if not col:
        out["verdict"] = "NO-COLUMN"
        return out
    if not body:
        out["verdict"] = "ALL-MARGIN"
        return out

    # COMPARE ON CENTRES, because that is what the bound itself tests. The asymmetric band edges are a settled
    # finding (CHAPTER-WORKFLOW, "what generalizes"): left = gutter, test the word's START; right = measure,
    # test its CENTRE. Probing on x1 while the model bounds on the centre would reject bounds that work.
    ctr = lambda w: (w["x0"] + w["x1"]) / 2.0
    m_lo = min(ctr(w) for ws in col for w in ws)
    b_hi = max(ctr(w) for ws in body for w in ws)
    out["margin_min_ctr"] = m_lo
    out["body_max_ctr"] = b_hi
    out["col_left"] = min(min(w["x0"] for w in ws) for ws in col)

    if b_hi < m_lo:
        mid = (b_hi + m_lo) / 2.0
        out["verdict"] = "SEPARABLE"
        out["gutter"] = (b_hi, m_lo)
        out["bound_px"] = mid
        out["bound_frac"] = round(mid / W, 4)
    else:
        out["verdict"] = "OVERLAP"
        # The rows that make it inseparable, worst first — these are what a bound would damage.
        bad = sorted(
            ({"text": " ".join(w["t"] for w in ws), "ctr": max(ctr(w) for w in ws),
              "y0": min(w["y0"] for w in ws)}
             for ws in body if max(ctr(w) for w in ws) >= m_lo),
            key=lambda r: -r["ctr"])
        out["offenders"] = bad
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--source", default="S6")
    ap.add_argument("--probe", type=float, default=None,
                    help="fraction of page width right of which a whole row counts as margin "
                         "(default: midpoint of the witness band)")
    ap.add_argument("--examples", type=int, default=3,
                    help="offending body rows to print on an OVERLAP leaf")
    a = ap.parse_args()

    od = SOURCES.get(a.source, a.source)
    PM.CHAPTER = a.chapter
    wbf = HERE / f".wordboxes-genesis-{a.chapter}.json"
    if not wbf.exists():
        raise SystemExit(f"no word boxes: {wbf.name} — run gen1_wordboxes.py --chapter {a.chapter}")
    wb = json.loads(wbf.read_text())
    if od not in wb:
        raise SystemExit(f"{od} not in the word-box set for chapter {a.chapter}")

    band = PM.SOURCE_MODEL[od]["body"]
    probe = a.probe if a.probe is not None else (band[0] + band[1]) / 2.0
    cm = PM.chapter_model(od, a.chapter)

    print(f"=== genesis {a.chapter} · {a.source} ({od})")
    print(f"    witness band {band}   probe x>={probe:.3f}   chapter_model={cm or '(none)'}")
    print(f"    a whole row right of the probe is a MARGIN row; the rest is BODY.\n")

    for page in sorted(wb[od], key=lambda p: int(p)):
        open_page = cm.get("open_page")
        cut = cm.get("chapter_open_y", 0.0) if str(open_page) == str(page) else 0.0
        r = probe_leaf(od, page, wb[od][page], cut, probe)
        ov = PM.PAGE_OVERRIDE.get((od, int(page)))
        tag = f"  [PAGE_OVERRIDE {ov['body']}]" if ov else ""
        head = (f"  -- p{page}  rows {r.get('n_rows',0)} "
                f"(body {r.get('n_body',0)} / margin {r.get('n_margin',0)})  cut={cut}{tag}")
        print(head)
        v = r["verdict"]
        if v == "SEPARABLE":
            lo, hi = r["gutter"]
            print(f"     SEPARABLE — {r['n_margin']} margin rows, column left edge x{r['col_left']:.0f}; "
                  f"body centres end {lo:.0f}, margin centres start {hi:.0f}; gutter {hi-lo:.0f}px")
            print(f"     -> bound {r['bound_frac']} (x{r['bound_px']:.0f} of {r['W']})  SWEEP IT, then read the token diff")
        elif v == "OVERLAP":
            print(f"     OVERLAP — margin column (left x{r['col_left']:.0f}) has min centre "
                  f"{r['margin_min_ctr']:.0f}, but a body row reaches centre {r['body_max_ctr']:.0f}. "
                  f"NO bound is safe on this leaf.")
            for o in r["offenders"][:a.examples]:
                print(f"        y{o['y0']:5.0f} ctr={o['ctr']:5.0f}  {o['text'][:92]}")
        elif v == "NO-COLUMN":
            print("     NO-COLUMN — no row lies wholly right of the probe; nothing to separate.")
        elif v == "ALL-MARGIN":
            print("     ALL-MARGIN — every row is right of the probe (annotations-only leaf?).")
        else:
            print("     EMPTY — no rows below the chapter cut.")
        print()


if __name__ == "__main__":
    main()
