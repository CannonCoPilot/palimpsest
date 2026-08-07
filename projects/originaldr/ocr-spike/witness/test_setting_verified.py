"""R8.4 — every witness is VERIFIED for its setting, or NAMED as unverified.

The `F` error was not caught by a test.  It was caught by chasing an
unrelated leaf-count discrepancy, four months after the claim was made, and
what made that possible is that "this witness attests the 1582 setting" was
recorded in a dict field no code path ever checked against evidence.

So the point of this test is NOT that the corpus is currently sound.  It is
that a witness can never again be *silently* assumed sound: a record with no
readings FAILS, rather than passing by absence.  Absence of evidence must
present as absence, which is the R1.4 lesson applied to provenance.

Criterion (roadmap R8.4): a witness is verified when it agrees with a partner
in the same claimed setting at >= MIN_POINTS separated printed pages -- same
printed page number, same running head, same text and line breaks.

Two things are deliberately NOT accepted as verification:
  * a constant leaf offset.  It corroborates and it is cheap, but two
    different editions of one translation can run parallel for pages; the
    offset is a property of the binding, the page number is a property of the
    setting.
  * a title page.  That is exactly what `F` borrowed.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witnesses as W

READINGS = Path(__file__).resolve().parent / "setting-readings.json"
MIN_POINTS = 3

# A witness that is the ONLY record of its setting cannot be collated against a
# partner, because there is no partner.  That is a structural fact about the
# corpus, not a verification, and it is listed here so it is stated rather than
# inferred from silence.  The value is what the setting DOES rest on, which is
# always weaker than a collation and must be described as such.
SOLE_WITNESS = {
    "OT-1635-M": "its own colophon (Rouen, Iohn Cousturier, M.DC.XXXV) and the "
                 "ten-year privilege of 3 August 1634 that it prints -- internal "
                 "evidence only, uncorroborated by any second copy",
}

FAILURES = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILURES.append(f"{label}: {detail}")


def main():
    d = json.loads(READINGS.read_text())
    readings, pairs = d["readings"], d["verified_pairs"]
    registered = {W.wid(v, s) for (v, s) in W.WITNESSES}

    print("every registered witness must appear in the readings file:")
    for wid in sorted(registered):
        check(f"{wid:14s} has readings", wid in readings,
              "no readings recorded -- a witness with no evidence is UNVERIFIED, "
              "and must be named so, not omitted")

    print("\nand the readings file may not carry a witness the registry does not:")
    for wid in sorted(readings):
        check(f"{wid:14s} is registered", wid in registered, "stale entry")

    # A pair is a CLAIM about the readings, and a claim that cites no reading is
    # exactly the drift these guards exist to stop -- asserted in one file,
    # unsupported in the one holding the evidence.  Every page a pair cites must
    # be present in BOTH witnesses' readings, or the pair is fiction.
    print("\nevery page a pair claims must be present in BOTH witnesses' readings:")
    pages_of = {w: {r["page"] for r in rs if r.get("page") is not None}
                for w, rs in readings.items()}
    for p in pairs:
        a, b = p["a"], p["b"]
        missing = {"a": sorted(set(p["pages"]) - pages_of.get(a, set())),
                   "b": sorted(set(p["pages"]) - pages_of.get(b, set()))}
        check(f"{a:14s} vs {b:14s} pages {p['pages']} are attested",
              not missing["a"] and not missing["b"],
              f"{a} lacks {missing['a']}; {b} lacks {missing['b']}")

    print(f"\neach witness agrees with a same-setting partner at >= {MIN_POINTS} "
          f"separated printed pages:")
    verified = {}
    for wid in sorted(registered):
        pts = set()
        partners = set()
        for p in pairs:
            if wid in (p["a"], p["b"]):
                other = p["b"] if p["a"] == wid else p["a"]
                # A pair only counts if BOTH sides really claim the same setting
                # in the registry.  Otherwise the readings file could assert a
                # verification the registry contradicts -- the exact drift
                # test_counts_vs_doc exists to stop for the leaf counts.
                va, sa = next(k for k in W.WITNESSES if W.wid(*k) == wid)
                vb, sb = next(k for k in W.WITNESSES if W.wid(*k) == other)
                if W.setting(va, sa) != W.setting(vb, sb):
                    check(f"{wid} vs {other}: registry agrees they share a setting",
                          False, f"{W.setting(va,sa)} vs {W.setting(vb,sb)}")
                    continue
                pts |= set(p["pages"])
                partners.add(other)
        verified[wid] = (pts, partners)
        if wid in SOLE_WITNESS:
            continue
        check(f"{wid:14s} {len(pts)} matched pages, partners {sorted(partners) or '-'}",
              len(pts) >= MIN_POINTS,
              f"only {len(pts)} matched printed page(s); the criterion is {MIN_POINTS}")

    print("\nsole witnesses to a setting -- NOT verified, and said so:")
    for wid, basis in sorted(SOLE_WITNESS.items()):
        same = [W.wid(v, s) for (v, s) in W.WITNESSES
                if W.wid(v, s) != wid
                and W.setting(v, s) == W.setting(*next(k for k in W.WITNESSES
                                                       if W.wid(*k) == wid))]
        # If a partner ever arrives, this entry is stale and the witness must be
        # collated for real rather than left on the exemption list.
        check(f"{wid:14s} still has no same-setting partner", not same,
              f"partner(s) now exist ({same}) -- collate and remove from SOLE_WITNESS")
        print(f"        rests on: {basis}")

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}\n---")
        for f in FAILURES:
            print(f"  {f}")
        return 1
    n_ver = sum(1 for w in registered if w not in SOLE_WITNESS)
    print(f"all checks passed — {n_ver} of {len(registered)} witnesses collated against "
          f"a same-setting partner; {len(SOLE_WITNESS)} named as sole witness, not assumed sound")
    return 0


if __name__ == "__main__":
    sys.exit(main())
