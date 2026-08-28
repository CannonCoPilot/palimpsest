#!/usr/bin/env python3
"""R14.8 -- GOLD-FOREEDGE: the gold below the head band, which did not exist.

THE COVERAGE LIMIT THIS LIFTS. `GOLD-HEADBAND` labels the **top three rows** of twenty leaves, so
every MarginNote in it is a HEAD-BAND note -- a note set at the same height as the running head, out
at the fore-edge. R14.0, R2.2o.1 and R14.1/R14.2 all inherit that limit, and all three said so. What
none of them could show is the class this edition is actually built around: **the note running down
the OUTER MARGIN beside the measure**. 99 detector boxes sit below the head band on these leaves and
NOT ONE of them has ever been scored against anything.

HOW THE GOLD IS MADE, AND ITS LIMITS, STATED BEFORE ITS NUMBERS
  * It addresses the **detector's** boxes (Surya, S1 perception), which are produced by a third-party
    model and are independent of this project's naming cues. So the gold is not scoring the agent
    against its own output.
  * It is adjudicated **from the leaf image** by ONE operator (`--blind` renders the boxes NUMBERED
    and UNLABELLED for exactly this purpose). ⚠️ **SINGLE-ADJUDICATOR, AND NOT FULLY BLIND**: the
    agent's calls on these boxes had been inspected in aggregate before adjudication began. That is
    recorded rather than hidden, and it is why this gold may NEVER be promoted to GOLD-LAYOUT (§7.8
    row 9), which requires a gathering-level split and a per-archetype quota.
  * It is the **SCORER**, never the trainer. §3.2 item 2's distant supervision is the trainer.

⚠️ THE PRE-REGISTERED EXPECTATION, WRITTEN BEFORE THE FIRST SCORE (R14.8's acceptance): **besideness
should do BETTER on fore-edge notes than on head-band notes.** A fore-edge note CLEARS the measure
outright, where a head-band note STRADDLES its edge -- which is exactly why 3 of the agent's 6
head-band misses were thin-margin abstentions. If fore-edge MN recall comes in BELOW head-band recall,
the besideness cue does not generalise and R14.2 re-opens; that is the outcome this file is built to
be able to report.

    ../ocr-venv/bin/python witness/build_foreedge_gold.py --blind   # render numbered, UNLABELLED
    ../ocr-venv/bin/python witness/build_foreedge_gold.py --check   # verify the gold reproduces
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W                      # noqa: E402
import visual_agent as VA                  # noqa: E402

GOLD = _HERE / "gold" / f"foreedge_regions_{VA.WITNESS}_{VA.LEAF_LO}-{VA.LEAF_HI - 1}.json"
BLIND = _HERE / "see" / "blind"


def candidates(lf) -> list:
    """Every box whose MASS sits below the head band — i.e. every box GOLD-HEADBAND cannot see.

    ⚠️ The population is defined by GEOMETRY ALONE, never by the agent's label, so the gold cannot
    inherit the agent's blind spots: a box the agent mis-types is still in the gold, and a class the
    agent has no name for is still in the gold.
    """
    return [b for b in sorted(lf.boxes, key=lambda b: (b.y0, b.x0))
            if 0.5 * (b.y0 + b.y1) > lf.head_y]


def render_blind() -> None:
    """Numbered boxes, NO labels, so the adjudication is made from the page."""
    from PIL import Image, ImageDraw, ImageFont

    def font(sz):
        try:
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", sz)
        except Exception:
            return ImageFont.load_default()

    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == VA.WITNESS][0]
    paths = W.leaves(vol, sig)
    BLIND.mkdir(parents=True, exist_ok=True)
    for lf in VA.load_leaves():
        im = Image.open(str(paths[lf.leaf])).convert("RGB")
        w0, h0 = im.size
        im = im.resize((900, int(h0 * 900 / w0)))
        Wp, Hp = im.size
        im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.30)
        dr = ImageDraw.Draw(im)
        f = font(26)
        ml, mr = lf.measure
        for x in (ml, mr):
            dr.line([(x * Wp, 0), (x * Wp, Hp)], fill=(0, 0, 255), width=2)
        dr.line([(0, lf.head_y * Hp), (Wp, lf.head_y * Hp)], fill=(0, 0, 255), width=2)
        for n, b in enumerate(candidates(lf)):
            dr.rectangle([b.x0 * Wp, b.y0 * Hp, b.x1 * Wp, b.y1 * Hp],
                         outline=(200, 0, 0), width=3)
            dr.text((b.x0 * Wp + 4, b.y0 * Hp + 2), str(n), fill=(200, 0, 0), font=f)
        im.save(BLIND / f"blind-{lf.leaf}.png")
        print(f"  leaf {lf.leaf}: {len(candidates(lf))} candidate box(es)")
    print(f"\n-> {BLIND}")


def check() -> int:
    """Every gold entry must still address a real detector box, by index AND by geometry."""
    if not GOLD.is_file():
        print(f"🔴 no gold at {GOLD}")
        return 1
    g = json.loads(GOLD.read_text())
    leaves = {lf.leaf: lf for lf in VA.load_leaves()}
    n = bad = 0
    per: dict[str, int] = {}
    for row in g["labels"]:
        lf = leaves.get(row["leaf"])
        cands = candidates(lf) if lf else []
        n += 1
        per[row["label"]] = per.get(row["label"], 0) + 1
        if row["idx"] >= len(cands):
            print(f"🔴 leaf {row['leaf']} idx {row['idx']} out of range ({len(cands)} boxes)")
            bad += 1
            continue
        b = cands[row["idx"]]
        # ⚠️ ADDRESSED BY GEOMETRY, NOT ONLY BY ORDINAL (R2.2j's lesson: an ordinal address COLLAPSES
        # under a pure renaming that moves no pixel). The recorded box must still be where it was.
        if abs(b.x0 - row["x0"]) > 1e-6 or abs(b.y0 - row["y0"]) > 1e-6:
            print(f"🔴 leaf {row['leaf']} idx {row['idx']} MOVED — the address no longer holds")
            bad += 1
    print(f"GOLD-FOREEDGE: {n} adjudicated boxes over {len(set(r['leaf'] for r in g['labels']))} leaves")
    print(f"  by class: {dict(sorted(per.items(), key=lambda kv: -kv[1]))}")
    print(f"  {n - bad}/{n} addresses reproduce from the page")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--blind" in sys.argv:
        render_blind()
        raise SystemExit(0)
    raise SystemExit(check())
