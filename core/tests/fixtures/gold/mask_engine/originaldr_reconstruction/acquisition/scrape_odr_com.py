#!/usr/bin/env python
"""P0.2 — Scrape originaldouayrheims.com into verse-addressable JSON + validate vs Madueke_A.

originaldouayrheims.com is the ARCHAIC-SPELLING, modern-typeset witness (independent of the
Madueke lineage). The site has completed the entire NT plus 12 OT books. This script:

  1. DISCOVERS each book's URL slug + chapter count empirically from the book landing page's
     chapter-link list (in the page <head>'s <h3><ul>) — never hardcoding chapter counts.
  2. FETCHES every chapter page (cached, resumable, polite) and parses verses from the
     ``<b>N. </b>text`` markup, capturing marginal ``<span class="side">`` notes and NT
     ``<span id="Annotations2">`` annotations separately, plus the book "argument" page.
  3. NORMALIZES the unicode small-caps used for opening words back to normal letters
     (Aɴᴅ -> And) while PRESERVING the diplomatic archaic spelling (long-s, ae/oe, u/v,
     i/j, vv, &) verbatim.
  4. VALIDATES parse accuracy against the modern-spelling Madueke_A witness at VERSE
     granularity where the books overlap, using the same archaic<->modern skeleton fold as
     originaldr_validation/collate_witnesses.py so spelling differences do NOT count as
     mismatches — only genuinely different WORDING does.

Outputs (scratch, gitignored):  odr-com/scrape/<book>.json  +  odr-com/cache/<slug>.html
Outputs (tracked):              acquisition/odr-scrape-manifest.json

The scrape's HTML-parse accuracy is *validated, not assumed*: the manifest records, per
overlapping book, the verse-count match and the post-fold wording-agreement fraction.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # R9.6
import project_root as pr  # noqa: E402  R9.6: one derived root

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
HERE = Path(__file__).resolve().parent                       # .../acquisition
# HERE.parents: [0]originaldr_reconstruction [1]mask_engine [2]gold [3]fixtures
#               [4]tests [5]core [6]<repo>
REPO = HERE.parents[6]
ODR = pr.ODR_COM
CACHE = ODR / "cache"
SCRAPE_OUT = ODR / "scrape"
MANIFEST = HERE / "odr-scrape-manifest.json"
MADA = pr.MADUEKE_A

BASE = "https://www.originaldouayrheims.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
DELAY = 0.7  # seconds between live fetches (polite)

# --------------------------------------------------------------------------- #
# Book roster — the 27 completed books. `landing` is the site's book landing page
# (from which slug + chapter count are DISCOVERED). We never hardcode chapter counts.
# The landing paths themselves are grounded in the probe HTML nav lists.
# --------------------------------------------------------------------------- #
OT_BOOKS = [  # (canonical book key, testament, landing path)
    ("genesis", "OT", "/old/genesis"),
    ("exodus", "OT", "/old/exodus"),
    ("ruth", "OT", "/old/ruth"),
    ("psalms", "OT", "/old/psalms"),
    ("wisdom", "OT", "/old/wisdom"),
    ("lamentations", "OT", "/old/lamentations"),
    ("baruch", "OT", "/old/baruch"),
    ("daniel", "OT", "/old/daniel"),
    ("jonas", "OT", "/old/jonas"),
    ("sophonias", "OT", "/old/sophonias"),
    ("1-machabees", "OT", "/old/1machabees"),
    ("2-machabees", "OT", "/old/2machabees"),
]
NT_BOOKS = [
    ("matthew", "NT", "/matthew"),
    ("mark", "NT", "/mark"),
    ("luke", "NT", "/luke"),
    ("john", "NT", "/john"),
    ("acts", "NT", "/acts"),
    ("romans", "NT", "/romans"),
    ("1-corinthians", "NT", "/1corinthians"),
    ("2-corinthians", "NT", "/2corinthians"),
    ("galatians", "NT", "/galatians"),
    ("ephesians", "NT", "/ephesians"),
    ("philippians", "NT", "/philippians"),
    ("colossians", "NT", "/colossians"),
    ("1-thessalonians", "NT", "/1thessalonians"),
    ("2-thessalonians", "NT", "/2thessalonians"),
    ("1-timothy", "NT", "/1timothy"),
    ("2-timothy", "NT", "/2timothy"),
    ("titus", "NT", "/titus"),
    ("philemon", "NT", "/philemon"),
    ("hebrews", "NT", "/hebrews"),
    ("james", "NT", "/james"),
    ("1-peter", "NT", "/1peter"),
    ("2-peter", "NT", "/2peter"),
    ("1-john", "NT", "/1john"),
    ("2-john", "NT", "/2john"),
    ("3-john", "NT", "/3john"),
    ("jude", "NT", "/jude"),
    ("apocalypse", "NT", "/revelations"),
]
BOOKS = OT_BOOKS + NT_BOOKS

# Candidate landing paths to try per book (the site is inconsistent: some NT books use an
# abbreviation, some spell out, some Roman-numeral OT/NT books use `.html` links). We probe
# these in order and take the first that returns a real (non-404) chapter-list page.
LANDING_CANDIDATES: dict[str, list[str]] = {
    "1-corinthians": ["/1corinthians", "/I Corinthians.html", "/1cor"],
    "2-corinthians": ["/2corinthians", "/II Corinthians.html", "/2cor"],
    "1-thessalonians": ["/1thessalonians", "/I Thessalonians.html", "/1thes"],
    "2-thessalonians": ["/2thessalonians", "/II Thessalonians.html", "/2thes"],
    "1-timothy": ["/1timothy", "/I Timothee.html", "/1tim"],
    "2-timothy": ["/2timothy", "/II Timothee.html", "/2tim"],
    "1-peter": ["/1peter", "/I Peter.html", "/1pet"],
    "2-peter": ["/2peter", "/II Peter.html", "/2pet"],
    "1-john": ["/1john", "/I John.html", "/1jo"],
    "2-john": ["/2john", "/II John.html", "/2jo"],
    "3-john": ["/3john", "/III John.html", "/3jo"],
    "apocalypse": ["/revelations", "/apocalypse", "/revelation"],
    # Machabees are hosted under /Old/ as literal-space .html files whose chapter links are
    # RELATIVE (e.g. "I Machabees2.html"), resolved against the landing directory (/Old/).
    "1-machabees": ["/Old/I Machabees.html", "/old/1machabees", "/old/machabees1"],
    "2-machabees": ["/Old/II Machabees.html", "/old/2machabees", "/old/machabees2"],
}

# --------------------------------------------------------------------------- #
# Small-caps normalization: map the site's opening-word small-caps back to letters,
# preserving the archaic spelling of the WORD (Aɴᴅ -> And; Iᴇꜱᴠꜱ -> Iesvs).
# Unicode "LATIN LETTER SMALL CAPITAL X" codepoints -> the plain capital X.
# --------------------------------------------------------------------------- #
SMALLCAP = {
    "ᴀ": "A", "ʙ": "B", "Ꞵ": "C", "ᴄ": "C", "ᴅ": "D",
    "ᴇ": "E", "ꜰ": "F", "ɢ": "G", "ʜ": "H", "ɪ": "I",
    "ᴊ": "J", "ᴋ": "K", "ʟ": "L", "ᴍ": "M", "ɴ": "N",
    "ᴏ": "O", "ᴘ": "P", "ǫ": "Q", "ʀ": "R", "ꜱ": "S",
    "ᴛ": "T", "ᴜ": "U", "ᴠ": "V", "ᴡ": "W", "ʏ": "Y",
    "ᴢ": "Z",
}
SMALLCAP_RE = re.compile("|".join(re.escape(k) for k in SMALLCAP))


def fold_smallcaps(s: str) -> str:
    return SMALLCAP_RE.sub(lambda m: SMALLCAP[m.group(0)], s)


# --------------------------------------------------------------------------- #
# Networking (cached / resumable)
# --------------------------------------------------------------------------- #
def cache_key(path: str) -> str:
    """Stable, filesystem-safe cache filename for a site path."""
    slug = path.strip("/").replace("/", "__").replace(" ", "_")
    slug = re.sub(r"[^A-Za-z0-9_.-]", "_", slug) or "root"
    if not slug.lower().endswith(".html"):
        slug += ".html"
    return slug


def fetch(path: str, *, allow_404: bool = True) -> tuple[str | None, str, bool]:
    """Fetch a site path with on-disk cache. Returns (text_or_None, cache_file, from_cache).

    A cached page is never re-fetched (resumable). ``text`` is None only on a hard network
    failure; 404 pages ARE cached (so discovery of chapter-count-by-probe is resumable).
    """
    cf = CACHE / cache_key(path)
    if cf.exists():
        return cf.read_text(encoding="utf-8", errors="replace"), str(cf), True
    url = BASE + urllib.parse.quote(path, safe="/:")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
        text = raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404 and allow_404:
            text = e.read().decode("utf-8", errors="replace") if e.fp else "<title>Page not found</title>"
        else:
            print(f"  !! HTTP {e.code} for {path}", file=sys.stderr)
            return None, str(cf), False
    except Exception as e:  # noqa: BLE001 — network is inherently flaky; log and skip
        print(f"  !! fetch error for {path}: {e}", file=sys.stderr)
        return None, str(cf), False
    cf.write_text(text, encoding="utf-8")
    time.sleep(DELAY)
    return text, str(cf), False


def is_404(text: str | None) -> bool:
    if text is None:
        return True
    return "<title>Page not found</title>" in text or "Original Douay" not in text and \
        "roleText" not in text and "<b>1." not in text and "class=\"side\"" not in text \
        and "class='side'" not in text and "Page not found" in text


# --------------------------------------------------------------------------- #
# Chapter-link discovery from a book landing page
# --------------------------------------------------------------------------- #
_HEAD_RE = re.compile(r"<head\b[^>]*>(.*?)</head>", re.S | re.I)
_LI_A_RE = re.compile(r"<a\s+[^>]*href=(['\"])(.*?)\1[^>]*>(.*?)</a>", re.S | re.I)


def resolve_href(href: str, landing_path: str) -> str:
    """Resolve a chapter/argument href to a site-absolute path.

    Site links are inconsistent: some are absolute (``/mat2``), some are relative to the
    landing page's directory (``I Machabees2.html`` from ``/Old/I Machabees.html`` ->
    ``/Old/I Machabees2.html``), and some use ``../`` (``../I Kings.html``). We resolve via
    urljoin against a fake origin so directory/relative semantics are handled correctly.
    """
    if href.startswith("/"):
        return href
    base = "http://x" + urllib.parse.quote(landing_path, safe="/: ")
    joined = urllib.parse.urljoin(base, urllib.parse.quote(href, safe="/: "))
    path = urllib.parse.urlsplit(joined).path
    return urllib.parse.unquote(path)


def discover_chapters(landing_html: str, book_key: str,
                      landing_path: str = "/") -> tuple[str | None, list[tuple[int, str]]]:
    """Parse a landing page's <head> chapter-link list.

    Returns (slug, [(chapter_number, chapter_path), ...]) sorted by chapter number, where
    slug is the discovered site slug (e.g. 'genesis', 'mat'). The chapter list is derived
    from the <li><a href=...>N</a> entries whose visible text is an integer. Relative hrefs
    are resolved against ``landing_path``.
    """
    head = _HEAD_RE.search(landing_html)
    scope = head.group(1) if head else landing_html
    chapters: dict[int, str] = {}
    for m in _LI_A_RE.finditer(scope):
        href = html.unescape(m.group(2)).strip()
        label = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        if not re.fullmatch(r"\d+", label):
            continue  # skip argument / summary links (non-numeric labels)
        n = int(label)
        chapters[n] = resolve_href(href, landing_path)
    if not chapters:
        return None, []
    # slug: from the chapter-2 path if present (e.g. /old/genesis/genesis2 -> genesis;
    # /mat2 -> mat), else from the landing path tail.
    slug = None
    ch2 = chapters.get(2) or chapters.get(min(k for k in chapters if k > 1)) if len(chapters) > 1 else None
    if ch2:
        tail = ch2.strip("/").split("/")[-1]
        tail = re.sub(r"\.html?$", "", tail, flags=re.I)  # strip .html so slug excludes it
        m = re.match(r"^(.*?)(\d+)$", tail)
        if m:
            slug = m.group(1).strip()
    return slug, sorted(chapters.items())


# --------------------------------------------------------------------------- #
# Chapter-page verse parsing
# --------------------------------------------------------------------------- #
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# The scripture container lives between the New-Testament <nav>... and the trailing
# <nav class="Old"> / <style> / <footer>. We isolate the <p>...</p> scripture block, but the
# markup is loose (unclosed <p>), so we bound by removing nav/footer/style regions instead.
_NAV_RE = re.compile(r"<nav\b.*?</nav>", re.S | re.I)
_FOOTER_RE = re.compile(r"<footer\b.*?</footer>", re.S | re.I)
_STYLE_RE = re.compile(r"<style\b.*?</style>", re.S | re.I)
_SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.S | re.I)
_HEAD_STRIP = re.compile(r"<head\b.*?</head>", re.S | re.I)
_H1_RE = re.compile(r"<h1\b.*?</h1>", re.S | re.I)

# tooltip / cross-ref markup that must NOT appear in verse text: the whole
# <span class="container"> ... </span> holds a <b class="tooltip...">MARKER<span class="tooltip2">
# HIDDEN NOTE</span></b> plus the anchor glyph. We drop the tooltip2 hidden text and the
# marker glyphs, but KEEP the surrounding scripture words.
_TOOLTIP2_RE = re.compile(r"<span\s+[^>]*class\s*=\s*['\"]?tooltip2['\"]?[^>]*>.*?</span>", re.S | re.I)
# side / annotation / summary / header-note spans are captured separately, then removed.
_SIDE_RE = re.compile(r"<span\s+[^>]*class\s*=\s*['\"]?side['\"]?[^>]*>(.*?)</span>", re.S | re.I)
_ANNOT2_RE = re.compile(r"<span\s+[^>]*id\s*=\s*['\"]?Annotations2['\"]?[^>]*>(.*?)</span>", re.S | re.I)
_HEADERNOTE_RE = re.compile(r"<span\s+[^>]*id\s*=\s*['\"]?HeaderNote['\"]?[^>]*>(.*?)</span>", re.S | re.I)
# glyph markers used as tooltip anchors
_MARKER_CHARS = "⋮✟*†"  # vertical-ellipsis, latin-cross, asterisk, dagger


def _clean_text(s: str) -> str:
    """Strip residual markup, unescape entities, fold small-caps, collapse whitespace.

    Preserves diplomatic archaic glyphs (long-s, ae/oe, u/v, i/j, vv, &) verbatim.
    """
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = fold_smallcaps(s)
    s = s.replace(" ", " ")
    for ch in _MARKER_CHARS:
        s = s.replace(ch, " ")
    s = unicodedata.normalize("NFC", s)
    return _WS.sub(" ", s).strip()


def _strip_containers(block: str) -> str:
    """Remove tooltip hidden text so cross-ref/annotation notes don't leak into verse text.

    We drop only the hidden ``tooltip2`` payload and the anchor marker glyphs; the visible
    scripture text that surrounds the container is preserved.
    """
    prev = None
    while prev != block:
        prev = block
        block = _TOOLTIP2_RE.sub(" ", block)
    return block


# THE ID MUST MATCH EXACTLY, and the optional quotes are why it did not. `['\"]?Annotations['\"]?` also
# matches the PREFIX of `id="Annotations2"` — the closing quote is optional, and `[^>]*` then swallows the
# trailing `2">`. So the scripture stream was cut at the first `Annotations2` span rather than at the real
# ANNOTATIONS. header, and `Annotations2` is a span the site uses INSIDE the scripture (see `parse_chapter`).
# That single character of slack silently truncated 13 of Genesis's 50 chapters — genesis 4, 6 and 9 at verse
# 7, genesis 13 at verse 4, genesis 49 at verse 2 — 155 verses of scripture, recorded in the manifest as
# `verse_count_match: 37/50` and never read.
_ANNOT_HDR_MARK = re.compile(r"<span\s+[^>]*id\s*=\s*(?:\"Annotations\"|'Annotations'|Annotations(?=[\s>]))"
                             r"[^>]*>", re.I)


def parse_chapter(page_html: str, _chapter_num: int) -> tuple[dict[str, str], list[str]]:
    """Parse a chapter page into ({verse_str: text}, [notes]).

    Verses are ``<b>N. </b>...`` runs. A leading ``<b>NN. </b>`` equal to the chapter number
    is the chapter heading, not a verse (handled).

    The scripture stream ENDS at the first ``<span id="Annotations">`` header ("ANNOTATIONS.")
    — everything after it is the apparatus (whether formatted as ``Annotations2`` or
    ``indenttext``) and is captured into ``notes``, never inlined into a verse. Marginal
    ``side``/``HeaderNote`` spans within the scripture region are likewise captured as notes.
    """
    # 1) drop non-scripture chrome regions
    body = _HEAD_STRIP.sub(" ", page_html)
    body = _H1_RE.sub(" ", body)
    body = _SCRIPT_RE.sub(" ", body)
    body = _STYLE_RE.sub(" ", body)
    body = _NAV_RE.sub(" ", body)
    body = _FOOTER_RE.sub(" ", body)

    notes: list[str] = []

    # 2) SPLIT scripture from apparatus at the "ANNOTATIONS." header. This is the robust
    #    boundary: all footnote/annotation prose (Annotations2 spans, indenttext spans, or
    #    loose text) lives after it and must NOT leak into the last verse.
    hdr = _ANNOT_HDR_MARK.search(body)
    if hdr:
        apparatus = body[hdr.start():]
        body = body[:hdr.start()]
        # capture the apparatus prose (drop the "ANNOTATIONS." header word itself later)
        appar_txt = _clean_text(_strip_containers(apparatus))
        appar_txt = re.sub(r"^\s*ANNOTATIONS\.?\s*", "", appar_txt, flags=re.I)
        if appar_txt:
            notes.append(appar_txt)

    # 3) capture marginal/header notes still inside the scripture region, then remove them.
    #
    #    `Annotations2` IS NOT A KIND OF CONTENT, IT IS A STYLE, and its meaning is positional: after the
    #    ANNOTATIONS. header it wraps annotation prose (`1. <i>In the beginning.</i>] The Church had only
    #    Traditions...`), but BEFORE it the site uses the very same id to wrap plain scripture — genesis 4
    #    carries verses 8-15 and 16-26 in two such spans, genesis 13 verses 5-9 and 10-18. Deleting them from
    #    the scripture region as apparatus would throw away the verses that the header fix has just recovered.
    #
    #    The two are told apart by what they contain, not by where the writer of this parser expected them:
    #    scripture spans carry `<b>N. </b>` verse markers, annotation spans number their notes in plain text.
    _has_verse_marker = re.compile(r"<b>\s*\d+\s*\.?\s*</b>", re.I)
    for rx in (_SIDE_RE, _HEADERNOTE_RE, _ANNOT2_RE):
        for m in rx.finditer(body):
            if rx is _ANNOT2_RE and _has_verse_marker.search(m.group(1)):
                continue                       # scripture in an annotation-styled span — leave it in `body`
            txt = _clean_text(_strip_containers(m.group(1)))
            if txt:
                notes.append(txt)
    body = _ANNOT2_RE.sub(lambda m: m.group(0) if _has_verse_marker.search(m.group(1)) else " ", body)
    body = _SIDE_RE.sub(" ", body)
    body = _HEADERNOTE_RE.sub(" ", body)

    # 4) strip tooltip hidden payloads so they don't pollute verse text
    body = _strip_containers(body)

    # 5) split on <b>N. </b> verse markers. Capture the number and the following run.
    marker = re.compile(r"<b>\s*(\d+)\s*\.?\s*</b>", re.I)
    parts = marker.split(body)
    # parts = [pre, num1, text1, num2, text2, ...]
    verses: dict[str, str] = {}
    i = 1
    while i < len(parts):
        num = parts[i]
        raw = parts[i + 1] if i + 1 < len(parts) else ""
        i += 2
        n = int(num)
        text = _clean_text(raw)
        # A marker whose number equals the chapter number and which has NO following verse
        # text of its own is a chapter heading, not verse 1. But a real verse can also carry
        # the chapter number (e.g. verse 1). Heuristic: treat as heading only if empty text.
        if not text:
            continue
        if str(n) in verses:
            verses[str(n)] = (verses[str(n)] + " " + text).strip()
        else:
            verses[str(n)] = text
    # de-dup / clean notes
    seen = set()
    uniq_notes = []
    for nn in notes:
        if nn not in seen:
            seen.add(nn)
            uniq_notes.append(nn)
    return verses, uniq_notes




def parse_argument(page_html: str) -> str | None:
    """Extract a book/chapter 'argument' page's prose (strip nav/footer/head/headers)."""
    body = _HEAD_STRIP.sub(" ", page_html)
    body = _H1_RE.sub(" ", body)
    body = _SCRIPT_RE.sub(" ", body)
    body = _STYLE_RE.sub(" ", body)
    body = _NAV_RE.sub(" ", body)
    body = _FOOTER_RE.sub(" ", body)
    body = _strip_containers(body)
    # remove any h2/h3 headers (book title / "THE ARGVMENT...")
    body = re.sub(r"<h[23]\b.*?</h[23]>", " ", body, flags=re.S | re.I)
    txt = _clean_text(body)
    return txt or None


