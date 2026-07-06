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
detector-discovered structure.

idx 108 (Douay-Rheims original) is a Catholic *Vulgate*-canon edition, so the Protestant-66
name-keyed oracle does not apply — the canon genuinely differs (Esther has the Greek
additions → 16 chapters, Daniel includes Susanna/Bel → 14, Baruch folds in the Epistle of
Jeremiah → 6, 1 Esdras = Ezra = 10) and its book labels are verbose incipits that defeat
name lookup. It gets its own external gate: the ORDERED ``catholic_dr`` oracle, checked
positionally against the fixed Clementine Vulgate order (identity by label token, gated on
the external chapter count). 75/76 books match; the sole discrepancy — Tobias carrying a
spurious 15th chapter — is a documented artifact of the upstream CC0 dataset (it captured
the book's Argument as a 1-verse chapter 1), recorded in the sources manifest's
``canon_exceptions`` rather than silently blessed.
"""
from __future__ import annotations

import pytest

# The oracle logic (alias resolution, span-containment book/chapter derivation,
# classification) is production code in palimpsest.gold, shared verbatim with the CLI's
# ``gold verify`` — so this test asserts exactly what that command computes.
from palimpsest.gold import (
    classify_books,
    classify_books_catholic,
    load_canon,
    novel_chapter_count,
    quran_sura_count,
)

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


# ── Catholic (Douay-Rheims / Clementine Vulgate) ordered oracle: idx 108, 109 ─────

# idx 108 (modern) and idx 109 (archaic diplomatic) are the two renderings of the SAME basis
# database; they share the catholic_dr skeleton and element structure exactly, so both must clear
# the ordered Vulgate oracle 76/76 (differing only in the scripture spelling/typeset layer).
_CATHOLIC_IDXS = (108, 109)


@pytest.mark.parametrize("idx", _CATHOLIC_IDXS)
def test_catholic_dr_canon_counts(idx: int) -> None:
    """DR-original (108 modern / 109 archaic) matches the external Vulgate chapter counts in order.

    Every book must sit in its expected Clementine-Vulgate slot (identity by label token,
    so a dropped/reordered book fails as an alignment error) and carry the externally
    established chapter count. The enriched reconstruction drops the spurious Tobias
    Argument chapter that the upstream CC0 dataset had captured, so all 76 books now match
    the Vulgate counts with no exceptions.
    """
    ok, count_bad, align_bad = classify_books_catholic(idx)
    assert not align_bad, f"catholic canon order/identity errors: {align_bad}"
    assert count_bad == [], (
        f"unexpected catholic chapter mismatches: {count_bad}"
    )
    assert len(ok) == 76, f"expected all 76 books to match the Vulgate counts, got {len(ok)}"


def test_catholic_oracle_data_complete() -> None:
    """The catholic_dr oracle data is well-formed: 76 ordered books, positive-int counts."""
    cath = load_canon()["catholic_dr"]
    assert len(cath) == 76, f"catholic_dr has {len(cath)} books, expected 76 (73 canon + 3 appendix)"
    assert all(isinstance(e["chapters"], int) and e["chapters"] > 0 for e in cath)
    assert all(e["match"] and e["book"] for e in cath), "every entry needs a book key and match token"
    assert cath[0]["book"] == "genesis" and cath[-1]["book"] == "4 esdras"


# ── Qur'an flat-sura count oracle: idx 29, 107 ────────────────────────────────────

# Both Qur'an gold maps: their 114 suras are top-level ``chapter`` sections with no
# enclosing ``book``, so the Bibles' positional book-identity oracle does not apply — the
# externally-established fact is the fixed 114-sura canon, gated as a pure count.
_QURAN_IDXS = (29, 107)


@pytest.mark.parametrize("idx", _QURAN_IDXS, ids=[f"work-{i}" for i in _QURAN_IDXS])
def test_quran_sura_count(idx: int) -> None:
    """Each Qur'an map carries exactly the canonical 114 suras.

    The Qur'an is structurally flat (114 sura sections directly under the body, no
    book → chapter nesting), so the positional book-alignment used for the Bibles cannot
    apply. The external fact is the fixed 114-sura canon, so the oracle is a pure section
    count — checked here against the ``quran_suras`` figure in canon_chapters.json.
    """
    assert quran_sura_count(idx) == load_canon()["quran_suras"] == 114


def test_quran_oracle_data_present() -> None:
    """The canon oracle records the fixed 114-sura Qur'an count as a positive int."""
    suras = load_canon()["quran_suras"]
    assert isinstance(suras, int) and suras == 114


# Single-work novels with an author-fixed, edition-stable chapter total.
_NOVEL_IDXS = ((56, 33), (71, 10))


@pytest.mark.parametrize("idx,expected", _NOVEL_IDXS, ids=[f"work-{i}" for i, _ in _NOVEL_IDXS])
def test_novel_chapter_count(idx: int, expected: int) -> None:
    """Each novel map carries exactly its canonical chapter total.

    Like the Qur'an, these novels are structurally flat (top-level ``chapter`` sections,
    no book nesting), so the oracle is a pure section count checked against the
    author-fixed figure in ``canon_chapters.json['novel_chapters']``.
    """
    assert novel_chapter_count(idx) == load_canon()["novel_chapters"][str(idx)] == expected


def test_novel_oracle_data_present() -> None:
    """The canon oracle records each gated novel's chapter total as a positive int."""
    novels = load_canon()["novel_chapters"]
    assert novels["56"] == 33 and novels["71"] == 10
    assert all(isinstance(v, int) and v > 0 for v in novels.values())
