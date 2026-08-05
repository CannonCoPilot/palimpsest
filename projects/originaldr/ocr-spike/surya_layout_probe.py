"""surya_layout_probe.py — rung-0 gate for Surya: does it type early-modern scripture pages?

Runs Surya layout detection on diagnosed diag PNGs and prints each region's label +
normalized bbox + reading position, so Jarvis can SEE whether it separates
body / Page-header / Footnote / Page-footer / marginalia before the pipeline trusts it.

Usage: ocr-venv/bin/python ocr-spike/surya_layout_probe.py <page.png> [<page2.png> ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from surya.fast_layout import FastLayoutPredictor


def main() -> int:
    pages = [Path(p) for p in sys.argv[1:]]
    if not pages:
        print("no pages given", file=sys.stderr)
        return 2
    predictor = FastLayoutPredictor()
    print("FastLayoutPredictor ready", flush=True)

    for pg in pages:
        im = Image.open(str(pg)).convert("RGB")
        W, H = im.size
        res = predictor([im])[0]
        boxes = sorted(res.bboxes, key=lambda b: (round(b.bbox[1]), b.bbox[0]))
        print(f"\n=== {pg.name}  ({W}x{H})  {len(boxes)} regions ===", flush=True)
        print(f"{'label':<16}{'xc':>6}{'yc':>6}{'x0':>6}{'y0':>6}{'x1':>6}{'y1':>6}{'pos':>5}", flush=True)
        for b in boxes:
            x0, y0, x1, y1 = b.bbox
            xc = (x0 + x1) / 2 / W
            yc = (y0 + y1) / 2 / H
            pos = getattr(b, "position", "?")
            print(f"{b.label:<16}{xc:>6.2f}{yc:>6.2f}{x0/W:>6.2f}{y0/H:>6.2f}{x1/W:>6.2f}{y1/H:>6.2f}{str(pos):>5}",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
