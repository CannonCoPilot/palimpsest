#!/usr/bin/env python3
"""DEWARP figures: levelled leaf vs dewarped leaf, cell angles drawn in red (residual), for the leaves
the survey dewarped. Writes level-figs/dewarp-<leaf>.jpg (untracked)."""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw
SP = Path(__file__).parent; CR = SP.parent; W_ = CR.parent
sys.path.insert(0, str(W_)); import plate_gold as PG
OUT = json.load(open(W_ / "plates" / "skew-survey-B.json"))
LEAVES = sys.argv[1:] or [l for l, r in OUT.items() if r.get("warp_status") == "dewarped"]
def annotate(img, cells, title):
    W, H = img.size; d = ImageDraw.Draw(img)
    for half, yc in (("top", H*0.28), ("bot", H*0.72)):
        for x, a, c in cells[half]:
            cx = x*W; t = math.radians(-a); L = W*0.07
            d.line([(cx-L*math.cos(t), yc-L*math.sin(t)), (cx+L*math.cos(t), yc+L*math.sin(t))], fill=(163, 43, 34), width=4)
            d.text((cx-14, yc-18), f"{a:+.2f}", fill=(163, 43, 34))
    for y in (H*0.28, H*0.72): d.line([(0, y), (W, y)], fill=(58, 90, 107), width=2)
    d.rectangle([0, 0, W, 34], fill=(26, 23, 20)); d.text((10, 10), title, fill=(233, 230, 222))
    return img
(SP / "level-figs").mkdir(exist_ok=True)
for lid in LEAVES:
    r = OUT[lid]; im = Image.open(CR / "img-B" / f"{lid}.jpg").convert("RGB"); lev = PG.deskew(im, r["skew"]); W, H = im.size
    dw = PG.apply_dewarp(lev, r["dewarp"]); cells_after, rms_after = PG.warp_cells(dw)
    a = annotate(lev.copy(), {h: [tuple(c) for c in r["cells"][h]] for h in r["cells"]}, f"{lid}  levelled {r['skew']:+.2f}° · cell residual RMS {r['rms_before']:.2f}°")
    b = annotate(dw, cells_after, f"{lid}  dewarped (colshear-v1) · RMS {rms_after:.2f}°")
    both = Image.new("RGB", (W*2+20, H), (218, 213, 201)); both.paste(a, (0, 0)); both.paste(b, (W+20, 0))
    both.resize((1400, round(H*1400/(W*2+20)))).save(SP / "level-figs" / f"dewarp-{lid}.jpg", "JPEG", quality=72); print("fig", lid)
