#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_holdout_prep.py — build a held-out training split for HONEST generalization measurement (P2).

Excludes ALL lines from the held-out gold pages from training, so those pages can be scored as genuinely
UNSEEN pages (Principle #1: prove the recognizer works on pages it never trained on). Rebuilds train/val
arrows from the remaining line-crops via `ketos compile`. Output: dr_train_ho.arrow / dr_val_ho.arrow.
"""
from __future__ import annotations
import json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / ".rung2-data"
KETOS = str(HERE.parent / "ocr-venv" / "bin" / "ketos")

# spans OT-clean / OT-hard / NT — a real cross-page, cross-volume generalization test
HELDOUT_SLUGS = {"scripture-genesis-24", "scripture-psalms-118", "scripture-2john"}


def main():
    man = json.loads((DATA / "_manifest.json").read_text())
    train_ids = [m["id"] for m in man if m["slug"] not in HELDOUT_SLUGS]
    held_ids = [m["id"] for m in man if m["slug"] in HELDOUT_SLUGS]
    print(f"held out {len(held_ids)} lines from {sorted(HELDOUT_SLUGS)}; {len(train_ids)} remain for training")

    pngs = [DATA / f"line_{i:04d}.png" for i in train_ids]
    missing = [p for p in pngs if not p.exists()]
    if missing:
        print(f"ERROR: {len(missing)} missing pngs, e.g. {missing[0]}"); return 1

    # fresh 85/15 train/val split of the remaining lines (strided, deterministic)
    k = max(1, round(len(pngs) * 0.15))
    stride = max(1, len(pngs) // k)
    val = pngs[::stride][:k]
    vset = set(val)
    train = [p for p in pngs if p not in vset]
    print(f"split: {len(train)} train / {len(val)} val")

    for arrow, imgs, lbl in ((DATA / "dr_train_ho.arrow", train, "train"),
                             (DATA / "dr_val_ho.arrow", val, "val")):
        if arrow.exists():
            arrow.unlink()
        print(f"compiling {len(imgs)} {lbl} lines → {arrow.name} …", flush=True)
        rc = subprocess.run([KETOS, "compile", "-f", "path", "--force-type", "bbox",
                             "-o", str(arrow)] + [str(p) for p in imgs], cwd=str(HERE),
                            capture_output=True, text=True)
        if rc.returncode != 0:
            print(f"ketos compile ({lbl}) failed:\n{rc.stderr[-1500:]}"); return rc.returncode
    print("done → dr_train_ho.arrow / dr_val_ho.arrow")
    # persist the training manifest (slugs actually trained on) for the eval harness
    (DATA / "_manifest-ho.json").write_text(json.dumps(
        [m for m in man if m["slug"] not in HELDOUT_SLUGS], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
