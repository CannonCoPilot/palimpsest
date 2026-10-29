#!/usr/bin/env python
"""R16.9 — extend GOLD-LAYOUT to the SETTINGS it does not cover, by systematic random sample.

🔴 THE GAP, IN LEAVES. GOLD-LAYOUT's 208 leaves come from three settings of type — the 1582 Rhemes
NT, the 1609 OT1 and the 1610 OT2 — across two copies. The corpus holds 12,891 leaves. **The 1633
Rouen NT (1,543 leaves) and the 1635 Rouen OT (2,071) have NO gold at all**, and they are not more of
the same book: a different press, a different compositor, different page furniture. Any accuracy
figure from today's gold is a claim about three settings WORN AS a claim about five.

⚠️ SYSTEMATIC, NOT UNIFORM RANDOM, AND THE REASON IS R16.1'S. A uniform sample over a volume CLUSTERS,
and leaves that cluster share a gathering — the same paper, ink and press run. R16.1 requires the
train/score split to be made at gathering grain precisely because such leaves are near-duplicates. A
random start with a fixed stride spreads the sample across gatherings BY CONSTRUCTION, so the defect
cannot arise and then need repairing. The start is seeded and recorded; the sample is reproducible.

⚠️ AND NO STRATUM IS TRIMMED OFF THE ENDS. The temptation is to sample "the body of the book" and skip
prelims and endmatter. Those ends are archetypes G and H — the title pages, tables and indexes that
R16.5 just gave a vocabulary to and that the corpus is thinnest in. Sampling them out would build an
eval set that cannot see the classes most recently added.

═══ ADMISSIBILITY, CHECKED AGAINST `witnesses.ROLES` RATHER THAN ASSUMED ═══════════════════════════

  NT-1633-F  role `lowres`      ✅ ADMITTED. The role text names *"page LAYOUT and geometry (region
                                boundaries, archetype classification, reading order)"* explicitly,
                                and bars it only at GLYPH grain (~168 ppi, the long-ſ nub under
                                1.6 px). Layout is not that grain.
  NT-1582-M  role `lowres`      ✅ ADMITTED, same clause — and `witnesses.py` says of `M` in as many
                                words that it *"is wanted for layout validation"*. ⚠️ It covers a
                                setting the gold ALREADY has (1582, via B), so it is sampled thinly
                                and for a DIFFERENT purpose: it is a 1-bit CCITT stencil out of a
                                2007 reprint PDF, where every other witness here is continuous tone.
                                That makes it a channel-robustness probe, NOT new-setting coverage,
                                and it must not be counted as the latter.
  OT-1635-M  role `frontmatter` ⚠️ **PENDING ADJUDICATION — SAMPLED AND MARKED, NOT ASSUMED.** The
                                role reads *"admitted for prelims and endmatter, excluded from the
                                verse text. No verse of scripture, at any resolution"*, and
                                `ROLE_VERSE_SCOPE` gives it `none`. That bar is stated on the VERSE
                                TEXT. A layout label takes no reading — it records WHERE the
                                scripture column sits, not what it says — so on the file's own
                                doctrine (*"a resolution bar is a bar on ONE GRAIN of question, never
                                on the witness"*) layout is a different grain. **But `frontmatter` is
                                not a resolution bar; it is an EDITION bar**, and widening it is a
                                scope decision of the same kind Sir made for the 190/18. So these
                                leaves are written with `pending_role_adjudication: true` and are
                                excluded from every count until that is settled. ⚠️ ALSO BLOCKED
                                UPSTREAM: the S06 raster package is the one R7.5a-2 has open, and its
                                jp2 directory is literally named `_broken`.
  NT-1633-R  role `support`     ❌ NOT SAMPLED. `support` is defined as *"admitted for named leaves
                                only"* — a permission about readings where the base has no leaf. It
                                grants nothing for layout, and F already covers this setting. Taking
                                R as well would also put two copies of ONE setting in the sample,
                                which is depth where the gold needs BREADTH.

    ../ocr-venv/bin/python witness/sample_gold_leaves.py           # report
    ../ocr-venv/bin/python witness/sample_gold_leaves.py --build   # write the manifest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W                                   # noqa: E402

OUT = _HERE / "plates" / "gold-expansion.json"
BUNDLE = _HERE / "plates" / "bundle.json"

# ⚠️ THE SEED IS PART OF THE RECORD, not a convenience. An unrecorded seed makes the sample
# unreproducible, and an unreproducible sample cannot be audited for the clustering it was drawn to
# avoid. §0.5's discipline applied to a sampling frame.
SEED = 16090610

# (vol, sig, n, purpose). ⚠️ `n` IS DELIBERATELY SMALL. Sir: "not a whole ton". These leaves must be
# reviewed BY HAND, at 15 classes, six of which have no cue and so cannot even be pre-populated —
# every AN/TB/DT/CO/OR/DC box gets drawn and named from scratch. 50 leaves is roughly a quarter
# again on top of the 208 already walked, which is a real cost and is the reason it is not 200.
PLAN = [
    ("NT", "F", 20, "NEW SETTING — 1633 Rouen NT, 1,543 corpus leaves with no gold"),
    ("OT", "M", 20, "NEW SETTING — 1635 Rouen OT, 2,071 corpus leaves with no gold"),
    ("NT", "M", 10, "CHANNEL PROBE — 1582 setting already covered by B; this is a 1-bit CCITT "
                    "stencil, not continuous tone. Robustness, NOT setting coverage."),
]
PENDING = {("OT", "M")}          # role `frontmatter`; see the docstring


def systematic(n_total: int, k: int, seed: int) -> list[int]:
    """A random-start, fixed-stride sample. Spreads across gatherings by construction.

    ⚠️ NO `random` MODULE. The start is derived from the recorded seed arithmetically, so the sample
    is reproducible without depending on a PRNG's implementation staying put across versions — the
    same reason this project pins what it can and records what it cannot.
    """
    stride = n_total / k
    start = seed % max(1, int(stride))
    return [min(n_total - 1, int(start + i * stride)) for i in range(k)]


def main(build: bool) -> int:
    have = {p["witness"] for p in json.loads(BUNDLE.read_text())["plates"]}
    print("R16.9 — GOLD-LAYOUT EXPANSION TO UNCOVERED SETTINGS")
    print(f"seed {SEED} · systematic random (random start, fixed stride)")
    print(f"settings already in gold: {' '.join(sorted(have))}\n")

    rows, total = [], 0
    for vol, sig, k, why in PLAN:
        wid = W.wid(vol, sig)
        rec = W.WITNESSES[(vol, sig)]
        leaves = W.leaves(vol, sig)
        idx = systematic(len(leaves), k, SEED)
        pend = (vol, sig) in PENDING
        print(f"  {wid:12s} role={rec['role']:11s} year={rec['year']}  "
              f"{k} of {len(leaves)} leaves  (stride {len(leaves)/k:.0f})"
              f"{'   ⚠️ PENDING ROLE ADJUDICATION' if pend else ''}")
        print(f"       {why}")
        print(f"       leaves: {' '.join(str(i) for i in idx[:10])}"
              f"{' …' if len(idx) > 10 else ''}")
        missing = [i for i in idx if not leaves[i].exists()]
        if missing:
            print(f"       🔴 {len(missing)} sampled leaf/leaves have NO RASTER: {missing}")
        for i in idx:
            rows.append({"id": f"{wid}_{i:04d}", "witness": wid, "leaf": i,
                         "role": rec["role"], "year": rec["year"],
                         "src": str(leaves[i]), "exists": leaves[i].exists(),
                         "purpose": why, "pending_role_adjudication": pend,
                         "split": None})     # ⚠️ UNASSIGNED — R16.1's gathering split, never defaulted
        if not pend:
            total += k
        print()

    print(f"COUNTED toward gold expansion : {total}")
    print(f"HELD pending adjudication     : {len(rows) - total}")
    print(f"gold 208 -> {208 + total} counted"
          f" ({208 + len(rows)} if the 1635 role question resolves in favour)")
    print("\n⚠️ EVERY ROW CARRIES `split: null`. R16.1's gathering-level split is UNASSIGNED for 188")
    print("   of the existing 208 too, and a leaf defaulted to `train` is a leaf that silently")
    print("   stops being able to score anything.")
    print("⚠️ AND SAMPLING IS NOT COVERAGE. These leaves have no boxes, no classes and no verdicts.")
    print("   They are a sampling FRAME; the review is the work, and it has not started.")

    if build:
        OUT.write_text(json.dumps({
            "_doc": "R16.9 systematic random sample of leaves from settings GOLD-LAYOUT does not "
                    "cover. A sampling frame, NOT reviewed leaves.",
            "_seed": SEED, "_method": "systematic: random start from seed, fixed stride",
            "_counted": total, "_pending": len(rows) - total,
            "leaves": rows}, indent=1, ensure_ascii=False))
        print(f"\nwritten -> {OUT.relative_to(_HERE.parent)}")
    else:
        print("\n(report only — pass --build to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--build" in sys.argv))
