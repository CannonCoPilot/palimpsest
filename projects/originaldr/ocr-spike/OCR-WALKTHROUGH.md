# OriginalDR OCR — Walkthrough

**What this document is**: the plan at working altitude — what actually happens, in order, to a leaf of the
1609 Douai Old Testament as it becomes a line of a published transcript. Where a step has a gate, the gate
is stated with its number so you can check it against `OCR-MASTERPLAN-V3.md` §9.6.

Companion documents: `OCR-EXECUTIVE-SUMMARY.md` · `OCR-OVERVIEW.md` · `OCR-MASTERPLAN-V3.md`.

---

# PART I — WHAT HAPPENS BEFORE ANY PAGE IS TOUCHED

## Step 0 — Establish which books we actually have *(week 1, blocking everything)*

Today the six scans are identified in our own documents **by pixel dimensions only**. Nothing anywhere maps
a scan to an edition, a volume, or a repository — and yet "which physical copy is the base document" is the
load-bearing decision of the entire project. The previous revision declared copy-text discipline in §0 and
deferred the bibliographic identification needed to exercise it to step 11.

For each of the six: **edition-issue · STC/ESTC number · volume (NT 1582 / OT1 1609 / OT2 1610 / later) ·
repository and shelfmark · scan provenance · native raster and whether a grayscale path exists ·
completeness and imperfections.**

Then choose, per bibliographic unit, **the base exemplar** — on completeness, impression quality and absence
of sophistication — and **document the losing candidates and why.**

Two things we already expect to find, and should say out loud now rather than discover in month four:
- **Some of the six are 1633/1635 and can never be a base document.** They are intervention sources only.
- **Where only one scan exists for a 1609/1610 volume, illegibility there cannot be resolved from a second
  photograph of the same forme, and gaps will be real.**

**Gate 0a**: every field resolved, **no UNKNOWN remaining.**

> **Why this is first**: I will not fill any of these in from memory. Candidate STC numbers surfaced during
> critique are recorded as *leads to verify against ESTC*, not as facts. A hallucinated shelfmark would
> poison the base-document choice and everything downstream of it.

## Step 0b — Look at the pages *(same week, one sitting)*

Three inventory questions close together by opening the scans and looking:

1. **Do Fogny and Kellam set any blackletter at all**, or only roman and italic?
2. **Is `ꝛ` (r-rotunda) present?** One editor called it anachronistic; the other pointed out that removing it
   *while admitting blackletter headings* is self-contradictory, since `ꝛ` is exactly the sort blackletter
   needs. **If there is no blackletter, both questions close at once.**
3. **Do the Latin per/pro brevigraphs `ꝑ ꝓ ꝗ` appear** in the running heads and Rheims annotations?

Until this is done, none of the three is enshrined in the glyph inventory. **This is now a task, not a
judgement call** — which is the right disposition for a question a photograph can answer.

## Step 1 — Ship the drop-cap fix *(week 1)*

Independent of everything else. A board cell carrying an unattested all-caps token fails — the chapter opens
`AFTER`, the recognizer reads `FTER` because the ornamental initial is not a character to it.

**18 cells.** They ship now because they must not be stranded behind the most speculative component in the
plan, which is what the previous build order did to them.

The **page axis** ships alongside: every open cell already carries its leaf, so a per-leaf view sorts
geometry defects to the top by construction.

**Gate 1**: 18 cells move to OPEN, **reported against a frozen board, never netted against gains.**

## Step 2 — The residue detector *(week 2 — the first real improvement)*

No ground truth, no new model, days of work.

For each leaf, compute **the fraction of that chapter's reference text matched by no recognised line at
all.** A high residue localises a region the geometry missed or clipped. Sort every leaf by residue, and
that ranked list is a **defect queue for the existing chapter workflow.**

Two properties that make this the right first build:
- It uses the incumbent pipeline **as a detector rather than as a generator**, so the incumbent's bias does
  not propagate into anything it produces.
- It targets exactly the failure class the campaign has been fixing by hand for weeks — and it **produces
  the stratification the layout ground truth needs, for free.**

Running alongside it, because the reference-based signal is **null exactly where there is no reference**
(the 8,383 loci): a **reference-independent** residue — ink groups with no line assignment at all.

**Gate 2**: precision@50 against hand-found defects ≥ 0.6, on 50 leaves of campaign history.

## Steps 4–5, in parallel — rasters and finding aids

**Rasters.** Extract, never render. **Grayscale is primary throughout**; 1-bit JBIG2 masks are a fallback
only, and any source that must use one is trained and scored as its own scope. Where only a mask exists,
reconstruct pseudo-grayscale with a **~0.8 px Gaussian at native resolution before any downsampling** —
applied identically at train and inference, so it carries no risk.

