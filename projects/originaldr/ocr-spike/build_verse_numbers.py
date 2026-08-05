#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_verse_numbers.py — recover printed verse numbers for the gold pages and CACHE them.

The gutter reads cost one olmOCR call per verse opening, so they are cached to `.verse-numbers/<slug>.json`
exactly as `.page-cache/` caches kraken: a recovered number cannot change unless the page image does, so every
downstream experiment should pay for it once. Usage: ../ocr-venv/bin/python build_verse_numbers.py [--force]
"""
from __future__ import annotations
import json, sys, time, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, ".")
from pathlib import Path
import verse_numbers, verse_seg as VS
from gate_calibrate import LOCI, gold_by_chapter, cached_page

OUT = Path(".verse-numbers"); OUT.mkdir(exist_ok=True)
GT = Path("ground-truth")

def main():
    force = "--force" in sys.argv
    slugs = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(LOCI)
    t0 = time.time()
    for slug in slugs:
        f = OUT / f"{slug}.json"
        if f.exists() and not force:
            print(f"[skip] {slug}"); continue
        book = LOCI[slug]
        gt = json.loads((GT / f"{slug}.json").read_text())
        r = cached_page(slug, gt.get("ocr_dir"), gt.get("page_index"))
        chs = sorted(gold_by_chapter(gt))
        exp = sorted({v for ch in chs for v in VS.chapter_verses(book, ch, VS.JANVIER)})
        try:
            out = verse_numbers.recover(r, gt.get("ocr_dir"), gt.get("page_index"), expected=exp)
        except Exception as e:
            print(f"[ERR ] {slug}: {type(e).__name__}: {e}"); continue
        anc = verse_numbers.anchors(r, out)
        f.write_text(json.dumps({"slug": slug, "anchors": {str(k): v for k, v in anc.items()},
                                 "n_crops": out["n_crops"], "n_read": out["n_read"],
                                 "n_accepted": out["n_accepted"], "notes": out["notes"]},
                                ensure_ascii=False, indent=2))
        print(f"[done] {slug}: crops={out['n_crops']} read={out['n_read']} ACCEPTED={out['n_accepted']} "
              f"({time.time()-t0:.0f}s)", flush=True)
    try:
        import reocr_r3; reocr_r3.shutdown_mlx()
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
