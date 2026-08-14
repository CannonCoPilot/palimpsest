#!/usr/bin/env python
"""Manual-review inspector for the Detect pipeline — dump mask spans with text.

The rubric (harness.py) rewards local well-formedness but is blind to spurious
overlays, over/under-segmentation, and dropped metadata. This tool prints the
actual text at each mask boundary so the masks can be read against the source.

Usage:
  inspect.py <idx> [type[,type...]] [--head N] [--full]
    idx       work index in order.json
    type      comma list to filter (e.g. translation,chapter,book); default: all
    --head N  chars to show at each end of a span (default 220)
    --full    print the whole span (use for short ones only)
  inspect.py <idx> --summary   # per-type counts + first/last span of each type
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "core"))
sys.path.insert(0, str(HERE))

from harness import project_for, short, work_order  # noqa: E402
from palimpsest.layout import detect_layout_sections  # noqa: E402
from palimpsest.server import _endnote_separator, _layout_boundaries  # noqa: E402


def _norm(s: str) -> str:
    return " ".join(s.split())


def sections_for(idx: int):
    proj = project_for(idx)
    if proj is None:
        raise SystemExit(f"work {idx} not ingested")
    text = proj.reference_text()
    secs = detect_layout_sections(
        _layout_boundaries(proj), len(text), _endnote_separator(proj.path), text=text
    )
    return text, secs


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    idx = int(sys.argv[1])
    types = None
    head = 220
    full = False
    summary = False
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--head":
            head = int(args[i + 1]); i += 2; continue
        if a == "--full":
            full = True; i += 1; continue
        if a == "--summary":
            summary = True; i += 1; continue
        types = set(a.split(",")); i += 1
    text, secs = sections_for(idx)
    print(f"# [{idx}] {short(work_order()[idx].name)} — {len(text):,} chars, {len(secs)} sections")

    if summary:
        by_type: dict[str, list] = {}
        for s in secs:
            by_type.setdefault(s.type, []).append(s)
        for t, items in sorted(by_type.items()):
            items.sort(key=lambda s: s.start)
            first, last = items[0], items[-1]
            print(f"\n## {t} ×{len(items)}")
            print(f"   first [{first.start}-{first.end}] {first.metadata} | {_norm(text[first.start:first.start+90])!r}")
            if len(items) > 1:
                print(f"   last  [{last.start}-{last.end}] {last.metadata} | {_norm(text[last.start:last.start+90])!r}")
        return

    shown = 0
    for s in sorted(secs, key=lambda x: (x.start, x.end)):
        if types and s.type not in types:
            continue
        shown += 1
        span = s.end - s.start
        seg = text[s.start:s.end]
        print(f"\n## {s.type} [{s.start}-{s.end}] ({span:,}c) name={s.name} meta={s.metadata}")
        if s.label:
            print(f"   label: {s.label[:100]!r}")
        if full or span <= head * 2:
            print(f"   {_norm(seg)!r}")
        else:
            print(f"   START {_norm(seg[:head])!r}")
            print(f"   END   {_norm(seg[-head:])!r}")
    print(f"\n({shown} spans shown)")


if __name__ == "__main__":
    main()
