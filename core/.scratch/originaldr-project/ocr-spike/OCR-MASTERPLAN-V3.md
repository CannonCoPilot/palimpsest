# OCR MASTERPLAN v3 — one faithful diplomatic Douay-Rheims

**Rewritten top to bottom 2026-08-03** after Sir rejected v3-draft's direction. That draft is superseded in
full, not amended. `OCR-MASTERPLAN-V2.md` remains the record of the ladder experiments; its pinned negative
results are carried forward in §14 and re-opened where they were used as excuses rather than findings.

---

## 0. WHAT WE ARE BUILDING — stated once, and everything else follows from it

> **A single diplomatic transcript of the 1582/1609–1610 Douay-Rheims, faithful in spelling and in
> archaic typography, complete across the whole Bible.**

Three consequences, and every later section is downstream of them:

1. **The six source OCRs are required inputs at publication quality — not intermediates to be skimped.**
   Consensus does not launder bad inputs into a good output; it multiplies the reliability of good ones. Every
   source is driven to full geometric parsing, optimised character recognition, and complete preservation of
   the archaic glyph inventory. *There is no "good enough to vote" tier in this plan.*
2. **The 1630s editions (S06 1635, S04 1633) are supplemental voters, not co-equal targets.** They are
   evidence about the words on a page. They do not earn their own transcript, and the product does not carry
   parallel edition variants.
3. **The alignment-and-voting stage is the final stage, not the spine.** It is where near-perfect per-source
   readings are collated verse by verse and used to correct glyph and spelling into ARCHAIC. It is worthless
   if fed mediocre input, which is why (1) is not negotiable.

### 0.1 The failure mode this rewrite corrects — in me, not in the code

Across the previous three exchanges, every time a measurement came back ambiguous I converted it into a reason
to keep the status quo:

| measurement | what I concluded | what was actually true |
|---|---|---|
| native resolution ≈ current at the metric's sensitivity | "no free win; adopt later" | the *model* was co-adapted; retrain it |
| model rescales lines to 120 px | "a training-time architecture choice, so not now" | `-s '[1,H,0,1 …]'` — it is a **parameter**, set it |
| attested-rate metric too coarse to resolve 0.2 pt | "we are at the limit of what can be measured" | build the better metric; that is Stage 3's job |
| voting turns weak inputs into strong consensus | "sources need only be good enough to vote" | the target is per-source publication quality |

That is status-quo preservation wearing the costume of empiricism, and it is the same disease as silent
degradation one level up: **an inconvenient result being converted into a terminal acceptance.** The rule for
this document: *an ambiguous measurement licenses a better experiment, never a lowered requirement.*

---

## 1. THE MEASUREMENTS THIS PLAN RESTS ON — corrected

### 1.1 `s_dismas` and `odr_com` are, as Sir said, essentially the same text

My earlier figures ("94% differ", "27.3% substantive", "88.8% character agreement") were artefacts of three
compounding errors: comparing verses **by key** when the two projects' verse numbering is known to diverge,
failing to strip verse numbers and footnote digits, and folding neither case nor `æ`. Corrected — content-
aligned within a ±5-verse window, normalised for long-ſ, `æ/ae`, case, punctuation and digits:

| measure | value |
|---|---|
| mean similarity | **0.9879** |
| median similarity | **1.0000** |
| verses ≥ 0.999 identical | 10,507 / 13,292 (**79.0%**) |
| verses ≥ 0.99 | 88.3% |
| verses ≥ 0.95 | 95.5% |
| **verses whose best match sits at a non-zero verse offset** | **1,062 (8.0%)** |

**The 8% is the finding, not the 1%.** It is a numbering-mapping defect between the two transcription
projects, concentrated in Psalms, Acts, Luke, Matthew and Mark — exactly where DR numbering conventions
diverge (psalm titles counted as verse 1 or not; Gospel and Acts chapter divisions). `ref_renumber` exists to
correct this and is evidently incomplete. **Any verse-keyed comparison of these two references is invalid
until it is finished**, and the earlier figures in this project's history that were computed verse-keyed are
retracted.

