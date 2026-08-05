# OriginalDR — Walkthrough

**What this document is**: the plan at working altitude — what happens, in order, to a leaf of the 1610
Douai Old Testament as it becomes a line of a published transcript. Gates are cited by number against
`OCR-MASTERPLAN.md` §7.8.

Companion documents: `OCR-EXECUTIVE-SUMMARY.md` · `OCR-OVERVIEW.md` · `OCR-MASTERPLAN.md`.

---

# PART I — BEFORE ANY PAGE IS TOUCHED

## Step 0 — Establish which books we have *(week 1, blocking)*

Nine scans are on disk and their raster properties are measured. **Their bibliographic identity is not.**
For each copy: **edition-issue · STC/ESTC · volume · repository and shelfmark · scan provenance ·
completeness and imperfections · made-up leaves.**

Then declare, per volume, **the base exemplar** — on completeness, impression quality and absence of
sophistication — **recording the losing candidate and why it lost.**

The measured raster column already narrows this decisively:

| volume | usable copies | base candidate | why |
|---|---|---|---|
| NT 1582 | S08, S09 | **S08** | the only continuous-tone scan in the corpus — no bitonal layer at all |
| OT1 1609 | S09, S03a | **S09** | 650 ppi vs 500 |
| OT2 1610 | S09, S03b | **S09** | 650 ppi vs 400 |

**S01 is excluded from all three** — 800 × 1124 px, ~168 ppi at the leaf, where the long-ſ nub spans under
1.6 px. It remains useful for page order and addressing.

**Gate 0a**: every field resolved, **no UNKNOWN remaining.**

> Nothing here is filled in from inference. A misattributed shelfmark would poison the base-exemplar choice
> and every downstream claim, so candidate STC numbers from earlier notes are treated as leads to verify
> against ESTC.

## Step 1 — Ship the drop-cap fix *(week 1)*

A board cell carrying an unattested all-caps token fails: the chapter opens `AFTER`, the recognizer reads
`FTER`, because the ornamental initial is not a character to it. **18 cells.**

**Gate 1**: 18 cells move to OPEN, **reported against a frozen board, never netted against gains.**

The **page axis** ships alongside — every open cell carries its leaf, so a per-leaf view sorts geometry
defects to the top by construction.

## Step 2 — The residue detector *(week 2 — the first real improvement)*

No ground truth, no new model, days of work.

For each leaf, compute **the fraction of that chapter's reference text matched by no recognised line.** High
residue localises a region the geometry missed or clipped. Sorted, that is a **ranked defect queue** for the
existing chapter workflow.

It uses the incumbent pipeline **as a detector rather than a generator**, so the incumbent's bias does not
propagate into what it produces; it targets the exact failure class the campaign has been fixing by hand;
and it yields the stratification the layout ground truth needs, free.

A **reference-independent** residue runs alongside — ink groups with no line assignment — because the
reference-based signal is null exactly where there is no reference.

**Gate 2**: leaf-ranking precision@50 against known defects ≥ 0.6, on 50 leaves of campaign history.

## Step 3 — The archaic typeset census *(week 2–3, blocks the codec)*

**The inventory is established before the codec is fixed**, by surveying the type itself.

1. **Sample** a stratified page set per volume — text pages, annotation pages, display pages.
2. **Enumerate** each candidate sort: present in this volume's fount? at what frequency? in which fount?
3. **Represent** each attested sort — standard Unicode and combining marks, **no Private Use Area**.
4. **Adjudicate** the ambiguous rows by inspection.
5. **Freeze** as a versioned document with an image exemplar per class.
6. **Record every *surveyed, not found*** so the question is closed rather than left open.

**Rows that the survey must settle rather than assume:**

- **"tall-s" vs "long-s"** — founts of this period normally carry two s-sorts, round `s` and long `ſ`. If
  only two are found, these are one sort under two names and the rows merge. The same question governs the
  `ſt`, `ſl` and `ſſ` entries that appear twice in the request.
- **"long-f"** — no such sort exists as such. Two things produce the impression: an `f` inside a ligature,
  or — the case that matters — **a long ſ cut with a full crossbar rather than a left-side nub.** Some
  founts do this, and it is then near-indistinguishable from `f`. **If attested, it is a genuine allograph
  needing its own class**, because it defeats nub-based discrimination and would otherwise be a silent
  systematic error across an entire volume.
