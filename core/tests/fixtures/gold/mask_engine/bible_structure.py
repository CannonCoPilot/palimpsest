#!/usr/bin/env python
"""Complete masking-map builder for the Douay-Rheims (Challoner) Bible, idx5.

Every element boundary is anchored to the real text (verified by close reading).
Elements may carry optional ``label`` (display title) and ``metadata`` so a chapter
is indexable by number / book / volume rather than by the first line of its text.

Layers (two-layer guarantee: every char >=1 GENERIC and >=1 SPECIFIC):
  GENERIC : body[0,EOF]; volume (Old/New Testament); book (canonical + apocryphal)
  SPECIFIC: front_matter (+ title_page / introduction[HISTORY] / contents[CONTENTS]);
            header (testament dividers); introduction (per-book header+note);
            chapter_heading ("<Book> Chapter N" line + the editorial argument);
            chapter (verse body only; every ". . ." note excluded -> footnotes);
            footnotes (Challoner annotation notes, inline and trailing);
            appendix (4 section containers) wrapping introduction / book+chapter
            structure / preface; glossary (hard words).

A canonical chapter in the text (verified across all 1334):
    <Book> Chapter N        P0  heading line       -> chapter_heading
    <argument / summary>    P1  editorial one-liner -> chapter_heading
    <verse 1> ...           P2  body                -> chapter (verses)

The appendices mirror this with "CHAP. <ROMAN>." markers (3/4 Esdras) or a single
unchaptered prayer/epistle (Manasses, and the 1582 comparison Abdias / Jude).
"""
from __future__ import annotations

import re

CHAPTER_RE = re.compile(r"(?m)^.{0,40}?\bChapter \d+\b")
BOOK_CH1_RE = re.compile(r"(?m)^.{0,40}?\bChapter 1\b")
CHAP_RE = re.compile(r"(?m)^CHAP\. ([IVXLC]+)\.")
TITLE_PREFIX = re.compile(r"^(THE [A-Z]|ECCLESIASTES|ECCLESIASTICUS|WISDOM|SOLOMON'S |THE PROLOGUE)")
NOTE_MARKER = re.compile(r"\. \. \.")  # Challoner annotation: "lemma. . .explanation"

