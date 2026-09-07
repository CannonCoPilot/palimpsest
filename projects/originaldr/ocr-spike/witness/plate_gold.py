#!/usr/bin/env python3
"""plate_gold.py — the READER for the Plate Tool's record (SIR-REVIEW-2026-09-01 Finding 5, T0).

The record is `plates/gold-layout.json`, written by `plate_tool.py` on every change. This module is
the only sanctioned way to consume it. It refuses a record whose source read has changed underneath
it, refuses accepted leaves that still carry `??`, and refuses classes outside the register.

    from plate_gold import load, is_gold, accepted
    g = load()                      # raises GoldError on any violation
    is_gold("OT1-1609-B", 412)      # True only for a leaf Sir ACCEPTED
    accepted()                      # {id: review} for every accepted leaf

CLI:  python3 plate_gold.py [--record plates/gold-layout.json] [--quiet]
"""
import argparse, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).parent
RECORD = HERE / "plates" / "gold-layout.json"

# The class register (cold-read rounds 1-3 + the B rebuild, 2026-09-05). Codes only; the meanings are
# in witness/cold-read/register-build/build_register_B.py and the live Class Register artifact.
TEXT = ["MT","MN","RH","PN","VN","CH","AR","DC","SG","CW",
        "AN","LM","IG","GK","BT","HD","CR","IX","TB","FN","AT","LR"]
NONTEXT = ["OR","RL","MS","XP","AP","ST","CT"]
STATES = ["BL","BP","EC"]          # blank leaf · blank lower page · empty table cell
ABSTAIN = "??"
CLASSES = TEXT + NONTEXT + STATES
VERDICTS = ("accept", "corrected", "defect")
SKEW_MAX = 6.0          # degrees; a leaf needing more than this is a capture defect, not a skew
CODE_RE = r"^[A-Z][A-Z0-9]{1,2}$"


# ---------------------------------------------------------------- geometry (the ONE implementation)
# `skew_deg` is the rotation applied to the raster, COUNTER-CLOCKWISE positive as PIL's Image.rotate,
# about the image centre, canvas size unchanged. Boxes in `review.regions` are fractions of THAT
# levelled canvas. `agent` boxes stay in the unrotated frame (skew 0), verbatim.
import math

def deskew(im, skew_deg):
    """Return the levelled raster a consumer must score against. Identity at 0."""
    if not skew_deg: return im
    return im.rotate(skew_deg, resample=3, expand=False, fillcolor=(255, 255, 255) if im.mode == "RGB" else 255)

def transform_box(box, w, h, d_deg):
    """Carry an axis-aligned box (fractions of a w×h canvas) across a rotation of the canvas by
    d_deg (CCW, about the centre). The centre is rotated exactly; the size is kept, which is the
    right first approximation for the small angles a bound book shows. Clamped to the canvas."""
    if not d_deg: return list(box)
    t = math.radians(d_deg); c, s = math.cos(t), math.sin(t)
    cx, cy = (box[0]+box[2])/2*w - w/2, (box[1]+box[3])/2*h - h/2
    # y is down: a visual CCW turn by t maps (x,y) -> (x cos t + y sin t, -x sin t + y cos t)
    nx, ny = cx*c + cy*s + w/2, -cx*s + cy*c + h/2
    bw, bh = (box[2]-box[0])*w, (box[3]-box[1])*h
    x0, y0, x1, y1 = nx-bw/2, ny-bh/2, nx+bw/2, ny+bh/2
    cl = lambda v, m: max(0.0, min(1.0, v/m))
    return [round(cl(x0, w), 4), round(cl(y0, h), 4), round(cl(x1, w), 4), round(cl(y1, h), 4)]

def _profile_var(g, a):
    r = g.rotate(a, resample=2, expand=False, fillcolor=0)
    prof = r.resize((1, r.height), resample=3).tobytes()      # row means by box filter (mode L)
    m = sum(prof)/len(prof)
    return sum((p-m)**2 for p in prof)/len(prof)

