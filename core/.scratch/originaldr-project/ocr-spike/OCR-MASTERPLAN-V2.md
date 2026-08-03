# OCR MASTERPLAN v2 — one pipeline, tuned per source / book / chapter / page

**Written 2026-08-03.** Supersedes the scope of `REOCR-MASTER-PLAN-2026-07-22.md`, which remains valid as the
record of the ladder experiments (§13 Q1–Q50) and is cited here rather than repeated.

This plan is written against measurements, not intentions. Every number below was produced in this project and
can be re-run; the commands are named. Where a thing was tried and failed, it is recorded as failed.

---

## 0. THE ONE-PARAGRAPH SUMMARY

We have been building the **second half** of an OCR pipeline while calling it a review process. The campaign's
per-chapter work is not post-hoc correction — it is layout analysis, performed by hand, one leaf at a time,
and encoded as 364 hand-tuned constants. It works: it moved the board from 0.8576 to 0.9374 in one session.
But it has reached the point where the constants are the ceiling, and the measured evidence says so from three
directions at once. The redesign replaces the constant-fitting with a **trained region model**, replaces
hand-audited ground truth with **forced alignment against a known transcription**, and promotes campaign work
from a review pass to **the pipeline's own tuning loop**, so that every chapter walked improves the engine
that processes every remaining book.

---

## 1. WHERE WE ACTUALLY ARE — the evidence base

### 1.1 What the campaign has bought (measured, this session)

| change | mechanism | cells | regressions |
|---|---|---|---|
| ch23 walk — S6 left bound, per-leaf | geometry | +15 | 0 |
| ch39 walk — **S6 two-axis, 62 leaves** | geometry | **+198** | 0 |
| ch41 walk — **1609 right bounds, 121 leaves** | geometry | **+106** | 0 |
| R3 pass (olmOCR attesting arm) | recognition | +72 | 0 |
| ch5 walk — S9 p48 left bound | geometry | +2 | 0 |
| **session total** | | **5245 → 5733 of 6116 (0.8576 → 0.9374)** | **0** |

**Every large win was geometry.** Not one came from a better recognizer, a better prompt, or a better
consensus rule. That is the single most important fact in the project's history and it has been true at every
scale we have looked at.

### 1.2 The three findings that end the current approach

**(i) The remaining failures have flipped from geometry to recognition.** Attributing all 383 open cells by
asking whether the missing words are physically present on the leaf but outside the band:

| class | cells | share |
|---|---|---|
| **RECOGNITION** — the words are not on the leaf at all | **172** | 45% |
| **GEOMETRY** — the words are on the leaf, outside the band | **125** | 33% |
| unattributable (chapter-level / r3 assembly) | 86 | 22% |

We have been optimising the layer we could see. The larger residual pool is now text the recognizer never
produced, and no amount of bound-tuning reaches it.

**(ii) The bounds model is structurally unable to describe these pages.** Measured leaf rotation across the
corpus (`deskew.py --all`):

| source | median \|skew\| | p90 | max |
|---|---|---|---|
| archive-ot1-1609 | 0.0029 | 0.0063 | 0.0113 |
| pdf-S03a | 0.0028 | 0.0059 | 0.0096 |
| **archive-holiebible-ot1** | **0.0105** | **0.0214** | **0.0370** |
| jp2-S06 | 0.0019 | 0.0120 | 0.0302 |

On `archive-holiebible-ot1` p48 the body's left edge migrates 0.212 → 0.226 down the leaf while the note
column's right edge falls 0.210 → 0.192. **At the head of that page the channel between apparatus and
scripture is 0.002 of page width — about four pixels.** No vertical line separates them. A single fraction is
not a badly-chosen constant there; it is the wrong kind of object. This is the common cause behind a run of
separately-diagnosed defects — `_trim_left_margin`'s pinned "one threshold cannot serve a ragged edge",
`gen1_r3.widen_to_measure`'s 6% crop margin ("2% does not clear the scan's skew"), and the ch5 walk's 73-leaf
sweep that cost 24 cells.

**(iii) Deskew cannot be retrofitted — measured, four ways.** Against a 5733 baseline:

