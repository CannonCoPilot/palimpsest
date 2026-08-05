from PIL import Image, ImageOps
import sys
sys.path.insert(0,'ocr-spike')
from jp2_page import load
im = load('archive-ot2-1610', 14)
print("full size", im.size)
# crops: (name, left, upper, right, lower)
W,H = im.size
crops = [
  ("A-head-para1", 520, 1560, 2860, 2500),
  ("B-mid",        520, 2440, 2860, 3260),
  ("C-bot-rule",   520, 3180, 2860, 3900),
  ("L-margin",     120,  520, 620, 3900),
]
for name,l,u,r,lo in crops:
    c = im.crop((l,u,r,lo))
    # upscale 1.8x for legibility, autocontrast
    c = c.resize((int(c.width*1.8), int(c.height*1.8)), Image.LANCZOS)
    c = ImageOps.autocontrast(c.convert('L'))
    out = f"ocr-spike/.ci-scan/ci-{name}.png"
    c.save(out)
    print("wrote", out, c.size)
