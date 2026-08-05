#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""page_cache.py — dump `reocr_core.reocr_page` results for the gold pages to `.page-cache/<slug>.json`.

Kraken segmentation + recognition costs ~10s/page and does NOT depend on any downstream geometry, scoring or
routing choice. Caching it turns every geometry experiment (column estimators, region grouping, apparatus
filters, containment sweeps) from a 2-minute run into an instant one, which is what made the 2026-07-26
crop-geometry investigation practical — most of its questions were answered with no model call at all.

`r3_variance.py` reads this cache when present and falls back to a live `reocr_page` when absent, so deleting
`.page-cache/` only costs time, never correctness.

Usage: ../ocr-venv/bin/python page_cache.py [--force] [slug ...]
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import reocr_core as core                # noqa: E402
from gate_calibrate import LOCI          # noqa: E402

OUT = HERE / ".page-cache"
GT = HERE / "ground-truth"


def build(slug: str) -> dict | None:
    gt = json.loads((GT / f"{slug}.json").read_text())
    od, pi = gt.get("ocr_dir"), gt.get("page_index")
    if od is None:
        return None
    r = core.reocr_page(od, pi, want_base=False, want_r1=False)
    return {"slug": slug, "ocr_dir": od, "page_index": pi, "page_px": r["page_px"], "r2_body": r["r2_body"],
            "lines": [{"text": l.get("text"), "role": l.get("role"), "conf": l.get("conf"),
                       "nchars": l.get("nchars"), "bbox": l.get("bbox")} for l in r["lines"]]}


def main() -> int:
    args = sys.argv[1:]
    force = "--force" in args
    slugs = [a for a in args if not a.startswith("--")] or sorted(LOCI)
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    for slug in slugs:
        ck = OUT / f"{slug}.json"
        if ck.exists() and not force:
            print(f"[skip] {slug}")
            continue
        d = build(slug)
        if d is None:
            print(f"[none] {slug} (no ocr_dir)")
            continue
        ck.write_text(json.dumps(d, ensure_ascii=False))
        print(f"[ok  ] {slug} lines={len(d['lines'])} px={tuple(d['page_px'])} ({time.time()-t0:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
