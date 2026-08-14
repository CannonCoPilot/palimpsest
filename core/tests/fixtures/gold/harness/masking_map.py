#!/usr/bin/env python
"""Complete masking-map materializer + two-layer coverage audit (gold ground truth).

Builds the FULL masking map of a work from its gold contract — every typed mask
element with EXACT boundaries — and audits it for the two-layer guarantee: every
character covered by >=1 GENERIC and >=1 SPECIFIC mask-type. This audits the
GOLD's own intended map (close-reading ground truth), NOT the detector.

Layers (per the ratified taxonomy):
  GENERIC  = {body, volume, book, part}              (broad containers)
  SPECIFIC = the other 30 types, INCLUDING `chapter`  (content + apparatus)

Element sources:
  * body [0,EOF]               — universal generic base (the work as a whole)
  * singular masks             — gold annotations with start/end anchors (resolved)
  * repeating instances        — instance_edges.RULES, tiled contiguously
  * generic subdivisions       — volume/book/part instance rules where authored

Audit outputs (per work):
  * type-count breakdown for ALL 34 types (including 0-counts)
  * mask-element width stats + distribution, by type
  * coverage classes per char-run: COVERED / GENERIC_ONLY / SPECIFIC_ONLY / UNCOVERED
  * flagged SPARSE regions (generic<1 or specific<1) with coordinates + excerpts

Usage:
  masking_map.py map <idx>      # print the materialized element list
  masking_map.py audit <idx>    # coverage audit + sparse flags
  masking_map.py json <idx>     # full audit as JSON (for the portfolio builder)
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import project_for  # noqa: E402
from instance_edges import RULES, materialize  # noqa: E402

REPO = HERE.parents[1]
GOLD = REPO / "core" / "tests" / "fixtures" / "gold"

GENERIC = {"body", "volume", "book", "part"}
ALL_TYPES = [
    "about_author", "acknowledgments", "addendum", "afterword", "appendix",
    "back_matter", "bibliography", "body", "book", "chapter", "chapter_heading",
    "colophon", "commentary", "contents", "copyright", "dedication", "discussion",
    "endnotes", "epigraph", "footnotes", "foreword", "front_matter", "glossary",
    "header", "index", "insert", "introduction", "letter", "part", "poetry",
    "preface", "title_page", "translation", "volume",
]

_WS = re.compile(r"\s+")

# Supplementary specific masks not yet in the durable gold contracts — the typed
# elements needed to complete two-layer coverage (front/back matter, apparatus the
# gold omitted). Kept here during iteration; migrated into gold/work-*.json after
# review. Each: {type, start_anchor, end_anchor, resolve?}. <<BOF>>=0, <<EOF>>=len.
SUPPLEMENT: dict[int, list[dict]] = {
    102: [
        {"type": "front_matter", "start_anchor": "<<BOF>>",
         "end_anchor": "THIS is my letter to the world"},  # TOC + From-the-Pages + Introduction
        {"type": "index", "start_anchor": "INDEX OF FIRST LINES\n\nA\n\nA bird",
         "end_anchor": "<<EOF>>"},  # Index of First Lines + endnotes tail
    ],
    103: [
        {"type": "copyright", "start_anchor": "<<BOF>>",
         "end_anchor": "Note\n\nMountain Interval, reprinted here"},  # Dover front blurb
    ],
    107: [
        {"type": "front_matter", "start_anchor": "<<BOF>>",
         "end_anchor": "In 2004 we published, under the auspices"},  # half-title+imprint+TOC+parts-list
        {"type": "front_matter", "start_anchor": "Index of Symbols Denoting\nPauses",
         "end_anchor": "AL-FATIHAH\n(Rev"},  # pause-key, after foreword, before surah 1
    ],
    70: [
        {"type": "title_page", "start_anchor": "<<BOF>>",
         "end_anchor": "Imprint\n\nThis ebook is the product"},
        {"type": "copyright", "start_anchor": "Imprint\n\nThis ebook is the product",
         "end_anchor": "\"She was her parents' only joy"},
        {"type": "epigraph", "start_anchor": "\"She was her parents' only joy",
         "end_anchor": "The Author's Preface"},
        {"type": "preface", "start_anchor": "The Author's Preface",
         "end_anchor": "Charlotte Temple\n\nA Tale of Truth\n\nVolume I"},
        {"type": "title_page", "start_anchor": "Charlotte Temple\n\nA Tale of Truth\n\nVolume I",
         "end_anchor": "I\n\nA Boarding School", "resolve": "last"},
    ],
    29: [
        {"type": "footnotes", "start_anchor": "1 It is to be borne in mind that, in its final compilation",
         "end_anchor": "<<EOF>>"},  # pooled 5326-note commentary apparatus
    ],
    18: [
        {"type": "contents", "start_anchor": "Ethical.\n\nIntroduction\n\n",
         "end_anchor": "Originally printed in 1885, the ten-volume set, Ante-Nicene Fathers"},
        {"type": "introduction", "start_anchor": "Tim Perrine CCEL Staff Writer",
         "end_anchor": "The Writings of the Fathers Down to A.D. 325\n\nANTE-NICENE FATHERS"},
        {"type": "title_page", "start_anchor": "The Nicene Council\n\nPreface.",
         "end_anchor": "We present a volume widely differing, in its contents"},
        {"type": "preface", "start_anchor": "may be found not less acceptable.",
         "end_anchor": "Apologetic.\n\nTitle Page.\n\nIntroductory Note.\n\nApology.\n\nOn Idolatry."},
        {"type": "contents", "start_anchor": "Apologetic.\n\nTitle Page.\n\nIntroductory Note.\n\nApology.\n\nOn Idolatry.\n\nThe Shows, or De Spectaculis.",
         "end_anchor": "Part First.\n\nIntroductory Note."},
        {"type": "commentary", "start_anchor": "Part First.\n\nIntroductory Note.\n\n————————————\n\n[ a.d. 145–220.] When our Lord repulsed",
         "end_anchor": "[Translated by the Rev. S. Thelwall, Late Scholar of Christ's College, Cantab.]"},
    ],
    106: [
        {"type": "title_page", "start_anchor": "Adam and Eve in the Armenian Tradition\nFifth through Seventeenth Centuries\nCopyright © 2013",
         "end_anchor": "Copyright © 2013 by the Society of Biblical Literature"},
        {"type": "contents", "start_anchor": "PART I\nThe Adam and Eve Traditions in Armenian\n\n-3-\nOutline",
         "end_anchor": "-11-\n1. Adam and Eve Traditions in\nFifth-Century"},
        {"type": "chapter", "start_anchor": "Part II\nTexts and Translations",
         "end_anchor": "-213-\nFifth Century\nAgat'angełos C5"},
    ],
    80: [
        {"type": "introduction", "start_anchor": "\n\nRules\n\nThis chapter contains those texts which can be called", "end_anchor": "1QRule of the Community (iQs)"},
        {"type": "introduction", "start_anchor": "Halakhic Texts\n\nA large part of the contents", "end_anchor": "4QHalakhic Letter' (4Q394 [4QMMT°])"},
        {"type": "introduction", "start_anchor": "Literature with Eschatological Content\n\nAlthough eschatology", "end_anchor": "1QWar Scroll (1QM [+1Q33])\n\nCol. i i For the Ins[tructor: The Rule] of the War."},
        {"type": "introduction", "start_anchor": "Exegetical Literature\n\nThe exegetical activity", "end_anchor": "4QTargum of Leviticus (4Q156 14QtgLev])"},
        {"type": "introduction", "start_anchor": "Para-biblical Literature\n\nThis chapter also gathers together", "end_anchor": "A 4QReworked Pentateuch' (4Q158 [4QRP'])"},
        {"type": "introduction", "start_anchor": "Poetic Texts\n\nDue to our ignorance", "end_anchor": "4QPsalmsi (4Q88 [4QPW])"},
        {"type": "introduction", "start_anchor": "Liturgical Texts\n\nThis chapter contains a set of poetic texts", "end_anchor": "4QDaily Prayers' (4Q5o3 [4QPrQuot])"},
        {"type": "introduction", "start_anchor": "Astronomical Texts, Calendars and Horoscopes\n\nThis chapter assembles", "end_anchor": "4QAstronomical Enochb (4Q2o9 [4QEnastrb at])"},
        {"type": "introduction", "start_anchor": "The Copper Scroll\n\nPossibly the most mystifying", "end_anchor": "3QCopper Scroll (3Q15)"},
        {"type": "endnotes", "start_anchor": "Notes to the Introduction\n\n1 F. M. Cross", "end_anchor": "Rules\n\nThis chapter contains those texts which can be called"},
    ],
    64: [
        {"type": "introduction", "start_anchor": "INTRODUCTION\n\nThe study of scripture", "end_anchor": "The study of scripture is a lifelong venture"},
        {"type": "introduction", "start_anchor": "Let us now proceed to the Book of Enoch.", "end_anchor": "[Chapter I}"},
        {"type": "introduction", "start_anchor": "Introduction to The Second Book\n\nof Enoch:\n\nSlavonic Enoch", "end_anchor": "Chapter 1\n\n1 There was a wise man"},
        {"type": "introduction", "start_anchor": "Intro duction of 3 Enoch", "end_anchor": "CHAPTER I\n\n"},
    ],
    19: [
        {"type": "copyright", "start_anchor": "<<BOF>>", "end_anchor": "Contents\n\nDedication\n\nEpigraph"},
        {"type": "contents", "start_anchor": "Contents\n\nDedication\n\nEpigraph", "end_anchor": "_150929195_\n\nTo Mark, with love"},
        {"type": "dedication", "start_anchor": "_150929195_\n\nTo Mark, with love", "end_anchor": "What I have made for myself is personal, but is not exactly peace…."},
        {"type": "epigraph", "start_anchor": "What I have made for myself is personal, but is not exactly peace….", "end_anchor": "A Preface\n\nAt last, on Monday"},
        {"type": "preface", "start_anchor": "A Preface\n\nAt last, on Monday", "end_anchor": "Felix Stone\n\n7 Rue de la Papillon\n\n84220 Gordes\n\nFRANCE\n\nJune 2, 2012\n\nFelix, my dear brother"},
        {"type": "acknowledgments", "start_anchor": "Acknowledgments\n\nWhen I was still in early draft", "end_anchor": "The Correspondent\n\nVirginia Evans\n\nDiscussion Questions"},
        {"type": "discussion", "start_anchor": "The Correspondent\n\nVirginia Evans\n\nDiscussion Questions", "end_anchor": "About the Author\n\nVirginia Evans is from"},
        {"type": "about_author", "start_anchor": "About the Author\n\nVirginia Evans is from", "end_anchor": "<<EOF>>"},
    ],
    48: [
        {"type": "header", "start_anchor": "I. Gospels and Related Traditions of New Testament Figures",
         "end_anchor": "A translation and introduction\n\nby Mark Glen Bilby"},
        {"type": "copyright", "start_anchor": "A catalog record for this book is available from the Library of Congress.",
         "end_anchor": "Dedicated to current students (and future scholars) of Christian apocrypha"},
        {"type": "glossary", "start_anchor": "Note on Cyrillic Transliteration by Slavomír Čéplö",
         "end_anchor": "Abbreviations\n\nUnless listed below, all abbreviations"},
    ],
    42: [
        {"type": "introduction", "start_anchor": "Introduction\n\nby Richard Bauckham and James R. Davila",
         "end_anchor": "Abbreviations\n\nUnless listed below, all abbreviations"},
        {"type": "glossary", "start_anchor": "Abbreviations\n\nUnless listed below, all abbreviations",
         "end_anchor": "I. Texts Ordered according to Biblical Chronology"},
    ],
    101: [
        {"type": "title_page", "start_anchor": "<<BOF>>", "end_anchor": "© 1981, 2013 by Intellectual Reserve, Inc."},
        {"type": "contents", "start_anchor": "English approval: 11/12", "end_anchor": "Contents\n\nT\nhe Book of Mormon is a volume of holy scripture"},
        {"type": "introduction", "start_anchor": "Contents\n\nT\nhe Book of Mormon is a volume of holy scripture", "end_anchor": "The Testimony of Three Witnesses\n\nB\ne it known unto all nations"},
        {"type": "introduction", "start_anchor": "Hiram Page\nJoseph Smith, Sen.\nHyrum Smith\nSamuel H. Smith", "end_anchor": "Chapter 1\n\nNephi begins the record of his people"},
        {"type": "insert", "start_anchor": "A Facsimile from the Book of Abraham\n\nFig. 1. The Angel", "end_anchor": "called the Book of\nAbraham, written by his own hand, upon papyrus."},
        {"type": "insert", "start_anchor": "A Facsimile from the Book of Abraham\n\nNo. 2", "end_anchor": "and, at that\nday, many followed after him."},
        {"type": "insert", "start_anchor": "A Facsimile from the Book of Abraham\n\nFig. 1. Abraham sitting", "end_anchor": "Abraham is reasoning upon the principles of Astronomy, in the king's court."},
        {"type": "back_matter", "start_anchor": "Zoramites—apostate sect of Nephites,\nfollowers of Zoram", "end_anchor": "<<EOF>>"},  # Guide-to-Scriptures tail + maps index
    ],
    6: [
        {"type": "front_matter", "start_anchor": "<<BOF>>", "end_anchor": "\n\n11 God created the heaven and the earth"},
        {"type": "appendix", "start_anchor": "A FORM OF PRAYER TO BE USED", "end_anchor": "The preceding prayers, from the 1599 Geneva Bible"},
        {"type": "afterword", "start_anchor": "The preceding prayers, from the 1599 Geneva Bible", "end_anchor": "GLOSSARY\n\nWORD"},
    ],
    105: [
        {"type": "contents", "start_anchor": "GENERAL TABLE OF CONTENTS\nI\n\nGENERAL INTRODUCTION", "end_anchor": "The Dead Sea Scrolls Reader (DSSR) presents for the first time"},
        {"type": "translation", "start_anchor": "2\n\nA. COMMUNITY RULES\n\nSerekh ha-Yaúad\n\n1QS I 1–III 12 ed.", "end_anchor": "1QS I 1–III 12 trans. M. Wise, M. Abegg, and E. Cook with"},
        {"type": "book", "start_anchor": "Serekh ha-Yaúad\n\n1QS I 1–III 12 ed.", "end_anchor": "Serekh le<anshey ha-Yaúad\n\n1QS V 1–XI 22, ed."},
        {"type": "book", "start_anchor": "Serekh le<anshey ha-Yaúad\n\n1QS V 1–XI 22, ed.", "end_anchor": "Damascus Document (D)\n\n4Q266 (4QDa) ed."},
        {"type": "book", "start_anchor": "Damascus Document (D)\n\n4Q266 (4QDa) ed.", "end_anchor": "194\n\nB. ESCHATOLOGICAL RULES"},
        {"type": "book", "start_anchor": "RULE OF THE CONGREGATION\n\n1Q28a (1QSa) ed.", "end_anchor": "1Q33 (1QM[ilúamah] = 1QWar Scroll [Rule]) ed."},
        {"type": "book", "start_anchor": "1Q33 (1QM[ilúamah] = 1QWar Scroll [Rule]) ed.", "end_anchor": "292\n\nC. PURITY RULE"},
        {"type": "book", "start_anchor": "326\n\nE. EPISTOLARY TREATISE CONCERNED WITH RELIGIOUS LAW\n\nMiq§at Ma>a°e Ha-Torah = MMT", "end_anchor": "338\n\nF. UNCLASSIFIED"},
        {"type": "footnotes", "start_anchor": "1 Several persons helped us in this", "end_anchor": "viii\n\nThe Dead Sea Scrolls Reader"},
        {"type": "footnotes", "start_anchor": "3 Exceptions to this rule are the", "end_anchor": "ix\n\nGeneral Introduction"},
        {"type": "footnotes", "start_anchor": "6 Some of the very fragmentary texts which ha", "end_anchor": "x\n\nThe Dead Sea Scrolls Reader"},
        {"type": "footnotes", "start_anchor": "10 These transcriptions were prepared for the", "end_anchor": "xi\n\nGeneral Introduction"},
        {"type": "footnotes", "start_anchor": "16 The data and difficulties involved are des", "end_anchor": "xii\n\nThe Dead Sea Scrolls Reader"},
        {"type": "footnotes", "start_anchor": "18 It would not be amiss to note that vol. V", "end_anchor": "xiii\n\nGeneral Introduction"},
        {"type": "footnotes", "start_anchor": "20 Such typographic errors are corrected in t", "end_anchor": "xiv\n\nThe Dead Sea Scrolls Reader"},
        {"type": "footnotes", "start_anchor": "1 DSSR follows the classification of A. Lange", "end_anchor": "xxii\n\nIntroduction to Part 1"},
    ],
    100: [
        {"type": "front_matter", "start_anchor": "<<BOF>>",
         "end_anchor": "Genesis Chapter 1\n\nGod createth Heaven and Earth"},  # title page + Contents
    ],
    5: [
        {"type": "front_matter", "start_anchor": "<<BOF>>",
         "end_anchor": "Genesis Chapter 1\n\nGod createth Heaven and Earth"},  # title page + TOC
        {"type": "appendix", "start_anchor": "PRAYER OF MANASSES",
         "end_anchor": "he old Testament lying by vs"},  # apocryphal appendix (Manasses, 3/4 Esdras)
        {"type": "afterword", "start_anchor": "he old Testament lying by vs",
         "end_anchor": "Abstracted. Dravven avvay"},  # editorial note on the translation
        {"type": "glossary", "start_anchor": "Abstracted. Dravven avvay",
         "end_anchor": "<<EOF>>"},  # A-Z glossary of terms
    ],
    104: [
        {"type": "front_matter", "start_anchor": "<<BOF>>",
         "end_anchor": "with breathing as (faithfully) her lownecked"},  # note+TOC+section-ONE header
    ],
}


# Custom element producers for works whose sub-structure can't be expressed by the
# RULES/SUPPLEMENT kinds (e.g. intro/translation that INTERLEAVE within each unit).
# Each: idx -> fn(text) -> list of {type,start,end}. Added on top of RULES/SUPPLEMENT.
def _custom_29(text: str) -> list[dict]:
    # Asad: within each surah, the editor's introduction precedes the verse translation
    # (which opens at "(1) "). Split each surah span into introduction + translation.
    lo = text.find("THE MESSAGE OF THE QUR'ĀN\n\nTHE FIRST SŪRAH")
    hi = text.find("APPENDIX I\n\nSYMBOLISM AND ALLEGORY IN THE QUR'ĀN")
    heads = [m.start() for m in re.finditer(r"(?m)^THE [A-Z\-]+(?: [A-Z\-]+)? SŪRAH$", text)
             if lo <= m.start() < hi]
    bounds = heads + [hi]
    out: list[dict] = []
    if heads and lo < heads[0]:
        out.append({"type": "header", "start": lo, "end": heads[0], "source": "custom"})  # body banner
    for i, s in enumerate(heads):
        e = bounds[i + 1]
        m = re.search(r"\(1\) ", text[s:e])
        if not m:
            continue
        t1 = s + m.start()
        out.append({"type": "introduction", "start": s, "end": t1, "source": "custom"})
        out.append({"type": "translation", "start": t1, "end": e, "source": "custom"})
    return out


def _custom_42(text: str) -> list[dict]:
    # OT Pseudepigrapha: 39 per-text translation units tile the body; each carries an
    # editor introduction + bibliography + numbered footnote run as typed sub-blocks.
    n = len(text)
    opener = re.compile(r"(?i)\n\n(?:A new translation and introduction|Introduction and a new translation)")
    title_starts = sorted(text.rfind("\n\n", 0, m.start()) + 2 for m in opener.finditer(text))
    parti = text.find("I. Texts Ordered according to Biblical Chronology")
    partii = text.find("II. Thematic Texts")
    out: list[dict] = []
    if parti >= 0 and partii > parti:
        out.append({"type": "part", "start": parti, "end": partii, "source": "custom"})
        out.append({"type": "part", "start": partii, "end": n, "source": "custom"})
    tile_starts = [parti] + title_starts[1:]
    tb = tile_starts + [n]
    for i, s in enumerate(tile_starts):
        out.append({"type": "translation", "start": s, "end": tb[i + 1], "source": "custom"})
    for i, s in enumerate(title_starts):
        hi = title_starts[i + 1] if i + 1 < len(title_starts) else n
        bib = text.find("\n\nBibliography\n\n", s)
        e = bib if 0 <= bib < hi else min(s + 4000, n)
        out.append({"type": "introduction", "start": s, "end": e, "source": "custom"})
    bounds = tile_starts + [n]
    for m in re.finditer(r"\n\nBibliography\n\n", text):
        s = m.start() + 2
        hi = next((x for x in bounds if x > s), n)
        mm = re.search(r"(?m)^\d+\. ", text[m.end():hi])
        e = m.end() + mm.start() if mm else hi
        while e > s and text[e - 1] == "\n":
            e -= 1
        out.append({"type": "bibliography", "start": s, "end": e, "source": "custom"})
    for b in [m.start() for m in re.finditer(r"\n\nBibliography\n\n", text)]:
        hi = next((x for x in bounds if x > b), n)
        m = re.search(r"(?m)^1\. ", text[b:hi])
        if not m:
            continue
        start = b + m.start()
        pos, last_end = start, start
        while True:
            if not re.match(r"\d+\. ", text[pos:pos + 12]):
                break
            nxt = text.find("\n\n", pos)
            if nxt < 0 or nxt >= hi:
                last_end = hi
                break
            last_end, pos = nxt, nxt + 2
        if last_end > start:
            out.append({"type": "footnotes", "start": start, "end": last_end, "source": "custom"})
    return out


CUSTOM_ELEMENTS = {29: _custom_29, 42: _custom_42}

# Gold singular masks to drop because their anchors are placeholders (e.g. end=<<EOF>>)
# that span far past the real element; the true extent is supplied via SUPPLEMENT.
GOLD_SKIP: dict[int, set] = {101: {"glossary"}}


def _resolve(text: str, anchor: str, mode: str = "first") -> int | None:
    if anchor == "<<EOF>>":
        return len(text)
    if anchor == "<<BOF>>":
        return 0
    if text.count(anchor) != 1:
        return None
    return text.rfind(anchor) if mode == "last" else text.find(anchor)


def build_elements(idx: int) -> tuple[str, list[dict]]:
    """Return (text, elements) where each element is {type,start,end,source}."""
    text = project_for(idx).reference_text()
    n = len(text)
    gold = json.loads((GOLD / f"work-{idx}.json").read_text())
    els: list[dict] = [{"type": "body", "start": 0, "end": n, "source": "base-generic"}]

    # singular masks (anchored spans)
    for a in gold.get("annotations", []):
        if a.get("structure") == "repeating":
            continue
        if a["type"] in GOLD_SKIP.get(idx, ()):
            continue  # placeholder/<<EOF>>-anchored gold mask superseded by a precise SUPPLEMENT
        mode = a.get("resolve", "first")
        s = _resolve(text, a["start_anchor"], mode)
        e = _resolve(text, a["end_anchor"], mode) if a.get("end_anchor") else n
        if s is None or e is None or not (0 <= s < e <= n):
            els.append({"type": a["type"], "start": -1, "end": -1,
                        "source": "UNRESOLVED-singular"})
            continue
        els.append({"type": a["type"], "start": s, "end": e, "source": "singular"})

    # supplementary specific masks (completion spec; pre-migration into gold)
    for a in SUPPLEMENT.get(idx, []):
        mode = a.get("resolve", "first")
        s = _resolve(text, a["start_anchor"], mode)
        e = _resolve(text, a["end_anchor"], mode)
        if s is None or e is None or not (0 <= s < e <= n):
            els.append({"type": a["type"], "start": -1, "end": -1,
                        "source": "UNRESOLVED-supplement"})
            continue
        els.append({"type": a["type"], "start": s, "end": e, "source": "supplement"})

    # repeating instances. tile=True (default): contiguous partition (chapters/poems
    # tile a region). tile=False: thin markers (a heading line) that don't tile —
    # each spans to the end of its block (next \n\n).
    rules = RULES.get(idx, [])
    for rule in rules:
        starts = materialize(text, rule)
        if not starts:
            continue
        if rule.get("tile", True):
            sing_starts = sorted(el["start"] for el in els
                                 if el["source"] in ("singular", "supplement")
                                 and el["start"] > starts[-1])
            region_end = sing_starts[0] if sing_starts else n
            bounds = starts + [region_end]
            for i, s in enumerate(starts):
                els.append({"type": rule["type"], "start": s, "end": bounds[i + 1],
                            "source": f"rule:{rule['kind']}"})
        else:
            for s in starts:
                blk = text.find("\n\n", s + 1)
                e = blk if blk > s else min(s + 80, n)
                els.append({"type": rule["type"], "start": s, "end": e,
                            "source": f"marker:{rule['kind']}"})

    # custom element producers (interleaved sub-blocks the rule kinds can't express)
    if idx in CUSTOM_ELEMENTS:
        for e in CUSTOM_ELEMENTS[idx](text):
            if 0 <= e["start"] < e["end"] <= n:
                els.append(e)
    return text, els


def coverage_runs(text: str, els: list[dict]) -> list[dict]:
    """Sweep-line: classify each maximal char-run by generic/specific depth."""
    n = len(text)
    good = [e for e in els if e["start"] >= 0]
    pts = sorted({0, n} | {e["start"] for e in good} | {e["end"] for e in good})
    runs = []
    for a, b in zip(pts, pts[1:]):
        if a >= b:
            continue
        gen = sum(1 for e in good if e["type"] in GENERIC and e["start"] <= a and e["end"] >= b)
        spec = sum(1 for e in good if e["type"] not in GENERIC and e["start"] <= a and e["end"] >= b)
        cls = ("COVERED" if gen and spec else "GENERIC_ONLY" if gen else
               "SPECIFIC_ONLY" if spec else "UNCOVERED")
        runs.append({"start": a, "end": b, "len": b - a, "gen": gen, "spec": spec, "cls": cls})
    return runs


def audit(idx: int) -> dict:
    text, els = build_elements(idx)
    n = len(text)
    runs = coverage_runs(text, els)

    # type-count breakdown (all 34, incl 0)
    counts = {t: 0 for t in ALL_TYPES}
    widths: dict[str, list[int]] = {t: [] for t in ALL_TYPES}
    for e in els:
        if e["start"] < 0:
            continue
        counts[e["type"]] += 1
        widths[e["type"]].append(e["end"] - e["start"])

    # coverage class totals (by chars)
    by_cls: dict[str, int] = {}
    for r in runs:
        by_cls[r["cls"]] = by_cls.get(r["cls"], 0) + r["len"]

    sparse = [r for r in runs if r["cls"] != "COVERED" and r["len"] > 0]
    sparse_big = sorted(sparse, key=lambda r: r["len"], reverse=True)[:25]
    for r in sparse_big:
        r["head"] = _WS.sub(" ", text[r["start"]:r["start"] + 90]).strip()

    unresolved = [e for e in els if e["start"] < 0]

    width_stats = {}
    for t, ws in widths.items():
        if ws:
            width_stats[t] = {
                "count": len(ws), "min": min(ws), "max": max(ws),
                "mean": round(statistics.mean(ws), 1),
                "median": int(statistics.median(ws)),
                "total": sum(ws),
            }

    return {
        "idx": idx,
        "work": json.loads((GOLD / f"work-{idx}.json").read_text()).get("work", "?"),
        "text_len": n,
        "n_elements": len([e for e in els if e["start"] >= 0]),
        "type_counts": counts,
        "width_stats": width_stats,
        "coverage_chars": by_cls,
        "coverage_pct": {k: round(100 * v / n, 2) for k, v in by_cls.items()},
        "sparse_regions": sparse_big,
        "n_sparse_runs": len(sparse),
        "sparse_chars": sum(r["len"] for r in sparse),
        "unresolved": [e["type"] for e in unresolved],
        "elements": [e for e in els if e["start"] >= 0],
    }


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 102
    if cmd == "map":
        _, els = build_elements(idx)
        for e in sorted(els, key=lambda x: (x["start"], x["end"])):
            print(f"  [{e['start']:>8} {e['end']:>8}] {e['type']:<14} {e['source']}")
    elif cmd == "json":
        print(json.dumps(audit(idx), indent=2, ensure_ascii=False))
    else:
        a = audit(idx)
        print(f"[{idx}] {a['work'][:50]}  ({a['text_len']:,} chars, {a['n_elements']} elements)")
        print(f"  coverage%: {a['coverage_pct']}")
        if a["unresolved"]:
            print(f"  UNRESOLVED singular masks: {a['unresolved']}")
        nz = {t: c for t, c in a["type_counts"].items() if c}
        print(f"  type counts (nonzero): {nz}")
        print(f"  sparse runs: {a['n_sparse_runs']} ({a['sparse_chars']:,} chars)")
        for r in a["sparse_regions"][:12]:
            print(f"    {r['cls']:<13} [{r['start']:>8}-{r['end']:>8}] {r['len']:>7,}c · {r.get('head','')[:64]!r}")


if __name__ == "__main__":
    main()
