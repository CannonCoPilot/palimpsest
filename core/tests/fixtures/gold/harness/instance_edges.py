#!/usr/bin/env python
"""Per-instance-edge materializer for repeating gold structures (Phase: per-instance-edge gold).

The gold contract stores, for a repeating structure, a COUNT + a few exemplars,
never the per-instance boundaries (schema: "Offsets derived at eval time, never
stored"). That makes assignment-correctness (A2) and boundary-accuracy (A3)
unscorable. This module closes that gap WITHOUT storing brittle offsets: each
repeating structure carries a declarative *instance rule* that materializes all
per-instance start edges from reference_text() at eval time. The rule is only
trusted once it reconciles to the hand-verified expected_count (the COUNT GATE).

A materialized gold edge set is an INDEPENDENT reference segmentation (authored
from human reading of the structure), so the production detector's boundaries and
types can finally be graded against it:
  * A3 boundary accuracy — does each gold edge land on a detector boundary?
  * A2 assignment correctness — what type does the detector assign over each
    gold instance's span, vs the gold's intended type?

Usage:
  instance_edges.py reconcile <idx>   # materialize + check the count gate, pinpoint anomalies
  instance_edges.py a23 <idx>         # boundary-accuracy (A3) + assignment-correctness (A2)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import project_for, _layout_boundaries  # noqa: E402
from harness import _endnote_separator, detect_layout_sections  # noqa: E402

_ROMAN = re.compile(r"^[IVXLC]+$", re.M)
_ROMAN_VAL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_to_int(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s):
        v = _ROMAN_VAL[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


# ── Declarative instance rules (one entry per repeating gold structure) ──────────
# kind="roman_in_span": every bare Roman-numeral line inside [span_start, span_end)
# is an instance header; numbering restarts at each part (value resets to I). Named
# proems (part openers that are not Roman-numbered) are added via extra_anchors.
RULES: dict[int, list[dict]] = {
    102: [
        {
            "type": "poetry",
            "kind": "roman_in_span",
            "span_start": "THIS is my letter to the world",
            "span_end": "INSPIRED BY EMILY DICKINSON'S POETRY\n\nDickinson is the American poet",
            "extra_anchors": [
                "THIS is my letter to the world",       # PART ONE proem (body, small-caps)
                "MY nosegays are for captives",          # PART TWO proem
                "IT's all I have to bring to-day",       # PART THREE proem
                "ONE sister have I in our house",        # PART FIVE proem
            ],
            "expected_count": 595,  # reconciled: 591 distinct numbered headers + 4 proems
            #   (gold's 589 was a max-numeral count; edition numbers non-monotonically)
        }
    ],
    104: [
        {
            "type": "poetry",
            "kind": "roman_in_span",
            "span_start": "ONE\n\nFIVE AMERICANS",  # section ONE marker
            "span_end": "Transcriber's note\n\nNon-standard spelling retained",
            "extra_anchors": [],  # no proems; every poem is Roman-numbered (restarts per section)
            "expected_count": 84,  # ONE I-XL(40)+TWO I-XI(11)+THREE I-X(10)+FOUR I-XVIII(18)+FIVE I-V(5)
        }
    ],
    103: [
        {
            "type": "poetry",
            "kind": "title_list",  # titled (not numbered) poems; body renders "Title\n\n<first line>"
            "titles": [
                "The Road Not Taken", "Christmas Trees", "An Old Man's Winter Night",
                "A Patch of Old Snow", "In the Home Stretch", "The Telephone",
                "Meeting and Passing", "Hyla Brook", "The Oven Bird", "Bond and Free",
                "Birches", "Pea Brush", "Putting In the Seed", "A Time to Talk",
                "The Cow in Apple Time", "An Encounter", "Range-Finding", "The Hill Wife",
                "The Bonfire", "A Girl's Garden", "The Exposed Nest", "\"Out, Out—\"",
                "Brown's Descent or The Willy-Nilly Slide", "The Gum-Gatherer",
                "The Line-Gang", "The Vanishing Red", "Snow", "The Sound of the Trees",
            ],
            "expected_count": 28,  # 28 top-level poems per the printed TOC (Hill Wife = 1 entry)
        }
    ],
    71: [
        {
            "type": "chapter",  # title_list generalizes from poetry to titled prose chapters
            "kind": "title_list",
            "titles": [
                "Story of the Door", "Search for Mr. Hyde", "Dr. Jekyll Was Quite at Ease",
                "The Carew Murder Case", "Incident of the Letter", "Incident of Dr. Lanyon",
                "Incident at the Window", "The Last Night", "Dr. Lanyon's Narrative",
                "Henry Jekyll's Full Statement of the Case",
            ],
            "expected_count": 10,  # 10 titled, un-numbered chapter sections
        }
    ],
    56: [
        {
            "type": "epigraph",  # one verse/quote epigraph opens each of 33 chapters
            "kind": "regex_in_span",
            "pattern": r"(?m)^Chapter \d+\n\n",
            "at": "end",  # instance = the epigraph, immediately after the chapter header
            "expected_count": 33,
        },
        {
            "type": "chapter",  # secondary: the 33 numbered chapters (covers headers + prose)
            "kind": "regex_in_span",
            "pattern": r"(?m)^Chapter \d+\n",
            "at": "start", "tile": True,
            "expected_count": 33,
        },
    ],
    5: [
        {
            "type": "book",  # 73 books (generic) — boundary at each book's Chapter 1
            "kind": "regex_in_span",
            "pattern": r"(?m)^.{0,40}?\bChapter 1\b",
            "at": "start", "tile": True,
            "expected_count": 73,
        },
        {
            "type": "chapter",  # 1334 chapters (specific) tile the verse bodies
            "kind": "regex_in_span",
            "pattern": r"(?m)^.{0,40}?\bChapter \d+\b",
            "at": "start", "tile": True,
            "expected_count": 1334,
        },
        {
            "type": "chapter_heading",  # 1334 heading+summary markers (gold primary)
            "kind": "regex_in_span",
            "pattern": r"(?m)^.{0,40}?\bChapter \d+\b",
            "at": "start", "tile": False,
            "expected_count": 1334,
        },
    ],
    107: [
        {
            "type": "chapter",  # 114 surahs (specific) tile the body; name-line + OCR-tolerant (Rev marker
            "kind": "regex_in_span",
            "pattern": r"(?m)^['‘’A-Z][^\n]{0,30}\n\(Rev[^\n]{0,40}",
            "at": "start", "tile": True,
            "expected_count": 114,
        },
    ],
    70: [
        {
            "type": "volume",  # 2 volumes (generic), printed "Volume I"/"Volume II" lines
            "kind": "regex_in_span",
            "pattern": r"(?m)^Volume [IVXLC]+\n\n",
            "at": "start", "tile": True,
            "span_start": "Charlotte Temple\n\nA Tale of Truth\n\nVolume I",
            "span_end": "Endnotes\n\nThe above lines, in the original American edition",
            "expected_count": 2,
        },
        {
            "type": "chapter",  # 35 chapters (specific); ^Roman + optional OCR-fused digits
            "kind": "regex_in_span",
            "pattern": r"(?m)^[IVXLC]+\d*\n\n",
            "at": "start", "tile": True,
            "span_start": "Volume I\n\nI\n\nA Boarding School",
            "span_end": "Endnotes\n\nThe above lines, in the original American edition",
            "expected_count": 35,
        },
    ],
    106: [
        {"type": "part", "kind": "regex_in_span",
         "pattern": r"(?m)^(?:PART I\nThe Adam and Eve Traditions in Armenian|Part II\nTexts and Translations)$",
         "at": "start", "tile": True,
         "span_start": "PART I\nThe Adam and Eve Traditions in Armenian",
         "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
         "expected_count": 2},
        {"type": "commentary", "kind": "regex_in_span",
         "pattern": r"(?m)^(?:-\d+-\n[1-5]\. Adam and Eve Traditions|-177-\nAppendix: Satan and the Serpent)",
         "at": "start", "tile": True,
         "span_start": "-11-\n1. Adam and Eve Traditions in\nFifth-Century",
         "span_end": "Part II\nTexts and Translations",
         "expected_count": 6},
        {"type": "chapter", "kind": "regex_in_span",
         "pattern": r"(?m)^-\d+-\n[1-5]\. Adam and Eve Traditions",
         "at": "start", "tile": True,
         "span_start": "-11-\n1. Adam and Eve Traditions in\nFifth-Century",
         "span_end": "-177-\nAppendix: Satan and the Serpent",
         "expected_count": 5},
        {"type": "chapter", "kind": "regex_in_span",
         "pattern": (r"(?m)^-\d+-\n(?:Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh"
                     r"|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth) Century\n"),
         "at": "start", "tile": True,
         "span_start": "Part II\nTexts and Translations",
         "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
         "expected_count": 14},
        {"type": "translation", "kind": "regex_in_span",
         "pattern": r"(?m)^.{1,60}? C\d+(?:[–\-]\d+)?\n",
         "at": "start", "tile": True,
         "span_start": "Part II\nTexts and Translations",
         "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
         "expected_count": 126},
        {"type": "footnotes", "kind": "regex_in_span",
         "pattern": "(?m)^\\d+\\. ",
         "at": "start", "tile": False,
         "span_start": "PART I\nThe Adam and Eve Traditions in Armenian",
         "span_end": "to make sweetness.\n\nAlphabetical List of Authors Quoted",
         "expected_count": None},
    ],
    18: [
        {
            "type": "part",  # 3 Tertullian classes (generic)
            "kind": "regex_in_span",
            "pattern": r"(?m)^Part (?:First|Second|Third)\.",
            "at": "start", "tile": True, "expected_count": 3,
        },
        {
            "type": "translation",  # 23 translated treatises (specific) tile the body
            "kind": "regex_in_span",
            "pattern": r"\[Translated by",
            "at": "start", "tile": True, "expected_count": 23,
        },
        {
            "type": "chapter",  # 743 in-body chapter headings (markers); lookaheads drop TOC echoes
            "kind": "regex_in_span",
            "pattern": r"(?m)^Chapter [IVXLC]+\.(?!\n\nChapter [IVXLC]+\.)(?!\n\nElucidations\.)(?!\n\n[IVXLC]+\.\n\n)",
            "at": "start", "tile": False, "expected_count": 743,
        },
        {
            "type": "footnotes",  # 6280 numbered note lines (markers) overlaying the body
            "kind": "regex_in_span",
            "pattern": "(?m)^\\d+\xa0\xa0\xa0 ",
            "at": "start", "tile": False, "expected_count": 6280,
        },
        {
            "type": "commentary",  # 13 Elucidation blocks (markers)
            "kind": "regex_in_span",
            "pattern": r"(?m)^Elucidations\.\n\n[—–-]{3,}\n\n[IVXLC]+\.\n\n\(",
            "at": "start", "tile": False, "expected_count": 13,
        },
        {
            "type": "introduction",  # 5 Introductory Notice headings (markers)
            "kind": "regex_in_span",
            "pattern": r"Introductory Notice",
            "at": "start", "tile": False, "expected_count": 5,
        },
    ],
    29: [
        {
            "type": "chapter",  # 114 surahs (specific) tile the main body
            "kind": "regex_in_span",
            "pattern": r"(?m)^THE [A-Z\-]+(?: [A-Z\-]+)? SŪRAH$",
            "at": "start", "tile": True,
            "span_start": "THE MESSAGE OF THE QUR'ĀN\n\nTHE FIRST SŪRAH",
            "span_end": "APPENDIX I\n\nSYMBOLISM AND ALLEGORY IN THE QUR'ĀN",
            "expected_count": 114,
        },
        {
            "type": "appendix",  # 4 Asad essays after surah 114
            "kind": "regex_in_span",
            "pattern": r"(?m)^APPENDIX [IVX]+$",
            "at": "start", "tile": True,
            "span_start": "APPENDIX I\n\nSYMBOLISM AND ALLEGORY IN THE QUR'ĀN",
            "span_end": "1 It is to be borne in mind that, in its final compilation",
            "expected_count": 4,
        },
    ],
    100: [
        {
            "type": "book",  # 73 books (generic)
            "kind": "regex_in_span",
            "pattern": r"(?m)^.{0,40}?\bChapter 1\b",
            "at": "start", "tile": True,
            "expected_count": 73,
        },
        {
            "type": "chapter",  # 1334 chapters (specific) — (?!\() drops the lone "(Psalm Chapter 10…)" note
            "kind": "regex_in_span",
            "pattern": r"(?m)^(?!\()(?:.{0,40}?)\bChapter \d+\b",
            "at": "start", "tile": True,
            "expected_count": 1334,
        },
        {
            "type": "chapter_heading",  # 1334 heading+summary markers
            "kind": "regex_in_span",
            "pattern": r"(?m)^(?!\()(?:.{0,40}?)\bChapter \d+\b",
            "at": "start", "tile": False,
            "expected_count": 1334,
        },
    ],
}

# ── Works whose rule sets are built programmatically (verbose patterns) ──────────
RULES[64] = [
    {"type": "chapter", "kind": "regex_in_span", "pattern": r"(?m)^[\[I]Chapt",
     "at": "start", "tile": True, "span_start": "[Chapter I}",
     "span_end": "Introduction to The Second Book\n\nof Enoch:\n\nSlavonic Enoch",
     "expected_count": 108},
    {"type": "chapter", "kind": "regex_in_span", "pattern": r"Chapter (?:\d+|S)\b[\"”’)]*\n\n",
     "at": "start", "tile": True, "span_start": "Chapter 1\n\n1 There was a wise man",
     "span_end": "Intro duction of 3 Enoch", "expected_count": 68},
    {"type": "chapter", "kind": "regex_in_span", "pattern": r"(?m)^CHAPTER\b",
     "at": "start", "tile": True, "span_start": "Intro duction of 3 Enoch",
     "expected_count": 54},
]

_P80 = "(?m)" + "|".join("(?:%s)" % h for h in [
    r"\n\nRules\n\nThis chapter contains", r"Halakhic Texts\n\nA large part",
    r"Literature with Eschatological Content\n\nAlthough", r"Exegetical Literature\n\nThe exegetical",
    r"Para-biblical Literature\n\nThis chapter also gathers", r"Poetic Texts\n\nDue to our ignorance",
    r"Liturgical Texts\n\nThis chapter contains a set",
    r"Astronomical Texts, Calendars and Horoscopes\n\nThis chapter assembles",
    r"The Copper Scroll\n\nPossibly the most mystifying"])
_MS80 = (r"(?m)(?:^(?:[ABC] )?(?:[0-9]{1,2}|[ilI])Q[^\n]{0,68}\([^\n)]{0,45}\)\s*$"
         r"|^Damascus Document\w? \(CD-[AB]\)\s*$)")
_SP80 = [
    ("1QRule of the Community (iQs)", "Halakhic Texts\n\nA large part of the contents", 25),
    ("4QHalakhic Letter' (4Q394 [4QMMT°])", "Literature with Eschatological Content\n\nAlthough eschatology", 18),
    ("1QWar Scroll (1QM [+1Q33])\n\nCol. i i For the Ins[tructor: The Rule] of the War.", "Exegetical Literature\n\nThe exegetical activity", 22),
    ("4QTargum of Leviticus (4Q156 14QtgLev])", "Para-biblical Literature\n\nThis chapter also gathers together", 30),
    ("A 4QReworked Pentateuch' (4Q158 [4QRP'])", "Poetic Texts\n\nDue to our ignorance", 91),
    ("4QPsalmsi (4Q88 [4QPW])", "Liturgical Texts\n\nThis chapter contains a set of poetic texts", 41),
    ("4QDaily Prayers' (4Q5o3 [4QPrQuot])", "Astronomical Texts, Calendars and Horoscopes\n\nThis chapter assembles", 33),
    ("4QAstronomical Enochb (4Q2o9 [4QEnastrb at])", "The Copper Scroll\n\nPossibly the most mystifying", 10),
    ("3QCopper Scroll (3Q15)", "List of the Manuscripts from Qumran", 1),
]
RULES[80] = [{"type": "part", "kind": "regex_in_span", "pattern": _P80,
              "at": "start", "tile": True, "expected_count": 9}] + [
    {"type": "translation", "kind": "regex_in_span", "pattern": _MS80, "at": "start",
     "tile": True, "span_start": s, "span_end": e, "expected_count": n} for s, e, n in _SP80]

RULES[19] = [{"type": "letter", "kind": "salutation", "expected_count": 124}]

RULES[48] = [
    {"type": "introduction", "kind": "regex_in_span",
     "pattern": r"(?m)^(?:A (?:new )?translation and introduction\n\nby |Introduction\n\nby |by Lorne R\. Zelyck\n\nIrenaeus)",
     "at": "start", "tile": True,
     "span_start": "I. Gospels and Related Traditions of New Testament Figures", "expected_count": 29},
    {"type": "translation", "kind": "regex_in_span", "pattern": r"(?m)^Translations?\n\n",
     "at": "start", "tile": False,
     "span_start": "I. Gospels and Related Traditions of New Testament Figures", "expected_count": 30},
    {"type": "bibliography", "kind": "regex_in_span", "pattern": r"(?m)^Bibliography\n\n",
     "at": "start", "tile": False,
     "span_start": "I. Gospels and Related Traditions of New Testament Figures", "expected_count": 29},
]

_CHAP101 = (r"(?m)^(?:Chapter|Section) \d+\b|^The Book of Enos\b|^The Book of Jarom\b"
            r"|^The Book of Omni\b|^The Words of Mormon\b|^Fourth Nephi\b"
            r"|^Joseph Smith—Matthew\n\n|^Joseph Smith—History\n\n|^The Articles of Faith\b")
_VOL101 = r"(?m)^BOOK OF\n\nMORMON|T\nhe Doctrine and Covenants is a co|T\nhe Pearl of Great Price is a se"
_BOOK101 = (r"(?m)^The First Book of Nephi\b|^The Second Book of Nephi\b|^The Book of Jacob\b"
            r"|^The Book of Enos\b|^The Book of Jarom\b|^The Book of Omni\b|^The Words of Mormon\b"
            r"|^The Book of Mosiah\b|^The Book of Alma\b|^The Book of Helaman\b|^Third Nephi\b"
            r"|^Fourth Nephi\b|^The Book of Mormon\n\nChapter 1\n\nAmmaron|^The Book of Ether\b"
            r"|^The Book of Moroni\b|^Selections from the\b|^The Book of Abraham\b"
            r"|^Joseph Smith—Matthew\n\n|^Joseph Smith—History\n\n|^The Articles of Faith\b")
RULES[101] = [
    {"type": "volume", "kind": "regex_in_span", "pattern": _VOL101, "at": "start", "tile": True, "expected_count": 3},
    {"type": "book", "kind": "regex_in_span", "pattern": _BOOK101, "at": "start", "tile": True, "expected_count": 20},
    {"type": "chapter", "kind": "regex_in_span", "pattern": _CHAP101, "at": "start", "tile": True, "expected_count": 393},
    {"type": "chapter_heading", "kind": "regex_in_span", "pattern": _CHAP101, "at": "start", "tile": False, "expected_count": 393},
    {"type": "footnotes", "kind": "regex_in_span", "pattern": r"(?m)^\d+ [a-z] ", "at": "start", "tile": False, "expected_count": 8404},
]

_CHAP6 = "\n\n(?:(?!\n\n)[\\s\\S])*?(?=\n\n1\xa0)"  # argument/superscription block before each verse-1
_OBAD6 = ["\n\nOBADIAH\n\n1 1 The vision"]  # Obadiah's v1 fused into its argument (no \n\n1\xa0 marker)
RULES[6] = [
    {"type": "chapter", "kind": "regex_in_span", "pattern": _CHAP6, "at": "start",
     "tile": True, "span_start": "THE FIRST BOOK OF MOSES", "span_end": "A FORM OF PRAYER TO BE USED",
     "extra_anchors": _OBAD6, "expected_count": 1133},
    {"type": "chapter_heading", "kind": "regex_in_span", "pattern": _CHAP6, "at": "start",
     "tile": False, "span_start": "THE FIRST BOOK OF MOSES", "span_end": "A FORM OF PRAYER TO BE USED",
     "extra_anchors": _OBAD6, "expected_count": 1133},
]

RULES[105] = [
    {"type": "part", "kind": "title_list", "expected_count": 6, "titles": [
        "2\n\nA. COMMUNITY RULES\n\nSerekh ha-Yaúad",
        "194\n\nB. ESCHATOLOGICAL RULES\n\nRULE OF THE CONGREGATION",
        "292\n\nC. PURITY RULE\n\n4Q274 (4QTohorot A) ed. J. M. Baumgarten, DJD XXXV",
        "298\n\nD. OTHER RULES\n\n4Q159 (4QOrdinancesa) ed. J. M. Allegro, DJD V",
        "326\n\nE. EPISTOLARY TREATISE CONCERNED WITH RELIGIOUS LAW\n\nMiq§at Ma>a°e Ha-Torah = MMT",
        "338\n\nF. UNCLASSIFIED TEXTS CONCERNED WITH RELIGIOUS LAW\n\n4Q276 (4QTohorot Ba) ed. J. M. Baumgarten, DJD XXXV",
    ]},
    {"type": "translation", "kind": "regex_in_span", "pattern": r"(?m)^.*\btrans\.\s",
     "at": "start", "tile": True, "expected_count": 63},
]


def _resolve_span(text: str, a: str) -> int:
    off = text.find(a)
    if off < 0:
        raise SystemExit(f"span anchor not found: {a[:50]!r}")
    return off


_SAL_PARA = re.compile(r"(?m)^([A-Z][^\n]{0,60}?,)\n\n")
_GREETING = re.compile(r"^(Dear |Dearest |Hello|Hi |Greetings|Good morning|Good day|To:? |My dear )", re.I)
_SIGNOFF_KW = re.compile(r"\b(regards|love|sincerely|yours|neighbou?r|friend|sister|best|wishes|response|writing|xoxo|fondly)\b", re.I)
_BARE_WHITELIST = {"Felix, my dear brother,"}


def _salutation_starts(text: str) -> list[int]:
    """Epistolary letter delimiter: greeting-form OR bare-name salutations (idx19)."""
    starts: list[int] = []
    for m in _SAL_PARA.finditer(text):
        line = m.group(1)
        body = text[m.end():m.end() + 400].split("\n\n")[0]
        if _GREETING.match(line):
            starts.append(m.start())
        elif line in _BARE_WHITELIST or (
            not _SIGNOFF_KW.search(line[:-1])
            and 1 <= len(line[:-1].replace(",", " ").split()) <= 2
            and all(w[0].isupper() for w in line[:-1].replace(",", " ").split() if w)
            and len(body) > 80
        ):
            starts.append(m.start())
    hdr = text.find("Felix Stone\n\n7 Rue")
    if hdr >= 0 and starts and starts[0] > hdr:
        starts[0] = hdr
    return sorted(set(starts))


def materialize(text: str, rule: dict) -> list[int]:
    """Return sorted unique instance start offsets for one repeating rule."""
    if rule["kind"] == "salutation":
        return _salutation_starts(text)
    if rule["kind"] == "title_list":
        # Each poem/section is delimited by a known title line; the body renders it
        # "Title\n\n<first line>", so "Title\n\n" matches the body occurrence only
        # (the TOC concatenates titles with spaces; the alpha-list appends page nums).
        # Match against an \xa0->space-normalized copy (Standard Ebooks puts non-breaking
        # spaces after "Mr."/"Dr."); \xa0 is one char, so offsets stay valid in the original.
        text = text.replace("\xa0", " ")
        starts = set()
        for title in rule["titles"]:
            plain = title + "\n\n"
            if text.count(plain) == 1:
                starts.add(text.find(plain))
                continue
            # short titles (e.g. "Snow") can match the tail of a longer title
            # ("A Patch of Old Snow"); require a standalone title (blank line before).
            pref = "\n\n" + title + "\n\n"
            if text.count(pref) == 1:
                starts.add(text.find(pref) + 2)
            # still-ambiguous titles are surfaced by reconcile()'s count mismatch
        return sorted(starts)
    if rule["kind"] == "regex_in_span":
        # A header regex delimits instances; "at"=start anchors on the header,
        # "at"=end anchors on the content immediately after it (e.g. an epigraph).
        pat = re.compile(rule["pattern"])
        lo = _resolve_span(text, rule["span_start"]) if rule.get("span_start") else 0
        hi = _resolve_span(text, rule["span_end"]) if rule.get("span_end") else len(text)
        at_end = rule.get("at") == "end"
        starts = {
            (m.end() if at_end else m.start())
            for m in pat.finditer(text)
            if lo <= m.start() < hi
        }
        for a in rule.get("extra_anchors", []):
            if text.count(a) == 1:
                starts.add(text.find(a))
        return sorted(starts)
    if rule["kind"] != "roman_in_span":
        raise SystemExit(f"unknown rule kind {rule['kind']}")
    lo = _resolve_span(text, rule["span_start"])
    hi = _resolve_span(text, rule["span_end"])
    starts = {m.start() for m in _ROMAN.finditer(text) if lo <= m.start() < hi}
    for a in rule.get("extra_anchors", []):
        if text.count(a) == 1:
            starts.add(text.find(a))
        # proems whose anchor isn't uniquely in-span are reported by reconcile()
    return sorted(starts)


def _walk_parts(text: str, starts: list[int]) -> list[str]:
    """Walk Roman headers; a value <= previous marks a part reset. Flag non-monotone."""
    notes: list[str] = []
    prev = 0
    part = 0
    for off in starts:
        m = re.match(r"[IVXLC]+", text[off : off + 8])
        if not m:
            continue  # a proem (non-Roman extra anchor)
        val = roman_to_int(m.group())
        if val == 1:
            part += 1
            prev = 0
        if val != prev + 1:
            notes.append(
                f"  ANOMALY @ {off}: part {part} value {m.group()}({val}) "
                f"follows {prev} (non-consecutive) :: {text[off:off+50]!r}"
            )
        prev = val
    return notes


def reconcile(idx: int) -> None:
    text = project_for(idx).reference_text()
    for rule in RULES[idx]:
        starts = materialize(text, rule)
        exp = rule["expected_count"]
        print(f"[{idx}] {rule['type']}: materialized {len(starts)} instances "
              f"(expected {exp}) -> GATE {'GREEN' if len(starts)==exp else 'RED'}")
        if rule["kind"] != "roman_in_span":
            continue  # monotonicity walk only meaningful for Roman-numbered structures
        notes = _walk_parts(text, starts)
        if notes:
            print("non-monotonic Roman sequence (edition quirk or stray header — adjudicate):")
            print("\n".join(notes))
        else:
            print("  Roman sequence strictly consecutive within every part (no stray headers).")
        # show per-part spans
        part_counts: list[int] = []
        cur = 0
        for off in starts:
            m = re.match(r"[IVXLC]+", text[off : off + 8])
            if not m:
                continue
            val = roman_to_int(m.group())
            if val == 1 and cur:
                part_counts.append(cur)
                cur = 0
            cur += 1
        part_counts.append(cur)
        print(f"  per-part numbered counts: {part_counts}  (sum={sum(part_counts)})")


def a23(idx: int) -> None:
    """A3 boundary accuracy + A2 assignment correctness, gold edges vs detector."""
    proj = project_for(idx)
    text = proj.reference_text()
    sections = detect_layout_sections(
        _layout_boundaries(proj), len(text), _endnote_separator(proj.path), text=text
    )
    det_bounds = sorted({s.start for s in sections} | {s.end for s in sections})
    for rule in RULES[idx]:
        starts = materialize(text, rule)
        # A3: nearest detector boundary to each gold edge
        deltas = []
        for g in starts:
            nearest = min(det_bounds, key=lambda b: abs(b - g))
            deltas.append(abs(nearest - g))
        exact = sum(1 for d in deltas if d == 0)
        within5 = sum(1 for d in deltas if d <= 5)
        print(f"[{idx}] {rule['type']} A3 boundary accuracy vs detector:")
        print(f"  gold edges={len(starts)}  exact-match={exact} "
              f"({100*exact/len(starts):.1f}%)  within-5c={within5} "
              f"({100*within5/len(starts):.1f}%)  median-delta={sorted(deltas)[len(deltas)//2]}")
        # A2: detector type covering each gold instance's first char
        from collections import Counter
        assigned = Counter()
        for g in starts:
            covering = [s for s in sections if s.start <= g < s.end and s.type != "body"]
            innermost = min(covering, key=lambda s: s.end - s.start).type if covering else "(body/none)"
            assigned[innermost] += 1
        print(f"  A2 assignment — detector type over gold {rule['type']} instances:")
        for typ, n in assigned.most_common():
            flag = "  <- MIS-TYPE" if typ != rule["type"] else "  (correct)"
            print(f"     {n:>4}  {typ}{flag}")


def summary() -> None:
    """Cross-work A2/A3 table over every ruled work (the re-scoped audit, in brief)."""
    from collections import Counter
    print(f"{'idx':>4} {'type':<11} {'cnt':>5} {'gate':<5} {'A3-exact':>9} "
          f"{'A3<=5c':>7}  A2 detector-type (mis-assignment)")
    print("-" * 92)
    for idx in sorted(RULES):
        proj = project_for(idx)
        text = proj.reference_text()
        sections = detect_layout_sections(
            _layout_boundaries(proj), len(text), _endnote_separator(proj.path), text=text
        )
        det_bounds = sorted({s.start for s in sections} | {s.end for s in sections})
        for rule in RULES[idx]:
            starts = materialize(text, rule)
            exp = rule["expected_count"]
            gate = "GRN" if len(starts) == exp else "RED"
            deltas = [min(abs(b - g) for b in det_bounds) for g in starts]
            ex = 100 * sum(d == 0 for d in deltas) / len(starts)
            w5 = 100 * sum(d <= 5 for d in deltas) / len(starts)
            assigned = Counter()
            for g in starts:
                cov = [s for s in sections if s.start <= g < s.end and s.type != "body"]
                inner = min(cov, key=lambda s: s.end - s.start).type if cov else "body/none"
                assigned[inner] += 1
            a2 = ", ".join(f"{t}×{n}" for t, n in assigned.most_common(3))
            correct = assigned.get(rule["type"], 0)
            print(f"{idx:>4} {rule['type']:<11} {len(starts):>5} {gate:<5} "
                  f"{ex:>8.0f}% {w5:>6.0f}%  {a2}  [correct {correct}/{len(starts)}]")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "reconcile"
    if cmd == "summary":
        summary()
        return
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 102
    {"reconcile": reconcile, "a23": a23}[cmd](idx)


if __name__ == "__main__":
    main()