# --------------------------------------------------------------------------- #
# Argument-page discovery: the landing page links a non-numeric "argument" entry.
# --------------------------------------------------------------------------- #
def find_argument_path(landing_html: str, landing_path: str = "/") -> str | None:
    head = _HEAD_RE.search(landing_html)
    scope = head.group(1) if head else landing_html
    for m in _LI_A_RE.finditer(scope):
        href = html.unescape(m.group(2)).strip()
        label = re.sub(r"<[^>]+>", "", m.group(3)).strip().upper()
        if "ARGVMENT" in label or "ARGUMENT" in label:
            return resolve_href(href, landing_path)
    return None


# --------------------------------------------------------------------------- #
# Scrape one book
# --------------------------------------------------------------------------- #
def scrape_book(book_key: str, testament: str, landing_default: str) -> dict:
    print(f"[{book_key}] discovering...", file=sys.stderr)
    landing_html = None
    landing_path = None
    for cand in LANDING_CANDIDATES.get(book_key, [landing_default]):
        text, _, _ = fetch(cand)
        if text and "<title>Page not found</title>" not in text and \
                (_LI_A_RE.search(text) and (">roleText" not in text)):
            # a real book landing page has numeric chapter links in <head>
            slug, chapters = discover_chapters(text, book_key, cand)
            if chapters:
                landing_html, landing_path = text, cand
                break
    if landing_html is None:
        # last resort: try the default landing even if heuristic above failed
        text, _, _ = fetch(landing_default)
        if text and "<title>Page not found</title>" not in text:
            landing_html, landing_path = text, landing_default

    slug, chapters = (None, [])
    if landing_html:
        slug, chapters = discover_chapters(landing_html, book_key, landing_path)

    arg_path = find_argument_path(landing_html, landing_path) if landing_html else None
    book_argument = None
    if arg_path:
        atext, _, _ = fetch(arg_path)
        if atext and "<title>Page not found</title>" not in atext:
            book_argument = parse_argument(atext)

    out_chapters = []
    pages = []
    if landing_path:
        pages.append(landing_path)
    if arg_path:
        pages.append(arg_path)

    for n, ch_path in chapters:
        text, _, _ = fetch(ch_path)
        pages.append(ch_path)
        if text is None or "<title>Page not found</title>" in text:
            print(f"  [{book_key}] ch{n} -> 404/empty ({ch_path})", file=sys.stderr)
            continue
        verses, notes = parse_chapter(text, n)
        out_chapters.append({
            "chapter": n,
            "argument": None,   # per-chapter arguments not consistently linked; book arg above
            "verses": verses,
            "notes": notes,
        })

    result = {
        "book": book_key,
        "testament": testament,
        "slug": slug,
        "landing_path": landing_path,
        "argument": book_argument,
        "chapters": out_chapters,
        "_pages": pages,
    }
    nv = sum(len(c["verses"]) for c in out_chapters)
    print(f"  [{book_key}] slug={slug} chapters={len(out_chapters)} verses={nv}", file=sys.stderr)
    return result