def estimate_skew(im, lo=-3.0, hi=3.0, step=0.1, margin=0.06, detail=False):
    """Projection-profile skew: the angle at which row-ink variance peaks, i.e. the text lines are
    level. The outer `margin` is trimmed first — the scan border is a straight edge on the image
    axes and would otherwise pin the answer to 0. Ink is measured relative to the paper (median),
    so the fill outside the rotated canvas is paper, not a second edge. Coarse sweep, fine sweep at
    0.02°. `confidence` = peak variance over the sweep median; below ~1.5 there are no lines to
    level (blank quarter, ornament) and the angle is not to be trusted."""
    g = im.convert("L")
    w, h = g.size; g = g.crop((int(w*margin), int(h*margin), int(w*(1-margin)), int(h*(1-margin))))
    if g.width > 900: g = g.resize((900, round(g.height*900/g.width)))
    hist = g.histogram(); paper = max(range(256), key=lambda v: hist[v])
    g = g.point(lambda v: max(0, paper - v))          # ink = darkness below paper; paper -> 0
    angles = [lo + i*step for i in range(int(round((hi-lo)/step))+1)]
    sc = [(_profile_var(g, a), a) for a in angles]
    best = max(sc)[1]
    fine = [(_profile_var(g, a), a) for a in [best - 0.3 + i*0.02 for i in range(31)]]
    peak, best = max(fine)
    lo_v = min(v for v, _ in sc) or 1e-9
    ink = sum(g.resize((1, g.height), resample=3).tobytes()) / g.height
    conf = round(peak/lo_v, 2) if ink >= INK_MIN else 0.0     # peak over the sweep's floor; blank -> 0
    if detail: return {"skew_deg": round(best, 2), "confidence": conf}
    return round(best, 2) if conf >= CONF_MIN else 0.0

CONF_MIN = 2.0   # peak/min of the sweep: blank ~1.2, ornament ~1.8, lines of text >= 2.3
INK_MIN = 8.0    # mean ink below paper; a blank quarter is ~3-4

def warp_profile(im, margin=0.06):
    """Is one angle enough? Estimate the skew in the four quarters of the leaf (inner area, margin
    trimmed). A rigid tilt gives four near-equal angles; gutter curl or cockling makes them disagree.
    Returns {"quarters": {tl,tr,bl,br}, "spread": max-min, "lr": |left-right| mean diff, "tb": |top-bottom|}."""
    w, h = im.size; x0, y0, x1, y1 = int(w*margin), int(h*margin), int(w*(1-margin)), int(h*(1-margin))
    xm, ym = (x0+x1)//2, (y0+y1)//2
    q = {"tl": (x0, y0, xm, ym), "tr": (xm, y0, x1, ym), "bl": (x0, ym, xm, y1), "br": (xm, ym, x1, y1)}
    d = {k: estimate_skew(im.crop(b), margin=0.0, detail=True) for k, b in q.items()}
    a = {k: v["skew_deg"] for k, v in d.items() if v["confidence"] >= CONF_MIN}
    v = list(a.values())
    mean = lambda ks: sum(a[k] for k in ks if k in a)/max(1, sum(1 for k in ks if k in a))
    return {"quarters": {k: (a[k] if k in a else None) for k in d}, "confidence": {k: v["confidence"] for k, v in d.items()},
            "spread": round(max(v)-min(v), 2) if len(v) >= 2 else 0.0,
            "lr": round(abs(mean(("tl","bl")) - mean(("tr","br"))), 2), "tb": round(abs(mean(("tl","tr")) - mean(("bl","br"))), 2)}

WARP_SPREAD = 0.5      # degrees between quarters beyond which one angle cannot level the leaf


# ---------------------------------------------------------------- dewarp (column shear, "colshear-v1")
# Gutter curl is a bend: the local line angle a(x) varies smoothly with distance from the spine and
# may differ between the top and bottom of the leaf. Integrating tan(a) along x gives the vertical
# displacement d(x) of a line relative to the centre column; shifting every column by -d straightens
# the lines and keeps boxes axis-aligned. The model is resolution-free: a(x) is a quadratic in x as a
# FRACTION of width, in degrees, for the top half (centre y=0.25) and bottom half (y=0.75), linearly
# interpolated in y. Fit on the LEVELLED raster; applied after deskew, before boxes are read.
import numpy as np