- **`ꝛ`, and the Latin brevigraphs `ꝑ ꝓ ꝗ`** — entangled with whether these founts set any blackletter.
  One inspection closes all three.

**Also surveyed**, because their omission would make the transcript wrong or unusable: the **note-reference
marks** `*` `†` `‡` `¶` and superscript letters — **in this edition the annotation is roughly half the book,
and without the keys it cannot be tied to the text** — plus `ﬃ ﬄ`, `ſi`, `œ`, `&` and Tironian forms,
terminal `ij`, Greek and Hebrew sorts in the annotations, braces and printers' rules.

**Gate 3**: every requested class resolved ATTESTED or NOT FOUND per volume, with an image exemplar and a
frequency count; every ambiguous row merged or explicitly split. **The codec is built from the census and
from nothing else.**

## Steps 4 and 6, in parallel — rasters and finding aids

**Rasters.** Extract, never render. **Grayscale is primary** — for the MRC files that means the JPX layer,
not the JBIG2 mask. Where only a 1-bit layer exists, reconstruct pseudo-grayscale with a **~0.8 px Gaussian
at native resolution before any downsampling**, applied identically at train and inference.

Two tests, measuring different things:
- **JBIG2 substitution** (**Gate 0b**, ≤0.1%) — lossy symbol matching merges visually similar glyphs, and
  `ſ`/`f` is the canonical case. Same 20 pages as mask and as composite, compared glyph-for-glyph.
- **Binarisation transfer gap** (**Gate 0c**) — which exists **even at a zero substitution rate**, because
  a two-valued image is off-manifold for filters fitted to antialiased edges, and the mismatch concentrates
  in the 2–4 px features the edition depends on.

**Finding aids.** Both archaic transcriptions are finding aids, never authorities — one of them splices
editorial annotation into scripture at `ruth/1/1` and `genesis/10/1`.

- **R1, renumber first** (**Gate 5**, offset-0 agreement ≥99.8%). 8.0% of verses currently best-match at a
  non-zero offset, and **every verse-keyed comparison is invalid until this is finished.** The gate is
  offset-0 exact-key agreement, *not* best-match — best-match can be passed by widening normalisation
  without fixing a single verse number.
- **R2, de-contaminate** (**Gate 6**): seed known splices and report **detection recall ≥0.90.** A published
  audit is a deliverable, not a metric; without a recall figure there is no claim to being clean.
- **The provenance audit** (**Gate 7**) — 200 verses against the scans, reporting each transcription's
  `ſ`/`s` accuracy, ligature policy and base edition. Runs **before any use**, and doubles as the `ſ`/`f`
  mining seed.

---

# PART II — A LEAF BECOMES TRANSCRIPT

From week 3 this loop runs continuously, and it is where the hours go.

## Step 5 — The correction loop

```
leaf (ranked by residue)
   ↓
lines ── recognizer ──→ proposed diplomatic text
   ↓                             ↓
line crop ────────→ vision model proposes corrections on the crop
   ↓                             ↓
   └───→ operator: accept / reject / retype, by keystroke ←──┘
                     ↓
          sha-pinned signed-off page
                     ↓
  ┌──────────┬───────────┬────────────┬──────────────┐
transcript  eval text  training GT  layout GT  glyph instances
```

**The same keystrokes produce all five.** There is no separate annotation project, because correcting a page
*is* the annotation.

- **The vision model sees a line crop, never a page** — the only point at which it touches the product.
- **The board is not the metric here**; the corrected page *is* the reference.
- **Rolling evaluation, free and ungameable**: fine-tune every N signed-off pages, and measure CER on **the
  last 20 signed pages before they entered training.** Each slice is used exactly once.

**The pilot is Micheas (Micah), OT2 1610 — 7 chapters across ~7 leaves, present in all three OT2 copies.**

It has **no archaic reference witness**, so it exercises the part of the corpus that is structurally
invisible to every reference-based mechanism and would otherwise surface last. At roughly **one chapter-open
per leaf** it is a dense test of the drop-cap and chapter-heading machinery. And it is small enough to
finish early. **Joel** (3 chapters, ~5 leaves) and **Amos** (9 chapters, ~11 leaves) are the alternatives in
the same condition if the scale proves wrong.

## Steps 7–9 — Pilot gold, frozen sets, addressing

