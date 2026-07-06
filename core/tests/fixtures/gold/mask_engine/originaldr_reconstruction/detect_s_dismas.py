#!/usr/bin/env python3
"""Phase 1 · P1.2 — s-dismas ARCHAIC Douay-Rheims detector (diplomatic witness).

Standalone companion to ``detect_sources.py`` (which we must NOT touch to avoid
races). Extracts the archaic diplomatic Douay-Rheims scripture out of the
``s-dismas`` PDF witness into per-verse read records aligned to the fixed
canonical skeleton, then validates the parse against the independent modern
Madueke_A witness using the archaic↔modern skeleton fold.

Pipeline per book PDF:
  1. pdftotext (plain, UTF-8) — clean archaic text, INLINE arabic verse numbers.
  2. Split into chapter blocks by "Chapter N" / "Psalme N" headings, deduped by a
     strictly-incrementing chapter counter (running page-headers repeat numbers).
     Single-chapter books (no heading) → one implicit chapter 1.
  3. Truncate each chapter block at its "Annotations" apparatus section.
  4. Drop the chapter *argument* (prose summary before the drop-cap capital).
  5. Strip page-number lines, repeated running-title/header lines, note anchors
     (♪), superscript markers (a) b)), and marginal cross-reference fragments
     (e.g. "Gen. 12. 22.", "1. Par. 2. 5.", "Eſa. 7, 14.").
  6. Segment the running chapter text on inline verse numbers using an
     increment heuristic (a verse number is a run-initial integer == expected k+1).

Archaic glyphs are PRESERVED EXACTLY in the stored surface (this is a diplomatic
witness): long-s ſ, æ/œ, u/v swaps, i/j swaps, vv, &, archaic spellings.

Reads → scratch (gitignored); validation summary → tracked JSON.

Run:  core/.venv/bin/python detect_s_dismas.py
      core/.venv/bin/python detect_s_dismas.py --book matthew      # single book
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # .../originaldr_reconstruction
MASK_ENGINE = HERE.parent                               # .../mask_engine
sys.path.insert(0, str(MASK_ENGINE))
sys.path.insert(0, str(MASK_ENGINE / "originaldr_validation"))

# skeleton fold (archaic print ↔ modern) reused from the validation harness
from ocr_sample import skel, raw_words  # type: ignore[import]  # noqa: E402

# repo root: HERE.parents = [0]mask_engine [1]gold [2]fixtures [3]tests
#            [4]core [5]<repo>
REPO = HERE.parents[5]
SRC = REPO / "core/.scratch/originaldr-project/sources/s-dismas"
READS_DIR = REPO / "core/.scratch/originaldr-project/reconstruction/reads"
OUT_READS = READS_DIR / "s_dismas.json"
OUT_VALID = HERE / "s-dismas-validation.json"
MADUEKE_READS = READS_DIR / "madueke_a.json"

SKELETON = json.loads((HERE / "skeleton.json").read_text())
_BOOK_CH = {b["slug"]: b["chapters"] for b in SKELETON["books"]}

# ------------------------------------------------------------------ #
# Book mapping: numeric filename prefix → canonical skeleton slug.
# s-dismas books are contiguous canonical DR order, mapped positionally,
# skipping 01-front-matter (apparatus) and 07-epistles-argument (NT apparatus).
# ------------------------------------------------------------------ #
NT_SLUGS = ["matthew", "mark", "luke", "john", "acts", "romans", "1-corinthians",
            "2-corinthians", "galatians", "ephesians", "philippians", "colossians",
            "1-thessalonians", "2-thessalonians", "1-timothy", "2-timothy", "titus",
            "philemon", "hebrews", "james", "1-peter", "2-peter", "1-john", "2-john",
            "3-john", "jude", "apocalypse"]
OT_SLUGS = ["genesis", "exodus", "leviticus", "numbers", "deuteronomy", "josue",
            "judges", "ruth", "1-kings", "2-kings", "3-kings", "4-kings",
            "1-paralipomenon", "2-paralipomenon", "1-esdras", "2-esdras", "tobias",
            "judith", "esther", "job", "psalms", "proverbs", "ecclesiastes",
            "canticle-of-canticles", "wisdom"]

# Books whose canonical chapter count is 1 → the PDF carries no "Chapter N" heading.
SINGLE_CHAPTER = {slug for slug, n in _BOOK_CH.items() if n == 1}


def book_files() -> list[tuple[str, Path]]:
    """Return [(slug, pdf_path)] in positional canonical order.

    NT files 02..29 map to NT_SLUGS but the NT dir also contains
    07-epistles-argument.pdf (pure apparatus) which must NOT consume a slug slot.
    We therefore map by *scripture* PDFs only, in filename order, skipping the two
    known apparatus PDFs (front-matter, epistles-argument).
    """
    APPARATUS = {"01-front-matter", "07-epistles-argument"}
    pairs: list[tuple[str, Path]] = []
    for testament, slugs in (("New-Testament", NT_SLUGS), ("Old-Testament", OT_SLUGS)):
        pdfs = sorted((SRC / testament).glob("*.pdf"), key=lambda p: int(p.stem.split("-")[0]))
        scripture = [p for p in pdfs if p.stem not in APPARATUS]
        if len(scripture) != len(slugs):
            raise SystemExit(
                f"{testament}: {len(scripture)} scripture PDFs != {len(slugs)} slugs\n"
                f"  files: {[p.name for p in scripture]}")
        pairs.extend(zip(slugs, scripture))
    return pairs


# ------------------------------------------------------------------ #
# Text extraction + cleaning
# ------------------------------------------------------------------ #
def pdftotext(path: Path) -> str:
    return subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(path), "-"],
        check=True, capture_output=True, text=True).stdout


CH_HEAD = re.compile(r"^(?:Chapter|Psalme|Psalm)\s+(\d+)\s*$")
ANNOT_HEAD = re.compile(r"^Annotations\b")

# A marginal cross-reference fragment: an abbreviated (Capitalised) book token
# followed by chapter/verse numbers — e.g. "Gen. 12. 22.", "1. Par. 2. 5.",
# "Eſa. 7, 14.", "Nu. 36.", "2. Re. 12. 24.", "Luc. 3. 31.", "1. Eſd. 3.".
# Abbrev book tokens are short Capitalised words (may carry a leading ordinal
# "1." / "2." / "3." / "4.") ending in a period, followed by run(s) of digits
# separated by ". " or ", ".
_ABBR = (r"(?:[1-4]\.\s*)?"                      # optional ordinal prefix
         r"[A-ZÆŒ][A-Za-zſæœ]{1,6}\.")           # Capitalised abbrev + dot
_NUMS = r"(?:\s*\d+\s*[.,])+"                    # one-or-more "N." / "N," groups
XREF = re.compile(_ABBR + _NUMS)
# A trailing bare "N. NN." xref continuation (no book token), e.g. "4. 18." "25. 29. 38."
XREF_CONT = re.compile(r"(?<![A-Za-z])(?:\d+\s*[.,]\s*){2,}(?=\s|$)")

NOTE_ANCHOR = re.compile(r"[♪†‡*∷·•◊✝☩]")
SUP_MARKER = re.compile(r"(?<![A-Za-z])[a-z]\)")   # superscript note markers a) b) c)
PAGENUM = re.compile(r"^\s*\d{1,4}\s*$")           # standalone page-number line

# Page-bottom footnote block: a line starting with a bare note letter + space +
# a capital/long-s word — e.g. "a This word Iuſt, ...", "b Chriſt ſignifieth ...".
FOOTNOTE_MARK = re.compile(r"^[a-z] [A-ZſÆŒ]")
VERSE_LINE = re.compile(r"^(\d+) [A-Za-zſÆŒ]")       # a scripture line resuming at a verse number


def strip_page_footnotes(page: str) -> str:
    """Remove ONLY the page-bottom footnote block that pdftotext dumps after the
    scripture body. Footnotes sit at the BOTTOM of a print page, so we identify the
    maximal TRAILING region that (a) begins at a footnote-marker line and (b)
    contains no resuming verse-number line and no drop-cap capital — i.e. it is pure
    apparatus down to the page's end — and cut only that. Anything above it
    (scripture, incl. verses that happen to precede the footnote) is preserved.
    This is per-page; it never touches the chapter's separate 'Annotations'
    apparatus (handled by chapter truncation)."""
    lines = page.split("\n")
    # locate the earliest footnote-marker line whose entire remainder to page-end is
    # apparatus (no verse line, no drop-cap) — that marks the page-bottom block.
    for i, ln in enumerate(lines):
        if not FOOTNOTE_MARK.match(ln.strip()):
            continue
        rest = lines[i + 1:]
        if any(VERSE_LINE.match(r.strip()) for r in rest):
            continue                              # scripture resumes → not page-bottom
        if any(len(r.strip()) == 1 and r.strip().isalpha() and r.strip().isupper()
               for r in rest):
            continue                              # a drop-cap follows → not page-bottom
        return "\n".join(lines[:i])
    return page


def running_header_lines(lines: list[str]) -> set[str]:
    """Lines repeated ≥3× that look like running titles/headers (not scripture)."""
    freq = Counter(l.strip() for l in lines if l.strip())
    hdrs = set()
    for text, n in freq.items():
        if n < 3:
            continue
        # scripture prose is not repeated verbatim ≥3×; running headers are short
        # title lines (book title / running head). Keep only header-ish lines:
        if len(text) <= 60 and re.search(r"[A-Za-z]", text) and not text[0].islower():
            # avoid nuking a genuine short repeated verse: require no inline
            # verse-number pattern and title-case-ish content
            hdrs.add(text)
    return hdrs


def strip_apparatus(text: str) -> str:
    """Strip note anchors, superscript markers, and marginal cross-ref fragments
    from a chapter's running scripture text. Preserve archaic glyphs otherwise."""
    text = NOTE_ANCHOR.sub(" ", text)
    text = SUP_MARKER.sub(" ", text)
    text = XREF.sub(" ", text)
    text = XREF_CONT.sub(" ", text)
    # collapse whitespace introduced by removals
    return re.sub(r"\s+", " ", text).strip()