# --------------------------------------------------------------------------- #
# Validation vs Madueke_A (verse-granularity, archaic<->modern skeleton fold)
# --------------------------------------------------------------------------- #
# Madueke book-display -> our book_key. Madueke titles are e.g. "Genesis", "1 Corinthians",
# "Apocalypse". We normalize both sides to a comparable key.
def _madueke_key(display: str) -> str:
    d = display.strip().lower()
    d = re.sub(r"\s+", "-", d)
    aliases = {
        "canticle-of-canticles": "canticle-of-canticles",
        "apocalypse": "apocalypse",
    }
    return aliases.get(d, d)


ODR_TO_MAD = {
    "genesis": "genesis", "exodus": "exodus", "ruth": "ruth", "psalms": "psalms",
    "wisdom": "wisdom", "lamentations": "lamentations", "baruch": "baruch",
    "daniel": "daniel", "jonas": "jonas", "sophonias": "sophonias",
    "1-machabees": "1-machabees", "2-machabees": "2-machabees",
    "matthew": "matthew", "mark": "mark", "luke": "luke", "john": "john",
    "acts": "acts", "romans": "romans", "1-corinthians": "1-corinthians",
    "2-corinthians": "2-corinthians", "galatians": "galatians", "ephesians": "ephesians",
    "philippians": "philippians", "colossians": "colossians",
    "1-thessalonians": "1-thessalonians", "2-thessalonians": "2-thessalonians",
    "1-timothy": "1-timothy", "2-timothy": "2-timothy", "titus": "titus",
    "philemon": "philemon", "hebrews": "hebrews", "james": "james",
    "1-peter": "1-peter", "2-peter": "2-peter", "1-john": "1-john", "2-john": "2-john",
    "3-john": "3-john", "jude": "jude", "apocalypse": "apocalypse",
}

