# THE CHAPTER WORKFLOW — bringing chapters of the DR to standard
### Phases 0-7 distilled from Genesis 1 and 16. **THE ROUND TEMPLATE below is distilled from the ten chapters that crossed 0.90 after them**, and it is the part that decides where a round's hours go.

> **READ THE ROUND TEMPLATE FIRST.** Phases 0-7 describe how to hand-build ONE cold chapter to 100%, which is
> how chapters 1 and 16 were closed. That is the most expensive tool in the kit — measured at **6% of the
> campaign's cells for the largest share of its hours**. It is still the right tool, but for one chapter per
> round and for a specific reason (below), not as the default loop.

---

# THE ROUND TEMPLATE — how to spend a round (2026-08-01, from the 0.7865 -> 0.8543 climb)

## 1. The economics, measured — `.campaign/progression.jsonl`

Ten recorded steps, 4,960 -> 5,225 cells (+265). Attributed by class:

| class | cells | share | what it costs |
|---|---|---|---|
| **Autonomous recognizer passes** (R2 attest arm, R2 + R3 sweeps) | **+183** | **69%** | unattended machine hours; near-zero attention |
| **Systemic defect fixes** (mixed leaf, verse-1 anchor, `line_split`/skew, R3 apparatus filter) | **+67** | 25% | hours of diagnosis, then minutes to apply |
| **Per-chapter and per-leaf hand work** (CHAPTER_MODEL, PAGE_OVERRIDE, visual reads, gutter sweeps) | **+16** | **6%** | by far the most expensive per cell |

**The naive conclusion — "just run the passes" — is wrong, and the ledger says why.** Every one of the +67
systemic fixes was DISCOVERED by hand-working a single worst chapter. ch39 was being worked depth-first when
`leaf_diag.py` showed `rows kept 0` on a leaf, which exposed `_is_annotation_leaf` deleting mixed leaves whole;
that one defect was worth **+38 across the book** and 3 cells in the chapter that found it.

> **THE RULE THAT SETS THE LOOP: hand-work's return is the GENERALIZABLE DEFECT IT EXPOSES, not the cells it
> closes in the chapter you are working.** Budget hand-work as reconnaissance, and judge it by whether it
> produced a rule — not by whether the chapter closed.

## 2. The round loop

```
0. MEASURE ALL 50           chapter_campaign.py --chapters 1-50 --phase measure     (~9 min)
1. TRIAGE BY SIGNAL         the router in §3 — NOT by score order
2. HAND-WORK EXACTLY ONE    the worst chapter that is not ref-blocked. Phases 0-7.
                            Treat every defect found as a CANDIDATE SYSTEMIC FIX.
3. SCOPE THE FIX            measure it BOTH scoped to its defect class AND applied globally (§4)
4. RUN THE PASS             r3-runner-v2.sh, and r2_attest.py for any leaf it lacks
5. RE-MEASURE ALL 50        knock-on gains are the point — Sir's standing instruction
                            AND check the ſ-surfaces: the board counts CONTENT only (§6b B4)
6. RE-RANK, and list open POLICY items beside open cells (§6b B8).
   If step 2 produced NO rule, that is an ALERT to redesign the approach (§6b B7) —
   it is NEVER a stopping point and never makes a short chapter done (§6b B5).
```

**Do not run steps 2 and 4 in series when you can overlap them.** The passes are unattended and serialized
behind their own lock; hand-work in step 2 is attention-bound. Start the pass first, then diagnose while it
runs. The one hard constraint is memory: **one 17GB olmOCR at a time** — take `.campaign/r3-runner.lock`.

## 3. THE ROUTER — triage by SIGNAL, not by score

**A chapter's score tells you how much is wrong, never what is wrong.** Every large win in this campaign came
from a signal, and the signals have very different yields. Check in this order:

