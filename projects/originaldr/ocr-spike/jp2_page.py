#!/usr/bin/env python3
"""jp2_page.py — raster access by legacy `ocr_dir`, routed through the registry.

R7.5. This module used to hold `OCR_DIR_TO_JP2`, a hand-written `ocr_dir` -> raster
directory table, and it was **the second route to the pixels**. `witnesses.py` grew
`pixel_source()` to refuse the renders and the composites; this table never called
it, so every consumer that addressed a page by `ocr_dir` bypassed the guard
entirely. Commit c44ba20 *verified* that this table is the mechanism that routed 48
of 51 ground-truth transcriptions to an inadmissible image. Verifying a defect is
not retiring it.

Four routes were wrong, and none of them looked wrong:

  * `archive-nt-1582`, `archive-ot1-1609`, `archive-ot2-1610` -> the `S01` JP2s.
    `S01` is PDF-primary: those JP2s are IA renders of an uploaded PDF, ~168 ppi
    at the leaf, where the long-s nub spans under 1.6 px. And the NT one is
    misnamed besides -- `S01`'s New Testament is the **1633** setting (1.1c).
  * `jp2-S08` -> `X`'s JP2s. `X` is a 2.00x upscale of `B`-NT with no real detail
    beyond it, and is an EXCLUDED witness.
  * `jp2-S04` -> `S04_1633-rheims-nt/1582 Douay Rheims NT_jp2`, the **retired MRC
    composite**, while the registry resolves `NT-1633-R` to the acquired Princeton
    original `newtestamentofie00engl_jp2`.
  * `jp2-S06` -> `Douay-Rheims-1610-Bible_jpg`, a 2550x3301 JPEG re-acquisition,
    while `M`'s primary artefact is the **CCITT in S06.pdf**. `S06`'s JP2 package
    is genuinely corrupt (renamed `..._jp2_broken`), so this entry could not simply
    be deleted -- `M` had to be rerouted to the PDF, not merely un-routed.

The fix is not a better table. It is that **there is no longer a table**: an
`ocr_dir` resolves to a witness, and the witness resolves its own raster. One route
to the pixels, and the guard is on it.

Two accessors, because the corpus genuinely has two admissible uses:

  * `pixel_path()` / `load()` — crops, training data, CER, glyph calls. Goes
    through `witnesses.glyph_source()` and **RAISES** for every witness barred from
    glyph work: `F` on resolution, `X` as an excluded upscale, anything in
    `NO_READING` on a binarised text layer. For `M`, whose JP2 package is corrupt
    and whose PDF holds the real CCITT stencils, it routes to **per-leaf PDF
    extraction** rather than refusing — the PDF is that witness's primary artefact,
    so reading it is not a workaround.
    (`pixel_source()` answers a narrower question — is this JP2 package the capture
    or an IA render — and so refuses `M`, which is why `glyph_source()` exists.)
  * `structure_path()` — page order, leaf counts, collation, page-number reads.
    Goes through `leaves()`, which is admissible for every witness, because a
    render preserves page content and page order.

`structure=True` must be passed explicitly and is the caller stating what it is
doing. An un-updated caller therefore FAILS LOUDLY rather than quietly receiving a
render, which is the whole point: the previous behaviour was silent success on the
wrong pixels.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "witness"))
import witnesses as W  # noqa: E402

SCANS = W.SCANS

# The legacy `ocr_dir` -> witness map lives in `witnesses.py`, beside the registry,
# and is re-exported here because that is the name existing callers import (R7.5b).
# It is NOT copied: one definition, and `test_raster_routing.py` fails if a second
# one appears anywhere in the tree.
OCR_DIR_TO_WITNESS = W.OCR_DIR_TO_WITNESS
S06_AMBIGUOUS = W.S06_AMBIGUOUS
S06_SPLIT = W.S06_SPLIT

# OCR page index -> leaf index, where the two numberings differ. VERIFIED BY
# RENDERING, not assumed: `jp2-S09ot2` OCR page 40 is leaf `..._0039` (read off the
# image, 2026-07-27). Without it, page N silently returns the NEXT LEAF for every
# page of S9's entire OT volume 2. Carried across the R7.5 rewrite unchanged --
# it is a real, checked property of that volume's OCR, not an artefact of the old
# routing table.
JP2_INDEX_OFFSET = {
    "jp2-S09ot2": -1,
}

CURATED = {"S1", "S3", "S4", "S6", "S8", "S9"}
_CACHE: dict[tuple, list[Path]] = {}


class InadmissibleRaster(ValueError):
    """A pixel-level read was attempted on a witness that cannot support one."""


# Six modules read `jp2_page.OCR_DIR_TO_JP2` at runtime and now fail, which is
# intended -- they were reading a table that routed to the wrong rasters. But a bare
# `AttributeError: module 'jp2_page' has no attribute 'OCR_DIR_TO_JP2'` tells the
# next reader nothing about why it went or what replaces it, and an uninformative
# failure invites the fastest repair rather than the right one (most likely: putting
# the table back). So the name is retired *with its reason attached*.
_RETIRED = {
    "OCR_DIR_TO_JP2":
        "retired by R7.5. It mapped an ocr_dir straight to a raster directory, which "
        "made it a SECOND route to the pixels that never called witnesses.pixel_source() "
        "-- the mechanism behind 48 of 51 ground-truth files being read from an "
        "inadmissible image. Four of its entries were wrong (F renders, X the excluded "
        "upscale, S04 the retired MRC composite, S06 a JPEG render instead of the CCITT).\n"
        "    Replace a lookup of the raster DIRECTORY with a lookup of the WITNESS:\n"
        "      jp2_page.witness_of(ocr_dir)              -> (vol, sig)\n"
        "      witnesses.glyph_source(vol, sig)          -> ('jp2'|'pdf', path), or raises\n"
        "      jp2_page.pixel_path(ocr_dir, i)           -> a leaf fit for glyph work\n"
        "      jp2_page.structure_path(ocr_dir, i)       -> a leaf for page order/counts\n"
        "    If this call site only needed the SET of known ocr_dirs, use "
        "jp2_page.OCR_DIR_TO_WITNESS. See roadmap R7.5b.",
    "_pages":
        "retired by R7.5 along with the routing table; use _leaves_for(ocr_dir, "
        "structure=...) or, better, pixel_path()/structure_path().",
}


def __getattr__(name):
    if name in _RETIRED:
        raise AttributeError(f"jp2_page.{name} {_RETIRED[name]}")
    raise AttributeError(f"module 'jp2_page' has no attribute {name!r}")


witness_of = W.witness_of        # (vol, sig) for a legacy ocr_dir, or a loud error


def wid_of(ocr_dir: str) -> str:
    """Canonical witness id ('OT2-1610-B') for a legacy `ocr_dir`.

    Provided so a consumer can RECORD which witness a page came from without
    importing the registry itself, and — more to the point — without recording a
    raster path instead. An id is an address; a path is a route.
    """
    return W.wid(*W.witness_of(ocr_dir))


EXTRACT_CACHE = Path(__file__).resolve().parent / ".scratch" / "pdf-leaves"


def _extract_leaf(vol: str, sig: str, k: int) -> Path:
    """One leaf of a PDF-primary witness, extracted on demand and cached.

    Extraction is per-leaf and lazy: `M`'s PDF is 2,872 pages, and a consumer that
    wants one leaf must not pay for all of them. Cached under `.scratch/` because
    the result is reproducible from the PDF -- it is script-emitted, so it is not
    tracked (the repo's rule: human-typed is tracked, script-emitted is not).
    """
    import extract_pdf_leaves as X
    out = EXTRACT_CACHE / W.wid(vol, sig)
    out.mkdir(parents=True, exist_ok=True)
    hit = sorted(out.glob(f"*_{k:04d}.png"))
    if hit:
        return hit[0]
    written = list(X.extract(vol, sig, [k], out))
    if not written:
        raise FileNotFoundError(
            f"{W.wid(vol, sig)}: extractor produced nothing for leaf {k}")
    return Path(written[0])


def _leaves_for(ocr_dir: str, structure: bool) -> list[Path] | None:
    key = (ocr_dir, structure)
    if key in _CACHE:
        return _CACHE[key]
    vol, sig = witness_of(ocr_dir)

    if structure:
        # Admissible for every witness: a render preserves page order and content.
        pages = list(W.leaves(vol, sig))
    else:
        try:
            kind, src = W.glyph_source(vol, sig)   # the guard, on the only route
        except ValueError as e:
            raise InadmissibleRaster(
                f"{ocr_dir} -> {W.wid(vol, sig)}: {e}\n"
                f"    If this call only needs page ORDER or page COUNT, pass "
                f"structure=True and say so. If it needs PIXELS, this witness "
                f"cannot supply them and no fallback is permitted (R5, R7)."
            ) from e
        if kind == "pdf":
            # `M`: handled per-leaf in _resolve, because its PDF is 2,872 pages and
            # listing them all to answer one index is the kind of waste that makes a
            # guarded route slow enough that someone routes around it.
            return None
        pages = sorted(Path(src).glob("*.jp2")) or list(W.leaves(vol, sig))

    if not pages:
        raise FileNotFoundError(f"{ocr_dir} -> {W.wid(vol, sig)}: no leaves resolved")
    _CACHE[key] = pages
    return pages


def _resolve(ocr_dir: str, page_index: int, structure: bool) -> Path:
    vol, sig = witness_of(ocr_dir)
    idx = page_index + JP2_INDEX_OFFSET.get(ocr_dir, 0)

    pages = _leaves_for(ocr_dir, structure)
    if pages is None:
        # PDF-primary glyph route: the extractor owns the `leaf_range` offset that
        # puts M's NT leaf 0 at package page 2072. Recomputing that here is exactly
        # how a frontmatter leaf gets attributed to the wrong tome, so the leaf
        # index is handed over as-is.
        n = W.WITNESSES[(vol, sig)]["leaves"]
        if not (0 <= idx < n):
            raise IndexError(f"{ocr_dir}: page {page_index} (leaf {idx}) outside 0..{n - 1}")
        return _extract_leaf(vol, sig, idx)

    for p in pages:                            # prefer the exact _NNNN label
        if p.stem.endswith(f"_{idx:04d}"):
            return p
    if not (0 <= idx < len(pages)):
        raise IndexError(f"{ocr_dir}: page {page_index} (leaf {idx}) outside "
                         f"0..{len(pages) - 1}")
    return pages[idx]


def pixel_path(ocr_dir: str, page_index: int) -> Path:
    """The leaf for a pixel-level read. Raises for inadmissible witnesses."""
    return _resolve(ocr_dir, page_index, structure=False)


def structure_path(ocr_dir: str, page_index: int) -> Path:
    """The leaf for a structural read — page order, counts, collation."""
    return _resolve(ocr_dir, page_index, structure=True)


def structure_leaves(ocr_dir: str) -> list[Path]:
    """Every leaf of a volume, in order, for STRUCTURAL work.

    R7.5b. The five modules that read the retired routing table all wanted the same
    thing from it: the raster DIRECTORY, so they could glob it and count or name the
    leaves. Handing back a directory is what made the table a route to the pixels,
    so it is not handed back -- this returns the leaves themselves, resolved through
    the registry.

    Structural because that is what those five do: page-count reconciliation, index
    alignment, missing-page detection, tome addressing. A render preserves page
    order and page content, so every witness is admissible for this and none is
    barred. A caller that wants to READ a leaf must ask for `pixel_path()` and will
    be refused where refusal is right; the two questions stay separate.
    """
    return list(_leaves_for(ocr_dir, structure=True) or ())


def leaf_index(ocr_dir: str, page_index: int) -> int:
    """OCR page index -> leaf index, applying the volume's verified offset.

    Split out because callers reconciling OCR pages against leaves need the offset
    without resolving a path, and the alternative -- each of them reaching into
    `JP2_INDEX_OFFSET` -- is how the verified `jp2-S09ot2 = -1` gets dropped by one
    of them and silently returns the next leaf for every page of that volume.
    """
    return page_index + JP2_INDEX_OFFSET.get(ocr_dir, 0)


def jp2_path(ocr_dir: str, page_index: int, structure: bool = False) -> Path:
    """Back-compatible entry point. Defaults to the GUARDED pixel route.

    The default is strict on purpose. Before R7.5 this function returned a render
    without complaint, so every caller that wanted pixels got them from the wrong
    image and nothing said so. Failing loudly now is the only way an existing
    caller gets told which of the two things it was doing.
    """
    return _resolve(ocr_dir, page_index, structure=structure)


def load(ocr_dir: str, page_index: int, structure: bool = False) -> Image.Image:
    p = jp2_path(ocr_dir, page_index, structure=structure)
    try:
        im = Image.open(p)
        im.load()          # force decode so PIL's lazy "broken data stream" surfaces here
        return im
    except Exception:
        # Some JP2 sets fail PIL's JPEG2000 decoder ("broken data stream"); fall
        # back to OpenJPEG's decoder. This is a DECODER fallback on the same file,
        # not a substitution of a different image, so it does not weaken the guard.
        import subprocess
        import tempfile
        tif = tempfile.NamedTemporaryFile(suffix=".tif", delete=False).name
        subprocess.run(["opj_decompress", "-i", str(p), "-o", tif],
                       check=True, capture_output=True, text=True)
        im = Image.open(tif)
        im.load()
        return im


def rasterize_png(ocr_dir: str, page_index: int, out_png: str | Path,
                  max_width: int | None = None, structure: bool = False) -> Path:
    """Save a leaf to PNG (optionally downscaled to max_width). Returns the path."""
    im = load(ocr_dir, page_index, structure=structure)
    if max_width and im.width > max_width:
        im = im.resize((max_width, int(im.height * max_width / im.width)), Image.LANCZOS)
    out = Path(out_png)
    im.save(out)
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        od, pi = sys.argv[1], int(sys.argv[2])
        out = sys.argv[3] if len(sys.argv) > 3 else f"{od}-{pi:04d}.png"
        p = rasterize_png(od, pi, out, max_width=int(sys.argv[4]) if len(sys.argv) > 4 else None)
        print("wrote", p, "from", jp2_path(od, pi).name)
    else:
        print(f"{'ocr_dir':26} {'witness':13} {'pixels':>8}  leaves")
        for od in sorted(OCR_DIR_TO_WITNESS) + [S06_AMBIGUOUS]:
            try:
                vol, sig = witness_of(od)
            except KeyError as e:
                print(f"  {od:26} AMBIGUOUS — {str(e).splitlines()[0][:60]}")
                continue
            try:
                n = len(_leaves_for(od, structure=True) or ())
            except Exception as e:
                n = f"ERR {type(e).__name__}"
            try:
                _leaves_for(od, structure=False)
                ok = "yes"
            except InadmissibleRaster:
                ok = "BARRED"
            print(f"  {od:26} {W.wid(vol, sig):13} {ok:>8}  {n}")
