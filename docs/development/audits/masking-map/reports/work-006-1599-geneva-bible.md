# Masking-Map Audit — [6] 1599 Geneva Bible

- **Source file:** `1599 Geneva Bible -- Tolle Lege Press [Press, Tolle Lege] -- 2013 -- Tolle Lege Press -- 19f28a695686af95cd3f5997c53aa3f2 -- Anna’s Archive.epub`
- **Text length:** 6,689,471 chars
- **Sections in current map:** 50
- **Distinct mask types present:** 10 (2 generic, 8 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 134 | 0.00% |
| ▒ generic-only (container, no specific element) | 6,670,260 | 99.71% |
| ▓ specific-only (element outside any container) | 19,077 | 0.29% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.00% of the text.** The remaining 100.00% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 66,895 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Acknowledgments   |▏                                                                                                   |
Copyright         |▏                                                                                                   |
Foreword          |▏                                                                                                   |
Front Matter      |▏                                                                                                   |
Glossary          |▏                                                                                                   |
Header            |█                                                                                                   |
Preface           |▏                                                                                                   |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 387 | 0.01% |
| 2 | 6,688,950 | 99.99% |
| 3 | 134 | 0.00% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Chapter Heading | specific | — | 0 | ❌ ABSENT from map |
| Book | generic | — | 21 | ✓ present |
| Glossary | specific | — | 1 | ✓ present |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

21 region(s), 6,670,260 chars (99.71% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 54,771 | 6,689,471 | 6,634,700 | body, book | Mal. THE NEW TESTAMENT Matthew Matt. Mark Mark Luke Luke John John Acts Acts Rom |
| 19,082 | 40,753 | 21,671 | body, book | indicates: But in the last days it shall come to pass, that the mountain of the  |
| 40,759 | 54,398 | 13,639 | body, book | 9: 6-7, 1599 Geneva Bible). Dr. Marshall Foster Advisory Board Member, 1599 Gene |
| 54,445 | 54,539 | 94 | body, book | Job Psalms Ps. Proverbs Prov. Ecclesiastes Eccl. Solomon's Song Song Isaiah Isa. |
| 54,663 | 54,685 | 22 | body, book | Jonah Micah Mic. Nahum Nah. Habakkuk Hab. Zephaniah Zeph. Haggai Hag. Zechariah  |
| 54,432 | 54,442 | 10 | body, book | Esther Job Job Psalms Ps. Proverbs Prov. Ecclesiastes Eccl. Solomon's Song Song  |
| 54,582 | 54,591 | 9 | body, book | Ezek. Daniel Dan. Hosea Hos. Joel Joel Amos Amos Obadiah Obad. Jonah Jonah Micah |
| 54,649 | 54,658 | 9 | body, book | Obad. Jonah Jonah Micah Mic. Nahum Nah. Habakkuk Hab. Zephaniah Zeph. Haggai Hag |
| 54,723 | 54,732 | 9 | body, book | Zeph. Haggai Hag. Zechariah Zech. Malachi Mal. THE NEW TESTAMENT Matthew Matt. M |
| 54,755 | 54,764 | 9 | body, book | Zech. Malachi Mal. THE NEW TESTAMENT Matthew Matt. Mark Mark Luke Luke John John |
| 54,402 | 54,410 | 8 | body, book | Ezra Nehemiah Neh. Esther Esther Job Job Psalms Ps. Proverbs Prov. Ecclesiastes  |
| 54,418 | 54,426 | 8 | body, book | Neh. Esther Esther Job Job Psalms Ps. Proverbs Prov. Ecclesiastes Eccl. Solomon' |

## ⚠ Mask-sparse regions (≤1 mask type total)

2 region(s), 387 chars (0.01% of text). Largest 2:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 898 | 1,283 | 385 | front_matter | Notes to the Modern Reader (by Gary D. DeMar, Ph.D.) The History and Impact of t |
| 21 | 23 | 2 | front_matter | Copyright © 2006-2010 by Tolle Lege Press All Rights reserved. No part of this p |