def warp_cells(im, nx=6, margin=0.06):
    """Local line angle in an nx×2 grid of overlapping windows (each a third of the width, so it is
    angle-sensitive), top and bottom halves. Returns cells {"top": [(x, angle, conf)], "bot": [...]}
    and the confidence-weighted RMS of the angles — the warp score. A rigid, levelled leaf scores ~0."""
    w, h = im.size; x0, x1 = w*margin, w*(1-margin); y0, y1 = h*margin, h*(1-margin); ym = (y0+y1)/2
    cells = {"top": [], "bot": []}
    win = (x1-x0)/3
    for i in range(nx):
        xc_px = x0 + (x1-x0)*(i+0.5)/nx; xc = xc_px/w
        cx0, cx1 = max(x0, xc_px-win/2), min(x1, xc_px+win/2)
        if cx1-cx0 < win: cx0, cx1 = (x0, x0+win) if cx0 <= x0 else (x1-win, x1)
        for half, (a0, a1) in (("top", (y0, ym)), ("bot", (ym, y1))):
            d = estimate_skew(im.crop((int(cx0), int(a0), int(cx1), int(a1))), margin=0.0, detail=True)
            if d["confidence"] >= CONF_MIN: cells[half].append((round(xc, 3), d["skew_deg"], d["confidence"]))
    allc = cells["top"] + cells["bot"]
    rms = round(float(np.sqrt(sum(c[2]*c[1]**2 for c in allc)/sum(c[2] for c in allc))), 2) if allc else 0.0
    return cells, rms

WARP_RMS = 0.35        # degrees RMS of cell angles beyond which one angle has not levelled the leaf

def fit_dewarp(im, cells=None):
    """Fit colshear-v1 to a levelled raster. Linear in x by default; quadratic only when it cuts the
    weighted residual by more than 40 % with 5+ cells. Returns None when fewer than 3 cells carry
    lines in both halves, or when the fitted angles are all within ±0.2° (nothing to correct)."""
    if cells is None: cells, _ = warp_cells(im)
    model = {"model": "colshear-v1", "y_top": 0.25, "y_bot": 0.75}
    for half in ("top", "bot"):
        c = cells[half]
        if len(c) < 3: model[half] = None; continue
        xs, ys, ws = (np.array([v[k] for v in c], dtype=float) for k in range(3)); sw = np.sqrt(ws)
        lin = np.polyfit(xs, ys, 1, w=sw); sse1 = float(np.sum(ws*(np.polyval(lin, xs)-ys)**2))
        coefs = lin
        if len(c) >= 5:
            quad = np.polyfit(xs, ys, 2, w=sw); sse2 = float(np.sum(ws*(np.polyval(quad, xs)-ys)**2))
            if sse2 < 0.6*sse1: coefs = quad
        model[half] = [round(float(v), 4) for v in coefs[::-1]]
    if model["top"] is None and model["bot"] is None: return None
    if model["top"] is None: model["top"] = model["bot"]
    if model["bot"] is None: model["bot"] = model["top"]
    xs = np.linspace(0.06, 0.94, 25)
    if max(abs(_angle(model["top"], xs)).max(), abs(_angle(model["bot"], xs)).max()) < 0.2: return None
    return model

def level_angle(im):
    """The page angle with the fallback the survey demanded: the whole-page estimate when its gate
    passes; otherwise the confidence-weighted mean of the cell angles (a sparse italic prelim has
    lines, just not enough ink for the page gate). Returns (deg, source) with source page|cells|none."""
    d = estimate_skew(im, detail=True)
    if d["confidence"] >= CONF_MIN: return d["skew_deg"], "page"
    cells, _ = warp_cells(im); allc = cells["top"] + cells["bot"]
    if len(allc) >= 2:
        return round(float(sum(c[2]*c[1] for c in allc)/sum(c[2] for c in allc)), 2), "cells"
    return 0.0, "none"

