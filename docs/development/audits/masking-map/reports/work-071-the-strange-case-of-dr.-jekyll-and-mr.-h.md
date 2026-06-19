# Masking-Map Audit — [71] The Strange Case of Dr. Jekyll and Mr. Hyde (Stevenson, Standard Ebooks)

- **Source file:** `The Strange Case of Dr_ Jekyll and Mr_ Hyde -- Robert Louis Stevenson -- 2015 -- Standard Ebooks -- 5b35483a9d153cce497b54a0d6b50431 -- Anna’s Archive.epub`
- **Text length:** 140,461 chars
- **Sections in current map:** 1
- **Distinct mask types present:** 1 (1 generic, 0 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 0 | 0.00% |
| ▒ generic-only (container, no specific element) | 140,461 | 100.00% |
| ▓ specific-only (element outside any container) | 0 | 0.00% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.00% of the text.** The remaining 100.00% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 1,405 chars; column shows the LEAST-covered class present)
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 140,461 | 100.00% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Copyright | specific | — | 0 | ❌ ABSENT from map |
| Chapter | generic | 10 | 0 | ❌ ABSENT from map |
| Colophon | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

1 region(s), 140,461 chars (100.00% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 0 | 140,461 | 140,461 | body | Imprint This ebook is the product of many hours of hard work by volunteers for S |

## ⚠ Mask-sparse regions (≤1 mask type total)

1 region(s), 140,461 chars (100.00% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 0 | 140,461 | 140,461 | body | Imprint This ebook is the product of many hours of hard work by volunteers for S |