def dropcap_index(lines: list[str]) -> int:
    """Index of the drop-cap capital line that starts verse 1 within a chapter
    block (single uppercase letter alone on a line). Returns -1 if none found."""
    for i, ln in enumerate(lines):
        s = ln.strip()
        if len(s) == 1 and s.isalpha() and s.isupper():
            return i
    return -1


def chapter_blocks(raw: str, slug: str) -> list[tuple[int, str]]:
    """Split raw pdftotext into (chapter_number, scripture_text) blocks.

    Strategy: walk lines tracking a chapter counter. A "Chapter N"/"Psalme N"
    heading opens a new chapter when N > cur AND it is CONFIRMED as a real heading
    (a drop-cap capital or a run of verse numbers follows it within a window,
    before the next heading/Annotations). Running-header repeats (N <= cur) and
    premature future-chapter headers inside an Annotations block (no drop-cap
    follows) are ignored. Gaps are tolerated (a MISSING heading — e.g. Genesis 26
    whose heading didn't survive extraction — just merges into the prior chapter
    rather than stalling the whole book). Scripture runs to the next confirmed
    heading; the chapter argument before the drop-cap is dropped downstream.
    """
    lines = raw.split("\n")
    hdrs = running_header_lines(lines)

    # positions of candidate headings
    cand = [(i, int(m.group(1)))
            for i in range(len(lines))
            if (m := CH_HEAD.match(lines[i].strip()))]

    def confirmed(idx: int, n: int) -> bool:
        """A candidate heading is real (not a page-top running header) iff a drop-cap
        capital — the decorated verse-1 initial — appears before the first inline
        verse number and before the next DIFFERENT heading / Annotations (window ≤80).

        A running header "Chapter N" printed at a page top sits ABOVE *continuing*
        scripture, so the next verse number after it is mid-sequence (e.g. 10) with
        NO intervening drop-cap; those are rejected. As a fallback, if the first
        verse number encountered is small (<=2), accept (some verse-1 initials may
        not survive extraction as a lone capital line).

        NB: a running header repeating the SAME chapter number often sits between
        the real heading and the drop-cap (page break inside the argument); such
        same-number headers must NOT terminate the scan (else the real heading is
        wrongly rejected and its whole chapter is lost — e.g. Luke 6, Acts 25)."""
        for j in range(idx + 1, min(idx + 80, len(lines))):
            s = lines[j].strip()
            mh = CH_HEAD.match(s)
            if mh:
                if int(mh.group(1)) == n:
                    continue                       # same-chapter running header → skip
                break                              # a different chapter heading → stop
            if ANNOT_HEAD.match(s):
                break
            if len(s) == 1 and s.isalpha() and s.isupper():
                return True                        # drop-cap → real heading
            mv = VERSE_LINE.match(s)
            if mv:
                # first inline verse number before any drop-cap:
                return int(mv.group(1)) <= 2
        return False

    single = slug in SINGLE_CHAPTER
    boundaries: list[tuple[int, int]] = []  # (line_index, chapter_number)
    cur = 0
    for i, n in cand:
        if n > cur and confirmed(i, n):
            boundaries.append((i, n))
            cur = n
        # else: running-header repeat, out-of-order, or unconfirmed → ignore
    if not boundaries:
        # single-chapter book (philemon, jude, 2-john, 3-john, abdias, ...):
        # whole file is chapter 1 scripture (still trimmed at Annotations + argument).
        boundaries = [(0, 1)]

    blocks: list[tuple[int, str]] = []
    for bi, (start, chnum) in enumerate(boundaries):
        end = boundaries[bi + 1][0] if bi + 1 < len(boundaries) else len(lines)
        seg = lines[start + (0 if single and start == 0 else 1):end]

        # truncate at first Annotations apparatus section
        for j, ln in enumerate(seg):
            if ANNOT_HEAD.match(ln.strip()):
                seg = seg[:j]
                break

        # drop the chapter argument: keep from the drop-cap capital onward.
        dc = dropcap_index(seg)
        if dc >= 0:
            # reconstruct verse-1 first word: dropcap letter + continuation.
            # The dropcap capital sits on its own line; the true continuation line
            # begins lowercase (the rest of the word). A running-header "Chapter N"
            # / page-number line frequently intervenes between the dropcap and the
            # continuation (pdftotext page break) — skip those so we don't glue
            # "A" + "Chapter 10" + "nd riſing..." into "AChapter 10 nd riſing".
            cap = seg[dc].strip()
            rest = seg[dc + 1:]
            k = 0
            while k < len(rest):
                s = rest[k].strip()
                if not s or PAGENUM.match(s) or CH_HEAD.match(s) or s in hdrs:
                    rest[k] = ""            # blank out intervening noise line
                    k += 1
                    continue
                break
            if k < len(rest):
                rest[k] = cap + rest[k].lstrip()
                seg = rest
            else:
                seg = [cap] + rest
        # else: no drop-cap detected → keep whole seg (verse-1 may lack a dropcap)

        # line-level cleaning: drop page numbers + running headers
        kept = []
        for ln in seg:
            s = ln.strip()
            if not s:
                continue
            if PAGENUM.match(s):
                continue
            if s in hdrs:
                continue
            if CH_HEAD.match(s):               # stray running "Chapter N" header
                continue
            kept.append(s)

        body = strip_apparatus(" ".join(kept))
        blocks.append((chnum, body))
    return blocks


