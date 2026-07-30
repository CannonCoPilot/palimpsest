# GENESIS CAMPAIGN — bring every chapter to the Genesis 1/16 standard (2026-07-29, autonomous session)

**Sir's order:** every chapter of Genesis to the standard of chapters 1 and 16 — every verse of every source
(S1, S3, S6, S9) matching **each** of the four references (s_dismas, odr_com, sabates_a, madueke_b) at **>=0.90**,
with every ſ-surface CLOSED. Agent-read GT is APPROVED as a ground-truth source (calibrated 2026-07-29: content
0.9923, ſ counts exact on 29/29 correctly-paired lines).

**This file is the ledger. It is rewritten after every chapter so the state survives a context clear.**

## Standing decisions for this campaign (do not re-litigate)
1. The chapter workflow is `CHAPTER-WORKFLOW.md` phases 0-7. Do not re-derive it.
2. Interpreter: `../ocr-venv/bin/python`. Tests: `pytest tests/` (169 at session start).
3. A below-bar cell stays OPEN and BLOCKS. No back-off, no cap, no "parked". Safeguards ALERT; they never accept.
4. Agent-read GT follows `ground-truth/GUIDELINES.md` — glyph-driven ſ, French spacing preserved, leading verse
   numbers stripped, `⟨?⟩` rather than a guess. Provenance `agent-read`, kept separable from human gold.
5. Commit in coherent units as work completes; the hold on PUSH remains until Sir says otherwise.

## STATE

| | |
|---|---|
| chapters at 100% | **1, 16** |
| chapters measured cold | 17 of 50 |
| cells at >=0.90 across measured chapters | **1317/1992 = 0.6611** |
| tests | 176 green (169 + 7 this campaign) |
| R2 model in production | `reichenau_dr.mlmodel` — challengers MEASURED AND REJECTED (see log) |

### WHAT THE COLD MEASUREMENT SETTLED
- The generalizable rules already carry **~66-70% of cells** on chapters nobody has touched, and **all-fail is
  ~0** everywhere: no localization, addressing or reference breakage. The residual is per-source recognition.
- The weakest source is consistently **S6** (0.30-0.50), the 1635 second edition, whose divergence from the 1609
  references is a known collation issue rather than an OCR one.
- `CHAPTER_MODEL` existed only for chapters 1 and 16; it is now DERIVED for every chapter, which was the single
  biggest structural gap.
- Geometry cannot separate the left-column intruders that dominate the residual — measured, pinned, sixth
  failure of that idea. The remedy is R3 (which reads the printed crop directly) or content-and-sequence
  alignment (unbuilt).

### THE PLAN FOR THE NIGHT
1. Breadth measurement of all 50 chapters (4 parallel workers) — in flight.
2. R3 SEQUENTIALLY, fewest-open-cells-first, self-driving via `r3-runner.sh`, ledger `.campaign/r3-ledger.txt`.
   Sequential is deliberate: the olmOCR-2 MLX model is ~17GB resident and two workers would swap.
3. Re-measure after each chapter; a chapter reaching 100% is CLOSED, anything else stays OPEN and blocks.
4. Commit as coherent units. Report honestly which chapters closed and which did not, and why.

## LOG
- 2026-07-29 21:0x — campaign opened. Item 2 (R2) arms A/B running; `chapter_campaign.py` built and validated
  (reproduces ch16 as CLEAN 64/64).
- 2026-07-29 21:1x — 4 commits staged (Genesis 16 closure · Q36 selector · Q37-Q39 R2 harvest + agent-read GT ·
  docs). Nothing pushed.
- 2026-07-29 21:2x — breadth measurement launched, 4 parallel workers over chapters 2-13, 14/15/17-25, 26-37,
  38-50. Heartbeat monitor armed (15-min progress events).
