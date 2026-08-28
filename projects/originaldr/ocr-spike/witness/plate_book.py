#!/usr/bin/env python3
"""R14.17 / R16.1 -- THE PLATE BOOK: every leaf of the gold set, with LIVE box geometry.

Sir, 2026-08-28: *"we will be walking through all of these in addition to the 20 currently included
in the Gold Set. The entire set of all of these plates will be the Gold Set."* That set is
**GOLD-LAYOUT** under R16.1 -- 208 leaves clears its >=125-page threshold -- and it is the blocker
sitting under both models and under §7.8 rows 10a/10b.

🔴 WHY THIS FILE EXISTS: THE OLD PLATE BOOK COULD NOT BE EDITED, AND NOT FOR A UI REASON.
`.scratch/r14/render_full.py` BURNED THE BOXES INTO THE JPEGs. Its `bundle.json` carried only a
per-leaf summary -- archetype, counts, overlaps, measure, head_y, foot_y -- and not one box
coordinate. A review tool cannot move a rectangle that exists only as ink in a photograph, so no
amount of front-end work could have produced a correction surface on top of it. The plates were an
INSTRUMENT FOR LOOKING; this is an instrument for CORRECTING.

⚠️ THE PLATES ARE RENDERED CLEAN AND THE BOXES ARE DRAWN BY THE TOOL, NOT BY THE RENDERER. That
separation is the whole point: the image is evidence, the boxes are a claim about it, and a claim
you can no longer separate from its evidence cannot be revised.

⚠️ GOLD-LAYOUT IS THE SCORER, NOT THE TRAINER (R14.6). Sir intends these plates to TRAIN a layout
model. The same leaves cannot both train and score it -- that is circular, and it is the failure
this project has spent its whole life instrumenting against. So every leaf carries a `split` field
from the moment it enters the book, and R16.1's GATHERING-LEVEL split is the mechanism: leaves from
one gathering never straddle train and test, because leaves of a gathering share paper, ink and
press and are near-duplicates of one another.

⚠️ THE AUXILIARY PERCEPTION RECORDS ARE PER-WITNESS AND MOSTLY DO NOT EXIST YET. `fount_*`, `skew_*`
and `reading_*` are keyed by witness and leaf range, and only `OT1-1609-B` 400-419 has them. On a
leaf without them LECTOR does NOT silently guess -- it reports `no fount record loaded` and the
dependent cues abstain WITH A CAUSE. Every plate therefore records which channels were live when it
was made, because a box named without the fount is a different claim from the same box named with
it, and a reviewer who cannot tell them apart is adjudicating two things at once.

    ../ocr-venv/bin/python witness/plate_book.py --manifest        # write/refresh the leaf manifest
    ../ocr-venv/bin/python witness/plate_book.py --build           # Surya + LECTOR + render (SLOW)
    ../ocr-venv/bin/python witness/plate_book.py                   # report what is built

Exits 0. This command BUILDS an instrument; it discharges no gate and scores nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import visual_agent as VA                                # noqa: E402
import witnesses as W                                    # noqa: E402

BOOK = _HERE / "plates"
MANIFEST = BOOK / "manifest.json"
BUNDLE = BOOK / "bundle.json"
IMG = BOOK / "img"
# The 188 leaves Sir added, listed as absolute jp2 paths by R14.18.
REQUEST = SPIKE / ".scratch" / "r14" / "gold-expansion-request.txt"
# The 20 already adjudicated. ⚠️ These are the ONLY leaves any current score is measured on.
SCORED = (VA.WITNESS, list(range(VA.LEAF_LO, VA.LEAF_HI)))
PLATE_MAXW = 1600        # rendered plate width in px; the tool scales boxes to whatever it gets


def _witness_of_path(p: Path):
    """-> witness id for a jp2 path, matched on its OWN jp2 DIRECTORY.

    ⚠️ NEVER MATCH ON THE SCAN FOLDER (`S09_...`). S09 alone holds THREE witnesses -- NT-1582-B,
    OT1-1609-B and OT2-1610-B -- so the scan label answers a different question from the one asked.
    Reading the jp2 directory is what showed that ZERO of Sir's 188 leaves are OT1-1609-B, the
    witness every existing score rests on.
    """
    for (vol, sig), d in W.WITNESSES.items():
        if d["jp2"].name in p.parts:
            return W.wid(vol, sig)
    return None


def build_manifest() -> int:
    """Enumerate the gold set as (witness, leaf) pairs. NEVER as bare leaf ordinals.

    ⚠️ A BARE LEAF NUMBER IS NOT AN ADDRESS IN A MULTI-WITNESS GOLD. OT1-1609-B has 1160 leaves and
    OT1-1609-P has 1146, so there is NO fixed offset between their ordinals; `leaf 400` names two
    different pages. R14.18 records that the mapping needs the PRINTED PAGE NUMBER, which is what
    R14.10b's `PN` class supplies -- and which is therefore load-bearing for this manifest, not a
    curiosity.
    """
    rows, missing = [], []
    for wid, leaves in [(SCORED[0], SCORED[1])]:
        for i in leaves:
            rows.append({"witness": wid, "leaf": i, "origin": "adjudicated-20",
                         "split": "test", "gold": "GOLD-HEADBAND+FOREEDGE"})
    if REQUEST.is_file():
        for line in REQUEST.read_text().split("\n"):
            line = line.strip()
            if not line:
                continue
            p = Path(line)
            wid = _witness_of_path(p)
            if wid is None:
                missing.append(line)
                continue
            stem = p.stem
            idx = stem.rsplit("_", 1)[-1]
            if not idx.isdigit():
                missing.append(line)
                continue
            rows.append({"witness": wid, "leaf": int(idx), "origin": "sir-2026-08-28",
                         "split": "unassigned", "gold": "GOLD-LAYOUT (R16.1), unadjudicated"})
    else:
        missing.append(f"{REQUEST} is absent — the 188 cannot be enumerated")

    seen, out = set(), []
    for r in rows:
        k = (r["witness"], r["leaf"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    BOOK.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({
        "_doc": ("The GOLD-LAYOUT leaf set (R16.1), addressed as (witness, leaf) pairs because a "
                 "bare ordinal names different pages in different witnesses. `split` is UNASSIGNED "
                 "until R16.1's gathering-level split is applied — it is NOT defaulted to train, "
                 "because a leaf silently defaulted into training is a leaf that can never honestly "
                 "score the model it trained."),
        "n": len(out), "unresolved": missing, "leaves": out}, indent=1))
    by_w: dict[str, int] = {}
    for r in out:
        by_w[r["witness"]] = by_w.get(r["witness"], 0) + 1
    print(f"manifest -> {MANIFEST.relative_to(SPIKE)}\n  {len(out)} leaf/leaves over "
          f"{len(by_w)} witness(es)")
    for k, v in sorted(by_w.items()):
        print(f"    {k:<12} {v:>4}")
    if missing:
        print(f"  🔴 {len(missing)} line(s) UNRESOLVED — reported, never dropped:")
        for m in missing[:5]:
            print(f"      {m}")
    return 0


def _aux_state(wid: str) -> dict:
    """Which perception channels exist for this witness. ⚠️ Reported per leaf, never assumed."""
    def has(kind):
        return bool(list((_HERE / "gold").glob(f"{kind}_{wid}_*.json")))
    return {"fount": has("fount"), "skew": has("skew"), "reading": has("reading")}


def build() -> int:
    from PIL import Image
    from surya.fast_layout import FastLayoutPredictor

    if not MANIFEST.is_file():
        print("🔴 no manifest — run --manifest first.")
        return 0
    man = json.loads(MANIFEST.read_text())
    IMG.mkdir(parents=True, exist_ok=True)
    pred = FastLayoutPredictor()
    paths: dict[str, list] = {}
    plates, failed = [], []

    for n, row in enumerate(man["leaves"], 1):
        wid, i = row["witness"], row["leaf"]
        if wid not in paths:
            vol, sig = [k for k in W.WITNESSES if W.wid(*k) == wid][0]
            paths[wid] = W.leaves(vol, sig)
        try:
            src = paths[wid][i]
            im = Image.open(str(src)).convert("RGB")
        except Exception as e:                                       # noqa: BLE001
            # ⚠️ A LEAF THAT CANNOT BE OPENED IS REPORTED, NEVER SKIPPED. A silently dropped leaf
            # shrinks the gold without changing any number that would reveal it.
            failed.append({"witness": wid, "leaf": i, "why": f"{type(e).__name__}: {e}"})
            print(f"  🔴 {wid} {i}: {type(e).__name__}: {e}", flush=True)
            continue

        boxes = VA.see(im, pred)
        lf = VA.settle(VA.Leaf(leaf=i, boxes=boxes))
        stem = f"{wid}_{i:04d}"
        w, h = im.size
        im.resize((PLATE_MAXW, round(h * PLATE_MAXW / w))).save(IMG / f"{stem}.jpg", quality=88)

        plates.append({
            "id": stem, "witness": wid, "leaf": i,
            "origin": row["origin"], "split": row["split"], "gold": row["gold"],
            "img": f"img/{stem}.jpg", "page_px": [w, h],
            "archetype": lf.archetype, "arch_conf": round(lf.arch_conf, 4),
            "arch_cause": lf.arch_cause,
            "measure": [round(x, 5) for x in lf.measure],
            "head_y": round(lf.head_y, 5), "foot_y": round(lf.foot_y, 5),
            "skew": round(lf.skew, 4), "skew_seen": lf.skew_seen,
            # The channels that were LIVE when this plate was made. A box named without the fount is
            # a different claim from the same box named with it.
            "channels": {**_aux_state(wid),
                         "fount_why": lf.fount_why, "read_why": lf.read_why,
                         "skew_why": lf.skew_why},
            "boxes": [{"i": k,
                       "x0": round(b.x0, 5), "y0": round(b.y0, 5),
                       "x1": round(b.x1, 5), "y1": round(b.y1, 5),
                       "surya": b.surya, "label": b.label,
                       "conf": round(b.conf, 4), "cause": b.cause}
                      for k, b in enumerate(lf.boxes)],
        })
        print(f"  {n}/{len(man['leaves'])} {stem}: {len(lf.boxes)} box(es), "
              f"archetype {lf.archetype}", flush=True)

    BUNDLE.write_text(json.dumps({
        "_doc": ("GOLD-LAYOUT plate book (R16.1) with LIVE box geometry — the boxes are DATA here, "
                 "not ink burned into the plate, which is what makes a correction surface possible. "
                 "Every label is LECTOR's CLAIM about the leaf and none of it is adjudicated until a "
                 "human records a verdict in the review tool."),
        "classes": list(VA.CLASSES), "n": len(plates), "failed": failed, "plates": plates},
        indent=1))
    print(f"\n{len(plates)} plate(s) -> {BUNDLE.relative_to(SPIKE)}")
    if failed:
        print(f"🔴 {len(failed)} leaf/leaves FAILED and are recorded in the bundle, not dropped.")
    return 0


def report() -> int:
    if not MANIFEST.is_file():
        print("🔴 NOT BUILT — no manifest. Run --manifest, then --build.")
        return 0
    man = json.loads(MANIFEST.read_text())
    print(f"GOLD-LAYOUT plate book (R16.1)\n\n  manifest : {man['n']} leaf/leaves")
    by_w: dict[str, int] = {}
    for r in man["leaves"]:
        by_w[r["witness"]] = by_w.get(r["witness"], 0) + 1
    for k, v in sorted(by_w.items()):
        print(f"      {k:<12} {v:>4}")
    if not BUNDLE.is_file():
        print("\n  plates   : 🔴 NOT BUILT — run --build (Surya over every leaf; this is the slow "
              "part).")
        return 0
    b = json.loads(BUNDLE.read_text())
    print(f"\n  plates   : {b['n']} built, {len(b['failed'])} failed")
    unassigned = sum(1 for p in b["plates"] if p["split"] == "unassigned")
    print(f"  split    : {unassigned} of {b['n']} UNASSIGNED — R16.1's gathering-level split is "
          f"NOT yet applied.\n             ⚠️ GOLD-LAYOUT is the SCORER; if these leaves also TRAIN "
          f"the model,\n             a leaf on both sides makes every resulting number circular.")
    nof = sum(1 for p in b["plates"] if not p["channels"]["fount"])
    print(f"  channels : {nof} of {b['n']} plate(s) made with NO fount record — their `AR` cue "
          f"could not fire\n             and says so; the same holds for `PN` without a reading "
          f"record.")
    return 0


def main() -> int:
    if "--manifest" in sys.argv:
        return build_manifest()
    if "--build" in sys.argv:
        return build()
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
