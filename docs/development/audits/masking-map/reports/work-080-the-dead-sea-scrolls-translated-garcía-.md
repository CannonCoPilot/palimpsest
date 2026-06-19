# Masking-Map Audit — [80] The Dead Sea Scrolls Translated (García Martínez)

- **Source file:** `The Dead Sea scrolls translated _ the Qumran texts in -- [edited by] Florentino García Martínez; Wilfred G_E_ -- 2011 -- William B_ Eerdmans -- isbn13 9780802841933 -- d376ed7413b2c8079b55a16507a08979 -- Anna’s Archive.epub`
- **Text length:** 1,237,399 chars
- **Sections in current map:** 11
- **Distinct mask types present:** 10 (1 generic, 9 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 1,022,630 | 82.64% |
| ▒ generic-only (container, no specific element) | 34,599 | 2.80% |
| ▓ specific-only (element outside any container) | 180,170 | 14.56% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 82.64% of the text.** The remaining 17.36% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▓███████▒▒▒███████████████████████████████████████████████████████████████████████████▓▓▓▓▓▓▓▓▓▓▓▓

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 12,374 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Back Matter       |                                                                                        ▏▏▏▏▏▏▏▏▏▏▏▏|
Contents          |▏▏                                                                                                  |
Foreword          | ▏▏                                                                                                 |
Front Matter      |▏▏▏                                                                                                 |
Index             |                                                                                        ▏▏▏▏▏▏▏▏▏▏▏▏|
Introduction      |  ▏▏▏▏▏▏█▏▏                                                                                         |
Preface           | ▏                                                                                                  |
Title Page        |▏                                                                                                   |
Translation       |            ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏           |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 34,729 | 2.81% |
| 2 | 1,202,670 | 97.19% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Title Page | specific | — | 1 | ✓ present |
| Contents | specific | — | 1 | ✓ present |
| Preface | specific | — | 1 | ✓ present |
| Foreword | specific | — | 1 | ✓ present |
| Introduction | specific | — | 2 | ✓ present |
| Part | generic | 9 | 0 | ❌ ABSENT from map |
| Introduction | specific | 9 | 2 | ⚠ under (2/9) |
| Translation | specific | 270 | 1 | ⚠ under (1/270) |
| Bibliography | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

1 region(s), 34,599 chars (2.80% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 125,059 | 159,658 | 34,599 | body | Rules' are unquestionably the most typical of all the documents from the Qumran  |

## ⚠ Mask-sparse regions (≤1 mask type total)

2 region(s), 34,729 chars (2.81% of text). Largest 2:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 125,059 | 159,658 | 34,599 | body | Rules' are unquestionably the most typical of all the documents from the Qumran  |
| 26 | 156 | 130 | front_matter | The Dead Sea Scrolls Translated The Qumran Texts in English Wi#'red G. E. Watson |
