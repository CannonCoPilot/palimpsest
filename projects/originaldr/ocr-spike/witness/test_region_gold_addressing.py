"""R2.1i GUARD -- a splitter change must not MISBIND a gold label. Exit 0 healthy, 1 on regression.

⚠️ WHY THIS GUARD EXISTS, MEASURED. The region gold was keyed by TOKEN ORDINAL. An ordinal is an
index into a list whose length depends on the splitter, so it is not an address. Wiring R2.1h's
tokeniser into `region_head` collapsed the R2.1g score -- MarginNote recall 0.8947 -> 0.5263,
unlabelled 80 -> 212 -- with NOT ONE REGION HAVING CHANGED. An instrument that reads tokenisation
work as a region regression punishes progress, and it would have done so silently for every future
splitter improvement. That is the failure this guard makes impossible to reintroduce.

⚠️ THE PRE-REGISTERED CRITERION WAS WRONG AS WRITTEN, AND IS CORRECTED HERE IN THE OPEN.
R2.1i pre-registered *"perturb the splitter and the region score must be UNCHANGED."* Executed, that
is UNACHIEVABLE, and not because the addressing is bad. The region rules legitimately consume token
GEOMETRY -- R5 asks where a token's centre sits -- so cutting `NVMERI.` into `NVME` + `RI.` moves
both fragments' centres and one falls outside the middle half. Measured: under a 0.4x splitter the
scored count, collisions and orphans are ALL unchanged (121 / 0 / 0, every label bound) while RH
recall still moves. Nothing was misaddressed; the tokens genuinely differ. The original wording
conflated an ADDRESSING failure with a MODELLING consequence.

⚠️ AND THE FIRST REPLACEMENT WAS WRONG TOO -- recorded, not quietly dropped. "Same token => same
label" still failed, on tokens the splitter had NOT re-cut, and the flips were cases where the
perturbed splitter produced the BETTER label. Cause: `region_head.block_measure` estimates the text
measure FROM TOKEN EDGES, so any splitter change moves the measure and with it every in-block
decision -- for tokens it never touched. So that formulation was ALSO a modelling test wearing an
addressing test's clothes. ⚠️ TWO WRONG CRITERIA IN ONE STEP, both kept on the record: the region
OUTPUT cannot be stable under a splitter change, because the splitter is one of the model's INPUTS.
What can be required, and is required below, is that a label is never SCORED against a token it does
not overlap. That is the whole of what v1 got wrong.

PRE-REGISTERED CRITERIA (v2, 2026-08-17), both required:
  A. ⚠️ BINDING FIDELITY. Every SCORED entry must bind to a token overlapping at least half of the
     gold span. Checked WITHOUT reference to any region label, which is what makes it a test of the
     ADDRESS rather than of the model. v1 had no such clause at all: it bound by ordinal, so a label
     read off 'NVMERI' could be scored against a token reading 'deuoured Ar of the Moabites' and the
     disagreement counted as a region error. Below the threshold the entry is an ORPHAN -- reported
     and unscored, never bound to whatever happens to be nearest.
  B. ⚠️ ACCOUNTING. Any change in the number of scored tokens must be FULLY ACCOUNTED FOR by
     reported drops. Unaccounted loss is the exact signature of silent misbinding, and it is what
     the ordinal keying produced. A gold set may lose a label to a merge -- it may not lose one to
     bookkeeping.
     ⚠️ R2.2l, 2026-08-21: the reported drops are collisions, orphans AND ambiguous-collisions.
     The third was missing from BOTH the scorer and this list, and the guard duly failed on it under
     the adopted `ink2d` address. The enumeration, not the invariant, was wrong -- so the scorer now
     reports that sink and it is counted here. Anything that still does not balance is a real leak.

⚠️ Perturbations are applied to the SPLITTER ONLY. Nothing here touches the region rules.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import collation_read as CR
import score_head_regions as S

def quantile_splitter(row, p):
    """R2.1h's estimator -- the real perturbation of interest, not a synthetic one."""
    return CR.row_word_gap(row, p, CR._word_gap(row, p))


def coarse(row, p):
    """Deliberately over-merging: forces collisions, so the accounting clause is actually exercised."""
    return int(round(1.6 * CR._word_gap(row, p)))


