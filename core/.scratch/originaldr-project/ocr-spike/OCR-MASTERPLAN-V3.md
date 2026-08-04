# OCR MASTERPLAN v3 — one faithful diplomatic Douay-Rheims

**Revision 2, 2026-08-03.** Revision 1 was rewritten top to bottom after Sir rejected the previous direction;
revision 2 rebuilds it again after five independent adversarial reviews (`OCR-MASTERPLAN-V3-CRITIQUE-R1.md`)
found that its metrics were unfalsifiable, its build order was a cycle, and its central mechanism for learning
ligatures could not work. `OCR-MASTERPLAN-V2.md` remains the record of the ladder experiments.

---

## 0. WHAT WE ARE BUILDING

> **A diplomatic transcript of the 1582/1609–1610 Douay-Rheims — faithful in spelling and archaic typography,
> complete across the whole Bible, and citable by other scholars.**

### 0.1 The editorial constitution — this governs everything below

A textual scholar's review made one thing unavoidable: *diplomatic* means the transcription of **one document,
one setting of type**. Voting glyph-by-glyph across six witnesses spanning fifty years produces a text whose
readings co-occur on no page ever printed. So the product is defined by **copy-text discipline**
(Greg/Bowers/Gaskell), which turns out to serve Sir's aim better than voting did:

1. **A declared copy-text per tome**, chosen on physical grounds and documented (completeness, impression
   quality, absence of sophistication). The transcript *is* that copy.
2. **Accidentals follow the copy-text absolutely** — spelling, `ſ`/`s`, ligatures, punctuation, `i/j`, `u/v`,
   capitalisation. No other witness may alter an accidental. Ever.
3. **Other witnesses supply readings only where the copy-text is physically illegible or demonstrably a press
   error**, and every such emendation is recorded with its siglum and authority.
4. **The 1633/1635 editions are substantive witnesses only, always** — they may bear on *what word* is
   printed, never on *how it is spelled or set*. This replaces the previous "abstain where they differ" rule,
   which three reviewers independently showed was circular (you must know the earlier reading to know where
   they differ).
5. **Compositorial evidence is preserved, not corrected.** Turned letters, wrong-fount sorts, spelling
   variation between compositors, `doe/do`, `-nesse/-nes` — these are evidence. A voting scheme that
   "corrects" them destroys the object.
6. **Nothing is synthesised.** Where no witness can be read, the transcript records a **gap**, not a guess.

So the six per-source OCRs remain required at publication quality — Sir's requirement stands undiminished —
but their role is now precise: **to read each witness accurately, and to flag where the copy-text may be
misread.** Collation is a detection instrument, not a text generator.

### 0.2 Two failure modes I have to hold at once

