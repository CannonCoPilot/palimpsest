"""THE DETECTION BUDGET — the one place LECTOR's perception constants are decided.

Before this module the numbers deciding what LECTOR is allowed to see were: one constant in
`surya/settings.py`, one in `surya/common/rfdetr/predictor.py`, and no dedup at all. None was
named in this repo, none was in the deciding-constant register, and one of them
(`num_select`) bound EVERY detection measurement ever taken here without appearing in a
single document. R16.20 measured all three together; this module owns them.

  ⚠️ ADOPTED FROM MEASUREMENT, NOT TASTE. Every constant below is the argmin or the
  measured optimum of a curve in `plates/DETECT-PROBE-2026-09-03.md`. Re-run
  `witness/probe_detect.py --report-only` and the tables that chose them print again.

## The finding this module exists to encode: ONE NUMBER WAS DOING TWO JOBS

`FAST_LAYOUT_CONFIDENCE_THRESHOLD = 0.4` was simultaneously
  (a) the DETECTION floor — what the model is allowed to propose, and
  (b) the FRAMING floor — which proposals get to vote on where the measure is.
It is wrong for (a) and right for (b), and because it was one number that could not be said.

  * As a DETECTION floor it deletes a correctly-detected body block on 45 of 208 leaves
    (R16.19), and the top-k cap above it silently truncated every leaf besides (R16.20 §0).
  * As a FRAMING floor it is the measured optimum. `visual_agent.frame` takes the MEDIAN
    EDGES of the column; dropping the detection floor to 0.10 swells that column from 2.0
    to 5.0 members per leaf and moves the frame on 90 of 208 leaves against a 6-leaf noise
    floor. Restricting the column to >= 0.40 takes that to 15. The curve is U-shaped with
    its minimum AT 0.40 — at 0.50 and 0.60 real body boxes leave the column and it
    degrades again — so this is an optimum, not a bigger-is-safer.

  ➡️ DETECT WIDE, FRAME NARROW, CUE ON EVERYTHING.

## ⚠️ THIS MODULE IS NOT FOR EVERY CALLER. Three call sites MUST NOT USE IT.

The reprioritised order said "floor 0.10-0.15 at all 6 call sites". That is wrong, and
following it would have re-baselined the adoption bar together with the thing being
measured against it. The sites divide by ROLE, not by which function they call:

  USE THIS MODULE — LECTOR's own perception:
    `visual_agent.build_cache`      the agent's cached perception
    `plate_book.build`              the plate book / `bundle.json`

  🔴 MUST STAY AT SHIPPED DEFAULTS — these measure SURYA OFF THE SHELF, and off-the-shelf
     is the whole claim. Re-tuning them would not improve a baseline, it would delete one:
    `score_surya_layout.py`         R14.0, the rung-0 admissibility score vs GOLD-HEADBAND
    `surya_layout_probe.py`         the rung-0 gate
    `rung1_surya.py`                the rung-1 controlled A/B; its Surya arm IS off-the-shelf

  📌 INSTRUMENTS keep their own declared settings and cite these constants rather than
     importing behaviour: `probe_threshold.py` (R16.19), `render_threshold_pairs.py`,
     `probe_detect.py` (R16.20), `tile_probe.py` (R16.12).

## Not fixed here

The 20 body blocks that only the lifted cap returns score 0.01-0.05 and are NOT reachable
by any global floor. 110 leaves still carry more than one body candidate. `NT-1582-B_0804`
moved from a healthy frame. All three stay OPEN; see the record's closing section.
"""
from __future__ import annotations

# ---------------------------------------------------------------- the register
# 🔴 THE DETECTION FLOOR. surya ships 0.40 (`surya/settings.py:136`); R16.19 showed that
# deletes a correctly-detected body block on 45 of 208 leaves. 0.10 recovers 20 of the 24
# genuinely collapsed frames. Not lower: at 0.05 the corpus carries 145 boxes/leaf, and the
# body blocks that appear between 0.01 and 0.05 are NOT recoverable by a global floor anyway.
DETECT_FLOOR = 0.10

