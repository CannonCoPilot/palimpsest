#!/usr/bin/env python
"""R16.7 — UNCLAIMED INK: the first instrument in this project that can see a MISSING box.

🔴 THE BLIND SPOT THIS CLOSES. `visual_agent`, `score_foreedge`, `score_head_regions`,
`score_argument_agent` — every scorer here walks a list of adjudicated boxes and asks what the agent
NAMED each one. That loop cannot visit a box that was never drawn. `plate_screen` is closer but reads
`bundle.json`, so it too sees only geometry that exists; its own docstring says *"it finds defects
that are visible in the GEOMETRY"*. The eye review found the detector dropping running heads, chapter
heads, signatures, catchwords, whole margin columns and — on seven leaves — THE SCRIPTURE COLUMN
ITSELF, and **not one of those can move any number this project publishes.**

🔑 SO THIS READS THE IMAGE, NOT THE BOXES. Ink that the page prints and no region claims is a
detection failure that needs no gold to observe: it is a fact about the leaf and the layout together.

    unclaimed = ink pixels falling inside NO box  ÷  ink pixels on the leaf

⚠️ IT IS AN INSTRUMENT, NOT A VERDICT. Unclaimed ink is not the same thing as a missed OBJECT: a
correct box that stops one line short leaves ink unclaimed, and so does bleed-through, and so does the
gutter shadow. It ranks leaves for attention. `plates/detection-standard.json` — the eye review's
graded claim — is what it is VALIDATED against, and that standard is itself unadjudicated.

🔴 BORDER-TOUCHING COMPONENTS ARE REMOVED FIRST, and this is a correctness requirement rather than a
tidy-up. A scan carries page edges, the gutter shadow and the dark surround of the platen; all are
"ink" to a grey threshold, all fall outside every box, and all would be counted as unclaimed on EVERY
leaf. That would not merely add noise — it would add a roughly CONSTANT offset, which is worse,
because a constant offset preserves the ranking and so looks like a working instrument while the
absolute number means nothing. `collation_read.text_runs` already records this failure mode for the
band case (*"a run that reaches the band's BOTTOM EDGE is the leaf edge / gutter shadow, not type"*).

⚠️ THE INK THRESHOLD IS `verify_setting.INK_LEVEL`, IMPORTED. The project has one declaration of what
counts as ink and this file does not get a second opinion about it.

═══ PRE-REGISTERED, WRITTEN BEFORE THE FIRST RUN ═══════════════════════════════════════════════════

⚠️ P0 IS **NOT** PRE-REGISTERED AND IS MARKED AS SUCH RATHER THAN SLIPPED INTO THE LIST. It was
added AFTER the first run, when the ranked table showed leaves losing 84% of their ink to border
removal. A check invented once the data is in can be shaped by the data — that is exactly what
pre-registration exists to prevent — so it is reported as what it is: a confound found by looking,
not a prediction that survived a test. ⚠️ It also means P1's PASS was obtained BEFORE anyone knew
two of its seven leaves were unreliable, which is the honest order of events and is why P1 is
reported as 5 solid + 2 unreliable rather than 7/7.

P1  SEVERE SEPARATES.  All 7 leaves the eye grades SEVERE (the body block itself unclaimed) rank in
    the TOP 25 of 208 by unclaimed fraction. ⚠️ If they do not, the measure does not see the largest
    detection failure in the corpus and it is REFUTED — a redesign trigger, never an accepted gap.

P2  EMPTY INVERTS.  The 4 leaves graded EMPTY (a box drawn over blank paper) carry a box whose INK
    DENSITY sits in the lowest decile of all boxes in the corpus. This is a negative control with the
    OPPOSITE sign: an instrument that only ever says "more ink is missing" could pass P1 by ranking
    dense leaves first, and P2 is not passable that way.

P3  SMALL DOES **NOT** SEPARATE, AND THIS IS PREDICTED TO FAIL, IN ADVANCE.  A missing catchword is
    two words; a leaf carries thousands. Precision@25 for SMALL-graded leaves will sit at or near the
    57% base rate. ⚠️ WRITING DOWN THE EXPECTED NULL IS WHAT MAKES IT EVIDENCE. If SMALL separated,
    the measure would be reading something other than ink mass and every reading here would need
    re-examining. A confirmed P3 is the SENSITIVITY FLOOR, measured instead of assumed, and it is the
    quantitative case that **ink coverage cannot be the whole detection instrument.**

⚠️ P1 AND P3 TOGETHER ARE THE POINT. Separately, either could be told as a success story. Together
they say exactly what this instrument is: it finds the catastrophic failures and is blind to the
common ones, which is a bounded claim and a usable one.

    ../ocr-venv/bin/python witness/score_detection.py            # score + the three tests
    ../ocr-venv/bin/python witness/score_detection.py --top 40   # widen the ranked listing

Exit 1 while any pre-registered test fails or the SEVERE leaves remain unrepaired — which is the
healthy state today, since nothing has been done about them yet.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import numpy as np                                    # noqa: E402
from PIL import Image                                 # noqa: E402
from scipy import ndimage                             # noqa: E402

import verify_setting as VS                           # noqa: E402

PLATES = _HERE / "plates"
BUNDLE = PLATES / "bundle.json"
STANDARD = PLATES / "detection-standard.json"
OUT = PLATES / "detection-scores.json"

# Working resolution. ⚠️ A SIZE PRIOR THAT INITIALISES AND DECIDES NOTHING (§3.0's permitted use):
# it fixes how fine a mark survives, and every leaf is measured at the same scale, so it cannot
# favour one leaf over another. At 1000px a line of this book's type is ~8px tall — a missing
# catchword is still several hundred pixels, well above the component floor below.
WIDTH = 1000
# A connected component smaller than this share of the page is speckle, foxing or a broken serif,
# never an object a detector was asked to find. Reported alongside the score so its effect is visible.
MIN_BLOB = 2e-5
TOP_N = 25          # P1's window, pre-registered above
# 🔴 ABOVE THIS SHARE OF INK REMOVED AS BORDER-TOUCHING, A LEAF IS NOT MEASURED — IT IS MANGLED.
# Border removal is necessary (see the docstring) and it is NOT SAFE AS IMPLEMENTED: on a leaf
# cropped tight to the type, the type block itself touches the frame and goes with the surround.
# `OT2-1610-P_0035` loses 84.5% of its ink this way and still ranks 8th, so it PASSES P1 on a
# measurement that means almost nothing. ⚠️ This threshold does not repair anything; it makes the
# damage COUNTABLE, which is the precondition for repairing it. See P0.
RELIABLE_DROP = 0.20
# Each side of a blank channel must hold at least this share of the box's ink for the channel to be
# a COLUMN GUTTER rather than the emptiness of a box drawn over nothing. ⚠️ Not fitted: two columns
# of a table or a parallel comparison split their ink roughly evenly, so anything well below 0.5
# admits every real case, and an empty box clears no positive value at all. It separates a defect
# from a DIFFERENT defect that already has its own grade (E23/EMPTY), which is what it is for.
GUTTER_FLANK = 0.20


def _ink(im: Image.Image) -> np.ndarray:
    """The project's own ink test, at working resolution. `collation_read._ink`, one scale down."""
    w, h = im.size
    im = im.convert("L").resize((WIDTH, max(1, round(h * WIDTH / w))))
    return (np.asarray(im, dtype=float) / 255.0) < VS.INK_LEVEL


