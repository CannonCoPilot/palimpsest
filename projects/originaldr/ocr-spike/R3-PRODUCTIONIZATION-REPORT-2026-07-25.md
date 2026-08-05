# OriginalDR re-OCR — R3 Productionization & Statistical Validation
**2026-07-25 · autonomous main-thread sprint · Jarvis**

Consolidates the M5 "R3 productionization" work: the confidence gate now *routes* — a flagged verse is turned
into a pixel band, re-read by a local vision model, re-scored on the janvier grid, and either accepted or held
OPEN. Every claim below is grounded in a run whose output is on disk; the harnesses are test-driven.

---

## 1. Executive summary

The re-OCR ladder is **base → R1 → R2 (fine-tuned) → [4-alarm gate] → R3 (vision) → OPEN ledger**. Before this
sprint the gate was calibrated but *inert*: it flagged verses, but nothing re-read them, and `run_r3=True`
could only re-transcribe a whole page (where the local model repetition-loops). This sprint built the missing
machinery and validated it end-to-end on real pages:

- **verse → pixel-band geometry** (`verse_geom.py`): a flagged janvier verse → its body-line indices → union
  bbox → fractional crop; contiguous flagged verses group into one body-column-clipped **region** crop.
- **load-once vision server** (`mlx_ocr_server.py` + `mlx_client.py`): olmOCR-2 loaded ONCE, served over a
  stdin/stdout protocol; self-healing (timeout, respawn-on-death); ~15–25 s/region instead of a 15 GB reload
  per crop.
- **the router** (`r3_route.py`): region crop → one olmOCR pass → **janvier-cut the output** → score the target
  verse → terminal state. Content and ſ-surface are scored on **separate axes**.
- **the terminal OPEN ledger** (`open_ledger.py`): any verse R3 cannot fully close stays OPEN, is a
  human-review worklist item, and **blocks the deliverable** — No Silent Degradation, as an artifact.

**Headline results:**
- **Gate** (177 gold verses, 46 known-bad): recognizer confidence is self-report-blind (mean conf bad 0.980 vs
  good 0.988); the cross-source alarm **separates** (mean xsrc bad 0.685 vs good 0.937) and reaches **recall = 1
  on all 46 known-bad at τx = 0.90 → 33 % escalation** (vs 87 % for confidence alone). The confident-wrong tail
  (42 verses conf ≥ 0.92) is caught **42/42** by the cross-source alarm and 2/42 by the internal alarms.
- **R3 content rescue** (65 gate-flagged verses across 13 gold pages, real olmOCR): on the 46 truly-known-bad
  verses the **content pass-rate (≥0.90 vs gold) went 0 → 50 %**; olmOCR is a **high-variance** rung — strongly
  positive on prose (**+0.113**, 76 % pass) and net-negative on the 2-column psalms apparatus (**−0.305**),
  which drags the raw mean to −0.114 while the median stays **+0.077** and 26/46 verses gain.
- **THE SAFETY RESULT (No Silent Degradation, empirical):** of the **23 verses the pipeline accepted, 0 are
  worse vs gold than R2** — every acceptance is a genuine improvement. olmOCR's catastrophic failures (psalms)
  all stayed OPEN; the witness-based gate, though the psalms witnesses are defective, laundered **nothing**.
- **Dual-track honesty:** olmOCR is a *content* rung — it lifts the ſ-blind content axis but modernizes ſ
  (80 % of outputs), so content-rescued verses are held **RESCUED_CONTENT_S_OPEN** (ſ surface owed to the
  ſ-faithful arbiter), never silently shipped ſ-less.
- **Tests:** 46 (37 fast hermetic + 9 slow integration); the two real-model integration suites pin the
  genesis-24 result so a regression in any stage is caught. An adversarial code-review pass then found and fixed
  two "report-success-while-degraded" gaps before this report was final (§7).

---

## 2. Architecture — the productionized ladder