NT_DIVIDER = "THE NEW TESTAMENT OF OUR LORD AND SAVIOUR JESUS CHRIST"
# End-matter anchors (each unique in the text).
A = dict(
    appendices="APPENDICES",
    additional="ADDITIONAL BOOKS",
    comparison="BOOKS FOR COMPARISON",
    supplemental="SUPPLEMENTAL MATERIAL",
    preface="THE PREFACE TO THE READER",
    glossary="HARD VVORDES EXPLICATED",
    manasses="THE PRAYER OF MANASSES",
    esdras3="THE THIRD BOOKE OF ESDRAS",
    esdras4="THE FOVRTH BOOKE OF ESDRAS",
    bensly="Note: This translation comes from the Latin text",
    abdias="THE PROPHECIE OF ABDIAS",
    jude="THE CATHOLIKE EPISTLE OF IVDE",
    history="HISTORY",
    contents="CONTENTS",
)
_ROM = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _roman(s: str) -> int:
    total = prev = 0
    for ch in reversed(s):
        v = _ROM[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def _para_start(T: str, pos: int) -> int:
    s = T.rfind("\n\n", 0, pos)
    return 0 if s < 0 else s + 2


def _book_header_start(T: str, chapter1_pos: int) -> int:
    fn_s = _para_start(T, chapter1_pos - 2)
    if TITLE_PREFIX.match(T[fn_s:fn_s + 40]):
        hs = fn_s
    else:
        hs = _para_start(T, fn_s - 2)
        if not TITLE_PREFIX.match(T[hs:hs + 40]):
            hs2 = _para_start(T, hs - 2)
            if TITLE_PREFIX.match(T[hs2:hs2 + 40]):
                hs = hs2
    if T[hs:hs + 13] == "THE PROLOGUE.":
        hs = _para_start(T, hs - 2)
    return hs


def _second_para(T: str, pos: int) -> int:
    """Offset after the 2nd '\\n\\n' from pos (heading P0, argument P1 -> verse P2)."""
    p0 = T.find("\n\n", pos)
    if p0 < 0:
        return pos
    p1 = T.find("\n\n", p0 + 2)
    return (p1 + 2) if p1 >= 0 else (p0 + 2)


def _carve_body(T: str, v1: int, ch_end: int) -> list[tuple[str, int, int]]:
    """Partition a chapter body [v1, ch_end] into disjoint, gap-free segments of
    consecutive verse paragraphs (-> ``chapter``) and Challoner ". . ." annotation
    paragraphs (-> ``footnotes``). Notes are carved out *wherever* they occur — inline
    (mid-chapter) as well as trailing — so a chapter span carries verse text only and
    every annotation becomes its own footnotes element.

    Each run boundary sits at the ``\\n\\n`` that precedes a run, so the blank line
    before a note belongs to the note. With a single trailing note this reproduces the
    former ``_trailing_note`` split byte-for-byte. Segments tile [v1, ch_end] exactly:
    no gaps (every char keeps SPECIFIC coverage via chapter|footnotes) and no overlaps.
    Returns a list of (kind, start, end)."""
    if v1 >= ch_end:
        return [("chapter", v1, ch_end)]
    # paragraph offsets within [v1, ch_end]
    paras: list[tuple[int, int]] = []
    p = v1
    while p < ch_end:
        nl = T.find("\n\n", p)
        end = ch_end if (nl < 0 or nl > ch_end) else nl
        paras.append((p, end))
        if nl < 0 or nl >= ch_end:
            break
        p = nl + 2
    # classify each paragraph; a whitespace-only paragraph inherits the prior kind so
    # stray blank lines never split a run into a spurious micro-segment.
    kinds: list[str] = []
    for (ps, pe) in paras:
        seg = T[ps:pe]
        if not seg.strip():
            kinds.append(kinds[-1] if kinds else "chapter")
        else:
            kinds.append("footnotes" if NOTE_MARKER.search(seg) else "chapter")
    # group consecutive same-kind paragraphs into runs; boundary before run starting at
    # paragraph index k>=1 is paras[k][0]-2 (the preceding "\n\n"); run 0 starts at v1.
    segs: list[tuple[str, int, int]] = []
    run0 = 0
    for i in range(1, len(paras) + 1):
        if i == len(paras) or kinds[i] != kinds[run0]:
            seg_start = v1 if run0 == 0 else paras[run0][0] - 2
            seg_end = ch_end if i == len(paras) else paras[i][0] - 2
            segs.append((kinds[run0], seg_start, seg_end))
            run0 = i
    return segs


def build_dr_elements(text: str) -> list[dict]:
    T = text
    N = len(T)
    els: list[dict] = []

    def add(t, s, e, src, label=None, meta=None):
        if 0 <= s < e <= N:
            d = {"type": t, "start": s, "end": e, "source": src}
            if label is not None:
                d["label"] = label
            if meta is not None:
                d["metadata"] = meta
            els.append(d)

    def idx(key, start=0):
        return T.index(A[key], start)

    ch_starts = sorted({m.start() for m in CHAPTER_RE.finditer(T)})
    b1_starts = sorted({m.start() for m in BOOK_CH1_RE.finditer(T)})
    headers = [_book_header_start(T, c) for c in b1_starts]

    nt_div = T.index(NT_DIVIDER)
    appendices = idx("appendices")
    ot_div = _para_start(T, headers[0] - 2)
    matthew_hdr = T.index("THE HOLY GOSPEL", nt_div)

    boundaries = sorted(set(headers) | {nt_div, appendices})

    def next_boundary(pos):
        for b in boundaries:
            if b > pos:
                return b
        return appendices

    def line(pos):
        nl = T.find("\n", pos)
        return T[pos:nl if nl >= 0 else pos + 60]

    # ---- front matter container + sub-sections ----
    hist = idx("history")
    cont = idx("contents")
    add("front_matter", 0, ot_div, "dr:front_matter")
    add("title_page", 0, hist, "dr:title_page")
    add("introduction", hist, cont, "dr:history")        # HISTORY note
    add("contents", cont, ot_div, "dr:contents")         # CONTENTS (book list)

    # ---- testament dividers (specific) + volumes (generic) ----
    add("header", ot_div, headers[0], "dr:divider")
    add("volume", ot_div, nt_div, "dr:volume_ot", label="The Old Testament")
    add("header", nt_div, matthew_hdr, "dr:divider")
    add("volume", nt_div, appendices, "dr:volume_nt", label="The New Testament")

    # ---- 73 canonical books: container + introduction ----
    for i, h in enumerate(headers):
        add("book", h, next_boundary(h), "dr:book", label=line(h))
        add("introduction", h, b1_starts[i], "dr:book_intro")

    # ---- canonical chapters: heading (line+argument) + body (verses, trailing notes carved) ----
    for i, cs in enumerate(ch_starts):
        b_end = next_boundary(cs)
        nxt = ch_starts[i + 1] if i + 1 < len(ch_starts) else N
        ch_end = min(nxt, b_end)
        v1 = min(_second_para(T, cs), ch_end)
        cline = line(cs)
        bk, _, num = cline.partition(" Chapter ")
        vol = "Old Testament" if cs < nt_div else "New Testament"
        meta = {"number": num.strip(), "name": cline, "book": bk.strip(), "volume": vol, "title": cline}
        add("chapter_heading", cs, v1, "dr:heading", label=cline, meta=meta)
        for kind, s, e in _carve_body(T, v1, ch_end):
            if kind == "chapter":
                add("chapter", s, e, "dr:body", label=cline, meta=meta)
            else:
                add("footnotes", s, e, "dr:note")

    # ================= APPENDICES (4 section containers) =================
    additional = idx("additional", appendices)
    comparison = idx("comparison", appendices)
    supplemental = idx("supplemental", appendices)
    preface = idx("preface", appendices)
    glossary = idx("glossary", appendices)

    def chaptered_book(name, b_start, b_end, intro_end, vol):
        """A book using 'CHAP. <ROMAN>.' markers (3/4 Esdras): intro + per-chap heading/body."""
        add("book", b_start, b_end, "dr:apx_book", label=name)
        add("introduction", b_start, intro_end, "dr:apx_book_intro")
        chaps = [(m.start(), m.group(1)) for m in CHAP_RE.finditer(T) if b_start <= m.start() < b_end]
        # the Bensly fragment (4 Esdras) is an extra trailing "chapter" introduced by a Note
        extra = T.find(A["bensly"], b_start)
        markers = chaps + ([(extra, "A")] if (0 <= extra < b_end) else [])
        markers.sort()
        for j, (cs, rom) in enumerate(markers):
            c_end = markers[j + 1][0] if j + 1 < len(markers) else b_end
            # Bensly fragment ("A"): the Note is the whole heading, verses (A:1..) follow
            # directly with no argument paragraph -> body starts after the first blank line.
            v1 = (T.find("\n\n", cs) + 2) if rom == "A" else _second_para(T, cs)
            v1 = min(v1, c_end)
            num = str(_roman(rom)) if rom != "A" else "A"
            title = f"{name} Chapter {num}" if rom != "A" else f"{name} (Bensly fragment)"
            meta = {"number": num, "name": title, "book": name, "volume": vol, "title": title}
            add("chapter_heading", cs, v1, "dr:apx_heading", label=title, meta=meta)
            for kind, s, e in _carve_body(T, v1, c_end):
                if kind == "chapter":
                    add("chapter", s, e, "dr:apx_body", label=title, meta=meta)
                else:
                    add("footnotes", s, e, "dr:apx_note")

    def single_chapter_book(name, b_start, b_end, has_argument, vol):
        """A 1-chapter book (Manasses prayer; 1582 Abdias/Jude): header[+argument] + verses."""
        add("book", b_start, b_end, "dr:apx_book", label=name)
        v1 = min(_second_para(T, b_start) if has_argument else (T.find("\n\n", b_start) + 2), b_end)
        title = f"{name} Chapter 1"
        meta = {"number": "1", "name": title, "book": name, "volume": vol, "title": title}
        add("chapter_heading", b_start, v1, "dr:apx_heading", label=title, meta=meta)
        for kind, s, e in _carve_body(T, v1, b_end):
            if kind == "chapter":
                add("chapter", s, e, "dr:apx_body", label=title, meta=meta)
            else:
                add("footnotes", s, e, "dr:apx_note")

    # appendix #1 — APPENDICES e-text/typography note (intro only)
    add("appendix", appendices, additional, "dr:apx1", label="Appendices")
    add("introduction", appendices, additional, "dr:apx1_intro")

    # appendix #2 — ADDITIONAL BOOKS (Manasses, 3 Esdras, 4 Esdras + Bensly fragment)
    manasses = idx("manasses", appendices)
    esdras3 = idx("esdras3", appendices)
    esdras4 = idx("esdras4", appendices)
    add("appendix", additional, comparison, "dr:apx2", label="Additional Books")
    add("introduction", additional, manasses, "dr:apx2_intro")     # ADDITIONAL BOOKS header + note
    def first_chap(after):
        m = CHAP_RE.search(T, after)
        return m.start() if m else after
    single_chapter_book("Prayer of Manasses", manasses, esdras3, False, "Additional Books")
    chaptered_book("Third Booke of Esdras", esdras3, esdras4, first_chap(esdras3), "Additional Books")
    chaptered_book("Fourth Booke of Esdras", esdras4, comparison, first_chap(esdras4), "Additional Books")

    # appendix #3 — BOOKS FOR COMPARISON (1582 Abdias, Jude)
    abdias = idx("abdias", appendices)
    jude = idx("jude", appendices)
    add("appendix", comparison, supplemental, "dr:apx3", label="Books for Comparison")
    add("introduction", comparison, abdias, "dr:apx3_intro")        # BOOKS FOR COMPARISON header
    single_chapter_book("Abdias (1582)", abdias, jude, True, "Books for Comparison")
    single_chapter_book("Jude (1582)", jude, supplemental, True, "Books for Comparison")

    # appendix #4 — SUPPLEMENTAL MATERIAL (note + NT preface)
    add("appendix", supplemental, glossary, "dr:apx4", label="Supplemental Material")
    add("introduction", supplemental, preface, "dr:apx4_intro")     # SUPPLEMENTAL MATERIAL note
    add("preface", preface, glossary, "dr:preface")                 # THE PREFACE TO THE READER

    # glossary — HARD VVORDES EXPLICATED
    add("glossary", glossary, N, "dr:glossary", label="Hard Vvordes Explicated")

    return els
