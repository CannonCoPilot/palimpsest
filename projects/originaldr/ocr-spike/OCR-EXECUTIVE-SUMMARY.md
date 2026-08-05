# OriginalDR — Executive Summary

**The objective**: a faithful documentary transcript of the first-edition Douay-Rheims Bible — the **1582
Rheims New Testament**, the **1609 Douai Old Testament volume 1**, and the **1610 Douai Old Testament
volume 2** — in archaic typeset and archaic spelling, recovered from photographic surrogates.

Companion documents: `OCR-OVERVIEW.md` (architecture) · `OCR-WALKTHROUGH.md` (how it runs) ·
`OCR-MASTERPLAN.md` (the plan).

---

## 1. What this is, and what it is not

**It is a documentary edition** — we read three physical books and reproduce what they print. **It is not a
critical edition**: there is no authorial revision to reconcile, no lost archetype to reconstruct, no
construction of a text from witnesses of competing authority. That distinction removes machinery that would
otherwise be mandatory — sigla, historical collation, rejected-reading registers, authority chains — none of
which serves a transcript of a single printing.

The consequence that matters most: **disagreement between two photographs of the same setting of type is a
scan-quality fact, not a textual one.** It needs no apparatus and no voting.

## 2. The corpus: three volumes, three copies each

Nine scans, all copies of one first-edition printing per volume. Two files are excluded deliberately — the
**1633 Rheims NT** (a second edition, whose admission would require a full witness apparatus for no gain)
and a **1610 whole-Bible facsimile**.

**Two measured facts reshape the plan:**

**The S01 set cannot do diplomatic work.** It is uniformly 800 × 1124 px across all three volumes — about
**168 ppi at the leaf, against 650 ppi for S09**. The long-ſ is distinguished from `f` by a nub of 3–6 px at
650 ppi; at 168 ppi that feature spans **under 1.6 px** and is simply not present in the file. S01 is
therefore **structure-only** — page order, addressing, gross verification — and is **disqualified as a base
exemplar and as training data.** That is a measurement, not a preference.

**`NT/S08` is the only continuous-tone scan in the corpus.** Every other copy is an MRC composite whose text
layer is a 1-bit JBIG2 mask, and binarisation destroys grey levels *upstream* of anything repairable later.
This makes S08 the natural base for the New Testament.

**So each volume has two usable copies, not three** — one base, one same-setting surrogate for resolving
illegibility.

## 3. How it works

**The correction loop is both the product and the ground truth.** A page goes through the recognizer, a
vision model proposes corrections on **line crops**, the operator accepts or retypes by keystroke, and the
signed-off page becomes — from the same keystrokes — the transcript, the evaluation text, the training
ground truth, the layout ground truth, and glyph instances. **There is no separate annotation project**,
which is the only reason the annotation is affordable.

**Residue is evidence.** The fraction of a chapter's reference text matched by *no* recognised line
localises a clipped or missed region. Ranked across leaves, that is a defect queue — needing no ground truth
and no new model, so it is the first real improvement to ship.

**Letterpress repeats the same physical sort.** Rather than classify `ſ` instance by instance, cluster the
candidate crops per fount per volume, key ~50 cluster exemplars, and propagate. This is the strongest lever
available, and it is unavailable to per-instance methods.

**And the recognizer may say it cannot tell.** Contested pairs emit `A` / `B` / *indeterminate*, abstaining
into `<unclear>`. On clean type the pair classifiers reach 0.97–0.99; on the difficult tail — touching,
over-inked, show-through, worn — 0.7–0.85, and that tail is 10–20% of instances.

> **An 8% abstention rate on `ſ`/`f` is an honest edition; a 0% one is a fabricated one.**

## 4. Training is organised by volume

The three volumes are **three different printings** — Rheims 1582 under one house, Douai 1609 and 1610 under
another, 27 years apart, different founts and compositor conventions. So:

```
CATMuS-Print [Large]  →  VOLUME  →  FOUNT
```

**VOLUME is the letterform boundary.** **FOUNT** — roman text, italic annotation, display — is the
letterform boundary *within* a volume, and the same axis the rendition layer already treats as semantic.

**COPY is not a model level.** Three copies of a volume photograph the same setting of the same type; they
differ in resolution, structure and skew — image statistics, not letterforms. Fitting a model per photograph
of one book would be a category error. Instead **copies are pooled within a volume as training
augmentation**, which is a genuine advantage of this corpus: *identical letterforms under different imaging
conditions* is exactly the invariance a recognizer should learn, and it is normally expensive to obtain.

Held-out splits are stratified **by copy and by gathering** — never by page, since adjacent leaves of one
gathering share paper, bleed-through, skew and the same forme.

> **Note on earlier naming.** Legacy identifiers (`archive-*`, `jp2-*`, `pdf-*`) describe *how a file was
> acquired*, not which book it is — and two of them each contain **all three volumes**. Training "per
> source" would therefore have pooled 1582 Rheims types with 1609/1610 Douai types into one model. The
> addressing unit is now `VOLUME/COPY`.

## 5. The archaic typeset census

**Before the codec is fixed, the inventory is established empirically** — surveyed from the actual type in
each volume, given a representation, then frozen. A class the model never sees cannot be output; a class
asserted but absent invites the model to hallucinate it out of damaged type.

