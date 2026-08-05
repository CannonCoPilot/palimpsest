#!/usr/bin/env python3
"""jp2_page.py — ALWAYS use the jp2 rasters (Sir 2026-07-19).

Maps every ocr_dir (and the curated source volumes) to its high-quality JPEG2000 page set, so all
rasterization for OCR pipelines, Jarvis' own visual transcription, and the browser review tool pulls
the jp2 page — never the low-res PDF. Curated reference set: S1, S3, S4, S6, S8, S9 (drop S2,S5,S7,S10-S15).
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image

SCANS = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/DouayRheims_DR/sources/scans")

# ocr_dir -> (source_id, jp2 dir relative to SCANS). Curated set only.
OCR_DIR_TO_JP2 = {
    "archive-ot1-1609":       ("S1", "S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  1 of 3 1609 Old Testament_jp2"),
    "archive-ot2-1610":       ("S1", "S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  2 of 3 1610 Old Testament_jp2"),
    "archive-nt-1582":        ("S1", "S01_1582-first-edition-3vol/1582 Douai Rheims Douay Rheims First Edition  3 of 3 1582 New Testament_jp2"),
    "pdf-S03a":               ("S3", "S03_holie-bible-engl-ot-vol1/holiebiblefaithf01engl_jp2"),
    "pdf-S03b":               ("S3", "S03_holie-bible-engl-ot-vol2/holiebiblefaithf02engl_jp2"),
    "jp2-S04":                ("S4", "S04_1633-rheims-nt/1582 Douay Rheims NT_jp2"),
    # S06 READS JPEG, NOT JP2 (2026-08-03). The shipped `Douay-Rheims-1610-Bible_jp2.zip` decoded to files
    # PIL cannot open, and the per-file .jp2 links return the same broken data — the directory has been
    # renamed `..._jp2_broken` so nothing can drift back onto it. `fetch_s06_jpg.py` re-acquired all 2,872
    # leaves as verified JPEG (2550x3301) from archive.org's zip-member transcode endpoint. This entry is
    # the ONLY reason S06 has a raster path at all; a KeyError here means the fetch has not been run.
    "jp2-S06":                ("S6", "S06_1610-facsimile-whole/Douay-Rheims-1610-Bible_jpg"),
    "jp2-S08":                ("S8", "S08_1582-rhemes-nt-hires/1582_Rhemes_New_Testament_jp2"),
    "pdf-S09nt":              ("S9", "S09_nevv-testament-mart-3vol/nevvtestamentofi00mart_jp2"),
    "archive-holiebible-ot1": ("S9", "S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_0_jp2"),
    # S9's OT2. Its OCR lives under `jp2-S09ot2` (1150 files, S09ot2_0001..S09ot2_1150) — the same volume,
    # written under a different name, which is why it looked like an unmapped witness AND like an un-OCR'd
    # source at the same time. `archive-holiebible-ot2` is retained as an alias of the same jp2 set.
    "jp2-S09ot2":             ("S9", "S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_jp2"),
    "archive-holiebible-ot2": ("S9", "S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_jp2"),
}

# OCR page index -> jp2 page index, where the two numberings differ. VERIFIED BY RENDERING, not assumed:
# `jp2-S09ot2` OCR page 40 is jp2 `holiebiblefaithf00mart_0039` (read off the image, 2026-07-27). Without
# this, `jp2_path` matches OCR page N to the file ending `_N` and silently returns the NEXT LEAF for every
# page of S9's entire Old Testament volume 2 — the wrong pixels for every crop, R3 read and visual check.
JP2_INDEX_OFFSET = {
    "jp2-S09ot2": -1,
}
CURATED = {"S1", "S3", "S4", "S6", "S8", "S9"}
_CACHE: dict[str, list[Path]] = {}


def _pages(ocr_dir: str) -> list[Path]:
    if ocr_dir not in OCR_DIR_TO_JP2:
        raise KeyError(f"{ocr_dir} not in curated jp2 map")
    if ocr_dir not in _CACHE:
        d = SCANS / OCR_DIR_TO_JP2[ocr_dir][1]
        # A source's rasters are whatever format that source HAS. S06's are JPEG because its JP2s are
        # corrupt; globbing only `*.jp2` returned an empty list, and an empty list makes `jp2_path` raise
        # IndexError deep inside a recognition run rather than saying "this source has no rasters".
        pages = sorted(d.glob("*.jp2")) or sorted(d.glob("*.jpg")) or sorted(d.glob("*.png")) \
            or sorted(d.glob("*.tif"))
        if not pages:
            raise FileNotFoundError(f"{ocr_dir}: no rasters under {d} (.jp2/.jpg/.png/.tif)")
        _CACHE[ocr_dir] = pages
    return _CACHE[ocr_dir]


def jp2_path(ocr_dir: str, page_index: int) -> Path:
    """the jp2 file for a 0-based page index (matches PDF page order / the `_NNNN` label)."""
    pages = _pages(ocr_dir)
    idx = page_index + JP2_INDEX_OFFSET.get(ocr_dir, 0)
    # prefer exact _NNNN match, else positional
    for p in pages:
        if p.stem.endswith(f"_{idx:04d}"):
            return p
    return pages[idx]


def load(ocr_dir: str, page_index: int) -> Image.Image:
    p = jp2_path(ocr_dir, page_index)
    try:
        im = Image.open(p)
        im.load()  # force decode so PIL's lazy "broken data stream" surfaces here
        return im
    except Exception:
        # Some jp2 sets (notably S6 / jp2-S06) fail PIL's JPEG2000 decoder ("broken data stream").
        # Fall back to OpenJPEG's opj_decompress (2026-07-20 fix).
        import subprocess
        import tempfile
        tif = tempfile.NamedTemporaryFile(suffix=".tif", delete=False).name
        subprocess.run(["opj_decompress", "-i", str(p), "-o", tif],
                       check=True, capture_output=True, text=True)
        im = Image.open(tif)
        im.load()
        return im


def rasterize_png(ocr_dir: str, page_index: int, out_png: str | Path, max_width: int | None = None) -> Path:
    """Save a jp2 page to PNG (optionally downscaled to max_width). Returns the path."""
    im = load(ocr_dir, page_index)
    if max_width and im.width > max_width:
        im = im.resize((max_width, int(im.height * max_width / im.width)), Image.LANCZOS)
    out = Path(out_png)
    im.save(out)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        od, pi = sys.argv[1], int(sys.argv[2])
        out = sys.argv[3] if len(sys.argv) > 3 else f"/tmp/{od}-{pi:04d}.png"
        p = rasterize_png(od, pi, out, max_width=int(sys.argv[4]) if len(sys.argv) > 4 else None)
        print("wrote", p, "from", jp2_path(od, pi).name)
    else:
        print("ocr_dir -> jp2 page counts:")
        for od in OCR_DIR_TO_JP2:
            try:
                print(f"  {od:26} {len(_pages(od)):>5} pages")
            except Exception as e:
                print(f"  {od:26} ERROR {e}")
