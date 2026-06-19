# Masking-Map Audit — [29] The Message of the Qur'An (Muhammad Asad)

- **Source file:** `The Message of the Qur'An -- Muhammad Asad [Asad, Muhammad] -- Place of publication not identified, 1980 -- The Book Foundation -- isbn13 9780317524567 -- f720bfc6c8902fb7c76dbd9aa6f64f30 -- Anna’s Archive.epub`
- **Text length:** 3,097,354 chars
- **Sections in current map:** 237
- **Distinct mask types present:** 8 (2 generic, 6 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 2,446 | 0.08% |
| ▒ generic-only (container, no specific element) | 1,264,674 | 40.83% |
| ▓ specific-only (element outside any container) | 1,830,234 | 59.09% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.08% of the text.** The remaining 99.92% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 30,974 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Appendix          |                                          ██                                                        |
Back Matter       |                                          ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏|
Foreword          |▏▏                                                                                                  |
Front Matter      |▏▏                                                                                                  |
Header            | █  ▏▏ ▏▏ ▏▏▏▏▏▏▏█▏▏█▏▏██▏█████████████████                                                         |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 1,796,944 | 58.02% |
| 2 | 1,294,731 | 41.80% |
| 3 | 5,679 | 0.18% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Chapter | generic | 114 | 114 | ✓ present |
| Introduction | specific | 114 | 0 | ❌ ABSENT from map |
| Translation | specific | 114 | 0 | ❌ ABSENT from map |
| Footnotes | specific | 5326 | 0 | ❌ ABSENT from map |
| Appendix | specific | 4 | 4 | ✓ present |
| Title Page | specific | — | 1 | ✓ present |
| Contents | specific | — | 0 | ❌ ABSENT from map |
| Foreword | specific | — | 1 | ✓ present |
| Bibliography | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

114 region(s), 1,264,674 chars (40.83% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 42,806 | 125,413 | 82,607 | body, chapter | Al-Baqarah (The Cow) Medina Period T HE TITLE of this sūrah is derived from the  |
| 174,789 | 224,954 | 50,165 | body, chapter | An-Nisā'(Women) Medina Period T HE TITLE An-Nisā' has been given to this sūrah b |
| 125,428 | 174,773 | 49,345 | body, chapter | Al `Imrān(The House Of `Imrān) Medina Period T HIS SŪRAH is the second or (accor |
| 310,841 | 360,109 | 49,268 | body, chapter | Al-A`rāf (The Faculty Of Discernment) Mecca Period T HE TITLE of this sūrah is b |
| 265,224 | 310,824 | 45,600 | body, chapter | Al-An`ām(Cattle) Mecca Period W ITH the possible exception of two or three verse |
| 383,980 | 424,976 | 40,996 | body, chapter | At-Tawbah(Repentance) Medina Period I N CONTRAST with every other sūrah of the Q |
| 224,969 | 265,209 | 40,240 | body, chapter | Al-Mā'idah(The Repast) Medina Period A CCORDING to all the available evidence, t |
| 453,370 | 483,785 | 30,415 | body, chapter | H Ūd Mecca Period R EVEALED very shortly after the tenth sūrah ( Yūnus) – that i |
| 553,961 | 583,697 | 29,736 | body, chapter | An-Naḥl(The Bee) Mecca Period A CCORDING to almost all the authorities (includin |
| 483,802 | 512,455 | 28,653 | body, chapter | Yūsuf(Joseph) Mecca Period A CCORDING to all the authoritative sources, this sūr |
| 424,991 | 453,352 | 28,361 | body, chapter | Yūnus(Jonah) Mecca Period T HIS SŪRAH, which derives its title from the solitary |
| 608,552 | 633,978 | 25,426 | body, chapter | Al-Kahf(The Cave) Mecca Period T HIS SŪRAH – revealed immediately before An-Naḥl |

## ⚠ Mask-sparse regions (≤1 mask type total)

4 region(s), 1,796,944 chars (58.02% of text). Largest 4:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 1,331,960 | 3,097,354 | 1,765,394 | back_matter | THE NIGHT JOURNEY T HE PROPHET'S "Night Journey" ( isrā') from Mecca to Jerusale |
| 1,307,093 | 1,326,268 | 19,175 | back_matter | SYMBOLISM AND ALLEGORY IN THE QUR'ĀN W HEN studying the Qur'ān, one frequently e |
| 14 | 6,856 | 6,842 | front_matter | THE QUR'ĀN TRANSLATED AND EXPLAINED by Muḥammad Asad For people who think Forewo |
| 34,428 | 39,961 | 5,533 | front_matter | Works of Reference T HIS WORK is based on the recension of ḤafS ibn Sulaymān al- |
