import sys
sys.path.insert(0, 'ocr-spike')
from jp2_page import load
from PIL import Image

# usage: crop.py <ocr_dir> <page> <l> <u> <r> <lo> <scale> <out>
_, ocr_dir, page, l, u, r, lo, scale, out = sys.argv
im = load(ocr_dir, int(page))
c = im.crop((int(l), int(u), int(r), int(lo)))
s = float(scale)
if s != 1.0:
    c = c.resize((int(c.width*s), int(c.height*s)), Image.LANCZOS)
if c.mode != 'RGB':
    c = c.convert('RGB')
c.save(out)
print(f"{out} {c.size} from {ocr_dir} p{page}")
