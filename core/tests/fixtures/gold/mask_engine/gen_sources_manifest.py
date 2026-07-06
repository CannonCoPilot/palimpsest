#!/usr/bin/env python
"""Generate ``sources.manifest.json`` — the Bible Gold Set audit trail + registry.

This is the single committed record of every Bible gold source and the artifacts it was
keyed to. It fingerprints the source *without redistributing it*: the raw epub/pdf/txt
stay in the gitignored ``imports/`` corpus (use ≠ distribution), while their sha256 +
provenance ship here so a holder of the corpus can prove their local binaries match what
each gold was built from (see ``verify_sources.py``).

It doubles as the gold **registry** (replaces the annotation-only ``GOLD_IDXS`` glob as
the enumeration source for CLI/API) and the Gold-Set **scorecard** (the ``validated``
block records operational readiness through each Palimpsest path).

Derived facts (source_sha256, reference_sha256, structure counts, canon shape) come from
the maps + the local corpus; curated facts (translation, year, spelling, typeset,
provenance) live in ``PROVENANCE`` below — the one place editorial metadata is maintained.

Usage:
  gen_sources_manifest.py            # regenerate ../sources.manifest.json
  gen_sources_manifest.py --check    # verify the committed manifest is up to date (CI)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE.parent  # core/tests/fixtures/gold
MAPS = GOLD / "maps"
REPO = HERE.parents[4]
IMPORTS = REPO / "imports"
OUT = GOLD / "sources.manifest.json"

# Curated editorial metadata, keyed by gold idx. Everything else is derived.
#   kind: marker (gen_marker_gold) | detector-epub (gen_gold_maps + annotation gold) | bespoke
#   accuracy_source: how this Bible's masking ACCURACY is independently checked —
#     canon-oracle (test_gold_canon) | annotation+detector (gold_ratify/a3) | map-gates (bespoke)
PROVENANCE: dict[int, dict] = {
    5:   {"translation": "Douay-Rheims Bible (Haydock)", "year": None, "spelling": "modern",
          "typeset": "modern", "canon": "catholic-douay", "kind": "detector-epub",
          "source_origin": "published-epub", "accuracy_source": "annotation+detector"},
    6:   {"translation": "Geneva Bible (1599, Tolle Lege)", "year": 2013, "spelling": "modernized",
          "typeset": "modern", "canon": "protestant-66", "kind": "detector-epub",
          "source_origin": "published-epub", "accuracy_source": "annotation+detector"},
    100: {"translation": "Douay-Rheims Bible (Challoner, Global Grey)", "year": 2024,
          "spelling": "modern", "typeset": "modern", "canon": "catholic-douay",
          "kind": "detector-epub", "source_origin": "published-epub",
          "accuracy_source": "annotation+detector"},
    108: {"translation": "Douay-Rheims Bible (Original, 1582-1610)", "year": 1610,
          "spelling": "modern", "typeset": "modern", "canon": "catholic-douay",
          "kind": "bespoke", "source_origin": "reconstructed-from-collated-digital-editions",
          "accuracy_source": "catholic-oracle",
          "note": "Scripture text is authoritatively the Madueke_A olprint 'Augmented Bible' HTML "
                  "edition (73 books); editorial apparatus (book/chapter arguments, footnotes, "
                  "annotations, 26 front/back reference documents) and the three-book apocryphal "
                  "appendix come from the janvier-s/original-douay-rheims CC0 dataset, which Madueke "
                  "omits. The two witnesses share a transcription lineage, so a verse-by-verse "
                  "collation (0 substantive wording differences) plus an INDEPENDENT tesseract OCR "
                  "of the original 1582/1609/1610 printed scans (0 genuine wording discrepancies "
                  "across five canonical divisions) confirm the scripture against the print — a "
                  "three-witness provenance recorded per element. Catholic Vulgate canon, gated by "
                  "the ordered Douay-Rheims/Clementine oracle (catholic_dr): all 76 books match the "
                  "external Vulgate chapter counts (Esther 16, Daniel 14, Baruch 6, 1 Esdras=Ezra=10, "
                  "3+4 Esdras appendix). The janvier-s dataset had captured Tobias's Argument as a "
                  "spurious 1-verse chapter 1; the reconstruction drops it, restoring the canonical "
                  "14 chapters (the Argument itself divides the book 4+8+2). Likewise 3 Esdras 2:1 "
                  "appeared twice in the janvier-s source (the second entry a leaked cross-reference "
                  "list mis-captured as a repeat verse); a keep-first verse-number dedup restores the "
                  "single canonical verse. idx 108 is emitted as a deterministic projection of the "
                  "Phase-1 basis database (render_modern.py): verse bodies from the consensus modern "
                  "surface under modern-standard.json, apparatus + structure from janvier-s at render "
                  "time — the reference text is byte-identical to the direct-witness build."},
    201: {"translation": "Coverdale Bible", "year": 1535, "spelling": "archaic", "typeset": "modern",
          "canon": "protestant-66", "kind": "marker", "source_origin": "reconstructed-from-web-scrape",
          "accuracy_source": "canon-oracle"},
    202: {"translation": "Bishops' Bible", "year": 1568, "spelling": "archaic", "typeset": "modern",
          "canon": "protestant-66", "kind": "marker", "source_origin": "reconstructed-from-web-scrape",
          "accuracy_source": "canon-oracle"},
    203: {"translation": "Wycliffe Bible", "year": 1382, "spelling": "archaic-middle-english",
          "typeset": "modern", "canon": "wider-73", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape",
          "accuracy_source": "canon-oracle", "note": "core-66 gated; deuterocanon recorded (Vulgate counts)."},
    208: {"translation": "Great Bible", "year": 1539, "spelling": "archaic", "typeset": "modern",
          "canon": "protestant-66", "kind": "marker", "source_origin": "reconstructed-from-web-scrape",
          "accuracy_source": "canon-oracle"},
    209: {"translation": "Matthew's Bible", "year": 1537, "spelling": "archaic", "typeset": "modern",
          "canon": "protestant-66", "kind": "marker", "source_origin": "reconstructed-from-web-scrape",
          "accuracy_source": "canon-oracle"},
    210: {"translation": "Webster's Bible", "year": 1833, "spelling": "modern", "typeset": "modern",
          "canon": "protestant-66", "kind": "marker", "source_origin": "reconstructed-from-web-scrape",
          "accuracy_source": "canon-oracle"},
    211: {"translation": "Wessex Gospels", "year": 990, "spelling": "archaic-old-english",
          "typeset": "modern", "canon": "gospels-only", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape", "accuracy_source": "canon-oracle"},
    212: {"translation": "Young's Literal Translation", "year": 1898, "spelling": "modern",
          "typeset": "modern", "canon": "protestant-66", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape", "accuracy_source": "canon-oracle"},
    213: {"translation": "Julia E. Smith Translation", "year": 1876, "spelling": "modern",
          "typeset": "modern", "canon": "protestant-66", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape", "accuracy_source": "canon-oracle"},
    214: {"translation": "King James Version (2016, NT)", "year": 2016, "spelling": "modern",
          "typeset": "modern", "canon": "new-testament", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape", "accuracy_source": "canon-oracle"},
    215: {"translation": "EMTV (English Majority Text Version, NT)", "year": 2003, "spelling": "modern",
          "typeset": "modern", "canon": "new-testament", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape", "accuracy_source": "canon-oracle"},
    216: {"translation": "King James Version (1769)", "year": 1769, "spelling": "modern-standardized",
          "typeset": "modern", "canon": "protestant-66", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape", "accuracy_source": "canon-oracle"},
    217: {"translation": "Tyndale Bible", "year": 1535, "spelling": "archaic", "typeset": "modern",
          "canon": "partial", "kind": "marker", "source_origin": "reconstructed-from-epub",
          "accuracy_source": "canon-oracle"},
    218: {"translation": "Geneva Bible (1560)", "year": 1560, "spelling": "archaic", "typeset": "modern",
          "canon": "protestant-66", "kind": "marker", "source_origin": "reconstructed-from-epub",
          "accuracy_source": "canon-oracle"},
    219: {"translation": "King James Version (1611, comprehensive)", "year": 1611, "spelling": "archaic",
          "typeset": "modern", "canon": "kjv-1611-80", "kind": "marker",
          "source_origin": "reconstructed-from-web-scrape", "accuracy_source": "canon-oracle",
          "note": "80-book edition with 1611 apparatus; core-66 + KJV-Apocrypha gated by the canon oracle."},
}

BIBLE_IDXS = sorted(PROVENANCE)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _local_index() -> dict[str, Path]:
    idx: dict[str, Path] = {}
    if IMPORTS.is_dir():
        for p in IMPORTS.rglob("*"):
            if p.is_file():
                idx.setdefault(p.name, p)
    return idx


def build() -> dict:
    local = _local_index()
    entries = []
    for idx in BIBLE_IDXS:
        mp = MAPS / f"work-{idx:03d}.map.json"
        m = json.loads(mp.read_text(encoding="utf-8"))
        src_name = m.get("source_file", "")
        src_path = local.get(src_name)
        tc = m.get("type_counts", {})
        prov = PROVENANCE[idx]
        ann = GOLD / f"work-{idx}.json"
        entries.append({
            "id": idx,
            "translation": prov["translation"],
            "year": prov["year"],
            "spelling": prov["spelling"],
            "typeset": prov["typeset"],
            "canon": prov["canon"],
            "kind": prov["kind"],
            "source_origin": prov["source_origin"],
            "source_file": src_name,
            "source_file_type": Path(src_name).suffix.lstrip(".").lower() or "unknown",
            "source_present": src_path is not None,
            "source_sha256": _sha256(src_path) if src_path else None,
            "reference_sha256": m.get("reference_sha256"),
            "structure": {
                "books": tc.get("book"),
                "chapters": tc.get("chapter"),
                "verses": m.get("verse_count"),
            },
            "gold_map": f"maps/work-{idx:03d}.map.json",
            "annotation_gold": f"work-{idx}.json" if ann.exists() else None,
            "accuracy_source": prov["accuracy_source"],
            # Operational readiness through each Palimpsest import path. The gold paths
            # (CLI `gold`, GET/POST /api/gold, UI Gold Library) are generic over every
            # registry entry, so all Bibles are reachable once those paths exist; the
            # path's own test is the evidence.
            "validated": {"cli": True, "api": True, "ui": True},
            **({"canon_exceptions": prov["canon_exceptions"]} if "canon_exceptions" in prov else {}),
            **({"note": prov["note"]} if "note" in prov else {}),
        })
    return {
        "schema": "palimpsest.gold-sources/v1",
        "scope": "bibles",
        "note": "Audit trail + registry + scorecard for the Bible Gold Set. Source binaries are "
                "NOT distributed (imports/ is gitignored); source_sha256 is the fingerprint. "
                "Regenerate with mask_engine/gen_sources_manifest.py; verify local corpus with "
                "verify_sources.py.",
        "count": len(entries),
        "bibles": entries,
    }


def main() -> int:
    manifest = build()
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("sources.manifest.json is STALE — run gen_sources_manifest.py", file=sys.stderr)
            return 1
        print("sources.manifest.json up to date")
        return 0
    OUT.write_text(text, encoding="utf-8")
    present = sum(1 for b in manifest["bibles"] if b["source_present"])
    print(f"wrote {OUT.name}: {manifest['count']} Bibles, {present} with local source binaries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
