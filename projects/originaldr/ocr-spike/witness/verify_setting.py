"""R8.4 — verify every witness's SETTING, not just the suspected one.

The `F` error stood for four months because the concordance verified *title
pages*, and a title page is exactly what `F` turns out to have borrowed.  The
test that catches it reads the **printed page number and the running head**
at several separated points and compares them across witnesses that claim the
same setting.  Two copies of one setting put the same printed page number on
the same text with the same running head; two different editions do not, and
they diverge by tens of pages (`B` 743 against `F` 692).

This module does the mechanical half: it crops the head of a leaf -- where the
running head and the page number sit -- for probe leaves spread through each
witness, and assembles one contact sheet per witness for reading.  The
readings themselves are recorded in `setting-readings.json` and checked by
`test_setting_verified.py`.

Structural work only, so `leaves()` is the correct accessor: a render
preserves page content and page order, which is all a page number needs.
`pixel_source()` would refuse five of the twelve and none of the refusals
would be relevant here -- a page number survives interpolation intact.
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witnesses as W

OUT = Path(__file__).resolve().parent.parent / ".scratch" / "setting-verify"

# Fraction of page height to keep.  The running head and page number sit in the
# top margin; 0.16 holds them plus the first lines of text, which is what makes
# a same-setting claim checkable -- identical line breaks are the corroboration
# the page number alone does not give.
HEAD_FRAC = 0.16
SHEET_W = 1500

# Probe positions as fractions of the leaf list.  Four, not three, because a
# probe can land on a plate, a blank or a leaf whose number failed to ink, and
# the acceptance criterion needs three *readable* points.  Spread wide: two
# adjacent probes cannot distinguish a constant offset from a coincidence.
PROBE_FRACS = (0.22, 0.42, 0.62, 0.82)


def probe_indices(n, fracs=PROBE_FRACS):
    return [min(n - 1, max(0, int(round(f * n)))) for f in fracs]


def head_crop(path, width=SHEET_W):
    im = Image.open(path)
    im.draft("RGB", (width * 2, int(width * 2 * 1.4)))  # cheap partial decode
    im = im.convert("RGB")
    w, h = im.size
    im = im.crop((0, 0, w, int(h * HEAD_FRAC)))
    scale = width / im.width
    return im.resize((width, max(1, int(im.height * scale))), Image.LANCZOS)


def leaf_paths(vol, sig, idxs, tmp):
    """Leaf images for the probe indices, from whichever artefact can supply them.

    `M`'s JP2 package is the known-broken one (`..._jp2_broken`), so `leaves()`
    yields paths that will not decode.  M is PDF-primary anyway, and the PDF is
    where its real CCITT stencils live, so falling back to the extractor is not
    a workaround -- it is reading the primary artefact.  The extractor also owns
    the `leaf_range` offset (M's leaf 0 is package page 2072); recomputing that
    here is exactly how a frontmatter leaf gets attributed to the wrong tome.

    The fallback is NEVER silent: an unreadable JP2 on a witness that is *not*
    PDF-primary is a real defect and must raise, not quietly reroute.
    """
    try:
        fs = W.leaves(vol, sig)
        Image.open(fs[idxs[0]]).convert("RGB")  # probe one before trusting all
        return [fs[i] for i in idxs], "jp2"
    except Exception as e:
        if W.PRIMARY[(vol, sig)] != "pdf":
            raise RuntimeError(
                f"{W.wid(vol, sig)}: JP2 leaves unreadable ({type(e).__name__}: {e}) "
                f"and this witness is JP2-primary, so there is no admissible "
                f"fallback. This is a defect, not a routing question.") from e
        import extract_pdf_leaves as X
        tmp.mkdir(parents=True, exist_ok=True)
        written = X.extract(vol, sig, list(idxs), tmp)
        return list(written), "pdf"


def sheet(vol, sig, out_dir=OUT, idxs=None, tag=""):
    """One contact sheet of head-crops for a witness, labelled by leaf index.

    `idxs` overrides the spread probes.  Targeted leaves are what turn a
    near-miss into a match: probing at fixed FRACTIONS lands two witnesses on
    neighbouring printed pages, which corroborates but does not demonstrate.
    The acceptance criterion wants the SAME printed page in both.
    """
    n = W.WITNESSES[(vol, sig)]["leaves"]
    if idxs is None:
        idxs = probe_indices(n)
    paths, via = leaf_paths(vol, sig, idxs, out_dir / f"_{W.wid(vol, sig)}_src")
    crops = [(i, head_crop(p)) for i, p in zip(idxs, paths)]
    band = 34
    total_h = sum(c.height + band for _, c in crops)
    sheet_im = Image.new("RGB", (SHEET_W, total_h), "white")
    d = ImageDraw.Draw(sheet_im)
    y = 0
    for i, c in crops:
        d.rectangle([0, y, SHEET_W, y + band], fill=(20, 20, 20))
        d.text((8, y + 10), f"{W.wid(vol, sig)}   leaf {i}  of {n}   [via {via}]",
               fill=(255, 255, 255))
        y += band
        sheet_im.paste(c, (0, y))
        y += c.height
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{W.wid(vol, sig)}{tag}.png"
    sheet_im.save(p)
    return p, idxs


def main():
    want = sys.argv[1:] or None
    for (vol, sig) in sorted(W.WITNESSES):
        wid = W.wid(vol, sig)
        if want and wid not in want and vol not in want:
            continue
        try:
            p, idxs = sheet(vol, sig)
            print(f"{wid:14s} leaves {idxs}  -> {p}")
        except Exception as e:  # reported, never skipped silently
            print(f"{wid:14s} FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
