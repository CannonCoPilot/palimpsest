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

def orphaned_by_resigla(vol, sig):
    """An inventory built under a siglum the registry has since retired.

    Inventories are keyed by `wid()`, which carries the YEAR, so correcting a
    witness's edition orphans its file.  The miss then prints as "not yet
    built" -- a well-formed absence that reads as work outstanding, when the
    work was done and the label moved.  That is the R1.4 fault exactly: an
    unmeasurable state must not be reported as a measured one.  Returns the
    stale path and the wid it was built under, or None.
    """
    for p in sorted(INV.glob("*.json")):
        parts = p.stem.split("-")
        if len(parts) == 3 and parts[0] == vol and parts[2] == sig:
            return p, p.stem
    return None


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
                stale = orphaned_by_resigla(vol, s)
                if stale:
                    p, built_as = stale
                    print(f"  {wid:14s}  ⚠ STALE -- inventory exists as {built_as}.json, built "
                          f"under a RETIRED siglum. It is NOT missing work: re-key or rebuild "
                          f"it before reading. ({p.name})")
                else:
                    print(f"  {wid:14s}  (inventory not yet built)")
                continue
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
            blocks[wid] = (block, W.setting(vol, s)[1])
            print(f"  {wid:14s} {n:6d} {i:4d}{b} {block:5d}{b} {n-1-j:5d}{b} {ib:>9s} "
                  f"{W.WITNESSES[(vol,s)]['role']}"
                  f"{'  [BLANK/SPARSE unresolvable; lead/trail are lower bounds]' if unresolved else ''}")
        # Deltas are computed WITHIN a setting, never across.  A leaf-count
        # difference between two editions attributes nothing -- it is not a
        # measurement of completeness, it is two different books being
        # subtracted.  This table previously reported F at -36 against the 1582
        # base, which is the number the dissolved R3.5 spent weeks trying to
        # attribute leaf by leaf.  `assert_same_setting()` existed and this
        # consumer never called it; a guard nothing calls guards nothing.
        for year in sorted({y for _, y in blocks.values()}):
            group = {w: b for w, (b, y) in blocks.items() if y == year}
            ref = max(group.values())
            others = [w for w in blocks if blocks[w][1] != year]
            print(f"  -- book-block deltas within the {year} setting, "
                  f"against the largest ({ref}):")
            if len(group) == 1:
                print(f"     {next(iter(group)):14s}    -- sole witness to this setting; "
                      f"nothing to compare it against")
            else:
                for wid, b in group.items():
                    print(f"     {wid:14s} {b-ref:+5d}")
            if others:
                print(f"     (not compared -- different setting: {', '.join(sorted(others))})")

if __name__ == "__main__":
    main()
