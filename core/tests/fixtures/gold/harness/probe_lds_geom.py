import sys, fitz
pdf = "imports/Scripture/BooksOfMormons/LDS_eng.pdf"
doc = fitz.open(pdf)
print(f"PAGES={doc.page_count}")
pages = [int(a) for a in sys.argv[1:]] or [19]
for pno in pages:
    pg = doc[pno]
    w,h = pg.rect.width, pg.rect.height
    print(f"\n===== PDF page index {pno}  (size {w:.0f}x{h:.0f}) =====")
    blocks = pg.get_text("blocks")  # (x0,y0,x1,y1,text,bno,btype)
    for b in sorted(blocks, key=lambda b:(round(b[1]),round(b[0]))):
        x0,y0,x1,y1,txt = b[0],b[1],b[2],b[3],b[4]
        snip = txt.replace("\n"," ⏎ ").strip()[:70]
        print(f"  x[{x0:6.1f}-{x1:6.1f}] y[{y0:6.1f}-{y1:6.1f}]  {snip!r}")
