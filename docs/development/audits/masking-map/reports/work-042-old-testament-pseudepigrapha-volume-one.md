# Masking-Map Audit — [42] Old Testament Pseudepigrapha, Volume One (Bauckham/Davila/Panayotov)

- **Source file:** `Old Testament pseudepigrapha_ Volume one _ More noncanonical -- Richard Bauckham; James R Davila; Alexander Panayotov; James -- INscribe Digital, -- isbn13 9780802827395 -- aab44f565a88b493ecb8ef452087ff78 -- Anna’s Archive.epub`
- **Text length:** 2,502,115 chars
- **Sections in current map:** 83
- **Distinct mask types present:** 10 (1 generic, 9 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 2,392,330 | 95.61% |
| ▒ generic-only (container, no specific element) | 0 | 0.00% |
| ▓ specific-only (element outside any container) | 109,785 | 4.39% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 95.61% of the text.** The remaining 4.39% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▓▓▓███████████████████████████████████████████████████████████████████████████████████████████████

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 25,021 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Afterword         |   ▏▏                                                        ▏▏      ▏▏                             |
Commentary        |    ▏▏██████▏▏█▏   ▏▏▏▏ ▏ ▏▏▏▏▏▏▏█▏█▏▏▏███▏   ▏▏▏▏█▏  ███▏██▏ ▏▏▏▏▏▏▏▏█▏     ▏▏▏             ▏▏▏▏▏▏▏|
Contents          |▏                                                                                                   |
Copyright         |▏                                                                                                   |
Epigraph          |█▏▏                                                      ▏                                          |
Front Matter      |▏▏▏▏▏                                                                                               |
Introduction      |▏                                         ▏ ▏      █▏                                     ▏      █  |
Title Page        |▏                                                                                                   |
Translation       |       ▏▏▏▏    ▏▏▏▏▏▏▏▏▏█▏▏▏▏    ▏▏▏▏▏  ▏ ▏▏▏▏▏▏█▏▏▏▏█▏ ▏▏ ▏▏▏▏▏▏▏▏    ▏▏▏▏▏▏▏ ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏      |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 64,582 | 2.58% |
| 2 | 2,360,586 | 94.34% |
| 3 | 76,947 | 3.08% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Part | generic | 2 | 0 | ❌ ABSENT from map |
| Translation | specific | 39 | 26 | ⚠ under (26/39) |
| Introduction | specific | 40 | 8 | ⚠ under (8/40) |
| Bibliography | specific | 40 | 0 | ❌ ABSENT from map |
| Footnotes | specific | — | 0 | ❌ ABSENT from map |
| Copyright | specific | — | 1 | ✓ present |
| Dedication | specific | — | 0 | ❌ ABSENT from map |
| Contents | specific | — | 1 | ✓ present |
| Foreword | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

_None — every character carries a specific mask too_

## ⚠ Mask-sparse regions (≤1 mask type total)

7 region(s), 64,582 chars (2.58% of text). Largest 7:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 50,419 | 88,402 | 37,983 | front_matter | This Collection It was in this rich atmosphere of scholarly accomplishment that  |
| 13,126 | 22,710 | 9,584 | front_matter | Inclusiveness If we placard what should be read to comprehend Early Judaism (300 |
| 23,882 | 32,266 | 8,384 | front_matter | Terminology For readers to make sense of what follows, a few terms need to be de |
| 3,940 | 9,671 | 5,731 | front_matter | Historic Collections The lost worlds of the early Scriptures were explored from  |
| 107,931 | 109,785 | 1,854 | front_matter | Abbreviations Unless listed below, all abbreviations used in this volume are fou |
| 86 | 1,130 | 1,044 | front_matter | Published 2013 by Wm. B. Eerdmans Publishing Co. 2140 Oak Industrial Drive N.E., |
| 65 | 67 | 2 | front_matter | All rights reserved Published 2013 by Wm. B. Eerdmans Publishing Co. 2140 Oak In |