**Mine, identified by Sir:** converting an ambiguous measurement into a reason to keep the status quo — I did
it four times in three exchanges (native resolution "no free win"; 120 px line height "a training-time
choice"; the coarse metric "the limit of what can be measured"; sources "good enough to vote").

**The opposite one, identified by the measurement reviewer:** over-correcting into unfalsifiable ambition —
targets with no stopping rule, requirements with no test, a project where every rung ends in
ALERT-and-redesign forever and therefore never ends.

The rule that avoids both: **an ambiguous measurement licenses a better experiment, never a lowered
requirement — and every requirement carries a defined test, a held-out set, and an escalation trigger.**

---

## 1. STAGE −1 — THE GOLD SETS. Nothing else in this plan is measurable without them

Four of five reviewers reached this independently and it is the single largest change in revision 2.

**Every metric in revision 1 was computed against ground truth the pipeline generated, scored against a
reference the pipeline corrects.** The accuracy target and the layout gate were both unfalsifiable. Sir's
instruction was to avoid *human-review-as-prerequisite bottlenecks*, and that instruction is honoured exactly
where it was aimed — at the **production** path, which stays automated and scales. But **evaluation cannot be
automated without becoming circular**, and a requirement that cannot fail is not a requirement. Building these
sets is what makes "0.5% CER" and "beats `PAGE_OVERRIDE`" into claims that can be false.

| set | content | size | rules |
|---|---|---|---|
| **GOLD-TEXT** | lines hand-keyed from the images under a written diplomatic protocol | 300–500 lines **per source** (~2–3k total), stratified by tome, fount, page type | frozen, sha-pinned, **never** used for training or GT generation |
| **GOLD-LAYOUT** | hand-drawn typed region polygons | 200–300 pages, stratified by source × leaf parity × book, **including the zero-archaic-witness books** | split once into frozen-eval and seed-train; the eval half is never trained on |
| **GOLD-GLYPH** | targeted instances of the rare inventory, mined not sampled | ≥200 instances per rare class where the class exists at all | the only honest evidence a rare class is being read |
| **NOISE-FLOOR** | a subset double-keyed by two transcribers and reconciled | ≥300 lines | **defines the attainable floor.** A target below inter-transcriber agreement is incoherent |

`PAGE_OVERRIDE`'s 371 hand-measured bands are human annotation the project already paid for, in a form that
cannot serve as evaluation. GOLD-LAYOUT is that cost paid once, correctly.

**Consequence for §5's target**: the noise floor is measured *before* the target is fixed, and the target is
set relative to it.

---

## 2. THE MEASUREMENTS THIS PLAN RESTS ON — corrected twice

### 2.1 `s_dismas` vs `odr_com` — the estimator, restated honestly

Sir was right that these are essentially the same text. My first figures ("94% differ") were verse-key
artefacts. My *second* figures are also flawed, and the measurement reviewer is right about why:

- 0.9879 is a **maximum over 11 candidate alignments** (±5 verses) — upward-biased by construction, with no
  null distribution, on text formulaic enough that any two DR-ish verses score well.
- It was computed on the **intersection** (13,292 mutually-covered verses — the easy subset) while coverage
  was computed on the **union**. Neither was stated.
- It folds long-ſ, `æ`, case and punctuation — **the dimensions the product exists to preserve** — and was
  then used to license repairing the glyph authority from a companion that does not preserve glyphs.

**Corrected reporting standard, now mandatory for any reference comparison:** offset-0 similarity as primary;
best-match-within-window as a labelled diagnostic; a permutation null (best match against 11 randomly drawn
verses of the same book) with the margin over null reported; and the metric computed a **second time with
glyphs unfolded** — that second number, not 0.9879, is the one relevant to ARCHAIC.

**What survives unchanged:** 8.0% of verses best-match at a non-zero offset. That is a numbering defect
concentrated in Psalms, Acts, Luke, Matthew and Mark, `ref_renumber` is incomplete, and **every verse-keyed
comparison of these two references is invalid until it is finished.**

### 2.2 `s_dismas` carries spliced apparatus, systematically

`ruth/1/1` and `genesis/10/1` both hold annotation in place of the verse tail. In the reference that governs
the archaic gate.

### 2.3 Coverage — and why the denominator needs an interval

| reference | arm | verses | % of union | chapters complete | chapters absent |
|---|---|---|---|---|---|
| `s_dismas` | ARCHAIC | 25,892 | 69.7% | 719 / 1,360 | 369 |
| `odr_com` | ARCHAIC | 16,201 | 43.6% | 552 / 1,360 | 774 |
| `sabates_a` | MODERN | 37,130 | 99.9% | 1,325 / 1,360 | 0 |
| `madueke_b` | MODERN | 35,809 | 96.3% | 1,299 / 1,360 | 26 |

Union: 37,166 verses / 1,360 chapters; **8,383 loci have no archaic witness at all.**

The union denominator hides three things and must be reported as an **interval**: it cannot see a book all
four dropped; it confuses versification *granularity* with incompleteness (a reference that splits verses
differently scores as short); and — most damaging — **it counts a verse as covered when its content is the
spliced apparatus of §2.2.** Upper bound comes from an independent source: the `VerseNumber` regions of our
own six scans (§4), which is a measurement we are building anyway. Headline becomes **"covered ∧ uncorrupt"**,
in characters as well as verses.

`coverage_figure.py` renders the book × chapter grid per reference with DR and modern book names. **Required
report panel from this version forward.**

### 2.4 Raster reality

S9 native 3231×4392 (650 ppi) · S06 JPEG 2550×3301 (JP2s corrupt; PDF stencil 2867×4146) · S03a 2262×3116 ·
S08 3035×4336. `preprocess()` forced everything to 2200 px with LANCZOS plus unconditional autocontrast.
The A/B/C/D experiment found no significant difference **with the current model** — which measures
co-adaptation, since the model's VGSL input is `(1,1,120,0)` and rescales every line to 120 px regardless.
**Input height is a parameter** (`ketos train -s '[1,H,0,1 …]'`), set deliberately in §5.

---

## 3. THE PIPELINE, AND ITS GENERATIONS

Two reviewers showed the build order was a cycle: alignment needs a recognizer, the recognizer needs alignment
GT, the region model needs alignment for labels, alignment needs regions for lines, and the region model's
gate was the board — which the recognizer produces. There is no entry point, and revision 1 silently resolved
it by using the incumbent geometry, i.e. the thing it claimed to be removing.

**So the pipeline is stated as an EM loop with numbered generations, and every generation is gated on metrics
computed against the frozen gold sets — never on the board, which moves between generations.**

```
G0  incumbent geometry (PAGE_OVERRIDE) + incumbent recognizer   → bootstrap only, never a gate
G1  ink-derived regions + GOLD-LAYOUT seed → region model v1 → recognizer v1 → alignment v1
G2  regions v2 (relabelled from v1 alignment) → recognizer v2 → alignment v2
…   until per-generation improvement < δ on GOLD, then ESCALATE with the measured floor attached
```

Stages, per generation:

```
 0  ACQUIRE      volume → verified native rasters, no lossy step
 1  GEOMETRY     page → typed region polygons (ink-derived shapes, text-derived labels)
 2  RECOGNISE    region → lines → diplomatic text over a decomposed glyph inventory
 3  GROUND TRUTH forced alignment → line GT;  typographic evidence → glyph GT
 4  PER-SOURCE   six transcripts, each measured against GOLD-TEXT
 5  LOCATE       tome map → book:chapter:verse across all six sources
 6  COLLATE      per-verse variant graph over witnesses + reference
 7  ADJUDICATE   copy-text emendation, image-adjudicated → THE TRANSCRIPT + apparatus
```

---

## 4. STAGES 0–1 — RASTERS AND GEOMETRY

### 4.1 Acquire

No lossy or resampling step anywhere in the working chain. **Extract, never render** (`pdfimages -png`;
verified S09 p60 → 3231×4392 mode `1`); composite only when the page needs it, at exactly native ppi
(`pdftoppm -r 650` → 3232×4393, verified); PNG/TIFF only; no autocontrast, denoise, sharpen or binarisation in
the default path; **`MAXW` deleted** — scaling happens once, inside the recognizer, at the declared line
height. S06 reads the 2,872 verified JPEGs (`jp2_page.py`, working). A raster manifest per source records
path, dimensions, bit depth, provenance and checksum.

**Two corrections from review, both blocking:**

- **Convert 1-bit → uint8 grayscale before any geometric operation.** Kraken's polygon line extraction
  resamples; nearest-neighbour aliasing on a 1-bit image removes precisely the few-pixel features — the `ſ`
  nub, the macron — that the edition depends on.
- **JBIG2 must be tested before the mask is trusted, and it now blocks step 1.** Lossy symbol matching merges
  visually similar glyphs and **`ſ`/`f` is the canonical case**. Test: extract the same 20 pages as mask and
  as high-DPI composite; compare glyph-for-glyph on every `ſ`/`f` and `c`/`e` instance; report substitution
  rate. If non-zero, the mask is disqualified as the primary and the composite path becomes primary.

### 4.2 Geometry — shapes from ink, labels from text

Revision 1 derived region polygons as hulls of aligned line boxes. Two reviewers showed this is
self-defeating: those line boxes were produced *under the bands*, so the labels inherit the bands' blind
spots, and MainText boundary error is bounded below by the hull's error — **making the boundary gate
unreachable in expectation.** Worse, the acceptance threshold discarded lines whose reading was far from the
reference, which is exactly what happens when a band clips scripture: the clipped words were never recognised,
so those leaves score badly and are censored out of training. Labels survived only where the incumbent was
already right.

Revision 2:

1. **Shapes come from ink.** Connected-component and projection-profile grouping on the native raster, plus a
   generic baseline segmenter (`blla.mlmodel`) run over the **untyped full page**, independent of
   `PAGE_OVERRIDE`. This is the only construction in which line geometry is not a descendant of the bands.
2. **Labels come from text**, assigned to ink groups: MainText from alignment to ARCHAIC verses, Marginalia
   from `madueke_b`'s 1,334 apparatus blocks, RunningHead / Catchword / Signature from self-verifying
   positional-and-text tests, VerseNumber from numeral-matches-adjacent-verse.
3. **The acceptance signal is inverted.** Unaligned residue is **positive evidence**: for each leaf, the
   fraction of the chapter's reference span matched by *no* line localises a missed or clipped region. That
   residue is a labelling target, not a discard. This is the single change that lets the model learn the
   failures the campaign has been fixing by hand.
4. **Invariant**: no ink of a typed group may fall outside its polygon.
5. **The fusion loses its correlated voter.** Distant supervision and the geometric prior both descend from
   `PAGE_OVERRIDE`, so 2-of-3 meant "the incumbent always carries" — laundering, and the sub-agent was
   outvoted exactly on the leaves where it was the only voter that could be right. Revision 2: the prior is an
   **initialisation and plausibility clamp, not a vote**; agent-versus-distant-supervision disagreements
   resolve **against pixel evidence in the disputed strip**. The A–C agreement rate is measured first; above
   ~0.95 the old fusion was decorative and is reported as such.
6. **DropCap leaves the region model.** It is one instance per chapter (~1,360 per source), nested inside
   MainText, and kraken's region polygons plus reading order handle nesting badly. It is detected as an
   **alignment deficit** at chapter open (reference `AFTER`, line reads `FTER`) and restored as a character.
   **The board fix ships now, independently**: a cell carrying an unattested all-caps token fails. That is 18
   cells and it must not be stranded behind the most speculative component in the plan.
7. **Marginalia negatives are mined explicitly** — only leaves with confirmed apparatus coverage contribute
   Marginalia-negative pixels, or every unlabelled marginal block becomes an implicit negative and teaches the
   model to suppress the class.
8. **Zero-archaic-witness books** (Ecclesiasticus, Jeremie, Isaie, Ezechiel, 3/4-Esdras) generate no
   distantly-supervised labels at all, so the training set would be a non-random book subset. **GOLD-LAYOUT's
   stratification must cover them**; they are otherwise structurally invisible to the whole plan.

**Gate — on GOLD-LAYOUT's frozen eval half, with the recognizer frozen** (so board movement cannot be
attributed to geometry it did not cause): per-class marginalia recall **and precision**, MainText boundary
error in pixels, per-class IoU. Target values are set from the G0 baseline measured on the same set, with a
pre-registered minimum effect size. The board is a **secondary sanity check only**.