def _drop_border(mask: np.ndarray) -> tuple[np.ndarray, float]:
    """Remove every ink component TOUCHING the image border, and report what was removed.

    ⚠️ THE REMOVED SHARE IS RETURNED, NOT SWALLOWED. On a well-cropped leaf this is a percent or two;
    on a leaf photographed with its neighbour it can be most of the frame. A leaf where this number
    is large is one whose unclaimed score means something different from the rest, and the caller
    cannot know that unless it is told.
    """
    lab, n = ndimage.label(mask)
    if n == 0:
        return mask, 0.0
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    edge = edge[edge > 0]
    if edge.size == 0:
        return mask, 0.0
    keep = ~np.isin(lab, edge)
    out = mask & keep
    return out, 1.0 - out.sum() / max(1, mask.sum())


def measure(plate: dict) -> dict | None:
    path = PLATES / plate["img"]
    if not path.is_file():
        return None
    with Image.open(path) as im:
        raw = _ink(im)
    mask, dropped = _drop_border(raw)
    h, w = mask.shape
    total = int(mask.sum())
    if total == 0:
        return {"id": plate["id"], "total_ink": 0, "unclaimed": 0.0, "blob": 0.0,
                "dropped": dropped, "min_box_density": None, "max_slack": None,
                "max_gutter": None, "n_boxes": len(plate["boxes"])}

    claimed = np.zeros_like(mask)
    densities, slack, gutter = [], [], []
    for b in plate["boxes"]:
        x0, x1 = int(b["x0"] * w), int(np.ceil(b["x1"] * w))
        y0, y1 = int(b["y0"] * h), int(np.ceil(b["y1"] * h))
        x0, y0 = max(0, x0), max(0, y0)
        if x1 <= x0 or y1 <= y0:
            continue
        claimed[y0:y1, x0:x1] = True
        sub = mask[y0:y1, x0:x1]
        densities.append(float(sub.mean()))          # P2's statistic: ink per pixel INSIDE the box
        # 🔴 THE OVER-BOXING STATISTICS (Sir, 2026-08-29). Unclaimed ink is HALF the problem: it
        # finds ink no box covers and is silent on a box covering far more than its object. ⚠️ AND
        # THE ASYMMETRY IS EXPLOITABLE — one box drawn round the whole leaf scores ZERO unclaimed
        # ink, a perfect result for a useless layout. Both defects corrupt the same downstream
        # artefact, the crop handed to the recogniser, in opposite directions.
        cols = sub.any(axis=0)                       # which columns of the box carry any ink
        rows_ = sub.any(axis=1)
        if cols.any():
            # SLACK — the box's own ink, tightly bounded, against the box. Catches a region padded
            # out over blank margin (E16) or drawn tall over nothing (E23).
            ci, ri = np.flatnonzero(cols), np.flatnonzero(rows_)
            tight = (ci[-1] - ci[0] + 1) * (ri[-1] - ri[0] + 1)
            slack.append(1.0 - tight / max(1, sub.size))
            # GUTTER — the widest FULLY BLANK vertical band inside the box, as a share of its width.
            # ⚠️ SLACK ALONE CANNOT SEE A TWO-COLUMN WRAP: ink reaches both edges, so the tight
            # bound IS the box and slack reads 0. The blank channel between the columns is the
            # signal, and it is exactly what E13 describes — *"multi-column matter taken as one
            # block"*. Measured only between the first and last inked column, so the box's own
            # margins are not counted as a gutter twice over.
            # 🔴 v1 OF THIS STATISTIC WAS REFUTED AT precision@25 = 0.0%, AND THE RANKING SAID WHY:
            # it was topped by `OT1-1609-P_1015` (fill 0.000) and `OT1-1609-P_0660` — boxes drawn
            # over BLANK PAPER, where the widest blank band is trivially the whole box. It was
            # measuring E23, a defect that already has its own grade, and calling it E13.
            # ⚠️ THE FIX IS STRUCTURAL, NOT A THRESHOLD ON DENSITY. A two-column wrap SPLITS ITS
            # INK: both flanks of the channel carry real mass. An empty box has mass on neither.
            # So the gutter only counts when each side holds a substantial share of the box's ink,
            # which is a statement about what a column IS rather than a number tuned until P4 passed.
            span = cols[ci[0]:ci[-1] + 1]
            colsum = sub.sum(axis=0)[ci[0]:ci[-1] + 1]
            tot = max(1, int(colsum.sum()))
            run = best = beg = 0
            for j, v in enumerate(span):
                if v:
                    run = 0
                else:
                    run += 1
                    if run > best:
                        lo, hi = j - run + 1, j + 1
                        if (colsum[:lo].sum() >= GUTTER_FLANK * tot
                                and colsum[hi:].sum() >= GUTTER_FLANK * tot):
                            best, beg = run, lo
            gutter.append(best / max(1, span.size))

    un = mask & ~claimed
    # Speckle removal, so a leaf's foxing cannot outrank a leaf's missing column.
    lab, n = ndimage.label(un)
    blob = 0.0
    if n:
        sizes = np.bincount(lab.ravel())[1:]
        floor = MIN_BLOB * h * w
        un = un & np.isin(lab, np.nonzero(sizes >= floor)[0] + 1)
        blob = float(sizes.max() / (h * w))
    return {"id": plate["id"], "total_ink": total,
            "unclaimed": float(un.sum() / total), "blob": blob, "dropped": float(dropped),
            "min_box_density": min(densities) if densities else None,
            "max_slack": max(slack) if slack else None,
            "max_gutter": max(gutter) if gutter else None,
            "n_boxes": len(plate["boxes"])}


