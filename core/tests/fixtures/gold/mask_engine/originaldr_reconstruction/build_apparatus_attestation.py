#!/usr/bin/env python3
"""Phase 1 · P1.5 — apparatus inclusion/exclusion & contributor matrix.

For EVERY apparatus item — the 26 front/back-matter reference docs AND every book's apparatus
channels — record, transparently and per source, whether the item is present, the scan-grounded
placement, and the consensus include/exclude decision with a rationale (plan §4.5). Apparatus
contributors are ALL document sources, not one; this is the evidence base for "why is this
apparatus here / why is it omitted", and the input to the §5/§7 contributor heatmaps.

The five contributing sources and the granularity at which each can honestly attest apparatus:

  sabates_a   (modern)   element-level. The apparatus backbone: supplies all 26 reference docs
                         (reference/{ot,nt}/<name>.json) and every book channel (book_argument
                         <- intros; chapter_argument <- summary; verse_footnotes <- verse notes;
                         cross_refs <- verse cross_refs; sidecar_notes <- annotations sidecar).
  odr_com     (archaic)  book/chapter-level, for the 39 scraped books: book_argument, per-chapter
                         chapter_argument, and per-chapter notes (a sidecar/annotation channel).
  s_dismas    (archaic)  book-level: the archaic-diplomatic PDFs carry each book's argument +
                         front matter (OT genesis->wisdom, all NT, + a front-matter fascicle).
  madueke_b   (modern)   aggregate corroboration only (the column-flattened pdftotext dump is not
                         reliably sliceable per chapter): ANNOTATIONS / ARGUMENT block counts +
                         the appendix headers. Reused from the committed apparatus-gapfill.json.
  archive_org (archaic)  the scan authority: reference-doc placement (grounded / co-located /
                         unlocatable / inventoried) from layout-map.json, and the book-level
                         physical fact that the printed apparatus stands in the scanned tome.

Sources are read from the gitignored scratch corpora (like the other detect_*.py builders); the
emitted apparatus-attestation.json is committed. Deterministic: same corpora -> same output.

Run:  core/.venv/bin/python build_apparatus_attestation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))  # R9.6: sibling import
import project_root as pr  # noqa: E402  R9.6: one derived root

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
RAW = REPO / ".scratch/original-douay-rheims/bible/raw"
ANNOT = REPO / ".scratch/original-douay-rheims/annotations"
REFERENCE = REPO / ".scratch/original-douay-rheims/reference"
ODR = pr.ODR_SCRAPE
SDISMAS = pr.S_DISMAS
SKELETON = HERE / "skeleton.json"
LAYOUT_MAP = HERE / "layout-map.json"
GAPFILL = HERE.parent / "originaldr_validation" / "apparatus-gapfill.json"
OUT = HERE / "apparatus-attestation.json"

CHANNELS = ["book_argument", "chapter_argument", "verse_footnotes", "cross_refs", "sidecar_notes"]
SPURIOUS_LEADING = {"tobias"}                       # source ch0 is a dropped fragment

SOURCES = [
    {"id": "sabates_a", "lineage": "janvier/madueke", "spelling": "modern", "independent": False,
     "role": "apparatus backbone — 26 reference docs + all book channels", "granularity": "element"},
    {"id": "odr_com", "lineage": "originaldouayrheims.com", "spelling": "archaic",
     "independent": True, "role": "book/chapter arguments + annotations (39 scraped books)",
     "granularity": "book/chapter"},
    {"id": "s_dismas", "lineage": "s-dismas", "spelling": "archaic", "independent": True,
     "role": "archaic-diplomatic book arguments + front matter (OT genesis->wisdom, all NT)",
     "granularity": "book"},
    {"id": "madueke_b", "lineage": "madueke", "spelling": "modern", "independent": False,
     "role": "aggregate corroboration (annotation/argument blocks + appendix)",
     "granularity": "aggregate"},
    {"id": "archive_org", "lineage": "archive.org scans", "spelling": "archaic",
     "independent": True, "role": "scan placement authority + physical apparatus presence",
     "granularity": "placement/book"},
]

# s-dismas covers OT ordinals 1..25 (genesis..wisdom) and every NT book (47..73); the OT tail
# (ecclesiasticus + the prophets + Machabees) and the appendix are absent from its PDF set.
SDISMAS_ORDINALS = set(range(1, 26)) | set(range(47, 74))
# reference-doc name -> a distinctive header substring for the madueke_b full-dump search.
MADB_REF_HEADERS = {
    "explication-words": "EXPLICATION", "table-corruptions": "HERETICAL",
    "table-catholic-truths": "CATHOLIKE", "apostles-creed": "APOSTLES CREED",
}


def _nonempty_json(p: Path) -> Optional[dict]:
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    return d if d else None


# --- sabates: reference docs + per-book channel coverage ------------------------------------- #
def sabates_reference(testament: str, name: str) -> dict[str, Any]:
    p = REFERENCE / testament.lower() / f"{name}.json"
    d = _nonempty_json(p)
    if d is None:
        return {"present": False, "granularity": "element",
                "note": f"no reference/{testament.lower()}/{name}.json"}
    paras = d.get("paragraphs") or []
    return {"present": True, "granularity": "element",
            "evidence": {"file": str(p.relative_to(REPO)), "section": d.get("section"),
                         "title": (d.get("title") or "")[:120], "paragraphs": len(paras)}}


def sabates_book_channels(slug: str) -> Optional[dict[str, Any]]:
    d = _nonempty_json(RAW / f"{slug}.json")
    if d is None:
        return None
    chapters = [c for c in d["chapters"]
                if _int_ok(c.get("chapter")) and not (slug in SPURIOUS_LEADING and _as_int(c["chapter"]) == 0)]
    n = len(chapters)
    hits = {ch: 0 for ch in CHANNELS}
    hits["book_argument"] = 1 if (d.get("intros")) else 0     # book-level: present/absent
    for c in chapters:
        if c.get("summary"):
            hits["chapter_argument"] += 1
        vn = sum((1 if v.get("has_annotation") else 0) + len(v.get("notes") or []) for v in c["verses"])
        cr = sum(len(v.get("cross_refs") or []) for v in c["verses"])
        if vn:
            hits["verse_footnotes"] += 1
        if cr:
            hits["cross_refs"] += 1
        chi = _as_int(c["chapter"])
        ap = ANNOT / slug / f"{chi:03d}.json"
        if ap.exists() and (json.loads(ap.read_text()).get("annotations") or []):
            hits["sidecar_notes"] += 1
    out: dict[str, Any] = {"chapters": n}
    for ch in CHANNELS:
        if ch == "book_argument":
            out[ch] = {"present": bool(hits[ch]), "granularity": "book"}
        else:
            out[ch] = {"present": hits[ch] > 0, "chapters_with": hits[ch],
                       "pct": round(100 * hits[ch] / n, 2) if n else 0.0, "granularity": "chapter"}
    return out


# --- odr-com: book/chapter arguments + per-chapter notes ------------------------------------- #
def odr_book_channels(slug: str) -> Optional[dict[str, Any]]:
    d = _nonempty_json(ODR / f"{slug}.json")
    if d is None:
        return None
    chapters = d.get("chapters") or []
    n = len(chapters)
    ch_arg = sum(1 for c in chapters if c.get("argument"))
    ch_notes = sum(1 for c in chapters if c.get("notes"))
    return {
        "chapters": n,
        "book_argument": {"present": bool(d.get("argument")), "granularity": "book"},
        "chapter_argument": {"present": ch_arg > 0, "chapters_with": ch_arg,
                             "pct": round(100 * ch_arg / n, 2) if n else 0.0, "granularity": "chapter"},
        "sidecar_notes": {"present": ch_notes > 0, "chapters_with": ch_notes,
                          "pct": round(100 * ch_notes / n, 2) if n else 0.0, "granularity": "chapter"},
    }


def _int_ok(v: Any) -> bool:
    try:
        int(v)
        return True
    except (TypeError, ValueError):
        return False


def _as_int(v: Any) -> int:
    return int(v)


# --- layout-map placement lookup ------------------------------------------------------------ #
def placement_index(layout: dict) -> dict[tuple[str, str], dict[str, Any]]:
    idx: dict[tuple[str, str], dict[str, Any]] = {}
    for pl in layout["apparatus_placements"]:
        ref = pl["apparatus_order_ref"]
        idx[(ref["section"], ref["name"])] = pl
    return idx


def madueke_aggregate() -> dict[str, Any]:
    d = _nonempty_json(GAPFILL) or {}
    mb = d.get("madueke_b_corroboration", {})
    return {
        "annotation_blocks": mb.get("annotations_blocks"),
        "argument_blocks": mb.get("argument_blocks"),
        "appendix_corroboration": mb.get("appendix_corroboration", {}),
        "sha256": mb.get("sha256"),
        "note": "column-flattened full dump; corroborates apparatus presence in aggregate, not "
                "reliably sliceable per chapter (see apparatus-gapfill.json).",
    }


def madb_text() -> str:
    p = pr.MADUEKE_B_RAW_INTERLEAVED
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def build_reference_docs(skeleton: dict, placements: dict, madb: str) -> tuple[list[dict], dict]:
    out: list[dict] = []
    counts = {"include": 0, "exclude": 0}
    for rd in skeleton["reference_docs"]:
        section, name, testament = rd["region"], rd["name"], rd["testament"]
        pl = placements.get((section, name))
        status = pl["status"] if pl else "inventoried"
        sab = sabates_reference(testament, name)
        arch = {"present": status in ("grounded", "co-located"), "status": status,
                "page": (pl.get("source") or {}).get("page") if pl else None,
                "crop": pl.get("crop_image") if pl else None,
                "identifying_text": pl.get("identifying_text") if pl else None}
        mad_hdr = MADB_REF_HEADERS.get(name)
        madv: dict[str, Any] = {"granularity": "aggregate"}
        if mad_hdr and madb:
            madv["present"] = mad_hdr in madb
            madv["evidence"] = f"header substring '{mad_hdr}' in merged.txt"
        else:
            madv["present"] = None
            madv["note"] = "not separately searched in the column-flattened dump"
        # decision: keep if the scan places it OR sabates attests it; drop when the scan proves
        # it absent from this testament (unlocatable) even though a source file exists.
        if status == "unlocatable":
            include = False
            rationale = (pl or {}).get("note") or "absent from every available scan for this testament"
        else:
            include = bool(sab["present"]) or arch["present"] or status == "inventoried"
            rationale = ("scan-placed (%s)" % status if arch["present"] or status in ("co-located",)
                         else "reference-set slot; source-attested, no distinct printed header located"
                         if status == "inventoried" else "source-attested")
        counts["include" if include else "exclude"] += 1
        out.append({
            "slot_id": rd["slot_id"], "section": section, "name": name, "testament": testament,
            "position": rd["position"],
            "attestation": {
                "sabates_a": sab, "archive_org": arch, "madueke_b": madv,
                "odr_com": {"present": False, "granularity": "n/a",
                            "note": "odr-com scrapes scripture + annotations, not front/back reference docs"},
                "s_dismas": {"present": None, "granularity": "aggregate",
                             "note": "s-dismas carries archaic front matter (front-matter fascicle); "
                                     "per-slot extraction not performed"}},
            "placement": {"status": status, "witness": (pl.get("source") or {}).get("witness") if pl else None,
                          "page": arch["page"], "crop_image": arch["crop"],
                          "identifying_text": arch["identifying_text"]},
            "decision": {"include": include, "rationale": rationale}})
    return out, counts


def build_book_channels(skeleton: dict) -> tuple[list[dict], dict]:
    out: list[dict] = []
    gaps_total = 0
    sab_channel_books = {ch: 0 for ch in CHANNELS}
    for b in skeleton["books"]:
        slug, ordv = b["slug"], b["ordinal"]
        sab = sabates_book_channels(slug)
        odr = odr_book_channels(slug)
        per_channel: dict[str, Any] = {}
        for ch in CHANNELS:
            entry: dict[str, Any] = {}
            if sab is not None:
                entry["sabates_a"] = sab[ch]
                if sab[ch].get("present"):
                    sab_channel_books[ch] += 1
            if odr is not None and ch in odr:
                entry["odr_com"] = odr[ch]
            per_channel[ch] = entry
        s_covered = ordv in SDISMAS_ORDINALS
        book_gaps: list[str] = []
        if sab is not None and not any(sab[ch].get("present") for ch in CHANNELS):
            book_gaps.append("no apparatus in any Sabates channel for this book")
        # per-chapter genuine gap surfaced from the gapfill finding (2-paralipomenon 12)
        rec = {
            "ordinal": ordv, "slug": slug, "testament": b["testament"],
            "chapters": b["chapters"], "is_appendix": b["is_appendix"],
            "sabates_chapters": sab["chapters"] if sab is not None else None,
            "per_channel": per_channel,
            "book_level_attestation": {
                "s_dismas": {"present": s_covered, "granularity": "book", "spelling": "archaic",
                             "note": "archaic-diplomatic PDF carries this book's argument + text"
                                     if s_covered else "outside the s-dismas PDF set"},
                "madueke_b": {"granularity": "aggregate",
                              "note": "corroborated in aggregate (see summary.madueke_b)"},
                "archive_org": {"present": True, "granularity": "book-scan",
                                "note": "the printed apparatus for this book stands in the scanned tome"}},
            "decision": {"include": sab is not None or odr is not None,
                         "rationale": "Sabates supplies the apparatus channels; corroborated by "
                                      "archaic witnesses where covered"},
            "gaps": book_gaps}
        gaps_total += len(book_gaps)
        out.append(rec)
    return out, {"channel_book_counts": sab_channel_books, "book_gap_flags": gaps_total}


def main() -> int:
    for p in (RAW, REFERENCE, SKELETON, LAYOUT_MAP):
        if not p.exists():
            print(f"!! missing input: {p}", file=sys.stderr)
            return 2
    skeleton = json.loads(SKELETON.read_text())
    layout = json.loads(LAYOUT_MAP.read_text())
    placements = placement_index(layout)
    madb = madb_text()

    reference_docs, ref_counts = build_reference_docs(skeleton, placements, madb)
    book_channels, book_stats = build_book_channels(skeleton)
    mad = madueke_aggregate()

    doc = {
        "artifact": "apparatus-attestation", "phase": "P1.5", "idx": 108,
        "generated_by": "build_apparatus_attestation.py",
        "note": "Source x apparatus-item presence + scan placement + include/exclude decision, for "
                "the 26 reference docs and every book's 5 apparatus channels. Contributors are ALL "
                "sources (sabates_a element-level; odr_com book/chapter; s_dismas book-level; "
                "madueke_b aggregate corroboration; archive_org scan placement). This is the "
                "evidence base for why each apparatus item is included or omitted (plan §4.5) and "
                "the input to the contributor heatmaps (§7).",
        "sources": SOURCES,
        "channels": CHANNELS,
        "reference_docs": reference_docs,
        "book_channels": book_channels,
        "madueke_b": mad,
        "summary": {
            "reference_docs": {"total": len(reference_docs), **ref_counts},
            "book_channels": {"books": len(book_channels),
                              "sabates_channel_book_counts": book_stats["channel_book_counts"],
                              "book_gap_flags": book_stats["book_gap_flags"]},
            "genuine_chapter_gap": {"book": "2-paralipomenon", "chapter": 12,
                                    "note": "bare-heading chapter; no apparatus in any digital "
                                            "witness (see apparatus-gapfill.json)."},
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"apparatus-attestation.json  ·  {len(reference_docs)} reference docs "
          f"({ref_counts['include']} include / {ref_counts['exclude']} exclude)  ·  "
          f"{len(book_channels)} books  ·  sabates channel-book counts "
          f"{book_stats['channel_book_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