**Escalation ladder, with a termination condition**: rung 1 is *annotate more pages* (the rung revision 1
omitted); then weighted resampling of the failing class; then finer model scope; then typology merge
(**recorded as a loss of resolution, not a success**); then re-test deskew now that bounds are polygons. Each
rung carries a cost estimate and a δ. After N rungs with improvement < δ, **escalate to Sir with the measured
floor attached** — the project rule permits escalation and revision 1 never said when it fires.

---

## 5. STAGE 2 — RECOGNITION

### 5.1 The inventory, rebuilt from the type rather than from MUFI's medieval list

The scholar's review removed items that are not in Douay-Rheims roman/italic type and added items that are:

**Removed as anachronistic**: `ꝛ` (r-rotunda — blackletter/textura), `ꝑ ꝓ ꝗ` (Latin scribal brevigraphs), PUA
codepoints generally. Requiring them invites transcribers and models to hallucinate them out of damaged type.

**Retained**: `ſ`/`s`; `ﬀ ﬁ ﬂ ﬃ ﬄ`; `æ Æ œ Œ`; `ct`/`ſt` ligature **presence-versus-absence as a recorded
fact**; vowel + macron for suppressed nasals, **unexpanded**; `u/v` and `i/j` as printed; `&` and Tironian
forms.

