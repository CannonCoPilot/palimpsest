#!/usr/bin/env python
"""Build the Original Douay-Rheims (1582 NT / 1609-1610 OT, Gregory Martin) Gold-Set text.

Source: the janvier-s/original-douay-rheims JSON dataset (CC0), cloned at
REPO/.scratch/original-douay-rheims. Each book is structured JSON (book_title,
intros, chapters[{chapter, summary, verses[{verse, text}]}]).

Because we GENERATE the reference text from structured data, we record every mask
element's exact char offset as we emit it — no fragile detection. The element model
mirrors the Challoner build (bible_structure.py): front_matter, volume, book,
introduction (book arguments), chapter_heading (book+chapter line + the chapter
summary/argument), chapter (verse body). Output:
  - imports/Scripture/Bibles/douay-rheims-original-1582-1610.txt   (the reference text)
  - core/tests/fixtures/gold/maps/work-108.map.json                (the masking map)

The generated text is normalization-stable (NFC, straight quotes, single spaces,
\\n\\n paragraphs), so Palimpsest's ingest reproduces it byte-for-byte and the
recorded offsets align (asserted via reference_sha256 at import time).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SRC = REPO / ".scratch/original-douay-rheims"
RAW = SRC / "bible/raw"
MAPS = HERE.parent / "maps"
OUT_TXT = REPO / "imports/Scripture/Bibles/douay-rheims-original-1582-1610.txt"
IDX = 108

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

_TAG = re.compile(r"</?(?:sc|i)>")            # keep content
_DROP = re.compile(r"<(?:cr|na|mn)>.*?</(?:cr|na|mn)>|<(?:cr|na|mn)/?>")  # drop marker tags
_WS = re.compile(r"[ \t]+")


def clean(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _DROP.sub("", s)
    s = _TAG.sub("", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = s.replace("\n", " ")
    return _WS.sub(" ", s).strip()


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


def book_title_line(meta: dict, slug: str) -> str:
    raw = (meta.get("book_title") or meta.get("short_title") or "").rstrip(", ")
    return clean(raw) or humanize(slug)


def build():
    B = Builder()

    # ---- front matter (OT title page + preface) ----
    fm_start = B.pos
    tp = json.loads((SRC / "reference/ot/title-page.json").read_text())
    pf = json.loads((SRC / "reference/ot/preface.json").read_text())
    tp_s = B.pos
    B.para(clean(tp["title"]))
    for p in tp["paragraphs"]:
        B.para(clean(p["text"]))
    B.add("title_page", tp_s, B.pos, label="Title Page")
    pf_s = B.pos
    B.para(clean(pf["title"]))
    for p in pf["paragraphs"]:
        B.para(clean(p["text"]))
    B.add("preface", pf_s, B.pos, label="Preface to the Reader")
    B.add("front_matter", fm_start, B.pos)

    def emit_book(slug: str, volume: str):
        meta = json.loads((RAW / f"{slug}.json").read_text())
        bk_start = B.pos
        short = clean(meta.get("short_title") or "") or humanize(slug)
        title_line = book_title_line(meta, slug)
        # book header
        hdr_s = B.pos
        B.para(title_line)
        # book introductions (arguments)
        for intro in meta.get("intros", []) or []:
            if intro.get("title"):
                B.para(clean(intro["title"]))
            if intro.get("text"):
                B.para(clean(intro["text"]))
        B.add("introduction", hdr_s, B.pos, label=title_line)
        # chapters
        for ch in meta["chapters"]:
            num = ch["chapter"]
            title = f"{short} Chapter {num}"
            cmeta = {"number": str(num), "name": title, "book": short, "volume": volume, "title": title}
            h_s = B.pos
            B.para(title)
            if ch.get("summary"):
                B.para(clean(ch["summary"]))
            B.add("chapter_heading", h_s, B.pos, label=title, meta=cmeta)
            body_s = B.pos
            for v in ch["verses"]:
                B.para(clean(v["text"]))
            B.add("chapter", body_s, B.pos, label=title, meta=cmeta)
        B.add("book", bk_start, B.pos, label=title_line)

    # ---- Old Testament ----
    ot_s = B.pos
    B.para("THE OLD TESTAMENT")
    B.add("header", ot_s, B.pos, label="The Old Testament")
    vol_ot_s = B.pos
    for slug in OT:
        emit_book(slug, "Old Testament")
    B.add("volume", vol_ot_s, B.pos, label="The Old Testament")

    # ---- New Testament ----
    nt_div_s = B.pos
    B.para("THE NEW TESTAMENT")
    B.add("header", nt_div_s, B.pos, label="The New Testament")
    vol_nt_s = B.pos
    for slug in NT:
        emit_book(slug, "New Testament")
    B.add("volume", vol_nt_s, B.pos, label="The New Testament")

    # ---- Apocrypha appendix ----
    apx_s = B.pos
    B.para("ADDITIONAL BOOKS")
    for slug in APOCRYPHA:
        emit_book(slug, "Additional Books")
    B.add("appendix", apx_s, B.pos, label="Additional Books")

    text = "".join(B.parts).rstrip()       # ingest normalize() trims trailing whitespace
    return text, B.els


def main():
    text, els = build()
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
        "generated_from": "mask_engine/gen_dr_original.py (janvier-s/original-douay-rheims JSON)",
        "applied": True, "extra_types": [], "mask_by_type": mask_by_type, "sections": sections,
    }
    MAPS.mkdir(parents=True, exist_ok=True)
    (MAPS / f"work-{IDX}.map.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"work-{IDX}.map.json: {len(sections)} elements, {len(types_present)} types, "
          f"{n} chars, sha {sha[:12]}")
    print("by type:", dict(per))


if __name__ == "__main__":
    import sys
    sys.exit(main())
