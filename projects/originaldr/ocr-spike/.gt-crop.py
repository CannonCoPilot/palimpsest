#!/usr/bin/env python3
"""Crop+zoom a fractional region of a jp2 page for close glyph reading.
Usage: .gt-crop.py <ocr_dir> <page_index> <x0> <y0> <x1> <y1> <scale> <out.png>
Coords are fractions 0-1 of the full page (x0,y0 top-left, x1,y1 bottom-right)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from jp2_page import load
from PIL import Image

od, pi = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1, scale = map(float, sys.argv[3:8])
out = sys.argv[8]
im = load(od, pi)
W, H = im.width, im.height
box = (int(x0*W), int(y0*H), int(x1*W), int(y1*H))
crop = im.crop(box)
if scale != 1.0:
    crop = crop.resize((int(crop.width*scale), int(crop.height*scale)), Image.LANCZOS)
crop.convert("RGB").save(out)
print(f"wrote {out} box={box} src={W}x{H} out={crop.width}x{crop.height}")