Two tests, and they are testing different things:
- **JBIG2 substitution** — lossy symbol matching merges visually similar glyphs, and **`ſ`/`f` is the
  canonical case.** Same 20 pages as mask and as composite, compared glyph-for-glyph. **Gate 0b**: ≤0.1%.
- **The binarisation gap** — which exists **even at a zero substitution rate**. A 1-bit image upcast to
  uint8 is two-valued, not grayscale; the pretrained model's first filters were fitted to antialiased edges
  with 20–40 grey levels across the transition, and binarised that gradient is a step. The penalty
  concentrates in **exactly the 2–4 px features the edition depends on — the `ſ` nub and the macron.**

**Finding aids.** Both archaic transcriptions are demoted from authorities to finding aids — verse
addressing, word identity, alignment anchors — because our own measurements show `s_dismas` splices
editorial annotation into scripture (`ruth/1/1`, `genesis/10/1`) in the reference that previously *governed*
glyph decisions.

- **R1, renumber first.** 8.0% of verses best-match at a non-zero offset. **Every verse-keyed comparison is
  invalid until this is finished.** **Gate 4**: offset-0 exact-key agreement ≥99.8%, residue enumerated per
  book — *not* best-match, which can be passed by widening normalisation without fixing a single number.
- **R2, de-contaminate.** **Gate 5**: seed known splices and report **detection recall ≥0.90.** The previous
  gate was "splice scan clean; audit published," which is a deliverable rather than a metric — you cannot
  claim clean without a recall figure.
- **The provenance audit** — 200 verses against the scans, reporting each transcription's `ſ`/`s` accuracy,
  its ligature policy and its base edition. It runs **before any use**, and it doubles as the seed set for
  `ſ`/`f` mining later.

---

# PART II — A LEAF BECOMES TRANSCRIPT

From week 3, this loop runs continuously and is where the hours go.

## Step 3 — The correction loop

```
leaf (ranked by residue)
   ↓
lines  ─── incumbent recognizer ───→  proposed diplomatic text
   ↓                                        ↓
line crop  ────────────────────→  VLM proposes corrections on the crop
   ↓                                        ↓
   └────────→  operator: accept / reject / retype, by keystroke  ←────┘
                            ↓
                sha-pinned signed-off page
                            ↓
   ┌──────────┬─────────────┬──────────────┬────────────────┐
transcript  eval text   training GT    layout GT     glyph instances
```

**The same keystrokes produce all five.** This is the difference between a plan with a ~250-hour annotation
prerequisite and a plan with none: there is no separate annotation project, because correcting a page *is*
the annotation.

Working rules:
- **The VLM sees a line crop, never a page.** That is the only point at which a vision model touches the
  product.
- **The board is not the metric here** — the corrected page *is* the reference.
- **Start in a zero-archaic-witness book** — Ecclesiasticus or Isaie. Those 8,383 loci are structurally
  invisible to every reference-based mechanism in the plan, so if they are not deliberately ordered first
  they are discovered last.
- **Rolling evaluation, free and ungameable**: fine-tune every N signed-off pages, and measure CER on **the
  last 20 signed pages before they entered training.** Each slice is used exactly once, so it cannot be
  worn out by repeated querying.

## Step 6 — Pilot gold, then Step 7 — freeze the sets

**Pilot first, because the previous plan sized its ground-truth sets from round numbers and was attacked
from both directions at once** — under-powered for the gates it wrote (**5.6× short**, so "CER ≤1.0%" could
not be distinguished from 1.29%) and over-sized for the work (**~200–280 hours**, stated nowhere).

Both attacks were right, because the sets were sized for the wrong scope. Under the one-product decision,
**diplomatic keying care is needed for the base document only** — and the correction loop generates it as a
by-product.

**Gate 3**: the pilot's job is to **measure the keying rate and its variance**, published; the real sets are
then sized from observed variance rather than from a guess.

**Gate 7/8**, when the sets freeze:
- **Split by gathering, never by page.** Adjacent leaves of one gathering share paper, bleed-through, skew
  and the same forme — a page-level split puts near-duplicates on both sides and inflates every geometry
  comparison.
- **Stop stratifying on book.** The previous scheme was 876 cells for ~125 pages — 0.14 pages per cell — and
  the zero-witness books, called structurally critical, got about 8 pages across all sources. Stratify
  **source × parity × page-type** instead, and **purposively over-sample**: ≥40 pages from zero-witness
  books, ≥60 chosen *because* they carry marginalia, weights recorded and the estimator re-weighted.
- **Three tiers**: DEV (unlimited) · VAL (budgeted, noised, **query count published**) · **HOLDOUT (opened
  once, at publication)**.
