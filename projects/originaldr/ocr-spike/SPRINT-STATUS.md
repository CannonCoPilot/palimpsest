# OriginalDR reOCR — Full-Completion Sprint Tracker

> **RESUME (state 2026-07-31, after the reference-gap session).**
>
> ## ⚠ READ `CAMPAIGN-STATUS.md` FIRST — it is the operational resume plan
> State table, next steps in order, tools, and the nine pinned negatives. Then `CHAPTER-WORKFLOW.md` for the
> per-chapter process, and `REOCR-MASTER-PLAN-2026-07-22.md` §13 (Q1-Q49) for the findings.
> **Do not re-derive the approach.**
>
> **⚠ TWO INTERPRETERS.** Everything runs on `../ocr-venv/bin/python`; MLX needs
> `PYTORCH_ENABLE_MPS_FALLBACK=1`. Tests: `pytest tests/` -> **188 passed**.
>
> ### THE GOVERNING LESSON OF THIS CAMPAIGN (§13 Q47)
> **A rule is measured by the TEXT IT CHANGES, not by the verdicts it flips.** `split_glued` scored +8 cells
> across 50 chapters and alters **1,356 tokens**, tearing real words apart (`lawful` -> `law ful` 28x). Run
> `faithfulness_audit.py` before adopting anything that edits text — **including your own fixes**: the audit
> caught a note-anchor pattern of mine matching `a ſonne` and deleting a page of scripture, in a commit whose
> scoreboard showed a gain.
>
> ### AND THE ONE FROM THIS SESSION (§13 Q48/Q49)
> **Before blaming the recognizer, interrogate the reference.** Four of five wins here were reference repairs,
> not OCR work. `odr_com` had lost 196 verses to an optional quote in a regex; the acquisition manifest
> recorded the loss in July (`verse_count_match: 37/50`) and nothing ever read it. **A fidelity figure that no
> gate fails on is a comment.**
>
> ### STATE
> | | |
> |---|---|
> | cells >=0.90 / ACHIEVABLE | **4,853 / 6,116 = 0.7935** |
> | CHAPTERS CLOSED | **2** (1, 16) — sentinels, re-measured on every change |
> | blocked by an absent reference | **4 cells / 1 chapter** (was 704 / 16; the REF-GAP class is gone) |
> | commits | 28, **nothing pushed** |
>
> **⚠ THE RATIO IS NOT COMPARABLE ACROSS THIS SESSION.** It fell 0.7916 -> 0.7884 at the moment 596 blocked
> cells were recovered, because they entered the denominator. Quote the ACHIEVABLE COUNT beside the rate.
>
> ### NEXT, IN ORDER (Sir's stance: DEPTH-FIRST, re-measuring all 50 after each chapter closes)
> 1. Size the three S6 causes separately — annotation-on-mixed-leaf / missing leaves / edition divergence.
>    S6 is now plainly dominant: 0.15 (ch44), 0.23 (ch47), 0.25 (ch23) against S9 at 0.7-1.0 in the same chapters.
> 2. Depth-first chapter closure: ch8 (7 short), ch12 (10), ch20 (11), ch22, ch33 (12), ch18, ch48 (13).
> 3. The s_dismas re-parser still fails 8 chapters it should reproduce (2, 16, 19, 26, 31, 35, 36, 44) — each
>    failure is a parse defect the SHIPPED reads may also carry, and chapter 30 proved those are invisible to a
>    count test.
> 4. odr_com genesis 23:20 — an ACQUISITION task. The site prints 19 verses where the DR has 20. Report, do not
>    patch: the 4 cells stay open and block chapter 23.

## ⏳ M39 ITEM 2 (IMPROVE R2) — the chapter-harvest premise is DEAD; the real lever is 88% of unused GT (2026-07-29)

**Item 2's stated premise was wrong, and finding that out cost less than acting on it would have.** The plan was
to harvest the two fully-worked chapters into R2 training pairs — they are validated at 100% of cells >=0.90
against four references with the ſ-surface closed, so they looked like free in-domain data.
`rung2_chapter_pairs.py` builds exactly that (align each leaf's rows to the witness's validated token stream,
crop the row, emit image/target pairs) and yields 218 pairs after safety filters. **They are useless, and partly
harmful:**

* **6.4% signal.** 204 of 218 targets are content-identical to what R2 already reads. A target that agrees with
  the model teaches nothing. It also made the val set near-circular — `reichenau_dr` scores 99.64% on it against
  93.96% on the real val split, because 93.6% of the targets are its own output.
* **Some of the 14 informative targets are WRONG.** `archive-ot1-1609` p22 and `jp2-S09ot2` p32 both print
  `and to gouerne the day & the night` — **verified by rendering the crop and reading it** — while the validated
  target says `gouverne`. That pair would teach the recognizer to insert a letter that is not in the ink.
  Another gives `:: Heauen:and` for the printed `Heauen: and`.
* **Root cause, and it generalizes: a GRAIN MISMATCH.** Verse-grain validation at >=0.90 against references is
  the right standard for the deliverable and far too coarse to be character-grain supervision. A verse can sit at
  0.97 while carrying precisely the one-letter deviation a recognizer would learn as truth. **Verse-grain
  validation cannot be re-purposed as line-level ground truth**, and reference-derived readings inside a
  validated verse are the specific hazard — correct as collation, wrong as ink.

**WHERE ITEM 2 ACTUALLY IS (§13 Q38): R2 was trained on 12% of the line-level GT this project already owns.**

| | files | GT body lines | in multi-page files | harvested |
|---|---|---|---|---|
| `scripture-*` | 16 | 423 | 0 | **311 = 74%** |
| `matter-*` | 34 | **2,188** | 1,576 | **0** |

Two mechanical causes, both now fixed in `rung2_prepare.py`:
1. `main` globbed **`scripture-*.json` only** — all 34 matter files were never considered.
2. `page_lines` returned `[]` when `page_index` is a LIST. 11 files are multi-page (up to 24 pages). Measured on
   the first 10 gold pages by the new `rung2_harvest_audit.py`: **584 of 617 lost lines = 95% were this one
   line of code.** Remaining losses are ordinary — 17 seg-shortfall, 14 greedy 1:1, 2 under min-sim.

Verified after the fix: `matter-nt-table-of-epistles` **0 -> 162 pairs**, `matter-ot1-argument-of-genesis`
**0 -> 59**, most at sim 1.0. Full harvest running into `.rung2-data-v2` (the existing `.rung2-data` is left
untouched so the 264/47 split `reichenau_dr` was measured on cannot shift).

**THE CAVEAT THAT DECIDES ADOPTION, stated before the numbers arrive.** Matter is the same press, the same founts,
the same ſ usage and the right grain — but tables of proper names and title pages in display capitals are not
scripture's content distribution. With no dictionary and no LM in the recognizer (both banned for surface
safety), typeface match should matter more than n-gram match — *should*, not *does*. The experiment: fine-tune
with and without matter, score BOTH on the **unchanged 47-line scripture val split** that neither model trained
on, and adopt only on a scripture-val gain with no fall in ſ recall. Provenance is tagged per line (`kind`) so
matter can be ablated on its own.

**Also built:** `rung2_eval_lines.py` — line-level CER + ſ-recall through kraken's Python API, because
`ketos test` fails on this project's arrows with `No test data in dataset`, the same raw-bbox defect that makes
`ketos train` report "No training data". Its first run scored every line 0.000 from a 1-pixel-out-of-bounds line
polygon: the sixth dead metric of this sprint, caught immediately because the pattern is now familiar.

## ✅ M38 GENESIS 16 CLOSED AT 256/256, AND Q30's HYPOTHESIS MEASURED CORPUS-WIDE (2026-07-29)

**Two results, and the smaller-looking one is the larger.**

### (1) Genesis 16 is 256/256 = 100% — closed with NO model call

The last open verse (`S3 16:9`) was diagnosed at handoff as a page-model duplication, and that was right. What
the diagnosis missed is that **ONE leaf junction was failing in TWO independent ways**, which is why removing
the duplicate first made the cell WORSE (0.933 -> 0.769, `missing returne to thy mistresse and`):

* **(a) the binder's SIGNATURE shields the catchword.** `pdf-S03a` p85's foot row is `H3 to thy` — three tokens
  against `FOOT_MAX_TOKENS` 2, and `row[0]` is the signature near the middle of the page rather than the
  catchword out at 0.75 of the measure, so BOTH halves of `_is_foot_line` failed. Also `H2 † Abram` (p83),
  `H to thy` and `H 2 † Abram` (`archive-holiebible-ot1` p91/p89, the letter and its number as separate tokens).
  Fixed by stripping a leading run of signature-shaped tokens before either test. Converts exactly those four
  rows across the Genesis 16 leaves; `archive-ot1-1609`'s short foot rows `com` / `m` / `amomn com` stay body,
  correctly — they sit at 0.17-0.28 of the measure and are garbled text, not catchwords.
* **(b) `head_frac` was deleting a BODY ROW at the same junction.** On `pdf-S03a` p86 the head `62 GENESIS.` is
  at y=30 and the first body line — `to thy miſtreſſe, and humble thy ſelfe vnder her hand.`, the continuation
  of 16:9 — is at y=97, under a cut at 0.055·H = 167. **This is the module's own documented lesson applied to
  itself:** the running head cannot be cut by `head_frac` at any value. `head_frac` now only bounds where a head
  is looked for; `_is_running_head`'s SHAPE test removes it, plus one explicit clause for a bare folio number
  (too few letters for the shape test to judge).

Genesis 16 means 0.986/0.986/0.980/0.980 -> **0.990/0.990/0.984/0.984**; Genesis 1 holds at 496/496 with means
unchanged, so the two fixes are additive rather than a trade. **The final residual of two fully-worked chapters
turned out to be two geometry bugs, not the recognizer** — worth remembering before spending a training run.

### (2) §13 Q30's open hypothesis: CONFIRMED, and it is not a boundary effect but a third of the corpus

`selector_corpus_probe.py` replays the live localize loop over **11 witnesses / 2,767 pages / 36,833
verse-spans**, writing nothing:

| | |
|---|---|
| arms DIFFER — the selector has a real decision | **82.8%** |
| selector DEAD (both arms `janvier_fit` 0.000) | **34.7%** |
| DEAD and the arms differ — a **silent coin flip** | **33.7%** (40.7% of real decisions) |
| `partial_fit` F1 separates those arms | **84.7%**, and would move ~4,470 to the walk arm |
| cross-page contests decided by the LENGTH tiebreak, not the selector | **716/9,129 = 7.8%** |

