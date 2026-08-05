#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grammar_eval.py — does the block grammar detect the right regime, and does the alarm fire where it should?
Usage: ../ocr-venv/bin/python grammar_eval.py"""
from __future__ import annotations
import json, sys, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, ".")
from pathlib import Path
import block_grammar, coverage_alarm, verse_locate
from gate_calibrate import LOCI, gold_by_chapter, cached_page
GT = Path("ground-truth")

print("REGIME DETECTION + COMPOSITION")
print(f"{'slug':<27} {'regime':<16} {'self-lbl':>8} {'conf':>5}  {'block runs (composed)'}")
for slug, book in sorted(LOCI.items()):
    gt = json.loads((GT / f"{slug}.json").read_text())
    r = cached_page(slug, gt.get("ocr_dir"), gt.get("page_index"))
    d = block_grammar.dispatch(r)
    runs = block_grammar.compose(block_grammar.parse_page(r))
    from collections import Counter
    c = Counter(x["type"] for x in runs)
    top = ", ".join(f"{k}×{v}" for k, v in c.most_common(4))
    print(f"{slug:<27} {d['regime']:<16} {str(d['self_labelling']):>8} {d['confidence']:>5.2f}  {top}")

print("\nCATASTROPHIC-FAILURE ALARM (page level)")
print(f"{'slug':<27} {'ch':>4} {'ref':<10} {'recall':>7} {'fidelity':>9} {'alarm':>6}")
for slug, book in sorted(LOCI.items()):
    gt = json.loads((GT / f"{slug}.json").read_text())
    r = cached_page(slug, gt.get("ocr_dir"), gt.get("page_index"))
    for ch in sorted(gold_by_chapter(gt)):
        a = coverage_alarm.page_alarm(r, book, ch)
        cov = a.get("coverage") or {}
        print(f"{slug:<27} {ch:>4} {str(cov.get('ref_source')):<10} "
              f"{(cov.get('recall') if cov.get('recall') is not None else -1):>7.3f} "
              f"{cov.get('fidelity', -1):>9.3f} {str(a['alarm']):>6}")
        for why in a["reasons"]:
            print(f"      ! {why}")