- **The noise floor**, and the honest version of it: there is one operator, so a genuine inter-transcriber
  floor is unavailable. Time-separated blind self-re-keying gives an **intra**-transcriber floor — **a lower
  bound, labelled as such everywhere it appears** — with three keyings on 150 lines to expose the
  *correlated* error two keyers sharing one protocol cannot see, per-class floors for `ſ`/`f` and macron
  drawn by census, and ~8 hours of a paid second keyer to validate it once. **If the two diverge, that is an
  ALERT that the estimator needs redesign, not a number to accept.**
- **δ is pre-registered *before* the floor is read**, or the target self-lowers when agreement is poor.

---

# PART III — THE MODELS

## Step 9 — Geometry

Region shapes come **from ink** — connected components and projection profiles on the native raster, plus a
generic baseline segmenter over the untyped full page, **independent of the incumbent bands.** That
independence is the whole point: the previous construction derived polygons from line boxes that had
themselves been produced *under* the bands, so the labels inherited the bands' blind spots and the boundary
gate was unreachable in expectation.

Region **labels come from text** — MainText from alignment, Marginalia from the 1,334 transcribed apparatus
blocks, RunningHead / Catchword / Signature from self-verifying positional tests, VerseNumber from
numeral-matches-adjacent-verse.

Two corrections worth naming:
- **The geometric prior is an initialisation and a plausibility clamp, not a vote.** As a vote it meant *the
  incumbent always carries* — and the sub-agent was outvoted **exactly on the leaves where it was the only
  voter that could be right.** Disagreements now resolve against pixel evidence in the disputed strip.
- **Marginalia negatives are mined explicitly.** Otherwise every unlabelled marginal block is an implicit
  negative and teaches the model to suppress the class.

**Gate 9**, published *before* the baseline is measured and sha-pinned, with the recognizer frozen so
movement cannot be attributed to geometry that did not cause it: **marginalia recall ≥0.85 and precision
≥0.90 at block-level n · MainText boundary error ≤8 px median, ≤25 px p95 · ≥125 eval pages.**

## Step 10 — Recognition

**The codec keeps everything atomic** — `ſ f æ ﬀ ﬁ ﬂ ﬃ ﬄ` and the macron vowels — with **NFC pinned** at
both ends, composing and decomposing only at output serialisation. The decomposition scheme in the previous
revision was backwards, and the reason is worth carrying: **CTC alignment is monotonic, and the macron sits
above the bowl rather than after it** — there is no horizontal slice where the mark is present and the base
is not, so a two-symbol target forces the network to invent an ordering the image does not contain, and the
mark gets absorbed into the base's frame run and dropped.

**Rare classes** are protected by oversampling capped at **3–8×** (beyond that, per-class loss weighting),
plus **synthetic line rendering from the fount** and **decode-time prior scaling** — with monitors that
watch the frequent neighbour's false-positive rate, because the failure mode is *precision collapsing while
recall climbs*, which reads as success.

**Scope is SOURCE, then FOUNT** — roman text, italic annotation, display — because that is the axis on which
letterforms actually differ. Gathering variation is handled by **stratifying the held-out split**, not by
another model level.

**Input height**, honestly costed: **only H=120 warm-starts cleanly** from the pretrained model; raising it
multiplies the recurrent stack's input width and **breaks weight transfer at the reshape**. The correct
joint move is a height-only pooling stage. **5 configs × 3 seeds = 15 runs ≈ 120–200 GPU-hours**, ranked on
a 5k-line subset, decided on **`ſ`/`f` and macron per-class F1** — because aggregate CER is ~97% dominated
by classes 120 px already handles and cannot resolve the question.

**Style never enters the codec.** Italic, small capitals, swash, blackletter, turned letters and wrong-fount
sorts are **rendition states, not characters** — admitting them would multiply the class count and destroy
the rare-class budget. Instead: a plain grapheme channel with a stable character index, **a parallel span
table** over that index, a **separate word-level font classifier over the line image**, and **two-channel
scoring** — CER on characters, span F on rendition, **never folded together.**

**Gate 10**: CER-folded ≤1.0% · CER-diplomatic at the measured floor + δ · per-class precision *and* recall
with support · **cluster bootstrap over pages, not Wilson intervals** (character errors cluster by line,
page and fount, so Wilson runs 2–4× too narrow) · line-segmentation error · WER · **abstention rate reported
as a headline**.

And the one that catches what everything else misses: **per-class error stratified by source × fount ×
neighbour-context, reporting the maximum over strata rather than the mean**, plus a run-length statistic.
Without it, the suite is passed by its most dangerous failure — **systematic attested substitution**, where
a model reads `ſ` for `f` in one specific context, produces a real word (`ſonne`), scores fine on aggregate
CER, and is diluted below detection because the class is right 97% of the time overall.

## Step 12 — Glyphs

