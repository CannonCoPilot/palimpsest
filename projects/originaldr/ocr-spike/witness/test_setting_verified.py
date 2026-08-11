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

# Two printed pages closer together than this are ONE point: they sit in the same gathering and
# often the same forme, so they cannot corroborate each other about the volume as a whole. 50 is
# chosen as the weakest statement that separates the real clusters actually recorded
# ([222,223,224] vs 457 vs [918,919,920]) -- it is not tuned, and widening it would only make the
# criterion stricter. Same discipline as the 0.5 fit floor in `build_tome_map_v2` (R7.5a-3).
MIN_SEPARATION = 50


def separated(pages) -> list[list[int]]:
    """Group printed pages into clusters no closer than MIN_SEPARATION. One cluster = one point."""
    out: list[list[int]] = []
    for p in sorted(pages):
        if out and p - out[-1][-1] < MIN_SEPARATION:
            out[-1].append(p)
        else:
            out.append([p])
    return out

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

# The criteria masterplan 0.3 actually names.  Kept as data so the test states
# the constitution rather than paraphrasing it.
FOOT_CRITERIA = ("signature", "catchword", "last_line")

FAILURES = []


def norm(v):
    """Compare readings without being defeated by compositor's spacing.

    `OT2-1610-B` sets its signature `Gg2` and `OT2-1610-P` sets the same sort as
    `G g 2`.  Inter-character space in a signature is a compositor's spacing
    decision within one setting, not a difference of setting, so it is normalised
    away.  Nothing else is: case, glyph identity (`ſ` is not `s`) and punctuation
    all stand, because those DO distinguish settings.
    """
    return None if v is None else "".join(str(v).split())


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILURES.append(f"{label}: {detail}")


def check_foot(d, registered):
    """R8.4a — the FOOT criteria of masterplan 0.3: signature and catchword.

    The head pass verified page number, running head, sidehead and line breaks.
    0.3 names signature, catchword and line-end words, and the first two live at
    the foot of the leaf where a head crop cannot see them.  This section holds
    the method to 0.3 instead of holding 0.3 to the method.
    """
    foot = d.get("foot_readings")
    if not foot:
        check("foot readings recorded at all", False,
              "0.3 requires signature and catchword; no foot readings exist")
        return

    print("\n0.3 FOOT criteria — every witness with a partner has foot readings:")
    for wid in sorted(registered):
        if wid in SOLE_WITNESS:
            continue          # no partner exists, so no pair can be formed
        check(f"{wid:14s} has foot readings", wid in foot,
              "no signature/catchword reading -- 0.3's criterion is unverified for "
              "this witness, and must be named so rather than implied by the head pass")

    # Index by (wid, page) so a pair's claim can be resolved to the actual reading.
    by = {}
    for wid, rs in foot.items():
        for r in rs:
            by[(wid, r["page"])] = r

    print("\nand every foot pair AGREES on signature, catchword and last line:")
    for p in d.get("foot_pairs", []):
        a, b = p["a"], p["b"]
        for page in p["pages"]:
            ra, rb = by.get((a, page)), by.get((b, page))
            if ra is None or rb is None:
                check(f"{a} vs {b} @{page}: both readings present", False,
                      f"missing reading for {a if ra is None else b}")
                continue
            for crit in FOOT_CRITERIA:
                va, vb = norm(ra.get(crit)), norm(rb.get(crit))
                # Both None is agreement: a verso carries no signature, and that
                # is a fact about the gathering, not a disagreement.
                check(f"{a:12s} vs {b:12s} @{page} {crit:10s} {ra.get(crit)!r}",
                      va == vb, f"{a}={va!r} but {b}={vb!r}")

    # A criterion that has never DISTINGUISHED anything is not known to work --
    # the same standard R0.5 and R5.2b are held to.  The negative control is the
    # load-bearing half of this section.
    print("\nnegative control — the foot criteria must SEPARATE different settings:")
    ncs = d.get("foot_negative_controls", [])
    check("at least one negative control is recorded", bool(ncs),
          "without one, agreement across a setting boundary would pass unnoticed")
    for nc in ncs:
        differs = [c for c in ("signature", "catchword")
                   if norm(nc.get(f"a_{c}")) != norm(nc.get(f"b_{c}"))]
        check(f"{nc['a']} ({nc['a_setting']}) vs {nc['b']} ({nc['b_setting']}) "
              f"@{nc['page']} differ on {differs or 'NOTHING'}",
              bool(differs),
              "same signature AND same catchword across two different settings -- "
              "either the settings are not distinct or the criterion cannot see it")
        check(f"   ...while sharing the running head {nc.get('running_head_both')!r}",
              nc.get("running_head_both") is not None,
              "the control is only sharp if the two agree on the head, so that the "
              "foot is what does the separating")


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
        # 🔴 SEPARATED points, not matched pages (R8.4b, 2026-08-10). §0.3 requires agreement at
        # "three or more separated points **spread through the volume**", and counting page
        # entries does not say that: `OT1-1609-P` vs `F` records seven pages, but they are
        # [222,223,224, 457, 918,919,920] -- THREE locations read three times each. Three adjacent
        # leaves would have satisfied the old count while testing nothing about the volume's span,
        # which is a criterion weaker than the one the constitution states and reads identical in
        # the output. Both numbers are printed so a future reader can see the difference.
        sep = separated(pts)
        check(f"{wid:14s} {len(sep)} separated point(s) over {len(pts)} matched page(s), "
              f"partners {sorted(partners) or '-'}",
              len(sep) >= MIN_POINTS,
              f"only {len(sep)} separated point(s) — adjacent pages count once; "
              f"the criterion is {MIN_POINTS} spread through the volume")

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

    check_foot(d, registered)

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