def dewarp_leaf(lev):
    """The whole decision for one levelled raster: measure, fit, apply, RE-MEASURE, keep the model only
    if it lowered the warp score. Returns (model_or_None, report). The report always carries the
    before/after scores and a status: rigid · dewarped · no-gain · no-fit."""
    cells, before = warp_cells(lev)
    rep = {"rms_before": before, "rms_after": None, "status": "rigid", "cells": cells}
    if before <= WARP_RMS: return None, rep
    m = fit_dewarp(lev, cells)
    if m is None: rep["status"] = "no-fit"; return None, rep
    _, after = warp_cells(apply_dewarp(lev, m)); rep["rms_after"] = after
    if after < before - 0.05 and after < before*0.8: rep["status"] = "dewarped"; return m, rep
    rep["status"] = "no-gain"; return None, rep

def _angle(coefs, x):
    return sum(c * x**k for k, c in enumerate(coefs))

def dewarp_shift(model, x, y, w, h):
    """Vertical shift (fraction of height) to apply at (x, y) fractions: d(x,y) = ∫₀.₅ˣ tan(a) dx·w/h,
    interpolated between the top and bottom halves. The centre column is the fixed reference."""
    def integ(coefs):
        n = 40; xs = np.linspace(0.5, x, n+1); a = np.radians(_angle(coefs, xs))
        return float(np.trapezoid(np.tan(a), xs)) if hasattr(np, "trapezoid") else float(np.trapz(np.tan(a), xs))
    dt, db = integ(model["top"]) * w / h, integ(model["bot"]) * w / h
    t = (y - model["y_top"]) / (model["y_bot"] - model["y_top"])
    return dt + (db - dt) * t

def apply_dewarp(im, model):
    """Resample: out(x, y) = in(x, y + d(x, y)). Per column, y + d is affine in y, so np.interp does it."""
    if not model: return im
    arr = np.asarray(im.convert("RGB")); h, w = arr.shape[:2]
    out = np.empty_like(arr); ys = np.arange(h); yf = ys / h
    for xi in range(w):
        xf = (xi + 0.5) / w
        d = dewarp_shift(model, xf, 0.0, w, h), dewarp_shift(model, xf, 1.0, w, h)
        src = (yf + d[0] + (d[1]-d[0]) * yf) * h
        for c in range(3):
            out[:, xi, c] = np.interp(src, ys, arr[:, xi, c], left=255, right=255)
    from PIL import Image
    return Image.fromarray(out)

def transform_box_dewarp(box, model, w, h, inverse=False):
    """Carry a box across the dewarp (levelled frame -> dewarped frame), or back with inverse=True.
    The shift at the box centre is applied to both y edges; x is untouched by a column shear."""
    if not model: return list(box)
    cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
    d = dewarp_shift(model, cx, cy, w, h) * (1 if inverse else -1)
    cl = lambda v: max(0.0, min(1.0, v))
    return [box[0], round(cl(box[1]+d), 4), box[2], round(cl(box[3]+d), 4)]


class GoldError(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _box_ok(b):
    return (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)
            and 0 <= b[0] < b[2] <= 1 and 0 <= b[1] < b[3] <= 1)


def all_classes(rec):
    """Register classes plus the record's own provisional additions (Sir's authority)."""
    return CLASSES + [c["code"] for c in rec.get("classes_added", [])]


