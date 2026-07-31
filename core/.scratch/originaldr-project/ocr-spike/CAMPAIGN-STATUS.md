# GENESIS CAMPAIGN — RESUME HERE (state 2026-07-30, after the overnight autonomous session)

**Sir's standing order:** every chapter of Genesis to the standard chapters 1 and 16 reached — every verse of
every source (S1, S3, S6, S9) matching **each** of the four references at **>=0.90**, every ſ-surface CLOSED.
**Stance (Sir, 2026-07-30): DEPTH-FIRST**, and after each chapter is brought up, **re-measure the others** —
knock-on gains from generalizable fixes should reduce the work as the campaign iterates.

## THE ONE RULE THAT GOVERNS EVERYTHING HERE (§13 Q47)

> **A rule is measured by the TEXT IT CHANGES, not by the verdicts it flips.**

`split_glued` scored HELPS 8 / HURTS 1 / net +8 cells across 50 chapters with the sentinels unmoved, and was
minutes from adoption. It alters **1,356 tokens**, tearing real words into morphemes (`lawful` -> `law ful` 28x,
`faithful` -> `faith ful` 14x). The score could not see it: the corruptions were score-neutral or fell in cells
that already failed. **Before adopting ANY rule that edits text, run `faithfulness_audit.py` and read what it
changes.** Nine rules are pinned OFF in this tree with their numbers; the audit is why the tenth was caught.

## STATE

| | |
|---|---|
| cells >=0.90 / ACHIEVABLE | **4,273 / 5,416 = 0.7890** |
| cells >=0.90 / raw total | 4,273 / 6,120 = 0.6982 |
| reference-complete chapters only | 3,496 / 4,332 = 0.8070 over 34 chapters |
| **CHAPTERS CLOSED** | **2** — chapters 1 and 16 (sentinels; re-measure them on EVERY change) |
| cells blocked by an absent reference | **704**, over 16 chapters |
| tests | **173 green** (`../ocr-venv/bin/python -m pytest tests/`) |
| commits | 23 this session, **nothing pushed** — the hold stands |

**REF-GAP chapters:** 4, 6, 8, 9, 11, 12, 13, 15, 18, 49 — plus partial gaps in 20, 23, 30, 34, 40, 41.
`odr_com` is the missing witness in 4, 6, 9, 11, 13, 49; `s_dismas` in 8. **Genesis 46 was recovered this
session (0/136 -> 107/136).**

## NEXT STEPS, IN ORDER — THIS IS THE RESUME PLAN

1. **GENESIS 8 RENUMBERING via `ref_renumber.CORRECTIONS`** (88 cells). The s_dismas PDF prints DR verses 15 and
   16 merged under `15` and shifts the rest. `ref_repair_s_dismas.py` parses it FAITHFULLY; the fix is a
   corroborated **split** entry (odr_com, sabates_a, madueke_b all agree), exactly like the documented
   `s_dismas genesis 26` merges. Then re-run the repair with ch8 accepted.
2. **`odr_com` GAPS — chapters 4, 6, 9, 11, 13, 49 (616 cells).** A DIFFERENT source and acquisition from
   s_dismas: `odr-com scrape/{book}.json`, `method: html-scrape`. Diagnose the same way — does the scrape hold
   the verses and the build drop them, or is the scrape itself short? **Do NOT invent text**; if the source
   lacks them that is an acquisition task to report, not to patch.
3. **SIZE THE THREE S6 CAUSES SEPARATELY** — not yet done, and the prerequisite for any ninth apparatus attempt:
   | cause | example | remedy class |
   |---|---|---|
   | annotation prose sharing rows with scripture on a MIXED leaf | ch22 p88, ch12 | within-leaf column separation — UNBUILT |
   | missing leaves / unlocalized verses | ch44 (8 verses with NO span; 4 leaves vs 5 elsewhere) | localizer coverage, upstream |
   | edition divergence 1635 vs 1609 references | CHAPTER-WORKFLOW | collation judgement; no recognizer closes it |
   Every one of the EIGHT pinned separation attempts was aimed at the AVERAGE of these three, which is why each
   convinced on its examples and failed on the population.
4. **DEPTH-FIRST CHAPTER WORK.** Closest reachable chapters, cells short after R3: **ch22 (12), ch33 (12),
   ch7 (13), ch48 (13), ch25 (14), ch45 (14), ch17 (15), ch2 (16)**. Follow CHAPTER-WORKFLOW phases 0-7. After
   each chapter closes, **re-measure all 50** (`chapter_campaign.py --chapters 1-50 --phase measure`) to capture
   knock-on gains — Sir's explicit instruction.

## TOOLS BUILT THIS SESSION (all in `ocr-spike/`, all chapter-parameterized)

| tool | what it answers |
|---|---|
| `chapter_campaign.py --report` | the whole board: per-chapter rate, triage, achievable vs blocked, closed set |
| `faithfulness_audit.py` | **what each rule CHANGES in the text** — run before adopting any text-editing rule |
| `s_lexicon.py --build --validate` | attested ſ and f-vs-ſ lexicons from human GT; 502/502 and 657/657 = 1.0000 held out |
| `ref_repair_s_dismas.py --verify` | re-parse of the s_dismas PDF with its three parse defects fixed |
| `chapter_model_derive.py` | opening-leaf model per chapter (**measured NET NEGATIVE, default OFF**) |
| `selector_probe.py`, `selector_corpus_probe.py` | the janvier_fit dead-selector measurement (§13 Q30/Q36) |
| `rung2_*.py` | R2 training-data recovery, pair verification, agent-read calibration |
| `.campaign/r3-ledger.txt`, `.campaign/matrix-genesis-N.json` | the R3 log and every chapter's matrix |

## PINNED NEGATIVES — DO NOT RE-PROPOSE WITHOUT READING THEIR NUMBERS

Nine, each wired-but-off with figures and a test: four geometric apparatus splits (word-x threshold, gap ratios,
widest-gap right edge, per-leaf median left edge), the S6 band sweep (0.228 costs chapter 1 four cells), the
margin-orphan gap test (fires nowhere), the row-interrupt content filter (deletes scripture: ch1 124->107), the
derived CHAPTER_MODEL (net -7 cells), and `split_glued` (1,356 corruptions for +8 cells).

## OPERATIONAL NOTES

* Interpreter `../ocr-venv/bin/python`; MLX needs `PYTORCH_ENABLE_MPS_FALLBACK=1`.
* R3 is ~17GB resident — run it SEQUENTIALLY. `r3-runner.sh` holds an atomic `mkdir` lock (a `pgrep` mutex is a
  race and let two models load at once).
* R3 adoptions are APPEND-ONLY and go stale when the page model improves —
  `chapter_campaign.stale_adoptions(ch)` reports them. 3 known, all still >=0.90, NOT auto-reverted: the adopted
  text carries a CLOSED ſ surface the page model's better-scoring text does not.
* Agent-read GT is APPROVED and calibrated: 40 blind reads, content 0.9923 mean, **ſ counts exact 29/29**.
  Follow `ground-truth/GUIDELINES.md`; provenance stays `agent-read` and separable.
* A monitor must read the ARTIFACTS (matrices), never a prose document — the first heartbeat grepped
  CAMPAIGN-STATUS.md and silently reported an empty closed-chapter list when this file was reworded.
