"""config_sweep.py — per-page configuration search (the user's ask: adapt per-page, take best).

For one page, sweep {source DPI} x {binarization} for a fixed recognizer, measure the
ALIGNMENT-FREE concat identity vs the true on-page reference verses (isolates recognition+
segmentation quality from the localization artifact). Also scores the EXISTING diplomatic OCR
as a reference point. Prints a table + the winning config.

Usage: ocr-venv/bin/python ocr-spike/config_sweep.py <ocr_dir> <pdf_page_index> <book> <chapter> <vlo> <vhi>
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rung1_surya as R  # noqa: E402
from char_identity import edit_ratio, fold_archaic  # noqa: E402

import fitz  # noqa: E402
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("rl", str(HERE / "reocr_ladder.py"))
rl = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rl)  # type: ignore

from skimage.filters import threshold_otsu, threshold_sauvola  # noqa: E402
from kraken import blla, rpred  # noqa: E402
from kraken.lib import models  # noqa: E402

MODEL = str(HERE / "models" / "reichenau_lat.mlmodel")
_REC = models.load_any(MODEL, device="cpu")


def strip_vnum(t: str) -> str:
    return re.sub(r"^\s*\d{1,3}\s*", "", t).strip()


def binarize(im: Image.Image, mode: str) -> Image.Image:
    if mode == "none":
        return im.convert("L")
    g = np.asarray(im.convert("L"))
    if mode == "otsu":
        th = threshold_otsu(g)
        b = (g > th).astype(np.uint8) * 255
    elif mode == "sauvola":
        th = threshold_sauvola(g, window_size=25)
        b = (g > th).astype(np.uint8) * 255
    else:
        raise ValueError(mode)
    return Image.fromarray(b, mode="L")


def kraken_lines_on(im_gray: Image.Image) -> list[dict]:
    seg = blla.segment(im_gray, device="cpu")
    out = []
    for r in rpred.rpred(_REC, im_gray, seg):
        b = getattr(r, "line", None)
        boundary = (b.get("boundary") if isinstance(b, dict) else None) or getattr(r, "boundary", None)
        if not boundary:
            continue
        xs = [p[0] for p in boundary]; ys = [p[1] for p in boundary]
        out.append({"text": str(getattr(r, "prediction", "") or ""),
                    "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return out


def concat_ratio(slines, ref_concat) -> tuple[float, int]:
    ocr = " ".join(strip_vnum(l["text"]) for l in slines if l["text"].strip())
    return edit_ratio(fold_archaic(ocr), fold_archaic(ref_concat)), ocr.count("ſ")


def main() -> int:
    ocr_dir, pidx, book, ch = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    vlo, vhi = int(sys.argv[5]), int(sys.argv[6])
    a_ref = R.archaic_ref(book)
    onpage = [f"scripture/{book}/{ch}/{v}" for v in range(vlo, vhi + 1) if f"scripture/{book}/{ch}/{v}" in a_ref]
    ref_concat = " ".join(a_ref[k] for k in onpage)
    ref_s = ref_concat.count("ſ")
    print(f"ref {book} {ch}:{vlo}-{vhi}  chars={len(ref_concat)} ſ={ref_s}\n")

    rows = []
    # existing diplomatic OCR reference point
    exist = glob.glob(f"sources/our-ocr-diplomatic/{ocr_dir}/*_{pidx:04d}.json")
    if exist:
        el = json.load(open(exist[0]))["lines"]  # raw lines incl. margin (no image to surya-filter existing)
        r, s = concat_ratio(el, ref_concat)
        rows.append(("existing-OCR", "n/a", "raw-lines", r, s))

    pdf = rl.ocrdir_to_pdf()[ocr_dir]["pdf"]
    doc = fitz.open(pdf)
    for dpi in (150, 300):
        pix = doc.load_page(pidx).get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
        base = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        regions = R.surya_regions(base)
        body = R.pick_body_regions(regions)
        for binm in ("none", "otsu", "sauvola"):
            g = binarize(base, binm)
            klines = kraken_lines_on(g)
            slines = R.surya_body_lines(klines, body)
            r, s = concat_ratio(slines, ref_concat)
            rows.append((f"reichenau", f"{dpi}dpi", binm, r, s))
            print(f"  {dpi}dpi {binm:<8} lines={len(klines):>3} body={len(slines):>3} concat={r:.4f} ſ={s}/{ref_s}", flush=True)

    rows.sort(key=lambda x: -x[3])
    print("\n=== ranked (alignment-free concat identity) ===")
    print(f"{'engine':<12}{'dpi':<8}{'binar':<9}{'concat':>8}{'ſ':>6}")
    for eng, dpi, binm, r, s in rows:
        print(f"{eng:<12}{dpi:<8}{binm:<9}{r:>8.4f}{s:>6}")
    best = rows[0]
    print(f"\nBEST: {best[0]} {best[1]} {best[2]} -> {best[3]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
