# FABLE COLD READ, ROUND 2 — 20 random tough leaves (2026-09-04)

**Sample.** `random.seed(20260904)`, 20 of the 188 unique leaves in `tough_leaves.txt`, excluding
the 5 already read. All 20 are in the 208-plate set, so the live pipeline's output exists for every
one. Rendered to `img/` from the plate JPEGs. Regions in `cold-read-20.json` — 222 regions with a
one-line reason each. Same rule as round 1: **image only, nothing else consulted before a leaf's
entry was written.** Scored afterwards by `compare_gold.py cold-read-20.json`.

**Same six moves, same order** as round 1 (orient → kind → measure → body → relations → read →
self-check). They held on every leaf, including the ones that are not a text column at all. What
changed is move 2: the page-kind inventory roughly tripled.

---

## WHAT THE 20 CONTAINED — page kinds the first 5 never showed

| kind | leaves | what a reader does differently |
|---|---|---|
| **Annotations leaf** — body is commentary in smaller type, no scripture | 0288, 0025, 1059(top), 0022(top), 0562(top), 0564 | The BODY is `AN`, not `MT`. Every paragraph opens with an italic LEMMA (`9. Svvete sauour.]`) — the quoted verse words plus `]`. That is the anchor a reader uses; it is a sub-region |
| **Annotation section header** `ANNOTATIONS. PSALME. III.` | 0023, 0024 | A heading that names the block below it. Sub-kind of `CH` |
| **Book opening** — ornament, book title, `CHAP. I.`, argument, giant woodcut initial | 0025, 0670 | Title is `BT`, not `RH`. 0670 has NO running head; 0025 has a topical one. Initial is 6-8 lines deep and a woodcut |
| **Book argument** — whole body italic prose | 0344, 1134, 1059(bottom) | `AR` at book level. A fount cue gets it right for the wrong reason (all italic); a position cue calls it `MT` |
| **Book boundary on one leaf** | 1059 | Judith's last annotation, a type-ornament rule, then Esther's argument title. TWO measures on one page, separated by an `OR` |
| **Psalter interleaved** | 0022, 0024 | Italic gloss lines set BETWEEN roman verse lines inside the same measure (`IG`), letter-keyed to a LEFT gloss-key column (`GK`) running the full height. NEITHER is in the inventory. A paragraph detector shreds this |
| **Ruled table** | 1089 | Five columns, header row, vertical rules, a centred section title mid-page. Not a text column. `TB` with header and cells; the rules are geometry the reader uses |
| **Two-column index** | 1112 | Two equal columns of entries + page refs. `IX`. The live frame is 0.184-0.987 with head/foot 0.047/0.118 — it found nothing |
| **Prelim dedication** | 0007 | Ornament headpiece, four-line display heading (`HD`), factotum initial, dagger signature `† 2`, and **ink pen-marks down the margin** (`MS`, not type) |
| **End of book** | 1085 | `FINIS.` centred (`FN`), lower page blank. No signature or catchword |
| **Latin approbation** | 1136 | Italic document title, Latin prose in a worn face, three signatory lines (`AT`), lower 40% blank |
| **Preface end + tailpiece** | 0028 | Prose with inline Greek, then a woodcut tailpiece (`OR`), lower third blank |
| **NT setting (Rhemes)** | 0562, 0564 | THREE-part headline: page number · title · `CHA. III.` at the outer head (`CR`, a chapter running-head, not a topical title). Annotations ABOVE a printed rule, chapter below. Greek in the right margin. Vertical frame rule at the text-area edge. 0564 has NO scripture: 70% annotations, rule, chapter head, argument, catchword, blank |

**Blank space was a region on 4 of 20 leaves** (1085, 1136, 0028, 0564). A reader reports it; a
pipeline that keeps searching it for a catchword hallucinates one.

---

## THE CLASS INVENTORY IS TOO SMALL — proposals, not rulings

Every code below was used in `cold-read-20.json` because the leaf needed it. Each is a proposal for
Sir; none was silently folded into an existing class. Grouped by what kind of decision they need.

**A. Classes for TEXT that has no name today (must exist or the text is misfiled):**
| code | what | seen on |
|---|---|---|
| `AN` | annotation body — commentary prose in smaller type | 7 leaves |
| `LM` | lemma — the quoted verse words + `]` opening an annotation | every `AN` paragraph |
| `IG` | interleaved gloss — italic lines inside the verse measure, letter-keyed | 0022, 0024 |
| `GK` | gloss-key column — the lettered notes the `IG` letters point to | 0022, 0024 |
| `BT` | book / section title (`THE BOOKE OF GENESIS`, `THE ARGVMENT OF…`) | 0025, 0344, 0670, 1059, 1089 |
| `HD` | display heading of a prelim document (dedication, censura) | 0007, 1136 |
| `CR` | chapter running-head at the outer head (`CHA. III.`) — NT setting | 0562, 0564 |
| `IX` | index entries, two-column | 1112 |
| `TB` | table (header row + cells) | 1089 |
| `FN` | end-of-book marker `FINIS.` | 1085 |
| `AT` | attestation / signatory block | 1136 |
| `??` | acrostic letter markers (round 1, Lamentations) | 0666 |