The documented hybrid (0.9488 vs the incumbent's 0.9215 on gold) **was not operating on ~37% of the spans where
a choice existed** — the incumbent aligner won them by default. `genesis/16/9` on `archive-holiebible-ot1`
appears in the cross-page list with length keeping F1 0.13 over a candidate at 0.50: **the same wrong leaf Q31
found by hand, so Q31 and this are one mechanism.**

`verse_locate.partial_fit` (precision, recall, F1 over ordered token matches) is the replacement. **Not
`span_fit` alone** — precision-only scores a ONE-TOKEN span 1.000 and that pathology chose spans for real
(`genesis/3/13`, `john/10/3`, `apocalypse/5/9`). **Rescue only, never replace:** on gold, replacing the selector
loses 18/18 changed verses; rescuing only the dead rows changes 0. And the gold set cannot validate the gain —
1/165 dead rows there against 34.7% corpus-wide, because gold pages are whole-verse pages by construction.
**The gold set does not exercise the failure it was being used to rule out**, and its judge shared the defect
(`evaluate_locus` against a per-page gold is also partial-blind), which is why the one dead gold row reads
0.000/0.000 and looked like "no gain available".

### (3) THE CORPUS A/B IS RUN — the defect is PREVALENT but LOW-YIELD, and my own earlier framing was wrong

Three arms, each a full `corpus_localize` + `book_audit genesis` + `qc_audit` over the 5 pilot books (25,472
localized cells). **Baseline re-derived all-pass 799 / all-fail 104 exactly.** Both-sites challenger:

| | baseline | `ODR_PARTIAL_FIT=1` |
|---|---|---|
| Genesis all-pass / all-fail | **799 / 104** | **799 / 104** unchanged |
| overall pass rate | 0.6220 | 0.6200 (-0.0020) |
| fail -> PASS / PASS -> fail | — | **3 / 0** |
| newly localized cells | — | **87** (80 at archaic_id 0.000, 1 passing) |
| no longer localized | — | **0** |
| `verse_cover_rate` | 0.9964 | 0.9964 unchanged |

**Nothing regressed** — every source's absolute pass count is equal or higher (S3 +2, S9 +1). The RATE fell only
because 87 attestations entered the denominator and 80 are worthless spans: the mirror image of the rule that an
un-localized verse inflates the score.

**And the yield is 3 cells in 25,472.** Prevalence (33.7% of decisions) and yield (0.01% of cells) are three
orders of magnitude apart, because the coin flips land on verses that fail for reasons the selector cannot touch
— edition divergence, reference defects, garbled scans. **So "this may be worth more than either model change"
was WRONG and is corrected: it is not.** Fix it because a production selector must not report 0.000 as a
decision, not because it is the lever on the all-fail class.

Also measured, and it forced the flag to become a SITE LIST (`spans` / `better`): F1 alone at the cross-page site
moved `genesis/1/1` to the volume's FRONT MATTER, because a short fragment can out-score a long garbled reading
of the real page. The length band is now the first key there and F1 decides only among plausibly-whole-verse
candidates. Pinned in `test_page_address.py`.

**169 tests** green with the flag off and on. **NOT ADOPTED**; production `.corpus-localize-*.json` restored and
byte-verified against the backups.

## ✅ M37 GENESIS 16 TO 252/256 (98.4%) — SPAN-EDGE FAULTS, AND A DEAD METRIC INSIDE A PRODUCTION SELECTOR (2026-07-29)

Genesis 16 went **244 -> 252 of 256** and S6 from 14/16 to **16/16**. Every fix was a span-edge or geometry
defect; not one was a recognizer improvement. Genesis 1 re-verified at **496/496** throughout, tests 159 green.

**The finding that matters most is §13 Q30: `verse_locate.janvier_fit` returns 0.000 for ANY PARTIAL SPAN.**

| input | fit |
|---|---|
| identical | 1.000 |
| the whole verse in archaic spelling | 0.959 |
| tail only | **0.000** |
| head only | **0.000** |

Spelling is not the problem; partialness is. A verse straddling two leaves is only ever a partial on each leaf —
exactly the case leaf selection exists for — so every candidate scored 0, `max()` chose arbitrarily, and the R3
crop transcribed **Genesis 15** twice under two different strategies. A fit floor changed nothing because
nothing cleared it. `gen1_r3.span_fit` (fraction of the SPAN's tokens occurring in order in the janvier verse,
precision-like) separates them cleanly — Genesis 15 leaves 0.25, correct leaves 0.85-0.92 — and fixed all three
witnesses at once.

**`best_spans` uses `janvier_fit` for its own hybrid selection.** So that selector may be blind at precisely the
boundary verses the M-series measured as the historic all-fail class. Uninvestigated corpus-wide, and cheap
relative to any model work.

### The other four span-edge defects

- **The corpus localizer's leaf attribution is unreliable at chapter boundaries** (§13 Q31). For 16:9 it names
  `pdf-S03a` p84 (`And the foules lighted vpon the carcaſſes` = Genesis 15:11) and `archive-holiebible-ot1` p90
  (`a shee goat of three yeares` = 15:9); right only on S1. The anchor is now a hypothesis tested against a
  floor, with a neighbour added only on TRUNCATION EVIDENCE — never by fit.
- **A multi-leaf join duplicated the overlap** — `...Returne to thy TO THY mistresse...`. `_stitch` collapses
  the longest suffix-of-accepted that is a prefix-of-incoming.
- **`trim_span_edges` needed the archaic/modern fold** — `Eightie` stayed attached to 16:15 because janvier
  spells verse 16's opening `Eighty`.
- **`s_arbiter` treats `ſhe` -> `She` as CONTENT, not surface** (its fold is ſ-only and case-sensitive), so such
  readings belong in `VISUAL_CONTENT`. It was silently dropping an observed ſ and tripping its own ALERT —
  correctly.

### The token merge, and why it was the small lever (§13 Q33)

The diagnosis came first and bounded the work: **R3 out-reads R2 on nearly every verse**, and the union beats
the better arm by only one or two tokens on about half the open verses. `merge_arms` therefore uses only
recognizer-internal evidence — agreement, and DROPOUTS (a dropout is not a reading) — and records genuine
disagreements rather than resolving them by reference. It closed both `v16` cells, where each arm held a word
the other dropped, and its limit showed immediately on 16:14 (`berwen Cadeſſe, | betwen Cadelle,`: R3 right on
one token, R2 on the other, arbiter ALERT, leaf read).

**The main event was geometry, not merging (§13 Q32):** the R3 crop was guillotining word beginnings — `ed in
the land` for `dwelled`, `ke parts` for `backe parts`, `I hold` for `Behold` — proven on one crop at three x0
values. Worth **0.09-0.16 per verse**, ten times the merge.

### What is NOT done

The user's plan was four items. **Item 1 (span-edge) is done. Items 2-4 — improve R2, survey open VLMs, LoRA
olmOCR-2-7B — are NOT STARTED**, deliberately: each is a substantial training/evaluation job and starting all
three would have produced four half-finished threads and no measured result. §13 Q35 records the quantified
case for them (**44 hand-read tokens / 1,532 adopted = 2.9%**, ~1,000 hand-reads over 50 chapters) and the order
the evidence supports.

## ✅ M36 GENESIS 1 COMPLETE — 496/496 CELLS, RUNG 3 CLOSED THE RESIDUAL (2026-07-29)

**Every verse of every source now matches every one of the four reference witnesses at >=0.90.** 496 of 496
cells, lowest cell 0.902, means 0.974 / 0.973 / 0.961 / 0.961. The page model reached 485 (97.8%) and the
ladder's third rung closed the last 11 — which is exactly the division of labour the ladder was designed for.

| cell | incumbent | after R3 | what R3 fixed |
|---|---|---|---|
| S1 v13 | 0.924 | **1.000** | recovered the dropped `was` |
| S3 v13 | 0.924 | **1.000** | recovered the dropped `was` |
| S9 v15 | 0.933 | **1.000** | dropped the margin word `firſt` |
| S9 v18 | 0.943 | **1.000** | dropped the margin words `of` and `Di` |
| S9 v21 | 0.934 | **0.989** | un-scrambled the word order, dropped `for` |
| S6 v8  | 0.895 | **0.926** | `euenins`->`euening`, `mornins`->`morning`, `firmameut`->`firmament` |

Backend: **olmOCR-2 via MLX, entirely local — no paid API.** Module `gen1_r3.py`; the adopted re-reads live in
`.gen1-r3-adopted.json` and are overlaid on the matrix and LABELLED `r3`, never blended in as though the page
model had read them. `gen1_matrix.py --no-r3` ablates the overlay and returns the pure 485.

### Three localization traps, and the first nearly hid the whole result

**A verse crop is not a verse.** `verse_geom.verse_crops` returns the band of LINES a verse occupies, so the
crop carries its neighbours. Scored whole against a single-verse reference, all six re-reads came back
**0.000** — and every one of them was good; S1 v13's transcript contained `And there was euening & morning that
made the third day` in plain sight. **That is the third time this sprint a dead metric produced a confident
wrong verdict** (cf. the kraken probe, M34). The lesson is now recorded twice over: check that the metric MOVES
before believing a null.

**The janvier grid must be restricted to the verses the crop contains.** Segmenting a 2-3 verse crop against
the whole 31-verse chapter is under-constrained — asked for gen 1:15, it returned 1:14's text. The neighbour set
is derived from the page's own geometry (which verses' lines overlap the cropped band), so it is a fact about
which pixels were sent, not a hint about the answer.

**But the restricted grid alone loses gen 1:13.** That crop ends just after v14's first word — too little for
the segmenter to claim it — so `Againe` stays attached and the score falls 1.000 -> 0.883. So three candidates
are segmented (full grid, restricted grid, and the hybrid `best_spans`, whose anchor-walk arm is the only one
that trims `Againe`) and the best JANVIER fit is kept. Localization on janvier, scoring on the archaic
references: the same separation the live pipeline relies on, and not circular.

### The ſ surface was restored by observation, not by rule

olmOCR modernizes ſ->s. Adopting its text raw would have traded the diplomatic surface — the point of the whole
project — for a content score that cannot see the difference, since `fold_archaic` folds ſ/s. **Measured cost of
the raw adoption: 7 long-s characters.** `s_arbiter.transfer` takes R3's CONTENT with R2's OBSERVED spelling
wherever the two agree modulo the ſ-fold; R2 (kraken + reichenau_lat) is itself a ſ-faithful visual recognizer,
so those glyphs are attested rather than invented. That restored `ſhine`, `ſo`, `ſawe`, `ſorte`, `ſecond`.
`long_s_rule.restore_long_s` was NOT used and must not be — at ~90.4% on this project's own gold it would
present about one invented glyph in ten as the printed surface.

### One token needed an eye — and the arbiter caught me misusing it

S6 v8 token 4: R2 read `firmameut`, R3 read `firmanent`, and **neither is right.** Rendering the leaf at
y 0.788-0.818 and reading it shows, plainly:

    firmament. And it was ſo done. 8. And God called the firmament,

Offered to `s_arbiter.arbitrate`, that reading **RAISED** — `sirmanent, -> sirmament,` — because arbitration is
a SURFACE path and its guard refuses content changes through it. The guard was right and I was wrong: an n->m
correction is a content change and must be visible and re-scored, not slipped in as a surface adoption. The fix
is now two separate, separately-visible things — `VISUAL_CONTENT` carries the observed correction and is
re-scored; `VISUAL_READINGS` answers only the question the arbiter exists for (is that `f` a ſ? no —
`firmament` contains no s at all). Pinned by `test_visual_content_and_surface_are_separate_paths`.

**All six ſ-surfaces are CLOSED with zero unresolved tokens.**

### Adoption is gated mechanically

A re-read is adopted only if it beats the incumbent on the governing archaic arm AND clears the bar.
Better-but-short is recorded as a partial and the cell **stays OPEN** — the module has no path to closing a
cell other than actually clearing it. Pinned by `test_r3_adoption_requires_clearing_the_bar`.

Tests **159 passed** (140 pre-existing untouched + 19 page-model / R3 specs).

**Before applying forward to Genesis 2-50 (Sir's instruction): analyse the approach.** Which rules generalize
(`_is_running_head`, `_is_foot_line`, the sloping-row reference, the band-edge asymmetry, the chapter stream,
the reference audit) versus which are leaf-specific (`PAGE_OVERRIDE`, `DROP_CAP`, `open_page`); and what the R3
call budget per chapter looks like — Genesis 1 needed 6 crops for 124 verse-instances, about 5%.

## ✅ M35 GENESIS 1 — 485/496 CELLS (97.8%); THE s_dismas GAP WAS THE REFERENCE (2026-07-29)

Sir asked why `s_dismas` scored so much worse than the others — parse error, or genuinely bad content? **It was
a parse error, and it was ours.** That question turned out to be the most valuable one asked this sprint: it
opened four distinct defects, three of which had nothing to do with recognition.

| step | cells >=0.90 | s_dismas | odr_com | sabates_a | madueke_b |
|---|---|---|---|---|---|
| M34 close | 402/496 (81.0%) | 0.756 | 0.946 | 0.923 | 0.923 |
| + `s_dismas` renumbering corrected (§13 Q24) | 431* | **0.947** | 0.946 | 0.923 | 0.923 |
| + S6 opening leaf configured (§13 Q27) | 431/496 | 0.957 | 0.956 | 0.934 | 0.934 |
| + sloping-line row reference (§13 Q26) | 455/496 | 0.969 | 0.968 | 0.944 | 0.944 |
| + each reference on its own arm (§13 Q25) | 477/496 | 0.969 | 0.968 | 0.956 | 0.956 |
| + catchwords & two-part head (§13 Q28) | **485/496 (97.8%)** | **0.971** | **0.970** | **0.958** | **0.958** |

\* the renumbering and the S6 leaf were measured in sequence; 431 is the figure after both.

**1. `s_dismas` is mis-numbered in Genesis 1 (§13 Q24).** It splits the printed verse 25 in two — `25` keeps
`And God made the beaſtes ... in his kind.` and a 7-token `26` takes the tail `And God ſaw that it was good,` —
so it runs the chapter to **32 verses** where the other three run it to 31, with everything from 26 shifted by
one. `s_dismas` 1:27 matches `odr_com` 1:26 at ratio **1.000**. Verses 26-31 were being compared against the
wrong text and **could not have passed by any amount of OCR work.** Corrected at load time in
`ref_renumber.py` — the source file is never touched and removing the entry restores the old behaviour
exactly. `s_dismas`: 0.756 -> 0.947, 86/124 -> 109/124.

To answer the question as asked: **not bad content, and not a bad loader.** `qc_audit.load_reads_verse` is
correct; the ingested `reads/s_dismas.json` carries an extra verse boundary. The reference's WORDS are right
everywhere — every one of its 31 corrected verses matches `odr_com` at >=0.90 — only its numbering was wrong.

**2. The detector had to be fixed before it could see its own headline case.** `ref_alignment_audit.py` scores
each verse against every other reference at offsets -3..+3 and calls a persistent nonzero offset a shift. On a
raw token ratio it found the Genesis 1 shift only against `odr_com`: `sabates_a`/`madueke_b` are
modern-spelling, `heauen`/`heaven` and `likenes`/`likeness` score as different words, so a **3-witness
unanimous agreement was dismissed as a 1-witness disagreement.** Folding the archaic/modern difference is what
lets a shift be corroborated across that boundary. Two further corroborated shifts are now visible and are
deliberately NOT corrected (`odr_com` genesis 39 from v7, `s_dismas` genesis 26 from v5) — Genesis 2-50 work
must re-run the audit and read the evidence one chapter at a time.

**3. Each reference must be scored with its own arm (§13 Q25).** The matrix was reading `archaic_id` for all
four references. `sabates_a`/`madueke_b` are modern-spelling, and `archaic_id` uses `fold_archaic`, which
PRESERVES archaic orthography — so a faithful transcription was being charged ~0.05 per cell for every
`heauen`/`heaven` and `kinde`/`kind`, differences of edition rather than of recognition. `evaluate_locus`
already computes `modern_id` for exactly this. 455 -> 477/496, no transcript changed. This is also the
project's own documented policy, which the matrix had drifted from (QC §1.4, revised by Sir 2026-07-10): the
archaic gate is the quality bar and `modern_id` does not gate.

**4. THE ROW REFERENCE MUST FOLLOW THE LINE'S SLOPE — the largest OCR-side lever in the sprint (§13 Q26).**
S9 was the worst source at 19/31 and the reason was mechanical. These leaves are photographed off bound
volumes and the lines are not level: on p32 one printed line runs from y=1157 at x=336 to y=1122 at x=999, a
**35px rise against a ~30px tolerance.** Comparing every word to the row's FIRST word, the far end of each
line fell out of tolerance, started a spurious row, collected the neighbouring line's words, and sorting by x
interleaved the two — which is why S9 gen 1:21-29 read as word salad (0.646-0.826) while S1 and S3, flatter
scans of the SAME 1609 edition, read those verses at 0.92-0.98. Comparing instead to the word LAST added
tracks the slope, because the step between adjacent words stays small however far the line rises.
**S9: 24/62 -> 62/62 on the archaic references.** The drift bound that stops the reference chaining across
lines is the dominant term and must be tight — the sweep is in `gen1_pagemodel.py`, and at the loose end the
result collapses to 0/248.

**5. The unit that owns a layout is the LEAF, not the witness (§13 Q27).** S6's chapter-opening leaf p18 was
never configured (`open_page: None`) and is a three-column page — left cross-refs at x 229-320, body, and a
CONTINUOUS PROSE annotation down the right margin from x 1692. Its scripture runs to x 1670; its ordinary
leaves run to x 1789. One right bound cannot serve both, and 0.825 admitted the entire annotation column into
verses 2-11. A per-leaf `PAGE_OVERRIDE` of (0.165, 0.765) took **S6 from 22/31 to 29/31.** The right bound
carried nearly all of it (0.825 -> 44/62, 0.765 -> 59/62); the left bound was nearly inert and `chapter_open_y`
measured as an outright NO-OP on this leaf, recorded as such rather than left in looking useful.

**6. Catchwords, and a head the shape test missed (§13 Q28).** Early-modern leaves print the first word of the
NEXT leaf at the foot. Leaf by leaf that is one stray token — but through the chapter stream it lands directly
before the word it duplicates, so gen 1:12 arrived as `grene grene herbe` in all three 1609 witnesses. Cut by
position: last row, one or two tokens, beginning past the middle of the measure. And the second edition's
two-part head `GENESIS. Creation.` is only 53% capitals, so it slipped the ratio test and put `genesis` and
`creation` into gen 1:11. That extra test had to be narrow — keyed on initial-capital alone it deleted body
rows opening `And God` — so it requires every token capitalised AND full-stopped, punctuated as a label.
477 -> 485/496.

**7. The kraken `seg_type` label is now corrected**, with a trap recorded. `fix_model_segtype.py` patches the
one JSON key; warning gone, transcript byte-identical. The obvious route —
`TorchVGSLModel.load_model` -> `save_model` — **corrupts the model**: it writes `model_type: 'r'` for
`'recognition'` and `load_any` then refuses the file. That was tried, it broke the R2 recognizer, and it was
restored from backup.

### The 11 open cells, with their causes

| cells | cause | class |
|---|---|---|
| S1 v13, S3 v13 (modern arm, 0.852) | both witnesses genuinely drop `was` from `And there was euening` | RECOGNITION |
| S9 v15, v18, v21 (modern arm, 0.881-0.896) | margin words `first`, `of`, `di`, `for` interleaved into body rows | SEGMENTATION (§13 Q23) |
| S6 v8 (odr_com only, 0.895) | `firmameut`, `euenins`, `mornins` (n/u, g/s) + the `(b)` annotation marker | RECOGNITION |

None is a layout defect any more, and none is a reference defect. **The remaining work is recognizer-side** —
which is the honest boundary of what the page model can do, and the point at which the R3 vision-LLM rung
becomes the lever rather than more geometry. Per No-Silent-Degradation these 11 stay OPEN and block; they are
not reclassified as acceptable.

Tests **155 passed** (140 pre-existing untouched + 15 page-model specs, including the pinned negative result
and the new sloping-line, catchword and label-punctuation rules).

## ✅ M34 GENESIS 1 AT 31/31, AND THE KRAKEN WARNING CLOSED (2026-07-29)

Sir's Genesis 1 target is met: **every verse of Genesis 1 now has at least 3 of 4 witnesses at >=0.90 archaic
identity**, 16 of 31 at 4/4. The gains came in four measured steps, none of them recognizer changes.

| step | >=3/4 | 4/4 | s_dismas | odr_com |
|---|---|---|---|---|
| M33 page model, as handed over | 25 | 8 | — | — |
| + re-runnable harness (`gen1_pagemodel_eval.py`), shared assembly path | 28 | 13 | 0.735 | 0.916 |
| + drop-cap orphan removal, opening display line | 29 | 14 | 0.737 | 0.918 |
| + asymmetric band edges, shape-based running head | 29 | 15 | 0.747 | 0.928 |
| **+ chapter-stream localization** | **31** | **16** | **0.756** | **0.946** |

**The harness came first and it changed the number by itself.** M33's 25/31 had been measured by hand and
lived only in a status document; building the re-runnable scorer put `body_text` and the scoring path through
ONE assembly function, and the row-boundary hyphen rejoin that only the scorer had was enough to carry three
verses (13, 21, 31) on its own. A result that cannot be re-measured is not a result — and in this case it was
also not the right number.

**What the individual fixes actually were.** Each came from rendering the leaf and looking at it:

* **The engraved initial is emitted as a stray token.** On `archive-holiebible-ot1` p31 the drop capital comes
  back as `2` at x=348 while that row's first real word begins at x=908. It is identified by WHERE it is —
  alone in the indent, separated by many times any inter-word gap — not by what it says, because it says
  something different in each witness. Left in, it also broke the rejoin: `hea-` glued to `2`, stranding `uen`.
* **The opening display line.** `NTHEbeginning` is one token because the display capitals are kerned tight and
  the initial is not type at all. Neither half is reachable by recognizer tuning, so the reading is recorded as
  the page datum it is, keyed by the glued token so it cannot fire elsewhere. gen 1:1 went 2/4 -> 4/4.
* **The two band edges are different kinds of edge.** The left bound is a gutter that nothing in the body
  crosses; the right bound is the measure, which body words overhang routinely (`tree` at x 1752-1821 against
  a bound of 1793). Testing both by the word's centre let the margin word `birdes` (centre 310, bound 308)
  into gen 1:12 in all three 1609 witnesses. Left bound now tests the word's START, right bound its centre.
* **The running head cannot be cut by y, at any `head_frac`.** On `archive-holiebible-ot1` the running head of
  p33 ends at y=165 while the first real BODY line of p32 begins at y=118 — the head of one leaf sits lower
  than the text of the next. It is cut by SHAPE instead: topmost row, one or two tokens, set in capitals. That
  catches `GENESIs.`, the misrecognized `GEMESIs.`, and `GENESIS.` alike, and travels to other chapters.
* **A word broken at the measure whose hyphen the recognizer lost.** `pdf-S03a` prints `hea` + `uen` with no
  mark. Joining every row boundary would glue `was` to `voide`, so the join requires independent evidence:
  neither fragment is a word of the book's archaic vocabulary and their concatenation is. **Measured honestly:
  this fires exactly twice in Genesis 1, both correct, and moves no score** — `evaluate_locus` already
  tolerated the split. Kept because the transcription is more correct, recorded as score-neutral because it is.

**The largest single step was not a fix at all — it was the unit of work (§13 Q22).** A verse is bounded by a
chapter, not a leaf. gen 1:12 begins `And the earth brought forth` as the LAST line of p21 and continues on
p22, so no per-page call could ever see it whole. Offering the localizer the chapter as one concatenated
stream alongside the per-leaf calls, and keeping whichever span fits janvier better — the same gold-free
hybrid selection `best_spans` already uses between its two segmenters — carried 29 -> 31. The chapter stream
wins only **7 of 124 spans (5.6%)**, all of them boundary verses. It also reframes the earlier finding that
all-fail verses are boundary verses: real, but substantially an artifact of asking a page-shaped question
about a chapter-shaped object.

**The kraken segmentation-type warning is closed, and it was nothing (§13 Q18).** It was the largest open
unknown in the plan — *"severely degraded performance"* on every recognition call for the whole sprint. The
mismatch turned out to be ours: `reichenau_lat` (the base) declares `seg_type: baselines`; only the fine-tuned
`reichenau_dr` declares `bbox`, the fingerprint of the raw-bbox training bypass. Inspection could not settle
it — `rpred.mm_rpred` raises the warning by comparing DECLARATIONS while choosing the extraction path from
`bounds.type` — so the model was asked directly, recognizing the same `blla` lines both ways on 7 leaves:

    baselines (current)   conf 0.9735   chapter recall 0.4042
    bbox (as declared)    conf 0.9016   chapter recall 0.1898     (-0.2144)

Worse on every leaf and every axis, with token yield collapsing where the leaf is warped (p32: 601 -> 96). The
model was trained on dewarped polygons; the ladder has been running it correctly all along and **no quality
figure this project has quoted is affected.** Remedy — rewrite the one metadata field — deliberately left
undone under the commit hold. Probe: `kraken_segtype_probe.py`.

*One methodological note.* The probe's first run scored both arms with `evaluate_locus` and got **0.000 for
both**: that metric compares a verse to its own reference, not a leaf to a chapter. A dead metric reads as a
tie, and the tie would have been reported as "mislabel" — the right verdict resting on no evidence at all. The
conclusion above stands on a token-level LCS recall, which moves.

**And one rule measured and REJECTED, pinned so it is not rebuilt (§13 Q23).** Deriving a per-leaf body left
edge from the median row start removes the genuine margin intruders (`birdes`, `in`, `Eſa.`, `Aug`) — and
strips the first real word off some forty rows across the four witnesses (`And it was ſo done` -> `ſo done`).
odr_com 0.928 -> 0.907, s_dismas 0.747 -> 0.725, 4/4 support 15 -> 11. One threshold cannot serve a ragged
left edge; this is the fourth incarnation of the family Q19 retired. `_trim_left_margin` is kept unwired with
the figures in its docstring, and `test_left_margin_trim_stays_unwired` asserts it stays that way. Those
intruders are a segmentation artifact — `blla` merged the columns and kraken emitted them in body reading
order — so the lever is the segmentation, not the margin.

**Not fixed, and correctly so: gen 1:29 in s_dismas.** s_dismas prints verse 28's text (`Increaſe and
multiplie, & repleniſh the earth`) under the number 29, so all four witnesses score 0.000 against it while
reading their own pages correctly. That is a collation fact about the reference, not an OCR failure, and it is
exactly the case §13 Q21 exists for: **flag the locus, never convert it to a pass.**

Tests: **151 passed** (140 pre-existing, unchanged, plus 11 new specs in `tests/test_gen1_pagemodel.py`). The
live corpus pipeline is untouched — the page model remains standalone.

## ✅ M33 PER-SOURCE PAGE MODEL FROM THE ACTUAL IMAGES — Gen 1 support 14 -> 25 of 31 (2026-07-29)

Sir's instruction was to stop inferring layout from coordinates and go and look at the pages, decomposing each
source and OVERFITTING to it. Rendering four leaves settled in one glance what six estimators could not.

**THE FOUR WITNESSES DO NOT SHARE A LAYOUT, AND TWO OF THEM ARE MIRROR IMAGES.**

| | first edition (S1, S3, S9 — 1609) | second edition (S6 — 1635) |
|---|---|---|
| far left | cross-reference column ~.05-.12 | — |
| left | verse-number column ~.15 | **MAIN ANNOTATION COLUMN .09-.215** |
| body | **.140 - .815** | **.215 - .825** |
| right | **MAIN ANNOTATION COLUMN .81-.99** | sparse cross-refs only |
| verse numbers | own column | **inline in the body** |
| opening leaf | ornament + "THE BOOKE OF GENESIS, IN HEBREW BERESITH." + "CHAP. I." + italic argument | — |

**This is why the word-level x threshold scored only 42-46% recall for 17-19% of scripture lost** — it was
being asked to catch a LEFT column and a RIGHT column with one number. Per-source bands separate them cleanly.

**RESULT — Genesis 1, every verse, every witness, against ALL FOUR references:**

| reference | stored stream | per-source page model |
|---|---|---|
| s_dismas | 46/123 | **71/124** |
| odr_com | 64/123 | **88/124** |
| sabates_a | 54/123 | **77/124** |
| madueke_b | 54/123 | **77/124** |

**Verses reaching ≥3/4 support: 14 -> 25 of 31**, of which 8 are 4/4.

Also in the model, each read off the pages: reading order rebuilt from the word boxes (kraken interleaves the
columns — S9 p31's annotation lines at y=4713/4862 are emitted BETWEEN body lines at y=4694/4877);
soft-hyphen rejoin (`hea-` + `uen` -> `heauen`); inline verse-number strip; and restoration of the ornamental
**DROP CAPITAL**, an engraved block the recognizer never sees, which is why "IN THE beginning" arrived as
"NTHEbeginning".

**⚠ SIX VERSES STILL SHORT — 1, 12, 13, 21, 29, 31 — and each is now diagnosed rather than mysterious:**
v31 scores fit 0.0 although its TEXT IS PERFECT (the span runs on into chapter 2 — a boundary problem, not
recognition); v13 is missing "was" in S1/S3; v12 keeps the running head "GENESIs." on p22 plus a "birdes"
intrusion; v21's word order is scrambled in S9 by my row-grouping tolerance; v29 has a hyphen split across a
LINE break that the within-line rejoin does not reach.

**NOTE, UNEXAMINED AND POSSIBLY IMPORTANT:** kraken warns *"Recognizers with segmentation types {'bbox'} will
be applied to segmentation of type baselines — this will likely result in severely degraded performance"* on
every recognition call in `reocr_core`. If real it depresses every re-OCR rung.

The live corpus pipeline is UNCHANGED (Genesis all-pass 799, corpus archaic 0.6381); the page model is a
standalone Genesis-1 path, as instructed.

## ⚠ M32 KRAKEN WORD BOXES FOR GENESIS 1 — obtained; the column split is NOT a geometry problem (2026-07-29)

Scope held to Genesis 1 per Sir. New modules: `gen1_wordboxes.py` (cache `.gen1-wordboxes.json`),
`gen1_rerecog_eval.py`. The live pipeline is UNCHANGED — both are standalone measurements.

**WORD BOXES EXIST, AND CHEAPLY.** `kraken`'s `rpred` returns an `ocr_record` whose **`.cuts` is a
per-CHARACTER polygon in page coordinates**, one per predicted character. The twelve leaves that supply
Genesis 1's verses (plus neighbours, 15 pages) re-recognized with the R2 model in **151 seconds**, ~700 words
per page. `reocr_core.recognize_lines` keeps only `text` and `conf` and **discards `.cuts`** — that is the sole
reason this project believed word geometry was unavailable.

**⚠ THE DEFINITIVE NEGATIVE RESULT: apparatus and scripture are NOT separable by geometry at ANY grain.**
Every word on a page was labelled by whether it anchors to the chapter's archaic reference, and the geometry
then asked to divide them:

| test | result |
|---|---|
| word x threshold at 0.78·W | **42-46% of apparatus caught for 17-19% of scripture lost**; on `jp2-S06` worse than useless |
| intra-line gap (max/median) | ratios **1.1-1.9**, and the split lands in the wrong place |

`blla` merges the two columns into single lines, and within them the apparatus words occupy the **same x range**
as the scripture. **This retires the entire family of geometric estimators** — widest-gap right edge,
proportional character offset, word-x threshold, intra-line gap — including the three that already failed
corpus validation. They should not be rebuilt.

**RE-RECOGNITION ALONE IS NET-WORSE IN THIS CONFIGURATION.** Genesis 1, every verse, all four references:

| reference | stored mean / pass | re-recognized mean / pass |
|---|---|---|
| s_dismas | 0.691 · 46/123 | 0.596 · 36/121 |
| odr_com | 0.852 · 64/123 | 0.782 · 56/121 |
| sabates_a | 0.826 · 54/123 | 0.752 · 48/121 |
| madueke_b | 0.826 · 54/123 | 0.752 · 48/121 |

Verses at ≥3/4 support: **14 → 11**. It gains on vv 12, 23, 24, 30 and loses on 5, 9, 13, 15, 16, 18, 21.
Individual readings are visibly better — the verse marker comes back as `†` where the stored stream has `F`,
and fragmentary lines return whole — so the aggregate loss needs the confound below resolved before the
re-recognized stream is judged.

**⚠ TWO CONFOUNDS, STATED SO THE RESULT IS NOT OVER-READ.** (1) The re-recognized arm ran WITHOUT the apparatus
pipeline (side-column demotion + margin-prefix strip) that the stored arm now has. (2) kraken warns
*"Recognizers with segmentation types {'bbox'} will be applied to segmentation of type baselines — this will
likely result in severely degraded performance"* — a model/segmentation-type mismatch inside `reocr_core`
itself, which if real is depressing **every** re-OCR rung, not just this experiment.

**STATE LEFT VALIDATED AND UNCHANGED:** Genesis all-pass **799** / all-fail 104 (S1 67.5 · S3 75.5 · S9 76.1 ·
S6 77.7); corpus `pass_rate_archaic` 0.6381, `verse_cover_rate` 0.8627. **140 tests.** v045.
**⚠ TARGET NOT MET:** 14 of 31 Genesis 1 verses reach ≥3/4 support.

**NEXT, and the evidence has narrowed it to three things:** (1) fix the bbox-vs-baseline segmentation-type
mismatch in `reocr_core`; (2) re-run the re-recognized arm THROUGH the apparatus pipeline before judging it;
(3) separate the apparatus by **content and sequence** — a reference-anchored monotone alignment over the token
stream — because geometry has now been ruled out at every grain.

## ⚠ M31 BOOK-LEVEL SPECIALIZATION — `genesis_tuned.py` built; anchor insight validated, filter not yet (2026-07-29)

**Sir's design principle, adopted:** books and chapters are handled by VARIATIONS of the shared logic, not by
identical code. The generic functions in `layout` / `verse_seg` / `corpus_localize` are left exactly as they
are to serve as the reference implementation for the next book; Genesis's variation lives in
`genesis_tuned.py` behind `ODR_GENESIS_TUNED`.

**THE VALIDATED FIND — why the generic apparatus filter could never work on Genesis.**
`verse_seg.segment(drop_apparatus=True)` anchors on **janvier, a MODERN-SPELLING text**, so the archaic
readings the DR actually prints — `sone`, `therfore`, `daies`, `citie`, `geue`, `betwene`, `darkenes` —
anchor to nothing and are indistinguishable from apparatus. That is why `apparatus_min` had to stay at 8 and
is documented as a no-op on Genesis. Genesis has its own archaic reference, and **anchoring on s_dismas +
odr_com instead cuts the archaic-spelling false positives 3,282 -> 838 (-74%)**. What remains un-anchored is
then dominated by the recognizer's confusions (`uhich`, `uho`, `uas`, `uere`, `aud`, `ot`, `ofthe`, `thec`),
not apparatus. Folding those classes in a Genesis-only `gfold` takes un-anchored 18.77% -> 14.54%. Root cause
of the largest gap: **`_afold` folds `vv->w` and `v->u` but never `w->u`, so `was` and `vas` can never match.**

**⚠ THE RUN-LENGTH RULE BUILT ON TOP IS NOT YET NET-POSITIVE, so it is OFF.**

| setting | Genesis all-pass | note |
|---|---|---|
| baseline (no tuning) | **799** | S1 67.5 · S3 75.5 · S9 76.1 · S6 77.7 |
| `min_run=2` | 518 | near-misses explode (S6 102->302); deletes scripture — the hyphen-split "a fir. ment" is *firmament* |
| `min_run=3` | 753 | S9 +0.9 but S6 -3.1 |

**NO WORD-LEVEL BOXES EXIST.** The raw OCR JSON carries only `bbox` + `text` per LINE. Character-exact column
splitting requires a kraken re-run over ~1,400 Genesis pages — hours of compute, and the honest prerequisite
for the remaining V3 apparatus class.

**STATE LEFT AT THE VALIDATED BEST:** Genesis all-pass 799 / all-fail 104; corpus `pass_rate_archaic`
**0.6381**, `verse_cover_rate` **0.8627**. **140 tests.**

**⚠ TARGET NOT MET.** Sir asked for Genesis at ~100% against all four references. Not achieved.

## ⚠ M30 MID-LINE APPARATUS — MECHANISM FOUND, NOT ADOPTED; TARGET NOT MET (2026-07-28 night)

**Sir's target: ≥3 of 4 passing witnesses for every verse of Genesis 1. NOT MET — 13 of 31 verses reach it.**
Recorded as a miss, with what was learned.

### What the mid-line apparatus actually is
Not one mechanism but three, and only two are safely removable.
1. **Merged LEFT prefix** — apparatus concatenated at a body line's start. Fixed earlier (`strip_margin_prefix`).
2. **Separate RIGHT-column lines typed `body`** — the apparatus has its OWN line, interleaved in READING
   ORDER between body lines (`archive-holiebible-ot1` p31: L40 y=4713 and L41 y=4862 sit BETWEEN L38 y=4694
   and L39 y=4877, at x≈5150-6000). Fixed earlier (`drop_side_column_lines`).
3. **Merged RIGHT suffix** — apparatus sharing a body line's y-band on the right, so the line begins at the
   body column like any other and only its END betrays it. **Implemented, measured, NOT ADOPTED.**

### The suffix strip: two attempts, two corpus regressions, defaulted OFF
| version | edge estimator | result |
|---|---|---|
| v1 | widest gap in the line-end distribution | cut **36.5% of `jp2-S06` psalms lines**, truncating plain prose ("…the Hebrew ſtile and man" -> "…and") — a RAGGED RIGHT MARGIN is not a column. Corpus **0.6384 -> 0.5602**. |
| v2 | edge evidenced by real side-column lines (≥3 required) | psalms safe, but still over-cuts Genesis pages that DO have a column: localization MISSES **S1 9->30, S3 5->24**, Genesis **76.2% -> 64.9%**. |

`ODR_STRIP_SUFFIX=0` by default; set to 1 to measure. **The mechanism is real — on Genesis 1 it took
zero-support verses 13 -> 3 — but the character-offset estimate is not accurate enough to spend scripture on.**

### AND A BUG OF MY OWN, FOUND BY READING THE PAGE
The apparatus stages ran in the wrong ORDER. Both strips locate the text block by the median body-line x0,
and while the right-column lines are still typed `body` their x0 (≈5150 of a 6048-wide page) drags that
median from **1075 to 2603**. Every legitimate line then looks like it starts in the margin, and the PREFIX
strip cut real scripture: "5 diuided the light" from L38, "light, Day, and the" from L39, "mament made
amidſt the" from L44 — deleting Genesis 1:5 in the act of protecting it. **Demote first, then strip.** Pinned
by `test_side_column_demotion_must_run_before_the_margin_strips`. The one-sided under-cut bias did NOT
prevent this: a bias only helps once the ESTIMATE is anchored on the right thing.

### Where Genesis 1 stands
Support histogram **{0: 9, 1: 6, 2: 3, 3: 3, 4: 10}** — 13 of 31 verses at ≥3/4. Classes: PASS 61 (49.2%) ·
**V3-APPARATUS 27 (21.8%)** · **V5-RECOG 26 (21.0%)** · V6-REF 6 · L4-LONG 3 · L4-MISS 1.
The stubborn verses are **1-13**, all on the chapter's opening leaf — drop capital, chapter argument and the
densest annotation in the book. Verses 14-23 pass almost universally.

**CORPUS HELD AT THE VALIDATED BASELINE:** pass_rate_archaic **0.6381**, verse_cover **0.8627**,
16,253 archaic passes. GENESIS: S1 67.5 · S3 75.5 · S9 76.1 · S6 77.7, all-fail 104. **140 tests.** v044.

**NEXT, and it is now well-posed:** the remaining V3 needs the apparatus column's boundaries to the CHARACTER,
which line-level bboxes cannot give. That means word-level boxes from the recognizer, or a re-segmentation
with explicit column detection — not another estimator on the same evidence.

## ⚠ M29 SPAN-LENGTH REJECTION + RETRY — implemented; the TIE-BREAK was the real defect (2026-07-28 night)

Sir asked for span-length rejection and retry. Both are implemented in `corpus_localize`. **The retry was
nearly worthless and the tie-break was the whole story** — recorded that way because the reasoning matters
more than the patch.

**RETRY (`localize_volume`, post-pass).** Re-offers each verse whose span is <0.5x or >1.5x the reference on
the pages either side, whatever those pages' chapter intervals claim. Result: **5 spans improved across the
four Genesis volumes.** The candidate pages were already being offered, because adjacent pages usually DO
list the chapter — so widening the candidate set was not the constraint.

**TIE-BREAK (`_better`) — this was the defect.** `archive-holiebible-ot1` genesis 1: pages 30 (front matter)
and 31 (the real text) both carry chapter 1. For verses 4, 5, 6, 9, 11 page 30 produced a **ONE-TOKEN** span
and page 31 an 18-, 13-, 19-, 20- and 26-token one — **and both scored `janvier_fit` 0.0**, because the real
text is present but too corrupt to match. The test was a strict `fit > incumbent`, so the tie went to
whichever page was visited first: the front matter. `janvier_fit` is length-aware (a one-token span scores
0.0, not 1.0), so these never out-scored anything; they simply arrived first and were never displaced.
Fit still decides whenever it can; length sanity breaks the tie only when fit cannot.

**GENESIS: `L4-SHORT` 6 -> 0** (eliminated). Length-suspect verses across the four volumes **212 -> 115**
(-46%). The six one-token spans now hold their real text and are reclassified into their TRUE causes —
V3-APPARATUS 28->29, V5-RECOG 23->29. **The localization defect had been MASKING the real causes.**

**⚠ CORPUS VERDICT: REGRESSED, marginally — reported, not spun.**

| | before | after |
|---|---|---|
| records (attestations) | 25,453 | **25,470** (+17) |
| archaic passes | 16,257 | **16,259** (+2) |
| `pass_rate_archaic` | 0.6387 | **0.6384** (-0.0003) |
| `verse_cover_rate` | 0.8626 | 0.8626 (=) |

**Passes went UP; the RATE fell because the denominator grew faster.** The +17 records are verses that
previously had NO span at all and now have a real one — honest attestations that fail visibly. That is the
opposite of laundering (deleting them would have RAISED the rate), but it is still a rate regression and it
stands as one. **Genesis pass counts are unchanged** (S1 1027 / S3 1150 / S9 1161 / S6 1188, all-fail 108):
the verses now fail holding their own text rather than one token of the front matter's.

**WHY KEEP IT ANYWAY (Sir's call to overturn).** Span correctness is not only a gate input — the R3 re-OCR
crop is cut from the span's geometry, so a one-token span sends the vision model at the wrong region of the
page. The rate cost is 0.03%; the routing benefit applies to every verse the ladder escalates. **137 tests.**

## ✅ M28 GENESIS 1 RESCORED AGAINST ALL FOUR REFERENCES (2026-07-28 night)

`gen1_rescore.py` — 31 verses × 4 witnesses = **124 source-verses**, each scored against **all four**
references (s_dismas, odr_com, sabates_a, madueke_b) instead of the one governing reference, and classified
first-applicable-wins. Rendered under **V12** in the pilot report (**v038**).

**WHY ALL FOUR.** The gate consults ONE reference, which merges causes living in different layers — and it
cannot see the case where **the witnesses and both modern references agree and the ARCHAIC reference is the
outlier**. Genesis 1:25 is exactly that: four witnesses at 0.93–0.97 modern, all failing on an s_dismas
reading at 0.75. It is NOT a misalignment (offset 0 scores best at 0.754, the realigner was right to leave
it) — s_dismas's *reading* diverges, and `ARCHAIC_VALID_FLOOR=0.50` lets it govern anyway. Raising that floor
globally was already tested and rejected (0.90 withdraws 754 refs and LOWERS pass), so the fix is a
**reference-outlier DETECTOR**, not a gate relaxation: flag the locus, never convert it to a pass.

| class | meaning | layer | n | share |
|---|---|---|---|---|
| PASS | at or above the bar | — | 56 | 45.2% |
| **V3-APPARATUS** | interleaved annotation inside the span | V3 | **28** | **22.6%** |
| **V5-RECOG** | words present, misrecognised | V5 | **23** | **18.5%** |
| L4-SHORT | span under half the reference length | V4 | 6 | 4.8% |
| V6-REF | witnesses + modern agree, archaic dissents | V6 | 6 | 4.8% |
| L4-LONG | span over 1.5× — swallowed a neighbour | V4 | 4 | 3.2% |
| L4-MISS | no span at all | V4 | 1 | 0.8% |

**THE DISCRIMINATOR IS SPAN-LENGTH SANITY, NOT CONTENT.** Comparing low-support (≤2 witnesses passing) with
high-support (≥3): **11 of 18 low-support verses have a span <0.5× or >1.5× the reference; 0 of 13
high-support verses do.** The MEAN length ratio does not separate them (1.07 vs 1.01) — only the extremes.
Reference disagreement does NOT explain failure: s_dismas-vs-odr_com divergence is 0.231 on low-support and
**0.287 on high-support** (vv. 26–28 diverge at 0.83–0.96 and pass 4/4). Support is bimodal — 13 verses at
0/4 and 10 at 4/4 — i.e. the chapter is two populations, not a gradient.

### The side-column fix that came out of it
Genesis 1:4 reads `'And God chapter be¬ ginninꝫ ofthe ſaw the light…'`. On `archive-ot1-1609` p21 the body
column starts at x≈2352 of a 6428-wide page and line 38 is `'ginninꝫ ofthe'` at x=[5455,6360] — a RIGHT-hand
annotation line that `type_lines` calls body, because the annotation column overlaps the text block's right
edge instead of sitting in a clean outer margin. `layout.drop_side_column_lines` demotes it to marginalia
(**default ON**, `ODR_DROP_SIDECOL=0` disables). ~9–10% of body lines in all four witnesses match.

**CORPUS: pass_rate_archaic 0.6300 → 0.6387 · verse_cover 0.8535 → 0.8626 · source_fail 0.3636 → 0.3535 ·
+221 archaic passes.** All up, none down. GENESIS all-fail 113 → **108**. **137 tests.**

**CUMULATIVE THIS SESSION (margin strip + side column):** pass_rate_archaic **0.5919 → 0.6387**,
verse_cover **0.8187 → 0.8626**, archaic passes **15,064 → 16,257 (+1,193)**.

### Derived solutions, by layer
- **DETECTION (V4)** — span-length sanity is a perfect separator on the extremes and is currently only a flag.
  Make it a REJECTION+RETRY signal: a span <0.5× or >1.5× the reference should force the localizer to
  re-attempt on the adjacent page before being accepted. 11 verses in Genesis 1 alone.
- **RECOGNITION (V5)** — the `w`→`v` confusion is the largest addressable defect and is provably recognition
  (S1/S3/S9 are three copies of the SAME 1609 edition and disagree on it). Targeted Rung-2 fine-tune.
- **IDENTITY SCORING (V6/V7)** — add the reference-outlier detector: ≥3 witnesses agreeing with each other
  AND with both modern references while the archaic dissents means the ARCHAIC is wrong. Flag, never pass.
- **APPARATUS (V3)** — still the largest class at 22.6%. Both column edges are now handled; what remains is
  annotation merged INTO the middle of a body line, which line-level bboxes cannot locate. Needs word-level
  boxes from the recognizer, or a re-segmentation with explicit column detection.

## ✅ M27 MID-LINE ANNOTATION STRIP (by geometry) + SPLIT-VERSE DIAGNOSIS (2026-07-28 late)

### The biggest single gain of the sprint — strip the merged marginal column
Sir asked whether mid-line annotation footnotes can be stripped. **Yes — by POSITION, never by vocabulary.**

The DR sets annotations in a column beside the text, and the line builder merges a marginal fragment with the
body text sharing its y-band into ONE `role="body"` line, past every downstream role filter.
`archive-ot1-1609` p58 L9 is the note "Of this commandment, or …" with Genesis 9:1 running through it:
`':: Ofthis com. IL them::: Increaſe, & multiplie, and replenish the carth.'`
The scripture column starts at x=1634; that line starts at x=281.

`layout.strip_margin_prefix` (**default ON**, `ODR_STRIP_MARGIN=0` disables): body column edge = median body
x0; a line starting >0.08·W left of it carries a prefix, whose width converts to characters through the line's
own mean char width, snapped back to a token boundary. **The bias is deliberately one-sided** — under-cutting
leaves noise, over-cutting DELETES SCRIPTURE; only one is recoverable.

Scale, normalised by page width: **S1 14.0% of body lines, S3 12.4%, S9 13.6%, S6 3.4%.**

| | corpus before | corpus after |
|---|---|---|
| `pass_rate_archaic` | 0.5919 | **0.6300** |
| `verse_cover_rate` | 0.8187 | **0.8535** |
| `source_fail_mean` | 0.4041 | **0.3636** |
| archaic passes | 15,064 | **16,036** (+972) |
| verse loci covered | 5,249 | **5,472** (+223) |

**Every scripture metric improved; none regressed.** GENESIS: S1 61.3→**67.4**, S3 68.9→**75.2**,
S9 68.1→**75.1**, S6 76.5→**76.9**; parity spread **15.2 → 9.5**; all-fail **137 → 113**; all-pass 724 → **794**.
The gain tracks the defect's own distribution (S6 has 3.4% merged lines and gains 0.4 points) — that shape,
not the size, is the evidence it is a mechanism and not a coincidence. **136 tests.** Report **v036**.

### Split-verse diagnosis — the recognizer graded against its own twin
`split_confusions.py <book>`. A SPLIT verse has a PASSING sibling, and a passing sibling is within 0.90 of the
reference — so it can stand as the correct reading for the same verse of the same edition. **This diagnoses;
it never rewrites.** Copying a sibling's text would manufacture agreement between independent copies and
destroy the redundancy the whole audit rests on.

**WHICH CONFUSIONS ACTUALLY COST ANYTHING** (measured against `char_identity`, not assumed):

| confusion | archaic_id | lever? |
|---|---|---|
| `w`→`v` (424 char, ~190 whole-word: was/vas, which/vhich, with/vith) | 0.943 | **YES — the biggest** |
| `e`→`c` / `c`→`e` (586) | 0.943 | **YES** |
| `t`→`r`, `t`→`f`, `f`→`t`, `r`→`t` (498) | ~0.94 | **YES** |
| `u`→`n` / `n`→`u` (221) | 0.981 | mild |
| `h`→`li` (68, a segmentation split) | ~0.94 | yes |
| **`ſ`→`s` — long-s LOST (36)** | **1.000** | **NO — invisible to the content gate; diplomatic only, s_arbiter's job** |
| punctuation `.`↔`,` (438) | **1.000** | **NO — cosmetic, not a lever** |

**The `w`→`v` confusion is provably RECOGNITION, not a print variant**: S1, S3 and S9 are three copies of the
SAME 1609 edition and they disagree on it. It is the single largest recognizer-addressable defect in Genesis
and it argues for a targeted Rung-2 fine-tune, NOT a text rewrite or a scoring tolerance.

**Who fails when witnesses disagree** (623 splits): S1 fails 387 (sole failer 80) · S3 267 (28) · S9 268 (20) ·
**S6 240 but SOLE FAILER 168.** S6 is the 1635 facsimile against three 1609/1610 witnesses, so its solo
failures are the place to look for **genuine edition divergence** rather than recognition error — a collation
question (V6), not a recognizer one. Length ratios 0.98-1.01 confirm substitution, not truncation.

## ✅ M26 GENESIS FOUR-WAY VALIDATION + ALL-FAIL ANATOMY (2026-07-28 late)

**Order (Sir):** validate the four witnesses against each other and FIX what is found, THEN analyse the
all-fails. New tool `allfail_anatomy.py <book>` → `allfail-anatomy-<book>.json`, rendered under V12.

### Part 1 — four-way validation
Structure is sound: 99.4-100% localized in every witness, no V0 alien attestation, no V1 chapter gap.
Four defects found.

| layer | finding | scale | status |
|---|---|---|---|
| **V6** | **The archaic reference shifts PART-WAY THROUGH a chapter.** gen 1 aligned for 25 verses then shifted +1 for 26-31; gen 26 shifted for 32 verses with the offset growing -1 → -2. `archaic_ref_align.detect` fits ONE offset per chapter, so an aligned head averages a shifted tail away — a MODEL limit, not a threshold. | **65 chapters corpus-wide**, 474 loci in the audited books | **FIXED** — `detect_piecewise` + `apply_piecewise` (monotone DP over offsets, `SWITCH_COST` 0.55, scored on archaic-vs-modern ONLY, no OCR) |
| **V6** | **A one-verse s_dismas stub overriding a complete odr_com.** gen 8 has exactly ONE s_dismas verse and its text is gen 8:6-7; being preeminent it displaces the correct 8:1. gen 46 same shape. | 2 verses × 4 witnesses | detected by the same pass |
| **V1** | **Volume front matter addressed as genesis 1** (Approbatio / Epistle to the Reader / Proemial Annotations): S1 24 pages, S3 26, S9 27, S6 8. | contained by the better-fit rule (S1/S3 keep 29-30 of 31 on real pages) but **S9 loses 12, S6 loses 11** | **OPEN** — see below |
| **V1** | Running head is letter-spaced, so `G E N E S 1 5.` folded to five single letters and never matched the book name. | book-name match 26% → 46% of scripture pages | FIXED (corpus-neutral; matters at book boundaries) |

**THREE FIXES TESTED AND REJECTED for the front-matter defect — record so they are not re-proposed.**
VOCABULARY fails (front matter scores 0.32-0.51 on gen 1 — it is *about* Genesis). VERSE-NUMBER DENSITY fails
(keeping 90% of real pages also keeps 51% of front matter). PEAKEDNESS fails worst (removing 89% of front
matter discards **57% of real scripture**). **The structural fix is M1**: front matter is forced into chapter 1
because the address space has nowhere else to put it. M1 is not a nice-to-have, it is the fix for this.

Result of the fixes: 4 of 5 scripture metrics improved, **`pass_rate_both` regressed 0.5529 → 0.5521**
(22 scan-verses; `both` is not the governing gate but it moved DOWN and is not buried). `pass_rate_archaic`
0.5914 → **0.5919**, `verse_cover_rate` → **0.8187**, `source_fail_mean` → **0.4041**, all-fail 138 → **137**,
genesis 26 all-fail → **1**. Report **v034**. **134 tests, 0 failures.**

### Part 2 — anatomy of the 137 all-fail verses (control: 724 that pass in EVERY witness)

| axis | all-fail | control | ratio | implicates |
|---|---|---|---|---|
| **verse 1 of its chapter** | 0.080 | 0.017 | **4.8×** | V3 |
| **neighbour verse on another page** | 0.167 | 0.062 | **2.7×** | V4 |
| last verse of its chapter | 0.058 | 0.026 | 2.2× | V3 |
| verse closes the page body | 0.114 | 0.064 | 1.8× | V3 |
| soft-hyphen breaks in the span | 0.420 | 0.237 | 1.8× | V5 |
| verse opens the page body | 0.156 | 0.110 | 1.4× | V3 |
| reference length (tokens) | 28.0 | 23.7 | 1.2× | — |
| marginalia share of page lines | 0.186 | 0.163 | 1.1× | — |
| distinct body x-starts (columns) | 3.18 | 2.81 | 1.1× | — |
| capitalised tokens (proper names) | 0.127 | 0.144 | 0.9× | — |
| mean token length | 4.32 | 4.33 | 1.0× | — |

**AN ALL-FAIL VERSE IS A BOUNDARY VERSE, NOT A HARD VERSE.** Every separating axis is POSITIONAL; every axis
measuring DIFFICULTY (vocabulary, proper names, token length, marginalia load, column count) is FLAT. No
recognizer improvement addresses them.

**Three mechanisms, all at the chapter opening**, confirmed by reading the pages:
1. **Drop capital detached and lost** — gen 3:1 is "But the ſerpent"; every witness returns "**but** the
   ſerpent … beaſts **D** of the earth": the large initial emitted as a stray glyph mid-line.
2. **Marginal note spliced into the body** — gen 9:1: "And he ſaid to **Ofthis com. IL** them::: Increaſe …
   the carth. **mandment, or I**" — one note broken across two insertion points.
3. **Chapter argument bleeds in** — two witnesses open gen 8:1 with "and offereth ſacrifice", the tail of the
   chapter summary.
All three are LINE-CONSTRUCTION artifacts (V3): the recognizer reads the glyphs; the line builder concatenates
a drop cap, a marginal column and an argument line into the body stream where no role filter can reach them.

## ✅ M25 BOOK-GRAIN CROSS-WITNESS AUDIT — the method, and GENESIS (2026-07-28 evening)

**Sir's directive:** stop chasing one source's gaps wherever they fall; audit **book by book, all witnesses at
once**, validating the horizontal stack (parity across S1/S3/S4/S6/S8/S9) and the vertical stack together.

**Why it works.** Holding the BOOK fixed and varying the WITNESS makes the witnesses controls for one another,
and one question splits two unrelated classes of defect:

> **Every witness fails the same verse** → no witness's recognizer is at fault; the defect is **VERTICAL**.
> **One witness fails what its siblings read correctly** → **HORIZONTAL**: that volume's scan, layout, or head.

Both #8 and #9 presented as recognition problems and were neither. A sibling reading the same verse correctly
is what exposed them. `book_audit.py <book>` operationalizes it → `book-audit-<book>.json`, rendered as **V12**
in the pilot report and as §12 of the 108-book reconstruction report.

**THE OPERATIONAL VERTICAL STACK.** A defect is attributed to the LOWEST layer that can explain it — calling a
truncated span "recognition" is how #8 survived three rounds.

| | owns | modules | characteristic fault |
|---|---|---|---|
| **V0** | source inventory | `witness_inventory` | a book attested by a volume that cannot hold it; a duplicate rendering admitted |
| **V1** | page addressing | `page_address` (monotone DP) | a chapter with no page; a page on the wrong chapter. Monotone ⇒ one false heading ERASES a range (#9) |
| **V2** | tome map | `build_tome_map_v2` | divergence from V1; derived from addressing, so never feedable as a prior |
| **V3** | pinning / body isolation | `_line_range`, `build_body_tokmap` | chapter lines truncated (#8) or over-offered; marginal apparatus concatenated INTO a body line |
| **V4** | verse localization | `verse_locate.best_spans`, `verse_seg` | no span for a verse on the page; a span short or over-long |
| **V5** | recognition | `reocr_core`, `r3_route` | substituted tokens — the ONLY layer a better recognizer fixes |
| **V6** | reference | s_dismas · odr_com · janvier | a locus the reference lacks; a versification offset |
| **V7** | gating / scoring | `qc_audit`, `xsrc_gate` | a metric consulting a set the label helped build (#7) |
| **V8** | reporting / versioning | `build_reocr_report`, `version_compare` | a stale or circular figure persisted where it will be quoted |

### GENESIS — first book audited
Carried by **4 witnesses** (S1, S3, S9, S6). S4/S8 are NT-only. **V0 alien attestations: none. V1 chapter gaps: none.**

| wit | volume | localized | passed | rate | A·extra V3 | B·missing V4 | C·subst V5 | D·near V5 | misses V4 |
|---|---|---|---|---|---|---|---|---|---|
| S6 | jp2-S06 | 1530/1530 | 1170 | **76.5%** | 10 | 17 | 221 | 112 | 0 |
| S3 | pdf-S03a | 1526/1530 | 1051 | 68.9% | 45 | 37 | 148 | 245 | 4 |
| S9 | archive-holiebible-ot1 | 1530/1530 | 1041 | 68.0% | 51 | 50 | 103 | 285 | 0 |
| S1 | archive-ot1-1609 | 1521/1530 | 933 | **61.3%** | 33 | 38 | 314 | 203 | 9 |

**Parity spread 15.1 points.** Cross-witness: all-pass **723 (47.3%)** · split **669 (43.7%)** · **ALL FAIL 138
(9.0%)** ← the honest size of the vertical problem; no recognizer work reaches those.

The profiles differ in KIND. S1 is recognition-dominated (314 of 588 failures are substituted tokens) — a V5
problem specific to that volume. S9 is near-miss dominated (285 of 489), accumulated glyph noise. **S6 leads
despite the corpus's worst addressing accuracy**: the 1635 facsimile's wider setting gives the fewest
interleave/truncation errors (A+B = 27 vs S9's 101). Scan layout and recognition quality are independent axes.

**A FIX CONSIDERED AND REJECTED — record it so it is not re-proposed.** 62% of Genesis failures carry a short
un-anchored token run, exactly the apparatus-filter signature, just under `apparatus_min=8`. Widening it would
have raised the score at once. Asking the siblings settled it: the same tokens appear in 3-4 INDEPENDENT copies
— `sone`, `therfore`, `daies`, `citie`, `geue`, `betwene`, `darkenes`, `uho` — and they are **correct archaic
spellings** a modern-spelling grid cannot match. The filter would have deleted scripture to raise a number.

**OPEN from Genesis:** the 15.1-point parity spread (S1 V5) · the 138 all-witness failures (vertical) ·
`jp2-S06` still at 52.15% held-out addressing.

## ✅ M24 M4 DONE · M3 RESOLVED · DEFECTS #6–#9 (the heading parser read half the corpus) — v030 (2026-07-28 PM)

**M4 (done).** Deleted the dead module-level `TOME = json.loads("tome-map.json")` and
`_tome_prior_v1_disabled` from `page_address_eval`. `_PIDX` stays — it is live in `load_pages`. The liability
was never the wasted read: a module-level load makes the module fail to IMPORT the day the retired artifact is
deleted, so dead code that runs at import is not dead. `tome_prior`'s docstring keeps the measurement that
retired the prior.

**Defect #6 — `CHAP_HEAD` did not match how the DR prints headings.** Measured: the old
`CHAP(?:TER)?\.?|PSALME?\.?` pattern saw **2,372 of 4,640** heading-bearing pages, **51%**. Three causes:

| cause | example | worst case |
|---|---|---|
| headings are set LETTER-SPACED | `C H A P. I.` | `jp2-S06` +687 pages |
| 1582/1610 NT abbreviates to `CHA.` | `C H A. I.` | `archive-nt-1582`: **6** readable headings in 762 pages |
| display capitals misread | `CηA.`, `CN A P.`, `O H A.`, `GHAP.` | `pdf-S09nt` +434 pages |

The `len(text.split()) > 4` display-line guard compounded it, rejecting fully letter-spaced headings as
"sentences" — the SAME pages, so the two defects multiplied rather than merely coexisting.

Fixed in `block_grammar` as the single source of truth: an OCR-tolerant `CHAP_HEAD`, `display_words()`, and
ONE subtractive `roman()` replacing the hand-typed `_ROMAN` lookup that was capped at XX (defect shape #5, still
live until now). Two deliberate restraints, both load-bearing: the NUMERAL is case-**sensitive** (under `re.I`
the marginal note `Cη. Ad` parsed as roman D = chapter 500), and psalms are NOT folded in — `_PSALM_HEAD` owns
them and tolerates `Pſalme`, which a literal-S stem would silently drop. Precision was audited before the
change was made: zero implausible chapter values corpus-wide, max 111, and a monotonically decaying
chapter-frequency distribution — the signature of genuine headings rather than stray numerals.

**M3 — matthew 1 unmapped — RESOLVED, and the cause was not the one in the plan.** It was never a
front-matter-boundary case. TWO things were wrong. First, all four NT volumes' front matter (the *Preface to
the Reader*) was being addressed as `matthew ch 2`, and monotonicity then made chapter 1 unreachable. Second
and decisively: **all eleven cached `.page-address-*.json` were built with `use_headings=False` — the held-out
VALIDATION configuration was being used as the production deliverable basis**, with the printed headings
deliberately withheld from the DP. With headings restored as evidence plus the parser fix, all four NT volumes
carry **matthew 1–28 complete** at 100% coverage. (`jp2-S06` correctly has no Matthew: its NT pages are the
dropped duplicate.) Held-out runs are now preserved separately as `.page-address-<v>.heldout.json`.

**Defect #7 — the circular metric, killed a second time.** `heldout_heading_accuracy` asked whether the
printed chapter was in `chapters_on_page`, but `address_volume` unions `printed_heading_lines(p)` into that set
unconditionally, held-out mode included. It returned exactly **1.0 on all eleven volumes in both modes**, and
it was the value PERSISTED to the artifact while the honest one went only to stdout. §12.6 had already
recorded this error once; it survived in a different field. Now the honest predicate (printed chapter vs the
DP's own chapter, allowing dp+1), with the old value kept as `circular_accuracy_do_not_quote`.

**Numbers.** Coverage 12,820/12,820 = 100% (unchanged). Honest held-out **86.13% (3,367/3,909)**, production
**93.27% (3,646/3,909)**. The prior **94.4% (2,238/2,372)** is SUPERSEDED, not regressed — it was computed on
an easy-biased half of the evidence. Honest DP disagreement fell in every volume once headings were used
(`jp2-S06` 12.78%→5.29%, `pdf-S09nt` 2.73%→0.87%, `jp2-S04` 3.66%→1.70%). **131 tests, 0 failures.**

**Defect #8 — `corpus_localize._line_range`, and the answer to "where did 659 scan-verses go".** The v028 run
read REGRESSED on scripture, so the missing attestations were traced rather than accepted. The cause was NOT
over-claim removal and NOT the front-matter pages: a controlled A/B with the heading parser held constant moved
`jp2-S04` by **+1 attestation**, so the held-out→production switch is not it. `_line_range` took only the FIRST
`printed-heading` pin, which is wrong in both directions once the headings became readable at all:

| failure | scale | example |
|---|---|---|
| **TRUNCATION** — a chapter owns a `carry-in` segment before its heading AND a `printed-heading` one after, whenever the heading falls mid-page | **3,006 pages, 67,284 body lines discarded** | `jp2-S04` p680 is Apocalypse 1 across all 83 lines with `CHA P. I.` at line 44 → returned (44, 82), discarding lines 0–43 and with them Apoc 1:11–15 at janvier fit 0.79–0.98 |
| **OVER-CLAIM** — a chapter with only a `carry-in` pin returned None, so the whole page was offered | **275 pages** | the exact runaway the function exists to prevent, on boundary-straddling pages |

Fix: a chapter's range is the UNION of every pin naming it. `printed-heading` remains authoritative for where a
chapter STARTS; it was never authoritative for where its text on this page begins or ends. **Mechanism proven,
not argued**: monkeypatching the old parser back in reproduced v026's S4 figure exactly (2,325).

**Result — v029, verdict IMPROVED, and the regression is closed.** Against the v026 pre-fix baseline:

| metric | v026 (pre-fix) | v028 (mid) | v029 (final) |
|---|---|---|---|
| scan-verse records | 25,328 | 24,669 | **25,423** |
| archaic passes | 14,949 | 14,407 | **15,032** |
| `pass_rate_archaic` | 0.5902 | 0.5840 | **0.5913** |
| `source_fail_mean` | 0.4053 | 0.4151 | **0.4044** |
| `verse_cover_rate` | 0.8181 | 0.8072 | 0.8169 |

**132 tests, 0 failures.**

**Defect #9 — page furniture accepted as a chapter heading (the S6 psalms 26–29 cluster).** Chasing the
residual −11 loci found the cause, and it was not the superscription offset. `jp2-S06` p1085 line 50 of 52
reads **`Pſal. 30`** — BELOW the page's last body line, after a catchword, beside the next leaf's
`T H E B O O K` header. Taken as a heading it is decisive evidence (+4.0), so the page was addressed to Psalm
30; and because the chain is MONOTONE and cannot go back, pages 1086–1088 were dragged to 30 with it. Content
alone had them right — 27, 28, 28, 29 — and p1086 plainly carries Vulgate Ps 28:6–7 ("breake them in pieces as
a calfe of Libanus … the voice of our Lord diuiding the flame of fire"). **Three psalms erased from the corpus
by one line of page furniture**, at a cost of 11 verse loci.

Rule: **a heading must head something** — there must be a body line AFTER it on the page. 68 of the corpus's
4,085 detected headings (1.7%) fail that test. Rejecting them costs nothing when the heading is real but its
chapter opens on the next leaf: the pin is simply not offered for THIS page, and content places it, which is
what content is for. Fixed alongside it: `page_evidence` was running its OWN heading scan one line below a
comment forbidding exactly that (the recurring defect shape in its purest form) — it now calls
`printed_heading_lines`, so a guard on one is a guard on both, evidence and held-out label alike.

**Result — v030. All six metrics at or better than the v026 pre-fix baseline; the residual is closed.**

| metric | v026 (pre-fix) | v028 | v029 | v030 (final) |
|---|---|---|---|---|
| scan-verse records | 25,328 | 24,669 | 25,423 | **25,452** |
| archaic passes | 14,949 | 14,407 | 15,032 | **15,052** |
| `pass_rate_archaic` | 0.5902 | 0.5840 | 0.5913 | **0.5914** |
| `verse_cover_rate` | 0.8181 | 0.8072 | 0.8169 | **0.8186** |
| covered verse loci | 5,245 | 5,175 | 5,237 | **5,248** (0 still-lost) |
| `source_fail_mean` | 0.4053 | 0.4151 | 0.4044 | **0.4044** |

Addressing: 100% coverage, honest held-out **86.95% (3,357/3,861)**, production **93.94%**. **134 tests, 0 failures.**

**⚠ ONE ITEM STAYS OPEN AND BLOCKS (No Silent Degradation).** `jp2-S06` honest held-out is **52.15%** — still
the worst volume by a wide margin (next worst ~87%), and its heading-vs-DP disagreement is **4.77%** against
~1% elsewhere. The psalms-26-29 cluster is fixed and was NOT the whole story. The superscription-offset
hypothesis was checked and rejected: the cause there was furniture, not versification. Next step is to
characterise the remaining 4.77% page by page rather than assume a single cause.

## ✅ M23 TOME-MAP DOSSIER + INTEGRITY SWEEP — 387 findings diagnosed to 118 (2026-07-28)
Sir asked for a full walk-through of `tome_prior` / tome-map v1 / v2, and his read that "the tome-map is
incomplete and inaccurate". It was — and so was v2. Published artifact: `tome-map-dossier.html`.

**v1 IS UNUSABLE ON THREE VOLUMES** (measured against the addressing, best of offsets -2..+2):
`jp2-S04` **0.0%** (claims `jeremie`+`john` for the 1633 Rheims NEW TESTAMENT — jeremie is an OT book) ·
`pdf-S03b` **0.0%** (claims `1-esdras` alone for an 1,134-page OT tome) · `archive-nt-1582` **25.5%** (3 books
for a 765-page NT) · `jp2-S09ot2` **absent entirely**. The 0.0% rows are flat at EVERY offset, whereas the
sound volumes peak sharply at one — that is what separates a wrong claim from a shifted index.

**`tome_prior` DISABLED, not re-pointed.** v2 cannot replace v1 as the prior because v2 is DERIVED from the
addressing — feeding it back would make the DP confirm its own answer. Removal was measured first: held-out
accuracy identical with and without it, on every volume tried.

**MY OWN ACCURACY FIGURE WAS CIRCULAR** (see the RESUME header). 61.5% honest, not 100%.

**THREE PARSER DEFECTS, each found by diagnosing rather than assuming:**
1. **Spaced roman numerals truncated.** `CHAP. X. V.` (XV=15), `CHAP. X I.X.` (XIX=19), `CHAP. X XII.` (XXII=22)
   all read as **X=10**. The addressing had placed those pages at 15, 18-19 and 22 — **right every time; the
   parser was wrong.** Honest accuracy 61.5% -> 92.5%.
2. **The same parser duplicated in `block_grammar.chapter_ranges`**, still truncating — and `chapters_on_page`
   took its chapter NUMBERS from there. **598 of 747 discontiguous-chapter outliers traced to exactly this.**
   Chapter numbers now come from one parser; `chapter_ranges` still supplies its LINE RANGES.
3. **False heading detections** (119): lowercase inline citations (`chap. 35. §.`, `chap. 1. in o.`) and prose
   lines. A heading must now LOOK like a display line — <=4 words, not lowercase. Both tests are on the line's
   FORM, never on whether the answer agrees with the addressing, or the held-out check goes circular again.

**`zacharias` — a whole book in the wrong tome.** `OT2_BOOKS` read `zacharie`; the canon spells it
`zacharias`. A minor prophet unambiguously in the second OT tome was classified OT1, given the OT1 state space,
and could never be found. Now guarded: the set validates against the canon at import and raises on an
unrecognised slug.

**INTEGRITY SWEEP (`integrity_sweep.py`) — ten checks, every tome, every source.** Each check exists because a
defect of that shape was already found by hand here.

    C1 out-of-tome 0 · C2 missing book 0 · C8 double-counted 0
    C3 missing chapter 5 · C4 skipped opening 5   (matthew 1, the NT volumes)
    C5 discontiguous 348 -> **78** · C6 overlong 15 · C7 front-matter dump 7 · C9 page-count 5 · C10 verse-vs-address 4
    TOTAL 387 -> **118**

**C5 DIAGNOSED BEFORE BEING TREATED AS AN ADDRESSING ERROR — 96% was the instrument:** 598 pages from the
duplicated parser, 119 from false headings, **30 (4%) from the addressing**. That ratio is the argument for
diagnosing first, and it has now held three rounds running.

**THE THREE RENDERINGS DISAGREE ON PAGE COUNT** (C9, informational but blocks M2): S09-OT1 is OCR 1160 / jp2
1159 / PDF 1156; deltas are not uniform, so **no single rule maps a jp2 page to a PDF page**. Each volume needs
its own verified offset, established BY IMAGE — the PDFs carry no text layer.

## ✅ M22 tome_prior REMOVED + REPORT REDESIGN (item FIVE, partial) — v026 (2026-07-28)

**`tome_prior` DISABLED, not re-pointed.** It fed tome-map **v1** into the addressing DP as evidence, and v1 is
25.5% accurate on `archive-nt-1582` and 0.0% on `jp2-S04` / `pdf-S03b` — that is not weak evidence, it is
misinformation with a +0.4 emission bonus attached. **v2 cannot replace it: v2 is DERIVED from this addressing,
so feeding it back would make the DP confirm its own previous answer** — a self-fulfilling prior that looks
like agreement and proves nothing. So it was removed, and the removal was MEASURED FIRST: with and without the
prior, held-out chapter accuracy is identical on every volume tried, including where v1 was accurate
(pdf-S03a 309/309, jp2-S08 150/150, archive-ot2-1610 152/152) and where it was worst (archive-nt-1582 14/14).
The content evidence and the monotone constraint already carry it.

**A LOGIC CONFLICT MY OWN PREDICATE FIX INTRODUCED — caught by the new governance panel.** `floor_modern` can
mean "the modern edition diverges" (invalidating modern) OR "the archaic entry is not this verse" (invalidating
archaic); it cannot mean both at one locus. After the predicate fix, `route_locus` withdrew the archaic
reference AND then refused modern on the same signal: **1752 records fell to `needs-in-family-reference` and
only 16 reached the modern gate**, so those verses could never pass. Fixed — once the archaic reference is
withdrawn as not-this-verse, the comparison it came from is void and cannot also condemn modern (Sir's policy
is explicit that janvier/madueke ARE primary where the archaic witness has gaps):

    pass 13,921/25,328 = 54.96%  ->  **14,335/25,328 = 56.60%**
    governance: archaic 23,560 (93.0%) · modern 16 -> **634** · needs-in-family-reference 1752 -> **1134**
    archaic reference withdrawn at 1702 records; **414 of them now pass under the modern witness**

### REPORT REDESIGN — the two tracks, stated at the top and badged on every figure
The report measured two different things without saying so, and conflating them is what made real progress
look like none for weeks. Every figure now carries a track badge (10 corpus-wide, 2 dev-set):

    CORPUS-WIDE (the deliverable)   5245 / 6411 verse loci · witness-anchored · what production can do at
                                    runtime with no gold. Moves ONLY when the pipeline is applied to the corpus.
    DEV SET / GT (the instrument)   base 0.7166 -> R2 0.9173 · 203 gold-anchored verses on 16 pages · the truth,
                                    not a proxy — but **3.2% of the corpus**. A rung validated here is evidence
                                    about the METHOD, not about the corpus, until the corpus figure moves.

The dev-set card also carries Sir's correction that the **Gold Transcript is NOT the authority** on
localization / presence / interval alignment / verse-line (janvier + madueke are), and may itself need
standardising against janvier's structure.

**V4 REBUILT AS A MOVEMENT, NOT A SNAPSHOT.** It plotted the current witness-depth histogram only, which cannot
distinguish a pipeline that never ran from one that ran and failed. Now grey = pre-re-OCR baseline, blue =
current: **mean witness depth 0.55 -> 2.32; verses with >=2 passing witnesses 943 -> 4293 of 6434.** The stale
caption claiming "the shortfall is universal" is replaced — but the E(v) point is RETAINED and restated,
because it is still true: E(v) is 9-12, every verse is still below it, and **the backward gate still fails
everywhere. The shortfall is narrower, not closed.**

**V5 — the AND-gate arm is now labelled as retained-for-continuity-only** (it compares against a scheme
abandoned before this phase) and a new panel answers the live question instead: WHICH witness actually judged
each record, and how often the archaic reference was withdrawn and why.

**STILL OUTSTANDING in item FIVE:** V8 apparatus detail (for later apparatus tuning) · V9 rung/arm completeness
pass · the sweep of remaining sections for stale captions like V4's. Report is **v026**; 126 tests green.

## ✅ M21 (THIRD+FOURTH) THE REFERENCE POLICY WAS ALREADY IMPLEMENTED — THE PREDICATE WAS WRONG (2026-07-27)
Sir: *"verify whether you've already implemented this somewhere else but have lost it. This was day-1 rules."*
**He was right.** `char_identity.evaluate_locus` has always read:

    archaic_ref_exists = archaic_ref is not None and archaic_ref.strip() != ""
    if archaic_ref_exists: governing_gate = "archaic"   else: governing_gate = "modern"

That IS the policy — archaic primary where it has text, modern otherwise. **What was wrong is the PREDICATE.**
`archaic_ref_exists` is true for any NON-EMPTY STRING, which is not "has text content of its own for this
verse". An entry holding the NEIGHBOURING verse satisfies the string test, governs, and fails a verse the OCR
read correctly. I was about to build a new heuristic for a rule that already existed.

### THE SYSTEMIC s_dismas DEFECT, READ OFF THE TEXT ITSELF (Sir's THIRD)
At the 517 loci where the OCR agrees with janvier >0.9 and the archaic reference agrees at 0.017, the archaic
entry is neither missing nor corrupt — **it is the neighbouring verse**:

    psalms/1/5   s_dismas "The impious not ſo: but as duſt…"   = Ps 1:4   janvier = Ps 1:5
    psalms/3/1   s_dismas "Lord why are they multiplied…"      = Ps 3:2   janvier = the SUPERSCRIPTION
    psalms/4/1   s_dismas "VVhen I inuocated…"                 = Ps 4:2   janvier = the SUPERSCRIPTION

**s_dismas does not count the Psalm superscription as verse 1; janvier does** — a known Vulgate/DR numbering
divergence, not an error in either witness. Every verse of such a psalm is shifted by exactly one.

**FIX = REALIGN, NOT DISCOUNT (`archaic_ref_align.py`).** The day-1 rule alone would hand these verses to
janvier — correct, but it throws away a real archaic witness that IS present, merely indexed differently.
Per-(book,chapter) offset detection scored by `floor_modern` (references only, NO OCR — so it cannot be tuned
to flatter the OCR) found **27 shifted chapters across 13 books** (psalms 10, mark 3, romans 3, luke 2, …) with
textbook profiles — a sharp peak at one offset and 0.0 at every other, the same signature that separated a
shifted tome-map index from a wrong one:

    2-paralipomenon/24   offset -1   floor_modern 0.1228 -> 0.8442
    luke/11              offset -2   floor_modern 0.0924 -> 0.9102
    archaic-vs-modern agreement over ALL loci: 0.9153 -> 0.9334 · >=0.90 on 91.1% -> 92.9%

### THE CORRECTED PREDICATE, CALIBRATED NOT PICKED
`ARCHAIC_VALID_FLOOR` = the archaic witness is primary only where `floor_modern >= floor`.

    floor 0.50   pass 13921/25329 = 54.96%   archaic withdrawn 1702
    floor 0.90   pass 13837/25329 = 54.63%   archaic withdrawn 2456

**0.90 withdraws 754 MORE references and LOWERS the pass rate** — those are loci where the OCR independently
corroborates the archaic reading, i.e. two witnesses agreeing, so the reference is sound even where it differs
from janvier (legitimate archaic/modern divergence). **0.50 is the calibrated value**, and the separation
supports it: floor_modern <0.5 on 0/4714 demonstrably-sound references, 504/517 demonstrably-wrong ones.

    audit basis                                    pairs    passing          mean archaic_id
    detect (legacy, where this all started)       27,241    3,512 = 12.89%       0.5202
    declared inventory                            25,329   13,476 = 53.20%       0.7650
    + realigned archaic ref + corrected predicate 25,329   13,921 = 54.96%       0.7910
    + OCR completion (no pilot-scope effect)      25,328   13,921 = 54.96%       0.7911

REPORT **v022**, comparator verdict **IMPROVED**: `pass_rate_archaic` 0.5325 -> **0.5902** ·
`verse_cover_rate` 0.7389 -> **0.8181** · `source_fail_mean` 0.4627 -> 0.4053 · verse loci with >=1 passing
scan **5245/6411** · chapter loci **23/271** (was 1/271 before any of this work).

### FOURTH — the five sets on the corrected basis (`five_sets.py`, `five-sets.json`)

    set                                  records  loci  floor_modern  archaic slot holds   withdrawn
    S1 modern<0.2                          1,596  1047     0.9057     this verse 920        123
    S2 archaic<0.2                         3,263  1437     0.6714     this verse 903 /
                                                                      DIFFERENT 481        1694
    S3 modern<0.2 AND archaic<0.2          1,497   996     0.9058     this verse 883        120
    S4 modern>0.9 AND archaic<0.8          1,124   404     **0.1128** DIFFERENT 364         988
    S5 archaic>0.9 AND modern<0.8             32    15     0.7964     DIFFERENT 15            0

**`floor_modern` cleanly partitions cause from cause.** S1/S3 sit at ~0.906 — the two references AGREE about
what the verse says, so the OCR is genuinely at fault; **that is the ladder's real work.** S4 sits at 0.113
with the archaic slot holding a DIFFERENT VERSE on 364 of 404 loci — a reference defect, and the corrected
predicate already withdraws 988 of its 1124 records. **S4:S5 = 1124:32 = 35:1**, which is the quantitative
statement that the archaic witness is the weaker instrument, not the OCR.

### THE TWO OCR DEFECTS
* **`jp2-S09ot2` jp2 mapping — FIXED and verified.** Added to `OCR_DIR_TO_JP2`, with a new `JP2_INDEX_OFFSET`
  table carrying its VERIFIED -1 shift (`jp2_path('jp2-S09ot2', 40)` now returns `…_0039.jp2`). Without it,
  every crop, R3 read and visual check for the whole of S9's OT2 would have used the NEXT LEAF.
* **`archive-holiebible-ot1` 380 missing pages — DONE. 1159/1159, zero missing.** Plus the residual gaps on
  three further volumes (pdf-S03a 6, pdf-S03b 12, pdf-S09nt 2). `ocr_complete_volume.py` is resumable by
  construction, which mattered: the run was killed twice and resumed from disk each time at no cost beyond the
  page in flight. Re-addressed at **100% coverage / 100% held-out**; archive-holiebible-ot1's held-out labels
  184 -> **313**, pages addressed 774 -> **1144**. Corpus now **12,820 pages, 11 volumes, all addressed**.

  **⚠ ATTRIBUTION, STATED SO THE REPORT'S JUMP IS NOT MISREAD: the 380-page completion contributed ZERO
  pilot-scope verses.** Those pages are Job and the later OT1 books; the pilot's genesis sits at pages 20-184.
  Measured, not assumed: `verses sourced from the newly-OCR'd range (>=780) = 0`. The work is real and the
  volume was a third blind, but **the report's v021->v022 movement is the REFERENCE POLICY, not this OCR run.**

## ✅ M20 THE WITNESS INVENTORY IS DECLARED, NOT INFERRED — and 6 of 11 volumes were mis-addressed (2026-07-27)
Sir, correctly: *"You know what is in each source, right? It's almost like you are deliberately trying to find
things to work on that you already are supposed to know the answer to. Audit your mess."* He was right. The
inventory is a FACT about the collection; I had been recovering it by measurement from three artifacts that
each claim authority and disagree:

    master-source-list.json   testaments per WITNESS, not per volume -> S1's 3-volume set hands "OT+NT" to
                              its New Testament
    tome-map.json             declares jp2-S04 — the 1633 Rheims NEW TESTAMENT — as ['NT','OT']
    (missing entry)           fell back to "both"

**A 27-book volume therefore got a 73-BOOK STATE SPACE, and the addressing DP used the room.** Audited against
Sir's stated collection:

    archive-ot2-1610  (S1 OT2)      140 pages addressed to NT books   <- an OT volume cannot hold an NT page
    jp2-S06           (S6 OT1+OT2)  772 pages addressed to NT
    jp2-S09ot2        (S9 OT2)      136 pages addressed to NT
    pdf-S03b          (S3 OT2)       30 pages addressed to OT1
    archive-ot1-1609 / pdf-S03a       1-2 page bleed
    ---------------------------------------------------------------------------
    6 of 11 volumes carried out-of-tome pages.

**`witness_inventory.py` (new) now holds the collection verbatim and everything defers to it.** Four
reconstructed complete copies: **A**=S1 · **B**=S3+S8 · **C**=S9 · **D**=S6+S4, with each source's tome→volume
mapping, the **S6-NT drop rule** (S6's NT repeats the 1582 edition already held by A/B/C — dropped, never
scored, or it would add a fourth copy of one edition and inflate every cross-source agreement), and the
excluded scan dirs. State spaces are now **21 books (OT1) / 25 (OT2) / 27 (NT) / 46 (S6)**.

**RESULT AFTER RE-ADDRESSING ON THE DECLARED BASIS: out-of-tome pages 6/11 volumes -> 0/11.** All 11 volumes
at **100% coverage**, **1712/1712 held-out chapter labels**, 12,446 pages.

**FULL CHAIN RE-RUN (address -> localize -> audit -> tome-map v2 -> report v021):**

    audit basis            pairs     passing            mean archaic_id
    detect (legacy)       27,241   3,512 = 12.89%           0.5202
    hybrid, bad inventory 27,751  14,458 = 52.10%           0.7601
    hybrid, DECLARED      25,329  13,476 = **53.20%**       **0.7650**

**THE 2,422 REMOVED PAIRS ARE THE S6-NT DROP RULE, VERIFIED NOT ASSUMED: 2,344 of them are `jp2-S06` on
matthew / john / apocalypse** (the rest is 78 pairs of small tome bleed). So S6 had been contributing a FOURTH
copy of the 1582 New Testament to every cross-source comparison — exactly the inflation Sir's rule exists to
prevent — and removing it RAISED the pass rate rather than lowering it. 0 pairs were added, so nothing was
lost in the exchange.

`tome-map-v2.json` now reports each volume at exactly its declared tomes (jp2-S06 = OT1+OT2, 46 books, NT
excluded; jp2-S09ot2 = OT2 with its verified -1 jp2 offset recorded and jp2-backing flagged absent).
Report **v021**: `pass_rate_archaic` 0.5214 -> **0.5325**, `source_fail_mean` 0.4743 -> 0.4627.
`verse_cover_rate` 0.7417 -> 0.7389, which is the S6-NT removal and is CORRECT, not a regression.

**IT ALSO DISSOLVES TWO THINGS I HAD BEEN TREATING AS OPEN QUESTIONS.** `jp2-S09ot2` is simply S9's OT2 volume
— no mystery, a directory name that did not say so. And `archive-holiebible-ot2` is not a missing witness; S9's
OT2 is already OCR'd under that other name. What REMAINS real from that investigation: the **verified +1 jp2
index offset** on `jp2-S09ot2`, and `archive-holiebible-ot1` being **380 pages short of OCR** (contiguous tail
— a run that died and was never resumed).

### REFERENCE-WITNESS POLICY, now stated and encoded (Sir, same date)

    LOCALIZATION · PRESENCE · INTERVAL ALIGNMENT · TEXT TYPE   janvier + madueke are PRIMARY (being modern
        does not disqualify them — these are structural questions about a type-modernized product).
    CONTENT · SURFACE   s_dismas + odr_com are PRIMARY **only at loci where they carry text of their own**;
        WHERE THEY HAVE GAPS, janvier + madueke are primary for content and surface too.
    GOLD TRANSCRIPT is NOT the authority on localization / presence / interval alignment / verse-line. It is
        the best-reviewed SUBSET — a comparative baseline for measuring re-OCR progress — and likely needs
        standardising so its structure is congruent with janvier's.

**THIS DISSOLVES THE POP-2 PROBLEM RATHER THAN CALIBRATING IT.** The 1535 records at archaic<0.2 / modern>0.9
with `floor_modern` 0.008 are loci where **s_dismas has no text of its own**. The policy already says
janvier/madueke are primary for content and surface exactly there. So the fix is not the ad-hoc symmetric
`floor_modern` threshold I proposed and was about to calibrate — **it is implementing the stated policy.**
Also: the `janvier_fit` selector the localizer has relied on all along turns out to be the policy's
localization rule, which was simply never written down.

**FRONT/BACK MATTER is in scope at every stage** — as source witnesses, as Gold Transcript pages, and in the
comparisons (gold vs OCR baseline vs rung-improved vs modern/archaic references).

## ✅ M19 (FIRST) SOURCE INVENTORY LOCKED DOWN — one rendering per source, audited at every stage (2026-07-27)
`source_inventory_audit.py` (new) + `source-inventory-audit.json`. Audits the OCR corpus on disk, the
registry's declared volumes, the page-address caches and the localization caches — because a duplicate that
never reaches the audit still costs compute and can leak into a later join.

**DUPLICATES FOUND AND QUARANTINED:** `pdf-S04` and `pdf-S06` are second renderings of `jp2-S04` / `jp2-S06`.
They are NOT declared in the registry — so `qc_audit` never read them and **no published number was ever
contaminated** — but I had addressed AND localized both in the Stage-1 run. Their caches are moved to
`.quarantine-duplicate-renderings/` (moved, not deleted; they regenerate). Re-running the audit afterwards
gives **14458/27751 = 52.10%, byte-identical to before** — the verification that the quarantine changed
nothing, which is the point of doing it as a check rather than an assertion.

**⚠ THE "PREFER jp2" RULE IS RIGHT, BUT THE `pdf-` PREFIX IS A LIE — a name-based audit would have reported a
problem that does not exist and missed the one that does.** `jp2_page.OCR_DIR_TO_JP2` maps `pdf-S03a`,
`pdf-S03b` and `pdf-S09nt` to **jp2 images**: the pipeline already reads jp2 for them, the directory name is
just historical. Two REAL inconsistencies surfaced once the audit looked at the mapping instead of the name:

    jp2-S09ot2                admitted witness volume with NO jp2 backing  — the only one in the curated set
    archive-holiebible-ot2    jp2-backed and NOT registered                — possibly S9-OT2's proper jp2 source

Those two are **flagged, not silently fixed**: changing which volume represents S9's OT2 changes the witness
set, which is Sir's call, not mine.

**⚠ AND THE jp2>pdf ASSUMPTION IS NOT UNIFORMLY TRUE — MEASURED, PAIRED, ON SHARED LOCI:**

    jp2-S04 vs pdf-S04   mean janvier_fit 0.8626 vs 0.8623   delta +0.0005   Wilcoxon p=0.0013   jp2 better
    jp2-S06 vs pdf-S06   mean janvier_fit 0.8148 vs 0.8304   delta -0.0191   Wilcoxon p=4e-78    **PDF better**

S04 is a statistical win with no practical difference. **S06's stored PDF OCR beats its stored jp2 OCR
decisively** — and the jp2 is 5100x6601, so this is NOT a resolution deficit. **THE COMPARISON IS CONFOUNDED
and I am not treating it as a verdict on the source:** these are two OCR RUNS that differ in source *and*
settings, so what it proves is that **the stored jp2-S06 OCR is bad, not that the jp2 image is worse.** The
correct response under "all OCR should be redone from jp2" is to RE-OCR jp2-S06 at proper settings and
re-measure — not to switch S6 to the PDF. Recorded as OPEN.

## 🔬 M18 DIAGNOSTICS A–E — TWO ROOT CAUSES, AND ONE IS THE REFERENCE (2026-07-27)
`audit_diagnose.py` (new) answers Sir's five diagnostic questions per-source, per-book and pooled from
`coverage-audit-verse.json` + `.corpus-localize-*.json`. No OCR re-run.

### A + D COLLAPSE INTO ONE BUG, NOW FIXED: FOUR VOLUMES WERE NEVER PROCESSED
The 694-pair regression and the S3/psalms + S9/genesis absences had the SAME cause — **I ran the addressing and
localization on 9 of the 13 `our-ocr-diplomatic` volumes.** `pdf-S03b`, `pdf-S04`, `pdf-S06` and
`archive-holiebible-ot1` were never touched, and S3's psalms live in `pdf-S03b`. 98% of the lost-and-passing
pairs (681 of 694) were "chapter outside every page's address interval" — the interval was empty because the
volume had no address records at all. All four now address at **100% coverage / 100% held-out** (249/249,
30/30, 151/151, 184/184). After re-localizing and re-auditing:

    lost pairs        4174 -> 215        lost-and-still-passing   694 -> 22
    S3 x psalms          0 -> 2512       S9 x genesis               0 -> 1498
    total scan-verse pairs 27,241 (detect) -> 27,751 (hybrid)  — a net coverage GAIN of 510, not a loss
    shared-pair pass rate 12.91% -> 52.42%

The 22 residual lost-and-passing are all "chapter addressed, verse not localized within it" — a small,
non-systemic tail, still OPEN. **Corpus addressing now covers 13 volumes / 16,081 pages / 1,865 held-out
labels, all at 100%.**

### B + C — THE SUB-0.2 SET IS **TWO POPULATIONS**, AND LUMPING THEM HID THE REAL CAUSE
4,442 locus×source records score archaic_id < 0.2 (psalms 2338 · matthew 747 · john 690 · genesis 452 ·
apocalypse 215). Splitting them by what the MODERN reference says about the same OCR separates them cleanly:

    POP-1  archaic<0.2 AND modern<0.2   1775 (40.0%)   floor_modern mean 0.8764   <- the two references AGREE
    POP-2  archaic<0.2 BUT modern>0.9   1535 (34.6%)   floor_modern mean 0.0080   <- the references CONTRADICT
           archaic<0.2, modern 0.7-0.9  1043 (23.5%)
           archaic<0.2, modern 0.2-0.7    89 ( 2.0%)

**`floor_modern` — which compares the two REFERENCES to each other, no OCR involved — is 0.876 for POP-1 and
0.008 for POP-2.** That is not a gradient, it is two different failure modes:

* **POP-1 is a genuine pipeline failure.** Both references agree about what the verse says and the OCR matches
  neither. This is the re-OCR ladder's actual work.
* **POP-2 IS A REFERENCE DEFECT BEING REPORTED AS AN OCR FAILURE.** The OCR agrees with janvier at >0.9 while
  the archaic reference agrees with janvier at 0.008 — **two independent readings agree against `s_dismas`,
  which makes `s_dismas` the outlier at that locus.** And the gate nonetheless governs on archaic for all
  1535, so it fails the verse. The split-axis counts confirm the asymmetry: **1660 records are
  modern>0.9 & archaic<0.8, against only 32 the other way — 52:1.** The archaic reference is the weak
  instrument, not the OCR.

**PROPOSED COMMON SOLUTION — USE `floor_modern` SYMMETRICALLY.** It already exists and already measures exactly
the right thing; it is simply applied in one direction only. Today a low `floor_modern` means "the modern
edition diverges, so trust archaic". It equally licenses "the archaic reference is misaligned here, so it
cannot govern a FAILURE verdict". The rule to add: **an archaic reference that disagrees with the modern
reference below a floor is not a valid yardstick for that locus** — report the locus as reference-unverified
and gate on modern, exactly as `gold_grid` now WITHDRAWS a per-verse label it cannot justify against janvier.
Same principle, same project, one level up. Expected effect: ~1535 verses stop being charged to the OCR.
**NOT YET IMPLEMENTED — this is a diagnosis and a proposal; the threshold needs calibrating and the change
must be measured before it is believed.**

### E — RED CHAPTERS: 271 -> **4**
Before Stage 1, 270 of 271 chapters had no passing scan. Now **4**, all psalms, all localized:

    psalms 17    best archaic 0.0000   structural — wrong/empty text (203 source-records, all localized)
    psalms 51    best archaic 0.8977   near miss
    psalms 92    best archaic 0.8525   near miss
    psalms 139   best archaic 0.8932   near miss

Three are near-misses inside 0.05 of the bar. **psalms 17 at 0.0 across 203 records with every source
localized is the POP-2 signature** (a reference defect, not 203 independent OCR failures) and should be
re-checked first under the symmetric-`floor_modern` rule.

## ✅ M17 STAGE 1 — THE WIRE-THROUGH IS DONE, AND THE REPORT MOVED (2026-07-27)
`qc_audit` now localizes the corpus with `page_address` + `verse_locate.best_spans` instead of
`detect_our_ocr.detect_book` (`LOCALIZER=hybrid`, `ODR_LOCALIZER=detect` reproduces the legacy operating
point). **NOTHING WAS RE-RECOGNISED** — the stored stream was already `reichenau_lat` output with per-line
bboxes; 2,653 pilot-book pages across 9 volumes localized in ~6 minutes, cached to `.corpus-localize-*.json`.

**THE REPORT'S OWN VERSION COMPARATOR NOW SAYS `IMPROVED` FOR THE FIRST TIME (v018 → v019):**

    pass_rate_archaic      0.1291 -> 0.5133      verse loci with >=1 passing scan   2129/6389 -> 4701/6411
    verse_cover_rate       0.3332 -> 0.7333      chapter loci                          1/271  ->   14/271
    source_fail_mean       0.8638 -> 0.4644      (apparatus flat, as it should be — untouched by this change)

**LIKE-FOR-LIKE, SO THE GAIN CANNOT BE A DENOMINATOR ARTIFACT.** The record count changed (27,241 → 23,741),
which on its own could inflate a pass-rate by dropping hard verses, so the comparison was made on the **23,067
locus×source pairs BOTH localizers attest**:

    shared pairs   pass 2818 -> 11908  =  12.22% -> 51.62%   ·   mean archaic_id 0.5167 -> 0.7623
                   materially better 15,582  vs  materially worse 914   (17:1)

**⚠ OPEN — A REAL COVERAGE REGRESSION, NOT ABSORBED. The hybrid attests 4,174 locus×source pairs FEWER than
`detect_book` did, and 694 of those were PASSING before.** A verse the old localizer found and the new one does
not is a loss whatever the aggregate says. It does not change the direction of the result (even crediting every
lost pair as a pass, the before-rate on the shared set is 12.2% against 51.6%) but it is a debt: those 694
belong on the worklist and the cause — most likely pages whose address interval excludes a chapter `detect_book`
reached by probing — needs diagnosis before Stage 2.

**WHAT THIS SETTLES ABOUT SIR'S CHALLENGE.** He was right that the report showed no progress, and right to
suspect the measurement layer. He was wrong that the work was empty: the component gains were real and
gold-anchored all along — **they had simply never been connected to the corpus the report scores.** The whole
distance between "no improvement at all" and `pass_rate_archaic 0.1291 → 0.5133` was one wiring job, plus the
addressing work that made it safe to do.

New: `corpus_localize.py`, `.corpus-localize-<volume>.json`, `qc_audit.LOCALIZER`.
Backup of the legacy audit: `coverage-audit-verse.json.detect-baseline`.

## ✅ M16 (1) PAGE ADDRESSING — EVERY PAGE ADDRESSED, BY MONOTONE ALIGNMENT (2026-07-27)
Sir: *"we want ALL pages to always be addressed as the correct book:chapter."* An UNRESOLVED verdict is a
safeguard for a trial run, never the deliverable — a page we cannot address is a page we cannot re-OCR.

**THE DESIGN: A VOLUME IS A SEQUENCE AND THE CANON IS ORDERED.** Per-page classification cannot reach total
coverage — a mid-chapter page prints no heading, a treatise page prints no scripture, two chapters read alike.
But chapter numbers never decrease as you turn pages, and that one constraint turns an ambiguous per-page guess
into a well-posed global alignment: line the page sequence up against the canonical (book, chapter) sequence.
**It is `verse_locate`'s monotone walk, one level up.** A page with no local evidence inherits its address from
its neighbours — what a human does when they flip back a leaf. All four hard cases fall out rather than needing
rules: mid-chapter pages continue the run · multi-chapter pages carry a SPAN (`chapter_ranges`) · chapter-less
pages are still addressed (`kind='no-scripture'` at the locus they sit inside — **"no scripture here" is an
ADDRESS, not a failure**) · an isolated wrong guess is outvoted by its neighbours.

    volume              pages   coverage   held-out chapter labels
    archive-ot2-1610     1128     100%      147/147
    archive-ot1-1609     1135     100%      156/156
    archive-nt-1582       762     100%       13/13
    jp2-S08               800     100%      148/148
    jp2-S04               764     100%       28/28
    jp2-S06              2872     100%       87/87
    jp2-S09ot2           1137     100%      229/229
    pdf-S03a             1137     100%      309/309
    pdf-S09nt             805     100%      134/134
    TOTAL              10,540     100%    1251/1251     · GT 16/16

**THE HELD-OUT DESIGN IS THE POINT.** Printed chapter headings are WITHHELD from the evidence, then used as
labels: how often does the DP independently recover the chapter the page actually prints? That is 1251 labels
across the corpus, gold-free — the evidence a 16-page GT set cannot supply.

### EXACT PINNING — tightened, and its CEILING measured rather than asserted
The interval says which REGION a page is in; `best_spans(book, chapter, line_range=)` needs to know which
chapter a given LINE belongs to, or every verse of both chapters competes for every position again (the §13 Q5
failure, at line grain). Two designs were built and the first was REJECTED BY MEASUREMENT:

  * **line-level content change-point DP** (the same monotone walk, one level down): landed within 2 lines of
    the true heading only **39.7%** of the time. A single line carries ~8 tokens and neighbouring chapters
    share vocabulary — the evidence is too thin at that grain.
  * **carry-chain from printed headings** — on the premise that the DR heads every chapter, so a page with no
    heading contains no chapter START. Correct for `CHAP. N` books, and **it collapsed on the Psalter**: psalms
    head `PSALME I.`, not `CHAP. I`, so the chain got stuck on one chapter for hundreds of pages (68%
    disagreement with the DP, GT 9/9 -> **1/9**). Rejected as a standalone chain.

**WHAT SHIPPED — headings pin exactly where they survive; the validated DP interval covers the rest.** The
heading matcher is now tolerant of the noise the recognizer actually makes on short display lines (`PSALηE I.`
reads as Psalm 1), and one matcher serves evidence, pins and held-out labels alike so they cannot disagree
about what the page prints.

    volume            exact line pins from a surviving printed heading    heading-vs-DP disagreement
    archive-ot2-1610            152/1128 = 13.5%                                  3.10%
    archive-ot1-1609            156/1135 = 13.7%                                  7.31%
    jp2-S08                     150/800  = 18.8%                                  6.50%
    archive-nt-1582              14/762  =  1.8%                                  1.05%

**THE HONEST CEILING: ~14% of pages carry a heading that survives OCR well enough to pin a line.** On the rest
the boundary is not printed-and-readable, and reporting a tight-but-wrong split would be worse than reporting
the small interval the verse localizer resolves within. Mean 1.95 chapters/page. That IS a usable Stage-1
input — two `best_spans` calls per page and the `janvier_fit` selector decides — but "every page pinned to
exactly one chapter" is NOT claimed. The remaining lever is verse-number anchors (`verse_numbers.recover`
already finds chapter-opening `N †`), which costs an olmOCR gutter read per page.

