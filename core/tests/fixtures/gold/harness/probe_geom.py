import sys, fitz
path = sys.argv[1]; pno = int(sys.argv[2]) if len(sys.argv)>2 else 30
doc = fitz.open(path)
pg = doc[pno]; w,h = pg.rect.width, pg.rect.height
print(f"PAGES={doc.page_count} size={w:.0f}x{h:.0f} page={pno}")
for b in sorted([b for b in pg.get_text('blocks') if b[6]==0 and b[4].strip()], key=lambda b:(round(b[1]),round(b[0]))):
    print(f"  x[{b[0]:6.1f}-{b[2]:6.1f}] y[{b[1]:6.1f}-{b[3]:6.1f}] {b[4].replace(chr(10),' / ').strip()[:62]!r}")
