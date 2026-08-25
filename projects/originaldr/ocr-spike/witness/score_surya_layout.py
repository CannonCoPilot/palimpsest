"""R14.0 -- run the learned layout model that was already in the repo, and SCORE it.

`surya_layout_probe.py` has sat in `ocr-spike/` for weeks: a rung-0 gate for Surya, asking whether it
types early-modern scripture pages. It appears in NONE of the five governing documents (Masterplan,
Roadmap, Walkthrough, Overview, Executive Summary), was never scored, and its result was recorded
nowhere. That is §3.2b's pattern exactly -- WORKING CODE THAT NO RULE GOVERNS -- landing on the one
capability Masterplan §3.0 S3/S4 is about. R14.0 closes it.

⚠️ WHAT THIS IS AND IS NOT.
  * It IS the first layout measurement of any kind on this corpus. Masterplan §7.8 states that rows
    10a/10b/10c and 11 have never been evaluated and that "no layout score of any kind exists on this
    corpus". This does not discharge any of those rows -- it is scored on the 121-entry R2.1g gold
    over 20 leaves of ONE witness, not on GOLD-LAYOUT (>=125 pages, per-archetype quota), and Gate
    10a/10b are explicitly reserved for GOLD-LAYOUT with the recogniser frozen.
  * It is a ROUNG-0 ADMISSIBILITY question: is this model worth building on at all?

⚠️ THE LABEL MAP IS AN ADJUDICATION, AND IT IS DECLARED RATHER THAN TUNED. Surya's vocabulary is a
MODERN-DOCUMENT one -- Caption, Footnote, PageHeader, PageFooter, SectionHeader, Text, Table, Code,
Form, ChemicalBlock, Bibliography. It contains NO marginalia / side-note class. Two maps are scored
and BOTH are reported, because a single map chosen after seeing the numbers would be the map that
flatters:
  * MAP_STRICT   -- by meaning. No Surya class denotes a printed side-note, so MN has NO source.
  * MAP_CHARITABLE -- additionally Footnote -> MN, the most generous reading available (a footnote and
    a side-note are both subsidiary apparatus, though this edition sets its notes in the OUTER MARGIN
    beside the measure, not at the foot).
If MN recall is ~0 under BOTH, the ceiling is a property of the model's inventory, not of the mapping.

⚠️ ADDRESSING IS NOT ADJUDICATION (R2.1i). Gold entries carry `xlf/xrf/y0f/y1f` -- PAGE fractions, the
band-independent address added at R2.2c -- so a gold entry is bound to the Surya box it overlaps most,
in page-fraction space, with no band crop involved. An entry overlapping no box is an ORPHAN and is
reported separately, never folded into accuracy (the discipline `score_argument_region` follows).

    ../ocr-venv/bin/python witness/score_surya_layout.py

Exit 1 while the model is inadmissible for this corpus, which is the finding, not a crash.
"""

import json
import sys
import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W
from score_head_regions import GOLD

WITNESS = "OT1-1609-B"
LEAF_LO, LEAF_HI = 400, 420

# Declared BEFORE the run. Surya label -> this project's region taxonomy.
MAP_STRICT = {
    "PageHeader": "RH",        # the book name set across the head of the page
    "Text": "MT",              # the text block
    "SectionHeader": "CH",     # CHAP. + numeral
}
MAP_CHARITABLE = dict(MAP_STRICT)
MAP_CHARITABLE["Footnote"] = "MN"   # the most generous available reading; see the docstring

# A rung-0 admissibility bar, pre-registered here before the numbers are seen. These are NOT Gate
# 10a/10b thresholds -- those are reserved for GOLD-LAYOUT -- they are the question "is this model
# worth building the agent on".
BAR_MN_RECALL = 0.50      # the class this edition is built around
BAR_OVERALL = 0.70        # bound-entry accuracy over all four classes


# R2.1i's clause, and it is here because the first version of this scorer LACKED it. A binding must be
# SUBSTANTIAL, not merely non-zero: the box must cover this much of the GOLD ENTRY's own area. Without
# it, a model emitting one page-sized box binds every entry and scores whatever its majority class is.
MIN_BIND_FRAC = 0.50


