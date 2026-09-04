# R16.20 — THE DETECTION BUDGET. R16.19 MEASURED THE WRONG CONSTANT FIRST, AND STEP (1) AS WRITTEN IS A REGRESSION.

**Instrument** `witness/probe_detect.py` · **data** `plates/detect-probe.json` ·
**baseline** `plates/bundle.json` (regression baseline, NOT gold). Run 2026-09-03, 208 leaves.
**Method** ONE forward pass per leaf at floor 0.01 with the top-k cap lifted to `num_queries`,
keeping every detection with geometry, score and label. Every reported (floor × cap × NMS ×
column) cell is a POST-FILTER of that one pass, so no cell differs from another by run-to-run
variation. Sections 6-8 re-derive the frame with `visual_agent.frame` itself, one line changed.

## 🔴 0. CORRECTION TO R16.19'S METHOD STATEMENT — THE PROBE NEVER RAN AT 0.01

R16.19 states "ONE forward pass per leaf at floor 0.01". It ran at the **shipped top-k cap**.

`surya/common/rfdetr/predictor.py:89` sets `num_select: 100`, and `PostProcess`
(`surya/common/rfdetr/models/lwdetr.py:363`) takes

```python
torch.topk(prob.view(out_logits.shape[0], -1), self.num_select, dim=1)
```

over the **flattened query × class** matrix. The 100 slots are therefore (box, label) **PAIRS**,
not boxes: one proposal scoring on three classes consumes three slots. `num_queries` is 300
(`predictor.py:88`), so the model proposes 300 boxes and the postprocess returns at most 100
pairs covering far fewer.

| | cap 100 (shipped) | cap 300 (`num_queries`) |
|---|---|---|
| detections/leaf at floor 0.01 | 100.0 | 300.0 |
| **distinct geometries**/leaf | **71.9** | 181.9 |
| slots spent on a duplicate geometry | **28%** | 39% |
| **effective floor**, median leaf | **0.0628** | 0.0277 |
| **effective floor**, worst leaf | **0.1718** | 0.0641 |

🔑 **All 208 leaves return exactly `num_select` detections at floor 0.01.** If the floor bound,
a leaf would return fewer. It never bound on any leaf. **The CAP bound**, at an effective floor
that is set by page content and varies from 0.037 to 0.172 across the corpus. That per-leaf,
content-dependent floor is exactly the confound "one pass, post-filtered" was written to remove.

⚠️ This does not overturn R16.19's headline. It re-sites it. The floor decomposition below the
cap stands, and one of its residues changes population.

## 1. R16.19's FLOOR-IMMUNE RESIDUE WAS A CAP ARTEFACT

"25 leaves have no body proposal at ANY floor" was measured through the cap.

| | leaves with NO body proposal at any floor |
|---|---|
| cap 100 (what R16.19 measured) | **25** |
| cap 300 | **5** |
| **recovered purely by lifting the cap** | **20** |

**16 of the 20 are `NT-1582-B`** — the one setting whose residue the floor could not explain
(49% floor-explained, against 100% / 89% / 75% elsewhere). The cap is the NT-specific defect
R16.19 correctly identified as "a different defect" and could not name.

⚠️ **The recovery is not harvestable by floor alone.** Those 20 body blocks score between 0.01
and 0.05. At floor 0.05 the corpus carries 145 boxes/leaf; at 0.10, where they are gone again,
no-body is 38 at either cap. Lifting the cap changes nothing at any shippable global floor.
**It is a per-leaf recovery that needs a per-leaf mechanism, and it stays OPEN.**

Residue sensitivity to the area criterion (cap 300, floor 0): a≥0.15 → 0 · a≥0.20 → 4 ·
a≥0.25 → 5 · a≥0.30 → 10. ⚠️ `MIN_BODY_AREA` is my constant, reports here and gates nothing.

## 🔴 2. STEP (1) AS WRITTEN — "floor 0.10-0.15 + class-agnostic NMS" — IS A REGRESSION

Measured with `visual_agent.frame` itself, against the live bundle as a **regression baseline**.
Re-running the LIVE config off the plate JPEGs (the bundle was built from source jp2s) moves
**6** leaves. That is the noise floor: a config moving 6 leaves has changed nothing.

| config | leaves moved >0.02 | >0.05 | >0.10 |
|---|---|---|---|
| live floor 0.40 cap 100 (**noise floor**) | 6 | 6 | 4 |
| floor 0.10 cap 100, no NMS | 88 | 75 | 55 |
| floor 0.10 cap 300 NMS 0.95 | 90 | 76 | 50 |
| floor 0.15 cap 300 NMS 0.95 | 74 | 62 | 35 |
| floor 0.10 cap 300 NMS 0.70 | 71 | 57 | 45 |

