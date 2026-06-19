# Masking-Map Audit — Methodology

This document defines the terms, rules, and data provenance for the per-work masking-map audits
in `reports/` and the cross-work `README.md` index. The audits replace the loose narrative in
`core/tests/fixtures/gold/ratification-results.md` with a reproducible, character-level analysis.

## 1. What a "masking map" is

The **masking map** of a text is the set of mask elements that annotate it — each element being a
`(type, start, end)` triple. Masks may **stack**: a single character can be covered by several
elements at once (e.g. a title-page line is inside `front_matter` *and* inside `volume`).

## 2. Generic vs. specific mask types

Every character should be covered by **two complementary layers**:

- **GENERIC** — broad nesting containers that *locate* text in the work's hierarchy but do not
  identify a small structural element. They "don't count" toward specific coverage:
  > `body`, `volume`, `book`, `part`, `chapter`

  (This matches the codebase's containment hierarchy `_TYPE_LEVEL`: body 0 ⊃ volume 1 ⊃ book/part 2
  ⊃ chapter 3.)

- **SPECIFIC** — every other type: the distinguishable structural / apparatus elements.
  > `front_matter, title_page, copyright, contents, dedication, foreword, preface, introduction,`
  > `epigraph, header, chapter_heading, footnotes, endnotes, translation, commentary, back_matter,`
  > `afterword, acknowledgments, about_author, discussion, glossary, index, bibliography, appendix,`
  > `addendum, insert, colophon, letter, poetry`

**Borderline calls (open for review):** `letter`, `poetry`, and `commentary` are *unmasked*
(`mask=False`) content units, yet are classed **specific** here — a letter or poem *is* a discrete,
nameable element, so text inside one is "specifically covered." If Sir prefers these to count as
generic content-containers, flip them in `GENERIC`/`SPECIFIC` in `masking_audit.py` and regenerate.

## 3. The two-layer coverage ideal

> Every single character of a text should be covered by **at least one GENERIC** mask **and at least
> one SPECIFIC** mask. Masks may stack many layers deep where evidence supports each. No character
> should be left with only generic containers, and none should be left unmasked.

Example: a title-page character is covered by `volume` (generic) + `front_matter` (specific) → ideal.
A bare verse covered only by `book`+`chapter` (both generic) → **violates** the ideal (generic-only).

## 4. Interval classification

The text is swept into maximal intervals between consecutive element boundaries. Each interval is:

| Class | Condition | Meaning |
|---|---|---|
| `COVERED` | ≥1 generic AND ≥1 specific | the ideal |
| `GENERIC_ONLY` | ≥1 generic, 0 specific | located in a container, but no specific element |
| `SPECIFIC_ONLY` | 0 generic, ≥1 specific | a specific element outside any container (unusual) |
| `UNCOVERED` | 0 masks | a hole in the map |

A region is **MASK-SPARSE** when covered by **≤1 mask type** total. Reports flag the
`UNCOVERED`, `GENERIC_ONLY`, and `SPARSE` regions with coordinates and text excerpts.

## 5. Data provenance — important

- **The map under audit is the *current materialized* map**: the typed, bounded sections the
  production layout pipeline emits (`detect_layout_sections(_layout_boundaries(proj), …)` over the
  project's `reference_text()`). This is the only **complete coordinate** map that exists.
- **The gold contract is the *target*, overlaid** in each report's type-coverage-gap table. The gold
  stores **types + counts + a few exemplar anchors** — **not** a per-instance edge for every element.
  Therefore the gold's *intended* coverage cannot itself be verified at character level today; the
  current-map audit is the achievable proxy and exposes where the map falls short of the gold target.

## 6. Visualization

- **Coverage ribbon** — the text linearized into 100 columns; each column shows the *least-covered*
  class touching it (so gaps never hide): `█` covered · `▓` specific-only · `▒` generic-only ·
  `·` uncovered.
- **Specific-type lanes** — one row per specific type, marking the columns where it appears.
- **Stacking-depth histogram** — chars by number of masks covering them.

## 7. Reproducing

```
.scratch/mask-eval/masking_audit.py all      # regenerate every per-work report
.scratch/mask-eval/masking_audit.py index    # regenerate the cross-work README.md
.scratch/mask-eval/masking_audit.py <idx>     # a single work
.scratch/mask-eval/masking_audit.py <idx> --json   # machine-readable summary
```

## 8. Known limitations & recommended next steps

1. **No per-instance edges in the gold.** To *establish* (not just measure) the two-layer guarantee,
   the gold needs a stored edge for every element (Phase-2 directive #1). Until then, repeating
   specific types (e.g. `footnotes`×6280) are asserted by count, not mapped.
2. **Detector under-emits specific types.** 12/20 works show <1% two-layer coverage because the
   production pipeline materializes containers (`book`/`chapter`) but few specific elements across the
   body. Closing this needs detector work to emit `chapter_heading`, `translation`, `commentary`,
   `footnotes`, etc. as bounded sections.
3. **Generic/specific assignment of `letter`/`poetry`/`commentary`** is a deliberate, reviewable
   choice (§2).
