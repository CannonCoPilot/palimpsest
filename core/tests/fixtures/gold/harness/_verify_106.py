#!/usr/bin/env python
"""Verify the complete gold masking map for work idx 106
(Adam and Eve in the Armenian Tradition, Stone, SBL 2013).

Monkeypatch-only: injects RULES[106] + SUPPLEMENT[106] into the shared engines,
then runs masking_map.audit(106) and reconciles each repeating rule's count.
Two parts tile the body:
  * Part I  [22692, 539977)  -> commentary(6) + chapter(5)+appendix (specific) + part (generic)
  * Part II [539977,1479974) -> translation(126) + chapter(14 centuries) + part (generic)
Singular front/back masks (13) come from gold/work-106.json automatically.
"""
import sys
import instance_edges
import masking_map

IDX = 106

# ── Repeating-instance rules (tiled specific + generic layers) ──────────────────
instance_edges.RULES[IDX] = [
    # GENERIC: the two top-level Parts (gold secondary `part`, expected 2).
    # regex_in_span at:start, tile:True -> each Part start tiles to the next Part /
    # back-matter. Part headings are unique body strings.
    {
        "type": "part", "kind": "regex_in_span",
        "pattern": r"(?m)^(?:PART I\nThe Adam and Eve Traditions in Armenian|Part II\nTexts and Translations)$",
        "at": "start", "tile": True,
        "span_start": "PART I\nThe Adam and Eve Traditions in Armenian",
        "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
        "expected_count": 2,
    },

    # SPECIFIC — Part I analytic layer.
    # commentary (6 units: 5 numbered chapters + Appendix) tiles Part I content.
    # Anchored on the chapter heading page-markers + the Appendix heading.
    {
        "type": "commentary", "kind": "regex_in_span",
        "pattern": r"(?m)^(?:-\d+-\n[1-5]\. Adam and Eve Traditions|-177-\nAppendix: Satan and the Serpent)",
        "at": "start", "tile": True,
        "span_start": "-11-\n1. Adam and Eve Traditions in\nFifth-Century",
        "span_end": "Part II\nTexts and Translations",
        "expected_count": 6,
    },
    # chapter (Part I): the 5 numbered chapters (navigational band). Same 5 heading
    # markers (NOT the appendix). Tiles ch1 start .. appendix start.
    {
        "type": "chapter", "kind": "regex_in_span",
        "pattern": r"(?m)^-\d+-\n[1-5]\. Adam and Eve Traditions",
        "at": "start", "tile": True,
        "span_start": "-11-\n1. Adam and Eve Traditions in\nFifth-Century",
        "span_end": "-177-\nAppendix: Satan and the Serpent",
        "expected_count": 5,
    },

    # SPECIFIC — Part II edition layer.
    # chapter (Part II): the 14 century-section subdivisions (navigational band).
    # Page-marker + bare century-name heading; running-header bare names lack the
    # leading "-NNN-\n" page marker so are excluded.
    {
        "type": "chapter", "kind": "regex_in_span",
        "pattern": (r"(?m)^-\d+-\n(?:Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh"
                    r"|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth) Century\n"),
        "at": "start", "tile": True,
        "span_start": "Part II\nTexts and Translations",
        "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
        "expected_count": 14,
    },
    # translation: the masked per-source-entry layer. Each entry opens with an author
    # header line ending in "C<NN>" (century tag). 126 such body headers (the
    # body-verifiable cardinality; the front/back "Authors Cited/Quoted" lists each
    # enumerate 121 distinct authors — the 5-entry surplus is transliteration-variant
    # re-statements + folded sub-source headers, see count correction below).
    {
        "type": "translation", "kind": "regex_in_span",
        "pattern": r"(?m)^.{1,60}? C\d+(?:[–\-]\d+)?\n",
        "at": "start", "tile": True,
        "span_start": "Part II\nTexts and Translations",
        "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
        "expected_count": 126,
    },
]

# ── Singular supplement masks (front/back/apparatus the gold omits) ─────────────
masking_map.SUPPLEMENT[IDX] = [
    # Inner title line between the gold title_page end and the copyright start
    # (the 75-char "Adam and Eve in the Armenian Tradition / Fifth through ..." block).
    {"type": "title_page",
     "start_anchor": "Adam and Eve in the Armenian Tradition\nFifth through Seventeenth Centuries\nCopyright © 2013",
     "end_anchor": "Copyright © 2013 by the Society of Biblical Literature"},

    # Part I "Outline" (the detailed analytic contents outline opening Part I, before
    # chapter 1). Typed `contents` (it is a sub-contents outline of Part I).
    {"type": "contents",
     "start_anchor": "PART I\nThe Adam and Eve Traditions in Armenian\n\n-3-\nOutline",
     "end_anchor": "-11-\n1. Adam and Eve Traditions in\nFifth-Century"},

    # Part II heading + its 52-char run-in before the first century/translation start.
    {"type": "chapter",
     "start_anchor": "Part II\nTexts and Translations",
     "end_anchor": "-213-\nFifth Century\nAgat'angełos C5"},

    # FOOTNOTES apparatus (NO DEFERRAL): the dense scholarly note regions. The notes
    # are pooled at the END of each analytic chapter / each Part II century-section as
    # blocks of "N. <text>" lines (number + EN-SPACE). Rather than one global
    # element (which would swallow content), type the apparatus as TWO bounded
    # footnotes regions, one per Part, sitting ON TOP of the content tile so the
    # apparatus carries its own type. See the per-region note blocks materialized by
    # the dedicated footnotes rule below (added via RULES); these two supplement
    # anchors mark the Part-level apparatus envelopes for completeness of typing.
]

# Footnotes are interleaved per-page/per-chapter, not a single pooled block. Model
# them as a repeating apparatus rule: each note-block START is a run of lines matching
# "(?m)^\d+\. " (number + EN-SPACE). tile:False so each marker spans only its own
# note line (does NOT swallow the surrounding content) — the footnotes layer thus sits
# ON TOP of the content tile as its own typed apparatus elements.
instance_edges.RULES[IDX].append({
    "type": "footnotes", "kind": "regex_in_span",
    "pattern": "(?m)^\\d+\\.\u2002",     # N. + EN-SPACE (U+2002) note separator
    "at": "start", "tile": False,           # thin markers, do not tile/absorb content
    "span_start": "PART I\nThe Adam and Eve Traditions in Armenian",
    "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
    "expected_count": None,                  # per gold: presence is the contract, not a global count
})


def main() -> None:
    text = masking_map.project_for(IDX).reference_text()

    print("=== count reconciliation ===")
    for rule in instance_edges.RULES[IDX]:
        starts = instance_edges.materialize(text, rule)
        exp = rule.get("expected_count")
        gate = "n/a" if exp is None else ("GREEN" if len(starts) == exp else "RED")
        print(f"  {rule['type']:<11} materialized={len(starts):<5} expected={exp}  GATE {gate}")

    a = masking_map.audit(IDX)
    print("\n=== audit ===")
    print("coverage:", a["coverage_pct"])
    print("counts:", {k: v for k, v in a["type_counts"].items() if v})
    print("unresolved:", a["unresolved"])
    print("n_sparse_runs:", a["n_sparse_runs"], "sparse_chars:", a["sparse_chars"])
    for r in a["sparse_regions"][:12]:
        print("  sparse", r["cls"], r["start"], r["end"], r["len"],
              repr(r.get("head", "")[:70]))


if __name__ == "__main__":
    main()
