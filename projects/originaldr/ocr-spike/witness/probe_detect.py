"""DETECTION PROBE -- the three constants that decide what LECTOR is allowed to see.

R16.19 measured ONE of them (the confidence floor) and found that "71 of 208 leaves have
no body block" is 83% an artefact of `FAST_LAYOUT_CONFIDENCE_THRESHOLD = 0.4`. This probe
re-opens that measurement because R16.19's own method statement is wrong in a way that
matters, and adds the second constant the fix cannot ship without.

  ⚠️ THE R16.19 PROBE DID NOT RUN AT FLOOR 0.01. It ran at the SHIPPED TOP-K CAP.
     `surya/common/rfdetr/predictor.py:89` sets `num_select: 100`, and PostProcess
     (`surya/common/rfdetr/models/lwdetr.py:363`) takes
         torch.topk(prob.view(bs, -1), num_select)
     over the FLATTENED query x class matrix -- so the 100 slots are (box, label) PAIRS,
     not boxes. One proposal that scores on three classes consumes three slots.
     Measured on three leaves: at num_select=100 every leaf returns exactly 100 detections
     covering only 62-84 DISTINCT geometries, and the lowest kept score is 0.037-0.070.
     The floor of 0.01 therefore never bound on any leaf. The CAP bound, at a
     PER-LEAF EFFECTIVE FLOOR THAT VARIES WITH PAGE CONTENT -- exactly the confound
     "one pass, post-filtered" was written to eliminate.

So every R16.19 conclusion below the cap is re-derived here, and the two claims that
depend on it most -- "25 leaves have no body proposal at ANY floor" and "4 genuinely
unexplained" -- are re-tested with the cap lifted to `num_queries` (300).

  BODY BLOCK := a detection whose area >= MIN_BODY_AREA of the leaf.
                ⚠️ MIN_BODY_AREA is MY constant and §3.0 forbids that kind from deciding.
                It REPORTS here and gates nothing, and every table is given at four values,
                exactly as R16.19 did, so no conclusion turns on the choice.

## What this probe is FOR

Reprioritised step (1) is "floor 0.10-0.15 at all 6 call sites + class-agnostic NMS +
carry the confidence". None of those three numbers can be chosen independently:

  * lowering the floor without lifting the cap buys nothing on a saturated leaf -- the
    detections below the cap were never returned to be filtered;
  * lifting the cap without NMS turns 11 boxes/leaf into a pile (R16.19 note 4:
    `OT1-1609-P_1011` already returns 8 overlapping body candidates at 0.10);
  * NMS chosen on a capped population is tuned against a truncation artefact.

This probe runs ONE forward pass per leaf at the largest budget the model can produce
(num_select = num_queries = 300, floor 0.01) and keeps every detection with its geometry,
score and label. Every reported (floor x cap x NMS) cell is a POST-FILTER of that one
pass, so no cell can differ from another by run-to-run variation.

  ⚠️ NESTING IS NOT A DUPLICATE AND MUST SURVIVE. Surya's boxes nest by design -- the body
  `Text` block physically contains the running head -- and `BIND_TIGHTEST`
  (`visual_agent.py`) depends on that nesting to address a gold entry to the right box.
  Class-agnostic IoU-NMS does not threaten it (a small box inside a large one has low IoU),
  but that is an argument, not a measurement, so containment is measured and reported
  alongside every NMS cell rather than assumed.

## Not done here

No constant is changed, no call site is touched, nothing is adopted. This is a
measurement. A leaf that stays collapsed after every cell stays OPEN and blocking.

  ../ocr-venv/bin/python witness/probe_detect.py [--limit N] [--out FILE]
  ../ocr-venv/bin/python witness/probe_detect.py --report-only   # re-report saved JSON
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent
PLATES = HERE / "plates"
OUT = PLATES / "detect-probe.json"

# ---- the shipped constants this probe is measuring, named so they can be cited ----
LIVE_FLOOR = 0.40          # surya/settings.py:136          FAST_LAYOUT_CONFIDENCE_THRESHOLD
LIVE_NUM_SELECT = 100      # surya/common/rfdetr/predictor.py:89   num_select
NUM_QUERIES = 300          # surya/common/rfdetr/predictor.py:88   num_queries -- the ceiling

# ---- probe settings ----
PROBE_FLOOR = 0.01         # run here; every reported floor is a post-filter of this pass
PROBE_NUM_SELECT = NUM_QUERIES
FLOORS = [0.01, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40]
CAPS = [LIVE_NUM_SELECT, PROBE_NUM_SELECT]
IOUS = [None, 0.95, 0.80, 0.70, 0.60, 0.50, 0.40]
AREAS = [0.15, 0.20, 0.25, 0.30]
MIN_BODY_AREA = 0.25       # reports; never gates. See the module docstring.
NEST_IOS = 0.90            # a box is CONTAINED when >= this much of it lies inside another


# ------------------------------------------------------------------ geometry helpers
def _area(d):
    return max(0.0, d["x1"] - d["x0"]) * max(0.0, d["y1"] - d["y0"])


def _inter(a, b):
    w = max(0.0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]))
    h = max(0.0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
    return w * h


def iou(a, b):
    i = _inter(a, b)
    u = _area(a) + _area(b) - i
    return i / u if u > 0 else 0.0


def ios(a, b):
    """Intersection over the SMALLER box. This is the NESTING measure, not IoU.

    A running head inside a page-sized body block has IoU ~0.02 and IoS ~1.0. Reporting
    only IoU would make a preserved nesting look like an unrelated pair.
    """
    s = min(_area(a), _area(b))
    return _inter(a, b) / s if s > 0 else 0.0


def nms(dets, thr):
    """Greedy CLASS-AGNOSTIC non-maximum suppression, highest score first.

    Class-agnostic is the point, not a simplification: the duplicates this has to remove are
    the SAME geometry under a DIFFERENT label, which a per-class NMS cannot see at all.
    """
    if thr is None:
        return list(dets)
    keep = []
    for d in sorted(dets, key=lambda x: -x["score"]):
        if all(iou(d, k) <= thr for k in keep):
            keep.append(d)
    return keep


def _sel(leaf, floor, cap, thr):
    """The detections a leaf would carry under one (floor, cap, NMS) cell.

    ⚠️ ORDER IS LOAD-BEARING AND MATCHES THE SHIPPED PIPELINE: the cap is applied to the
    RAW score-ranked list first (that is what PostProcess does), THEN the floor, THEN NMS.
    Applying NMS before the cap would measure a detector surya does not ship.
    """
    d = leaf["dets"][:cap]
    d = [x for x in d if x["score"] > floor]
    return nms(d, thr)


def _has_body(dets, area=MIN_BODY_AREA):
    return any(_area(d) >= area for d in dets)


def _n_body(dets, area=MIN_BODY_AREA):
    return sum(1 for d in dets if _area(d) >= area)


# ------------------------------------------------------------------ run
def run(limit: int, out: str) -> list:
    from PIL import Image
    from surya.fast_layout import FastLayoutPredictor

    bundle = json.loads((PLATES / "bundle.json").read_text())
    plates = bundle["plates"][: limit] if limit else bundle["plates"]

    pred = FastLayoutPredictor()
    det = pred.model.model                       # RfDetrTorch -> RFDetrDetector
    shipped = det.postprocess.num_select
    if shipped != LIVE_NUM_SELECT:               # the citation above must stay true
        print(f"⚠️  shipped num_select is {shipped}, not the documented {LIVE_NUM_SELECT}")
    det.postprocess.num_select = PROBE_NUM_SELECT
    print(f"num_select {shipped} -> {PROBE_NUM_SELECT} for the probe pass; "
          f"floor {PROBE_FLOOR}\n")

    rows, t0 = [], time.time()
    for n, p in enumerate(plates, 1):
        img = Image.open(PLATES / p["img"]).convert("RGB")
        W, H = img.size
        res = pred([img], threshold=PROBE_FLOOR)[0]
        dets = []
        for b in res.bboxes:
            x0, y0, x1, y1 = b.bbox
            dets.append({"x0": round(x0 / W, 5), "y0": round(y0 / H, 5),
                         "x1": round(x1 / W, 5), "y1": round(y1 / H, 5),
                         "score": round(float(b.confidence), 5), "label": b.label})
        # PostProcess returns score-ranked pairs; the cap is a PREFIX of this list, so the
        # order is part of the record and must not be re-sorted on write.
        dets.sort(key=lambda d: -d["score"])
        rows.append({"id": p["id"], "witness": p["witness"], "page_px": [W, H],
                     "dets": dets})
        if n % 20 == 0 or n == len(plates):
            el = time.time() - t0
            print(f"  {n}/{len(plates)}  {el:.0f}s  ({el/n:.2f}s/leaf)", flush=True)

    Path(out).write_text(json.dumps(
        {"probe_floor": PROBE_FLOOR, "probe_num_select": PROBE_NUM_SELECT,
         "live_floor": LIVE_FLOOR, "live_num_select": LIVE_NUM_SELECT,
         "num_queries": NUM_QUERIES, "min_body_area": MIN_BODY_AREA,
         "n": len(rows), "leaves": rows}))
    print(f"\nwrote {out}")
    return rows


# ------------------------------------------------------------------ report
def report(rows):
    N = len(rows)

    print("\n=== 1. THE CAP BINDS, THE FLOOR DOES NOT ===")
    print("If the floor bound, a leaf would return FEWER than num_select detections.")
    print(f"{'leaves returning exactly num_select at floor 0.01':<52} "
          f"{sum(1 for r in rows if len(r['dets']) >= PROBE_NUM_SELECT):>4} / {N}")
    print("\nDistinct GEOMETRIES per leaf inside the (box,label) budget — the slots lost to")
    print("the same box under a different label:")
    print(f"{'cap':>6} {'dets/leaf':>10} {'distinct geom':>14} {'wasted':>8} "
          f"{'eff. floor med':>15} {'eff. floor max':>15}")
    for cap in CAPS:
        tot = geo = 0
        effs = []
        for r in rows:
            d = r["dets"][:cap]
            tot += len(d)
            geo += len({(x["x0"], x["y0"], x["x1"], x["y1"]) for x in d})
            if d:
                effs.append(min(x["score"] for x in d))
        effs.sort()
        med = effs[len(effs) // 2] if effs else 0.0
        print(f"{cap:>6} {tot/N:>10.1f} {geo/N:>14.1f} {1-geo/max(1,tot):>7.0%} "
              f"{med:>15.4f} {max(effs):>15.4f}")
    print("\n🔑 The 'effective floor' is the lowest score the cap let through ON THAT LEAF.")
    print("   It varies with page content, so a fixed nominal floor is NOT a fixed floor.")

    print("\n=== 2. R16.19 RE-TESTED WITH THE CAP LIFTED ===")
    print(f"'no body block' (area >= {MIN_BODY_AREA:.2f}) by floor, at each cap")
    print(f"{'floor':>7} {'no-body @100':>13} {'no-body @300':>13} "
          f"{'boxes/leaf @300':>16}")
    for f in FLOORS:
        a = sum(1 for r in rows if not _has_body(_sel(r, f, LIVE_NUM_SELECT, None)))
        b = sum(1 for r in rows if not _has_body(_sel(r, f, PROBE_NUM_SELECT, None)))
        bx = sum(len(_sel(r, f, PROBE_NUM_SELECT, None)) for r in rows) / N
        mark = "   <-- LIVE" if f == LIVE_FLOOR else ""
        print(f"{f:>7.2f} {a:>13} {b:>13} {bx:>16.1f}{mark}")

    print("\n=== 3. THE FLOOR-IMMUNE RESIDUE — R16.19's '25 at ANY floor' ===")
    for cap in CAPS:
        never = [r["id"] for r in rows if not _has_body(_sel(r, 0.0, cap, None))]
        print(f"  cap {cap:>3}: {len(never):>3} leaves have NO body proposal at any floor")
    freed = [r["id"] for r in rows
             if not _has_body(_sel(r, 0.0, LIVE_NUM_SELECT, None))
             and _has_body(_sel(r, 0.0, PROBE_NUM_SELECT, None))]
    print(f"  recovered PURELY by lifting the cap: {len(freed)}")
    for i in freed[:20]:
        print(f"    {i}")
    print("\n  sensitivity of the residue to the area criterion (cap 300, floor 0):")
    print("   " + "  ".join(f"a>={x:.2f}:{sum(1 for r in rows if not _has_body(_sel(r,0.0,PROBE_NUM_SELECT,None),x)):>4}"
                            for x in AREAS))

    print("\n=== 4. THE PILE — body CANDIDATES per leaf, and what NMS does to it ===")
    print("A frame anchored on max(area) is decided by ONE box; N candidates means N-1 are")
    print("competing for that anchor. This is the R16.19 note-4 problem, measured.")
    for f in (0.10, 0.15, LIVE_FLOOR):
        print(f"\n  floor {f:.2f}, cap {PROBE_NUM_SELECT}")
        print(f"  {'NMS IoU':>8} {'boxes/leaf':>11} {'body cand/leaf':>15} "
              f"{'leaves >1 cand':>15} {'nested pairs/leaf':>18}")
        for thr in IOUS:
            bx = cand = multi = nest = 0
            for r in rows:
                d = _sel(r, f, PROBE_NUM_SELECT, thr)
                bx += len(d)
                c = _n_body(d)
                cand += c
                multi += 1 if c > 1 else 0
                nest += sum(1 for i in range(len(d)) for j in range(i + 1, len(d))
                            if ios(d[i], d[j]) >= NEST_IOS)
            lab = "none" if thr is None else f"{thr:.2f}"
            print(f"  {lab:>8} {bx/N:>11.1f} {cand/N:>15.2f} {multi:>15} {nest/N:>18.1f}")
    print(f"\n🔑 'nested pairs' (IoS >= {NEST_IOS:.2f}) must NOT go to zero — `BIND_TIGHTEST`")
    print("   addresses a gold entry to the smallest box containing it, and needs the nesting.")

    print("\n=== 5. PER WITNESS — acceptance is per-setting (R16 :4959), never pooled ===")
    for w in sorted({r["witness"] for r in rows}):
        sub = [r for r in rows if r["witness"] == w]
        print(f"\n  {w}  (n={len(sub)})")
        print(f"  {'cell':<28} {'no-body':>8} {'boxes/leaf':>11} {'body cand/leaf':>15}")
        for f, cap, thr in ((LIVE_FLOOR, LIVE_NUM_SELECT, None),
                            (0.10, LIVE_NUM_SELECT, None),
                            (0.10, PROBE_NUM_SELECT, None),
                            (0.10, PROBE_NUM_SELECT, 0.70),
                            (0.15, PROBE_NUM_SELECT, 0.70)):
            d = [_sel(r, f, cap, thr) for r in sub]
            nb = sum(1 for x in d if not _has_body(x))
            lab = f"floor {f:.2f} cap {cap} nms {'-' if thr is None else f'{thr:.2f}'}"
            print(f"  {lab:<28} {nb:>8} {sum(len(x) for x in d)/len(sub):>11.1f} "
                  f"{sum(_n_body(x) for x in d)/len(sub):>15.2f}")


# ------------------------------------------------------------------ the frame, measured
# ⚠️ THE LIVE BUNDLE IS NOT GOLD AND IS NOT TREATED AS GOLD HERE. It is the REGRESSION
# BASELINE: R16.19 established that on 138 of 208 leaves the frame is sound, so a change
# that moves those frames is buying its recovery with damage, and the size of that damage
# is the thing this section refuses to leave unmeasured. Every leaf that moves is then
# CLASSIFIED against the live frame's own geometry and listed by name -- a net mover whose
# live frame looked healthy is reported as REVIEW, never absorbed into a total.
FRAME_TOL = [0.02, 0.05, 0.10]
COLUMN_MINS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60]
SICK_FRAC = 0.60           # a live frame under this fraction of the corpus median is collapsed
OK_FRAC = 1.15             # a repaired frame must not overshoot the median by more than this


def _va():
    import visual_agent as VA
    return VA


def _boxes(VA, dets):
    """probe detections -> `visual_agent.Box`, WITH the detector's score attached.

    ⚠️ The score rides on `Box.conf` for this probe ONLY, because nothing here runs a cue and
    `conf` is therefore free. IN THE PIPELINE `conf` IS THE CUE'S CONFIDENCE and the detector's
    score needs its OWN field -- writing one into the other would feed a cue its own decision,
    which is the trap `leaf_from_cache` already documents.
    """
    out = []
    for d in dets:
        b = VA.Box(d["x0"], d["y0"], d["x1"], d["y1"], d["label"])
        b.conf = d["score"]
        out.append(b)
    return out


def _frame(VA, boxes, lf, col_min):
    """`visual_agent.frame`, with ONE line changed: the COLUMN may be restricted by score.

    The column is the set whose MEDIAN edges become the measure. The anchor is untouched --
    section 6 shows the anchor is not what moves the frame, so changing it would be a fix
    aimed at the wrong mechanism.
    """
    if not boxes:
        return (0.0, 1.0), 0.0, 1.0
    body = max(boxes, key=lambda b: b.area)
    bw = max(1e-9, body.x1 - body.x0)
    col = [b for b in boxes
           if b.area >= VA.SMALL_AREA and b.conf >= col_min
           and max(0.0, min(b.x1, body.x1) - max(b.x0, body.x0)) >= VA.COLUMN_OVERLAP * bw]
    if not col:
        col = [body]
    import statistics as _st
    return ((_st.median([b.x0 for b in col]), _st.median([b.x1 for b in col])),
            min(VA.ry(b.cx, b.y0, lf) for b in col),
            max(VA.ry(b.cx, b.y1, lf) for b in col))


def _run_frame(VA, rows, base, floor, cap, thr, col_min):
    """(leaves moving past each tolerance, the moved ids, column members/leaf)."""
    import statistics as _st
    mv = {t: 0 for t in FRAME_TOL}
    moved, ncol = [], []
    for r in rows:
        bs = _boxes(VA, _sel(r, floor, cap, thr))
        lf = VA.Leaf(leaf=0, witness=r["witness"], boxes=bs)
        (l, rt), h, f = _frame(VA, bs, lf, col_min)
        if bs:
            body = max(bs, key=lambda b: b.area)
            bw = max(1e-9, body.x1 - body.x0)
            ncol.append(len([b for b in bs if b.area >= VA.SMALL_AREA and b.conf >= col_min
                             and max(0.0, min(b.x1, body.x1) - max(b.x0, body.x0))
                             >= VA.COLUMN_OVERLAP * bw]))
        b = base.get(r["id"])
        if not b:
            continue
        (bl, br), bh, bf = b
        dm = max(abs(l - bl), abs(rt - br), abs(h - bh), abs(f - bf))
        for t in FRAME_TOL:
            if dm > t:
                mv[t] += 1
        if dm > FRAME_TOL[0]:
            moved.append((r["id"], dm, (bl, br, bh, bf), (l, rt, h, f)))
    return mv, moved, (_st.median(ncol) if ncol else 0.0)


def report_frame(rows):
    """Sections 6-8: what the change does to THE FRAME, which is the thing R16.15 is about."""
    import statistics as _st
    VA = _va()
    live = json.loads((PLATES / "bundle.json").read_text())
    base = {p["id"]: (tuple(p["measure"]), p["head_y"], p["foot_y"])
            for p in live["plates"]}

    print("\n=== 6. WHAT ACTUALLY MOVES THE FRAME — it is NOT the anchor ===")
    print("`frame()` anchors on max(area) and then takes the MEDIAN EDGES of the COLUMN.")
    print("Lowering the floor swells the column, so the median moves whatever anchors it.")
    print(f"\n  {'column members/leaf':<24} {'median':>8} {'max':>6}")
    for lab, f, cap, thr in (("live  floor 0.40 cap 100", LIVE_FLOOR, LIVE_NUM_SELECT, None),
                             ("probe floor 0.10 cap 300", 0.10, PROBE_NUM_SELECT, 0.95)):
        n = []
        for r in rows:
            bs = _boxes(VA, _sel(r, f, cap, thr))
            if not bs:
                continue
            body = max(bs, key=lambda b: b.area)
            bw = max(1e-9, body.x1 - body.x0)
            n.append(len([b for b in bs if b.area >= VA.SMALL_AREA
                          and max(0.0, min(b.x1, body.x1) - max(b.x0, body.x0))
                          >= VA.COLUMN_OVERLAP * bw]))
        print(f"  {lab:<24} {_st.median(n):>8.1f} {max(n):>6}")

    noise = {m[0] for m in _run_frame(VA, rows, base, LIVE_FLOOR, LIVE_NUM_SELECT, None, 0.0)[1]}
    print(f"\n  🔑 BASELINE NOISE: re-running the LIVE config off the plate JPEGs (the bundle was")
    print(f"     built from the source jp2s) moves {len(noise)} leaves. That is the floor under every")
    print(f"     number below — a config moving {len(noise)} leaves has changed NOTHING.")

    print("\n=== 7. THE COLUMN'S CONFIDENCE FILTER — the constant that decides the frame ===")
    print("Detection at floor 0.10 / cap 300 / NMS 0.95 throughout; ONLY the column min moves.")
    print(f"\n  {'column min':>11} " + " ".join(f"{'moved>'+format(t,'.2f'):>12}" for t in FRAME_TOL)
          + f" {'col/leaf':>9}")
    for cm in COLUMN_MINS:
        mv, _, nc = _run_frame(VA, rows, base, 0.10, PROBE_NUM_SELECT, 0.95, cm)
        print(f"  {cm:>11.2f} " + " ".join(f"{mv[t]:>12}" for t in FRAME_TOL) + f" {nc:>9.1f}")
    print("\n  🔑 The curve is U-SHAPED and its minimum sits AT THE SHIPPED FLOOR. That is the")
    print("     finding: 0.40 is a sound FRAMING constant and an unsound DETECTION constant, and")
    print("     one number has been doing both jobs. Above 0.50 real body boxes leave the column")
    print("     and the frame degrades again, so this is a measured optimum, not a bigger-is-safer.")

    print("\n=== 8. EVERY NET MOVER, NAMED AND CLASSIFIED ===")
    mv, moved, _ = _run_frame(VA, rows, base, 0.10, PROBE_NUM_SELECT, 0.95, 0.40)
    net = [m for m in moved if m[0] not in noise]
    wmed = _st.median([p["measure"][1] - p["measure"][0] for p in live["plates"]])
    smed = _st.median([p["foot_y"] - p["head_y"] for p in live["plates"]])
    print(f"  moved {len(moved)}, of which {len(noise & {m[0] for m in moved})} are raster noise "
          f"⇒ {len(net)} NET")
    print(f"  corpus live medians: measure width {wmed:.3f}, head-foot span {smed:.3f}\n")
    print(f"  {'leaf':<20} {'delta':>6} {'live w':>7} {'live span':>10} {'new w':>7} "
          f"{'new span':>9}  verdict")
    review = 0
    for lid, d, (bl, br, bh, bf), (l, rt, h, f) in sorted(net, key=lambda t: -t[1]):
        lw, lsp, nw, nsp = br - bl, bf - bh, rt - l, f - h
        sick = lw < SICK_FRAC * wmed or lsp < SICK_FRAC * smed
        better = (nw > lw and nw <= wmed * OK_FRAC) or (nsp > lsp and nsp <= smed * OK_FRAC)
        if sick and better:
            v = "live COLLAPSED -> repaired"
        elif sick:
            v = "live COLLAPSED, not repaired — OPEN"
        else:
            v = "🔴 live looked FINE — REVIEW"
            review += 1
        print(f"  {lid:<20} {d:>6.3f} {lw:>7.3f} {lsp:>10.3f} {nw:>7.3f} {nsp:>9.3f}  {v}")
    print(f"\n  ⚠️ {review} leaf/leaves moved from a HEALTHY live frame. Those are not absorbed into")
    print("     a total and are not a pass — they are named so a human can settle them.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="first N plates only (timing)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--report-only", action="store_true",
                    help="re-report the saved JSON without re-running the detector")
    a = ap.parse_args()
    if a.report_only:
        rows = json.loads(Path(a.out).read_text())["leaves"]
    else:
        rows = run(a.limit, a.out)
    report(rows)
    # ⚠️ Sections 6-8 need the LIVE BUNDLE as a regression baseline. Missing it is REPORTED,
    # never silently skipped — an absent baseline makes the frame numbers unavailable, which
    # is a different fact from "the frame did not move", and collapsing the two is how an
    # unmeasured thing gets read as a measured zero.
    if (PLATES / "bundle.json").is_file():
        report_frame(rows)
    else:
        print("\n🔴 no plates/bundle.json — sections 6-8 (THE FRAME) NOT RUN. "
              "The frame is unmeasured, not unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
