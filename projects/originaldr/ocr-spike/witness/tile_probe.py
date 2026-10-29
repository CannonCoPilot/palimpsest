#!/usr/bin/env python3
"""R16.10 — DOES DETECTING AT NATIVE SCALE RECOVER THE SMALL OBJECTS?

R16.10 established that the detector never sees this book. `surya_layout2/config.json` carries
`"resolution": 448` and `common/rfdetr/predictor.py` does `TF.resize(t, (448, 448))`, so a
3092x4367 leaf is squashed **6.9x horizontally and 9.7x vertically, ANISOTROPICALLY**. A 40px line
of this book's type arrives at ~4px. A catchword, a signature or a page number arrives at 1-2px.

R14.15 named a "detection floor" and read it as a limit of the MODEL. If it is instead a limit of
the PREPROCESSING, then it is removable without training anything, and the gold set does not have
to be built around it. That is a large enough difference to test before drawing another box.

⚠️ THIS SCRIPT TRAINS NOTHING AND TOUCHES NO GOLD. It re-runs the SAME checkpoint on the SAME
leaves through a different input path, and scores both with `score_detection.measure()` — the same
instrument, the same image, only the boxes differ.

--------------------------------------------------------------------------------------------
PRE-REGISTERED, BEFORE THE FIRST RUN. Written down here so a result cannot be reinterpreted into
a pass afterwards; the failures below are recorded as failures, exactly as P0/P2/P4 were.

  P5  SMALL RECOVERY. On leaves the detection standard grades SMALL (E3 catchword / E9 note /
      E27 signature), tiled detection reduces unclaimed ink by a median of >= 25% RELATIVE to
      the same leaf's whole-page score.
      ⚠️ If P5 fails, the 448px finding does NOT explain the detection families and R14.15's
      floor stands as a model limit after all.

  P6  THE FALSIFIER, AND IT PREDICTS A NULL. On leaves graded SEVERE (E26, the BODY BLOCK
      itself unclaimed), the same reduction is < 25%. A body block is the largest object on the
      page and survives the squash; if tiling "fixes" it too, then the statistic is responding
      to box COUNT rather than to object SIZE and P5's pass means nothing.
      ⚠️ A test whose every outcome confirms the hypothesis is not a test. This is the leg that
      can break it.

  P7  THE OVER-BOXING GUARD (Sir, 2026-08-29). Unclaimed ink is HALF the problem and the half
      that is trivially gameable: more boxes always claims more ink. So the win is void unless
      the other half holds — median `max_slack` must not rise by more than 0.05 absolute.
      ⚠️ Twelve tiles produce more boxes BY CONSTRUCTION. Without this leg, P5 is guaranteed to
      pass and measures nothing.

🔴 GROUPING DEFECT, FOUND AND CORRECTED AFTER THE FIRST FULL RUN — RECORDED, NOT QUIETLY FIXED.
   Run 1 built these groups with a REGEX over the E-codes in `eye-findings.json`. That returns
   ZERO for E24-E28, and `eye-findings.json`'s own `_provenance` says why: *"E24-E28 were minted
   from the readers' verbatim strings AFTER they worked, so NO finding string carries those codes
   and a regex over the codes counts them as ZERO."* So run 1's SMALL group was E3/E9 only and its
   SEVERE group was EMPTY — **P6 did not fail, it never ran**, and a leg that cannot run must
   never be reported as a leg that passed or failed.
   ⚠️ The project already owned the correct enumeration: `build_detection_standard.py` addresses
   E25/E26/E27 by the readers' own phrasing and grades every leaf. The rule is now RUN rather than
   REIMPLEMENTED. **The bars are untouched** — only the addressing changed, and run 1's numbers
   are kept below so the correction cannot launder a result:
       run 1 (mis-addressed): P5 +11.4% on 73 leaves · P6 n/a on 0 leaves · P7 -0.035


Reported per witness as well as pooled, because 34% of the corpus sits in settings with no gold
and a single mean would hide a setting that got worse.
--------------------------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import statistics as stats
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import witnesses as W                     # noqa: E402
import score_detection as SD              # noqa: E402
import visual_agent as VA                 # noqa: E402

PLATES = _HERE / "plates"
BUNDLE = PLATES / "bundle.json"
STANDARD = PLATES / "detection-standard.json"
OUT = PLATES / "tile-probe.json"
# The merged tiled boxes, cached per leaf and flushed as they are produced. ⚠️ NOT an optimisation:
# run 1 computed 208 leaves correctly and then died in `json.dumps`, losing every forward pass to a
# formatting bug. Detection is the expensive half and adjudication is the half that gets revised, so
# they must not share a failure. `--reuse` re-adjudicates from this file without touching the model.
BOXES = PLATES / "tile-probe-boxes.json"

# ---------------------------------------------------------------- tiling constants
# 3x4 over a 2:3 leaf gives tiles of ~1030x1091 — very nearly SQUARE, so the anisotropy of the
# 448x448 resize collapses along with the scale factor. Reduction falls 6.9x/9.7x -> ~2.3x/2.4x.
# ⚠️ Chosen from the leaf's aspect ratio, not tuned against the score.
COLS, ROWS = 3, 4
# Tiles overlap so an object lying on a seam is seen whole by at least one neighbour.
OVERLAP = 0.15
# NMS: the same object seen by two tiles.
IOU_SUPPRESS = 0.50
CONTAIN_SUPPRESS = 0.80
# SEAM STITCH: an object genuinely cut in half by a seam appears as two fragments meeting AT the
# seam. ⚠️ STITCHING IS RESTRICTED TO PAIRS THAT STRADDLE A SEAM LINE, deliberately. An
# unrestricted "merge adjacent same-label boxes" rule would re-create E13 — multi-column matter
# taken as one block — and would do it in the direction that flatters the score. Repairing an
# artefact this script itself introduced is a different act from merging what the book set apart.
SEAM_BAND = 0.010          # how close to the seam the shared edge must fall, page fraction
SEAM_GAP = 0.008           # how far apart the two fragments may be across the seam
SEAM_ALIGN = 0.60          # overlap along the other axis, share of the smaller fragment

SMALL_GRADE = "SMALL"       # E3 catchword / E9 note / E27 signature — the objects the squash eats
BODY_GRADE = "SEVERE"       # E26, the body block itself unclaimed — the object it cannot eat
P5_BAR = 0.25              # pre-registered relative reduction
P7_BAR = 0.05              # pre-registered absolute slack rise


# ---------------------------------------------------------------- geometry
def _iou(a: dict, b: dict) -> float:
    ix = max(0.0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]))
    iy = max(0.0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    aa = (a["x1"] - a["x0"]) * (a["y1"] - a["y0"])
    bb = (b["x1"] - b["x0"]) * (b["y1"] - b["y0"])
    return inter / max(1e-12, aa + bb - inter)


def _contained(a: dict, b: dict) -> float:
    """Share of `a` lying inside `b`."""
    ix = max(0.0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]))
    iy = max(0.0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
    aa = max(1e-12, (a["x1"] - a["x0"]) * (a["y1"] - a["y0"]))
    return ix * iy / aa


def detect_tiled(im, pred) -> list[dict]:
    """Run the SAME predictor over overlapping native-scale tiles and merge back to page coords."""
    Wp, Hp = im.size
    tw, th = Wp / COLS, Hp / ROWS
    ox, oy = tw * OVERLAP, th * OVERLAP
    crops, origins = [], []
    xs = [c * tw for c in range(COLS)]
    ys = [r * th for r in range(ROWS)]
    for x in xs:
        for y in ys:
            x0, y0 = max(0, x - ox), max(0, y - oy)
            x1, y1 = min(Wp, x + tw + ox), min(Hp, y + th + oy)
            crops.append(im.crop((int(x0), int(y0), int(x1), int(y1))))
            origins.append((x0, y0))
    raw = []
    for res, (ox0, oy0) in zip(pred(crops), origins):
        for b in res.bboxes:
            x0, y0, x1, y1 = b.bbox
            raw.append({"x0": (x0 + ox0) / Wp, "y0": (y0 + oy0) / Hp,
                        "x1": (x1 + ox0) / Wp, "y1": (y1 + oy0) / Hp,
                        "surya": b.label, "conf": float(getattr(b, "confidence", 0.0) or 0.0)})

    # --- NMS, highest confidence first
    raw.sort(key=lambda d: -d["conf"])
    keep: list[dict] = []
    for b in raw:
        if any(_iou(b, k) >= IOU_SUPPRESS or _contained(b, k) >= CONTAIN_SUPPRESS for k in keep):
            continue
        keep.append(b)

    # --- seam stitch, to a fixpoint
    seam_x = [x / Wp for x in xs[1:]]
    seam_y = [y / Hp for y in ys[1:]]

    def _straddles(a: dict, b: dict) -> bool:
        # vertical seam: a is left of b, their facing edges both sit on the same seam line
        for s in seam_x:
            if (abs(a["x1"] - s) <= SEAM_BAND and abs(b["x0"] - s) <= SEAM_BAND
                    and b["x0"] - a["x1"] <= SEAM_GAP):
                ov = max(0.0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
                if ov >= SEAM_ALIGN * min(a["y1"] - a["y0"], b["y1"] - b["y0"]):
                    return True
        for s in seam_y:
            if (abs(a["y1"] - s) <= SEAM_BAND and abs(b["y0"] - s) <= SEAM_BAND
                    and b["y0"] - a["y1"] <= SEAM_GAP):
                ov = max(0.0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]))
                if ov >= SEAM_ALIGN * min(a["x1"] - a["x0"], b["x1"] - b["x0"]):
                    return True
        return False

    changed = True
    while changed:
        changed = False
        for i in range(len(keep)):
            for j in range(len(keep)):
                if i == j:
                    continue
                a, b = keep[i], keep[j]
                if a["surya"] != b["surya"]:
                    continue
                if _straddles(a, b) or _straddles(b, a):
                    merged = {"x0": min(a["x0"], b["x0"]), "y0": min(a["y0"], b["y0"]),
                              "x1": max(a["x1"], b["x1"]), "y1": max(a["y1"], b["y1"]),
                              "surya": a["surya"], "conf": max(a["conf"], b["conf"])}
                    keep = [k for n, k in enumerate(keep) if n not in (i, j)] + [merged]
                    changed = True
                    break
            if changed:
                break
    return keep


# ---------------------------------------------------------------- eye-review families
def _families() -> dict[str, set[str]]:
    """Which detection GRADES the standard records for each leaf.

    ⚠️ READ FROM `detection-standard.json`, NOT parsed out of the finding strings. See the
    grouping-defect note in the module docstring: E24-E28 postdate the readers, so no finding
    string carries them and a regex silently returns an empty group rather than an error.
    """
    doc = json.loads(STANDARD.read_text())["leaves"]
    return {pid: set(v.get("grades", ())) for pid, v in doc.items()}


def _rel(base: float, tiled: float) -> float | None:
    """Relative reduction in unclaimed ink. None when the baseline has nothing to reduce."""
    if base <= 1e-9:
        return None
    return (base - tiled) / base


def main(limit: int | None, reuse: bool) -> int:
    print(__doc__)
    from PIL import Image

    bundle = json.loads(BUNDLE.read_text())
    fam = _families()
    plates = bundle["plates"][:limit] if limit else bundle["plates"]
    cache: dict[str, list] = {}
    if reuse and BOXES.is_file():
        cache = json.loads(BOXES.read_text())["boxes"]
        print(f"  ♻️  reusing {len(cache)} cached tiled detections — THE MODEL IS NOT RUN.")
    pred = None
    paths: dict[str, list] = {}
    rows, failed = [], []

    for n, p in enumerate(plates, 1):
        wid, i = p["witness"], p["leaf"]
        if p["id"] in cache:
            tiled = cache[p["id"]]
        else:
            if pred is None:
                from surya.fast_layout import FastLayoutPredictor
                pred = FastLayoutPredictor()
            if wid not in paths:
                vol, sig = [k for k in W.WITNESSES if W.wid(*k) == wid][0]
                paths[wid] = W.leaves(vol, sig)
            try:
                im = Image.open(str(paths[wid][i])).convert("RGB")
            except Exception as e:                                   # noqa: BLE001
                # ⚠️ REPORTED, NEVER SKIPPED — a dropped leaf shrinks the comparison without
                # changing any number that would reveal it.
                failed.append({"id": p["id"], "why": f"{type(e).__name__}: {e}"})
                print(f"  🔴 {p['id']}: {type(e).__name__}: {e}", flush=True)
                continue
            tiled = detect_tiled(im, pred)
            im.close()
            cache[p["id"]] = tiled
            BOXES.write_text(json.dumps({"_doc": "R16.10 merged tiled detections, per leaf.",
                                         "boxes": cache}))
        base_m = SD.measure(p)
        tile_m = SD.measure({**p, "boxes": tiled})
        if base_m is None or tile_m is None:
            failed.append({"id": p["id"], "why": "plate image missing"})
            continue
        small_base = sum(1 for b in p["boxes"]
                         if (b["x1"] - b["x0"]) * (b["y1"] - b["y0"]) < VA.SMALL_AREA)
        small_tile = sum(1 for b in tiled
                         if (b["x1"] - b["x0"]) * (b["y1"] - b["y0"]) < VA.SMALL_AREA)
        rows.append({
            "id": p["id"], "witness": wid, "codes": sorted(fam.get(p["id"], ())),
            "dropped": base_m["dropped"],
            "base_unclaimed": base_m["unclaimed"], "tile_unclaimed": tile_m["unclaimed"],
            "rel": _rel(base_m["unclaimed"], tile_m["unclaimed"]),
            "base_slack": base_m["max_slack"], "tile_slack": tile_m["max_slack"],
            "base_boxes": len(p["boxes"]), "tile_boxes": len(tiled),
            "base_small": small_base, "tile_small": small_tile,
        })
        print(f"  {n}/{len(plates)} {p['id']}: unclaimed "
              f"{base_m['unclaimed']:.3f} -> {tile_m['unclaimed']:.3f}  "
              f"boxes {len(p['boxes'])} -> {len(tiled)}", flush=True)

    # ---------------------------------------------------------------- adjudication
    # ⚠️ P0's finding carries over: a leaf that lost more than RELIABLE_DROP of its ink to border
    # removal is not measured, it is mangled. Those leaves are reported and EXCLUDED from the
    # medians, not quietly averaged in.
    ok = [r for r in rows if r["dropped"] <= SD.RELIABLE_DROP and r["rel"] is not None]
    mangled = [r for r in rows if r["dropped"] > SD.RELIABLE_DROP]

    small = [r for r in ok if SMALL_GRADE in r["codes"]]
    body = [r for r in ok if BODY_GRADE in r["codes"]]
    other = [r for r in ok if r not in small and r not in body]
    # ⚠️ A GROUP THIS SMALL IS DECLARED, NOT HIDDEN. The standard grades only 7 leaves SEVERE
    # corpus-wide, and border exclusion can only shrink that. P6 is the falsifying leg, so its
    # power matters more than its verdict: a null over a handful of leaves is weak evidence
    # AGAINST tiling fixing the body block, and it is reported as weak rather than as clean.
    MIN_POWER = 5

    def med(xs):
        return stats.median(xs) if xs else None

    def f(v, spec=".4f"):
        """⚠️ AN ABSENT NUMBER PRINTS AS `n/a`, NEVER AS 0. An empty group and a group that
        measured zero are different states, and a format string is not the place to merge them."""
        return "n/a" if v is None else format(v, spec)

    p5 = med([r["rel"] for r in small])
    p6 = med([r["rel"] for r in body])
    slack_delta = med([(r["tile_slack"] or 0.0) - (r["base_slack"] or 0.0) for r in ok])
    # ⚠️ THREE STATES, NOT TWO: PASS · FAIL · UNEVALUABLE. An empty or underpowered group is not
    # a failed prediction — it is a prediction that was never put at risk, and collapsing the two
    # is how run 1 reported "P6 🔴 FAIL" for a leg that had zero leaves in it.
    def verdict(value, ok_, n, floor=1):
        if value is None or n < floor:
            return "UNEVALUABLE"
        return "PASS" if ok_ else "FAIL"

    v5 = verdict(p5, p5 is not None and p5 >= P5_BAR, len(small))
    v6 = verdict(p6, p6 is not None and p6 < P5_BAR, len(body), MIN_POWER)
    v7 = verdict(slack_delta, slack_delta is not None and slack_delta <= P7_BAR, len(ok))
    p5_pass, p6_pass, p7_pass = v5 == "PASS", v6 == "PASS", v7 == "PASS"
    mark = {"PASS": "✅ PASS", "FAIL": "🔴 FAIL", "UNEVALUABLE": "⚠️ UNEVALUABLE"}

    print("\n" + "=" * 92)
    print(f"MEASURED {len(rows)} leaves; {len(mangled)} excluded as border-mangled "
          f"(>{SD.RELIABLE_DROP:.0%} ink lost); {len(ok)} adjudicated.")
    print(f"  groups: SMALL={SMALL_GRADE}(E3/E9/E27) {len(small)} · BODY={BODY_GRADE}(E26) {len(body)} · other {len(other)}")
    print(f"\n  median unclaimed {f(med([r['base_unclaimed'] for r in ok]))} -> "
          f"{f(med([r['tile_unclaimed'] for r in ok]))}")
    print(f"  median slack     {f(med([r['base_slack'] for r in ok if r['base_slack'] is not None]))}"
          f" -> {f(med([r['tile_slack'] for r in ok if r['tile_slack'] is not None]))}")
    print(f"  median boxes {f(med([r['base_boxes'] for r in ok]), '.1f')} -> "
          f"{f(med([r['tile_boxes'] for r in ok]), '.1f')}   "
          f"small boxes {f(med([r['base_small'] for r in ok]), '.1f')} -> "
          f"{f(med([r['tile_small'] for r in ok]), '.1f')}")
    # ⚠️ THE EXCLUDED LEAVES ARE PRINTED, NOT DROPPED. Border mangling is P0's open defect and it
    # hits BOTH ARMS IDENTICALLY — same image, same mask — so the paired change is still readable
    # even where the absolute score is not. Reported as a SECONDARY line so it cannot be mistaken
    # for the adjudicated result, and so a large excluded group cannot hide.
    if mangled:
        mrel = [x for x in (_rel(r["base_unclaimed"], r["tile_unclaimed"]) for r in mangled)
                if x is not None]
        print(f"\n  SECONDARY, NOT ADJUDICATED — {len(mangled)} border-mangled leaves: "
              f"median rel reduction {f(med(mrel), '+.1%')}")
    print(f"\n  P5 SMALL recovery   n={len(small):3d}  median rel reduction "
          f"{f(p5, '+.1%')} vs bar {P5_BAR:.0%}   {mark[v5]}")
    print(f"  P6 BODY null        n={len(body):3d}  median rel reduction "
          f"{f(p6, '+.1%')} must stay < {P5_BAR:.0%}   {mark[v6]}"
          + ("" if len(body) >= MIN_POWER else f"  (needs n>={MIN_POWER} to put the leg at risk)"))
    print(f"  P7 over-box guard   n={len(ok):3d}  median slack change "
          f"{f(slack_delta, '+.3f')} vs bar +{P7_BAR:.2f}   {mark[v7]}")

    print("\n  PER SETTING — never one mean; a third of the corpus sits in settings with no gold.")
    for wid in sorted({r["witness"] for r in ok}):
        g = [r for r in ok if r["witness"] == wid]
        print(f"    {wid:14s} n={len(g):3d}  unclaimed {f(med([r['base_unclaimed'] for r in g]))}"
              f" -> {f(med([r['tile_unclaimed'] for r in g]))}"
              f"   boxes {f(med([r['base_boxes'] for r in g]), '.1f')}"
              f" -> {f(med([r['tile_boxes'] for r in g]), '.1f')}")

    if not (p5_pass and p6_pass and p7_pass):
        print("\n  🔴 ALERT ON THE APPROACH, NOT AN ACCEPTED GAP. A leg that failed above is a")
        print("     statement about the EXPERIMENT'S HYPOTHESIS, and the leaves it concerns stay")
        print("     OPEN. Nothing here is licensed to be recorded as a resolved detection family.")

    OUT.write_text(json.dumps({
        "_doc": "R16.10 tile probe. Same checkpoint, same leaves, native-scale tiles. "
                "Pre-registration in tile_probe.py's module docstring.",
        "tiling": {"cols": COLS, "rows": ROWS, "overlap": OVERLAP,
                   "iou_suppress": IOU_SUPPRESS, "contain_suppress": CONTAIN_SUPPRESS,
                   "seam_band": SEAM_BAND, "seam_gap": SEAM_GAP, "seam_align": SEAM_ALIGN},
        "bars": {"P5": P5_BAR, "P6": P5_BAR, "P7": P7_BAR},
        # ⚠️ `float()`/`str()` are not cosmetic: `stats.median` over numpy inputs returns
        # `np.float64`, whose comparisons yield `np.bool_`, which `json.dumps` refuses. Run 1
        # computed every number correctly and then died writing the file.
        "verdict": {"P5": v5, "P6": v6, "P7": v7,
                    "n": {"small": len(small), "body": len(body), "adjudicated": len(ok)},
                    "p5_median": None if p5 is None else float(p5),
                    "p6_median": None if p6 is None else float(p6),
                    "slack_delta": None if slack_delta is None else float(slack_delta)},
        "excluded_border_mangled": [r["id"] for r in mangled],
        "failed": failed,
        "leaves": rows,
    }, indent=2, default=float))
    print(f"\n  → {OUT.relative_to(_HERE)}")
    return 0 if (p5_pass and p6_pass and p7_pass) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="first N plates only (smoke test)")
    ap.add_argument("--reuse", action="store_true",
                    help="re-adjudicate from cached tiled detections; does not run the model")
    a = ap.parse_args()
    raise SystemExit(main(a.limit, a.reuse))
