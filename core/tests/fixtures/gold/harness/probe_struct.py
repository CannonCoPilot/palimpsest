#!/usr/bin/env python
"""Throwaway probe: inspect the heading-track + section shapes for gold works."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "core"))

from harness import project_for  # noqa: E402
from palimpsest.server import _endnote_separator, _layout_boundaries  # noqa: E402
from palimpsest.layout import detect_layout_sections  # noqa: E402


def probe(idx: int) -> None:
    proj = project_for(idx)
    text = proj.reference_text()
    bnds = _layout_boundaries(proj)
    print(f"\n==== idx {idx}  text_len={len(text)} ====")
    print(f"_layout_boundaries type={type(bnds).__name__} len={len(bnds)}")
    # show first element's shape
    if bnds:
        b0 = bnds[0]
        print(f"  boundary[0] type={type(b0).__name__} repr={b0!r}"[:300])
        for attr in ("offset", "start", "end", "label", "level", "kind", "type", "track"):
            if hasattr(b0, attr):
                print(f"    .{attr} = {getattr(b0, attr)!r}"[:160])
    secs = detect_layout_sections(bnds, len(text), _endnote_separator(proj.path), text=text)
    print(f"detect_layout_sections -> {len(secs)} sections")
    if secs:
        s0 = secs[0]
        print(f"  section attrs: {[a for a in dir(s0) if not a.startswith('_')]}")


for i in (70, 19):
    probe(i)