**Added, and genuinely present**: **italic/roman contrast as a semantic** (proper names, quoted Old Testament,
annotations — a transcript that loses font-switching loses real information); small capitals (`LORD`);
swash italic capitals; blackletter in headings; capital `VV` for `W` in display sizes; **turned letters and
wrong-fount sorts, preserved as compositorial evidence**; punctuation practice including the worn-type `?`/`;`
confusion; hyphenation and line-end marks.

**Added as machinery, not glyphs**: an `unclear` / `gap` mechanism (TEI `<unclear cert="">`,
`<gap reason="damage"/>`). Revision 1 had **no way to say "I cannot read this"** — which, with No Silent
Degradation, is a serious omission: an unreadable glyph was being forced into a confident reading.

### 5.2 Making rare classes survivable

`ﬃ ﬄ` and the abbreviation marks occur tens of times corpus-wide. Under CTC a class with under ~100 instances
is essentially never emitted — the loss is lower if the model prints blank plus the frequent neighbour. Codec
size is harmless; the **imbalance** is fatal, and it would silently delete exactly the inventory this project
exists to preserve.

- **Decompose in the codec, compose at output.** NFD the abbreviation marks so `ã ẽ ĩ õ ũ` share one
  U+0304 combining class instead of five rare atoms. Keep `ﬀ ﬁ ﬂ` as atoms; let `ﬃ ﬄ` decompose.
