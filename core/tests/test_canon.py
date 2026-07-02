"""Canonical book → genre-division + apocrypha mapping (palimpsest.canon)."""
from palimpsest.canon import DIVISIONS, book_division


def test_pentateuch_is_law():
    for b in ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"):
        assert book_division(b) == ("Law", False)


def test_john_gospel_vs_epistle_by_ordinal():
    assert book_division("John") == ("Gospels", False)
    assert book_division("1 John") == ("Epistles", False)
    assert book_division("2 John") == ("Epistles", False)
    assert book_division("3 John") == ("Epistles", False)


def test_acts_historical_and_revelation_epistles():
    assert book_division("Acts") == ("Historical", False)
    assert book_division("Revelation") == ("Epistles", False)
    assert book_division("Apocalypse") == ("Epistles", False)


def test_dr_latin_and_old_spelling_names():
    assert book_division("3 Kings") == ("Historical", False)
    assert book_division("1 Paralipomenon") == ("Historical", False)
    assert book_division("Abdias") == ("Prophets-Minor", False)
    assert book_division("Aggeus") == ("Prophets-Minor", False)
    assert book_division("Sophonias") == ("Prophets-Minor", False)
    assert book_division("Canticle of Canticles") == ("Wisdom-poetry", False)
    assert book_division("Isaias") == ("Prophets-Major", False)


def test_deuterocanon_keeps_literary_genre_and_is_flagged_apocryphal():
    assert book_division("Wisdom") == ("Wisdom-poetry", True)
    assert book_division("Ecclesiasticus") == ("Wisdom-poetry", True)
    assert book_division("Baruch") == ("Prophets-Major", True)
    assert book_division("1 Machabees") == ("Historical", True)
    assert book_division("Tobias") == ("Historical", True)
    assert book_division("Judith") == ("Historical", True)
    assert book_division("Prayer of Manasses") == ("Wisdom-poetry", True)


def test_esdras_collision_resolved_by_dr_vulgate_convention():
    # DR/Vulgate: 1-2 Esdras ARE Ezra/Nehemiah — canonical Historical, not apocryphal.
    assert book_division("1 Esdras") == ("Historical", False)
    assert book_division("2 Esdras") == ("Historical", False)
    # Apocryphal 3-4 Esdras, incl. the raw "Booke of" heading form the DR appendix prints.
    assert book_division("Third Booke of Esdras") == ("Historical", True)
    assert book_division("Fourth Booke of Esdras") == ("Prophets-Major", True)


def test_edition_tag_stripped_and_non_scripture_rejected():
    assert book_division("Abdias (1582)") == ("Prophets-Minor", False)
    assert book_division("Jude (1582)") == ("Epistles", False)
    assert book_division("Chapter 5") == (None, False)
    assert book_division("Introduction") == (None, False)
    assert book_division("") == (None, False)


def test_every_returned_division_is_canonical():
    for name in ("Genesis", "Ruth", "Psalms", "Daniel", "Amos", "Luke", "Hebrews", "Baruch"):
        div, _ = book_division(name)
        assert div in DIVISIONS
