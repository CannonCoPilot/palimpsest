#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_finetune.py — fine-tune a per-typeface DR recognizer (Rung 2) from the reichenau_lat BASE on the
gold line-pairs produced by rung2_prepare.py. Transfer learning per the research (arXiv:1712.05586/2106.07881/
1809.05501/1807.02004): tens–hundreds of gold lines of the target print → CER toward ≤0.10, surface-preserving.

SURFACE SAFETY (non-negotiable): normalization is NFC (NOT NFKC — NFKC folds ſ→s = modernization). --resize both
EXTENDS reichenau's codec with DR-only glyphs (†, macrons, æ) while keeping the base's learned strokes. No
dictionary/language model is involved, so archaic spelling is preserved by construction.

Run: ocr-venv/bin/python ocr-spike/rung2_finetune.py [--data .rung2-data] [--epochs 50] [--device cpu]
Output: models/reichenau_dr_best.mlmodel (best-val checkpoint, symlinked/copied from the ketos output dir).
"""
from __future__ import annotations
import sys, subprocess, argparse, glob, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE = HERE / "models" / "reichenau_lat.mlmodel"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".rung2-data")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--min-epochs", type=int, default=8)
    ap.add_argument("--lag", type=int, default=5)
    ap.add_argument("--partition", type=float, default=0.85)
    ap.add_argument("--device", default="cpu")  # cpu is reliable; mps faster but kernel bugs on some ops
    ap.add_argument("--out", default="models/reichenau_dr")
    a = ap.parse_args()
    data = HERE / a.data
    pngs = sorted(glob.glob(str(data / "line_*.png")))
    if not pngs:
        print(f"no training pngs in {data} — run rung2_prepare.py first"); return 1
    outdir = HERE / a.out
    outdir.parent.mkdir(exist_ok=True)
    ketos = str(HERE.parent / "ocr-venv/bin/ketos")
    # explicit train/val split (kraken 7 binary train wants -t train.arrow -e eval.arrow; positional = path only)
    k = max(1, int(round(len(pngs) * (1 - a.partition))))
    val_png = pngs[::len(pngs)//k][:k] if k else []
    val_set = set(val_png)
    train_png = [p for p in pngs if p not in val_set]
    train_arrow, val_arrow = data / "dr_train.arrow", data / "dr_val.arrow"
    for arrow, imgs, lbl in ((train_arrow, train_png, "train"), (val_arrow, val_png, "val")):
        if arrow.exists():
            continue
        print(f"compiling {len(imgs)} {lbl} lines → {arrow.name} …", flush=True)
        rc = subprocess.run([ketos, "compile", "-f", "path", "--force-type", "bbox",
                             "-o", str(arrow)] + imgs, cwd=str(HERE))
        if rc.returncode != 0:
            print(f"ketos compile ({lbl}) failed"); return rc.returncode
    # -t/-e want a MANIFEST (text file listing dataset paths, one per line), not the arrow itself
    train_manifest = data / "train_manifest.txt"; train_manifest.write_text(str(train_arrow) + "\n")
    val_manifest = data / "val_manifest.txt"; val_manifest.write_text(str(val_arrow) + "\n")
    # fine-tune from the base
    cmd = [
        ketos, "-d", a.device, "train",
        "--load", str(BASE),
        "--format-type", "binary",
        "--resize", "both",              # extend codec with DR-only glyphs, keep base weights
        "-u", "NFC",                     # ſ-PRESERVING (NFKC would fold ſ→s — banned)
        "-o", str(outdir),
        "-q", "early", "--lag", str(a.lag),
        "--min-epochs", str(a.min_epochs), "-N", str(a.epochs),
        "-F", "1.0",
        "-t", str(train_manifest),
        "-e", str(val_manifest),
    ]
    print(f"fine-tuning from {BASE.name}: {len(train_png)} train / {len(val_png)} val lines (device={a.device}) …", flush=True)
    r = subprocess.run(cmd, cwd=str(HERE))
    if r.returncode != 0:
        print(f"ketos train exited {r.returncode}"); return r.returncode
    # pick the best checkpoint
    ckpts = sorted(glob.glob(str(outdir) + "*best*.mlmodel")) or sorted(glob.glob(str(outdir) + "*.mlmodel"))
    if ckpts:
        best = ckpts[-1]
        dest = HERE / "models" / "reichenau_dr_best.mlmodel"
        shutil.copy2(best, dest)
        print(f"\nBEST → {dest}  (from {Path(best).name})")
    else:
        print("no checkpoint found — inspect", outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