**Pilot first.** Its job is to **measure the keying rate and its variance** (**Gate 4**), so the real sets
are sized from observed variance rather than a guess. Diplomatic keying care is needed **for the base
exemplar only**; the correction loop then grows the set as a by-product.

**When the sets freeze** (**Gate 9**):
- **Split by gathering, never by page** — adjacent leaves share paper, bleed-through, skew and the same
  forme, so a page-level split puts near-duplicates on both sides.
- **Do not stratify on book** — copies × parities × books gives more cells than pages. Stratify **copy ×
  parity × page-type**, **plus purposive over-sampling**: ≥40 pages from books with no archaic reference,
  ≥60 chosen *because* they carry marginalia, weights recorded and the estimator re-weighted.
- **Three tiers**: DEV (unlimited) · VAL (budgeted, noised, **query count published**) · **HOLDOUT (opened
  once)**.
- **The noise floor**, honestly: with one operator there is no true inter-transcriber floor. Time-separated
  blind self-re-keying gives an **intra**-transcriber floor — **a lower bound, labelled as such everywhere**
  — with three keyings on 150 lines to expose the *correlated* error a shared protocol hides, per-class
  floors for `ſ`/`f` and the tilde vowels drawn by census, and ~8 hours of a paid second keyer to validate
  it once. **If the two diverge, that is an alert that the estimator needs redesign, not a number to
  accept.**
- **δ is pre-registered before the floor is read**, or a poor floor silently lowers the target.

**Addressing** (**Gate 8**, page-assignment error ≤1%): three independent signals — tome map, VerseNumber
regions, content alignment — and **a disagreement is a flag, not an average.** The printed numeral does not
decide; psalm titles counted as verse 1, `xv`/`xu` misprints, merged and split verses and mid-page
chapter-opens all produce numerals that lie.

---

# PART III — THE MODELS

## Step 10 — Geometry

Shapes come **from ink** — connected components and projection profiles on the native raster, plus a generic
baseline segmenter over the untyped full page, **independent of the incumbent bands.** That independence is
the point: polygons derived from line boxes produced *under* the bands inherit the bands' blind spots.

Labels come **from text** — MainText from alignment, Marginalia from the 1,334 transcribed apparatus blocks,
RunningHead / Catchword / Signature from self-verifying positional tests, VerseNumber from
numeral-matches-adjacent-verse.

**Gate 10**, published before the baseline is measured and sha-pinned, recognizer frozen: **marginalia
recall ≥0.85 and precision ≥0.90 at block-level n · MainText boundary error ≤8 px median, ≤25 px p95 ·
≥125 eval pages.**

## Step 11 — Recognition

**The codec is the census inventory, all atomic, in NFC.** Decomposing the tilde vowels is
counterproductive: **CTC alignment is monotonic and the mark sits *above* the bowl, not after it** — there
is no horizontal slice where the mark is present and the base is not, so a two-symbol target forces an
ordering the image does not contain and the mark is absorbed and dropped.

**Rare classes** are protected by oversampling capped at **3–8×** (beyond that, per-class loss weighting),
plus **synthetic line rendering** and **decode-time prior scaling** — with monitors watching the frequent
neighbour's false-positive rate, because the failure mode is *precision collapsing while recall climbs*,
which reads as success.

**Scope is VOLUME, then FOUNT**, with **copies pooled within a volume as augmentation** and held-out splits
stratified by copy and gathering.

**Input height** is costed honestly: **only the incumbent height warm-starts cleanly** from the pretrained
model; raising it multiplies the recurrent stack's input width and **breaks weight transfer at the
reshape.** The correct joint move is a height-only pooling stage. **5 configs × 3 seeds = 15 runs ≈ 120–200
GPU-hours**, ranked on a 5k-line subset, decided on **`ſ`/`f` and tilde-vowel per-class F1** — aggregate CER
is dominated by classes the incumbent height already handles and cannot resolve the question.

**Style never enters the codec** — a stand-off rendition layer with a span table, a separate word-level font
classifier, and two-channel scoring.

**Gate 11**: CER-folded ≤1.0% · CER-diplomatic at the measured floor + δ · per-class precision and recall
with support · **cluster bootstrap over pages, not Wilson intervals** · line-segmentation error · WER ·
**abstention rate reported as a headline.**

And the one that catches what the rest miss: **per-class error stratified by volume × fount ×
neighbour-context, reporting the maximum over strata**, plus a run-length statistic. Without it the suite is
passed by **systematic attested substitution** — a model reading `ſ` for `f` in one context produces a real
word, scores well on aggregate CER, and is diluted below detection because the class is right 97% of the
time overall.

