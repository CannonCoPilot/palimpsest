#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_s06_jpg.py — re-acquire S06 as JPEG, one leaf at a time, from archive.org's zip-member endpoint.

WHY. `Douay-Rheims-1610-Bible_jp2.zip` produced unreadable JP2s, and the per-file `.jp2` links return files
that will not decode either. The endpoint that DOES work asks archive.org to transcode the zip member on the
fly and hand back a JPEG:

    https://archive.org/download/<ITEM>/<ZIP>/<MEMBER>&ext=jpg

Confirmed 2026-08-03: leaf 0055 returns `200 image/jpeg`, 1,670,876 bytes. This script walks 0000-2871.

THE FAILURE MODE THIS GUARDS AGAINST. A 200 response is not an image. archive.org serves HTML error pages,
rate-limit notices and zero-length bodies with a 200 and sometimes with `image/jpeg` in the header, and a
directory of 2,872 files where nine are HTML is indistinguishable from a good directory until a training run
fails three weeks later on a stratified sample that happens to include one. So every file is verified by its
MAGIC BYTES (`\\xff\\xd8\\xff` in, `\\xff\\xd9` out) and a minimum size before it is allowed to keep its name;
anything that fails is deleted and recorded in the failure ledger. **A leaf that cannot be verified is a
MISSING leaf, loudly, never a file of the right name with the wrong content.**

Resumable: an already-verified file is skipped, so re-running after an interruption costs one stat per leaf.

Usage:
    ../ocr-venv/bin/python fetch_s06_jpg.py                    # all 2872 leaves
    ../ocr-venv/bin/python fetch_s06_jpg.py --start 0 --end 99 # a range
    ../ocr-venv/bin/python fetch_s06_jpg.py --verify-only      # re-verify what is on disk, download nothing
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ITEM = "1610A.d.DouayOldTestament1582A.d.RheimsNewTestament_176"
ZIP = "Douay-Rheims-1610-Bible_jp2.zip"
MEMBER = "Douay-Rheims-1610-Bible_jp2%2FDouay-Rheims-1610-Bible_{n:04d}.jp2"
URL = f"https://archive.org/download/{ITEM}/{ZIP}/{MEMBER}&ext=jpg"

DEST = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/DouayRheims_DR"
            "/sources/scans/S06_1610-facsimile-whole/Douay-Rheims-1610-Bible_jpg")
LEDGER = DEST.parent / "fetch-s06-jpg-ledger.json"

N_LEAVES = 2872          # 0000-2871 inclusive, per the URLs Sir confirmed
MIN_BYTES = 40_000       # a real facsimile leaf at this resolution is >1MB; 40KB is a generous floor
WORKERS = 4              # archive.org is a shared good; four streams is polite and is not the bottleneck
RETRIES = 3
UA = "originaldr-reocr/1.0 (palimpsest research; contact via archive.org account)"


def verify(p: Path) -> tuple[bool, str]:
    """Magic bytes in, magic bytes out, and a size floor. Returns (ok, reason-if-not)."""
    try:
        if not p.exists():
            return False, "absent"
        size = p.stat().st_size
        if size < MIN_BYTES:
            return False, f"too small ({size}B)"
        with p.open("rb") as fh:
            head = fh.read(3)
            fh.seek(-2, 2)
            tail = fh.read(2)
        if head != b"\xff\xd8\xff":
            return False, f"not JPEG (head {head!r})"
        if tail != b"\xff\xd9":
            return False, "truncated (no EOI marker)"
        return True, ""
    except Exception as e:                                    # noqa: BLE001 — any read failure is a failure
        return False, f"unreadable: {e}"


def fetch_one(n: int) -> tuple[int, bool, str]:
    out = DEST / f"S06_{n:04d}.jpg"
    ok, _ = verify(out)
    if ok:
        return n, True, "cached"
    url = URL.format(n=n)
    last = ""
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            tmp = out.with_suffix(".part")
            tmp.write_bytes(body)
            ok, why = verify(tmp)
            if ok:
                tmp.replace(out)
                return n, True, f"{len(body)}B"
            tmp.unlink(missing_ok=True)
            last = why
        except (urllib.error.URLError, OSError) as e:          # transport, not content
            last = str(e)
        time.sleep(2 * (attempt + 1))
    return n, False, last or "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=N_LEAVES - 1)
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args(argv)
    DEST.mkdir(parents=True, exist_ok=True)
    leaves = list(range(a.start, a.end + 1))

    if a.verify_only:
        bad = [(n, why) for n in leaves for ok, why in [verify(DEST / f"S06_{n:04d}.jpg")] if not ok]
        print(f"verified {len(leaves) - len(bad)}/{len(leaves)}; {len(bad)} NOT USABLE")
        for n, why in bad[:40]:
            print(f"  {n:04d}  {why}")
        return 1 if bad else 0

    done, failed, t0 = 0, [], time.time()
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for n, ok, note in ex.map(fetch_one, leaves):
            done += 1
            if not ok:
                failed.append({"leaf": n, "why": note})
            if done % 50 == 0 or done == len(leaves):
                rate = done / max(time.time() - t0, 1e-9)
                print(f"  {done}/{len(leaves)}  {rate:.1f}/s  failures {len(failed)}", flush=True)

    LEDGER.write_text(json.dumps({"requested": len(leaves), "failed": failed,
                                  "dest": str(DEST)}, indent=1))
    print(f"\n{len(leaves) - len(failed)}/{len(leaves)} usable JPEGs in {DEST}")
    if failed:
        # NOT a warning to be scrolled past. Downstream stages must not run on a partial corpus believing
        # it whole, so this exits non-zero and names the leaves.
        print(f"FAILED {len(failed)} leaves — these are MISSING, not degraded. Ledger: {LEDGER}")
        for f in failed[:40]:
            print(f"  {f['leaf']:04d}  {f['why']}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