def validate(rec, check_source=True):
    """Raise GoldError on the first violation. Returns the record unchanged."""
    import re
    if rec.get("format") != "plate-gold/1":
        raise GoldError(f"unknown record format {rec.get('format')!r}")
    seen = set(CLASSES)
    for c in rec.get("classes_added", []):
        if not re.match(CODE_RE, c.get("code", "")) or not c.get("meaning", "").strip():
            raise GoldError(f"classes_added: bad entry {c!r} (code 2-3 caps, meaning required)")
        if c["code"] in seen or c["code"] == ABSTAIN:
            raise GoldError(f"classes_added: {c['code']} already exists")
        seen.add(c["code"])
    classes = all_classes(rec)
    src = rec.get("source", {})
    if check_source:
        p = Path(src.get("path", ""))
        if not p.is_absolute(): p = HERE / p
        if not p.exists():
            raise GoldError(f"source read missing: {p}")
        if sha256(p) != src.get("sha256"):
            raise GoldError(f"source read has CHANGED since the record was written: {p}. "
                            "Corrections were made against a different claim; re-open in plate_tool.")
    for lid, L in rec.get("leaves", {}).items():
        rv = L.get("review") or {}
        v = rv.get("verdict")
        if v is not None and v not in VERDICTS:
            raise GoldError(f"{lid}: verdict {v!r} not in {VERDICTS}")
        sk = rv.get("skew_deg", 0) or 0
        if not isinstance(sk, (int, float)) or abs(sk) > SKEW_MAX:
            raise GoldError(f"{lid}: skew_deg {sk!r} outside ±{SKEW_MAX}° — a capture defect, flag it, do not level it")
        dw = rv.get("dewarp")
        if dw is not None and (dw.get("model") != "colshear-v1" or not dw.get("top") or not dw.get("bot")):
            raise GoldError(f"{lid}: dewarp model not understood: {dw!r}")
        for i, r in enumerate(rv.get("regions", [])):
            c = r.get("class")
            if c != ABSTAIN and c not in classes:
                raise GoldError(f"{lid} region {i}: class {c!r} not in the register or the record's additions")
            if not _box_ok(r.get("box")):
                raise GoldError(f"{lid} region {i}: bad box {r.get('box')!r}")
            if r.get("origin") not in ("agent", "human"):
                raise GoldError(f"{lid} region {i}: origin must be agent|human")
        if v == "accept":
            bad = [i for i, r in enumerate(rv.get("regions", [])) if r.get("class") == ABSTAIN]
            if bad:
                raise GoldError(f"{lid}: ACCEPTED but regions {bad} are still '??' — "
                                "an accepted leaf has no open abstentions")
            if not rv.get("regions"):
                raise GoldError(f"{lid}: ACCEPTED with zero regions — a blank leaf is BL, not empty")
    return rec


_cache = {}
def load(record=RECORD, check_source=True):
    record = Path(record)
    key = (str(record), record.stat().st_mtime if record.exists() else None)
    if key in _cache: return _cache[key]
    if not record.exists():
        raise GoldError(f"no record at {record}; nothing has been reviewed")
    rec = validate(json.load(open(record)), check_source)
    _cache.clear(); _cache[key] = rec
    return rec


def accepted(record=RECORD):
    return {lid: L["review"] for lid, L in load(record)["leaves"].items()
            if (L.get("review") or {}).get("verdict") == "accept"}


def is_gold(witness, leaf, record=RECORD):
    lid = f"{witness}_{int(leaf):04d}"
    return lid in accepted(record)


