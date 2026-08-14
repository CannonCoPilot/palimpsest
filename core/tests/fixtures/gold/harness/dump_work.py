#!/usr/bin/env python
"""Inspection aid for by-eye gold vetting.

  dump_work.py text  <idx>   # write reference_text to text/work-<idx>.txt (verbatim read)
  dump_work.py elems <idx>   # print every detector section + uncovered runs (FN hunt)
  dump_work.py nav   <idx>   # print the full heading track with offsets
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "core"))

from harness import project_for, uncovered_runs  # noqa: E402
from palimpsest.layout import detect_layout_sections  # noqa: E402
from palimpsest.server import _endnote_separator, _layout_boundaries  # noqa: E402

HERE = Path(__file__).resolve().parent
TEXT = HERE / "text"


def _flat(s: str) -> str:
    return s.replace("\n", "⏎").replace("\t", "→")


def main() -> None:
    cmd, idx = sys.argv[1], int(sys.argv[2])
    proj = project_for(idx)
    text = proj.reference_text()
    n = len(text)
    if cmd == "text":
        TEXT.mkdir(parents=True, exist_ok=True)
        out = TEXT / f"work-{idx}.txt"
        out.write_text(text)
        print(f"wrote {out} ({n:,} chars)")
        return
    bnds = _layout_boundaries(proj)
    secs = detect_layout_sections(bnds, n, _endnote_separator(proj.path), text=text)
    if cmd == "nav":
        print(f"idx {idx}: {len(bnds)} heading-track entries")
        for (s, e, label) in bnds:
            print(f"  [{s:>8}-{e:>8}] {label!r}")
        return
    if cmd == "elems":
        print(f"idx {idx}: {len(secs)} detector sections over {n:,} chars\n")
        for s in sorted(secs, key=lambda x: x.start):
            seg = text[s.start:s.end]
            head = _flat(seg[:70])
            tail = _flat(seg[-40:]) if len(seg) > 110 else ""
            print(f"[{s.start:>8}-{s.end:>8}] {s.end-s.start:>8}c  {s.type:<14} masked={s.masked}")
            print(f"      START {head!r}")
            if tail:
                print(f"      END   …{tail!r}")
        body = next((s for s in secs if s.type == "body"), None)
        span = (body.start, body.end) if body else (0, n)
        runs = uncovered_runs(secs, span)
        big = sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:15]
        print(f"\n--- {len(runs)} uncovered runs in body (FN hunt); biggest 15 ---")
        for a, b in big:
            print(f"  [{a:>8}-{b:>8}] {b-a:>8}c  {_flat(text[a:a+80])!r}")


if __name__ == "__main__":
    main()
