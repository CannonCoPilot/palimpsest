#!/usr/bin/env python
"""Text source for gold masking-map generation.

Resolves a work index -> its ingested, NORMALIZED reference text, replacing the
eval-harness coupling. Gold map offsets are computed against the `reference.txt`
that `ingest_file` produces, so generation must read that exact text. This module
locates an existing ingest (eval or demo workspace) by matching the work's source
filename from the committed `order.json` work order.

Generated maps are self-contained (they carry their `reference_sha256`), so this
module is only needed at generation time, not at import time.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # mask_engine -> gold -> fixtures -> tests -> core -> <repo>
sys.path.insert(0, str(REPO / "core"))
from palimpsest.project import Project  # noqa: E402

ORDER_FILE = HERE / "order.json"
IMPORTS = REPO / "imports"
# Machine-local (gitignored) workspaces holding cached ingests, in priority order.
# R11.1: the mask-eval root honours $MASK_EVAL_DATA so the two agree on one location.
_MASK_EVAL = Path(os.environ.get("MASK_EVAL_DATA", REPO / ".scratch" / "mask-eval"))
WORKSPACES = [_MASK_EVAL / "ws", REPO / ".scratch/demo"]


def work_order() -> list[Path]:
    """Fixed seed-1729 work order (import-relative POSIX paths) -> absolute epubs."""
    return [IMPORTS / rel for rel in json.loads(ORDER_FILE.read_text())]


def project_for(idx: int):
    """Load the ingested Project for work `idx`, matched by source filename."""
    epub = work_order()[idx]
    # R11.1: distinguish "no cache on this machine" from "this work is not ingested".
    # Both used to return None, so a missing 2 GB cache read as 108 un-ingested works
    # and every consumer reported a clean empty result (R1.4, `_empty_because` §1.4).
    if not any(ws.exists() for ws in WORKSPACES):
        raise FileNotFoundError(
            "no ingest workspace on this machine; looked in: "
            + ", ".join(str(w) for w in WORKSPACES)
            + "\nThe cache is machine-local by design; set MASK_EVAL_DATA to point at it."
        )
    for ws in WORKSPACES:
        if not ws.exists():
            continue
        for d in sorted(ws.iterdir()):
            if d.is_dir() and (d / "metadata.json").exists():
                meta = json.loads((d / "metadata.json").read_text())
                if meta.get("source_file") == epub.name:
                    return Project.load(d)
    return None