_MAD_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
_MAD_ROLE_RE = re.compile(r"class='roleText'[^>]*>(.*?)</div>", re.S)
_MAD_SUP_RE = re.compile(r"<sup>(\d+)</sup>")


def parse_madueke() -> dict[str, dict[int, dict[int, str]]]:
    """Parse Madueke_A per-chapter HTML into {mad_key: {chapter: {verse: raw_text}}}."""
    books: dict[str, dict[int, dict[int, str]]] = {}
    if not MADA.exists():
        return books
    for p in sorted(MADA.glob("*.html"), key=lambda p: int(p.stem)):
        h = p.read_text(encoding="utf-8", errors="replace")
        mt = _MAD_TITLE_RE.search(h)
        if not mt:
            continue
        mm = re.match(r"^(.*?)\s+(\d+)$", mt.group(1).strip())
        if not mm:
            continue
        display, ch = mm.group(1).strip(), int(mm.group(2))
        key = _madueke_key(display)
        joined = " ".join(_MAD_ROLE_RE.findall(h))
        parts = _MAD_SUP_RE.split(joined)
        verses: dict[int, str] = {}
        i = 1
        while i < len(parts):
            vn = int(parts[i])
            vt = parts[i + 1] if i + 1 < len(parts) else ""
            verses[vn] = (verses.get(vn, "") + " " + vt).strip() if vn in verses else vt
            i += 2
        books.setdefault(key, {})[ch] = verses
    return books


