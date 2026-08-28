#!/usr/bin/env python3
"""R14.14 -- PERCEPTION: THE LEAF'S OWN BASELINE ANGLE, measured once and recorded.

Sir, 2026-08-27: *"it's not angling properly. It's cutting off parts of text in other boxes."* He is
right, and the state was worse than "wrongly angled" -- **the agent had no angle at all**. Every box
is axis-aligned, the head and foot lines were horizontal and the measure edges vertical, on leaves
that are genuinely tilted.

MEASURED BEFORE ANYTHING WAS BUILT. Fitting a line through the bottom edges of each row's glyph
components, over leaves 400-419: real baseline tilt runs **-2.39° to +2.75°** and varies per leaf
(400 is -0.34°, 409 is +1.64°). At +1.6° the vertical drop across a page width is **about one full
line of type**, which is why one horizontal line severed **41 boxes**.

⚠️ THIS IS NOT `fount_*.json`'s `slant_mode`, AND CONFUSING THEM WOULD BE A DEAD METRIC IMPERSONATING
A MEASUREMENT. That quantity is GLYPH slant -- the lean of the strokes, which is what separates
italic from roman -- it is quantised to whole degrees, and it reads **0.00 on all twenty leaves**.
Read as skew it says every leaf is square. Baseline angle is the rotation of the ROW, a different
thing measured a different way.

⚠️ WHY A RECORD AND NOT A CALL IN `frame()`. `settle()` has no page image, deliberately, so that
`leaf_from_cache` can reproduce the agent's naming from the perception cache alone. Surya's boxes are
AXIS-ALIGNED and therefore carry no angle at all -- the tilt is only visible in glyph geometry, which
needs the image. Same reasoning, and the same shape, as `attach_fount` and `attach_reading`.

    ../ocr-venv/bin/python witness/build_skew_record.py            # report only (default)
    ../ocr-venv/bin/python witness/build_skew_record.py --build    # measure + write

⚠️ NO-ARGUMENT BEHAVIOUR IS THE REPORT, NOT THE BUILD. The verification standard runs every enrolled
command WITHOUT ITS ARGUMENTS; a script whose bare invocation rebuilds a record WILL be rebuilt by
that block at random times. `build_recog_gold.py` records what that cost once.
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import witnesses as W                     # noqa: E402
import collation_read as CR               # noqa: E402
import visual_agent as VA                 # noqa: E402

OUT = VA.SKEW

# A row must carry this many glyph components before its angle is fitted. ⚠️ A short row's fit is
# dominated by one stray component; the estimate is a MEDIAN over rows, so admitting noisy rows
# widens the spread without moving the centre -- but the spread is reported and used, so it matters.
MIN_COMPONENTS = 6
# Rows whose fitted angle lies outside this are discarded as fits to something that is not a line of
# type. ⚠️ A CLAMP, not a decision: the measured population runs -2.39..+2.75, so this excludes only
# shapes far outside anything this book exhibits, and the audit reports how many it excluded.
ANGLE_CLAMP = 8.0


def leaf_angle(path) -> tuple[float | None, dict]:
    """-> (median row angle in degrees, diagnostics). None when the leaf cannot be measured."""
    rows, frame, p, why = CR.page_type_rows(path)
    if rows is None:
        return None, {"why": f"row segmentation abstained — {why}"}
    ang = []
    for r in rows:
        if len(r) < MIN_COMPONENTS:
            continue
        xs = [(g[2] + g[3]) / 2 for g in r]
        ys = [g[1] for g in r]                      # bottom edge — the baseline proxy
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        if den <= 0:
            continue
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
        a = math.degrees(math.atan(slope))
        if abs(a) <= ANGLE_CLAMP:
            ang.append(a)
    if len(ang) < 5:
        return None, {"why": f"only {len(ang)} row(s) admitted a baseline fit — too few to take a "
                             f"median without inventing one"}
    ang.sort()
    return st.median(ang), {
        "n_rows": len(ang),
        "p10": ang[int(0.10 * len(ang))], "p90": ang[int(0.90 * len(ang))],
        "min": ang[0], "max": ang[-1],
        "spread": ang[int(0.90 * len(ang))] - ang[int(0.10 * len(ang))],
    }


def build() -> int:
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == VA.WITNESS][0]
    paths = W.leaves(vol, sig)
    out = []
    for i in range(VA.LEAF_LO, VA.LEAF_HI):
        a, diag = leaf_angle(paths[i])
        out.append({"leaf": i, "angle_deg": a, **diag})
        print(f"  leaf {i}: " + ("ABSTAIN — " + diag["why"] if a is None else
                                 f"{a:+.3f}° over {diag['n_rows']} rows "
                                 f"(p10 {diag['p10']:+.2f} … p90 {diag['p90']:+.2f})"), flush=True)
    OUT.write_text(json.dumps({
        "_doc": ("R14.14's BASELINE ANGLE, per leaf, fitted through the bottom edges of each row's "
                 "glyph components. ⚠️ NOT the fount record's `slant_mode`, which is GLYPH slant and "
                 "reads 0.00 on every leaf here. A leaf that cannot be measured carries angle_deg "
                 "null and a `why`, and the agent falls back to an UNROTATED frame AND SAYS SO — "
                 "never a silent zero, which would be indistinguishable from a square page."),
        "witness": VA.WITNESS, "window": [VA.LEAF_LO, VA.LEAF_HI - 1],
        "min_components": MIN_COMPONENTS, "angle_clamp": ANGLE_CLAMP,
        "pivot": "x = 0.5 of page width; rotated y = y - tan(angle) * (x - 0.5)",
        "leaves": out,
    }, indent=1))
    got = [d for d in out if d["angle_deg"] is not None]
    if got:
        vals = [d["angle_deg"] for d in got]
        print(f"\n{len(got)}/{len(out)} leaf angle(s) -> {OUT.relative_to(SPIKE)}")
        print(f"range {min(vals):+.3f}° … {max(vals):+.3f}°, median {st.median(vals):+.3f}°")
    return 0


def report() -> int:
    if not OUT.is_file():
        print(f"🔴 NOT BUILT — {OUT.relative_to(SPIKE)} is absent.")
        print("   The frame stays UNROTATED and every leaf says so. Run with --build.")
        return 0
    d = json.loads(OUT.read_text())
    got = [x for x in d["leaves"] if x["angle_deg"] is not None]
    vals = [x["angle_deg"] for x in got]
    print(f"R14.14 baseline-angle record — {len(got)}/{len(d['leaves'])} leaves measured, "
          f"{VA.WITNESS} {d['window'][0]}-{d['window'][1]}\n")
    print(f"    range     {min(vals):+.3f}° … {max(vals):+.3f}°")
    print(f"    median    {st.median(vals):+.3f}°")
    print(f"    |angle| > 1.0° on {sum(1 for v in vals if abs(v) > 1.0)} leaf/leaves — at 1.6° the "
          f"drop across a page is about one line of type")
    print(f"\n    ⚠️ This is the ROW's rotation, not the GLYPH's lean. The fount record's "
          f"`slant_mode`\n       reads 0.00 on every leaf here and would report these pages as square.")
    for x in d["leaves"]:
        if x["angle_deg"] is None:
            print(f"    🔴 leaf {x['leaf']} UNMEASURED — {x['why']}")
    return 0


def main() -> int:
    return build() if "--build" in sys.argv else report()


if __name__ == "__main__":
    raise SystemExit(main())
