# Masking-Map Audit — [104] is 5 (E.E. Cummings)

- **Source file:** `is 5 -- E_E_ Cummings -- 1926 -- Boni & Liveright, New York -- fdb61a2b996b8f7a13a83b2ea8e001a2 -- Anna’s Archive.epub`
- **Text length:** 62,038 chars
- **Sections in current map:** 41
- **Distinct mask types present:** 7 (2 generic, 5 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 47 | 0.08% |
| ▒ generic-only (container, no specific element) | 29,776 | 48.00% |
| ▓ specific-only (element outside any container) | 32,215 | 51.93% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.08% of the text.** The remaining 99.92% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 620 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Copyright         |▏                                                                                                   |
Foreword          |▏▏▏▏                                                                                                |
Front Matter      |▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏                                                |
Header            |                                                   ▏  ▏▏██▏▏ ▏ ▏                       ▏ █▏▏▏▏      |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 30,268 | 48.79% |
| 2 | 31,770 | 51.21% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Poetry | specific | 84 | 0 | ❌ ABSENT from map |
| Part | generic | 5 | 0 | ❌ ABSENT from map |
| Colophon | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

16 region(s), 29,778 chars (48.00% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 39,673 | 54,253 | 14,580 | body, chapter | my sweet old etcetera aunt lucy during the recent war could and what is more did |
| 58,153 | 62,038 | 3,885 | body, chapter | i go to this window just as day dissolves when it is twilight(and looking up in  |
| 36,979 | 39,671 | 2,692 | body, chapter | little ladies more than dead exactly dance in my head, precisely dance where dan |
| 32,216 | 33,544 | 1,328 | body, chapter | the season 'tis, my lovely lambs, of Sumner Volstead Christ and Co. the epoch of |
| 54,256 | 55,258 | 1,002 | body, chapter | you being in love will tell who softly asks in love, am i separated from your bo |
| 36,131 | 36,977 | 846 | body, chapter | come, gaze with me upon this dome of many coloured glass, and see his mother's p |
| 56,215 | 56,889 | 674 | body, chapter | i am a beggar always who begs in your mind (slightly smiling, patient, unspeakin |
| 33,546 | 34,219 | 673 | body, chapter | opening of the chambers close quotes the microscopic pithicoid President in a ne |
| 56,892 | 57,519 | 627 | body, chapter | if within tonight's erect everywhere of black muscles feels a weightless slownes |
| 57,523 | 58,148 | 625 | body, chapter | how this uncouth enchanted person, arising from a restaurant, looks breathes or  |
| 34,810 | 35,407 | 597 | body, chapter | it's jolly odd what pops into your jolly tete when the jolly shells begin droppi |
| 34,222 | 34,808 | 586 | body, chapter | "next to of course god america i love you land of the pilgrims' and so forth oh  |

## ⚠ Mask-sparse regions (≤1 mask type total)

3 region(s), 30,268 chars (48.79% of text). Largest 3:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 2,120 | 32,215 | 30,095 | front_matter | ONE FIVE AMERICANS I. LIZ I with breathing as (faithfully) her lownecked dress a |
| 182 | 353 | 171 | front_matter | IS FIVE FIVE BOOKS by E. E. Cummings The Enormous Room Tulips and Chimneys & Xli |
| 471 | 473 | 2 | front_matter | FOREWORD On the assumption that my technique is either complicated or original o |