# archaic<->modern skeleton fold (mirrors collate_witnesses.py's philosophy: fold long-s,
# ae/oe, u/v, i/j, vv->w, &->and, strip note anchors, drop non-letters). Applied to BOTH
# sides so only genuinely different WORDING survives. This is the AGGRESSIVE archaic fold
# appropriate for archaic-vs-modern comparison (not the light modern-vs-modern fold): it
# additionally collapses doubled consonants and drops a silent trailing -e, so that archaic
# forms like "shal/sonne/cunning" skeletonize to the same token as modern "shall/son/cuning".
def _skeleton(text: str) -> str:
    s = unicodedata.normalize("NFC", text or "")
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = fold_smallcaps(s)
    s = s.lower()
    # archaic ligatures / glyphs -> modern skeleton
    s = s.replace("ſ", "s")          # long-s
    s = s.replace("æ", "ae").replace("œ", "oe")
    s = s.replace("&", " and ")
    s = s.replace("vv", "w")
    # strip note-anchor glyphs and punctuation
    for ch in _MARKER_CHARS:
        s = s.replace(ch, " ")
    # remove diacritics
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    # letters only, then fold u<->v, i<->j, and y->i (praiers/prayers, daies/days) to a
    # canonical letter each — all common archaic<->modern orthographic variants.
    s = re.sub(r"[^a-z ]+", " ", s)
    s = s.replace("v", "u").replace("j", "i").replace("y", "i")
    return _WS.sub(" ", s).strip()


