# Masking-Map Audit — [48] New Testament Apocrypha: More Noncanonical Scriptures (MNTA vol. 3, Burke ed.)

- **Source file:** `New Testament apocrypha _ more noncanonical scriptures_ -- Tony Burke; Brent Landau -- Grand Rapids, Michigan, 2016 -- Eerdmans Publishing Company, -- isbn13 9780802872890 -- 99bbecbce461db3b220b58e59c569acc -- Anna’s Archive.epub`
- **Text length:** 1,944,206 chars
- **Sections in current map:** 62
- **Distinct mask types present:** 8 (1 generic, 7 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 1,904,987 | 97.98% |
| ▒ generic-only (container, no specific element) | 103 | 0.01% |
| ▓ specific-only (element outside any container) | 39,116 | 2.01% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 97.98% of the text.** The remaining 2.02% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▒█████████████████████████████████████████████████████████████████████████████████████████████████

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 19,442 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Commentary        |  ▏▏▏  ▏▏▏  ▏▏▏     ▏▏ ▏█▏ ▏▏ ▏▏▏▏    ▏▏ ▏▏▏▏▏▏           ▏▏▏▏ ▏▏▏▏ ▏     ▏▏▏▏  ▏▏  ▏▏▏██▏  ▏▏▏▏    |
Contents          |▏                                                                                                   |
Copyright         |▏                                                                                                   |
Front Matter      |▏▏▏                                                                                                 |
Preface           |▏▏▏                                                                                                 |
Title Page        |▏                                                                                                   |
Translation       |  ▏▏▏▏▏▏ ▏▏▏▏ ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏    ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏███▏▏▏▏▏▏▏▏▏▏▏██▏▏▏▏▏▏▏▏█▏ ▏▏▏▏▏|
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 2,450 | 0.13% |
| 2 | 1,941,756 | 99.87% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Copyright | specific | — | 1 | ✓ present |
| Dedication | specific | — | 0 | ❌ ABSENT from map |
| Contents | specific | — | 1 | ✓ present |
| Preface | specific | — | 1 | ✓ present |
| Introduction | specific | — | 0 | ❌ ABSENT from map |
| Glossary | specific | — | 0 | ❌ ABSENT from map |
| Part | generic | 4 | 0 | ❌ ABSENT from map |
| Book | generic | 29 | 0 | ❌ ABSENT from map |
| Introduction | specific | 29 | 0 | ❌ ABSENT from map |
| Translation | specific | 29 | 30 | ✓ present |
| Bibliography | specific | 29 | 0 | ❌ ABSENT from map |
| Footnotes | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

1 region(s), 103 chars (0.01% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 39,116 | 39,219 | 103 | body | I. Gospels and Related Traditions of New Testament Figures The Hospitality and P |

## ⚠ Mask-sparse regions (≤1 mask type total)

4 region(s), 2,450 chars (0.13% of text). Largest 4:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 546 | 2,441 | 1,895 | front_matter | List of Abbreviations I. GOSPELS AND RELATED TRADITIONS OF NEW TESTAMENT FIGURES |
| 143 | 501 | 358 | front_matter | Published 2023 Book design by Leah Luyk Printed in the United States of America  |
| 39,116 | 39,219 | 103 | body | I. Gospels and Related Traditions of New Testament Figures The Hospitality and P |
| 30 | 124 | 94 | front_matter | 4035 Park East Court SE, Grand Rapids, Michigan 49546 www.eerdmans.com © 2023 To |