**The recommended change moves the frame on 43% of the corpus, 55 leaves by more than a tenth
of the page, against a noise floor of six.** R16.19 established that on 138 of 208 leaves the
frame was already sound, so most of that movement is damage. **The region metric is already
known-unsound (12×12 tiling scores perfect), so nothing downstream would have caught it.**

### NMS is not the remedy, and aggressive NMS is itself damage

| NMS IoU | boxes/leaf | body cand/leaf | leaves >1 cand | leaves LOSING their only body block |
|---|---|---|---|---|
| none | 54.8 | 2.61 | 124 | — |
| 0.95 | 41.2 | 1.84 | 110 | 1 |
| 0.80 | 39.0 | 1.46 | 89 | 2 |
| 0.70 | 37.3 | 1.27 | 74 | 2 |
| 0.50 | 32.9 | 1.00 | 37 | **4** |

Greedy class-agnostic NMS suppresses by score, so a body block overlapped by a higher-scoring
neighbour is deleted. At IoU 0.50 it destroys the body block on 4 leaves that had one, and
`OT1-1609-B`'s no-body count goes **0 → 1**. NMS at **0.95** is a pure duplicate-geometry
dedup: near-duplicate pairs/leaf 18.1 → 0.6, true nesting (IoS ≥ 0.90, IoU < 0.50) 89.0 → 86.3
against 89.0 for exact-geometry dedup, i.e. **it removes duplicate relations and no real
nesting**. That matters because `BIND_TIGHTEST` addresses a gold entry to the smallest box
containing it and cannot work without the nesting.

**Class-agnostic is not a simplification.** The duplicates are the same geometry under a
different label. A per-class NMS cannot see them at all.

## 🔴 3. THE ANCHOR IS NOT THE MECHANISM. THE COLUMN IS.

My first hypothesis was that `frame()`'s `max(area)` anchor breaks once low-confidence boxes
appear, and it is a reasonable one: at floor 0.40 the anchor scores median **0.796** / min
**0.402**, and at floor 0.10 it scores median **0.393**, with **108 of 208 anchors being boxes
the shipped pipeline would have discarded**. On `OT1-1609-B_0412` it takes a 0.742-area box
scoring 0.112 over a 0.261-area box scoring 0.911.

**The hypothesis is wrong, and the measurement refuted it.** Swapping the anchor for
`max(score×area)`, `max(score | area≥0.25)` or `max(area | score≥0.40)` moves the count from
90 to **89**. The anchor is not what moves the frame.

`frame()` anchors on one box and then takes the **MEDIAN EDGES OF THE COLUMN** — every box
above `SMALL_AREA` sharing ≥ `COLUMN_OVERLAP` of the body's width. Lowering the floor swells
that set, and the median moves regardless of what anchors it.

| | column members/leaf, median | max |
|---|---|---|
| live floor 0.40 cap 100 | 2.0 | 8 |
| floor 0.10 cap 300 NMS 0.95 | 5.0 | 22 |

## ✅ 4. THE FIX — SPLIT THE ONE NUMBER THAT IS DOING TWO JOBS

Detection at floor 0.10 / cap 300 / NMS 0.95 throughout; **only the column's confidence
filter moves**:

| column min score | moved >0.02 | >0.05 | >0.10 | col/leaf |
|---|---|---|---|---|
| 0.00 | 90 | 76 | 50 | 5.0 |
| 0.20 | 62 | 52 | 34 | 3.0 |
| 0.30 | 34 | 28 | 21 | 3.0 |
| **0.40** | **15** | **14** | **12** | 2.0 |
| 0.50 | 44 | 44 | 40 | 2.0 |
| 0.60 | 69 | 68 | 62 | 2.0 |

🔑 **The curve is U-shaped and its minimum sits at the shipped floor.** `0.40` is a **sound
framing constant and an unsound detection constant**, and one number has been doing both jobs.
Above 0.50 real body boxes leave the column and the frame degrades again, so this is a measured
optimum rather than a bigger-is-safer. **This is what "carry the confidence" is FOR**: it is
not a nicety for future cues, it is the precondition without which the floor change cannot ship.

**Detect wide, frame narrow, cue on everything.** ⚠️ **THE THIRD CLAUSE IS WRONG AND R16.20a §A3
REFUTES IT** — handing the naming step the wider set costs 6 MarginNote entries. Left standing here
as written because it is what this measurement concluded, and the correction belongs where it was found.

## 5. RESULT — EVERY NET MOVER, NAMED

Detection floor 0.10 / cap 300 / NMS 0.95, column min 0.40. Moved 15, of which 6 are raster
noise ⇒ **9 net**. Corpus live medians: measure width 0.721, head-foot span 0.808.

