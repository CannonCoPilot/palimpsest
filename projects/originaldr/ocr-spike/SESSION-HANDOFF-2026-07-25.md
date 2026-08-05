# SESSION HANDOFF — OriginalDR reOCR · R3 Productionization (2026-07-25)

**Read this first to restore context, then `SPRINT-STATUS.md` (top block) + `R3-PRODUCTIONIZATION-REPORT-2026-07-25.md` for full detail.**
This session was an autonomous main-thread sprint that took milestone **M5 (Gate + R3)** from "gate calibrated but inert"
to **R3 productionized, tested, statistically validated, and adversarially code-reviewed.**

---

## 1. State in one paragraph

The reOCR ladder (`base → R2 fine-tuned → four-alarm gate → R3 vision → OPEN ledger`) now **routes end-to-end**: a
gate-flagged verse is turned into a pixel crop, re-read by local olmOCR-2 (loaded once), re-scored on the janvier grid,
and either accepted or held OPEN. Built 5 new modules (~1,000 LOC), all TDD (**46 tests: 37 fast + 9 slow, all green**).
Validated on 13 gold pages. **Nothing is committed** — `ocr-spike/` is gitignored (on-disk deliverables). No Anthropic
API is called anywhere (local olmOCR only; `_r3_claude` guarded by `OCR_ALLOW_ANTHROPIC_API`).

## 2. What was built (all in `ocr-spike/`)

| File | Role |
|---|---|
| `verse_geom.py` | verse → body-line indices → union bbox → fractional crop; `region_crops` (contiguous flagged verses → 1 body-column-clipped crop); `group_contiguous`, `body_column`. `verse_seg.segment` now emits `tok_lo/tok_hi` (the bridge). |
| `mlx_client.py` + `mlx_ocr_server.py` | olmOCR loaded ONCE, stdin/stdout JSONL; reader-thread timeout, respawn-on-death, RLock. `reocr_r3._r3_mlx` uses the worker by default. |
| `open_ledger.py` | terminal OPEN worklist; dedup-by-locus, best-score-tracking provenance, blocks deliverable. |
| `r3_route.py` | the router: region crop → 1 olmOCR pass → **janvier-cut the R3 blob (P5)** → score verse span → terminal state. States: RESCUED / RESCUED_CONTENT_S_OPEN / OPEN. |
| `r3_stats.py` | statistical harness: gold-anchored + gold-free R3 lift across gold pages; `--aggregate` recomputes from `.r3-stats/` checkpoints (no olmOCR). |
| wiring | `reocr_core.reocr_page` attaches per-line `bbox`; `reocr_batch(run_r3=True)` routes via `r3_route.rescue_page` + writes `_open_ledger.json`. |

Tests: `tests/test_{verse_seg_spans,verse_geom,mlx_client,open_ledger,r3_route,integration_geom,integration_r3}.py`.

## 3. Validated results (all from on-disk runs)

- **Gate** (`.gate-calibration.json`, 177 verses, 46 known-bad): conf self-report-blind (0.980 vs 0.988); cross-source
  alarm separates (0.685 vs 0.937); **recall=1 @ τx=0.90 → 33% escalation**; confident-wrong tail caught 42/42.
- **R3 lift** (`.r3-stats/_summary.json`, 65 flagged verses): olmOCR is **high-variance** — **prose R2 0.749→R3 0.862
  (+0.11, pass 0→76%)** vs **psalms R2 0.734→R3 0.428 (−0.31, pass 0→28%)** (2-col apparatus wrecks it). Raw mean
  −0.114, median +0.077.
- **SAFETY (No Silent Degradation, empirical): of 23 ACCEPTED verses, 0 are worse vs gold than R2.** Every olmOCR
  failure stayed OPEN; the witness-based gate laundered nothing. olmOCR modernizes ſ on 80% of outputs → content rung.
- **Deliverables:** report `R3-PRODUCTIONIZATION-REPORT-2026-07-25.md`; artifact https://claude.ai/code/artifact/94b9a36c-18dc-4823-9a13-debf16d40193

## 4. Critical gotchas (repeat-bug sources — DO NOT re-break)