# 🔴 THE TOP-K CAP, and the constant nothing in this repo knew about. surya ships 100
# (`surya/common/rfdetr/predictor.py:89`) and `PostProcess` (`models/lwdetr.py:363`) takes
# `topk` over the FLATTENED query x class matrix — so the slots are (box, label) PAIRS and
# 28% of them go to the same geometry under a different label. All 208 leaves returned
# exactly 100 at floor 0.01, i.e. THE CAP BOUND ON EVERY LEAF and the effective floor was
# per-leaf (median 0.063, worst 0.172). 300 is `num_queries` — the model's own ceiling, so
# this is not a tunable but the removal of a truncation.
NUM_SELECT = 300

# 🔴 DEDUP. There is no NMS anywhere in surya (`grep -rn nms surya/` = 0). At 0.95 this is a
# DUPLICATE-GEOMETRY dedup and nothing more: near-duplicate pairs/leaf 18.1 -> 0.6, while
# true nesting (IoS >= 0.90, IoU < 0.50) goes 89.0 -> 86.3 against 89.0 for a pure
# exact-geometry dedup. ⚠️ NOT LOWER. At 0.50 it DELETES the body block on 4 leaves that had
# one and takes `OT1-1609-B`'s no-body count from 0 to 1. It is a dedup, not a pile solver:
# 110 leaves still carry >1 body candidate afterwards, and that stays OPEN.
DEDUP_IOU = 0.95

# 🔴 THE FRAMING FLOOR — read by `visual_agent.frame`, which is the ONLY consumer. This is
# the surviving half of the shipped 0.40, kept at its measured value for the job it is
# actually good at. See the module docstring.
COLUMN_MIN_CONF = 0.40

# 🔴 THE CUE FLOOR — and the constant that REFUTES THE THIRD CLAUSE OF THIS MODULE'S OWN SLOGAN.
# "Detect wide, frame narrow, CUE ON EVERYTHING" is wrong, and one measurement said so. Handing
# the naming step the wider box set costs six entries on the pre-registered rung-0 score, all of
# them MarginNote, and the confusion is MN -> RH: the cues were WRITTEN AGAINST A POPULATION
# ALREADY FILTERED AT 0.40 and over-fire on anything wider. Measured on GOLD-HEADBAND, the only
# score that reads LECTOR's perception at all:
#
#     cue floor    0.00    0.20    0.30    0.40    0.50
#     boxes/leaf   23.8    10.8     8.6     7.8     6.6
#     overall     111/121 116/121 117/121 117/121  106/110  <-- ⚠️ DENOMINATOR COLLAPSES
#     MN recall    12/19   17/19   18/19   18/19    13/14
#
# 0.30 and 0.40 both restore 117/121 exactly. 0.40 is taken because it is the value already
# standing, so this introduces no new number — and at 0.50 gold entries stop binding at all,
# which is the same U-shape the framing floor has.
#
# ⚠️ THIS IS A HOLDING POSITION AND IT IS NAMED AS ONE. It is NOT a claim that low-confidence
# boxes are worthless: `see()` now carries `surya_conf`, so a cue can WEIGH a proposal for the
# first time, and none does yet. R16.6 is exactly that work (Surya emits Picture x47, Table x11,
# ListGroup x123 in the rebuilt bundle and no cue reads any of them). When a cue weighs
# confidence instead of assuming it, this floor comes down — and the withheld boxes are kept on
# the leaf and written to the bundle precisely so that work needs no re-detection.
CUE_MIN_CONF = 0.40


# ---------------------------------------------------------------- geometry
def iou(a, b) -> float:
    """IoU over two objects exposing x0/y0/x1/y1. Used only by `dedup`."""
    iw = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    ih = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    inter = iw * ih
    ua = max(0.0, a.x1 - a.x0) * max(0.0, a.y1 - a.y0)
    ub = max(0.0, b.x1 - b.x0) * max(0.0, b.y1 - b.y0)
    u = ua + ub - inter
    return inter / u if u > 0 else 0.0


