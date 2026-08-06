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
            interior_blank = sum(1 for r in rec[i:j+1] if r["kind"] in ("BLANK", "PLATE", "BINDING"))
            blocks[wid] = block
            print(f"  {wid:14s} {n:6d} {i:5d} {block:6d} {n-1-j:6d} {interior_blank:9d} "
                  f"{W.WITNESSES[(vol,s)]['role']}")
        if blocks:
            ref = max(blocks.values())
            print(f"  -- book-block deltas against the largest ({ref}):")
            for wid, b in blocks.items():
                print(f"     {wid:14s} {b-ref:+5d}")

if __name__ == "__main__":
    main()
