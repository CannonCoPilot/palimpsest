#!/usr/bin/env python3
"""test_drop_rule_enforced.py -- a rule nothing enforces is not a rule.

`witness_inventory` declares `S6: {"drop_tomes": ["NT"]}` and describes it as a SCORING rule:
S6's New Testament pages are not to be counted as a witness, because they repeat the 1582
edition already carried by A, B and C.  R7.5a-3 established what that declaration was
actually doing: `page_address_eval.volume_books()` read it as a CONTAINMENT claim and built
the addressing DP's state space from it, which force-fitted 800 New Testament leaves onto
Old Testament books.  That misreading was the rule's ONLY effect anywhere in the system.

The misreading is fixed.  What the fix exposed is that no scorer has ever read the rule.
While the addressing was broken, S6's NT could not localize a verse, so the drop appeared to
be in force -- it was being enforced by a defect.  With the addressing corrected, S6 enters
the coverage audit as an attesting witness for matthew (1,067), john (877) and apocalypse
(400), and nothing in the codebase has an opinion about whether it should.

This guard fails while that is true.  It does not decide the question -- the answer is a
judgement about evidence, and there is a real argument on the other side: the drop's stated
justification is that S6's NT is a redundant repeat, and Session 9 established that the NT
has ONE witness to its own setting (B; F is 1633, X is B upscaled).  NT-1582-M is a genuine
1582 Rheims setting, so it is not redundant, and the justification for dropping it may not
survive the finding.  Retire the rule or enforce it; what must not continue is a declaration
that reads as policy, is cited as policy, and does nothing.

Exit 1 while any declared drop has no consumer.  Exit 0 when every one is either enforced by
a listed consumer or removed from the registry.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(SPIKE))
import witness_inventory as WI  # noqa: E402

# Modules that mention `drop_tomes` WITHOUT enforcing it. Listed by name so that adding a real
# consumer is what makes this guard pass -- a new mention cannot pass it by accident.
NON_CONSUMERS = {
    "witness_inventory.py",              # the declaration itself, and its summary print
    "corpus_localize.py",                # reports a drop when explaining an empty result; does not apply it
    "witness/test_drop_rule_enforced.py",  # this file
}


def consumers() -> list[str]:
    """Files that read `drop_tomes` and are not on the known non-consumer list."""
    out = []
    for p in sorted(SPIKE.rglob("*.py")):
        rel = str(p.relative_to(SPIKE))
        if "__pycache__" in rel or rel.startswith(".superseded") or rel in NON_CONSUMERS:
            continue
        try:
            t = p.read_text()
        except OSError:
            continue
        if re.search(r"\bdrop_tomes\b", t):
            out.append(rel)
    return out


def main() -> int:
    declared = {sid: w["drop_tomes"] for sid, w in WI.WITNESSES.items() if w.get("drop_tomes")}
    found = consumers()
    print("declared scoring drops:")
    for sid, tomes in sorted(declared.items()):
        print(f"  {sid}: {tomes}")
    if not declared:
        print("\nno scoring drop is declared; nothing to enforce.")
        return 0
    print(f"\nconsumers that read the rule: {found or 'NONE'}")
    if found:
        print("\nthe declared drop(s) are read by a scorer.")
        return 0
    print("\nOPEN — the rule is declared and cited and NOTHING READS IT. Until R7.5a-3 it was\n"
          "enforced by a defect: S6's NT could not localize a verse because its leaves were\n"
          "addressed to Old Testament books. With the addressing corrected S6 attests\n"
          "matthew/john/apocalypse and no scorer has an opinion about it.\n"
          "Decide: enforce the drop in the scorer, or retire it from the registry with the\n"
          "reason recorded. Exit 1 is the healthy state until one of those happens.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
