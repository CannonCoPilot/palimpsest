# Masking-Map Audit — [56] The Last of the Mohicans (Cooper)

- **Source file:** `The Last of the Mohicans -- Cooper, James Fenimore -- The Leatherstocking Tales 2, 1919 -- C_ Scribner's sons -- isbn13 9785551075097 -- 1164165e8537a4b55cd9c0d05ff87858 -- Anna’s Archive.epub`
- **Text length:** 845,214 chars
- **Sections in current map:** 55
- **Distinct mask types present:** 5 (2 generic, 3 specific)

## What this audits (provenance & method)

- **Map under audit = the *current materialized* masking map**: the typed, bounded sections the production layout pipeline emits for this work (`detect_layout_sections(_layout_boundaries(proj), …)`). This is the only complete coordinate map that exists today.
- **The gold contract is the *target*, overlaid** in the gap table below. The gold stores mask **types + counts + a few exemplar anchors**, NOT a per-instance edge for every element — so the gold's *intended* coverage cannot itself be verified at character level until per-instance edges exist (Phase-2 directive #1). The current-map audit is the achievable proxy and exposes where the map falls short of the gold target.
- **Generic** (broad nesting containers — locate text but do not name a specific element): `body, volume, book, part, chapter`. **Specific** = every other type (front/back-matter subtypes, chapter_heading, footnotes, epigraph, translation, commentary, letter, poetry, …). **Ideal:** every character carries ≥1 generic AND ≥1 specific mask.

## Coverage summary (character-level)

| Class | Chars | % of text |
|---|---:|---:|
| █ covered (>=1 generic + >=1 specific) | 251 | 0.03% |
| ▒ generic-only (container, no specific element) | 836,997 | 99.03% |
| ▓ specific-only (element outside any container) | 7,966 | 0.94% |
| · uncovered (0 masks) | 0 | 0.00% |

**Two-layer coverage (>=1 generic + >=1 specific): 0.03% of the text.** The remaining 99.97% violates the coverage ideal.

## Masking-map layout (linearized, left→right = start→end of text)

```
0%                                              50%                                             100%
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

legend:  █ covered   ▓ specific-only   ▒ generic-only   · uncovered
         (each column ≈ 8,452 chars; column shows the LEAST-covered class present)
```

### Specific-type lanes (where each specific mask appears)

```
Front Matter      |▏                                                                                                   |
Header            |▏  ▏ ▏ ▏  ▏ ▏  ▏  ▏  ▏ ▏  ▏  ▏   ▏  ▏  ▏  ▏  ▏   ▏  ▏  ▏  ▏  ▏  ▏   ▏  ▏  ▏                         |
Title Page        |▏                                                                                                   |
```

## Mask stacking depth (how many masks cover a character)

| Depth | Chars | % |
|---:|---:|---:|
| 1 | 7,942 | 0.94% |
| 2 | 837,272 | 99.06% |

## Gold contract vs. detector map (type-coverage gap)

| Mask type | Kind | Gold expected | Detector found | Status |
|---|---|---:|---:|---|
| Title Page | specific | — | 1 | ✓ present |
| Introduction | specific | — | 0 | ❌ ABSENT from map |
| Epigraph | specific | 33 | 0 | ❌ ABSENT from map |
| Chapter | generic | 33 | 26 | ⚠ under (26/33) |
| Endnotes | specific | — | 0 | ❌ ABSENT from map |

## ⚠ Uncovered regions (0 masks)

_None — every character carries at least one mask_

## ⚠ Generic-only regions (container mask, but NO specific element)

26 region(s), 836,997 chars (99.03% of text). Largest 12:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 632,538 | 845,214 | 212,676 | body, chapter | "Bot. — Let me play the lion too." — Midsummer Night's Dream Notwithstanding the |
| 250,659 | 282,606 | 31,947 | body, chapter | "Clo. — I am gone, sire, And anon, sire, I'll be with you again." — Twelfth Nigh |
| 386,589 | 418,434 | 31,845 | body, chapter | "Weave we the woof. The thread is spun. The web is wove. The work is done." — Gr |
| 546,818 | 576,780 | 29,962 | body, chapter | "But though the beast of game The privilege of chase may claim; Though space and |
| 306,812 | 336,596 | 29,784 | body, chapter | "Guard. — Qui est la? Puc. — Paisans, pauvres gens de France." — King Henry VI D |
| 604,019 | 632,528 | 28,509 | body, chapter | "Snug. — Have you the lion's part written? Pray you, if it be, give it to me, fo |
| 443,882 | 471,706 | 27,824 | body, chapter | "Salar. — Why, I am sure, if he forfeit, thou wilt not take his flesh; what's th |
| 223,125 | 250,649 | 27,524 | body, chapter | "Cursed be my tribe If I forgive him." — Shylock The Indian had selected for thi |
| 576,790 | 604,009 | 27,219 | body, chapter | "Thus spoke the sage: the kings without delay Dissolve the council, and their ch |
| 471,716 | 497,547 | 25,831 | body, chapter | "Land of Albania! let me bend mine eyes On thee; thou rugged nurse of savage men |
| 197,426 | 223,115 | 25,689 | body, chapter | "I fear we shall outsleep the coming morn As much as we this night have overwatc |
| 521,324 | 546,808 | 25,484 | body, chapter | "Bot. — Abibl we all met? Qui. — Pat — pat; and here's a marvelous convenient pl |

## ⚠ Mask-sparse regions (≤1 mask type total)

1 region(s), 7,942 chars (0.94% of text). Largest 1:

| start | end | chars | covered by | excerpt |
|---:|---:|---:|---|---|
| 24 | 7,966 | 7,942 | front_matter | BY J AMES F ENIMORE C OOPER Introduction It is believed that the scene of this t |