Every requested sort is resolved **ATTESTED or NOT FOUND, per volume**, with an image exemplar and a
frequency count: the `ct`, `æ`, `ﬁ`, `ﬂ`, `ﬀ`, `ſt`, `ſl`, `ſh`, `ſſ` ligatures, long-ſ, and the `ã õ ũ`
suppressed-nasal vowels — plus the **note-reference marks** (`*`, `†`, `‡`, `¶`) without which the
annotation cannot be keyed to the text, and in this edition **the annotation is roughly half the book**.

Three items need the survey to settle them rather than an assumption:

- **"tall-s" versus "long-s"** — early-modern founts normally carry two s-sorts, round `s` and long `ſ`. If
  the census finds only two, these are one sort under two names and the rows merge. The same question
  governs the `ſt`, `ſl` and `ſſ` entries listed twice.
- **"long-f"** — there is no long-f sort as such, and two different things produce that impression. One is
  an `f` inside a ligature. The other is real and important: **some founts cut the long ſ with a full
  crossbar rather than a left-side nub**, making it near-indistinguishable from `f`. **If that allograph is
  attested it needs its own class**, because it defeats nub-based discrimination entirely — which would
  otherwise be a silent, systematic error across a whole volume.
- **`ꝛ` and the Latin brevigraphs `ꝑ ꝓ ꝗ`** — entangled with whether these founts set any blackletter at
  all. One inspection closes all three.

## 6. On connected components — a correction

An earlier draft asserted that connected-component analysis fails outright, because at 650 ppi a well-inked
line is largely one connected component. **That over-stated the case, and the plan now reflects the
correction.**

It remains true that ink load and paper absorbency drive whether adjacent sorts touch, so **CC count alone
decides nothing.** But **the pairs that ligature are a small closed set, and a ligature sort is a distinct
piece of type with its own form** — not two letters that happen to collide. That yields three real
advantages, and the method now uses them:

1. **A tiny hypothesis space** — never "which of 400 classes," only "is this the `ﬁ` sort, or `f` followed
   by `i`."
2. **False-positive control by construction** — a ligature can only be proposed where its constituent
   letters are expected.
3. **Revisability** — because the set is closed, every decision for a class can be re-swept corpus-wide when
   that class's classifier improves. Ligature decisions become **revisable data, not irreversible
   transcription events.**

Connected components are therefore used as a **candidate detector within the closed set**, with a per-pair
CNN deciding on the crop and abstaining when it cannot.

## 7. What ships, and when

| when | what |
|---|---|
| **week 1** | source concordance and base-exemplar declaration; drop-cap board fix (**18 cells**); page axis |
| **week 2** | **residue detector** — ranked defect queue, no ground truth, no new model |
| **week 2–3** | **archaic typeset census** — the frozen inventory the codec is built from |
| **week 3+** | **correction loop on Micheas**, producing transcript and ground truth together |
| later | frozen evaluation sets, G1 geometry and recognition, glyph census, the edition |

**The pilot book is Micheas (Micah) in OT2** — 7 chapters across about 7 leaves, present in all three OT2
copies. Chosen because it has **no archaic reference witness**, so it exercises the part of the corpus that
is structurally invisible to every reference-based mechanism and would otherwise be discovered last; because
at roughly one chapter-open per leaf it is an unusually dense test of the drop-cap and chapter-heading
machinery; and because it is small enough to finish early. **Joel** (3 chapters, ~5 leaves) and **Amos**
(9 chapters, ~11 leaves) are the smaller and larger alternatives in the same condition.

**The honest total cost**: ~3,000–4,500 pages at 6–15 min/page corrected = **400–1,000 hours**. That is the
price of this product under any architecture. The design does not remove those hours; it makes them produce
the deliverable directly rather than producing the instrument that produces it.

## 8. How the plan keeps itself honest

- **Three evaluation tiers with a published query ledger** — freezing a set stops contamination but not
  repeated querying; at realistic set sizes ~57 adoption queries yield ~0.18% apparent improvement from
  noise alone.
- **Rare classes get a census, not a rate** — every instance on a declared page set, so the denominator is
  page-defined rather than detector-defined. **Below n=30 a class is UNMEASURABLE: open and blocking.**
- **Every gate carries metric, threshold, named set, n, and a pre-registered effect size**, as a
  document-level invariant.
- **Two terminals, never one** — *converged-at-target* closes; *stalled-below-target* is **open, blocking,
  and raises an alert that the approach needs redesign.** No below-threshold result is ever given a terminal
  accepted state.
- **Escalation must name a different resource class than the one that failed** — paid hours, a better scan,
  an outside ruling, or reduced **coverage** — **never reduced fidelity.**

## 9. Open

**Blocking**: the bibliographic concordance — edition, STC/ESTC, repository and shelfmark are unresolved for
all nine copies, and are deliberately **not** filled in from inference, because a misattributed shelfmark
would poison the base-exemplar choice and everything downstream. One citation carried from earlier work is
unverified and load-bearing for a geometry gate: resolve or delete. And the typeset census, which also
closes the `ꝛ` / brevigraph / blackletter questions.

**Unratified**: the archaic-preeminent board gate, pending blind adjudication of n ≥ 100 newly-passing cells
against the scans.