**B. NON-TEXT that must be seen so it is NOT OCR'd:**
| code | what | seen on |
|---|---|---|
| `OR` | ornament — headpiece, tailpiece, type-ornament band, woodcut | 0007, 0025, 0670, 1059, 0028 |
| `RL` | printed rule — horizontal separators, vertical column/frame rules | 0670, 1089, 0562, 0564 |
| `MS` | manuscript pen marks, reader ticks, ink foliation | 0007 |
| blank | large empty regions, reported not searched | 1085, 1136, 0028, 0564 |

**C. Sub-kinds of an EXISTING class that a reader distinguishes by content** (ruling needed on
whether they are separate classes or attributes):
- `MN` splits into **summary note** (prose, roman), **citation note** (italic refs, `Io. 4. v. 24.`),
  **alternate reading** (`* or, manah sacrifice.`), **Greek note** (`κατατομή περιτομή`). All sit in
  the margin; they do different jobs and the transcription treats them differently.
- `CH` splits into **chapter head**, **psalm head** (`PSALME. III.`), **annotation-section head**.
- `DC` splits into **two-line typographic initial** and **6–8-line woodcut initial** (0007, 0025,
  0562) and the **two-sort `VV` initial** (0024). Same role; very different detection.
- `RH` vs topical running title — round 1's open question, now with 6 more instances.

---

## RESULT vs THE LIVE PIPELINE (post-R16.20 bundle), scripted

222 regions. Each addressed to the live box covering it most; cover < 0.30 = "no box".

| | n | % |
|---|---|---|
| live label AGREES with mine | 98 | 44% |
| live label DISAGREES | 79 | 36% |
| live has NO box where I drew one | 45 | 20% |

**Per leaf, worst first:** 0024 (1 of 13 agree — the interleaved Psalter is shredded, 115 boxes
withheld), 1089 (1 of 9 — the table), 1112 (1 of 5 — the index; frame head/foot 0.047/0.118),
1136 (1 of 5), 0007 (2 of 11), 0564 (2 of 11). **Best:** 0747 (10 of 12 — the one standard scripture
leaf), 0023 (11 of 16), 1134 (8 of 10).

**My classes the live pipeline mislabelled, by count:** AN 10 · MN 9 · DC 8 · CW 8 · PN 6 · SG 5 ·
BT 5 · RH 4 · VN 4 · TB 3 · HD 2 · LM 2 · AR 2 · OR 2 · CH 2 · RL 2 · CR 2 · MT 1 · FN 1 · AT 1.

Three readings of that list:
1. **`AN` at the top is the biggest single finding.** Seven of twenty tough leaves have an
   annotation body, and the pipeline calls it `MT` every time because it has no other name for a
   prose column. Every annotation leaf in the Bible is currently filed as scripture.
2. **The round-1 four are still there** — `DC` 8, `CW` 8, `SG` 5, `VN` 4 — and `PN` joins them.
   All five are decided by reading two or three sorts. Unchanged diagnosis.
3. **The frame is wrong on the non-column pages** as it must be: table, index, Psalter (0022
   head/foot 0.091/0.306, 0024 measure 0.014-0.81), and every page with blank space below
   (0028, 0564, 1136 all have a foot far above the page foot, which is correct, but the live
   `foot_y` on 0022 at 0.306 is a body cut in half).

## WHAT THIS ADDS TO THE DESIGN

- **Move 2 is where the leverage is.** Twelve page kinds in twenty tough leaves. Once the kind is
  known, the block inventory is nearly determined: an annotations leaf HAS lemmas and no verse
  numbers; a book opening HAS an ornament and a `BT`; a Psalter leaf HAS a gloss-key column. The
  archetype should carry the *expected inventory*, and the director's job at move 4 is to find it.
- **Two measures on one leaf is normal** (1059, 0562, 0564, 0022, 0024) — annotations above a rule
  and scripture below have different left edges. `frame()` returns one measure; the page has two.
- **Rules and ornaments are landmarks, not noise.** The rule on 0562/0564 is the boundary between
  `AN` and `MT`. The ornament on 1059 is the boundary between two books. A detector that has no
  class for them throws away the page's own structure markers.
- **Blank must be a first-class output.** Four of twenty leaves end early.
