# Masking-Map Audit — [101] LDS Triple Combination (2013 PDF)

- **Source file:** `LDS_eng.pdf`
- **Text length:** 4,852,544 chars
- **Sections in current map:** 533
- **Distinct mask types present:** 7 (2 generic, 5 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 2,988,192 | 61.58% |
| ▒ generic-only (container, no specific element) | 1,839,058 | 37.90% |
| ▓ specific-only (element outside any container) | 25,294 | 0.52% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 61.58% of the text.** The remaining 38.42% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▒████████▒███████████████████████████▒▒▒███████▒█▒████▒██▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 48,525 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Copyright         |▏                                                                                                   |
Front Matter      |▏                                                                                                   |
Header            |██████████████████████████████████████                    ███                                       |
Title Page        |▏                                                                                                   |
Translation       |▏▏▏▏▏▏▏▏▏█▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏██▏▏▏▏▏▏▏█▏█▏▏▏▏█▏▏▏████▏   ▏▏ ███▏  ▏▏   ▏▏     ▏  ▏    ▏ █  |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 25,268 | 0.52% |
| 2 | 1,839,201 | 37.90% |
| 3 | 2,988,075 | 61.58% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Volume | generic | 3 | 0 | ❌ ABSENT from map |
| Book | generic | 20 | 0 | ❌ ABSENT from map |
| Chapter | generic | 393 | 248 | ⚠ under (248/393) |
| Chapter Heading | specific | 393 | 0 | ❌ ABSENT from map |
| Footnotes | specific | — | 0 | ❌ ABSENT from map |
| Insert | specific | 3 | 0 | ❌ ABSENT from map |
| Copyright | specific | — | 1 | ✓ present |
| Front Matter | specific | — | 1 | ✓ present |
| Glossary | specific | — | 0 | ❌ ABSENT from map |
| Index | specific | — | 0 | ❌ ABSENT from map |
| Appendix | specific | — | 0 | ❌ ABSENT from map |
| Appendix | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

38 region(s), 1,839,058 chars (37.90% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 3,945,691 | 4,226,249 | 280,558 | body, chapter | D&C 4:5 (12:8) l. qualifies men for God's work; 20:19 (42:29; 59:5) commandment  |
| 3,010,696 | 3,228,383 | 217,687 | body, chapter | Governments. b tg Kings, Earthly. c tg Obedience. d D&C 58:21 (21–23). 13 a Phil |
| 4,407,233 | 4,612,464 | 205,231 | body, chapter | are had among all people; 8:22–23 nations that uphold s. c. shall be destroyed;  |
| 3,698,140 | 3,901,831 | 203,691 | body, chapter | these things in plain h.; Moro. 8:10 par- ents must h. themselves as their littl |
| 4,232,839 | 4,401,571 | 168,732 | body, chapter | Abr. 2:9–11 p. given to Abraham; JS—H 1:39 (Mal. 4:6) the Lord will plant in hea |
| 3,526,235 | 3,666,144 | 139,909 | body, chapter | Gadianton—leader of robber bands [c. 50 b.c.]. See also Gadianton Robbers Hel. 2 |
| 4,729,225 | 4,852,544 | 123,319 | body, chapter | God; 14:12 numbers of Church of the Lamb are small because of w. of abominable c |
| 4,615,376 | 4,710,522 | 95,146 | body, chapter | among all t.; 31:13–14 (32:2) after receiving the Holy Ghost, ye can speak with  |
| 3,279,221 | 3,367,994 | 88,773 | body, chapter | Moses 5:25 Cain rejects greater c. from God; 6:28 men have sought their own c. i |
| 3,459,456 | 3,520,290 | 60,834 | body, chapter | D&C 20:20 by transgression of holy laws man became fallen man; 29:40–41 man was  |
| 3,232,289 | 3,273,896 | 41,607 | body, chapter | JS—M 1:36 (Matt. 24:30) the Son of Man coming in c. of heaven; JS—H 1:68 John th |
| 3,903,852 | 3,941,841 | 37,989 | body, chapter | D&C 10:22 Satan l. souls to destruc- tion; 11:12 trust in that Spirit which l. t |

## ⚠ Mask-sparse regions (≤1 mask type total)

2 region(s), 25,268 chars (0.52% of text). Largest 2:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 425 | 25,294 | 24,869 | front_matter | English approval: 11/12 Introduction . . . . . . . . . . . . . . . . . vii Testi |
| 7 | 406 | 399 | front_matter | MORMON DOCTRINE AND COVENANTS PEARL OF GREAT PRICE The Book of Mormon Another Te |
