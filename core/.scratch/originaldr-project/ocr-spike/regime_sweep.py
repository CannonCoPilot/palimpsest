#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""regime_sweep.py — TIER B: does the block grammar hold across every curated source?

The over-fitting worry, made empirical. The grammar was designed from 14 gold pages of essentially two
volumes; if it only describes those, an unseen source will either (a) be forced into a regime that does not
fit — the silent failure — or (b) come back `unmatched`, which is the signal we built it to give. This sweep
runs regime detection + the page-level coverage alarm across a sample of pages from EVERY curated source and
reports the rates, so "does the Matthew regime extend across the NT?" gets a number instead of an assumption.

Kraken is run live (~10s/page) and cached under `.regime-sweep/` so a re-run is free.

Usage: ../ocr-venv/bin/python regime_sweep.py [--pages N] [ocr_dir ...]
"""
from __future__ import annotations
import json, sys, time, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, ".")
from collections import Counter
from pathlib import Path
import block_grammar, curated_sources as CS, reocr_core as core

OUT = Path(".regime-sweep"); OUT.mkdir(exist_ok=True)


def page(ocr_dir: str, pi: int) -> dict | None:
    f = OUT / f"{ocr_dir}-{pi}.json"
    if f.exists():
        d = json.loads(f.read_text())
        return {"page_px": tuple(d["page_px"]), "r2_body": d["r2_body"], "lines": d["lines"]}
    try:
        r = core.reocr_page(ocr_dir, pi, want_base=False, want_r1=False)
    except Exception as e:
        print(f"    [skip] {ocr_dir} p{pi}: {type(e).__name__}: {e}", flush=True)
        return None
    d = {"page_px": r["page_px"], "r2_body": r["r2_body"],
         "lines": [{"text": l.get("text"), "role": l.get("role"), "conf": l.get("conf"),
                    "bbox": l.get("bbox")} for l in r["lines"]]}
    f.write_text(json.dumps(d, ensure_ascii=False))
    return {"page_px": tuple(d["page_px"]), "r2_body": d["r2_body"], "lines": d["lines"]}


def main():
    args = sys.argv[1:]
    n = 3
    if "--pages" in args:
        i = args.index("--pages"); n = int(args[i + 1]); del args[i:i + 2]
    dirs = args or sorted(CS.OCR_DIR_SOURCE)
    # spread the sample through each volume rather than clustering at the front matter
    offsets = [120, 400, 700, 900, 1100][:n]
    rows = []
    t0 = time.time()
    for od in dirs:
        src = CS.OCR_DIR_SOURCE.get(od, "?")
        for pi in offsets:
            r = page(od, pi)
            if r is None:
                continue
            d = block_grammar.dispatch(r)
            runs = Counter(x["type"] for x in block_grammar.compose(block_grammar.parse_page(r)))
            rows.append({"src": src, "ocr_dir": od, "page": pi, "regime": d["regime"],
                         "self_labelling": d["self_labelling"], "conf": d["confidence"],
                         "n_body": d["evidence"].get("n_body", 0), "runs": dict(runs)})
            print(f"  {src:<4} {od:<26} p{pi:<5} {d['regime']:<15} conf={d['confidence']:.2f} "
                  f"body={d['evidence'].get('n_body', 0):<4} ({time.time()-t0:.0f}s)", flush=True)
    (OUT / "_sweep.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n{'=' * 78}\nREGIME COVERAGE across {len({r['src'] for r in rows})} curated sources, "
          f"{len(rows)} pages")
    by_src = {}
    for r in rows:
        by_src.setdefault(r["src"], Counter())[r["regime"]] += 1
    for src in sorted(by_src):
        print(f"  {src}: {dict(by_src[src])}")
    tot = Counter(r["regime"] for r in rows)
    unmatched = tot.get("unmatched", 0)
    print(f"\n  ALL: {dict(tot)}")
    print(f"  unmatched: {unmatched}/{len(rows)} = {unmatched/max(1,len(rows)):.1%} "
          f"({'coverage gap — extend the vocabulary' if unmatched else 'every sampled page matched a regime'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
