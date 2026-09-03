"""THRESHOLD PROBE -- is "71/208 leaves have no body block" a defect or an artefact?

Runs the layout detector ONCE per leaf at a very low floor and keeps every detection
with its score, then re-derives, in post, what the leaf would look like at any floor.
One forward pass answers every threshold.

The question, stated so it can be refuted: Root Cause 1 (Masterplan 3.0, R16.15) says
frame() anchors on a marginal column because no body block exists on 71 of 208 leaves.
If the body block IS detected and then deleted by surya/settings.py:136
FAST_LAYOUT_CONFIDENCE_THRESHOLD = 0.4, then Root Cause 1 is downstream of the floor
and the demotion work aimed at it is aimed at an artefact.

  BODY BLOCK := a detection whose area >= MIN_BODY_AREA of the leaf.
                0.25 is the criterion already used for "clean leaf" in the 2026-09-01
                review; reported at 0.15/0.20/0.25/0.30 so the answer does not turn on it.

Reports per leaf and per witness: n boxes, largest-box area, and whether a body block
exists, at each floor. No adoption, no code change -- a measurement only.

  ../ocr-venv/bin/python witness/probe_threshold.py [--limit N] [--out FILE]
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image

HERE = Path(__file__).resolve().parent
PLATES = HERE / "plates"
PROBE_FLOOR = 0.01          # run at this; every reported floor is a post-filter
FLOORS = [0.01, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40]
LIVE = 0.40                 # what the project runs today
AREAS = [0.15, 0.20, 0.25, 0.30]
MIN_BODY_AREA = 0.25


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="first N plates only (timing)")
    ap.add_argument("--out", default=str(PLATES / "threshold-probe.json"))
    a = ap.parse_args()

    bundle = json.loads((PLATES / "bundle.json").read_text())
    plates = bundle["plates"]
    if a.limit:
        plates = plates[: a.limit]

    from surya.fast_layout import FastLayoutPredictor
    pred = FastLayoutPredictor()

    rows, t0 = [], time.time()
    for n, p in enumerate(plates, 1):
        img = Image.open(PLATES / p["img"]).convert("RGB")
        W, H = img.size
        res = pred([img], threshold=PROBE_FLOOR)[0]
        dets = []
        for b in res.bboxes:
            x0, y0, x1, y1 = b.bbox
            dets.append({
                "area": max(0.0, (x1 - x0) / W) * max(0.0, (y1 - y0) / H),
                "score": float(getattr(b, "confidence", None) or 0.0),
                "label": b.label,
            })
        rows.append({"id": p["id"], "witness": p["witness"], "dets": dets})
        if n % 20 == 0 or n == len(plates):
            el = time.time() - t0
            print(f"  {n}/{len(plates)}  {el:.0f}s  ({el/n:.2f}s/leaf)", flush=True)

    out = {"probe_floor": PROBE_FLOOR, "live_floor": LIVE,
           "min_body_area": MIN_BODY_AREA, "n": len(rows), "leaves": rows}
    Path(a.out).write_text(json.dumps(out))
    print(f"\nwrote {a.out}")
    report(rows)
    return 0


def report(rows):
    print("\n=== BODY BLOCK PRESENT (area >= %.2f), by floor ===" % MIN_BODY_AREA)
    print(f"{'floor':>7} {'has body':>9} {'no body':>8} {'boxes/leaf':>11}")
    for f in FLOORS:
        have = boxes = 0
        for r in rows:
            keep = [d for d in r["dets"] if d["score"] > f]
            boxes += len(keep)
            if any(d["area"] >= MIN_BODY_AREA for d in keep):
                have += 1
        mark = "   <-- LIVE" if f == LIVE else ""
        print(f"{f:>7.2f} {have:>9} {len(rows)-have:>8} {boxes/max(1,len(rows)):>11.1f}{mark}")

    print("\n=== SENSITIVITY: 'no body block' count vs the area criterion ===")
    hdr = "  ".join(f"a>={x:.2f}" for x in AREAS)
    print(f"{'floor':>7}  {hdr}")
    for f in FLOORS:
        cells = []
        for area in AREAS:
            miss = sum(1 for r in rows
                       if not any(d["area"] >= area for d in r["dets"] if d["score"] > f))
            cells.append(f"{miss:>6}")
        print(f"{f:>7.2f}  " + "  ".join(cells))

    print("\n=== RECOVERED BY LOWERING THE FLOOR 0.40 -> 0.10 ===")
    rec = []
    for r in rows:
        at40 = any(d["area"] >= MIN_BODY_AREA for d in r["dets"] if d["score"] > 0.40)
        at10 = any(d["area"] >= MIN_BODY_AREA for d in r["dets"] if d["score"] > 0.10)
        if at10 and not at40:
            best = max((d for d in r["dets"] if d["area"] >= MIN_BODY_AREA),
                       key=lambda d: d["score"])
            rec.append((r["id"], best["area"], best["score"], best["label"]))
    print(f"leaves whose body block is DETECTED THEN DELETED: {len(rec)}")
    for i, (lid, area, sc, lab) in enumerate(sorted(rec, key=lambda t: -t[2])):
        if i < 25:
            print(f"  {lid:<22} area {area:.3f}  score {sc:.4f}  {lab}")
    if len(rec) > 25:
        print(f"  ... and {len(rec)-25} more")

    print("\n=== PER WITNESS: no-body-block count, 0.40 vs 0.10 ===")
    ws = sorted({r["witness"] for r in rows})
    print(f"{'witness':<16} {'n':>4} {'@0.40':>7} {'@0.10':>7} {'recovered':>10}")
    for w in ws:
        sub = [r for r in rows if r["witness"] == w]
        m40 = sum(1 for r in sub if not any(d["area"] >= MIN_BODY_AREA
                                            for d in r["dets"] if d["score"] > 0.40))
        m10 = sum(1 for r in sub if not any(d["area"] >= MIN_BODY_AREA
                                            for d in r["dets"] if d["score"] > 0.10))
        print(f"{w:<16} {len(sub):>4} {m40:>7} {m10:>7} {m40-m10:>10}")


if __name__ == "__main__":
    raise SystemExit(main())