### 1.2 `s_dismas` carries spliced apparatus, systematically

`ruth/1/1` — *"…to ſeiourne in the **The hiſtorie of Ruth is regeſtred in holie Scripture, for**…"*; the
verse tail is lost and the annotation is in its place. `genesis/10/1` — *"and children were **q. 57. in Gen.
ho. 29. Moral. c. 18. Tradit. Hebra.**"*. This is the same defect class we chase in our own OCR, frozen into
the reference that **governs** the archaic gate. It must be detected and repaired before ARCHAIC is built.

### 1.3 Coverage, measured independently per reference

Denominator = the union of all four references (this project holds no external canonical verse table; the
figure states this on its face, and a chapter shown complete may still be short if *all four* are short).

| reference | arm | verses | % of union | chapters complete | chapters absent |
|---|---|---|---|---|---|
| `s_dismas` | ARCHAIC | 25,892 | **69.7%** | 719 / 1,360 | **369** |
| `odr_com` | ARCHAIC | 16,201 | **43.6%** | 552 / 1,360 | **774** |
| `sabates_a` | MODERN | 37,130 | 99.9% | 1,325 / 1,360 | 0 |
| `madueke_b` | MODERN | 35,809 | 96.3% | 1,299 / 1,360 | 26 |

Union: **37,166 verses across 1,360 chapters.** The two archaic references combined still leave **8,383 loci
(22.6%) with no archaic witness at all** — Ecclesiasticus 1,592, Jeremie 1,363, Isaie 1,292, Ezechiel 1,272,
4-Esdras 856, 3-Esdras 450.

**`coverage_figure.py` renders this as a book × chapter grid per reference, with Douay-Rheims book names and
their modern equivalents. It is a required panel of the report from this version forward.**

### 1.4 Raster reality

| source | native raster | what the pipeline fed the recognizer |
|---|---|---|
| `archive-holiebible-ot1` (S9) | 3231 × 4392 (650 ppi, 1-bit JBIG2 in the PDF; jp2 matches) | 2200 × 2990 |
| `jp2-S06` | **JPEG 2550 × 3301** (JP2s corrupt; PDF stencil 2867 × 4146 CCITT) | *nothing — raster path was dead* |
| `pdf-S03a` | 2262 × 3116 (500 ppi) | 2200 × 3030 |
| `S08` | 3035 × 4336 | — |

`reocr_core.preprocess()` forced `MAXW=2200` with LANCZOS and applied unconditional `autocontrast`. The A/B/C/D
experiment found no significant difference **with the current model** (spread ≤ 0.002 on the attested-char
metric) — which measures the model's co-adaptation, not the value of resolution, because
`reichenau_dr.mlmodel`'s VGSL input is `(1, 1, 120, 0)`: every line is rescaled to 120 px regardless. **Input
height is a settable parameter** (`ketos train -s '[1,H,0,1 …]'`), and kraken's own documentation states that
its old 48 px default destroys diacritics and abbreviation marks after three `Mp2,2` stages — which is
precisely our ligature and abbreviation problem. §4 sets it deliberately.

---

## 2. THE PIPELINE

```
 0  ACQUIRE      volume → verified native rasters, no lossy step anywhere
 1  GEOMETRY     page → typed region polygons (trained; distantly supervised)
 2  RECOGNISE    region → lines → diplomatic text over the full glyph inventory
 3  GROUND TRUTH forced alignment + variant lattices → line- and glyph-level GT
 4  PER-SOURCE   six transcripts, each driven to publication quality
 5  LOCATE       tome map → book:chapter:verse addressing across all six sources
 6  COLLATE      per-verse multiple alignment of six witnesses + ARCHAIC
 7  RESTORE      glyph-and-spelling voting, image adjudication → THE TRANSCRIPT
```

Stages 5–7 are the final stage Sir describes. Stages 0–4 exist to make their input worth collating.

---

## 3. STAGE 0 — ACQUIRE: highest available fidelity, as a requirement

**Rule: the working chain contains no lossy or resampling step, anywhere, ever.**

