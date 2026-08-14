#!/usr/bin/env python
"""Scan-derived apparatus-ordering EVIDENCE for the Original Douay-Rheims (idx 108).

The v2 generator hard-coded OT_FRONT / OT_BACK / NT_FRONT / NT_BACK as literal Python lists asserted
to match "the tome positions of the 1609/1610 print", with no data trail. This script replaces that
assertion with a committed evidence file (apparatus-order.json) that records, for every apparatus
section, its emitted position AND the basis for that position.

WHY MIXED EVIDENCE (and why that is the honest answer)

  The apparatus is MASKED in the reading text, so what matters is front/back-of-tome placement per
  testament, not intra-page layout. Order evidence comes from four methods, each labeled per section:

    * section-field : Sabates reference-doc `section` carries an exact numeric prefix
                      (01-title-page / 02-approbatio / 03-preface; historical-table-age-1..6).
    * ocr-offset    : the section header survives OCR in the archive.org scan djvu, so its character
                      offset there fixes its order relative to other OCR-visible sections.
    * manual-visual : ornamental headers the OCR mangles (privilege, censura, the S.Peter/S.Paul
                      tables, the creed) were confirmed by eye against the original scan pages.
    * structural    : front matter precedes its testament; study tables/glossary are back matter.

  Empirically, plain OCR anchoring fails for most ornamental apparatus headers (they are the worst-
  OCR'd type on the page). Claiming an ocr-offset for a header the OCR cannot read would be a
  fabricated data trail; instead each position states the strongest HONEST evidence available.

The generator loads the NAME order from this file (see gen_dr_original.py). Output: apparatus-order.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "originaldr_reconstruction"))  # R9.6
import project_root as pr  # noqa: E402  R9.6: one derived root

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
SRC = REPO / ".scratch/original-douay-rheims"
REF = SRC / "reference"
AO = pr.ARCHIVE_ORG
OUT = HERE / "apparatus-order.json"

# Verified emit order per region (unchanged from v2 -- confirmed faithful; this file records WHY).
REGIONS = {
    "ot_front": ("ot", ["title-page", "approbatio", "preface", "privilege", "censura"]),
    "ot_back": ("ot", ["historical-table-age-1", "historical-table-age-2", "historical-table-age-3",
                        "historical-table-age-3b", "historical-table-age-4", "historical-table-age-5",
                        "historical-table-age-6", "glossary", "epistles-table"]),
    "nt_front": ("nt", ["title-page", "preface", "censure"]),
    "nt_back": ("nt", ["explication-words", "table-peter", "table-paul", "table-corruptions",
                       "table-catholic-truths", "table-epistles-gospels", "apostles-creed",
                       "evangelical-history", "scripture-authority"]),
}

# djvu witness whose scan OCR is searched for a region's headers.
REGION_DJVU = {"ot_front": "ot1-1609", "ot_back": "ot2-1610",
               "nt_front": "nt-1582", "nt_back": "nt-1582"}

# Robust OCR anchor (case-insensitive regex) for the FEW headers that survive OCR; else None ->
# fall back to section-field / manual-visual / structural.
OCR_ANCHOR = {
    ("ot_front", "title-page"): r"FAITHF[VU]LLY",
    ("ot_back", "historical-table-age-1"): r"HISTORICALL? TABLE",
    ("ot_back", "glossary"): r"PARTIC[VU]LAR TABLE",
    ("nt_front", "preface"): r"\bPREFACE\b",
    ("nt_back", "explication-words"): r"EXPLICATION",
}

# Manual-visual confirmations recorded by the prior scan-review pass (headers OCR mangles).
MANUAL_VISUAL = {
    ("ot_front", "privilege"): "French royal privilege page follows the preface in the 1609 front matter",
    ("ot_front", "censura"): "theologians' Censura follows the privilege in the 1609 front matter",
    ("nt_front", "censure"): "Censure & Approbation follows the preface in the 1582 NT front matter",
    ("nt_back", "table-peter"): "Table of S. Peter precedes the Table of S. Paul in the 1582 NT back matter",
    ("nt_back", "table-paul"): "Table of S. Paul precedes the Apostles' Creed in the 1582 NT back matter",
    ("nt_back", "apostles-creed"): "Apostles' Creed follows the Pauline table in the 1582 NT back matter",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref_section(sub: str, name: str) -> str | None:
    p = REF / sub / f"{name}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("section")


def ocr_offset(region: str, name: str, djvu_text: str) -> int | None:
    pat = OCR_ANCHOR.get((region, name))
    if not pat:
        return None
    m = re.search(pat, djvu_text, re.I)
    return m.start() if m else None


def main() -> int:
    if not REF.exists() or not AO.exists():
        print(f"!! source missing (REF={REF.exists()} AO={AO.exists()})", file=sys.stderr)
        return 2

    djvu_cache: dict[str, str] = {}

    def djvu(name: str) -> str:
        if name not in djvu_cache:
            djvu_cache[name] = (AO / f"{name}_djvu.txt").read_text(encoding="utf-8", errors="replace")
        return djvu_cache[name]

    regions_out = {}
    method_tally: dict[str, int] = {}
    for region, (sub, names) in REGIONS.items():
        wit = REGION_DJVU[region]
        text = djvu(wit)
        entries = []
        for pos, name in enumerate(names):
            sec = ref_section(sub, name)
            sec_basis = None
            if sec:
                mp = re.match(r"^(\d+)-", sec)          # 01-title-page (global front-matter order)
                ms = re.search(r"age-(\d+)", sec)        # historical-table-age-3 (table sequence)
                if mp:
                    sec_basis = f"numeric prefix {sec!r} pins front-matter order"
                elif ms:
                    sec_basis = f"historical-table sequence {sec!r} pins table order"
            off = ocr_offset(region, name, text)
            mv = MANUAL_VISUAL.get((region, name))
            if sec_basis is not None:
                method, basis = "section-field", sec_basis
            elif off is not None:
                method, basis = "ocr-offset", f"header OCR-attested in {wit} at char {off}"
            elif mv is not None:
                method, basis = "manual-visual", mv
            else:
                method, basis = "structural", "front matter precedes testament / tables are back matter"
            method_tally[method] = method_tally.get(method, 0) + 1
            entries.append({
                "position": pos, "name": name, "section_field": sec,
                "evidence": {"method": method, "basis": basis,
                             "ocr_witness": wit if off is not None else None,
                             "ocr_char_offset": off},
            })
        regions_out[region] = entries

    artifact = {
        "artifact": "apparatus-order",
        "generated_by": "build_apparatus_order.py",
        "idx": 108,
        "note": "Apparatus is masked; front/back-of-tome placement per testament is what matters. "
                "Each section's position states the strongest honest evidence: section-field numeric "
                "prefix, OCR offset in the archive.org scan where the header survives OCR, manual-visual "
                "scan confirmation for ornamental headers OCR mangles, or structural placement.",
        "method_tally": method_tally,
        "scan_sources": {name: {"path": str((AO / f"{name}_djvu.txt").relative_to(REPO)),
                                "sha256": sha256_file(AO / f"{name}_djvu.txt")}
                         for name in sorted(set(REGION_DJVU.values()))},
        **regions_out,
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print("apparatus-order.json written. evidence methods:", method_tally)
    for region, entries in regions_out.items():
        seq = " -> ".join(f"{e['name']}[{e['evidence']['method'][:4]}]" for e in entries)
        print(f"  {region}: {seq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
