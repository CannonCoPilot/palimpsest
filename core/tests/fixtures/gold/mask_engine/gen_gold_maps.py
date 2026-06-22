#!/usr/bin/env python
"""Generate durable Gold Set masking maps as Palimpsest-importable LayoutConfig JSON.

For each work index, materialize the COMPLETE masking map (every element of every
type via build_elements) and write it to ../maps/work-NNN.map.json in the exact
shape the Palimpsest API consumes (LayoutConfig: sections + mask_by_type + applied
+ extra_types) plus a header (schema/idx/source_file/reference_sha256/element_count).

A map is only written if it passes BOTH gates:
  * 0 unresolved elements (every gold anchor/rule resolves against the text), and
  * 100% two-layer COVERED coverage (no UNCOVERED/GENERIC_ONLY/SPECIFIC_ONLY runs).

reference_sha256 is the integrity key the importer checks against the freshly
ingested text, guaranteeing the offsets land on the same coordinate space.

Usage:
  gen_gold_maps.py <idx>      # generate one map
  gen_gold_maps.py all        # generate all 20 gold works
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from masking_map import GOLD, audit, build_elements
from palimpsest.layout import _UNMASKED_TYPES

MAPS = GOLD / "maps"
WS_RE = re.compile(r"\s+")
GOLD_IDXS = sorted(int(p.stem.split("-")[1]) for p in GOLD.glob("work-*.json"))

# Works whose map text is NOT reproducible by the standard ingest of their source_file
# (e.g. a PDF needing custom column-aware extraction). For these, the importable text
# is a pre-extracted .txt staged in imports/; its basename is recorded as import_source
# so the API import ingests that text (whose normalized SHA matches reference_sha256)
# instead of re-extracting the original. idx101 LDS Triple Combination -> mask_engine/lds_extract.py.
IMPORT_SOURCE: dict[int, str] = {101: "LDS_eng.reference.txt"}


def _label(text: str, s: int, e: int, cap: int = 80) -> str:
    for line in text[s:e].splitlines():
        t = WS_RE.sub(" ", line).strip()
        if t:
            return t[:cap]
    return ""


def build_map(idx: int) -> dict:
    """Materialize the complete map for `idx` and return a LayoutConfig+header dict.

    Raises SystemExit if either completeness gate fails.
    """
    text, els = build_elements(idx)
    n = len(text)
    unresolved = [e for e in els if e["start"] < 0]
    if unresolved:
        raise SystemExit(f"[{idx}] GATE FAIL: {len(unresolved)} unresolved elements")
    cov = audit(idx)["coverage_pct"]
    if cov != {"COVERED": 100.0}:
        raise SystemExit(f"[{idx}] GATE FAIL: coverage not 100% two-layer: {cov}")

    per_type: Counter = Counter()
    sections = []
    for el in els:
        t = el["type"]
        per_type[t] += 1
        k = per_type[t]
        # Builders may supply an explicit display label + structured metadata (e.g. a
        # chapter's book/volume/number); else fall back to the span's first line.
        label = el.get("label")
        if label is None:
            label = "" if t == "body" else _label(text, el["start"], el["end"])
        meta = {"gold_source": el["source"], **(el.get("metadata") or {})}
        sections.append({
            "id": f"{t}-{k:04d}",
            "type": t,
            "start": el["start"],
            "end": el["end"],
            "label": label,
            "name": "body" if t == "body" else f"{t}_{k}",
            "parent_id": None,
            "source": "gold",
            "masked": None,            # inherit from mask_by_type (toggleable in UI)
            "mask_as": None,
            "metadata": meta,
        })

    types_present = sorted(per_type)
    mask_by_type = {t: (t not in _UNMASKED_TYPES) for t in types_present}
    gc = json.loads((GOLD / f"work-{idx}.json").read_text())
    return {
        "schema": "palimpsest.gold-map/v1",
        "idx": idx,
        "source_file": gc.get("source_file", ""),
        "import_source": IMPORT_SOURCE.get(idx, gc.get("source_file", "")),
        "reference_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_len": n,
        "element_count": len(sections),
        "type_counts": dict(per_type),
        "generated_from": "mask_engine/build_elements (gold contract + instance rules)",
        "applied": True,
        "extra_types": [],
        "mask_by_type": mask_by_type,
        "sections": sections,
    }


def write_map(idx: int) -> Path:
    m = build_map(idx)
    MAPS.mkdir(parents=True, exist_ok=True)
    out = MAPS / f"work-{idx:03d}.map.json"
    out.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{idx:>3}] {out.name}: {m['element_count']} elements, "
          f"{len(m['type_counts'])} types, sha {m['reference_sha256'][:12]}, "
          f"100% two-layer  OK")
    return out


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    arg = sys.argv[1]
    idxs = GOLD_IDXS if arg == "all" else [int(arg)]
    for idx in idxs:
        write_map(idx)


if __name__ == "__main__":
    main()