1. **Extract, never render.** `pdfimages -png` writes the decoded native stream. For the MRC files (S03a, S09)
   that is the 1-bit mask carrying every letterform — verified: S09 p60 → `3231 × 4392`, mode `1`. Rendering
   composites that crisp mask with a near-empty 22 KB colour layer and returns an antialiased grey image; the
   noise is created by the export.
2. **Composite only when the page genuinely needs it** (plates, colour), at *exactly* native ppi:
   `pdftoppm -r 650 -png` → 3232 × 4393, verified 1:1.
3. **PNG or TIFF only.** No JPEG in the working chain.
4. **No autocontrast, no denoise, no sharpen, no binarisation of our own** in the default path. Any tonal
   operation is per source, measured, and recorded in `SOURCE_MODEL`.
5. **No page-level resize.** `MAXW` is deleted. Scaling happens exactly once, inside the recognizer, at the
   line-height the model declares (§4.2).
6. **S06 reads JPEG** — `jp2_page.py` now maps `jp2-S06` to `Douay-Rheims-1610-Bible_jpg` (2,872 leaves,
   2550 × 3301, magic-byte verified) and `_pages()` falls back across `.jp2/.jpg/.png/.tif` with a
   `FileNotFoundError` naming the source instead of an `IndexError` from inside a recognition run.
   **Verified working.** The corrupt set stays renamed `_jp2_broken`. A PDF-stencil extraction at 2867 × 4146
   is queued as a candidate upgrade, to be adopted on measurement.
7. **A raster manifest per source** — path, native dimensions, bit depth, provenance, checksum — so a silent
   substitution is impossible and every later experiment can name what it consumed.

---

## 4. STAGES 1–2 — GEOMETRY AND RECOGNITION, BUILT FOR THE INVENTORY WE WANT

### 4.1 Geometry: a trained region model, distantly supervised

`PAGE_OVERRIDE`'s 371 constants are replaced by a kraken segmentation model over a real typology:
`MainText`, `Marginalia`, `RunningHead`, `VerseNumber`, `Argument`, `Annotations`, `DropCap`,
`Signature/Catchword`. Regions come back as polygons in the baselines' own coordinate space, so a rotated leaf
needs no compensation.

**Labels are derived, not drawn.** Every class is decidable from text we already hold:

| class | derivation |
|---|---|
| MainText | lines aligning to ARCHAIC verses of this chapter (Stage 3) |
| Marginalia | lines aligning to `madueke_b`'s 1,334 transcribed apparatus blocks |
| RunningHead | top-band line matching the book's head form, recurring at the same y across the gathering |
| VerseNumber | numeric token whose value matches the verse the adjacent aligned text belongs to |
| DropCap | oversized glyph at a chapter open — **the class that hides the 13 verse-1 defects on the board** |
| Catchword | last line, single token, equal to the first token of the next leaf — self-verifying |

Precedent: arXiv:2112.12703 trains layout models for printed books from digital-edition markup, validated at
Deutsches-Textarchiv scale. We are a better case than theirs: four witnesses of one text let a label be
corroborated across witnesses before it is trusted.

**Agents are one voter of three, never an oracle.** Signal A = distant supervision; Signal B = a sub-agent
given the page image, returning typed polygons; Signal C = the geometric prior (incumbent band, parity,
gathering position). Two-of-three agreement emits a label; anything else goes to a DISPUTED queue carrying the
*specific* conflict rather than the whole page. Precedent for the fusion: arXiv:2511.08903 (88.2 AP at 5%
labels). The reason for the discipline is our own record — `s6_bounds_probe` proposed importing all 88 of ch23
p89's note tokens into scripture, and the ch5 sweep was thoroughly convincing and cost 24 cells.

