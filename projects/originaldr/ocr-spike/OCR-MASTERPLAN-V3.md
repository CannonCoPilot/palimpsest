# OCR MASTERPLAN V3 — revision 3

**Status**: revised after **two** rounds of adversarial specialist critique. Round 1 = five critics
(`OCR-MASTERPLAN-V3-CRITIQUE-R1.md`). Round 2 = **eight** critics in two blind panels of four
(`OCR-MASTERPLAN-V3-CRITIQUE-R2.md`) — a context refresh caused an accidental replication, so every remit
has two independent critiques that never saw each other. Findings confirmed by both panels are treated as
settled; the four points where same-remit specialists disagreed are marked **[SIR'S CALL]** and carry my
decision plus the losing argument, so overturning any of them is a one-paragraph change.

Companion documents: `OCR-MASTERPLAN-V2.md` (ladder experiments, still valid) ·
`WALKTHROUGH-PROTOCOL.md` · `CAMPAIGN-STATUS.md` · `CHAPTER-WORKFLOW.md`.

---

## 0. THE DECISION THIS REVISION MAKES

### 0.1 We are building one documentary transcript, not six publication-quality OCR transcripts

This is the largest change in the document, and it came from two specialists on different remits reaching
it independently — a program lead costing the plan, and a scholarly editor reading its constitution.

Revision 2 adopted copy-text discipline, under which **five of the six sources may never alter an
accidental**. It then carried forward from V2 the requirement that **all six reach publication quality**,
and sized the ground-truth sets, the model hierarchy, the six-way collation, the variant graph, the witness
weighting and the drift guard accordingly. Those two commitments do not belong to the same project:

> **"Six sources at publication quality" is the plan's largest cost driver and it does not serve the stated
> product. It serves a different product — a six-witness collated critical edition. Deciding which one is
> being built is the highest-leverage decision available, and the plan currently pays for both."**

**Decision: the product is a faithful documentary transcript of the 1582 New Testament and the 1609/1610
Old Testament in archaic typeset and archaic spelling.** The other scans are a **detection and legibility
instrument**, not deliverables. They are consulted as *images*, at flagged loci, which is all the
constitution ever permitted them to do.

**What this deletes outright**: six-way multiple alignment and the variant graph · calibrated ensembles ·
Henikoff weighting and effective-N · the entire write-back drift guard (no write-back loop survives to
guard) · five-sixths of the diplomatic ground truth · the model hierarchy below the fount level.

**What it costs, stated honestly and up front**: ~3,000–4,500 pages at 6–15 min/page of human correction =
**400–1,000 hours**. That is the true price of this product *under any architecture*. The point of the
simplification is not that the hours go away — it is that **in this architecture those hours produce the
deliverable directly, instead of producing the instrument that produces it.**

### 0.2 [SIR'S CALL #1] Documentary edition, not critical edition

Both editors agreed revision 2 had over-imposed a critical-edition framework. They disagreed on the remedy.
One would keep copy-text discipline and repair it with a three-way witness typology. The other argued the
framing itself is the defect, and I have adopted that view:

> Greg's rationale exists to solve one problem: an editor must **construct** a text from witnesses of
> differing authority, chiefly where an author revised. **Its accidentals/substantives split is a rule
> about *authority*, not about *fidelity*.** This project has no authorial revision, no lost archetype and
> no reconstructive ambition. And once you say "copy-text," an apparatus follows by convention — historical
> collation, sigla, rejected readings, authority chains, cross-exemplar press-variant collation — **which
> is exactly the overhead revision 2 acquired.** The six scans are not witnesses to a text; **they are
> photographic surrogates of documents. Disagreement among them is scan quality plus OCR error, not textual
> variation.**

**This edition is therefore documentary/diplomatic** (TEI P5 ch. 11, *Representation of Primary Sources*;
Tanselle, *Editing Historical Documents*). Copy-text survives as a **mechanism** for choosing which
physical copy is transcribed — not as the edition's constitution.

**Deleted from the old constitution**: the rule admitting the 1630s editions as always-substantive
witnesses, and the rule giving other witnesses standing over substantives. **They licensed a 1633 reading
into a document dated 1582.** The 1630s printings are **reading aids for illegible passages**; any use of
one is an *intervention*, recorded as such, with its own date and STC number visible to the reader.

*Losing argument, for the record*: retaining copy-text language would have kept continuity with the round-1
critique and with a large body of editorial practice, and the three-way typology does fix the specific
`accidental` defect. I judged that the word drags the apparatus in behind it, which is what happened once
already.

### 0.3 The constitution, restated

1. **The base document is a named exemplar of a named edition-issue** — a specific physical copy, chosen on
   physical grounds and documented **with the losing candidates and why**.
2. **The transcript reproduces what that document prints.** Spelling, glyph forms, ligature presence,
   punctuation, capitalisation and compositorial evidence (turned letters, wrong-fount sorts) are preserved
   as set.
3. **Nothing is synthesised.** No rule-generated spelling ever enters the transcript. Where a reading cannot
   be established, the transcript **records a gap** — it does not guess.
4. **Illegibility is resolvable from another photograph of the same setting of type, and that is
   transcription, not emendation** (§0.4).
5. **Supply from a different setting is an intervention**, bracketed in every view, carrying the supplying
   document's identity and date.
6. **Every reading is addressable and checkable** — page and signature in the output, always.

### 0.4 Two disjoint channels — the distinction revision 2 had no way to express

Revision 2 routed "the copy-text is blotted here, the other scan of the same forme is clean" through the
same apparatus as "this word comes from 1635." The first is reading the document; the second is altering
it. Merged, thousands of routine legibility resolutions drown the handful of real interventions.

**The mechanical setting-identity test, applied before any cross-source use**: same signature, same
catchword, **same turn-lines (line-end words)**. Identical ⇒ same setting. Setting identity is **proved,
never assumed.**

| channel | when | recorded as | where it appears |
|---|---|---|---|
| **Surrogate register** | base surrogate illegible; a **same-setting** surrogate resolves it | `resolved_from: <surrogate id> @facs zone` + certainty, **and nothing else** | machine-readable sidecar; **summarised statistically** in the editorial statement — never enumerated in the apparatus |
| **Intervention apparatus** | supply from a **different setting** (1633/1635, or another exemplar with stop-press variance) | `supplied-from-other-setting` + the source's **own STC number and date** | bracketed in the reading text, in every view |

### 0.5 The three units, all declared

"Tome" was a scan-volume word, and scan volumes do not respect bibliographic boundaries — front matter,
bound-together copies, made-up exemplars.

| level | unit | why it is the right granularity |
|---|---|---|
| **bibliographic** | **edition-issue**, cited by STC/ESTC | the NT and the two OT volumes are **three separate printings**, two towns, two houses, 27 years apart, different founts and compositor conventions |
| **exemplar** | one named copy: repository + shelfmark | **this is the document being transcribed** |
| **substitution** | **gathering / forme** | **stop-press correction is a forme phenomenon** — two copies of one edition differ gathering by gathering |

The reference text is therefore **three documentary transcripts concatenated**, each labelled, **with no
accidental harmonisation across the joins.** Still one deliverable; still what was asked for. Where the base
exemplar is defective and a second copy supplies leaves, that is declared **leaf by leaf in a made-up-copy
table** — standard STC/ESTC practice for imperfect copies.

### 0.6 The two failure modes, and where revision 2 landed between them

Revision 1 was diagnosed with **status-quo preservation dressed as empiricism**: each time a measurement was
ambiguous it became a reason to keep the incumbent. Revision 2 over-corrected, and both red teams named the
result precisely:

> The over-correction is **not** "unfalsifiable ambition" as the plan feared — **it is unstartability,
> which is the original failure mode reached by a longer route.** A prerequisite that cannot be satisfied
> produces the same observable outcome as status-quo preservation: nothing moves.

Concretely: revision 2 put **ten of twelve build steps behind a ground-truth stage that was unbudgeted
(~200–280 operator-hours, stated nowhere), partly unpassable (≥200 instances of a class with ~40), and
lacking the written transcription protocol that is its own prerequisite.** It also claimed to honour the
instruction to avoid human-review bottlenecks "at the production path" — while **making the entire build
order depend on the review path, which is the same bottleneck one level up.**

**The rule this revision adopts, with the cost bound revision 2 lacked**: an ambiguous measurement licenses
a better experiment, never a lowered requirement — **and every such experiment carries a stated hour ceiling
and a pre-registered decision rule before it starts.** Where a number must be reported before its
properly-sized evidence exists, it is reported **with its confidence interval and the label PROVISIONAL /
non-citable**, and **no gate closes on it.**

---

## 1. WHAT MUST EXIST BEFORE STEP 0 — the source concordance

**The constitution is unimplementable until this table exists, and revision 2 never noticed.** It declared
copy-text discipline while **deferring to step 11 the bibliographic identification needed to choose a
copy-text**, and §2.4 identified the scans only by pixel dimensions. Nothing in the document mapped a scan
to an edition, a volume, or a repository — yet that mapping is the load-bearing decision of the whole
project.

| field | S9 | jp2-S06 | pdf-S03a | S08 | (others) |
|---|---|---|---|---|---|
| edition-issue | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** |
| STC / ESTC | **UNVERIFIED** | | | | |
| volume (NT 1582 / OT1 1609 / OT2 1610 / later) | **UNKNOWN** | | | | |
| repository + shelfmark | **UNKNOWN** | | | | |
| scan provenance / IIIF | partial | `Douay-Rheims-1610-Bible_jpg` | | | |
| native raster | 3231×4392 (650 ppi) | 2550×3301 JPEG | 2262×3116 | 3035×4336 | |
| grayscale path available? | 1-bit JBIG2 in PDF | **JPEG only** | | | |
| completeness / imperfections | **UNKNOWN** | 2,872 leaves verified | | | |

**Every UNKNOWN above is a blocking task, and I am not filling any of them in from memory.** Candidate STC
numbers surfaced during critique (NT 1582 Rheims, Fogny; OT 1609 Douai, Kellam) are **unverified** and are
recorded as leads to check against ESTC, not as facts. Basing a copy-text choice on a hallucinated shelfmark
would poison everything downstream.

**Two consequences to state now rather than discover at step 11:**
- **Some of the six scans are 1633/1635 and are therefore ineligible as the base document for anything.**
  They can only ever be intervention sources.
- **Where only one scan exists for a given 1609/1610 volume, the same-setting resolution route of §0.4 is
  unavailable there, and gaps will be real.** That is a property of the surviving evidence, not a defect to
  iterate on.

---

## 2. THE MEASUREMENTS THIS PLAN RESTS ON — corrected twice, and their reporting standard

### 2.1 `s_dismas` vs `odr_com` — the estimator, restated honestly

Sir was right that these are essentially the same text; my first figures ("94% differ") were verse-key
artefacts. **My second figures are also flawed**, and the reasons matter more than the number:

- 0.9879 is a **maximum over 11 candidate alignments** (±5 verses) — upward-biased by construction, with no
  null distribution, on text formulaic enough that any two DR-ish verses score well.
- It was computed on the **intersection** (13,292 mutually-covered verses — the easy subset) while coverage
  was computed on the **union**. Neither was stated.
- It folds long-ſ, `æ`, case and punctuation — **the dimensions the product exists to preserve** — and was
  then used to license repairing a glyph authority from a companion that does not preserve glyphs.

**Mandatory reporting standard for any reference comparison, from this version forward**: offset-0
similarity as **primary**; best-match-within-window as a **labelled diagnostic**; a **permutation null**
(best match against 11 randomly drawn verses of the same book) with the margin over null reported; and the
metric computed a **second time with glyphs unfolded** — that second number is the only one relevant to the
archaic arm.

**What survives unchanged**: **8.0% of verses best-match at a non-zero offset.** `ref_renumber` is
incomplete, the defect concentrates in Psalms, Acts, Luke, Matthew and Mark, and **every verse-keyed
comparison of these two references is invalid until it is finished.**

### 2.2 `s_dismas` carries spliced apparatus, systematically

`ruth/1/1` and `genesis/10/1` both hold annotation in place of the verse tail — in the reference that
revision 1 made the *glyph authority*. Both archaic transcriptions are now **finding aids** (verse
addressing, word identity, alignment anchors, GT candidate generation), never authorities. **The glyph
authority is the image.** Before either is used at all: a **provenance audit** — 200 verses sampled against
the scans, reporting each transcription's `ſ`/`s` accuracy, its ligature policy and its base edition,
published.

### 2.3 Coverage — and what the 8,383 actually means

| reference | arm | verses | % of union | chapters complete | chapters absent |
|---|---|---|---|---|---|
| `s_dismas` | ARCHAIC | 25,892 | 69.7% | 719 / 1,360 | 369 |
| `odr_com` | ARCHAIC | 16,201 | 43.6% | 552 / 1,360 | 774 |
| `sabates_a` | MODERN | 37,130 | 99.9% | 1,325 / 1,360 | 0 |
| `madueke_b` | MODERN | 35,809 | 96.3% | 1,299 / 1,360 | 26 |

Union: 37,166 verses / 1,360 chapters. **8,383 loci have no archaic *reference*.**

**Revision 2 mis-stated what that number is, and both editors flagged it as alarming and false.** Those loci
are **not transcript gaps — the scans contain those books.** It is a **QC-coverage figure: there is no
independent check on the OCR there.** The real risk is narrower and should be stated as exactly that:
**where the OCR is unsure *and* no archaic reference exists, a plausible hallucination is indistinguishable
from a reading.** The remedies are §5's abstention machinery and a **quota** (not a gesture) of
ground-truth stratification in those books — Ecclesiasticus 1,592, Jeremie 1,363, Isaie 1,292, Ezechiel
1,272, 4-Esdras 856, 3-Esdras 450.

**Cut from revision 2**: the coverage *interval* with its `VerseNumber`-derived upper bound. It measured
the references, and the references are now finding aids. `coverage_figure.py`'s book × chapter grid remains
a **required report panel**.

### 2.4 Raster reality

S9 native 3231×4392 (650 ppi, 1-bit JBIG2 in the PDF) · S06 JPEG 2550×3301 (JP2s corrupt; PDF stencil
2867×4146 CCITT) · S03a 2262×3116 · S08 3035×4336. `preprocess()` forced everything to 2200 px with LANCZOS
plus unconditional autocontrast.

The A/B/C/D experiment found **no significant difference with the current model** (spread ≤0.002) — which
measures **co-adaptation**, since the model's VGSL input is `(1,1,120,0)` and rescales every line to 120 px
regardless. **Input height is a settable parameter** (`ketos train -s '[1,H,0,1 …]'`). My claim that the
2200 cap was costing accuracy was **not supported**, and the honest reading of that null is in §5.6.

---

## 3. THE PIPELINE

### 3.1 Generations, and the rule for when one is worse than the last

Two round-1 reviewers showed the build order was a **cycle**: alignment needs a recognizer, the recognizer
needs alignment GT, the region model needs alignment for labels, and the region model's gate was the board —
which the recognizer produces. Revision 1 resolved it silently by using the incumbent geometry, i.e. the
thing it claimed to be removing.

**So the pipeline is stated as numbered generations, gated on frozen evaluation sets — never on the board,
which moves between generations.** Revision 2 called this an EM loop; a red team correctly objected that
**there is no shared likelihood** — geometry, recognition and alignment optimise different objectives — so
"EM" is dropped. It is an iterated refinement with an explicit termination rule and an explicit regression
rule, both of which revision 2 lacked.

```
G0  incumbent geometry (PAGE_OVERRIDE) + incumbent recognizer  → bootstrap only, never a gate
G1  ink-derived regions + seed labels → region model v1 → recognizer v1 → alignment v1
G2  regions v2 (relabelled from v1 alignment) → recognizer v2 → alignment v2
```

**Primary scalar**: CER-diplomatic on VAL-GOLD. **Non-inferiority constraints** that must hold
simultaneously: marginalia recall and precision, MainText boundary error, rare-class macro error. A single
free choice among five metrics is not a convergence criterion.

**Two terminals, and they are not the same state** — revision 2 collapsed them, which reintroduced the
laundering it had just removed elsewhere:

| terminal | condition | disposition |
|---|---|---|
| **CONVERGED-AT-TARGET** | metric ≥ threshold ∧ Δ < δ | closed |
| **STALLED-BELOW-TARGET** | metric < threshold ∧ Δ < δ | **OPEN, blocking, ALERT for approach redesign. The deliverable does not ship.** |

**Regression rule**: if G(n+1) is worse than G(n) by more than the paired CI, **G(n+1) is a failed
experiment — revert artifacts to G(n), do not adopt, and do not re-baseline.** Keep-best checkpointing
throughout.

**δ is pre-registered per metric before step 6, and δ ≥ 2× the evaluation set's standard error or the gate
is void.** Revision 2 used δ in three places and never gave it a value anywhere.

### 3.2 Stages, per generation

```
 0  ACQUIRE      volume → verified native rasters, grayscale primary, no lossy step
 1  GEOMETRY     page → typed region polygons (ink-derived shapes, text-derived labels)
 2  RECOGNISE    region → lines → diplomatic text + a stand-off rendition layer
 3  GROUND TRUTH forced alignment → line GT;  text-side mining → glyph GT
 4  TRANSCRIBE   the base document, corrected page by page, signed off
 5  LOCATE       page/signature primary address · verse secondary
 6  CONSULT      flagged loci only → surrogate register or intervention apparatus
 7  PUBLISH      transcript + minimal apparatus, versioned and sha-pinned
```

Stage 4 replaces revision 2's "six transcripts driven to publication quality." Stage 6 replaces its six-way
collation. **That is the §0.1 decision expressed as pipeline.**

---

## 4. STAGES 0–1 — RASTERS AND GEOMETRY

### 4.1 Acquire — grayscale is primary, and the binarisation gap is upstream of the fix

No lossy or resampling step anywhere in the working chain. **Extract, never render** (`pdfimages -png`;
verified S09 p60 → 3231×4392 mode `1`); composite only when the page needs it, at exactly native ppi
(`pdftoppm -r 650` → 3232×4393, verified); PNG/TIFF only; no autocontrast, denoise, sharpen or binarisation
of our own in the default path; **`MAXW` deleted** — scaling happens once, inside the recognizer. S06 reads
the 2,872 verified JPEGs (`jp2_page.py`, working). A raster manifest per source records path, dimensions,
bit depth, provenance and checksum, so a silent substitution is impossible.

**Revision 2 said "convert 1-bit → uint8 before any geometric operation" and treated that as sufficient. It
is not, and this was confirmed by both HTR critics:**

> 1-bit upcast to uint8 yields a **two-valued {0,255} image, not grayscale**. CATMuS's first conv filters
> were fitted to antialiased stroke edges with 20–40 grey levels across a 2–3 px transition; binarised,
> that gradient is a **step**. Expect a **2–5× CER multiplier zero-shot**, and after fine-tuning a
> persistent penalty **concentrated in exactly the 2–4 px features — the `ſ` nub and the macron.** The
> uint8 conversion fixes resampling aliasing only; **it does not restore grey levels, which were destroyed
> upstream at binarisation.**

**Policy, restated:**
1. **Grayscale native is primary throughout.** 1-bit JBIG2 masks are a **fallback for sources with no
   grayscale path only**, and any such source is **trained and evaluated as its own scope with its own
   reported CER**.
2. Where only the mask exists (the S06 stencil), **reconstruct pseudo-grayscale with a ~0.8 px Gaussian
   blur at native resolution before any downsampling** — it restores an edge gradient, and it is zero-risk
   because it is applied identically at train and inference.
3. **The JBIG2 substitution test still blocks step 0** — lossy symbol matching merges visually similar
   glyphs and **`ſ`/`f` is the canonical case**. Extract the same 20 pages as mask and as high-DPI
   composite; compare glyph-for-glyph on every `ſ`/`f` and `c`/`e`; report substitution rate with per-class
   instance counts. **But note what it does and does not cover: it measures substitution, and the
   binarisation gap of (1) exists even at a zero substitution rate.**

### 4.2 Geometry — shapes from ink, labels from text

Revision 1 derived region polygons as hulls of aligned line boxes. Two reviewers showed this
self-defeating: those line boxes were produced *under the bands*, so labels inherit the bands' blind spots,
and MainText boundary error is bounded below by the hull's error — **making the boundary gate unreachable
in expectation.** Worse, the acceptance threshold discarded lines whose reading was far from the reference
— **exactly what happens when a band clips scripture** — so those leaves scored badly and were censored out
of training. Labels survived only where the incumbent was already right.

1. **Shapes come from ink.** Connected-component and projection-profile grouping on the native raster, plus
   a generic baseline segmenter (`blla.mlmodel`) over the **untyped full page**, independent of
   `PAGE_OVERRIDE`. This is the only construction in which line geometry is not a descendant of the bands.
2. **Labels come from text**, assigned to ink groups: MainText from alignment to the archaic finding aid;
   Marginalia from `madueke_b`'s 1,334 apparatus blocks; RunningHead / Catchword / Signature from
   self-verifying positional-and-text tests; VerseNumber from numeral-matches-adjacent-verse.
3. **The acceptance signal is inverted — unaligned residue is positive evidence.** For each leaf, the
   fraction of the chapter's reference span matched by *no* line localises a missed or clipped region. That
   residue is a **labelling target, not a discard**, and it is **the single change that lets the model learn
   the failures the campaign has been fixing by hand.**
   **Corrected: residue-as-signal is null where there is no reference** — the 8,383 loci and the archaic
   arm's coverage gaps, which is precisely where geometry is unlabelled. **A reference-independent residue
   signal is therefore required alongside it: ink-groups with no line assignment at all.**
4. **Invariant**: no ink of a typed group may fall outside its polygon.
5. **The geometric prior is an initialisation and plausibility clamp, not a vote.** Distant supervision and
   the prior both descend from `PAGE_OVERRIDE`, so "2-of-3" meant *the incumbent always carries* — and the
   sub-agent was outvoted **exactly on the leaves where it was the only voter that could be right.**
   Disagreements resolve **against pixel evidence in the disputed strip**, adjudicated by a VLM given the
   crop, with a recorded decision rule and a gate — revision 2 named no adjudicator, no crop rule and no
   gate, which a red team correctly called words rather than mechanism. The A–C agreement rate is measured
   first; above ~0.95 the old fusion was decorative and is reported as such.
6. **DropCap leaves the region model.** One instance per chapter, nested inside MainText, and kraken's
   region polygons plus reading order handle nesting badly. It is detected as an **alignment deficit** at
   chapter open (reference `AFTER`, line reads `FTER`) and restored as a character. **The board fix ships
   now, independently**: a cell carrying an unattested all-caps token fails. **18 cells, and they must not
   be stranded behind the most speculative component in the plan.**
7. **Marginalia negatives are mined explicitly** — only leaves with confirmed apparatus coverage contribute
   Marginalia-negative pixels, or every unlabelled marginal block becomes an implicit negative and teaches
   the model to suppress the class.
8. **Under the §0.1 decision, this whole component is deferred behind the base document.**
   `PAGE_OVERRIDE`'s 371 constants are adequate for *one* witness; a generalising region model is only
   needed for the other five, and the other five are now an instrument, not a deliverable.

**Gate — published *before* G0 is measured, and sha-pinned** (revision 2 promised "targets set from the G0
baseline with a pre-registered minimum effect size" and pre-registered nothing): on the frozen evaluation
half, **with the recognizer frozen** so board movement cannot be attributed to geometry it did not cause —
**marginalia recall ≥0.85 and precision ≥0.90 (reported at block-level n)** · **MainText boundary error
≤8 px median, ≤25 px p95** · per-class IoU · n ≥ 125 eval pages. The board is a **secondary sanity check
only.**

---

## 5. STAGE 2 — RECOGNITION

### 5.1 The inventory — and the line between a character and a rendition state

Removed as anachronistic: **PUA codepoints** (state the rule as *no PUA in output; combining marks
preferred* — much of MUFI is now standard Unicode).

Retained: `ſ`/`s` · `ﬀ ﬁ ﬂ ﬃ ﬄ` · `æ Æ œ Œ` · `ct`/`ſt` **presence-versus-absence as a recorded fact** ·
vowel + macron for suppressed nasals, **unexpanded** · `u/v` and `i/j` **as printed** · `&` and Tironian
forms.

**Added, and genuinely present** (from the scholarly review, and missing from every prior revision):
**note-reference marks — `*`, `†`, `‡`, `¶`, superscript letters.** In the Douay-Rheims **the apparatus is
half the book, and a transcript that drops the keys linking annotation to text is unusable.** Also: roman
numerals including **terminal `ij`** · **Greek and Hebrew sorts** in the annotations · braces and printers'
rules · **`ſſ ſi ſl`** alongside `ſt`/`ct`.

**[SIR'S CALL #4 — resolvable by looking, and now a task rather than a judgement.]** The two editors
disagreed on `ꝛ` (r-rotunda) and `ꝑ ꝓ ꝗ` (Latin brevigraphs). One removed both as blackletter/scribal
anachronisms; the other objected that **removing `ꝛ` while simultaneously admitting blackletter headings is
self-contradictory — `ꝛ` is precisely the sort blackletter needs** — and that **per/pro brevigraphs do occur
in the roman-type Latin of the Rheims annotations and running heads.** A third question is entangled with
these: whether Fogny and Kellam set **any** blackletter at all, or only roman and italic.
**All three close together by inspecting the scans. Until then all three are OPEN, and none is enshrined.**

**Machinery, not glyphs**: an `unclear` / `gap` mechanism (`<unclear cert="">`, `<gap reason="damage"/>`).
Revision 1 had **no way to say "I cannot read this"** — which, under No Silent Degradation, forced an
unreadable glyph into a confident reading.

### 5.2 Style is a stand-off layer, never a codec class

Revision 2 added italic/roman contrast, small capitals, swash italic capitals, blackletter, `VV` for `W`,
turned letters and wrong-fount sorts **to the inventory**. Three critics on two remits independently called
this the single largest words-only item in the document: **a CTC line recognizer over a character codec
structurally cannot emit a style channel**, and revision 2 supplied no encoding scheme, no GT protocol, no
annotation cost and no gate. Worse, admitting them as classes **multiplies the class count several-fold,
destroying the rare-class budget §5.3 exists to protect.**

They are **rendition states of characters, not characters.** `VV` is two sorts — **transcribe `VV`, record
the rendition.** And a **turned `u` standing for `n` is not a glyph, it is a defect in a sort**; encoding it
as a character forces a reading decision into the codec.

**The encoding, which is also the only form that survives OCR, alignment and edit distance:**

- The **text channel** is a plain grapheme string with a **stable character index**.
- A **parallel span table** holds `{start, end, rend}` over that same index (TEI P5 `<span>`/`@spanTo`).
- **Font is recognised by a separate classifier over the line image, never by the CTC head** — word-level,
  not character-level.
- **Alignment and collation run on the character channel, unchanged.**
- **Scoring is two channels**: CER on characters, **plus span-level precision/recall/F on rendition,
  reported separately and never folded into CER.**
- Serialisation materialises spans into `<hi rend="italic">`, `<seg rend="sc">`, `@rend="blackletter"`.
- **The same layer carries `<sic>` with `@rend="turned"` / `@rend="wrong-fount"`**, so the requirement to
  preserve compositorial evidence is met **without touching the codec.**

**If the style classifier is not built in G1, style is explicitly scoped out and recorded as a known
non-preservation in the statement of editorial principles.** It is not left as an unbudgeted promise.

### 5.3 Rare classes — keep them atomic, and mine them from the text side

`ﬃ ﬄ` and the abbreviation marks occur tens of times corpus-wide. Under CTC a class with under ~100
instances is essentially never emitted — the loss is lower if the model prints blank plus the frequent
neighbour — so the imbalance would **silently delete exactly the inventory this project exists to
preserve.**

**Revision 2's NFD decomposition is withdrawn.** Both HTR critics rejected it, and the mechanism is
decisive:

> **CTC alignment is monotonic and one-symbol-per-frame-run. The macron sits *above* the bowl, not after it
> — there is no horizontal region where the mark is present and the base is not.** A two-symbol target
> forces the network to manufacture an ordering **the image does not contain**; the mark's peak collapses
> into the base's frame run and is absorbed by repeat-collapse or blank. **`õ` decomposed is strictly
> *harder* than atomic `õ`, not easier** — macron recall can fall while support rises. It also doubles the
> target length on those lines, and **makes CER count one visual error as two edits, so CER-folded is no
> longer comparable to the literature.** And kraken's `PytorchCodec` builds from GT graphemes, so **a bare
> U+0304 becomes a standalone codepoint emittable after any base — the model can produce `t̄` and other
> non-sorts.**

Additionally, splitting `ﬃ` while keeping `ﬁ` atomic **creates a codec in which `ﬃ` and `ﬁ`+`f` compete for
identical pixels — the exact ambiguity §5.4 says has no likelihood asymmetry.**

- **All of `ã ẽ ĩ õ ũ ﬀ ﬁ ﬂ ﬃ ﬄ` stay atomic. Pin NFC** across codec construction, GT files and
  edit-distance scoring; mixed forms silently produce duplicate codec entries and a CER that is simply
  wrong. **Compose/decompose only at output serialisation, never in the codec.**
- Recover the parameter sharing NFD was meant to buy by **initialising the five macron output rows from
  their base-letter rows plus a shared learned offset** — or simply accept five atoms: 5 classes × ~200
  mined instances = 1,000, above CTC's viability floor.
- **Oversampling: 3–8× line replication maximum.** Revision 2's 10–50× is a metric-gaming engine.
  Replication is **line-level**, so it duplicates the line's ~40 other characters, its fount, its page
  texture and its binarisation artefacts — and rare-class lines cluster in a few gatherings, so **50× means
  memorising a handful of pages and, in letterpress, learning the specific damaged sort rather than the
  class.** **Precision breaks before recall does.** Above 8×, switch mechanism to **per-class CTC loss
  weighting (∝ 1/√freq, capped ~10)**, which affects only the rare symbol's contribution.
- **Any oversampling breaks the softmax as a probability of the real distribution** — so **calibrate on an
  unweighted held-out set, never the training distribution.**
- **Add what revision 2 omitted entirely: synthetic line rendering** from a digitised fount with
  degradation (the standard remedy for rare-class CTC), and **decode-time logit prior scaling**
  (÷ prior^α — costs nothing, distorts no training).
- **Monitors at every checkpoint, per rare class**: precision **and the frequent neighbour's false-positive
  rate** (if `ﬁ` recall climbs while `f`+`i` precision falls, the reweighting buys nothing); reliability
  diagram / ECE for every class used downstream.
- **Report per-class support with every per-class metric.** Recall on 12 instances is noise.

### 5.4 Ligatures and allographs — what actually discriminates

**Revision 1's variant-lattice bootstrap stays withdrawn**, and for the right reason: a CTC model puts
posterior mass only on symbols in its codec, so an untrained `ﬁ` is **unscoreable rather than low-scoring**
and the lattice picks `f`+`i` with a huge margin forever. Both panels confirmed the withdrawal and the
reasoning.

**But revision 2's replacement is also wrong**, and both HTR critics dismantled it independently:

- **`ſ`/`f` should never have left the codec.** It differs by a left nub vs a full crossbar — a decisive,
  always-present cue on a class with **tens of thousands of instances**. Routing it to a per-pair crop
  classifier removes a **high-support** class from end-to-end training and reintroduces the
  segment-then-classify pipeline CTC exists to avoid. **The real cause of `ſ`/`f` error is that the nub is
  3–6 px at 650 ppi and 2–4 px after rescale to H=120** — plus JBIG2 merging and the binarisation gap.
- **Connected components fail**: at 650 ppi with 1582 ink spread, **a printed line is largely one connected
  component**; adjacent sorts in a well-inked forme touch routinely, and a badly-inked ligature breaks into
  two. **CC count is a function of ink load and paper absorbency, not of the sort.**
- **Advance width is the true physical discriminant — and it is unmeasurable.** A ligature is cast on one
  body, but **you can only measure ink extent**, which differs from body width by a spread varying several
  hundred µm within a page. The `fi` difference in 16-pt roman is **0.15–0.25 em ≈ 15–25 px at 650 ppi,
  against comparable spread noise plus ±2–4 frames of CTC cut jitter.**
- **And forced-aligning to `ﬁ` requires `ﬁ` already in the codec — the lattice circularity, relocated.**

**What replaces it:**

1. **`ſ f æ ﬀ ﬁ ﬂ ﬃ ﬄ` and the macron vowels all stay in the codec**, trained end-to-end. Fix `ſ`/`f` by
   **resolution** (x-height normalisation, §5.5) and **decode-time prior correction**, and report it as a
   per-class confusion, not a subsystem.
2. **Pair CNNs on the crop, no hand features** — over **fixed windows centred on the base model's `f`/`ſ`/`t`
   emission frame**, at native resolution. The discriminators are pair-specific and visual: **`ﬁ`/`ﬂ` — the
   tittle is absent in the ligature sort** (that is the ligature's whole reason to exist); **`ﬀ` — one
   crossbar spanning both stems vs two**; **`ct`/`ſt` — the connecting arc.**
3. **Three-way output — `A` / `B` / `indeterminate` — abstaining into `<unclear cert="">`.** This is the
   honest form, because the realistic ceiling says so: clean instances `ſ`/`f` 0.97–0.99 F1 and `fi`-lig
   0.90–0.95, but **on the tail that matters — touching, over-inked, show-through, worn type — 0.7–0.85, and
   that tail is 10–20% of instances.** **Calibrate the abstention threshold so per-class precision hits
   target, and report the abstention rate as a headline number. An 8% abstention rate on `ſ`/`f` is an
   honest edition; a 0% one is a fabricated one.**
4. **Exploit the sort, not the instance** — the strongest single idea from either panel. **Letterpress
   repeats the same physical sort.** Cluster all `ſ`-candidate crops **per fount per exemplar,
   unsupervised; key ~50 cluster exemplars; propagate.** Per-instance classification throws away the one
   real asymmetry the medium offers.
5. **Mining is bootstrappable — through the TEXT side, never the shape side.** Revision 2's "find candidate
   crops by shape" was circular: you need the classifier to find the instances that train the classifier.
   The terminating procedure both critics converged on:
   1. **Contexts are enumerable with no classifier.** `ﬃ` occurs only where the letters are `ffi`. Search
      the finding aids for tokens containing `ffi|ffl|st|fi|fl|ff` (`office`, `affliction`, `first`) —
      thousands in a 400-page Bible.
   2. **Align those tokens with the incumbent recognizer over the fold-equivalent letters** — `f`,`i` are in
      the codec, so cuts localise to **±1 character even when the ligature is misread as `f`+`i` or
      dropped.**
   3. Crop that window. **Every crop is a positive-context candidate**, and the only remaining question is
      the pair classifier's own.
   4. Key ~200 per class.
   - **Macrons**: mine loci where the recognised token is **exactly one character shorter** than the
     reference token with a nasal at the deletion point.
   - **Declare and bound the recall bias**: you find ligatures only where the reference spells the letters,
     missing compositorial ligatures at unexpected loci. **Bound it by keying a random 100-line sample and
     counting misses.**
   - **`ſ`/`f` cannot be seeded this way** — the finding aids' `ſ` policy is unaudited — so **seed it from
     §7's 200-verse provenance audit**, which is already scheduled.
6. **Store mined instances as whole GT lines with the locus marked, not as crops.** Revision 2 specified
   crops and then required "macro error over the rare inventory **measured on GOLD-GLYPH**" — **crops cannot
   score a line recognizer, so that metric had no computable evaluation path.**

### 5.5 Model scope, input height, and what the sweep really costs

**[SIR'S CALL #2] FOUNT replaces TOME as the third scope level.**

```
CATMuS-Print [Large]  →  SOURCE  →  FOUNT
```

**BOOK was cut in revision 2 and stays cut**: distinguishing 0.60% from 0.50% CER needs ~10⁵ held-out
characters per comparison — more ground truth than this project will ever have — and the books that would
most need a book model are exactly those with no archaic witness and therefore no alignment GT.

**Both HTR critics said TOME-as-written was wrong; they disagreed on the remedy.** One would cut it (it
inherits BOOK's power problem). The other showed *why* it is the wrong axis, and I have taken that:

> What actually varies inside a 1609 tome: the **fount** (roman text vs italic annotation vs blackletter
> heading — **genuinely different letterforms, and the axis §5.2 just declared semantic**), the
> **compositor** (spelling habits, not letterforms — irrelevant to a recognizer), and the **gathering**
> (paper, ink load, impression). **Tome matches none of these — it is a proxy for scan conditions, which is
> what SOURCE already is.**

FOUNT has **far more data per scope than 440 books did**, and it aligns the model hierarchy with the
rendition layer. **Gathering variation is handled by stratifying the held-out split by gathering — the
plan's own independence argument demands this and revision 2 never stated it — not by another model level.**

**Adoption at each level requires** a paired bootstrap over lines, a pre-registered minimum effect size, and
a second never-touched confirmation set; otherwise the winner's curse guarantees the adopted hierarchy
overfits.

**Input height, stated honestly — revision 2 treated the sweep as an incidental line item:**

> In the CATMuS-family VGSL spec, raising H from 120 to 192 multiplies the height reaching the `S1(1x0)1,3`
> reshape by 1.6, **multiplying the LSTM input width by 1.6 — so `ketos train -i catmus.mlmodel --resize
> new` will not transfer the reshape and LSTM layers. Only H=120 warm-starts cleanly from CATMuS.**

- The correct joint move is **a fourth height-only `Mp2,1` stage** to restore the reshape dimension.
  `Mp2,2` pools height *and* width, and **changing width pooling would alter frames/char (~8 at 120 px) and
  confound the whole sweep.**
- Grid: 3 heights × 2 pooling variants minus the invalid cell = **5 configs × 3 seeds = 15 runs** (3 seeds
  because single-run variance exceeds the effect on rare classes). At 6–12 GPU-h/run, with H=192 cold-start
  on the recurrent stack: **120–200 GPU-hours.**
- **Rank on a fixed ~5k-line subset (~40 h), confirm only the top-2 at full data.**
- **Decision metric pre-registered as `ſ`/`f` + macron per-class F1 with a paired bootstrap over lines** —
  **aggregate CER is ~97% dominated by classes 120 px already handles and cannot resolve it.**
- **Normalise to measured x-height, not line-box height.** Line boxes include variable ascender/descender
  and marginalia at other type sizes, so a fixed line-box height presents different stroke widths and blur
  scales across sources at 650 / 300 / ~230 effective ppi. **Without this, any pooled or cross-source model
  is invalid.**

**Ensemble work is deferred** (§0.1 removes its consumer). If it ever returns: voters must have **different
parents** — Reul found same-parent voters vote worse, and revision 1's all descended from CATMuS — a
Calamari voter needs `TF_USE_LEGACY_KERAS=1` on py3.12 **and defaults to binarised input, contradicting
§4.1**, and cross-height ensembling requires **ROVER/alignment-level voting, not frame-level.**

### 5.6 The accuracy target — restated so it can fail

The literature does not support 0.5% over a large diplomatic alphabet on 1582 print: Reul's sub-0.5% is
book-specific models on human-corrected GT with a **small** alphabet, voting away *stochastic* error;
Al Azawi's 0.40% is a **supervised** voter trained on aligned GT.

| metric | target | measured on |
|---|---|---|
| **CER-folded** (long-ſ, ligatures, `æ` folded) | ≤ 1.0% — comparable to the literature | GOLD-TEXT |
| **CER-diplomatic** (full inventory, nothing folded) | **measured floor + δ**, δ pre-registered *before* the floor is read | GOLD-TEXT |
| **per-class precision AND recall**, with support | per class, no aggregate hiding | GOLD-TEXT + glyph census |
| **macro error over the rare inventory** | class-balanced | glyph census, **scored on host lines** |
| **line-segmentation error** (missed / merged / clipped) | pre-registered | GOLD-LAYOUT |
| **WER** | pre-registered | GOLD-TEXT |
| **rendition span P/R/F** | pre-registered, **never folded into CER** | GOLD-TEXT |
| **abstention rate** per contested pair | reported as a headline, not minimised | glyph census |

**Four corrections to revision 2's suite, all from round 2:**

1. **Cluster bootstrap over pages, not Wilson intervals.** Character errors cluster strongly by line, page
   and fount; **Wilson assumes i.i.d. Bernoulli and will be 2–4× too narrow** — and §5.5 already mandates a
   cluster bootstrap for model comparison, so revision 2 contradicted itself.
2. **Attested-form rate is demoted to a diagnostic and may never be a gate.** It **penalises precisely the
   turned letters, wrong-fount sorts and compositorial spellings §0.3 requires preserving**, and its lexicon
   derived from references §2.2 documents as contaminated. Where attestation is used at all, score against
   an **external corpus (EEBO-TCP 1580–1640)** with the overlap rate reported, and **enumerate the
   unattested tokens** rather than reducing them to a number.
3. **Add per-class error stratified by source × fount × neighbour-context, reporting the
   max-over-strata, not the mean** — plus a **run-length / consecutive-error statistic.** Otherwise the
   suite is passed by its most dangerous failure mode: **systematic, attested substitution.** A model
   reading `ſ` for `f` in one ligature context produces output that is *attested* (`ſonne` is a real word),
   scores fine on CER-folded, and is **diluted below detection in per-class recall because the class is
   right 97% of the time overall. Nothing in revision 2's suite conditioned on context**, and it could not
   distinguish 100 scattered errors from 100 errors on one gathering.
4. **The GT's own error rate is reported alongside every target.** If GOLD-TEXT's own CER is 1%, a 0.5%
   target is unmeasurable in principle — **saying so is not a lowered requirement, it is the requirement
   becoming enforceable.**

---

## 6. STAGE 3 — GROUND TRUTH

Alignment is **intra-page**: concatenate a page's recognized lines into one character stream with
line-boundary offsets, concatenate the chapter's reference likewise, align at character level, project each
line's range onto the reference span it matched, then refine per-character cuts with kraken's
`ForcedAlignmentTaskModel`. Character-level alignment keeps `hea-` and `uen` on their own lines — the
Transkribus Text2Image artefact (hyphenated word assigned wholly to one line, fragment dropped) is avoided
by construction.

**Acceptance, and the censoring that survived revision 2.** A line becomes GT under a strict distance
threshold, **and its complement is recorded** as a geometry signal (§4.2.3). But a red team found the
censoring fix was applied to *geometry labels* and **not to GT acceptance**: words the recognizer never read
still never enter GT, so the next generation trains on the same censored distribution.
→ **The fraction of reference span never accepted is recorded and reported per generation as a blocking
OPEN quantity.**

**Substitution costs are NOT derived from the pipeline's own confusion matrix.** Revision 2 specified
exactly that, and it is a circularity both red teams caught: **`ſ`↔`f` becomes cheap *because* the model
confuses them, so confused lines are accepted as GT and the confusion is trained in.** A second defect
compounds it: OCR-vs-reference confusions **contain real textual variance, not just OCR error.**
→ Costs are **typographically motivated** (`m`↔`rn`, `ſ`↔`f`, `u`↔`n`, `c`↔`e` set from letterform
similarity) **or estimated on GOLD-TEXT only**, and **frozen at G1**.

**Never align against the modern finding aids for character supervision.** They supply word identity, never
glyph identity.

**Pseudo-archaic never enters ground truth, and never enters the transcript.** Revision 1 contradicted
itself here; revision 2 resolved it in words but kept it as a *scoring* prior — and a prior that decides
which lines pass GT acceptance **injects synthesised spelling through selection.** Resolved absolutely in
§7-R4.

---

## 7. THE FINDING AIDS

**R1 — Renumber first.** Finish `ref_renumber` so `s_dismas` and `odr_com` share one address space.
**Gate**: offset-0 exact-key agreement after renumbering — not best-match, which can be passed by widening
normalisation without fixing a single verse number — **threshold and n pre-registered**, residue enumerated
per book.

**R2 — De-contaminate `s_dismas`** (apparatus splices). **Gate**: **seed known splices and report detection
recall.** Revision 2's gate was "splice scan clean; audit published," which is a deliverable, not a metric —
**you cannot claim clean without a recall figure.** Unrepairable loci are **OPEN and blocking**.

**R3 — Collapse to ARCHAIC and MODERN finding aids**, adjudicated in batches **after R1 and R2**, or the
adjudicator is fed thousands of pseudo-disagreements — verse offsets and apparatus splices — and will
"correct" sound text onto the wrong verse. Modern disagreements may be adjudicated by reasoning about sense
and completeness; **archaic spelling and glyph disagreements consult the scans.**

**Both archaic transcriptions are finding aids, not authorities** (§2.2). The **provenance audit** — 200
verses against the scans, reporting `ſ`/`s` accuracy, ligature policy and base edition — **runs before any
use**, and doubles as the `ſ`/`f` mining seed (§5.4.5).

**R4 — Pseudo-archaic is cut as a pipeline component.** Revision 2 barred it from the transcript and from
GT, leaving it "an alignment and scoring prior" — at which point, as a program lead observed, it **had its
own gate, its own eval set and its own lattice-size metric, and no consumer.** Its alignment role is
subsumed by §6's typographic substitution costs.

**It survives only as a separately-named reconstruction layer**, under the bright line the scholarly review
supplied:

> `<supplied>` requires `@source` pointing at a **document**. **Rule-generated pseudo-archaic has no
> document source and therefore can never appear inside `<supplied>`, bracketed or not.**

That layer is a **distinct file**, `type="reconstruction"`, **never merged into the documentary text,
excluded from every citable export, and labelled non-documentary at the top of every view.** Used that way
it is legitimate and no reader can mistake it for the text.

---

## 8. STAGES 4–6 — TRANSCRIBE, LOCATE, CONSULT

### 8.1 Transcribe — the correction loop is the deliverable and the ground truth at once

**[SIR'S CALL #3] Both first-builds ship, composed: the residue detector orders the pages, the correction
UI transcribes them.** One program lead proposed each; they are complementary, and the second carries the
load-bearing claim:

> **Gold-keying and production transcription are the same keystrokes.** Page → lines → incumbent recognizer
> → operator correction UI → sha-pinned corrected page. **One activity, five outputs**: (a) shippable
> product, (b) GOLD-TEXT, (c) fine-tuning GT for the next generation, (d) GOLD-LAYOUT if the UI captures
> line and region boxes, (e) glyph-census instances via click-to-tag. **That is the only way ~250 hours of
> annotation becomes affordable — it is not overhead, it is the deliverable.**

- **The residue detector feeds it.** Per leaf, the fraction of the chapter's reference span matched by no
  recognised line, plus the reference-independent signal of §4.2.3. Sort leaves by residue → a **ranked
  defect queue**. It needs no gold set, uses the incumbent pipeline **as a detector rather than a
  generator** (so its bias does not propagate), targets exactly the clipping failure the campaign has been
  fixing by hand, and **produces GOLD-LAYOUT's stratification for free.**
- **A VLM proposes corrections on line crops**, accepted or rejected by keystroke. **It sees a crop, never a
  page** — the one place a vision model touches the product.
- **A rolling held-out set that is free and cannot be gamed**: fine-tune every N signed-off pages, and
  **measure CER on the last 20 signed pages *before* they entered training.** Never stale, no annotation
  cost, and **immune to adaptive leakage because each slice is used exactly once.**
- **The board is never the metric here, because the corrected page *is* the reference.**
- **Order the first pages from a zero-archaic-witness book** (Ecclesiasticus, Isaie). Those 8,383 loci are
  structurally invisible to every reference-based mechanism in the plan and **will otherwise be discovered
  last.**

### 8.2 Locate — two address systems, both primary in their own register

The tome map gives, for every page of every source, its book and chapter, so the lookup is a query rather
than a search. **Iterate the union verse table (37,166), not the archaic arm** — revision 1's loop was
`for (book, chapter) in ARCHAIC`, silently dropping the 22.6% with no archaic witness, i.e. exactly the
books the product must not omit. The tome map's "100% coverage by construction" is a tautology, not an
accuracy claim, and needs a **held-out audit with a reported page-assignment error rate, threshold and n
pre-registered.**

**Three independent signals for one address** — tome map (leaves), `VerseNumber` regions (numerals),
alignment (content) — and **a disagreement among them is a flag, not an average.** The printed numeral does
not decide: psalm titles counted as verse 1, `xv`/`xu` misprints, merged and split verses and chapter-opens
mid-page all produce numerals that lie. **Content alignment assigns the address.** Rare-token anchoring
returns as a **cheap post-hoc orthology guard**: any witness whose identity to the emerging consensus falls
below threshold is rejected rather than aligned.

**The two systems, per the scholarly review** — revision 2 had only one and it was the wrong one for
citation:

- **Page/signature is the primary physical address** (`<pb n="" facs=""/>`, `<milestone unit="signature"/>`)
  — verses span pages, and 1582 and 1609 paginate differently.
- **Verse is the secondary logical address**, following **the base document's own numerals where they
  exist**, with the content-derived address recorded as a **separate attribute** when they differ.
- **Never silently normalise to modern versification.**

### 8.3 Consult — collation detects, it does not generate

Under §0.1 there is no six-way collation and no variant graph. What remains is a **verse-level diff of each
consulted surrogate against the base transcript**, which finds the same disagreement loci at a fraction of
the machinery. A disagreement routes to exactly one of three places:

1. **Base document legible and stands** → no record. The overwhelming majority.
2. **Base illegible, same-setting surrogate resolves it** → **surrogate register** (§0.4). Not apparatus.
3. **Different-setting supply, or a demonstrable press error** → **intervention apparatus**, bracketed,
   with the supplying document's STC number and date.

**The constraint that kills the chimera class outright**: the adjudicated reading must be a path **some
document actually supports.** Revision 2's path-validity constraint permitted a path assembled from
*different* witnesses across a verse; under documentary discipline the stronger form holds — **the base
document's reading stands unless the locus is individually and visibly emended. There is no witness-voting
path for accidentals at all.**

**Withdrawn with the six-way collation**: per-column character MSA (the `ſoñne` chimera), the partial-order
variant graph, isotonic calibration, LLR summation, indel priors, Henikoff weighting, effective-N, and the
write-back drift guard. The worked counter-example that killed per-column MSA is retained in the round-1
record; it no longer needs a mechanism here because the stage that produced it is gone.

**One guard survives, because its failure mode survives**: **image adjudication fires on low-confidence loci
*and* on a random sample of loci where everything agrees.** Concurrence between a model and a finding aid
that helped train it is not evidence, and the unanimous sample is the **only estimator of the
correlated-error rate we will have.**

---

## 9. EVALUATION ARCHITECTURE

This section is new. Revision 2 scattered its evaluation commitments across six sections and both red teams
found the same consequence: **nine or ten of twelve gates could not fail as written**, and **δ — used in
three places as the convergence criterion — was never given a value anywhere in the document.**

### 9.1 Three tiers, and a published query ledger

**Freezing a set prevents *contamination*; it does not prevent *adaptive leakage*. Revision 2 conflated
two different failures.** The arithmetic, computed independently by both red teams:

> Per generation ≈ 3 layout + 5 recognition + ~6 sweep + 5 escalation rungs ≈ **19 queries; three
> generations ≈ 57.** At the plan's own set size, SE = 0.074%, so **E[max of 57 noise draws] ≈ 2.4σ ≈ 0.18%
> apparent CER gain from pure noise — larger than any δ the plan would plausibly set.** And **escalation
> rung 1 was "annotate more pages" — growing the eval set in response to failing it.**

| tier | use | discipline |
|---|---|---|
| **DEV-GOLD** | sweeps, escalation rungs, all iteration | unlimited queries |
| **VAL-GOLD** | generation adoption decisions | **Laplace-noised reporting, tolerance T=0.3%, hard budget B=20 queries, counter published in every report.** Exhausting the budget requires **re-keying new pages** before continuing |
| **HOLDOUT-GOLD** | **opened once, at publication** | supplies **the only publishable numbers** |

**Escalation rung-1 pages go to DEV/train only — never to VAL or HOLDOUT.**

### 9.2 Sizing — the honest arithmetic in both directions

Revision 2 was attacked from both sides and **both attacks were right, because the sets were sized for the
wrong scope.**

**Too small** — for the gates it wrote: 400 lines × ~45 chars ≈ **1.8×10⁴ chars/source, 5.6× short of the
plan's own stated ~10⁵ requirement.** At p=0.01, SE=0.074%, 95% CI **±0.145%**, and **±0.21–0.25% once
error clustering is accounted for.** So "CER-folded ≤1.0%" **could not be distinguished from 1.29%.**
Properly powered to detect δ=0.1%: **~5,000 lines/source = 30,000 lines total.**

**Too large** — for the work: **155–275 h and 210–280 h**, independently costed. GOLD-TEXT 55–150 h ·
GOLD-LAYOUT 25–75 h (ink-tight boundaries, because the gate is boundary error *in pixels*) · glyph work
20–40 h plus miner development · floor 25 h. **At 12 productive hrs/week that is 17–23 weeks before the
product stage can start.**

**Both resolve under §0.1.** Diplomatic keying care is required **for the base document only**:

| set | scope after §0.1 | size | hours |
|---|---|---|---|
| **GOLD-TEXT** | base document only, **grown continuously by §8.1's correction loop** | 200 lines to start | **8–12 h**, then free |
| **GOLD-LAYOUT** | eval half **split by gathering, never by page** | ~80 eval + ~60 seed | ~15–20 h, then free via the UI |
| **glyph census** | see §9.3 | exhaustive on a declared page set | deferred to G1 |
| **NOISE-FLOOR** | see §9.4 | 150 lines × 3 keyings | ~15 h + one paid validation |

**Not reducible in kind, and non-negotiable**: a frozen, image-derived, never-trained-on evaluation half for
text and layout. Round 1 was right that without it every number is circular. **It is ~15–20 hours, not
200.**

**Stratification — revision 2's was arithmetically impossible.** 6 sources × 2 parities × 73 books = **876
cells for ~125 eval pages = 0.14 pages/cell**, and the five zero-witness books got ~8 pages across all
sources — **the stratum the plan called structurally critical was the one it could not measure.**
Marginalia was worse: ~15 blocks in 125 pages, **Wilson width ±25pp, so the marginalia gate was
unfalsifiable at any threshold.**
→ **Stop stratifying on book.** Stratify **source × parity × page-type** (~48 cells, ≥3 pages each ≈ 150
pages), **plus purposive over-sampling: ≥40 pages from zero-witness books and ≥60 selected *because* they
contain marginalia**, with sampling weights recorded and the estimator re-weighted. **Report marginalia at
block-level n.**

### 9.3 The glyph census — a census, not a rate

Revision 2 required **≥200 instances per rare class** while §5.3 stated those classes **occur tens of times
corpus-wide.** Both red teams called this what it is: **a requirement that cannot be met, whose escape
clause ("where the class exists at all") converts it into automatic satisfaction at n=30 — a below-threshold
unit given a terminal accepted state, which is the one thing this project forbids.** And because instances
were **mined by the detector under evaluation, misses were invisible: rare-class recall was unmeasurable by
construction.**

- **Exhaustive keying of a declared page set**: every instance on N fully-keyed pages, so **the denominator
  is page-defined, not detector-defined.**
- **Clopper–Pearson intervals** on the true n.
- **Disjoint train/eval halves split by page**, with the never-train rule applied verbatim — revision 2
  trained the pair classifiers on the same set it scored them on.
- **Census below n=30 ⇒ UNMEASURABLE ⇒ OPEN and blocking. Never silently passed.**
- **A census is stronger than a recall figure on n=12, not weaker.** Every instance found and adjudicated
  once, published as a list.

### 9.4 NOISE-FLOOR — and the second human who does not exist

This is the named stall component. Revision 2 defined the floor as double-keyed by two transcribers and
made CER-diplomatic's target *floor + δ*. **There is one operator. An agent cannot supply an independent
*human* floor — that is the entire point of the measurement.** And the estimator self-lowers: **δ was
unfixed while the floor was measured first, so poor agreement would drop the requirement.**

1. **Pre-register δ *before* the floor is read.**
2. **Time-separated blind self-re-keying** — same operator, ≥3 weeks apart. This is an **intra**-transcriber
   floor, a **lower bound** on the true floor, which is the conservative direction. **It is labelled as such
   everywhere it appears.**
3. **Three keyings on n=150** rather than two on 300, to expose 3-way vs 2-way agreement and estimate the
   **correlated error** that two keyers sharing one protocol cannot see — *both misread the worn `?` as
   `;`, both miss the same macron* — **and that is the component that actually bounds achievable CER.**
4. **Per-class floors on a purposive census** of `ſ`/`f` and macron (≥300 instances each, drawn by census
   not by line sampling). 300 lines yields perhaps **5 `ſ`/`f` disagreements — the floor for the single
   distinction the edition rests on, estimated from 5 events.** **A single aggregate floor is not usable
   for a per-class target.**
5. **Buy ~8 hours of a second keyer for the 150 lines (~$200–400) to validate the self-re-key once. If the
   two diverge, ALERT: the floor estimator needs redesign.**
6. Resolve each disagreement against a magnified crop and record a **per-class irreducible-ambiguity rate**
   — the `ſ`-nub, macron-versus-speck cases. That per-class rate is what §5.6 actually needs.

### 9.5 Circularity — every surviving path, closed

Revision 2 cut the main loop and declared the matter settled. Two red teams found **six** live paths.

| # | path | closure |
|---|---|---|
| i | **alignment substitution costs from the pipeline's own confusion matrix** | typographically motivated or GOLD-TEXT-estimated; **frozen at G1** (§6) |
| ii | **isotonic calibration on pipeline-generated alignment GT** | stage cut with the ensemble (§8.3); any survivor calibrates on GOLD-TEXT, **unweighted** |
| iii | **attested-form rate scored against a lexicon derived from the object under repair** | **external corpus (EEBO-TCP 1580–1640)**, overlap reported; demoted to diagnostic (§5.6) |
| iv | **residue-as-signal computed against a reference that is absent at the 8,383 loci** | **reference-independent residue**: ink-groups with no line assignment (§4.2.3) |
| v | **GT acceptance still censors what the recognizer never read** | **never-accepted reference-span fraction reported per generation as a blocking OPEN quantity** (§6) |
| vi | **G2 regions relabelled from G1 alignment, which ran on G1 geometry** | the only external check is GOLD-LAYOUT, so §9.1's query ledger is what makes it honest |

Also closed: **§9.6's drop-cap board fix no longer keys off an internally-derived lexicon**, and **mining is
text-side, so the glyph denominator is not detector-conditioned** (§5.4.5, §9.3).

### 9.6 Every gate, with all five fields

**Document-level invariant: no step enters the build order until its row carries metric · threshold ·
named set · n · pre-registered effect size.** Revision 2 had two complete rows out of twelve.

| # | step | metric | threshold | set | n |
|---|---|---|---|---|---|
| **0a** | source concordance | fields resolved per source | **100%, no UNKNOWN** | — | all sources |
| **0b** | JBIG2 substitution | `ſ`/`f` and `c`/`e` substitution rate | **≤0.1%, CI upper bound** | composite-vs-mask pairs | 20 pages, **per-class instance count reported** |
| **0c** | binarisation gap | zero-shot CER, grayscale vs 1-bit | **reported per source**; 1-bit sources scoped separately | DEV-GOLD | 200 lines |
| **1** | drop-cap board fix + page axis | cells moving to OPEN | **18, reported against a frozen board, never netted** | board | 18 |
| **2** | residue detector | leaf-ranking precision@50 vs hand-found defects | **≥0.6** | campaign history | 50 leaves |
| **3** | pilot gold | **keying rate and variance measured** | protocol validated; **rate published** | pilot | 60 lines, 20 pages |
| **4** | R1 renumber | offset-0 exact-key agreement | **≥99.8%** (from 92.0%) | both finding aids | all 13,292 shared |
| **5** | R2 de-contaminate | **splice detection recall on seeded splices** | **≥0.90** | seeded set | ≥100 seeded |
| **6** | provenance audit | `ſ`/`s` accuracy, ligature policy, base edition | **published, no threshold — it is a characterisation** | scans | 200 verses |
| **7** | tome map | page-assignment error rate | **≤1%** | held-out | 300 pages |
| **8** | GOLD frozen | sets sha-pinned; **gathering-level split**; keying rate from step 3 | **frozen; per-class n published** | — | §9.2 sizes |
| **9** | G1 geometry | marginalia recall / precision · boundary error | **≥0.85 / ≥0.90 · ≤8 px median, ≤25 px p95** | GOLD-LAYOUT eval, **recognizer frozen** | ≥125 pages, block-level n |
| **10** | G1 recognition | CER-folded · CER-diplomatic · per-class · abstention | **≤1.0% · floor+δ · published per class · reported** | GOLD-TEXT | §9.2, cluster bootstrap |
| **11** | alignment | accepted-line precision · **never-accepted span fraction** | **≥0.98 · reported, blocking if rising** | held-out | 500 lines |
| **12** | G2 | primary scalar + non-inferiority set | **Δ > δ ⇒ adopt; Δ < δ ∧ below target ⇒ STALLED, blocking; worse than G1 beyond paired CI ⇒ revert** | VAL-GOLD | budget B |
| **13** | publish | apparatus schema validates; **HOLDOUT opened once** | **schema-checkable completeness assertion** | HOLDOUT | — |

**Steps 4–7 run in parallel with 1–3. Nothing except the metric *claims* waits on step 8** — that
decoupling is the direct answer to §0.6.

### 9.7 Escalation — with a receiver, a ceiling, and a different resource class

Revision 2's ladder terminated in "escalate to Sir with the measured floor attached." **Sir is the operator;
escalation from the operator to the operator is a no-op**, and no rung had a cost ceiling, so "after N rungs
with improvement < δ" had **no N and no δ.**

- **Pre-register N=3 rungs and an hour ceiling per rung**, before the generation starts.
- **Every escalation must name a *different resource class* than the one that failed**: paid annotation
  hours · a purchased or borrowed better scan · an outside palaeographer's ruling · or **a stated scope
  reduction in *coverage* — fewer books at full fidelity — never a reduction in fidelity.**
- **Escalation writes a dated, numbered ALERT record** naming the approach to be redesigned; the component
  parks as **OPEN with that number attached.** It is never a terminal acceptance.
- **Release-blocking vs campaign-open.** Applying "OPEN and blocking" uniformly means nothing ever ships.
  **Base-document loci are release-blocking; everything else is campaign-open.** Both stay open; only one
  gates a version.

---

## 10. THE BOARD, AND THE APPARATUS

### 10.1 Board

- **The governing (archaic-preeminent) gate is not adopted on provenance.** "Approved 2026-07-10" is
  provenance, not evidence, and the party proposing the change benefits from it. Before adoption:
  **blind-adjudicate a random sample of n ≥ 100 newly-passing cells against the scans** — the adjudicator
  sees image and candidate reading, **not which gate it passed or which way it moved** — with the
  vindicating pass rate **pre-registered**. **The +122 and the −18 are reported separately against a frozen
  board, never netted.**
- **"WARNING class, not a silent pass" stays withdrawn.** It was itself a silent pass: a below-threshold
  unit converted to a terminal non-blocking state. A cell passing ARCHAIC while failing MODERN badly is
  **OPEN and blocking**; the warning is the alert, not the disposition.
- **A page axis is added** — every open cell already carries its leaf, and a per-leaf view sorts geometry
  defects to the top by construction. It is also what the residue detector writes into.
- **The drop-cap class opens now**, independently of everything else.

### 10.2 Minimal viable apparatus

Revision 2 specified a critical edition's apparatus. Under §0.2 most of it is unanswerable and the rest is
noise. **One record type, at intervention granularity — the overwhelming majority of verses produce zero
entries:**

```
{ locus:  signature + leaf side + line + char-offset   (e.g. Aa3v.12.7)
  verse:  secondary logical address
  category: gap | unclear | resolved-from-surrogate* | supplied-from-other-setting
          | sic-preserved | editorial-correction
  base_reading | adopted_reading | evidence | agent | cert }
```
`*` lives in the surrogate register (§0.4), not the apparatus.
`evidence` = surrogate id + `@facs` zone, **or** the supplying source's STC number **and date**.

**Once per edition, not per locus**: STC/ESTC + repository + shelfmark + **made-up-leaf table** · scan
provenance and checksums · **a statement of editorial principles listing what is silently normalised** (line
breaks, word division at line-end, whitespace) **so those never generate records** · TEI header with
`<sourceDesc>`, `<encodingDesc>`, `<respStmt>` · versioned, sha-pinned release.

**`<pb n="" facs=""/>` and `<milestone unit="signature"/>` in the text stream are the one non-negotiable
obligation — without them no reading can be checked against the book.** They must be captured **during**
transcription or never.

**Demoted to optional or cut**: the rejected-variant record (that is a critical edition's negative
apparatus — **ship the raw collation output as a data file, not as prose**) · **press-variant collation as a
programme** (it needs multiple exemplars per forme we do not have → a stated caveat plus opportunistic
recording where a second exemplar exists) · **uncertainty markup at every adjudicated locus** (restrict to
loci **not** resolved by the base image, or the markup is noise).

### 10.3 The uncertainty gradient the transcript may use

| state | encoding | plain-text export |
|---|---|---|
| read, confident | plain text | the reading |
| read, uncertain | `<unclear reason="damage\|inking" cert="low\|medium" resp="">` | **the reading, flagged** |
| not read | `<gap reason="damage" quantity="4" unit="chars"/>` | **the gap, never a guess** |
| supplied from a **document** | `<supplied source="#stc____" cert="">` | **bracketed in every view** |

**The bright line, restated because it is the project's central editorial commitment: `<supplied>` requires
`@source` pointing at a document. Rule-generated text has no document source and can never appear inside it.**

### 10.4 What is in the transcript — the scope table revision 2 omitted entirely

The scholarly review found **no lineation, hyphenation or paratext policy anywhere in the document**, and
called these the largest unstated scoping decisions in the project. **These are Sir's to set; my proposed
defaults follow, and every one is cheap to change now and expensive to change later.**

| class | proposed | note |
|---|---|---|
| original line breaks | **preserved**, `<lb/>` | diplomatic requirement |
| line-end hyphenation | `<lb break="no"/>`, both fragments kept | §6 aligns at character level to make this possible |
| catchwords | **excluded** from the reading text, recorded | standing instruction |
| signatures | **recorded as milestones** | §10.2, non-negotiable |
| running heads | **recorded**, separate layer | |
| chapter arguments | **included**, marked | they are part of the book |
| marginal annotations | **included**, separate layer, **keyed to text by the §5.1 reference marks** | **the apparatus is half the book** |
| 1582 preface, chapter-end annotations | **included** | |
| verse numerals | **recorded as printed**, address per §8.2 | |
| word division, whitespace | **silently normalised**, declared in the editorial statement | so it never generates records |

---

## 11. BUILD ORDER

Sequenced so that **value ships in week 2** and metric *claims* — not improvements — are what wait on
frozen evaluation sets.

| # | step | ships | depends on |
|---|---|---|---|
| **0** | Source concordance; **declare the three base exemplars**; resolve or delete arXiv:2607.00596; **inspect the scans for blackletter / `ꝛ` / brevigraphs** | the decision the constitution needs | — |
| **1** | **Drop-cap board fix + page axis** | 18 cells | — |
| **2** | **Residue detector** → ranked leaf defect queue | a working defect queue for the existing chapter workflow | — |
| **3** | **Correction UI**, single-witness, base document first, **starting in a zero-witness book** | **transcript pages, and GOLD-TEXT, and GT, and GOLD-LAYOUT, and census instances** | 0, 2 |
| **4** | JBIG2 test; grayscale policy; 1-bit→uint8 + 0.8 px Gaussian | raster policy settled | — |
| **5** | R1 renumber; R2 de-contaminate; provenance audit | finding aids usable | — |
| **6** | **Pilot gold** — measures keying rate and variance | the sizing evidence for step 7 | 3 |
| **7** | GOLD-TEXT / GOLD-LAYOUT frozen, **split by gathering**; NOISE-FLOOR (3 keyings + paid validation); **δ pre-registered** | the frozen sets | 6 |
| **8** | Tome map + held-out audit | addressing | 5 |
| **9** | **G1 geometry** — ink shapes, text labels, dual residue signal | region model v1 | 7, 2 |
| **10** | **G1 recognition** — inventory, atomic codec, x-height, SOURCE scope | recognizer v1 | 7, 4 |
| **11** | Alignment with typographic costs; `unclear`/`gap` and page anchors **in the data model** | line GT at scale | 10 |
| **12** | **Glyph census**; text-side mining; pair CNNs with abstention; H×pooling sweep | rare-class evidence | 10, 11 |
| **13** | **FOUNT scope**; style classifier **or** explicit scope-out | recognizer v2 | 12 |
| **14** | G2; **HOLDOUT opened once**; apparatus; versioned release | the edition | all |

**Steps 1, 2, 4, 5 need no gold set and no new model.** Step 3 begins as soon as a base exemplar is
declared. **Nothing in the first quarter waits on step 7.**

---

## 12. OPEN AND UNMEASURED

**Blocking, this week**: the **source concordance** (§1 — every field UNKNOWN, and the constitution is
unimplementable without it) · **arXiv:2607.00596 carried unverified from V2 and load-bearing for §4.2's
gate — resolve or delete** · **inspect the scans** for blackletter headings, `ꝛ`, and Latin per/pro
brevigraphs (**one task, closes three inventory questions**).

**Open, measured later**: JBIG2 symbol substitution *and* the separate binarisation gap · pair-CNN
separability on the touching/over-inked tail, and the abstention rate it forces · whether unsupervised sort
clustering per fount propagates as cleanly as the medium suggests · input height jointly with pooling ·
`ch8/8:14` policy · whether the style classifier is built in G1 or style is formally scoped out.

**Two decisions Sir has said he leans toward and has NOT ratified**: adopting the governing
(archaic-preeminent) gate, and opening the drop-cap class. **The drop-cap class opens now (§10.1). The gate
change now requires blind adjudication of n ≥ 100 newly-passing cells first (§10.1).**

**Four [SIR'S CALL] items where same-remit specialists disagreed and I decided** — each reversible in a
paragraph: **#1** documentary framing over copy-text (§0.2) · **#2** FOUNT over TOME (§5.5) · **#3** both
first-builds, composed (§8.1) · **#4** `ꝛ` and brevigraphs deferred to inspection (§5.1).

**Housekeeping, flagged not fixed**: this document and both critique records live in a **gitignored scratch
directory**. They are the most valuable artefacts of the last two sessions and are currently one `rm` from
gone. Moving them under version control is a five-minute change **and it is Sir's call where the project
keeps its planning documents**, so I have not moved them unilaterally.

---

## 13. CITATIONS

**Resolved**: arXiv:2112.12703 · arXiv:2511.08903 (**88.2 AP at 5% labels — evidence *for* a small seed set,
not against one**) · arXiv:1802.10038 (Reul et al.) · arXiv:1711.09670 · arXiv:2509.19768 (CHURRO) · kraken
docs (VGSL input height, `ketos segtrain` typology, `ForcedAlignmentTaskModel`, `PytorchCodec`) ·
CATMuS-Print [Large] + guidelines · Bollmann & Søgaard 2016 · Pettersson et al. 2014 · cSMTiser ·
Al Azawi et al. · Transkribus Text2Image hyphenation artefact · OmniDocBench / olmOCR-Bench.

**Editorial**: Greg, "The Rationale of Copy-Text" · Bowers, *Principles of Bibliographical Description* ·
Tanselle, "The Editorial Problem of Final Authorial Intention" and "Editing Historical Documents" ·
**TEI P5 ch. 11, *Representation of Primary Sources*** (the framework this revision adopts) · STC/ESTC
practice for imperfect and made-up copies.

**Unverified and not to be relied on until resolved**: arXiv:2607.00596 · the candidate STC numbers for the
1582 NT and 1609 OT surfaced during critique.

**Overreach corrected (retained from revision 2)**: arXiv:2112.12703's leverage was TEI *structural markup*
typing regions directly; our verse-keyed plaintext has no page association, 43.6–69.7% coverage and
documented contamination. The claim "we are a better case than theirs" is **deleted** — four witnesses
corroborate *word identity*, never *region geometry*, because they have different page layouts.
