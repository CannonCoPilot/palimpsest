# Masking-Map Audit — [5] Douay-Rheims Bible (1a24..)

- **Source file:** `Douay-Rheims Bible Complete - Original, Unabriged, Full -- Douay-Rheims Version -- 2018 -- 1a24ae78af9f25ce66b9f156d163841a -- Anna’s Archive.epub`
- **Text length:** 5,485,105 chars
- **Sections in current map:** 2643
- **Distinct mask types present:** 7 (2 generic, 5 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 24,267 | 0.44% |
| ▒ generic-only (container, no specific element) | 5,370,726 | 97.91% |
| ▓ specific-only (element outside any container) | 90,112 | 1.64% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.44% of the text.** The remaining 99.56% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 54,851 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Appendix          |                                                                                                   ▏|
Back Matter       |                                                                                                   ▏|
Front Matter      |▏                                                                                                   |
Header            |▏███████████████████████████████████████████████████████████████████████████████████████████████    |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 78,602 | 1.43% |
| 2 | 5,406,503 | 98.57% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Chapter Heading | specific | 1334 | 0 | ❌ ABSENT from map |
| Book | generic | 73 | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

1319 region(s), 5,370,726 chars (97.91% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 5,261,729 | 5,449,680 | 187,951 | body, chapter | The water and tree of life. The conclusion. And he shewed me a river of water of |
| 2,456,594 | 2,471,302 | 14,708 | body, chapter | Beati immaculati. Of the excellence of virtue consisting in the love and observa |
| 3,635,710 | 3,649,826 | 14,116 | body, chapter | Nabuchodonosor set up a golden statue; which he commands all to adore: the three |
| 4,005,554 | 4,018,033 | 12,479 | body, chapter | Alexander Bales sets himself up for king: both he and Demetrius seek to make Jon |
| 1,380,375 | 1,392,125 | 11,750 | body, chapter | The dedication of the temple: Solomon's prayer and sacrifices. Then all the anci |
| 3,690,575 | 3,701,838 | 11,263 | body, chapter | The angel declares to Daniel many things to come, with regard to the Persian and |
| 3,448,834 | 3,460,042 | 11,208 | body, chapter | Under the figure of an unfaithful wife, God upbraids Jerusalem with her ingratit |
| 807,345 | 818,204 | 10,859 | body, chapter | Many blessings are promised to observers of God's commandments: and curses threa |
| 4,018,055 | 4,028,636 | 10,581 | body, chapter | Ptolemee invades the kingdom of Alexander: the latter is slain: and the former d |
| 2,338,699 | 2,349,176 | 10,477 | body, chapter | Exurgat Deus. The glorious establishment of the church of the New Testament, pre |
| 4,287,279 | 4,297,590 | 10,311 | body, chapter | The Jews conspire against Christ. He is anointed by Mary. The treason of Judas.  |
| 3,327,516 | 3,337,599 | 10,083 | body, chapter | The miseries that shall fall upon Babylon from the Medes: the destruction of her |

## ⚠ Mask-sparse regions (≤1 mask type total)

2 region(s), 78,602 chars (1.43% of text). Largest 2:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 14 | 54,687 | 54,673 | front_matter | Translated from the Latin Vulgate Diligently Compared with the Hebrew, Greek, an |
| 5,461,176 | 5,485,105 | 23,929 | back_matter | ABDIAS borne in Sichem, of the tribe Ephraim, prophecied the same time with Amos |
