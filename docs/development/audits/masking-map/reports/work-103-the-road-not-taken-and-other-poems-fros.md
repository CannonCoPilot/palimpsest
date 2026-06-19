# Masking-Map Audit — [103] The Road Not Taken and Other Poems (Frost)

- **Source file:** `The Road Not Taken and Other Poems -- Frost, Robert -- 2012 -- Dover Publications -- isbn13 9780486111292 -- 9d94b2c221d6d795f99642712ed2d7d0 -- Anna’s Archive.epub`
- **Text length:** 71,309 chars
- **Sections in current map:** 3
- **Distinct mask types present:** 3 (1 generic, 2 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 0 | 0.00% |
| ▒ generic-only (container, no specific element) | 69,507 | 97.47% |
| ▓ specific-only (element outside any container) | 1,802 | 2.53% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.00% of the text.** The remaining 100.00% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 713 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Front Matter      |▏▏▏                                                                                                 |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 71,174 | 99.81% |
| 2 | 135 | 0.19% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Poetry | specific | 28 | 0 | ❌ ABSENT from map |
| Preface | specific | — | 0 | ❌ ABSENT from map |
| Dedication | specific | — | 0 | ❌ ABSENT from map |
| Contents | specific | — | 0 | ❌ ABSENT from map |
| Index | specific | — | 0 | ❌ ABSENT from map |
| Back Matter | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

1 region(s), 69,507 chars (97.47% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 1,802 | 71,309 | 69,507 | body | Note Mountain Interval, reprinted here in the unabridged text of its original 19 |

## ⚠ Mask-sparse regions (≤1 mask type total)

1 region(s), 71,174 chars (99.81% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 135 | 71,309 | 71,174 | front_matter | Manufacturing books in the United States ensures compliance with strict environm |