```
                 ┌─ base OCR (existing scan)
 (ocr_dir,page)  ├─ R1  (base recognizer + preprocess)
      │          └─ R2  (fine-tuned reichenau_dr)  ── body-isolate (layout.py) ─┐
      │                                                                          │
      ▼                                                                          ▼
 reocr_page ── per-line {text, conf, role, bbox} ──────────────►  r2_body (janvier-cut)
      │                                                                          │
      ▼                     ┌──────────────── 4-ALARM GATE (gold-free) ──────────┤
 cross_source_verse_scores  │ 1 conf (self-report-blind)                         │
   (xsrc_gate, alarm 2)     │ 2 cross-source divergence vs witness  ◄── the one  │
      │                     │ 3 verse_seg length-anomaly            that sees    │
      │  flagged verses     │ 4 ſ-presence            systematic misreads        │
      ▼                     └────────────────────────────────────────────────────┘
 verse_geom.region_crops ── contiguous flagged verses → one body-column-clipped pixel crop
      │
      ▼
 reocr_r3.r3_transcribe(crop)  ── olmOCR-2 via the LOAD-ONCE worker (mlx_client → mlx_ocr_server)
      │
      ▼
 r3_route: janvier-cut the R3 blob → score verse span (content, ſ-blind) + ſ-count vs R2
      │
      ├─ content ≥ τx & ſ kept ─────────────► RESCUED            (accepted at R3, recorded)
      ├─ content ≥ τx & ſ dropped ──────────► RESCUED_CONTENT_S_OPEN → OPEN ledger (ſ owed → arbiter)
      └─ content < τx  /  no geometry ───────► OPEN                    → OPEN ledger (blocks deliverable)
```

The design keeps **P1 gold-free** (the gate/geometry/rescue read only witnesses + the page's own pixels; gold
is used *only* in the eval harnesses of §3–4) and **P5 janvier-cut both sides** (the R3 output is re-cut to the
same grid before scoring — the fix for the measurement bug in §5).

---

## 3. The gate — cross-source alarm efficacy (`gate_calibrate.py`, 177 gold verses)

The §7 thesis, now empirical. Recognizer confidence cannot see systematic misreads; an independent witness can.

| signal | mean on known-bad (46) | mean on good (131) | separates? |
|---|---|---|---|
| recognizer confidence (alarm 1) | 0.980 | 0.988 | **no** (Δ 0.008) |
| cross-source xsrc_id (alarm 2) | **0.685** | **0.937** | **yes** (Δ 0.25) |

- **conf-only** gate at recall = 1 forces **87 %** escalation (useless).
- **full gate** (conf<0.92 OR seg-OPEN OR ſ OR xsrc<τx) reaches **recall = 1 at τx = 0.90 → 33 % escalation, 13
  false-alarms.** The confident-wrong tail (42 known-bad with conf ≥ 0.92) is caught **42/42** by alarm 2, **2/42**
  by the internal alarms — the external witness is doing essentially all the anti-laundering work, exactly as §7
  predicted.
- Axis-aware τx: archaic verses use 0.90; the 13 archaic-gap (modern-fallback) verses use 0.92. The thinnest
  known-bad margin is xsrc 0.8954 (matthew-28 28:1) — caught at 0.90, and the harness ALERTs (never silently
  misses) if a future gold verse lands above τx.

*Interpretation:* the gate is a **router**, not an acceptor — high agreement never accepts a reading; it only
declines to escalate. The real guarantee is the terminal OPEN state (§6).

---

## 4. R3 content rescue — statistical validation (`r3_stats.py`, 13 gold pages, real olmOCR)

Method: for every gate-flagged verse on the gold scripture pages, run the region-based R3 (olmOCR, load-once)
and measure the content lift two ways — **gold-anchored** (`archaic_id` vs the Jarvis diplomatic gold, the truth)
and **gold-free** (xsrc vs the witness, what production sees). `archaic_id` folds ſ→s (ſ-blind), so it isolates
the CONTENT recovery olmOCR is capable of. 65 flagged verses (61 with gold); gate precision vs gold **0.754**
(46/61 flagged are truly R2<0.90 — the rest are borderline, correctly escalated). Total run: 448 s for 13
pages, one 15 GB model load.

**4.1 Aggregate lift (46 truly-known-bad verses, gold-anchored `archaic_id`):**

| | R2 mean | R3 mean | mean Δ | median Δ | positive | pass-rate ≥0.90 |
|---|---|---|---|---|---|---|
| all known-bad (46) | 0.741 | 0.626 | −0.114 | **+0.077** | 26/46 | **0 → 0.50** |
| **prose / other (21)** | 0.749 | **0.862** | **+0.113** | +0.137 | 18/21 | **0 → 0.76** |
| **psalms (25)** | 0.734 | 0.428 | −0.305 | −0.165 | 8/25 | 0 → 0.28 |

