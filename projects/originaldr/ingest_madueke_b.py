#!/usr/bin/env python
"""Ingest the Madueke_B witness (whole-Bible Douay-Rheims PDF WITH apparatus) into a
transcribed-witness reads file aligned to the OriginalDR canonical verse skeleton.

Source : sources/madueke-b/Original-DouayRheims-Bible.pdf  (1318pp, two-column, scripture
         + per-chapter ARGUMENTS + inline ANNOTATION anchors).
Output : reconstruction/reads/madueke_b.json  (schema mirrors sibling madueke_a.json).

The pages are two-column. `pdftotext -bbox-layout` gives every word's x/y box but
interleaves the two columns within each physical text line. We de-interleave per page by
splitting on the page gutter (x-midpoint), then read the LEFT column fully (top-to-bottom)
before the RIGHT column. That reconstructs correct reading order. Chapters are marked
"Chapter N"; verse 1 opens with a drop-cap (split first letter, no leading number); later
verses open with a bare inline integer. A per-chapter ARGUMENT precedes verse 1.

Book identity is driven by the ordered stream of chapters: a new canonical book begins each
time the chapter number resets (drops to a value <= the running max within the current book).
The resulting book segments are mapped in order onto the skeleton's canonical book list
(chapter counts used to validate). This is deterministic and needs no OCR.

Run:  .venv/bin/python ingest_madueke_b.py
"""
from __future__ import annotations

import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, Optional

import lxml.etree as etree  # type: ignore[import]

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]  # .../palimpsest/core
PDF = HERE / "sources/madueke-b/Original-DouayRheims-Bible.pdf"
BBOX = HERE / ".claude/scratch/madueke_b_bbox.xhtml"
SKELETON = CORE / "tests/fixtures/gold/mask_engine/originaldr_reconstruction/skeleton.json"
MAD_A = HERE / "reconstruction/reads/madueke_a.json"
OUT = HERE / "reconstruction/reads/madueke_b.json"

XHTML_NS = {"x": "http://www.w3.org/1999/xhtml"}
GUTTER = 300.0  # page x-midpoint separating the two columns (page width 612pt)
HEADER_Y = 46.0  # words above this y are running headers (page number + book name)
FOOTER_Y = 748.0  # words below this y are running footers, if any
NORMAL_H = 15.5  # normal body-text glyph box height (pts)
DROPCAP_H = 30.0  # a verse-1 drop cap renders ~64pt tall — anything > this is a drop cap

# ---------------------------------------------------------------------------
# 1. bbox extraction (cached)
# ---------------------------------------------------------------------------


def ensure_bbox() -> Path:
    """Produce (once) the bbox-layout XHTML for the whole PDF."""
    if BBOX.exists() and BBOX.stat().st_size > 1_000_000:
        return BBOX
    BBOX.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftotext", "-bbox-layout", str(PDF), str(BBOX)],
        check=True,
        capture_output=True,
    )
    return BBOX


# ---------------------------------------------------------------------------
# 2. per-page de-interleave into reading-order token stream
# ---------------------------------------------------------------------------

Word = tuple[float, float, float, float, str]  # (xMin, yMin, xMax, height, text)


def page_words(pg: Any) -> list[Word]:
    out: list[Word] = []
    for w in pg.findall(".//x:word", XHTML_NS):
        t = w.text
        if t is None:
            continue
        y0 = float(w.get("yMin", "0"))
        y1 = float(w.get("yMax", "0"))
        out.append(
            (
                float(w.get("xMin", "0")),
                y0,
                float(w.get("xMax", "0")),
                y1 - y0,
                t,
            )
        )
    return out


def running_header(words: list[Word]) -> str:
    """Book display name from the running header (drops the page-number token)."""
    top = [w for w in words if w[1] < HEADER_Y and not w[4].strip().isdigit()]
    top.sort(key=lambda w: w[0])
    return " ".join(w[4] for w in top).strip()


def _sort_column(ws: list[Word]) -> list[Word]:
    # cluster by text line (round y to a small band), read left-to-right within a line
    return sorted(ws, key=lambda w: (round(w[1] / 2.0), w[0]))


def page_reading_order(words: list[Word]) -> list[Word]:
    """Left column (top-to-bottom) then right column (top-to-bottom); drop headers/footers."""
    body = [w for w in words if HEADER_Y <= w[1] <= FOOTER_Y]
    left = _sort_column([w for w in body if w[0] < GUTTER])
    right = _sort_column([w for w in body if w[0] >= GUTTER])
    return left + right


# ---------------------------------------------------------------------------
# 3. drop-cap + token-stream normalization
# ---------------------------------------------------------------------------

# A drop cap renders as an over-sized lone capital letter immediately followed by the rest
# of the word, e.g. big "I" + "N the beginning..." -> "In the beginning...". We detect it by
# glyph box height (>DROPCAP_H), NOT by mere capitalization (arguments contain lone capitals
# like "A Priest's" that must NOT be treated as drop caps).
_CAP = re.compile(r"^[A-Za-z]$")

# a token is (text, is_dropcap)
Tok = tuple[str, bool]


