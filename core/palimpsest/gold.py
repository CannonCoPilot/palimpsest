"""Gold-Set registry + verification — the production core shared by the CLI, the API,
and the canon-oracle test, so all three read the registry and judge a map identically.

The gold artifacts live under ``core/tests/fixtures/gold/`` — the same location the
server resolves via ``server._gold_maps_dir`` — and this module is their single
programmatic entry point: the sources manifest (registry), the frozen masking maps, the
canonical versification oracle, and a from-JSON map verifier that needs no source text.
"""
from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from palimpsest.canon import _normalize

GOLD_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "gold"
MAPS_DIR = GOLD_DIR / "maps"
MANIFEST_PATH = GOLD_DIR / "sources.manifest.json"
CANON_PATH = GOLD_DIR / "canon_chapters.json"

# Variant base names (Vulgate/Latin/Old-English/apocryphal spellings) → canon_chapters
# keys. Sourced from canon.py's _BASE_DIVISION variants; the resolver preserves ordinals,
# so e.g. "1 paralipomenon" → "1 chronicles".
_ALIAS: dict[str, str] = {
    "josue": "joshua", "paralipomenon": "chronicles", "nehemias": "nehemiah",
    "canticle of canticles": "song of solomon", "song of songs": "song of solomon",
    "osee": "hosea", "abdias": "obadiah", "jonas": "jonah", "micheas": "micah",
    "habacuc": "habakkuk", "sophonias": "zephaniah", "aggeus": "haggai",
    "zacharias": "zechariah", "malachias": "malachi", "malachie": "malachi",
    "isaias": "isaiah", "isaie": "isaiah", "jeremias": "jeremiah", "jeremy": "jeremiah",
    "ezechiel": "ezekiel", "apocalypse": "revelation",
    # deuterocanon variants
    "tobias": "tobit", "wisdom": "wisdom of solomon", "sirach": "ecclesiasticus",
    "epistle of jeremiah": "letter of jeremiah", "epistle of jeremy": "letter of jeremiah",
    "song of the three children": "prayer of azariah", "prayer of manasses": "prayer of manasseh",
    "machabees": "maccabees",
}


def load_manifest() -> dict[str, Any]:
    """The Bible Gold-Set registry (sources.manifest.json)."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_canon() -> dict[str, Any]:
    """The external versification oracle (canon_chapters.json)."""
    return json.loads(CANON_PATH.read_text(encoding="utf-8"))


def map_path(idx: int) -> Path:
    return MAPS_DIR / f"work-{idx:03d}.map.json"


@lru_cache(maxsize=None)
def load_map(idx: int) -> dict[str, Any]:
    return json.loads(map_path(idx).read_text(encoding="utf-8"))


def manifest_entry(idx: int) -> dict[str, Any] | None:
    return next((b for b in load_manifest()["bibles"] if b.get("id") == idx), None)


def canon_key(label: str) -> str:
    """Resolve a book label to its canon_chapters key (ordinal-aware, variant-normalized)."""
    ordinal, base = _normalize(label)
    base = _ALIAS.get(base, base)
    return f"{ordinal} {base}" if ordinal else base


def books_chapters(gmap: dict) -> list[tuple[str, int]]:
    """(book_label, chapter_count) per book via span-containment (metadata-agnostic)."""
    secs = gmap["sections"]
    chaps = [s for s in secs if s["type"] == "chapter"]
    out = []
    for b in (s for s in secs if s["type"] == "book"):
        bs, be = b["start"], b["end"]
        out.append((b.get("label", "?"), sum(1 for c in chaps if bs <= c["start"] < be)))
    return out


def classify_books(idx: int) -> tuple[list, list, list, list]:
    """Resolve every book of a map against the oracle.

    Returns (core_ok, core_bad, deutero, unresolved), each a list of (key, label, got,
    expected) tuples — core_bad/unresolved being the accuracy failures a strict Bible
    must have empty.
    """
    canon = load_canon()
    core, apoc = canon["protestant_66"], canon["kjv_apocrypha"]
    core_ok, core_bad, deutero, unresolved = [], [], [], []
    for label, got in books_chapters(load_map(idx)):
        key = canon_key(label)
        if key in core:
            (core_ok if got == core[key] else core_bad).append((key, label, got, core[key]))
        elif key in apoc:
            deutero.append((key, label, got, apoc[key]))
        else:
            unresolved.append((key, label, got, None))
    return core_ok, core_bad, deutero, unresolved


def verify_map(idx: int) -> list[str]:
    """Verify a frozen gold map from the JSON alone — structural gates + canon oracle.

    Re-derives the marker generator's gates through the *production* loader/masker (a
    schema or taxonomy drift that would break real gold application fails here), then, for
    Bibles whose registered accuracy source is the canon oracle, checks per-book chapter
    counts against the external versification table. Needs no source text. Returns a list
    of human-readable problems; empty means the map passes.
    """
    from palimpsest.layout import LayoutConfig, masked_intervals

    problems: list[str] = []
    d = load_map(idx)
    n = d.get("text_len", 0)
    if not isinstance(n, int) or n <= 0:
        return [f"invalid text_len: {n!r}"]

    bad = [(s.get("id"), s["start"], s["end"]) for s in d["sections"]
           if not (0 <= s["start"] < s["end"] <= n)]
    if bad:
        problems.append(f"{len(bad)} malformed spans, e.g. {bad[:3]}")

    if dict(Counter(s["type"] for s in d["sections"])) != d.get("type_counts"):
        problems.append("type_counts do not reconcile with sections")

    try:
        cfg = LayoutConfig.from_dict(d)
        mi = masked_intervals(cfg.sections, cfg.mask_by_type, n)
        if not all(0 <= a < b <= n for a, b in mi):
            problems.append("masked interval out of range")
        if not all(mi[i][1] <= mi[i + 1][0] for i in range(len(mi) - 1)):
            problems.append("masked intervals not sorted/disjoint")
        if sum(b - a for a, b in mi) <= 0:
            problems.append("map masks zero characters")
    except Exception as e:  # noqa: BLE001
        problems.append(f"production loader/masker rejected map: {e}")

    if "gen_marker_gold" in (d.get("generated_from") or ""):
        tc = d.get("type_counts", {})
        if tc.get("chapter") != tc.get("chapter_heading"):
            problems.append("chapter/chapter_heading parity broken")

    entry = manifest_entry(idx)
    if entry and entry.get("accuracy_source") == "canon-oracle":
        core_ok, core_bad, _deutero, unresolved = classify_books(idx)
        if core_bad:
            problems.append(f"canon chapter mismatches: {core_bad}")
        if core_ok and unresolved:
            problems.append(f"unresolved book labels (add alias?): {[u[1] for u in unresolved]}")

    return problems
