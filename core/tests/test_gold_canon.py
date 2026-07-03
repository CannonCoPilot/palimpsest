"""Independent canonical versification oracle for the Bible Gold Set.

`test_gold_maps.py` proves each map is internally consistent (spans tile, counts
reconcile, masking round-trips). It cannot prove the map is *correct* — a scrape that
silently dropped Genesis 31 would still tile perfectly and self-report a consistent
count, because the marker generator only ever checks the map against its own re-parsed
markers. That is the same blind spot the annotation golds close with `gold_ratify`'s
independent recount + human eyeball.

This module closes it for the map-only marker Bibles with an *external* oracle: for each
Bible, it derives per-book chapter counts by span-containment from the frozen map and
checks them against `canon_chapters.json` — externally-established counts the map never
had a hand in. The 66-book Protestant core (chapter divisions stable since Langton,
c.1227) is strict-gated for every Bible that contains those books; deuterocanon varies by
tradition, so only the well-established KJV-Apocrypha set (idx 219) is gated, the rest
recorded. This gives the marker Bibles an accuracy guarantee stronger than the annotation
works' human eyeball — the rigor-parity elevation for map-only scripture.

Epub Bibles (idx 5/6/100) are out of scope here by design: their accuracy rigor comes
from their annotation gold + detector recall (a3), the mechanism appropriate to
detector-discovered structure. idx 108 (Douay-Rheims original) is also out of scope: it
is a Catholic *Vulgate*-canon edition (Esther has the Greek additions → 16 chapters,
Daniel includes Susanna/Bel → 14), so the Protestant-66 oracle does not apply. Its kind
(Catholic Douay-Rheims) already carries parity-bearing members with annotation golds
(idx 5, 100); 108's route to full parity is an annotation gold or a Catholic oracle, and
its versification is recorded in the sources manifest rather than gated here.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest

from palimpsest.canon import _normalize

GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"
MAPS_DIR = GOLD_DIR / "maps"

# Marker Bibles whose chapter sections are 1:1 canonical chapters (guaranteed by
# gen_marker_gold parity) and which use standard book names → strict oracle targets.
_STRICT_IDXS = [201, 202, 203, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219]
# The KJV-Apocrypha edition whose deuterocanon counts are externally established.
_KJV_APOCRYPHA_IDX = 219

# Variant base names (Vulgate/Latin/Old-English/apocryphal) → canon_chapters.json keys.
# Sourced from canon.py's _BASE_DIVISION variant spellings; ordinals are preserved by the
# resolver, so e.g. "1 paralipomenon" → "1 chronicles".
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


@lru_cache(maxsize=1)
def _oracle() -> dict:
    return json.loads((GOLD_DIR / "canon_chapters.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _map(idx: int) -> dict:
    return json.loads((MAPS_DIR / f"work-{idx:03d}.map.json").read_text(encoding="utf-8"))


def _canon_key(label: str) -> str:
    ordinal, base = _normalize(label)
    base = _ALIAS.get(base, base)
    return f"{ordinal} {base}" if ordinal else base


def _books_chapters(idx: int) -> list[tuple[str, int]]:
    """(book_label, chapter_count) for each book, via span-containment (metadata-agnostic)."""
    secs = _map(idx)["sections"]
    chaps = [s for s in secs if s["type"] == "chapter"]
    out = []
    for b in (s for s in secs if s["type"] == "book"):
        bs, be = b["start"], b["end"]
        out.append((b.get("label", "?"), sum(1 for c in chaps if bs <= c["start"] < be)))
    return out


def _classify(idx: int):
    """Resolve every book → (core_ok, core_bad, deutero, unresolved) lists of (key,label,got,exp)."""
    oracle = _oracle()
    core, apoc = oracle["protestant_66"], oracle["kjv_apocrypha"]
    core_ok, core_bad, deutero, unresolved = [], [], [], []
    for label, got in _books_chapters(idx):
        key = _canon_key(label)
        if key in core:
            (core_ok if got == core[key] else core_bad).append((key, label, got, core[key]))
        elif key in apoc:
            deutero.append((key, label, got, apoc[key]))
        else:
            unresolved.append((key, label, got, None))
    return core_ok, core_bad, deutero, unresolved


@pytest.mark.parametrize("idx", _STRICT_IDXS, ids=[f"work-{i}" for i in _STRICT_IDXS])
def test_core66_chapter_counts(idx: int) -> None:
    """Every 66-book-core book present resolves and matches the external chapter count."""
    core_ok, core_bad, _deutero, unresolved = _classify(idx)
    assert not core_bad, f"core-66 chapter mismatches: {core_bad}"
    assert not unresolved, f"unresolved book labels (add alias?): {[u[1] for u in unresolved]}"
    assert core_ok, "no core-66 books resolved — Bible contains none of the canonical 66?"


def test_kjv_apocrypha_chapter_counts() -> None:
    """The KJV-1611 comprehensive edition (219) matches the established KJV-Apocrypha counts."""
    _core_ok, _core_bad, deutero, _unresolved = _classify(_KJV_APOCRYPHA_IDX)
    bad = [(k, lbl, got, exp) for (k, lbl, got, exp) in deutero if got != exp]
    assert not bad, f"KJV-Apocrypha chapter mismatches: {bad}"
    assert len(deutero) >= 14, f"expected 14 apocrypha books, resolved {len(deutero)}"


def test_oracle_covers_full_protestant_canon() -> None:
    """The oracle data itself is complete: 66 core books, all counts positive ints."""
    core = _oracle()["protestant_66"]
    assert len(core) == 66, f"protestant_66 has {len(core)} books, expected 66"
    assert all(isinstance(v, int) and v > 0 for v in core.values())
    assert core["genesis"] == 50 and core["psalms"] == 150 and core["revelation"] == 22