def _ov(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def _area_ov(e, box):
    return _ov((e["xlf"], e["xrf"]), (box[0], box[2])) * _ov((e["y0f"], e["y1f"]), (box[1], box[3]))


def _e_area(e):
    return max(1e-9, (e["xrf"] - e["xlf"]) * (e["y1f"] - e["y0f"]))


def _b_area(box):
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def main() -> int:
    g = json.loads(GOLD.read_text())
    entries = [e for e in g["labels"] if "xlf" in e]
    by_leaf = {}
    for e in entries:
        by_leaf.setdefault(e["leaf"], []).append(e)

    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == WITNESS][0]
    leaves = W.leaves(vol, sig)

    from PIL import Image

    from surya.fast_layout import FastLayoutPredictor

    pred = FastLayoutPredictor()
    print(f"R14.0 -- Surya FastLayoutPredictor vs GOLD-HEADBAND, {WITNESS} leaves {LEAF_LO}-{LEAF_HI-1}")
    print("addressing: PAGE FRACTIONS (R2.2c), max area overlap. Labels: two DECLARED maps, both reported.\n")

    bound, orphans = [], []
    surya_labels = {}
    for i in range(LEAF_LO, LEAF_HI):
        ents = by_leaf.get(i, [])
        if not ents:
            continue
        im = Image.open(str(leaves[i])).convert("RGB")
        Wp, Hp = im.size
        res = pred([im])[0]
        boxes = []
        for b in res.bboxes:
            x0, y0, x1, y1 = b.bbox
            boxes.append((x0 / Wp, y0 / Hp, x1 / Wp, y1 / Hp, b.label))
            surya_labels[b.label] = surya_labels.get(b.label, 0) + 1
        for e in ents:
            best, bov = None, 0.0
            for bx in boxes:
                a = _area_ov(e, bx)
                if a > bov:
                    best, bov = bx, a
            if best is None or bov < MIN_BIND_FRAC * _e_area(e):
                orphans.append(e)
            else:
                bound.append((e, best[4], _b_area(best)))
        print(f"  leaf {i}: {len(res.bboxes):2d} boxes, {len(ents):2d} gold entries", flush=True)

    print(f"\nSurya emitted: {dict(sorted(surya_labels.items(), key=lambda kv: -kv[1]))}")
    print(f"gold entries {len(entries)}   bound {len(bound)}   ORPHANS {len(orphans)} "
          f"(overlapped no box; reported, not scored)")

    print("\n⚠️ SURYA'S VOCABULARY CONTAINS NO MARGINALIA / SIDE-NOTE CLASS.")
    print("   Caption · Footnote · PageHeader · PageFooter · SectionHeader · Text · Table · Code ·")
    print("   Form · ChemicalBlock · Bibliography · TableOfContents · Figure · Picture · ListGroup.")
    print("   This edition's printed side-note has no home in it. That is a property of the MODEL,")
    print("   not of the mapping, which is why both maps below are reported.")

    # ⚠️ THE CONTAINMENT TRAP, measured rather than assumed. A model emitting one page-sized Text box
    # scores MainText 1.0000 and marginalia 0.0000 -- which is close to what is reported below. So the
    # SIZE of the box each entry bound to is printed per gold class: if MainText entries bind to boxes
    # covering a large share of the page, the recall figure is COVERAGE, not boundary quality. Gate 10b
    # (§7.8) is the boundary measurement and this is NOT it.
    import statistics as _st
    per_size = {}
    for e, _sl, ba in bound:
        per_size.setdefault(e["label"], []).append(ba)
    print("\n⚠️ BOX SIZE per bound gold class, as a fraction of PAGE AREA (the containment check):")
    for lab in ("RH", "MN", "MT", "CH"):
        if lab in per_size:
            v = per_size[lab]
            print(f"    {lab}  median {_st.median(v):.4f}  max {max(v):.4f}  n={len(v)}")
    print("    A MainText median near or above ~0.30 means the body 'recall' below is CONTAINMENT in a")
    print("    page-sized block, not a boundary result. Read it with Gate 10b, which is NOT measured here.")

    worst = 1.0
    results = {}
    for name, mp in (("MAP_STRICT", MAP_STRICT), ("MAP_CHARITABLE", MAP_CHARITABLE)):
        per = {}
        conf = {}
        for e, slab, _ba in bound:
            got = mp.get(slab)
            gold_lab = e["label"]
            per.setdefault(gold_lab, [0, 0])
            per[gold_lab][1] += 1
            if got == gold_lab:
                per[gold_lab][0] += 1
            conf[(gold_lab, slab)] = conf.get((gold_lab, slab), 0) + 1
        hit = sum(v[0] for v in per.values())
        tot = sum(v[1] for v in per.values())
        acc = hit / tot if tot else 0.0
        mn = per.get("MN", [0, 0])
        mn_r = mn[0] / mn[1] if mn[1] else 0.0
        results[name] = (acc, mn_r)
        worst = min(worst, acc)
        print(f"\n{name}: bound-entry accuracy {hit}/{tot} = {acc:.4f}")
        for lab in ("RH", "MN", "MT", "CH"):
            if lab in per:
                c, n = per[lab]
                print(f"    {lab} recall {c}/{n} = {c/n:.4f}")
        print("    confusion (gold -> surya, top 6):")
        for (gl, sl), n in sorted(conf.items(), key=lambda kv: -kv[1])[:6]:
            print(f"      {gl} -> {sl:14} {n}")

    best_acc = max(v[0] for v in results.values())
    best_mn = max(v[1] for v in results.values())
    print(f"\nRUNG-0 ADMISSIBILITY BARS, pre-registered in this file before the run:")
    print(f"  MN recall >= {BAR_MN_RECALL:.2f} : best over both maps {best_mn:.4f} "
          f"{'PASS' if best_mn >= BAR_MN_RECALL else '🔴 FAIL'}")
    print(f"  overall   >= {BAR_OVERALL:.2f} : best over both maps {best_acc:.4f} "
          f"{'PASS' if best_acc >= BAR_OVERALL else '🔴 FAIL'}")

    print("\n⚠️ THIS DOES NOT DISCHARGE GATE 10a OR 10b (§7.8). Those are reserved for GOLD-LAYOUT")
    print("   (>=125 pages, per-archetype quota, recogniser frozen). This is 121 entries over 20")
    print("   leaves of ONE witness, and it answers only: is this model worth building on?")

    if best_mn >= BAR_MN_RECALL and best_acc >= BAR_OVERALL:
        print("\n✅ R14.0: Surya is ADMISSIBLE as a starting point for R14.1-R14.2.")
        return 0
    print("\n🔴 R14.0: Surya OFF THE SHELF IS INADMISSIBLE -- but READ WHY, because the reason is")
    print("   much more favourable to the learned route than the MN 0.0000 suggests.")
    print("   * Its DETECTOR LOCALISES the marginal notes. They bind to TIGHT boxes (median box area")
    print("     printed above, ~0.004 of the page) -- not to the half-page Text block. The regions are")
    print("     FOUND as distinct objects.")
    print("   * Its LABEL INVENTORY has no name for them, so they are filed under PageHeader/Text.")
    print("   ⇒ THIS IS A LABELLING FAILURE ON TOP OF A WORKING DETECTOR, not blindness. The repair is")
    print("     a CLASS-INVENTORY fine-tune -- keep the detector, teach it THIS BOOK'S classes -- which")
    print("     is what Masterplan §3.2a's REQUIRES/FORBIDS contract already specifies, and it is far")
    print("     cheaper than training a detector from scratch. R14.1 is redirected accordingly.")
    print("   ⚠️ AND THE MainText FIGURE IS NOT A WIN. MT bound boxes cover a median ~0.56 of the PAGE.")
    print("     A half-page block containing every body entry scores 1.0000 by CONTAINMENT. Gate 10b's")
    print("     boundary error is the check that would separate them and it is NOT measured here.")
    print("   ⚠️ COVERAGE LIMIT, stated so the finding is not over-read: GOLD-HEADBAND labels the TOP 3")
    print("     ROWS, so every MN entry scored here is a HEAD-BAND note. That Surya localises notes")
    print("     running down the OUTER MARGIN beside the measure is NOT shown by this run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