# ------------------------------------------------------------------ #
# Verse segmentation
# ------------------------------------------------------------------ #


def segment_verses(body: str) -> dict[int, str]:
    """Split a chapter's running text into {verse_number: surface}.

    A verse number is a whitespace-delimited token that is a bare integer equal to
    the expected next verse (k+1). Verse 1 typically has no leading "1" (it is the
    text before the first "2"), so we seed expected=2 and assign the leading text
    to verse 1. Integers that don't match the expected increment are treated as
    ordinary text (stray page numbers, surviving citation digits) and kept inline
    — but a bare integer that equals expected is a verse boundary.
    """
    tokens = body.split()
    verses: dict[int, list[str]] = {}
    cur_v = 1
    expected = 2
    verses[1] = []
    for tok in tokens:
        if tok.isdigit():
            n = int(tok)
            if n == expected:
                cur_v = n
                expected = n + 1
                verses[cur_v] = []
                continue
            # allow a small forward skip (rare mis-drop of a verse) — accept the
            # next integer only if it is expected+1 or expected+2 AND > cur_v,
            # so we resync rather than swallow a whole verse into the prior one.
            if expected < n <= expected + 2 and n > cur_v:
                cur_v = n
                expected = n + 1
                verses[cur_v] = []
                continue
        verses.setdefault(cur_v, []).append(tok)
    out = {v: " ".join(ws).strip() for v, ws in verses.items()}
    # drop an empty leading verse-1 (chapter that genuinely started at a printed "1")
    if out.get(1, "") == "":
        del out[1]
    return out


