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

# Padding around the candidate box, in page fractions. ⚠️ SAME VALUES AS `build_recog_gold.py`, and
# for the reason recorded there: PAD_X was 0.004 and CLIPPED the leading sort of a line, which asks
# the model to read something the page does not print. A page number is two or three sorts, so a
# clipped leading glyph is a third of the evidence.
PAD_X, PAD_Y = 0.009, 0.004


def build() -> int:
    from PIL import Image
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == VA.WITNESS][0]
    paths = W.leaves(vol, sig)
    prov = RG.provenance()
    CROPS.mkdir(parents=True, exist_ok=True)

    out = []
    for lf in VA.load_leaves():
        im = Image.open(str(paths[lf.leaf]))
        im.draft("RGB", (3200, 4500))
        im = im.convert("RGB")
        Wp, Hp = im.size
        n = 0
        for k, b in enumerate(lf.boxes):
            if not VA.pn_candidate(b, lf):
                continue
            png = CROPS / f"leaf{lf.leaf}_box{k}.png"
            px = (max(0, int((b.x0 - PAD_X) * Wp)), max(0, int((b.y0 - PAD_Y) * Hp)),
                  min(Wp, int((b.x1 + PAD_X) * Wp)), min(Hp, int((b.y1 + PAD_Y) * Hp)))
            im.crop(px).save(png)
            out.append({"leaf": lf.leaf, "x0": b.x0, "y0": b.y0, "x1": b.x1, "y1": b.y1,
                        "text": RG.read_stamped(png)["text"],
                        "crop": str(png.relative_to(SPIKE))})
            n += 1
        print(f"  leaf {lf.leaf}: {n} candidate(s) read", flush=True)

    OUT.write_text(json.dumps({
        "_doc": ("R14.10b's CONFIRMING READ. One entry per head-band candidate box: what the "
                 "SELECTED recogniser makes of it. ⚠️ This is PERCEPTION, never a label — the "
                 "reading decides the CLASS, and the printed number itself is adjudicated "
                 "separately from the page (see score_pagenumber_agent.py)."),
        "witness": VA.WITNESS, "window": [VA.LEAF_LO, VA.LEAF_HI - 1],
        "stamp": prov, "readings": out,
    }, indent=1))
    print(f"\n{len(out)} reading(s) -> {OUT.relative_to(SPIKE)}")
    print(f"stamp: {prov['model']} sha {prov['model_sha']}")
    return 0


def report() -> int:
    if not OUT.is_file():
        print(f"🔴 NOT BUILT — {OUT.relative_to(SPIKE)} is absent.")
        print("   The `PN` cue does not fire without it, and it says so rather than falling")
        print("   through to the size prior. Run with --build.")
        return 0
    d = json.loads(OUT.read_text())
    s, cur = d["stamp"], RG.provenance()
    print(f"R14.10b reading record — {len(d['readings'])} reading(s) over "
          f"leaves {d['window'][0]}-{d['window'][1]}\n")
    print(f"    built by      {s['model']} sha {s['model_sha']}")
    print(f"    selected now  {cur['model']} sha {cur['model_sha']}")
    ok = s["model_sha"] == cur["model_sha"]
    print(f"    {'✅ MATCH — the record is admissible' if ok else '🔴 STALE — attach_reading will REFUSE it'}\n")
    digits = sum(1 for r in d["readings"] if r["text"].strip().isdigit())
    empty = sum(1 for r in d["readings"] if not r["text"].strip())
    print(f"    all-digit readings  {digits}")
    print(f"    empty readings      {empty}   -- these ABSTAIN; they are never guessed into a class")
    print(f"    lettered readings   {len(d['readings']) - digits - empty}   -- fall through to the "
          f"head-band note logic")
    return 0


def main() -> int:
    return build() if "--build" in sys.argv else report()


if __name__ == "__main__":
    raise SystemExit(main())
