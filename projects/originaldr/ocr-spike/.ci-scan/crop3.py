from PIL import Image, ImageOps
import sys
sys.path.insert(0,'ocr-spike')
from jp2_page import load
im = load('archive-ot2-1610', 14)
crops = [
  ("wherwith",   520, 2050, 2860, 2170, 2.6),   # wherwith it was written, which our Sauiour gaue to the Church
  ("aug-tight", 1600, 2660, 2600, 2790, 4.0),   # them, s. Aug ser. 18. de
  ("head-tight",2050, 1580, 2680, 1730, 4.5),   # Scriptures ,
  ("para4-w",    520, 3060, 2860, 3180, 2.6),   # which God wil haue hidden ... curiously searched
]
for name,l,u,r,lo,z in crops:
    c = im.crop((l,u,r,lo)).resize(( int((r-l)*z), int((lo-u)*z) ), Image.LANCZOS)
    c = ImageOps.autocontrast(c.convert('L'))
    out = f"ocr-spike/.ci-scan/z2-{name}.png"; c.save(out); print("wrote", out, c.size)
