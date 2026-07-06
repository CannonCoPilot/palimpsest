#!/usr/bin/env python3
"""Phase 1 · P1.2 — per-source detection & alignment (map every read to the skeleton).

For each witness, detect every scripture element it carries and align it to a
skeleton coordinate (`scripture/<book>/<ch>/<v>`), emitting one *read record* per
detected element:

    {skeleton_id, present, surface, spelling, locus, method, local_confidence, evidence_ptr}

Read records are the "aligned reads" of the multiple-sequence-alignment model.
They are INTERMEDIATE and fully regenerable from the sha-pinned sources via this
committed detector, so the bulky per-source reads/<source>.json are written to
scratch (not git); the per-witness readings are permanently captured downstream in
the basis-db attestation records (P1.6). Here we also emit a compact, TRACKED
`reads-coverage.json` (per-source coverage vs the skeleton) for review + CI.

This module is extensible: each detector is `detect_<source>() -> list[read]`.
The structured modern witnesses (Madueke_A HTML, Sabates_A JSON) are implemented
here; archaic/OCR witnesses (s-dismas, odr-com, archive.org OCR, our fresh OCR)
plug in as their acquisition completes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASK_ENGINE = HERE.parent
sys.path.insert(0, str(MASK_ENGINE))
import gen_dr_original as gen  # type: ignore[import]  # noqa: E402

SKELETON = json.loads((HERE / "skeleton.json").read_text())
READS_DIR = gen.REPO / "core/.scratch/originaldr-project/reconstruction/reads"

# skeleton book -> chapter count, for grid validation
_BOOK_CH = {b["slug"]: b["chapters"] for b in SKELETON["books"]}


def read_record(skid: str, surface: str, spelling: str, locus: str,
                method: str, conf: str, evidence: str) -> dict:
    return {"skeleton_id": skid, "present": True, "surface": surface, "spelling": spelling,
            "locus": locus, "method": method, "local_confidence": conf, "evidence_ptr": evidence}


def _drop_spurious(slug: str, chapters: list) -> list:
    """Mirror the 108 builder: drop a known spurious leading chapter (Tobias ch0 fragment)
    so chapter numbering matches the DR/Vulgate canon + the skeleton grid."""
    if slug in gen.SPURIOUS_LEADING_CHAPTER and len(chapters) > 1:
        return chapters[1:]
    return chapters


def detect_madueke_a() -> list[dict]:
    """Madueke_A per-chapter HTML: authoritative modern scripture, verse-structured."""
    books, order = gen.parse_madueke()
    slugs = list(gen.OT) + list(gen.NT)      # Madueke has the 73 canonical books, no appendix
    reads: list[dict] = []
    if len(order) != len(slugs):
        raise SystemExit(f"Madueke book count {len(order)} != canonical {len(slugs)}")
    for disp, slug in zip(order, slugs):
        for ch in sorted(books[disp]):
            for v in sorted(books[disp][ch]):
                txt = gen.clean_scripture(books[disp][ch][v])
                if not txt:
                    continue
                reads.append(read_record(
                    f"scripture/{slug}/{ch}/{v}", txt, "modern",
                    f"madueke-a/books ({disp} {ch})", "html-parse", "high",
                    f"madueke_a:{disp}:{ch}:{v}"))
    return reads


def detect_sabates_a() -> list[dict]:
    """Sabates_A JSON: modern scripture for all 76 books (incl. the 3-book apocryphal appendix
    that Madueke omits). Apparatus is detected separately (P1.5)."""
    reads: list[dict] = []
    slugs = list(gen.OT) + list(gen.NT) + list(gen.APOCRYPHA)
    for slug in slugs:
        path = gen.RAW / f"{slug}.json"
        if not path.exists():
            continue
        meta = json.loads(path.read_text())
        chapters = _drop_spurious(slug, meta.get("chapters", []))
        for n, ch in enumerate(chapters, 1):
            for v in ch.get("verses", []):
                vn = gen._vnum(v.get("verse"))
                txt = gen.clean(v.get("text", ""))
                if vn is None or not txt:
                    continue
                reads.append(read_record(
                    f"scripture/{slug}/{n}/{vn}", txt, "modern",
                    f"sabates raw/{slug}.json ch{n}", "json-parse", "high",
                    f"sabates_a:{slug}:{n}:{vn}"))
    return reads


DETECTORS = {
    "madueke_a": {"fn": detect_madueke_a, "lineage": "madueke", "independent": False,
                  "spelling": "modern"},
    "sabates_a": {"fn": detect_sabates_a, "lineage": "sabates", "independent": False,
                  "spelling": "modern"},
}


def coverage(reads: list[dict]) -> dict:
    """Coverage of a read set vs the skeleton grid: books/chapters/verses touched, out-of-grid."""
    chapters, verses, out_of_grid = set(), 0, []
    books = set()
    for r in reads:
        parts = r["skeleton_id"].split("/")   # scripture/<book>/<ch>/<v>
        if len(parts) != 4 or parts[0] != "scripture":
            continue
        _, book, ch, _v = parts
        verses += 1
        books.add(book)
        chapters.add((book, int(ch)))
        maxch = _BOOK_CH.get(book)
        if maxch is None or int(ch) > maxch:
            out_of_grid.append(r["skeleton_id"])
    return {"books": len(books), "chapters": len(chapters), "verses": verses,
            "out_of_grid": out_of_grid[:20], "out_of_grid_count": len(out_of_grid)}


def main() -> int:
    only = sys.argv[1:] or list(DETECTORS)
    READS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"skeleton_chapters": SKELETON["totals"]["chapters"], "sources": {}}
    for name in only:
        spec = DETECTORS[name]
        reads = spec["fn"]()
        cov = coverage(reads)
        out = {"source": name, "lineage": spec["lineage"], "independent": spec["independent"],
               "spelling": spec["spelling"], "count": len(reads), "coverage": cov, "reads": reads}
        (READS_DIR / f"{name}.json").write_text(json.dumps(out, ensure_ascii=False))
        summary["sources"][name] = {k: v for k, v in out.items() if k != "reads"}
        flag = "" if not cov["out_of_grid_count"] else f"  ⚠ {cov['out_of_grid_count']} out-of-grid"
        print(f"{name}: {len(reads)} reads · {cov['books']} books · {cov['chapters']} chapters "
              f"· {cov['verses']} verses{flag}")
    (HERE / "reads-coverage.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"reads → {READS_DIR}  ·  coverage → reads-coverage.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