## Step 13 — Glyphs

**Mining is text-side and terminates.** `ﬃ` occurs only where the letters are `ffi`, so search the
references for the closed-set contexts, align them with the incumbent recognizer over the fold-equivalent
letters (which *are* in the codec, so cuts localise to ±1 character **even when the ligature is misread or
dropped**), and crop that window. Every crop is a positive-context candidate found without the classifier.
Tilde vowels are mined where the recognised token is one character short with a nasal at the deletion point.

The recall bias is **declared and bounded** — this finds ligatures only where the reference spells the
letters — by keying a random 100-line sample and counting misses.

**Decisions come from three sources, in order**: the codec end-to-end for high-support classes;
**unsupervised sort clustering per fount** — key ~50 exemplars, propagate; and **pair CNNs on
emission-centred crops** for `ﬁ`/`ﬂ` (tittle absent in the ligature), `ﬀ` (one crossbar or two), `ct`/`ſt`
(the connecting arc), `ſſ` (the two nubs and shared shoulder). **Connected components serve as a candidate
detector within the closed set**, never as a general segmenter.

**Every instance on a declared page set is keyed — a census, not a rate**, so the denominator is
page-defined rather than detector-defined. **Below n=30 a class is UNMEASURABLE: open, blocking, never
quietly passed.**

---

# PART IV — WHAT REACHES THE READER

## Steps 12 and 15 — Address, adjudicate, publish

**Two addresses on every line**: page and signature **primary physical** — verses span pages and the three
volumes paginate differently — and verse **secondary logical**, following **the base document's own
numerals**, with content-derived disagreement recorded as a separate attribute. **Never silently normalised
to modern versification.**

**Disagreement routes to exactly one of three places**, and most verses generate nothing:

| situation | disposition |
|---|---|
| base document legible and stands | **no record** — the overwhelming majority |
| base illegible, **same-setting** copy resolves it | **surrogate register** — legibility provenance, summarised statistically, never enumerated as apparatus. *Transcription, not emendation.* |
| **different-setting** supply, or a demonstrable press error | **intervention apparatus** — bracketed in every view, with the supplying document's identity and date |

Setting identity is **proved before any cross-copy use**: same signature, same catchword, **same line-end
words.**

**The uncertainty gradient:**

| state | encoding | plain-text export |
|---|---|---|
| confident | plain text | the reading |
| uncertain | `<unclear cert="">` | **the reading, flagged** |
| unread | `<gap reason="damage" quantity="" unit="chars"/>` | **the gap — never a guess** |
| supplied from a document | `<supplied source="#...">` | **bracketed, always** |

> **`<supplied>` requires a source pointing at a *document*. Rule-generated archaic spelling has no document
> source, so it can never appear in the transcript at all.**

**The apparatus records interventions only** — one record type, most verses empty — plus, once per edition,
the bibliographic identification, made-up-leaf table, scan checksums, and **a statement of editorial
principles listing what is silently normalised, so those things never generate records.**

**The one non-negotiable obligation**: `<pb>` and signature milestones **in the text stream**. Without them
no reading can be checked against the book — **and they must be captured during transcription or never.**

---

# APPENDIX — what can run today

Before any new component exists:

| what | needs | tells us |
|---|---|---|
| `walkthrough.py --status` / `--next` | nothing | campaign state — board **5744/6116 = 0.9392**, `--next` = ch4 |
| `pipeline_run.py` on a chapter | nothing | watch a chapter cross the stages read-only |
| **Residue detector over walked Genesis chapters** | days, no gold, no model | **Gate 2** — and the first honest estimate of how much residual is geometry rather than recognition |
| Drop-cap fix | ready | 18 cells |
| Typeset census on Micheas leaves | the scans | **Gate 3**, and it closes the `ꝛ` / brevigraph / blackletter questions |

**Recommended first demonstration**: run the **residue detector over the Genesis chapters already walked**.
Those were hand-fixed, so their defects are known — the detector's ranking can be scored against ground
truth we already hold. That is Gate 2, it needs nothing that does not exist, and it converts "the geometry is
the problem" from an assertion into a measurement.

Standing order unchanged: every Genesis chapter under 100% gets one to two full chapter-workflow efforts,
and status comes from `walkthrough.py --status/--next`, never from memory.
