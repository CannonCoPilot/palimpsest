#!/usr/bin/env python3
"""test_setting_guard.py — a witness may only be collated within its own setting.

Roadmap R8.  For four months the plan recorded NT/S01 as `NT-1582-F`, an
independent witness to the 1582 Rhemes New Testament.  Its body is the 1633
Rouen setting.  Nothing in the code contradicted the claim, because the year sat
in a dict field that only `wid()` ever read, and no consumer asked whether two
sigla attested the same edition before comparing them.

The failure mode is quiet, which is why it needs a test rather than a note: two
editions of one translation agree for pages at a time, so a conflation surfaces
only where they differ — precisely the loci a documentary edition exists to
report.

Both directions are exercised.  A guard that has only ever passed is not known
to work.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from witness import witnesses as W  # noqa: E402

FAILURES: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}{(' -- ' + detail) if detail and not cond else ''}")
    if not cond:
        FAILURES.append(label)


def main() -> int:
    print("settings present per volume:")
    for vol in ("NT", "OT1", "OT2"):
        years = sorted({W.WITNESSES[(v, s)]["year"] for (v, s) in W.WITNESSES if v == vol})
        for y in years:
            print(f"  {vol} {y}: {W.witnesses_to(vol, y)}")

    print("\npositive — sigla within one setting are collatable:")
    check("NT 1582 = B, M, X", W.witnesses_to("NT", 1582) == ["B", "M", "X"],
          f"got {W.witnesses_to('NT', 1582)}")
    check("NT 1633 = F, R", W.witnesses_to("NT", 1633) == ["F", "R"],
          f"got {W.witnesses_to('NT', 1633)}")
    check("assert_same_setting(NT, B, X, M) passes", W.assert_same_setting("NT", "B", "X", "M"))
    check("assert_same_setting(NT, F, R) passes", W.assert_same_setting("NT", "F", "R"))
    for vol, yr in (("OT1", 1609), ("OT2", 1610)):
        check(f"{vol} {yr} = B, F, P", W.witnesses_to(vol, yr) == ["B", "F", "P"],
              f"got {W.witnesses_to(vol, yr)}")
        check(f"assert_same_setting({vol}, B, P, F) passes", W.assert_same_setting(vol, "B", "P", "F"))

    print("\nNEGATIVE — the guard must REFUSE a cross-edition collation:")
    for a, b in (("B", "F"), ("B", "R"), ("X", "F"), ("M", "R")):
        try:
            W.assert_same_setting("NT", a, b)
            check(f"NT {a}+{b} refused", False, "it was ALLOWED")
        except ValueError:
            check(f"NT {a}+{b} refused", True)

    print("\nthe id itself must carry the edition:")
    check("wid(NT,F) == NT-1633-F", W.wid("NT", "F") == "NT-1633-F", f"got {W.wid('NT', 'F')}")
    check("wid(NT,B) == NT-1582-B", W.wid("NT", "B") == "NT-1582-B", f"got {W.wid('NT', 'B')}")
    check("NT-1633-F != NT-1633-R", W.wid("NT", "F") != W.wid("NT", "R"))

    print("\nregression — no NT witness may claim 1582 unless its body is 1582:")
    check("F is not registered as 1582", W.WITNESSES[("NT", "F")]["year"] != 1582)

    print("\nattests_transcribed_setting — which witnesses may carry the TEXT:")
    check("NT B attests 1582", W.attests_transcribed_setting("NT", "B") is True)
    check("OT1 P attests 1609", W.attests_transcribed_setting("OT1", "P") is True)
    # The negative case is the whole point: this is the call that reclassifies the 9
    # ground-truth files read from F's New Testament.
    check("NT F REJECTED (1633)", W.attests_transcribed_setting("NT", "F") is False)
    check("NT R REJECTED (1633)", W.attests_transcribed_setting("NT", "R") is False)
    # ...and it must not fire on the volume admitted BECAUSE it is another edition.
    # `False` and `None` are different answers and a bool test would conflate them.
    check("OT M -> None, not False", W.attests_transcribed_setting("OT", "M") is None,
          f"got {W.attests_transcribed_setting('OT', 'M')!r}")
    check("OT1 F still attests 1609", W.attests_transcribed_setting("OT1", "F") is True)

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}\n---")
        for f in FAILURES:
            print(f"  {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