| configuration | board | Δ |
|---|---|---|
| hand-tuned bounds, no deskew | **5733** | — |
| + deskew on untuned leaves only | 5724 | −9 |
| + deskew on all leaves | 5728 | −5 |
| + deskew and bounds re-derived on deskewed pages | 5708 | −25 |

The deskew itself is sound: S9's line-start spread falls 0.0157 → 0.0043 and **all four witnesses converge on
the same ~0.004 floor**, which is the residual raggedness of hand-set type. It loses cells anyway because
every calibrated constant in the stack — the per-leaf overrides, the *source defaults*, R3's crop margin, the
head/foot tests — was fitted in the skewed frame. Straightening the page moves it out from under all of them
at once. **Deskew is adoptable only together with a re-derivation of the whole geometry, and that
re-derivation must beat 364 hand-measurements — which a heuristic probe does not (−25).**

### 1.3 What is NOT in the pipeline, contrary to reasonable assumption

- **No visual model decides any boundary, anywhere — including the re-OCR rungs.** R3 is a vision-LLM
  (olmOCR), but `widen_to_measure()` hands it a crop drawn by `SOURCE_MODEL` + `chapter_model` constants plus
  a 6% pad. The model never sees a page and never proposes a region. It is a recognizer inside a rectangle we
  drew.
- **No region segmentation.** `kraken.blla` does return a `regions` field and `gen1_wordboxes.py` discards
  it — but this barely matters, because the default model emits **one** region (`text`, spanning 0.075–0.963
  on S9 p48). It does not separate marginalia. Verified directly.
- **No per-page feature-block detection.** `PAGE_OVERRIDE` *is* our layout analysis: 364 constants.
- **Baselines are discarded.** Kraken returns a polyline baseline per line (S9 p48 line 0:
  `[175,648] → [435,638]`, slope −0.038). We reduce each line to an axis-aligned bbox at the moment of
  storage, throwing away the rotation we then spend the campaign compensating for by hand.

### 1.4 What the 2026 literature says (verified citations; full report in `.campaign/`)

- **Marginalia is the worst-detected class** for YOLO/DETR document detectors on historical material
  (arXiv:2607.00596 reports exactly this class as remaining poor). Do not expect an off-the-shelf detector to
  solve our specific problem.
- **Kraken's `ketos segtrain` trains a region typology** in the same coordinate space as our recognizer. The
  reason we see one region is that the default model was trained with a flat typology — not a model limit.
- **`blla` rectifies each line along its own polyline baseline**, so *recognition* already tolerates
  within-page skew. This is consistent with our data and it is why our recognition is decent on crooked
  leaves while our *geometry* is not: the defect is in the coordinate frame we store and threshold, not in the
  reading. Image-space dewarping (DvD, TADoc, DocMatcher) is aimed at camera-captured documents and would
  break image↔PageXML correspondence. **Coordinate-space correction is the right axis and we have it.**
- **Book-specific recognizers reach ~2% CER on early print** (arXiv:1712.05586). We are at val 0.9396 ≈ 6%.
  The gap is ground truth for *this book*, not architecture.
- **Forced alignment turns a known transcription into line-level GT** (arXiv:2112.12703 with `passim`;
  arXiv:2508.07904 CTC alignment). This is the unpulled lever, and the Douay-Rheims is an unusually good case
  because the text is known.
- **The hard caveat**: editorial transcriptions resolve abbreviations, merge hyphenated line-ends and
  modernise spelling. A modern-spelling reference used as GT teaches the model to modernise — the exact
  failure this project exists to prevent. Alignment gives *line boundaries and candidate targets*; it does
  not give diplomatic truth.
- **CATMuS-Print [Large]** already encodes our transcription conventions (long-ſ preserved, u/v and i/j
  preserved, abbreviations unresolved). Re-basing on it removes a convention-mismatch tax we currently pay.
- **Vision-LLMs collapse on historical scans**: olmOCR scores 97.8 on olmOCR-Bench Base and **42.8 on Old
  Scans**. Aggregate leaderboards do not predict our corpus.
- **No published work measures whether any VLM preserves long-ſ / u-v / i-j.** We must measure it ourselves
  and treat every VLM as guilty until proven innocent.

---

## 2. THE ARCHITECTURE

