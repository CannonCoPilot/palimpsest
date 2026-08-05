# P3 re-OCR — Diagnosis + Per-Page-Config Redesign Report (Genesis 24, page idx 99)

Cycle: run → **report** → review → redesign. This closes the "why did Surya+reichenau look
recognition-bound, and can per-page config search beat it?" question you raised.
All numbers below are reproduced from evidence logs this session (not recall).

---

## TL;DR

1. **"Recognition-bound at ~0.55" was a measurement artifact, not a recognizer ceiling.** My
   single-page harness had no neighbouring pages to localize with, so it scattered good OCR
   across wrong-chapter verse slots and scored it against unrelated refs. Alignment-free, the
   same OCR is **0.8171 identical** to Genesis 24:12–31 (ſ 55/60 preserved).
2. **Per-page DPI × binarization search does NOT push past ~0.82.** Best config (150 DPI,
   grayscale) = 0.8171, statistically tied with the existing OCR (0.8163). Binarization *hurts*;
   300 DPI is slightly worse than 150. DPI/binarization is not the lever.
3. **The residual 0.82→0.90 gap is genuine recognition loss, not a scoring artifact.** Removing
   all spacing moves the score by +0.0013 (nil), and the fold already neutralizes ſ/u-v/i-j/æ.
   The gap is glyph substitutions + a ~6% length deficit (dropped short words / partial lines).
4. **Your instinct — adapt per page, iterate configs — is the right *frame*, but the winning
   config already ≈ the existing OCR.** The next lever is a better *recognizer / consensus*,
   not a better *pre-processing config*.

---

## 1. Corrected root cause (the big reversal)

Evidence: `ocr-spike/.diag-align-gen24.log`

| Measurement | Score | What it means |
|---|---|---|
| per-verse mean (assigned slots) | 0.5704 | **bogus** — harness mis-alignment |
| oracle best-match per read | 0.6546 | still depressed by cross-chapter smearing |
| **alignment-free concat (OCR body vs Gen 24:12–31)** | **0.8171** | the *true* recognition level |

The drift is explicit in the log: OCR of Gen 24:13 landed in the `26/17` slot (oracle best-match
24/13); 24:24 content landed in `30/21`; etc. Well-aligned verses recognize at **0.85–0.98**
(v18=0.980, v24=0.976). The recognizer is good; my single-page `detect_book` fabricated the low
scores. **Correct measurement requires the full-book context (neighbouring pages), not a single
page in isolation.**

## 2. Tested redesign — per-page config sweep

Evidence: `ocr-spike/.config-sweep-gen24.log`. Metric = alignment-free concat identity
(`edit_ratio(fold_archaic(ocr), fold_archaic(ref))`), reference = Genesis 24:12–31.

| engine | DPI | binarize | concat | ſ (of 60) |
|---|---|---|---|---|
| **reichenau** | **150** | **none** | **0.8171** | **55** |
| existing-OCR | n/a | raw-lines | 0.8163 | 55 |
| reichenau | 300 | none | 0.8042 | 54 |
| reichenau | 150 | otsu | 0.7336 | 50 |
| reichenau | 150 | sauvola | 0.7243 | 50 |
| reichenau | 300 | otsu | 0.7044 | 50 |
| reichenau | 300 | sauvola | 0.6938 | 52 |

**Conclusions**
- **Binarization hurts** — grayscale ("none") wins on every DPI. The "legacy model wants bitonal
  input" hypothesis is empirically **rejected**. (Binarization also drops ſ: 55 → 50.)
- **300 DPI < 150 DPI** — DPI is not the lever (likely kraken line-height/scale mismatch at 300).
- **Best re-OCR (0.8171) ≈ existing OCR (0.8163).** Per-page pre-processing tuning does *not*
  push past ~0.82. The earlier "+0.02 Surya win" (0.5506 → 0.5704) was the Surya **body-region
  selection dropping margin/apparatus pollution**, not better glyph recognition.

## 3. Is the residual gap real, or a scoring artifact? (refuted hypothesis)

Open question going in: maybe faithful OCR scores as "error" because the fold doesn't reconcile
u/v, i/j, or spacing. **Refuted this session** (probe reproduces the 0.8163 anchor exactly):

| variant | score |
|---|---|
| base concat (spaces count as edits) | 0.8163 |
| space-blind concat (all spaces stripped) | 0.8176 |
| **spacing / word-fusion share of the gap** | **+0.0013 (nil)** |

- `fold_archaic` already folds ſ→s, v→u, j→i, æ→ae, vv→w, collapses whitespace runs, and strips
  punctuation/digits — so typography is *not* costing points.
- Removing spacing entirely barely moves the score → word-fusion ("ofthe") is *not* the gap.
- What's left: **glyph substitutions + a 162-char (~6%) folded-length deficit** = dropped short
  words / partial lines. **This is genuine recognition + segmentation loss.**

So 0.82 → 0.90 will not be closed by fold engineering, binarization, or DPI.

## 4. "Take the best config per page" — the selection-signal problem

Your idea is powerful but needs a **selection signal**:
- **On gold/pilot pages** (have a reference): select by score. Trivial.
- **On the full work** (no reference): need a **reference-free proxy** — dictionary-word rate,
  LM perplexity, or **multi-config agreement**: run N configs as pseudo-witnesses and take a
  per-line majority vote. That last option is attractive because it **unifies per-page adaptation
  with the consensus lever** in one mechanism.

