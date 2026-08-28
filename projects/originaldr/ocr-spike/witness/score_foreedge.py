#!/usr/bin/env python3
"""R14.8 -- score the agent BELOW the head band, and settle whether besideness generalises.

THE QUESTION. Every MarginNote figure this project has ever quoted -- Surya's 0/19, `region_head`'s
17/19, the agent's 16/19 -- is measured on GOLD-HEADBAND, which labels the **top three rows**. So
every one of them is a HEAD-BAND note: a note set at the same height as the running head, out at the
fore-edge, which STRADDLES the measure's edge. The class this edition is actually built around is the
note running down the **outer margin beside the measure**, and it had never been scored at all.

⚠️ THE PRE-REGISTERED EXPECTATION, written into `build_foreedge_gold.py` BEFORE this ran:
**besideness should do BETTER on fore-edge notes than on head-band notes**, because a fore-edge note
CLEARS the measure outright where a head-band note straddles it -- which is precisely why 3 of the
agent's 6 head-band misses were thin-margin abstentions. **If fore-edge MN recall comes in BELOW
head-band recall, the besideness cue does not generalise and R14.2 RE-OPENS.** Writing the expected
direction down first is what makes either outcome informative; a cue that "passes" whatever it scores
has not been tested.

⚠️ THIS SCORES A POPULATION THE AGENT WAS NOT BUILT AGAINST. The four cues were written and debugged
against the head band. Nothing here was tuned on these 42 boxes.

    ../ocr-venv/bin/python witness/score_foreedge.py

Exit 1 while any class the page prints has no name in the agent, which is the healthy state today.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import visual_agent as VA                                   # noqa: E402
from build_foreedge_gold import GOLD, candidates            # noqa: E402

# The agent's class inventory, so "the agent has no name for this" is a CHECKED claim rather than a
# reading of the source. 🔴 R14.10a — IT IS NOW IMPORTED, NOT RESTATED, AND THE REASON IS THAT THE
# RESTATED COPY WENT STALE THE MOMENT A CLASS WAS ADDED: the first run after `AR` was adopted scored
# `AR recall 4/4` and printed `AR ⚠️ NO NAME IN THE AGENT` about the same four boxes. A checking
# claim that can drift from what it checks is not a check.
AGENT_CLASSES = VA.CLASSES

# Head-band MarginNote recall, from `visual_agent.py` on GOLD-HEADBAND. The comparison this file
# exists to make; it is a measured figure, not a bar invented here.
# 🔴 R14.11, 2026-08-28 — THIS WAS THE LITERAL `HEADBAND_MN = 16 / 19` AND IT WENT STALE THE MOMENT
# THE AGENT IMPROVED. Retiring `CENTRED_LO/HI` moved head-band MarginNote 16/19 -> 18/19, and this
# file went on comparing the fore-edge against 16/19 while printing "(16/19)" beside it — the
# comparison silently became one against a figure the head band no longer scored. It is now COMPUTED
# by `visual_agent.headband_score`, the one place that number exists. ⚠️ Exactly the defect this
# file's own docstring records about its restated copy of `CLASSES`, one level up.


def _headband_mn() -> tuple[int, int]:
    _, _, per = VA.headband_score()
    ok, n = per.get(VA.MN, [0, 0])
    return ok, n


def main() -> int:
    g = json.loads(GOLD.read_text())
    leaves = {lf.leaf: lf for lf in VA.load_leaves()}

    print("R14.8 — THE AGENT BELOW THE HEAD BAND (GOLD-FOREEDGE)")
    print(f"{VA.WITNESS}; {len(g['labels'])} adjudicated boxes over "
          f"{len(set(r['leaf'] for r in g['labels']))} DECLARED leaves; both fore-edges represented\n")

    per: dict[str, list[int]] = {}
    conf: dict[tuple, int] = {}
    unnameable: dict[str, int] = {}
    for row in g["labels"]:
        lf = leaves[row["leaf"]]
        b = candidates(lf)[row["idx"]]
        gold, got = row["label"], b.label
        per.setdefault(gold, [0, 0])
        per[gold][1] += 1
        if got == gold:
            per[gold][0] += 1
        conf[(gold, got)] = conf.get((gold, got), 0) + 1
        if gold not in AGENT_CLASSES:
            unnameable[gold] = unnameable.get(gold, 0) + 1

    hit = sum(v[0] for v in per.values())
    tot = sum(v[1] for v in per.values())
    print(f"overall {hit}/{tot} = {hit / tot:.4f}")
    for lab in sorted(per):
        c, n = per[lab]
        mark = "" if lab in AGENT_CLASSES else "   ⚠️ NO NAME IN THE AGENT"
        print(f"    {lab} recall {c}/{n} = {c / n:.4f}{mark}")

    print("\n  confusion (gold -> agent), errors only:")
    for (gl, al), n in sorted(conf.items(), key=lambda kv: -kv[1]):
        if gl != al:
            print(f"     🔴 {gl} -> {al:3s} {n}")

    # ---- THE PRE-REGISTERED TEST
    mn = per.get(VA.MN, [0, 0])
    mn_r = mn[0] / mn[1] if mn[1] else 0.0
    print(f"\n📌 THE PRE-REGISTERED COMPARISON — does besideness GENERALISE off the head band?")
    hb_ok, hb_n = _headband_mn()
    headband_mn = hb_ok / hb_n if hb_n else 0.0
    print(f"    head-band MarginNote recall (GOLD-HEADBAND) : {headband_mn:.4f}  ({hb_ok}/{hb_n})")
    print(f"    fore-edge MarginNote recall (GOLD-FOREEDGE) : {mn_r:.4f}  ({mn[0]}/{mn[1]})")
    if mn_r >= headband_mn:
        print("    ✅ AS PREDICTED — a fore-edge note CLEARS the measure where a head-band note")
        print("       straddles it, so the cue is on firmer ground here, not weaker. The besideness")
        print("       cue GENERALISES, and the head-band figure was its WORST case, not its best.")
    else:
        print("    🔴 CONTRARY TO THE PREDICTION — the cue does NOT generalise off the head band.")
        print("       R14.2 RE-OPENS. ⚠️ This is a redesign trigger, never an accepted gap.")

    # ---- the class-inventory finding
    print(f"\n🔴 CLASSES THE PAGE PRINTS AND THE AGENT CANNOT NAME: {sum(unnameable.values())} box(es)")
    for lab, n in sorted(unnameable.items(), key=lambda kv: -kv[1]):
        print(f"     {lab} × {n}")
    print("   ⚠️ A CLASS WITH NO NAME IS NOT SKIPPED — IT IS MISFILED into the nearest name the")
    print("   agent does have, which is exactly how a gathering signature became a chapter heading")
    print("   on leaf 409 (R14.9). These boxes are counted as errors above, correctly: the agent is")
    print("   WRONG about them, not merely silent. They are Roadmap R14.10.")

    print("\n⚠️ COVERAGE, STATED. 5 of 20 leaves, ONE witness, ONE operator, NOT fully blind (the")
    print("   agent's aggregate calls had been seen before adjudication). Discharges NO gate; rows")
    print("   10a/10b remain reserved for GOLD-LAYOUT (R16.1). This gold may never be promoted.")

    return 1 if unnameable else 0


if __name__ == "__main__":
    raise SystemExit(main())