| leaf | Δ | live w | live span | new w | new span | verdict |
|---|---|---|---|---|---|---|
| `OT2-1610-P_0666` | 0.815 | 0.147 | 0.552 | 0.815 | 0.484 | collapsed → repaired |
| `OT1-1609-P_1011` | 0.753 | 0.141 | 0.159 | 0.903 | 0.891 | collapsed → repaired |
| `OT2-1610-P_0821` | 0.749 | 0.150 | 0.749 | 0.749 | 0.845 | collapsed → repaired |
| `NT-1582-B_0313` | 0.661 | 0.131 | 0.521 | 0.793 | 0.524 | collapsed → repaired |
| `OT2-1610-P_1111` | 0.404 | 0.397 | 0.306 | 0.807 | 0.669 | collapsed → repaired |
| `NT-1582-B_0803` | 0.378 | 0.360 | 0.458 | 0.739 | 0.457 | collapsed → repaired |
| `NT-1582-B_0782` | 0.376 | 0.353 | 0.765 | 0.732 | 0.751 | collapsed → repaired |
| `NT-1582-B_0802` | 0.369 | 0.353 | 0.631 | 0.354 | 0.559 | collapsed → repaired |
| `NT-1582-B_0804` | 0.045 | 0.729 | 0.724 | 0.673 | 0.724 | 🔴 **live looked FINE — REVIEW** |

`OT1-1609-P_1011` is the leaf R16.19 named as returning 8 overlapping body candidates. Its
measure goes 0.141 → 0.903 and its span 0.159 → 0.891.

⚠️ **`NT-1582-B_0804` moved from a healthy frame and is NOT absorbed into a total.** It is one
leaf, it is named, and it stays OPEN until a human settles it. Eight repairs and one unexplained
move is not "9 improved".

## CONSEQUENCES FOR THE WORK ORDER

1. 🔴 **Reprioritised step (1) must be re-stated.** Its three parts are not a list, they are an
   ORDER with a dependency: carry the confidence and filter the column FIRST, then lower the
   floor. Shipped as written it regresses 43% of the corpus.
2. 🔴 **NMS is a duplicate dedup at 0.95, not a pile solver.** 110 leaves still carry >1 body
   candidate. Aggressive NMS deletes body blocks. The pile is not solved by this change.
3. 🔴 **`num_select` is a FOURTH unnamed deciding constant**, in a vendored dependency, and it
   bound on every leaf of every measurement ever taken here. It belongs in the deciding-constant
   register alongside the floor.
4. ⚠️ **R16.12's tiling attribution is confounded a second way.** Tiling changes scale AND
   confidence AND how many proposals fit under the cap.
5. ⚠️ **Every per-setting detection number was taken under a per-leaf effective floor**, not the
   nominal one. Re-measure per setting is now non-optional (already step 6 of the order).
6. 📌 The 20 cap-recovered body blocks score 0.01-0.05 and **stay OPEN**. They are not reachable
   by any global floor and need a per-leaf mechanism.

## NOT DONE IN THE MEASUREMENT

Sections 0-5 above changed no constant, touched no call site and rebuilt nothing. Everything
below this line is the ADOPTION, run afterwards (`7a0a55e`), and it is reported separately
because two of its findings CONTRADICT the measurement that licensed it.

---

# R16.20a — THE ADOPTION. TWO THINGS THE PROBE COULD NOT SEE.

**Code** `witness/detect.py` (new, owns all five constants) · `visual_agent.py` ·
`plate_book.py`. **Rebuilt** `plates/bundle.json`, `gold/perception_OT1-1609-B_400-419.json`.

## 🔴 A1. "THE FLOOR AT ALL 6 CALL SITES" IS WRONG — 3 OF THE 6 MUST NOT MOVE

The sites divide by ROLE, not by which function they call. `score_surya_layout.py` (R14.0),
`surya_layout_probe.py` and `rung1_surya.py` measure **Surya off the shelf**, and R14.0's
**100/121 IS the bar the agent is scored against**. Re-tuning them would not improve a baseline,
it would delete one: the number would move together with the thing it exists to be compared
against. All three now carry a DO-NOT-CHANGE comment saying so. Only `visual_agent.see` and
`plate_book.build` route through `detect.py`.

## 🔴 A2. THE ANCHOR AND THE COLUMN MUST COME FROM THE SAME POPULATION

§3 above concludes "the anchor is not the mechanism" from a corpus count of 90 → 89. That is
true of the anchor's IDENTITY and **false of its POPULATION**, and the difference cost two leaves.

`COLUMN_OVERLAP` is a fraction **of the anchor's own width**, so the anchor sets the admission
rule for every other box. On `NT-1582-B_0439` a `Text` box scoring **0.137** spanning x
0.106–0.899 won `max(area)`; admission then demanded 0.397 of horizontal overlap, and the real
body text at x 0.395–0.774 is 0.379 wide, so it **could not qualify at any confidence**. Foot
0.826 → 0.499. `OT2-1610-P_1135` failed identically on a 0.199 `ListGroup`.

