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

    ../ocr-venv/bin/python witness/build_fount_record.py                          # report only
    ../ocr-venv/bin/python witness/build_fount_record.py --build                  # scored witness
    ../ocr-venv/bin/python witness/build_fount_record.py --build --witness ALL    # every witness
                                                                                 # ~4.5s per leaf

⚠️ REBUILD IF THE LEAF SET CHANGES, on the same terms as the perception cache. A stale fount record
addressed against a different page is a wrong answer with a confident cause, which is worse than a
missing one -- so `visual_agent` REFUSES to fire the fount cue when the record is absent rather
than falling through silently, and `score_argument_agent.py` proves that negative.

⚠️ NO-ARGUMENT BEHAVIOUR IS NOW THE REPORT, NOT THE BUILD (R16.2), for the reason
`build_reading_record.py` records: the verification standard runs every enrolled command WITHOUT
ITS ARGUMENTS. Bare, this script used to rebuild the scored witness; across four witnesses that is
188 leaves and roughly fourteen minutes of recomputation on every suite run. The scored witness's
record and its filename are UNCHANGED, so R14.10a's result is untouched.

WHY THIS WENT PER-WITNESS (R16.2). `AR` was measured at 4/4 on `OT1-1609-B` and named ZERO times on
the other 188 leaves of the plate book. That looked like a dead class; it is not. `AR` is decided on
the FOUNT, the fount record existed for one witness only, and every other leaf therefore abstained
WITH A STATED CAUSE -- the correct behaviour, misread as a failure. The repair is data, not a rule.
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
import visual_agent as VA                # noqa: E402

WITNESS = "OT1-1609-B"
LEAF_LO, LEAF_HI = 400, 420
RECORD = _HERE / "gold" / f"fount_{WITNESS}_{LEAF_LO}-{LEAF_HI - 1}.json"

MANIFEST = _HERE / "plates" / "manifest.json"


def leaves_for(wid: str) -> list[int]:
    """Which leaves this witness's record must cover.

    ⚠️ THE SCORED WITNESS KEEPS ITS CONTIGUOUS WINDOW, so the file R14.10a was measured against is
    reproduced byte-for-byte by a rebuild. Every other witness takes its leaf set from the PLATE
    MANIFEST, which is not contiguous -- inventing a range for them would build a record addressed
    against pages the book does not contain, and `attach_fount` would then match the wrong leaf.
    """
    if wid == WITNESS:
        return list(range(LEAF_LO, LEAF_HI))
    if not MANIFEST.is_file():
        raise SystemExit(f"🔴 no plate manifest at {MANIFEST} — run plate_book.py --manifest first.")
    rows = json.loads(MANIFEST.read_text())["leaves"]
    return sorted(r["leaf"] for r in rows if r["witness"] == wid)


def record_path(wid: str):
    """One definition of where the record lives -- `visual_agent`'s, not a second copy.

    ⚠️ A BUILDER THAT DECIDES ITS OWN PATH IS A SECOND SOURCE OF TRUTH. If this drifted from the
    reader, the build would report success and the cue would still abstain, which is the exact
    failure shape (working code that no rule reads) this step exists to repair.
    """
    return VA._rec_path("fount", wid)


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


def build_one(wid: str) -> int:
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == wid][0]
    paths = W.leaves(vol, sig)
    want = leaves_for(wid)
    print(f"\n=== {wid}: {len(want)} leaf/leaves ===", flush=True)
    out = []
    for n, i in enumerate(want, 1):
        t0 = time.time()
        rec = leaf_fount(paths[i])
        rec["leaf"] = i
        out.append(rec)
        it = sum(1 for s in rec["segments"]
                 if s["slant"] - (rec["slant_mode"] or 0.0) >= RG.ARGUMENT_SLANT_MIN)
        print(f"  {n}/{len(want)} leaf {i}: {len(rec['segments']):3d} segments, {it:3d} italic, "
              f"page slant mode {rec['slant_mode']}  ({time.time() - t0:.1f}s)", flush=True)
    p = record_path(wid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "witness": wid,
        "_doc": ("PERCEPTION, never a label. Row-SEGMENT deslanting angles in page fractions, plus "
                 "each leaf's roman slant. Built by witness/build_fount_record.py from R2.2d's "
                 "existing instrument (CR.row_slant / CR.region_segments / CR.page_slant_mode). "
                 "Rebuild if the leaf set changes."),
        "slant_min": RG.ARGUMENT_SLANT_MIN,
        "min_components": RG.ARGUMENT_MIN_COMPONENTS,
        "upright_tol": RG.ARGUMENT_UPRIGHT_TOL,
        "leaves": out,
    }, indent=1))
    # ⚠️ A leaf whose roman slant could not be measured is reported HERE, at build time. It will
    # abstain at read time with a cause, and a count of those is the difference between "the record
    # covers this witness" and "the record covers this witness usefully".
    nomode = sum(1 for r in out if r["slant_mode"] is None)
    print(f"  -> {p.relative_to(_HERE.parent)}   ({len(out)} leaves, "
          f"{nomode} with NO roman-slant reference — those abstain)", flush=True)
    return 0


def witnesses_from_argv() -> list[str]:
    if "--witness" not in sys.argv:
        return [WITNESS]
    val = sys.argv[sys.argv.index("--witness") + 1]
    if val.upper() != "ALL":
        return [val]
    if not MANIFEST.is_file():
        raise SystemExit(f"🔴 no plate manifest at {MANIFEST}.")
    rows = json.loads(MANIFEST.read_text())["leaves"]
    return sorted({r["witness"] for r in rows})


def report() -> int:
    wids = witnesses_from_argv() if "--witness" in sys.argv else None
    if wids is None:
        wids = sorted({r["witness"] for r in json.loads(MANIFEST.read_text())["leaves"]}) \
            if MANIFEST.is_file() else [WITNESS]
    print("R14.10a fount record — coverage by witness\n")
    for wid in wids:
        p = record_path(wid)
        if not p.is_file():
            print(f"  🔴 {wid:14s} NOT BUILT — `AR` cannot fire on this witness, and every leaf")
            print(f"     {'':14s} says so rather than falling through. Run with --build.")
            continue
        d = json.loads(p.read_text())
        nomode = sum(1 for r in d["leaves"] if r["slant_mode"] is None)
        segs = sum(len(r["segments"]) for r in d["leaves"])
        print(f"  ✅ {wid:14s} {len(d['leaves']):3d} leaves · {segs:6d} segments · "
              f"{nomode} with no roman-slant reference")
    print("\n(report only — pass --build to write)")
    return 0


def main() -> int:
    if "--build" not in sys.argv:
        return report()
    for wid in witnesses_from_argv():
        build_one(wid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
