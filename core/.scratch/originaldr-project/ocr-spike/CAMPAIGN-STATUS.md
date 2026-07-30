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
| chapters in flight | — |
| chapters not started | 2-15, 17-50 |
| tests | 169 green |
| R2 model in production | `reichenau_dr.mlmodel` (311 unverified pairs, val 0.9396) |
| R2 challengers | arm A `dr_v3_armA` val **0.9739** (219 verified scripture lines) · arm B training |

## LOG
- 2026-07-29 21:xx — campaign opened. Item 2 (R2) arms A/B running; driver being built.
