#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_split_v2.py — build the train/val arrows for the item-2 R2 experiment (§13 Q38, 2026-07-29).

THE EXPERIMENT. Does adding the 2,188 previously-unharvested `matter-*` GT lines improve the recognizer's reading
of SCRIPTURE? Two training arms, one val set:

    arm A   scripture pairs only          (the historical composition, re-harvested)
    arm B   scripture + matter pairs      (the challenger)
    val     held-out SCRIPTURE GT FILES, whole — used by neither arm

WHY THE SPLIT IS BY GT **FILE** AND NOT BY LINE, and why the old `dr_val.arrow` is NOT reused. The v2 harvest
re-derives pairs from the same 16 scripture GT files the original 264/47 split came from, so any line-level split
would put the same GT LINE (a slightly different crop of the same ink) on both sides. Holding out whole files is
the only clean cut available here.

THE BIAS, STATED UP FRONT AND IN THE HONEST DIRECTION. The incumbent `reichenau_dr` was trained on 264 lines
drawn from ALL 16 scripture files, so the lines in our held-out files are probably IN its training set. That
inflates the incumbent on this val set, not the challenger. So a challenger WIN is trustworthy and a narrow
challenger loss is not conclusive — which is the right way round for a change we are considering adopting.

Usage: ../ocr-venv/bin/python rung2_split_v2.py [--data .rung2-data-v2] [--val-files 4]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
KETOS = str(HERE.parent / "ocr-venv" / "bin" / "ketos")


def compile_arrow(pngs: list[Path], out: Path) -> int:
    if out.exists():
        out.unlink()
    if not pngs:
        print(f"  ! no images for {out.name}")
        return 1
    print(f"  compiling {len(pngs)} lines -> {out.name} …", flush=True)
    rc = subprocess.run([KETOS, "compile", "-f", "path", "--force-type", "bbox", "-o", str(out)]
                        + [str(p) for p in pngs], cwd=str(HERE), capture_output=True, text=True)
    if rc.returncode != 0:
        print(f"  FAILED:\n{rc.stderr[-1200:]}", file=sys.stderr)
        return rc.returncode
    print(f"  ok ({out.stat().st_size/1e6:.1f} MB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".rung2-data-v2")
    ap.add_argument("--val-files", type=int, default=4, help="how many scripture GT files to hold out")
    a = ap.parse_args()
    d = HERE / a.data
    man = json.loads((d / "_manifest.json").read_text())
    by_slug: dict[str, list[dict]] = {}
    for m in man:
        by_slug.setdefault(m["slug"], []).append(m)
    scripture = sorted(s for s in by_slug if s.startswith("scripture-"))
    matter = sorted(s for s in by_slug if not s.startswith("scripture-"))
    # deterministic, strided hold-out so the choice is reproducible and spread across books rather than clustered
    step = max(1, len(scripture) // a.val_files)
    val_slugs = scripture[::step][:a.val_files]
    print(f"scripture files {len(scripture)}, matter files {len(matter)}")
    print(f"HELD OUT (val, used by neither arm): {val_slugs}")

    def pngs(slugs):
        out = []
        for s in slugs:
            for m in by_slug[s]:
                p = d / f"line_{m['id']:04d}.png"
                if p.exists() and (d / f"line_{m['id']:04d}.gt.txt").exists():
                    out.append(p)
        return out

    train_scripture = [s for s in scripture if s not in val_slugs]
    sets = {
        "v2_val_scripture": pngs(val_slugs),
        "v2_train_scripture": pngs(train_scripture),
        "v2_train_matter": pngs(matter),
    }
    for k, v in sets.items():
        print(f"  {k:<22} {len(v)} lines")
    counts = Counter("scripture" if m["slug"].startswith("scripture-") else "matter" for m in man)
    print(f"  (manifest totals: {dict(counts)})")
    rc = 0
    for k, v in sets.items():
        rc |= compile_arrow(v, d / f"{k}.arrow")
    print("\nARM A (scripture only):  --train-arrow v2_train_scripture.arrow --val-arrow v2_val_scripture.arrow")
    print("ARM B (scripture+matter): --train-arrow v2_train_scripture.arrow,v2_train_matter.arrow "
          "--val-arrow v2_val_scripture.arrow")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