**FOUR DEFECTS FOUND BY MEASUREMENT, each of which had been silently corrupting addressing:**
1. **Content fit asked the wrong question.** It normalised by the CHAPTER's tokens (the chapter's recall by the
   page), so it failed systematically by chapter length: Psalm 118 (176 verses) scored 0.097 on its own page
   while short psalms scored ~0.19 on incidental words — **the model preferred short chapters regardless of
   what the page said.** Addressing is a PRECISION question (what fraction of THIS PAGE does the chapter
   explain); denominator switched to the page. p227 fit 0.097 → 0.449, and it now addresses correctly.
2. **A start-position prior of `-0.02·j`** reached −18 on a 900-position canon — an order of magnitude above
   any emission — so a slice legitimately beginning mid-volume was dragged to the front of the canon and the
   monotone constraint propagated that error through every following page.
3. **Book front matter had no legal position.** The DR prints a title/argument before chapter 1 of every book;
   with nowhere to sit, those pages pulled the path into Psalm 2 by page 12 and (staying being free) it sat
   there through p16, mis-addressing Psalm 1 whose own content scored 0.414 vs 0.175. Chapter 0 is now a real
   position. **Front matter is part of the book's sequence, so it needs a seat in the sequence.**
4. **THE COLOSSIANS-3 ROOT CAUSE, FOUND: `tome-map` claims archive-nt-1582 contains only matthew, mark and
   john — for a 765-page New Testament.** Luke, Acts, every epistle and the Apocalypse are absent. Seeding the
   state space from that coverage claim left 2john and colossians with NO LEGAL POSITION, so the addressing
   scored 0/2 there because it could not represent the right answer. The state space is now the CANON of the
   testaments the volume covers; tome-map is demoted to a per-page prior, where being wrong costs a little
   evidence instead of the answer. **`jp2-S08` p571 now addresses as colossians/3** — the page whose suspected
   mis-address has been the FLAGGED confound in every lift figure since 2026-07-22.

