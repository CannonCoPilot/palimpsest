# Masking-Map Audit — [70] Charlotte Temple

- **Source file:** `Charlotte Temple -- Rowson, Susanna Haswell -- 2022 -- Standard Ebooks -- 8491224f92259d041f364596501e9f9a -- Anna’s Archive.epub`
- **Text length:** 218,036 chars
- **Sections in current map:** 71
- **Distinct mask types present:** 7 (2 generic, 5 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 110 | 0.05% |
| ▒ generic-only (container, no specific element) | 213,801 | 98.06% |
| ▓ specific-only (element outside any container) | 4,125 | 1.89% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.05% of the text.** The remaining 99.95% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 2,180 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Copyright         |▏                                                                                                   |
Front Matter      |▏▏                                                                                                  |
Header            | ▏  ▏  ▏  ▏   ▏ ▏  ▏  ▏  ▏  ▏▏  ▏  ▏  ▏ ▏ ▏  ▏ ▏  ▏  ▏     ▏  ▏  ▏  ▏ ▏  ▏  ▏  ▏  ▏   ▏ ▏   ▏ ▏     |
Preface           |▏▏                                                                                                  |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 924 | 0.42% |
| 2 | 217,112 | 99.58% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Volume | generic | 2 | 0 | ❌ ABSENT from map |
| Chapter | generic | 35 | 33 | ⚠ under (33/35) |
| Endnotes | specific | — | 0 | ❌ ABSENT from map |
| Colophon | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

31 region(s), 213,803 chars (98.06% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 22,714 | 36,392 | 13,678 | body, chapter | Change of Fortune "It was some days," continued Mr. Eldridge, recovering himself |
| 116,926 | 129,758 | 12,832 | body, chapter | Virtue﻿—When Most Amiable "Virtue never appears so amiable as when reaching fort |
| 205,731 | 218,036 | 12,305 | body, chapter | Conclusion Shortly after the interment of his daughter, Mr. Temple, with his dea |
| 178,912 | 189,129 | 10,217 | body, chapter | "Friendship a Name" And what is friendship but a name, A charm that lulls to sle |
| 55,256 | 65,323 | 10,067 | body, chapter | We Know Not What a Day May Bring Forth Various were the sensations which agitate |
| 159,370 | 167,478 | 8,108 | body, chapter | "Like a Fair Lily" Pensive she mourn'd, and hung her languid head, Like a fair l |
| 141,953 | 150,022 | 8,069 | body, chapter | Mystery Developed Unfortunately for Charlotte, about three weeks before this unh |
| 193,748 | 201,115 | 7,367 | body, chapter | Which People Void of Feeling Need Not Read When Mrs. Beauchamp entered the apart |
| 15,641 | 22,712 | 7,071 | body, chapter | Unexpected Misfortunes "My life," said Mr. Eldridge, "till within these few year |
| 76,463 | 83,141 | 6,678 | body, chapter | Cruel Disappointment "What pleasure!" cried Mr. Eldridge, as he stepped into the |
| 104,037 | 110,699 | 6,662 | body, chapter | Reflections "And am I indeed fallen so low," said Charlotte, "as to be only piti |
| 42,560 | 49,147 | 6,587 | body, chapter | Natural Sense of Propriety Inherent in the Female Bosom "I can not think we have |

## ⚠ Mask-sparse regions (≤1 mask type total)

2 region(s), 924 chars (0.42% of text). Largest 2:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 16 | 898 | 882 | front_matter | By Susanna Haswell Rowson. Imprint This ebook is the product of many hours of ha |
| 4,083 | 4,125 | 42 | front_matter | Charlotte Temple A Tale of Truth Volume I I A Boarding School "Are you for a wal |
