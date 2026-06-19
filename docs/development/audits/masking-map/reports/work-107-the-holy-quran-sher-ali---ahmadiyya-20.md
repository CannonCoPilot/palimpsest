# Masking-Map Audit — [107] The Holy Quran (Sher Ali / Ahmadiyya, 2021 PDF)

- **Source file:** `The Holy Quran With Arabic Text And English Translation -- Maulawī Sher ʻAlī; Tahir Ahmad -- 2021 -- Islam International Publications Limited -- isbn13 9781848800229 -- 45d547fdc78588e53a0fc7b3166a36b4 -- Anna’s Archive.pdf`
- **Text length:** 1,491,930 chars
- **Sections in current map:** 1854
- **Distinct mask types present:** 6 (2 generic, 4 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 20,436 | 1.37% |
| ▒ generic-only (container, no specific element) | 1,451,744 | 97.31% |
| ▓ specific-only (element outside any container) | 19,750 | 1.32% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 1.37% of the text.** The remaining 98.63% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 14,919 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Contents          |▏▏                                                                                                  |
Front Matter      |▏▏                                                                                                  |
Header            | ████████████████████████████████ █████████████████████████████████████████████████████████         |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 1,591 | 0.11% |
| 2 | 1,490,339 | 99.89% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Chapter | generic | 114 | 925 | ✓ present |
| Part | generic | 30 | 0 | ❌ ABSENT from map |
| Translation | specific | — | 0 | ❌ ABSENT from map |
| Commentary | specific | — | 0 | ❌ ABSENT from map |
| Title Page | specific | — | 1 | ✓ present |
| Copyright | specific | — | 0 | ❌ ABSENT from map |
| Contents | specific | — | 1 | ✓ present |
| Preface | specific | — | 0 | ❌ ABSENT from map |
| Foreword | specific | — | 0 | ❌ ABSENT from map |
| Glossary | specific | — | 0 | ❌ ABSENT from map |
| Index | specific | — | 0 | ❌ ABSENT from map |
| Back Matter | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

925 region(s), 1,451,744 chars (97.31% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 1,346,517 | 1,491,930 | 145,413 | body, chapter | Gui] u ,, 0 ~ \.l.J I ~ ' ,, ,, LI ,,,. I 0 ~\.l.Jl~I ,, ,, ,, F' ,,,, ,,,, ti 0 |
| 480,072 | 511,475 | 31,403 | body, chapter | ,:, 2. Alif Lam Ra. This is a book whose verses are fortified and made flawless  |
| 228,610 | 232,939 | 4,329 | body, chapter | As to the first question the orthodox build a fantastic scenario according to wh |
| 224,798 | 228,592 | 3,794 | body, chapter | one crucified; and those who differ therein are certainly in a state of doubt ab |
| 96,579 | 99,981 | 3,402 | body, chapter | ~,:,254_ These Messengers have We 1 ii'.:: exalted, some of them above '- others |
| 371,904 | 375,285 | 3,381 | body, chapter | say, 'God! lighten our burden,' and enter the gate in humility, We shall forgive |
| 826,786 | 830,130 | 3,344 | body, chapter | 17. And Solomon was heir to David. And he said, 'O ye people, we have been taugh |
| 555,687 | 558,927 | 3,240 | body, chapter | no harm to God; verily, Allah is 0 ~ Self-Sufficient, Praiseworthy.' - ,, .9 ,,, |
| 1,207,112 | 1,210,344 | 3,232 | body, chapter | who came to them for refuge, and find not in their breasts any desire for that w |
| 917,919 | 921,126 | 3,207 | body, chapter | 11 . When they came upon you from above you, and from below you, and when your e |
| 467,009 | 470,183 | 3,174 | body, chapter | ;J Those who call on others than Allah do not really follow these 'partners'; th |
| 237,925 | 241,037 | 3,112 | body, chapter | AL-MA'IDAH (Revealed after l lijrah) 1. In the name of Allah, the :L Gracious, t |

## ⚠ Mask-sparse regions (≤1 mask type total)

1 region(s), 1,591 chars (0.11% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 18 | 1,609 | 1,591 | front_matter | THE HOLY QUR' AN ARABIC TEXT AND ENGLISH TRANSLATION Translated by MaulawI Sher  |