- **Oversample or loss-weight** lines containing rare classes at 10–50×.
- **Pin one Unicode normalisation form** across codec construction, GT files and edit-distance scoring. Mixed
  NFC/NFD silently produces duplicate codec entries and a CER that is simply wrong.
- **Report per-class support** with every per-class metric. Recall on 12 instances is noise.

### 5.3 Ligatures and allographs — a typographic decision, not a decoding one

**The variant-lattice bootstrap of revision 1 is withdrawn.** A CTC model puts posterior mass only on symbols
in its codec, so an untrained `ﬁ` is *unscoreable* rather than low-scoring and the lattice picks `f`+`i` with a
huge margin forever; and even trained, one ligature sort and two kerned sorts explain identical pixels — there
is no likelihood asymmetry to exploit. The `ſ`/`f` case is the same, differing by a nub of a few pixels.

Replaced by evidence that actually discriminates:

1. **Typographic features from the image**: forced-alignment character cuts, connected components, and advance
   width. A ligature is one component on one sort-width; `f`+`i` is two cuts and an `i` that carries a tittle.
2. **A small binary classifier per contested pair**, trained on GOLD-GLYPH crops.
3. **GOLD-GLYPH as the primary path, not a fallback** — with **targeted instance mining** (find candidate
   crops by shape, then key them), because ~200–500 instances *per class* is the requirement and random lines
   will never supply that for `ﬃ ﬄ ſt`.

### 5.4 Model scopes

```
CATMuS-Print [Large]  →  SOURCE  →  TOME
```

**The BOOK level is cut.** Distinguishing 0.60% from 0.50% CER at conventional significance needs on the order
of 10⁵ held-out characters per comparison — ~2,000+ held-out lines per model, times ~440 scopes, which is more
ground truth than this project will ever have. Worse, held-out lines drawn from the same few gatherings share
paper, ink and compositor and are not independent; and the books that would most need a book model are exactly
the ones with no archaic witness and therefore no alignment GT. Adoption at each surviving level requires a
**paired bootstrap over lines, a pre-registered minimum effect size, and a second never-touched confirmation
set** — otherwise the winner's curse guarantees the adopted hierarchy overfits.

**Input height** is swept **jointly with the pooling and filter configuration** (raising H from 120 to 192
under unchanged `Mp2,2` stages changes the receptive-field aspect ratio the filters were fitted for) and is
evaluated **on the `ſ`/`f` and macron classes specifically** — aggregate CER is ~97% dominated by classes that
120 px already handles.

**Ensemble diversity must be real.** Reul found same-parent voters vote worse, and revision 1's voters all
descended from CATMuS. At least one Calamari voter (different framework and architecture), one at a different
input height, one on differently-preprocessed rasters.

### 5.5 The accuracy target — restated so it can fail

The literature I cited does not support 0.5% over a ~400-class diplomatic alphabet on 1582 print: Reul's
sub-0.5% is book-specific models on human-corrected GT with a **small** alphabet, voting away *stochastic*
error; Al Azawi's 0.40% is a **supervised** voter trained on aligned GT. Reporting one aggregate number would
also hide which classes are dead.

| metric | target | measured on |
|---|---|---|
| **CER-folded** (long-ſ, ligatures, `æ` folded) | **≤ 1.0%** per source — comparable to the literature | GOLD-TEXT |
| **CER-diplomatic** (full inventory, nothing folded) | **the noise floor + δ**, where the floor is measured, not assumed | GOLD-TEXT |
| **per-class precision AND recall**, with support and Wilson intervals | per class, no aggregate hiding | GOLD-TEXT + GOLD-GLYPH |
| **macro error over the rare inventory** | class-balanced, so rare classes cannot be averaged away | GOLD-GLYPH |
| **attested-form rate** | proportion of output tokens attested in the archaic lexicon | GOLD-TEXT |

The third and fifth are new and they close a gaming route: per-class **recall alone** rewards a model that
prints `ſ` everywhere, and nothing in revision 1 caught **hallucinated archaisation** — a model inventing
archaic-looking forms would have scored *better* on glyph fidelity.

**And the GT's own error rate is reported alongside.** If GOLD-TEXT's own CER is 1%, a 0.5% target is
unmeasurable in principle, and saying so is not a lowered requirement — it is the requirement becoming
enforceable. **NOISE-FLOOR is measured before the target is fixed.**

---

## 6. STAGE 3 — GROUND TRUTH

