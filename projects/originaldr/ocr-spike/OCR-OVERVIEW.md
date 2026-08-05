# OriginalDR — Overview of the Architecture

**What this document is**: the shape of the system, and why it has that shape. Above the master plan's
mechanisms, below the executive summary's decisions. Read `OCR-EXECUTIVE-SUMMARY.md` first.

---

## 1. The product, stated so it constrains the design

**One documentary transcript of three printed books** — the 1582 Rheims New Testament, the 1609 Douai Old
Testament volume 1, the 1610 volume 2 — **reproducing what those documents print**: archaic spelling,
long-ſ, ligatures as set, `u`/`v` and `i`/`j` as printed, suppressed nasals unexpanded, compositorial
accidents preserved.

Three properties of that sentence do most of the architectural work.

**"Documentary."** We are not reconstructing a lost ideal text from disagreeing witnesses; we are reading
three physical objects. Disagreement between two photographs of the *same* setting of type is **a
scan-quality fact, not a textual fact** — so it needs no apparatus, no sigla, and no voting.

**"Three books."** Not one. Separate printings, two towns, two houses, 27 years apart, different founts and
compositor conventions. **Three base documents, three sets of spellings, no harmonisation across the
joins** — concatenated into one deliverable, each labelled.

**"What those documents print."** Not what the Douay-Rheims *said* — four modern transcriptions answer that,
and they are useful, but as **finding aids**, never authorities. The authority is the image.

---

## 2. The corpus, and what each copy is for

**Nine scans: three volumes × three copies**, all of one first-edition printing per volume.

| volume | copies | base candidate |
|---|---|---|
| **NT 1582** | S01, S08, S09 | **S08** — the only continuous-tone scan in the corpus |
| **OT1 1609** | S01, S03a, S09 | **S09** — 650 ppi |
| **OT2 1610** | S01, S03b, S09 | **S09** — 650 ppi |

**Excluded**: the 1633 Rheims NT (second edition) and a 1610 whole-Bible facsimile. Admitting a second
edition would require a witness typology, sigla, and an apparatus of readings supplied across settings —
cost that buys nothing for a first-edition documentary transcript.

**S01 is structure-only.** At 800 × 1124 px it resolves to roughly 168 ppi at the leaf, against 650 ppi for
S09. The feature distinguishing long-ſ from `f` — a nub of 3–6 px at 650 ppi — spans under 1.6 px there.
It can order pages and verify addressing; it cannot carry a diplomatic reading, and it is not training data.

**So each volume has two usable copies**, which maps exactly onto the two roles the constitution defines:

| role | what it may do |
|---|---|
| **base exemplar** | **it is the document.** Everything in the transcript comes from here |
| **same-setting surrogate** | **resolve illegibility — this is transcription, not emendation** |

The second role is the distinction that keeps the apparatus usable. Without it, every routine "the base copy
is blotted here, the other is clean" becomes an *emendation*, and thousands of non-events bury the handful
of real interventions. With it, they go to a lightweight surrogate register, summarised statistically and
never enumerated.

**Setting identity is proved, not assumed**: same signature, same catchword, **same line-end words**.

---

## 3. The pipeline

```
 0  ACQUIRE      volume → verified native rasters, grayscale primary
 1  GEOMETRY     page → typed region polygons (shapes from ink, labels from text)
 2  RECOGNISE    region → lines → diplomatic text + a stand-off rendition layer
 3  GROUND TRUTH forced alignment → line GT;  text-side mining → glyph GT
 4  TRANSCRIBE   the base document, corrected page by page, signed off
 5  LOCATE       page/signature primary address · verse secondary
 6  CONSULT      flagged loci only → surrogate register or intervention apparatus
 7  PUBLISH      transcript + minimal apparatus, versioned and sha-pinned
```

### Generations, and their two exits

Build order would otherwise be circular — alignment needs a recognizer, the recognizer needs alignment
ground truth, the region model needs alignment for its labels. So the work is stated as numbered
generations, each gated on **frozen evaluation sets, never on the campaign board**, which moves between
generations.

- **Two terminals, and they are not the same state.** *Converged-at-target* closes. *Stalled-below-target*
  is **open, blocking, and raises an alert that the approach needs redesign — the deliverable does not
  ship.** Collapsing these is how a below-threshold result quietly becomes an accepted one.
- **A regression rule.** If a generation is worse than its predecessor by more than the paired confidence
  interval, it is a **failed experiment** — revert, do not adopt, **do not re-baseline.**

