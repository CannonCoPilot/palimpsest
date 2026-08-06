"""Negative tests for the primacy guard (roadmap R0.5).

A guard that has never rejected anything is not known to work.  Every witness
whose JP2 package is an IA render of an uploaded PDF must RAISE from
`pixel_source`, and every genuine capture must pass — asserted both ways, since
a guard that rejects everything is equally useless.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witnesses as W

FAILURES = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def main():
    print("registry coverage")
    check(set(W.PRIMARY) == set(W.WITNESSES),
          "every witness declares a primary artefact")
    check(all(k in W.PDF for k, v in W.PRIMARY.items() if v == "pdf"),
          "every pdf-primary witness names its PDF path")
    check(all(p.is_file() for p in W.PDF.values()),
          "every named PDF exists on disk")

    print("\nnegative — renders and binarised primaries must raise")
    for key in sorted(k for k, v in W.PRIMARY.items() if v == "pdf"):
        try:
            W.pixel_source(*key)
            check(False, f"{W.wid(*key)} did NOT raise")
        except ValueError as e:
            reason = "binarised" if key in W.NO_READING else "render"
            check(True, f"{W.wid(*key)} raised ({reason}): {str(e)[:58]}…")

    print("\nnegative — the binarised-primary guard, proven synthetically")
    # NO_READING is empty now that NT/R's original was acquired (R4.4).  An
    # unexercised guard is an untested one, so inject an entry and require the
    # refusal — otherwise this protection would silently rot until the next
    # re-upload of an MRC PDF entered the corpus unnoticed.
    victim = ("NT", "B")
    W.NO_READING[victim] = "synthetic — test fixture"
    try:
        W.pixel_source(*victim)
        check(False, "binarised-primary guard did NOT raise")
    except ValueError as e:
        check("no reading" in str(e), f"{W.wid(*victim)} refused while listed: {str(e)[:50]}…")
    finally:
        del W.NO_READING[victim]
    check(W.pixel_source(*victim).is_dir(), f"{W.wid(*victim)} passes again once delisted")

    print("\npositive — genuine captures must pass")
    for key in sorted(k for k, v in W.PRIMARY.items() if v == "jp2"):
        try:
            p = W.pixel_source(*key)
            check(p.is_dir(), f"{W.wid(*key)} resolves to {p.name[:34]}")
        except ValueError as e:
            check(False, f"{W.wid(*key)} wrongly raised: {e}")

    print("\nstructural access stays open for every witness")
    for key in sorted(W.WITNESSES):
        check(len(W.leaves(*key)) > 0, f"{W.wid(*key)} leaves() returns pages")

    print(f"\n{'FAILED: ' + str(len(FAILURES)) if FAILURES else 'all checks passed'}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
