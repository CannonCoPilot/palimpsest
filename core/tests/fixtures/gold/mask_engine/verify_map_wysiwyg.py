#!/usr/bin/env python
"""Enforce the WYSIWYG rule: the LIVE Palimpsest state must EXACTLY equal the stored map.

For a work index + project id, diff the stored ../maps/work-NNN.map.json against the
live `GET /api/projects/{pid}/sections`, asserting:
  * identical section set: exact (type, start, end, masked, name) multiset, AND
  * identical masked_intervals (server's vs recomputed from the stored map).

Exit 0 = WYSIWYG holds; exit 1 = drift (prints the diff). Run after every import.

Usage:
  verify_map_wysiwyg.py <idx> <project_id>
"""
from __future__ import annotations

import json
import sys
import urllib.request

from masking_map import GOLD
from palimpsest.layout import DEFAULT_MASK_BY_TYPE, LayoutSection, masked_intervals

MAPS = GOLD / "maps"
API = "http://localhost:8080"


def _key(s: dict) -> tuple:
    return (s["type"], int(s["start"]), int(s["end"]), s.get("masked"), s.get("name"))


def verify(idx: int, pid: str, quiet: bool = False) -> bool:
    """True iff the live server layout for `pid` exactly equals stored work-NNN.map.json."""
    stored = json.loads((MAPS / f"work-{idx:03d}.map.json").read_text())

    with urllib.request.urlopen(f"{API}/api/projects/{pid}/sections", timeout=60) as r:
        live = json.load(r)

    smap = sorted(_key(s) for s in stored["sections"])
    lmap = sorted(_key(s) for s in live["sections"])
    sections_match = smap == lmap

    # masked_intervals: recompute from the stored map, compare to the server's
    mbt = dict(DEFAULT_MASK_BY_TYPE)
    mbt.update(stored.get("mask_by_type", {}))
    secs = [LayoutSection(id=s["id"], type=s["type"], start=s["start"], end=s["end"],
                          masked=s.get("masked"), mask_as=s.get("mask_as"))
            for s in stored["sections"]]
    local_mi = sorted(masked_intervals(secs, mbt, stored["text_len"]))
    server_mi = sorted((a, b) for a, b in live["masked_intervals"])
    mi_match = local_mi == server_mi
    ok = sections_match and mi_match

    if not quiet:
        print(f"idx={idx} pid={pid[:40]}…")
        print(f"  sections: stored={len(smap)} live={len(lmap)} EXACT_MATCH={sections_match}")
        if not sections_match:
            print(f"    in stored not live: {sorted(set(smap) - set(lmap))[:5]}")
            print(f"    in live not stored: {sorted(set(lmap) - set(smap))[:5]}")
        print(f"  masked_intervals: stored={len(local_mi)} live={len(server_mi)} EXACT_MATCH={mi_match}")
        print(f"  WYSIWYG: {'PASS — live == stored map' if ok else 'FAIL — drift detected'}")
    return ok


def main() -> int:
    return 0 if verify(int(sys.argv[1]), sys.argv[2]) else 1


if __name__ == "__main__":
    sys.exit(main())