| # | signal | what it means | tool | action | historical yield |
|---|---|---|---|---|---|
| 1 | `ref_gaps` non-empty | **UNREACHABLE.** The reference lacks the verse | `chapter_campaign.py --report` | **SKIP THE CHAPTER.** Acquisition, not OCR | ch23 sits 2nd-worst and cannot move |
| 2 | cells with **NO TEXT** | leaf discarded or never localized | `leaf_diag.py`, `chapter_open_probe.py` | mixed leaf -> `chapter_open_y`; check `_is_annotation_leaf` | **+38, zero regressions** — the campaign's best single fix |
| 3 | **one reference's mean far below the other three** | the INSTRUMENT is broken, not the OCR | `ref_alignment_audit.py` | `ref_renumber.CORRECTIONS`, corroborated | 700 blocked cells -> 4 |
| 4 | one source far below **its own median** in this chapter | a LEAF defect | `leaf_diag.py` | `PAGE_OVERRIDE` / `CHAPTER_MODEL` | ch39 0.554->0.717, ch44 0.61->0.824 |
| 5 | a source low **everywhere** | recognition quality | `s6_causes.py --source SX --examples 3` | R2/R3 — do not look for geometry | the +183 |
| 6 | **all four sources fail the same verse** | **TWO CAUSES — split them.** A REFERENCE defect, or a true divergence | the split test below | if one reference binds and the others pass -> `ref_renumber` | **20 cells recovered, 2026-08-01** |

**SIGNAL 6 WAS MIS-SPECIFIED IN THE FIRST DRAFT OF THIS TEMPLATE, AND THE ERROR COST 20 CELLS.** It was written
as "edition divergence, a ceiling, never chase". Two things were wrong:

* **The reasoning.** "Divergence is a property of the page all four photographed, so it cannot fail in one
  source alone" is false for S6 — S6 is the **1635 second edition** and the archaic references are 1609, so it
  is a DIFFERENT PAGE. Its divergence can and does fail alone. Measured: the arm gap
  (`min(modern refs) - min(archaic refs)`) is median **-0.0110 for S1, S3 and S9 alike** — identical to four
  decimals, as three witnesses of one edition should be — and **+0.0000 median / +0.0115 mean for S6**. A real
  +0.024 shift, in the predicted direction, with the metric artifact controlled out by the 1609 witnesses.
* **The instruction.** "Never chase it" sent the whole bucket to the bin, and **five of the 34 all-fail verses
  are REFERENCE DEFECTS worth 20 cells**, three of them in the worst-seven chapters.

**THE SPLIT TEST — run it on every all-fail verse:**

> For each reference, does **every** source fail against it? If exactly ONE reference binds and all four sources
> **pass** the other three, it is a **reference defect, not a reading failure.** Corroborate on word count.

All five found this way are `s_dismas`, and every one is an outlier-high word count — the apparatus
contamination of Phase 1, occurring at **verse** scale where no chapter-level mean can see it:

| verse | s_dismas | the other three | what s_dismas spliced in |
|---|---|---|---|
| genesis 26:2 | **62** | 23 / 23 / 23 | |
| genesis 29:15 | **23** | 21 / 21 / 21 | |
| genesis 33:10 | **56** | 46 / 46 / 45 | |
| genesis 41:52 | **25** | 22 / 22 / 22 | the name gloss `Fruitful or` / `Grovving.`, and the tail `in the land of my pouertie` lost |
| genesis 47:4 | **63** | 44 / 44 / 44 | |

genesis 41:52 is the archetype: all four sources read it nearly perfectly — **S6 scores 0.99 against three
references** — and every one fails on s_dismas alone at 0.811-0.835.

**What remains after the split is 7 verses where all four references bind.** THAT is the true divergence /
bad-read ceiling, and it is the number to quote — not 33, and not 34.

**Do not chase divergence either, but for a measured reason, not the one first given.** The ch8 signature
(modern arm passes, archaic arm fails) is **not enriched in S6**: S6 8.4% of open cells, S1 7.2%, S3 8.3%,
**S9 12.9% — the highest**. `modern_id` is simply a looser fold. The signature is not a divergence detector,
and the examples confirm it: S6 gen 5:25 `Muthuſula ... hundrod` is a plain misread the modern fold forgives.
**A real divergence detector is §13 Q21 and is STILL UNBUILT.** Until it exists, "edition divergence" is a
hypothesis about a cell, never a classification of one.

**Signal 4 is the one that finds the big ones.** Rank `(chapter, source)` pairs by how far the source sits
below its OWN book-wide median. A source at 0.90 across the book and 0.23 in one chapter has a leaf defect;
a source at 0.72 everywhere has a recognizer. Every large win came off the top of that list.

