"""Gate 0b, stage 1: per-leaf physical inventory of every witness.

Classifies each leaf as TEXT / BLANK / PLATE-or-BINDING / TARGET by ink
coverage and tone, so leaf-count differences between copies can be
accounted for rather than guessed at.  Writes one JSON per witness.
"""
import json, sys, os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witnesses as W

OUT = Path(__file__).resolve().parent.parent / ".scratch" / "inventory"

# Ink-coverage cuts, named because the resolvability check has to compare the
# witness's floor against the cut it is about to apply, not against a constant
# repeated at three call sites.
BLANK_CUT = 0.010     # below this a leaf carries no text
SPARSE_CUT = 0.035    # flyleaf with an inscription, ornament, half-title

def classify(f):
    im = Image.open(f)
    size = im.size
    im.draft("RGB", (160, 220))          # one decode only, reduced resolution
    small = im.convert("RGB").resize((120, 165))
    rgb = np.asarray(small).astype(np.float32)
    a = rgb.mean(2)
    p95 = float(np.percentile(a, 95))
    # ink = pixels well below the page's own paper tone
    ink = float((a < (p95 - 45)).mean())
    dark = float((a < 60).mean())
    mx, mn = rgb.max(2), rgb.min(2)
    sat = float(((mx - mn) / (mx + 1e-6)).mean())
    return dict(size=list(size), ink=round(ink, 4), dark=round(dark, 4),
                sat=round(sat, 3))

def label(rec):
    """Assign kinds using thresholds relative to this witness.

    Absolute saturation cannot separate a marbled endpaper from a warm-toned
    scan: a uniformly sepia rehost saturates as highly as a colour plate.
    What distinguishes a plate is standing out *against its own book*.

    The same argument applies to ink, and applying it to saturation alone was a
    bug.  A contrast-boosted rehost darkens its background everywhere, so its
    ink floor rises with it: the F witnesses bottom out at ink 0.196 against a
    0.010 BLANK cut, which is above the B witnesses' *median* of 0.25.  On such
    a witness BLANK and SPARSE can never fire, and the inventory reported zero
    blanks for all three F volumes -- a number that reads as the finding "the
    rehost stripped its blanks" when it really means "this test cannot run
    here".

    So the floor is checked before it is used.  A witness whose ink
    distribution has no low mode gets BLANK/SPARSE reported as UNRESOLVED
    rather than as zero: an unmeasurable quantity must not be emitted as a
    measurement of zero, which is the shape a silent degradation takes.
    """
    sats = sorted(r["sat"] for r in rec)
    p60 = sats[int(0.60 * len(sats))]
    plate_cut = max(0.20, p60 + 0.10)

    inks = sorted(r["ink"] for r in rec)
    med = inks[len(inks) // 2]
    # Compare the floor to the CUT, not to the median.  The question is not
    # "is this witness's range wide?" but "could a blank leaf be detected by
    # the threshold about to be applied?", and only the second is answerable.
    #
    # A ratio against the median was tried first and split the three F
    # witnesses inconsistently -- OT1 tripped at 0.196/0.350 while NT passed at
    # 0.193/0.409 -- although all three share the same pathology and not one of
    # them has a single leaf below ink 0.06.  The median is a property of the
    # text, so a ratio against it measures contrast, not detectability.
    ink_resolvable = inks[0] < 5 * BLANK_CUT

    for r in rec:
        if r["dark"] > 0.55:                                r["kind"] = "BINDING"
        elif r["sat"] > plate_cut and r["ink"] > 0.10:      r["kind"] = "PLATE"
        elif not ink_resolvable:                            r["kind"] = "TEXT?"
        elif r["ink"] < BLANK_CUT:                          r["kind"] = "BLANK"
        elif r["ink"] < SPARSE_CUT:                         r["kind"] = "SPARSE"
        else:                                               r["kind"] = "TEXT"

    if not ink_resolvable:
        print(f"  !! ink floor {inks[0]:.4f} is {inks[0]/BLANK_CUT:.0f}x the BLANK cut "
              f"({BLANK_CUT}), median {med:.4f} -- BLANK/SPARSE UNRESOLVABLE on this "
              f"witness; leaves marked TEXT?", flush=True)
    return rec

def _one(arg):
    i, f = arg
    r = classify(f); r["i"] = i; r["file"] = f.name
    return r

def run(vol, sig, workers=None):
    fs = W.leaves(vol, sig)
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    with ProcessPoolExecutor(workers) as ex:
        rec = label(list(ex.map(_one, list(enumerate(fs)), chunksize=8)))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{W.wid(vol, sig)}.json"
    out.write_text(json.dumps(dict(witness=W.wid(vol, sig), legacy=W.WITNESSES[(vol,sig)]["legacy"],
                                   n=len(rec), leaves=rec), indent=1))
    from collections import Counter
    c = Counter(r["kind"] for r in rec)
    # Report every kind PRESENT, not a fixed list: a kind missing from the list
    # would drop out of the summary while n stayed right, which is how an
    # unresolved leaf would come to look like an accounted-for one.
    print(f"{W.wid(vol,sig):14s} n={len(rec):5d} " +
          " ".join(f"{k}={c[k]}" for k in sorted(c)), flush=True)
    assert sum(c.values()) == len(rec), "kind counts must account for every leaf"
    return rec

if __name__ == "__main__":
    todo = sys.argv[1:] or [f"{v}:{s}" for (v, s) in W.WITNESSES]
    for t in todo:
        v, s = t.split(":"); run(v, s)
