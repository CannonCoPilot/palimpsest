#!/usr/bin/env python3
"""R14.10a -- THE FOUNT RECORD: what SETTING each piece of type on the leaf is in.

⚠️ THIS IS PERCEPTION, NOT A LABEL, and the distinction is the one `visual_agent`'s box cache
already turns on. A slant angle is an OBSERVATION of the page -- the same category of thing as a
box -- so caching it is admissible. Caching a DECISION would not be: `leaf_from_cache`'s docstring
records why (a cue change would then be scored against stale calls), and nothing here stores a class.

WHY IT EXISTS. R14.8 measured that the agent has no name for the ARGUMENT -- the multi-line italic
prose summary this edition sets between the chapter head and the first verse -- and R14.10a is the
repair. **The capability to see it has existed since R2.2d and no rule read it**: `region_head`
defines `ARGUMENT = "AR"`, `ARGUMENT_SLANT_MIN` and a per-segment fount test, and `collation_read`
provides `row_slant`, `region_segments` and `page_slant_mode`. That is this project's signature
defect wearing its third hat -- working code that no rule governs -- so R14.10a WIRES THE EXISTING
INSTRUMENT rather than building a second one.

WHAT IS STORED, and at what grain. Per leaf, every ROW SEGMENT that supports a slant estimate:
its page-fraction box, its deslanting angle, and its component count. Plus the leaf's own
`page_slant_mode` -- the ROMAN slant, i.e. the sheet's skew -- because the fount test is an
ABSOLUTE one and a skewed scan shifts every row together.

⚠️ THE SEGMENT, NOT THE ROW, AND THAT WAS MEASURED AND REFUTED ONCE ALREADY (R2.2d). A row-level
slant is an AVERAGE over everything sharing a baseline, and this edition sets its SIDE-NOTES in
italic beside roman scripture -- leaf 405's `† How beautiful are thy tabernacles o Iacob` shares
its line with a note and averages to 8 degrees, firing the rule on a verse. `region_segments` cuts
a row where a gap exceeds the line pitch, which is exactly the grain the fount question needs.

    ../ocr-venv/bin/python witness/build_fount_record.py          # ~4.5s per leaf

⚠️ REBUILD IF THE LEAF SET CHANGES, on the same terms as the perception cache. A stale fount record
addressed against a different page is a wrong answer with a confident cause, which is worse than a
missing one -- so `visual_agent` REFUSES to fire the fount cue when the record is absent rather
than falling through silently, and `score_argument_agent.py` proves that negative.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W                    # noqa: E402
import collation_read as CR              # noqa: E402
import region_head as RG                 # noqa: E402

WITNESS = "OT1-1609-B"
LEAF_LO, LEAF_HI = 400, 420
RECORD = _HERE / "gold" / f"fount_{WITNESS}_{LEAF_LO}-{LEAF_HI - 1}.json"


def leaf_fount(leaf_path) -> dict:
    """-> the fount record for one leaf. Abstains WITH ITS CAUSE, never with a default."""
    mode, why_mode = CR.page_slant_mode(leaf_path)
    rows, frame, p, why = CR.page_type_rows(leaf_path)
    if rows is None or p is None:
        return {"slant_mode": mode, "why": why, "segments": []}
    page, _ = CR.band_frame(leaf_path, 0.0, 1.0)
    ink = CR._ink(page)
    segs = []
    for row in rows:
        for seg in CR.region_segments(row, p):
            # A segment too small to support a slant estimate does not get a fount. It is DROPPED
            # from the record rather than recorded as upright -- absence of evidence must not be
            # storable as evidence of roman.
            if len(seg) < RG.ARGUMENT_MIN_COMPONENTS:
                continue
            s = CR.row_slant(ink, seg)
            if s is None:
                continue
            segs.append({
                "x0": CR.page_x_frac(frame, min(g[2] for g in seg)),
                "x1": CR.page_x_frac(frame, max(g[3] for g in seg)),
                "y0": CR.page_y_frac(frame, min(g[0] for g in seg)),
                "y1": CR.page_y_frac(frame, max(g[1] for g in seg)),
                "slant": s,
                "n": len(seg),
            })
    return {"slant_mode": mode, "why": why_mode, "segments": segs}


def main() -> int:
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == WITNESS][0]
    leaves = W.leaves(vol, sig)
    out = []
    for i in range(LEAF_LO, LEAF_HI):
        t0 = time.time()
        rec = leaf_fount(leaves[i])
        rec["leaf"] = i
        out.append(rec)
        it = sum(1 for s in rec["segments"]
                 if s["slant"] - (rec["slant_mode"] or 0.0) >= RG.ARGUMENT_SLANT_MIN)
        print(f"  leaf {i}: {len(rec['segments']):3d} segments, {it:3d} italic, "
              f"page slant mode {rec['slant_mode']}  ({time.time() - t0:.1f}s)", flush=True)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps({
        "witness": WITNESS,
        "_doc": ("PERCEPTION, never a label. Row-SEGMENT deslanting angles in page fractions, plus "
                 "each leaf's roman slant. Built by witness/build_fount_record.py from R2.2d's "
                 "existing instrument (CR.row_slant / CR.region_segments / CR.page_slant_mode). "
                 "Rebuild if the leaf set changes."),
        "slant_min": RG.ARGUMENT_SLANT_MIN,
        "min_components": RG.ARGUMENT_MIN_COMPONENTS,
        "upright_tol": RG.ARGUMENT_UPRIGHT_TOL,
        "leaves": out,
    }, indent=1))
    print(f"\nfount record -> {RECORD.relative_to(_HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
