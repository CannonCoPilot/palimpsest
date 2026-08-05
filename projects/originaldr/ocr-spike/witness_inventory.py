#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""witness_inventory.py — THE AUTHORITATIVE witness collection, as stated by Sir 2026-07-27.

STOP RE-DERIVING THIS. Three separate artifacts were each being consulted as if authoritative about what a
volume contains — `master-source-list.json` (testaments per WITNESS, not per volume), `tome-map.json` (whose
own metadata declares the 1633 Rheims NEW TESTAMENT as ['NT','OT']) and `jp2_page.OCR_DIR_TO_JP2` — and the
addressing was inferring tome membership from whichever it happened to read. That is how a 27-book New
Testament ended up with a 73-book state space. The inventory is a FACT about the collection, not something to
be recovered by measurement; it is declared here once and everything else defers to it.

FOUR RECONSTRUCTED COMPLETE COPIES of the Douay-Rheims as originally printed:

    A   S1              OT1 1609 · OT2 1610 · NT 1582      three separate volumes
    B   S3 + S8         OT1 1609 · OT2 1610 (S3, two volumes) · NT 1582 (S8)
    C   S9              OT1 1609 · OT2 1610 · NT 1582      three separate volumes
    D   S6 + S4         OT1/OT2 1635 (S6, one file) · NT 1633 (S4)
        ** S6's NT pages are DROPPED: they repeat the same 1582 edition already carried by A, B and C. **

REFERENCE-WITNESS POLICY (Sir, same date) — which reference is authoritative for WHICH QUESTION:

    LOCALIZATION · PRESENCE · INTERVAL ALIGNMENT · TEXT TYPE   janvier + madueke are PRIMARY.
        Being modern does not disqualify them; these are structural questions about a type-modernized product,
        and they are the best evidence for them.
    CONTENT · SURFACE                                           s_dismas + odr_com are PRIMARY, but ONLY at
        loci where they actually carry text of their own. **WHERE THEY HAVE GAPS, janvier + madueke are
        primary for content and surface too.**
    GOLD TRANSCRIPT is NOT the authority on localization, presence, interval alignment or verse/line. It is the
        best-reviewed SUBSET, a comparative baseline for measuring re-OCR progress — and it likely needs
        correction/standardisation so its structure is congruent with janvier's.

**THIS POLICY IS THE DIAGNOSIS OF POP-2.** 1535 locus×source records score archaic < 0.2 while modern > 0.9,
with `floor_modern` (archaic-ref vs modern-ref, no OCR involved) at 0.008: the archaic witness has no real text
at those loci, or text that is not this verse. The gate governs on archaic there anyway and fails the verse.
Under the policy above the archaic witness simply is not primary at a locus where it has no content, so those
verses should be governed by janvier/madueke. The fix is not a new heuristic — it is implementing the stated
policy.

