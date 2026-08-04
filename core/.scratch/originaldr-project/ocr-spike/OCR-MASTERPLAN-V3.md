# OCR MASTERPLAN v3 — the trained pipeline

**Written 2026-08-03**, revising `OCR-MASTERPLAN-V2.md` against thirteen questions from Sir and a fresh
literature pass. V2's evidence base (§1) stands and is not repeated; V2 §6's pinned negative results stand and
are carried forward. **What changes in v3 is the answer to "who produces the training data", and it changes
almost everything downstream.**

Every external claim below carries a citation, and §18 records which were resolved *this* session versus
carried forward from V2's research pass unverified. Where a question could not be settled from the literature
it is marked **UNMEASURED** and given an experiment, not an opinion.

---

## 0. THE ONE-PARAGRAPH SUMMARY OF WHAT CHANGED

V2 said: train a region model on 30–50 pages annotated by hand in LAREX. That was the plan's critical path and
its largest human cost. **It is now deleted.** We do not need a human to draw the regions, because we already
possess the two things distant supervision requires — a known text and a text-to-image alignment — and the
published precedent for exactly this move is validated on half a million pages of the Deutsches Textarchiv
(arXiv:2112.12703, *Digital Editions as Distant Supervision for Layout Analysis of Printed Books*). The
campaign's 371 hand-measured constants stop being the layout model and become the **seed and the referee** for
one that is machine-generated at corpus scale. Human effort moves from *producing* labels to *adjudicating
disagreements*, and even that is delegable to sub-agents under an objective test. Downstream, four further
changes follow from Sir's questions: a **pseudo-archaic reference** that backfills 8,383 loci where no archaic
witness exists; a **glyph inventory** wider than long-ſ, learned through variant lattices rather than declared
by rule; **collapsed but variant-carrying** MODERN and ARCHAIC references; and a **hierarchical recognizer
registry** where the most specific model that is *measured* to beat its parent wins.

---

## 1. THE THIRTEEN QUESTIONS — answers first, detail after

| # | Sir's question | answer | where |
|---|---|---|---|
| 1 | How do we train geometry without a human bottleneck? | **Distant supervision + agent fusion.** Labels derive from text we already have; agents vote, they do not decide | §3 |
| 2 | Archaic↔modern dictionary and pseudo-archaic backfill | **Adopted, sized at 8,383 loci.** Built from token alignment, extended by character-level SMT | §4 |
| 3 | More archaic characters, fully trained | **Adopted via variant lattices** — the image decides the allograph, not a rule | §5 |
| 4 | Reconcile the reference pairs, collapse to two | **Adopted with one amendment**: collapsed references must carry their variants | §6 |
| 5 | Per source × volume × book training sets | **Adopted**, automated off the tome map; sampler specified | §7 |
| 6 | Re-download S06 as JPEG | **DONE** — `fetch_s06_jpg.py`, verified by magic bytes, running | §8 |
| 7 | No silent failure on the region model | **Adopted, with a named escalation ladder** and an anti-overfit rule for hybrids | §9 |
| 8 | Per-book/per-source models, not one corpus model | **Adopted as a hierarchy**, because per-book models need per-book ground truth | §10 |
| 9 | Target 0.5% CER | **Achievable and validated** — but only with ensemble voting, and only if CER is measured on the full glyph inventory | §11 |
| 10 | Revise Stage 3 for the polished archaic reference | **Rewritten** | §12 |
| 11 | What actually gets aligned, line to verse? | **Neither — align two character streams and project onto line boundaries** | §12.2 |
| 12 | Escalated geometry review; page or chapter gating? | **Both: a geometry rung is added, and the board gains a page axis** | §13 |
| 13 | Run every VLM, restore lost glyphs by rule? | **Run them all, yes. Restore by rule, no** — restoration must be witness-attested | §14 |

---

## 2. THE SEVEN STAGES, v3

```
 0  ACQUIRE      volume → verified page rasters                            [exists; S06 refetched]
 1  GEOMETRY     page → typed region polygons                              [TRAINED, distantly supervised]
 2  RECOGNISE    region → lines → diplomatic text over a wide glyph set    [hierarchical model registry]
 3  ALIGN        ARCHAIC/pseudo-archaic ↔ lines → line GT + glyph GT       [the engine everything feeds on]
 4  ASSEMBLE     lines → verses                                            [folds forward, region-aware]
 5  ESCALATE     weak cells → geometry rung / recognition rung / consensus [re-targeted, two rungs]
 6  SCORE        verses vs TWO references → board + validity audits        [gate corrected, page axis added]
```

The dependency that governs the build order: **Stage 3 is upstream of everything, including Stage 1.** The
alignment engine is what converts a known text into labels, and labels are what Stages 1 and 2 consume. V2 put
alignment third by leverage; v3 puts it first by dependency.

---

## 3. STAGE 1 — GEOMETRY, TRAINED WITHOUT A HUMAN ANNOTATOR (Q1, Q7)

### 3.1 Why the annotation bottleneck is removable

A region label is a polygon plus a class. We can derive both from things already on disk:

| region class | how its label is DERIVED, with no human drawing it |
|---|---|
| **MainText** | lines whose tokens align to the ARCHAIC reference for a verse of this chapter (Stage 3 gives the alignment) |
| **Marginalia** | lines whose tokens align to `madueke_b`'s **1,334 transcribed apparatus blocks** (`apparatus_crossmap.py`) rather than to scripture |
| **RunningHead** | first-band line matching the book's head form, corroborated by recurrence at the same y across the gathering |
| **VerseNumber** | numeric tokens whose value matches the verse the adjacent aligned text belongs to |
| **Argument** | italic block between a `CHAP. N.` line and the first aligned verse — the position is already in `CHAPTER_MODEL` |
| **Catchword** | last line, single token, equal to the first token of the next leaf — a self-verifying test |
| **Signature** | last line, short, matching the gathering's alphabetic sequence |

Every one of those is a *text* test, and we have the text. This is precisely the distant-supervision argument
of arXiv:2112.12703, which trained layout models for printed books from the semantic markup of digital
editions and validated at DTA scale. Our situation is strictly better than theirs in one respect — we have
four independent witnesses of the same text, so a label can be *corroborated across witnesses* before it is
trusted.

**And we already hold a seed set nobody has to make**: 371 hand-measured `PAGE_OVERRIDE` bands, each one the
product of a campaign walk and most of them measured against outcomes. Those are not annotations of the kind
LAREX produces — they are horizontal bands, not polygons — but they are correct where they were measured, and
they bootstrap the first iteration.

