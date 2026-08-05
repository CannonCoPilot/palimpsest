#!/usr/bin/env python3
"""Crop + enhance a column band from a rendered historical-table page for close reading.
Usage: hist_crop.py <src_png> <x0frac> <x1frac> <y0frac> <y1frac> <out_png> [scale] [enhance]
fracs are 0..1 of width/height. scale default 2.0. enhance=1 applies autocontrast+sharpen.
"""
import sys
from PIL import Image, ImageOps, ImageFilter

src, x0, x1, y0, y1, out = sys.argv[1:7]
scale = float(sys.argv[7]) if len(sys.argv) > 7 else 2.0
enhance = (len(sys.argv) > 8 and sys.argv[8] == "1")
im = Image.open(src).convert("L")
W, H = im.size
box = (int(float(x0)*W), int(float(y0)*H), int(float(x1)*W), int(float(y1)*H))
c = im.crop(box)
c = c.resize((int(c.width*scale), int(c.height*scale)), Image.LANCZOS)
if enhance:
    c = ImageOps.autocontrast(c, cutoff=1)
    c = c.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))
c.save(out)
print("wrote", out, c.size)
