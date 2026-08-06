#!/usr/bin/env python3
"""Extract leaves from a PDF-primary witness, at the raster the PDF actually holds.

Five of the eleven witnesses are PDF-primary (OCR-MASTERPLAN.md 1.2): a user
uploaded a PDF and IA *rendered* the JP2 package from it.  For those, reading
the JP2s means reading interpolation -- S08 at 2.00x, the OT S01 volumes at
4.17x, S06 at 2x on top of a letter-size re-lay-out.  The pixels the edition may
actually cite live in the PDF.

This extracts the EMBEDDED image rather than rasterising the page.  The
difference matters: rasterising asks MuPDF to draw the page at a DPI of our
choosing, which is one more render on top of the ones we just went to the
trouble of avoiding.  Pulling the embedded XObject gives the stencil as stored.

LEAF NUMBERING.  A sliced witness (NT-1582-M) numbers its own leaves from zero,
while its leaves sit at an offset inside the package -- M's leaf 0 is package
page 2072.  That offset is read from the registry's leaf_range and applied here,
in one place.  Hand-computing it at each call site is precisely how a
frontmatter leaf gets attributed to the wrong edition.

Usage:
    extract_pdf_leaves.py NT M 0 1 2 3 4 --out DIR
"""
import argparse
import pathlib
import sys

import fitz  # PyMuPDF

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from witness import witnesses as W  # noqa: E402


def package_index(vol, sig, k):
    """Package page index for this witness's own leaf k (0-based).

    Raises rather than clamping: a k past the end of the slice is a caller bug,
    and returning a neighbouring leaf would hand back a page from the OTHER
    testament for M, silently.
    """
    rec = W.WITNESSES[(vol, sig)]
    lo, hi = rec.get("leaf_range", (0, rec["leaves"]))
    if not 0 <= k < hi - lo:
        raise IndexError(
            f"{W.wid(vol, sig)}: leaf {k} is outside the witness "
            f"(0..{hi - lo - 1}); its slice is package pages {lo}..{hi - 1}")
    return lo + k


# A page whose ink covers this much or more of the sheet is not resolvable by
# the minority-class rule -- a full-page woodcut or a heavily inked plate could
# genuinely exceed it.  Ordinary letterpress text pages sit far below.
_POLARITY_CEILING = 0.35


def _normalise_polarity(path):
    """Make ink DARK, deciding from the image rather than from a convention.

    A PDF /ImageMask carries no polarity of its own: which of its two values is
    ink is set by the page's fill colour and /Decode, so an extracted stencil
    comes out white-on-black as often as not.  Feeding that to a recognizer is a
    silent defect -- it still looks like a page, and every stroke-width and
    ink-coverage statistic computed from it is inverted.

    Decided by the minority class: on a text page ink is much rarer than paper.
    If neither class is clearly the minority the image is left ALONE and the
    caller is told loudly, rather than a coin being flipped -- the same failure
    the leaf classifier hit when an absolute ink threshold was applied to a
    witness whose ink floor sat above another's median.
    """
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(path).convert("L")
    # Downsample before counting: polarity is a whole-page property, and this
    # turns a 2600x4150 count into a trivial one.
    small = im.resize((im.width // 8 or 1, im.height // 8 or 1))
    px = list(small.getdata())
    dark = sum(1 for v in px if v < 128) / len(px)
    if dark <= _POLARITY_CEILING:
        return ""                       # already ink-dark
    if dark >= 1 - _POLARITY_CEILING:
        from PIL import ImageOps
        ImageOps.invert(im).save(path)
        return f"  [polarity inverted; ink was {1 - dark:.1%} of the sheet]"
    return (f"  [!! POLARITY UNRESOLVED: {dark:.1%} dark -- neither class is a "
            f"clear minority, so the image is LEFT AS EXTRACTED. Do not cite or "
            f"train on it until the polarity is established by inspection.]")


def extract(vol, sig, ks, out):
    key = (vol, sig)
    if W.PRIMARY[key] != "pdf":
        raise SystemExit(
            f"{W.wid(vol, sig)} is JP2-primary -- its PDF is IA's derivative and "
            f"carries MRC composition and JBIG2 binarisation. Read the JP2 "
            f"package via pixel_source() instead.")
    pdf = W.PDF[key]
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    print(f"{W.wid(vol, sig)}  <- {pdf.name}  ({doc.page_count} pages)")
    written = []
    for k in ks:
        p = package_index(vol, sig, k)
        imgs = doc[p].get_images(full=True)
        # S06's pages carry two XObjects: the leaf itself, and a 1x1 DeviceGray
        # swatch that is ONE shared xref reused on every page -- a Distiller
        # background fill, not a soft mask (no /SMask, no /ImageMask, and it is
        # not linked from the leaf).  Dropping it by rule rather than by hand,
        # and only when it really is the degenerate case: anything larger stays
        # and is reported, because a genuine second image on a page would mean
        # the leaf is composited and must be inspected before it is cited.
        kept = [im for im in imgs
                if not (doc.extract_image(im[0])["width"] == 1
                        and doc.extract_image(im[0])["height"] == 1)]
        dropped = len(imgs) - len(kept)
        if len(kept) != 1:
            print(f"  leaf {k:4d} (page {p}): {len(kept)} substantive embedded "
                  f"images -- NOT the one-image-per-page assumption; inspect "
                  f"before use")
        for n, im in enumerate(kept):
            d = doc.extract_image(im[0])
            suffix = "" if len(kept) == 1 else f"_{n}"
            f = out / f"{W.wid(vol, sig)}_{k:04d}{suffix}.{d['ext']}"
            f.write_bytes(d["image"])
            pol = _normalise_polarity(f)
            written.append(f)
            note = f"  (+{dropped} 1x1 filler dropped)" if dropped else ""
            print(f"  leaf {k:4d} (page {p}): {d['width']}x{d['height']} "
                  f"{d['colorspace']}ch {d['ext']} -> {f.name}{note}{pol}")
    doc.close()
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("siglum")
    ap.add_argument("leaves", nargs="+", type=int, help="witness-local, 0-based")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    extract(a.volume, a.siglum, a.leaves, a.out)
