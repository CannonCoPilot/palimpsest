# Gold Set Mask Ratification — By-Eye Vetting Results

Per-work record of reading each Gold Set text and validating **every mask element** for
accuracy (false-positive / false-negative) and precision (character-level boundaries),
noting every mistype, untyped section, and misalignment, and the gold edits applied.

Tools (all re-runnable):
- `gold_verify.py` — consistency + anchor uniqueness + mask-vs-taxonomy.
- `gold_ratify.py` — independent count re-derivation + boundary text dumps.
- `.scratch/mask-eval/dump_work.py` — full-text dump, detector sections, nav track, uncovered-run FN hunt.

## Methodology & standards

- **Verbatim** (read end-to-end): idx104 (62K), idx103 (71K), idx70 (218K).
- **Structured** (front/back matter + transitions verbatim; complete instance-heading list
  + boundary chars reviewed; every anomaly + a structured sample char-level): the four
  Bibles (idx5 5.5M, idx100 5.5M, idx6 6.7M, idx101 4.9M) and the larger novels/poetry
  (idx102 304K, idx19 364K). The standard applied is stated per work.
- **Boundary policy (design tension, flagged):** the gold scores *recall-of-count, not exact
  edges*, and never stores per-instance offsets (anti-Goodhart). I validate every boundary
  char-level by eye; I edit the gold for any **type error, untyped/maskable section (FN),
  false positive, or wrong anchor**. A per-instance edge mis-*formed by the detector* (not a
  wrong gold anchor) is logged as a detector/Phase-B finding, not a gold edit.

Status legend: ✅ vetted & error-free · ✏️ edited · ⚠️ open question.

---

## [104] is 5 — E. E. Cummings (1926 Boni & Liveright) · 62,038 chars · VERBATIM ✅✏️

**Elements:** `poetry` (84, primary, unmasked) · `part` (5, secondary, unmasked) · `colophon` (added).

**Ground truth from the book itself.** The foreword carries the publisher's contents table:
`ONE I–XL (40) · TWO I–XI (11) · THREE I–X (10) · FOUR I–XVIII (18) · FIVE I–V (5)` = **84**.
This is stronger than the prior "84 standalone Roman markers" cue and independently confirms
the count and the 5 parts.

**Errors found & fixed:**

1. ✏️ **Mis-anchored first-poem exemplar (mislabel).** Prior anchor `"the season 'tis, my
   lovely lambs"` was labeled "section ONE, I" but resolves to **offset 32216 — after the
   'TWO' marker**, i.e. section TWO's poem I. The true first poem of the work is section ONE
   → "FIVE AMERICANS" → "I. LIZ" → I: `"with breathing as (faithfully) her lownecked"`.
   Root cause: the detector over-swallows section ONE (40 poems) into front_matter, so the
   first *detected* poem is section TWO's — the original authoring anchored the detector's
   view, not the text. **Re-anchored to the true first poem.**
2. ✏️ **Mis-anchored last-poem exemplar (mislabel).** Prior anchor `"i go to this window"`
   labeled "section FIVE" resolves **before the 'FIVE' marker** → it is section FOUR's poem
   XVIII. True last poem is section FIVE, poem V: `"if i have made,my lady,intricate"`.
   **Re-anchored.**
3. ✏️ **Untyped false-negative: editorial back matter.** Lines after the final poem are a
   "Transcriber's note" (non-standard spelling retained; a missing line on p.46; landscape
   placement on p.55) — non-authorial apparatus that would pollute literary analysis, but
   the gold left it untyped (detector swallows it into the last poem's section). **Added a
   `colophon` element** `[61597→62038]` (start "Transcriber's note", end EOF; mask=true).
   Boundary verified: starts exactly after "…meadow of my soul.", ends at EOF.

**Precision:** all three repeating exemplars + the colophon span resolve uniquely; the
colophon boundaries are char-exact.

**⚠️ Open question (type choice):** the Transcriber's note is typed `colophon` (the EOF
production-note slot, matching idx70/idx100). It is arguably a `back_matter` or a
not-yet-existing `transcriber_note` type. Flagged for your call; no perfect taxonomy fit.

**Detector/Phase-B findings (not gold errors):** body_start mis-anchored at "TWO" swallows
section ONE (40 poems) into front_matter; recall 18/84 (0.21); MIRAGE composite 91.7.

**Post-edit checks:** `gold_verify 104` → consistent; `gold_ratify 104` → 0 flags; count 84
re-grounded (foreword TOC).

---

## Scope decision adopted from idx103 on (definition "B")

idx103 forced the recurring question: how complete must the map be? Adopted definition **B**:
type **every present maskable section** (front/back/editorial matter included — TOC, dedication,
indexes, publisher catalogs), validate primary structure char-level by eye, but keep **large
repeating windows** (Bible chapter-summaries, poem sequences) as **counted-repeating** rather than
individually char-spanned — preserving the anti-Goodhart "no stored per-instance edges" design.
This satisfies "leave nothing demoted" without reversing that design. Front/back matter the
detector already regionises correctly is not re-annotated (no FN there); only leaked/untyped
maskable sections are added.

## [103] The Road Not Taken and Other Poems — Frost (Dover 1993) · 71,309 chars · VERBATIM ✅✏️

