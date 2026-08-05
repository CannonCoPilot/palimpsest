# Rung-3 validation — the evidence-based reOCR path (2026-07-21, main-thread)

## Question
Skipping the remaining matter transcription (2 tables + continuance), where does the reOCR ladder stand,
and what is the path over the 0.90 **surface** bar?

## What the gold-scored evidence says (this supersedes the v9 "go to rung 1" optimism)
The cheaper rungs are **exhausted against real gold**:
- **Rung 0** (visual diagnostic gate): DONE — `RUNG0-SIGNOFF-v9.md`. Print is clean; failure is NOT glyph-level.
- **Rung 1** (layout / region typing): executed 2026-07-12 → **+0.02** only; uniform geometric suppression
  regressed clean scans and was REVERTED. Layout is a small lever.
- **Multi-witness consensus** (`consensus_v2.py`, 37,130 verses, mean 8.8 witnesses/verse): self-reports
  archaic_match 0.897 **vs s_dismas** — but `gt_rescore.py` scores it **vs GOLD at 0.622 (8% pass@0.9)**.
  The 0.897 was agreement with s_dismas, which is **itself only 0.80 faithful to gold** (odr_com 0.81).
  Consensus of existing OCR + noisy reference texts converges to a NOISY target, not truth → 0.62. Insufficient.

## The decisive experiment — Rung 3 (vision-LLM) vs GOLD, dual-track
Genesis 24 (S1 archive-ot1-1609 p99, printed 79 — the canonical benchmark page; gold =
`scripture-genesis-24.json`, 43 lines, 51 long-ſ). Jarvis (Claude) diplomatic vision pass: render →
2 high-res column-bands → per-glyph ſ (sh-vs-ſh decided visually) → score `.scratch/rung3_gen24_score.py`:

| track | Rung 3 | consensus baseline |
|---|---|---|
| CONTENT (fold_archaic, ſ-blind) | **0.998** | 0.622 |
| SURFACE (raw, ſ-preserving) | **0.954** | — |
| ſ-count (companion check) | 49 vs 51 gold (Δ-2, 0.961) | — |

**Rung 3 CLEARS 0.90 on BOTH tracks** and the ſ-count confirms it PRESERVES the archaic surface (not
modernizing — the opposite of catmus's 0-ſ failure). This is the one lever with headroom over the bar.

## HARD-CASE confirmed (2026-07-21) — the finding is now robust across the difficulty range
psalms/118 (S1 archive-ot2-1610 p227) — the WORST rung-0 locus (recall **0.194**): roman scripture
interleaved with italic annotations + margin glosses + acrostic headers (the multi-region layout that
broke old OCR). Rung-3 vision pass extracts the scripture surface only (`.scratch/rung3_ps118_score.py`):

| track | Rung 3 (psalms/118) |
|---|---|
| CONTENT (fold_archaic) | **0.9964** |
| SURFACE (raw, ſ-preserving) | **0.9915** |
| ſ-count | 11 vs 11 gold (exact) |

Rung-3 clears the bar **more easily on the HARD case (0.99)** than the easy one (genesis 0.95), because the
difficulty was LAYOUT (separating roman scripture from italic annotations) — trivial for a vision model,
fatal for the old OCR (which merged them → 0.194). **Rung-3 also caught 2 GOLD ERRORS**: v104 gold reads
"the…therefore", the print reads "thy…therfore" (Vulgate "a mandatis **tuis**" confirms "thy"). So a rung-3
pass can be MORE faithful than the existing gold — gold itself needs a QC pass.

## Remaining caveats (No Silent Degradation)
2. **Reproducibility, not third-party independence** — the gold was itself a Jarvis/Claude visual read, so
   this proves a vision-LLM pass reliably REPRODUCES gold-grade surface output (which IS the production
   requirement for un-gold pages), but it is not an independent-oracle validation.
3. **Manual-careful vs automated-scaled** — this was a careful human-in-loop pass. An automated/prompted
   batch (or a local model: CHURRO/olmOCR) may score 2-5pt lower; budget headroom above 0.90.

## METRIC ARTIFACT + CONSENSUS DILUTION (2026-07-21 pm) — reframes the "improve Rungs 0-2" goal
Investigating Sir's question "s_dismas/odr_com should have converged with the improved GT":
- **They HAVE converged** — the low aggregate B/C (0.80/0.81) is a **per-verse alignment ARTIFACT**, not divergence.
  The gold groups body text by printed LINE and tags each line to a verse; on PROSE, lines straddle verse
  boundaries, so a per-verse gold carries fragments of neighbours. At **page grain** the artifact vanishes:
  genesis/24 s_dismas 0.664→**0.835**, genesis/16 0.586→**0.939**, matthew/28 0.652→**0.996**, psalms/150 0.837→**1.000**.
  (Psalms per-verse was already high because 1 line ≈ 1 verse, no straddle.)
- **The main audit (coverage-audit-verse.json) DOES realign** (genesis/24/13 best=0.936 vs gt_rescore's 0.66),
  so gt_rescore is the deflating tool; the main audit is sounder. But grain still matters everywhere.
- **ocr_consensus is DILUTED**: page-grain 0.67–0.75 — BELOW its own converged reference components (0.84–1.00),
  because the fusion votes noisy scan-OCR in at equal weight with the good references.
- Official report rerun (v010/v011): pass_rate_archaic 0.116, verse-cover 0.342, **2186/6391 verses have ≥1 scan
  passing**; rung routing **8 layout / 0 glyph** (Rung 2 = glyph has ZERO candidates — print too clean).

**Implication (Sir's goal = each rung must PROVABLY improve):** you cannot prove a rung's gain against a metric
that swings ±0.3 on segmentation. FIRST FIX = the metric (score at aligned/page/~20-word-window grain, reuse
align_coords.realign + the E5b window scorer). THEN redesign: (2) consensus fusion weighted by per-locus witness
fidelity (0.67→toward 0.84–1.00, a provable win, Rung ~1.5); (3) re-scope Rung 2 off "glyph" onto the real
residual failures (footnote-fused body lines → finer LINE seg; genuine recognition misses); (4) Rung 3 gated,
reserved for what 0–2 can't lift. Do NOT grind Rung-3 loci through the per-verse metric first — it would mislead.

## The path forward (concrete)
1. **Validate rung-3 on the HARD rung-0 loci** (psalms/118, matthew/28-annotations) — confirm it generalizes.
2. **Adopt rung-3 as the production reconstruction method**: column-crop → diplomatic vision pass →
   dual-track + ſ-count gate. Where gold exists, score; where it doesn't, rung-3 output IS the new
   gold-grade surface (gated, No-Silent-Degradation: below-bar stays OPEN).
3. **Wire rung-3 surfaces into the report/audit**, flipping loci OPEN→PASS as they cross 0.90 surface.
4. **Scale**: Claude/Gemini for the residual/hardest; local CHURRO+olmOCR MLX for bulk; always dual-track gated.

Scripts: `.scratch/rung3_gen24_score.py` · `gt_rescore.py` (consensus-vs-gold) · `reocr_ladder.py` (rung-0) ·
`consensus_v2.py`. Skill: `AI_OCR` (archaic-faithful recipe + dual-track rule + ſ-blindness caveat).