**A FIFTH DEFECT, CAUGHT BY THE REGRESSION TESTS I WROTE TO PIN THE OTHER FOUR.** `_emission` flattened a
page's score to a constant whenever `detect_regime` said `no-scripture` — **destroying a content fit of 0.88 on
a 40-token slice of Psalm 100.** The first guard (`n_body_tokens < 120`) was arbitrary: it is not length that
makes a page scripture, and the regime detector demonstrably mislabels real scripture pages (ot2-1610 p227
carries 381 body tokens of Psalm 118 and is called `no-scripture`). The guard is now on the EVIDENCE — "no
scripture here" means precisely "nothing on this page matches any chapter" (`best_fit < 0.20`). Re-validated
across four volumes after the change: coverage 100%, held-out 100%, **GT 16/16**.

All five defects carry regression tests (`tests/test_page_address.py`, 8 tests). **126 tests green.**
New: `page_address.py`, `page_address_eval.py`, `tests/test_page_address.py`, caches `.page-address-<volume>.json`.

## 🔴 M15 "IS GT-3 REALLY ONLY 15 PAGES?" — NO. AND THREE DIVERGENT REGISTRIES WERE HIDING IT (2026-07-27)
Sir asked. The answer is no, and the reason it looked like 15 is a defect, not a fact.

