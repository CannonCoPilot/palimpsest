#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_chapter_compile.py — compile `rung2_chapter_pairs.py`'s output into kraken arrows (item 2, 2026-07-29).

Splits are taken from the harvest manifest, which assigns whole LEAVES to train or val — never lines, because
lines off one leaf share typeface, inking, skew and scan geometry and would leak a near-duplicate into val.

The existing `.rung2-data/dr_train.arrow` (264) and `dr_val.arrow` (47) are LEFT ALONE and passed alongside
these at training time, so the two harvests compose without recompiling the old one (and without any chance of
quietly reshuffling the split the current `reichenau_dr` was measured against).

Usage: ../ocr-venv/bin/python rung2_chapter_compile.py [--data .rung2-chapters]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KETOS = str(HERE.parent / "ocr-venv" / "bin" / "ketos")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".rung2-chapters")
    a = ap.parse_args()
    data = HERE / a.data
    man = json.loads((data / "_manifest.json").read_text())
    groups = {"train": [], "val": []}
    for m in man["lines"]:
        png = data / f"{m['stem']}.png"
        gt = data / f"{m['stem']}.gt.txt"
        if png.exists() and gt.exists():
            groups[m["split"]].append(png)
    print(f"manifest {len(man['lines'])} lines -> {len(groups['train'])} train / {len(groups['val'])} val "
          f"(leaf-level split over {man['n_leaves']} leaves)")
    for lbl, imgs in groups.items():
        out = data / f"dr_ch_{lbl}.arrow"
        if out.exists():
            out.unlink()
        if not imgs:
            print(f"  ! no {lbl} images — skipped")
            continue
        print(f"  compiling {len(imgs)} {lbl} lines -> {out.name} …", flush=True)
        rc = subprocess.run([KETOS, "compile", "-f", "path", "--force-type", "bbox", "-o", str(out)]
                            + [str(p) for p in imgs], cwd=str(HERE), capture_output=True, text=True)
        if rc.returncode != 0:
            print(f"  ketos compile ({lbl}) FAILED:\n{rc.stderr[-1500:]}", file=sys.stderr)
            return rc.returncode
        print(f"  ok: {out.name} ({out.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