def _fold_word(w: str) -> str:
    """Per-word archaic skeleton: collapse doubled letters and drop a silent trailing -e.

    Order matters: collapse doubled letters first (shall->shal, call->cal), then drop a
    trailing e on words of length>=3 (sonne->sonn->son via the collapse+strip; borne->born).
    Applied identically to archaic and modern tokens so only real wording diffs survive.
    """
    if len(w) < 3:
        return w
    w = re.sub(r"(.)\1+", r"\1", w)          # doubled -> single (shall->shal, sonne->sone)
    if len(w) > 2 and w.endswith("e"):
        w = w[:-1]                            # silent trailing -e (sone->son, borne->born)
    return w


def _words(text: str) -> list[str]:
    return [_fold_word(w) for w in _skeleton(text).split()]


def validate_book(book: dict, mad: dict[str, dict[int, dict[int, str]]]) -> dict | None:
    mad_key = ODR_TO_MAD.get(book["book"])
    if not mad_key or mad_key not in mad:
        return None
    mad_book = mad[mad_key]
    overlap_ch = 0
    verse_count_match = 0
    verse_count_total = 0
    word_agree = 0
    word_total = 0
    # chapter-level bag-of-words agreement — VERSIFICATION-INSENSITIVE. When the two editions
    # split a chapter into a different number of verses, per-verse alignment goes off-by-one
    # and under-reports; this whole-chapter metric isolates genuine text loss from mere
    # verse-boundary differences (high chapter-bag + low per-verse == versification, not a
    # parse defect).
    ch_word_agree = 0
    ch_word_total = 0
    chapter_reports = []
    for cobj in book["chapters"]:
        cn = cobj["chapter"]
        if cn not in mad_book:
            continue
        overlap_ch += 1
        verse_count_total += 1
        odr_v = cobj["verses"]
        mad_v = {str(k): v for k, v in mad_book[cn].items()}
        odr_nums = set(odr_v)
        mad_nums = set(mad_v)
        if odr_nums == mad_nums:
            verse_count_match += 1
        # per-verse folded word agreement over the intersection of verse numbers
        for vn in odr_nums & mad_nums:
            ow = _words(odr_v[vn])
            mw = _words(mad_v[vn])
            # bag-of-words agreement (order-insensitive) — robust to minor tokenization
            oc, mc = Counter(ow), Counter(mw)
            inter = sum((oc & mc).values())
            denom = max(sum(oc.values()), sum(mc.values()), 1)
            word_agree += inter
            word_total += denom
        # whole-chapter bag (versification-insensitive)
        oc_all = Counter(_words(" ".join(odr_v.values())))
        mc_all = Counter(_words(" ".join(mad_v.values())))
        ch_word_agree += sum((oc_all & mc_all).values())
        ch_word_total += max(sum(oc_all.values()), sum(mc_all.values()), 1)
        chapter_reports.append({
            "chapter": cn,
            "odr_verses": len(odr_nums),
            "mad_verses": len(mad_nums),
            "verse_num_match": odr_nums == mad_nums,
            "odr_only": sorted((odr_nums - mad_nums), key=lambda x: int(x))[:8],
            "mad_only": sorted((mad_nums - odr_nums), key=lambda x: int(x))[:8],
        })
    folded_agreement = round(word_agree / word_total, 4) if word_total else None
    chapter_bag_agreement = round(ch_word_agree / ch_word_total, 4) if ch_word_total else None
    return {
        "madueke_key": mad_key,
        "overlap_chapters": overlap_ch,
        "verse_count_match_chapters": verse_count_match,
        "verse_count_total_chapters": verse_count_total,
        "folded_agreement": folded_agreement,
        "chapter_bag_agreement": chapter_bag_agreement,
        "chapter_detail": chapter_reports,
    }