**Before:** only `poetry` (28). **After:** `poetry` + `preface` + `dedication` + `contents` +
`index` + `back_matter` (front_matter `[0–1802]` already correct in the detector).

**Primary structure — validated.** `poetry` = **28** top-level poems, confirmed by eye against
the printed Table of Contents (lists exactly Road Not Taken→Sound of the Trees, **Hill Wife as a
single entry**) and corroborated by nav (33 poem entries = 27 standalone + Hill Wife + its 5
sub-parts: Loneliness/House Fear/The Smile/The Oft-Repeated Dream/The Impulse). No FP/FN among the
poems. The body span `[3677–62530]` holds exactly the 28 poems.

**Errors found & fixed — all false negatives (untyped maskable sections leaked into the body
blob; detector mis-anchored body_start at the editorial "Note", offset 1802, and detected 0
structure):**

1. ✏️ `preface` `[1802–2738]` — Dover editor's "Note" on the volume. (Subtype soft: preface vs
   foreword/introduction; heading is literally "Note".)
2. ✏️ `dedication` `[2738–3064]` — original Mountain Interval dedication "TO YOU…".
3. ✏️ `contents` `[3064–3677]` — Table of Contents.
4. ✏️ `index` `[62530–64333]` — the two Alphabetical Lists (Titles, First Lines).
5. ✏️ `back_matter` `[64333–71309]` — Dover Thrift publisher catalog (advertising).

**Precision:** all 5 new spans resolve uniquely and are char-exact and **contiguous** (each end
== next start), tiling all non-body maskable matter end-to-end. Verified by reading both
boundaries of every span.

**Detector/Phase-B findings (not gold errors):** detector found 0 poems (entire work one body
blob, cover≈0) and mis-placed body_start at "Note"; front/back matter separation failed beyond the
first 1802 chars. COARSE.

**Post-edit checks:** `gold_verify 103` → consistent (6 types); `gold_ratify 103` → spans clean.

## [70] Charlotte Temple — Susanna Rowson (Standard Ebooks) · 218,036 chars · VERBATIM ✅✏️

**Before:** `chapter` (35) + `endnotes` + `colophon`. **After:** + `volume` (2).

**Primary structure — validated.** `chapter` = **35** (nav I–XXXV), recount MATCH. The two
"missing" detector chapters are a **source-label corruption** confirmed by eye: nav labels
`XXI11` and `XXXI18` (endnote-reference digits fused into the Roman numeral). Not a gold error —
the gold pins the true 35; the detector's 33 is the measured recall (0.94). Chapter I and XXXV
exemplars land on clean openings.

**Apparatus — validated (already present).** `endnotes` `[208703–217800]` (21 `↩` backlinks;
Standard Ebooks editorial endnotes) and `colophon` `[217800–EOF]` both char-exact; the detector
emits neither (swallowed into the last chapter), so the gold correctly captures both. No separate
inline footnotes exist — the work uses collected endnotes.

**Error found & fixed — false negative:**

1. ✏️ `volume` (secondary, count 2) — the text divides into **Volume I (chapters I–XVII)** and
   **Volume II (chapters XVIII–XXXV)**, printed as "Volume I"/"Volume II" division lines. These are
   **absent from the EPUB nav**, so both the nav-built gold and the nav-driven detector missed the
   grouping entirely. Added as an unmasked structural container; exemplars anchor both division
   lines (Volume II sits immediately before chapter XVIII "Reflections", offset 104021).

**Precision:** volume exemplars + chapter exemplars + both apparatus spans resolve uniquely.

**Detector/Phase-B findings:** chapters XXI/XXXI lost to fused-digit labels; endnotes + colophon
undetected; volume level invisible (not in nav).

**Post-edit checks:** `gold_verify 70` → consistent (4 types); `gold_ratify 70` → chapter 35 MATCH,
spans clean.

## [102] The Collected Poems of Emily Dickinson — B&N Classics · 304,525 chars · STRUCTURED ✅✏️

Standard: front/back matter + all 5 part dividers + boundary regions read verbatim; the 589
numbered-poem markers reviewed via nav + detector segmentation (not 589 individual reads).
Detector already types front_matter, introduction, index, endnotes correctly.

**Errors found & fixed:**

1. ✏️ **`part` count wrong: 4 → 5.** The gold listed only Life/Nature/Love/Time-and-Eternity. The
   text (and TOC) carry a **PART FIVE — THE SINGLE HOUND** (the 1914 collection this edition
   appends), body divider at offset 208410. Corrected to 5; added exemplars for PART ONE/LIFE and
   PART FIVE/THE SINGLE HOUND. This was a real false negative — a whole structural part missing.
2. ✏️ **Untyped editorial back matter (FN).** After the last poem (CXLVI), a ~25K block —
   "INSPIRED BY EMILY DICKINSON'S POETRY" essay → Comments & Questions → For Further Reading —
   runs to the index (269170) but is swallowed into the final poem's section (0 uncovered runs
   masked it). Added `back_matter` `[244196–269170]` (mask=true). The detector correctly types the
   following index + endnotes `[269170–EOF]`.

