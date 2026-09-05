#!/usr/bin/env python3
"""Render the LEVEL figures for the Class Register: raw vs levelled leaf, per-quarter line angle in red,
a slate horizontal for reference. Reads ../../plates/skew-survey-B.json; writes level-figs/<leaf>.jpg
(untracked: *.jpg is ignored repo-wide, so run this before build_register_B.py)."""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw
SP = Path(__file__).parent; CR = SP.parent; W_ = CR.parent
sys.path.insert(0, str(W_)); import plate_gold as PG
OUT = json.load(open(W_ / "plates" / "skew-survey-B.json"))
LEAVES = sys.argv[1:] or ["OT1-1609-B_0409", "OT2-1610-B_0026", "NT-1582-B_0562", "NT-1582-B_0781"]

def annotate(img, quarters, title):
    W, H = img.size; d = ImageDraw.Draw(img)
    d.line([(0, H//2), (W, H//2)], fill=(58, 90, 107), width=3)
    for q, (cx, cy) in {"tl": (W*.28, H*.28), "tr": (W*.72, H*.28), "bl": (W*.28, H*.72), "br": (W*.72, H*.72)}.items():
        a = quarters.get(q)
        if a is None: d.text((cx-40, cy-8), "no lines", fill=(140, 135, 124)); continue
        t = math.radians(-a); L = W*.18
        d.line([(cx-L*math.cos(t), cy-L*math.sin(t)), (cx+L*math.cos(t), cy+L*math.sin(t))], fill=(163, 43, 34), width=4)
        d.text((cx-L*math.cos(t), cy-L*math.sin(t)-16), f"{a:+.2f}°", fill=(163, 43, 34))
    d.rectangle([0, 0, W, 34], fill=(26, 23, 20)); d.text((10, 10), title, fill=(233, 230, 222))
    return img

(SP / "level-figs").mkdir(exist_ok=True)
for lid in LEAVES:
    im = Image.open(CR / "img-B" / f"{lid}.jpg").convert("RGB"); r = OUT[lid]; k = r["skew"]; W, H = im.size
    q_lev = {qq: (None if v is None else round(v-k, 2)) for qq, v in r["quarters"].items()}
    a = annotate(im.copy(), r["quarters"], f"{lid}  raw  · page {k:+.2f}° · quarters as measured")
    b = annotate(PG.deskew(im, k), q_lev, f"{lid}  levelled by {k:+.2f}° · residual per quarter · spread {r['spread']:.2f}°")
    both = Image.new("RGB", (W*2+20, H), (218, 213, 201)); both.paste(a, (0, 0)); both.paste(b, (W+20, 0))
    both.resize((1400, round(H*1400/(W*2+20)))).save(SP / "level-figs" / f"{lid}.jpg", "JPEG", quality=72)
    print("fig", lid)