FRONT/BACK MATTER is in scope for re-OCR improvement and testing at every stage: as source witnesses, as Gold
Transcript pages, and in the comparisons (gold vs OCR baseline vs rung-improved vs modern/archaic references).
"""
from __future__ import annotations

SCANS_ROOT = ("/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/"
              "DouayRheims_DR/sources/scans")

# copy -> the sources that together reconstruct one complete printed Bible
COPIES = {
    "A": ["S1"],
    "B": ["S3", "S8"],
    "C": ["S9"],
    "D": ["S6", "S4"],
}

# source -> tome -> {scan_dir, ocr_dir, year}. `ocr_dir` is the existing OCR directory name, which is
# historical and often misleading (`pdf-S03a` is served from jp2); the TOME here is authoritative.
WITNESSES = {
    "S1": {
        "copy": "A", "title": "1582/1609/1610 First Edition, three volumes",
        "scan_root": "S01_1582-first-edition-3vol",
        "tomes": {
            "OT1": {"year": 1609, "ocr_dir": "archive-ot1-1609"},
            "OT2": {"year": 1610, "ocr_dir": "archive-ot2-1610"},
            "NT":  {"year": 1582, "ocr_dir": "archive-nt-1582"},
        },
    },
    "S3": {
        "copy": "B", "title": "Holie Bible ('engl' copy), OT in two volumes",
        "scan_root": ["S03_holie-bible-engl-ot-vol1", "S03_holie-bible-engl-ot-vol2"],
        "tomes": {
            "OT1": {"year": 1609, "ocr_dir": "pdf-S03a"},
            "OT2": {"year": 1610, "ocr_dir": "pdf-S03b"},
        },
    },
    "S8": {
        "copy": "B", "title": "1582 Rhemes New Testament (high resolution)",
        "scan_root": "S08_1582-rhemes-nt-hires",
        "tomes": {"NT": {"year": 1582, "ocr_dir": "jp2-S08"}},
    },
    "S9": {
        "copy": "C", "title": "Holie Bible / Nevv Testament ('mart' copy), three volumes",
        "scan_root": "S09_nevv-testament-mart-3vol",
        "tomes": {
            "OT1": {"year": 1609, "ocr_dir": "archive-holiebible-ot1"},
            "OT2": {"year": 1610, "ocr_dir": "jp2-S09ot2"},
            "NT":  {"year": 1582, "ocr_dir": "pdf-S09nt"},
        },
    },
    "S6": {
        "copy": "D", "title": "1635 facsimile, whole Bible in one file (OT1/OT2 kept; NT dropped)",
        "scan_root": "S06_1610-facsimile-whole",
        "tomes": {
            "OT1": {"year": 1635, "ocr_dir": "jp2-S06"},
            "OT2": {"year": 1635, "ocr_dir": "jp2-S06"},
        },
        # S6's NT pages repeat the 1582 edition already carried by A, B and C. They are DROPPED, not scored —
        # counting them would add a fourth copy of one edition and inflate every cross-source agreement.
        "drop_tomes": ["NT"],
    },
    "S4": {
        "copy": "D", "title": "1633 Rheims New Testament",
        "scan_root": "S04_1633-rheims-nt",
        "tomes": {"NT": {"year": 1633, "ocr_dir": "jp2-S04"}},
    },
}

# Everything else under scans/ is NOT a witness for OCR / re-OCR / gold work.
EXCLUDED_SCAN_DIRS = ["S02_1609-douay-ot-hires", "S05_newtestament-engl-nt", "S07_1635-facsimile-whole",
                      "S10_eebo-nt", "S11_eebo-vol1-nt", "S12_eebo-vol2-ot-genesis",
                      "S13_eebo-vol3-ot-joshua", "S14_eebo-vol4-ot-psalms", "S15_eebo-vol5-ot-isaiah"]

OT1_BOOKS_NOTE = "OT1 = Genesis..Job; OT2 = Psalms..Machabees (the printed two-tome split)."
OT2_BOOKS = {"psalms", "proverbs", "ecclesiastes", "canticle-of-canticles", "wisdom", "ecclesiasticus",
             "isaie", "jeremie", "lamentations", "baruch", "ezechiel", "daniel", "osee", "joel", "amos",
             "abdias", "jonas", "micheas", "nahum", "habacuc", "sophonias", "aggeus", "zacharias", "malachie",
             "1-machabees", "2-machabees"}


def _validate_ot2_books():
    """A hand-typed book list MUST be checked against the canon, or a typo silently deletes a book.

    MEASURED: this set read `zacharie` where the canon spells it `zacharias`, so Zacharias — a minor prophet,
    unambiguously in the second OT tome — was classified OT1, given the OT1 state space, and could never be
    addressed because it is not physically in those volumes. Two OT1 volumes report it missing to this day.
    This is the third instance of the same defect shape in this project (the three divergent LOCI dicts, the
    GT's `2john` vs the canon's `2-john`), so it is guarded rather than merely corrected."""
    import json as _json
    from pathlib import Path as _Path
    recon = _Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/mask_engine/"
                  "originaldr_reconstruction/skeleton.json")
    canon = {b["slug"] for b in _json.loads(recon.read_text())["books"]}
    bad = sorted(OT2_BOOKS - canon)
    if bad:
        raise ValueError(f"OT2_BOOKS contains slugs absent from the canon: {bad}. "
                         f"Fix the spelling — a typo here silently removes a book from its tome.")


_validate_ot2_books()

# Which reference witness is PRIMARY for which question (see the policy in the module docstring).
REFERENCE_ROLE = {
    "localization": ["janvier", "madueke"],
    "presence": ["janvier", "madueke"],
    "interval_alignment": ["janvier", "madueke"],
    "text_type": ["janvier", "madueke"],
    "content": ["s_dismas", "odr_com", "janvier", "madueke"],   # archaic first, but only where it has text
    "surface": ["s_dismas", "odr_com", "janvier", "madueke"],
}


def ocr_dir_tome() -> dict:
    """{ocr_dir: (source, [tomes])} — the authoritative tome membership of each OCR directory."""
    out: dict = {}
    for sid, w in WITNESSES.items():
        for tome, t in w["tomes"].items():
            out.setdefault(t["ocr_dir"], (sid, []))[1].append(tome)
    return out


def testaments_for(ocr_dir: str) -> list:
    """The testaments a volume may legally contain — the addressing DP's state space, declared not inferred."""
    ent = ocr_dir_tome().get(ocr_dir)
    if not ent:
        return []
    return sorted({"NT" if t == "NT" else "OT" for t in ent[1]})


def tomes_for(ocr_dir: str) -> list:
    ent = ocr_dir_tome().get(ocr_dir)
    return sorted(ent[1]) if ent else []


def admitted_ocr_dirs() -> list:
    return sorted(ocr_dir_tome())


if __name__ == "__main__":
    import json
    print(f"FOUR RECONSTRUCTED COPIES: " + " · ".join(f"{k}={'+'.join(v)}" for k, v in COPIES.items()))
    print(f"\n{'ocr_dir':26} {'src':4} {'tomes':10} {'testaments':12}")
    print("-" * 56)
    for od, (sid, tomes) in sorted(ocr_dir_tome().items()):
        print(f"{od:26} {sid:4} {'+'.join(sorted(tomes)):10} {'+'.join(testaments_for(od)):12}")
    print(f"\nadmitted OCR dirs: {len(admitted_ocr_dirs())}")
    print(f"S6 drop rule: {WITNESSES['S6'].get('drop_tomes')} (repeat of the 1582 NT held by A/B/C)")