# ------------------------------------------------------------------ #
# Read records + coverage
# ------------------------------------------------------------------ #
def read_record(skid, surface, locus, conf, evidence):
    return {"skeleton_id": skid, "present": True, "surface": surface,
            "spelling": "archaic", "locus": locus, "method": "pdftotext-parse",
            "local_confidence": conf, "evidence_ptr": evidence}


def detect_book(slug: str, pdf: Path) -> tuple[list[dict], list[str]]:
    raw = pdftotext(pdf)
    # strip page-bottom footnote blocks per print page (form-feed delimited) before
    # chapter splitting, so mid-chapter footnotes don't leak into verse text.
    raw = "\n".join(strip_page_footnotes(pg) for pg in raw.split("\f"))
    reads: list[dict] = []
    warnings: list[str] = []
    for chnum, body in chapter_blocks(raw, slug):
        if not body:
            warnings.append(f"{slug} ch{chnum}: empty body")
            continue
        verses = segment_verses(body)
        if not verses:
            warnings.append(f"{slug} ch{chnum}: no verses segmented")
            continue
        # confidence: high if verse numbering is dense & contiguous from 1..max
        vnums = sorted(verses)
        contiguous = vnums == list(range(vnums[0], vnums[-1] + 1))
        conf = "high" if (contiguous and vnums[0] == 1) else "moderate"
        for v in vnums:
            surf = verses[v]
            if not surf:
                continue
            skid = f"scripture/{slug}/{chnum}/{v}"
            reads.append(read_record(
                skid, surf, f"s-dismas {pdf.name} Chapter {chnum}", conf,
                f"s_dismas:{slug}:{chnum}:{v}"))
    return reads, warnings