**TRUE GT INVENTORY (`gt_registry.audit()`): 50 files / 70 declared pages.**

    scripture   16 files /  16 pages /  8 distinct books
    matter      31 files /  51 pages /  4 volumes
    nt-*         3 files /   3 pages
    + 2 unreachable (no declared page) · 3 loci salvaged from the slug (malformed, flagged for a GT fix)

**Every lift number I have reported was measured on 15 of them.**

**THREE HAND-TYPED `LOCI` DICTS HAD DRIFTED APART, and each harness printed its own subset's number as "the"
number:** `gate_calibrate.LOCI` 14 (never saw 2john or colossians-3) · `reocr_lift.LOCI` 15 (never saw
abdias-01) · `r3_stats` inherits gate_calibrate's. **`scripture-abdias-01` is a completed, Sir-reviewed GT page
excluded from every lift figure I quoted, because a dict I hand-typed lacked one line.** The harness printed
`no book/page` and moved on — and **a skipped input that reports as a blank line is indistinguishable from one
that passed.** Same silent-degradation class the ledger exists to prevent, applied to the measuring apparatus.

**FIX — `gt_registry.py`: the registry is DERIVED from the GT files' own `locus` field, never hand-typed.**
An unmappable GT RAISES instead of being skipped. It caught three further defects immediately, which is the
point of failing loud: (1) `page_index` is a LIST on multi-page matter sections and a scalar on scripture;
(2) six loci did not match the expected form (three genuinely malformed `matter-nt-table` hyphen-loci —
salvaged from the slug and FLAGGED, not silently rewritten in Sir-reviewed files; three legitimate
`nt/marke/...#p104` fragment-loci my pattern was simply too narrow for); (3) **the GT writes `2john` while the
canon spells it `2-john`** — a plain dict lookup missed it and my first cut of the registry silently dropped
2john while restoring abdias, i.e. **I nearly replaced one silent drop with another.** Book tokens are now
resolved against the skeleton canon and an unresolvable book RAISES.

**EXCLUSIONS ARE NOW DECLARED, NOT ABSENT.** `gate_calibrate` deliberately holds colossians-3 out of the fitted
threshold (a known §4/§11 confound would corrupt a calibration). That is defensible; being *invisible* was not.
It is now `CALIB_EXCLUDE` with its reason, printed every run.

**CORRECTED LIFT (16 pages / 203 verses, was 15 / 191): base 0.7166 → R2 0.9173, pass-rate 40% → 68%**
(representative, confound excluded: 41% → 73%). The restored pages did not distort the figure — which is worth
saying plainly: **the numbers were right about the pages they saw, and wrong about how many pages that was.**
118 tests green; all self-checks pass.

## 🔴 M14 THE WIRE-THROUGH GAP — WHY THE REPORT SHOWED NO PROGRESS (2026-07-27, Sir's challenge)
Sir: "per the report it feels like we are working and working and getting nowhere." **He was right, and the
mechanism is specific.** Verified in code, not from memory:
- `qc_audit.py` — the authority behind EVERY headline number — reads its OCR from `sources/our-ocr-diplomatic`
  (via `detect_our_ocr.DIPL_ROOT`). `reocr_core.base_ocr` — the **"base" column of V9**, the one R2 beats by
  +0.204 — reads **THE SAME DIRECTORY**. The report has been showing the BEFORE state on 6438 verses and the
  AFTER state on 15 pages, and never joining them.
- `qc_audit.py` imports **ZERO** of `verse_locate`, `xsrc_gate`, `r3_route`, `s_arbiter` (grep count 0 each).
  Nothing writes R3/arbiter output back into the corpus stream. **The improved pipeline has touched 191 of
  6438 verses = 3.0%, and even those are not persisted.**
- The tier structure (A/B/C1/C2/D) measured INSTRUMENT READINESS, not corpus transcription. "All five tiers
  closed" was true and the deliverable had still not moved. M6 "Scale-out" — the only milestone that moves it
  — was parked as a REVIEW milestone. **That is the goalpost failure; own it.**

### `corpus_wire_probe.py` — MEASURED, and it REFUTED my own hypothesis
I predicted the lift was mostly **body-isolation** (droppable straight off the stored bboxes). Wrong. Three
arms, same 191 gold-anchored verses, same janvier-cut archaic-preeminent scoring:

    ARM1  base (the stream every headline scores)      mean 0.7213   pass  77/191 = 40%
    ARM2a stored + body-isolation only                 mean 0.7720   pass  82/191 = 43%   (25% of the lift)
    ARM2b stored + body-isolation + HYBRID LOCALIZER   mean 0.8724   pass 115/191 = 60%   (74% of the lift)
    ARM3  live-R2 (re-run kraken per page)             mean 0.9256   pass 130/191 = 68%

**THE LOCALIZER IS THE LEVER, NOT THE RECOGNIZER OR THE ISOLATION.** Body isolation alone buys 3 points of
pass-rate; adding `verse_locate.best_spans` buys 17 more. And **74% of the entire live-R2 lift is recoverable
from what is already on disk, with ZERO re-recognition** — the corpus stream was already produced with
`reichenau_lat` and every stored line carries a `bbox`. The residual 26% needs the kraken re-run (fresh
segmentation + preprocessing: autocontrast, and upscaling for the low-res 800px sources).

**CAVEAT, STATED NOT BURIED:** these are 15 GOLD pages — curated, and the pages I built the localizer against.
Corpus-wide behaviour is not established by this probe; the wire-through IS the test. The relative direction
transfers; the magnitude does not, and the corpus base rate (`pass_rate_archaic` 0.1291) is far below the gold
pages' 40%, so no corpus number should be predicted from these.

## ✅ M13 TIER D — THE DELIVERABLE RENDERED: REP-2/4/5 + AUDIT RE-RUN + COMPLETENESS PASS (2026-07-27)
Report **v018** (`reocr-report-pilot.html`). Three new sections; the version comparator's own verdict on the
first of them was **"NO EMPIRICAL CHANGE (PRESENTATION-ONLY)"**, which is the correct reading — Tier D adds
EVIDENCE to the report, it does not move a single audited number.

**REP-2 + REP-4 — V9 "Re-OCR stream ladder", the only GOLD-anchored figure in the report.** `reocr_lift.py` now
persists `reocr-lift.json` and joins the whole ladder onto one grid: base → R2 → R3 (`.r3-stats/`) → ſ-arbiter
(`.s-arbiter/`). Every other figure is witness-anchored (what production can do at runtime); this one is scored
against the Jarvis diplomatic gold for that very page, which is the only place the reOCR mandate can be
*verified* rather than asserted. **base 0.7213 → R2 0.9256 (+0.204), pass-rate 40% → 68%** over 191 verses on
15 pages; representative (confound excluded) **0.7211 → 0.9308, 41% → 73%**. The lift harness now reads
`.page-cache`, so the whole figure rebuilds offline. `colossians-3` stays FLAGGED and pink-striped in the table
with its reason inline (base 0.7245 → R2 0.0 — multi-chapter GT page + body-isolation dropping the gold
content, NOT recognizer quality). **A false BAD is reported as loudly as a false good.**

