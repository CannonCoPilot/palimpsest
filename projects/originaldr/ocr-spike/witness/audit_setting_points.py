#!/usr/bin/env python3
"""audit_setting_points.py -- R8.4b: the foot criteria are proved at ONE point, not three.

§0.3 requires setting identity to be proved by agreement at **three or more separated points spread
through the volume**, on all five criteria: printed page number · running head · sidehead ·
**signature** · **catchword** (plus line-end words).  The head band supplies the first three; the
**foot band** supplies the signature and the catchword (R8.4a).

The head pass used three or more separated points throughout.  **The foot pass used exactly one
matched page per setting.**  Master Plan §2 nevertheless recorded the result as "11 of 12 records
verified on the full §0.3 criterion" until 2026-08-10 -- and that sentence is four days younger than
the §0.3 rewrite it was flattening, a rewrite whose whole occasion was an audit that came out
*"stronger on one axis and silently weaker on two"*.  **A correction is not self-enforcing.** This
audit is what enforces it.

⚠️ **AUDIT, not a guard.** It exits **1** until the foot criteria reach `MIN_POINTS` separated
points for every verified pair, and exit 1 is the healthy state while R8.4b is open.  Put in
`test_setting_verified.py` it would turn a green guard red, which in this project's grammar reads as
a regression rather than as an outstanding remedy -- and the pressure would then be to weaken it.

**Separated, not merely counted.** Adjacent pages are one point: `OT1-1609-P` vs `F` records seven
head pages, but they are [222,223,224], [457], [918,919,920] -- three locations read three times.
Three adjacent leaves say nothing about a volume's span, and would satisfy a raw count while
failing the criterion §0.3 actually states.

Exit 0 only when head AND foot both reach the criterion. Exit 1 naming each shortfall.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_setting_verified import MIN_POINTS, MIN_SEPARATION, separated  # noqa: E402

READINGS = HERE / "setting-readings.json"


def main() -> int:
    d = json.loads(READINGS.read_text())
    short: list[str] = []

    for label, key in (("HEAD (page no · running head · sidehead)", "verified_pairs"),
                       ("FOOT (signature · catchword)", "foot_pairs")):
        pairs = d.get(key, [])
        print(f"\n{label} — {MIN_POINTS} separated points required "
              f"(pages < {MIN_SEPARATION} apart count once):")
        if not pairs:
            short.append(f"{key}: no pairs recorded at all")
            print("  FAIL  no pairs recorded")
            continue
        for p in pairs:
            sep = separated(p["pages"])
            ok = len(sep) >= MIN_POINTS
            if not ok:
                short.append(f"{key} {p['a']} vs {p['b']} ({p['setting']}): "
                             f"{len(sep)} separated point(s), need {MIN_POINTS} "
                             f"— pages {p['pages']}")
            print(f"  {'ok  ' if ok else '--  '} {p['setting']:10} {p['a']:12} vs {p['b']:12} "
                  f"{len(sep)} separated / {len(p['pages'])} page(s)  {[c[0] for c in sep]}")

    # The negative control is what licenses the criterion at all: criteria that have never
    # SEPARATED two settings are not known to discriminate. R8.4a proved it at one page; extending
    # the positive side to three points without extending this would widen the claim on the
    # unlicensed axis.
    ncs = d.get("foot_negative_controls", [])
    print(f"\nfoot negative controls (a criterion that never separated anything is not a criterion): "
          f"{len(ncs)} recorded")
    for nc in ncs:
        print(f"  ok    p.{nc['page']} {nc['a']} ({nc['a_setting']}) sig={nc['a_signature']!r} "
              f"vs {nc['b']} ({nc['b_setting']}) sig={nc['b_signature']!r}")
    if len(ncs) < MIN_POINTS:
        short.append(f"foot_negative_controls: {len(ncs)} recorded, and the positive side is being "
                     f"raised to {MIN_POINTS} points — the discriminating evidence must be raised "
                     f"with it, or the criterion is trusted further than it has been tested")

    print()
    if not short:
        print(f"R8.4b holds: head and foot criteria both proved at >= {MIN_POINTS} separated "
              f"points for every verified pair.")
        return 0
    print(f"OPEN (R8.4b) — {len(short)} shortfall(s):")
    for s in short:
        print(f"  {s}")
    print("\n**Exit 1 is the healthy state while R8.4b is open.** The remedy is to read the foot "
          "band at two further separated pages per setting with `verify_setting.py` and record "
          "them — NOT to lower MIN_POINTS, and NOT to move this into the guard.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
