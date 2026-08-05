#!/usr/bin/env python3
"""gt_rescore.py — empirical baseline: score OCR + references against the GOLD TRANSCRIPTS (Sir, 2026-07-18).

At the GT-covered scripture loci, per complete verse, compute (fold_archaic + edit_ratio, the pilot metric):
  A  ocr_consensus vs GT   — TRUE OCR fidelity to truth
  B  s_dismas      vs GT   — how faithful the s_dismas reference is to truth (divergence = 1-B)
  C  odr_com       vs GT   — how faithful the odr_com reference is to truth
  D  ocr_consensus vs s_dismas — what the PILOT measures (OCR vs the noisy reference)

The (A - D) gap is the MEASUREMENT ARTIFACT: how much the s_dismas reference's own divergence
depresses the pilot's OCR score below OCR's true fidelity.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from statistics import mean

SPIKE = Path(__file__).resolve().parent
ROOT = SPIKE.parent
sys.path.insert(0, str(SPIKE))
from char_identity import fold_archaic, edit_ratio  # noqa: E402

def load_reads(name):
    d = json.loads((ROOT / "reconstruction/reads" / f"{name}.json").read_text())
    return {e["skeleton_id"]: e.get("surface", "") for e in d["reads"] if e.get("present")}

SD = load_reads("s_dismas")
OC = load_reads("odr_com")
CO = load_reads("ocr_consensus")

# GT scripture loci -> book (chapter comes from the per-line verse tag "ch:v")
LOCI = {
    "scripture-genesis-24": "genesis", "scripture-genesis-16-p081": "genesis",
    "scripture-genesis-16-p082": "genesis", "scripture-psalms-001": "psalms",
    "scripture-psalms-074-p137": "psalms", "scripture-psalms-074-p138": "psalms",
    "scripture-psalms-115-116": "psalms", "scripture-psalms-118": "psalms",
    "scripture-psalms-150-p265": "psalms", "scripture-psalms-150-p266": "psalms",
    "scripture-matthew-28-p102": "matthew", "scripture-2john": "2john",
}

def gt_verses(slug, book):
    """-> {skeleton_id: gt_text} for COMPLETE verses (skip a/b/c partials + excluded/catchword)."""
    d = json.loads((SPIKE / "ground-truth" / f"{slug}.json").read_text())
    by_v = {}
    for L in d.get("body", []):
        if L.get("role") in ("excluded", "catchword"):
            continue
        vt = L.get("verse") or ""
        m = re.match(r"^(\d+):(\d+)([a-c])?$", vt)
        if not m:
            continue
        partial = m.group(3) is not None
        skel = f"scripture/{book}/{m.group(1)}/{m.group(2)}"
        by_v.setdefault(skel, {"text": [], "partial": False})
        by_v[skel]["text"].append(L.get("text", "") if isinstance(L.get("text"), str) else "")
        if partial:
            by_v[skel]["partial"] = True
    # a verse is scoreable only if NONE of its lines were partial (fully on page)
    return {s: " ".join(v["text"]) for s, v in by_v.items() if not v["partial"]}

rows = []
for slug, book in LOCI.items():
    gts = gt_verses(slug, book)
    scored = 0
    for skel, gttext in gts.items():
        g = fold_archaic(gttext)
        if not g:
            continue
        sd, oc, co = SD.get(skel), OC.get(skel), CO.get(skel)
        r = {"locus": slug, "skel": skel,
             "A_ocr_gt": edit_ratio(fold_archaic(co), g) if co is not None else None,
             "B_sd_gt": edit_ratio(fold_archaic(sd), g) if sd is not None else None,
             "C_oc_gt": edit_ratio(fold_archaic(oc), g) if oc is not None else None,
             "D_ocr_sd": edit_ratio(fold_archaic(co), fold_archaic(sd)) if (co is not None and sd is not None) else None}
        rows.append(r); scored += 1

def agg(key, rs):
    vals = [r[key] for r in rs if r[key] is not None]
    return (mean(vals), sum(1 for v in vals if v >= 0.90), len(vals)) if vals else (None, 0, 0)

print(f"{'locus':28} {'n':>3}  {'A ocr·GT':>9} {'B sd·GT':>9} {'C odr·GT':>9} {'D ocr·sd':>9}   pass@.9 A/D")
print("-" * 92)
for slug in LOCI:
    rs = [r for r in rows if r["locus"] == slug]
    if not rs:
        print(f"{slug:28}   (no scoreable complete verses vs references)"); continue
    (a, ap, an), (b, _, _), (c, _, _), (d, dp, dn) = agg("A_ocr_gt", rs), agg("B_sd_gt", rs), agg("C_oc_gt", rs), agg("D_ocr_sd", rs)
    fa = lambda x: f"{x:.3f}" if x is not None else "  —  "
    print(f"{slug:28} {len(rs):>3}  {fa(a):>9} {fa(b):>9} {fa(c):>9} {fa(d):>9}   {ap}/{an}  {dp}/{dn}")

print("-" * 92)
(A, Ap, An), (B, Bp, Bn), (C, Cp, Cn), (D, Dp, Dn) = agg("A_ocr_gt", rows), agg("B_sd_gt", rows), agg("C_oc_gt", rows), agg("D_ocr_sd", rows)
print(f"{'OVERALL':28} {len(rows):>3}  {A:.3f}     {B:.3f}     {C:.3f}     {D:.3f}")
print(f"\nTRUE OCR fidelity vs Gold (A):           mean {A:.3f},  pass@0.9 = {Ap}/{An} = {100*Ap/An:.0f}%")
print(f"What the pilot measures (OCR vs s_dismas, D): mean {D:.3f},  pass@0.9 = {Dp}/{Dn} = {100*Dp/Dn:.0f}%")
print(f"MEASUREMENT ARTIFACT (A - D):            +{A - D:.3f} mean,  +{100*Ap/An - 100*Dp/Dn:.0f} pts pass-rate")
print(f"\ns_dismas faithfulness to Gold (B): mean {B:.3f}  -> s_dismas diverges {100*(1-B):.1f}% from truth (pass@.9 {Bp}/{Bn})")
print(f"odr_com  faithfulness to Gold (C): mean {C:.3f}  -> odr_com  diverges {100*(1-C):.1f}% from truth (pass@.9 {Cp}/{Cn})")

out = {"metric": "fold_archaic + edit_ratio (pilot metric)", "n_verses": len(rows),
       "overall": {"A_ocr_vs_gt": A, "B_sdismas_vs_gt": B, "C_odrcom_vs_gt": C, "D_ocr_vs_sdismas": D,
                   "pass_A": [Ap, An], "pass_D": [Dp, Dn]}, "rows": rows}
(SPIKE / "gt-rescore-baseline.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(f"\nwrote gt-rescore-baseline.json ({len(rows)} verse rows)")
