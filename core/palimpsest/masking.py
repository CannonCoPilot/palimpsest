"""Import-time masking: the single code path that turns an ingested project into its accurate,
precise mask layers — the structural layout (books, chapters, chapter headings, front/back matter,
…) and the content verse index (the verse-number layer).

Shared by the HTTP API import endpoints, the CLI ``import`` command, and the UI "detect layout"
endpoint so all three produce identical masking (CLI/UI/API parity). No analysis extractor runs
here — analysis is on-demand — so import stops at masking and stays fast.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from palimpsest.atomic import atomic_write_text


def _layout_boundaries(project: Any) -> list[tuple[int, int, str]]:
    """Section boundaries (start, end, heading) from the sections track, else segmenter."""
    out: list[tuple[int, int, str]] = []
    sec_path = project.path / "tracks" / "sections.jsonl"
    if sec_path.exists():
        for line in sec_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            sel = d.get("target", {}).get("selector", {})
            start = sel.get("start")
            end = sel.get("end")
            body = d.get("body", {})
            heading = body.get("palimpsest:headingText") or body.get("value") or ""
            if start is not None:
                out.append((int(start), int(end if end is not None else start), str(heading)))
    if not out:
        out = [(s, e, h) for s, e, h in project.sections()]
    out.sort(key=lambda b: b[0])
    return out


def _endnote_separator(project_dir: Path) -> int:
    """Char offset where the endnote region begins, or -1."""
    coord = project_dir / "coordinates.json"
    if coord.exists():
        c = json.loads(coord.read_text())
        er = c.get("endnote_region")
        if er and int(er.get("separator_offset", -1)) > 0:
            return int(er["separator_offset"])
    return -1


def _write_verses_track(project_dir: Path, text: str) -> int:
    """Write the per-project verse coordinate index as a compact ``verses.jsonl`` track.

    One line per verse: ``{b: book, c: chapter, v: verse, ns: num_start, s: text_start,
    e: text_end}``. The masked number token is ``[ns, s)``; the verse prose is ``[s, e)``.
    This is BOTH the lazy verse track's source and the verse-number mask layer (the union
    of ``[ns, s)`` spans). It is far more compact than W3C element annotations — tens of
    thousands of verses stay a ~1-2MB file the Browser can fetch lazily when zoomed in.
    """
    from palimpsest.verses import detect_verses

    records = detect_verses(text)
    track_path = project_dir / "tracks" / "verses.jsonl"
    track_path.parent.mkdir(parents=True, exist_ok=True)
    if records:
        lines = [
            json.dumps({"b": r["book"], "c": r["chapter"], "v": r["verse"],
                        "ns": r["num_start"], "s": r["text_start"], "e": r["text_end"]},
                       ensure_ascii=False)
            for r in records
        ]
        atomic_write_text(track_path, "\n".join(lines) + "\n")
    else:
        track_path.unlink(missing_ok=True)
    return len(records)


def detect_and_save_layout(project: Any, reference: str | None = None) -> tuple[Any, int]:
    """Detect and persist a project's structural layout. Returns ``(LayoutConfig, text_len)``.

    The layout half of :func:`compute_masking`, split out because the UI "detect layout" endpoint
    re-runs exactly this step (without the verse track) and returns the config to the browser.
    Pass ``reference`` to reuse an already-read reference text and avoid re-reading it from disk.
    """
    from palimpsest.layout import (
        LayoutConfig,
        detect_layout_sections,
        load_layout,
        save_layout,
    )

    project_dir = project.path
    ref: str = project.reference_text() if reference is None else reference
    text_len = len(ref)
    sections = detect_layout_sections(
        _layout_boundaries(project), text_len, _endnote_separator(project_dir), text=ref,
    )
    cfg = load_layout(project_dir) or LayoutConfig()
    cfg.sections = sections
    cfg.applied = False
    # detect_layout_sections already linked parents; recording that avoids the O(n^2) lazy parent
    # backfill on the first subsequent layout load (a server hot path).
    cfg.parents_computed = True
    save_layout(project_dir, cfg)
    return cfg, text_len


def compute_masking(project: Any) -> dict[str, int]:
    """Detect and persist a project's full masking at import: structural layout + verse index.

    Runs NO analysis extractor — analysis stays on-demand via ``POST /analyze/{track}`` — so import
    stops at accurate, precise masking. Returns ``{"sections": n, "verses": n}``.
    """
    reference = project.reference_text()
    cfg, _text_len = detect_and_save_layout(project, reference)
    verse_n = _write_verses_track(project.path, reference)
    return {"sections": len(cfg.sections), "verses": verse_n}
