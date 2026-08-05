#!/usr/bin/env python3
"""crop_band.py — crop a fractional box from a rendered page PNG and upscale for legible reads.
Usage: crop_band.py <in.png> <out.png> <left> <top> <right> <bottom> [scale]
Fractions are 0..1 of width/height. scale default 1.5 (LANCZOS)."""
import sys
from PIL import Image

inp, outp = sys.argv[1], sys.argv[2]
l, t, r, b = (float(x) for x in sys.argv[3:7])
scale = float(sys.argv[7]) if len(sys.argv) > 7 else 1.5
im = Image.open(inp)
W, H = im.size
box = (int(l * W), int(t * H), int(r * W), int(b * H))
c = im.crop(box)
c = c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)
c.save(outp)
print("wrote", outp, c.size, "from box", box)
