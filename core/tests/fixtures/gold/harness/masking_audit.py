#!/usr/bin/env python
"""Masking-map audit engine for the Palimpsest gold set.

For a gold work, materializes the *current* masking map (the detector's typed,
bounded sections), then runs a character-level coverage analysis against the
two-layer ideal: every character should be covered by at least one GENERIC
container mask AND at least one SPECIFIC structural-element mask.

GENERIC (broad nesting containers that tile/nest the work — they locate text in
the hierarchy but do not identify a small structural element; "don't count"):
    body, volume, book, part, chapter
SPECIFIC (everything else — the distinguishable structural / apparatus elements,
including the unmasked content units letter/poetry/commentary):
    front_matter, title_page, copyright, contents, dedication, foreword, preface,
    introduction, epigraph, header, chapter_heading, footnotes, endnotes,
    translation, commentary, back_matter, afterword, acknowledgments, about_author,
    discussion, glossary, index, bibliography, appendix, addendum, insert, colophon,
    letter, poetry

Per-interval classification (interval = maximal gap between consecutive boundaries):
    UNCOVERED      0 masks                       (gap in the map)
    GENERIC_ONLY   >=1 generic, 0 specific       (located but no specific element)
    SPECIFIC_ONLY  0 generic, >=1 specific       (specific element outside any container)
    COVERED        >=1 generic AND >=1 specific  (the ideal)
A region is MASK-SPARSE when covered by <=1 mask type total.

Usage:
    masking_audit.py <idx> [<idx> ...]      # write per-work report(s)
    masking_audit.py all                    # every ingested gold work
    masking_audit.py <idx> --json           # print machine-readable summary only
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "core"))

from harness import (  # noqa: E402
    _endnote_separator,
    _layout_boundaries,
    detect_layout_sections,
    project_for,
    work_order,
    short,
)
from palimpsest.layout import SECTION_LABELS, SECTION_TYPES  # noqa: E402

GOLD_DIR = REPO / "core/tests/fixtures/gold"
OUT_DIR = REPO / "docs/development/audits/masking-map/reports"

GENERIC = {"body", "volume", "book", "part", "chapter"}
SPECIFIC = set(SECTION_TYPES) - GENERIC

# ── coverage computation ──────────────────────────────────────────────────────


def _intervals(sections, text_len):
    """Maximal intervals between consecutive boundaries, with covering sections."""
    pts = sorted({0, text_len} | {s.start for s in sections} | {s.end for s in sections})
    out = []
    for a, b in zip(pts, pts[1:]):
        if a >= b:
            continue
        cov = [s for s in sections if s.start <= a and s.end >= b]
        gen = sorted({s.type for s in cov if s.type in GENERIC})
        spec = sorted({s.type for s in cov if s.type in SPECIFIC})
        out.append({"start": a, "end": b, "len": b - a, "generic": gen, "specific": spec,
                    "depth": len(cov), "ntypes": len(set(s.type for s in cov))})
    return out


def _classify(iv):
    g, s = bool(iv["generic"]), bool(iv["specific"])
    if not g and not s:
        return "UNCOVERED"
    if g and not s:
        return "GENERIC_ONLY"
    if s and not g:
        return "SPECIFIC_ONLY"
    return "COVERED"


CLASS_GLYPH = {"UNCOVERED": "·", "GENERIC_ONLY": "▒", "SPECIFIC_ONLY": "▓", "COVERED": "█"}
CLASS_LABEL = {
    "UNCOVERED": "uncovered (0 masks)",
    "GENERIC_ONLY": "generic-only (container, no specific element)",
    "SPECIFIC_ONLY": "specific-only (element outside any container)",
    "COVERED": "covered (>=1 generic + >=1 specific)",
}


def audit(idx: int) -> dict:
    proj = project_for(idx)
    if proj is None:
        raise SystemExit(f"work {idx} not ingested")
    text = proj.reference_text()
    n = len(text)
    sections = detect_layout_sections(
        _layout_boundaries(proj), n, _endnote_separator(proj.path), text=text)
    ivs = _intervals(sections, n)
    for iv in ivs:
        iv["class"] = _classify(iv)

    by_class = {k: 0 for k in CLASS_GLYPH}
    for iv in ivs:
        by_class[iv["class"]] += iv["len"]

    by_type = {}
    for s in sections:
        by_type[s.type] = by_type.get(s.type, 0) + 1

    # depth histogram (how many masks stack on a character, weighted by chars)
    depth_hist: dict[int, int] = {}
    for iv in ivs:
        depth_hist[iv["depth"]] = depth_hist.get(iv["depth"], 0) + iv["len"]

    # flagged regions: uncovered, generic-only, and sparse (<=1 type) — merged-adjacent
    def runs_of(pred):
        runs = []
        for iv in ivs:
            if pred(iv):
                if runs and iv["start"] - runs[-1]["end"] <= 1:
                    runs[-1]["end"] = iv["end"]
                else:
                    runs.append({"start": iv["start"], "end": iv["end"],
                                 "generic": iv["generic"], "specific": iv["specific"]})
        for r in runs:
            r["len"] = r["end"] - r["start"]
            r["excerpt"] = " ".join(text[r["start"]:r["start"] + 110].split())
        return sorted(runs, key=lambda r: r["len"], reverse=True)

    uncovered = runs_of(lambda iv: iv["class"] == "UNCOVERED")
    generic_only = runs_of(lambda iv: iv["class"] == "GENERIC_ONLY")
    sparse = runs_of(lambda iv: iv["ntypes"] <= 1)

    # gold overlay
    gold = json.loads((GOLD_DIR / f"work-{idx}.json").read_text())
    gold_rows = []
    for a in gold["annotations"]:
        t = a["type"]
        gold_rows.append({"type": t, "expected": a.get("expected_count"),
                          "detected": by_type.get(t, 0),
                          "kind": "generic" if t in GENERIC else "specific"})

    return {
        "idx": idx, "work": gold.get("work", short(work_order()[idx].name)),
        "source_file": gold.get("source_file", ""), "text_len": n,
        "n_sections": len(sections), "by_type": by_type,
        "by_class_chars": by_class,
        "by_class_pct": {k: round(100 * v / n, 2) for k, v in by_class.items()},
        "depth_hist": depth_hist,
        "uncovered": uncovered, "generic_only": generic_only, "sparse": sparse,
        "gold": gold_rows,
        "sections": [{"start": s.start, "end": s.end, "type": s.type,
                      "label": (getattr(s, "label", "") or "")[:60]} for s in sections],
        "_text": text,
    }


# ── visualization ─────────────────────────────────────────────────────────────


def _ribbon(ivs_classed, text_len, width=100):
    """A linearized coverage ribbon: each column = text_len/width chars, glyph = the
    *worst* (least-covered) class touching that column, so gaps never hide."""
    order = ["UNCOVERED", "GENERIC_ONLY", "SPECIFIC_ONLY", "COVERED"]
    col = [None] * width
    per = text_len / width
    for iv in ivs_classed:
        c0 = int(iv["start"] / per)
        c1 = min(width - 1, int((iv["end"] - 1) / per))
        rank = order.index(iv["class"])
        for c in range(c0, c1 + 1):
            if col[c] is None or rank < order.index(col[c]):
                col[c] = iv["class"]
    return "".join(CLASS_GLYPH[c or "UNCOVERED"] for c in col)


def _type_lanes(sections, text_len, width=100):
    """One row per specific type present, marking columns where it appears."""
    per = text_len / width
    lanes = {}
    for s in sections:
        if s.type in GENERIC:
            continue
        row = lanes.setdefault(s.type, [" "] * width)
        c0 = int(s.start / per)
        c1 = min(width - 1, int(max(s.start, s.end - 1) / per))
        for c in range(c0, c1 + 1):
            row[c] = "▏" if row[c] == " " else "█"
    return {t: "".join(r) for t, r in sorted(lanes.items())}


def render(a: dict) -> str:
    n = a["text_len"]
    ivs = []
    # rebuild classed intervals for the ribbon from sections (cheap re-derive)
    proj_sections = a["sections"]

    class _S:  # lightweight stand-in with start/end/type
        __slots__ = ("start", "end", "type")

        def __init__(s, d):
            s.start, s.end, s.type = d["start"], d["end"], d["type"]
    secs = [_S(d) for d in proj_sections]
    ivs = _intervals(secs, n)
    for iv in ivs:
        iv["class"] = _classify(iv)

    L = []
    L.append(f"# Masking-Map Audit — [{a['idx']}] {a['work']}")
    L.append("")
    L.append(f"- **Source file:** `{a['source_file']}`")
    L.append(f"- **Text length:** {n:,} chars")
    L.append(f"- **Sections in current map:** {a['n_sections']}")
    L.append(f"- **Distinct mask types present:** {len(a['by_type'])} "
             f"({sum(1 for t in a['by_type'] if t in GENERIC)} generic, "
             f"{sum(1 for t in a['by_type'] if t in SPECIFIC)} specific)")
    L.append("")

    L.append("## What this audits (provenance & method)")
    L.append("")
    L.append("- **Map under audit = the *current materialized* masking map**: the typed, bounded "
             "sections the production layout pipeline emits for this work "
             "(`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete "
             "coordinate map that exists today.")
    L.append("- **The gold contract is the *target*, overlaid** in the gap table below. The gold "
             "stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for "
             "every element — so the gold's *intended* coverage cannot itself be verified at "
             "character level until per-instance edges exist (Phase-2 directive #1). The "
             "current-map audit is the achievable proxy and exposes where the map falls short of "
             "the gold target.")
    L.append("- **Generic** (broad nesting containers — locate text but do not name a specific "
             "element): `body, volume, book, part, chapter`. **Specific** = every other type "
             "(front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, "
             "commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND "
             "≥1 specific mask.")
    L.append("")

    # coverage summary
    L.append("## Coverage summary (character-level)")
    L.append("")
    L.append("| Class | Chars | % of text |")
    L.append("|---|---:|---:|")
    for k in ["COVERED", "GENERIC_ONLY", "SPECIFIC_ONLY", "UNCOVERED"]:
        L.append(f"| {CLASS_GLYPH[k]} {CLASS_LABEL[k]} | {a['by_class_chars'][k]:,} | "
                 f"{a['by_class_pct'][k]:.2f}% |")
    L.append("")
    twolayer = a["by_class_pct"]["COVERED"]
    L.append(f"**Two-layer coverage (>=1 generic + >=1 specific): {twolayer:.2f}% of the text.** "
             f"The remaining {100 - twolayer:.2f}% violates the coverage ideal.")
    L.append("")

    # ribbon
    L.append("## Masking-map layout (linearized, left→right = start→end of text)")
    L.append("")
    L.append("```")
    L.append("0%" + " " * 46 + "50%" + " " * 45 + "100%")
    L.append(_ribbon(ivs, n, 100))
    L.append("")
    L.append("legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered")
    L.append("         (each column ≈ {:,} chars; column shows the LEAST-covered class present)".format(round(n / 100)))
    L.append("```")
    L.append("")

    # type lanes
    lanes = _type_lanes(secs, n, 100)
    if lanes:
        L.append("### Specific-type lanes (where each specific mask appears)")
        L.append("")
        L.append("```")
        for t, row in lanes.items():
            L.append(f"{SECTION_LABELS.get(t, t)[:18]:18}|{row}|")
        L.append("```")
        L.append("")

    # stacking depth
    L.append("## Mask stacking depth (how many masks cover a character)")
    L.append("")
    L.append("| Depth | Chars | % |")
    L.append("|---:|---:|---:|")
    for d in sorted(a["depth_hist"]):
        L.append(f"| {d} | {a['depth_hist'][d]:,} | {100 * a['depth_hist'][d] / n:.2f}% |")
    L.append("")

    # gold overlay / gap
    L.append("## Gold contract vs. detector map (type-coverage gap)")
    L.append("")
    L.append("| Mask type | Kind | Gold expected | Detector found | Status |")
    L.append("|---|---|---:|---:|---|")
    for g in a["gold"]:
        exp = g["expected"] if g["expected"] is not None else "—"
        det = g["detected"]
        if det == 0:
            status = "❌ ABSENT from map"
        elif g["expected"] and isinstance(g["expected"], int) and det < g["expected"]:
            status = f"⚠ under ({det}/{g['expected']})"
        else:
            status = "✓ present"
        L.append(f"| {SECTION_LABELS.get(g['type'], g['type'])} | {g['kind']} | {exp} | {det} | {status} |")
    L.append("")

    # flagged regions
    def flagged_table(title, runs, note, limit=12):
        L.append(f"## {title}")
        L.append("")
        if not runs:
            L.append(f"_None — {note}_")
            L.append("")
            return
        total = sum(r["len"] for r in runs)
        L.append(f"{len(runs)} region(s), {total:,} chars ({100 * total / n:.2f}% of text). "
                 f"Largest {min(limit, len(runs))}:")
        L.append("")
        L.append("| start | end | chars | covered by | excerpt |")
        L.append("|---:|---:|---:|---|---|")
        for r in runs[:limit]:
            cov = ", ".join(r["generic"] + r["specific"]) or "—"
            exc = r["excerpt"].replace("|", "¦")[:80]
            L.append(f"| {r['start']:,} | {r['end']:,} | {r['len']:,} | {cov} | {exc} |")
        L.append("")

    flagged_table("⚠ Uncovered regions (0 masks)", a["uncovered"],
                  "every character carries at least one mask")
    flagged_table("⚠ Generic-only regions (container mask, but NO specific element)",
                  a["generic_only"], "every character carries a specific mask too")
    flagged_table("⚠ Mask-sparse regions (≤1 mask type total)", a["sparse"],
                  "every character is covered by ≥2 mask types")

    return "\n".join(L)


def write_index(idxs):
    rows = []
    for idx in idxs:
        a = audit(idx)
        rows.append(a)
    rows.sort(key=lambda a: a["by_class_pct"]["COVERED"])
    L = ["# Masking-Map Audit — Cross-Work Index",
         "",
         "Per-work character-level coverage of the **current materialized masking map** against the "
         "two-layer ideal (every character covered by ≥1 generic container mask AND ≥1 specific "
         "structural-element mask). See `../METHODOLOGY.md` for definitions and provenance. One "
         "report per work in `reports/`.",
         "",
         "## Coverage ranking (worst → best two-layer coverage)",
         "",
         "| idx | Work | chars | sections | covered | generic-only | uncovered | specific types in map |",
         "|---:|---|---:|---:|---:|---:|---:|---:|"]
    for a in rows:
        nspec = sum(1 for t in a["by_type"] if t in SPECIFIC)
        L.append(f"| {a['idx']} | [{a['work'][:42]}](reports/{_slug(a)}) | {a['text_len']:,} | "
                 f"{a['n_sections']} | {a['by_class_pct']['COVERED']:.1f}% | "
                 f"{a['by_class_pct']['GENERIC_ONLY']:.1f}% | {a['by_class_pct']['UNCOVERED']:.1f}% | "
                 f"{nspec} |")
    L.append("")
    # aggregate findings
    n = len(rows)
    zero = [a for a in rows if a["by_class_pct"]["COVERED"] < 1.0]
    high = [a for a in rows if a["by_class_pct"]["COVERED"] >= 50.0]
    L.append("## Aggregate findings")
    L.append("")
    L.append(f"- **{len(zero)}/{n} works** have effectively **no two-layer coverage** (<1%): the "
             "current map locates the text in containers but assigns essentially no specific "
             "structural element across the body.")
    L.append(f"- **{len(high)}/{n} works** reach ≥50% two-layer coverage — all are scholarly "
             "translation/anthology works whose `translation`/`commentary`/`part` layers the "
             "detector segments richly.")
    L.append("- The split is bimodal: coverage tracks how much *specific* structure the production "
             "pipeline currently materializes, not how much the gold *declares*. Gold types absent "
             "from each map are tabulated per report (the type-coverage gap).")
    L.append("- **Root limitation:** the gold stores counts + exemplars, not per-instance edges, so "
             "the gold's intended character-level coverage is not directly verifiable. Establishing "
             "the “every character ≥1 generic + ≥1 specific” guarantee requires per-instance edge "
             "generation (Phase-2 directive #1) plus detector emission of the specific types.")
    L.append("")
    (OUT_DIR.parent / "README.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote index: {OUT_DIR.parent / 'README.md'}")


def _slug(a):
    s = (a["work"][:40].lower().replace(" ", "-").replace("/", "-")
         .replace("(", "").replace(")", "").replace(",", "").replace("'", ""))
    return f"work-{a['idx']:03d}-{s}.md"


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    as_json = "--json" in sys.argv
    all_idxs = [i for i in range(len(work_order())) if project_for(i) is not None
                and (GOLD_DIR / f"work-{i}.json").exists()]
    if args == ["index"]:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        write_index(all_idxs)
        return
    if args == ["all"]:
        idxs = [i for i in range(len(work_order())) if project_for(i) is not None
                and (GOLD_DIR / f"work-{i}.json").exists()]
    else:
        idxs = [int(x) for x in args]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for idx in idxs:
        a = audit(idx)
        if as_json:
            a.pop("_text", None)
            print(json.dumps({k: v for k, v in a.items() if k != "sections"}, indent=2))
            continue
        slug = (a["work"][:40].lower().replace(" ", "-").replace("/", "-")
                .replace("(", "").replace(")", "").replace(",", "").replace("'", ""))
        path = OUT_DIR / f"work-{idx:03d}-{slug}.md"
        path.write_text(render(a), encoding="utf-8")
        written.append((idx, a["by_class_pct"]["COVERED"], path.name))
        print(f"[{idx:>3}] two-layer-covered={a['by_class_pct']['COVERED']:5.1f}%  → {path.name}")
    return written


if __name__ == "__main__":
    main()
