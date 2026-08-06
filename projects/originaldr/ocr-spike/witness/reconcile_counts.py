"""Account for every leaf-count difference between witnesses of one volume.

Splits each witness into leading matter / book block / trailing matter by
position, not by totals, so the arithmetic is checkable leaf by leaf.
"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witnesses as W

INV = Path(__file__).resolve().parent.parent / ".scratch" / "inventory"
NONBOOK = {"BINDING", "PLATE", "BLANK", "SPARSE"}

def split(rec):
    """Leading and trailing runs of non-text material bound the book block."""
    n = len(rec)
    i = 0
    while i < n and rec[i]["kind"] in NONBOOK: i += 1
    j = n - 1
    while j >= 0 and rec[j]["kind"] in NONBOOK: j -= 1
    return i, j, n

def load(wid):
    p = INV / f"{wid}.json"
    return json.loads(p.read_text())["leaves"] if p.exists() else None

def main():
    for vol in ("NT", "OT1", "OT2"):
        sigs = [s for (v, s) in W.WITNESSES if v == vol]
        print(f"\n=== {vol}")
        print(f"  {'witness':14s} {'total':>6s} {'lead':>5s} {'block':>6s} {'trail':>6s} "
              f"{'blank-in':>9s} {'role'}")
        blocks = {}
        for s in sigs:
            wid = W.wid(vol, s); rec = load(wid)
            if rec is None:
                print(f"  {wid:14s}  (inventory not yet built)"); continue
            i, j, n = split(rec)
            block = j - i + 1
            # A witness whose ink floor left BLANK/SPARSE unresolvable carries
            # TEXT? leaves.  Printing 0 interior blanks for it would report a
            # measurement that was never taken, and a reader would take the
            # zero for the finding "this copy has no interior blanks".
            unresolved = any(r["kind"] == "TEXT?" for r in rec)
            ib = ("n/a" if unresolved else
                  str(sum(1 for r in rec[i:j+1] if r["kind"] in ("BLANK", "PLATE", "BINDING"))))
            # Leading and trailing runs are bounded by NONBOOK kinds, two of
            # which (BLANK, SPARSE) cannot fire on an unresolvable witness.  So
            # its lead/trail are LOWER BOUNDS -- a blank flyleaf would read as
            # book block.  Marked '+' rather than printed as if counted.
            b = "+" if unresolved else " "
            blocks[wid] = block
            print(f"  {wid:14s} {n:6d} {i:4d}{b} {block:5d}{b} {n-1-j:5d}{b} {ib:>9s} "
                  f"{W.WITNESSES[(vol,s)]['role']}"
                  f"{'  [BLANK/SPARSE unresolvable; lead/trail are lower bounds]' if unresolved else ''}")
        if blocks:
            ref = max(blocks.values())
            print(f"  -- book-block deltas against the largest ({ref}):")
            for wid, b in blocks.items():
                print(f"     {wid:14s} {b-ref:+5d}")

if __name__ == "__main__":
    main()