---

## 4. The four ideas the architecture rests on

### 4.1 The correction loop is simultaneously the product and the ground truth

```
page → lines → recognizer → operator correction UI → sha-pinned corrected page
                                      │
      ┌───────────────┬───────────────┼───────────────┬────────────────┐
 transcript      evaluation      training GT      layout GT      glyph instances
   (product)        text       (next generation)  (line/region      (click-to-tag)
                                                     boxes)
```

**One activity, five outputs.** Annotation is not a prerequisite stage to be endured before product work
begins — the same keystrokes produce the transcript. There is no separate annotation project.

Two supporting mechanisms:
- **A vision model proposes corrections on line crops** — accepted or rejected by keystroke. It sees a crop,
  never a page. That is the only point at which a vision model touches the product.
- **A rolling held-out set that is free and cannot be gamed**: fine-tune every N signed-off pages, and score
  on **the last 20 signed pages *before* they entered training.** Never stale, no annotation cost, and
  immune to evaluation-set exhaustion because each slice is used exactly once.

### 4.2 Residue is evidence, not waste

An acceptance rule that discards lines reading far from the reference **censors exactly the failure it
should detect**: when a layout band clips scripture, the clipped words were never recognised, so the leaf
scores badly and drops out of training. Labels survive only where the incumbent was already right, and the
model can only learn to reproduce the failure.

**Inverted**: the fraction of a chapter's reference text matched by *no* line **localises a missed or
clipped region.** Sorted across leaves, that is a ranked defect queue — needing no ground truth and no new
model, and using the incumbent pipeline **as a detector rather than a generator**, so its bias does not
propagate.

Because that signal is null where there is no reference — precisely the 8,383 loci with no archaic witness
— a **reference-independent** residue runs alongside it: ink groups with no line assignment at all.

### 4.3 Letterpress repeats the same physical sort

A page was printed from a finite tray of metal sorts, and **the same sort appears thousands of times.** So
rather than deciding `ſ` versus `f` instance by instance, **cluster the candidate crops per fount per
volume, key ~50 cluster exemplars by hand, and propagate.** Per-instance classification throws away the one
real asymmetry the medium offers.

Where a decision genuinely cannot be made, the classifier says so: **`A` / `B` / *indeterminate***,
abstaining into `<unclear>`. This is mandatory rather than optional, because the ceiling makes it so — clean
instances reach 0.97–0.99, but the difficult tail (touching type, over-inking, show-through, worn sorts)
runs 0.7–0.85, **and that tail is 10–20% of instances.**

### 4.4 The ligature set is closed, and that is the lever

The ligature sorts of a fount are few, known, and **cut as distinct shapes** — a ligature is a different
piece of type, not two letters that happen to touch. Ink load does drive whether adjacent sorts collide, so
connected-component *count* decides nothing on its own. But working from the closed set gives three things
open-set classification cannot:

1. **A tiny hypothesis space** — the question is never "which of 400 classes," only "is this the `ﬁ` sort or
   `f` followed by `i`."
2. **False-positive control by construction** — a ligature is proposed only where its constituent letters
   are expected.
3. **Revisability** — every decision for a class can be re-swept corpus-wide when that class's classifier
   improves, making ligature decisions **revisable data rather than irreversible transcription events.**

Connected components therefore serve as a **candidate detector within the closed set**, with a per-pair CNN
deciding on the crop.

---

## 5. Scope: volume, fount, and why copy is neither

```
CATMuS-Print [Large]  →  VOLUME  →  FOUNT
```

**VOLUME** is the letterform boundary — three printings, two houses, 27 years apart.
**FOUNT** — roman text, italic annotation, display — is the letterform boundary *within* a volume, and the
same axis the rendition layer treats as semantic.

**COPY is not a model level.** Three copies photograph the same setting of the same type; they differ in
resolution, MRC structure, colour and skew — image statistics, not letterforms. Fitting a model per
photograph of one book would be a category error.

Instead **copies are pooled within a volume as training augmentation.** This is a real advantage of the
corpus: *identical letterforms under different imaging conditions* is precisely the invariance a recognizer
should learn, and it is normally expensive to obtain. **Held-out splits are stratified by copy and by
gathering** — never by page, since adjacent leaves of a gathering share paper, bleed-through, skew and the
same forme.

**BOOK is not a scope**: separating 0.60% from 0.50% CER needs ~10⁵ held-out characters per comparison, more
than this project will hold — and the books that would most need a book model are exactly those with no
archaic reference and therefore the least alignment ground truth.