Alignment is **intra-page**: concatenate a page's recognized lines into one character stream with
line-boundary offsets, concatenate the chapter's reference likewise, align at character level, project each
line's range onto the reference span it matched, then refine per-character cuts with kraken's
`ForcedAlignmentTaskModel`. Character-level alignment keeps `hea-` and `uen` on their own lines — the
Transkribus Text2Image artefact (hyphenated word assigned wholly to one line, fragment dropped) is avoided by
construction.

**Acceptance, corrected**: a line becomes GT under a strict distance threshold **and** its complement is
recorded — the unaligned residue is kept as a geometry signal (§4.2.3) instead of being silently discarded.

**Substitution costs are derived from the pooled OCR confusion matrix**, not unit-cost Levenshtein, which
cannot align `m`↔`rn`, `ſ`↔`f`, `u`↔`n`, `c`↔`e` correctly.

**Never align against MODERN for character supervision.** Those texts supply word identity, never glyph
identity.

**Pseudo-archaic never enters ground truth.** Revision 1 contradicted itself on this — the diagram fed it into
the GT stream while the text forbade it. Resolved absolutely: it is an **alignment and scoring prior only**,
it is never character supervision, and **it never appears in the transcript**. Synthesised archaic spelling in
a diplomatic edition is fabrication. The 8,383 archaic-less loci are transcribed **from the scans**, which
have those books; where no witness can be read, the transcript records a gap.

---

## 7. THE REFERENCES

**R1 — Renumber first.** Finish `ref_renumber` so `s_dismas` and `odr_com` share one address space. **Gate:**
offset-0 exact-key agreement after renumbering — not best-match, which can be passed by widening
normalisation without fixing a single verse number — with the residue enumerated per book.

**R2 — De-contaminate `s_dismas`** (apparatus splices). Unrepairable loci are **OPEN and blocking**.

**R3 — Collapse to ARCHAIC and MODERN**, adjudicated in batches by sub-agents **after R1 and R2**, or the
adjudicator is fed thousands of pseudo-disagreements (verse offsets, apparatus splices) and will "correct"
sound text onto the wrong verse. MODERN disagreements may be adjudicated by reasoning about sense and
completeness; **ARCHAIC spelling and glyph disagreements consult the scans**, which is where and only where
the six witnesses enter this stage.

**`s_dismas` is demoted from "glyph authority".** It is an unprovenanced modern transcription of unknown base
edition which our own §2.2 shows splices annotation into scripture. **The glyph authority is the image**,
adjudicated against the copy-text page. Both transcriptions become **finding aids** — verse addressing, word
identity, alignment anchors, GT candidate generation. Before any use: a **provenance audit** — 200 verses
sampled against the scans, reporting its `ſ`/`s` accuracy, its ligature policy and its base edition,
published.

**R4 — Pseudo-archaic**, for alignment and scoring only, per §6. **Gate:** rank-1 accuracy *and* mean lattice
size jointly (lattice-containment alone is trivially inflated by widening the lattice), on the 25,892 loci
where the true archaic reading is known.

---

## 8. STAGES 5–7 — LOCATE, COLLATE, ADJUDICATE

### 8.1 Locate

The tome map gives, for every page of every source, its book and chapter — so the lookup is a query, not a
search, and the computational scope collapses to a chapter's worth of leaves. **Iterate the union verse table
(37,166), not ARCHAIC** — revision 1's loop was `for (book, chapter) in ARCHAIC`, which silently dropped the
22.6% of the Bible with no archaic witness, i.e. exactly the books the product must not omit.

**Three independent signals for one address** — tome map (leaves), `VerseNumber` regions (numerals),
alignment (content) — and a disagreement among them is a flag, not an average. The printed numeral does not
decide: **content alignment assigns the address**, because psalm titles counted as verse 1, `xv`/`xu` numeral
misprints, merged and split verses, and chapter-opens mid-page all produce numerals that lie. Revision 1
discarded rare-token anchoring entirely; it returns as a **cheap post-hoc orthology guard** — any witness
whose identity to the emerging consensus falls below threshold is rejected rather than aligned. The tome map's
"100% coverage by construction" is a tautology, not an accuracy claim, and needs a **held-out audit with a
reported page-assignment error rate.**

### 8.2 Collate — a variant graph, not a column matrix

**Per-column character MSA is withdrawn.** The worked counter-example is decisive:

```
w2 ſ o n - -      col3 = {n×5, ñ×1}
w5 ſ o ñ - e      col4 = {n×4, gap×2}     →  restored  ſoñne
```