### 3.2 The agentic layer, and the discipline that makes it safe (Q1)

Sir asked for sub-agents handed a page, deriving layout, block types, book and chapter. That is buildable, and
there is a published precedent: **LLM-Guided Probabilistic Fusion** (arXiv:2511.08903) queries an LLM over OCR
text blocks to identify structural regions, then fuses those proposals with a teacher detector's predictions
by confidence-weighted alignment to produce pseudo-labels for a student — reaching 88.2 AP on PubLayNet with
**5% of the labels**. The operative word is *fusion*. The LLM is a voter, not an oracle.

**The rule I will not design around: an agent cannot certify its own layout claim.** This project's entire
record of trustworthy negative results comes from refusing exactly that move — `s6_bounds_probe` proposed
importing all 88 of ch23 p89's note tokens into scripture and was overruled by line-membership; the ch5
left-column sweep was convincing, was applied to 73 leaves, and cost 24 cells. An agent that reads a page and
says "the marginalia is at 0.10–0.21" is producing a *hypothesis with no orthogonal corroborator*, which is
the same class of evidence that has been wrong every time it was trusted alone.

So the agent pipeline is built as a three-signal fusion, and a label is emitted only where two of three agree:

```
  SIGNAL A  distant supervision   text alignment says these lines are scripture / apparatus / head
  SIGNAL B  agent proposal        a sub-agent sees the page image and proposes typed polygons
  SIGNAL C  geometric prior       the incumbent band + the leaf's parity/gathering position
        ↓
  FUSION    2-of-3 agreement → label emitted;  1-of-3 or a 3-way split → DISPUTED queue
        ↓
  OBJECTIVE TEST  the emitted label set is adopted only if a model trained on it moves the BOARD
```

The DISPUTED queue is where human attention goes — and it is bounded, auditable, and mostly delegable to a
second-round agent given the *specific* disagreement rather than a whole page. This is the answer to "avoid
human-review-as-prerequisite": review is not a gate on producing labels, it is a gate on the *residual*.

### 3.3 The sample (Q1, Q5)

Kraken's documentation gives no fixed page count and says the amount needed is variable, generated from pages
typographically similar to the target. That is unhelpful as a target and helpful as a warning: **similarity is
per source and per tome, so the sample must be stratified that way.** With distant supervision the cost of a
page is near zero, so the sample is sized by *coverage of layout types*, not by annotation budget:

- **Every source × every tome × every book**, per Sir's instruction, drawn from the tome map (§7).
- Within a book, stratified by **leaf type**: ordinary, chapter-open, argument-bearing, annotation-heavy,
  frontmatter, backmatter, plate/illustrated, and the two parity classes for sources that alternate.
- Deliberate over-sampling of the classes the literature says are hardest: **marginalia is the worst-detected
  class for document detectors on historical material** (arXiv:2607.00596), so it gets weighted sampling and a
  gate of its own.
- A **held-out set chosen before training**, never re-drawn. `ketos segtrain` allocates 90/10 by default and
  the docs recommend supplying your own evaluation set when infrequent classes are present — which is exactly
  our case, so we always pass `-e`.

### 3.4 Build steps — Stage 1