def fine(row, p):
    """Deliberately over-splitting: forces orphans and unlabelled tokens."""
    return max(3, int(round(0.4 * CR._word_gap(row, p))))


def main() -> int:
    base = S.main(gap_fn=None, quiet=True)
    print("R2.1i -- is the region gold addressed independently of the splitter?\n")
    print(f"  baseline        pairs {base['pairs']:3d}  acc {base['acc']:.4f}  "
          f"RH {base['rh']:.4f}  MN {base['mn']:.4f}  coll {base['coll']} orph {base['orph']}")

    ok = True
    for name, fn in (("R2.1h-quantile", quantile_splitter), ("coarse x1.6", coarse),
                     ("fine x0.4", fine)):
        r = S.main(gap_fn=fn, quiet=True)
        lost = base["pairs"] - r["pairs"]
        # R2.2l. 🔴 THIS ENUMERATION WAS INCOMPLETE AND THE TEST WAS RIGHT TO FAIL ON IT.
        # `score_head_regions.main` has a THIRD sink: an entry that binds a token an AMBIGUOUS gold
        # entry also binds is dropped rather than scored. It is the same event as a collision -- the
        # splitter merged two labelled spans into one token -- but it was neither counted nor
        # printed, so every drop through it read here as a token vanishing for no stated reason.
        # ⚠️ This is NOT a relaxation. The scorer now REPORTS that sink (`ambcoll`, one increment
        # site, printed like the others) and it is counted here for the same reason collisions and
        # orphans are: the invariant is "nothing disappears UNREPORTED", not "nothing disappears".
        # Measured before the change: `ambcoll` is 1 in the one failing cell and 0 in the other five,
        # so counting it closes the gap without loosening any cell that already balanced.
        accounted = r["coll"] + r["orph"] + r["ambcoll"]
        flag = []

        # Criterion A -- BINDING FIDELITY. Every scored entry must bind to a token that actually
        # overlaps it. This is checked without reference to any region LABEL, which is what makes
        # it a test of the address rather than of the model.
        weak = []
        for k, (tl, tr, _) in r["bind"].items():
            _, _, gl, gr = k
            ov = max(0.0, min(gr, tr) - max(gl, tl))
            if ov < S.MIN_BIND_FRAC * max(1.0, gr - gl):
                weak.append((k, ov / max(1.0, gr - gl)))
        if weak:
            flag.append(f"{len(weak)} entry/entries SCORED against a token they barely overlap")

        # Criterion B -- ACCOUNTING.
        if lost > accounted:
            flag.append(f"{lost - accounted} token(s) lost WITHOUT a reported collision, orphan "
                        f"or ambiguous-collision")

        # REPORTED, NOT FAILED: the region numbers themselves. `block_measure` estimates the text
        # measure FROM TOKEN EDGES, so a splitter change legitimately moves the measure and with it
        # every in-block decision. That is the model consuming its input, not the gold losing track
        # of a label -- and conflating the two is what the first two versions of this test did.
        print(f"  {name:15} pairs {r['pairs']:3d}  acc {r['acc']:.4f}  "
              f"RH {r['rh']:.4f}  MN {r['mn']:.4f}  coll {r['coll']} orph {r['orph']} amb {r['ambcoll']}  "
              f"| weak {len(weak)}  lost {lost} accounted {accounted}"
              + ("   ok" if not flag else "   🔴 " + "; ".join(flag)))
        for k, frac in weak:
            print(f"      🔴 leaf {k[0]} row {k[1]} span ({k[2]:.0f},{k[3]:.0f}): "
                  f"only {frac:.2f} of the gold span overlaps its bound token")
        ok = ok and not flag

    print()
    if ok:
        print("✅ addressing is by SPAN and holds under every perturbation: nothing was scored")
        print("   against a token it does not overlap, and every label the perturbation costs")
        print("   is reported as a collision, an orphan or an ambiguous-collision. NUMBERS move, and")
        print("   is correct -- the splitter is one of the region model's inputs.")
        return 0
    print("🔴 the gold MISBINDS under a splitter change -- labels are being scored against")
    print("   tokens they do not overlap, so tokenisation work will read as region regression.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