**Primary structure — validated.** `poetry` = **589** numbered markers (detector recall 1.0, MATCH);
first exemplar = PART ONE poem I "SUCCESS", last = CXLVI "I did not reach thee" (confirmed the last
numbered marker). Poems still mis-typed as `chapter` (Phase-B retype gap).

**⚠️ Honest uncertainty:** at least PART ONE opens with an *unnumbered proem* ("THIS is my letter to
the world") before numbered poem I. If every part has one, the true poem count is ~589+5. 589 is the
numbered-marker count (the recall basis); flagged in the gold note, not silently resolved.

**Detector/Phase-B findings:** poems mis-typed as chapter; 5 part dividers undetected (0 parts);
editorial back matter + last poem bleed together.

**Post-edit checks:** `gold_verify 102` → consistent (3 types); `gold_ratify 102` → 589 MATCH, part
exemplars + back_matter span clean.

## [19] The Correspondent — Virginia Evans · 364,494 chars · STRUCTURED ✅✏️

Standard: front/back matter + preface region + first/last-letter regions read verbatim; salutation
distribution scanned across the whole text. Detector types front/back matter well (contents,
acknowledgments, discussion, about_author).

**Errors found & fixed:**

1. ✏️ **Mis-anchored "first letter" exemplar.** Prior anchor "Dear Ms. Toole" (offset ~33872) is
   NOT the first letter — ~25 letters precede it. The detector mis-types `[2107–28955]` as one
   `preface` block, swallowing the real narrative preface (offset 2454) **plus the first ~25
   letters**, so the original authoring anchored the detector's body_start. **True first letter =
   "Felix, my dear brother,"** (Sybil to her brother, signed "your loving sister, Sybil"). Re-anchored.
2. ✏️ **Count recharacterised as a lower bound.** 102 = "Dear X," salutations, but many letters open
   with a **name form** ("Felix, my dear brother,", "Felix,") the regex misses — true top-level
   letter count is **higher (~110–120, fuzzy)**. Kept 102 as the measurable recall basis but flagged
   it explicitly as a proxy/lower-bound, not the true total.

**⚠️ Honest uncertainty:** the exact letter count is undetermined — it needs mixed-salutation +
date-line + signature-block boundary detection across the whole epistolary body, which I did not
build. 102 is a floor, not the answer.

**Detector/Phase-B findings:** preface block over-extends across the real preface + dedication ("To
Mark, with love") + Joan Didion epigraph + first ~25 letters; body is one undetected block → COARSE.
Embedded documents (news clippings, ship manifest) are in-narrative content (not masked).

**Post-edit checks:** `gold_verify 19` → consistent; `gold_ratify 19` → both exemplars resolve,
'Dear' recount 102 MATCH.

## [5] Douay-Rheims Bible (1a24…) · 5,485,105 chars · STRUCTURED ✅ (no edits)

Standard: front matter (0–54687) + back matter (5449680–EOF) read; book-heading forms + the
"<Book> Chapter N" apparatus sampled; counts cross-checked by regex. NOT 5.5M chars verbatim.

**Both elements validated, no errors:**
- `chapter_heading` = **1334** — independently regex-confirmed (`<Book> Chapter N` = 1334, exact).
  Exemplars (Genesis-1 summary; Genesis book-intro) resolve. Editorial apparatus, masked — correct.
- `book` = **73** — Catholic canon (46 OT + 27 NT). Heading forms vary as the cue states: exactly
  **16** use "THE BOOK OF <NAME>"; the rest use "The Nth Book of Moses called X", "The Gospel
  According to…", etc. Canon-grounded, masked=false (structural) — correct.

**Considered & rejected (honest):** the text shows "THE OLD TESTAMENT" (body divider @5523) but
**no "THE NEW TESTAMENT" body divider** (only the title-page mention @224). So a testament/`volume`
level can't be cleanly anchored (unlike idx70's explicit Volume I/II) — NOT added.

**Coverage:** front matter (translation HISTORY, prefaces) + back matter (3/4 Esdras appendix,
prophet-bio notes) are all detector-region-masked; no untyped maskable FN found.

**Detector/Phase-B findings:** body_start mis-anchored at "Genesis Chapter 14" (offset 54687) —
Genesis 1–13 swallowed into front_matter (explains detector chapter 1319 vs true 1334); book level
flattened to 0. Both are detector gaps, not gold errors.

**Post-edit checks:** unchanged; `gold_verify 5` consistent; chapter_heading 1334 MATCH.

## [100] Douay-Rheims Bible (Challoner, Global Grey) · 5,487,386 chars · STRUCTURED ✅✏️(minor)

Standard: front matter (title + "Book NN" contents) read; 73 book sections + the chapter apparatus
+ colophon checked; counts cross-checked by regex. Most-analysed work in the prior ratification pass.

**All elements validated:**
- `book` = **73** — detector segments all 73 (the "Book NN – <Name>" running heads; regex "Book NN –"
  = 146 = 73 TOC + 73 body). Confirmed.
- `chapter_heading` = **1334** — independently regex-confirmed this session (1332 strict + Job-39
  inline-summary + 1-Machabees-2 trailing-period; bare 1335 − 1 parenthetical). Undetected by the
  detector (0 chapters) → the COARSE-mirage that the same-work-diff-format test (vs idx5) exposes.
- `colophon` `[5486630–EOF]` — Global Grey production note, char-exact, swallowed into the last book.

**Edit (minor consistency):** ✏️ added `role: primary` to `chapter_heading` (idx5's parallel element
is primary; the idx5-vs-idx100 discriminator must compare primary-to-primary). A3 still MIRAGE
(recall 0.00) vs idx5 OPTIMIZED (0.99), both composite ~100 — the discriminator fires.

**Coverage:** front matter (title + contents) detector-masked; no untyped FN.

**Post-edit checks:** `gold_verify 100` consistent; `a3_score` → idx100 MIRAGE recall 0.00 (intact).

## [6] 1599 Geneva Bible (Tolle Lege) · 6,689,471 chars · STRUCTURED ✅✏️

Standard: front matter + nav track + book/chapter heading forms + tail read; counts assessed for
groundability.

**This is a SCRAMBLED e-text.** The EPUB nav is broken: only 21 book entries, out of order (Micah
first), most as 12–97-char fragments clustered at 54398–54764, with the entire remaining 6.6M chars
as ONE "book". This empirically vindicates the gold's honest-null counts.

**Both counts confirmed honest-null (no edit):**
- `chapter_heading` = **null** — Geneva's numbered "arguments" mimic verse numbers; "CHAPTER" ×786
  are cross-refs, not heads. No clean text cue. Structure present (exemplar resolves), count
  honestly null. Correct.
- `book` = **null** — ~80 books, but ALLCAPS headings conflate with section heads and the nav is
  broken; not cleanly countable. Book heading "THE FIRST BOOK OF MOSES, CALLED GENESIS" confirms
  presence. Correct.

**Error found & fixed — false negative:**

1. ✏️ `glossary` `[6667696–EOF]` (~21.8K) — a back-matter "Glossary of Middle-English Terms" (A–Z,
   abalienate→wrought, WORD/MEANING/SAMPLE-LOCATION columns) sits at the very end, swallowed into the
   trailing giant "book". The scramble is striking: the glossary's **title line is displaced to the
   front** (offset 1283, where the detector mislabels the foreword block "glossary"), while its
   **content is here at EOF**. Added; char-exact start ("GLOSSARY\n\nWORD…") to EOF.

**Detector/Phase-B findings:** nav broken (21 scrambled fake books); chapter level 0 → MIRAGE;
front "glossary" element is actually the foreword (nav mislabel).

**Post-edit checks:** `gold_verify 6` consistent (3 types); `gold_ratify 6` glossary span clean.

## [101] LDS Triple Combination (2013 PDF) · 4,904,644 chars · STRUCTURED ✅ (no edit) ⚠️

Standard: front matter + back-matter boundary regions read; chapter_heading exemplars verified.
This is the deliberate **degraded-PDF stress-case** (soft-hyphens, fused footnote-letters, wrap).

**Element validated:** `chapter_heading` = **null** (primary). Two sub-forms confirmed by eye, both
exemplars resolve: BoM em-dash chapter summaries (2 Nephi 17) + D&C "Section N" verse-range headers.
Count honestly null — PDF degradation makes the BoM half not cleanly countable. PRESENT-OK.

**Significant detector finding (documented, NOT a gold edit):** back_matter `[2861206–4904644]` is
2.04M chars (42% of the work) and is **mis-segmented**: its first ~366K is actually **Pearl of Great
Price scripture** (Book of Moses/Abraham) wrongly typed as `endnotes` (visible footnote-letter
artifacts: "f‌truth", "g‌no", "h‌know"), i.e. ~366K of body scripture wrongly masked; the *real*
back matter (a topical-guide/index, "Candle. See also Candlestick…") begins ~3227562.

**⚠️ Honest limitation:** I did NOT add a corrected body/back_matter boundary. In this degraded PDF
the true PoGP-scripture↔index boundary cannot be char-anchored reliably (footnote-letter fusion,
wrap, soft-hyphens), and idx101's role in the gold is explicitly a degraded stress-case, not a clean
reference. Fabricating a precise boundary here would be guessing — surfaced instead of invented.

**Post-edit checks:** `gold_verify 101` consistent (1 type); exemplars resolve.

---

# Cross-work summary & adversarial self-review

**Coverage:** all 9 gold works read/structured-reviewed by eye. Post-edit, `gold_verify` (all) =
consistent; `gold_ratify` (all) = 1 explained flag (idx103, see below); `a3_score` (all) = ratings
UNCHANGED from baseline (OPTIMIZED=3, MIRAGE=3, COARSE=2, PRESENT-OK=1) — coverage additions did not
perturb the primary recall ratings (verified no regression).

**Edits applied (7 works touched; idx5 clean, idx101 documented-only):**

| idx | edits |
|----|-------|
| 104 | 2 mis-anchored exemplars fixed (true first/last poem); +colophon (transcriber note); count re-grounded to foreword TOC |
| 103 | +preface +dedication +contents +index +back_matter (5 untyped FNs); poems validated vs printed TOC |
| 70  | +volume (2: Vol I ch I–XVII / Vol II ch XVIII–XXXV) |
| 102 | part 4→**5** (PART FIVE "THE SINGLE HOUND" was missing); +editorial back_matter |
| 19  | mis-anchored first-letter exemplar fixed ("Felix, my dear brother,"); count recharacterised as lower-bound |
| 5   | none — validated clean |
| 100 | +role:primary on chapter_heading (discriminator parity with idx5) |
| 6   | +glossary (end-of-work, displaced by a scrambled e-text) |
| 101 | none — degraded stress-case; mis-mask documented, not fabricated |

**Systematic pattern (the most important finding):** in **3 of 9 works (104, 102, 19)** the original
"first/last instance" exemplars were anchored to the **detector's body_start**, which is itself wrong
when front matter over-swallows the opening (Cummings) or editorial/preface regions absorb early
content (Dickinson PART FIVE tail; Correspondent's first ~25 letters). The gold had inherited the
detector's segmentation errors. This is an authoring-process bias, not random: any work whose detector
mis-anchors body_start is suspect for mis-anchored exemplars. All three are now corrected to true
text positions.

**Second pattern — leaked maskable matter:** front/back matter that the detector fails to regionise
gets swallowed into the body blob and left untyped (idx103 indexes+catalog+TOC; idx102 editorial
block; idx6 end-glossary). Added in every case. Where the detector DOES regionise front/back matter
correctly (idx5, idx100), nothing was added — only genuine FNs.

**Open uncertainties (honestly surfaced, not resolved):**
1. **idx102 poem count** — 589 *numbered* markers, but ≥1 part opens with an unnumbered proem; true
   count may be ~589+5. 589 kept as the recall basis.
2. **idx19 letter count** — 102 = "Dear X," salutations is a LOWER BOUND; name-form openings push the
   true total to ~110–120 (fuzzy). Exact count needs mixed-salutation boundary detection (not built).
3. **idx101 body/back_matter boundary** — ~366K of Pearl-of-Great-Price scripture is mis-masked as
   endnotes, but the degraded PDF defeats reliable char-anchoring; not fabricated.
4. **idx103 flag** — "28" needs the documented Hill-Wife −5 adjustment (nav 33 − 5 sub-parts); no
   single automated signal lands it, so it stays flagged-but-explained.
5. **Type choices** — idx104 transcriber note → `colophon` (vs back_matter / a future transcriber_note);
   idx103 "Note" → `preface` (vs foreword/introduction). Both soft, flagged in the contracts.

**What this pass did NOT do:** per-instance char-level boundaries for the 1334×2 Bible chapter
summaries, 589 poems, etc. are NOT individually stored (preserved the anti-Goodhart counted-repeating
design). Boundary precision was validated by eye on every span element + first/last instances; the
detector-formed per-instance edges remain a Phase-B measurement, not gold-stored truth.

---

# Phase 2 directives (2026-06-18, user) — IN PROGRESS

**Design reversal (approved by user):** store + track **per-instance edges of everything** — every
chapter/poem/letter/section, not count+exemplars. This reverses the anti-Goodhart "no stored edges"
choice; tradeoff noted (it reintroduces the risk of tuning the detector to exact gold edges — to be
managed by keeping the gold an independent hand/parser-verified artifact, not a detector output).

**Mask-type coverage (answer to "are all types represented?"):** 15 / 34 present
[back_matter, book, chapter, chapter_heading, colophon, contents, dedication, endnotes, glossary,
index, letter, part, poetry, preface, volume]. **19 missing** — of which:
- present-in-works-but-unannotated (add per-instance where they occur): footnotes, epigraph, insert,
  title_page, copyright, front_matter, foreword, introduction, afterword, acknowledgments,
  about_author, discussion, bibliography, appendix, header, body.
- **NO exemplar in any of the 9 works → need a new gold work:** `translation` + `commentary`
  (a study-bible / ANF-style anthology). `addendum` also still unexemplified.

**Done this phase:**
- ✅ `OceanofPDF.com` watermark strip added to `ingest/extractor.extract_text` (covers all formats;
  collapses the blank line it leaves). 113 extractor/ingest tests pass. (Not in the gold-set copies,
  which are Anna's-Archive sourced — defensive hardening.)
- ✅ idx102 poem count corrected **589 → 593** (589 numbered + 4 named section-opening proems:
  'This is my letter to the world'/ONE, 'My nosegays are for captives'/TWO, "It's all I have to bring
  to-day"/THREE, 'One sister have I in our house'/FIVE; PART FOUR has none). First exemplar re-anchored
  to the true first poem (the ONE proem). 'FROM THE PAGES OF…' header excluded as front matter.

**Remaining (large, multi-session):** idx101 perfect Triple-Combination parse (full spec captured in
task); idx19 per-letter metadata (recipient/sender/date/email/insert); per-instance edge generation
+ schema for all works; cover the missing types incl. a translation/commentary gold work.

---

## idx101 — LDS Triple Combination (2013 PDF): structural parse + gold expansion (2026-06-18)

**Root finding — the extraction was scrambled, not the source.** The naive linear `reference_text()`
dump of `LDS_eng.pdf` (5.0M chars, 1375 pages) emits, *per page*, the **footnote apparatus BEFORE the
chapter it annotates**, and interleaves the two verse columns. This is why prior detection saw a
"mirage" (chapter_heading present but un-countable). It is an extraction-order artifact, NOT PDF
degradation — confirmed by pymupdf block geometry.

**Solution — column-aware geometry parser** (`.scratch/mask-eval/lds_extract.py`). Per page, `get_text("blocks")`
bboxes cleanly separate three layers:
- **running header** (`y0 < 36`): `"<printed#>  <Book chap:verse-range>"`, e.g. `"32  Abraham 2:1–10"`.
- **body band**: full-width headers (book title + italic argument; `x` spans the gutter) and two verse
  columns (left `x0≈36`, right `x0≈222`), read left-column-top-to-bottom then right-column.
- **footnote apparatus**: 3 columns at the page bottom. Detected without a magic-y by the signature
  **middle footnote column `x0≈159`** — an x-band the verse body never occupies; apparatus top =
  `min(y0)` of blocks in that band.
A book's opening page has no page-number running head, so its top block is the **book title** (no
leading digit) → promoted to a structural header.

**Recovered map — canon-validated to the exact count.** `lds_extract.py books/scan` over all 1375 pages:

| Volume | Structure | Count | Validation |
|---|---|---|---|
| Book of Mormon | 15 books | **239 chapters** | 1Ne22 2Ne33 Jacob7 Enos1 Jarom1 Omni1 WofM1 Mosiah29 Alma63 Hel16 3Ne30 4Ne1 Morm9 Ether15 Moroni10 — **= canonical 239** |
| Doctrine & Covenants | 138 sections | 138 (+2 Official Declarations) | max Section = distinct Sections = 138 |
| Pearl of Great Price | 5 books | 16 chapters | Moses8 Abraham5 JS-M1 JS-H1 AoF1 |

Total chapter-level containers = **393**. The exact-canon match (239 BoM chapters, 138 D&C sections)
is independent ground truth that the geometry parse is sound — no hand-anchoring involved.

**Gold contract expansion** (`work-101.json`): **1 → 5 annotation types**, all `gold_verify`-clean
(8 exemplar anchors resolve uniquely; mask defaults match taxonomy):
- `volume` (secondary, 3) — BoM/D&C/PoGP, anchored on each volume's Introduction first line.
- `book` (secondary, 20) — 15 BoM + 5 PoGP; exemplars 1 Nephi + Third Nephi (title-form stress-point).
- `chapter` (secondary, 393) — canon breakdown in cue.
- `chapter_heading` (primary, **393**, was `null`) — two sub-forms (BoM em-dash summary / D&C section
  header). The geometry parse RESOLVED the scramble that made this "not cleanly countable" before.
- `footnotes` (secondary, NEW) — the cross-ref apparatus, now recognized as its own masked layer.

**A3 score:** rating **COARSE**, recall **0.60** (chapter 236/393), coverage 100%, unc 0%. This is a
*more honest* score than the prior "PRESENT-OK / count unverified": the detector recovers only 236 of
393 chapters and 0 of the volume/book/footnote levels — the gap is now a measured number.

**Minutiae / adjustments / honest uncertainties:**
1. **5 BoM + 3 PoGP single-chapter books** (Enos, Jarom, Omni, Words of Mormon, 4 Nephi; JS—Matthew,
   JS—History, Articles of Faith) print **no "Chapter 1" label** — straight to verses. `chapters=0`
   from the label scan = 1 actual chapter. Encoded as implicit.
2. **384 explicit labels recovered vs 385 expected** (234 BoM + 13 PoGP labeled + 138 D&C). The
   1-label shortfall is a single degraded/wrapped "Chapter N"/"Section N" — **not yet localized**;
   flagged, not silently rounded.
3. **"+1 decl" false positive** traced to the Contents dot-leader line `"Official Declarations . . . 291"`
   matching the declaration regex — a Contents artifact, not a real declaration in Moroni. (The 2 real
   Official Declarations are in D&C: OD-1 ~printed 291, OD-2 at pdf 860.)
4. **Footnote apparatus is NOT exemplar-anchorable by content** — entries reuse Topical-Guide targets
   (`"Record Keeping"` recurs 28×, `"tg Birthright."` 3×), so no footnote string resolves uniquely.
   Annotation carries presence + count_cue only; edges come from the parser.
5. **Dropcap artifact**: verse-1 / intro initial capitals extract as separate one-char blocks
   (`"he Doctrine and Covenants is…"`). Volume anchors deliberately start past the dropcap.
6. **Facsimiles** (3 in Book of Abraham; "A Facsimile from the Book of Abraham" header, images skipped,
   "Explanation" + "Fig. N" verse-like lines): **type `insert`, NOT yet annotated** — precise body
   anchors pending a read of pdf pages ~899/911/912. Fac No.2 belongs inside Book of Abraham (page
   before Abraham's start), per user spec.
7. **Back matter not yet anchored**: Pronunciation Guide (`glossary`), Index (`index`), Church History
   Maps + Photographs (`appendix`). Structure known from the scan; precise unique start anchors PENDING.
8. **Inline footnote-letter markers** (`a born of b goodly c parents`) still pollute verse-body text —
   stripping needs span-level (`get_text("dict")`) superscript-font filtering, a polish pass.

**DECISION REQUIRED (Sir) — the per-instance-edge fork.** Phase-2 directive #1 wants stored per-instance
edges for everything. For idx101 that is only meaningful if the **column-aware parser becomes idx101's
canonical `reference_text()`** (the current linear stream interleaves apparatus before each chapter, so
edges against it are nonsense). Promoting `lds_extract.py` into `core/palimpsest/ingest/extractor.py`
as a PDF-geometry path WILL change the product detector's idx101 input (and its A3 score). Options:
**(a)** make the geometry parse canonical for idx101 (recommended — it is the only path to the true 393
edges, and the gold already references it); **(b)** keep linear reference_text() and treat the parser as
a gold-only oracle. Recommend (a); flagged here rather than chosen unilaterally because it touches
product extraction + scoring.

---

# Phase 2 — 11 new gold works (2026-06-19): scholarly-translation type-gap closure

**Mandate (user, 2026-06-18):** add 11 new gold works and author each to a `gold_verify`-GREEN
contract, end-to-end, autonomously. Gold set expands **9 → 20 works**. Primary motivation: close the
`translation` + `commentary` exemplar gap (previously **no** work in the set exemplified either type).

**Execution model.** Per-work authoring delegated to general-purpose subagents against a shared spec
(`.scratch/mask-eval/GOLD_AUTHORING_SPEC.md`); each subagent authored its contract to `gold_verify`
GREEN, ran `a3_score`, and returned a report. Every contract was then **independently re-verified** by
Jarvis (`gold_verify <idx>` GREEN + `a3_score <idx>` + spot-review of type-boundary judgments). Full-set
`gold_verify` = **GREEN across all 20 works**.

| idx | Work | types | A3 | primary recall | headline |
|---|---|---|---|---|---|
| 18 | Ante-Nicene Fathers Vol. 3 (Tertullian; Schaff) | 10 | MIRAGE | 0.00 | **translation(23)+commentary(13) — type-gap closed** |
| 42 | OT Pseudepigrapha Vol. 1 (Bauckham/Davila) | 9 | COARSE | 0.67 | translation(39) primary; part-heads only in TOC |
| 48 | NT Apocrypha / MNTA (Burke, Eerdmans) | 12 | MIRAGE | 0.00 | translation recalled but intro/biblio 0/29 |
| 56 | The Last of the Mohicans (Cooper) | 5 | MIRAGE | — | **epigraph(33)** new exemplar (entire layer undetected) |
| 64 | The Books of Enoch (1/2/3 Enoch, Lumpkin) | 8 (7 types) | OPTIMIZED | 0.97 | chapter 221/228; no fabricated 1-Enoch "parts" |
| 71 | Jekyll & Hyde (Stevenson) | 3 | COARSE | — | copyright/chapter×10/colophon; nbsp gotcha handled |
| 80 | Dead Sea Scrolls Translated (García Martínez) | 9 | MIRAGE | 0.00 | translation≈270; NFD/NFC filename snag fixed |
| 29 | The Message of the Qur'ān (Asad) | 9 | MIRAGE | 0.00 | translation×114 + footnotes×5326 (pooled @ EOF) |
| 105 | Dead Sea Scrolls Reader Vol. 1 (Parry & Tov) | 8 | MIRAGE | 0.02 | translation 1/63 — textbook coarse mirage |
| 106 | Adam & Eve in the Armenian Tradition (Stone) | 16 | MIRAGE | 0.00 | **richest contract**; translation(121)+commentary(6) |
| 107 | The Holy Quran (Sher Ali / Ahmadiyya, PDF) | 12 | COARSE | 8.11 | over-segments on per-page running heads (114 surahs) |

**Type-gap closure (the headline).** `translation` and `commentary` are now exemplified across idx
18, 29, 42, 48, 80, 105, 106, 107 — the central gap that motivated the expansion. New exemplars also
landed for `epigraph` (idx56, 33×, primary), and reinforcement for `insert`/`copyright`/`footnotes`.

**The A3 pathology this batch pins down.** Nearly every scholarly-translation work scored MIRAGE
(composite ~99–100, primary recall ~0.00): the detector emits a flawless-looking composite by finding
coarse chapter containers while completely missing the high-value `translation`/`commentary`/
`introduction` layers underneath. idx106 is the limit case — composite **100.0**, primary recall
**0.00**. These contracts convert that blind spot from anecdote into measured ground truth.

**Key type-boundary judgments (spot-reviewed, all sound):**
- **idx18** — `translation`(23) = bracketed `[Translated by <name>.]` credits; `commentary`(13) =
  Coxe's first-person "Elucidations" essays; `introduction`(5) = "Introductory Notice" notices. Three
  principled, non-overlapping editorial layers.
- **idx29** — per-surah preamble typed `introduction` (masked editorial framing), not `commentary`;
  `footnotes`=5326 are pooled at EOF (marker→note edges unrecoverable from the linear stream — same
  scramble class as idx101; counted, not edge-anchored).
- **idx106** — Armenian-script passages deliberately **not** annotated as a separate type (no
  original-language type in the taxonomy → no fabrication); English renderings = `translation`(121,
  cross-validated against both Authors-Cited and Authors-Quoted lists); Part-I analytic prose =
  `commentary`(6, unmasked) over the `discussion` alternative.
- **idx64** — the five named 1-Enoch "sections" appear only as scholarly chapter-range descriptions in
  the intro; body has no printed division headings, so encoding them as `part` was correctly refused.

**Honest scoping decisions (documented, not hidden):**
- **idx107 Arabic** — original Arabic verse text extracts as garbage glyphs (broken font glyph→Unicode
  map). Scoped IN: English translation + all Latin-script structure. Scoped OUT: Arabic body (OCR
  deferred). No Arabic masks fabricated.
- **idx105/106 RTL** — Hebrew/Aramaic and Armenian transcriptions extract with garbled glyph order; the
  rated English-translation layer is clean. Documented per-work.
- **null counts** — `footnotes` left `expected_count=null` wherever two interleaved apparatuses reuse
  non-unique strings (idx18/42/48/106) rather than guessing a count.

**Goodhart controls (decision, told Sir).** Storing per-instance mask edges is safe **only with three
controls**, not secrecy/blinding alone: (1) **independence-of-derivation** — gold edges come from
canon / by-eye / parser oracle, never the detector (secrecy doesn't fix shared lineage); (2) a
**held-out slice + capped re-evals** (score leaks via adaptive overfitting); (3) **tolerance-based
scoring** (A3 is recall-of-count, not exact-offset). Keep all three.

**Correction to the idx101 fork note above.** The `OceanofPDF.com` watermark strip in
`ingest/extractor.extract_text` was confirmed a **deliberate, tested Phase-2 change** (113 extractor/
ingest tests pass), not a mid-run subagent edit. Full-set `gold_verify` GREEN (20 works) confirms it
broke no anchor — text-anchored gold (resolve-by-search, offsets derived at eval) is robust to the
offset shift a watermark removal causes.

**Git status:** all 11 contracts + this record are **UNCOMMITTED** (no commit approved by Sir).

---

# idx101 #9 — parser-to-product promotion (2026-06-19): geometry parse is now canonical

**Decision executed (Sir pre-approved option a, "after the subagent batch").** The column-aware
geometry parser is promoted out of `.scratch/` into the product and made idx101's canonical
`reference_text()`.

**What changed:**
- New product module `core/palimpsest/ingest/lds_columnar.py` — `parse_page()` (block-geometry split:
  running-head / 2 verse columns / 3-column footnote apparatus) + `extract_fulltext(pdf)` which
  assembles per-page reading order **headers → body (L col then R col) → apparatus**, reversing the
  linear dump's apparatus-before-chapter scramble. Running-head printed#/ref (repeated page furniture)
  dropped; book-opening title kept as a structural header.
- `ingest_file()` gained an explicit opt-in `text_extractor: Callable[[Path], str] | None` override
  (project.py). **No change to the generic `extract_text()` PDF dispatch** — auto-detection was
  rejected as too risky (could misfire on the large Bible PDFs and corrupt a GREEN contract). idx101
  was re-ingested through the normal product path with `text_extractor=extract_fulltext`, so
  `reference.txt`, `reference.sha256`, paragraph/section/sentence segments, and all metadata counts
  regenerated consistently.
- idx101 `reference_text()`: **5,004,232 → 4,885,404 chars** (post-`normalize()`); de-scrambled, in
  true reading order. All 385 structural labels recovered (247 Chapter + 138 Section).

**A3 delta — HONEST FINDING: no change.** COARSE, recall **0.60** (chapter_heading 236/393),
composite 98.7 — *identical* to the scrambled-stream baseline. **The scramble was never the
recall bottleneck.** The detector misses 157 of 393 chapter headings due to heading-recognition
limits (format variety, dropcap/wrap artifacts), independent of reading order. The promotion's real
payoff is (1) **reading-order correctness** — the product's sequential tracks (sentiment,
narrative_arc, coreference) read `reference_text()` in order, so the de-scrambled stream materially
improves their input for idx101; and (2) **back-matter unblocking** (below). Reporting the null A3
delta correctly relocates the recall gap onto the detector, not the extraction.

**Back-matter anchors (now unblocked) — idx101 expanded 7 → 11 types, 12 annotations, gold_verify
GREEN.** Added: `index` (the scripture-wide Index, ~3.040M→4.848M — NOT the ~4.867M running-header
artifact), `appendix` ×2 (Church History Maps; Church History Photographs→EOF), `glossary`
(Pronunciation Guide, between BoM and D&C), `front_matter` (Testimonies of the Three/Eight Witnesses,
in BoM front matter). All anchors verified unique (`reference_text().count(anchor)==1`).

**Remaining idx101 polish (bounded, not blocking):**
- Inline footnote-letter markers still lightly pollute verse-body text (minutiae #8) — needs span-level
  `get_text("dict")` superscript-font filtering, a separate pass.
- `lds_columnar.py` band constants are tuned to the 2-column verse body; within the multi-column
  map-index / glossary / photo pages, *entry-block* ordering is locally imperfect (headwords/captions
  still extract readably; section boundaries and alphabetical order hold — presence + section-level
  anchoring are sound). A back-matter-aware geometry mode would perfect it.
- Per-instance stored edges (Phase-2 directive #1) remain a separate cross-work workstream; idx101
  stays on the count+exemplars schema for consistency with the other 19 works.

**Full-set re-verify after re-ingest:** `gold_verify` GREEN across all **20 works**.
