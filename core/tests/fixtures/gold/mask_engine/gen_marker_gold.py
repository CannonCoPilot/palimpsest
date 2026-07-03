#!/usr/bin/env python
"""Generalized Gold-Set map generator for canonical marker-format scripture.

Turns any ingested marker-format Bible (``# Book`` / ``## Book N`` / ``<num>\\t verse``)
into a durable Gold-Set masking map (``../maps/work-NNN.map.json``) in the exact
LayoutConfig shape the Palimpsest API consumes.

Why this is non-circular even though the runtime also parses markers: the markers
ARE the source-of-truth (they came from the scrape/OCR, not from Palimpsest's
detector). This generator re-parses them with its OWN contiguous-tiling logic and
then asserts book/chapter counts against the raw markers, so a detector regression
would make a future re-import diverge from the frozen map. It is deliberately
independent of ``palimpsest.layout._versed_bible_layout``.

Structure emitted (mirrors the ratified taxonomy):
  * body   [0, EOF]                          GENERIC base
  * book   [# marker, next # marker/EOF]     GENERIC container (genre/apocrypha meta)
  * chapter[tiled: ## marker -> next]        SPECIFIC backbone (tiles 100%, analyzable)
  * chapter_heading  (the "## Book N" line)  SPECIFIC, masked, overlaid on chapter
  * header           (the "# Book" line)     SPECIFIC, masked, overlaid on chapter 1
  * genre_division   (>=2 same-genre books)  SPECIFIC, masked container
  * front_matter/back_matter (only if the text has pre-book / post-verse material)

Two gates (same guarantee as gen_gold_maps): 0 unresolved elements, and 100%
two-layer coverage (every char >=1 GENERIC and >=1 SPECIFIC).

Usage:
  gen_marker_gold.py <idx> <project_dir> [--title T] [--source-file NAME]
    project_dir = an ingested Palimpsest project (has reference.txt + metadata.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # mask_engine -> gold -> fixtures -> tests -> core -> <repo>
sys.path.insert(0, str(REPO / "core"))
from palimpsest.canon import book_division, esdras_is_apocryphal  # noqa: E402
from palimpsest.layout import _UNMASKED_TYPES  # noqa: E402

MAPS = HERE.parent / "maps"
GOLD = HERE.parent
WS_RE = re.compile(r"\s+")

# Independent re-implementation of the marker grammar (NOT imported from verses.py).
BOOK_RE = re.compile(r"(?m)^# (.+)$")             # "# Genesis"
CHAP_RE = re.compile(r"(?m)^## .*?(\d+)\s*$")     # "## Genesis 1" -> trailing int
VERSE_RE = re.compile(r"(?m)^(\d{1,3})[ \t]+")    # "1 In the beginning..."
PROL_RE = re.compile(r"(?m)^@ (.+)$")             # "@ Prologe on Exodus" -> apparatus block

GENERIC = {"body", "volume", "book", "part", "section"}
# Kept aligned with the runtime verse detector (verses.py _MARKER_MIN_BOOKS): both admit
# Gospel harmonies at ≥4 books. They MUST move together — a lower floor here alone would
# emit a structurally-valid map for a partial canon the runtime masks with ZERO verses.
MIN_BOOKS = 4
MIN_CHAPTERS = 20


def _eol(text: str, pos: int) -> int:
    nl = text.find("\n", pos)
    return len(text) if nl < 0 else nl


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _gaps(merged: list[tuple[int, int]], n: int) -> list[tuple[int, int]]:
    """Uncovered ranges of [0, n) given merged, sorted, non-overlapping spans."""
    gaps: list[tuple[int, int]] = []
    cur = 0
    for s, e in merged:
        if s > cur:
            gaps.append((cur, s))
        cur = max(cur, e)
    if cur < n:
        gaps.append((cur, n))
    return gaps


def _prologue_blocks(text: str) -> list[tuple[int, int, str]]:
    """Apparatus (``@ Title``) blocks: span [@ marker -> next @ or # marker / EOF).

    The interior is opaque to the book/chapter/verse grammar, so a prologue's prose
    (which routinely leaks OCR page numbers, ``N PROLOGUE.`` footnote lines, etc.) can
    never be miscounted as scripture. ``## `` lines do NOT terminate a block.
    """
    stops = sorted([m.start() for m in PROL_RE.finditer(text)]
                   + [m.start() for m in BOOK_RE.finditer(text)])
    blocks: list[tuple[int, int, str]] = []
    for m in PROL_RE.finditer(text):
        s = m.start()
        nxt = next((p for p in stops if p > s), len(text))
        blocks.append((s, nxt, m.group(1).strip()))
    return blocks


def build_marker_elements(text: str) -> list[dict]:
    """Independent, contiguously-tiled gold elements from the marker structure.

    ``@ Title`` apparatus blocks (prologues, general prologues) are masked as
    ``front_matter``, carved out of chapter tiling, and their interiors are opaque to
    the marker grammar. Bibles with no ``@`` markers behave exactly as before.
    """
    n = len(text)
    blocks = _prologue_blocks(text)

    def _in_block(pos: int) -> bool:
        return any(s <= pos < e for s, e, _ in blocks)

    books = [(m.start(), m.group(1).strip())
             for m in BOOK_RE.finditer(text) if not _in_block(m.start())]
    chaps = [(m.start(), int(m.group(1)))
             for m in CHAP_RE.finditer(text) if not _in_block(m.start())]
    n_verses = sum(1 for m in VERSE_RE.finditer(text) if not _in_block(m.start()))
    if len(books) < MIN_BOOKS or len(chaps) < MIN_CHAPTERS:
        raise SystemExit(f"not marker-format scripture: {len(books)} books, {len(chaps)} chapters")

    block_starts = sorted(s for s, _, _ in blocks)
    body_start = books[0][0]
    body_end = n
    els: list[dict] = [{"type": "body", "start": 0, "end": n, "source": "marker:body", "label": ""}]

    esdras_apoc = esdras_is_apocryphal(name for _, name in books)
    book_spans: list[tuple[int, int, str, str | None, bool]] = []
    for i, (bstart, bname) in enumerate(books):
        bend = books[i + 1][0] if i + 1 < len(books) else body_end
        div, apoc = book_division(bname, esdras_apocryphal=esdras_apoc)
        book_spans.append((bstart, bend, bname, div, apoc))

    # genre_division containers over consecutive same-division runs (>=2 books)
    run = 0
    for j in range(len(book_spans) + 1):
        if j < len(book_spans) and book_spans[j][3] == book_spans[run][3]:
            continue
        div = book_spans[run][3]
        if div is not None and j - run >= 2:
            els.append({"type": "genre_division", "start": book_spans[run][0],
                        "end": book_spans[j - 1][1], "source": "marker:genre",
                        "label": div, "metadata": {"genre": div}})
        run = j

    for bstart, bend, bname, div, apoc in book_spans:
        meta: dict = {"book": bname}
        if div is not None:
            meta["genre"] = div
        if apoc:
            meta["apocrypha"] = True
        els.append({"type": "book", "start": bstart, "end": bend, "source": "marker:book",
                    "label": bname, "metadata": meta})
        els.append({"type": "header", "start": bstart, "end": _eol(text, bstart),
                    "source": "marker:header", "label": bname})

        bchaps = [c for c in chaps if bstart <= c[0] < bend]
        for k, (cstart, chnum) in enumerate(bchaps):
            nxt = bchaps[k + 1][0] if k + 1 < len(bchaps) else bend
            # carve out any apparatus block that opens inside this chapter's span so the
            # chapter never absorbs a following book's prologue (would mask it as scripture)
            clip = next((bs for bs in block_starts if cstart < bs < nxt), None)
            if clip is not None:
                nxt = clip
            span_start = bstart if k == 0 else cstart  # first chapter absorbs the "# Book" line
            label = f"{bname} {chnum}"
            els.append({"type": "chapter", "start": span_start, "end": nxt,
                        "source": "marker:chapter", "label": label,
                        "metadata": {"book": bname, "number": str(chnum)}})
            els.append({"type": "chapter_heading", "start": cstart, "end": _eol(text, cstart),
                        "source": "marker:chapter_heading", "label": label})

    # apparatus blocks -> masked front_matter (carved from chapter tiling above)
    for s, e, title in blocks:
        els.append({"type": "front_matter", "start": s, "end": e,
                    "source": "marker:prologue", "label": title or "Prologue"})

    # leading front matter (only if not already an apparatus block anchored at offset 0)
    if body_start > 0 and not any(s == 0 for s, _, _ in blocks):
        els.append({"type": "front_matter", "start": 0, "end": body_start,
                    "source": "marker:front_matter", "label": "Front Matter"})

    # Attach independent-validation counts for the caller.
    els_meta = {"n_books": len(books), "n_chapters": len(chaps), "n_verses": n_verses}
    for e in els:
        e.setdefault("metadata", {})
    els[0]["_counts"] = els_meta  # stash on body; stripped before serialize
    return els


def _audit(els: list[dict], n: int) -> None:
    generic = _merge([(e["start"], e["end"]) for e in els if e["type"] in GENERIC])
    specific = _merge([(e["start"], e["end"]) for e in els if e["type"] not in GENERIC])
    for layer, merged in (("GENERIC", generic), ("SPECIFIC", specific)):
        gaps = _gaps(merged, n)
        if gaps:
            raise SystemExit(f"GATE FAIL: {layer} coverage gaps: {gaps[:5]}"
                             f"{' ...' if len(gaps) > 5 else ''} ({len(gaps)} total)")


def _label(text: str, s: int, e: int, cap: int = 80) -> str:
    for line in text[s:e].splitlines():
        t = WS_RE.sub(" ", line).strip()
        if t:
            return t[:cap]
    return ""


def build_map(idx: int, project_dir: Path, title: str | None, source_file: str | None) -> dict:
    text = (project_dir / "reference.txt").read_text(encoding="utf-8")
    meta = json.loads((project_dir / "metadata.json").read_text())
    n = len(text)
    els = build_marker_elements(text)
    counts = els[0].pop("_counts")

    unresolved = [e for e in els if e["start"] < 0 or e["end"] > n or e["end"] <= e["start"]]
    if unresolved:
        raise SystemExit(f"[{idx}] GATE FAIL: {len(unresolved)} unresolved/invalid elements")
    _audit(els, n)

    # Independent raw-marker parity: the map's structural counts MUST equal the markers.
    n_books = sum(1 for e in els if e["type"] == "book")
    n_chaps = sum(1 for e in els if e["type"] == "chapter")
    n_heads = sum(1 for e in els if e["type"] == "chapter_heading")
    assert n_books == counts["n_books"], f"book parity {n_books}!={counts['n_books']}"
    assert n_chaps == counts["n_chapters"], f"chapter parity {n_chaps}!={counts['n_chapters']}"
    assert n_heads == counts["n_chapters"], f"heading parity {n_heads}!={counts['n_chapters']}"

    per_type: Counter = Counter()
    sections = []
    for el in els:
        t = el["type"]
        per_type[t] += 1
        k = per_type[t]
        label = el.get("label")
        if not label:
            label = "" if t == "body" else _label(text, el["start"], el["end"])
        md = {"gold_source": el["source"], **(el.get("metadata") or {})}
        sections.append({
            "id": f"{t}-{k:04d}", "type": t, "start": el["start"], "end": el["end"],
            "label": label, "name": "body" if t == "body" else f"{t}_{k}",
            "parent_id": None, "source": "gold", "masked": None, "mask_as": None,
            "metadata": md,
        })

    types_present = sorted(per_type)
    src = source_file or meta.get("source_file", "")
    return {
        "schema": "palimpsest.gold-map/v1",
        "idx": idx,
        "source_file": src,
        "import_source": src,
        "reference_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_len": n,
        "element_count": len(sections),
        "type_counts": dict(per_type),
        "verse_count": counts["n_verses"],
        "generated_from": "mask_engine/gen_marker_gold (independent marker parse)",
        "applied": True,
        "extra_types": [],
        "mask_by_type": {t: (t not in _UNMASKED_TYPES) for t in types_present},
        "sections": sections,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("idx", type=int)
    ap.add_argument("project_dir", type=Path)
    ap.add_argument("--title")
    ap.add_argument("--source-file")
    args = ap.parse_args()
    m = build_map(args.idx, args.project_dir, args.title, args.source_file)
    MAPS.mkdir(parents=True, exist_ok=True)
    out = MAPS / f"work-{args.idx:03d}.map.json"
    out.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    tc = m["type_counts"]
    print(f"[{args.idx}] {out.name}: {m['element_count']} elements "
          f"(book={tc.get('book')} chapter={tc.get('chapter')} "
          f"chapter_heading={tc.get('chapter_heading')} header={tc.get('header')} "
          f"genre_division={tc.get('genre_division')}) verses={m['verse_count']} "
          f"sha {m['reference_sha256'][:12]} 100% two-layer OK")


if __name__ == "__main__":
    main()
