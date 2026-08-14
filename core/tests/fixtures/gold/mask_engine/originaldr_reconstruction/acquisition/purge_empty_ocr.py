#!/usr/bin/env python3
"""Purge zero-line OCR page caches so a hardened re-run can retry them.

Context: the earlier 10-worker OCR runs thrashed memory (Sir's rein-in), OOM-crashing
kraken segmentation on ~28% of pages. The old pipeline wrote an empty ``{"lines": []}``
for each crash, and the resume logic (skip-if-json-exists) then cached those empties
permanently. ocr_pipeline.py is now hardened to never cache a failed page, but the
already-written empties must be deleted so the re-run re-OCRs them.

A genuinely blank leaf also yields ``{"lines": []}``; deleting it is harmless — the
re-run simply re-confirms it empty once (segmentation on a blank page is cheap). So the
safe, self-correcting criterion is: delete every 0-line cache, then re-run.

Dry-run by default. Pass --apply to actually delete.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# R11.4 -- this reached the dead pre-2633cbb tree by RELATIVE TRAVERSAL rather than by
# naming the root, which is why R9.6's sweep (written against modules that RESTATE the
# root) never saw it. A search shaped by the fix's vocabulary finds only what shares it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project_root as pr  # noqa: E402

OUT_ROOT = pr.DIPL_ROOT


def page_line_count(path: Path) -> int | None:
    """Return the number of OCR lines in a page cache, or None if it is unreadable."""
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    lines = obj.get("lines") if isinstance(obj, dict) else None
    return len(lines) if isinstance(lines, list) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="delete the empty caches (default: dry-run, list only)")
    ap.add_argument("--root", type=Path, default=OUT_ROOT,
                    help="our-ocr-diplomatic root (default: the scratch source dir)")
    args = ap.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}")
        return 2

    empties: list[Path] = []
    unreadable: list[Path] = []
    total = 0
    per_line: dict[str, int] = {}
    for line_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for cache in line_dir.glob("*.json"):
            if cache.name.startswith("_manifest"):
                continue
            total += 1
            n = page_line_count(cache)
            if n is None:
                unreadable.append(cache)
            elif n == 0:
                empties.append(cache)
                per_line[line_dir.name] = per_line.get(line_dir.name, 0) + 1

    print(f"scanned {total} page caches under {root.name}/")
    for line, n in sorted(per_line.items()):
        print(f"  {line}: {n} empty")
    print(f"empty (0-line): {len(empties)}   unreadable: {len(unreadable)}")
    for u in unreadable:
        print(f"  UNREADABLE (also purge): {u.name}")

    to_delete = empties + unreadable
    if not to_delete:
        print("nothing to purge.")
        return 0

    if not args.apply:
        print(f"\nDRY-RUN — would delete {len(to_delete)} caches. Re-run with --apply to delete.")
        return 0

    for p in to_delete:
        p.unlink()
    print(f"\nDELETED {len(to_delete)} caches. Re-run ocr_pipeline.py (hardened) to backfill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