Seven stages. Each has an owner artifact, a tuning scope, and a gate that must pass before the next stage
consumes its output. Stages 0–3 are new or substantially changed; 4–6 exist and are folded forward.

```
 0  ACQUIRE      volume → page rasters, per-volume raster choice        [exists]
 1  GEOMETRY     page → typed regions (MainText/Marginalia/Head/Verse)  [REPLACE constants]
 2  RECOGNISE    region → lines → diplomatic text + boxes               [re-base + per-edition fine-tune]
 3  ALIGN        known transcription ↔ lines → line-level GT            [NEW — the GT engine]
 4  ASSEMBLE     lines → verses (localization, hyphen-join, cleaning)   [exists, fold forward]
 5  ESCALATE     low-confidence verses → rungs R2/R3/consensus          [exists, re-target]
 6  SCORE        verses vs references → board + validity audits         [exists, add validity]
```

### Stage 1 — GEOMETRY: a trained region model replaces the constants

**The change.** `PAGE_OVERRIDE`'s 364 constants are replaced by a kraken segmentation model trained with a
real typology: `MainText`, `Marginalia`, `RunningHead`, `VerseNumber`, `Argument`, `Annotations`,
`Signature/Catchword`. Regions come back as polygons in the same coordinate space as the baselines, so a
rotated leaf needs no compensation — the polygon leans with the page.

**Why this and not more constants.** §1.2(ii): on the leaves that matter no vertical line exists. A polygon
is the smallest object that can express what is actually there. And §1.3: we already generate the
coordinate space this needs.

**Training data, and the honest cost.** 30–50 annotated pages, stratified across the four witnesses and
across leaf types (ordinary, chapter-open, annotation-leaf, argument-leaf). Annotate in **LAREX** (active as
of 2026-07-28, and it now ships a kraken action plugin). Base model: kraken's general segmentation model
(Zenodo 10.5281/zenodo.14602569), `ketos segtrain --resize both -i`. This is hours of GPU on the Mac Studio,
and roughly a day of human annotation — the largest single human cost in this plan, and the one that retires
the largest recurring cost.

**Do NOT adopt the full OCR4all suite.** Its core app has been stalled since 2024-11; LAREX alone is the live
and useful piece, and its Calamari-centric workflow is not ours.

**Gate (per-class, not mean IoU).** Layout quality is gated on **marginalia recall** and **MainText
boundary error**, separately. A mean-IoU gate would hide exactly the class we care about; the DLER literature
makes this argument and our own history confirms it — every contamination we found was a marginalia leak.

**Fallback, explicit.** Until the region model passes its gate, the constants stay. This is a
parallel-then-switch migration with a shadow comparison, not a rewrite: the region model runs beside
`PAGE_OVERRIDE` and must beat it on the board before it replaces it. **A below-gate region model does not get
adopted "to unblock" anything.**

### Stage 2 — RECOGNISE: re-base, then fine-tune per edition

1. **Re-base on CATMuS-Print [Large]** rather than continuing from the current R2 checkpoint. Its
   transcription conventions already match our diplomatic rules, so we stop paying a convention-mismatch tax.
2. **One model per edition**, not one model for the corpus: the 1609 witnesses and the 1635 `jp2-S06` are
   different type. Merge only if the merge is empirically shown to be free.
3. Target ~2% CER, the published book-specific figure, against our current ≈6%.

### Stage 3 — ALIGN: the ground-truth engine (new, and the highest-leverage build)

This is what turns a known text into training data at scale.

```
   diplomatic reference text  ─┐
                               ├─►  passim (line-level alignment)  ─►  CTC forced alignment  ─►  line GT
   recognizer output + boxes  ─┘                                          (recognizer's own)
```

**The discipline that makes it safe.** Alignment output is *noisy* GT and is treated as such:
- Accept a line only when its alignment distance is under a strict threshold; everything else goes to review.
- Align against a **diplomatic** witness. `s_dismas` and `odr_com` are modern-spelling references — they are
  excellent *scorers* and **dangerous trainers**. Using them as GT would teach the model to modernise ſ→s,
  which destroys the point of the project while *improving* CER by 1–2%.
- Keep a **glyph-fidelity rate** (per-class recall on ſ, u/v, i/j, ligatures) as a first-class metric beside
  CER, precisely so that a modernisation win cannot masquerade as an accuracy win.

