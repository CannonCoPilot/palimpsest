#!/usr/bin/env python3
"""test_counts_vs_doc.py — the plan's witness table must agree with the registry.

Roadmap R8.  A bare numeral in OCR-MASTERPLAN.md 1.1 has gone stale four times:
"ten files, seven witnesses"; then the omission of S06; then the omission of
S06's Old Testament half; then the discovery that a witness recorded as 1582 is
a 1633 book.  Each time the prose was corrected by hand and each time it drifted
again, because nothing connected it to the registry.

This test parses the 1.1 table out of the document and compares it, row for row,
against `witnesses.WITNESSES`.  It checks the witness id, the leaf count and the
primary artefact kind — the three fields that have actually drifted.

Run it whenever either side changes.  Exit 1 on any disagreement.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
from witness import witnesses as W  # noqa: E402

DOC = HERE.parents[1] / "OCR-MASTERPLAN.md"

# `NT-1582-B` ... | PDF/JP2 `...` | 812 | role
ROW = re.compile(
    r"^\|[^|]*\|\s*\**`(?P<wid>[A-Z0-9]+-\d{4}-[A-Z])`\**\s*\|"      # witness id
    r"[^|]*\|\s*(?P<artefact>[^|]*?)\s*\|"                            # primary artefact cell
    r"\s*\**(?P<leaves>[\d,]+)\**\s*\|",                              # leaf count
    re.M)


def parse_doc() -> dict[str, tuple[int, str]]:
    text = DOC.read_text()
    start = text.index("### 1.1 The files")
    end = text.index("### 1.1a")
    rows: dict[str, tuple[int, str]] = {}
    for m in ROW.finditer(text[start:end]):
        art = m.group("artefact")
        kind = "pdf" if "PDF" in art else ("jp2" if "JP2" in art else "?")
        rows[m.group("wid")] = (int(m.group("leaves").replace(",", "")), kind)
    return rows


def main() -> int:
    doc = parse_doc()
    reg = {W.wid(v, s): (W.WITNESSES[(v, s)]["leaves"], W.PRIMARY[(v, s)])
           for (v, s) in W.WITNESSES}

    failures: list[str] = []
    print(f"registry: {len(reg)} witness records | 1.1 table: {len(doc)} rows\n")

    for wid in sorted(set(reg) | set(doc)):
        r, d = reg.get(wid), doc.get(wid)
        if r is None:
            failures.append(f"{wid}: in the plan's table but NOT in the registry")
            print(f"  FAIL  {wid:14} in table, absent from registry")
        elif d is None:
            failures.append(f"{wid}: in the registry but MISSING from the plan's 1.1 table")
            print(f"  FAIL  {wid:14} in registry, absent from table")
        elif r != d:
            failures.append(f"{wid}: registry {r} vs table {d}")
            print(f"  FAIL  {wid:14} registry leaves={r[0]} primary={r[1]} | "
                  f"table leaves={d[0]} primary={d[1]}")
        else:
            print(f"  ok    {wid:14} leaves={r[0]:<5} primary={r[1]}")

    print()
    if failures:
        print(f"FAILED: {len(failures)}\n---")
        for f in failures:
            print(f"  {f}")
        print("\nThe registry is the source of truth. Correct the plan's 1.1 table to match it.")
        return 1
    print("all checks passed — 1.1 table agrees with the registry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