def coverage(reads: list[dict]) -> dict:
    chapters, verses, out_of_grid = set(), 0, []
    books = set()
    for r in reads:
        parts = r["skeleton_id"].split("/")
        if len(parts) != 4 or parts[0] != "scripture":
            continue
        _, book, ch, _ = parts
        verses += 1
        books.add(book)
        chapters.add((book, int(ch)))
        maxch = _BOOK_CH.get(book)
        if maxch is None or int(ch) > maxch:
            out_of_grid.append(r["skeleton_id"])
    return {"books": len(books), "chapters": len(chapters), "verses": verses,
            "out_of_grid": out_of_grid[:20], "out_of_grid_count": len(out_of_grid)}


# ------------------------------------------------------------------ #
# Validation vs Madueke_A (folded token agreement)
# ------------------------------------------------------------------ #
# The reused raw_words() tokenizer ([A-Za-zÆæŒœ]+) does NOT treat long-s ſ (U+017F)
# as a letter, so archaic words fragment ("Iſrael" -> "I","rael"; "leaſt" -> "lea","t").
# For the COMPARISON ONLY we pre-fold archaic glyphs to ASCII so tokenisation is
# correct; the stored diplomatic surface keeps ſ untouched. We also join line-break
# hyphenation ("Beth- lehem" -> "Bethlehem") which pdftotext leaves in the flow.
_ARCHAIC_TO_ASCII = str.maketrans({"ſ": "s", "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
                                   "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"})
