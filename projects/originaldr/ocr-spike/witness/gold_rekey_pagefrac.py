"""R2.2c -- re-key the head-region gold to a PAGE-ANCHORED address, so it stops naming one band.

⚠️ THIS IS THE THIRD TIME THIS GOLD'S ADDRESS HAS FAILED, AND THE FAILURES RHYME.
  * R2.1i  the address was a TOKEN ORDINAL -- an index into a list the splitter controls, so
           changing the splitter renumbered every key and the score collapsed with no region
           having changed. Re-keyed to band-pixel span.
  * R2.1j  an ENTRY could be COARSER THAN A TOKEN, so `match`'s half-span rule was unsatisfiable
           the moment the splitter got finer than the labeller was. Fixed by binding on INK.
  * R2.2c  the address is band-pixel `(row, l, r)` -- and `row` is AGAIN AN ORDINAL, this time
           into a list the BAND controls. It names a position in the 0..0.35h scorer crop. The
           production reader receives 0.06h..0.30h, in which the running head is not present on
           any of the 20 leaves, so row 0 of the reader's band is a DIFFERENT ROW OF THE PAGE.

Each time the fix has been the same shape: replace an index into something a stage controls with a
measurement of the PAGE, which no stage controls. This module finishes that move. It adds, to every
entry (labelled and ambiguous):

    xlf, xrf   the entry's span, as fractions of PAGE WIDTH
    y0f, y1f   the INK EXTENT OF THAT ENTRY'S OWN GLYPHS, as fractions of PAGE HEIGHT

⚠️ `y0f`/`y1f` are taken over the glyphs INSIDE the entry's x span, NOT over the whole row. A
headline band is not a line (`region_head` R5): leaf 400 row 0 carries `NVMERI` and `Og Alaine.
Bal-` at different heights, and a row-level y would place the running head wherever its loudest
neighbour sits -- re-importing at the y axis exactly the row-is-homogeneous assumption that
`region_head` had to abandon on the x axis.

The band-pixel fields `row`, `l`, `r` are KEPT and unchanged, so every number recorded against this
gold (0.8760 max-overlap, the R2.1j ink figures) stays reproducible and comparable. This adds an
address; it does not retire one. Nothing is relabelled -- `label` and `text` are copied verbatim.

    python witness/gold_rekey_pagefrac.py            # report only, writes nothing
    python witness/gold_rekey_pagefrac.py --write
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W
import collation_read as CR

GOLD = _HERE / "gold/head_regions_OT1-1609-B_400-419.json"
TOP_FRAC = 0.35            # the band the gold was LABELLED in -- score_head_{regions,tokens}.TOP_FRAC
LEAVES = range(400, 420)


def entry_y(rows, e):
    """-> (y0, y1) band px, the ink extent of the glyphs lying inside entry `e`'s span, or None.

    A glyph counts when its CENTRE is inside the span: an entry's edge was drawn by hand against a
    rendered word, so a glyph may poke a pixel or two past it, and an edge-strict test would drop
    the first and last letters of every entry -- shrinking exactly the entries whose extent matters.
    """
    r = rows[e["row"]]
    inside = [g for g in r if e["l"] <= (g[2] + g[3]) / 2.0 <= e["r"]]
    if not inside:
        return None
    return float(min(g[0] for g in inside)), float(max(g[1] for g in inside))


def rekey(write=False) -> int:
    g = json.loads(GOLD.read_text())
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    by_leaf = {}
    unplaced = []
    for i in LEAVES:
        band, frame = CR.band_frame(leaves[i], 0.0, TOP_FRAC)
        p, src = CR.scale(band)
        if p is None:
            print(f"  🔴 leaf {i}: no type scale ({src}) -- entries here CANNOT be re-keyed")
            unplaced.append((i, None, f"no type scale ({src})"))
            continue
        rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
        by_leaf[i] = (frame, rows)

    n = 0
    for group in ("labels", "ambiguous"):
        for e in g[group]:
            i = e["leaf"]
            if i not in by_leaf:
                continue
            frame, rows = by_leaf[i]
            if e["row"] >= len(rows):
                unplaced.append((i, e, f"row {e['row']} beyond the {len(rows)} rows found"))
                continue
            ext = entry_y(rows, e)
            if ext is None:
                unplaced.append((i, e, "no glyph centre lies inside the entry's span"))
                continue
            y0, y1 = ext
            e["xlf"], _ = CR.to_page_frac(frame, x=e["l"])
            e["xrf"], _ = CR.to_page_frac(frame, x=e["r"])
            _, e["y0f"] = CR.to_page_frac(frame, y=y0)
            _, e["y1f"] = CR.to_page_frac(frame, y=y1)
            for k in ("xlf", "xrf", "y0f", "y1f"):
                e[k] = round(e[k], 6)
            n += 1

    # The file must describe its own keys. A gold whose `_doc` explains half its address is how the
    # next reader ends up binding on `row` again without knowing there is a better key in the file.
    g["_doc"]["address"] = (
        "TWO ADDRESSES, both live, and a consumer must choose deliberately. (a) `row`,`l`,`r` are "
        "BAND PIXELS in the 0..0.35h crop at width 1400 -- the address every recorded number "
        "(0.8760 max-overlap, the R2.1j ink figures) was measured against, kept so those stay "
        "reproducible. ⚠️ `row` is an ORDINAL into a list THE BAND CONTROLS, so this address is "
        "only meaningful to a consumer cropping 0..0.35h. (b) `xlf`,`xrf`,`y0f`,`y1f` are "
        "fractions of PAGE width/height -- band-independent, and the address R2.2c added because "
        "the production reader crops 0.06h..0.30h, in which 0 of 20 RunningHead entries and 2 of "
        "19 MarginNote entries lie. Prefer (b) for any question about WHERE ON THE PAGE a label "
        "is; (a) is for reproducing the recorded scores. Written by witness/gold_rekey_pagefrac.py."
    )

    tot = len(g["labels"]) + len(g["ambiguous"])
    print(f"\nR2.2c gold re-key -- page-anchored address for {GOLD.name}")
    print(f"  entries re-keyed       {n} / {tot}")
    print(f"  UNPLACED               {len(unplaced)}   -- ACCOUNTING criterion: must be 0")
    for i, e, why in unplaced:
        what = "whole leaf" if e is None else f"row {e['row']} {e.get('text', e.get('reason'))!r}"
        print(f"    🔴 leaf {i} {what}: {why}")

    # The finding this re-key exists to make statable, printed whether or not it writes.
    lo, hi = CR.HEAD_BAND
    rh = [e for e in g["labels"] if e.get("label") == "RH" and "y0f" in e]
    if rh:
        y0 = min(e["y0f"] for e in rh)
        y1 = max(e["y1f"] for e in rh)
        inside = sum(1 for e in rh if e["y0f"] >= lo and e["y1f"] <= hi)
        print(f"\n  RunningHead entries    {len(rh)}   spanning {y0:.4f}h .. {y1:.4f}h")
        print(f"  reader band            {lo:.4f}h .. {hi:.4f}h  (CR.HEAD_BAND, frozen)")
        print(f"  RH entries inside it   {inside} / {len(rh)}")

    if unplaced:
        print("\n  🔴 NOT WRITTEN -- an unplaced entry means the address is not yet total, and a "
              "partial\n     re-key would leave two addressing schemes live in one file.")
        return 1
    if write:
        GOLD.write_text(json.dumps(g, indent=1, ensure_ascii=False) + "\n")
        print(f"\n  ✅ written: {GOLD}")
    else:
        print("\n  (report only -- pass --write to update the gold)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    raise SystemExit(rekey(ap.parse_args().write))