def main(top: int) -> int:
    bundle = json.loads(BUNDLE.read_text())
    std = json.loads(STANDARD.read_text())["leaves"]
    plates = bundle["plates"]

    print("R16.7 — UNCLAIMED INK, the detection instrument")
    print(f"{len(plates)} leaves · ink < {VS.INK_LEVEL} · working width {WIDTH}px · "
          f"border components removed\n")

    rows = []
    for i, p in enumerate(plates):
        m = measure(p)
        if m is None:
            print(f"  🔴 NO IMAGE for {p['id']} — it cannot be measured and is NOT scored as clean")
            continue
        m["severity"] = std.get(p["id"], {}).get("severity", "")
        rows.append(m)
        if (i + 1) % 50 == 0:
            print(f"  … {i + 1}/{len(plates)}", flush=True)

    rows.sort(key=lambda r: -r["unclaimed"])
    rank = {r["id"]: i for i, r in enumerate(rows)}

    print(f"\nRANKED BY UNCLAIMED INK (top {top}):")
    print(f"  {'#':>3}  {'leaf':22s} {'unclaimed':>9} {'blob':>7} {'edge-drop':>9} {'n':>3}  eye")
    for i, r in enumerate(rows[:top]):
        print(f"  {i:>3}  {r['id']:22s} {r['unclaimed']:>8.1%} {r['blob']:>7.3f} "
              f"{r['dropped']:>8.1%} {r['n_boxes']:>3}  {r['severity']}")

    # ═══ P0 — DOES THE PREPROCESSING LEAVE ANYTHING TO MEASURE? ═══════════════════
    # 🔴 ASKED FIRST BECAUSE THE OTHER THREE ARE MEANINGLESS WITHOUT IT. A test on a leaf whose ink
    # was 84% deleted before the measurement is a test on the residue.
    bad = [r for r in rows if r["dropped"] > RELIABLE_DROP]
    print(f"\nP0 — IS THE MEASUREMENT SOUND? leaves losing >{RELIABLE_DROP:.0%} of their ink to "
          f"border removal: {len(bad)}/{len(rows)} ({len(bad)/len(rows):.0%})")
    for r in sorted(bad, key=lambda x: -x["dropped"])[:6]:
        print(f"     {r['id']:22s} {r['dropped']:>6.1%} removed   unclaimed {r['unclaimed']:>6.1%} "
              f"{r['severity']}")
    p0 = len(bad) / len(rows) <= 0.05
    print(f"     {'✅ PASS' if p0 else '🔴 FAIL'} — "
          f"{'border removal is taking the surround and leaving the type.' if p0 else
             'BORDER REMOVAL IS EATING TYPE. On a leaf cropped tight to its text block the type '
             'touches the frame and is deleted with the scanner surround. ⚠️ THIS IS AN ALERT ON '
             'THE APPROACH, NOT AN ACCEPTED GAP: the component rule needs to distinguish a page '
             'EDGE (thin, elongated, framing) from a text block that happens to reach the crop. '
             'Every number below inherits this and says so.'}")

    # ═══ P1 ═══════════════════════════════════════════════════════════════════════
    sev = sorted(k for k, v in std.items() if v["severity"] == "SEVERE")
    inside = [k for k in sev if rank.get(k, 10**6) < TOP_N]
    print(f"\nP1 — SEVERE SEPARATES. {len(sev)} eye-graded SEVERE leaves; how many in the top {TOP_N}?")
    for k in sev:
        r = rank.get(k)
        print(f"     {k:22s} rank {r if r is not None else '—':>4}  "
              f"unclaimed {next((x['unclaimed'] for x in rows if x['id'] == k), float('nan')):.1%}")
    p1 = len(inside) == len(sev)
    print(f"     {'✅' if p1 else '🔴'} {len(inside)}/{len(sev)} in the top {TOP_N} — "
          f"{'PASS' if p1 else 'REFUTED: the measure cannot see the corpus worst failure. REDESIGN.'}")
    # ⚠️ AND THE CAVEAT TRAVELS WITH THE RESULT, rather than living in a comment nobody re-reads.
    shaky = [k for k in sev
             if next((r["dropped"] for r in rows if r["id"] == k), 0.0) > RELIABLE_DROP]
    if shaky:
        print(f"     ⚠️ {len(shaky)} of the {len(sev)} PASS ON AN UNRELIABLE MEASUREMENT (P0): "
              f"{' '.join(shaky)}")
        print(f"     So P1's evidence is {len(sev) - len(shaky)} solid + {len(shaky)} unreliable, "
              f"NOT {len(sev)} solid. It is reported that way rather than banked as {len(sev)}/{len(sev)}.")

    # ═══ P2 ═══════════════════════════════════════════════════════════════════════
    dens = sorted(r["min_box_density"] for r in rows if r["min_box_density"] is not None)
    cut = dens[max(0, int(0.10 * len(dens)) - 1)] if dens else 0.0
    emp = sorted(k for k, v in std.items() if v["severity"] == "EMPTY")
    ok_e = [k for k in emp
            if (d := next((r["min_box_density"] for r in rows if r["id"] == k), None)) is not None
            and d <= cut]
    print(f"\nP2 — EMPTY INVERTS. lowest-decile box ink density = {cut:.4f}")
    for k in emp:
        d = next((r["min_box_density"] for r in rows if r["id"] == k), None)
        print(f"     {k:22s} emptiest box density {d:.4f}  {'✅' if d is not None and d <= cut else '🔴'}")
    p2 = len(ok_e) == len(emp)
    print(f"     {'✅' if p2 else '🔴'} {len(ok_e)}/{len(emp)} in the lowest decile — "
          f"{'PASS' if p2 else 'REFUTED'}")
    if not p2:
        # 🔴 THE REFUTATION IS DIAGNOSED, NOT TUNED AWAY. The two failing boxes read 0.131 and 0.082
        # at `INK_LEVEL` 0.55 and 0.022 and 0.018 at 0.25 — the marks inside them are GREY, not
        # black. The eye review says what they are in as many words: *"the only marks inside it are
        # verso show-through"*, *"no ink of this leaf inside it"* (E11, E23).
        # ⚠️ SO THE PROJECT'S INK TEST CANNOT TELL THIS LEAF'S INK FROM THE VERSO'S, and lowering
        # the threshold until P2 passes would be fitting a shared constant to one test of one
        # instrument. `VS.INK_LEVEL` was derived for LINE FINDING, where show-through is harmless
        # noise; asked to decide whether a REGION is empty, it is being used outside its derivation.
        # A show-through-aware ink test needs its own step and its own negative control.
        print("     🔴 DIAGNOSED, NOT TUNED: the marks in those boxes are verso SHOW-THROUGH — grey,")
        print("        not type. They fall below `INK_LEVEL` 0.55 and above 0.25. E11 says so by eye.")
        print("        ⚠️ `VS.INK_LEVEL` was derived for LINE FINDING, where show-through is harmless.")
        print("        Retuning it here would fit a shared constant to one test. FILED, NOT FIXED.")

    # ═══ P3 ═══════════════════════════════════════════════════════════════════════
    base = sum(1 for r in rows if r["severity"]) / len(rows)
    small_base = sum(1 for r in rows if r["severity"] == "SMALL") / len(rows)
    topk = rows[:TOP_N]
    p_small = sum(1 for r in topk if r["severity"] == "SMALL") / len(topk)
    print(f"\nP3 — SMALL DOES NOT SEPARATE (predicted to FAIL, in advance).")
    print(f"     base rate, any detection finding : {base:.1%}")
    print(f"     base rate, SMALL as worst grade  : {small_base:.1%}")
    print(f"     precision@{TOP_N} for SMALL        : {p_small:.1%}")
    p3 = p_small <= small_base + 0.15
    print(f"     {'✅' if p3 else '🔴'} "
          f"{'CONFIRMED — this is the SENSITIVITY FLOOR, and it is now measured rather than assumed.'
             if p3 else 'PREDICTION REFUTED — SMALL separates. The measure is reading something '
                        'other than ink mass and every reading above needs re-examining.'}")

    # ═══ P4 — OVER-BOXING, THE OTHER HALF ═══════════════════════════════════════
    # ⚠️ NOT PRE-REGISTERED EITHER, and for a better reason than P0: this half of the problem was
    # MISSING FROM THE INSTRUMENT until Sir pointed it out. It is a new prediction on an existing
    # standard, stated here before it was run, and it is marked as added-later because the SEVERE
    # and SMALL grades it is scored against were built while looking at the other half.
    gut = [r for r in rows if r.get("max_gutter") is not None]
    gut.sort(key=lambda r: -r["max_gutter"])
    slack_base = sum(1 for r in rows if r["severity"] == "SLACK") / len(rows)
    topg = gut[:TOP_N]
    p_sl = sum(1 for r in topg if r["severity"] == "SLACK") / max(1, len(topg))
    print(f"\nP4 — OVER-BOXING SEPARATES. ranked by widest BLANK GUTTER inside a box:")
    print(f"  {'#':>3}  {'leaf':22s} {'gutter':>7} {'slack':>7} {'fill':>7}  eye")
    for i, r in enumerate(topg[:12]):
        print(f"  {i:>3}  {r['id']:22s} {r['max_gutter']:>6.1%} {r['max_slack']:>6.1%} "
              f"{r['min_box_density']:>6.3f}  {r['severity']}")
    print(f"     base rate, SLACK as worst grade : {slack_base:.1%}")
    print(f"     precision@{TOP_N} for SLACK        : {p_sl:.1%}")
    p4 = p_sl > slack_base
    print(f"     {'✅ PASS' if p4 else '🔴 REFUTED'} — "
          f"{'a blank channel inside a box does find the swallowed and merged columns.'
             if p4 else 'the gutter statistic does not find the columns the eye found.'}")
    if not p4:
        # 🔴 REFUTED TWICE, AND THE SECOND TIME WITH A DIAGNOSIS FROM THE PROJECT'S OWN EVIDENCE.
        # v1 (0.0%) was confounded by boxes drawn over blank paper — the widest blank band in an
        # empty box is the whole box, so it measured E23 and called it E13. v2 added the structural
        # requirement that both flanks carry ink, which removed the confound and moved precision to
        # 8.0% against a 16.3% base rate: STILL BELOW CHANCE.
        #
        # ⚠️ THE MEASURE IS LOOKING FOR A CHASM WHERE THIS BOOK PRINTS A HAIRLINE. R12's archetype
        # B1 records the actual separation, measured: *"body line-ends x1<=1647, margin x0>=1673, a
        # REAL 26px gutter"* — 26 pixels against a measure of roughly 1,650, about 1.6% of the box's
        # width. A statistic that RANKS BY THE WIDEST channel therefore sorts every leaf with a
        # ragged margin above every leaf with a swallowed column.
        # 🔑 SO THE REDESIGN IS NOT A WIDER WINDOW OR A LOWER BAR: E5/E13 need a measure keyed to a
        # NARROW BUT PERSISTENT full-height channel — a projection profile with a minimum RUN
        # LENGTH down the box, not a maximum width across it. Filed; not attempted here, because a
        # third formulation invented against the same 208 leaves would be fitting, not measuring.
        print("     🔴 ALERT ON THE APPROACH, not an accepted gap. DIAGNOSIS: R12 measured this")
        print("     book's real body/margin separation at 26px on a ~1650px measure — 1.6%. A")
        print("     statistic ranking by the WIDEST blank channel sorts ragged margins above")
        print("     swallowed columns. E5/E13 need a NARROW-but-FULL-HEIGHT channel measure")
        print("     (projection profile, minimum run DOWN the box). Filed as R16.8(d), not")
        print("     attempted here — a third formulation against these same 208 leaves would be")
        print("     fitting rather than measuring.")
    print("     🔑 WHY THIS HALF EXISTS AT ALL: a single box drawn round the whole leaf scores")
    print("     ZERO unclaimed ink. P1 alone can be satisfied by a detector that has stopped")
    print("     detecting, so the two measures must be reported TOGETHER or neither means much.")

    OUT.write_text(json.dumps({"_doc": "R16.7 unclaimed-ink + over-boxing scores per leaf.",
                               "_pre_registered": {"P1": p1, "P2": p2, "P3": p3},
                               "_added_later": {"P0": p0, "P4": p4},
                               "width": WIDTH, "ink_level": VS.INK_LEVEL,
                               "leaves": rows}, indent=1, ensure_ascii=False))
    print(f"\nwritten -> {OUT.relative_to(_HERE.parent)}")

    # 🔴 THE EXIT CODE TRACKS THE BOOK, NOT THE INSTRUMENT. All three tests can pass while every
    # SEVERE leaf is still missing its body block — that would mean the measure WORKS, not that the
    # detector does. Passing here would be the instrument congratulating itself on its own accuracy.
    print(f"\n🔴 {len(sev)} leaves still have an unclaimed body block. The instrument now SEES them;")
    print("   nothing has yet been done about them. Exit 1 until that changes.")
    return 0 if (p0 and p1 and p2 and p3 and p4 and not sev) else 1


if __name__ == "__main__":
    n = TOP_N
    if "--top" in sys.argv:
        n = int(sys.argv[sys.argv.index("--top") + 1])
    raise SystemExit(main(max(n, TOP_N)))
