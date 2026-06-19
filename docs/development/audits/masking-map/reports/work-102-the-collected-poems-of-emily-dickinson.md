# Masking-Map Audit — [102] The Collected Poems of Emily Dickinson

- **Source file:** `The Collected Poems of Emily Dickinson (Barnes & Noble -- Dickinson, Emily; Wetzsteon, Rachel -- Barnes & Noble classics, New York, New York State, -- isbn13 9781593080501 -- a4d7cce7b4c5749f13a3b3e795969a32 -- Anna’s Archive.epub`
- **Text length:** 304,525 chars
- **Sections in current map:** 1186
- **Distinct mask types present:** 10 (2 generic, 8 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 2,398 | 0.79% |
| ▒ generic-only (container, no specific element) | 213,519 | 70.12% |
| ▓ specific-only (element outside any container) | 88,608 | 29.10% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.79% of the text.** The remaining 99.21% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 3,045 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Back Matter       |                                                                                        ▏▏▏▏▏▏▏▏▏▏▏▏|
Copyright         |▏                                                                                                   |
Endnotes          |                                                                                              ▏▏▏▏▏▏|
Front Matter      |▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏                                                                                  |
Header            |                 ███████████████████████████████████████████████████████████████                    |
Index             |                                                                                        ▏▏▏▏▏▏▏     |
Introduction      |  ▏                                                                                                 |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 52,258 | 17.16% |
| 2 | 252,267 | 82.84% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Poetry | specific | 593 | 0 | ❌ ABSENT from map |
| Part | generic | 5 | 0 | ❌ ABSENT from map |
| Back Matter | specific | — | 1 | ✓ present |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

568 region(s), 213,540 chars (70.12% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 243,296 | 269,170 | 25,874 | body, chapter | I did not reach thee, But my feet slip nearer every day; Three Rivers and a Hill |
| 100,257 | 101,570 | 1,313 | body, chapter | AN altered look about the hills; A Tyrian73 light the village fills; A wider sun |
| 68,973 | 70,184 | 1,211 | body, chapter | A poor torn heart, a tattered heart, That sat it down to rest, Nor noticed that  |
| 96,032 | 97,137 | 1,105 | body, chapter | SOFTENED by Time's consummate plush, How sleek the woe appears That threatened c |
| 144,479 | 145,556 | 1,077 | body, chapter | I cannot live with you, It would be life, And life is over there Behind the shel |
| 53,978 | 55,047 | 1,069 | body, chapter | 'T is so much joy! 'T is so much joy! If I should fail, what poverty! And yet, a |
| 89,630 | 90,691 | 1,061 | body, chapter | I measure every grief I meet With analytic eyes; I wonder if it weighs like mine |
| 208,161 | 209,218 | 1,057 | body, chapter | ON this wondrous sea, Sailing silently, Knowest thou the shore Ho! pilot, ho! Wh |
| 122,427 | 123,463 | 1,036 | body, chapter | A something in a summer's day, As slow her flambeaux126 burn away, Which solemni |
| 55,845 | 56,864 | 1,019 | body, chapter | THE heart asks pleasure first, And then, excuse from pain; And then, those littl |
| 116,935 | 117,940 | 1,005 | body, chapter | BESIDES the autumn poets sing, A few prosaic days A little this side of the snow |
| 97,858 | 98,841 | 983 | body, chapter | THE day came slow, till five o'clock, Then sprang before the hills Like hindered |

## ⚠ Mask-sparse regions (≤1 mask type total)

3 region(s), 52,258 chars (17.16% of text). Largest 3:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 7,004 | 53,253 | 46,249 | front_matter | EMILY DICKINSON Emily Dickinson was born on December 10, 1830, in Amherst, Massa |
| 181 | 6,113 | 5,932 | front_matter | PART ONE - LIFE I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII XVIII |
| 0 | 77 | 77 | front_matter | Table of Contents FROM THE PAGES OF THE COLLECTED POEMS OF EMILY DICKINSON Title |