_HYPHEN_BREAK = re.compile(r"(\w)-\s+(\w)")


def _prefold(text: str) -> str:
    text = text.translate(_ARCHAIC_TO_ASCII)
    return _HYPHEN_BREAK.sub(r"\1\2", text)


def fold_tokens(text: str) -> list[str]:
    return [s for s in (skel(t) for t in raw_words(_prefold(text))) if len(s) >= 1]


def token_agreement(a: str, b: str) -> tuple[int, int]:
    """Multiset token overlap after skeleton fold. Returns (matched, denom)
    where denom is max(len_a, len_b) — penalises both drops and leakage."""
    ta, tb = Counter(fold_tokens(a)), Counter(fold_tokens(b))
    inter = sum((ta & tb).values())
    denom = max(sum(ta.values()), sum(tb.values())) or 1
    return inter, denom


_SHIFT = (-3, -2, -1, 1, 2, 3)


def validate(reads: list[dict]) -> dict:
    """Compare s-dismas verses to Madueke_A modern reads via skeleton fold.

    Two agreement views are reported per book + aggregate:
      * folded_agreement       — STRICT per-verse (same skeleton_id) token overlap.
      * folded_agreement_shift  — best token overlap over Madueke verses within ±3
                                  of the verse number. This absorbs EDITION
                                  VERSIFICATION OFFSETS (s-dismas numbers a passage
                                  differently than Madueke), isolating true wording
                                  fidelity from index-shift artefacts. A large
                                  strict→shift gap means "correct wording, different
                                  versification" (an edition property faithfully
                                  captured), NOT a parse error.
    """
    mad = json.loads(MADUEKE_READS.read_text())
    mad_surface = {r["skeleton_id"]: r["surface"] for r in mad["reads"]}
    ours = {r["skeleton_id"]: r["surface"] for r in reads}

    def best_shift(skid: str, surf: str) -> tuple[int, int]:
        slug, ch, v = skid.split("/")[1], skid.split("/")[2], int(skid.split("/")[3])
        best = token_agreement(surf, mad_surface.get(skid, "")) if skid in mad_surface \
            else (0, len(fold_tokens(surf)) or 1)
        best_frac = best[0] / best[1] if best[1] else 0.0
        for dv in _SHIFT:
            kk = f"scripture/{slug}/{ch}/{v + dv}"
            if kk in mad_surface:
                m, d = token_agreement(surf, mad_surface[kk])
                if d and m / d > best_frac:
                    best, best_frac = (m, d), m / d
        return best

    per_book: dict[str, dict] = {}
    for skid, surf in ours.items():
        slug = skid.split("/")[1]
        pb = per_book.setdefault(slug, {
            "book": slug, "our_verses": 0, "mad_verses": 0, "aligned_verses": 0,
            "matched_tok": 0, "denom_tok": 0, "matched_tok_shift": 0, "denom_tok_shift": 0})
        pb["our_verses"] += 1
        if skid in mad_surface:
            pb["aligned_verses"] += 1
            m, d = token_agreement(surf, mad_surface[skid])
            pb["matched_tok"] += m; pb["denom_tok"] += d
            ms, ds = best_shift(skid, surf)
            pb["matched_tok_shift"] += ms; pb["denom_tok_shift"] += ds
    for skid in mad_surface:
        slug = skid.split("/")[1]
        if slug in per_book:
            per_book[slug]["mad_verses"] += 1

    books_out = []
    agg = Counter()
    for slug, pb in sorted(per_book.items(), key=lambda kv: list(_BOOK_CH).index(kv[0])):
        agree = round(pb["matched_tok"] / pb["denom_tok"], 4) if pb["denom_tok"] else 0.0
        agree_s = round(pb["matched_tok_shift"] / pb["denom_tok_shift"], 4) \
            if pb["denom_tok_shift"] else 0.0
        vc_ratio = round(pb["our_verses"] / pb["mad_verses"], 4) if pb["mad_verses"] else None
        rec = {**pb, "folded_agreement": agree, "folded_agreement_shift": agree_s,
               "verse_count_ratio_vs_madueke": vc_ratio}
        books_out.append(rec)
        for k in ("matched_tok", "denom_tok", "matched_tok_shift", "denom_tok_shift",
                  "our_verses", "mad_verses", "aligned_verses"):
            agg[k] += pb[k]

    aggregate = {
        "books": len(per_book),
        "our_verses": agg["our_verses"],
        "madueke_verses_same_books": agg["mad_verses"],
        "aligned_verses": agg["aligned_verses"],
        "folded_agreement": round(agg["matched_tok"] / agg["denom_tok"], 4)
        if agg["denom_tok"] else 0.0,
        "folded_agreement_shift": round(agg["matched_tok_shift"] / agg["denom_tok_shift"], 4)
        if agg["denom_tok_shift"] else 0.0,
        "verse_count_ratio_vs_madueke": round(agg["our_verses"] / agg["mad_verses"], 4)
        if agg["mad_verses"] else None,
    }
    # flag a book only if it is low even AFTER absorbing versification offsets
    # (shift agreement) OR its verse count diverges materially — those are the
    # genuine parse-quality concerns, distinct from mere index shifts.
    low = [b for b in books_out if b["folded_agreement_shift"] < 0.85 or
           (b["verse_count_ratio_vs_madueke"] or 1) < 0.85 or
           (b["verse_count_ratio_vs_madueke"] or 1) > 1.15]
    worst = min(books_out, key=lambda b: b["folded_agreement"]) if books_out else None
    worst_s = min(books_out, key=lambda b: b["folded_agreement_shift"]) if books_out else None
    return {
        "witness": "s-dismas (archaic diplomatic Douay-Rheims)",
        "modern_reference": "madueke_a",
        "method": {
            "fold": "skeleton fold (ocr_sample.skel): long-s/u-v/i-j/vv-w/ligature/"
                    "silent-e/doubled-letter; archaic glyphs pre-normalised to ASCII "
                    "for tokenisation only (stored surface keeps ſ, æ, u/v, i/j, &).",
            "folded_agreement": "STRICT per-verse token multiset overlap, denom=max(len_a,len_b).",
            "folded_agreement_shift": "best overlap over Madueke verses within ±3 of the "
                                      "verse number — absorbs edition versification offsets.",
        },
        "target_folded_agreement": 0.88,
        "aggregate": aggregate,
        "worst_book_strict": {"book": worst["book"], "folded_agreement": worst["folded_agreement"],
                              "folded_agreement_shift": worst["folded_agreement_shift"]}
        if worst else None,
        "worst_book_shift": {"book": worst_s["book"],
                             "folded_agreement_shift": worst_s["folded_agreement_shift"]}
        if worst_s else None,
        "flagged_books": [{"book": b["book"], "folded_agreement": b["folded_agreement"],
                           "folded_agreement_shift": b["folded_agreement_shift"],
                           "verse_count_ratio_vs_madueke": b["verse_count_ratio_vs_madueke"],
                           "our_verses": b["our_verses"], "madueke_verses": b["mad_verses"]}
                          for b in low],
        "per_book": books_out,
    }


