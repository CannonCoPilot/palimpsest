#!/usr/bin/env python3
"""P1.4 visual-survey helper (SCRATCH tool, not committed).

Renders front/back leaves of an EEBO scan PDF and montages their header bands
into legible contact sheets so apparatus headers can be visually located +
transcribed. Usage:

  p14_survey.py <md5> <label> [front_n] [back_n] [--full a-b] [--dpi N] [--band f]
"""
import glob, os, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
ORIG = os.path.join(REPO, "imports/Scripture/Bibles/DouayRheims_DR/Original")
RENDER = os.path.dirname(__file__) + "/p14-render"


def pdf_for(md5):
    g = glob.glob(f"{ORIG}/*{md5}*.pdf")
    if not g:
        raise SystemExit(f"no EEBO pdf for md5 {md5}")
    return g[0]


def npages(pdf):
    out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if ln.startswith("Pages:"):
            return int(ln.split()[1])
    return 0


def render_range(pdf, lo, hi, prefix, dpi):
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(lo), "-l", str(hi),
                    pdf, prefix], check=True)


def montage(pngs, out, band, tile_w=820, cols=2):
    from PIL import Image, ImageDraw
    bands = []
    for f in pngs:
        im = Image.open(f).convert("RGB"); w, h = im.size
        crop = im if band >= 1.0 else im.crop((0, 0, w, int(h * band)))
        bw, bh = crop.size; nh = int(bh * tile_w / bw)
        tag = os.path.basename(f).split("-")[-1].split(".")[0]
        bands.append((tag, crop.resize((tile_w, nh))))
    bh = max(b.size[1] for _, b in bands); rows = (len(bands) + cols - 1) // cols
    pad, lab = 8, 22
    sheet = Image.new("RGB", (cols * (tile_w + pad) + pad, rows * (bh + lab + pad) + pad), "white")
    dr = ImageDraw.Draw(sheet)
    for i, (tag, b) in enumerate(bands):
        r, c = divmod(i, cols); x = pad + c * (tile_w + pad); y = pad + r * (bh + lab + pad)
        dr.rectangle([x, y, x + tile_w, y + lab], fill=(255, 235, 190))
        dr.text((x + 4, y + 4), f"PAGE {tag}", fill="red")
        sheet.paste(b, (x, y + lab))
    sheet.save(out); print("  ->", out, sheet.size)


def main():
    md5, label = sys.argv[1], sys.argv[2]
    front_n = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 14
    back_n = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 12
    dpi = 150; band = 0.28
    full = None
    a = sys.argv[3:]
    for i, tok in enumerate(a):
        if tok == "--dpi": dpi = int(a[i + 1])
        if tok == "--band": band = float(a[i + 1])
        if tok == "--full":
            lo, hi = a[i + 1].split("-"); full = (int(lo), int(hi))
    pdf = pdf_for(md5); n = npages(pdf)
    print(f"{label}: {os.path.basename(pdf)[:60]} ({n}pp)")
    os.makedirs(RENDER, exist_ok=True)
    if full:
        lo, hi = full
        pfx = f"{RENDER}/{label}_full"
        render_range(pdf, lo, hi, pfx, dpi)
        pngs = sorted(glob.glob(f"{pfx}-*.png"))
        montage(pngs, f"{RENDER}/{label}-full-{lo}_{hi}.png", band)
        return
    # front
    render_range(pdf, 1, min(front_n, n), f"{RENDER}/{label}_front", dpi)
    montage(sorted(glob.glob(f"{RENDER}/{label}_front-*.png")), f"{RENDER}/{label}-front.png", band)
    # back
    blo = max(1, n - back_n + 1)
    render_range(pdf, blo, n, f"{RENDER}/{label}_back", dpi)
    montage(sorted(glob.glob(f"{RENDER}/{label}_back-*.png")), f"{RENDER}/{label}-back.png", band)
    print(f"  back pages = {blo}..{n}")


if __name__ == "__main__":
    main()
