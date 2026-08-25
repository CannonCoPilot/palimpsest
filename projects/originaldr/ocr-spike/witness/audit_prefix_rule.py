"""R2.1h -- the >=4-char prefix rule scores a WHOLE-LINE BLOB in OPPOSITE DIRECTIONS.

⚠️ AUDIT: exit 1 while the defect stands, 0 when it is closed. It is in the roadmap's audits block,
not its guards block, and it is EXPECTED to fail until R2.1h closes.

R2.1f recorded that the head reader "fails in BOTH directions" and could not size either. This
audit proves the mechanism in the SCORER, which is a separate cause from the reader:

`norm()` strips spaces, so a blob collapses to one long string. `agrees()` then accepts when the
shorter side is a prefix of the longer AND is at least 4 characters. Therefore the SAME blob shape
scores differently according to how long the catchword happens to be:

    catchword 'face'  vs blob 'faceof the earth, sit tinga'   -> AGREE     (blob rewarded)
    catchword 'two,'  vs blob 'two, the euerie lambe ...'     -> DISAGREE  (blob punished)

'two,' normalises to 'two', three letters, so the rule refuses a reading that is manifestly correct;
'face' normalises to four and the rule accepts a reading that never located a word boundary at all.
⚠️ THE LENGTH OF THE CATCHWORD IS NOT A PROPERTY OF THE INSTRUMENT, so a metric that changes sign
with it is measuring the book's vocabulary as much as the reader. This is why the rate could not be
attributed, and it is why fixing the splitter ALONE would move the number in an uninterpretable
direction: the two biases would not cancel at the same rate afterwards.

The fix is NOT to lower the 4-character floor -- that was raised deliberately in R2.1d' because a
2-character misread like 'wl' matched almost anything, and lowering it would restore that. The fix
is that the head side must present a WORD, so that a prefix comparison is comparing words. That is
R2.1h's splitter, and the two halves must close together.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import r2_1d_continuity as R2
import witnesses as W
import collation_read as CR


BLOB_LONG = "faceof the earth, sit tinga"          # leaf 401, measured
BLOB_SHORT = "two, the euerie lambe the tenth"     # leaf 414, measured (dagger dropped by norm)

# ⚠️ WHAT CLOSES THIS AUDIT, AND WHAT DOES NOT.
# The direction-dependence below is a permanent property of `agrees()` and will never stop
# reproducing -- a prefix test with a minimum length IS length-dependent, by construction. So an exit
# condition asserting that `agrees()` has changed would be asserting something that must not happen:
# the >=4-character floor was raised deliberately in R2.1d' because a 2-character misread ('wl')
# matched almost anything, and lowering it to close this audit would trade one defect for the one it
# replaced. The mechanism demonstration therefore stays as a REGRESSION CHECK on the scorer.
#
# What closes the audit is the OTHER end: the rule mis-scores BLOBS, so it stops mattering when the
# reader stops producing them. That is measurable on the reader itself, without reference to any
# catchword, and it is measured here on the window R2.1d'(A) scored 0.312 on.
LEAVES = range(400, 420)
BLOB_WIDTH_FRAC = 0.50      # a word is never half a justified line


def head_is_word(model, leaf_path):
    """-> (ok, detail). Does the production head reader return a WORD rather than a line?

    ⚠️ TWO TESTS, AND THE SECOND IS THE ONE THAT MATTERS. Checking only for an internal space is a
    criterion this audit could pass while wholly defeated: when the recogniser decodes NO space at
    all, a whole-line token comes back as one unbroken string -- leaf 417 returned
    'hpromiſſe,hal' -- and a whitespace test waves it through. The blob was never defined by
    whitespace, it was defined by a token spanning the LINE, so the token's SPAN is tested against
    the row it came from. Written after the whitespace-only version was found to be unfalsifiable in
    the direction that counts.
    """
    toks, why = CR.head_tokens(model, leaf_path, k=1)
    if not toks:
        return None, f"ABSTAIN -- {why}"        # abstention is not a blob; counted separately
    t = toks[0]
    txt = t["read"]
    frac = (t["r"] - t["l"]) / max(1.0, t["row_r"] - t["row_l"])
    if any(c.isspace() for c in txt.strip()):
        return False, f"{txt!r} carries an internal space -- more than one word"
    if frac > BLOB_WIDTH_FRAC:
        return False, (f"{txt!r} spans {frac:.0%} of its row -- a word is never that much of a "
                       f"justified line, so this is a line the recogniser decoded without spaces")
    return True, f"{txt!r} ({frac:.0%} of row)"


def main() -> int:
    cases = [
        ("face", BLOB_LONG, True, "a 4-letter catchword: the blob is REWARDED"),
        ("two,", BLOB_SHORT, False, "a 3-letter catchword: the same blob shape is PUNISHED"),
    ]
    print("R2.1h -- is the prefix rule direction-dependent on catchword length?\n")
    got = []
    for catch, head, expect_blob_passes, why in cases:
        a = R2.agrees(catch, head)
        got.append(a)
        print(f"  agrees({catch!r:8}, blob) -> {str(a):5}   {why}")
        assert a == expect_blob_passes, f"measured behaviour changed for {catch!r}"

    # The same two catchwords against a CORRECTLY SPLIT head, which is what the fix must deliver.
    print()
    for catch, word in (("face", "face"), ("two,", "two,")):
        print(f"  agrees({catch!r:8}, {word!r:8}) -> {R2.agrees(catch, word)}   (split head: correct)")

    if got[0] == got[1]:
        print("\n🔴 THE MECHANISM DEMONSTRATION STOPPED REPRODUCING. `agrees()` no longer changes")
        print("   sign with catchword length -- which means the >=4-character floor moved. That")
        print("   floor was raised in R2.1d' because 'wl' matched almost anything. Check why.")
        return 1

    print("\n" + "=" * 78)
    print("R2.1h CLOSING CRITERION -- does the READER hand this rule words or lines?\n")
    from kraken.lib import models
    model = models.load_any(str(_HERE.parent / "models/reichenau_dr.mlmodel"))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    blobs, words, absts = [], 0, []
    for i in LEAVES:
        ok, detail = head_is_word(model, leaves[i])
        if ok is None:
            absts.append((i, detail))
        elif ok:
            words += 1
        else:
            blobs.append((i, detail))
        print(f"  leaf {i}: {'WORD   ' if ok else ('ABSTAIN' if ok is None else '🔴 BLOB ')} {detail}")

    print(f"\n  words {words} · blobs {len(blobs)} · abstentions {len(absts)} "
          f"(of {len(list(LEAVES))} leaves)")
    if absts:
        print("  ⚠️ abstentions are NOT successes and NOT blobs; they are counted here so that a")
        print("     reader that closed this audit by refusing to read would be visible:")
        for i, d in absts:
            print(f"       leaf {i}: {d}")
    if blobs:
        print("\n🔴 DEFECT STANDS. The reader still hands the prefix rule multi-word readings, so")
        print("   the continuity rate still mixes an instrument property with a vocabulary one.")
        return 1
    print("\n✅ CLOSED. Every leaf the reader reads, it reads as a single WORD, so `agrees()` is")
    print("   comparing a catchword against a word. The rule's length-dependence is unchanged and")
    print("   still real -- it simply no longer decides the sign of a blob comparison.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