`ſoñne` is a reading no witness holds and no compositor set. The cause is structural: `æ`↔`ae`, `ﬁ`↔`fi`,
`ã`↔`an`, `&`↔`and` are **1↔2 correspondences** a column matrix cannot express, so every witness downstream of
a ligature shifts one column for the rest of the word.

Revision 2:

1. **Align over an equivalence-class alphabet** — grapheme clusters normalised to expansion-invariant symbols
   — carrying the surface form as a per-witness *attribute* of the cell. Glyph form is decided after the
   reading is settled, by a separate ballot among witnesses that agree on the underlying word.
2. **Partial-order alignment / variant graph** (CollateX-style) rather than reference-first progressive
   alignment. Anchoring the first profile on ARCHAIC is star alignment: it freezes the reference's indel
   structure into the column set, and ARCHAIC is the sequence we *know* carries splices and an 8% numbering
   offset. No guide tree, no reference privilege, transposition-tolerant.
3. **Word-level segmentation first, intra-word alignment second.** Preserving whitespace in the MSA turns
   common word-boundary disagreements into gap runs that dominate the score.
4. **Indels are voted as blocks, not columns.** Deletions are properties of a run (hyphenation, dropped word,
   catchword bleed); per-column voting over a run produces half-deletions.
5. **The hard constraint that kills the chimera class outright: the adjudicated reading must be a path that
   some witness or the copy-text actually supports.**

### 8.3 Adjudicate — under copy-text discipline

Collation **detects**; it does not generate. Where witnesses disagree with the copy-text, the copy-text stands
unless it is illegible or a demonstrable press error, and the emendation is recorded.

Where a decision is genuinely needed:

- **Confidences are calibrated before they are used.** Six models with different parents, heights and codecs
  produce softmax values on incomparable scales; kraken's are CTC per-frame peaks, over-confident on frequent
  classes and near-uniform on rare ones — *inverted* from what a ligature decision needs. Isotonic
  calibration per model per class on held-out GT, converted to **log-likelihood ratios** and summed.
- **Indel columns get an explicit prior.** A character never emitted has no frame and therefore no confidence;
  revision 1 left that as an implicit 0 or 1, a silent policy on the most error-prone column class. Per-model
  insertion/deletion rates estimated from held-out GT.
- **Witness weighting by effective independence.** All six descend from one parent, are trained on GT from one
  alignment, and share one preprocessing path — so majority-of-six is majority-of-about-two. Henikoff
  position-based weighting over the graph, or a measured pairwise error-correlation matrix; **effective N is
  reported per locus alongside the vote.**
- **Image adjudication fires on low LLR margin *and* on a random sample of unanimous loci.** This is the fix
  for the sharpest finding in the review: the training loop makes wrong votes *unanimous*, so a safeguard that
  fires only on close votes is anti-correlated with the failure. The unanimous sample is the **only estimator
  of the correlated-error rate** we will have.
- **A VLM sees a glyph crop, never a page** — the one place a vision model touches the product.

### 8.4 The drift guard, rebuilt

Revision 1's guard protected glyph identity but not spelling (`ſon`→`ſonne` survives a `ſ/s` fold), and did
not guard the training loop at all. The loop: ARCHAIC anchors alignment → aligned lines become GT →
recognizers train on it → the six agree with ARCHAIC *because they were trained on it* → concurrence is easier
→ more write-back → the board rises while the pixels say otherwise.

1. **`ARCHAIC_v0` is frozen permanently** as the alignment anchor. Restorations go to a **separate product
   stream that is never fed back into GT generation.**
2. **The headline metric is GOLD**, which is image-derived, sha-pinned, and never enters GT or write-back.
3. **Every board number is reported against `v0` and against current**, with the write-back delta itemised.
4. **Per-round agreement against GOLD is tracked.** If agreement with gold falls while consensus rises, the
   pipeline is in the loop and it stops.

---

## 9. THE BOARD, AND THE APPARATUS

### 9.1 Board changes

- **The gate correction to archaic-preeminent is not adopted on provenance.** "Approved 2026-07-10" is
  provenance, not evidence, and the party proposing the change benefits from it. Before adoption:
  **blind-adjudicate a random sample (n ≥ 100) of newly-passing cells against the scans** — adjudicator sees
  image and candidate reading, not which gate it passed or which way it moved — with the vindicating pass rate
  **pre-registered**. And the +122 and the −18 are reported **separately against a frozen board**, never
  netted.
