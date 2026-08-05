# OriginalDR OCR — Overview of the Architecture

**What this document is**: the shape of the thing, and *why* it has that shape. It is the middle altitude —
above the master plan's mechanisms, below the executive summary's decisions. Read `OCR-EXECUTIVE-SUMMARY.md`
first if you have not.

---

## 1. The product, stated so it constrains the design

**One documentary transcript of three printed books** — the 1582 Rheims New Testament, the 1609 Douai Old
Testament volume 1, the 1610 Old Testament volume 2 — **reproducing what those documents print**: archaic
spelling, long-ſ, ligatures as set, `u`/`v` and `i`/`j` as printed, macrons unexpanded, compositorial
accidents preserved.

Three properties of that sentence do almost all the architectural work:

**"Documentary."** We are not reconstructing a lost ideal text from disagreeing witnesses. We are reading
three physical objects. Disagreement between two scans of the *same* setting of type is **a scan-quality
fact, not a textual fact** — so it does not belong in an apparatus, does not need voting, and does not need
witness weighting. This single observation removes about a third of the previous plan.

**"Three books."** Not one. Separate printings, two towns, two houses, 27 years apart, different founts and
compositor conventions. **Three base documents, three sets of spellings, no harmonisation across the
joins** — concatenated into one deliverable, each labelled.

**"What those documents print."** Not what the Douay-Rheims *said* — we have four modern transcriptions for
that, and they are useful, but as **finding aids**, never authorities. The authority is the image. That
demotion is the correction to my largest earlier error, which was letting an unprovenanced modern
transcription (`s_dismas`) govern *glyph* decisions while our own measurements showed it splices editorial
annotation into scripture.

---

## 2. The six scans, and what each is for

| role | which | what it may do |
|---|---|---|
| **base exemplar** | one named copy per bibliographic unit, **still to be declared** (§1 of the plan) | **it is the document.** Everything in the transcript comes from here |
| **same-setting surrogate** | another photograph of the *same* forme | **resolve illegibility. This is transcription, not emendation** |
| **other-edition witness** | the 1633/1635 printings | **supply a reading only when nothing else can**, bracketed, with its own date visible to the reader |

The middle row is the distinction the previous revision had no way to express, and it matters more than it
sounds. Without it, every routine "the base copy is blotted here, the other scan is clean" becomes an
*emendation* — thousands of non-events flooding the apparatus until the handful of real interventions are
unfindable. With it, they go to a lightweight surrogate register that is summarised statistically and never
enumerated.

**Setting identity is proved, not assumed**: same signature, same catchword, **same line-end words**.
Identical ⇒ same setting.

**Consequence to state plainly**: some of the six scans are 1633/1635 and can therefore *never* be a base
document. And where only one scan exists for a given 1609/1610 volume, **the same-setting route is
unavailable there and gaps will be real.** That is a property of the surviving evidence, not a defect to
iterate against.

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

Stage 4 is where the previous plan said *"six transcripts driven to publication quality"*. Stage 6 is where
it said *"per-verse multiple alignment of six witnesses"*. **Those two substitutions are the whole
simplification.**

### The loop, and its two exits

The build order used to be a **cycle**: alignment needs a recognizer, the recognizer needs alignment ground
truth, the region model needs alignment for its labels, and the region model's gate was the board — which
the recognizer produces. There was no entry point, and revision 1 resolved it silently by using the
incumbent geometry, i.e. the thing it claimed to be replacing.

So it is stated as numbered generations — G0 bootstrap, G1, G2 — each gated on **frozen evaluation sets,
never on the board**, which moves between generations. Two rules the previous revision lacked:

- **Two terminals, and they are not the same state.** *Converged-at-target* closes. *Stalled-below-target*
  is **OPEN, blocking, and raises an ALERT that the approach needs redesign — the deliverable does not
  ship.** Collapsing these was how a below-threshold result would have quietly become a terminal accepted
  one.
- **A regression rule.** If a generation is worse than its predecessor by more than the paired confidence
  interval, it is a **failed experiment** — revert, do not adopt, **do not re-baseline.**

---

## 4. The three ideas the architecture actually rests on

### 4.1 The correction loop is simultaneously the product and the ground truth

This is the load-bearing idea, and it is what makes the hours affordable.

```
page → lines → incumbent recognizer → operator correction UI → sha-pinned corrected page
                                            │
        ┌───────────────┬───────────────┬───┴───────────┬────────────────┐
   transcript      evaluation      training GT      layout GT      glyph instances
     (product)        text        (next generation)  (if the UI    (click-to-tag)
                                                    captures boxes)
```

**One activity, five outputs.** The previous plan treated ~200–280 hours of annotation as a prerequisite
stage to be endured before product work could start. Here the same keystrokes produce the transcript. There
is no separate annotation project.

Two supporting mechanisms:
- **A VLM proposes corrections on line crops** — accepted or rejected by keystroke. It sees a crop, never a
  page. That is the only place a vision model touches the product.
- **A rolling held-out set that is free and cannot be gamed**: fine-tune every N signed-off pages, and score
  on **the last 20 signed pages *before* they entered training**. Never stale, no annotation cost, and
  immune to the evaluation-set exhaustion described in §5.

### 4.2 Residue is evidence, not waste

The old acceptance rule discarded lines whose reading was far from the reference. But **that is exactly what
happens when a layout band clips scripture**: the clipped words were never recognised, so the leaf scored
badly and was *censored out of training*. Labels survived only where the incumbent was already right — the
model could only ever learn to reproduce the failure it was supposed to fix.