## 4. SCOPE EVERY FIX TO ITS DEFECT CLASS — and measure both ways

The mixed-leaf fix, measured two ways on the same day:

| | cells | regressions |
|---|---|---|
| applied to **every** chapter | **+41** | **9 chapters, 1-4 each** |
| applied only to its **defect class** (a `(source, chapter)` whose cells have NO TEXT) | +38 | **ZERO** |

**The scoped version scores lower and is the right one.** The same shape got `chapter_model_derive` pinned OFF
(re-verified: still net -6). A global rule that nets positive is still wrong if it regresses chapters that had
nothing wrong with them — those regressions are text it is corrupting, and the board is averaging them away.

This is the §13 Q47 rule at round scale: **a rule is measured by the text it changes, not the verdicts it
flips.** Run `faithfulness_audit.py` before adopting anything that edits text, *including your own fixes.*

## 5. WHAT THE ROUND SHOULD EXPECT TO FIND — the residue has hardened

`s6_causes.py --source S6`, before and after the two passes:

| bucket | before | after | change |
|---|---|---|---|
| MISREAD | 255 (44.9%) | **219 (51.5%)** | **-14% only** |
| DIVERGE | 198 | 126 | -36% |
| INTERLEAVE | 100 | 79 | -21% |
| NO-TEXT | 14 | 1 | gone |
| **S6 open, total** | 568 | **425** | -25% |

**The passes cut DIVERGE and INTERLEAVE hardest and MISREAD least, so the remainder is now MORE concentrated in
exactly what the passes are for.** Re-running the same passes is the intuitive next move and the low-yield one.

And MISREAD is not random noise — it is a **confusion set**, visible in every example:

```
truit / ot        f -> t          .he              t -> .
vou / aud / ihal  u<->v, n->u, s->i
openod / hundrod  e -> o          Muthuſula        a -> u
commanthat        `commanded vs` collapsed — a DROPOUT, not a misread
```

That is recognizer-targeted work (confusion-aware post-correction, or an R2 fine-tune weighted to these pairs),
not another sweep. See "The R3 model question" at the foot of this document — option 1, improve R2, is the
best return per unit effort and this measurement is the evidence for it.

## 6. WHAT IS ALREADY EXHAUSTED — do not re-open these

- **GEOMETRY.** ch3, ch6 and ch41 were all carried as column/interleave chapters and none of them were: ch3/ch6
  lacked a chapter model, ch41 had a real margin merge worth +1 cell. Nine apparatus-separation attempts are
  pinned dead with their numbers. **Per-source x-BANDS work; single thresholds never will.**
