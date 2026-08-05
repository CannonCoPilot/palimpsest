#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ocr_complete_volume.py — OCR the pages of an admitted volume that were never OCR'd (2026-07-27).

THE DEFECT. `tome_map_audit` found `archive-holiebible-ot1` holds 1160 jp2 pages and 780 OCR files, stopping
dead at page 779: **380 contiguous pages — a third of S9's first Old Testament volume — were never OCR'd.**
A contiguous tail is the signature of a run that died and was never resumed, and nothing downstream reported
it because a page that was never OCR'd simply is not in any denominator: it cannot be addressed, localized,
scored, or flagged. It is invisible rather than failing.

Recognition is `reocr_core.reocr_page` — the same preprocess -> kraken blla segmentation -> reichenau_lat
(ſ-faithful) path that produced the rest of the corpus — and the output is written in the SAME on-disk shape
the corpus already uses ({page, lines:[{bbox, text}]}), so `stored_page`, the addressing and the localizer
consume it with no special case.

Resumable by construction: a page whose json already exists is skipped, so an interrupted run costs only the
page it was on. Usage: ocr-venv/bin/python ocr-spike/ocr_complete_volume.py <ocr_dir> [--limit N]
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jp2_page                       # noqa: E402
import reocr_core as core             # noqa: E402
import witness_inventory as WI        # noqa: E402

_NUM = re.compile(r"_(\d{4})$")


def missing_pages(ocr_dir: str) -> tuple[list, str]:
    """Page indices present as jp2 but absent from the OCR corpus, plus the stem pattern to write."""
    entry = jp2_page.OCR_DIR_TO_JP2.get(ocr_dir)
    if not entry:
        raise KeyError(f"{ocr_dir} has no jp2 mapping — cannot complete it")
    jp2 = sorted(int(m.group(1)) for p in glob.glob(str(jp2_page.SCANS / entry[1] / "*.jp2"))
                 if (m := _NUM.search(Path(p).stem)))
    have = {int(m.group(1)) for p in glob.glob(str(core.BASE_OCR_ROOT / ocr_dir / "*.json"))
            if (m := _NUM.search(Path(p).stem))}
    existing = sorted(glob.glob(str(core.BASE_OCR_ROOT / ocr_dir / "*.json")))
    stem = _NUM.sub("", Path(existing[0]).stem) if existing else Path(entry[1]).name.replace("_jp2", "")
    off = jp2_page.JP2_INDEX_OFFSET.get(ocr_dir, 0)
    return [p - off for p in jp2 if (p - off) not in have], stem


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("ocr_dir")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    if a.ocr_dir not in WI.admitted_ocr_dirs():
        raise SystemExit(f"{a.ocr_dir} is not an admitted witness volume (witness_inventory)")

    todo, stem = missing_pages(a.ocr_dir)
    if a.limit:
        todo = todo[:a.limit]
    out_dir = core.BASE_OCR_ROOT / a.ocr_dir
    print(f"{a.ocr_dir}: {len(todo)} pages to OCR (stem '{stem}_NNNN'), writing to {out_dir}", flush=True)
    t0, done, failed = time.time(), 0, []
    for pi in todo:
        target = out_dir / f"{stem}_{pi:04d}.json"
        if target.exists():
            continue
        try:
            r = core.reocr_page(a.ocr_dir, pi, want_base=False, want_r1=False)
            # Same shape as the rest of the corpus: page label + per-line bbox/text. Roles are NOT stored —
            # they are recomputed from geometry at read time, exactly as for the pages already on disk.
            target.write_text(json.dumps(
                {"page": f"{stem}_{pi:04d}",
                 "lines": [{"bbox": list(l["bbox"]) if l.get("bbox") else None, "text": l.get("text", "")}
                           for l in r["lines"] if l.get("bbox")]},
                ensure_ascii=False))
            done += 1
        except Exception as e:                                   # noqa: BLE001
            failed.append((pi, f"{type(e).__name__}: {e}"))
        if done and done % 25 == 0:
            el = time.time() - t0
            print(f"  {done}/{len(todo)} pages · {el:.0f}s · {el/max(1,done):.1f}s/page · "
                  f"{len(failed)} failed", flush=True)
    print(f"\n{a.ocr_dir}: wrote {done}, failed {len(failed)}, {time.time()-t0:.0f}s")
    for pi, why in failed[:10]:
        print(f"   FAILED p{pi}: {why}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
