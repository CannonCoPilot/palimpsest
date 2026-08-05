#!/usr/bin/env python3
"""apparatus_crossmap.py -- cross-source apparatus-section map (task 5).

Aligns apparatus / marginal content across witnesses, keyed by book/chapter/kind, so the
naming/edition drift between printings is visible and each apparatus unit's attestation is
recorded. Three evidence streams:

  1. madueke_b.apparatus_blocks -- 1334 structured {book,chapter,kind,text} TRANSCRIBED units
     (the clean backbone; kinds e.g. 'argument').
  2. SCAN MARGINALIA            -- region-typed marginal words per chapter, pulled from each
     source Stream's `margin_by_page` via the tome map's `chapter_pages` (which pages hold each
     chapter). Raw, ſ-preserved capture -- NOT skeleton-gridded.
  3. SKELETON apparatus slots   -- book arguments (apparatus/<book>/argument) + the 26
     reference_docs (frontmatter/backmatter) as the canonical slot vocabulary; frontmatter
     carriers are bounded region-level from the tome map's matter_regions.

odr_com apparatus is NOT in odr_com.json (that file is scripture-only); its notes live in the
raw originaldouayrheims.com scrape -> flagged as a follow-up ingestion, not included here.

Output: apparatus-cross-map.json
Run:  core/.venv/bin/python apparatus_crossmap.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import consensus_v2 as C  # noqa: E402  # type: ignore[import-not-found]  # harness streams
D = C.D                    # detect_our_ocr module (SKELETON, READS_DIR, margin geometry)

TOME_PATH = HERE / "tome-map.json"
OUT = HERE / "apparatus-cross-map.json"


def load_madueke_b() -> dict[tuple[str, int], list[dict]]:
    """(book, chapter) -> transcribed apparatus blocks."""
    p = D.READS_DIR / "madueke_b.json"
    idx: dict[tuple[str, int], list[dict]] = defaultdict(list)
    if not p.exists():
        return idx
    for blk in json.loads(p.read_text()).get("apparatus_blocks", []):
        book = blk.get("book", "")
        ch = blk.get("chapter")
        try:
            ch = int(ch)
        except (TypeError, ValueError):
            ch = 0
        idx[(book, ch)].append({
            "kind": blk.get("kind", ""),
            "chars": len(blk.get("text", "")),
            "text_head": blk.get("text", "")[:180],
        })
    return idx


def scan_marginalia(tome: dict, streams: dict) -> dict[tuple[str, int], dict]:
    """(book, chapter) -> {source: {n_words, sample}} from each source's region-typed margin
    capture, using the tome map's chapter_pages to know which pages carry the chapter."""
    out: dict[tuple[str, int], dict] = defaultdict(dict)
    for src, s in tome["sources"].items():
        st = streams.get(src)
        if st is None:
            continue
        for book, r in s.get("books", {}).items():
            for ch_str, pages in r.get("chapter_pages", {}).items():
                words: list[str] = []
                for pg in pages:
                    words.extend(st.margin_by_page.get(pg, []))
                if words:
                    out[(book, int(ch_str))][src] = {
                        "n_words": len(words),
                        "sample": " ".join(words[:24]),
                    }
    return out


def frontmatter_carriers(tome: dict) -> list[dict]:
    """Each skeleton reference_doc -> the sources whose tome-map matter region could carry it.
    Region-level only (exact page label = title-match follow-up)."""
    matter: dict[str, list[dict]] = defaultdict(list)
    for src, s in tome["sources"].items():
        for reg, pgs in s.get("matter_regions", {}).items():
            if pgs:
                matter[reg].append({"source": src, "n_pages": len(pgs),
                                    "page_span": [pgs[0], pgs[-1]]})
    # tome map merges the inter-testament gap as 'ot_back__nt_front'
    def carriers_for(region: str) -> list[dict]:
        got = list(matter.get(region, []))
        if region in ("ot_back", "nt_front"):
            got += matter.get("ot_back__nt_front", [])
        return got
    docs = []
    for rd in D.SKELETON.get("reference_docs", []):
        docs.append({
            "slot_id": rd.get("slot_id"), "name": rd.get("name"),
            "region": rd.get("region"), "position": rd.get("position"),
            "carrier_sources": carriers_for(rd.get("region", "")),
        })
    return docs


def build() -> dict:
    tome = json.loads(TOME_PATH.read_text())
    streams = C.load_all_streams()
    mad = load_madueke_b()
    scan = scan_marginalia(tome, streams)

    chapters: dict[str, dict] = defaultdict(dict)
    all_keys = sorted(set(mad) | set(scan))
    for (book, ch) in all_keys:
        transcribed = mad.get((book, ch), [])
        scans = scan.get((book, ch), {})
        chapters[book][str(ch)] = {
            "transcribed_madueke_b": transcribed,
            "n_transcribed": len(transcribed),
            "kinds": sorted({t["kind"] for t in transcribed}),
            "scan_marginal": scans,
            "n_scan_sources": len(scans),
            "cross_attested": bool(transcribed) and bool(scans),
        }

    # book-argument slots from the skeleton (apparatus/<book>/argument) matched to madueke_b args
    book_args = []
    for b in D.SKELETON.get("books", []):
        slug = b.get("slug", "")
        arg_id = b.get("argument_id")
        has_mad_arg = any(t["kind"] == "argument"
                          for ch in chapters.get(slug, {}).values()
                          for t in ch["transcribed_madueke_b"])
        book_args.append({"book": slug, "argument_id": arg_id,
                          "madueke_b_argument_present": has_mad_arg})

    n_cross = sum(1 for b in chapters.values() for c in b.values() if c["cross_attested"])
    n_scan_words = sum(v["n_words"] for k in scan for v in scan[k].values())
    return {
        "schema": "originaldr-apparatus-cross-map/v1",
        "note": ("apparatus units keyed book/chapter/kind. transcribed=madueke_b (1334 blocks); "
                 "scan_marginal=region-typed capture via tome-map chapter_pages. odr_com apparatus "
                 "= raw scrape follow-up (not in odr_com.json). frontmatter carriers region-level."),
        "totals": {
            "chapters_with_apparatus": sum(len(v) for v in chapters.values()),
            "chapters_cross_attested": n_cross,
            "transcribed_blocks": sum(len(v) for v in mad.values()),
            "scan_marginal_words": n_scan_words,
        },
        "book_arguments": book_args,
        "frontmatter_reference_docs": frontmatter_carriers(tome),
        "chapters": {b: chapters[b] for b in sorted(chapters)},
    }


def main() -> int:
    cm = build()
    OUT.write_text(json.dumps(cm, ensure_ascii=False, indent=2))
    t = cm["totals"]
    print(f"wrote {OUT}")
    print(f"chapters w/ apparatus : {t['chapters_with_apparatus']}")
    print(f"cross-attested (both) : {t['chapters_cross_attested']}")
    print(f"transcribed blocks    : {t['transcribed_blocks']}")
    print(f"scan marginal words   : {t['scan_marginal_words']}")
    print(f"reference_docs mapped : {len(cm['frontmatter_reference_docs'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