But note the sweep result tempers expectations: on this page the config *spread that helps* is
narrow (grayscale 150 vs everything else), and the winner ties the existing OCR. Per-page config
search is worth keeping as cheap insurance, but it is **not** what closes 0.82→0.90.

## 5. Recommended next rung (for review)

The gap is recognition, so the levers are, in priority order:
- **(b) A typeface-tuned or vision-LLM recognizer** for the residual glyph errors (rung-3). This
  targets the actual failure mode (substitutions + dropped words).
- **(c) Multi-witness / multi-config per-line consensus** — doubles as the reference-free selector
  for the whole work. Highest leverage because it serves two needs at once.
- **(d) Better line/word segmentation** — smaller expected gain (spacing share is ~nil), but the
  ~6% length deficit suggests some dropped/partial lines that segmentation could recover.

Explicitly **de-prioritized** (empirically dead ends here): more binarization/DPI tuning, more
fold normalization.

## Guardrail note (No Silent Degradation)

Genesis 24 remains **OPEN** at 0.8171 < 0.90. Nothing here accepts the gap — the sweep is a fired
safeguard that says *the pre-processing approach is exhausted; redesign toward recognizer/consensus.*
Correct measurement (full-book context, not single-page detect_book) is a precondition before
scoring any locus as pass/fail.

---

## REVISED CONCLUSION (2026-07-12 pm, Sir's ask: bench against a perfect transcription)

I produced a full diplomatic transcription of Genesis 24 page 99 (visual read of the 400 DPI
raster, following the AI_OCR skill's diplomatic recipe, one uncertain word flagged honestly).
Stored: `ocr-spike/ground-truth/scripture-genesis-24.json`. Then re-scored the same recognizers
against the ground truth. **The result rewrites the story:**

| comparison | fold-archaic | raw surface | ſ delta |
|---|---:|---:|---:|
| existing-OCR vs s_dismas [v12-31 sweep span] — the number that started this | 0.8163 | 0.8068 | -5 |
| existing-OCR vs s_dismas [v12-30 on-page span, correct] | 0.8502 | 0.8417 | +1 |
| **existing-OCR vs MY GT** (the actual printed page) | **0.8955** | **0.8819** | -7 |
| s_dismas [v12-30] vs MY GT (reference's own faithfulness) | 0.9117 | 0.8905 | -8 |

### The 0.083 "recognition gap" decomposes as:

| component | contribution | interpretation |
|---|---:|---|
| **verse-span error** (v12-31 vs actual v12-30 on-page) | **+0.034** | Sweep's ref pulled in v31 text not printed on this page |
| **reference-vs-page divergence** (s_dismas ≠ 1609 print) | **+0.045** | s_dismas is itself only 0.9117 faithful to the printed page |
| **actual recognizer error** (existing OCR vs printed page) | **0.045** | Genuine glyph misreads + dropped words |

**Only ~half of the measured gap was the recognizer.** The other half was measurement error —
scoring against a reference that isn't the printed page, on a verse span that isn't the printed
page. This vindicates Sir's ask: **the perfect-transcription bench is the correct instrument.**

### Consequences

- **The typeface-tuning / vision-LLM / segmentation build is still valuable, but for a residual
  ~0.045 gap, not a ~0.083 gap.** The bar is nearer than we thought.
- **Multi-config consensus (Phase 3) becomes the highest-leverage single lever.** Closing 0.045
  against a per-page GT is exactly what consensus of error-diverse witnesses is good at, and it
  doubles as the reference-free selector for the full-work-no-gold case.
- **Fine-tuning kraken (Phase 2b) drops in priority.** If the raw recognizer is already 0.8955,
  the marginal return from typeface adaptation on this particular typeface is smaller than
  ensembling.
- **Rescore the sweep against GT.** The reichenau 150 grayscale re-OCR that scored 0.8171 vs
  s_dismas likely scores ~0.88-0.90 against GT — meaning the recognizer *may already be at bar*
  and we've just been under-crediting it.
- **The full-work benchmark must also switch to GT.** Every locus in `qc_audit`'s v9 pilot needs a
  ground-truth transcription; otherwise we're measuring reference divergence, not OCR quality.

### Path forward (revised priority)

1. **Extend ground truth** to the other 11 v9 pilot pages + representative pages from the
   test-book first/middle/last selection. Each is 20-40 minutes of my careful visual reading.
2. **Re-score everything already collected** against GT: reichenau sweep configs, existing OCR
   per scan, the reverted rung-1 attempt. Establish which are actually below bar.
3. **Build multi-config consensus (Phase 3)** as the primary remedy for whatever residual gap
   remains.
4. **Vision-LLM (Phase 2c) becomes a *witness* in the consensus, not a standalone recognizer.**
   Its role is error-diversity injection, not baseline recognition.
5. **Typeface fine-tune (Phase 2b) deferred** unless GT-based re-scoring shows recognition is
   genuinely below 0.85 on multiple pages.

The plan is not smaller — it's re-aimed. The recognizer we have is much better than the metric
was letting it prove.

---
Evidence files (all in `ocr-spike/`): `.diag-align-gen24.log`, `.config-sweep-gen24.log`,
`.rung1-surya-gen24.log`, `ground-truth/scripture-genesis-24.json`. Scorers: `config_sweep.py`,
`diag_align.py` (both use `char_identity.edit_ratio ∘ fold_archaic`).
