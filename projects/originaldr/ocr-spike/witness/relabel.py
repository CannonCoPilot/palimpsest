"""Re-apply `label()` to stored inventories without re-reading any image.

The inventory is deliberately two-pass: `classify()` measures raw features and
`label()` interprets them.  Every feature label() needs is already in the JSON,
so a change to the interpretation costs seconds rather than the ~40 minutes an
image pass over 10 witnesses takes.  That cheapness is the point -- a threshold
nobody can afford to revise is a threshold that never gets revised.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inventory_leaves import OUT, label


def main(argv):
    targets = argv or sorted(p.stem for p in OUT.glob("*.json"))
    for wid in targets:
        p = OUT / f"{wid}.json"
        if not p.exists():
            print(f"  {wid}: no inventory"); continue
        d = json.loads(p.read_text())
        before = Counter(r.get("kind") for r in d["leaves"])
        d["leaves"] = label(d["leaves"])
        after = Counter(r["kind"] for r in d["leaves"])
        assert sum(after.values()) == d["n"], f"{wid}: counts must account for every leaf"
        p.write_text(json.dumps(d, indent=1))
        changed = "  (unchanged)" if before == after else ""
        print(f"  {wid:14s} n={d['n']:5d} " +
              " ".join(f"{k}={after[k]}" for k in sorted(after)) + changed, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