- **"WARNING class, not a silent pass" is withdrawn.** It was itself a silent pass: a below-threshold unit
  converted to a terminal non-blocking state, which the project's own rule forbids. A cell passing ARCHAIC
  while failing MODERN badly is **OPEN and blocking**; the warning is the alert, not the disposition.
- **A page axis is added** — every open cell already carries its leaf, and a per-leaf view sorts geometry
  defects to the top by construction.
- **The drop-cap class opens now**, independently of everything else.

### 9.2 The apparatus that makes this citable — absent from revision 1 entirely

Mandatory, and none of it is optional if other scholars are to use the result:

- **Bibliographic identification per source**: STC / ESTC number, repository, shelfmark, scan provenance,
  imperfections and sophistication of the copy.
- **A statement of editorial principles**: what is preserved, what is silently regularised, how line and page
  breaks are treated, the transcription protocol with worked examples.
- **Page and signature references in the output** (`|Aa3v|`, `<pb n=""/>`) — without which no reading can be
  checked against the book.
- **A list of emendations** with siglum and authority; **a record of rejected variants**; **uncertainty
  encoding at every adjudicated locus**, in the published text and not only in internal provenance.
- **A TEI header** with `<sourceDesc>`, `<encodingDesc>`, responsibility statements; a versioned citable
  release.
- **Press variants and stop-press correction** considered explicitly.

---

## 10. BUILD ORDER

| # | step | gate (all on frozen GOLD unless stated) |
|---|---|---|
| **0** | Stage 0 rasters; **JBIG2 substitution test**; 1-bit→uint8 before geometry | substitution rate on `ſ`/`f`, `c`/`e` over 20 pages; manifests complete |
| **1** | **GOLD-TEXT / GOLD-LAYOUT / GOLD-GLYPH / NOISE-FLOOR** | sets frozen and sha-pinned; inter-transcriber floor reported |
| **2** | Ship the drop-cap board fix; add the page axis | 18 cells move to OPEN; board reported before/after |
| **3** | R1 renumber | offset-0 exact-key agreement; residue per book |
| **4** | R2 de-contaminate `s_dismas`; provenance audit of both archaic transcriptions | splice scan clean; audit published |
| **5** | Tome map → chapter→leaf-set, six sources, front/back matter | held-out page-assignment error rate |
| **6** | G1 geometry: ink shapes, text labels, residue-as-signal | per-class recall+precision, boundary error, IoU vs G0, recognizer frozen |
| **7** | G1 recognition: inventory, decomposition, H sweep, hierarchy to TOME | CER-folded ≤1%; CER-diplomatic vs floor; per-class with support |
| **8** | Stage 3 alignment; confusion-derived costs | accepted-line precision on held-out; residue recorded |
| **9** | R3 collapse; R4 pseudo-archaic (priors only) | rank-1 accuracy and lattice size jointly |
| **10** | G2: relabel, retrain, realign | improvement > δ on GOLD or **escalate with the floor attached** |
| **11** | Collate + adjudicate under copy-text; apparatus | path-validity constraint holds; unanimous-sample audit rate; apparatus complete |

Steps 3–5 run in parallel with 1. **Step 1 gates every metric claim in the plan.**

---

## 11. OPEN AND UNMEASURED

JBIG2 symbol substitution (now blocking step 0) · ligature separability by typographic features (§5.3) · input
height jointly with pooling · `ch8/8:14` policy · a 1635 reference, now needed only to *validate* S06 rather
than to build the product · **arXiv:2607.00596 carried from V2 unverified** and load-bearing for §4.2's gate —
resolve or drop before step 6.

## 12. CITATIONS

Resolved this session: arXiv:2112.12703 · arXiv:2511.08903 (**88.2 AP at 5% labels — evidence *for* a seed
set, not against one**) · arXiv:1802.10038 · arXiv:1711.09670 · arXiv:2509.19768 (CHURRO) · kraken docs (VGSL
input height, `ketos segtrain` typology, `ForcedAlignmentTaskModel`) · CATMuS-Print [Large] + guidelines ·
Bollmann & Søgaard 2016; Pettersson et al. 2014; cSMTiser · Al Azawi et al. · Transkribus Text2Image
hyphenation artefact · OmniDocBench / olmOCR-Bench.

**Overreach corrected:** arXiv:2112.12703's leverage was TEI *structural markup* that types regions directly;
our verse-keyed plaintext has no page association, 43.6–69.7% coverage and documented contamination. The claim
"we are a better case than theirs" is **deleted** — four witnesses corroborate *word identity*, never *region
geometry*, because they have different page layouts.
