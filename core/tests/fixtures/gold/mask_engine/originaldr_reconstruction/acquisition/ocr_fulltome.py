#!/usr/bin/env python3
"""Phase 0 · P0.4a — full-tome fresh OCR of the archive.org page scans ("our tesseract").

Per Sir's locked scope decision (FULL-TOME + images): fresh-OCR EVERY page of all six
archive.org jp2 scan sets with our own tesseract, producing an INDEPENDENT third OCR
witness to majority-fuse with the two archive.org OCR products (djvu.txt + hOCR) in
P0.4b. This axis is what lets the consensus corroborate — not just gap-fill — every
element, and it supplies archaic coverage for the OT books absent from s-dismas
(Gen→Wisdom) and odr-com (12 books): Ecclesiasticus + the prophets.

Design: deterministic + RESUMABLE. Each page's plain-text OCR is cached to
    sources/our-ocr/<alias>/<page-stem>.txt
and a page is skipped if its cache exists non-empty, so the job survives interruption
(and JICM clears) and simply resumes. jp2 pages are streamed out of the zip one at a
time (no bulk extraction) into a per-worker temp file. Output text is SCRATCH
(gitignored, regenerable from the sha-pinned zips); only this script + the final
our-ocr-manifest.json are tracked.

Run detached:  nohup .venv/bin/python <thisfile> >> <log> 2>&1 &
Progress:      tail -f the log; or read our-ocr-manifest.json when complete.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # R9.6
import project_root as pr  # noqa: E402  R9.6: one derived root

HERE = Path(__file__).resolve().parent
# repo root = .../palimpsest ; this file is 8 dirs deep under it
REPO = HERE.parents[6]
ARCHIVE = REPO / "imports/Scripture/Bibles/DouayRheims_DR/archive-org"
OUT_ROOT = pr.OCR_ROOT
MANIFEST = HERE / "our-ocr-manifest.json"

ALIASES = ["ot1-1609", "ot2-1610", "nt-1582",
           "holiebible-ot1", "holiebible-ot2", "newtestament"]

WORKERS = int(os.environ.get("OCR_WORKERS", "6"))
TESS = "/opt/homebrew/bin/tesseract"


def find_zip(alias: str) -> Path | None:
    d = ARCHIVE / alias
    if not d.is_dir():
        return None
    zips = sorted(d.glob("*_jp2.zip"))
    return zips[0] if zips else None


def ocr_page(zpath: Path, entry: str, out_path: Path) -> tuple[str, bool, str]:
    """OCR a single jp2 zip entry -> out_path (.txt). Returns (entry, ok, note)."""
    if out_path.exists() and out_path.stat().st_size > 0:
        return entry, True, "cached"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zpath) as zf:
            data = zf.read(entry)
        with tempfile.NamedTemporaryFile(suffix=".jp2", delete=False) as tf:
            tf.write(data)
            tmp = tf.name
        try:
            # tesseract writes <base>.txt; pass base without extension
            base = str(out_path.with_suffix(""))
            r = subprocess.run(
                [TESS, tmp, base, "--dpi", "300", "-l", "eng"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        finally:
            os.unlink(tmp)
        if r.returncode == 0 and out_path.exists():
            return entry, True, "ocr"
        return entry, False, f"rc={r.returncode}"
    except Exception as e:  # noqa: BLE001 — record and continue; one bad page must not kill the tome
        return entry, False, type(e).__name__


def process_alias(alias: str) -> dict:
    zpath = find_zip(alias)
    if zpath is None:
        return {"alias": alias, "error": "no jp2.zip", "pages": 0, "done": 0, "failed": 0}
    with zipfile.ZipFile(zpath) as zf:
        entries = sorted(n for n in zf.namelist() if n.lower().endswith(".jp2"))
    out_dir = OUT_ROOT / alias
    out_dir.mkdir(parents=True, exist_ok=True)

    def out_for(entry: str) -> Path:
        return out_dir / (Path(entry).stem + ".txt")

    todo = [(e, out_for(e)) for e in entries]
    done = failed = 0
    t0 = time.time()
    print(f"[{alias}] {len(todo)} pages · {WORKERS} workers · {zpath.name}", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(ocr_page, zpath, e, o): e for e, o in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            _entry, ok, _note = fut.result()
            if ok:
                done += 1
            else:
                failed += 1
            if i % 100 == 0 or i == len(todo):
                rate = i / max(1e-6, time.time() - t0)
                print(f"[{alias}] {i}/{len(todo)}  done={done} failed={failed} "
                      f"{rate:.1f} pg/s", flush=True)
    return {"alias": alias, "zip": zpath.name, "pages": len(entries),
            "done": done, "failed": failed, "seconds": round(time.time() - t0, 1)}


def main() -> int:
    only = sys.argv[1:] or ALIASES
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    results = []
    for alias in only:
        results.append(process_alias(alias))
        MANIFEST.write_text(json.dumps(
            {"status": "in_progress", "workers": WORKERS,
             "elapsed_s": round(time.time() - started, 1), "aliases": results},
            indent=2) + "\n")
    total_pages = sum(r["pages"] for r in results)
    total_done = sum(r["done"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    MANIFEST.write_text(json.dumps(
        {"status": "complete", "workers": WORKERS,
         "elapsed_s": round(time.time() - started, 1),
         "total_pages": total_pages, "total_done": total_done,
         "total_failed": total_failed, "out_root": str(OUT_ROOT), "aliases": results},
        indent=2) + "\n")
    print(f"\nDONE · {total_done}/{total_pages} pages OCR'd · {total_failed} failed · "
          f"{round(time.time() - started, 1)}s · manifest → {MANIFEST.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
