from PIL import Image, ImageOps
import sys; sys.path.insert(0,'ocr-spike')
from jp2_page import load
im = load('archive-ot2-1610', 14)
# line 6: 'to abide for euer, the Spirite of truth ; to teach al truth. Ioan. 14. 16.'
c = im.crop((520, 2175, 2600, 2300)).resize((int((2600-520)*3.0), int((2300-2175)*3.0)), Image.LANCZOS)
c = ImageOps.autocontrast(c.convert('L'))
c.save("ocr-spike/.ci-scan/z3-truthline.png"); print("wrote", c.size)
# also 'Scripture, is made' region on line 3 to check comma spacing
c2 = im.crop((1900, 1930, 2860, 2050)).resize((int((2860-1900)*3.0), int((2050-1930)*3.0)), Image.LANCZOS)
c2 = ImageOps.autocontrast(c2.convert('L'))
c2.save("ocr-spike/.ci-scan/z3-scripture-is.png"); print("wrote", c2.size)
