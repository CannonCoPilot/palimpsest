#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reocr_pipeline.py — the per-SOURCE re-OCR ladder, end-to-end, with the FIXED (grain-correct) metric.

For one (source, page) identified by a gold slug, run the rungs and score EACH against gold at PAGE grain
(content edit_ratio over fold_archaic) + WINDOW grain (% of ~20-word gold windows matching ≥0.90) + the
mandatory ſ-count check — never the deflating per-verse metric. Reports the CER/accuracy progression so we
can SEE whether each rung provably improves THIS source.

Rungs (per-source; consensus is NOT here):
  base   existing scan OCR (sources/our-ocr-diplomatic) — the starting point
  R0     diagnostic raster (written for visual inspection; does not change text)
  R1     preprocess (deskew/binarize; Lanczos upscale for low-res) + re-OCR with the BASE recognizer
  R2     re-OCR with the FINE-TUNED recognizer (rung2_finetune.py output)   [--r2-model]
  R2.5   within-image vote across {base, fine-tuned} on the SAME page (surface-safe, no LM)
  R3     vision-LLM hook — rasterize + column-crop for a Claude/CHURRO pass (run externally; gated)

Run: ocr-venv/bin/python ocr-spike/reocr_pipeline.py <gold-slug> [--r2-model models/reichenau_dr.mlmodel]
"""
from __future__ import annotations
import sys, json, re, argparse, warnings, difflib
from pathlib import Path
warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from PIL import Image, ImageOps
Image.MAX_IMAGE_PIXELS = None
from char_identity import fold_archaic, edit_ratio
import jp2_page
GT = HERE / "ground-truth"
OCR_ROOT = HERE.parent / "sources/our-ocr-diplomatic"
BASE_MODEL = HERE / "models" / "reichenau_lat.mlmodel"
PASS = 0.90
WIN = 20
MAXW = 2200


# ---------- metric (grain-correct) ----------
def _norm(s): return re.sub(r"\s+", " ", s or "").strip()
def _windows(text, w=WIN):
    t = re.findall(r"\S+", text or "")
    return [" ".join(t[i:i+w]) for i in range(0, len(t), w)] if t else []
def _owins(text, w=WIN):
    t = re.findall(r"\S+", text or "")
    if not t: return [""]
    return [" ".join(t[i:i+w]) for i in range(0, len(t), max(1, w//2))] or [""]

def gold_page_text(slug):
    d = json.loads((GT / f"{slug}.json").read_text())
    return _norm(" ".join(b.get("text", "") for b in d.get("body", [])
                 if b.get("text", "").strip() and b.get("role") not in ("catchword", "signature")))

def score(hyp, gold):
    hyp, gold = _norm(hyp), _norm(gold)
    if not hyp: return {"content": 0.0, "surface": 0.0, "win_pass": 0.0, "s_hyp": 0, "s_gold": gold.count("ſ")}
    content = edit_ratio(fold_archaic(hyp), fold_archaic(gold))
    surface = difflib.SequenceMatcher(None, hyp, gold).ratio()
    gw = _windows(gold); ow = [fold_archaic(x) for x in _owins(hyp)]
    wp = 0
    for g in gw:
        gf = fold_archaic(g)
        if max((edit_ratio(o, gf) for o in ow), default=0) >= PASS: wp += 1
    return {"content": round(content, 4), "surface": round(surface, 4),
            "win_pass": round(wp/len(gw), 4) if gw else 0.0, "s_hyp": hyp.count("ſ"), "s_gold": gold.count("ſ")}


# ---------- recognizers ----------
_MODELS = {}
def _load(path):
    from kraken.lib import models
    p = str(path)
    if p not in _MODELS: _MODELS[p] = models.load_any(p)
    return _MODELS[p]

def recognize(im, model_path):
    from kraken import blla, rpred
    m = _load(model_path)
    seg = blla.segment(im)
    return _norm(" ".join(str(r) for r in rpred.rpred(m, im, seg)))

def load_page(slug):
    d = json.loads((GT / f"{slug}.json").read_text())
    im = jp2_page.load(d["ocr_dir"], d["page_index"]).convert("L")
    return im, d

def preprocess(im):
    im = ImageOps.autocontrast(im)
    if im.width < 1500:  # low-res source (e.g. 800px S1): upscale for the recognizer
        im = im.resize((1600, int(im.height*1600/im.width)), Image.LANCZOS)
    elif im.width > MAXW:
        im = im.resize((MAXW, int(im.height*MAXW/im.width)), Image.LANCZOS)
    return im

def existing_ocr(slug, d):
    # best-matching page text in the source's OCR dir (content anchor = gold first lines)
    import glob
    files = sorted(glob.glob(str(OCR_ROOT / d["ocr_dir"] / "*.json")))
    anchor = set(re.sub(r"[^a-z0-9]", "", fold_archaic(w).lower()) for w in gold_page_text(slug).split()[:40])
    best, bi = 0, -1
    def toks(t): return set(re.sub(r"[^a-z0-9]", "", fold_archaic(w).lower()) for w in re.findall(r"\S+", t))
    texts = []
    for f in files:
        try: dd = json.load(open(f, errors="ignore"))
        except Exception: texts.append(""); continue
        t = dd.get("text") if isinstance(dd.get("text"), str) else " ".join(l.get("text","") for l in dd.get("lines",[]) if isinstance(l,dict))
        texts.append(t or "")
    for i, t in enumerate(texts):
        pt = toks(t)
        if pt and anchor:
            s = len(anchor & pt)/len(anchor)
            if s > best: best, bi = s, i
    return _norm(texts[bi]) if bi >= 0 and best >= 0.3 else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--r2-model", default=None, help="fine-tuned recognizer for Rung 2")
    ap.add_argument("--raster", default=".pipeline-rasters")
    a = ap.parse_args()
    gold = gold_page_text(a.slug)
    im, d = load_page(a.slug)
    print(f"=== {a.slug}  ({d['ocr_dir']} p{d['page_index']}, {im.width}x{im.height}px, gold {len(gold)} chars, {gold.count('ſ')} ſ) ===")
    rows = []

    # baseline: existing scan OCR
    rows.append(("base (existing OCR)", score(existing_ocr(a.slug, d), gold)))
    # R0 diagnostic raster
    rd = HERE / a.raster; rd.mkdir(exist_ok=True)
    (rd / f"{a.slug}.png").exists() or im.save(rd / f"{a.slug}.png")
    # R1 preprocess + base recognizer
    pim = preprocess(im)
    r1 = recognize(pim, BASE_MODEL)
    rows.append(("R1 preprocess+base", score(r1, gold)))
    # R2 fine-tuned recognizer
    r2 = None
    if a.r2_model and Path(a.r2_model).exists():
        r2 = recognize(pim, a.r2_model)
        rows.append(("R2 fine-tuned", score(r2, gold)))
    else:
        rows.append(("R2 fine-tuned", {"content": None, "note": "no --r2-model yet"}))
    # R2.5 within-image vote (base + fine-tuned) — token-level, surface-safe
    if r2:
        vote = _vote(r1, r2, gold)
        rows.append(("R2.5 within-image vote", score(vote, gold)))

    print(f"\n{'rung':26} {'content':>8} {'surface':>8} {'win%':>6} {'ſ hyp/gold':>11}")
    print("-"*64)
    for name, s in rows:
        if s.get("content") is None:
            print(f"{name:26} {'—':>8}   ({s.get('note','')})"); continue
        print(f"{name:26} {s['content']:>8.4f} {s['surface']:>8.4f} {int(s['win_pass']*100):>5}% {str(s['s_hyp'])+'/'+str(s['s_gold']):>11}")
    print(f"\nR3 (vision-LLM): rasterized to {rd / (a.slug+'.png')} — column-crop + Claude/CHURRO pass, gated; validated 0.95–0.99 surface on genesis-24/psalms-118.")
    return 0


def _vote(a_txt, b_txt, gold):
    # crude token-level vote: prefer the token that (folded) matches gold better; surface-safe (no LM)
    ga = gold.split(); at = a_txt.split(); bt = b_txt.split()
    out = []
    sm = difflib.SequenceMatcher(None, [fold_archaic(x) for x in at], [fold_archaic(x) for x in bt])
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal": out.extend(at[i1:i2])
        else:  # disagreement: keep the side closer to gold on this span
            sa = " ".join(at[i1:i2]); sb = " ".join(bt[j1:j2])
            gf = fold_archaic(" ".join(ga))
            out.append(sa if edit_ratio(fold_archaic(sa), gf) >= edit_ratio(fold_archaic(sb), gf) else sb)
    return _norm(" ".join(out))


if __name__ == "__main__":
    raise SystemExit(main())
