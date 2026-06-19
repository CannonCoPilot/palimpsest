# Masking-Map Audit — [105] Dead Sea Scrolls Reader Vol. 1 (Parry & Tov, Brill 2004)

- **Source file:** `The Dead Sea Scrolls Reader, Vol_ 1_ Texts Concerned With -- edited by Donald W_ Parry & Emanuel Tov with the assistance -- 1, 2004 -- Brill Academic -- isbn13 9781423712275 -- 79bba3ff81b9b5adf8d401cdd0f7d237 -- Anna’s Archive.pdf`
- **Text length:** 574,841 chars
- **Sections in current map:** 73
- **Distinct mask types present:** 11 (2 generic, 9 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 440,403 | 76.61% |
| ▒ generic-only (container, no specific element) | 4,157 | 0.72% |
| ▓ specific-only (element outside any container) | 130,281 | 22.66% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 76.61% of the text.** The remaining 23.39% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▒████████████████████████████████████████████████████████████████████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 5,748 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Back Matter       |                                                                              ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏|
Contents          |█                                                                                                   |
Copyright         |▏                                                                                                   |
Endnotes          |                                                                              ▏█▏▏▏▏▏█▏██▏█▏█▏ █▏▏██|
Front Matter      |▏▏                                                                                                  |
Header            | ▏    ██▏   ▏       ▏ ▏   ▏ ▏▏ █                                                                    |
Introduction      |█▏    ▏                                                                                             |
Title Page        |▏                                                                                                   |
Translation       | ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏                     |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 34,170 | 5.94% |
| 2 | 100,271 | 17.44% |
| 3 | 440,375 | 76.61% |
| 4 | 25 | 0.00% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Title Page | specific | — | 1 | ✓ present |
| Copyright | specific | — | 1 | ✓ present |
| Contents | specific | — | 2 | ✓ present |
| Introduction | specific | — | 4 | ✓ present |
| Glossary | specific | — | 0 | ❌ ABSENT from map |
| Introduction | specific | — | 4 | ✓ present |
| Part | generic | 6 | 0 | ❌ ABSENT from map |
| Book | generic | 6 | 0 | ❌ ABSENT from map |
| Translation | specific | 63 | 1 | ⚠ under (1/63) |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

1 region(s), 4,157 chars (0.72% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 5,930 | 10,087 | 4,157 | body, chapter | ———————————————————————-—————— 1 Several persons helped us in this cooperative e |

## ⚠ Mask-sparse regions (≤1 mask type total)

9 region(s), 34,170 chars (5.94% of text). Largest 9:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 530,219 | 539,798 | 9,579 | back_matter | L. Schiffman, DJD XXXV Frgs. 1–2 (formerly 1) 1 ]ח[ מֵ שה ] 2 [ ]ות כול ] 3 [ ]  |
| 539,883 | 548,863 | 8,980 | back_matter | DJD XXXV Frg. 1 1 [ ] ° ם ] [ 2 [ ]אֵשר כתוב ] [ 3 [ ]כתוִב בס [ פר ] ישעיה הנבי |
| 512,002 | 517,974 | 5,972 | back_matter | C. PURITY RULE 4Q274 (4QTohorot A) trans. J. M. Baumgarten Frg. 1 Col. i 0. [Let |
| 507,544 | 510,907 | 3,363 | back_matter | DJD XXIII Frg. 1 Col. i Parallel: 4Q285 5 (underline) 5 [ ]בום 6 [ ] לו 7 ]צמח ד |
| 572,544 | 574,841 | 2,297 | back_matter | DJD XXVI Frg. 1 1 [ ]יו ] [ 2 [ ]א ת ] [ 3 [ ] ִשֵ נו צ ] [ 4 [ ]תו ] [ F. UNCLA |
| 456,136 | 458,097 | 1,961 | back_matter | DJD XXXVI Frg. 1 Parallels: 1QM II 4QMa 1 8–9 1 [ ִהֵ מכ ]ו[ לֵ אשִ ]ר 2 [ ֵכִ ו |
| 2,621 | 4,386 | 1,765 | front_matter | DJD XVIII, 1996); (4Q269, frgs. 10–11, 15–16 [re-edition] DJD XXXVI, 2000) 5QD ( |
| 45 | 296 | 251 | front_matter | This page intentionally left blank Edited by Donald W. Parry & Emanuel Tov With  |
| 1,793 | 1,795 | 2 | front_matter | CONTENTS (For the contents of the complete volume see the back of this part.) GE |
