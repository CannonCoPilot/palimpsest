# Masking-Map Audit — [18] Ante-Nicene Fathers Vol. 3 (Tertullian; Schaff/Menzies, CCEL)

- **Source file:** `Ante-Nicene Fathers Volume 3 - Enhanced Version -- Philip Schaff [Schaff, Philip] -- Ante-Nicene Fathers Volume 3, 2009 -- Christian Classics Ethereal -- eef3b5fa6fe129392d6fb890c5b5ca85 -- Anna’s Archive.epub`
- **Text length:** 3,608,567 chars
- **Sections in current map:** 1443
- **Distinct mask types present:** 6 (2 generic, 4 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 80,023 | 2.22% |
| ▒ generic-only (container, no specific element) | 3,464,562 | 96.01% |
| ▓ specific-only (element outside any container) | 63,982 | 1.77% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 2.22% of the text.** The remaining 97.78% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 36,086 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Contents          |▏                                                                                                   |
Front Matter      |▏▏                                                                                                  |
Header            | ▏████████████████████████████████████████████████████████▏   ▏   ██████████████████████████████████|
Introduction      |▏▏                                                                                                  |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 2 | 3,608,567 | 100.00% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Contents | specific | — | 1 | ✓ present |
| Introduction | specific | — | 1 | ✓ present |
| Title Page | specific | — | 0 | ❌ ABSENT from map |
| Preface | specific | — | 0 | ❌ ABSENT from map |
| Part | generic | 3 | 0 | ❌ ABSENT from map |
| Translation | specific | 23 | 0 | ❌ ABSENT from map |
| Commentary | specific | 13 | 0 | ❌ ABSENT from map |
| Introduction | specific | 5 | 1 | ⚠ under (1/5) |
| Chapter | generic | 737 | 737 | ✓ present |
| Footnotes | specific | 6280 | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

702 region(s), 3,464,562 chars (96.01% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 2,238,378 | 2,397,285 | 158,907 | body, chapter | "The head of every man is Christ."5529 What Christ, if He is not the author of m |
| 2,093,073 | 2,238,102 | 145,029 | body, chapter | In like manner does He also know the very time it behoved Him to suffer, since t |
| 2,061,747 | 2,092,820 | 31,073 | body, chapter | "Salvation comes to the house" of Zacchæus even.4962 For what reason? Was it bec |
| 1,278,294 | 1,307,233 | 28,939 | body, chapter | These evidences, then, of a stricter discipline existing among us, are an additi |
| 2,022,081 | 2,050,285 | 28,204 | body, chapter | But Christ prohibits divorce, saying, "Whosoever putteth away his wife, and marr |
| 1,823,235 | 1,850,335 | 27,100 | body, chapter | "In the like manner," says He,3982 "did their fathers unto the prophets." What a |
| 3,186,983 | 3,212,699 | 25,716 | body, chapter | But, (this doctrine of yours bears a likeness) to the Jewish faith, of which thi |
| 1,141,009 | 1,165,400 | 24,391 | body, chapter | All souls, therefore, are shut up within Hades: do you admit this? (It is true,  |
| 1,975,176 | 1,998,506 | 23,330 | body, chapter | Justly, therefore, was the hypocrisy of the Pharisees displeasing to Him, loving |
| 1,884,109 | 1,907,343 | 23,234 | body, chapter | But "what manner of man is this? for He commandeth even the winds and water!"421 |
| 1,680,560 | 1,703,347 | 22,787 | body, chapter | Yes, certainly,3435 you say, I do hope from Him that which amounts in itself to  |
| 251,499 | 272,717 | 21,218 | body, chapter | In that case, you say, why do you complain of our persecutions? You ought rather |

## ⚠ Mask-sparse regions (≤1 mask type total)

_None — every character is covered by ≥2 mask types_
