#!/usr/bin/env python
"""Build the Original Douay-Rheims (1582 NT / 1609-1610 OT, Gregory Martin) Gold-Set text.

TWO collated witnesses of one edition, each authoritative for a different layer:

  - Madueke_A  (olprint "Augmented Bible" HTML, codeberg) — the AUTHORITATIVE SCRIPTURE
    text. Verse bodies come from here: books/<N>.html, one file per chapter, verse text in
    <div class='roleText'> segments split on inline <sup>V</sup> markers. Modern spelling,
    expands ae/oe, ALL-CAPS divine speech. It carries NO apparatus and NO appendix.
  - Sabates_A  (janvier-s/original-douay-rheims JSON, CC0) — the APPARATUS witness. Supplies
    everything Madueke lacks: book arguments (intros), chapter arguments (summary), per-chapter
    footnotes/cross-refs/marginal annotations, the 26 front/back reference documents, and the
    three-book apocryphal appendix (Prayer of Manasses, 3 & 4 Esdras) that Madueke omits.

Why two witnesses: Sabates derives from Madueke, so their agreement could inherit a shared
transcription error. A verse-by-verse collation (compare_madueke_sabates.py) found 0 substantive
wording differences (only ae/oe-ligature and case/punctuation), and an INDEPENDENT tesseract OCR
of the original 1582/1609/1610 printed scans (ocr_validate.py) confirmed the shared text against
the print with 0 genuine wording discrepancies. So verse bodies switch to Madueke as the fuller,
authoritative rendering; Sabates supplies the apparatus it uniquely carries. Every element records
PROVENANCE / CONFIDENCE / COVERAGE in its map metadata.

Because we GENERATE the reference text from structured data, we record every mask element's exact
char offset as we emit it — no fragile detection. The element model mirrors the Challoner build:
front_matter, volume, book, introduction (book arguments), chapter_heading (book+chapter line +
the chapter summary/argument), chapter (verse body), annotation (masked apparatus). Output:
  - imports/Scripture/Bibles/OriginalDR/OriginalDR-modern-1582-1610.txt   (the reference text)
  - core/tests/fixtures/gold/maps/work-108.map.json                        (the masking map)

The generated text is normalization-stable (NFC, straight quotes, single spaces,
\\n\\n paragraphs), so Palimpsest's ingest reproduces it byte-for-byte and the
recorded offsets align (asserted via reference_sha256 at import time).
"""
from __future__ import annotations

import hashlib
import html as htmllib
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
# Source clone location moved under the OriginalDR project tree; keep a fallback to the
# legacy path so an older checkout still resolves.
_CANDIDATES = [REPO / ".scratch/bible-ingest/repos/original-douay-rheims",
               REPO / ".scratch/original-douay-rheims"]
SRC = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])
RAW = SRC / "bible/raw"
REF = SRC / "reference"
ANNOT = SRC / "annotations"
# Madueke_A authoritative scripture text (per-chapter HTML books). The OriginalDR project tree
# lives under core/.scratch; keep a REPO-root fallback so either checkout layout resolves.
_MAD_CANDIDATES = [REPO / "core/.scratch/originaldr-project/sources/madueke-a/books",
                   REPO / ".scratch/originaldr-project/sources/madueke-a/books"]
MADUEKE = next((p for p in _MAD_CANDIDATES if p.exists()), _MAD_CANDIDATES[0])
MAPS = HERE.parent / "maps"
OUT_TXT = REPO / "imports/Scripture/Bibles/OriginalDR/OriginalDR-modern-1582-1610.txt"
IDX = 108

# ── janvier-s reference apparatus, placed at the tome positions of the 1609/1610 print ──
# The order is loaded from the committed scan-derived evidence file
# originaldr_validation/apparatus-order.json, where every section's position is backed by explicit
# evidence (section-field numeric prefix / OCR offset in the archive.org scan / manual-visual scan
# confirmation / structural placement). The hard-coded lists below are the fallback used only if the
# evidence file is absent — they encode the identical, verified order, so the emitted text is stable.
_APPARATUS_ORDER_FILE = HERE / "originaldr_validation/apparatus-order.json"
_APPARATUS_ORDER_FALLBACK = {
    "ot_front": ["title-page", "approbatio", "preface", "privilege", "censura"],
    "ot_back": ["historical-table-age-1", "historical-table-age-2", "historical-table-age-3",
                "historical-table-age-3b", "historical-table-age-4", "historical-table-age-5",
                "historical-table-age-6", "glossary", "epistles-table"],
    "nt_front": ["title-page", "preface", "censure"],
    "nt_back": ["explication-words", "table-peter", "table-paul", "table-corruptions",
                "table-catholic-truths", "table-epistles-gospels", "apostles-creed",
                "evangelical-history", "scripture-authority"],
}


