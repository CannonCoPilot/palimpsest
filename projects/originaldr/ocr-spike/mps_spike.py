#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""MPS-vs-CPU spike: is the M4 Max GPU a stable, memory-competitive, faster kraken runner?

Runs the FULL pipeline stage (baseline segmentation + reichenau recognition) on real
2x-upscaled archive pages, on one device, reporting per-page wall time, peak RSS, GPU
allocation, and a text sample (ſ must survive). Run once per device in its OWN process so
peak RSS is isolated:

    ocr-venv/bin/python mps_spike.py cpu
    ocr-venv/bin/python mps_spike.py mps
"""
from __future__ import annotations

import io
import resource
import sys
import time
import zipfile
from pathlib import Path

from PIL import Image

REPO = Path("/Users/nathanielcannon/Claude/Projects/palimpsest")
ARCHIVE = REPO / "imports/Scripture/Bibles/DouayRheims_DR/archive-org"
MODEL = REPO / "projects/originaldr/ocr-spike/models/reichenau_lat.mlmodel"
ALIAS = "ot1-1609"
WARMUP = 1
TIMED = 3
FIRST_PAGE = 200   # deep enough to be scripture text, not front matter

rss_gb = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 3)


def load_pages(n: int) -> list[Image.Image]:
    zp = sorted((ARCHIVE / ALIAS).glob("*_jp2.zip"))[0]
    out: list[Image.Image] = []
    with zipfile.ZipFile(zp) as zf:
        names = sorted(x for x in zf.namelist() if x.lower().endswith(".jp2"))
        for name in names[FIRST_PAGE:FIRST_PAGE + n]:
            im = Image.open(io.BytesIO(zf.read(name))).convert("L")
            im = im.resize((im.width * 2, im.height * 2), Image.Resampling.LANCZOS)
            out.append(im)
    return out


def main() -> int:
    device = sys.argv[1] if len(sys.argv) > 1 else "cpu"
    import torch
    from kraken import blla, rpred
    from kraken.lib import models

    def sync():
        if device == "mps":
            torch.mps.synchronize()

    t0 = time.perf_counter()
    rec = models.load_any(str(MODEL), device=device)
    print(f"[{device}] models loaded in {time.perf_counter()-t0:.1f}s  RSS={rss_gb():.2f}GB", flush=True)

    pages = load_pages(WARMUP + TIMED)
    print(f"[{device}] prepped {len(pages)} pages ({pages[0].size[0]}x{pages[0].size[1]}px)", flush=True)

    times: list[float] = []
    sample_text = ""
    for i, im in enumerate(pages):
        t = time.perf_counter()
        seg = blla.segment(im, device=device)
        preds = list(rpred.rpred(rec, im, seg))
        sync()
        dt = time.perf_counter() - t
        tag = "warmup" if i < WARMUP else f"timed[{i-WARMUP}]"
        if i >= WARMUP:
            times.append(dt)
        if i == WARMUP:
            sample_text = " ".join(p.prediction for p in preds[:8])
        print(f"[{device}] {tag}: {dt:.1f}s  lines={len(preds)}", flush=True)

    med = sorted(times)[len(times) // 2] if times else float("nan")
    gpu = ""
    if device == "mps":
        gpu = f"  GPU_driver_alloc={torch.mps.driver_allocated_memory()/(1024**3):.2f}GB"
    print(f"\n[{device}] === median {med:.1f}s/page  (~{1/med:.3f} pg/s single-stream)  "
          f"peakRSS={rss_gb():.2f}GB{gpu} ===", flush=True)
    print(f"[{device}] ſ in sample: {sample_text.count(chr(0x17f))}  | {sample_text[:120]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