The gold-free (witness) mean Δ (−0.104) tracks the gold-anchored mean (−0.114) — the production proxy is
directionally faithful to the truth, validating gold-free routing.

**4.2 olmOCR is high-variance (bimodal), not uniformly good.** Distribution of gold-anchored ΔR3 on the 46:

```
  big-rescue (Δ>+0.3)   ██ 2      better (+0.05..+0.3)  ████████████████████████ 24
  flat (±0.05)          █████ 5   worse (−0.3..−0.05)   ██ 2   catastrophic (Δ<−0.3) █████████████ 13
```

26 verses gain, 15 lose (13 catastrophically), 5 flat. The catastrophic tail is almost entirely **psalms**: the
interleaved 2-column central-apparatus layout makes olmOCR hallucinate/misread. This is the honest ceiling of a
*generic* vision-OCR on complex layout — and the argument for the layout-aware crop-geometry work (§8, R3-4).

**4.3 THE SAFETY RESULT — No Silent Degradation holds empirically.** The critical question a high-variance rung
raises: since acceptance is *witness-based* and the psalms witnesses are defective (DIV-1: odr_com Ps-118
versification broken), could the pipeline "rescue" a verse with a reading that is actually worse vs gold?

> **Of the 23 verses the pipeline ACCEPTED (RESCUED / RESCUED_CONTENT_S_OPEN), 0 are worse vs gold than R2.**
> All 23 are genuine gold improvements — 16/16 prose, 7/7 psalms. Zero witness-misled acceptances.

Every one of olmOCR's catastrophic failures stayed **OPEN** (below τx), so none entered the transcript. The
witness, though imperfect, never scored a gold-bad reading as acceptable — a reading bad enough to hurt gold
also failed the witness bar. The gate is conservative in the right direction: it over-escalates (safe) rather
than over-accepts (unsafe). This is the anti-laundering guarantee, measured rather than asserted.

**4.4 Terminal states (65 flagged):** 1 RESCUED · 22 RESCUED_CONTENT_S_OPEN · 42 OPEN. The OPEN ledger holds 58
deduped loci (39 content-open, 19 ſ-surface); blocks_deliverable = True. ſ-deficiency 52/65 (80 %) — olmOCR
modernizes ſ, the expected surface residual routed to the arbiter.

---

## 5. Critical finding — the janvier-cut measurement bug (fixed)

The first end-to-end run scored **0/5** rescued on genesis-24 and looked like an R3 failure. It was a
**measurement bug**, caught by reading the actual olmOCR output: a verse crop spans the verse *and its
line-sharing neighbours*, so olmOCR returns a multi-verse blob; comparing that blob to a *single-verse*
reference craters the edit-ratio to 0.0 even when the reading is perfect (v27 read *"Blessed be the Lord God of
my lord Abraham…"* — correct — yet blob-scored 0.0).

The fix is the system's own core principle (**P5**): **cut both sides by the same janvier grid** before scoring.
Re-cutting the R3 blob and extracting the target verse's span lifted v28 from 0.0 → 0.978. This is why the
router janvier-cuts every R3 output, and why **region crops** (contiguous verses, body-column-clipped) beat
per-verse crops — full context yields sharper cuts and the body-column clip removes marginal-note bleed
(v27 0.84 → 1.00 once the *"Her father"* margin note was clipped out).

*Lesson recorded:* the metric redesign that the whole project rests on (janvier-cut both sides) had to be
applied to the *new* rung too; skipping it hid a real, positive result behind a flat zero.

---

## 6. The OPEN ledger — honest residual (`open_ledger.py`)

Every flagged verse R3 does not fully close becomes an OPEN entry that records the locus, the source page, every
rung tried, the best (still-sub-threshold) score reached, and the reference it was measured against; the ledger
**blocks the deliverable** while non-empty and dedupes by locus across re-runs (keeping the highest score seen).
Two residual classes are named distinctly:

- **`s-surface`** — content recovered by R3 but ſ dropped → owed to the ſ-faithful arbiter: **in-agent Jarvis**
  (reads the crop in-session — no API call, per the no-Anthropic-API policy) or R2/reichenau's ſ-faithful glyphs.
  This is the expected olmOCR residual, tracked, never shipped as-is.
- **`xsrc<taux-after-R3`** / **`no-geometry`** — content still below bar (hard cross-page fragments, addressing
  gaps) → human-review worklist / approach redesign.

Genesis-24 ledger: 5 OPEN (3 s-surface, 2 content), blocks_deliverable = True — even though R3 *did* recover the
content of 3 of them. That is the point: content recovery is reported, but the diplomatic surface is not
laundered.

---

## 7. Test suite (TDD) & performance

- **46 tests** — 37 fast hermetic (synthetic page dicts / a pure-Python fake MLX server → millisecond runs, no
  model, no images) + 9 slow integration (real kraken segmentation, real olmOCR). `pytest.ini` isolates the
  suite from the parent palimpsest xdist config; `ocr-venv` carries pytest.
- **Adversarial code-review pass** (independent subagent, ran the code): 2 HIGH + 3 MED + 1 LOW found and fixed,
  each regression-guarded. Both HIGH were anti-laundering gaps — `reocr_page` forcing the archaic τx onto
  modern-fallback verses (silently under-escalating the [0.90,0.92) band), and a single olmOCR timeout aborting
  a whole page's rescue and dropping the residual from the ledger. The core logic (verse→pixel mapping, the P5
  janvier-cut re-scoring, the gold-free contract) was verified sound. The statistical numbers above are
  unaffected — `r3_stats` calls the gate directly with the correct axis-aware τx.