**On using `s_dismas` / `odr_com` / gold as training truth** — the question as posed: **yes for line
boundaries and candidate targets, no for character-level supervision**, unless and until each is shown to be
diplomatic at the glyph level. The gold transcripts *are* usable directly, and are the seed corpus.

### Stage 4 — ASSEMBLE: fold forward, unchanged in spirit

Localization, hyphen rejoining, glue-splitting, running-head and catchword removal, annotation-leaf
detection. These are hard-won and mostly correct. They fold forward. Two changes:
- The tests that currently operate on fractional bands take **region membership** instead once Stage 1 lands.
- `_trim_left_margin` stays retired; its diagnosis ("segmentation problem") was right and Stage 1 is the fix.

### Stage 5 — ESCALATE: re-target the rungs at recognition, not geometry

The rungs were built to fix geometry by re-cropping. With Stage 1 owning geometry, they re-target:
- **Routing signal**: multi-model disagreement (Consensus-Entropy style) rather than a score threshold.
- **Merge**: ROVER-style character-level voting across witnesses/models, aligned with **CollateX**, with any
  lexicon verification restricted to a *period* lexicon. A modern-English lexicon verifier would be actively
  harmful here.
- **VLM rung**: test `dots.ocr` (best MLX support), `Qwen3-VL-30B-A3B` (MoE, ~17GB at 4-bit), and `CHURRO`
  (purpose-built for historical text) — each gated on a glyph-fidelity measurement first, because no
  published work establishes that any of them preserves archaic orthography.
- **Note**: our pinned finding that `qwen3-vl:8b` is thinking-locked is an **Ollama serving** problem, not a
  model problem. The MLX path does not have it. That pin should be narrowed, not generalised.

### Stage 6 — SCORE: add the validity audits the board cannot see

The board counts cells that pass. It cannot see a cell that passes *while wrong*. Two audits become
first-class and run after every geometry change:
- **Apparatus-vocabulary scan** over every `cellgrid` — this found `ch3 v7 S9` reading
  `made thems. Chriſclues aprons` (= `made themſelues aprons` with `S. Chriſ` spliced through it) **scoring
  0.918–0.928 on all four references, and passing**.
- **Glyph-fidelity rate**, per §Stage 3.

---

## 3. THE TUNING MODEL — per source / book / chapter / page

Tuning stays, and gets a defined hierarchy with one rule: **the most specific scope that is measured wins,
and nothing is tuned at a scope broader than its evidence.**

| scope | what belongs here | example | artifact |
|---|---|---|---|
| **SOURCE** | the witness's type, edition, transcription conventions, recognizer checkpoint | 1635 `jp2-S06` sets glosses in the outer margin | `SOURCE_MODEL`, per-edition model |
| **BOOK** | book-level apparatus conventions, running-head form | Genesis heads read `GENESIS.` | book profile (new) |
| **CHAPTER** | which leaf opens it, argument block, drop cap | `("jp2-S06", 39): open_page 130` | `CHAPTER_MODEL` |
| **PAGE** | this leaf's regions | p48's note column and its lean | **region polygons** (replacing `PAGE_OVERRIDE`) |

The key structural change: the page scope stops being *numbers we chose* and becomes *polygons the model
produced and a human approved*. Per-page tuning is preserved — it is strictly richer than today — but it is
no longer hand-authored by default.

---

## 4. CAMPAIGN MODE BECOMES THE PIPELINE

**The reframing, stated plainly.** What has been done to the other books is the first half of the pipeline.
What campaign work is doing now is the second half. Today those halves are separated by an accident of
history: campaign fixes land in `gen1_pagemodel.py` and reach the board, while the report and the rest of the
corpus are served by `qc_audit.py`, **which carries its own layout model**. That is the single most important
structural defect in the project, because it means campaign learning does not propagate.

**Therefore:**

1. **One geometry engine, one recognizer registry, one assembler** — used by the board, the report, and every
   book. The `qc_audit.py` fork is closed. (This is the "report bridge", open since 2026-08-01.)
