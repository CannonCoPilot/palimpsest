#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compare_audits.py — A/B two `qc_audit` artifacts on the metrics that gate adoption.

Written for the §13 Q36 A/B (`ODR_PARTIAL_FIT` off vs on), but there is nothing specific to it here: give it
two `coverage-audit-verse*.json` and it reports the headline pass rates, the per-source pass rates, and — the
part a rate cannot show — WHICH verses changed verdict in each direction. A net-zero rate with 40 verses moving
each way is a different fact from a net-zero rate with nothing moving, and only the second is "no change".

Usage: ../ocr-venv/bin/python compare_audits.py BASE.json CHALLENGER.json [--limit 25]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def rates(d: dict) -> dict:
    """Pass rates under the audit's own archaic-preeminent gate, overall and per source."""
    tot = Counter()
    per: dict[str, Counter] = {}
    for locus, v in d["verses"].items():
        for s, sd in (v.get("sources") or {}).items():
            if not sd.get("localized"):
                continue
            c = per.setdefault(s, Counter())
            c["attested"] += 1
            tot["attested"] += 1
            if sd.get("passed_effective"):
                c["passed"] += 1
                tot["passed"] += 1
    return {"total": tot, "per_source": per}


def verdicts(d: dict) -> dict[tuple[str, str], bool]:
    return {(locus, s): bool(sd.get("passed_effective"))
            for locus, v in d["verses"].items()
            for s, sd in (v.get("sources") or {}).items() if sd.get("localized")}


def main() -> int:
    argv = sys.argv[1:]
    limit = 25
    if "--limit" in argv:
        i = argv.index("--limit")
        limit = int(argv[i + 1])
        del argv[i:i + 2]                 # ...or the option's VALUE is read as a positional path
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2
    base, cur = (json.loads(Path(a).read_text()) for a in args)
    rb, rc = rates(base), rates(cur)
    print(f"{'':<8} {'BASE attested':>14} {'passed':>8} {'rate':>7}    "
          f"{'CHAL attested':>14} {'passed':>8} {'rate':>7}   {'Δrate':>8}")
    for label, kb, kc in [("ALL", rb["total"], rc["total"])] + [
            (s, rb["per_source"].get(s, Counter()), rc["per_source"].get(s, Counter()))
            for s in sorted(set(rb["per_source"]) | set(rc["per_source"]))]:
        pb = kb["passed"] / kb["attested"] if kb["attested"] else 0.0
        pc = kc["passed"] / kc["attested"] if kc["attested"] else 0.0
        print(f"{label:<8} {kb['attested']:>14} {kb['passed']:>8} {pb:>7.4f}    "
              f"{kc['attested']:>14} {kc['passed']:>8} {pc:>7.4f}   {pc-pb:>+8.4f}")

    vb, vc = verdicts(base), verdicts(cur)
    gained = sorted(k for k in vc if vc[k] and not vb.get(k, False))
    lost = sorted(k for k in vb if vb[k] and not vc.get(k, False))
    appeared = sorted(set(vc) - set(vb))
    vanished = sorted(set(vb) - set(vc))
    print(f"\nVERDICT MOVEMENT (cells = locus x source)")
    print(f"  fail -> PASS      {len(gained)}")
    print(f"  PASS -> fail      {len(lost)}")
    print(f"  newly localized   {len(appeared)}   (a verse the challenger attests and the base did not)")
    print(f"  no longer local.  {len(vanished)}   <- NEVER acceptable silently: an un-localized verse leaves "
          f"the denominator and INFLATES the rate")
    for label, rows in (("GAINED", gained), ("LOST", lost), ("VANISHED", vanished)):
        if not rows:
            continue
        print(f"\n  {label} (first {limit}):")
        for locus, s in rows[:limit]:
            print(f"    {locus:<28} {s}")
        by_book = Counter(locus.split("/")[1] for locus, _ in rows)
        print(f"    by book: {dict(by_book)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