1. **P5 — janvier-cut BOTH sides before scoring.** An R3 crop returns a MULTI-verse blob; comparing it to a
   single-verse ref craters to 0.0 even when correct. `r3_route._score_and_decide` re-cuts the R3 blob first. (This
   bug scored the first e2e 0/5; the fix revealed v28 0.0→0.978.)
2. **Axis-aware τx must pass through as `taux=None`.** `cross_source_verse_scores` resolves 0.90 archaic / 0.92
   modern per verse. NEVER pre-resolve to `xsrc_gate.TAUX` (was code-review HIGH-1 in `reocr_page`; now fixed).
3. **Contain per-region failures.** A `transcribe()` timeout must ledger-OPEN that region + continue, never abort the
   page (was HIGH-2; fixed + test `test_region_transcribe_failure_is_contained_and_ledgered`).
4. **olmOCR (olmOCR-2-7B) modernizes ſ** → CONTENT rung only; ſ-surface owed to the in-agent Jarvis arbiter (NOT the
   API). It repetition-loops on full dense pages → always crop/region, never whole-page.

## 5. How to run

```bash
cd /Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr/ocr-spike
../ocr-venv/bin/python -m pytest tests/ -q -m "not slow"   # 37 fast (ms); add -m slow for 9 real-model (~55s, one olmOCR load)
../ocr-venv/bin/python r3_stats.py --aggregate             # recompute stats from checkpoints (no olmOCR)
../ocr-venv/bin/python r3_stats.py                         # full run (real olmOCR, ~8min; resumable via .r3-stats/)
../ocr-venv/bin/python -c "import json,sys; sys.path.insert(0,'.'); import gate_calibrate as g; g.calibrate(json.load(open('.gate-calibration.json')))"  # gate headline, no kraken
```
MLX backend runs in the SEPARATE `../ocr-mlx-venv` (mlx-vlm 0.3.12 + transformers==5.1.0). Don't run two olmOCR jobs
concurrently (2×15GB = memory pressure).

## 6. Where to resume — the next levers (priority order)

> **SUPERSEDED 2026-07-26 for lever 1.** Read `R3-GEOMETRY-VARIANCE-FINDINGS-2026-07-26.md` FIRST.
> Lever 1 was driven to completion and is **CLOSED by measurement**: the "2-column apparatus" hypothesis below
> is WRONG (psalms pages are mostly single-column), and R3 is **variance-limited, not geometry-limited** — the
> gold-*oracle* over 4 crop variants reaches only 0.543 acceptance, and best-of-N buys 1 verse in 46. One real
> defect was fixed (`body_column` full-measure); a wider-crop "fix" was measured WORSE (Wilcoxon p=0.018) and
> reverted. **Do not re-attempt wider crops or best-of-N selection.** The new #1 is symbol-conditional,
> apparatus-aware segmentation (†-anchored boundaries + annotation removal) — see §5 of that report.

1. ~~**[BIGGEST] Layout-aware crop geometry for psalms (§8 R3-4).**~~ **CLOSED — see the note above.** olmOCR fails psalms because the generic region crop
   feeds it the interleaved 2-column central apparatus. Build a column-band crop per layout mode (prose 1-col, psalms
   2-col+apparatus), sweep × source, VALIDATE with `r3_stats.py` (it already measures the exact metric). `verse_geom.
   body_column` is single-column today (documented). Target: lift psalms pass-rate off 0.28.
2. **ſ-faithful in-agent arbiter rung.** Close the 19 `RESCUED_CONTENT_S_OPEN` ſ-surface debts: read each flagged
   crop in-session (I have vision; NO API), produce the ſ-faithful surface, re-score. Converts "content recovered" →
   "diplomatically complete".
3. **Hard cross-page fragments** (`xsrc<taux-after-R3`, e.g. genesis 24:12/24:30) — need addressing/segmentation
   (§4/§11), not a bigger crop.
4. **GT-3 breadth (Sir-review labor tail)** — S3/S4/S9 source-coverage gold; abdias vv13-21. olmOCR content draft →
   Jarvis ſ-correction → your review at the GT tool (`gt_review_server.py` :8099).

Authorization standing: Sir granted full autonomy to drive the program to completion at highest rigor; he reviews GT
AFTER the work. DECIDE forks and proceed (don't block on AskUserQuestion). No Silent Degradation is absolute.
