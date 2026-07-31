# THE CHAPTER WORKFLOW — bringing one chapter of the DR to standard, distilled from Genesis 1 and 16

**The standard.** Every verse of every source's OCR matches the corresponding verse in **each** of the four
reference witnesses at **≥0.90**, with the best approaching 1.000, and every ſ-surface **CLOSED**. That is
`verses × 4 sources × 4 references` cells (Genesis 1: 496; Genesis 16: 256) plus a surface verdict per rescued
cell. A cell below the bar stays **OPEN** and blocks — it is never reclassified as acceptable.

**Results so far — BOTH WORKED CHAPTERS ARE CLOSED.** Genesis 1: **496/496 = 100%**, all ſ-surfaces closed,
means 0.982/0.981/0.968/0.968. Genesis 16: **256/256 = 100%** from a 73.8% cold start, means
0.990/0.990/0.984/0.984. The figure passed *through* 87.5% when surface-gated adoption was turned on — it fell
because the standard rose, then went past the old number as the span-edge defects were fixed. **The last verse
closed with no model call at all**: it was two page-model geometry bugs at one leaf junction (§13 Q34). Before
commissioning a training run on a residual, exhaust the geometry.

> **⚠ TWO INTERPRETERS.** Everything here runs on `../ocr-venv/bin/python`. The other venv
> (`../../../.venv/bin/python`) cannot import kraken and will fail confusingly.
> Tests: `../ocr-venv/bin/python -m pytest tests/` → 167 passed.
> (Module names keep a historical `gen1_` prefix; they are all chapter-parameterized via `--chapter`.)

---

## Phase 0 — Word boxes (once per chapter, ~150s for 17 leaves)

```
../ocr-venv/bin/python gen1_wordboxes.py --chapter N
```

Leaves are discovered from `.corpus-localize-<ocr_dir>.json`, not hand-listed. Output
`.wordboxes-genesis-N.json`. **Why word boxes at all:** `kraken`'s `rpred` returns a per-CHARACTER polygon in
`ocr_record.cuts`, which the stored corpus stream throws away — it is the only reason this project believed
word geometry was unavailable.

## Phase 1 — Audit the REFERENCES before touching the OCR

**Do this first, always.** In both chapters worked so far the governing archaic reference was defective, and in
both cases it looked exactly like an OCR problem. A reference gap has a signature: **one reference's mean sits
far below the others'** (Genesis 1: s_dismas 0.756 vs odr_com 0.946; Genesis 16: 0.883 vs 0.943).

```
../ocr-venv/bin/python ref_alignment_audit.py --book genesis
```

Two distinct faults, with different remedies:

| fault | signature | remedy |
|---|---|---|
| **Mis-numbering** (Gen 1) | reference has N+1 verses; verse k+1 matches the others' k at ~1.000, shift persists | add a `merge` entry to `ref_renumber.CORRECTIONS` with its corroboration |
| **Apparatus contamination** (Gen 16) | one verse >1.4× the others' median length; head aligns, tail matches nothing | automatic via `ref_renumber.load_corrected(..., trim=(book, chapter))` |

**Only corroborated corrections, and never to the source file.** `ref_renumber` rewrites keys in the loaded
dict; deleting an entry restores the old behaviour exactly.

**Two traps here, both hit for real:**
- The audit's own comparison must **fold archaic/modern spelling**, or `sabates_a`/`madueke_b` score `heauen`
  vs `heaven` as different words and a unanimous 3-witness shift is dismissed as a 1-witness disagreement.
- The contamination trim **must check whether the tail is the NEXT verse.** Without that guard it fired 149
  times corpus-wide and destroyed real scripture (`matthew/1/3` lost "And Aram begat Aminadab…"), because a
  reference that MERGES two verses looks identical to one carrying a glued annotation on a length test alone.
  It is opt-in and chapter-scoped for the same reason.

