# Masking-Map Audit — [100] Douay-Rheims Bible (Challoner, Global Grey)

- **Source file:** `Douay–Rheims Bible -- Challoner's Revised Version -- 2024 -- Global Grey ebooks -- d727529260a20949024cead95f4b81cf -- Anna’s Archive.epub`
- **Text length:** 5,487,386 chars
- **Sections in current map:** 150
- **Distinct mask types present:** 6 (2 generic, 4 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 1,336 | 0.02% |
| ▒ generic-only (container, no specific element) | 5,484,276 | 99.94% |
| ▓ specific-only (element outside any container) | 1,774 | 0.03% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.02% of the text.** The remaining 99.98% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 54,874 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Contents          |▏                                                                                                   |
Front Matter      |▏                                                                                                   |
Header            |▏   ▏  ▏ ▏   ▏  ▏▏  █  ▏ ▏ ▏  ▏ ▏  ▏▏▏▏█  ▏    ▏ █▏▏  ▏   ▏    █▏   ▏ ▏████  ▏▏  ▏ ▏  ▏ ▏ ▏ ▏██████ |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 236 | 0.00% |
| 2 | 5,485,814 | 99.97% |
| 3 | 1,336 | 0.02% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Book | generic | 73 | 73 | ✓ present |
| Chapter Heading | specific | 1334 | 0 | ❌ ABSENT from map |
| Colophon | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

73 region(s), 5,484,276 chars (99.94% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 2,309,510 | 2,611,374 | 301,864 | body, book | THE BOOK OF PSALMS The psalms are called by the Hebrews TEHILLIM, that is, Hymns |
| 3,234,754 | 3,485,589 | 250,835 | body, book | THE PROPHECY OF JEREMIAS Jeremias was a priest, a native of Anathoth, a priestly |
| 3,537,866 | 3,774,892 | 237,026 | body, book | THE PROPHECY OF EZECHIEL EZECHIEL, whose name signifies the STRENGTH OF GOD, was |
| 1,791 | 227,609 | 225,818 | body, book | THE BOOK OF GENESIS This book is so called from its treating of the GENERATION,  |
| 3,012,669 | 3,234,736 | 222,067 | body, book | THE PROPHECY OF ISAIAS This inspired writer is called by the Holy Ghost, the gre |
| 2,826,602 | 3,012,653 | 186,051 | body, book | ECCLESIASTICUS This Book is so called from a Greek word that signifies a preache |
| 227,625 | 412,000 | 184,375 | body, book | THE BOOK OF EXODUS The Second Book of Moses is called EXODUS, from the Greek wor |
| 542,290 | 721,701 | 179,411 | body, book | THE BOOK OF NUMBERS This fourth Book of Moses is called NUMBERS, because it begi |
| 721,722 | 880,252 | 158,530 | body, book | THE BOOK OF DEUTERONOMY This Book is called DEUTERONOMY, which signifies a SECON |
| 4,331,646 | 4,485,991 | 154,345 | body, book | THE HOLY GOSPEL OF JESUS CHRIST ACCORDING TO SAINT MATTHEW Saint Matthew, one of |
| 1,118,390 | 1,269,767 | 151,377 | body, book | THE FIRST BOOK OF SAMUEL, OTHERWISE CALLED THE FIRST BOOK OF KINGS This and the  |
| 4,572,373 | 4,722,518 | 150,145 | body, book | THE HOLY GOSPEL OF JESUS CHRIST ACCORDING TO ST. LUKE St. Luke was a native of A |

## ⚠ Mask-sparse regions (≤1 mask type total)

1 region(s), 236 chars (0.00% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 46 | 282 | 236 | front_matter | First published 1749 - 1777 This ebook edition was published by Global Grey on t |
