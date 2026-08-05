#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""five_sets.py — Sir's FOURTH: the five diagnostic sets, per-source, per-book and pooled (2026-07-27).

    S1  modern < 0.2
    S2  archaic < 0.2
    S3  modern < 0.2 AND archaic < 0.2
    S4  modern > 0.9 AND archaic < 0.8
    S5  archaic > 0.9 AND modern < 0.8

Run on the CORRECTED basis (declared witness inventory · realigned archaic reference · archaic-validity
predicate), so the populations mean what they say. Each set is reported with the diagnostic that separates
its causes rather than a bare count:

  floor_modern  archaic-ref vs modern-ref, NO OCR involved. High => the two references agree about what the
                verse says, so a low identity is the OCR's fault. Low => the references disagree, so the
                reference is the outlier and the OCR may be fine. This is the single most informative column
                and it is why S4 and S5 are asymmetric.
  ref kind      what the archaic slot actually holds: this verse / a different verse / a fragment / overlong.
  ref invalid   whether the corrected predicate already withdrew the archaic reference at that locus.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import char_identity as CI                    # noqa: E402
import qc_audit as QA                         # noqa: E402
from audit_diagnose import pairs, _split      # noqa: E402
from ref_policy_diagnose import classify      # noqa: E402


def build_sets(B: dict) -> dict:
    def A(r):
        return r.get("archaic_id")

    def M(r):
        return r.get("modern_id")
    return {
        "S1 modern<0.2": [(k, r) for k, r in B.items() if M(r) is not None and M(r) < 0.2],
        "S2 archaic<0.2": [(k, r) for k, r in B.items() if A(r) is not None and A(r) < 0.2],
        "S3 modern<0.2 AND archaic<0.2": [(k, r) for k, r in B.items()
                                          if M(r) is not None and M(r) < 0.2 and A(r) is not None and A(r) < 0.2],
        "S4 modern>0.9 AND archaic<0.8": [(k, r) for k, r in B.items()
                                          if M(r) is not None and M(r) > 0.9 and A(r) is not None and A(r) < 0.8],
        "S5 archaic>0.9 AND modern<0.8": [(k, r) for k, r in B.items()
                                          if A(r) is not None and A(r) > 0.9 and M(r) is not None and M(r) < 0.8],
    }


def main():
    B = pairs(HERE / "coverage-audit-verse.json")
    archaic, modern, asrc, _ = QA.build_refs()
    sets = build_sets(B)
    out = {}
    print(f"total scan-verse records: {len(B)}")
    for name, rows in sets.items():
        loci = sorted({k[0] for k, _ in rows})
        by_src = Counter(k[1] for k, _ in rows)
        by_book = Counter(_split(k[0])[0] for k, _ in rows)
        inval = sum(1 for _, r in rows if r.get("archaic_reference_invalid_here"))
        fms, kinds = [], Counter()
        for locus in loci:
            f = CI.floor_modern(archaic.get(locus), modern.get(locus))
            if f is not None:
                fms.append(f)
            kinds[classify(archaic.get(locus), modern.get(locus))] += 1
        print(f"\n{'='*100}\n{name}: {len(rows)} records over {len(loci)} loci "
              f"({100*len(rows)/len(B):.1f}% of all records)\n")
        print(f"   by source: {dict(by_src.most_common())}")
        print(f"   by book  : {dict(by_book.most_common())}")
        if fms:
            print(f"   floor_modern (references vs each other): mean {mean(fms):.4f} · "
                  f"<0.5 on {sum(1 for x in fms if x < 0.5)}/{len(fms)} loci")
        print(f"   archaic slot holds: " + " · ".join(f"{k.split('(')[0].strip()}={v}" for k, v in kinds.most_common()))
        print(f"   archaic reference already withdrawn by the predicate: {inval}/{len(rows)}")
        # per-source x per-book, the cell that dominates
        cell = Counter((k[1], _split(k[0])[0]) for k, _ in rows)
        top = " · ".join(f"{s}/{b}={n}" for (s, b), n in cell.most_common(5))
        print(f"   worst source x book cells: {top}")
        out[name] = {"records": len(rows), "loci": len(loci), "by_source": dict(by_src),
                     "by_book": dict(by_book), "ref_kinds": dict(kinds),
                     "floor_modern_mean": round(mean(fms), 4) if fms else None,
                     "archaic_withdrawn": inval,
                     "top_cells": {f"{s}/{b}": n for (s, b), n in cell.most_common(10)}}
    (HERE / "five-sets.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n-> wrote five-sets.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
