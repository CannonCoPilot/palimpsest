#!/usr/bin/env python3
"""R14.10b -- PERCEPTION: the CONFIRMING READ, cut once and recorded with its model stamp.

§3.0's S2 describes a *"quick confirming read"* -- the reader's glance at a mark to settle what kind
of thing it is -- and `PN` is the first class in this agent that genuinely needs one. Measured over
leaves 400-419, page numbers and head-band notes OVERLAP on both sides of the measure (page numbers
0.000-0.043 and 0.812-0.972 of the measure; notes 0.010-0.110 and 0.857-1.072), so **no position
rule can separate them** -- the R2.2o.1 shape, one class over. What separates them is that one says
`380` and the other says `Sacrifices for`.

⚠️ WHY A RECORD AND NOT A CALL INSIDE THE CUE. `settle()` has no page image -- deliberately, because
`leaf_from_cache` must reproduce the agent's naming from the perception cache alone. Reading inside
`_cue` would put a model load and a disk crop inside a function called once per box per leaf, and
would make the agent's naming unreproducible from the cache. `attach_fount` solved the same problem
the same way in R14.10a; this is that pattern, applied to a second perception channel.

⚠️ THE STAMP IS THE POINT OF THE FILE FORMAT. Every reading carries the model id and the artefact
digest that produced it (R13.1's provenance rule), so a record built by one recogniser can never be
mistaken for one built by another. `attach_reading` REFUSES a record whose stamp does not match the
currently selected model rather than using it -- a stale reading wearing the selected model's
authority is R13.1's defect exactly.

    ../ocr-venv/bin/python witness/build_reading_record.py            # report only (default)
    ../ocr-venv/bin/python witness/build_reading_record.py --build    # cut crops + read + write

⚠️ NO-ARGUMENT BEHAVIOUR IS THE REPORT, NOT THE BUILD, AND THAT IS DELIBERATE. The verification
standard runs every enrolled command WITHOUT ITS ARGUMENTS; enrolling `build_recog_gold.py --check`
made the suite run it bare, which took the cutting path and blanked all 51 hand-keyed truth files.
A script whose no-argument behaviour is destructive WILL be run destructively by that block.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import witnesses as W                     # noqa: E402
import visual_agent as VA                 # noqa: E402
import recogniser as RG                   # noqa: E402

OUT = VA.READING
CROPS = _HERE / "gold" / "reading-crops"
BUNDLE = _HERE / "plates" / "bundle.json"


def leaves_for(wid: str):
    """The Leaf objects to read candidates from, for `wid`.

    The scored witness comes from its own perception cache, unchanged. Every other witness comes from
    the PLATE BUNDLE, which already holds Surya's boxes for all 208 leaves -- so this reads no images
    through the detector a second time.

    ⚠️ THE BUNDLE ALSO HOLDS LABELS, AND THEY ARE NOT READ. `leaf_from_cache` takes the five
    perception keys only; feeding a previous decision back in would let the `PN` cue be scored
    against its own earlier output.
    """
    if wid == VA.WITNESS:
        return VA.load_leaves()
    if not BUNDLE.is_file():
        raise SystemExit(f"🔴 no plate bundle at {BUNDLE} — run plate_book.py --build first.")
    plates = json.loads(BUNDLE.read_text())["plates"]
    return [VA.leaf_from_cache(p, witness=wid) for p in plates if p["witness"] == wid]


def crop_name(wid: str, leaf: int, k: int) -> str:
    """⚠️ THE WITNESS IS IN THE FILENAME BECAUSE LEAF ORDINALS COLLIDE ACROSS WITNESSES. Leaf 5 of
    `OT1-1609-P` and leaf 5 of `OT2-1610-P` are different pages; `leaf5_box0.png` would have named
    both, and the second build would have silently overwritten the first witness's crop while its
    record still pointed at the path. A reading is only evidence if it is addressed to one page.
    """
    return f"{wid}_leaf{leaf}_box{k}.png"

# Padding around the candidate box, in page fractions. ⚠️ SAME VALUES AS `build_recog_gold.py`, and
# for the reason recorded there: PAD_X was 0.004 and CLIPPED the leading sort of a line, which asks
# the model to read something the page does not print. A page number is two or three sorts, so a
# clipped leading glyph is a third of the evidence.
PAD_X, PAD_Y = 0.009, 0.004


def build_one(wid: str) -> int:
    from PIL import Image
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == wid][0]
    paths = W.leaves(vol, sig)
    prov = RG.provenance()
    CROPS.mkdir(parents=True, exist_ok=True)

    leaves = leaves_for(wid)
    print(f"\n=== {wid}: {len(leaves)} leaf/leaves ===", flush=True)
    out = []
    for lf in leaves:
        im = Image.open(str(paths[lf.leaf]))
        im.draft("RGB", (3200, 4500))
        im = im.convert("RGB")
        Wp, Hp = im.size
        n = 0
        for k, b in enumerate(lf.boxes):
            if not VA.pn_candidate(b, lf):
                continue
            png = CROPS / crop_name(wid, lf.leaf, k)
            px = (max(0, int((b.x0 - PAD_X) * Wp)), max(0, int((b.y0 - PAD_Y) * Hp)),
                  min(Wp, int((b.x1 + PAD_X) * Wp)), min(Hp, int((b.y1 + PAD_Y) * Hp)))
            im.crop(px).save(png)
            out.append({"leaf": lf.leaf, "x0": b.x0, "y0": b.y0, "x1": b.x1, "y1": b.y1,
                        "text": RG.read_stamped(png)["text"],
                        "crop": str(png.relative_to(SPIKE))})
            n += 1
        print(f"  leaf {lf.leaf}: {n} candidate(s) read", flush=True)

    p = VA._rec_path("reading", wid)
    doc = {
        "_doc": ("R14.10b's CONFIRMING READ. One entry per head-band candidate box: what the "
                 "SELECTED recogniser makes of it. ⚠️ This is PERCEPTION, never a label — the "
                 "reading decides the CLASS, and the printed number itself is adjudicated "
                 "separately from the page (see score_pagenumber_agent.py)."),
        "witness": wid, "stamp": prov, "readings": out,
    }
    # The scored witness keeps its contiguous `window`; the others record the LEAF LIST, because a
    # window would misdescribe a non-contiguous set and `report()` would print a coverage it lacks.
    if wid == VA.WITNESS:
        doc["window"] = [VA.LEAF_LO, VA.LEAF_HI - 1]
    else:
        doc["leaves"] = sorted({lf.leaf for lf in leaves})
    p.write_text(json.dumps(doc, indent=1))
    digits = sum(1 for r in out if r["text"].strip().isdigit())
    empty = sum(1 for r in out if not r["text"].strip())
    print(f"\n{len(out)} reading(s) -> {p.relative_to(SPIKE)}")
    print(f"  {digits} all-digit · {empty} empty (these ABSTAIN) · "
          f"{len(out) - digits - empty} lettered")
    print(f"stamp: {prov['model']} sha {prov['model_sha']}")
    return 0


def witnesses_from_argv() -> list[str]:
    if "--witness" not in sys.argv:
        return [VA.WITNESS]
    val = sys.argv[sys.argv.index("--witness") + 1]
    if val.upper() != "ALL":
        return [val]
    if not BUNDLE.is_file():
        raise SystemExit(f"🔴 no plate bundle at {BUNDLE}.")
    return sorted({p["witness"] for p in json.loads(BUNDLE.read_text())["plates"]})


def report() -> int:
    wids = sorted({p["witness"] for p in json.loads(BUNDLE.read_text())["plates"]}) \
        if BUNDLE.is_file() else [VA.WITNESS]
    cur = RG.provenance()
    print(f"R14.10b reading record — coverage by witness\n\n"
          f"    recogniser selected now: {cur['model']} sha {cur['model_sha']}\n")
    for wid in wids:
        p = VA._rec_path("reading", wid)
        if not p.is_file():
            print(f"  🔴 {wid:14s} NOT BUILT — the `PN` cue does not fire, and it says so rather")
            print(f"     {'':14s} than falling through to the size prior. Run with --build.")
            continue
        d = json.loads(p.read_text())
        s = d["stamp"]
        ok = s["model_sha"] == cur["model_sha"]
        digits = sum(1 for r in d["readings"] if r["text"].strip().isdigit())
        empty = sum(1 for r in d["readings"] if not r["text"].strip())
        other = len(d["readings"]) - digits - empty
        mark = "✅" if ok else "🔴"
        print(f"  {mark} {wid:14s} {len(d['readings']):4d} reading(s) · {digits} digit · "
              f"{empty} empty (ABSTAIN) · {other} lettered")
        if not ok:
            print(f"     {'':14s} STALE — built by {s['model']} sha {s['model_sha']}; "
                  f"attach_reading will REFUSE it")
    print("\n(report only — pass --build to write)")
    return 0


def main() -> int:
    if "--build" not in sys.argv:
        return report()
    for wid in witnesses_from_argv():
        build_one(wid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