**REP-5 — V10 "Matter as first-class books". The V7 mismatch RECONCILED: they were never the same artifact.**
V7 renders `coverage-audit-apparatus.json` (s_dismas front/back-matter *slot* coverage); REP-5 asks for the 30
curated *matter sections* scored as books, which lives in `matter-scoring-summary.json`. Both are now rendered,
each labelled with its own grain, instead of one being mistaken for the other. **110 rows (30 sections × their
testament's curated sources): 105 located, 3 at or above the 90% bar, 107 flagged and held OPEN.** The honest
headline is that matter fails as badly as scripture's baseline did — same mandate, different body of text. The
`own` source (the one the GT was transcribed from) is scored like any other and given no credit.

**V11 — the OPEN ledger is now IN the report.** 38 blocking units with rungs-tried, best score, reference and
reason per row. Previously the thing that blocks the deliverable was a JSON file no reader of the report saw.

**⚠ A RENDERING BUG THAT READ AS "NOTHING IS BLOCKING" — found and structurally fixed.** Five not-located matter
rows carry no scores at all; `sc.para[0]` on `undefined` threw, and because `renderAll()` called every section
in one unguarded sequence, **the exception silently deleted V11 — the OPEN ledger — from the rendered page.**
A report that drops its own blocking list because of an unrelated crash is the worst failure mode this project
has. `renderAll` now isolates each section in try/catch and logs the failure; not-located rows render the
ABSENCE explicitly (`not located`, `n/a`) instead of being dropped or scored as zero.

**PRODUCTION AUDIT RE-RUN — reproduces EXACTLY.** `qc_audit.py` re-run over the full pilot scope (6438 verses,
190s). The output file's bytes differ (key ordering) but a recursive value-by-value diff against the pre-run
artifact finds **zero differences**, and every headline metric is flat to 4 dp. The audit is deterministic.

**COMPLETENESS REVIEW — PASS.** `validate_completeness.py`: oracle 76 books / 1360 chapters, **zero
zero-attestation books, zero low-confidence-only books, zero chapter gaps**, exit 0.

**STILL OWED (flagged, not attempted — none is a Tier D gate):** colossians-3 ADDR-2 page verification (C1
leftover; it is the one FLAGGED confound in V9) · `verse_numbers.verse_opening_lines` keys on † so the NT
numeral regime recovers 0 numbers · the 9.1% `unmatched` regime-sweep pages want new block types · **the
38-entry ledger BLOCKS the deliverable and is the real remaining work.**

## ✅ M13 TIER C2 — ſ-FAITHFUL ARBITER: 17 of 21 ſ DEBTS CLOSED BY OBSERVATION; 4 WERE CONTENT BUGS (2026-07-27)
**118 tests green** (+20), all seven module self-checks pass. New: `s_arbiter.py`, `s_arbiter_run.py`,
`tests/test_s_arbiter.py`. Cache `.s-arbiter/` (texts + crops + verdicts — the olmOCR cost is paid once).
**OPEN ledger 55 → 38.** Pre-arbiter ledger kept at `.r3-stats/_open_ledger.json`; new one at
`.s-arbiter/_open_ledger.json`, so the two side by side show the debts closed by observation, not by a moved bar.

**THE METHOD — SURFACE TRANSFER, THEN A BOUNDED VISUAL RESIDUE.** `restore_long_s` is ~90.4% on our own gold, so
publishing it would present ~1-in-10 INVENTED glyphs as the printed surface; the arbiter never calls it. Instead:
R2 (kraken/reichenau_lat) IS an ſ-faithful recognizer — only its CONTENT was rejected — so a token R2 and R3 read
identically modulo the ſ-fold has content R3 confirms and a surface R2 OBSERVED. Adopt it. Only where R3
*corrected* R2 is the ſ unattested. **That reduced 21 verses to 21 residue tokens over 8 crops**, which I read
in-session off the rendered jp2 (NO paid API). Every emitted glyph carries provenance: R2-observed /
vision-observed / no-decision. The alignment fold is ſ-ONLY — folding u/v, i/j or case would let a token R3
corrected register as "agreeing" and hand the deliverable R2's rejected reading back.

**⚠ FINDING 1 — olmOCR DOES NOT ONLY FLATTEN ſ→s; IT ALSO MISREADS ſ AS f.** Measured on this debt set:
`haiſt`→`haift`, `anſwere`→`anfwere`, `deſpiſed`→`despifed`, `pleaſeth`→`pleafeth`, `ſixe`→`fixe`. An f-token
carries no s-glyph, so an s-only detector calls it settled and **ships a wrong surface silently** — the
confident-wrong class one level below the gate, and invisible to the ledger's ſ-count test. `decision_positions`
now treats medial `f` as an open decision. It over-reports on genuine f (`fountaine`, `therefore`) — the right
direction of error: a false residue costs one look at the crop, a missed one corrupts the deliverable.

**⚠ FINDING 2 — THE ſ-DEFICIENCY BASELINE WAS CHARGING THE VERSE FOR MARGINALIA.** The debt opens on
`r3_ſ < r2_ſ` over R2's whole line band, which interleaves apparatus R2 read and R3 correctly excluded (`on
Eaſter eue.`, `his Iuſt balancedo`, the `The Ghoſper` running note INSIDE Matthew 28:16). Those ſ are not verse
material, and charging them made closure unreachable for a reason unrelated to the surface — **8 of 21 debts sat
in that state.** The baseline is now the RETAINED material (`delete` blocks dropped; within a `replace` block,
an R2 token is retained only if some R3 token in the block matches its skeleton ≥0.6, which separates the
correction from the intruded note); what was dropped is REPORTED, never silently discounted. ALERTs 8 → 0.

**⚠ FINDING 3 (THE IMPORTANT ONE) — READING THE CROP FOR ſ EXPOSED 4 TOKEN-LEVEL CONTENT MISREADS THAT THE
VERSE-LEVEL GATE ABSORBED.** Each verse scored ≥ τx overall, so one wrong word rode through:

    abdias 1:3     'layst'   should read 'ſayſt'    (olmOCR read the initial ſ as l)
    matthew 28:2   'satte'   should read 'ſate'
    proverbs 16:22 'foolcs'  should read 'fooles'   (e read as c)
    genesis 16:6   'affliet' should read 'afflict'  (ct ligature read as et; the ff is a genuine double-f)

Publishing a tidy ſ on top of a wrong word is the worst available outcome, so these **re-open on the CONTENT
axis** (`CONTENT_OPEN`, new terminal state) and stay in the ledger with the misread named. **This is a general
result about the gate's GRAIN, not four incidents: a per-verse threshold cannot see a single bad token in an
otherwise good verse.** The four were found only because the surface work forced a per-token visual read.

**RESULT — 17 CLOSED, 0 unresolved on the surface axis, 0 ALERT, 4 CONTENT_OPEN.** The ſh/sh inconsistency that
caps positional restoration at ~90% was confirmed directly on the page: proverbs 16:21 prints `shal` and
`ſweete` in the same line, round s before h and long ſ before w. Observation was the only way to get that right.

## ✅ M12 SPRINT — TIER A DONE, TIER B DONE, C1 DONE (2026-07-27)
**89 fast tests green** (+4), all self-checks pass.

### TIER A1 — verse numbers recovered corpus-wide, and the honest limit on using them
`build_verse_numbers.py` caches gutter reads to `.verse-numbers/` (olmOCR, 372s for 14 pages, cached
thereafter). **145 verse openings → 58 numbers read (40%) → 45 ACCEPTED (31%)** after monotonicity + chapter
vetting. Recovery is regime-dependent exactly as the grammar predicts: psalms/genesis pages give 60-88%,
while **abdias (0/11) and proverbs (0/21) give nothing because those pages print no numbers** — the module
reports absence instead of inventing. matthew gave 0 crops because `verse_opening_lines` keys on the dagger;
the NT numeral regime needs its own opening detector (its numbers already survive in the OCR, so this is a
completeness gap, not a loss).
- **⚠ ANCHORS MUST NOT REWRITE SPANS (measured, pinned).** Using accepted anchors to correct verse starts made
  things WORSE: known-bad **24 → 45**. A lone anchor moves ONE verse's start without moving its neighbour's,
  leaving the two spans mutually inconsistent. The anchor is right about its own verse and SILENT about the
  rest; using it for spans needs a joint re-solve (all verses re-placed subject to all anchors at once), which
  is not built. Anchors therefore drive the ALARM only and do not touch the output.

### TIER A2 — recall=1 RESTORED, and the alarm it was built for turned out not to be needed
Built alarm 5 (`xsrc_gate.anchor_disagreement`): a span that contradicts its own printed verse number — the
one signal about IDENTITY rather than quality, invisible to all four content alarms. Then measured the target
case and found **the gate was right and the REFERENCE was wrong**: psalms-118 118:109's span is verbatim
janvier 118:109; `gold_grid` had handed v109 the text of v103 on that under-marked page.
- **FIX AT THE INSTRUMENT:** `gold_grid` now WITHDRAWS any label scoring <0.35 against janvier. The gold is my
  own transcription, so a segment reading as a different verse is a labelling error, not a bad verse; the
  verse is reported unbuilt with a reason rather than published wrong. 4 labels withdrawn corpus-wide.
- **RESULT — the §7 gate gate is MET again:** four alarms, fair reference, **recall 1.000 at τx=0.90 → 24%
  escalation, 18 false alarms** (was 33%/13 on the biased reference, and 26% with one verse missed).
- **ALARM 5 IS KEPT BUT DEFAULTED OFF, on measurement:** with it, recall 1.000 @ **40% escalation, 44 false
  alarms** — 16 points of escalation for zero additional catches, because its precision is bounded by 31%
  anchor recovery and its firings are dominated by sparse anchors, not real disagreements. The failure class
  is real and this gold set contains no instance of it; turn it on when recovery improves.
- Fair-grid segmentation after the instrument fix: **hybrid 0.9629 mean, 143/165 pass, oracle == hybrid,
  worsened 0, p<0.00001**.

### TIER B — regime coverage across ALL SIX curated sources (33 pages, live kraken)

    ot-dagger 20 · nt-numeral 7 · no-scripture 3 · UNMATCHED 3 = 9.1%
    S1 {nt-numeral 3, ot-dagger 6} · S3 {ot-dagger 6} · S4 {nt-numeral 3}
    S6 {nt-numeral 1, no-scripture 1, unmatched 1} · S8 {ot-dagger 1, no-scripture 1, unmatched 1}
    S9 {ot-dagger 7, no-scripture 1, unmatched 1}

**THE NT QUESTION IS ANSWERED WITH A NUMBER: the numeral regime is NOT S1/Matthew-specific — it appears in
S1, S4 and S6, on 7 of 33 sampled pages.** So a regime detected on one book does extend across editions, which
is the property the grammar was designed for. **9.1% unmatched is the honest coverage gap** — the sweep
reports it rather than forcing those pages into the nearest regime, which is exactly the signal Sir asked for.
`no-scripture` fired on 3 pages, confirming that treatise/matter pages are recognised as carrying no verse
text instead of having verses forced onto them. Cached in `.regime-sweep/` (re-runs free).

### TIER C1 — multi-chapter pages (§13 Q5, colossians-3)
`block_grammar.chapter_ranges()` reads chapter headings (`CHAP. IIII`, roman or arabic) and returns per-chapter
line ranges; `verse_locate.best_spans(..., line_range=)` honours them. `verse_seg.segment`'s documented
contract ("split the body by chapter first and call once per chapter") had NO caller honouring it, so on a
straddling page every verse of both chapters competed for every position — the runaway the walk exists to
prevent, reintroduced at page level. Now available; the colossians-3 ADDR-2 page verification remains.

### NOT REACHED IN M12 (C2 has since been closed in M13, above)
**D** REP-2/4/5 + production audit + report artifact + completeness review — unblocked, unchanged in scope.

## ▶ NEXT SPRINT — AUTONOMOUS TARGETS (queued 2026-07-27, awaiting Sir's go)
Full tiering + gates in `REOCR-MASTER-PLAN-2026-07-22.md` §12.5 (rev 4). Ordered by dependency, each tier
gated so a failure ALERTS for redesign rather than being absorbed.

| tier | work | gate | risk |
|---|---|---|---|
| **A1** | wire `verse_numbers.recover` → `block_grammar.dispatch` → segmenters (self-labelling anchors) | psalms detect as `psalm-numbered`; fair-grid mean + pass reported | low — parts built & tested |
| **A2** | **FIFTH ALARM**: span disagrees with its own PRINTED verse number | recall=1 restored on the fair reference, escalation cost reported | med — may need redesign; ALERTs if so |
| **B1-3** | regime breadth across 6 curated sources × layout modes (supersedes SEG-1/2) | every source×mode detects a regime or is `unmatched` WITH a reason; **NT uniformity answered with a number** | med — unknown unknowns are the point |
| **C1** | §13 Q5 colossians-3: ADDR-2 verify + chapter-split multi-chapter pages | colossians-3 unblocked or evidenced | low |
| **C2** | ſ-faithful in-agent arbiter (~21 ſ-surface debts, in-session vision, NO paid API) | debts closed or itemised in the ledger | med |
| **D** | REP-2/4/5, production audit re-run, report artifact, COMPLETENESS REVIEW | curated-clean per-verse + guard + matter, rendered & verified | med — the deliverable |

**OUT OF SCOPE, flagged not attempted:** M4 recognizer retrain (REVIEW milestone; depends on GT that Tier B
may still change — retraining now risks doing it twice) · Sir-only GT calls (NT roman-lowercase `w` RATIFY;
summe-of-nt p29 re-review) · the full GT-3 matter/layout sweep (a bounded slice is in scope: abdias vv13-21 +
one gold per missing source S3/S4/S9).

**CARRIED OPEN INTO THE SPRINT:** gate recall <1 on the fair reference (1 known-bad invisible to all four
alarms) · 55-entry OPEN ledger blocking the deliverable · psalms-118 fair grid builds only 6 of 12 verses.

## ✅ M11 COMPOSABLE BLOCK GRAMMAR + VERSE-NUMBER RECOVERY + PAGE ALARM (2026-07-27)
Four new modules, **94 tests green** (15 new), all six module self-checks pass.

**`verse_numbers.py` — the numbers ARE recoverable (measured, olmOCR).** kraken's line polygons start at the
dagger, so the printed number sits outside the recognized line: across the 14 cached gold pages an `N †`
opening survives in the OCR exactly ONCE. It is not being stripped — it is never being read.
- **MEASURED CROP GEOMETRY:** a bare digit sliver recovered **0 of 7** openings on psalms-118 (a vision model
  given two glyphs and no context returns nothing). The same crops widened to carry the opening words
  recovered **5 of 7 read, 3 ACCEPTED** — `105`, `110`, `111`, all correct against the page image. The number
  is isolated afterwards from the token before the dagger; the context is what makes it legible at all.
- **GLYPH-CONFUSION IS SAFE HERE:** `III †` (111) and `1c9 †` (109) are read as numbers because POSITION
  already guarantees the token is one. The same substitutions on free text would corrupt words.
- **REFUSAL, NOT REPAIR:** two misreads (v2, v1 after v111) were REFUSED by the monotone check. A wrong verse
  number relabels a correct span with confidence — strictly worse than no number.

**`block_grammar.py` — regimes, not books.** 12 shared block types; markers classified as SELF-LABELLING
(`N.` NT-1582, `N †` psalm-numbered) or positional (bare †); geometry separates continuation from annotation
because they move in OPPOSITE directions (a wrap is indented FURTHER, an annotation LESS and to the full
measure) — the distinction the symbol-only prototype could not make, which is why it destroyed proverbs.
`compose()` folds lines into runs (a verse absorbs its wraps). `dispatch()` returns regime + schema.
- **`no-scripture` IS A FIRST-CLASS DETECTION**: ot2-1610 p216 sits INSIDE the Psalm 118 range and carries no
  verse text at all (the General Annotations treatise). The schema returns `segmenter: None` — do not attempt
  verse localization — instead of forcing verses onto a treatise and then reporting failure.
- **`unmatched` IS REPORTED, NEVER FORCED.** An unseen book either matches a regime or is flagged. This is the
  anti-over-fitting property: book identity is a PRIOR, never a key.
- Detected on the 14 gold pages: nt-numeral ×1, ot-dagger ×13 (psalms-118 is ot-dagger and NOT psalm-numbered
  **because its numbers were never OCR'd** — recovery must run BEFORE dispatch to unlock the stronger regime).

**`coverage_alarm.py` — the page-level "is the grammar failing?" signal.** Distinct in grain from `xsrc_gate`:
a per-verse gate cannot raise it, because a misfired grammar makes EVERY verse look individually bad and the
gate escalates all of them to a rung that cannot help. Reports RECALL (did we FIND the verses the references
place here → suspect the REGIME) and FIDELITY (does what we found READ like the chapter → suspect the
RECOGNIZER) **separately**, because they demand opposite remedies.
- **MULTI-REFERENCE, AND IT MATTERED IMMEDIATELY.** Scoring against one witness reported a correctly-read page
  as catastrophic: `s_dismas` gives 2-Esdras 7 **70** verses where `sabates_a`/`madueke_b` give **73**, so our
  v27 was compared to a different verse — **fidelity 0.064**. Consulting every source that covers the locus
  and keeping the best gives **0.889**, and the spread is reported as a REFERENCE-numbering divergence rather
  than blamed on the page. That is the most expensive class of false alarm, now designed out.
- **LOW-EVIDENCE GUARD:** a chapter with <3 verses on the page cannot support a page-level verdict (every page
  boundary would cry wolf); those verses stay gated per-verse. Result on the gold pages: **3 alarms of 17
  chapters** — 2 reference-numbering divergences, 1 genuine low-fidelity page.

**NOT YET RUN — the NT breadth question.** The instrument for "does the Matthew regime extend evenly across
the NT?" is now built (regime detector + `unmatched` reporting + the page alarm), but it has only been run on
the 14 gold pages. Running it across an NT page sample is the next step and requires no new machinery.

## ✅ M10 PSALM 118 VISUAL INSPECTION + GEOMETRIC APPARATUS VARIANTS (2026-07-27)
Rendered and read ot2-1610 pp215-236 directly (`.ps118-render/`, pdftoppm @130dpi — the PDF is 178MB, over
the 100MB text-extraction limit, so it must be rasterised first).

**THE FINDING THAT EXPLAINS THE psalms FAILURES — WE DELETE THE STRONGEST MARKER BY ASSUMPTION.**
Psalm 118 prints its verse number INLINE, immediately before the dagger: `14 † I am delighted...`,
`15 † I wil be exercised...`. Psalm 119 (p234) prints the number in the RIGHT MARGIN instead. **Either way the
DR body DOES number its verses — and the number is SELF-LABELLING**, the strongest marker class we have (an
off-by-one becomes impossible). But `layout.strip_verse_numbers` deletes exactly these tokens, documented on
the assertion that "the DR body marks verses with † / ‡, **never digits**" — which the page disproves. On the
psalms-118 gold page the numbers survive NOWHERE: not in the OCR body, not in the GT transcription.
**So every alarm is downstream of a body text that had its best boundary signal removed before any alarm ran.
That is why nothing caught 118:109: the gate is not weak there, it is blind to a signal we discarded.**

**PAGE STRUCTURE (Ps 118, p219) — the composable block vocabulary:**
  verse opening `N †`, inset from the measure · verse CONTINUATION indented FURTHER (hanging indent) ·
  ANNOTATION starting LEFT of the verse block and running the FULL measure, keyed by an italic letter ·
  STANZA HEADING (centred, short: "Gimel. Fulnes.") every 8 verses (the acrostic) · marginal notes BOTH sides.
p216 inside the Ps-118 range carries **NO scripture at all** — it is the "General Annotations" treatise
(Hebrew-letter tables, two-sided margins). p234 composes six block types on ONE page: section heading,
treatise, psalm heading, italic argument, rubric, drop-cap verse, annotations.

**GEOMETRIC APPARATUS VARIANTS — MEASURED, NO VARIANT BEATS THE BASELINE (negative result, pinned).**
`apparatus_geom.py` (6 variants: left-edge, right-edge, AND, OR, marker-anchored, marker-anchored +
continuation protection) scored end-to-end vs the FAIR gold by `apparatus_eval.py`:

    baseline 0.9561 (146/170) | v3 -0.0014 | v6 -0.0162 | v1/v5 -0.0383 | v2 -0.1199 | v4 -0.1573

Only 2 pages gain anything (psalms-115-116 +0.012, psalms-074-p138 +0.009). **The earlier prototype's promise
(ps115-116 ch116 0.500 -> 0.985) was measured against a much weaker baseline: the hybrid localizer has since
SUBSUMED apparatus handling** — `drop_apparatus` plus the walk's unclaimed-run residue already exclude
annotation text. Apparatus removal is therefore NOT the remaining lever; the missing verse NUMBERS are.

## ✅ M9 FAIR PER-VERSE GOLD GRID — the reference was the bug (2026-07-27)
Built `gold_grid.py`: the gold is now cut into verses at the PRINTED VERSE MARKERS instead of by
`verse_seg.segment` (the incumbent aligner). **Every M7/M8 per-verse number was measured on a grid the
incumbent produced**, which charged every boundary-word disagreement to the challenger.
- **THE DR PRINTS THREE DIFFERENT CONVENTIONS** — the first hard evidence for book-specific schemas:
  OT 1609/1610 (genesis/proverbs/psalms/2-esdras) marks verses with **†** (positional only); NT 1582
  (matthew) uses **arabic numerals "2."** which are **SELF-LABELLING** (the marker carries its own verse
  number, so an off-by-one is impossible); abdias prints **no marker** (one verse per line); psalms-118 is
  **under-marked** (4 † for 12 verses).
- **`†` IS OVERLOADED** — it opens a verse AND serves as an intra-verse annotation reference. Counting
  daggers therefore does NOT cut a page: one intra-verse dagger in genesis-24 shifted every label by one
  (mean janvier identity **0.051** — the "gold" was reading v15's text as v14's). Fix: boundaries come from
  the print (a verse never runs through a marker unremarked), LABELS come from a monotone DP that may merge
  consecutive pieces, scored by janvier identity. Janvier never decides WHERE a verse ends — only WHICH
  printed segment is which verse, and a wrong labelling is detectable because identity collapses.
- Three further defects found and fixed by the same self-check: a **discardable leading fragment** (a page
  opens mid-verse; forcing that tail onto the first tagged verse corrupted it — genesis 16:10 gold 0.67 while
  the gate saw xsrc **1.00**, i.e. the REFERENCE was wrong, not the OCR), **repair for missing markers**
  (matthew 28:17 ran into v18), and **continue-past-unrepairable** (psalms-118 built 5 of 12 when the loop
  stopped at the first failure). All 17 chapters now build LOSSLESS; inferred boundaries are COUNTED.

**RE-MEASUREMENT ON THE FAIR GRID — the hybrid never loses a verse:**

    reference grid          align mean   hybrid mean   hybrid pass   worsened   Wilcoxon
    aligner-cut (legacy)        0.9215        0.9548     147/177=.83         11    p=0.00007
    FAIR (printed markers)      0.8979        0.9480     143/169=.85    ****0****  p<0.00001

The oracle EQUALS the hybrid (selector captures **100%** of available gain). **The entire "honest cost" of
M7/M8 was an artifact of the reference.** genesis-16-p082, the headline regression (reported 8/8 → 6/8), is
on the fair grid **4/7 → 6/7, an IMPROVEMENT**. NEXT item 2 ("close the selector cost") is therefore CLOSED:
there is no cost to close.

**⚠ OPEN ALERT (No Silent Degradation) — recall is NOT 1.0 on the fair reference.** Recalibrated:
hybrid 24 known-bad, **23 caught at τx=0.90, 1 MISSED** (psalms-118 118:109, gold 0.0 but xsrc 0.985, conf
0.973 — invisible to all four alarms); align **5 MISSED**, including the genesis/proverbs verses previously
attributed to the hybrid as its "cost" — they are ALIGN's failures that the gate cannot see. The previously
reported "recall=1 @ 33% escalation" was partly an artifact of a reference that mislabelled which verses were
bad. This stays OPEN and blocks: the approach needs a fifth alarm, not a lowered bar.

## ✅ M9b LAYOUT FINGERPRINT — regime detection is GOLD-FREE and PREDICTIVE (2026-07-27)
`layout_profile.py` computes a per-page fingerprint from the recognizer's own output only (line text +
bboxes): dagger/numeral/star fractions, short-line fraction, indent spread, right-edge raggedness,
lines-per-verse. Measured on the 14 gold pages:
- **`right_ragged` separates prose from verse-per-line/poetic setting with a clean gap and NO overlap**:
  2-esdras 0.039, abdias 0.052, genesis 0.117–0.145 | psalms 0.44–0.72, proverbs 0.46. matthew is separated
  first by `numeral_frac` 0.42 (the NT regime).
- **The fingerprint PREDICTS which segmenter wins** — poetic pages take the anchor-walk 39% of the time and
  gain +0.072 mean; prose pages take it 22% and gain +0.047. So dispatching a page to a fitted schema is
  buildable on signals available at runtime, which is the prerequisite for the book-specific program.

## ✅ M8 HYBRID LOCALIZATION WIRED INTO PRODUCTION — flagged set −21%, recall STILL 1.0 (2026-07-27)
M7's `best_spans` was built, measured and then left unconsumed. It is now the production segmentation: ONE
localization per page feeds BOTH the gate and the crop geometry. **70 fast tests green (79 with slow).**
Four defects were found while wiring, each by measurement, each fixed and pinned:
- **DEFECT A — the walk EMITTED the alignment fold.** `verse_seg._afold` is documented "for ALIGNMENT only
  (never emitted)": it lowercases, folds ſ→s, v→u, j→i, y→i and collapses doubled letters. `locate` returned
  `" ".join(folded)` as the verse text — i.e. handed the diplomatic pipeline a modernized, case-flattened
  reading, destroying the exact surface this project exists to preserve. Now matches on the fold, emits the
  raw page tokens. **Effect: walk arm 0.8598 → 0.8760, HYBRID 0.9488 → 0.9548, passing 143 → 147, selector
  capture of the oracle gain 80% → 87%.**
- **DEFECT B — two coordinate systems under one key.** `verse_seg` publishes `tok_lo/tok_hi` in RAW body-token
  space; the walk published FOLDED indices (punctuation dropped). `best_spans` mixed both, so any geometry
  consumer would have read the wrong pixels. Both now publish RAW; `page_tokens` returns the bridge.
- **DEFECT C — geometry from the LOSING engine.** `verse_seg` emits no `lines`, so `best_spans`' fallback
  ("use the walk's lines if the winner has none") fired on EVERY align-sourced verse: winner's text, loser's
  pixels. Now resolved from the selected span's own extent. Nothing consumed it yet; regression-pinned.
- **DEFECT D — the walk was NOT REPRODUCIBLE.** `_seed_positions` ranked seeds with `sorted(SET, key=df)`;
  set-of-strings iteration is randomized per process (PEP 456) and a df-only key leaves ties broken by that
  randomness. Two identical sweeps of the same cache gave psalms-118 walk 0.811 vs 0.747. A result that will
  not reproduce cannot be held to a threshold. Fixed with a TOTAL order (tie-break on the token), verified
  identical across 4 PYTHONHASHSEEDs. **Fixing the seed would have hidden it, not removed it.**

**GATE RECALIBRATION (13 gold pages / 177 verses, both engines on IDENTICAL cached inputs):**

    engine    known-bad   recall @ τx=0.90   escalation   false-alarms
    align            46            1.000            33%             13
    hybrid           30            1.000            27%             18

**21 verses left the known-bad set because they were LOCALIZATION failures, not misreads** (several at a hard
0.000 — never located at all): abdias 1:2,1:3 · proverbs 16:9,10,12,25 · psalms-001 1:4,1:6 · psalms-074 73:23,
74:1,74:4 · psalms-115-116 115:2,3,6 · psalms-118 118:108,114 · psalms-150-p265 149:2,3,5,6,7. Recall stays 1.0
— **No Silent Degradation held: the flagged set shrank because fewer verses are bad, not because the bar moved.**
**HONEST COST — 5 verses newly known-bad** (genesis-16-p082 16:15,16 · proverbs 16:21,22 · psalms-001 1:5).
All 5 still ESCALATE, so none is laundered; R3 then re-read 16:15 → **1.00** and 16:16 → **0.984**.
`gate_calibrate.py` is now cache-aware (`cached_page`) and engine-switchable (`--engine=align|hybrid`), so the
two operating points are comparable on identical inputs instead of across two differently-built runs.

**MEASURED REJECTION, PINNED — a switching margin does NOT fix the cost.** The obvious remedy (make align the
default, require the walk to beat it by δ) was swept: δ=0.005–0.01 changes nothing, 0.02–0.05 is flat-to-worse,
0.10 loses a verse, 0.20 costs 11. The bad switches have fit gaps of **0.07–0.13** — far above any usable
margin — so no threshold separates them. `switch_margin` is kept as a parameter (default 0.0) with the sweep
recorded. Trailing †/‡ trimming was also measured: **exactly zero** rows change (archaic_id already folds
non-alphanumerics), so the dagger is not the cost driver either.

**R3 RE-RUN ON THE NEW FLAGGED SET (real olmOCR, 14 pages, 366s — was 448s):** R3's ceiling ROSE, exactly as
the M7 handoff predicted it would once mislocated spans stopped being routed as OCR failures.

    metric                                    align-gate (2026-07-25)   hybrid-gate (2026-07-27)
    flagged verses                                        65                        56
    truly-known-bad among them                            46                        30
    content pass-rate (≥0.90 vs gold) after R3       0 → 50%                   0 → 63.3%
    positive-lift verses                              26/46                     22/30
    accepted verses WORSE vs gold than R2                  0                         0

**THE SAFETY RESULT SURVIVES THE CHANGE: of 21 accepted verses, 0 are worse vs gold than R2** — every olmOCR
failure stayed OPEN. Gate precision vs gold 0.625; ſ-deficiency 45/56 (80%), the residual owed to the arbiter.
OPEN ledger holds 55 (30 xsrc<τx-after-R3, 21 ſ-surface, 4 no-geometry) and BLOCKS the deliverable.
Artifacts: `.gate-calibration.json` (hybrid) · `.gate-calibration-align.json` (baseline) ·
`.gate-calibration.json.pre-hybrid-20260727` · `.r3-stats/` · `.r3-stats.pre-hybrid-20260727/` ·
`.r3-stats-hybrid-run.log`.

**⚠️ FINDING THAT LIMITS EVERY NUMBER ABOVE — THE GOLD REFERENCE IS CUT BY THE INCUMBENT.** Per-verse gold is
built as `verse_seg.segment(gold_text, janvier)` — the ALIGNER. So align-vs-hybrid is scored on an
align-shaped grid, and boundary disagreements are charged to the challenger. Demonstrated on the headline cost
case: the gold cut puts "Eightie" at the END of genesis 16:15, but janvier's v16 begins "Eighty" — **the word
belongs to v16, the walk places it there, and is scored WORSE for being right.** Therefore the measured hybrid
gain is a **LOWER BOUND** and part of the 5-verse "cost" is a measurement artifact. The fair reference is
buildable: GT lines carry verse tags and the printed text carries † at each verse start (10 of 14 gold pages;
abdias and matthew-28 have none and must degrade to alignment). **This is now the top NEXT item — it changes
every number in this sprint, so it comes before further selector tuning.**

## ✅ M7 ANCHOR-WALK VERSE LOCALIZATION — +6.8pp PASS-RATE, GOLD-FREE (2026-07-26)
Built Sir's "find the verse on the page, then read it there" proposal. `verse_locate.py`: use janvier (which
tells us WHAT each verse says) to find WHERE it sits, via seeded local matching + an exact monotone DP over
(verse × candidate window), then reverse-look-up the geometry. **72 tests green (63 fast + 9 slow).**
- **RESULT (13 gold pages, 177 verses, per-verse archaic_id vs gold, all offline via `.page-cache`):**
  incumbent global-align **0.9215 / 131 pass** · anchor-walk alone 0.8598 / 127 · **HYBRID `best_spans`
  (per-verse gold-free pick) 0.9488 / 143 pass = 0.808** · oracle (gold pick) 0.9553 / 150.
  **+6.8pp absolute pass-rate, Wilcoxon p=0.004 (30 improved / 15 worsened), 80% of the oracle's gain.**
- **Selector = `janvier_fit`** (span identity vs the janvier verse it claims to be) — gold-free, same standing
  as `xsrc_gate`'s witness. It cannot certify diplomatic fidelity but strongly detects a span pointed at the
  WRONG PLACE, which diverges from janvier far more than spelling variation does. Chosen: walk 52 / align 125.
- **HYBRID, not replacement — they fail in different places.** Global align wins on clean prose (long
  unambiguous blocks); the walk wins where align degenerates: psalms-074 ch74 **0.000→0.943**, psalms-150-p265
  ch149 **0/8→5/8 pass**, psalms-115-116 ch115 5/9→8/9, psalms-118 8/12→10/12, abdias 0.794→0.946.
  **RUNAWAY SPANS ELIMINATED** (M6 defect 3: the 53/47/39-line "verses" are gone).
- **HONEST COST:** genesis-16-p082 8/8→5/8 (0.998→0.943) — selector mistakes where the incumbent was already
  near-perfect. First thing to attack (require a switching margin, or add the †/layout-mode signal).
- **THREE BUGS FOUND BY MEASUREMENT during the build** (each a full re-measure, not a guess): (1) **trim
  BEFORE the walk** — monotonicity was enforced on the padded 2.2× search window so every verse blocked its
  successor, **84/177 not-located**, mean 0.42 → 0.824 once fixed; (2) **give the unmatched text back** —
  anchoring on MATCHED tokens and stopping there strips the verse of exactly its divergent wording (the text
  we want); expand into the unclaimed gap budgeted by still-unmatched janvier tokens (+0.026); (3) **IDF
  weighting is LOAD-BEARING** — 2-Esdras 7 is the census list ("the children of <name>"), unweighted matching
  aligned the scaffolding across verse boundaries and v53 lost its position to v54 entirely. This is Sir's
  "book-specific pattern" point solved GENERICALLY: it protects any genealogy/litany/psalmic parallelism with
  no per-book rule.
- **MEASURED PARAMETER REJECTION (pinned):** letting a verse reclaim text proportional to its own length
  (theory: editions ADD words janvier lacks) degrades identity MONOTONICALLY — 0.0→0.860, 0.10→0.809,
  0.15→0.782, 0.25→0.700, 0.40→0.654. The gap material is APPARATUS, not verse expansion. `expand_pad`=0.0.
- **APPARATUS FALLS OUT FREE:** unclaimed token runs are returned with their line indices — already the input
  to the "found and bound, then chunk the residual" step.
- **NOT YET WIRED:** `best_spans` is built/tested/measured but no consumer uses it. Next: wire into
  `xsrc_gate`/`reocr_core`/`verse_geom`, re-run gate calibration + `r3_stats` (better segmentation should
  shrink the flagged set AND raise R3's ceiling — several "R3 failures" were mislocated spans).

## ✅ M6 R3 CROP GEOMETRY — LEVER CLOSED BY MEASUREMENT (2026-07-26)
Drove handoff lever 1 ("layout-aware column-band crops for psalms — the BIGGEST lever") to a definitive
**negative result**, plus one real fix and a new evidence-backed lever. Full report:
`R3-GEOMETRY-VARIANCE-FINDINGS-2026-07-26.md`. **60 tests green (51 fast + 9 slow).**
- **The handoff's causal hypothesis was WRONG.** Psalms pages are mostly SINGLE-column (left-edge histograms);
  the real signature was 13 verses at an exact **0.000** — a hard zero (no span recovered), not degraded
  quality. Hypothesis refuted from line geometry before any code was written.
- **DEFECT 1 (FIXED, TDD):** `body_column` medianed over ALL body lines, but DR psalms set short italic gloss
  fragments flush-right INSIDE the text block, and they are the MAJORITY of the line count — dragging the
  left edge into the scripture column and clipping the opening of every full line (psalms-001 x0 **0.310 vs
  true 0.161**, 15% of page width of scripture cut off). Fixed to full-measure lines only. Containment
  0.456→0.675. Justified on DETERMINISTIC geometry, **not** on score (see below).
- **R3 IS VARIANCE-LIMITED, NOT GEOMETRY-LIMITED** (new harness `r3_variance.py`, 4 label-preserving crop
  variants that only GROW the box). Chaos term: gold-score spread across variants of the SAME region **mean
  0.271, max 1.0, >0.3 on 13/46**; FLAT across region size (refutes "whole-page crops cause the chaos").
  Selection: single-run accept 0.435 → best-of-4 argmax-by-witness 0.457 → medoid 0.457, **ORACLE (best of 4
  chosen WITH gold) 0.543**. Best-of-4 buys ONE verse in 46 and the oracle ceiling still fails 46%. **No crop
  strategy can close psalms** → No Silent Degradation: redesign the METHOD, threshold stays.
- **DEFECT 2 (INVESTIGATED → REVERTED, pinned negative result):** clipping to a MEDIAN x1 means half the
  lines overflow by construction (containment 0.456; genesis-24 0.21). Raising to a q=0.90 envelope lifts
  containment to **0.949** — and scored **WORSE**: 4-variant paired mean **0.6875→0.6631, 18 worsened vs 5
  improved, Wilcoxon p=0.018**, acceptance unchanged. The seductive argument ("over-inclusion is recoverable,
  the P5 cut discards unaligned material") is **empirically false** — the admitted material is the interleaved
  annotation apparatus and the cut does not discard it. Two durable lessons pinned in code + tests:
  **containment is NOT a proxy for quality**, and **over-inclusion is NOT free**.
- **DEFECT 3 (OPEN):** verse localization degenerates at page boundaries — psalms-150-p265 ch150 v1 absorbs
  **53 lines / 0.74 of the page**; ch116 v1 47 lines; ch74 v1 39 lines. A 53-line band is not a verse band.
- **NEW LEVER (Sir's proposal, measured & backed):** symbol-conditional, apparatus-aware segmentation.
  Nothing in the pipeline uses †/‡ (they appear only in COMMENTS); all segmentation is janvier alignment.
  (a) **† is recovered near-exactly** — proverbs 21 vs 21 †, psalms-150-p265 10 vs 10, psalms-074-p137 11 vs
  11 (matthew-28 has 0 † → any rule must degrade to alignment, not fail). (b) **Sir's layout distinction is
  gold-free detectable** — †-line fraction 0–2/41 (paragraph: genesis/2esdras/abdias) vs 6–17/40-60
  (verse-per-line: psalms/proverbs). (c) † alone is WORSE (boundaries right, content polluted — annotation
  lines are role='body' and interleave). (d) **Apparatus removal is where the value is**: a crude filter gave
  psalms-115-116 ch116 **0.500→0.985**, psalms-150-p265 ch149 0.808→0.931, genesis-24 0.956→0.973 — but
  over-drops on proverbs (0.943→0.337) because verses WRAP onto indented continuation lines carrying no †.
  That wrapped-continuation case is the design work to do.
- **DO NOT RE-ATTEMPT:** wider/enveloped crops; best-of-N crop selection. Both measured, both closed.
- **Methodology note for any future A/B here:** a single olmOCR run CANNOT resolve a geometry change (prose
  pages whose column moved <0.001 moved up to 0.25 in score). Use the 4-variant mean + Wilcoxon.

## ✅ M5 R3 PRODUCTIONIZATION — verse→crop geometry + load-once server + OPEN ledger + TDD (2026-07-25)
Drove the §8 R3 "STILL OWED" tail to a tested, end-to-end-validated finish (main-thread, autonomous). The gate
now ROUTES: flagged verse → pixel band → olmOCR re-read → re-score → terminal state → OPEN ledger. All new code
is TDD'd (pytest suite, **46 tests: 37 fast + 9 slow**, `ocr-venv` now carries pytest; `pytest.ini` isolates the
suite from the parent palimpsest xdist config).
- **CODE-REVIEW PASS (adversarial subagent, 2026-07-25) — 2 HIGH + 3 MED + 1 LOW found & FIXED, all regression-
  guarded.** Both HIGH were "report-success-while-degraded" gaps: **HIGH-1** `reocr_page` pre-resolved a single
  page-wide τx, forcing archaic 0.90 onto modern-fallback verses → silently under-escalated the [0.90,0.92)
  band; fixed to pass `taux=None` (axis-aware) through, matching `rescue_page`. (The `r3_stats` validation called
  the gate directly with axis-aware τx, so the reported numbers are unaffected.) **HIGH-2** one `transcribe()`
  failure in `rescue_flagged`'s region loop aborted the whole page — discarding already-scored regions AND
  dropping the failed region's verses with no ledger trace (MLXWorker timeout path is unconditional → live on
  any slow crop); fixed to contain per-region + ledger-OPEN + continue. **MED**: ledger provenance tracks the
  best attempt; `MLXWorker` RLock; `region_crops` single-column assumption documented. **LOW**: R3 temp PNGs →
  project-local `.r3-tmp`. Core logic (geometry mapping, P5 janvier-cut re-scoring, gold-free contract) SOUND.
- **`verse_geom.py` (NEW, §8 R3-4 crop geometry):** maps a flagged janvier verse → its body-line indices →
  union pixel bbox → fractional crop, reconstructed from a `reocr_page` result (no image re-seg). `verse_crops`
  (per-verse), `region_crops` (contiguous flagged verses → ONE body-column-clipped crop), `group_contiguous`,
  `body_column`. NO-SILENT-DEGRADATION guard: reconstructed body text must match stored `r2_body` or it RAISES;
  a verse that localizes but has no geometry is an explicit OPEN, never dropped. `verse_seg.segment` now emits
  `tok_lo/tok_hi` (raw-token extent per verse) — the bridge; additive, validated numbers unchanged.
- **`mlx_client.py` + `mlx_ocr_server.py` (NEW, §8 R3-1 load-once):** olmOCR loaded ONCE, served over stdin/
  stdout JSONL; reader-thread+queue gives timeout-safe reads; self-heals (respawn-on-death, one-shot retry);
  per-request ERROR raised (never a silent empty transcript). `mlx_ocr.py` split into `load_model`/`run`/
  `transcribe`. `reocr_r3._r3_mlx` uses the worker by default (`reload_per_call=True` = one-shot fallback).
- **`open_ledger.py` (NEW, §7 terminal / §8 R3-5):** the OPEN worklist — dedupes by locus, keeps the highest
  (still-sub-τx) score, unions rungs tried, BLOCKS the deliverable while non-empty. `reocr_batch` writes
  `_open_ledger.json` per run.
- **`r3_route.py` (NEW): the router** — gate scores + region crops → 1 olmOCR pass/region → **janvier-cut the R3
  blob** (P5 linchpin) → score verse span → terminal state. Two axes kept separate: CONTENT (xsrc, ſ-blind —
  what olmOCR lifts) vs ſ SURFACE (vs ſ-faithful R2 — olmOCR modernizes ſ). States: RESCUED /
  RESCUED_CONTENT_S_OPEN (ſ owed → arbiter) / OPEN.
- **Wiring:** `reocr_core.reocr_page` attaches per-line `bbox`; `reocr_batch(run_r3=True)` routes flagged verses
  via `r3_route.rescue_page` (verse-targeted, was whole-page), accumulates the OPEN ledger, shuts the worker.
- **CRITICAL FINDING (fixed):** first e2e scored 0/5 — a MEASUREMENT bug, not R3 failure. The crop spans a
  verse ± neighbours so olmOCR returns a multi-verse blob; comparing the blob to a single-verse ref craters to
  0.0. Fix = **janvier-cut the R3 output first** (the same P5 "cut both sides on one grid" the whole system
  rests on). Region crops (contiguous verses, body-column-clipped) beat per-verse (cleaner cuts, no margin bleed).
- **E2E VALIDATED (genesis-24, real olmOCR, region-based, 38s / one model load + 2 region crops):** the 5 gate-
  flagged verses `{12,27,28,29,30}` route correctly — **content RESCUED on 3/5 with real lift: v27 0.884→1.00,
  v28 0.777→0.967, v29 0.876→0.990**; all 3 are ſ-deficient (olmOCR drops ſ) → RESCUED_CONTENT_S_OPEN (ſ surface
  owed → Claude arbiter); v12/v30 stay OPEN (genuine cross-page fragments). OPEN ledger holds all 5, blocks the
  deliverable. **Nothing laundered** — content-recovery and ſ-surface debt reported separately.
- **STATISTICAL VALIDATION DONE (`r3_stats.py`, 13 gold pages, 65 flagged verses, real olmOCR, 448s):** measured
  the R3 content lift GOLD-ANCHORED (archaic_id vs gold — truth) AND gold-free (vs witness — production). On the
  46 truly-known-bad: **content pass-rate (≥0.90 vs gold) 0 → 50%**; olmOCR is HIGH-VARIANCE (bimodal): **prose
  R2 0.749→R3 0.862 (+0.113, 76% pass) vs psalms R2 0.734→R3 0.428 (−0.305, 28% pass)** — the 2-col apparatus
  wrecks generic olmOCR, dragging the raw mean to −0.114 (median +0.077, 26/46 gain). **THE SAFETY RESULT (No
  Silent Degradation, empirical): of 23 ACCEPTED verses, 0 are worse vs gold than R2** — every olmOCR failure
  stayed OPEN; the witness-based gate (psalms witnesses defective) laundered NOTHING. ſ-deficiency 52/65 (80%).
  Report: `R3-PRODUCTIONIZATION-REPORT-2026-07-25.md`. Gold-free witness Δ (−0.104) tracks gold Δ (−0.114) →
  proxy validated. Artifacts: `.r3-stats/`, `.gate-calibration.json` (177 verses, recall=1 @ τx0.90, 33% esc).
- **OPEN / next:** (1) **layout-aware crop geometry for psalms (R3-4, biggest lever)** — column-band crop per
  mode (the run pinpoints psalms as the failure; harness ready to prove any fix); (2) ſ arbiter rung
  (backend='claude') to close the 19 RESCUED_CONTENT_S_OPEN ſ-debts; (3) GT-3 breadth (labor tail, Sir-review).
  Files: `verse_geom.py`, `mlx_client.py`, `mlx_ocr_server.py`, `open_ledger.py`, `r3_route.py`, `r3_stats.py`, `tests/`.

## ✅ GT REVIEW TOOL FIXES + CORRECTIONS FOLDED (2026-07-23)
Sir reported two tool bugs + a design question while reviewing matter sections; all resolved:
- **Issue 3 (broken raster)** FIXED: `gt_review_server.py` `/raster` crashed with TypeError when `raster` was a
  LIST (multi-page sections store a list of paths) → broken-image icon. Now restricts the pre-rendered fast-path
  to actual `.png` strings and falls through to on-demand jp2→PNG render for all else. Verified: explication,
  argument-of-genesis, brief-recapitulation, summe-of-old-testament all render 200 PNG.
- **Issue 2 (multi-page sections)** DECIDED + BUILT — **Option A: show the whole section across ALL its pages,
  page-aligned.** `/raster?page=<pi>` renders any declared page (validated); `gt_review.html` stacks one labeled
  image per page and tags each body line with its `page`. Makes "not-on-page" obsolete. Verified: summe-of-nt
  serves p28 AND p29; undeclared page→404.
- **Corrections folded** (`gt_apply_corrections.py`, +No-Silent-Degradation guard): summe-of-nt applied the "to
  wit" edit but **DEFERRED L44–54** (all page 29, marked 'not-on-page' only because the old tool hid p29) as
  `needs_rereview` — NOT excluded (would have destroyed valid p29 content). signification + censure edits applied.
  books-of-nt was an empty submission (no-op). **Sir: re-review summe-of-nt p29 with the fixed tool (11 lines).**

## ✅ M5 GATE — CROSS-SOURCE ALARM WIRED + CALIBRATED (2026-07-23)
The §7 confidence gate was proven self-report-BLIND (conf recall=1 → 88% escalation; confident-wrong tail
40/40 uncaught by internal alarms). **FIXED:** built `xsrc_gate.py` (alarm 2 = R2 vs the reference-witness
cascade, janvier-cut, archaic-preeminent, GOLD-FREE), extended `gate_calibrate.py`, and wired it into
`reocr_core.reocr_page(locus=(book,chapter))` + `reocr_batch(locus_map=…)`.
- **Result:** mean xsrc known-bad **0.714** vs good **0.936** (separates; conf's gap was 0.008). FULL gate
  **recall=1 on all 43 known-bad at τx=0.90 → 34% escalation** (vs conf's 88%), 0 blind spots. Confident-wrong
  tail **40/40 caught**. E2E gold-free `reocr_page(genesis-24, locus=…)` recall **4/4** (vv27–30 + fragment v12).
- **Verified:** all self-checks PASS; calibrator reproduces identical numbers pre/post DRY refactor (calibrator
  + production share `xsrc_gate` — no drift). Independent re-derivation from `.gate-calibration.json` confirms.
- **R3-1 backend DONE (olmOCR-2 via MLX):** qwen3-vl:8b was thinking-locked/empty → replaced by **olmOCR-2-7B**
  (`mlx-community/olmOCR-2-7B-1025-bf16`) in an isolated `ocr-mlx-venv` (mlx-vlm 0.3.12 + transformers==5.1.0;
  5.2.0 has a Qwen2.5-VL video-processor bug). `mlx_ocr.py` ← subprocess ← `reocr_r3._r3_mlx` (default backend).
  **VALIDATED end-to-end: olmOCR-crop beats R2 on ALL 4 genesis-24 flagged verses** (archaic_id: R2 0.69–0.88 →
  R3 0.90–1.00). Loop on full pages → crop/bands fix it. **ſ finding:** olmOCR modernizes ſ on crops (content
  rung, not diplomatic-surface); ſ-faithful surface = Claude arbiter; `restore_long_s` = labeled ~90% utility.
- **GT-3 + axis-aware τx DONE (this connects Unit 2 → the gate):** modern-fallback τx **CALIBRATED** — the gate
  is now axis-aware (`xsrc_gate`: **archaic τx=0.90 / modern-fallback τx=0.92**). Confirmed on the first GT-3
  archaic-gap gold **`scripture-abdias-01`** (Abdias 1:1-12, archive-ot2-1610 p840; all 12 verses modern-axis, 3
  known-bad incl. 2 confident-wrong caught). Full calibration now 177 verses / 46 known-bad, recall=1 at 33%
  escalation. Abdias is live in the review tool for Sir.
- **OPEN / next:** (1) R3 productionization — verse→crop geometry (map flagged verse → pixel band via kraken
  bboxes) + `mlx_vlm.server` (load-once) + wire `run_r3=True`; (2) **GT-3 breadth (labor tail)** — abdias vv13-21
  (p841), S3/S4/S9 source-coverage gold (SIR-DIRECTIVE §2.1), matter/layout coverage. Draft via olmOCR content +
  Jarvis ſ-correction → push to the fixed review tool. Files: `xsrc_gate.py`, `gate_calibrate.py`, `reocr_core.py`,
  `reocr_r3.py`, `mlx_ocr.py`, `long_s_rule.py`, `ground-truth/scripture-abdias-01.json`.

## 🔄 MAIN-THREAD COMPLETION RUN 2026-07-21 (Sir: NO sub-agents; do ALL work here, in series, to FINAL)
Sir authorized a fresh 5h session to finish everything in the MAIN thread (no delegation, disregard spend).
Jarvis is doing all rendering + visual transcription directly (render jp2 → rband.py column bands → read → build GT).
**29/33 matter GT done.**
  1. ✅ table-of-epistles-nt → S8 pp773-776 DONE (matter-nt-table-of-epistles.json: 213 rows, 210 intervals, 356 ſ,
     core round-trips clean). Also hardened glyph_map (added ū→u macron; was only ũ). 2026-07-21.
  2. ✅ table-of-certaine-places DONE (matter-nt-table-of-certaine-places.json: 135 intervals = 22 book-headings
     + 110 corruption entries + title/subtitle/closing; 482 ſ; clean core). CORRECTION: it is NOT at S8 pp722-728
     (that's the Apocalypse argument) — it is the "A TABLE OF CERTAINE PLACES / HERETICAL CORRVPTIONS" appendix in
     **S1 archive-nt-1582 pp722-728** (S8 hi-res set lacks this appendix). p724 folded from existing matter-nt-table.
     S1 is a low-res 800px scan → italic w/vv below per-glyph threshold (flagged). 2026-07-21.
### ✅ COMPLETENESS GAPS DONE (2026-07-21): summe-and-partition +p17 tail (pages 15-17, RESOLVED);
  books-of-new-testament +p26-27 patristic catena (pts 3,4,5 + Augustine/Tertullian/Hierom/Vincentius/Baſil,
  pages 25-27, RESOLVED, 56 intervals). Both clean core round-trip.
### 📍 SECTION 5 LOCATED (continuance-of-church): it is "THE CONTINVANCE OF THE CHVRCH, AND RELIGION IN THE
  SIXTH AGE" — a LONG (~14pp) dense-italic apologetic treatise at **S1 archive-ot2-1610 pp988–~1001** (running
  header "CONTINVANCE OF THE / CHVRCH AND RELIGION" thru p1000; a genealogy/3rd-booke section follows by p1004;
  Historical Table = pp1077-1100). matter-ot2-backmatter.json already = its OPENING page (p988, header + treatise
  start, drop-cap S "SVCH is the prouidence…"). "Continuance of the Church" recurs at many S6 loci (6-age series)
  → that scatter caused the resume's 1961/1969-vs-941 confusion; the sixth-age back-matter one anchors at S1 p988.
  TODO: extend matter-ot2-backmatter with pp989-1001 (single wide column, roman/italic alternating). Not a quick win.
### ✅ DELIVERABLE SECURED (Sir chose "secure deliverable first", 2026-07-21):
  - **E5b**: matter_match_report.py enhanced — ~20-word WINDOW-grain PARA pool + interval-grain APPARATUS pool
    (score_para_windows / score_pools). Self-test GREEN. glyph_map hardened: ū→un, legend marks ⁘ ⊣ stripped.
  - **E**: matter_scoring_run.py scored all 30 matter GT × their testament's curated sources →
    matter-scoring-summary.json. Honest baseline: 102/105 located source-rows below 90% → reOCR-flagged
    (mirrors scripture: coverage-audit-verse.json = 6438 verses / 271 chapters all in shortfall).
  - **FINAL**: qc_audit.py all ran (scripture coverage). Matter completeness+scoring AUDIT ARTIFACT published:
    **https://claude.ai/code/artifact/47533001-7aa9-42cf-a944-f0f887004e67** (30 books, pools, OPEN items, log).
  - Build scripts durable in ocr-spike/.scratch/ (build_matter_audit_artifact.py, matter_scoring_run.py).
**REMAINING TRANSCRIPTION** (main-thread; per Sir's plan these come AFTER the secured deliverable; may end
  partial-but-honest — mark OPEN, never fake):
  3. particular-table → S6 pp2049-2068 (20pp alphabetical index; hi-res 5100px). **PARTIAL/OPEN**: pp2049-2051
     DONE (matter-ot2-particular-table.json: title + 2 intro notes + letter A Aaron→Aureola + letter B start
     Baal→Bleſſing, 55 entries, clean core). pp2052-2068 (rest of B→Z, tail LAVS DEO) REMAIN. NOTE recto/verso
     column shift: recto R col needs x~0.455 (else first chars clip). builder=.scratch/build_matter_ot2_particular_table.py
  4. ample-and-particular-table → S8 pp776-798 (HUGE alphabetical index; starts bottom of p776 after the rule)
  5. continuance-of-church → S6, RE-VERIFY location (grep 1961/1969 vs agent-at-941); long treatise, scope extent first.
Then: completeness-gaps (p17-tail, books-nt p26-27) → E5b (window-grain scoring) → E → F → FINAL audit + report V3.
(Original pre-/clear checkpoint preserved below.)

## ⏸ PRE-/CLEAR CHECKPOINT 2026-07-21 — resume via `.claude/context/.resume-prompt.md`
**28/31 matter GT done.** Agents BLOCKED: **monthly spend limit** hit (raise at claude.ai/settings/usage) + session limit.
Efficient agents (few-bands, write-to-file) work once unblocked — verified (censure/faults-escaped/etc. done lean ~27-33 tools).
**5 REMAINING** (all near-complete but died before writing — RETRY, exact pages, ⚡efficient, ONE agent each):
  1. table-of-epistles-nt → S8 pp773-776   2. table-of-certaine-places → S8 pp722-728 (="Table of Controversies")
  3. particular-table → S6 pp2050-2067 (was on final p2067)   4. ample-and-particular-table → S8 pp776-798 (HUGE; NO sub-split — /tmp collisions)
  5. continuance-of-church → S6, RE-VERIFY location (grep 1961/1969 vs agent-at-941); long treatise, scope extent first.
Then: completeness-gaps (p17-tail, books-nt p26-27) → E5b (window-grain scoring) → E → F → FINAL audit + report V3.

## Phases (efficient order)
- **D — matter-books** (~22 sections) + the NEW matter-INTERVAL coordinate system (paragraphs/rows) for
  mask-inventory + gold thresholds. Transcribe (agents, emit `intervals[]`), QC (localization/identity/
  placement/completeness), align/insert.
- **C — S9 Psalms remedial**: resolve localization/coord/accuracy causing broad S9-Psalms OCR failure.
- **F — stratified resample** per Inclusion Rules (all sources ≥1 page, all pages ≥2 sources, all books +
  matter represented); verify OCR (localization/coord/layout/accuracy); resolve blockers.
- **E — complete scoring**: extend gt_match_report to matter intervals (E5b) + all newly included/remediated
  pages; fold into build_reocr_report V3 html.
- **FINAL**: production audit (qc_audit all, curated+aligned+matter) → regen report Artifact → completeness review.

## Matter interval design (implemented in MATTER-AGENT-BRIEF.md)
`intervals[] = {idx, kind, text, lines[]}`; kind ∈ title_block/heading/subtitle/paragraph/table_row/
list_item/colophon_line. Coordinate `matter/<slug>/<idx>`. Scoring = align source OCR → GT intervals
(reuse align_coords.realign at interval grain), % intervals edit_ratio≥0.90 (E4/E5a analog). Agents emit
intervals from visible paragraph breaks (reliable). Existing 11 GT: derive/annotate intervals + scorer-validate.

## Matter section worklist (✅ have · ⏳ dispatched · ☐ todo · source)
### OT1 (S1 archive-ot1-1609, 1609 first ed.)
- ✅ Title Page · ✅ Approbatio · ✅ To the Right Wellbeloved (matter-ot1-preface)
- ☐ The Summe and Partition (front, ~p48) · ☐ The Summe of the Old Testament (front)
- ☐ Of Moyses (front, ~p18) · ☐ The Argument of Genesis (front, ~p19) · ☐ The Signification of the Markes (front, ~p20)
- ☐ A Brief Recapitulation (BACK, ~p1085-1135)
- (matter-ot1-colophon exists — verify which section it is)
### OT2 (S1 archive-ot2-1610, 1610; 1635-tagged → S6 jp2-S06)
- ✅ Title Page · ✅ Proemial Annotations (matter-ot2-preface-psalms) · ✅ Table of Epistles (matter-ot2-table-epistles)
- ☐ Approbatio (front) · ☐ Concerning Interpretation (front)
- ☐ Continuance of the Church (1635→S6, back) · ☐ An Historical Table (back) · ☐ A Particular Table / Chiefe Contents (1635→S6, back)
- ☐ Censura trium Theologorum (back) · ☐ Faults Escaped in the Printing (1635→S6, back) · ☐ Extraict du Privilege du Roi (1635→S6, back)
- (matter-ot2-backmatter exists — verify which section it is)
### NT (S8 jp2-S08 hires 1582 for 1582 sections)
- ✅ Title Page · ✅ Preface to the Reader (matter-nt-preface)
- ☐ The Censure and Approbation (front) · ☐ The Signification or Meaning (front) · ☐ The Summe of the New Testament (front) · ☐ The Books of the New Testament (front; verify vs matter-nt-table)
- ☐ The Explication of Certaine Words (back) · ☐ A Table of Certaine Places (back) · ☐ A Table of the Epistles (NT, back) · ☐ An Ample and Particular Table (back) · ☐ Faults Escaped in the Text (back)

## SESSION-LIMIT PACING (2026-07-20) — 2nd window exhausted, resets 5:50am Denver
Hit the session token limit AGAIN at cap 2 (~9 heavy agents/window ≈ 2M tok). Main-loop still works.
Windowed pace: ~8-9 matter agents per 5h window; ~16 sections left = ~2 more windows. Background waiter set
(~50min) to retry agents after reset. Recovery: concerning-interpretation WAS written (valid) before its stall;
brief-recapitulation NOT written → RETRY after reset (pages 1128-1131, distinct from p1132 colophon; header "OF IOB",
body "perſeuering conſtant in vertue…", ref "1.Tim.3"[content 2Tim3:12]).
**Matter GT done so far: 18/31.** Remaining: brief-recapitulation(retry) + OT2{historical-table p1077-1100,
censura, continuance/particular-table/faults-escaped/privilege-du-roi in S6 ~p2050-2140} + NT(9, locate first).
Non-agent TODO while blocked: E5b scorer pools (para vs apparatus split), p17-tail cleanup (render p17), F prep.
**E5b GRANULARITY FINDING (2026-07-20)**: matter-scorer FUNCTIONAL (flags reOCR: of-moyses/summe-of-OT vs S1 =
✗0%, honest baseline — raw matter OCR far from gold, like scripture). BUT paragraph-grain intervals are too COARSE
for the 0.90-per-interval bar (300-word paragraphs accumulate OCR error → always fail). For verse-comparable
%-threshold COHERENCE (Sir's ask), the E-phase must score at a finer grain: ~20-word WINDOW within each paragraph
(sentence-split is unreliable — abbreviation periods 'S.Aug. li.2.'). Keep paragraph intervals[] as the
inventory/localization unit; add window-grain scoring for the % metric. Apparatus pool (citation/gloss/marginalia)
scored COMBINED = E5b. matter_match_report.py: split SCORE_KINDS → PARA vs APP pools + window scoring (E phase).

## OT2 dispatch page-hints (located 2026-07-20)
- Approbatio → S1 archive-ot2-1610 front (~p2-14; DISPATCHED a9b9e4028d81d0799)
- Concerning Interpretation → S1 archive-ot2-1610 front (~p3-15; self-locate)
- An Historical Table → S1 archive-ot2-1610 BACK ~p1077-1100
- Censura trium Theologorum → S1 archive-ot2-1610 BACK ~p1030-1100 (near Historical Table)
- Particular Table / Chiefe Contents (1635) → S6 jp2-S06 ~p2050-2067
- Extraict du Privilege du Roi (1635) → S6 jp2-S06 ~p2071
- Faults Escaped in the Printing (1635) → S6 jp2-S06 ~p2090
- Continuance of the Church (1635) → S6 jp2-S06, self-locate in ~p2040-2140 region (or earlier; scattered)
- NT dispatch (S8 jp2-S08, 800pp; headers OCR poorly so hints are weak — self-locate in region):
  FRONT ~p2-40: Censure-and-Approbation (~p2), Signification-or-Meaning (~p8-30), Summe-of-NT (self-locate front),
  Books-of-NT (self-locate front). [Preface=matter-nt-preface, Title=matter-nt-title already have]
  BACK ~p760-800: Explication-of-Certaine-Words (~p765-799), Table-of-Certaine-Places (~back), Table-of-Epistles-NT
  (~back; distinct from OT2 table-epistles), Ample-and-Particular-Table (~p760-800, LARGE multi-page index/table),
  Faults-Escaped-in-the-Text (~back). NOTE verify Books-of-NT vs existing matter-nt-table (may be the same).

## ⏸ CHECKPOINT — PAUSED 2026-07-20 (session tokens 94%; Sir: interrupt/gather/checkpoint/wait)
**MATTER GT DONE: 22/31.** Both agents stopped cleanly. Resume = re-dispatch below at cap 2.
### 🔴 CRITICAL S6 DECODE FIX (discovered by privilege-du-roi agent)
`jp2_page.py`/PIL fails on EVERY S6 (jp2-S06) page ("broken data stream" — systematic PIL/decoder failure, NOT
page corruption). **Render S6 pages with `opj_decompress` (OpenJPEG)**, not jp2_page.py/PIL. Add this to future
S6-agent prompts (particular-table, continuance). (S6 page 2071 is genuinely truncated 1198B/blank — after privilege.)
### OT2 remaining (3) — corrected page map (from privilege agent's back-matter survey)
- particular-table → S6 ~p2050-2067 (agent reached p2063 before stop; RETRY, use opj_decompress). S1 has a 1610
  counterpart alphabetical index @archive-ot2-1610 p1101-1125 (edition nuance — flag for Sir).
- faults-escaped → S6 **p2070** (the "FAVLTS ESCAPED IN THE PRINTING" errata page; privilege box sits at its FOOT).
  (My earlier ~p2090 hint was WRONG — NT title begins S6 p2072, so OT2 ends ~2071.)
- continuance-of-church → S6, self-locate (longer apologetic section; ~p2040 or earlier; use opj_decompress).
- S6 OT2 back-matter order: …index tail "LAVS DEO" 2068 · Censura(Latin) 2069 · Faults-Escaped+Privilege 2070 ·
  blank/corrupt 2071 · NT title 2072.
### NT remaining (9) — S8 jp2-S08, hints recorded above (front ~p2-40, back ~p760-800).
### Post-matter: E5b window-grain scoring + apparatus pools; p17-tail cleanup (summe-and-partition); F resample; FINAL audit.

## NT FRONT structure recovered (from killed agents, 2026-07-20 eve) — S8 jp2-S08 indices
- Preface-to-Reader = idx23 (have=matter-nt-preface) · **Signification-or-Meaning = idx24** (heading "THE
  SIGNIFICATION OR MEANING OF THE NVMBERS AND MARKES vſed in this Nevv Teſtament"; single page, sig "d",
  catchword "THE") · **Books-of-NT = idx25** ("THE BOOKES OF THE NEVV Teſtament"). Censure-and-Approbation ~p2.
  summe-of-nt located in front (heading "NEW", display-VV). 
- **EFFICIENCY LESSON (Sir killed 3 NT agents for over-working)**: short single-page matter sections do NOT need
  the heavy iterative crop/zoom analysis used for dense scripture. Re-dispatch LEAN: render the page ONCE at full
  res, read it directly, minimal targeted crops only for genuinely ambiguous glyphs. Give EXACT page indices.

## COMPLETENESS-GAP CLEANUP LIST (batched, before FINAL — render spill pages + extend)
- summe-and-partition: final paragraph tail on TOP of OT1 p17 (before "SVMME OF THE OLD TESTAMENT").
- books-of-new-testament: patristic catena continues p26–27+ (points 3–4 Augustine/Tertullian/Hierom); p25 core done.
- (grep all matter GT for "continues"/"TRUNCATED"/"out of scope"/"would need" notes to find others.)

## Progress log
- 2026-07-19: Phase D START. Interval design + agent brief written. Batch 1 (OT1: 6 sections) DISPATCHED (opus agents):
  - a1eaeba9441bcd2c3 = summe-and-partition · aa727dcd57d3ed4ef = summe-of-old-testament
  - a3e7ffd752f7e1d0f = of-moyses · a67e3a5a794a7b341 = argument-of-genesis
  - a91ce34457a45dd40 = signification-of-the-markes · abff2e6158a75394d = brief-recapitulation
  Harvest each on completion (harvest_newmode-style: last GT object from .output), QC vs raster, add intervals check, insert.
  Batches 2 (OT2, 8) + 3 (NT, 9) staged — dispatch AFTER QC of batch 1 (validate interval format first).
- 2026-07-20 00:xx: **6-parallel dispatch HIT SESSION LIMIT — all 6 failed.** Sir: cap 2 agents at a time, deeper
  todo list, work within 5h window. Recovered PAGE-MAP from failures (no complete GT survived). Relaunched cap-2
  (seeded exact pages, skip locating): a9bc5b8acf30636ee=summe-and-partition(p15-16),
  a3a4a5496effb4fe9=summe-of-old-testament(p17-18). Queue: of-moyses(p18-19), argument-of-genesis(p19),
  signification-of-the-markes(p20), brief-recapitulation(p1127-29). Todo list = harness tasks #1-8.
- 2026-07-20: **matter_match_report.py BUILT + VALIDATED** (E5b core). Self-test correct (identical 3/3, noise
  3/3, garbled 0/3); lectionary vs S6 = ✗12% (located + scored, honest baseline). intervals_of() reliable for
  tables/display; PROSE needs agent-emitted intervals (new GT) or raster paragraph annotation (existing 11 = coarse).
- 2026-07-20: OT1 progress — ✅ summe-of-old-testament (a3a4a5496effb4fe9: 84 body, 34 intervals [2 para +
  title + citations/glosses], prose-conserv OK, self-validated). Running: summe-and-partition (a9bc5b8acf30636ee),
  of-moyses (aa86975a6508cf7f1). Queue: argument-of-genesis(p19), signification-of-markes(p20), brief-recap(p1127-29).
  Harvester `harvest_matter.py <agent_id>` (unescapes &amp;, writes GT, structural QC). 
  **E5b refinement TODO**: matter scoring = 2 pools — PARAGRAPH intervals (E4/E5a analog: per-interval + combined)
  vs APPARATUS intervals (citation/gloss/annotation/marginalia/footnote/heading → E5b "all apparatus combined").
  Update matter_match_report SCORE_KINDS split accordingly before the scoring run.
- 2026-07-20: OT1 cont'd — ✅ summe-and-partition (a9bc5b8: 78 body, 5 intervals, 3 para). **COMPLETENESS GAP**:
  its final paragraph (interval 4) TRUNCATES at p16 foot; ~5-line tail completes on TOP of p17 before "THE SVMME
  OF THE OLD TESTAMENT". Flagged in the GT's interval-4 "continues" note. Running: of-moyses, argument-of-genesis.
  Queue: signification-of-markes(p20), brief-recap(p1127-29).
  **Brief updated → WRITE-TO-FILE**: remaining matter agents Write GT to disk + return SHORT summary (was dumping
  ~15-20K-token GTs into orchestrator context). Old-style agents still running (of-moyses, argument-of-genesis).
  **COMPLETENESS-GAP CLEANUP (batched, before FINAL)**: grep all matter GT for "TRUNCATED"/"continues"/"out of scope"
  notes → render the spill page(s) → complete the tail(s). Known: summe-and-partition p17 tail.
- 2026-07-20: **C S9-Psalms RESOLVED** — jp2-S09ot2 gives 150/150 chapters (2402 vv, was empty). Residual per-verse
  noise (dropped drop-caps, 'THE BO' header-bleed) = general reOCR baseline shared by all sources (E-flagged), NOT
  S9-specific. No S9 coordinate/localization defect remains.
- 2026-07-22: **M2 VERSE-SEG ENGINE BUILT + VALIDATED** (`verse_seg.py` + `verse_seg_eval.py`; full record in
  REOCR-MASTER-PLAN §0.5). The §5 linchpin: janvier-cut both sides removes the boundary artifact — genesis-24
  witness 0.638→0.938 (+0.30). Real R2 per-verse identity now TRACKS page quality: genesis 0.956 (15/19 ≥.90, GATE
  MET), psalms 0.936 (8/12; residual = 3 genuine R2 recognition errors + 1 catchword leak → R3/M4, NOT seg —
  stays OPEN per No Silent Degradation). VS-4 length-sanity flags cross-page partials OPEN (genesis v30 `24:30a`).
  +2 new capabilities: (1) acrostic-paratext strip (janvier inlines "Nun. Everlasting." markers Ps 118 v=8k+1;
  fixed v105/v113 0.68→1.0); (2) **janvier-as-apparatus-filter** — drops interleaved central-column footnotes
  using the janvier grid alone, NO Surya/geometry (psalms 0.298→0.936); partial answer to §11 SEG. FINDING:
  witnesses NOT uniformly ~0.99 (s_dismas `\hfil` LaTeX artifacts; odr_com Ps-118 versification broken 175 vv in
  range 1..207) → §9 witness-witness claim qualified. STILL OWED for full M2: GT-3 gold-expansion, DIV-1 matrix.
  Code-review of both modules running. — **M2 REVIEW milestone reached.**
- 2026-07-22 (cont.): **code-review of verse_seg applied** — 3 real boundary-math bugs fixed+regression-guarded,
  validated numbers unchanged (local-anchor placement replaces global interpolation; block_min=3 localization
  kills unrelated-prose mislocalization 32→1; sorted(cverses)). **DIV-1 DONE** (`divergence.py`): witness noise
  floor janvier-cut, 28 ch — mod↔mod 0.9948, arc↔arc 0.9805 (NOT the asserted 0.994), Gold↔witness 0.96–0.978;
  per-verse crater routing (§7 alarm-2) surfaces 15 flag-IN loci (psalms-118 v107=0.0 pins odr_com defect).
  **GT-2 DONE** (`gt2_restandardize.py`): all 15 scripture GT re-standardized janvier-cut, non-destructive+backed
  up (.gt2-backup/); caught & verified Ps-1 janvier-6-vs-printed-7-verse difference. **M3 CORE**: qc_audit
  realign_vmap swapped align_coords→verse_seg (genesis base-OCR honest 0.65, artifact gone); REP-1 curated filter
  (S14 leak killed) + renderer guard; ocr_consensus already zero-ref. Pilot re-run (5 books) → coverage-audit-
  verse.json in flight; then render v010. OWED: REP-2 (R2 stream, compute-tail), REP-4 (gold col), REP-5 (matter
  rows). Docs: REOCR-MASTER-PLAN §0.5/§9/§12 current.
- 2026-07-22 (M3 rendered + REP-2): pilot re-run promoted → `coverage-audit-verse.json` (old `.pre-verse_seg`);
  **report RENDERED v014 `reocr-report-pilot.html`, 6438 verses, curated-clean** (DATA + version-compare delta
  both S1–S9 only; banned only in explanatory narrative). Base-OCR honest baseline (arc ~0.36–0.70, 1/271 chapters
  passing). **REP-2 base→R2 lift `reocr_lift.py`: all 15pp 0.721→0.926 (+0.204, pass 40%→68%); representative 14pp
  +0.210 (41%→73%)** — reOCR value proven; residual = R3 set (OPEN). colossians-3 FLAGGED confound (base 0.72→R2
  0.0, greek-margins + multi-chapter + suspected §4 mis-address; page 571 base-OCR lacks the gold Col-3:18) →
  §13 Q5, blocks its deliverable. NEXT: M5 four-alarm gate calibration; then M4 (needs GT-3), REP-4/5, M6.