def _load_apparatus_order() -> dict[str, list[str]]:
    if not _APPARATUS_ORDER_FILE.exists():
        return _APPARATUS_ORDER_FALLBACK
    data = json.loads(_APPARATUS_ORDER_FILE.read_text())
    order = {r: [e["name"] for e in data[r]] for r in _APPARATUS_ORDER_FALLBACK}
    # guard: the evidence file must cover the same section set (order may be re-evidenced, not re-scoped)
    for r, names in _APPARATUS_ORDER_FALLBACK.items():
        assert set(order[r]) == set(names), f"apparatus-order.json {r} section set diverged from generator"
    return order


_APPARATUS_ORDER = _load_apparatus_order()
OT_FRONT = _APPARATUS_ORDER["ot_front"]
OT_BACK = _APPARATUS_ORDER["ot_back"]
NT_FRONT = _APPARATUS_ORDER["nt_front"]
NT_BACK = _APPARATUS_ORDER["nt_back"]

# Books whose source carries a known spurious leading "chapter": a 1-verse duplicate holding
# only a truncated fragment of the book's opening verse (an upstream parsing artifact). The
# complete verse survives in the following chapter, so dropping the fragment and renumbering is
# lossless and restores the Vulgate/DR chapter count. See the OriginalDR report.
SPURIOUS_LEADING_CHAPTER = {"tobias"}  # source ch0 = 8-word fragment of Tobias 1:1 → DR Tobias has 14

OT = ["genesis", "exodus", "leviticus", "numbers", "deuteronomy", "josue", "judges",
      "ruth", "1-kings", "2-kings", "3-kings", "4-kings", "1-paralipomenon",
      "2-paralipomenon", "1-esdras", "2-esdras", "tobias", "judith", "esther", "job",
      "psalms", "proverbs", "ecclesiastes", "canticle-of-canticles", "wisdom",
      "ecclesiasticus", "isaie", "jeremie", "lamentations", "baruch", "ezechiel",
      "daniel", "osee", "joel", "amos", "abdias", "jonas", "micheas", "nahum",
      "habacuc", "sophonias", "aggeus", "zacharias", "malachie", "1-machabees", "2-machabees"]
NT = ["matthew", "mark", "luke", "john", "acts", "romans", "1-corinthians",
      "2-corinthians", "galatians", "ephesians", "philippians", "colossians",
      "1-thessalonians", "2-thessalonians", "1-timothy", "2-timothy", "titus",
      "philemon", "hebrews", "james", "1-peter", "2-peter", "1-john", "2-john",
      "3-john", "jude", "apocalypse"]
APOCRYPHA = ["prayer-of-manasses", "3-esdras", "4-esdras"]

# ── per-element provenance / confidence / coverage, recorded in map metadata ──
# Verse bodies of the 73 canonical books: authoritative Madueke, corroborated by the Sabates
# lineage AND by independent OCR of the original print (0 substantive/genuine discrepancies).
PROV_SCRIPTURE = {"provenance": "Madueke_A", "corroborated_by": ["Sabates_A", "OCR-original-scan"],
                  "confidence": "high", "coverage": "three-witness"}
# Apocryphal appendix verse bodies: Madueke_A omits these books, so Sabates supplies the text.
# Madueke_B (merged.txt full edition) carries the Prayer of Manasses + 3 & 4 Esdras with clear book
# headers (see originaldr_validation/apparatus-gapfill.json), corroborating the appendix's PRESENCE
# and structure — so it is two-witness. Confidence stays moderate: Madueke_B is a column-flattened
# dump that corroborates presence, not verbatim wording.
PROV_APPENDIX = {"provenance": "Sabates_A", "corroborated_by": ["Madueke_B"],
                 "confidence": "moderate",
                 "coverage": "two-witness (Sabates_A text + Madueke_B corroborated; Madueke_A omits)"}
# All editorial apparatus (arguments, chapter summaries, footnotes/annotations, reference docs):
# Madueke carries none of it, so Sabates is authoritative and sole here.
PROV_APPARATUS = {"provenance": "Sabates_A", "corroborated_by": [],
                  "confidence": "moderate", "coverage": "single-witness (apparatus; Madueke omits)"}
