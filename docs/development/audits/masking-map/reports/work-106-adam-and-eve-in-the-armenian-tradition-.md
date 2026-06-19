# Masking-Map Audit — [106] Adam and Eve in the Armenian Tradition (Stone, SBL 2013)

- **Source file:** `Adam And Eve In The Armenian Tradition, Fifth Through -- Michael E_ Stone -- SBL Early Judaism and Its Literature, 38, 2013 -- Society of Biblical -- isbn13 9781589838987 -- b3740d792550531690234343f398e9b7 -- Anna’s Archive.pdf`
- **Text length:** 1,588,919 chars
- **Sections in current map:** 12
- **Distinct mask types present:** 7 (3 generic, 4 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 46 | 0.00% |
| ▒ generic-only (container, no specific element) | 1,566,181 | 98.57% |
| ▓ specific-only (element outside any container) | 22,692 | 1.43% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.00% of the text.** The remaining 100.00% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 15,889 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Copyright         |▏                                                                                                   |
Front Matter      |▏▏                                                                                                  |
Header            | ▏                   ▏    ▏                                                  ▏                      |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 21,399 | 1.35% |
| 2 | 317,276 | 19.97% |
| 3 | 1,250,244 | 78.69% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Translation | specific | 121 | 0 | ❌ ABSENT from map |
| Commentary | specific | 6 | 0 | ❌ ABSENT from map |
| Part | generic | 2 | 1 | ⚠ under (1/2) |
| Chapter | generic | 5 | 3 | ⚠ under (3/5) |
| Chapter | generic | 14 | 3 | ⚠ under (3/14) |
| Footnotes | specific | — | 0 | ❌ ABSENT from map |
| Introduction | specific | — | 0 | ❌ ABSENT from map |
| Title Page | specific | — | 1 | ✓ present |
| Copyright | specific | — | 1 | ✓ present |
| Dedication | specific | — | 0 | ❌ ABSENT from map |
| Contents | specific | — | 0 | ❌ ABSENT from map |
| Front Matter | specific | — | 1 | ✓ present |
| Preface | specific | — | 0 | ❌ ABSENT from map |
| Glossary | specific | — | 0 | ❌ ABSENT from map |
| Index | specific | — | 0 | ❌ ABSENT from map |
| Back Matter | specific | — | 0 | ❌ ABSENT from map |
| Bibliography | specific | — | 0 | ❌ ABSENT from map |
| Index | specific | — | 0 | ❌ ABSENT from map |
| Index | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

4 region(s), 1,566,181 chars (98.57% of text). Largest 4:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 420,500 | 1,228,293 | 807,793 | body, chapter, part | 2.8 Eve, Traditions about According to Azaria J̌ułayec'i C16, Eve deceived Adam; |
| 1,228,303 | 1,588,919 | 360,616 | body, chapter, part | 36 Եւա յԱդամայ է՝ այլ ի կողէն. եւ Աբէլ յորովայնէ Ադամայ. սակայն մի են բնութիւնք  |
| 22,698 | 338,681 | 315,983 | body, part | The Adam and Eve Traditions in Armenian -3- Outline 1. Adam and Eve Traditions i |
| 338,696 | 420,485 | 81,789 | body, chapter, part | 5. Mxit'ar Ayrivanec'i 2. 6. See Stone 2007a. 7. Ibid., 85. FOURTEENTH AND FIFTE |

## ⚠ Mask-sparse regions (≤1 mask type total)

2 region(s), 21,399 chars (1.35% of text). Largest 2:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 1,826 | 22,692 | 20,866 | front_matter | 2013022985 Printed on acid-free, recycled paper conforming to ANSI /NISO Z39.48– |
| 126 | 659 | 533 | front_matter | ADAM AND EVE IN THE ARMENIAN TRADITION Fifth through Seventeenth Centuries Socie |