2. **A chapter walk emits artifacts, not edits.** Today a walk edits constants. Tomorrow it emits: corrected
   region polygons (→ Stage 1 training data), confirmed line GT (→ Stage 3 corpus), and a rule or an ALERT.
   Each is an input that improves the engine for *every* book, not a patch for one chapter.
3. **The walkthrough protocol survives intact.** Its seven steps, its three anti-theatre rules, and its
   refusal to accept "nothing to do here" are the reason this project has a trustworthy record of negative
   results. They apply unchanged to the new stages. `--record` continues to refuse a pass that cannot name
   its signals and diagnostics.
4. **Every remaining book inherits the tuned engine and adds only its own scope** — its running-head form,
   its chapter opens, its leaf regions. Genesis is the calibration set; the rest of the Bible is the run.

---

## 5. BUILD ORDER, WITH GATES

Ordered by measured leverage, and each step is refusable on its own evidence.

| # | step | sized at | gate before adoption |
|---|---|---|---|
| **1** | **Close the `qc_audit.py` fork** — one geometry engine for board + report | unblocks everything else | report and board agree cell-for-cell on Genesis |
| **2** | **Annotate 30–50 pages in LAREX; `ketos segtrain`** | ≤125 geometry cells + the validity class | per-class: marginalia recall, MainText boundary error; **must beat `PAGE_OVERRIDE` on the board** |
| **3** | **Forced-alignment GT engine** (passim → CTC) | the 172 recognition cells, and the whole corpus | accepted-line precision audited on a held-out sample; glyph-fidelity ≥ current |
| **4** | **Re-base on CATMuS-Print, fine-tune per edition** | CER 6% → ~2% target | CER *and* glyph-fidelity, per edition, on held-out lines |
| **5** | **Deskew, adopted together with region geometry** | — (already built, `deskew.py`) | only meaningful once bounds are polygons; re-test then |
| **6** | **Consensus + VLM rung re-target** | the residual tail | glyph-fidelity gate per model *before* any quality claim |

**Note on step 5.** `deskew.py` is built, validated, and currently **default `off` because it measures
worse** (§1.2 iii). It is retained deliberately: it is correct, it is the right axis per the literature, and
it becomes adoptable the moment the geometry is polygons rather than fractions. Keeping a correct component
switched off with its negative result recorded is the honest state, not a failure.

---

## 6. MEASURED AND REJECTED — the pinned negative results

These are load-bearing. Each cost real time and each closes a door that looks open.

| thing | result | why it matters |
|---|---|---|
| Deskew retrofitted into the constant stack | −5 / −9 / −25 | the stack is co-adapted to the skewed frame |
| Fresh automatic bound derivation (328 leaves) | −25 vs hand-tuned | heuristics do not beat 364 measurements |
| Left-column detector swept over 73 leaves (ch5) | −24 cells | "admits too much" has no orthogonal corroborator |
| `_trim_left_margin` (median row start) | −0.02 ref mean | one threshold cannot serve a ragged edge |
| Widening odd-leaf right bounds (ch41) | −7 | odd leaves genuinely carry the column |
| Bulk two-direction emit over measured entries | −11 | an estimate must never overturn a measurement |
| XY-cut on S9 p47 | one block | there is no gutter — it was merged lines |
| `qwen3-vl:8b` via Ollama | unusable | **serving** defect; the MLX path is untested and is not covered by this pin |

---

## 7. OPEN RISKS, NAMED

- **The region model may not clear `PAGE_OVERRIDE`.** 364 hand-measurements are a strong baseline and the
  literature says marginalia is the hardest class. Mitigation: shadow-run and switch on evidence; the
  constants stay until beaten. This risk is why step 2 is gated, not assumed.
- **Alignment may teach modernisation.** Mitigated by diplomatic-only references, a distance threshold, and a
  glyph-fidelity metric that makes the failure visible rather than flattering.
- **VLM orthographic fidelity is unmeasured in the literature.** We must measure it before we trust any rung.
- **Annotation is a real human cost** and it is the plan's critical path. There is no version of this that
  reaches ~2% CER without ground truth.
- **ch8/8:14 remains a policy question**, not an OCR one: no reading of those pixels satisfies both a 1609
  and a 1635 reference. Open since 2026-07-31.
- **`ch23 / odr_com gen 23:20`** remains an acquisition question. Achievable there is 76, not 80.