# A verse where Madueke unexpectedly lacked the text and we fell back to Sabates — a real
# collation gap, surfaced (not silently papered over) so it can be investigated.
PROV_FALLBACK = {"provenance": "Sabates_A", "corroborated_by": [],
                 "confidence": "low", "coverage": "single-witness (Madueke verse absent — FLAG)"}

_TAG = re.compile(r"</?(?:sc|i)>")            # keep content
_DROP = re.compile(r"<(?:cr|na|mn)>.*?</(?:cr|na|mn)>|<(?:cr|na|mn)/?>")  # drop marker tags
_ALLTAGS = re.compile(r"<[^>]+>")             # ref-doc titles carry <br>/<span class=…> etc.
_WS = re.compile(r"[ \t]+")

# Keys carrying human-readable text in the reference apparatus, in a sensible emit order.
_REF_TEXT_KEYS = ("title", "subtitle", "heading", "letter", "word", "term", "book",
                  "emperor", "text", "definition", "desc", "note", "closing")
_REF_LIST_KEYS = ("paragraphs", "words", "entries", "articles", "subsections", "books",
                  "sections", "columns", "notes")


def clean(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _DROP.sub("", s)
    s = _TAG.sub("", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("\n", " ")
    return _WS.sub(" ", s).strip()


def clean_ref(s: str) -> str:
    """Clean a reference-apparatus string: strip ALL markup (titles carry <br>/<span>)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _ALLTAGS.sub(" ", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("\n", " ")
    return _WS.sub(" ", s).strip()


def clean_scripture(s: str) -> str:
    """Clean a Madueke verse body to normalization-stable prose: strip residual markup and the
    ^/* margin-note & word-explication anchors, decode &amp; entities, straighten every quote
    style normalize() folds (incl. guillemets), fold nbsp, collapse whitespace. Mirrors
    palimpsest ingest normalize() so the emitted text round-trips byte-for-byte."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _ALLTAGS.sub("", s)                    # any residual inline markup (sup already split out)
    s = htmllib.unescape(s)                    # &amp; -> & , &lt; -> < …
    s = s.replace("^", "").replace("*", "")    # Madueke marginal-note / word-explication anchors
    s = s.replace(" ", " ")               # nbsp -> space (normalize's \s regex excludes nbsp)
    for a, b in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"), ("«", '"'), ("»", '"')):
        s = s.replace(a, b)
    s = s.replace("\n", " ")
    return _WS.sub(" ", s).strip()


def parse_madueke() -> tuple[dict[str, dict[int, dict[int, str]]], list[str]]:
    """Parse Madueke_A per-chapter HTML into {book_display: {chapter: {verse: raw_text}}} plus
    book order (first-seen). Verse text is the roleText content between <sup>V</sup> markers,
    left RAW here (cleaned at emit time by clean_scripture)."""
    books: dict[str, dict[int, dict[int, str]]] = {}
    order: list[str] = []
    for p in sorted(MADUEKE.glob("*.html"), key=lambda p: int(p.stem)):
        h = p.read_text(encoding="utf-8")
        mt = re.search(r"<title>(.*?)</title>", h)
        if not mt:
            continue
        mm = re.match(r"^(.*?)\s+(\d+)$", mt.group(1).strip())
        if not mm:
            continue
        book, ch = mm.group(1).strip(), int(mm.group(2))
        joined = " ".join(re.findall(r"class='roleText'[^>]*>(.*?)</div>", h, re.S))
        parts = re.split(r"<sup>(\d+)</sup>", joined)
        verses: dict[int, str] = {}
        i = 1
        while i < len(parts):
            vn = int(parts[i]); vt = parts[i + 1] if i + 1 < len(parts) else ""
            verses[vn] = (verses.get(vn, "") + " " + vt).strip() if vn in verses else vt
            i += 2
        if book not in books:
            books[book] = {}
            order.append(book)
        books[book][ch] = verses
    return books, order


def render_ref(value) -> list[str]:
    """Flatten an arbitrary reference-doc value into ordered, cleaned paragraphs.

    The 26 janvier-s apparatus docs come in nine shapes (paragraphs, glossary entries,
    parallel-column tables, creed articles, numbered subsections …). Because the apparatus
    is *masked* in the reading text, faithful reconstruction needs the full text in document
    order, not pixel-perfect tabular layout — so this walks the structure generically,
    emitting every text-bearing field once, and joins short row cells onto one line.
    """
    out: list[str] = []

    def walk(x):
        if isinstance(x, str):
            c = clean_ref(x)
            if c:
                out.append(c)
        elif isinstance(x, list):
            for it in x:
                walk(it)
        elif isinstance(x, dict):
            # A table row (short parallel cells) reads better joined than split.
            cells = [x[k] for k in ("emperor", "col1", "col2", "col3", "mt", "mr", "lu", "io")
                     if isinstance(x.get(k), str) and x.get(k)]
            if len(cells) >= 2:
                row = clean_ref(" · ".join(cells))
                if row:
                    out.append(row)
            for k in _REF_TEXT_KEYS:
                if k in x and isinstance(x[k], str):
                    walk(x[k])
            for k in _REF_LIST_KEYS:
                if k in x and isinstance(x[k], list):
                    walk(x[k])

    walk(value)
    return out


def chapter_apparatus(slug: str, ch: dict) -> list[str]:
    """Aggregate a chapter's masked footnote/marginal apparatus into ordered paragraphs:
    chapter-summary notes, then per-verse footnotes and cross-references, then the marginal
    commentary sidecar (annotations/{slug}/{NNN}.json). All of this is masked in the reading
    text; it is emitted after the chapter body so verse bodies stay a single unmasked span.
    """
    out: list[str] = []
    for sn in ch.get("summary_notes") or []:
        t = clean(sn.get("text", ""))
        if t:
            mk = sn.get("marker")
            out.append(f"{mk}. {t}" if mk not in (None, "") else t)
    for v in ch.get("verses", []):
        for nt in v.get("notes") or []:
            t = clean(nt.get("text", ""))
            if t:
                lb = nt.get("label")
                out.append(f"{lb}. {t}" if lb not in (None, "") else t)
        for cr in v.get("cross_refs") or []:
            t = clean(cr.get("text", "")) if isinstance(cr, dict) else clean(str(cr))
            if t:
                out.append(t)
    src_num = ch.get("chapter")
    if src_num not in (None, ""):
        apath = ANNOT / slug / f"{int(src_num):03d}.json"
        if apath.exists():
            for a in json.loads(apath.read_text()).get("annotations") or []:
                head = " ".join(x for x in (clean(a.get("title", "")), clean(a.get("text", ""))) if x)
                if head:
                    out.append(head)
                for sub in a.get("notes") or []:
                    st = clean(sub.get("text", ""))
                    if st:
                        mk = sub.get("marker")
                        out.append(f"{mk} {st}" if mk not in (None, "") else st)
    return out


class Builder:
    def __init__(self):
        self.parts: list[str] = []
        self.pos = 0
        self.els: list[dict] = []

    def emit(self, text: str) -> tuple[int, int]:
        start = self.pos
        self.parts.append(text)
        self.pos += len(text)
        return start, self.pos

    def para(self, text: str) -> tuple[int, int]:
        if not text:                       # never emit an empty paragraph (would yield \n\n\n\n)
            return self.pos, self.pos
        s, e = self.emit(text)
        self.emit("\n\n")
        return s, e

    def add(self, t, s, e, label=None, meta=None):
        d = {"type": t, "start": s, "end": e}
        if label is not None:
            d["label"] = label
        if meta is not None:
            d["metadata"] = meta
        self.els.append(d)


def humanize(slug: str) -> str:
    return " ".join(w if w.isdigit() else w.capitalize() for w in slug.split("-"))


def _vnum(x) -> int | None:
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def book_title_line(meta: dict, slug: str) -> str:
    raw = (meta.get("book_title") or meta.get("short_title") or "").rstrip(", ")
    return clean(raw) or humanize(slug)


def build():
    B = Builder()
    warns: list[str] = []                       # collation gaps (Madueke verse absent), surfaced

    # Madueke_A authoritative scripture, aligned book-display -> Sabates slug. The verse-by-verse
    # collation (compare_madueke_sabates.py) validated this zip; if the book counts ever diverge
    # we degrade loudly (every OT/NT verse flags a fallback) rather than silently misalign.
    mad_books, mad_order = parse_madueke()
    sab_order = OT + NT
    slug_to_mad: dict[str, dict] = {}
    if len(mad_order) == len(sab_order):
        for disp, slug in zip(mad_order, sab_order):
            slug_to_mad[slug] = mad_books.get(disp, {})
    else:
        warns.append(f"Madueke books ({len(mad_order)}) != Sabates OT+NT ({len(sab_order)}); "
                     f"scripture provenance degraded to Sabates fallback")

    # element type per reference doc: the two canonical front pieces keep their own types;
    # every other apparatus doc is a masked `apparatus` element identified by its title.
    _REF_TYPE = {"title-page": "title_page", "preface": "preface"}

    def emit_ref(sub: str, name: str):
        path = REF / sub / f"{name}.json"
        if not path.exists():
            return
        doc = json.loads(path.read_text())
        paras = render_ref(doc)
        if not paras:
            return
        label = clean_ref(doc.get("title", "")) or humanize(name)
        s = B.pos
        for p in paras:
            B.para(p)
        B.add(_REF_TYPE.get(name, "apparatus"), s, B.pos, label=label,
              meta={"section": doc.get("section", name), "testament": sub.upper()})

    def emit_region(container: str, label: str, sub: str, names: list[str]):
        s = B.pos
        for name in names:
            emit_ref(sub, name)
        if B.pos > s:                          # skip an empty region
            B.add(container, s, B.pos, label=label)

    def emit_book(slug: str, volume: str, mad_book: dict[int, dict[int, str]] | None):
        """Emit one book. Verse bodies come from Madueke_A (mad_book) when present; mad_book is
        None only for the apocryphal appendix, which Madueke omits (Sabates is then sole witness).
        The apparatus (arguments, summaries, footnotes) always comes from Sabates."""
        meta = json.loads((RAW / f"{slug}.json").read_text())
        bk_start = B.pos
        short = clean(meta.get("short_title") or "") or humanize(slug)
        title_line = book_title_line(meta, slug)
        # book header + introductions (arguments) — Sabates apparatus
        hdr_s = B.pos
        B.para(title_line)
        for intro in meta.get("intros", []) or []:
            if intro.get("title"):
                B.para(clean(intro["title"]))
            if intro.get("text"):
                B.para(clean(intro["text"]))
        B.add("introduction", hdr_s, B.pos, label=title_line, meta=dict(PROV_APPARATUS))
        # chapters — drop a known spurious leading "chapter" (mis-captured Argument) and
        # renumber so the reconstructed count matches the DR/Vulgate canon.
        chapters = meta["chapters"]
        if slug in SPURIOUS_LEADING_CHAPTER and len(chapters) > 1:
            chapters = chapters[1:]
        for n, ch in enumerate(chapters, 1):
            title = f"{short} Chapter {n}"
            cmeta = {"number": str(n), "name": title, "book": short, "volume": volume, "title": title}
            # chapter heading + argument — Sabates apparatus
            h_s = B.pos
            B.para(title)
            if ch.get("summary"):
                B.para(clean(ch["summary"]))
            B.add("chapter_heading", h_s, B.pos, label=title, meta={**cmeta, **PROV_APPARATUS})
            # verse bodies — Madueke authoritative (Sabates fallback only if a verse is absent)
            body_s = B.pos
            mad_ch = (mad_book or {}).get(n, {})
            n_fallback = 0
            for v in ch["verses"]:
                vn = _vnum(v.get("verse"))
                mtext = mad_ch.get(vn) if (mad_book is not None and vn is not None) else None
                if mtext is not None:
                    B.para(clean_scripture(mtext))
                else:
                    if mad_book is not None:                 # Madueke expected this verse — flag
                        n_fallback += 1
                        warns.append(f"{slug} {n}:{v.get('verse')} — Madueke verse absent, "
                                     f"fell back to Sabates")
                    B.para(clean(v["text"]))
            if mad_book is None:
                body_meta = {**cmeta, **PROV_APPENDIX}
            elif n_fallback:
                body_meta = {**cmeta, **PROV_FALLBACK, "fallback_verses": n_fallback}
            else:
                body_meta = {**cmeta, **PROV_SCRIPTURE}
            B.add("chapter", body_s, B.pos, label=title, meta=body_meta)
            # masked per-chapter apparatus (footnotes, cross-refs, marginal commentary) — Sabates,
            # after the body so the verse-body span stays single-purpose and unmasked.
            app = chapter_apparatus(slug, ch)
            if app:
                a_s = B.pos
                for p in app:
                    B.para(p)
                B.add("annotation", a_s, B.pos, label=f"{title} apparatus",
                      meta={**cmeta, **PROV_APPARATUS})
        B.add("book", bk_start, B.pos, label=title_line)

    # ---- Old Testament: front matter → books → back matter ----
    emit_region("front_matter", "Old Testament front matter", "ot", OT_FRONT)
    ot_s = B.pos
    B.para("THE OLD TESTAMENT")
    B.add("header", ot_s, B.pos, label="The Old Testament")
    vol_ot_s = B.pos
    for slug in OT:
        emit_book(slug, "Old Testament", slug_to_mad.get(slug, {}))
    B.add("volume", vol_ot_s, B.pos, label="The Old Testament")
    emit_region("back_matter", "Old Testament back matter", "ot", OT_BACK)

    # ---- New Testament: front matter → books → back matter ----
    emit_region("front_matter", "New Testament front matter", "nt", NT_FRONT)
    nt_div_s = B.pos
    B.para("THE NEW TESTAMENT")
    B.add("header", nt_div_s, B.pos, label="The New Testament")
    vol_nt_s = B.pos
    for slug in NT:
        emit_book(slug, "New Testament", slug_to_mad.get(slug, {}))
    B.add("volume", vol_nt_s, B.pos, label="The New Testament")
    emit_region("back_matter", "New Testament back matter", "nt", NT_BACK)

    # ---- Apocrypha appendix — Madueke omits these, Sabates is sole witness (mad_book=None) ----
    apx_s = B.pos
    B.para("ADDITIONAL BOOKS")
    for slug in APOCRYPHA:
        emit_book(slug, "Additional Books", None)
    B.add("appendix", apx_s, B.pos, label="Additional Books")

    text = "".join(B.parts).rstrip()       # ingest normalize() trims trailing whitespace
    return text, B.els, warns


def main():
    text, els, warns = build()
    # normalization-stability assert: the offsets are valid only if ingest won't move them
    from palimpsest.ingest.normalizer import normalize
    norm = normalize(text, strip_paratextual=False)
    assert norm == text, "generated text is NOT normalization-stable; offsets would drift"

    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # body + section list
    n = len(text)
    from collections import Counter
    per = Counter()
    sections = [{"id": "body-0001", "type": "body", "start": 0, "end": n, "label": "",
                 "name": "body", "parent_id": None, "source": "gold", "masked": None,
                 "mask_as": None, "metadata": {"gold_source": "base-generic"}}]
    per["body"] = 1
    for el in sorted(els, key=lambda e: (e["start"], -(e["end"]))):
        t = el["type"]
        end = min(el["end"], n)              # rstrip may have trimmed the final separator
        if el["start"] >= end:
            continue
        per[t] += 1
        sections.append({
            "id": f"{t}-{per[t]:04d}", "type": t, "start": el["start"], "end": end,
            "label": el.get("label", ""), "name": f"{t}_{per[t]}", "parent_id": None,
            "source": "gold", "masked": None, "mask_as": None,
            "metadata": {"gold_source": "dr-original", **(el.get("metadata") or {})},
        })
    from palimpsest.layout import _UNMASKED_TYPES
    types_present = sorted(per)
    mask_by_type = {t: (t not in _UNMASKED_TYPES) for t in types_present}
    m = {
        "schema": "palimpsest.gold-map/v1", "idx": IDX,
        "source_file": OUT_TXT.name, "import_source": OUT_TXT.name,
        "reference_sha256": sha, "text_len": n, "element_count": len(sections),
        "type_counts": dict(per),
        "generated_from": "mask_engine/gen_dr_original.py (Madueke_A olprint HTML scripture + "
                           "janvier-s/original-douay-rheims apparatus)",
        "applied": True, "extra_types": [], "mask_by_type": mask_by_type, "sections": sections,
    }
    MAPS.mkdir(parents=True, exist_ok=True)
    (MAPS / f"work-{IDX}.map.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"work-{IDX}.map.json: {len(sections)} elements, {len(types_present)} types, "
          f"{n} chars, sha {sha[:12]}")
    print("by type:", dict(per))
    if warns:
        print(f"\n⚠ {len(warns)} collation gap(s) — Madueke verse absent, fell back to Sabates:")
        for w in warns[:20]:
            print(f"    {w}")
    else:
        print("scripture provenance: all canonical verses supplied by Madueke_A (0 fallbacks)")


if __name__ == "__main__":
    import sys
    sys.exit(main())
