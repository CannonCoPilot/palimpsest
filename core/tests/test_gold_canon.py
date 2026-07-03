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

import pytest

# The oracle logic (alias resolution, span-containment book/chapter derivation,
# classification) is production code in palimpsest.gold, shared verbatim with the CLI's
# ``gold verify`` — so this test asserts exactly what that command computes.
from palimpsest.gold import classify_books, load_canon

# Marker Bibles whose chapter sections are 1:1 canonical chapters (guaranteed by
# gen_marker_gold parity) and which use standard book names → strict oracle targets.
_STRICT_IDXS = [201, 202, 203, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219]
# The KJV-Apocrypha edition whose deuterocanon counts are externally established.
_KJV_APOCRYPHA_IDX = 219


@pytest.mark.parametrize("idx", _STRICT_IDXS, ids=[f"work-{i}" for i in _STRICT_IDXS])
def test_core66_chapter_counts(idx: int) -> None:
    """Every 66-book-core book present resolves and matches the external chapter count."""
    core_ok, core_bad, _deutero, unresolved = classify_books(idx)
    assert not core_bad, f"core-66 chapter mismatches: {core_bad}"
    assert not unresolved, f"unresolved book labels (add alias?): {[u[1] for u in unresolved]}"
    assert core_ok, "no core-66 books resolved — Bible contains none of the canonical 66?"


def test_kjv_apocrypha_chapter_counts() -> None:
    """The KJV-1611 comprehensive edition (219) matches the established KJV-Apocrypha counts."""
    _core_ok, _core_bad, deutero, _unresolved = classify_books(_KJV_APOCRYPHA_IDX)
    bad = [(k, lbl, got, exp) for (k, lbl, got, exp) in deutero if got != exp]
    assert not bad, f"KJV-Apocrypha chapter mismatches: {bad}"
    assert len(deutero) >= 14, f"expected 14 apocrypha books, resolved {len(deutero)}"


def test_oracle_covers_full_protestant_canon() -> None:
    """The oracle data itself is complete: 66 core books, all counts positive ints."""
    core = load_canon()["protestant_66"]
    assert len(core) == 66, f"protestant_66 has {len(core)} books, expected 66"
    assert all(isinstance(v, int) and v > 0 for v in core.values())
    assert core["genesis"] == 50 and core["psalms"] == 150 and core["revelation"] == 22
