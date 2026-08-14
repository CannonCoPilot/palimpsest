#!/usr/bin/env python
"""Reconcile the Douay chapter-heading count between idx5 and idx100."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "core"))
from harness import project_for  # noqa: E402

BARE = re.compile(r"\bChapter \d+\b")
LINE = re.compile(r"(?m)^\s*(?:[1-4] )?[A-Z][\w’.]+(?: of [A-Z][\w’.]+)? Chapter \d+\s*$")
# every line that contains "Chapter N" — to inspect the formats
LINE_ANY = re.compile(r"(?m)^.*\bChapter \d+\b.*$")

for idx in (5, 100):
    text = project_for(idx).reference_text()
    bare = BARE.findall(text)
    line = LINE.findall(text)
    any_lines = LINE_ANY.findall(text)
    # lines that contain "Chapter N" but do NOT match the strict line regex
    missed = [ln for ln in any_lines if not LINE.match(ln)]
    print(f"\n=== idx {idx} ===")
    print(f"  bare  \\bChapter \\d+\\b  = {len(bare)}")
    print(f"  line-anchored strict   = {len(line)}")
    print(f"  total lines w/ 'Chapter N' = {len(any_lines)}")
    print(f"  lines w/ 'Chapter N' NOT matched by strict ({len(missed)}):")
    for ln in missed[:30]:
        print(f"      {ln.strip()[:90]!r}")
