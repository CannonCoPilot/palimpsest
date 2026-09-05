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
    med = sorted(v for v, _ in sc)[len(sc)//2] or 1e-9
    conf = round(peak/med, 2)
    if detail: return {"skew_deg": round(best, 2), "confidence": conf}
    return round(best, 2) if conf >= 1.5 else 0.0

CONF_MIN = 1.5

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


def gold_raster(im, lid, record=RECORD):
    """The raster an accepted leaf's boxes are expressed on: the source image levelled by its skew."""
    rv = accepted(record)[lid]
    return deskew(im, rv.get("skew_deg", 0) or 0)


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