def dedup(boxes, thr: float = DEDUP_IOU):
    """Greedy CLASS-AGNOSTIC suppression, highest detector score first.

    🔑 CLASS-AGNOSTIC IS THE POINT, NOT A SIMPLIFICATION. The duplicates this removes are
    the SAME geometry under a DIFFERENT LABEL — an artefact of `topk` running over the
    flattened query x class matrix — and a per-class NMS cannot see them at all.

    ⚠️ NESTING MUST SURVIVE AND IT DOES, MEASURED. Surya's boxes nest by design: the body
    `Text` block physically contains the running head, and `BIND_TIGHTEST` addresses a gold
    entry to the SMALLEST box containing it. A nested pair has low IoU, so `DEDUP_IOU`
    leaves it alone — but that is an argument, and the measurement is the reason: true
    nesting per leaf 89.0 (exact-geometry dedup) vs 86.3 (this, at 0.95).

    Requires `surya_conf` on each box. Sorting by anything else — area, or the cue's
    `conf` — would suppress by the wrong ranking, and suppressing by the cue's confidence
    would feed a detection decision its own downstream verdict.
    """
    keep = []
    for b in sorted(boxes, key=lambda x: -x.surya_conf):
        if all(iou(b, k) <= thr for k in keep):
            keep.append(b)
    return keep


# ---------------------------------------------------------------- the predictor
def predictor(**kw):
    """A `FastLayoutPredictor` with the top-k cap lifted to `NUM_SELECT`.

    🔴 THE PATCH IS VERIFIED, NEVER ASSUMED. `num_select` lives three attributes deep in a
    VENDORED dependency. If that path moves under a surya upgrade, a silent no-op would
    leave every caller believing it had lifted a cap that was still at 100 — and because
    the cap binds on every leaf, that is not a small error, it is the whole measurement
    reverting while the numbers keep being reported as post-fix. So the attribute is read
    back and a failure RAISES.
    """
    from surya.fast_layout import FastLayoutPredictor

    pred = FastLayoutPredictor(**kw)
    try:
        post = pred.model.model.postprocess
    except AttributeError as e:                                       # noqa: BLE001
        raise RuntimeError(
            "detect.predictor: cannot reach the rf-detr postprocess to lift the top-k cap "
            f"({e}). surya's internals have moved; re-derive the path before running — "
            "the cap binds on EVERY leaf and a silent no-op reverts R16.20 invisibly."
        ) from e
    post.num_select = NUM_SELECT
    if post.num_select != NUM_SELECT:
        raise RuntimeError(
            f"detect.predictor: num_select is {post.num_select} after being set to "
            f"{NUM_SELECT}. The cap was NOT lifted."
        )
    return pred


def detect(image, pred, floor: float = DETECT_FLOOR):
    """Detect on ONE image, returning `(x0, y0, x1, y1, label, score)` in PAGE FRACTIONS.

    Returns tuples rather than `visual_agent.Box` so that this module has no dependency on
    the agent — `visual_agent` imports THIS, and the reverse would be a cycle. Detection
    only: `dedup` is a SEPARATE call because the caller builds `Box`es in between, and
    because keeping them separate is what lets a caller measure one without the other.

    ⚠️ ORDER MATCHES THE SHIPPED PIPELINE: the cap is applied inside `PostProcess` on the
    raw score-ranked list, THEN the floor, THEN dedup. Deduping before the cap would
    measure a detector surya does not ship.
    """
    Wp, Hp = image.size
    res = pred([image], threshold=floor)[0]
    out = []
    for b in res.bboxes:
        x0, y0, x1, y1 = b.bbox
        out.append((x0 / Wp, y0 / Hp, x1 / Wp, y1 / Hp, b.label,
                    float(getattr(b, "confidence", None) or 0.0)))
    return out
