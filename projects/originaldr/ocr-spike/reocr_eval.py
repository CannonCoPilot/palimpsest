#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reocr_eval.py — the EVALUATION harness. This is the ONLY place gold is touched.

It runs the gold-free production pipeline (`reocr_core.reocr_page`) on the pages that happen to have a gold
transcript, and scores each rung against gold at the grain-correct metric (page content edit_ratio over
fold_archaic + ~20-word window pass-rate + the mandatory ſ-count companion check). It reports per-page,
splitting TRAIN pages (contributed fine-tuning lines) from HELD-OUT pages (a clean generalization signal),
because Principle #1 is: the pipeline must work on pages with NO gold, and only a held-out page proves that.

Gold is used here for MEASUREMENT and for offline calibration of the confidence gate — never at runtime.
"""
from __future__ import annotations
import sys, json, re, difflib, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from char_identity import fold_archaic, edit_ratio
import reocr_core as core

HERE = Path(__file__).resolve().parent
GT = HERE / "ground-truth"
# Prefer the held-out training manifest (what reichenau_dr_ho actually trained on) so the eval correctly
# labels the 3 held-out pages as HELD-OUT; fall back to the full manifest for the full model.
_HO_MANIFEST = HERE / ".rung2-data" / "_manifest-ho.json"
TRAIN_MANIFEST = _HO_MANIFEST if _HO_MANIFEST.exists() else (HERE / ".rung2-data" / "_manifest.json")
PASS, WIN = 0.90, 20


def _norm(s): return re.sub(r"\s+", " ", s or "").strip()

def gold_body(slug):
    d = json.loads((GT / f"{slug}.json").read_text())
    return _norm(" ".join(b.get("text", "") for b in d.get("body", [])
                 if b.get("text", "").strip() and b.get("role") not in ("catchword", "signature")))

def gold_meta(slug):
    d = json.loads((GT / f"{slug}.json").read_text())
    return d.get("ocr_dir"), d.get("page_index")

def _windows(text, w=WIN):
    t = re.findall(r"\S+", text or "");  return [" ".join(t[i:i+w]) for i in range(0, len(t), w)] if t else []
def _owins(text, w=WIN):
    t = re.findall(r"\S+", text or "")
    if not t: return [""]
    return [" ".join(t[i:i+w]) for i in range(0, len(t), max(1, w//2))] or [""]

def _containment(gold, hyp):
    """Fraction of `gold` (chars, in order) found within `hyp`. This is the CORRECT metric for the DR gold,
    which is VERSE-SCOPED (a page's gold body = the target verses only) while the pipeline transcribes the
    WHOLE page (verses + commentary + annotations — legitimately, for the corpus). Whole-page edit_ratio
    wrongly punishes that extra content; containment asks the honest question: did we correctly transcribe
    the gold verses, wherever they sit on the page? Ignores hyp's extra (un-golded) content by design."""
    if not gold: return 0.0
    M = sum(b.size for b in difflib.SequenceMatcher(None, gold, hyp, autojunk=False).get_matching_blocks())
    return M / len(gold)


def score(hyp, gold):
    hyp, gold = _norm(hyp), _norm(gold)
    g_gold = gold.count("ſ")
    if not hyp:
        return {"contain": 0.0, "s_contain": 0.0, "content": 0.0, "surface": 0.0, "win": 0.0, "s_hyp": 0, "s_gold": g_gold}
    gf, hf = fold_archaic(gold), fold_archaic(hyp)
    contain = _containment(gf, hf)              # PRIMARY: verses correctly read (ſ-blind)
    s_contain = _containment(gold, hyp)         # surface containment: verses read EXACTLY (ſ-faithful)
    content = edit_ratio(hf, gf)                # whole-page (secondary; misleading for verse-scoped gold)
    surface = difflib.SequenceMatcher(None, hyp, gold).ratio()
    gw = _windows(gold); ow = [fold_archaic(x) for x in _owins(hyp)]; wp = 0
    for g in gw:
        gg = fold_archaic(g)
        if max((edit_ratio(o, gg) for o in ow), default=0) >= PASS: wp += 1
    return {"contain": round(contain, 4), "s_contain": round(s_contain, 4),
            "content": round(content, 4), "surface": round(surface, 4),
            "win": round(wp/len(gw), 4) if gw else 0.0, "s_hyp": hyp.count("ſ"), "s_gold": g_gold}


def train_slugs():
    if not TRAIN_MANIFEST.exists(): return set()
    return set(m.get("slug") for m in json.loads(TRAIN_MANIFEST.read_text()))


def evaluate(slugs, r2_model=None):
    tr = train_slugs()
    kw = {} if r2_model is None else {"r2_model": r2_model}
    rows = []
    for slug in slugs:
        gold = gold_body(slug)
        od, pi = gold_meta(slug)
        if od is None or pi is None or not gold.strip():
            rows.append((slug, None, None, None, None, "no scan/gold")); continue
        held = slug not in tr
        try:
            r = core.reocr_page(od, pi, want_base=True, want_r1=True, **kw)
        except Exception as e:
            rows.append((slug, held, None, None, None, f"ERROR {type(e).__name__}: {e}")); continue
        rows.append((slug, held, score(r.get("base",""), gold), score(r.get("r1_body",""), gold),
                     score(r["r2_body"], gold),
                     f"conf {r['page_conf']} {'⚠esc' if r['escalate_r3'] else ''} drop{r['dropped_apparatus']}"))
    return rows


def _fmt(s):
    if not s: return f"{'—':>8} {'—':>8} {'—':>7} {'—':>5} {'—':>7}"
    return (f"{s['contain']:>8.4f} {s['s_contain']:>8.4f} {s['content']:>7.4f} "
            f"{int(s['win']*100):>4}% {str(s['s_hyp'])+'/'+str(s['s_gold']):>7}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*", help="gold slugs (default: all scripture-* with a scan+gold)")
    ap.add_argument("--r2-model", default=None)
    a = ap.parse_args()
    slugs = a.slugs or sorted(p.stem for p in GT.glob("scripture-*.json"))
    rows = evaluate(slugs, r2_model=a.r2_model)
    print("PRIMARY metric = `contain` (gold verses found within the whole-page transcription; the DR gold is "
          "verse-scoped). `s_contain` = ſ-faithful containment. `content` = whole-page (secondary, deflated by "
          "correctly-transcribed commentary the verse-gold omits).")
    hdr = f"{'slug':30} {'set':8} {'rung':10} {'contain':>8} {'s_cont':>8} {'wholeC':>7} {'win%':>5} {'ſ h/g':>7}"
    for grp, label in ((True, "HELD-OUT (clean generalization — the headline)"), (False, "TRAIN (partial overlap)")):
        sub = [r for r in rows if r[1] is grp]
        if not sub: continue
        print(f"\n### {label} ###\n{hdr}\n" + "-"*len(hdr))
        for slug, held, base, r1, r2, note in sub:
            tag = "held-out" if held else "train"
            if base is None: print(f"{slug:30} {tag:8} {note}"); continue
            print(f"{slug:30} {tag:8} {'base':10} {_fmt(base)}")
            print(f"{'':30} {'':8} {'R1 body':10} {_fmt(r1)}")
            print(f"{'':30} {'':8} {'R2 body':10} {_fmt(r2)}   {note}")
    print("\n### AGGREGATE mean CONTAINMENT (headline = HELD-OUT R2 contain) ###")
    for grp, label in ((True, "held-out"), (False, "train")):
        sub = [r for r in rows if r[1] is grp and r[2]]
        if not sub: continue
        for k, idx in (("base", 2), ("R1 body", 3), ("R2 body", 4)):
            cv = [r[idx]["contain"] for r in sub]; sv = [r[idx]["s_contain"] for r in sub]
            print(f"  {label:9} {k:9} contain {sum(cv)/len(cv):.4f}  s_contain {sum(sv)/len(sv):.4f}  (n={len(cv)})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
