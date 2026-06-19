# Masking-Map Audit — [19] The Correspondent

- **Source file:** `The Correspondent_ A Novel -- Virginia Evans -- 2025 -- Crown Publishing Group, The -- isbn13 9780593798430 -- f542b169cc729ca2fdc329d48c3911f5 -- Anna’s Archive.epub`
- **Text length:** 364,494 chars
- **Sections in current map:** 10
- **Distinct mask types present:** 10 (1 generic, 9 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 0 | 0.00% |
| ▒ generic-only (container, no specific element) | 328,513 | 90.13% |
| ▓ specific-only (element outside any container) | 35,981 | 9.87% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.00% of the text.** The remaining 100.00% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 3,645 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
About the Author  |                                                                                                   ▏|
Acknowledgments   |                                                                                                  ▏▏|
Back Matter       |                                                                                                  ▏▏|
Contents          |▏                                                                                                   |
Copyright         |▏                                                                                                   |
Discussion Questio|                                                                                                   ▏|
Front Matter      |▏▏▏▏▏▏▏▏                                                                                            |
Preface           |▏▏▏▏▏▏▏▏                                                                                            |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 330,423 | 90.65% |
| 2 | 34,071 | 9.35% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Letter | specific | 102 | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

1 region(s), 328,513 chars (90.13% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 28,955 | 357,468 | 328,513 | body | by Alex Toole, Columnist The honorable Judge Guy D. Donnelly of Frederick, Maryl |

## ⚠ Mask-sparse regions (≤1 mask type total)

4 region(s), 330,423 chars (90.65% of text). Largest 4:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 28,880 | 357,468 | 328,588 | front_matter | What Ever Happened to Sybil Van Antwerp? Baltimore Sun Opinion/Editorial by Alex |
| 387 | 2,075 | 1,688 | front_matter | Penguin Random House values and supports copyright. Copyright fuels creativity,  |
| 241 | 353 | 112 | front_matter | Crown An imprint of the Crown Publishing Group A division of Penguin Random Hous |
| 361,325 | 361,360 | 35 | back_matter | The Correspondent Virginia Evans Discussion Questions In order to provide readin |
