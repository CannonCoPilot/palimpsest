# R16.19 (NEW) — THE DETECTION FLOOR, MEASURED. "71/208 HAS NO BODY BLOCK" DECOMPOSES.

**Instrument** `witness/probe_threshold.py` · **data** `plates/threshold-probe.json` ·
**figures** `witness/render_threshold_pairs.py`. Run 2026-09-03, 208 leaves, 39 s, 0.19 s/leaf.
**Method**: ONE forward pass per leaf at floor 0.01 keeping every detection with its score;
every reported floor is a post-filter of that one pass. Nothing is re-detected per floor, so
no floor comparison can be contaminated by run-to-run variation.
**Calibration**: at 0.40 the probe reports 70 no-body leaves against the live bundle's 71,
69 in common — the probe reproduces the live pipeline before it is used to criticise it.

## THE RESULT — the headline number is three different things
| population | n / 208 | |
|---|---|---|
| "no body block" at the live floor 0.40 (the reported defect) | **70** (34%) | |
| ...of which the FRAME IS ACTUALLY FINE | **49** | the test is wrong for multi-paragraph pages |
| COLLAPSED FRAME — the damage Root Cause 1 describes | **24** (12%) | |
| ...floor-recoverable (body IS proposed at 0.10) | **20** (83%) | |
| **genuinely unexplained after a one-line change** | **4** (1.9%) | |

🔑 **Root Cause 1 is 83% a threshold artefact, and its stated size is 3× the real damage.**
`FAST_LAYOUT_CONFIDENCE_THRESHOLD = 0.4` (`surya/settings.py:136`) deletes a correctly detected
body block on 45 of 208 leaves. Lowering to 0.10 takes no-body 70 → 38 and collapsed 24 → 4.

## 🔴 THE CRITERION IS ALSO WRONG — 49 leaves are misfiled by the test, not by the detector
`NT-1582-B_0009` ("TO THE READER") is segmented **correctly and confidently** into four paragraph
blocks, each < 0.25 of the leaf, plus its marginal notes; frame = head 0.102 / foot 0.851 /
measure (0.093, 0.795), labels RH·CH·MT×3·MN×4·CW. **A "largest box ≥ 25% of the page" test cannot
describe a prose page set in paragraphs**, and Surya's `Text` is a PARAGRAPH region (R16.16 §0666).
Of the 25 leaves with no body proposal at ANY floor, **21 have a plausible frame anyway**.
⚠️ `MIN_BODY_AREA = 0.25` is my own constant and is exactly the kind §3.0 forbids from deciding.
It is used here to REPORT, never to gate, and the result is given at 0.15/0.20/0.25/0.30.

## PER SETTING — pooling would have hidden this (acceptance is per-setting, R16 :4959)
| witness | n | no-body @0.40 | @0.10 | @0.01 | floor-explained |
|---|---|---|---|---|---|
| OT1-1609-B | 20 | 2 | 0 | 0 | **100%** |
| OT2-1610-P | 73 | 19 | 5 | 2 | **89%** |
| OT1-1609-P | 60 | 8 | 4 | 2 | 75% |
| NT-1582-B | 55 | 41 | 29 | 21 | **49%** |
🔴 **NT-1582-B is a different defect and the floor does not explain it.** Its residue is mostly the
criterion artefact above (prose prelims in paragraphs). Any single global floor is a per-setting claim.

## CONSEQUENCES FOR THE WORK ORDER
1. 🔴 **R16.15 (demote the head band, C4) is aimed at a 12% defect of which 83% is a one-line fix.**
   Its motivating finding must be re-stated before it is built. It is currently 4th in the amended order.
2. 🔴 **R16.12's tiling attribution is confounded.** Tiling changes box confidences as well as scale;
   SEVERE 5/5 "fixed by tiling" is consistent with the floor alone. Do not act on
   "R16.12 CHANGES WHAT THE GOLD SET HAS TO CONTAIN" (:4935) until re-run at a lowered floor.
3. 🔴 **R14.15 must not start.** Its re-aim puts `rfdetr` head re-initialisation on the critical path
   for a small-object floor that is, at least in part, a CONFIDENCE floor.
4. ⚠️ **The floor cannot ship alone.** Boxes/leaf 11.0 → 52.4 at 0.10; `OT1-1609-P_1011` returns
   **8 overlapping body candidates**. There is no NMS anywhere in surya (`grep -rn nms surya/` = 0).
   Class-agnostic NMS is part of the same change, not a follow-up.
5. 📌 **`see()` DISCARDS the detector's confidence** (`visual_agent.py:565` builds
   `Box(x0,y0,x1,y1,b.label)`), so no cue can weigh it even if one wanted to. Carry it.
6. 📌 Recovered bodies are labelled **Text 16 · ListGroup 15 · Table 1**. `ListGroup` is half, and
   no cue in `_cue()` reads it. Verse-per-paragraph settings arrive as `ListGroup`.

## CALL SITES — 6 on disk, not 5 (`git grep` misses the untracked one)
`visual_agent.py:1178` · `plate_book.py:185` · `score_surya_layout.py:108` ·
`tile_probe.py:241` (**UNTRACKED**) · root `rung1_surya.py:59` · root `surya_layout_probe.py:23`.

## NOT DONE HERE
No threshold was changed, no NMS was added, no bar moved, nothing adopted. This is a measurement.
The 4 genuinely unexplained collapsed leaves stay **OPEN and blocking**.
