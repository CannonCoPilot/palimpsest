#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ref_policy_diagnose.py — is s_dismas systemically mishandled at the POP-2 loci? (Sir's THIRD, 2026-07-27)

THE DAY-1 RULE IS ALREADY IMPLEMENTED. `char_identity.evaluate_locus` reads:

    archaic_ref_exists = archaic_ref is not None and archaic_ref.strip() != ""
    if archaic_ref_exists: governing_gate = "archaic"    else: governing_gate = "modern"

which is exactly Sir's policy — archaic is primary where it has text, modern otherwise. **What is wrong is the
PREDICATE, not the rule.** `archaic_ref_exists` is true for any NON-EMPTY STRING at the locus, whether or not
that string is THIS VERSE's text. Sir's wording is "only at the loci where they actually have text content of
their own"; a non-empty entry holding a different verse, a fragment, or boilerplate is not that.

`floor_modern` (archaic-ref vs modern-ref, no OCR involved) already measures the difference and is consulted
in ONE direction only: a low value invalidates the MODERN yardstick and never the archaic one. That asymmetry
is the whole bug — 1535 records govern on an archaic reference whose agreement with janvier is 0.008.

This module looks at what s_dismas ACTUALLY HOLDS at those loci, per-source and per-book and pooled, so the
predicate is fixed on evidence rather than on a threshold picked to make the number move.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import qc_audit as QA               # noqa: E402
import char_identity as CI          # noqa: E402
from audit_diagnose import pairs, _split  # noqa: E402

_W = re.compile(r"[A-Za-zſ]+")


def classify(arc: str | None, mod: str | None) -> str:
    """What KIND of thing is sitting in the archaic reference slot at this locus?"""
    if arc is None:
        return "absent (no entry)"
    if not arc.strip():
        return "empty string"
    na, nm = len(_W.findall(arc)), len(_W.findall(mod or ""))
    fm = CI.floor_modern(arc, mod)
    if fm is not None and fm >= 0.90:
        return "this verse (agrees with modern)"
    if nm and na < 0.30 * nm:
        return "FRAGMENT (far shorter than the verse)"
    if nm and na > 2.5 * nm:
        return "OVERLONG (several verses merged)"
    return "DIFFERENT TEXT (length plausible, content disagrees)"


def main():
    B = pairs(HERE / "coverage-audit-verse.json")
    # build_refs returns (archaic, modern, archaic_src, modern_src) — unpacking it the other way round
    # silently swapped every label in this diagnostic's first run and would have inverted the conclusion.
    archaic, modern, asrc, msrc = QA.build_refs()

    def A(r):
        return r.get("archaic_id")

    def M(r):
        return r.get("modern_id")

    sets = {
        "POP-2 archaic<0.2 & modern>0.9": [(k, r) for k, r in B.items()
                                           if A(r) is not None and A(r) < 0.2 and M(r) is not None and M(r) > 0.9],
        "POP-1 archaic<0.2 & modern<0.2": [(k, r) for k, r in B.items()
                                           if A(r) is not None and A(r) < 0.2 and M(r) is not None and M(r) < 0.2],
        "CONTROL archaic>0.9": [(k, r) for k, r in B.items() if A(r) is not None and A(r) > 0.9],
    }
    out = {}
    for name, rows in sets.items():
        # one locus can appear once per source; the REFERENCE is a property of the LOCUS, so dedupe
        loci = sorted({k[0] for k, _ in rows})
        kinds = Counter()
        by_book, by_src = defaultdict(Counter), Counter()
        fms = []
        for locus in loci:
            arc, mod = archaic.get(locus), modern.get(locus)
            kind = classify(arc, mod)
            kinds[kind] += 1
            by_book[_split(locus)[0]][kind] += 1
            by_src[asrc.get(locus, "—")] += 1
            fm = CI.floor_modern(arc, mod)
            if fm is not None:
                fms.append(fm)
        print(f"\n{'='*100}\n{name}: {len(rows)} records over {len(loci)} distinct loci\n")
        for k, n in kinds.most_common():
            print(f"   {n:5} ({100*n/max(1,len(loci)):5.1f}%)  {k}")
        print(f"   archaic reference source: {dict(by_src)}")
        if fms:
            print(f"   floor_modern over these loci: mean {mean(fms):.4f} · <0.5 on "
                  f"{sum(1 for x in fms if x < 0.5)}/{len(fms)}")
        print("   by book:")
        for b, c in sorted(by_book.items()):
            print(f"     {b:12} " + " · ".join(f"{k.split('(')[0].strip()}={v}" for k, v in c.most_common(3)))
        out[name] = {"records": len(rows), "loci": len(loci), "kinds": dict(kinds),
                     "archaic_source": dict(by_src),
                     "floor_modern_mean": round(mean(fms), 4) if fms else None}

    # SAMPLES — the actual strings, because a category count is not evidence on its own.
    pop2 = sets["POP-2 archaic<0.2 & modern>0.9"]
    print(f"\n{'='*100}\nSAMPLE POP-2 LOCI — what is actually in each reference\n")
    seen = set()
    for (locus, wid), r in pop2:
        if locus in seen:
            continue
        seen.add(locus)
        if len(seen) > 6:
            break
        print(f"  {locus}   (archaic source: {asrc.get(locus)})")
        print(f"     archaic : {(archaic.get(locus) or '<none>')[:110]}")
        print(f"     modern  : {(modern.get(locus) or '<none>')[:110]}")
        print(f"     kind    : {classify(archaic.get(locus), modern.get(locus))}")
    (HERE / "ref-policy-diagnosis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n-> wrote ref-policy-diagnosis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