---

## 6. The typeset census — the inventory comes before the codec

A class the model never sees cannot be output; a class asserted but absent invites hallucination out of
damaged type. So the inventory is **surveyed from the actual type**, per volume, then frozen: sample a
stratified page set, enumerate what is present and at what frequency, assign each attested sort a
representation (standard Unicode and combining marks, **no Private Use Area**), adjudicate the ambiguous
pairs by inspection, and record every *surveyed, not found* so the question is closed rather than left open.

**Ligature presence versus absence is itself recorded data** — whether the compositor set `ct` or `c`+`t` at
a locus is a fact about the forme, not noise to normalise away.

**Style is not part of the codec.** Italic, small capitals, swash, blackletter and `VV` are **rendition
states of characters**; a turned `u` standing for `n` is a **defect in a sort**, not a glyph. Admitting them
as classes would multiply the alphabet and destroy the rare-class budget. They live in a **stand-off
rendition layer**: a plain grapheme channel with a stable character index, a parallel span table over that
index, a separate word-level font classifier over the line image, and **two-channel scoring** — CER on
characters, span F on rendition, never folded together.

---

## 7. How the plan keeps itself honest

**Everything is measured against sets built from images, never from pipeline output.** Three tiers, because
**freezing a set stops contamination but not repeated querying**:

| tier | use | discipline |
|---|---|---|
| DEV | sweeps, iteration, escalation | unlimited |
| VAL | generation-adoption decisions | **budgeted, noised, query count published** |
| HOLDOUT | **opened once, at publication** | the only publishable numbers |

The arithmetic forcing this: ~57 adoption queries against one frozen set, where the expected maximum of 57
noise draws is **~0.18% apparent improvement from nothing at all** — larger than any threshold worth
setting. And "annotate more pages" is not an escalation rung when the pages would grow the set being failed.

**Rare classes get a census, not a rate.** Requiring "≥200 instances" of classes occurring tens of times
corpus-wide is unsatisfiable, and mining with the detector under evaluation makes misses invisible. Instead:
**key every instance on a declared page set**, so the denominator is page-defined; **below n=30 a class is
UNMEASURABLE — open and blocking.** A census is *stronger* than a recall figure on twelve instances.

**Every gate carries five fields** — metric, threshold, named set, n, pre-registered effect size — as a
document-level invariant.

**Circularity is closed path by path**, including the subtle one: deriving alignment costs from the
pipeline's own confusion matrix makes `ſ`↔`f` cheap *because the model confuses them*, so confused lines are
accepted as ground truth and **the confusion is trained in.**

**Escalation names a different resource class than the one that failed** — paid annotation hours, a better
scan, an outside palaeographer's ruling, or a stated reduction in **coverage** (fewer books at full
fidelity) — **never a reduction in fidelity.** It writes a dated, numbered alert, and the component parks as
open with that number attached.

---

## 8. What the reader of the finished edition gets

- **A transcript addressed physically first**: page and signature as primary, verse as secondary, both on
  every line, **verse numbering following the base document's own numerals** — never silently normalised to
  modern versification.
- **An uncertainty gradient that never lies**: confident readings plain; uncertain readings *present and
  flagged*; unread positions as **gaps, never guesses**; supplied text **bracketed in every view**.
- **A bright line on synthesis.** `<supplied>` requires a source pointing at **a document**. Rule-generated
  archaic spelling has no document source, so **it can never appear in the transcript at all.**
- **An apparatus of interventions only** — most verses produce zero records — plus the one non-negotiable
  obligation: **page and signature marks in the text stream**, without which no reading can be checked
  against the book. They are captured *during* transcription or never.

---

## 9. What is still unknown

**Blocking**: which scan is which edition. The bibliographic concordance is empty — no STC numbers, no
repositories, no shelfmarks — and it is deliberately not filled in from inference, because a misattributed
shelfmark would poison the base-exemplar choice and everything downstream. Also: one citation carried from
earlier work that a geometry gate depends on (**resolve or delete**), and the typeset census, which closes
the `ꝛ` / brevigraph / blackletter questions together.

**Open and scheduled**: JBIG2 substitution and the separate binarisation-transfer gap; whether sort
clustering propagates as cleanly as letterpress suggests; the input-height sweep, honestly costed at
**120–200 GPU-hours** — because only the incumbent height warm-starts cleanly from the pretrained model, and
raising it breaks weight transfer at the recurrent stack.
