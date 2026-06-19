# Masking-Map Audit — [64] The Books of Enoch (1/2/3 Enoch, Lumpkin)

- **Source file:** `The Books of Enoch_ A Complete Volume Containing 1 Enoch -- Enoch & Joseph B_ Lumpkin [Enoch & Lumpkin, Joseph B_] -- 2009 -- Fifth Estate, -- isbn13 9781933580807 -- 6d9f4271e0a52f5b84fa059abc2857c0 -- Anna’s Archive.epub`
- **Text length:** 511,261 chars
- **Sections in current map:** 450
- **Distinct mask types present:** 7 (2 generic, 5 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 287,419 | 56.22% |
| ▒ generic-only (container, no specific element) | 198,343 | 38.79% |
| ▓ specific-only (element outside any container) | 25,499 | 4.99% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 56.22% of the text.** The remaining 43.78% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▓▓▒█████████████████████████████████▒████████▒▒▒████▒▒▒███████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 5,113 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Copyright         |▏                                                                                                   |
Front Matter      |▏▏▏▏▏                                                                                               |
Header            |    ▏██▏█▏███████████▏████▏▏███▏██  ▏ ▏█▏█▏██▏█  █████▏▏█████████   ▏█▏ ████▏▏ ▏█▏█▏▏▏██████▏▏█▏█ ▏ |
Title Page        |▏                                                                                                   |
Translation       |    ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏█▏▏▏▏▏▏▏▏▏ ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 25,445 | 4.98% |
| 2 | 198,979 | 38.92% |
| 3 | 286,837 | 56.10% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Title Page | specific | — | 1 | ✓ present |
| Copyright | specific | — | 1 | ✓ present |
| Contents | specific | — | 0 | ❌ ABSENT from map |
| Introduction | specific | — | 0 | ❌ ABSENT from map |
| Book | generic | 3 | 0 | ❌ ABSENT from map |
| Introduction | specific | 2 | 0 | ❌ ABSENT from map |
| Chapter | generic | 228 | 221 | ⚠ under (221/228) |
| Back Matter | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

62 region(s), 198,343 chars (38.79% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 330,187 | 348,678 | 18,491 | body, chapter | (Note: Enoch was born on the 6th day of Tsivan. Tsi7.mn is the first month of th |
| 393,692 | 407,405 | 13,713 | body, chapter | The order of ranks of the angels is established by the homage. Rabbi Ishmael sai |
| 358,147 | 368,997 | 10,850 | body, chapter | Metatron is Enoch who was translated to heaven at the time of the flood. Rabbi I |
| 241,512 | 251,848 | 10,336 | body, chapter | The Books of Enoch Introduction to The Second Book of Enoch: Slavonic Enoch As p |
| 502,234 | 511,261 | 9,027 | body, chapter | - The names of Metatron. The names fall into three major categories, those which |
| 348,687 | 356,476 | 7,789 | body, chapter | INTRODUCTION: Rabbi Ishmael ascends to heaven to witness the vision of the Merka |
| 495,560 | 502,222 | 6,662 | body, chapter | - An Enoch-Metatron piece. (1)"1 seized him, and 1 took him and 1 appointed him" |
| 487,427 | 493,476 | 6,049 | body, chapter | - Rabbi Ishmael sees the Right Hand of the Most High Rabbi Ishmael said: Metatro |
| 435,691 | 441,659 | 5,968 | body, chapter | The Prince of the Seraphim. Description of the Seraphim Rabbi Ishmael said: Meta |
| 477,455 | 483,346 | 5,891 | body, chapter | Past and future events recorded on the Curtain of the Throne. 402 The Books of E |
| 411,730 | 416,957 | 5,227 | body, chapter | KERUBIEL, the Prince of the Cherubim. Description of the Cherubim Rabbi Ishmael  |
| 423,330 | 428,005 | 4,675 | body, chapter | The winds are blowing under the wings of the Cherubim Rabbi Ishmael said: Metatr |

## ⚠ Mask-sparse regions (≤1 mask type total)

2 region(s), 25,445 chars (4.98% of text). Largest 2:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 388 | 25,499 | 25,111 | front_matter | All rights reserved. Printed in the United States of America. No part of this bo |
| 19 | 353 | 334 | front_matter | A Complete Volume Containing 1 Enoch (The Ethiopic Book of Enoch) 2 Enoch (The S |
