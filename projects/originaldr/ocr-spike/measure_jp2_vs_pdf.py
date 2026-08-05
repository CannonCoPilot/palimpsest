#!/usr/bin/env python3
"""Authoritative jp2-master vs PDF-content-raster resolution comparison.

The earlier WIN table trusted a PDF "census" that recorded the FIRST embedded
image per page -- but archive.org PDFs stack a low-res color preview over a
hi-res masked content image. pdftoppm (what the OCR pipeline feeds kraken)
rasterizes from the CONTENT image, so the PDF's true resolution ceiling is the
MAX embedded raster, not the first. This script measures both sides directly
from the files and flags a re-OCR WIN only where jp2 meaningfully out-resolves
the PDF's real content raster (>1.3x linear).
"""
import io
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
SCANS = Path(
    "/Users/nathanielcannon/Claude/Projects/palimpsest/imports/"
    "Scripture/Bibles/DouayRheims_DR/sources/scans"
)
WIN_LINEAR = 1.3  # require >30% more linear resolution to justify re-OCR

# key -> (scans subdir, jp2 zip filename, pdf filename or None to auto-pick)
SOURCES = {
    "S1-ot1": ("S01_1582-first-edition-3vol", "1582 Douai Rheims Douay Rheims First Edition  1 of 3 1609 Old Testament_jp2.zip", None),
    "S1-ot2": ("S01_1582-first-edition-3vol", "1582 Douai Rheims Douay Rheims First Edition  2 of 3 1610 Old Testament_jp2.zip", None),
    "S1-nt":  ("S01_1582-first-edition-3vol", "1582 Douai Rheims Douay Rheims First Edition  3 of 3 1582 New Testament_jp2.zip", None),
    "S2":     ("S02_1609-douay-ot-hires", "1635 Douay Old Testament 1_jp2.zip", "S02.pdf"),
    "S3a":    ("S03_holie-bible-engl-ot-vol1", "holiebiblefaithf01engl_jp2.zip", "S03a.pdf"),
    "S3b":    ("S03_holie-bible-engl-ot-vol2", "holiebiblefaithf02engl_jp2.zip", "S03b.pdf"),
    "S4":     ("S04_1633-rheims-nt", "1582 Douay Rheims NT_jp2.zip", "S04.pdf"),
    "S5":     ("S05_newtestament-engl-nt", "newtestamentofie00engl_jp2.zip", "newtestamentofie00engl.pdf"),
    "S6":     ("S06_1610-facsimile-whole", "Douay-Rheims-1610-Bible_jp2.zip", "S06.pdf"),
    "S8":     ("S08_1582-rhemes-nt-hires", "1582_Rhemes_New_Testament_jp2.zip", None),
    "S9-nt":  ("S09_nevv-testament-mart-3vol", "nevvtestamentofi00mart_jp2.zip", None),
    "S9-ot1": ("S09_nevv-testament-mart-3vol", "holiebiblefaithf00mart_0_jp2.zip", None),
    "S9-ot2": ("S09_nevv-testament-mart-3vol", "holiebiblefaithf00mart_jp2.zip", None),
}
IMG_EXT = (".jp2", ".jpg", ".jpeg", ".png", ".tif", ".tiff")


def zip_complete(zp: Path) -> bool:
    """True if the zip has a valid central directory (i.e. fully downloaded)."""
    try:
        with zipfile.ZipFile(zp) as z:
            return z.testzip() is None or True  # open succeeded = CD present
    except zipfile.BadZipFile:
        return False


def jp2_dims(zp: Path):
    with zipfile.ZipFile(zp) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith(IMG_EXT))
        if not names:
            return None
        best = (0, 0)
        # sample 3 mid-document pages, take max
        n = len(names)
        for idx in {n // 3, n // 2, (2 * n) // 3}:
            with z.open(names[idx]) as f:
                im = Image.open(io.BytesIO(f.read()))
                if im.size[0] * im.size[1] > best[0] * best[1]:
                    best = im.size
        return best, n


def pdf_max_raster(pdf: Path):
    """Max embedded raster (image OR stencil) + its bpc, across sampled pages.

    archive.org facsimile PDFs often store the scan as a CCITT 1-bit *stencil*
    rather than an image, so we must count both. bpc==1 means bitonal (pre-
    thresholded) -- a quality penalty for archaic ſ/f disambiguation even at
    equal resolution.
    """
    best = (0, 0)
    best_bpc = None
    for f, l in ((200, 205), (400, 405)):
        try:
            out = subprocess.run(
                ["pdfimages", "-list", "-f", str(f), "-l", str(l), str(pdf)],
                capture_output=True, text=True, timeout=60,
            ).stdout
        except Exception:
            continue
        for line in out.splitlines()[2:]:
            p = line.split()
            if len(p) >= 8 and p[2] in ("image", "stencil", "mask", "smask"):
                try:
                    w, h, bpc = int(p[3]), int(p[4]), int(p[7])
                except ValueError:
                    continue
                if w * h > best[0] * best[1]:
                    best = (w, h)
                    best_bpc = bpc
    return (best, best_bpc) if best != (0, 0) else None


def pick_pdf(subdir: Path, name):
    if name:
        p = subdir / name
        return p if p.exists() else None
    pdfs = sorted(subdir.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def main():
    only = set(sys.argv[1:])
    print(f"{'key':8} {'jp2 master':>16} {'pdf content':>16} {'lin×':>5}  verdict")
    print("-" * 72)
    for key, (sub, jp2name, pdfname) in SOURCES.items():
        if only and key not in only:
            continue
        subdir = SCANS / sub
        zp = subdir / jp2name
        if not zp.exists():
            print(f"{key:8} {'(not downloaded)':>16}")
            continue
        if not zip_complete(zp):
            print(f"{key:8} {'(partial dl)':>16}")
            continue
        jd = jp2_dims(zp)
        if not jd:
            print(f"{key:8} {'(no images)':>16}")
            continue
        (jw, jh), npages = jd
        pdf = pick_pdf(subdir, pdfname)
        pr = pdf_max_raster(pdf) if pdf else None
        jp2_str = f"{jw}x{jh}"
        if pr:
            (pw, ph), bpc = pr
            bit = "1bit" if bpc == 1 else f"{bpc}bit"
            pdf_str = f"{pw}x{ph} {bit}"
            lin = ((jw * jh) / (pw * ph)) ** 0.5 if pw * ph else 0
            # WIN on resolution OR on tonal depth (bitonal PDF loses ſ signal)
            if lin > WIN_LINEAR:
                verdict = "WIN"
            elif bpc == 1:
                verdict = "WIN (bitonal->gray)"
            else:
                verdict = "no gain"
            print(f"{key:8} {jp2_str:>16} {pdf_str:>20} {lin:5.2f}  {verdict} ({npages}pg)")
        else:
            print(f"{key:8} {jp2_str:>16} {'(no pdf raster)':>20}   ?    needs pdftoppm check ({npages}pg)")


if __name__ == "__main__":
    main()
