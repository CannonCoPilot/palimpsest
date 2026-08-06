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
    """
    sats = sorted(r["sat"] for r in rec)
    p60 = sats[int(0.60 * len(sats))]
    plate_cut = max(0.20, p60 + 0.10)
    for r in rec:
        if r["dark"] > 0.55:                                r["kind"] = "BINDING"
        elif r["sat"] > plate_cut and r["ink"] > 0.10:      r["kind"] = "PLATE"
        elif r["ink"] < 0.010:                              r["kind"] = "BLANK"
        elif r["ink"] < 0.035:                              r["kind"] = "SPARSE"
        else:                                               r["kind"] = "TEXT"
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
    print(f"{W.wid(vol,sig):14s} n={len(rec):5d} " +
          " ".join(f"{k}={c[k]}" for k in ("TEXT","BLANK","SPARSE","PLATE","BINDING")), flush=True)
    return rec

if __name__ == "__main__":
    todo = sys.argv[1:] or [f"{v}:{s}" for (v, s) in W.WITNESSES]
    for t in todo:
        v, s = t.split(":"); run(v, s)