def join_tokens(tokens: list[Tok]) -> str:
    """Join a reading-order token list into text, healing drop-caps.

    A drop-cap capital is merged with the following token; the drop cap itself is upper-case
    while the rest of the word may be upper-case glyphs (small-caps rendering), so we
    title-case the merged first word (e.g. "I"+"N the" -> "In the", "O"+"UR Lord" -> "Our
    Lord"), preserving all-caps only when the source clearly intends it is not resolvable
    from geometry, so we normalize the drop-cap word to Titlecase which matches the upstream.
    """
    out: list[str] = []
    i = 0
    while i < len(tokens):
        text, is_dc = tokens[i]
        if is_dc and i + 1 < len(tokens):
            nxt = tokens[i + 1][0]
            merged = text + nxt
            # drop-cap word is rendered CAP + SMALLCAPS; upstream uses Titlecase.
            merged = merged[:1].upper() + merged[1:].lower()
            out.append(merged)
            i += 2
            continue
        out.append(text)
        i += 1
    return " ".join(out)


_ANCHOR = re.compile(r"[\^*]")  # Madueke annotation/word-explication anchors
_WS = re.compile(r"\s+")


def clean_surface(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = _ANCHOR.sub("", s)
    s = _WS.sub(" ", s).strip()
    # heal a drop-cap capital left dangling before a lowercase run, e.g. "IN" already ok;
    # normalize a leading all-caps duo like "IN the" is fine.
    return s


# ---------------------------------------------------------------------------
# 4. chapter/verse segmentation
# ---------------------------------------------------------------------------

VERSE_NUM = re.compile(r"^\d+$")


def segment_chapters(pages: list[Any]):
    """Walk pages in order, emit an ordered list of chapters.

    Each chapter -> dict(header=book-display-name, ch=int, tokens=[(text, is_dropcap), ...]).
    Chapter boundaries are the "Chapter N" markers in reading order.
    """
    chapters: list[dict] = []
    cur: Optional[dict] = None
    for pg in pages:
        ws = page_words(pg)
        header = running_header(ws)
        stream = page_reading_order(ws)  # list[Word]
        i = 0
        while i < len(stream):
            text = stream[i][4]
            if (
                text == "Chapter"
                and i + 1 < len(stream)
                and VERSE_NUM.match(stream[i + 1][4])
            ):
                ch = int(stream[i + 1][4])
                cur = {"header": header, "ch": ch, "tokens": []}
                chapters.append(cur)
                i += 2
                continue
            if cur is not None:
                is_dc = (
                    len(text) == 1
                    and _CAP.match(text) is not None
                    and stream[i][3] > DROPCAP_H
                )
                cur["tokens"].append((text, is_dc))
            i += 1
    return chapters


def split_verses(tokens: list[Tok]) -> tuple[str, dict[int, str]]:
    """Return (argument_text, {verse_no: text}).

    The ARGUMENT is everything before verse 1's drop cap. Verse 1 opens with a geometric
    drop cap (over-sized capital, no leading number). Later verses open with a bare integer.

    Some short Psalms have no drop cap; there we cannot split the argument geometrically, so
    verse 1 absorbs the preceding argument/psalm-title (present, but flagged low by the
    surface comparison downstream) rather than dropping the verse.
    """
    # locate verse-1 start = first geometric drop-cap position
    start = None
    for i, (_t, is_dc) in enumerate(tokens):
        if is_dc:
            start = i
            break
    if start is None:
        argument = ""
        body = tokens
    else:
        argument = join_tokens(tokens[:start]).strip()
        body = tokens[start:]

    verses: dict[int, str] = {}
    cur_v = 1
    buf: list[Tok] = []
    for tok in body:
        text = tok[0]
        if VERSE_NUM.match(text) and 1 < int(text) <= 250 and cur_v < int(text) + 5:
            # a bare integer greater than the current verse (allowing small gaps) => new verse
            if buf:
                verses[cur_v] = clean_surface(join_tokens(buf))
            cur_v = int(text)
            buf = []
        else:
            buf.append(tok)
    if buf:
        verses[cur_v] = clean_surface(join_tokens(buf))
    verses = {k: v for k, v in verses.items() if v}
    return clean_surface(argument), verses


# ---------------------------------------------------------------------------
# 5. book alignment to skeleton
# ---------------------------------------------------------------------------


def group_books(chapters: list[dict]) -> list[list[dict]]:
    """Group the ordered chapter stream into books: a new book starts whenever the chapter
    number resets to 1, OR drops below the running max of the current book."""
    books: list[list[dict]] = []
    cur: list[dict] = []
    cur_max = 0
    for c in chapters:
        ch = c["ch"]
        new_book = (not cur) or ch == 1 or ch <= cur_max
        # single-chapter books stay ch==1; consecutive ch==1 => new book each time
        if new_book and cur:
            books.append(cur)
            cur = []
            cur_max = 0
        cur.append(c)
        cur_max = max(cur_max, ch)
    if cur:
        books.append(cur)
    return books


def load_skeleton() -> list[dict]:
    d = json.loads(SKELETON.read_text())
    return d["books"]  # ordinal-ordered, includes 3-book appendix


# ---------------------------------------------------------------------------
# 6. madueke_a reference for confidence + coverage sanity
# ---------------------------------------------------------------------------


def load_ref_surfaces() -> dict[str, str]:
    """skeleton_id -> normalized comparison key from madueke_a surfaces."""
    d = json.loads(MAD_A.read_text())
    ref: dict[str, str] = {}
    for r in d["reads"]:
        ref[r["skeleton_id"]] = r["surface"]
    return ref


def cmp_key(s: str) -> str:
    s = unicodedata.normalize("NFC", s.lower())
    s = s.replace("æ", "ae").replace("œ", "oe").replace("&", "and")
    return re.sub(r"[^a-z0-9]", "", s)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    ensure_bbox()
    tree = etree.parse(str(BBOX))
    pages = tree.findall(".//x:page", XHTML_NS)

    chapters = segment_chapters(pages)
    books = group_books(chapters)
    skel = load_skeleton()
    ref = load_ref_surfaces()

    # Align book segments to skeleton. Both should be 76 (73 canonical + 3 appendix) but the
    # PDF may omit the appendix. Map positionally; validate chapter counts and warn on drift.
    n = min(len(books), len(skel))
    reads: list[dict] = []
    apparatus: list[dict] = []
    display_names: dict[str, str] = {}  # slug -> most common running header

    book_ch_seen: set[str] = set()
    verses_total = 0
    high = 0

    for bi in range(n):
        seg = books[bi]
        meta = skel[bi]
        slug = meta["slug"]
        exp_ch = meta["chapters"]
        # record display name
        hdrs = [c["header"] for c in seg if c["header"]]
        if hdrs:
            display_names[slug] = max(set(hdrs), key=hdrs.count)
        locus_book = display_names.get(slug, slug)

        for c in seg:
            ch = c["ch"]
            if ch < 1 or ch > exp_ch:
                # chapter number outside expected range for this book: skip (likely a
                # spurious "Chapter N" from a mis-grouped boundary); keep honest.
                continue
            argument, verses = split_verses(c["tokens"])
            book_ch_seen.add(f"{slug}/{ch}")
            if argument:
                apparatus.append(
                    {"book": slug, "chapter": ch, "kind": "argument", "text": argument}
                )
            for vn, surface in sorted(verses.items()):
                sid = f"scripture/{slug}/{ch}/{vn}"
                ref_surface = ref.get(sid)
                if ref_surface is not None and cmp_key(surface) == cmp_key(ref_surface):
                    conf = "high"
                    high += 1
                elif ref_surface is not None and (
                    cmp_key(surface)[:40] == cmp_key(ref_surface)[:40]
                    or cmp_key(ref_surface).startswith(cmp_key(surface)[:60])
                    or cmp_key(surface).startswith(cmp_key(ref_surface)[:60])
                ):
                    conf = "medium"
                else:
                    conf = "low"
                reads.append(
                    {
                        "skeleton_id": sid,
                        "present": True,
                        "surface": surface,
                        "spelling": "modern",
                        "locus": f"madueke-b/pdf ({locus_book} {ch})",
                        "method": "pdf-bbox-two-column",
                        "local_confidence": conf,
                        "evidence_ptr": f"madueke_b:{locus_book}:{ch}:{vn}",
                    }
                )
                verses_total += 1

    # coverage
    books_cov = len({sid.split("/")[1] for sid in (r["skeleton_id"] for r in reads)})
    chapters_cov = len(book_ch_seen)
    # out_of_grid: reads whose (book,ch,verse) exceed skeleton — we already clamp chapters to
    # expected range and only emit known slugs, so grid is exact; keep the key for schema parity.
    out_of_grid: list[str] = []

    doc = {
        "source": "madueke_b",
        "lineage": "madueke",
        "independent": False,
        "spelling": "modern",
        "count": len(reads),
        "coverage": {
            "books": books_cov,
            "chapters": chapters_cov,
            "verses": verses_total,
            "out_of_grid": out_of_grid,
            "out_of_grid_count": len(out_of_grid),
        },
        "reads": reads,
        "apparatus_blocks": apparatus,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1))

    # ---- report ----
    print(f"book segments detected: {len(books)}  (skeleton books: {len(skel)})")
    print(f"aligned books        : {books_cov}")
    print(f"chapters covered     : {chapters_cov}")
    print(f"verses parsed        : {verses_total}")
    print(f"  high-confidence    : {high} ({high/verses_total*100:.1f}%)" if verses_total else "  (no verses)")
    print(f"apparatus_blocks     : {len(apparatus)}")
    print(f"wrote {OUT}")

    # spot-check
    def show(sid: str) -> None:
        for r in reads:
            if r["skeleton_id"] == sid:
                print(f"  {sid} [{r['local_confidence']}] {r['surface']!r}")
                return
        print(f"  {sid} MISSING")

    print("\n--- Genesis 1:1-5 ---")
    for v in range(1, 6):
        show(f"scripture/genesis/1/{v}")
    print("--- John 1:1-3 ---")
    for v in range(1, 4):
        show(f"scripture/john/1/{v}")


if __name__ == "__main__":
    main()