**Mining is text-side, and it terminates.** `ﬃ` can only occur where the letters are `ffi` — so search the
finding aids for `ffi|ffl|st|fi|fl|ff` tokens (`office`, `affliction`, `first`), align them with the
incumbent recognizer over the fold-equivalent letters (which *are* in the codec, so the cuts localise to ±1
character **even when the ligature is misread or dropped**), and crop that window. Every crop is a
positive-context candidate, found without the classifier it will train. Macrons are mined where the
recognised token is exactly one character short with a nasal at the deletion point.

The recall bias is **declared and bounded**: you only find ligatures where the reference spells the letters,
so a random 100-line sample is keyed to count what was missed.

**Decisions come from three sources, in this order**: the codec (end-to-end, for the high-support classes) ·
**unsupervised sort clustering per fount** — key ~50 exemplars, propagate, because letterpress repeats the
same physical sort · and **pair CNNs on emission-centred crops** for `ﬁ`/`ﬂ` (tittle absent in the
ligature), `ﬀ` (one crossbar or two), `ct`/`ſt` (the connecting arc).

**Not** connected components, and **not** advance width. At 650 ppi a printed line is largely one connected
component, and advance width — the true physical discriminant — cannot be measured, because ink extent
differs from body width by a spread of comparable magnitude to the effect.

**Every instance on a declared page set is keyed — a census, not a rate.** The denominator is page-defined
rather than detector-defined, so misses are visible. **Anything below n=30 is UNMEASURABLE: open, blocking,
never quietly passed.**

---

# PART IV — WHAT REACHES THE READER

## Steps 11 and 14 — Address, adjudicate, publish

**Two addresses, both carried on every line**: page and signature as the **primary physical** address —
because verses span pages and the three books paginate differently — and verse as the **secondary logical**
one, following **the base document's own numerals**, with any content-derived disagreement recorded as a
separate attribute. **Never silently normalised to modern versification.**

**Disagreement routes to exactly one of three places**, and most verses generate nothing at all:

| situation | disposition |
|---|---|
| base document legible and stands | **no record** — the overwhelming majority |
| base illegible, **same-setting** surrogate resolves it | **surrogate register** — legibility provenance, summarised statistically, never enumerated as apparatus. *This is transcription, not emendation.* |
| **different-setting** supply, or a demonstrable press error | **intervention apparatus** — bracketed in every view, carrying the supplying document's STC number **and date**, so a reader can see that a word in the 1582 text came from 1635 |

Setting identity is **proved before any cross-source use**: same signature, same catchword, **same line-end
words.**

**The uncertainty gradient the transcript may use:**

| state | encoding | what a plain-text export shows |
|---|---|---|
| confident | plain text | the reading |
| uncertain | `<unclear cert="">` | **the reading, flagged** |
| unread | `<gap reason="damage" quantity="" unit="chars"/>` | **the gap — never a guess** |
| supplied from a document | `<supplied source="#stc____">` | **bracketed, always** |

> **The bright line: `<supplied>` requires a source pointing at a *document*. Rule-generated archaic
> spelling has no document source, so it can never appear in the transcript at all.** It survives only as a
> separately-named reconstruction layer — its own file, excluded from every citable export, labelled
> non-documentary at the top of every view.

**The apparatus records interventions only** — one record type, most verses empty — plus, once per edition,
the bibliographic identification, the made-up-leaf table, scan checksums, and **a statement of editorial
principles listing what is silently normalised so those things never generate records.**

**The one non-negotiable obligation**: `<pb>` and signature milestones **in the text stream**. Without them
no reading can be checked against the book — **and they must be captured during transcription or never.**

---

# APPENDIX — running Genesis through it, today

You asked to see chapters move through the pipeline. Here is what can honestly run **now**, before any of
the new components exist, and what each would tell us:

| what | needs | tells us |
|---|---|---|
| **`pipeline_run.py` on a Genesis chapter** | nothing new | watch a chapter cross the seven stages read-only — this is what found the drop-cap class |
| **Residue detector over Genesis** | days of work, no gold, no model | **the ranked defect queue** — and the first honest estimate of how much of the board's residual is geometry rather than recognition |
| **Drop-cap fix** | ready | 18 cells, immediately |
| **Coverage figure** | built | `reference-coverage.html`, the required report panel |

`walkthrough.py --next` is **ch4**; the board stands at **5744/6116 = 0.9392**, with ch23, ch39, ch41, ch5
and ch10 walked and the R3 v3b pass complete. **The standing order is unchanged**: every Genesis chapter
under 100% gets one to two full chapter-workflow efforts, and status comes from `--status/--next`, never
from memory.

**My recommendation for the demonstration**: run the **residue detector** over the Genesis chapters that are
already walked. Because those chapters have been hand-fixed, we know what their defects were — so the
detector's ranking can be scored against ground truth we already possess. That is **Gate 2**, it needs
nothing that does not exist, and it converts "the geometry is the problem" from an assertion into a
measurement.
