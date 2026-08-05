#!/usr/bin/env python3
"""Ad-hoc crop helper for matter GT transcription. Crops a jp2 page region at full raster res.
Usage: _matter_crop.py <ocr_dir> <page_index> <x0> <y0> <x1> <y1> <out.png> [scale]
Coords are pixels in the full raster. Optional scale upsamples (LANCZOS) for legibility.
"""
import sys
from jp2_page import load

od, pi = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1 = map(int, sys.argv[3:7])
out = sys.argv[7]
scale = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0
im = load(od, pi)
c = im.crop((x0, y0, x1, y1))
if scale != 1.0:
    c = c.resize((int(c.width * scale), int(c.height * scale)))
c.save(out)
print(f"wrote {out} size={c.size} from full {im.size}")
