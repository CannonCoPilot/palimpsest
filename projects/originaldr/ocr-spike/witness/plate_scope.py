#!/usr/bin/env python
"""Stamp per-leaf SCOPE decisions onto the existing plate book, and count what is left.

Why this exists separately from `plate_book.py --build`: rebuilding re-runs Surya over every
leaf, and a scope decision changes no geometry. This applies the decision in place. The build
path reads the same `plates/scope.json`, so a later rebuild carries it forward.

A leaf is OUT OF SCOPE only when its objects have no correct label available in `CLASSES` —
title page, key to the marks, table of contents, argument/summary pages. That is a claim about
the class set, not about the leaf.

⚠️ OUT OF SCOPE IS NOT A PASS. An out-of-scope leaf contributes nothing to GOLD-LAYOUT and is
counted apart from it. This script therefore always reports the IN-SCOPE count against R16.1's
≥125-leaf bar, and says plainly when that bar stops being met. Shrinking the denominator until
a bar is cleared is exactly the laundering this project forbids.

Safe with no arguments: reports only. Pass --apply to write.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLATES = os.path.join(HERE, "plates")
BUNDLE = os.path.join(PLATES, "bundle.json")
SCOPE = os.path.join(PLATES, "scope.json")
BAR = 125  # R16.1: GOLD-LAYOUT needs >= 125 leaves to clear its bar


def main(apply: bool) -> int:
    if not os.path.exists(BUNDLE):
        print(f"FAIL no bundle at {BUNDLE}", file=sys.stderr)
        return 1
    bundle = json.load(open(BUNDLE))
    scope = json.load(open(SCOPE)).get("leaves", {}) if os.path.exists(SCOPE) else {}

    for p in bundle["plates"]:
        d = scope.get(p["id"], {})
        p["scope"] = d.get("scope", "in")
        p["scope_why"] = d.get("why", "")
        # R16.5 — a leaf READMITTED by widening CLASSES, not one that was always in. Carried onto
        # the bundle so the review tool can show it and so the count below is derived, not asserted.
        p["scope_readmitted"] = d.get("was") == "out"
        p["scope_blocker"] = d.get("residual_blocker", "")

    inn = [p for p in bundle["plates"] if p["scope"] == "in"]
    out = [p for p in bundle["plates"] if p["scope"] != "in"]

    by_w: dict[str, list] = {}
    for p in inn:
        by_w.setdefault(p["witness"], []).append(p)

    print(f"plates      : {len(bundle['plates'])}")
    print(f"IN SCOPE    : {len(inn)}")
    for w in sorted(by_w):
        print(f"                {w} {len(by_w[w])}")
    print(f"OUT OF SCOPE: {len(out)}  (no correct label available in CLASSES)")
    for p in out:
        print(f"                {p['id']}  {p['scope_why']}")

    # 🔴 R16.5 — THE READMITTED LEAVES, COUNTED APART. A denominator that grows because the class
    # set widened is NOT the same evidence as a denominator that was always there, and reporting
    # 208-in without this line would let an ontology edit read as 18 leaves of new gold. It is the
    # exact mirror of the warning above: shrinking the denominator to clear a bar is laundering, and
    # so is growing it and saying nothing.
    re_in = [p for p in inn if p.get("scope_readmitted")]
    if re_in:
        print(f"\nREADMITTED by R16.5 (CLASSES widened): {len(re_in)}")
        print("   ⚠️ THESE ARE NOT LEAVES THE AGENT NOW GETS RIGHT. A correct answer EXISTS for their")
        print("   objects; no cue emits it. They are wrong VISIBLY instead of being excluded, which")
        print("   is the whole gain — an excluded leaf produces no signal at all.")
        blocked = [p for p in re_in if p.get("scope_blocker")]
        if blocked:
            print(f"   of these, {len(blocked)} now block on DETECTION or the FRAME, not on the class set:")
            for p in blocked:
                print(f"      {p['id']}  {p['scope_blocker']}")

    if len(inn) >= BAR:
        print(f"\nR16.1 bar >= {BAR}: MET by the in-scope set ({len(inn)}).")
    else:
        print(f"\n🔴 R16.1 bar >= {BAR}: NOT MET — {len(inn)} in scope, short by {BAR - len(inn)}.")
        print("   This is an ALERT on the approach, not an acceptance. GOLD-LAYOUT stays OPEN and")
        print("   blocks the deliverable until either more leaves are gathered or CLASSES is")
        print("   widened so the excluded genres have a correct answer.")

    if apply:
        # 🔴 THE BUNDLE CARRIES A COPY OF `CLASSES` AND THE REVIEW TOOL READS IT. Written by
        # `plate_book.py --build`, which re-runs Surya — so before R16.5 the only way to refresh it
        # was to redo the perception, and a scope edit would have left the tool offering the OLD
        # nine classes for leaves readmitted BY the six new ones. Stamped here from the one
        # declaration, for the same reason `score_foreedge` stopped keeping its own copy.
        sys.path.insert(0, HERE)
        import visual_agent as VA
        was = list(bundle.get("classes", []))
        if was != list(VA.CLASSES_ORDERED):
            added = sorted(set(VA.CLASSES) - set(was))
            # ⚠️ ORDER-ONLY AND INVENTORY CHANGES ARE REPORTED APART. Printing "15 -> 15 (+)" for a
            # reordering reads as a no-op that still rewrote the file, which is how a real change
            # gets skimmed past. The review tool's button row depends on the order, so a reorder is
            # a genuine change to what a person sees, and it says so in those words.
            print(f"\nclass inventory REFRESHED: {len(was)} -> {len(VA.CLASSES)}  (+{' '.join(added)})"
                  if added else
                  f"\nclass ORDER refreshed ({len(was)} classes, inventory unchanged) — the review "
                  f"tool's button row follows this order")
            bundle["classes"] = list(VA.CLASSES_ORDERED)
        json.dump(bundle, open(BUNDLE, "w"), indent=1, ensure_ascii=False)
        print(f"\nwritten -> {BUNDLE}")
    else:
        print("\n(report only — pass --apply to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
