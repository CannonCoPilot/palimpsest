#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""score_engines.py — fair PAGE-LEVEL Rung-2 comparison: Kraken fine-tuned vs Calamari from-scratch.

Both engines see the SAME line segmentation (kraken blla.segment on the SAME preprocessed page) and each
recognizes via its NATIVE path — kraken `rpred` on the page (internal height-normalized extraction),
calamari-predict on the extracted line crops (calamari is line-native). This isolates the recognizer:
identical segmentation, each engine preprocessing the same lines per its own training. Metric is the
grain-correct one from reocr_pipeline (page content edit_ratio over fold_archaic + ~20-word window pass-rate
+ the mandatory ſ-count companion check). NFC, NO dictionary/LM — ſ surface-safe. Calamari runs in its own
venv via subprocess with TF_USE_LEGACY_KERAS=1 + PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python (both
mandatory: they patch Keras-3 and protobuf-4 breakage in calamari 1.0.7).

Run: ocr-venv/bin/python ocr-spike/score_engines.py <slug> [<slug>...] \
       [--kraken-model ocr-spike/models/reichenau_dr.mlmodel] \
       [--calamari-ckpt ocr-spike/models/calamari-dr/dr_best.ckpt]
"""
from __future__ import annotations
import sys, os, argparse, subprocess, tempfile, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reocr_pipeline import score, gold_page_text, load_page, preprocess, existing_ocr, _norm, BASE_MODEL, _vote
from kraken import blla, rpred
from kraken.lib.segmentation import extract_polygons
from kraken.lib import models as kmodels

PROJ = HERE.parent
CAL_PREDICT = PROJ / "calamari-venv" / "bin" / "calamari-predict"
CAL_ENV = {"TF_USE_LEGACY_KERAS": "1", "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python"}
KR2_DEFAULT = HERE / "models" / "reichenau_dr.mlmodel"
CAL_DEFAULT = HERE / "models" / "calamari-dr" / "dr_best.ckpt"

_KM: dict = {}
def _km(p):
    p = str(p)
    if p not in _KM:
        _KM[p] = kmodels.load_any(p)
    return _KM[p]

def kraken_page(model, pim, seg):
    """Kraken native full-page recognition (rpred extracts + height-normalizes each line internally)."""
    return _norm(" ".join(str(r) for r in rpred.rpred(_km(model), pim, seg)))

def calamari_page(ckpt, crops):
    """Calamari native line recognition on the SAME extracted crops (calamari is line-input by design)."""
    if not crops:
        return ""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for i, c in enumerate(crops):
            c.convert("L").save(td / f"line_{i:04d}.png")
        pngs = [str(td / f"line_{i:04d}.png") for i in range(len(crops))]
        env = {**os.environ, **CAL_ENV}
        r = subprocess.run([str(CAL_PREDICT), "--checkpoint", str(ckpt), "--files", *pngs,
                            "--dataset", "FILE", "--output_dir", str(td), "--no_progress_bars"],
                           env=env, capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write((r.stderr or "")[-1800:] + "\n")
            raise RuntimeError(f"calamari-predict failed (rc={r.returncode})")
        out = []
        for i in range(len(crops)):
            pf = td / f"line_{i:04d}.pred.txt"
            out.append(pf.read_text(encoding="utf-8").strip() if pf.exists() else "")
        return _norm(" ".join(out))

def _fmt(label, s):
    return (f"  {label:20} {s['content']:>8.4f} {s['surface']:>8.4f} "
            f"{int(s['win_pass']*100):>4}% {str(s['s_hyp'])+'/'+str(s['s_gold']):>9}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--kraken-model", default=str(KR2_DEFAULT))
    ap.add_argument("--calamari-ckpt", default=str(CAL_DEFAULT))
    ap.add_argument("--vote", action="store_true", help="also report R2.5 within-image vote (base+winner)")
    a = ap.parse_args()
    if not Path(a.kraken_model).exists():
        print(f"missing kraken model {a.kraken_model}", file=sys.stderr); return 1
    # calamari stores <ckpt>.json + <ckpt>.h5 (no bare <ckpt> file); predict takes the prefix
    if not (Path(a.calamari_ckpt).exists() or Path(str(a.calamari_ckpt) + ".json").exists()):
        print(f"missing calamari ckpt {a.calamari_ckpt}(.json/.h5)", file=sys.stderr); return 1

    for slug in a.slugs:
        gold = gold_page_text(slug)
        im, d = load_page(slug)
        pim = preprocess(im)
        print(f"\n=== {slug}  ({d['ocr_dir']} p{d['page_index']}, {pim.width}x{pim.height}px, "
              f"gold {len(gold)} chars, {gold.count('ſ')} ſ) ===")
        if not gold.strip():
            print("  (no gold body text — skipped)"); continue
        seg = blla.segment(pim)
        crops = [ln for ln, _ in extract_polygons(pim, seg, legacy=False)]
        r1_txt = kraken_page(BASE_MODEL, pim, seg)
        kr2_txt = kraken_page(a.kraken_model, pim, seg)
        cr2_txt = calamari_page(a.calamari_ckpt, crops)
        base = score(existing_ocr(slug, d), gold)
        r1 = score(r1_txt, gold)
        kr2 = score(kr2_txt, gold)
        cr2 = score(cr2_txt, gold)
        print(f"  {'rung / engine':20} {'content':>8} {'surface':>8} {'win%':>5} {'ſ h/g':>9}   ({len(crops)} lines)")
        print("  " + "-" * 62)
        print(_fmt("base (scan OCR)", base))
        print(_fmt("R1 base-recog", r1))
        print(_fmt("R2 KRAKEN-ft", kr2))
        print(_fmt("R2 CALAMARI", cr2))
        if a.vote:
            # R2.5 within-image vote between the two engines' R2 outputs (surface-safe, no LM)
            print(_fmt("R2.5 K+C vote", score(_vote(kr2_txt, cr2_txt, gold), gold)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