**Distinct from all of the above:** a divergent *reading* at a correctly numbered, uncontaminated verse (gen
1:25 — all four witnesses read the page right, s_dismas's wording simply differs). That is a collation
judgement. **Flag it; never auto-pass it.** (§13 Q21, still open.)

## Phase 2 — Measure cold, before tuning anything

```
../ocr-venv/bin/python gen1_matrix.py --chapter N --json genN-matrix.json
```

Read the blocks **by source**, not by verse. Genesis 16 came in at 73.8% with zero chapter-specific tuning,
which tells you immediately that the generalizable rules are carrying most of the load and only the outliers
need work. Record this number — it is what any later claim of improvement is measured against.

## Phase 3 — LOOK AT THE PAGES OF ALL FOUR SOURCES, starting with the worst

**This is the phase that cannot be skipped or inferred.** And it must cover **every source, not only the
worst** — a source that scores well still hides misreads. Genesis 16 proved it twice: S9 came in at 16/16 on
both archaic references, and its leaf still had `therefore` for the printed `therfore` and `afflicte` for
`afflict`; S1 read 16/16 while printing `SARAI therfore` where the transcript carried `and ſmaelSARAI`. Work
the worst source first, because that is where the structural findings are, then read the others for the
stragglers.

Render the leaf and read it:

```python
import reocr_r3; reocr_r3._render_page_png(ocr_dir, page, "/tmp/x.png", maxw=2400, crop=(x0,y0,x1,y1))
```

Then read the PNG. Every layout finding in this project came from doing this, and none came from reasoning
about coordinates. Also dump the rows with geometry:

```python
for ts, r in PM.row_tokens(od, page, wb[od][str(page)], lex): ...   # x/y per token
```

**What to look for, in the order it has actually mattered:**

1. **Is this the chapter's OPENING leaf?** It will carry a title block, an italic argument, and an engraved
   drop capital the recognizer cannot see. Add a `CHAPTER_MODEL[(ocr_dir, chapter)]` entry:
   `open_page`, `chapter_open_y`, `drop_cap`. Genesis 16/S6: `CHAP. XVI.` at y 413, argument to y 622, and
   `ARAI therfore the wife of Abram` → the engraved S makes it **SARAI**.
2. **Is the leaf ANNOTATIONS-ONLY?** The second edition prints each chapter's commentary on its own leaf
   (`jp2-S06` p77 for Genesis 16 is entirely notes on the Manichees and Luther). The localizer credits it to
   the chapter, so it enters the word-box set and its prose competes for verse spans. Excluded whole-leaf by
   `_is_annotation_leaf`, matched on `NNOTATION` — the leading `A` is lost into the previous word by the
   recognizer, so match the distinctive core, not the whole word.
3. **Does this leaf have its own measure?** `jp2-S06` p18's body runs x 848–1670 while its ordinary leaves run
   to 1789 — one right bound cannot serve both. Add `PAGE_OVERRIDE[(ocr_dir, page)]`. **The unit that owns a
   layout is the LEAF, not the witness.**
4. **Sweep, don't guess.** The Genesis 1/S6 band was swept: `hi=0.825 → 44/62`, `hi=0.765 → 59/62`. The right
   bound carried nearly everything and the left bound was inert. Record which parameter actually moved.

## Phase 4 — Re-measure and attribute

Re-run Phase 2. **Attribute every change to the rule that caused it, and report score-neutral rules as
neutral.** Two real examples: the lexicon-evidenced hyphen rejoin fires twice in Genesis 1, both correct, and
moves nothing; the Genesis 16/S6 layout rules are correct and moved 0.943→0.944, because that leaf's problem
was recognition all along. A correct rule that changes no score is not a win.

**If a rule regresses, revert it and pin the negative result** (`_trim_left_margin`, kept unwired with its
figures and a test asserting it stays that way). Negative results are only cheap once.

## Phase 5 — Rung 3 on the residual

```
../ocr-venv/bin/python gen1_r3.py --chapter N --improve-below 0.95
```

**Always pass `--improve-below 0.95`.** The bar is 0.90 but a cell at 0.91 usually holds a real misread, and a
cell that clears the bar drops off the worklist and keeps whatever it had. Measured: on Genesis 1 — already at
496/496 — running at 0.95 raised the means from 0.974/0.973/0.961/0.961 to **0.981/0.980/0.967/0.967** without
changing a single verdict. On Genesis 16 it took the cleared count from 6 to 17.

Local olmOCR-2 via MLX — **no paid API.** ~20–60s per crop; Genesis 1 needed 6 crops for 124 verse-instances
(~5%), Genesis 16 needed 20 for 64 (~31%). Adoption requires beating the incumbent on the governing archaic arm
AND clearing the bar; better-but-short is recorded and the cell **stays OPEN**. Adopted cells are overlaid and
labelled `r3` in the matrix — `--no-r3` ablates them.

`--improve-below X` also re-reads cells that already pass but score under X. **Use it:** S6 v8 in Genesis 1
cleared the bar the moment the apparatus filter dropped its `(b)`, which took it off the worklist and silently
kept `firmameut … euenins mornins` in place of a better reading already established by eye. A passing score is
not a reason to keep a worse transcript.

**The localization discipline, which is where all the difficulty is:**
- **A verse crop is not a verse.** `verse_geom.verse_crops` returns the band of LINES a verse occupies, so the
  crop carries its neighbours. Scored whole, all six Genesis 1 re-reads returned **0.000 and all six were
  good.** Localize the crop transcript first — on the **janvier** grid, never on the scoring reference.
- **Restrict the grid to the verses the crop contains**, derived from the page's own geometry. Against the whole
  chapter it mis-assigns (asked for 1:15, returned 1:14).
- **But keep the full grid and the hybrid `best_spans` as candidates too**, and select on janvier fit. The
  restricted grid alone leaves gen 1:13's trailing `Againe` attached (1.000 → 0.883); only the walk arm trims it.
- **Never search for the leaf by fit.** For a chapter-stream span, take the leaf from
  `.corpus-localize-<ocr_dir>.json`. Searching all leaves for the best fit chose a **Genesis 15** leaf for
  Genesis 16:9 and cropped `the birdes he diuided not … a deepe sleepe fel vpon Abram`. A fit score cannot tell
  "the verse is here" from "something matched".
- **Run R3 output through `PM.clean_tokens`.** It bypassed the filter once and a printed verse number `9.`
  reached the deliverable.

## Phase 6 — The ſ surface

olmOCR modernizes ſ→s and `fold_archaic` folds ſ/s, so **the content gate cannot see the loss** (measured on
Genesis 1: 7 long-s characters). `s_arbiter.transfer` takes R3's CONTENT with R2's **observed** spelling
wherever the two agree modulo the ſ-fold — R2/reichenau is itself ſ-faithful, so those glyphs are attested.

- **Never `long_s_rule.restore_long_s`** (~90.4% on this project's gold = about 1 invented glyph in 10
  published as the printed surface).
- Where R3 *corrected* R2 the surface is unattested → `unresolved`. Render the crop and **read it**.
- **Content and surface are separate paths.** `s_arbiter.arbitrate` raises if a reading changes the content
  skeleton, and that guard is correct — it caught an n→m fix (`firmanent`→`firmament`) being smuggled through
  the ſ path. Content corrections go in `gen1_r3.VISUAL_CONTENT` and are re-scored; `VISUAL_READINGS` answers
  only "is that f/s a ſ?".

## Phase 7 — Exit criteria

1. Every cell ≥0.90 against all four references.
2. Every R3-adopted cell's ſ-surface **CLOSED** with zero unresolved tokens.
3. No apparatus tokens in any verse text — re-run the sweep from §"Footnote sweep" below.
4. Full suite green; the live corpus pipeline unaffected (the page model is standalone).
5. Every rule added is attributed, and every rejected rule pinned with a test.

### Footnote sweep (Phase 7 check, and it caught 7 real artifacts in Genesis 1)

Scan every verse text for: parenthesized single letters (`(b)` `(d)` `(e)` — the second edition's inline
footnote references), bare single letters other than `a/A/O/o/I`, single letter + stop (`S.` `I.` — marginal
cross-references merged into a body row), and bare or glued verse numbers (`16.And`). These survive every
geometric filter because they are set INSIDE the measure. Handled by `PM.is_apparatus_mark` / `PM.clean_tokens`.
`†`/`‡` are genuine printed verse marks — no reference carries them and they cost nothing (punctuation folds), so
they stay.

---

## What generalizes, and what does not

**Generalizes — do not re-derive per chapter:**
`SOURCE_MODEL` bands (per witness) · `_is_running_head` (shape, not y — no `head_frac` can work, S9's p33 head
ends *below* p32's first body line) · `_is_foot_line` (catchwords) · `_is_annotation_leaf` · the sloping-row
reference (`ROW_TOL` 0.5 / `ROW_MAX_DRIFT` 0.8) · the asymmetric band edges (left = gutter, test the word's
START; right = measure, test its CENTRE) · the chapter stream · `clean_tokens` · `ref_alignment_audit` ·
scoring each reference on its own arm (`archaic_id` for s_dismas/odr_com, `modern_id` for sabates_a/madueke_b).

**Per chapter:** `CHAPTER_MODEL[(ocr_dir, chapter)]` — `open_page`, `chapter_open_y`, `drop_cap`.
**Per leaf:** `PAGE_OVERRIDE[(ocr_dir, page)]`.
**Per locus:** `ref_renumber.CORRECTIONS`, `VISUAL_CONTENT`, `VISUAL_READINGS`.

## THE RULE THAT GOVERNS EVERY RULE (2026-07-30, §13 Q47)

**A rule is measured by the TEXT IT CHANGES, not by the verdicts it flips.** `split_glued` measured HELPS 8 /
HURTS 1 / net **+8 cells** across all 50 chapters with chapters 1 and 16 unmoved — and alters **1,356 tokens**,
tearing real words into morphemes (`lawful` -> `law ful` 28x, `faithful` -> `faith ful` 14x, `prayeth` ->
`pray eth` 17x). The matrix could not see it because the corruptions were score-neutral or fell in cells that
already failed.

**So before adopting anything that edits text, run `faithfulness_audit.py`** and read what it changes. The first
full audit (413,814 tokens) cleared every rule that is ON — `clean_tokens` 1.92%, `rejoin_break` 0.57%,
`s_arbiter` archaic-equivalence 0.03%, `s_lexicon` 0.23% — and isolated the one that was not.

## The standing traps

- **A DEAD METRIC IS NOT A TIE — AND IT IS INSIDE A PRODUCTION SELECTOR ON A THIRD OF THE CORPUS (§13 Q36).**
  `best_spans` chooses between its two arms with `janvier_fit`, which returns 0.000 for any PARTIAL span, so on
  **33.7% of 36,833 live verse-spans** the comparison is `0.0 > 0.0` and the aligner wins by default — 40.7% of
  every decision the hybrid actually makes. `verse_locate.partial_fit` (precision/recall/F1 over ordered token
  matches) sees 84.7% of them. Use it to RESCUE the dead rows only: replacing the selector outright loses 18/18
  changed verses on gold. And note what the gold pages could not tell us — 1/165 dead rows there, because they
  are whole-verse pages by construction. **A gold set can fail to exercise the very failure you are using it to
  rule out.** DEFAULT OFF under `ODR_PARTIAL_FIT` pending the corpus A/B.
- **A dead metric reads as a verdict.** This bit **four** times: the kraken probe (0.000 both arms → "tie"), the
  R3 crops (0.000 on six good re-reads), the matrix's wrong metric arm (~0.05/cell), and `evaluate_locus` on a
  leaf-vs-chapter comparison. **`evaluate_locus` compares a verse to ITS OWN reference and nothing else. Check
  the metric MOVES before believing a null.**
- **One threshold cannot serve a ragged edge.** Four incarnations of geometric apparatus separation are dead:
  word-x threshold (42–46% recall for 17–19% scripture lost), intra-line gap ratios, widest-gap right edge
  (36.5% of S6 psalms lines), and the per-leaf median left edge (odr_com 0.928→0.907). **Per-source x-BANDS
  work; single thresholds never will.**
- **Do NOT lower `verse_seg.apparatus_min` against janvier** — it is modern-spelling, so archaic readings look
  like apparatus. `ODR_STRIP_SUFFIX` stays 0. Do NOT raise `ARCHAIC_VALID_FLOOR`.
- **Never delete a span to raise a rate.** An un-localized verse leaves the denominator and inflates the score.
- **Never fix a kraken model via `TorchVGSLModel.save_model`** — it writes `model_type: 'r'` and `load_any` then
  refuses the file. Patch `description.metadata.userDefined['kraken_meta']`.
- **Measure corpus-wide before adopting anything into the live pipeline.** Book-level results disguise
  layout-specific heuristics every time.

## Open work items

**RESOLVED since the first draft:**
- ✅ *Straddling verses.* A verse spanning two leaves is now cropped from EACH contributing leaf and the
  transcripts joined in leaf order. Candidate leaves come from `.corpus-localize-*.json` bounded to leaves the
  localizer credits to this chapter — **never searched for by fit**, which had chosen a Genesis 15 leaf.
  Genesis 16:9 on S1 went 0.874 → 1.000. A leaf junction also drags the next leaf's running head into the
  prose, so `clean_tokens` now drops capitalised heading words.
- ✅ *Surface-gated adoption.* See Phase 6. Cost Genesis 16 three points of headline score, correctly.
- ✅ *Reference shifts.* `ref_renumber` now supports **merge**, **split** and **shift**. `odr_com` genesis 39
  (v6 empty, v7+ one too high) and `s_dismas` genesis 26 (two merges, at v4 and v21) are both encoded and now
  show ZERO residual drift at matching verse counts. `ref_alignment_audit` marks each finding
  `[encoded]` / `[UNENCODED — WORK]` so Phase 1 distinguishes known from new.

**THE TWO FINDINGS FROM THE S6 p76 INVESTIGATION** — worth reading before diagnosing any chapter:

- **THE CROP WAS GUILLOTINING WORD BEGINNINGS, and this was systemic.** `verse_geom.verse_crops` unions the
  verse's own line boxes and pads 2%. On a leaf whose body left edge varies down the page (`jp2-S06` p76 is
  indented beside its argument) that is not enough, and the vision model faithfully transcribes the fragment it
  is shown: `ed in the land` for `dwelled in the land`, `ke parts` for `backe parts`, `I hold` for `Behold`.
  Proven on one crop at three x0 values (0.2186 → `ed`, −3% → `velled`, −8% → `dwelled`). `widen_to_measure`
  now keeps the crop tight in **y** (which selects the verse) and full-width in **x** (which keeps words
  whole), margin 0.06. Worth **0.09–0.16 per verse** — far more than the token merge.
- **MOST OF WHAT LOOKED LIKE OCR FAILURE ON S6 IS EDITION DIVERGENCE.** S6 is the 1635 second edition; the
  archaic references are 1609. S6 genuinely prints `ſeen` where they print `ſene`, `parts` for `partes`,
  `betweene` for `betwen`, `Egyptian`/`Ægyptian`, `anſwer` for `anſwere`, `one wel` for `that wel, the wel`.
  Confirmed by eye. No recognizer work can close that gap, and it should be flagged as collation, not chased.

**THE TOKEN MERGE (`merge_arms`) — a last-mile lever, deliberately bounded.** R3 out-reads R2 on nearly every
verse and the union beats the better arm by only one or two tokens on about half the open verses. It uses only
what the recognizers establish between themselves: agreement → take it; one arm has tokens where the other has
**none** → take them (a dropout is not a reading); genuine disagreement → keep R3 but RECORD the conflict. On a
conflict where the pair differs only by the ſ-fold it keeps R2's, the ſ-faithful arm. It may never choose by
which token matches the scoring reference — that would manufacture a transcript neither recognizer produced.
It closed both `v16` cells (each arm held a word the other dropped) and its own limit showed immediately: on
`archive-ot1-1609` 16:14 the conflict `berwen Cadeſſe, | betwen Cadelle,` has R3 right on one token and R2 on
the other, the arbiter returned ALERT, and the leaf had to be read.

**THE SPAN-EDGE INVESTIGATION — five defects, and the first one invalidated a production selector.**

1. **`verse_locate.janvier_fit` RETURNS 0.000 FOR ANY PARTIAL SPAN.** It delegates to `evaluate_locus`, which
   compares a WHOLE verse to its reference. Measured on genesis 16:9:

       identical 1.000 · whole verse in archaic spelling 0.959 · tail-only 0.000 · head-only 0.000

   Spelling is not the problem; partialness is. A verse straddling two leaves appears on each leaf ONLY as a
   partial — exactly the case leaf selection exists for — so every candidate scored 0, `max()` chose
   arbitrarily, and the crop came back reading **Genesis 15**. Adding a floor did nothing because nothing ever
   cleared it. This is the FIFTH instance of the dead-metric pattern in this project and the first inside a
   production selector; `best_spans`'s own hybrid selection uses the same function, so it is blind at exactly
   the boundary verses that were historically the all-fail class. `gen1_r3.span_fit` is the partial-tolerant
   replacement: the fraction of the SPAN's tokens occurring in order in the janvier verse — precision-like, so
   a partial is not penalised for what it lacks. It separates the cases cleanly (Genesis 15 leaves 0.25 vs
   correct leaves 0.85–0.92) and fixed all three witnesses' leaf choice at once.
2. **The corpus localizer's leaf attribution is unreliable at chapter boundaries.** For genesis 16:9 it names
   `pdf-S03a` p84 (whose span reads `And the foules lighted vpon the carcaſſes` — Genesis 15:11) and
   `archive-holiebible-ot1` p90 (`a shee goat of three yeares` — Genesis 15:9), and is right only on
   `archive-ot1-1609`. So the anchor is a HYPOTHESIS, tested against `LEAF_FIT_FLOOR`; a neighbour leaf is added
   only on TRUNCATION EVIDENCE (the span touches the leaf's first or last body row), never by fit.
3. **A multi-leaf join duplicates the overlap.** `...Returne to thy TO THY mistresse...`. `_stitch` collapses the
   longest suffix-of-accepted that is a prefix-of-incoming. A duplicated phrase costs a verse as surely as a
   missing one.
4. **`trim_span_edges` needed the archaic/modern fold.** `Eightie` stayed attached to 16:15 because janvier
   spells verse 16's opening `Eighty` — the token WAS in the next verse and an unfolded test could not see it.
   Same fold, same reason, as `ref_alignment_audit`.
5. **`s_arbiter` treats `ſhe` -> `She` as CONTENT, not surface** — its fold is ſ-only and case-sensitive, so the
   two are not fold-equal and no ſ decision is ever opened. Such readings belong in `VISUAL_CONTENT`, not
   `VISUAL_READINGS`. (It was silently dropping an observed ſ and tripping its own ALERT, correctly.)

**RESOLVED 2026-07-29 — the last Genesis 16 verse, and it was TWO bugs at ONE junction (§13 Q34).** `S3 16:9`
was diagnosed as a page-model duplication, correctly. But removing the duplicate made the cell WORSE
(0.933 → 0.769) because a second, opposite defect sat at the same leaf junction:

- **The binder's SIGNATURE shares the foot row with the catchword and is set to its LEFT**, which defeats both
  halves of `_is_foot_line` at once — `H3 to thy` is three tokens AND its `row[0]` is the signature near the
  middle of the page, not the catchword out at 0.75 of the measure. Strip a leading run of signature-shaped
  tokens (`H2`, `H`, `2`, `Aa3`) before either test, and test the position of the first REMAINING token.
- **`head_frac` was deleting a BODY ROW.** `pdf-S03a` p86's head sits at y=30, its first body line — the
  continuation of 16:9 — at y=97, and the cut fell at 167. `head_frac` now only BOUNDS where a head may be
  looked for; the SHAPE test removes it. This is this document's own rule (*no `head_frac` can work*) applied
  to the one place the module still violated it.

**The generalizable lesson: when a fix makes a cell WORSE, that is evidence of a SECOND defect at the same
place — not evidence against the fix.**

**STILL OPEN:**
1. **THE ſ COST IS QUANTIFIED AND IT DOES NOT SCALE.** Across both chapters: 60 adopted cells / 1,532 tokens,
   **0 left surface-open after `s_arbiter`** — but **44 tokens needed a human eye** (2.9% of adopted tokens).
   Over 50 chapters of Genesis that is on the order of a thousand hand-reads. A ſ-faithful R3 would remove
   most of it; see "The R3 model question" below.
4. **The `--improve-below` sweep surfaces cells whose R3 read is WORSE** (S6 gen 1 v13 0.930 → 0.828). They are
   correctly rejected, but a rejected re-read still costs a crop; worth a cheap pre-filter.
5. **§13 Q21's reference-outlier detector** is still unbuilt (gen 1:25 archetype).
6. A **third** class of reference defect may exist: `trim_apparatus` reports 16 uncorroborated length outliers
   across the corpus that no single witness confirms.


---

## The R3 model question — would a ſ-faithful vision model remove this work?

**Mostly yes, and the cost above says it is worth doing.** olmOCR-2 modernizes ſ→s because its OCR fine-tuning
targets normalized modern text; the project already established that no prompt overrides this, and the same
fine-tuning also modernizes SPELLING (`therefore` for `therfore`, `afflicte` for `afflict`, `selfe` for `ſelf`),
which is a second, separate correction burden the ſ-arbiter does not even cover.

Options, in the order their evidence supports:

1. **Improve R2 instead of replacing R3.** R2 (`reichenau_dr`, kraken) is ALREADY ſ-faithful — its weaknesses
   were dropouts and n/u, g/s confusions, and a large share of what looked like R2 failure turned out to be the
   crop bug and span boundaries. It also has the cheaper training loop (`ketos`, line images, no VLM). Every
   token R2 gets right is a token `s_arbiter` can transfer without an eye. **Best return per unit effort.**
2. **LoRA fine-tune an open VLM on ſ-faithful crops.** Training data already exists and is free: the
   `R2-observed` tokens `s_arbiter` provenance-tags, plus the archaic references as weak supervision. This is
   the direct answer to "retrain an open model" and it is feasible locally (the olmOCR-2-7B weights are already
   cached; MLX-LoRA on a 7B VLM fits a Mac Studio).
3. **Try other open VLMs before training anything.** Cheap to test with the existing harness — `r3_transcribe`
   is backend-pluggable and `gen1_r3.py` measures per cell. Note `qwen3-vl:8b` is already RETIRED (thinking-lock,
   returns empty). Candidates worth one measured pass each: Qwen2.5-VL, InternVL, GOT-OCR2, dots.ocr.

**What a better R3 would NOT fix**, and this matters for expectations: the edition divergence (S6 is 1635
against 1609 references), the span-boundary faults that are the entire Genesis 16 residual, and the reference
defects Phase 1 exists for. Those are the three largest remaining categories. A ſ-faithful R3 removes a
recurring 3%-of-tokens tax on human attention; it does not move the current blockers.

**Do not** replace observation with `long_s_rule.restore_long_s` in the meantime (~90.4% = about one invented
glyph in ten presented as the printed surface).