**Gate:** per-class marginalia recall and MainText boundary error, *and* the board. **Iterate until it beats
`PAGE_OVERRIDE`.** Escalation ladder, each rung measured: more data on the failing class → finer model scope
→ fix the *labels* (sample DISPUTED) → re-examine typology → re-test deskew (now that bounds are polygons,
V2's pin no longer applies) → add a detector as a second voter. A below-gate model is never adopted, and "the
method cannot reach it" means redesign the method. If constants survive on some leaves, the split must be
decided by a rule fixed **in advance** and validated held-out — choosing post hoc per leaf is fitting the test
set.

### 4.2 Recognition: the glyph inventory, and the input height that can see it

**The inventory is declared before any ground truth is generated**, because a class the model never sees
cannot be output. MUFI-encoded where Unicode lacks a codepoint:

- allographs `ſ`/`s`, `ꝛ`; ligatures `ﬀ ﬁ ﬂ ﬃ ﬄ æ Æ œ Œ ct ſt` and the `&`/Tironian forms;
- abbreviation marks — vowel + macron (`ã ẽ ĩ õ ũ`), `ꝑ ꝓ ꝗ`, `q̃`, superscript contractions — **unresolved**;
- `u/v` and `i/j` preserved (already our convention, and CATMuS's).

**Input height is set to the inventory, not inherited.** `-s '[1,H,0,1 …]'`. H is chosen by experiment across
{120, 160, 192} on the ligature and abbreviation classes specifically, trained **from scratch or from a
same-height checkpoint** — fine-tuning cannot change it. Kraken's docs warn a taller model is slower to
converge and needs `--min-epochs 20` or early stopping kills it before it learns anything; that is a training
schedule, not a reason to stay at 120.

**Base:** CATMuS-Print [Large] — early print, long-ſ preserved, u/v and i/j preserved, abbreviations
unresolved. It is the right *base* and the wrong *target convention* (it declines ligatures), so our fine-tune
extends the alphabet beyond it. The current R2 codec is 233 symbols; the inventory will exceed that.

**Model hierarchy — most specific scope that is *measured* to beat its parent wins:**

```
CATMuS-Print [Large]  →  SOURCE (e.g. jp2-S06)  →  TOME (S06/OT1)  →  BOOK (S06/OT1/genesis)
```

Each level fine-tunes its parent, carries its own frozen held-out set, and is adopted only on a measured win.
A book model that does not beat its tome parent is not adopted — that is a finding about the type, not a
degradation.

**Ensemble, because the target requires it.** Reul et al. (arXiv:1802.10038): CER ≤1% at 1,000 GT lines,
**below 0.5% with confidence voting**; arXiv:1711.09670: per-character confidence voting beats ISRI sequence
voting by a further 5–10%; Al Azawi: a trained LSTM voter over two aligned engines reached **~0.40% CER** on
Fraktur where the ISRI tool reached ~2%. Cross-fold voters must have **different parents** — Reul found
same-parent voters vote worse.

### 4.3 The accuracy target

**0.5% CER-diplomatic per source**, on the full inventory, no folding. Not a consensus-only target — Sir's
requirement is six publication-quality transcripts, and the collation stage then drives the *product* below
that. Reported always as a pair:

| metric | definition |
|---|---|
| **CER-diplomatic** | edit distance over the full glyph inventory, nothing folded |
| **glyph-fidelity** | per-class recall on `ſ`, `u/v`, `i/j`, each ligature, each abbreviation mark |

A CER gain with a glyph-fidelity fall is a **regression**, reported as one. This is the metric that makes
modernisation impossible to disguise as accuracy.

---

## 5. STAGE 3 — GROUND TRUTH

```
   ARCHAIC (repaired, renumbered) ─┐
   pseudo-archaic at gap loci      ├─► stream align → project to lines → CTC refine → line GT + glyph GT
   glyph variant lattice           │
   recognizer output + line boxes ─┘
```

**What is aligned.** Not line-to-verse. Concatenate a page's recognized lines into one character stream with
line-boundary offsets; concatenate the chapter's ARCHAIC text likewise; align globally at character level;
project each line's offset range onto the reference span it matched. A line's span may cross a verse boundary
or hold half a hyphenated word — both are correct answers no line-to-verse map can express. Then kraken's own
`ForcedAlignmentTaskModel` refines per-character cuts within the line, which is what gives glyph boxes.

*(Note the scope difference from Stage 5–6: this is intra-page alignment for GT generation, where offsets are
short and anchored by the page. Cross-source collation does **not** use character offsets — see §7.)*

**Hyphenation is handled by construction.** Transkribus's Text2Image is documented to assign a hyphenated
word wholly to one line and drop the fragment (visible in the Bullinger dataset). Character-level alignment
keeps `hea-` on its line and `uen` on the next, which is what a diplomatic transcript requires.

**Ligature GT without a human transcriber — variant lattices.** The reference says `fi`; the lattice offers
`fi | ﬁ`; the recognizer's CTC posteriors over the pixels choose. Same for `s|ſ`, `ae|æ`, `and|&`, `an|ã`. The
decision is made by the image, never by a positional rule — which matters here specifically, because this
project's pinned finding is that Douay-Rheims long-ſ is **glyph-driven, not positional**. Bootstrapping: round
one accepts only high-margin picks, retrain, lower the margin. **UNMEASURED and therefore the stage's first
experiment**: whether a CATMuS-based model separates `ﬁ` from `f`+`i` at all before fine-tuning — 200 lines
known to contain the ligature, report the margin. If null, a bounded one-time seed of ~100 hand-confirmed
lines covers the ligature classes.

**Acceptance discipline.** A line becomes GT only under a strict alignment-distance threshold, with the
speech-pipeline QC transferred directly: compute CER between the aligned reference and the model's own reading
of that span, discard above threshold. Never align against MODERN for character supervision — those texts
supply *word identity*, never *glyph identity*. The Gold Transcript is the seed corpus, used directly.

---

## 6. THE REFERENCES — repaired, renumbered, collapsed

Order matters here; three of these steps were previously run out of order and produced retracted numbers.

**Step R1 — Renumber before comparing anything.** Finish `ref_renumber` so `s_dismas` and `odr_com` share one
verse address space. 8.0% of verses currently best-match at a non-zero offset. **Gate:** that figure falls
below 0.2%, and the residue is enumerated by book rather than averaged away.

**Step R2 — De-contaminate `s_dismas`.** Detect spliced apparatus (`ruth/1/1`, `genesis/10/1` class) by
apparatus-vocabulary scan plus length divergence against `odr_com`, and by the verse tail being absent.
Repair from the companion reference where it is clean; where both are damaged, the locus is **OPEN** and
blocks, it is not silently accepted.

**Step R3 — Collapse the pairs.** MODERN = `sabates_a` ⊕ `madueke_b`; ARCHAIC = `s_dismas` ⊕ `odr_com`, with
`s_dismas` as the **glyph authority** (`odr_com` does not preserve long-ſ, so it contributes word identity and
completeness only, and may never overwrite a glyph). Disagreements are batched to sub-agents as Sir specified.
Two constraints, both about the *evidence*, not the speed:

- Adjudication runs **after** R1 and R2, or the adjudicator is fed thousands of pseudo-disagreements — verse
  offsets and apparatus splices — and will "correct" sound text onto the wrong verse.
- For MODERN, a model reasoning about meaning and completeness is an adequate adjudicator. For ARCHAIC
  *spelling and glyph* disagreements it is not, because it will regress toward modern norms; those consult the
  scans, which is exactly and only where the six witnesses enter this stage.

**No edition-variant apparatus.** Per Sir: the product is a faithful 1582/1609–1610 transcript. Where the
1630s editions differ, they simply do not vote on that locus (§7.4). We are not producing parallel editions.

**Step R4 — Pseudo-archaic backfill for the 8,383.** Token-align archaic↔modern within a verse to harvest the
dictionary (25,892 archaic loci is a large corpus by this literature's standards — bi-LSTM normalisers train
on 2,000–11,000 tokens); generalise to unseen tokens with character-level SMT (`cSMTiser`; Pettersson et al.
found char-SMT best on four of five historical languages). **Backwards is one-to-many** — `son` ← {`ſonne`,
`ſon`} — so pseudo-archaic is a **lattice**, not a string, carrying attested alternatives with frequencies.
Flagged in provenance on every locus, never overriding a real archaic witness, never used as character-level
training truth. **Gate:** generate pseudo-archaic from the modern reading at the 25,892 loci where the true
archaic reading is known, and report per book how often the lattice contains it.

---

## 7. STAGES 5–7 — LOCATE, COLLATE, RESTORE

This is Sir's design, and it is better than the character-offset scheme I proposed. Recorded as such.

### 7.1 LOCATE — the tome map is the coordinate system

We already know, for every page of every source, which book and chapter it carries (`tome-map-v2.json`: 11
admitted volumes, every page addressed, 100% coverage by construction). So the lookup is a query:

```
for (book, chapter) in ARCHAIC:
    for source in SIX:
        pages = tome_map[source][book][chapter]      # the leaves carrying this chapter
        verses = per_source_verses(source, pages)    # Stage 4's publication-quality reading
```

No rare-token anchoring, no global character offsets, no drift. The computational scope collapses from a
book-length alignment to a chapter's worth of leaves, and every step is addressable and auditable.

**What must be built to make this exact.** The tome map is currently page → (book, chapter). Verse-level
addressing within the page comes from Stage 1's `VerseNumber` regions plus Stage 3's alignment — so the
chain is: tome map gives the leaves; region model gives the verse numbers on those leaves; alignment confirms
them against ARCHAIC. **Three independent signals for one address**, and a disagreement among them is a flag,
not an average. The tome map is rebuilt to carry chapter → leaf-set explicitly for all six sources including
frontmatter and backmatter.

### 7.2 COLLATE — multiple alignment, one verse at a time

For each `(book, chapter, verse)`: take the reading from every source that has it, plus ARCHAIC, and compute a
**multiple sequence alignment** over characters, preserving whitespace. This is the standard MSA problem and
the tooling is mature; progressive alignment with the reference as the first profile is the natural order, and
the output is a column-wise matrix where each column is one *glyph locus* across all witnesses.

Sir's analogy is exact and worth keeping in the design vocabulary: the tome map is the map to the gene, the
chapter:verse address is the primer, the per-verse MSA is the amplicon, and the column is the base position at
which we genotype.

### 7.3 RESTORE — voting at the glyph locus

Each MSA column holds one glyph per witness. Voting is **per-column**, with:

- **Confidence weighting** — each source's recognizer confidence for that character (`kraken` gives per-char
  confidences), not a flat majority. Per-character confidence voting is measurably better than sequence voting.
- **Image adjudication where the vote is close.** Stage 3's forced alignment gives per-character *cuts*, so a
  contested column resolves against the actual pixels of that glyph in each source — and where the models
  still disagree, a VLM sees the crop. This is the only place a vision model touches the product, and it sees
  a glyph, not a page.
- **The result writes back into ARCHAIC**, which is how archaic spelling and typography are *restored* rather
  than merely scored. Provenance per changed locus: which sources voted, their confidences, whether the image
  was consulted.

**The circularity guard.** ARCHAIC is both anchor and target. So: alignment anchors on a glyph-*insensitive*
fold (the anchor decides *where*), voting uses raw readings (the sources decide *what*); a change requires
concurrence of ≥k independent sources; every changed locus keeps provenance and is re-auditable; and the
board cannot count a cell as passing because of a change the board's own OCR caused.

### 7.4 Which sources vote

All six vote on **words**. On *spelling and glyph* at loci where the 1630s editions are known to differ from
the 1582/1609–1610, the later editions abstain — not because they are wrong, but because the product targets
the earlier text. That is a narrow abstention rule at identified loci, not a parallel apparatus.

---

## 8. WHAT THE BOARD BECOMES

The per-source cell board is retained in full — it is how we know a source has reached publication quality,
which §0 requires. Two changes:

1. **The gate is corrected to the documented archaic-preeminent standard** (`char_identity.evaluate_locus`,
   approved 2026-07-10), scoring against ARCHAIC (real, else pseudo-archaic-flagged), with MODERN recorded and
   reported. A cell passing ARCHAIC while failing MODERN badly is a **WARNING class**, not a silent pass.
2. **A page axis is added.** Every open cell already carries its leaf; a per-leaf view sorts geometry defects
   to the top by construction and would have surfaced the ch10 parity holes immediately.

Plus the **product** metric, which is new and is the real deliverable: coverage and per-locus confidence of
the restored ARCHAIC transcript.

**The drop-cap class opens.** 18 passing cells carry a destroyed word, 13 of them verse 1 (`FTER`, `HEN`,
`HERFORE`, `BRAM`, `ACOB`, `HESE`, `NTHE`). A cell carrying an unattested all-caps token fails regardless of
score. The board moves *down* by up to 18, which is the correct direction. Structurally it is a `DropCap`
region class (§4.1), so the fix is a label, not a filter.

---

## 9. BUILD ORDER

| # | step | gate |
|---|---|---|
| **1** | Stage 0 raster path: extraction, manifests, no lossy step, `MAXW` deleted | every source has verified native rasters; S06 live (**done**) |
| **2** | R1 renumber `s_dismas`↔`odr_com` | non-zero-offset best-match < 0.2%, residue enumerated by book |
| **3** | R2 de-contaminate `s_dismas` | apparatus-splice scan clean; unrepairable loci OPEN and listed |
| **4** | Rebuild tome map to chapter → leaf-set, all six sources, incl. front/back matter | every chapter of every source resolves to leaves; spot-audited against images |
| **5** | Stage 3 alignment engine + variant lattices | accepted-line precision audited held-out; glyph-fidelity ≥ current |
| **6** | Region model trained + gated | beats `PAGE_OVERRIDE` on the board; per-class marginalia recall |
| **7** | Recognizers: inventory, input height H, hierarchy, cross-fold ensemble | 0.5% CER-diplomatic per source; glyph-fidelity per class |
| **8** | R3 collapse → ARCHAIC/MODERN; R4 pseudo-archaic | round-trip test on the 25,892 known loci |
| **9** | Stages 5–7 locate → collate → restore | per-locus confidence; provenance complete; audit sample against images |

Steps 2–4 are independent of 5–7 and run in parallel. **Step 1 is done or in progress and is not deferred.**

---

## 10. OPEN AND UNMEASURED — named, not buried

- **JBIG2 symbol-matching is lossy** and is documented to have substituted characters in scanned documents.
  Whether these PDFs used generic-region or symbol coding is **UNMEASURED**. Test before the mask is trusted.
- **Ligature separability before fine-tuning** — UNMEASURED (§5).
- **Input height H** — 120 vs 160 vs 192 is an experiment, not a guess.
- **`ch8/8:14`** — a policy question, open since 2026-07-31.
- **A 1635 reference** — no longer needed for the product (§0.2), but still the only way to *validate* S06's
  readings independently.
- **arXiv:2607.00596** (marginalia is the worst-detected class) — carried from V2's research pass and **not
  re-verified**; it is load-bearing for §4.1's per-class gate and should be resolved before step 6.

---

## 11. CITATIONS

Resolved this session: arXiv:2112.12703 (distant supervision for layout) · arXiv:2511.08903 (LLM-guided
pseudo-label fusion, 88.2 AP @ 5% labels) · arXiv:1802.10038 and arXiv:1711.09670 (Reul et al.; CER <0.5% with
confidence voting) · arXiv:2509.19768 (CHURRO; 82.3% NLS printed; diplomatic prompt protocol) · kraken docs
(`ketos segtrain` typology, VGSL input height, `ForcedAlignmentTaskModel`) · CATMuS-Print [Large] + guidelines
· Bollmann & Søgaard COLING 2016, Pettersson et al. 2014, cSMTiser · Al Azawi et al. (~0.40% CER voter) ·
Transkribus Text2Image hyphenation artefact · OmniDocBench / olmOCR-Bench old-scans.
Carried forward unverified: arXiv:2607.00596.

---

## 12. CRITIQUE ROUNDS

*(Round 1 and Round 2 specialist critiques and the resulting revisions are recorded in §13–§14.)*