- Coverage: verse_seg token-span contract (4), verse_geom geometry incl. region-grouping (14), MLXWorker
  protocol/timeout/restart (7), open_ledger dedup/best-score/blocking (6), r3_route terminal-state logic (5),
  and the two real-model integration suites pinning the genesis-24 result (8) + the load-once smoke (1).
- **Performance:** the load-once worker serves a whole page's flagged regions from one 15 GB load
  (genesis-24: 2 regions in 38 s incl. load), versus one full model reload per crop previously.

---

## 8. What remains (honestly)

1. **Layout-aware crop geometry for psalms (the biggest lever, R3-4).** The statistical run localizes olmOCR's
   weakness precisely: **prose +0.11 / 76 % pass vs psalms −0.31 / 28 % pass.** The generic full-region crop
   feeds olmOCR the interleaved 2-column central apparatus, which it hallucinates. A column-band crop per layout
   mode (prose 1-col, psalms 2-col+apparatus) — swept and validated per mode × source — is the principled fix,
   and the harness (`r3_stats.py`) already measures the exact metric to prove any improvement. Until then, psalms
   verses correctly stay OPEN (they are *not* degraded — just not yet rescued).
2. **ſ-faithful arbiter rung** — close the 19 `RESCUED_CONTENT_S_OPEN` ſ-surface debts via the **in-agent Jarvis
   arbiter** (reads the crop directly in-session, ſ-faithful — no API call, per the no-Anthropic-API policy),
   then re-score ſ-surface. The `run_r3` pipeline itself uses only the local olmOCR backend; it never calls the
   Anthropic API. This is the rung that converts "content recovered" into "diplomatically complete".
3. **hard cross-page fragments** (`xsrc<taux-after-R3`) — verses whose text continues past the page/crop
   (genesis 24:12, 24:30) need addressing/segmentation (§4/§11), not a bigger crop.
4. **GT-3 breadth** — the visual-transcription labor tail (S3/S4/S9 source-coverage gold), best interleaved with
   Sir's review.

*Bottom line:* the productionized R3 rung is **sound and measured** — it genuinely rescues prose content
(+0.11, pass 0→76 %), it never launders a worse reading (0/23 accepted are gold-regressions), and its one real
weakness (psalms layout) is exposed, contained as OPEN, and has a clear next experiment. The pipeline reports
its own limits honestly rather than reporting success while degraded.

*Files:* `verse_geom.py`, `mlx_client.py`, `mlx_ocr_server.py`, `open_ledger.py`, `r3_route.py`, `r3_stats.py`,
`tests/`, wiring in `reocr_core.py` / `reocr_r3.py`. Result artifacts: `.r3-stats/`, `.gate-calibration.json`,
`.reocr-out/r3-validation-genesis24/`.