# ---------------------------------------------------------------- rows (line grain)
def ink_rows(im, box, min_h=0.004, gap=0.0015, thr=0.35):
    """Rows of ink inside a box: the horizontal ink profile of the crop, thresholded at `thr` of its
    peak, runs merged across gaps shorter than `gap` (fractions of image height), runs shorter than
    `min_h` dropped. Returns [[x0, y0, x1, y1], ...] in image fractions, top to bottom — one row per
    line of type inside the box. This is the segmentation the verse-number column and the body share."""
    w, h = im.size; x0, y0, x1, y1 = int(box[0]*w), int(box[1]*h), int(box[2]*w), int(box[3]*h)
    if x1-x0 < 2 or y1-y0 < 2: return []
    g = np.asarray(im.convert("L").crop((x0, y0, x1, y1)), dtype=float)
    paper = np.percentile(g, 90); ink = np.clip(paper - g, 0, None)
    prof = ink.mean(axis=1); prof = np.convolve(prof, np.ones(3)/3, mode="same")
    if prof.max() <= 0: return []
    on = prof > thr*prof.max()
    rows, start = [], None
    for i, v in enumerate(list(on) + [False]):
        if v and start is None: start = i
        elif not v and start is not None: rows.append([start, i]); start = None
    merged = []
    for r in rows:
        if merged and (r[0]-merged[-1][1]) <= gap*h: merged[-1][1] = r[1]
        else: merged.append(r)
    merged = [r for r in merged if (r[1]-r[0]) >= min_h*h]
    if len(merged) >= 3:                       # a run taller than 1.5 pitches is several rows the ink bridged
        hs = sorted(b-a for a, b in merged); med = hs[len(hs)//2]
        split = []
        for a, b in merged:
            k = int(round((b-a)/med)) if med else 1
            if k >= 2 and (b-a) > 1.5*med:
                split += [[a + (b-a)*i//k, a + (b-a)*(i+1)//k] for i in range(k)]
            else: split.append([a, b])
        merged = split
    out = []
    for a, b in merged:
        cols = np.where(ink[a:b].mean(axis=0) > thr*ink[a:b].mean(axis=0).max())[0]
        cx0, cx1 = (x0 + cols.min(), x0 + cols.max() + 1) if len(cols) else (x0, x1)
        out.append([round(cx0/w, 4), round((y0+a)/h, 4), round(cx1/w, 4), round((y0+b)/h, 4)])
    return out

BODY_CLASSES = ("MT", "AN", "IG", "AR")

def link_verse_numbers(im, regions):
    """For every VN region: its numeral rows, the body region it serves (largest vertical overlap,
    nearest horizontally), that body's line rows, and each numeral paired with the body line whose
    centre is nearest in y. The link runs from the numeral to the measure edge on the column's side,
    which is where the verse's first word sits. Returns a list, one entry per VN region."""
    out = []
    bodies = [(i, r) for i, r in enumerate(regions) if r["class"] in BODY_CLASSES]
    for vi, r in enumerate(regions):
        if r["class"] != "VN": continue
        vb = r["box"]; vrows = ink_rows(im, vb)
        best, bscore = None, None
        for bi, b in bodies:
            bb = b["box"]; ov = max(0.0, min(vb[3], bb[3]) - max(vb[1], bb[1]))
            if ov <= 0: continue
            dx = min(abs(vb[2]-bb[0]), abs(bb[2]-vb[0]))
            sc = ov - dx
            if bscore is None or sc > bscore: best, bscore = bi, sc
        entry = {"vn_index": vi, "body_index": best, "side": None, "rows": [], "lines": []}
        if best is not None:
            bb = regions[best]["box"]; lines = ink_rows(im, bb); entry["lines"] = lines
            entry["side"] = "left" if (vb[0]+vb[2])/2 < (bb[0]+bb[2])/2 else "right"
            for rw in vrows:
                yc = (rw[1]+rw[3])/2
                li = min(range(len(lines)), key=lambda k: abs((lines[k][1]+lines[k][3])/2 - yc)) if lines else None
                entry["rows"].append({"box": rw, "line": li, "origin": "auto"})
        else:
            entry["rows"] = [{"box": rw, "line": None, "origin": "auto"} for rw in vrows]
        out.append(entry)
    return out


def gold_raster(im, lid, record=RECORD):
    """The raster an accepted leaf's boxes are expressed on: the source image levelled by its skew,
    then dewarped by its colshear model if it has one."""
    rv = accepted(record)[lid]
    return apply_dewarp(deskew(im, rv.get("skew_deg", 0) or 0), rv.get("dewarp"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--record", default=str(RECORD))
    ap.add_argument("--no-source-check", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    try:
        rec = load(a.record, check_source=not a.no_source_check)
    except GoldError as e:
        print(f"GOLD REFUSED: {e}", file=sys.stderr); sys.exit(2)
    leaves = rec["leaves"]
    by = {}
    for L in leaves.values():
        by[(L.get("review") or {}).get("verdict")] = by.get((L.get("review") or {}).get("verdict"), 0) + 1
    if not a.quiet:
        print(f"record OK · {len(leaves)} leaves touched · " +
              " · ".join(f"{k or 'unreviewed'} {v}" for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))))
        for lid in sorted(accepted(a.record)):
            print("  gold:", lid)
    sys.exit(0)


if __name__ == "__main__":
    main()
