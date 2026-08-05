"""rung1_reocr.py — RUNG 1 of the re-OCR ladder: layout-aware re-OCR of a diagnosed locus.

This is the load-bearing half of the P3 re-OCR loop that v6–v9 skipped: after rung-0 visual
sign-off names a locus as a layout/segmentation failure, this actually RE-RUNS the OCR with
kraken baseline layout analysis (blla) — which types regions and computes reading order — and
recognizes the body with an archaic-faithful MLX recognizer (reichenau_lat / catmus-print).

Step 1 (this version): run kraken segment+recognize on a page raster and dump the structured
line/region output so the segmentation quality is INSPECTABLE before we trust it. Body-vs-margin
is classified by x-centre against the page so we can see whether kraken separates the marginalia,
running header, and verse-number rail that the rung-0 diagnosis flagged.

Usage:
    ocr-venv/bin/python ocr-spike/rung1_reocr.py <page.png> [--model models/reichenau_lat.mlmodel] [--device cpu]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = HERE / "models" / "reichenau_lat.mlmodel"


def main() -> int:
    ap = argparse.ArgumentParser(description="Rung-1 layout-aware re-OCR (kraken)")
    ap.add_argument("page", help="page raster PNG")
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--device", default="cpu", help="cpu | mps")
    ap.add_argument("--out", default=None, help="write structured JSON here")
    args = ap.parse_args()

    from kraken import blla, rpred
    from kraken.lib import models

    t0 = time.perf_counter()
    rec = models.load_any(args.model, device=args.device)
    print(f"model loaded in {time.perf_counter()-t0:.1f}s", flush=True)

    im = Image.open(args.page).convert("L")
    W, H = im.size
    print(f"page {W}x{H}px", flush=True)

    t1 = time.perf_counter()
    seg = blla.segment(im, device=args.device)
    print(f"segmented in {time.perf_counter()-t1:.1f}s", flush=True)

    # region inventory (kraken types regions: text, title, etc.)
    regions = getattr(seg, "regions", {}) or {}
    print("=== REGIONS ===", flush=True)
    for rtype, rlist in regions.items():
        print(f"  {rtype}: {len(rlist)}", flush=True)

    seg_lines = getattr(seg, "lines", []) or []
    print(f"=== LINES: {len(seg_lines)} ===", flush=True)

    t2 = time.perf_counter()
    records = list(rpred.rpred(rec, im, seg))
    print(f"recognized {len(records)} lines in {time.perf_counter()-t2:.1f}s", flush=True)

    def bbox_of(r):
        # kraken ocr_record: try .line boundary, else bbox
        b = getattr(r, "line", None)
        boundary = None
        if isinstance(b, dict):
            boundary = b.get("boundary")
        boundary = boundary or getattr(r, "boundary", None)
        if boundary:
            xs = [p[0] for p in boundary]
            ys = [p[1] for p in boundary]
            return [min(xs), min(ys), max(xs), max(ys)]
        return None

    out_lines = []
    for r in records:
        txt = str(getattr(r, "prediction", "") or "")
        bb = bbox_of(r)
        xc = ((bb[0] + bb[2]) / 2 / W) if bb else None
        yc = ((bb[1] + bb[3]) / 2 / H) if bb else None
        out_lines.append({"text": txt, "bbox": bb, "x_center": xc, "y_center": yc})

    # crude body-vs-margin split by x-centre band (the CURRENT heuristic 0.11–0.88) so we can
    # SEE what a rung-1 region model would need to fix
    band = [0.11, 0.88]
    body = [l for l in out_lines if l["x_center"] is not None and band[0] <= l["x_center"] <= band[1]]
    margin = [l for l in out_lines if l["x_center"] is not None and not (band[0] <= l["x_center"] <= band[1])]
    print(f"=== x-band split: body~{len(body)}  margin~{len(margin)} ===", flush=True)
    print("--- first 20 lines (y-sorted): [x_center] text ---", flush=True)
    for l in sorted(out_lines, key=lambda z: (z["y_center"] if z["y_center"] is not None else 0))[:20]:
        xc = f"{l['x_center']:.2f}" if l["x_center"] is not None else " ?? "
        print(f"  [{xc}] {l['text'][:90]}", flush=True)

    if args.out:
        Path(args.out).write_text(json.dumps(
            {"page": args.page, "size": [W, H], "n_lines": len(out_lines),
             "regions": {k: len(v) for k, v in regions.items()},
             "lines": out_lines}, indent=1, ensure_ascii=False))
        print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