# --------------------------------------------------------------------------- #
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", nargs="*", help="restrict to these book keys (default: all 27)")
    ap.add_argument("--no-validate", action="store_true", help="skip Madueke validation")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    SCRAPE_OUT.mkdir(parents=True, exist_ok=True)

    roster = [b for b in BOOKS if (not args.books or b[0] in args.books)]

    mad = {} if args.no_validate else parse_madueke()
    if not args.no_validate:
        print(f"Madueke_A parsed: {len(mad)} books", file=sys.stderr)

    manifest_books = []
    totals = Counter()
    for book_key, testament, landing in roster:
        book = scrape_book(book_key, testament, landing)
        pages = book.pop("_pages")
        # write per-book JSON (contract order)
        out = {
            "book": book["book"],
            "testament": book["testament"],
            "slug": book["slug"],
            "argument": book["argument"],
            "chapters": book["chapters"],
        }
        (SCRAPE_OUT / f"{book_key}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        nch = len(book["chapters"])
        nv = sum(len(c["verses"]) for c in book["chapters"])
        totals["chapters"] += nch
        totals["verses"] += nv

        # page sha manifest (sha over cached bytes)
        page_records = []
        for pth in dict.fromkeys(pages):  # dedup, keep order
            cf = CACHE / cache_key(pth)
            sha = sha256_text(cf.read_text(encoding="utf-8", errors="replace")) if cf.exists() else None
            page_records.append({"url": BASE + pth, "sha256": sha})

        val = None if args.no_validate else validate_book(book, mad)
        val_summary = None
        if val:
            val_summary = {
                "madueke_key": val["madueke_key"],
                "overlap_chapters": val["overlap_chapters"],
                "verse_count_match": f"{val['verse_count_match_chapters']}/{val['verse_count_total_chapters']}",
                "folded_agreement": val["folded_agreement"],
                "chapter_bag_agreement": val["chapter_bag_agreement"],
            }
            # keep full chapter detail in a sidecar for auditing low-agreement books
            (SCRAPE_OUT / f"{book_key}.validation.json").write_text(
                json.dumps(val, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        manifest_books.append({
            "book": book_key,
            "slug": book["slug"],
            "testament": testament,
            "landing_path": book["landing_path"],
            "chapters": nch,
            "verses_total": nv,
            "has_argument": book["argument"] is not None,
            "pages": page_records,
            "madueke_validation": val_summary,
        })

    # aggregate agreement across validated books (mean over books that have a value)
    v_agrees = [b["madueke_validation"]["folded_agreement"] for b in manifest_books
                if b["madueke_validation"] and b["madueke_validation"]["folded_agreement"] is not None]
    c_agrees = [b["madueke_validation"]["chapter_bag_agreement"] for b in manifest_books
                if b["madueke_validation"] and b["madueke_validation"].get("chapter_bag_agreement") is not None]
    mean = lambda xs: round(sum(xs) / len(xs), 4) if xs else None

    manifest = {
        "scraped_on": date.today().isoformat(),
        "base_url": BASE,
        "user_agent": UA,
        "book_count": len(manifest_books),
        "validation_method": (
            "Verse-granularity comparison vs Madueke_A (modern-spelling, same edition). Both "
            "sides skeleton-folded (small-caps, long-s, ae/oe, u->v, i->j, y->i, vv->w, &->and, "
            "doubled-letter collapse, silent trailing -e) so archaic<->modern SPELLING does not "
            "count as a mismatch — only genuine WORDING differs. 'folded_agreement' is per-verse "
            "(penalized by versification differences); 'chapter_bag_agreement' is whole-chapter "
            "bag-of-words (versification-insensitive) — the gap between them isolates verse-"
            "boundary differences from text loss."
        ),
        "books": manifest_books,
        "totals": {
            "books": len(manifest_books),
            "chapters": totals["chapters"],
            "verses": totals["verses"],
            "validated_books": sum(1 for b in manifest_books if b["madueke_validation"]),
            "mean_folded_agreement": mean(v_agrees),
            "mean_chapter_bag_agreement": mean(c_agrees),
        },
    }
    # MERGE, NEVER REPLACE. `--books genesis` used to write a manifest containing genesis alone, deleting the
    # other 38 books' records outright; and with the Madueke_A source tree no longer on disk the validation
    # cannot be recomputed, so a re-scrape would also have erased the acquisition-time agreement figures — the
    # very figures (`verse_count_match: 37/50`) that recorded the truncation this run repairs. A record that a
    # later run cannot reproduce is still evidence: it is carried forward, marked with the date it was measured
    # and the reason it was not recomputed, never silently dropped and never silently presented as current.
    prior = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"books": []}
    prior_by_book = {b["book"]: b for b in prior.get("books", [])}
    for b in manifest_books:
        old = prior_by_book.get(b["book"], {})
        if not b["madueke_validation"] and old.get("madueke_validation"):
            b["madueke_validation"] = None
            b["madueke_validation_stale"] = {
                "measured_on": prior.get("scraped_on"),
                "not_recomputed_because": "the Madueke_A source tree is absent from scratch at this re-scrape",
                "superseded": "these figures describe the PREVIOUS scrape, not this one",
                **old["madueke_validation"],
            }
        elif old.get("madueke_validation_stale") and not b["madueke_validation"]:
            b["madueke_validation_stale"] = old["madueke_validation_stale"]
        prior_by_book[b["book"]] = b
    order = [b["book"] for b in prior.get("books", [])]
    order += [b["book"] for b in manifest_books if b["book"] not in order]
    manifest["books"] = [prior_by_book[k] for k in order]
    manifest["book_count"] = len(manifest["books"])
    manifest["books_rescraped"] = sorted(b["book"] for b in manifest_books)
    manifest["totals"]["books"] = len(manifest["books"])
    manifest["totals"]["chapters"] = sum(b["chapters"] for b in manifest["books"])
    manifest["totals"]["verses"] = sum(b["verses_total"] for b in manifest["books"])
    manifest["totals"]["validated_books"] = sum(1 for b in manifest["books"] if b.get("madueke_validation"))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n=== scrape complete ===", file=sys.stderr)
    print(f"books={len(manifest_books)} chapters={totals['chapters']} verses={totals['verses']}",
          file=sys.stderr)
    for b in manifest_books:
        v = b["madueke_validation"]
        vs = (f"agree={v['folded_agreement']} chbag={v['chapter_bag_agreement']} "
              f"vcount={v['verse_count_match']}" if v else "no-overlap")
        print(f"  {b['book']:<18} slug={str(b['slug']):<14} ch={b['chapters']:<3} "
              f"v={b['verses_total']:<5} {vs}", file=sys.stderr)
    print(f"mean folded={mean(v_agrees)} mean chapter-bag={mean(c_agrees)}", file=sys.stderr)
    print(f"manifest -> {MANIFEST}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