**Inverted**: the fraction of a chapter's reference text matched by *no* line **localises a missed or
clipped region**. Sorted across leaves, that is a ranked defect queue — which is week 2's deliverable, needs
no ground truth and no new model, and uses the incumbent pipeline **as a detector rather than a generator**
so its bias does not propagate.

One correction from round 2: **that signal is null where there is no reference**, which is precisely the
8,383 loci with no archaic witness. So a **reference-independent** residue signal runs alongside it — ink
groups with no line assignment at all.

### 4.3 Letterpress repeats the same physical sort

The strongest single idea from either critique panel. Per-instance glyph classification throws away the one
real asymmetry the medium offers: **a page was printed from a finite tray of metal sorts, and the same sort
appears thousands of times.** So instead of deciding `ſ` versus `f` instance by instance, **cluster the
candidate crops per fount per exemplar, key ~50 cluster exemplars by hand, and propagate.**

And where a decision genuinely cannot be made, the classifier says so: **`A` / `B` / *indeterminate***,
abstaining into `<unclear>`. The realistic ceiling makes this mandatory rather than optional — clean
instances reach 0.97–0.99, but on the tail that matters (touching type, over-inking, show-through, worn
sorts) it is 0.7–0.85, **and that tail is 10–20% of instances.**

> **An 8% abstention rate on `ſ`/`f` is an honest edition; a 0% one is a fabricated one.**

---

## 5. How the plan keeps itself honest

Two rounds of critique were aimed almost entirely here, so it is worth stating as its own layer.

**Everything is measured against sets built from images, never from pipeline output.** Three tiers, because
**freezing a set stops contamination but does nothing about repeated querying**:

| tier | use | discipline |
|---|---|---|
| DEV | sweeps, iteration, escalation | unlimited |
| VAL | generation-adoption decisions | **budgeted, noised, and the query count is published** |
| HOLDOUT | **opened once, at publication** | the only publishable numbers |

The arithmetic that forced this: the previous plan would have made **~57 adoption queries against one frozen
set**, where the expected maximum of 57 noise draws is **~0.18% apparent improvement from nothing at all** —
larger than any threshold it would plausibly have set. Worse, its first escalation rung was *"annotate more
pages"* — growing the evaluation set in response to failing it.

**Rare classes get a census, not a rate.** Requiring "≥200 instances per class" of classes that occur *tens
of times corpus-wide* is unmeetable, and its escape clause quietly converted it into automatic satisfaction
at n=30. Instead: **key every instance on a declared page set**, so the denominator is page-defined rather
than detector-defined, and **anything below n=30 is UNMEASURABLE — open and blocking, never passed.** A
census is *stronger* than a recall figure on twelve instances.

**Every gate carries five fields** — metric, threshold, named set, n, pre-registered effect size — as a
document-level invariant. The previous revision had two complete rows out of twelve, and **δ, its
convergence criterion in three places, had no value anywhere.**

**Six circularity paths are closed by name**, including the subtle one: deriving alignment costs from the
pipeline's own confusion matrix makes `ſ`↔`f` cheap *because the model confuses them*, so confused lines are
accepted as ground truth and **the confusion is trained in.**

**And escalation now has a receiver.** "Escalate to Sir" was a no-op when Sir is the operator. Every
escalation must now name **a different resource class than the one that failed** — paid annotation hours, a
better scan, an outside palaeographer's ruling, or a stated reduction in **coverage** (fewer books at full
fidelity) — **never a reduction in fidelity.** It writes a dated, numbered ALERT, and the component parks as
OPEN with that number attached.

---

## 6. What the reader of the finished edition gets

- **A transcript addressed physically first**: page and signature as the primary address, verse as the
  secondary logical one, both present on every line, **verse numbering following the base document's own
  numerals** — never silently normalised to modern versification.
- **An uncertainty gradient that never lies**: confident readings plain; uncertain readings *present and
  flagged*; unread positions as **gaps, never guesses**; and supplied text **bracketed in every view**.
- **A bright line on synthesis.** `<supplied>` requires a source pointing at **a document**. Rule-generated
  archaic spelling has no document source, so **it can never appear in the transcript at all** — bracketed
  or otherwise. It survives only as a separately-named reconstruction layer, in its own file, excluded from
  every citable export.
- **An apparatus of interventions only** — most verses produce zero records — plus the one obligation that
  is non-negotiable: **page and signature marks in the text stream, without which no reading can be checked
  against the book.** They must be captured *during* transcription or never.

---

## 7. What is still unknown

**Blocking, and honestly unknown rather than glossed**: **we have not yet established which scan is which
edition.** The source concordance is empty — no STC numbers, no repositories, no shelfmarks. The
constitution is unimplementable until it exists, and I have deliberately not filled it in from memory,
because a hallucinated shelfmark would poison the copy-text choice and everything downstream of it.

Also blocking: one citation carried unverified from V2 that a gate depends on — **resolve or delete** — and
a scan inspection that closes three inventory questions at once (blackletter headings, `ꝛ`, Latin
brevigraphs).

**Open and scheduled**: the JBIG2 substitution test *and* the separate binarisation-transfer gap; whether
sort-clustering propagates as cleanly as the medium suggests; the input-height sweep, now honestly costed at
**120–200 GPU-hours** rather than an incidental line item — because only H=120 warm-starts cleanly from the
pretrained model, and raising it breaks weight transfer at the recurrent stack.
