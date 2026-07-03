"""Canonical Bible book → literary-genre division, plus deuterocanon/apocrypha membership.

Overlays a content-type layer on the structural book layer: consecutive books of one genre
are wrapped in a ``genre_division`` container, and each book carries its genre (and, for the
deuterocanon, an ``apocrypha`` flag) in ``metadata``. The mapping normalizes across the
naming conventions a scripture edition can print — Protestant, Douay-Rheims/Latin
("Paralipomenon", "Aggeus", "Apocalypse"), and old-English — so the *same* seven divisions
apply to every version even though their physical book order differs.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

#: The seven canonical-division genre categories, in canonical order.
DIVISIONS: tuple[str, ...] = (
    "Law", "Historical", "Wisdom-poetry", "Prophets-Major",
    "Prophets-Minor", "Gospels", "Epistles",
)

# base book-name (lowercased, ordinal-stripped) → division. Covers the Protestant 66 plus
# the DR/Latin and old-English spelling variants the detector's book lexicon can emit
# (layout.py:_BIBLE_BOOK_NAMES). Deuterocanonical books are placed in their LITERARY genre
# here and separately flagged apocryphal below. ``john`` and ``esdras`` are ordinal-sensitive
# and resolved in :func:`book_division`, so they are intentionally absent from this table.
_BASE_DIVISION: dict[str, str] = {
    # Law (Pentateuch)
    "genesis": "Law", "exodus": "Law", "leviticus": "Law", "numbers": "Law",
    "deuteronomy": "Law",
    # Historical (incl. deuterocanonical histories Tobit/Judith/Maccabees; Acts by rule)
    "joshua": "Historical", "josue": "Historical", "judges": "Historical",
    "ruth": "Historical", "samuel": "Historical", "kings": "Historical",
    "chronicles": "Historical", "paralipomenon": "Historical", "ezra": "Historical",
    "nehemiah": "Historical", "nehemias": "Historical", "esther": "Historical",
    "tobit": "Historical", "tobias": "Historical", "judith": "Historical",
    "maccabees": "Historical", "machabees": "Historical", "acts": "Historical",
    "susanna": "Historical", "bel and the dragon": "Historical",
    # Wisdom-poetry (incl. deuterocanonical Wisdom/Sirach; the Prayer of Manasses)
    "job": "Wisdom-poetry", "psalms": "Wisdom-poetry", "psalm": "Wisdom-poetry",
    "proverbs": "Wisdom-poetry", "ecclesiastes": "Wisdom-poetry",
    "canticle of canticles": "Wisdom-poetry", "song of solomon": "Wisdom-poetry",
    "song of songs": "Wisdom-poetry", "wisdom": "Wisdom-poetry",
    "wisdom of solomon": "Wisdom-poetry",
    "sirach": "Wisdom-poetry", "ecclesiasticus": "Wisdom-poetry",
    "prayer of manasses": "Wisdom-poetry", "prayer of manasseh": "Wisdom-poetry",
    "prayer of azariah": "Wisdom-poetry", "song of the three children": "Wisdom-poetry",
    # Prophets-Major (incl. deuterocanonical Baruch, per the project rule)
    "isaiah": "Prophets-Major", "isaias": "Prophets-Major", "jeremiah": "Prophets-Major",
    "jeremias": "Prophets-Major", "lamentations": "Prophets-Major", "baruch": "Prophets-Major",
    "letter of jeremiah": "Prophets-Major", "epistle of jeremiah": "Prophets-Major",
    "epistle of jeremy": "Prophets-Major",
    "ezekiel": "Prophets-Major", "ezechiel": "Prophets-Major", "daniel": "Prophets-Major",
    # Prophets-Minor (the Twelve)
    "hosea": "Prophets-Minor", "osee": "Prophets-Minor", "joel": "Prophets-Minor",
    "amos": "Prophets-Minor", "obadiah": "Prophets-Minor", "abdias": "Prophets-Minor",
    "jonah": "Prophets-Minor", "jonas": "Prophets-Minor", "micah": "Prophets-Minor",
    "micheas": "Prophets-Minor", "nahum": "Prophets-Minor", "habakkuk": "Prophets-Minor",
    "habacuc": "Prophets-Minor", "zephaniah": "Prophets-Minor", "sophonias": "Prophets-Minor",
    "haggai": "Prophets-Minor", "aggeus": "Prophets-Minor", "zechariah": "Prophets-Minor",
    "zacharias": "Prophets-Minor", "malachi": "Prophets-Minor", "malachias": "Prophets-Minor",
    # Gospels ("john" without ordinal resolves here in book_division)
    "matthew": "Gospels", "mark": "Gospels", "luke": "Gospels",
    # Epistles (Revelation/Apocalypse by rule; "1/2/3 john" resolve here in book_division)
    "romans": "Epistles", "corinthians": "Epistles", "galatians": "Epistles",
    "ephesians": "Epistles", "philippians": "Epistles", "colossians": "Epistles",
    "thessalonians": "Epistles", "timothy": "Epistles", "titus": "Epistles",
    "philemon": "Epistles", "hebrews": "Epistles", "james": "Epistles",
    "peter": "Epistles", "jude": "Epistles", "revelation": "Epistles",
    "apocalypse": "Epistles",
}

# Deuterocanonical / apocryphal base names (Protestant "Apocrypha"). These carry
# metadata["apocrypha"]=True on their book section in addition to their literary genre.
_APOCRYPHA_BASES: frozenset[str] = frozenset({
    "tobit", "tobias", "judith", "wisdom", "wisdom of solomon", "sirach", "ecclesiasticus",
    "baruch", "letter of jeremiah", "epistle of jeremiah", "epistle of jeremy",
    "maccabees", "machabees", "prayer of manasses", "prayer of manasseh",
    "susanna", "bel and the dragon", "song of the three children", "prayer of azariah",
})

_ORDINAL_NUM: dict[str, int] = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3,
    "4th": 4, "iv": 4, "iii": 3, "ii": 2, "i": 1, "1": 1, "2": 2, "3": 3, "4": 4,
}
# Longest ordinal alternatives first so "iv"/"iii" win over "i".
_ORDINAL_RE = re.compile(
    r"^(?:(first|second|third|fourth|1st|2nd|3rd|4th|iv|iii|ii|i|[1234])\s+)?(.+)$"
)
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")  # strip edition tags like "Abdias (1582)"
_THE_RE = re.compile(r"^the\s+")
_BOOKOF_RE = re.compile(r"^book[e]?\s+of\s+")  # "Third Booke of Esdras" → ordinal 3 + "esdras"


def _normalize(name: str) -> tuple[int | None, str]:
    """(ordinal_or_None, lowercased_base_name) from a printed book display name.

    Handles a leading ``The``, an ordinal (word or numeral, before an optional ``Book(e) of``
    wrapper), and the ``Book(e) of`` wrapper itself — so raw source headings like
    "Third Booke of Esdras" reduce to ordinal 3 + base "esdras".
    """
    core = _PAREN_RE.sub("", name.strip())
    core = re.sub(r"[.,:;]+$", "", core).strip().lower()
    core = _THE_RE.sub("", core)
    m = _ORDINAL_RE.match(core)
    if not m:
        return None, _BOOKOF_RE.sub("", core).strip()
    ordinal = _ORDINAL_NUM.get(m.group(1) or "")
    base = _BOOKOF_RE.sub("", re.sub(r"\s+", " ", m.group(2).strip())).strip()
    return ordinal, base


def esdras_is_apocryphal(book_names: Iterable[str]) -> bool:
    """Whether an edition's ``1/2 Esdras`` are the apocryphal books rather than Ezra/Nehemiah.

    ``Esdras`` collides across canons: Douay-Rheims/Vulgate print Ezra and Nehemiah *as*
    "1 Esdras" / "2 Esdras" (canonical Historical) and have no standalone Ezra, whereas a
    KJV-*Apocrypha* edition keeps Ezra and Nehemiah under their own names and prints separate
    apocryphal "1/2 Esdras" (the Greek Esdras and the Ezra-apocalypse). The tell is therefore
    whether the edition already names Ezra (and Nehemiah) directly: if it does, any Esdras it
    also prints must be the apocryphal ones. Deriving the hint from the book set keeps it
    edition-agnostic — no per-edition configuration to maintain.
    """
    bases = {_normalize(n)[1] for n in book_names}
    return "ezra" in bases and ("nehemiah" in bases or "nehemias" in bases)


def book_division(name: str, *, esdras_apocryphal: bool = False) -> tuple[str | None, bool]:
    """Return ``(genre_division, is_apocrypha)`` for a printed book name.

    ``genre_division`` is one of :data:`DIVISIONS` or ``None`` when the name is not a
    recognized scripture book (so a non-scripture heading never spawns a division). The
    match is spelling/naming-agnostic (Protestant, Douay-Rheims/Latin, old-English) and
    ordinal-aware where it matters:

    * ``John`` with no ordinal is a Gospel; ``1/2/3 John`` are Epistles.
    * ``Esdras`` collides across canons — in Douay-Rheims/Vulgate ``1/2 Esdras`` ARE
      Ezra/Nehemiah (canonical Historical), while apocryphal ``3/4 Esdras`` are the Greek
      Esdras (Historical) and the Ezra-apocalypse (Prophets-Major). Pass
      ``esdras_apocryphal=True`` (see :func:`esdras_is_apocryphal`) for a KJV-*Apocrypha*
      edition, which keeps Ezra/Nehemiah under their own names, so *its* "1 Esdras" is the
      Greek Esdras (Historical) and "2 Esdras" the Ezra-apocalypse (Prophets-Major) — both
      apocryphal, mirroring the Vulgate 3/4 Esdras.
    """
    ordinal, base = _normalize(name)
    if base == "john":
        return ("Epistles" if ordinal else "Gospels"), False
    if base == "esdras":
        if ordinal in (3, 4):
            return ("Historical" if ordinal == 3 else "Prophets-Major"), True
        if esdras_apocryphal:
            return ("Prophets-Major" if ordinal == 2 else "Historical"), True
        return "Historical", False
    return _BASE_DIVISION.get(base), base in _APOCRYPHA_BASES