- **A ninth geometric apparatus separation.** It would target at most a fifth of S6's failures, in a category
  S6 does not even lead on (its INTERLEAVE share, 17.6%, is *below* S9's 20.1%).
- **`chapter_model_derive` globally**, `split_glued`, `_trim_left_margin`, `restore_long_s`. All pinned with
  tests asserting they stay off.

## 6b. WHAT THIS LOOP IS BLIND TO — adversarial review of the template itself (2026-08-01)

Written by asking what the loop cannot see. Each item is measured, not speculated; the two that turned out to
be false are kept **because a pinned negative is what stops the next session paying for it again.**

**B1. THERE IS NO PER-VERSE REFERENCE-DEFECT DETECTOR, and the loop assumes there is.** `ref_gaps` sees only an
ABSENT verse (4 cells, ch23). Signal 3 sees only chapter-scale means. Genesis 30 already proved a reference can
be PRESENT BUT HOLED and pass every count test. So a single corrupted reference verse is **indistinguishable
from an OCR failure** — except through signal 6, which the first draft told you to ignore. B1 and the signal-6
error compound: the one place the defect is visible was the one place declared out of bounds.
**Build it:** the split test above is the detector, and it needs no new instrument — run
`ref_alignment_audit`'s contamination test PER VERSE over the all-fail set, not per chapter.

**B2. "REF-BLOCKED" IS UNDER-DEFINED — it names only the absent-verse case.** A chapter can be blocked by
degree as well as by absence. Grade it: **ABSENT** (`ref_gaps`; ch23 — skip, acquisition) · **CONTAMINATED**
(B1's five — repair, cheap, 20 cells) · **DIVERGENT** (the 7 all-refs-bind verses — needs a policy decision,
below). Only the first is genuinely unreachable, and the first draft's "SKIP" collapsed all three into it.

**B3. RESOLUTION IS NOT THE CEILING — TESTED, NEGATIVE, PINNED.** `reocr_core.MAXW = 2200` hard-downsamples
every page before the recognizer sees it, and the natives are far larger (`archive-holiebible-ot1` 3224x4329,
`jp2-S06` **5100x6601** — a 81% areal discard). It is the one constant in this project that was never swept,
and MISREAD (51.5% of S6's residue) is made of exactly the fine-stroke confusions a downsample should destroy
(`truit`/`fruite`, `vou`/`you`, `aud`/`and`, `ihal`/`shal`, `openod`/`opened` — f/t, u/v, n/u, s/i, e/o).
**Measured at MAXW 2200 vs 3400, tokens found in the reference vocabulary:**

    jp2-S06 p26              59.3%  ->  59.6%      (+0.3pp)
    archive-holiebible-ot1 p39   40.5%  ->  41.3%      (+0.8pp)

Flat. **The mechanism is that kraken normalises every line to the model's fixed input height**, and
`reichenau_dr` was fine-tuned at that scale, so page-level resolution barely matters above a threshold. Raising
MAXW costs time and buys nothing. **Do not spend a session on this.**

**B4. THE ROUND LOOP DROPS HALF THE STANDARD.** The standing order is "every verse >= 0.90 **and every ſ-surface
CLOSED**". The board counts content cells ONLY, so a round can raise the board while leaving surfaces open, and
nothing in the loop notices. Phase 7 criterion 2 exists; the round template never invokes it. **Add a surface
check to step 5**, and note the known cost: 2.9% of adopted tokens need a human eye — on the order of a
thousand hand-reads across Genesis. That number does not scale and the loop currently hides it.

**B5. THE EXIT CONDITION IS A SILENT-DEGRADATION TRAP.** "Stop the round when step 2 stops producing rules"
reads as a terminal state and is exactly the parked/unreachable acceptance the project forbids. **Correct
form:** when hand-work stops producing rules, that is an **ALERT that the APPROACH needs redesign** — escalate
via B7 — never a stopping point, and never a reason to call a below-threshold chapter done.

**B6. THE TEMPLATE IS GENESIS-ONLY, but the aim is chapters AND BOOKS.** Everything is Genesis-fitted:
`SOURCE_MODEL` bands, the four-reference set, the janvier grid, the book lexicon, `CHAPTER_MODEL`. Nothing
states the cold-start cost of a new book, what transfers, or what must be re-derived. And this document's own
warning applies with full force — *"book-level results disguise layout-specific heuristics every time."*
**Before the next book, measure which of the generalizable rules survive on ONE chapter of it.** Expect the
reference set to be the expensive part: Genesis took 700 blocked cells down to 4, and that work is per book.

**B7. WHEN THE SIGNALS ARE EXHAUSTED, THE LEVER MOVES UP A LEVEL — the loop has no ladder, so add one.** The
router only ever asks "how do we read the page better". Escalate in this order, and note that each rung is a
different KIND of work:

  1. **Read the page better** — recognizer. R2 fine-tune on the confusion set. (Where we are.)
  2. **Measure against the right instrument** — B1's detector; **acquire a 1635 reference so S6 is scored
     against its own edition.** This is the single highest-leverage unbuilt thing: S6 is the worst source in
     15 of the next 16 chapters and is currently graded against a text it does not print.
  3. **Acquire a better page** — a further witness for ch23's absent verse; a cleaner scan of a bad leaf.
     Note B3: more PIXELS of the same scan is not this rung.
  4. **Change the standard** — Sir's call, never the pipeline's.

**B8. POLICY QUESTIONS HAVE NO ESCALATION PATH AND SILENTLY BECOME PERMANENT.** ch8/8:14 has been open since
2026-07-31: the transcription is CORRECT, and no reading of those pixels can satisfy both a 1609 and a 1635
reference. It needs a decision (an edition-appropriate reference, or a divergence verdict distinct from a
transcription failure). It is not a cell anyone can win, and it has sat unasked through three sessions because
the loop has no step that surfaces it. **Step 6 of the round must list open POLICY items alongside open cells.**

## 7. THE NEXT BATCH IS ONE PROBLEM WEARING SIXTEEN CHAPTER NUMBERS

The 0.85-0.90 band: **S6 is the worst source in 15 of 16 chapters.** The extreme case is ch12 — S1, S3 and S9
all at **1.000**, S6 at **0.500**; the entire chapter deficit is one witness. ch45 (S6 0.607), ch19 (0.605),
ch44 (0.618), ch46 (0.676) are the same shape.

**So do not work these sixteen chapters as sixteen chapters.** Route them through signal 5, work S6's
recognizer quality once, and re-measure all 50. A chapter-by-chapter pass over this band would be the single
most expensive way to buy the same cells.

---


**The standard.** Every verse of every source's OCR matches the corresponding verse in **each** of the four
reference witnesses at **≥0.90**, with the best approaching 1.000, and every ſ-surface **CLOSED**. That is
`verses × 4 sources × 4 references` cells (Genesis 1: 496; Genesis 16: 256) plus a surface verdict per rescued
cell. A cell below the bar stays **OPEN** and blocks — it is never reclassified as acceptable.

**Board (2026-08-01): 5,225 / 6,116 achievable = 0.8543.** 2 chapters CLOSED, 12 at >=0.90, 1 below 0.70.
See `CAMPAIGN-STATUS.md` for the live state and the worst-first queue; this document is the method.

**Results from the two hand-built chapters — BOTH CLOSED.** Genesis 1: **496/496 = 100%**, all ſ-surfaces closed,
means 0.982/0.981/0.968/0.968. Genesis 16: **256/256 = 100%** from a 73.8% cold start, means
0.990/0.990/0.984/0.984. The figure passed *through* 87.5% when surface-gated adoption was turned on — it fell
because the standard rose, then went past the old number as the span-edge defects were fixed. **The last verse
closed with no model call at all**: it was two page-model geometry bugs at one leaf junction (§13 Q34). Before
commissioning a training run on a residual, exhaust the geometry.

> **⚠ TWO INTERPRETERS.** Everything here runs on `../ocr-venv/bin/python`. The other venv
> (`../../../.venv/bin/python`) cannot import kraken and will fail confusingly.
> Tests: `../ocr-venv/bin/python -m pytest tests/` → **202 passed** (2026-08-01).
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

**RUN IT ON YOUR OWN FIXES TOO (2026-07-31).** Widening the s_dismas page-foot note scan, the note-anchor class
was written `[A-ZſVI]` — meaning to admit a note opening on a long-s word. `ſ` is LOWERCASE, so the pattern
matched the commonest phrase in the book: `a ſonne`. It ate genesis 30's verse-6 tail, and when the line
`a ſonne, 11 she ſaid:` was read as an anchor it took the whole page beneath it, verses 11 to 26. **The
scoreboard would have shown a GAIN**, because the same commit repaired a real defect in that chapter. The audit
showed removals jumping 875 -> 2,462 tokens, and reading them showed sixteen spans of plain scripture. The
author of a rule is the last person its score will warn.

## BEFORE BLAMING THE RECOGNIZER, INTERROGATE THE REFERENCE (2026-07-31, §13 Q48/Q49)

Four of the five wins in the reference-gap session were repairs to the REFERENCES, not to the OCR — 700 blocked
cells reduced to 4. A chapter that will not come up is at least as likely to be measured against a broken
instrument as to be badly read. Check, in this order:

1. **Does the reference have the verse at all?** `chapter_campaign.py --report` lists per-chapter reference
   counts against janvier. A truncation shows as a contiguous 1..N run — that is a PARSE failure, never a
   witness that "only has seven verses".
2. **Does it have the RIGHT verse there?** Compare token counts across the four. `len(a) ≈ len(a)+len(a+1)` in
   the others is a merge; a persistent +1/-1 offset is a numbering shift. Both belong in
   `ref_renumber.CORRECTIONS`, corroborated, with the source file untouched.
3. **Is a nearly-full chapter actually whole?** A count test cannot see a hole. Genesis 30 held 42 of 43 and
   passed every gate while carrying a verse with its middle cut out.
4. **Did the acquisition step already tell you?** The odr-com manifest recorded the exact defect in July —
   `verse_count_match: 37/50` — and nothing read it. **A fidelity figure that no gate fails on is a comment.**

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
