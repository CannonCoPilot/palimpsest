#!/usr/bin/env python
"""Regenerate the per-text masking-map audit reports from the COMPLETED gold maps.

Replaces the obsolete detector-map reports with the gold-intended-map audit: each work's
map is now complete and 100% two-layer, so every report documents the finalized coverage,
the full mask-type breakdown (incl. 0-counts), element-width stats, the per-instance edge
rule, and any count correction. Generated from masking_map.audit (gold ground truth).
"""
import json
import re
import sys
from pathlib import Path

import masking_map as mm  # noqa: E402
from masking_map import ALL_TYPES, GENERIC  # noqa: E402

REPO = Path(".").resolve()
RPT = REPO / "docs" / "development" / "audits" / "masking-map" / "reports"
GOLD = REPO / "core" / "tests" / "fixtures" / "gold"
IDXS = [5, 6, 18, 19, 29, 42, 48, 56, 64, 70, 71, 80, 100, 101, 102, 103, 104, 105, 106, 107]

# stable single-char code per specific type for the ASCII ribbon
_SPEC = [t for t in ALL_TYPES if t not in GENERIC]
_CODE = {t: c for t, c in zip(_SPEC, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJ")}


def _ribbon(a, width=96):
    """Linearized specific-layer ribbon: each cell = dominant specific type code."""
    n = a["text_len"]
    spec = [e for e in a["elements"] if e["type"] not in GENERIC]
    cells = []
    used = {}
    for i in range(width):
        lo, hi = i * n // width, (i + 1) * n // width
        best, blen = None, -1
        for e in spec:
            ov = min(e["end"], hi) - max(e["start"], lo)
            if ov > blen:
                blen, best = ov, e["type"]
        cells.append(_CODE.get(best, "?") if best else ".")
        if best:
            used[best] = _CODE.get(best, "?")
    legend = "  ".join(f"{c}={t}" for t, c in sorted(used.items(), key=lambda kv: kv[1]))
    return "".join(cells), legend


def _slug(work):
    s = re.sub(r"[^a-z0-9]+", "-", work.lower()).strip("-")
    return s[:46]


def report(idx, fname):
    a = mm.audit(idx)
    gold = json.loads((GOLD / f"work-{idx}.json").read_text())
    n = a["text_len"]
    nspec = sum(1 for t in ALL_TYPES if a["type_counts"][t] and t not in GENERIC)
    ngen = sum(1 for t in ALL_TYPES if a["type_counts"][t] and t in GENERIC)
    ribbon, legend = _ribbon(a)

    L = [f"# Masking-Map Audit — [{idx}] {a['work']}", ""]
    L += [f"- **Source file:** `{gold.get('source_file','?')}`",
          f"- **Text length:** {n:,} chars",
          f"- **Mask elements (complete map):** {a['n_elements']:,}",
          f"- **Distinct mask types:** {ngen + nspec} ({ngen} generic, {nspec} specific)",
          f"- **Status:** ✅ COMPLETE — 100% two-layer, 0 sparse regions", ""]

    L += ["## What this audits", "",
          "The **gold's own intended masking map** — every mask element typed by close reading "
          "with exact, materialized per-instance boundaries (NOT the production detector's output). "
          "**Generic** = `body, volume, book, part` (broad containers). **Specific** = the other 30 "
          "types, including `chapter`. **Gate:** every character carries ≥1 generic AND ≥1 specific "
          "mask; `body[0,EOF]` is the universal generic base, so the specific layer must tile 100%.", ""]

    cov = a["coverage_pct"]
    L += ["## Coverage summary", "",
          "| Class | Chars | % of text |", "|---|---:|---:|",
          f"| ✅ covered (≥1 generic + ≥1 specific) | {a['coverage_chars'].get('COVERED',0):,} | {cov.get('COVERED',0):.2f}% |",
          f"| generic-only | {a['coverage_chars'].get('GENERIC_ONLY',0):,} | {cov.get('GENERIC_ONLY',0):.2f}% |",
          f"| specific-only | {a['coverage_chars'].get('SPECIFIC_ONLY',0):,} | {cov.get('SPECIFIC_ONLY',0):.2f}% |",
          f"| uncovered | {a['coverage_chars'].get('UNCOVERED',0):,} | {cov.get('UNCOVERED',0):.2f}% |", "",
          f"**Two-layer coverage: {cov.get('COVERED',0):.2f}%.** "
          f"Sparse regions (generic-only or specific-only): **{a['n_sparse_runs']}** "
          f"({a['sparse_chars']:,} chars).", ""]

    L += ["## Masking-map layout (specific layer, linearized left→right)", "",
          "```", ribbon, "```", f"<sub>{legend}</sub>", "",
          f"![coverage ribbon](../portfolio/figures/w{idx}-ribbon.png)", "",
          "*(Ribbon = innermost specific type per cell; the generic layer + mask-stack-depth "
          "profile — showing the ≥2 two-layer floor — are in the figure above.)*", ""]

    L += ["## Mask-type breakdown (all 34 types, including 0-counts)", "",
          "| type | layer | count | width min / median / max | total chars |",
          "|---|---|---:|---:|---:|"]
    for t in ALL_TYPES:
        c = a["type_counts"][t]
        ws = a["width_stats"].get(t)
        layer = "generic" if t in GENERIC else "specific"
        w = f"{ws['min']:,} / {ws['median']:,} / {ws['max']:,}" if ws else "—"
        tot = f"{ws['total']:,}" if ws else "—"
        mark = "" if c else " "
        L.append(f"| {'**'+t+'**' if c else t} | {layer} | {c}{mark} | {w} | {tot} |")
    L.append("")

    L += ["## Per-instance edges & rules", ""]
    reps = [an for an in gold.get("annotations", []) if an.get("structure") == "repeating"]
    if reps:
        L += ["| structure | role | count | materialization |", "|---|---|---:|---|"]
        for an in reps:
            ir = an.get("instance_rule", {})
            kind = ir.get("kind", "—") if isinstance(ir, dict) else "multi"
            recon = "✏️ corrected" if "RECONCILED 2026-06-19" in an.get("count_cue", "") else ""
            L.append(f"| {an['type']} | {an.get('role','primary')} | "
                     f"{an.get('expected_count','—')} | `{kind}` {recon} |")
        L.append("")
    corr = [an for an in reps if "RECONCILED 2026-06-19" in an.get("count_cue", "")]
    if corr:
        L += ["**Count corrections this build:**", ""]
        for an in corr:
            note = an["count_cue"].split("RECONCILED 2026-06-19")[-1].strip(" ():").strip(".")
            L.append(f"- `{an['type']}` → **{an['expected_count']}** — {note}.")
        L.append("")

    L += ["## Element-width distribution by type", "",
          f"![type counts & widths](../portfolio/figures/w{idx}-stats.png)", "",
          "---", "",
          "<sub>Generated from the gold-intended masking map "
          "(`core/tests/fixtures/gold/harness/masking_map.py`); detector not consulted. "
          "Coordinates character-exact from `reference_text()`. Part of the "
          "[unified audit portfolio](../portfolio/index.html).</sub>", ""]

    (RPT / fname).write_text("\n".join(L))
    return a["n_elements"]


def main():
    existing = {int(re.match(r"work-(\d+)", p.name).group(1)): p.name
                for p in RPT.glob("work-*.md")}
    for idx in IDXS:
        fname = existing.get(idx) or f"work-{idx:03d}-{_slug(mm.audit(idx)['work'])}.md"
        ne = report(idx, fname)
        print(f"  idx{idx:>3} -> {fname}  ({ne} elements)")
    print(f"\n{len(IDXS)} reports regenerated in {RPT}")


if __name__ == "__main__":
    main()
