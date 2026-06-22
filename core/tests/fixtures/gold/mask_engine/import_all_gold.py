#!/usr/bin/env python
"""Import every Gold Set work into the running Palimpsest server with its stored
masking map (one-call gold import), then verify WYSIWYG for each.

Each work's CURRENT epub path is resolved from the server's /api/imports listing,
matched by the map's source_file basename — robust to import-folder reorganization.

Usage:
  import_all_gold.py              # all 20
  import_all_gold.py 5 6 18       # a subset
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from gen_gold_maps import GOLD_IDXS
from masking_map import GOLD
from verify_map_wysiwyg import verify

API = "http://localhost:8080"
MAPS = GOLD / "maps"


def _get(path: str):
    with urllib.request.urlopen(API + path, timeout=120) as r:
        return json.load(r)


def _post(path: str, body: dict):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=1200) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main() -> int:
    idxs = [int(a) for a in sys.argv[1:]] or GOLD_IDXS
    listing = _get("/api/imports")
    items = listing if isinstance(listing, list) else listing.get("files", [])
    by_name: dict[str, str] = {}
    for it in items:
        by_name.setdefault(it["name"], it["path"])  # first wins; exact basename match

    rows = []
    for idx in idxs:
        m = json.loads((MAPS / f"work-{idx:03d}.map.json").read_text())
        path = by_name.get(m.get("import_source", m["source_file"]))
        if not path:
            rows.append((idx, "NO_SOURCE_FILE", "", False))
            continue
        code, resp = _post("/api/import/local", {
            "path": path, "process": False, "overwrite": True,
            "layout_path": f"work-{idx:03d}.map.json",
        })
        if code != 200:
            rows.append((idx, f"IMPORT_{code}", str(resp.get("detail", ""))[:70], False))
            continue
        pid = resp["project_id"]
        gm = resp.get("gold_map", {})
        ok = verify(idx, pid, quiet=True)
        detail = f"{gm.get('element_count')} els / {gm.get('masked_spans')} masks / {gm.get('masked_chars')} ch"
        rows.append((idx, "OK" if ok else "WYSIWYG_FAIL", detail, ok))

    print(f"\n{'idx':>4} {'status':<14} detail")
    print("-" * 60)
    for idx, status, detail, _ in rows:
        print(f"{idx:>4} {status:<14} {detail}")
    n_ok = sum(1 for *_, ok in rows if ok)
    print(f"\nWYSIWYG PASS: {n_ok}/{len(idxs)} works")
    return 0 if n_ok == len(idxs) else 1


if __name__ == "__main__":
    sys.exit(main())