1. **`region_labels.py`** — emit typed polygons per leaf from signals A and C, with a per-label confidence and
   the reason it was assigned. Read-only over existing artifacts. Output PageXML (kraken's native input).
2. **`region_agent_fusion.py`** — dispatch leaves to sub-agents in batches; collect typed-polygon proposals;
   fuse 2-of-3; write the DISPUTED queue with the specific conflict, not the page.
3. **Corroborate across witnesses** — the same chapter on four sources should yield the same *classes* in the
   same reading order. A class present on one witness and absent on three is a defect in the label, not an
   edition fact, and goes to DISPUTED.
4. **`ketos segtrain`** from kraken's general segmentation model (Zenodo 10.5281/zenodo.14602569),
   `--resize both -i`, `-q early`, explicit `-e` held-out set, one model **per source × tome** to start (§10).
5. **Shadow-run** against `PAGE_OVERRIDE` on the whole Genesis board, cell for cell.
6. **Gate**, per class and separately: marginalia recall, MainText boundary error, **and the board.**

### 3.5 No silent failure — the escalation ladder (Q7)

Sir's instruction is exact and I am adopting it verbatim as policy: **we train, run and retrain until the
region model beats `PAGE_OVERRIDE`.** A below-gate model is never adopted to unblock anything, and "the method
cannot reach it" means redesign the method. The ladder, in order, each rung measured:

1. More data on the failing class (weighted resampling of the leaf types where it loses).
2. Split the model scope finer — source × tome → source × tome × book (§10's rule applies to segmenters too).
3. Fix the labels, not the model: sample the DISPUTED queue and ask whether the *supervision* is wrong.
4. Change the typology: merge classes the model confuses and cannot be taught to separate (`--merge-regions`),
   **and record the merge as a loss of resolution, not as a success.**
5. Re-examine the input: deskew becomes available here (V2 §6 pinned it as unusable against *fractional*
   bounds; polygons remove that objection and the experiment is re-run, not assumed).
6. Change the architecture: a detector trained on region crops (DocLayout-YOLO class) as a second voter, fused
   as in §3.2. Note RT-DocLayout (arXiv:2606.23344) and GutenOCR (arXiv:2601.14490) as current grounded-layout
   baselines worth testing rather than adopting on reputation.

**The anti-overfit rule for hybrids.** If we end up keeping constants on some leaves and the model on others,
that split must be decided by a rule fixed *in advance* (e.g. "constants win on leaves whose class the model
scores below gate") and validated on the held-out set. Choosing per-leaf, post hoc, whichever scored better is
not a hybrid — it is fitting the test set, and it would inflate the board while degrading every other book.

---

## 4. THE ARCHAIC↔MODERN DICTIONARY AND THE PSEUDO-ARCHAIC REFERENCE (Q2)

### 4.1 The size of the hole — measured today

| references | scripture loci |
|---|---|
| `s_dismas` | 25,892 (52 books) |
| `odr_com` | 16,201 (39 books) |
| `sabates_a` | 37,130 (76 books) |
| `madueke_b` | 35,809 (73 books) |
| **loci with a MODERN reference and NO ARCHAIC one** | **8,383** |

Worst-affected: Ecclesiasticus (1,592), Jeremie (1,363), Isaie (1,292), Ezechiel (1,272), 4-Esdras (856),
3-Esdras (450). **Roughly a fifth of the Bible currently cannot be scored on the governing archaic arm at
all.** Sir's pseudo-archaic proposal is therefore not a convenience — it is the only route to a board that
covers the corpus, and it moves to the top of the build order alongside geometry.

### 4.2 How the dictionary is built

The four references are already aligned at the verse level, which makes the dictionary nearly free:

1. **Token-align** each verse's archaic reading against its modern reading (Needleman-Wunsch over characters,
   projected to tokens — the same aligner Stage 3 uses).
2. **Harvest pairs** `(modern → archaic)` with counts and per-book context: `heaven→heauen`, `son→ſonne`,
   `Japheth→Iapheth`, `Tubal→Thubal`, `taken→taken`. 25,892 archaic loci is a large training corpus by the
   standards of this task — the historical-normalization literature reports bi-LSTM normalizers trained on
   2,000–11,000 tokens (Bollmann & Søgaard, COLING 2016).
3. **Generalize to unseen tokens with character-level SMT.** Pettersson et al. found character-level SMT best
   on four of five historical languages; `cSMTiser` is the standard implementation and recent work reports it
   approaching Transformer performance with a ceiling around 98% accuracy. We are running it in the
   *unusual* direction (modern → archaic), which is the harder direction, and that matters — see below.

### 4.3 The caveat that shapes the design: the map is ambiguous backwards

Modernization is many-to-one and therefore **de-modernization is one-to-many**: `son` ← {`ſonne`, `ſon`},
`taken` ← {`taken`, `takē`}, `and` ← {`and`, `&`}. A single pseudo-archaic string is a *guess* at which
variant the 1609 compositor set on that line, and scoring a witness against a guess would charge it for our
guess being wrong.

**Therefore the pseudo-archaic reference is a LATTICE, not a string.** At each ambiguous token it carries the
attested alternatives with their corpus frequencies; the scorer accepts any attested path. This costs nothing
in implementation (the scorer already normalizes) and removes the entire class of fabricated failures.

Three hard rules on it, all of which exist to stop it laundering anything:

- **Provenance flag on every locus.** A cell scored against pseudo-archaic is marked as such on the board and
  in the report. It is a *different kind of pass* and the report must say so.
- **Never overrides a real archaic witness.** Pseudo-archaic fills gaps; it never competes.
- **Never used as character-level training truth.** It is derived from modern spelling; training on it teaches
  our own dictionary back to the recognizer. It supplies *line boundaries and candidate targets* for Stage 3
  in the 8,383-locus gap, and the lattice keeps the ambiguity visible while doing so.

### 4.4 Build steps — the dictionary

1. `ref_align_pairs.py` — verse-level char alignment across the four references → token pair table with counts.
2. `archaic_lexicon.py` — the dictionary, per book and corpus-wide, with frequencies and a coverage report.
3. `pseudo_archaic.py` — modern → lattice, using the lexicon first and cSMTiser for OOV; emits a reference in
   the same store format with `provenance: pseudo-archaic` and per-token alternatives.
4. **Gate**: on the 25,892 loci where a *real* archaic reference exists, generate pseudo-archaic from the
   modern reading and measure how often the lattice contains the true archaic reading. Report per book. This
   is a held-out test of the generator against ground truth we already own, and it must be published before
   any pseudo-archaic locus is used for anything.

---

## 5. THE GLYPH INVENTORY — MORE THAN LONG-ſ (Q3)

Sir is right that we settled for too little, and the reason we settled is worth stating: the references we
score against mostly do not encode ligatures, so a wider inventory looked unscoreable. That is an argument
about *references*, and §4 and §6 are fixing references. It was never an argument about what the model can
learn.

### 5.1 The inventory

Declared **before** any ground truth is generated, because a class the model never sees in training cannot
ever be output. Encoded per MUFI (Medieval Unicode Font Initiative) where Unicode proper lacks a codepoint:

- **Allographs**: `ſ` (long s) vs `s`; `r` vs `ꝛ` (r rotunda) where present.
- **Ligatures**: `ﬀ ﬁ ﬂ ﬃ ﬄ`, `æ Æ œ Œ`, `ct`, `ſt`, `&` (Tironian/ampersand forms).
- **Abbreviation marks**: vowel + macron for a suppressed nasal (`ã ẽ ĩ õ ũ`), `ꝑ ꝓ ꝗ`, `q̃`, superscript
  contractions — **transcribed unresolved**, per CATMuS practice, which explicitly leaves abbreviations
  unexpanded.
- **Historical letter use preserved**: `u/v`, `i/j` — already our convention and already CATMuS's.

CATMuS-Print's own convention is "no ligature except those that still exist, no allographic variants except
the long s". So **CATMuS is the right base model and the wrong target convention**: re-basing on it buys us a
recognizer already tuned to early print with u/v, i/j and long-ſ preserved, and then our fine-tune extends the
alphabet. Kraken derives its alphabet from the ground truth it is given, so a wider inventory needs no
architectural change — it needs ground truth that contains the glyphs.

### 5.2 Where the ligature ground truth comes from without a human transcribing it

This is the elegant part, and it is Q3 and Q11 answered by the same mechanism. **Allow one-to-many character
alignments in forced alignment, and expand the reference into a variant lattice.** The reference says `fi`;
the lattice says `fi | ﬁ`; the CTC posteriors from the recognizer decide which path the *image* supports. The
same lattice carries `s | ſ`, `ae | æ`, `and | &`, `an | ã`.

Two properties make this sound rather than wishful:

- The decision is made by the recognizer's own likelihoods over the pixels, not by a rule about where long-ſ
  belongs. **That matters specifically here**: this project's pinned finding is that Douay-Rheims long-ſ usage
  is *glyph-driven, not positional*, so any positional rule fabricates. The lattice never asserts, it offers.
- It bootstraps. A base model that cannot yet distinguish `ﬁ` from `fi` will pick nearly at random in round
  one — so round one's lattice decisions are gated on **posterior margin**, only confident picks become GT,
  the model is retrained, and the margin threshold is lowered. This is standard iterative pseudo-labelling
  with an explicit confidence gate, and the honest expectation is that rare glyphs need two or three rounds.

**UNMEASURED, and therefore an experiment, not a claim**: whether CTC posteriors from a CATMuS-based model
separate `ﬁ` from `f`+`i` at all before any fine-tuning. First experiment of the stage: take 200 lines where
the image is known to contain the ligature, measure the margin, and report it. If the margin is null, the
fallback is a small seed of hand-confirmed lines for the ligature classes only — a bounded, one-time cost of
perhaps 100 lines, not a per-book bottleneck.

---

## 6. COLLAPSING THE REFERENCES — ADOPTED; MY AMENDMENT NARROWED BY MEASUREMENT (Q4)

**REVISED 2026-08-03 after Sir's challenge and a measurement I should have run first.** My original objection
imported the textual-critic's frame — witnesses whose variants are evidence — and applied it to objects that
are not witnesses. `s_dismas`, `odr_com`, `sabates_a` and `madueke_b` are **modern transcriptions**, derived
texts. The physical witnesses are the six scanned sources. Sir is right that a disagreement between two
transcriptions is, overwhelmingly, one of them being wrong. Measured:

| pair | shared loci | raw differ | after folding long-ſ | **substantive** |
|---|---|---|---|---|
| `s_dismas` vs `odr_com` | 13,293 | 12,512 (94.1%) | 4,985 (37.5%) | **3,632 (27.3%)** |
| `sabates_a` vs `madueke_b` | 35,809 | 2,376 (6.6%) | — | **1,333 (3.7%)** |

And the character of the disagreements confirms the diagnosis rather than my objection:

- `matthew/1/7` — `s_dismas`: *"And Salomon begat And Roboam begat Abia"*; `odr_com` carries *"And Salomon
  begat Roboam."* **A dropout in `s_dismas`** — the same defect class we chase in our own OCR.
- `matthew/1/3` — `s_dismas` reads **`Efron`** where `odr_com` reads `Esron`. That is a **long-ſ misread as
  `f`**: an OCR error frozen into the reference we treat as the governing standard.
- `genesis/10/16` — `sabates_a` `Iebusæus` vs `madueke_b` `Iebusaeus`. Pure encoding convention, decidable by
  policy without evidence.

**Two things this changes.** First, `s_dismas` — the *governing* reference under the archaic-preeminent gate —
carries dropouts and glyph errors, which means some cells recorded as OCR failures are reference failures. The
ch10 discovery (`s_dismas` gen 10:1 spliced with apparatus) was not an isolated defect; it was one visible
instance of a 27.3% dispute rate. Second, **the collapse is ASYMMETRIC and must be coded that way**:
`odr_com` does not preserve long-ſ (`Moſoch` → `Mosoch`, `Christ` for `Chriſt`). It is therefore a valid
authority on **word identity and completeness** and no authority at all on **glyph identity**. A symmetric
merge would silently modernise the one reference that preserves our orthography.

### 6.0 What survives of my amendment — and it is not about transcription noise

One case remains where a single flat reading would be wrong, and it is the case that produced the governing-
gate alert in the first place: **the corpus contains two editions.** `S1`/`S3`/`S9` are 1609; `jp2-S06` is
1635, and it genuinely prints `Tubal` where the 1609 prints `Thubal`. Neither `s_dismas` nor `odr_com` is a
transcription of the 1635, so **ARCHAIC will be a 1609-family reference** — and forcing S6 to match it
recreates exactly the defect we identified. So:

- Variants are carried **only for inter-edition variance**, identified by the scans splitting along edition
  lines — a small, testable set, not a general apparatus.
- Everything else — 27.3% of the archaic pair, 3.7% of the modern pair — is corrected and **collapsed flat**,
  as Sir specified.
- The 1635 gap stays OPEN and is what **B7 rung 2** (acquiring a 1635 reference) exists to close. It is not
  fixable by reconciling the references we have.

### 6.1 (original argument, superseded above)

Sir's design: map the pair, collect disagreements, batch them to sub-agents, take corrections back, collapse
`sabates_a`+`madueke_b` → **MODERN** and `s_dismas`+`odr_com` → **ARCHAIC**. Score every verse against two
references instead of four.

I am adopting it, and the ch10 walk is evidence *for* it: `Iapheth/Iauan/Thubal` versus `Japheth/Javan/Tubal`
is a disagreement between reference families that currently fails cells transcribed exactly, and 158 of 383
open cells are that shape.

**The amendment, and I want to be plain about why.** The collation literature draws a distinction our pipeline
must not lose: OCR voting seeks a single consensus and treats disagreement as noise; textual collation
preserves the variant graph because *the differences are the scholarly object*. Two references collapsed into
one flat string would destroy the only evidence that tells us whether a witness's odd reading is an edition
fact or an OCR defect — and this project has already been burned once by grading a witness against a text it
does not print.

So: **collapse the pair into one reference that carries its variants.** At every locus where the pair agreed,
a single reading. At every locus where they disagreed and adjudication resolved it, the resolved reading plus
the rejected one, recorded. At every locus where adjudication could **not** resolve it, both readings as
alternates, and a cell passes if it matches either. Two references, as Sir asked; a variant apparatus
underneath, which costs nothing at scoring time.

**The second amendment concerns the adjudicators.** Sir's design has sub-agents "reason from their own
training about what the correct element string should be". A model reasoning from parametric memory about the
wording of a 1609 English Bible verse will produce fluent, confident, and sometimes fabricated text — this is
the same failure mode as citing a plausible DOI. Adjudication must be **evidence-bound**:

1. The agent is given the disagreement **plus the readings of all six scanned witnesses at that locus** —
   which we have, because that is the board.
2. It must return not only the reading but **which witness evidence supports it**.
3. A reading supported by no witness is not a correction; it goes to the unresolved apparatus.
4. Adjudications are **spot-audited against the scans**, and the audit rate is reported.

That keeps the whole speed advantage of Sir's design and removes the one way it could quietly rewrite the
Douay-Rheims into what a language model expects the Douay-Rheims to say.

### 6.1 Build steps — reference reconciliation

1. `ref_pair_map.py` — align the pair at char level per locus; classify each difference as orthographic
   (auto-resolvable: `æ/ae`, punctuation, `&/and`) or substantive.
2. `ref_disputes.py` — batch substantive disagreements with all six witnesses' readings attached.
3. `ref_adjudicate.py` — dispatch to sub-agents; require `reading` + `supporting_witnesses` + `confidence`;
   reject any unsupported reading into the apparatus.
4. `ref_collapse.py` — emit `ARCHAIC` and `MODERN`, each with `variants[]` per locus and full provenance.
5. Backfill `ARCHAIC` from §4's pseudo-archaic lattice at the 8,383 empty loci, flagged.
6. **Gate**: the collapsed references must reproduce the current board within a tolerance explainable
   cell-by-cell. Any cell that changes state is inspected, not netted.

---

## 7. TRAINING SETS PER SOURCE × VOLUME × BOOK (Q5)

The tome map (`tome-map-v2.json`, v2 schema, 11 admitted volumes, 100% page coverage by construction) already
carries every page's book:chapter address, its tome, and its jp2 reference — so selection is a query, not a
project.

`training_sampler.py`, specified:

```
for source in SOURCES:                       # S1 S3 S4 S6 S8 S9 (+ the pdf/archive variants)
  for tome in source.tomes:                  # OT1, OT2, NT
    for book in tome.books:                  # every book, INCLUDING frontmatter and backmatter
      pages = stratify(book.pages, by=LEAF_TYPE, n=quota(book))
```

- `LEAF_TYPE` ∈ {ordinary, chapter-open, argument, annotation-heavy, plate, frontmatter, backmatter, parity-A,
  parity-B} — derived from the existing `CHAPTER_MODEL` opens, the annotation-leaf detector and leaf parity.
- `quota` scales with book length but never below a floor per (source, tome, book), so short books are not
  invisible — the failure mode Sir is guarding against.
- Emits a manifest with a **frozen held-out split**, and the manifest is committed so a training run is
  reproducible and a later "it got worse" can be attributed.

---

## 8. S06 RE-ACQUISITION (Q6) — DONE

`fetch_s06_jpg.py` is built and running. It walks leaves 0000–2871 against the zip-member transcode endpoint
Sir confirmed, four polite workers, three retries with backoff, resumable.

**Every file is verified by magic bytes** (`\xff\xd8\xff` in, `\xff\xd9` out) and a 40 KB floor before it is
allowed to keep its name, because archive.org returns HTML error pages and truncated bodies with HTTP 200, and
a directory of 2,872 files where nine are HTML is indistinguishable from a good one until a training run fails
weeks later. A leaf that cannot be verified is deleted, recorded in a ledger, and the script **exits non-zero**
— a partial corpus must never be mistaken for a whole one.

Verified on leaves 0050–0057: 8/8, ~1.5 MB each, ~1.7 leaves/s.

---

## 9. (folded into §3.5)

---

## 10. THE RECOGNIZER HIERARCHY (Q8)

Sir: one model per book per source, or at minimum per tome per source; definitely not one for the corpus.
Agreed on direction, with a constraint that decides the shape: **a per-book model needs per-book ground
truth**, and 73 books × 6 sources is 438 scopes. Stage 3 generates GT cheaply, but not infinitely, and a model
trained on too little data is worse than its parent.

So the same rule V2 §3 applies to geometry applies to recognizers — **the most specific scope that is
*measured* to beat its parent wins**:

```
  CORPUS base        CATMuS-Print [Large]        (never used directly)
    └─ SOURCE        e.g. jp2-S06                 fine-tuned on all that source's GT
        └─ TOME      jp2-S06 / OT1                adopted only if it beats SOURCE on held-out lines
            └─ BOOK  jp2-S06 / OT1 / genesis      adopted only if it beats TOME on held-out lines
```

Each level is a fine-tune of its parent, each carries its own held-out set, and **adoption is a measurement,
never a default**. A book-level model that does not beat its tome-level parent is not adopted — and that is
not a degradation, it is the correct finding that this book's type is not distinctive enough to need one.

The registry records, per scope: training lines, held-out CER, held-out glyph-fidelity, parent, and the delta
that justified adoption. The board consults the registry; nothing is hard-coded.

**One design constraint from the literature that will bite if ignored**: Reul et al. found that using the
*same* pretrained model to train different voters yields worse voted results than using *different*
pretraining models. Our ensemble (§11) must therefore be diverse by construction — different seeds is not
enough; different parents, different augmentation, ideally a different architecture in the mix.

---

## 11. THE 0.5% CER TARGET (Q9) — VALIDATED, WITH TWO CONDITIONS

Sir asked for 0.5% instead of 2%. **The literature supports it**, and names the mechanism:

- Reul et al. 2018 (arXiv:1802.10038): pretraining + cross-fold training + confidence voting on **early
  printed books** reduces error by up to 55%, reaching CER ≤1% with 1,000 lines of GT, and **confidence voting
  pushes CER below 0.5%**. With pretraining and augmentation, 100 lines suffice for ~1.2%.
- Reul et al. 2017 (arXiv:1711.09670): per-character confidence voting beats ISRI-style sequence voting by a
  further 5–10%.
- Al Azawi et al.: an LSTM trained as a *voter* over two aligned engines reached ~0.40% CER on German Fraktur
  where the ISRI voting tool reached ~2%.
- Calamari reaches 0.11% on UW3 and 0.18% on DTA19 Fraktur — modern/19th-century, but it bounds what the
  architecture can do when the type is consistent.

**Condition one: 0.5% is an ensemble number, not a single-model number.** The target is adopted for the
*pipeline output* — cross-fold models per scope plus a confidence voter — and each single model is held to a
looser, separately-tracked figure. Writing 0.5% against a single model would guarantee an unreachable gate and
the pressure to launder that comes with it.

**Condition two: CER must be computed on the full glyph inventory (§5).** A pipeline that folds `ſ`→`s` and
`ﬁ`→`fi` will show a *better* CER while destroying the thing the project exists to preserve — the
normalization literature's own caveat is that PUA codepoints and long-s distinctions inflate CER unless
normalized first, which is exactly the temptation. Two headline metrics, always reported together:

| metric | definition |
|---|---|
| **CER-diplomatic** | edit distance over the full inventory, no folding. **This is the 0.5% target.** |
| **glyph-fidelity** | per-class recall on `ſ`, `u/v`, `i/j`, each ligature, each abbreviation mark |

A gain in CER-diplomatic accompanied by a fall in glyph-fidelity is a **regression** and is reported as one.

---

## 12. STAGE 3 — ALIGN, REWRITTEN (Q10, Q11)

### 12.1 What it consumes now

```
   ARCHAIC (collapsed, variant-carrying)  ─┐
   pseudo-archaic lattice at gap loci      ├─►  stream alignment  ─►  line projection  ─►  CTC refinement
   glyph variant lattice (§5)              │        (char-level)         (offsets)          (kraken)
   recognizer output + line boxes         ─┘
```

### 12.2 What actually gets aligned — the answer to Q11

**Not line-to-verse.** Sir's instinct that a line-to-verse mapping is needed is the right diagnosis of the
problem and the mapping is the wrong cure — building it requires knowing where verses start on the page, which
is what we are trying to learn. The elegant version inverts it:

1. **Concatenate the page's recognized lines into one character stream**, keeping a table of the offset where
   each line begins and ends. A line boundary is now just an index.
2. **Concatenate the chapter's ARCHAIC reference into one character stream**, keeping the offset where each
   verse begins.
3. **Globally align the two streams** at character level (Needleman-Wunsch with a historical-aware
   substitution cost; `passim` for a coarse pass on long texts).
4. **Project.** Read off, for each line's offset range, the reference span it aligned to. That span may cross a
   verse boundary, may be half a word, may be a hyphenated fragment — all of which are *correct answers* and
   none of which a line-to-verse mapping could express.
5. **Refine within the line** with kraken's own forced alignment (`ForcedAlignmentTaskModel` takes an image
   plus a `Segmentation` of `BaselineLine`s carrying known text and returns per-character `cuts`) to get glyph
   boxes — which is what the glyph lattice of §5 needs to resolve allographs.

Why this shape and not the other:

- **Hyphenation is handled by construction.** The research turned up a warning worth heeding: Transkribus's
  Text2Image alignment assigns a hyphenated word wholly to one line and *drops the fragment*, an artifact
  visible in the Bullinger dataset. Aligning characters rather than words keeps `hea-` on its line and `uen`
  on the next, which is what a diplomatic transcription requires and what our `rejoin_break` already models.
- **The apparatus problem is solved on the same pass.** Lines that align to *nothing* in scripture are
  candidates for Marginalia — which is precisely Signal A of §3.1. One alignment feeds both stages.
- **Verse boundaries fall out** instead of being assumed, which retires the whole `witness_spans` localization
  guesswork in the medium term.

### 12.3 The acceptance discipline

Alignment output is noisy GT and is treated as such:

- Accept a line only when its alignment distance is under a strict threshold. The speech-pipeline QC heuristic
  transfers directly: compute the CER between the aligned reference and the model's own transcription of that
  span, and discard above threshold.
- **Never align against `MODERN`** for character supervision. Sir is right that `s_dismas` and `odr_com` are
  decent diplomatic sources and the Gold Transcript is close to character-perfect — those are the training
  truth. `sabates_a`/`madueke_b` supply *word identity* (what the word is) and never *glyph identity* (how it
  was set), which is exactly the split Sir drew in Q2 and it is the right one.
- The Gold Transcript is the seed corpus and is used directly — with the caveat Sir named, that it lacks the
  extended inventory of §5, so it trains everything except the new glyph classes, which come from lattices.

---

## 13. STAGE 5 — TWO RUNGS, AND THE GATING QUESTION (Q12)

**Sir is right that geometry needs an escalation rung.** V2 re-targeted the rungs at recognition on the
strength of the 45%/33% split, and that was an over-correction: 125 open cells are geometry, and today the
only thing that fixes them is me walking a chapter. So Stage 5 has two rungs, routed by `triage.py` — which
already answers exactly this question per cell:

| rung | fires when | does |
|---|---|---|
| **R-GEOM** | triage says the missing words are on the leaf, outside the band | re-run the leaf through Stage 1 at higher resolution; propose a corrected polygon; **measure**; emit as Stage 1 training data |
| **R-RECOG** | triage says the words are not on the leaf at all | re-read with the ensemble; consensus by confidence voting; VLM rung (§14) |

Routing signal for R-RECOG is multi-model disagreement rather than a score threshold, and the merge is
character-level confidence voting (§11), with any lexicon verification restricted to a **period** lexicon —
LV-ROVER's lexicon-verified voting is the right family, and a modern-English verifier would be actively
harmful here.

### 13.1 Page or chapter? — both, and the page axis is missing today

We gate on **cells** (verse × witness) and aggregate to **chapters**. That is why the ch10 parity holes were
invisible for weeks: a defect that is *page-shaped* was being read through a chapter-shaped lens, and seven
leaves sitting on a stale default never showed up as anything but four chapters that were a bit low.

So: keep the cell as the unit of truth, and **add a page axis to the board** — every open cell already carries
its leaf (`from: p56`), so a per-leaf view costs nothing but has never been built. It gives:

- **Geometry defects sort to the top by construction** — a bad band produces many failing cells on one leaf.
- A natural trigger for R-GEOM: *leaf* open-rate above threshold, not chapter rate.
- The parity/gathering pattern becomes visible, since leaves sort in physical order.

Neither replaces the other: recognition defects are page-scattered and chapter-shaped work (arguments,
apparatus conventions) stays chapter-shaped. **The chapter stays the unit of the walkthrough; the page becomes
the unit of geometry triage.**

---

## 14. THE VLM RUNG, AND GLYPH RESTORATION (Q13)

### 14.1 Run them all — cheaply, and with a fixed protocol

Yes, and there is a clean way to make it cheap. Every candidate runs the **same fixed 200-line probe set**
(stratified across the six sources and the glyph classes of §5) before it is allowed near the corpus, and each
is scored on the two metrics of §11. Candidates:

| model | why it is on the list |
|---|---|
| **CHURRO** (3B, Qwen2.5-VL base) | purpose-built for historical text; CHURRO-DS is 99,491 pages / 22 centuries; 82.3% NLS printed, beating Gemini 2.5 Pro at 15.5× lower cost; **and it was evaluated with a diplomatic prompt that preserves original characters without modernization** — the only candidate with that property in its own evaluation protocol |
| **dots.ocr** (1.7B) | strongest MLX support; competitive layout detection from a single VLM; 40.9 on olmOCR-Bench old-scans vs PaddleOCR-VL's 37.8 |
| **Qwen3-VL** via **MLX** | our pinned failure is an *Ollama serving* defect (thinking-lock), not a model defect; the MLX path is untested and the pin must be narrowed, not generalized |
| **olmOCR** | incumbent R3; keep as the control |

Note the ceiling this sets: olmOCR scores 97.8 on olmOCR-Bench Base and **42.8 on Old Scans**, and CHURRO's
82.3% is *NLS, not CER* — none of these numbers is a 0.5%-CER instrument. **The VLM rung is a rescue rung for
cells the ensemble cannot read, not the backbone.** Treating it as the backbone is the error the aggregate
leaderboards invite.

### 14.2 Restoration by rule — no; restoration by attestation — yes

Sir's proposal is to let the VLMs run and, where glyph fidelity is poor, apply a derived rules conversion to
restore the lost glyphs. I have to push back on the rule half, and the reason is a finding this project
already paid for: **Douay-Rheims long-ſ usage is glyph-driven, not positional.** A positional rule ("long-ſ
everywhere except word-final") is exactly the kind of rule that would look right, score better, and fabricate
orthography on every exception — and it would do so invisibly, because the metric that would catch it is the
one the rule improves.

What is sound, and gets the same benefit:

1. **Attested transfer.** Align the VLM's modernized output to the ARCHAIC reference (§12.2's aligner). Where
   the tokens match, transfer the *glyph identity from the reference*, which is a witness statement about how
   this word was set in this edition, not a guess. This is restoration, and it is evidence-bound.
2. **Image adjudication for the rest.** Where the reference disagrees or is absent, ask the recognizer's own
   posteriors over that glyph box (we have the boxes from §12.2 step 5). The image decides.
3. **Never restore into an unattested, unverifiable token.** It stays as read, and it is flagged.
4. **Report restoration as a separate provenance class**, and audit its effect on both metrics of §11. If
   restoration improves CER-diplomatic while glyph-fidelity is flat, the restoration is doing nothing but
   flattering the metric.

---

## 15. THE TWO DECISIONS SIR LEANS TOWARD

### 15.1 Adopt the governing gate

`char_identity.evaluate_locus` documents an archaic-preeminent gate approved 2026-07-10; `chapter_campaign`
gates on the minimum over all four references. Adopting the documented gate moves the board 5744 → ~5870/6120
(+~122 measured at 5733; to be re-measured on adoption). **This is not a relaxation** — it is the removal of a
gate nobody ratified, which was charging faithful transcriptions for diverging from a modern edition, and
§6's collapse to MODERN/ARCHAIC makes the whole question structural rather than a per-cell rule.

Implementation, when Sir confirms:
1. `chapter_campaign` gates on ARCHAIC (real, else pseudo-archaic-flagged); MODERN is recorded and reported.
2. **A cell passing the archaic gate while failing MODERN badly is a WARNING class, not a silent pass** — that
   is a signal the verse is being read as the wrong words, and it goes to the validity audits.
3. The board is re-baselined once, loudly, with the old and new figures side by side and the delta attributed
   per chapter. No chapter's history is rewritten.

### 15.2 Open the drop-cap class

18 passing cells across 50 chapters carry a destroyed word; **13 are verse 1** — `FTER`, `HEN`, `HERFORE`,
`BRAM`, `ACOB`, `HESE`, `NTHE`. The chapter-opening drop capital is lost and the verse still clears 0.90.

Implementation: the caps-anomaly audit (`pipeline_run.py`) becomes a first-class gate — a cell carrying an
unattested all-caps token **fails regardless of score**, which will move the board *down* by up to 18 and is
the correct direction. Structurally the drop cap is a Stage 1 region class (it is its own region, and the
region model should be typed to know it), so the fix is not a filter but a label.

---

## 16. BUILD ORDER, REVISED — with gates

| # | step | why here | gate before adoption |
|---|---|---|---|
| **1** | **Close the `qc_audit.py` fork** — one geometry engine for board + report | still unblocks everything | board and report agree cell-for-cell on Genesis |
| **2** | **Reference reconciliation → MODERN + ARCHAIC (variant-carrying)** | Stage 3 cannot align against four disagreeing texts | reproduces the current board with every changed cell inspected |
| **3** | **Archaic↔modern dictionary → pseudo-archaic lattice** | 8,383 loci have no archaic reference at all | round-trip test on the 25,892 loci that do |
| **4** | **Stage 3 alignment engine** (stream align → line projection → CTC refine) | it is what makes labels for 1 and 2 | accepted-line precision audited on a held-out sample; glyph-fidelity ≥ current |
| **5** | **Distant-supervision region labels + agent fusion → `ketos segtrain`** | now cheap, because step 4 exists | per-class marginalia recall + MainText boundary error, **and must beat `PAGE_OVERRIDE` on the board** |
| **6** | **Glyph inventory extension via variant lattices** | needs 4; feeds 7 | posterior-margin experiment first; glyph-fidelity per class |
| **7** | **Hierarchical model registry + cross-fold ensemble + confidence voter** | needs 4 and 6 | CER-diplomatic 0.5% at pipeline level; every scope beats its parent or is not adopted |
| **8** | **Deskew, re-tested against polygons** | V2 pinned it as unusable against fractions | re-run the four configurations of V2 §1.2(iii) |
| **9** | **VLM rung with attested restoration** | rescue rung, last | 200-line probe on both metrics *before* any corpus use |

Steps 2 and 3 can run in parallel with 1. Step 5 is the one Sir's no-human-bottleneck instruction most
directly changes — it moves from "a day of annotation" to "a fusion pipeline and a disputed queue".

---

## 17. WHAT I CHANGED MY MIND ABOUT, AND WHAT I STILL DISAGREE WITH

**Changed my mind:**
- *LAREX annotation as the critical path.* Wrong, and expensively so — distant supervision was available the
  whole time and is published for exactly this material.
- *Re-targeting the rungs away from geometry.* An over-correction; 125 geometry cells have no automated path
  today and Sir's R-GEOM rung is the fix.
- *2% CER as the target.* Under-ambitious. 0.5% is documented for early printed books via ensemble voting.
- *"Alignment gives line boundaries and candidate targets, not diplomatic truth."* Too pessimistic. With
  variant lattices the alignment can decide *glyph identity from the image*, which is diplomatic truth
  obtained without a human transcriber.

**Still disagree, and the reasons are recorded so they can be overruled deliberately:**
- **Rule-based glyph restoration** (Q13) — our own finding says DR long-ſ is not positional; a rule would
  fabricate invisibly. Attested transfer gets the same benefit with evidence behind it.
- **Flat collapse of the reference pairs** (Q4) — collapsing is right, discarding the variants is not. The
  variants are how we tell an edition fact from an OCR defect, which is the distinction the whole board rests
  on.
- **Sub-agents adjudicating from parametric memory** (Q4) — they must adjudicate from the six witnesses'
  readings and name their evidence, or we will slowly rewrite the Douay-Rheims into what a model expects it
  to say.
- **Per-book models everywhere** (Q8) — right as an aspiration, wrong as a default; a scope with too little
  ground truth produces a worse model than its parent, so adoption must be measured per scope.

---

## 19. STAGE 0 — RASTERISATION: WE HAVE BEEN THROWING AWAY HALF THE PIXELS

**Measured 2026-08-03, in answer to Sir's question about PDF detail.** He is right that the PDFs preserve more
than the JPEGs, and the reason is structural rather than a matter of format quality.

### 19.1 What is actually inside these PDFs

Most are **MRC** (Mixed Raster Content): the scanner splits each page into a heavily-compressed colour
background plus a **1-bit mask carrying every letterform**. `pdfimages -list` on the real files:

| source | layers on one page | native text layer | ppi |
|---|---|---|---|
| `pdf-S03a` | jpx 754×1038 · jpx 2262×3116 (11.9 KB!) · **smask 2262×3116 JBIG2** | **2262×3116, 1-bit** | 500 |
| `S09` OT1 | jpx 1077×1464 · jpx 3231×4392 (22.8 KB) · **smask 3231×4392 JBIG2** | **3231×4392, 1-bit** | 650 |
| `S06` | **stencil 2867×4146 CCITT G4** | **2867×4146, 1-bit** | 377 |
| `S08` | single JPEG 3035×4336 rgb | 3035×4336 | (72 nominal) |
| `S01` ot1-1609 pdf | JPEG 800×1124 | 800×1124 — a low-res derivative; the jp2s are the real source | — |

The 3231×4392 *colour* layer in the S09 PDF is **22.8 KB** — it is a near-empty smear. All the detail is in
the 84 KB 1-bit mask. So "exporting a page from the PDF" composites a crisp binary mask with a blurred colour
layer and hands back an antialiased grey image: **that is the pixelation noise Sir is seeing, and it is
introduced by the export, not present in the source.**

### 19.2 The defect in our own pipeline

`reocr_core.preprocess()`:

```python
im = ImageOps.autocontrast(im)
if im.width < 1500:  im = im.resize((1600, ...), Image.LANCZOS)   # invents pixels
elif im.width > MAXW: im = im.resize((2200, ...), Image.LANCZOS)  # MAXW = 2200
```

Every page is forced to 2,200 px wide. Against the natives above that is:

| source | available | fed to the recognizer | discarded |
|---|---|---|---|
| S09 OT1 | 3231 px | 2200 px | **32% linear, 2.16× the pixels** |
| S06 (PDF stencil) | 2867 px | 2200 px | 23% linear |
| S06 (new JPEG) | 2550 px | 2200 px | 14% linear |
| S03a | 2262 px | 2200 px | 3% |

Two further problems in three lines of code: **LANCZOS downsampling of a 1-bit source** manufactures grey
fringes on every stroke — the classic way to destroy an already-clean binary scan — and **unconditional
`autocontrast`** applies a per-page tonal stretch, so the same typeface presents differently depending on how
dark that leaf's margins happen to be. Both are noise added by us.

This bears directly on §5 and §11: distinguishing `ﬁ` from `f`+`i`, or `ſ` from `f`, is a *stroke-level*
discrimination, and we have been performing it at two thirds of the available resolution on our best source.

### 19.3 The policy

1. **Never render a PDF to raster when the embedded image can be extracted.** `pdfimages -png` writes the
   decoded native stream; for MRC files that is the 1-bit mask, exactly as the scanner segmented it. Verified:
   S09 p60 → `3231×4392 mode "1"`, 0.3 MB.
2. **When a composite is genuinely needed** (illustrated leaves, colour plates), render at *exactly* the
   native ppi — `pdftoppm -r 650 -png` reproduced 3232×4393, a 1:1 with the embedded image. Any other DPI
   resamples. Verified.
3. **Never JPEG, ever, in the working chain.** PNG or TIFF only. The S06 JPEGs are an acquisition of last
   resort because the JP2s are corrupt — and note the PDF stencil (2867 px, 1-bit, CCITT) is *better* than the
   JPEGs we just fetched, so **S06 should read from the PDF and keep the JPEGs as the colour fallback.**
4. **Delete `autocontrast` from the default path.** If a source needs tonal work it gets it per source, as a
   measured decision, recorded in `SOURCE_MODEL`.
5. **Raise `MAXW` to the source's native width**, per source, with the memory cost measured rather than
   guessed. If a ceiling is genuinely needed for kraken, it belongs at the *line-crop* stage, not the page.
6. **JBIG2 caveat, flagged not assumed.** JBIG2's symbol-matching mode is lossy and is documented to have
   substituted whole characters in scanned documents. Whether these files used generic-region (lossless) or
   symbol coding is **UNMEASURED**. Test: extract the same page as mask and as a high-DPI composite, compare
   glyph-for-glyph on a sample. Until then, the mask is preferred but not trusted blindly.

### 19.4 The experiment that must run before any of this is adopted

Re-recognise a fixed set of leaves — one per source, chosen from chapters already walked so the answer is
known — at (a) the current 2200 px + autocontrast, (b) native-resolution extracted mask, (c) native-resolution
composite. Report CER-diplomatic, glyph-fidelity, and board cells for each. **This is cheap and it is a
prerequisite for the CER target of §11**: if resolution is the binding constraint, every model-side effort is
being spent against a handicap we imposed.

---

## 18. CITATIONS RESOLVED THIS SESSION

- arXiv:2112.12703 — *Digital Editions as Distant Supervision for Layout Analysis of Printed Books* (DTA scale)
- arXiv:2511.08903 — *LLM-Guided Probabilistic Fusion for Label-Efficient Document Layout Analysis* (88.2 AP @ 5% labels)
- arXiv:1802.10038 — Reul et al., pretraining + voting + active learning; **CER <0.5% with confidence voting**
- arXiv:1711.09670 — Reul et al., cross-fold training and confidence voting; per-character voting beats ISRI by 5–10%
- arXiv:2509.19768 / EMNLP 2025 — **CHURRO**, 3B historical VLM; 82.3% NLS printed; diplomatic prompt protocol
- Kraken documentation — `ketos segtrain` typology control, `--merge-regions`, `-e` held-out sets, `-q early`;
  `ForcedAlignmentTaskModel` in the Python API
- CATMuS-Print [Large], Zenodo 10592716; CATMuS guidelines — long-ſ preserved, abbreviations unresolved, u/v and i/j preserved
- Bollmann & Søgaard, COLING 2016; Pettersson et al. 2014; cSMTiser — historical spelling normalization
- Al Azawi et al. — LSTM voter over two engines, ~0.40% CER on Fraktur
- OmniDocBench / olmOCR-Bench old-scans — dots.ocr 40.9, PaddleOCR-VL 37.8; olmOCR 97.8 base / 42.8 old scans
- Transkribus Text2Image — hyphenated-word artifact observed in the Bullinger dataset (the failure §12.2 avoids)
- arXiv:2606.23344 (RT-DocLayout), arXiv:2601.14490 (GutenOCR) — surfaced as current grounded-layout baselines;
  **titles only, not read** — listed as candidates to test, not as evidence for anything above

**CARRIED FORWARD FROM V2 AND NOT RE-VERIFIED THIS SESSION** — flagged rather than quietly reused, because an
unchecked citation that survives two documents starts to look like a finding:
- arXiv:2607.00596 — marginalia is the worst-detected class for historical document detectors. Load-bearing
  for §3.3's weighted sampling and §3.4's per-class gate, so it is worth resolving before step 5 begins.
- arXiv:1712.05586 — book-specific recognizers reach ~2% CER on early print. Now superseded as the *target* by
  Reul et al.'s sub-0.5% voting result, so it is no longer load-bearing.