# ------------------------------------------------------------------ #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="restrict to a single slug (debug)")
    ap.add_argument("--no-validate", action="store_true")
    args = ap.parse_args()

    READS_DIR.mkdir(parents=True, exist_ok=True)
    pairs = book_files()
    if args.book:
        pairs = [(s, p) for s, p in pairs if s == args.book]
        if not pairs:
            raise SystemExit(f"no such book slug: {args.book}")

    all_reads: list[dict] = []
    all_warn: list[str] = []
    missing_chapters: dict[str, list[int]] = {}
    for slug, pdf in pairs:
        reads, warn = detect_book(slug, pdf)
        all_reads.extend(reads)
        all_warn.extend(warn)
        got = {int(r["skeleton_id"].split("/")[2]) for r in reads}
        # only meaningful for multi-chapter books whose full chapter run is expected
        exp = _BOOK_CH.get(slug, 0)
        miss = [c for c in range(1, exp + 1) if c not in got]
        if miss:
            missing_chapters[slug] = miss
            all_warn.append(f"{slug}: chapter(s) {miss} not segmented "
                            f"(heading absent/scrambled in extraction → merged into neighbour)")
        print(f"{slug:22s} {pdf.name:26s} {len(reads):5d} verses · {len(got):3d} chapters"
              + (f"  ⚠ missing ch {miss}" if miss else ""))

    cov = coverage(all_reads)
    cov["missing_chapters"] = missing_chapters
    out = {"source": "s_dismas", "lineage": "s-dismas", "independent": True,
           "spelling": "archaic", "count": len(all_reads), "coverage": cov,
           "reads": all_reads}
    OUT_READS.write_text(json.dumps(out, ensure_ascii=False))
    print(f"\nreads → {OUT_READS.relative_to(REPO)}  "
          f"({cov['books']} books · {cov['chapters']} chapters · {cov['verses']} verses"
          + (f" · ⚠ {cov['out_of_grid_count']} out-of-grid" if cov['out_of_grid_count'] else "")
          + ")")
    if all_warn:
        print(f"warnings ({len(all_warn)}): " + "; ".join(all_warn[:10])
              + (" ..." if len(all_warn) > 10 else ""))

    if not args.no_validate:
        val = validate(all_reads)
        val["parse_warnings"] = all_warn
        val["coverage"] = cov
        OUT_VALID.write_text(json.dumps(val, ensure_ascii=False, indent=2) + "\n")
        a = val["aggregate"]
        print(f"\nvalidation vs madueke_a: folded_agreement={a['folded_agreement']} "
              f"(strict) · {a['folded_agreement_shift']} (±3-shift, versification-tolerant) "
              f"· target 0.88")
        print(f"  aligned {a['aligned_verses']}/{a['our_verses']} verses "
              f"· vc_ratio {a['verse_count_ratio_vs_madueke']}")
        if val["worst_book_strict"]:
            w = val["worst_book_strict"]
            print(f"  worst strict: {w['book']} ({w['folded_agreement']}; "
                  f"shift {w['folded_agreement_shift']})")
        if val["flagged_books"]:
            print(f"  flagged ({len(val['flagged_books'])}): "
                  + ", ".join(f"{b['book']}={b['folded_agreement']}/{b['folded_agreement_shift']}"
                              for b in val["flagged_books"][:12]))
        else:
            print("  no books flagged (all pass shift-tolerant + verse-count gates)")
        print(f"validation → {OUT_VALID.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
