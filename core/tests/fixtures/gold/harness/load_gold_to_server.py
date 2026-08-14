#!/usr/bin/env python
"""Load a gold masking map (build_elements(idx)) into the running Palimpsest server
as the project's layout sections, then apply (writes the elements track).

Offsets are byte-aligned because the server's reference.txt SHA == the gold text SHA
(verified separately). Types are all builtin; DEFAULT_MASK_BY_TYPE already encodes the
gold masking policy (body/book/chapter unmasked; heading markers + matter masked).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections import Counter

from masking_map import build_elements

API = "http://localhost:8080"
WS = re.compile(r"\s+")


def _label(text: str, s: int, e: int, cap: int = 80) -> str:
    """First non-empty line of the span, whitespace-collapsed, capped."""
    for line in text[s:e].splitlines():
        t = WS.sub(" ", line).strip()
        if t:
            return t[:cap]
    return ""


def build_sections(idx: int):
    text, els = build_elements(idx)
    n = len(text)
    per_type = Counter()
    sections = []
    for el in els:
        if el["start"] < 0:
            raise SystemExit(f"UNRESOLVED element present: {el}")
        t = el["type"]
        per_type[t] += 1
        k = per_type[t]
        name = "body" if t == "body" else f"{t}_{k}"
        label = "" if t == "body" else _label(text, el["start"], el["end"])
        sections.append({
            "id": f"{t}-{k:04d}",
            "type": t,
            "start": el["start"],
            "end": el["end"],
            "label": label,
            "name": name,
            "source": "user",
            "metadata": {"gold_source": el["source"]},
        })
    return text, n, sections


def _post(path: str, body: dict, method: str = "POST"):
    req = urllib.request.Request(
        API + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method=method,
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.status, json.loads(r.read().decode())


def main():
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    pid = sys.argv[2]
    text, n, sections = build_sections(idx)
    print(f"idx={idx} chars={n} sections={len(sections)}")
    print("by type:", dict(Counter(s["type"] for s in sections)))

    # PUT sections (mask_by_type omitted -> server uses DEFAULT_MASK_BY_TYPE = gold policy)
    status, payload = _post(f"/api/projects/{pid}/sections",
                            {"sections": sections, "applied": True}, method="PUT")
    print("PUT /sections ->", status)
    mi = payload.get("masked_intervals", [])
    masked_chars = sum(b - a for a, b in mi)
    print(f"  masked_intervals: {len(mi)} spans, {masked_chars} chars "
          f"({masked_chars / n * 100:.2f}% masked)")
    mbt = payload.get("mask_by_type", {})
    print("  mask_by_type (gold-relevant):",
          {t: mbt.get(t) for t in
           ["body", "book", "chapter", "chapter_heading",
            "front_matter", "appendix", "afterword", "glossary"]})

    # apply -> writes the unified 'elements' track for the reading/analysis view
    status, _ = _post(f"/api/projects/{pid}/sections/apply", {})
    print("POST /sections/apply ->", status)


if __name__ == "__main__":
    main()
