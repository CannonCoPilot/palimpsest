from PIL import Image, ImageOps
import sys
sys.path.insert(0,'ocr-spike')
from jp2_page import load
im = load('archive-ot2-1610', 14)
crops = [
  ("head-punct", 1750, 1560, 2700, 1740, 3.0),   # heading right end: '...Scriptures ,'
  ("explication",1450, 1880, 2500, 2050, 3.0),    # '(nor explication) of Scripture ,is'
  ("para1-l1",    520, 1720, 2860, 1900, 2.2),    # AS Prophecie ... inspired
  ("para1-colon", 520, 1880, 1900, 2060, 3.0),    # Ghost: so no prophecie
  ("wcheck",      520, 2140, 2860, 2320, 2.5),    # wherwith it was written which
  ("aug-cite",    900, 2600, 2900, 2820, 2.8),    # s. Aug ser. 18. de verb. Domini
  ("truth-semi", 1400, 2210, 2860, 2360, 3.0),    # truth; to teach al truth. Ioan
]
for name,l,u,r,lo,z in crops:
    c = im.crop((l,u,r,lo))
    c = c.resize((int(c.width*z), int(c.height*z)), Image.LANCZOS)
    c = ImageOps.autocontrast(c.convert('L'))
    out = f"ocr-spike/.ci-scan/z-{name}.png"
    c.save(out); print("wrote", out, c.size)
