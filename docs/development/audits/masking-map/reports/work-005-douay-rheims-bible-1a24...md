# Masking-Map Audit — [5] Douay-Rheims Bible (1a24..)

- **Source file:** `Douay-Rheims Bible Complete - Original, Unabriged, Full -- Douay-Rheims Version -- 2018 -- 1a24ae78af9f25ce66b9f156d163841a -- Anna’s Archive.epub`
- **Text length:** 5,485,105 chars
- **Mask elements (complete map):** 2,746
- **Distinct mask types:** 8 (2 generic, 6 specific)
- **Status:** ✅ COMPLETE — 100% two-layer, 0 sparse regions

## What this audits

The **gold's own intended masking map** — every mask element typed by close reading with exact, materialized per-instance boundaries (NOT the production detector's output). **Generic** = `body, volume, book, part` (broad containers). **Specific** = the other 30 types, including `chapter`. **Gate:** every character carries ≥1 generic AND ≥1 specific mask; `body[0,EOF]` is the universal generic base, so the specific layer must tile 100%.

## Coverage summary

| Class | Chars | % of text |
|---|---:|---:|
| ✅ covered (≥1 generic + ≥1 specific) | 5,485,105 | 100.00% |
| generic-only | 0 | 0.00% |
| specific-only | 0 | 0.00% |
| uncovered | 0 | 0.00% |

**Two-layer coverage: 100.00%.** Sparse regions (generic-only or specific-only): **0** (0 chars).

## Masking-map layout (specific layer, linearized left→right)

```
thhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhheeee
```
<sub>e=appendix  h=chapter  t=front_matter</sub>

![coverage ribbon](../portfolio/figures/w5-ribbon.png)

*(Ribbon = innermost specific type per cell; the generic layer + mask-stack-depth profile — showing the ≥2 two-layer floor — are in the figure above.)*

## Mask-type breakdown (all 34 types, including 0-counts)

| type | layer | count | width min / median / max | total chars |
|---|---|---:|---:|---:|
| about_author | specific | 0  | — | — |
| acknowledgments | specific | 0  | — | — |
| addendum | specific | 0  | — | — |
| **afterword** | specific | 1 | 7,687 / 7,687 / 7,687 | 7,687 |
| **appendix** | specific | 1 | 201,101 / 201,101 / 201,101 | 201,101 |
| back_matter | specific | 0  | — | — |
| bibliography | specific | 0  | — | — |
| **body** | generic | 1 | 5,485,105 / 5,485,105 / 5,485,105 | 5,485,105 |
| **book** | generic | 73 | 2,459 / 45,436 / 284,874 | 5,262,985 |
| **chapter** | specific | 1334 | 263 / 3,712 / 14,726 | 5,262,985 |
| **chapter_heading** | specific | 1334 | 13 / 18 / 31 | 24,527 |
| colophon | specific | 0  | — | — |
| commentary | specific | 0  | — | — |
| contents | specific | 0  | — | — |
| copyright | specific | 0  | — | — |
| dedication | specific | 0  | — | — |
| discussion | specific | 0  | — | — |
| endnotes | specific | 0  | — | — |
| epigraph | specific | 0  | — | — |
| footnotes | specific | 0  | — | — |
| foreword | specific | 0  | — | — |
| **front_matter** | specific | 1 | 5,914 / 5,914 / 5,914 | 5,914 |
| **glossary** | specific | 1 | 7,418 / 7,418 / 7,418 | 7,418 |
| header | specific | 0  | — | — |
| index | specific | 0  | — | — |
| insert | specific | 0  | — | — |
| introduction | specific | 0  | — | — |
| letter | specific | 0  | — | — |
| part | generic | 0  | — | — |
| poetry | specific | 0  | — | — |
| preface | specific | 0  | — | — |
| title_page | specific | 0  | — | — |
| translation | specific | 0  | — | — |
| volume | generic | 0  | — | — |

## Per-instance edges & rules

| structure | role | count | materialization |
|---|---|---:|---|
| chapter_heading | primary | 1334 | `regex_in_span`  |
| book | secondary | 73 | `regex_in_span`  |

## Element-width distribution by type

![type counts & widths](../portfolio/figures/w5-stats.png)

---

<sub>Generated from the gold-intended masking map (`.scratch/mask-eval/masking_map.py`); detector not consulted. Coordinates character-exact from `reference_text()`. Part of the [unified audit portfolio](../portfolio/index.html).</sub>