⚠️ **Filtering the anchor is the obvious fix and it does not survive measurement.** The body
blocks the lowered floor recovers ARE the low-confidence ones. Swept over all 208 leaves against
the 26 frames the old bundle had collapsed, column floor held at 0.40:

| anchor floor | 0.10 | 0.15 | 0.20 | 0.25 | 0.40 |
|---|---|---|---|---|---|
| REPAIRED | **7** | 5 | 5 | 3 | 0 |
| still collapsed | 19 | 21 | 21 | 23 | 26 |
| BROKEN | 2 | 1 | 1 | 1 | 1 |

**No interior optimum.** Unlike the column floor, whose U-shaped curve licensed choosing 0.40,
this one is monotone and every cell that repairs also breaks. Choosing a value would be fitting a
constant to 26 leaves with no gold behind it. **So no anchor constant was introduced, the variant
repairing most was taken, and the damage is NAMED.** The real fix is a redesign of
`COLUMN_OVERLAP`'s admission rule, which needs gold regions — step (2).

## 🔴 A3. "CUE ON EVERYTHING" IS WRONG — MY OWN SLOGAN, REFUTED

Handing the naming step the wider set cost **6 MarginNote entries**, confusion MN → RH. Measured
on GOLD-HEADBAND via `visual_agent.py`, the only score that reads LECTOR's perception at all:

| cue floor | 0.00 | 0.20 | 0.30 | 0.40 | 0.50 |
|---|---|---|---|---|---|
| boxes/leaf | 23.8 | 10.8 | 8.6 | 7.8 | 6.6 |
| overall | **111/121** | 116/121 | **117/121** | **117/121** | 106/**110** ⚠️ |
| MN recall | 12/19 | 17/19 | **18/19** | **18/19** | 13/14 |

The cues were written against a population already filtered at 0.40 and over-fire on anything
wider. ⚠️ At 0.50 the DENOMINATOR collapses — gold entries stop binding at all — the same U-shape.
0.40 is taken because it introduces no new number.

🔑 **THE FLOOR'S POSITION IN `settle()` IS THE WHOLE DESIGN**: after `frame`, before naming. The
two stages want OPPOSITE things from a low-confidence box — `frame` needs them (7 repairs depend
on a sub-0.40 anchor), every cue is harmed by them. Filtering once cannot serve both.

⚠️ **WITHHELD, NOT DISCARDED** (the E2/E14 lesson again): 30.3 boxes/leaf are kept on the leaf and
written to `bundle.json`, including **ListGroup 123 · Picture 83 · Table 16**, none read by any
cue. This is a HOLDING POSITION, not a verdict — `surya_conf` now exists so a cue can WEIGH a
proposal, and R16.6 can lower this floor without re-detecting 208 leaves.

## RESULT (208 plates, against the pre-adoption bundle)

| | |
|---|---|
| collapsed frames **REPAIRED** | **7** of 26 |
| collapsed frames still collapsed | 19 |
| previously healthy leaves **BROKEN** | **2** |
| GOLD-HEADBAND via `visual_agent.py` | **117/121**, MN 18/19 — UNCHANGED |
| named boxes/leaf | 10.9 → 10.8 · withheld 30.3 |
| archetypes moved | 8 leaves |

`OT1-1609-P_1011` measure width 0.141 → 0.911. `OT2-1610-P_0749` — the leaf REVIEW-STATE names
first under E26, "the scripture column itself unclaimed" — 0.149 → 0.897.

Other scorers: `score_argument_agent` A1–A5 PASS (overall 117/121 vs bar 115) · `score_skew_frame`
PASS · `score_foreedge` MN 18/18 · `score_pagenumber_agent` **B5 still FAILS**, pre-existing
(R14.10b), not caused here.

🔴 **`score_head_regions.py` IS UNCHANGED BECAUSE IT NEVER IMPORTS `visual_agent`.** A **DEAD
METRIC** for this change. It is not evidence of no regression, and quoting it as such would have
been the comfortable move.

## 🔴 OPEN AND BLOCKING AFTER THE ADOPTION

`NT-1582-B_0439` · `OT2-1610-P_1135` · `NT-1582-B_0804` · the **19 frames still collapsed** · the
**20 cap-recovered body blocks** scoring 0.01–0.05 that no global floor reaches · the **110 leaves
carrying >1 body candidate** (dedup at 0.95 removes duplicates; it does not solve the pile).

📌 `rung1_surya.py`'s do-not-change guard is UNCOMMITTED: the secret scanner false-positives on two
PRE-EXISTING strings there (an absolute filesystem path, and a slash-joined run of Surya class
names in the module docstring) under its 40-char alphanumeric AWS rule, which matches any long
alphanumeric-and-slash run. Both are already in HEAD; the diff there is six comment lines. For Sir.
