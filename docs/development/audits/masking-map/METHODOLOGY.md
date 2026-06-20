# Masking-Map Audit — Methodology

This document defines the terms, rules, and data provenance for the per-work masking-map audits in
[`reports/`](reports/), the cross-work [`README.md`](README.md) index, and the visual
[`portfolio/`](portfolio/index.html). The audits supersede the loose narrative in the former
`ratification-results.md` with a reproducible, character-level analysis of each work's **complete,
hand-verified gold masking map**.

## 1. What a "masking map" is

The **masking map** of a text is the set of mask elements that annotate it — each element a
`(type, start, end)` triple. Masks **stack**: one character can be covered by several elements at
once (e.g. a verse is inside `book` *and* `chapter`, a note is inside `chapter` *and* `footnotes`).

## 2. Generic vs. specific mask types

Every character must be covered by **two complementary layers**:

- **GENERIC** — the broad nesting containers that *locate* text in the work's hierarchy but do not
  name a small structural element (4 types):
  > `body`, `volume`, `book`, `part`
- **SPECIFIC** — every other type (30), the distinguishable structural / apparatus elements,
  **including `chapter`**:
  > `chapter`, `chapter_heading`, `poetry`, `letter`, `commentary`, `translation`, `epigraph`,
  > `header`, `footnotes`, `endnotes`, `front_matter`, `title_page`, `copyright`, `contents`,
  > `dedication`, `foreword`, `preface`, `introduction`, `back_matter`, `afterword`,
  > `acknowledgments`, `about_author`, `discussion`, `glossary`, `index`, `bibliography`,
  > `appendix`, `addendum`, `insert`, `colophon`

> **`chapter` counts as SPECIFIC** (ratified 2026-06-19). A chapter is a discrete, nameable
> structural unit, so a plain prose chapter masked by `body`+`chapter` already satisfies the
> two-layer ideal. Only the four broad containers are generic.

## 3. The two-layer coverage ideal

> At **every coordinate position** the mask stack must be **≥2 deep — at least one GENERIC and at
> least one SPECIFIC** mask. This is a per-*position* depth requirement, not a per-character mask:
> masks span ranges and stack many layers deep where evidence supports each.

`body[0,EOF]` is added as the universal generic base for every work, so in practice the audit
verifies that the **SPECIFIC layer tiles 100% of the text** — front matter → content instances
(chapters / poems / verses / letters / translations) → back matter, contiguous, no gaps.

## 4. Interval classification

The text is swept into maximal intervals between consecutive element boundaries; each is:

| Class | Condition | Meaning |
|---|---|---|
| `COVERED` | ≥1 generic AND ≥1 specific | the ideal |
| `GENERIC_ONLY` | ≥1 generic, 0 specific | located in a container, but no specific element |
| `SPECIFIC_ONLY` | 0 generic, ≥1 specific | a specific element outside any container |
| `UNCOVERED` | 0 masks | a hole in the map |

**Gate:** a finalized map is `{COVERED: 100.0%}` exactly — 0 `GENERIC_ONLY`, 0 `SPECIFIC_ONLY`,
0 `UNCOVERED`. All 20 works meet this.

## 5. Data provenance — the GOLD's intended map

The map under audit is the **gold's own intended masking map**, built by close reading of the actual
text — **the production detector is not consulted.** It is assembled by
[`.scratch/mask-eval/masking_map.py`](../../../../.scratch/mask-eval/masking_map.py) as:

```
body[0,EOF]  +  gold singular masks  +  completion masks (SUPPLEMENT)
             +  per-instance repeating elements (instance_edges.RULES / CUSTOM_ELEMENTS)
```

**Per-instance edges, materialized — never stored.** Each repeating structure (chapters, poems,
verses, letters, translations, footnotes …) carries an executable **instance rule** that materializes
all of its per-instance boundaries from `reference_text()` at eval time, consistent with the gold
schema's "offsets derived at eval time, never stored" principle. A rule is trusted only when its
materialized instance count reconciles to the hand-verified `expected_count` (the **count gate**).
Rule kinds: `roman_in_span`, `title_list`, `regex_in_span` (tiled partition or thin markers),
`salutation`, and computed-offset `CUSTOM_ELEMENTS` for interleaved sub-blocks.

> This resolves the prior audit's central limitation. The earlier reports graded the *detector's*
> output and noted the gold "stores counts + exemplars, not per-instance edges." The per-instance
> pass closes that gap: the gold's intended coverage is now verified at character level, and the
> reconciled rules + corrected counts are recorded in each `gold/work-*.json` (`instance_rule`,
> `map_status`).

## 6. Visualization (portfolio)

Per work: a **coverage ribbon** (the specific layer linearized, coloured by innermost type) over a
**generic-layer** ribbon and a **mask-stack-depth profile** (with the red ≥2 two-layer floor); a
**type-count breakdown** of all 34 types including 0-counts; and **element-width** min–max–mean by
type. Cross-work: a summary table and a **type-presence matrix**.

## 7. Reproducing

```
.venv/bin/python .scratch/mask-eval/masking_map.py audit <idx>   # coverage audit, one work
.venv/bin/python .scratch/mask-eval/masking_map.py map   <idx>   # the materialized element list
.venv/bin/python .scratch/mask-eval/instance_edges.py reconcile <idx>   # count-gate check
.venv/bin/python .scratch/mask-eval/portfolio.py                 # regenerate the HTML portfolio + figures
.venv/bin/python .scratch/mask-eval/gen_reports.py               # regenerate per-work reports
.venv/bin/python .scratch/mask-eval/gen_index.py                 # regenerate this README index
.venv/bin/python core/tests/fixtures/gold/gold_verify.py         # gold-contract consistency
```

## 8. Status & disclosed judgment calls

All 20 maps meet the three gates (100% accurate, 100% precise, two-layer everywhere). Remaining
type-judgment notes, surfaced rather than hidden:

1. **idx48** — the numbered + lettered note apparatuses are inseparably interleaved with numbered
   prose (`^N.` collides with prose enumeration); carving footnote spans would mis-type prose
   (*reducing* accuracy), so notes are covered by the per-text `introduction` tile.
2. **idx107** — the 30 Juz' (`part`) headings are OCR-destroyed in-body; `part` is generic, so the
   guarantee is met by `body` + the surah `chapter` layer.
3. **idx101** — per-page footnote bands are not recoverable from the linear stream; typed as 8,404
   per-entry markers.
4. **idx6** — the Geneva e-text is physically scrambled (1133 materialized chapter units vs 1189
   canonical) and is the 66-book Protestant canon (no Apocrypha); counts reflect the physical text.
