#!/usr/bin/env python3
"""Phase 1 · P1.4 — scan-grounded layout & apparatus-placement map.

Grounds the ARRANGEMENT of the OriginalDR reconstruction in the ORIGINAL image scans, per
plan §4.4. The EEBO facsimile PDFs are the primary layout authority; where a leaf is absent
from the (partial) EEBO facsimiles — chiefly the back-matter tables — the archive.org
full-tome scans (which carry a searchable OCR text layer, so a header maps deterministically
to an exact page) are the sanctioned fallback authority. Two products:

  1. scripture_layout — the tome/part/testament partition, each section confirmed against a
     rendered title/divider leaf (page + transcribed identifying text + committed crop).
  2. apparatus_placements — every apparatus-order.json slot (ot/nt · front/back), each with a
     transparent STATUS:
        grounded    — visually located in a scan: committed header crop
                      (placement-crops/<slot>.png) + page + transcribed identifying_text
                      + source-PDF sha256, and (where available) an archive.org OCR offset.
        co-located  — printed on the SAME leaf/table as another grounded slot (e.g. the OT
                      privilege prints as the title-page-foot permission line; the six "ages"
                      are subdivisions of one Historical Table); crop = that shared leaf.
        unlocatable — genuinely absent from every available scan; flagged with a reason.
        inventoried — a reference-set slot with no distinct printed header located; not
                      asserted as placed.
     Belt-and-suspenders (plan §4.4): nothing rests on bare structural assertion.

EEBO volume->content was VISUALLY VERIFIED from rendered title leaves (2026-07-06). Two
corrections to the earlier mapping are baked in here:
  * the EEBO OT scans are the 1635 Rouen reissue (John Cousturier, "Permissu Superiorum"),
    NOT the 1609/1610 first edition — the title-page feet read M.DC.XXXV; and
  * the two scans keyed "ot_prophetical" / "ot_secondtome" were swapped — 8ff9c022 is the
    "SECOND TOME" general title, 55c87902 is the "FOVRTH PART ... PROPHETICAL BOOKES" (p.442).
The Phase-0 seal is UNAFFECTED (the seal used archive.org + our-OCR witnesses, never EEBO).

Deterministic: identical inputs -> identical layout-map.json + crops.

Run:  core/.venv/bin/python build_layout_map.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
ORIGINAL = REPO / "imports/Scripture/Bibles/DouayRheims_DR/Original"
ARCHIVE_ORG = REPO / "imports/Scripture/Bibles/DouayRheims_DR/archive-org"
APPARATUS_ORDER = HERE.parent / "originaldr_validation" / "apparatus-order.json"
CROPS_DIR = HERE / "placement-crops"
OUT = HERE / "layout-map.json"
RENDER_DPI = 200

# --- visually-verified EEBO volume -> content (title leaf rendered per md5, 2026-07-06) ---- #
# NB: keys are semantic labels; the two prophetical/second-tome md5s were swapped in the
# earlier mapping and are corrected here so each key names the scan it actually shows.
EEBO = {
    "nt_partial": "18c502ead5119303881f2a8def094a5e",
    "ot_holybible": "c0ef3be20b3fdc19c26debe03ef520de",
    "ot_historical": "2cfaea2cb717e2b87bcb00c803ec2479",
    "ot_secondtome": "8ff9c0224c2dec4d8a7de4861ab3b38c",   # "THE SECOND TOME" general title
    "ot_prophetical": "55c87902453884748a6069ea26bcf41b",  # "THE FOVRTH PART ... PROPHETICAL"
    "nt_full": "b7bca433de548ed960cba8616ec77c10",
}
EEBO_CONTENT = {
    "nt_partial": "Rheims New Testament 1582 (Rhemes: Iohn Fogny, 'Cum priuilegio') — NT general "
                  "title + front matter (Censure & Approbation p.2, Preface p.3) + partial NT",
    "ot_holybible": "OT First Tome general title 'THE HOLY BIBLE' — Rouen: Iohn Covsturier, "
                    "'Permissu Superiorum', M.DC.XXXV (1635 reissue of the 1609 Douay OT First "
                    "Tome); front matter (Approbatio p.2, Preface p.3+) + Pentateuch",
    "ot_historical": "OT 'THE SECOND PART OF THE OLD TESTAMENT: HISTORICAL BOOKES' (Argument of "
                     "Iosve; leaf printed p.419) — First-Tome divider fragment",
    "ot_secondtome": "OT Second Tome general title 'THE SECOND TOME OF THE HOLIE BIBLE' — "
                     "Rouen: Iohn Covsturier, 1635",
    "ot_prophetical": "OT 'THE FOVRTH PART OF THE OLD TESTAMENT: PROPHETICAL BOOKES' (Argument of "
                      "Prophetical bookes in general; leaf printed p.442)",
    "nt_full": "Full Rheims New Testament 1582, incl. back-matter tables (Tables of S. Peter / "
               "S. Paul + Apostles' Creed after Acts; Explication of words, Heretical Corruptions, "
               "Epistles & Gospels, and the Table of Controversies at the end)",
}

# --- archive.org full-tome scans (searchable text.pdf) = back-matter fallback authority ----- #
AO_ALIASES = {
    "nt-1582": "full Rheims New Testament 1582 (archive.org) — carries the NT back-matter tables",
    "ot2-1610": "Douay Old Testament Second Tome (archive.org) — carries the OT back-matter "
                "Historical Table + Particular Table of Principal Things",
}

_pdf_cache: dict[str, tuple[Path, str]] = {}


def _sha256(pdf: Path) -> str:
    return hashlib.sha256(pdf.read_bytes()).hexdigest()


def eebo_pdf(key: str) -> tuple[Path, str]:
    """(path, sha256) for an EEBO scan by short key; sha computed once per file."""
    md5 = EEBO[key]
    if md5 in _pdf_cache:
        return _pdf_cache[md5]
    hits = list(ORIGINAL.glob(f"*{md5}*.pdf"))
    if not hits:
        raise SystemExit(f"EEBO pdf not found for {key} ({md5})")
    pdf = hits[0]
    _pdf_cache[md5] = (pdf, _sha256(pdf))
    return _pdf_cache[md5]


def ao_pdf(alias: str) -> tuple[Path, str]:
    """(path, sha256) for an archive.org text.pdf by alias dir; sha computed once per file."""
    ck = f"ao:{alias}"
    if ck in _pdf_cache:
        return _pdf_cache[ck]
    hits = list((ARCHIVE_ORG / alias).glob("*text.pdf"))
    if not hits:
        raise SystemExit(f"archive.org text.pdf not found for alias {alias}")
    pdf = hits[0]
    _pdf_cache[ck] = (pdf, _sha256(pdf))
    return _pdf_cache[ck]


def _crop_page(pdf: Path, page: int, box: tuple[float, float, float, float], out_png: Path) -> None:
    """Render one page at RENDER_DPI and crop the fractional box (l,t,r,b) -> out_png."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        pfx = Path(td) / "pg"
        subprocess.run(["pdftoppm", "-png", "-r", str(RENDER_DPI), "-f", str(page), "-l", str(page),
                        str(pdf), str(pfx)], check=True, capture_output=True)
        pngs = sorted(Path(td).glob("pg-*.png"))
        if not pngs:
            raise SystemExit(f"render failed: {pdf.name} p{page}")
        im = Image.open(pngs[0]).convert("RGB")
        w, h = im.size
        l, t, r, b = box
        im.crop((int(w * l), int(h * t), int(w * r), int(h * b))).save(out_png)


def render_eebo_crop(key: str, page: int, box: tuple[float, float, float, float], out: Path) -> None:
    _crop_page(eebo_pdf(key)[0], page, box, out)


def render_ao_crop(alias: str, page: int, box: tuple[float, float, float, float], out: Path) -> None:
    _crop_page(ao_pdf(alias)[0], page, box, out)


Box = tuple[float, float, float, float]

# --- EEBO-grounded placements: (eebo key, page, crop box, identifying_text, ocr second-proof) - #
# crop box = (left, top, right, bottom) as fractions of the rendered page.
GROUNDED: dict[tuple[str, str], dict[str, Any]] = {
    ("ot_front", "title-page"): dict(
        key="ot_holybible", page=1, box=(0.03, 0.02, 0.97, 0.62),
        text="THE HOLY BIBLE FAITHFVLLY TRANSLATED INTO ENGLISH OVT OF THE AVTHENTICAL LATIN, "
             "diligently conferred with the Hebrew, Greek, & other Editions in diuers languages",
        ocr=("ot1-1609", 6)),
    ("ot_front", "approbatio"): dict(
        key="ot_holybible", page=2, box=(0.0, 0.0, 1.0, 0.36),
        text="APPROBATIO. Nos infrascripti, in alma Duacensi vniuersitate Sacrae Theologiae "
             "professores ...", ocr=(None, None)),
    ("ot_front", "preface"): dict(
        key="ot_holybible", page=3, box=(0.0, 0.0, 1.0, 0.36),
        text="TO THE RIGHT WEL-BELOVED ENGLISH READER (running head: TO THE ENGLISH READER)",
        ocr=(None, None)),
    ("nt_front", "title-page"): dict(
        key="nt_partial", page=1, box=(0.05, 0.03, 0.95, 0.66),
        text="THE NEVV TESTAMENT OF IESVS CHRIST, TRANSLATED FAITHFVLLY INTO ENGLISH out of the "
             "authentical Latin ... in the ENGLISH COLLEGE OF RHEMES ... 1582",
        ocr=("nt-1582", None)),
    ("nt_front", "preface"): dict(
        key="nt_partial", page=3, box=(0.0, 0.0, 1.0, 0.36),
        text="THE PREFACE TO THE READER TREATING OF THESE THREE POINTS ...",
        ocr=("nt-1582", 4961)),
    ("nt_front", "censure"): dict(
        key="nt_partial", page=2, box=(0.0, 0.0, 1.0, 0.36),
        text="THE CENSVRE AND APPROBATION. V.M. huius versionis ac editionis authoritate ...",
        ocr=("nt-1582", None)),
}

# --- archive.org-grounded placements (back-matter tables absent from the partial EEBO scans) -- #
# dict: (section, name) -> alias, page, box, identifying_text, djvu char-offset second-proof.
GROUNDED_AO: dict[tuple[str, str], dict[str, Any]] = {
    ("nt_back", "explication-words"): dict(
        alias="nt-1582", page=721, box=(0.0, 0.03, 1.0, 0.22),
        text="THE EXPLICATION OF CERTAINE WORDS IN THIS TRANSLATION, not familiar to the vulgar "
             "Reader, which might not conueniently be vttered otherwise", djvu=None),
    ("nt_back", "table-peter"): dict(
        alias="nt-1582", page=361, box=(0.0, 0.19, 1.0, 0.30),
        text="A TABLE OF S. PETER — a summary of the acts of S. Peter, following the Actes of "
             "the Apostles", djvu=998445),
    ("nt_back", "table-paul"): dict(
        alias="nt-1582", page=362, box=(0.0, 0.16, 1.0, 0.27),
        text="A TABLE OF S. PAVL — a summary of the acts of S. Paul", djvu=1002493),
    ("nt_back", "apostles-creed"): dict(
        alias="nt-1582", page=363, box=(0.0, 0.55, 1.0, 0.70),
        text="THE APOSTLES CREED; or SYMBOLVM APOSTOLORVM", djvu=1006256),
    ("nt_back", "table-corruptions"): dict(
        alias="nt-1582", page=724, box=(0.0, 0.02, 1.0, 0.18),
        text="A TABLE OF HERETICAL CORRVPTIONS (of the sacred text) in this later age of the "
             "Church", djvu=2158711),
    ("nt_back", "table-epistles-gospels"): dict(
        alias="nt-1582", page=730, box=(0.0, 0.02, 1.0, 0.18),
        text="A TABLE OF THE EPISTLES AND GHOSPELS AFTER THE ROMANE VSE, vpon euerie Sunday and "
             "feast throughout the yeare", djvu=None),
    ("nt_back", "table-catholic-truths"): dict(
        alias="nt-1582", page=737, box=(0.0, 0.02, 1.0, 0.36),
        text="AN AMPLE AND PARTICVLAR TABLE DIRECTING THE READER TO THE CATHOLIKE TRVTHS ... "
             "(the Table of Controuersies)", djvu=2179805),
    ("ot_back", "historical-table-age-1"): dict(
        alias="ot2-1610", page=1078, box=(0.0, 0.02, 1.0, 0.16),
        text="AN HISTORICAL TABLE OF THE TIMES, SPECIAL PERSONS, MOST NOTABLE THINGES, AND "
             "CANONICAL BOOKES OF THE OLD TESTAMENT (opening; the table is subdivided into the "
             "six ages of the world)", djvu=2910802),
    ("ot_back", "historical-table-age-4"): dict(
        alias="ot2-1610", page=1086, box=(0.0, 0.0, 1.0, 0.30),
        text="THE BEGINNING OF THE FOVRTH AGE — a subsection of the Historical Table of the Old "
             "Testament", djvu=None),
    ("ot_back", "historical-table-age-6"): dict(
        alias="ot2-1610", page=1097, box=(0.0, 0.0, 1.0, 0.30),
        text="THE BEGINNING OF THE SIXTH AGE — a subsection of the Historical Table of the Old "
             "Testament", djvu=None),
    ("ot_back", "glossary"): dict(
        alias="ot2-1610", page=1102, box=(0.0, 0.02, 1.0, 0.16),
        text="A PARTICVLAR TABLE OF THE MOST PRINCIPAL THINGES CONTEINED IN THE OLD TESTAMENT "
             "(the OT back-matter reference index)", djvu=2937683),
}

# --- co-located slots: printed on a leaf/table already grounded by another slot ------------- #
# `crop_box` renders an own crop of the co-located element; otherwise `crop_of` reuses a crop.
CO_LOCATED: dict[tuple[str, str], dict[str, Any]] = {
    ("ot_front", "privilege"): dict(
        testament="OT", key="ot_holybible", page=1, crop_box=(0.03, 0.62, 0.97, 1.0),
        text="PERMISSV SVPERIORVM. — Printed by IOHN COVSTVRIER. M.DC.XXXV (OT title-page foot). "
             "This 1635 Rouen edition prints the permission as the title-page imprint line; there "
             "is no separate French royal-privilege leaf.",
        note="co-located on the OT First Tome title-page leaf (p.1 foot)"),
    ("ot_front", "censura"): dict(
        testament="OT", key="ot_holybible", page=2, crop_of="ot-approbatio",
        text="Censura / Approbatio co-located on one leaf (OT First Tome, p.2)",
        note="the OT approval is printed as a single APPROBATIO leaf; no separate censura leaf"),
    ("ot_back", "historical-table-age-2"): dict(
        testament="OT", key=None, crop_of="ot-historical-table-age-1",
        text="Second Age — an internal division of the Historical Table of the Old Testament",
        note="subdivision of the one Historical Table (grounded at historical-table-age-1); the "
             "First/Second/Third/Fifth-age headers are OCR-mangled in the dense table and are not "
             "separately cropped"),
    ("ot_back", "historical-table-age-3"): dict(
        testament="OT", key=None, crop_of="ot-historical-table-age-1",
        text="Third Age — an internal division of the Historical Table of the Old Testament",
        note="subdivision of the one Historical Table (grounded at historical-table-age-1)"),
    ("ot_back", "historical-table-age-3b"): dict(
        testament="OT", key=None, crop_of="ot-historical-table-age-1",
        text="Third Age (continued) — an internal division of the Historical Table of the OT",
        note="subdivision of the one Historical Table (grounded at historical-table-age-1)"),
    ("ot_back", "historical-table-age-5"): dict(
        testament="OT", key=None, crop_of="ot-historical-table-age-1",
        text="Fifth Age — an internal division of the Historical Table of the Old Testament",
        note="subdivision of the one Historical Table (grounded at historical-table-age-1); the "
             "Fourth (p.1086) and Sixth (p.1097) ages are separately grounded as anchors"),
}

# --- genuinely absent from every available scan --------------------------------------------- #
UNLOCATABLE: dict[tuple[str, str], dict[str, str]] = {
    ("ot_back", "epistles-table"): dict(
        reason="No 'table of Epistles & Gospels' is printed among the OT back matter: the "
               "archive.org ot2-1610 scan carries the Historical Table (p.~1077-1101) and the "
               "Particular Table of Principal Things (p.~1102-1126), then ends. This appears to "
               "be an NT-only apparatus item (see nt_back table-epistles-gospels) over-enumerated "
               "for the OT."),
}

# --- reference-set slots with no distinct printed header located ---------------------------- #
INVENTORIED: dict[tuple[str, str], dict[str, Any]] = {
    ("nt_back", "evangelical-history"): dict(
        text="evangelical history",
        note="no distinct printed header located in the nt-1582 back matter; the essay 'THE "
             "ACTES OF THE OTHER APOSTLES ... AFTER the Gospels' (nt-1582 p.363) is the nearest "
             "related text. Reference-set slot; not separately grounded."),
    ("nt_back", "scripture-authority"): dict(
        text="scripture authority",
        note="no distinct printed header located in the available NT scans. Reference-set slot; "
             "not separately grounded."),
}

# scan-grounded scripture-layout section/divider leaves (EEBO).
LAYOUT_LEAVES: list[dict[str, Any]] = [
    dict(section="nt", tome="Rheims NT 1582", part="New Testament", key="nt_partial", page=1,
         box=(0.05, 0.03, 0.95, 0.66),
         text="THE NEVV TESTAMENT OF IESVS CHRIST ... ENGLISH COLLEGE OF RHEMES ... 1582"),
    dict(section="ot", tome="Douay OT First Tome (1635 Cousturier reissue)",
         part="general title / Pentateuch", key="ot_holybible", page=1, box=(0.03, 0.02, 0.97, 0.62),
         text="THE HOLY BIBLE FAITHFVLLY TRANSLATED INTO ENGLISH ... M.DC.XXXV (1635)"),
    dict(section="ot", tome="Douay OT First Tome (1635 Cousturier)",
         part="Second Part: Historical Bookes", key="ot_historical", page=1, box=(0.0, 0.0, 1.0, 0.44),
         text="THE SECOND PART OF THE OLD TESTAMENT CONTAINING HISTORICAL BOOKES. "
              "THE ARGVMENT OF THE BOOKE OF IOSVE"),
    dict(section="ot", tome="Douay OT Second Tome (1635 Cousturier reissue)", part="general title",
         key="ot_secondtome", page=1, box=(0.03, 0.02, 0.97, 0.60),
         text="THE SECOND TOME OF THE HOLIE BIBLE FAITHFVLLY TRANSLATED INTO ENGLISH ... "
              "Rouen: Iohn Covsturier ... 1635"),
    dict(section="ot", tome="Douay OT Second Tome (1635 Cousturier)",
         part="Fourth Part: Prophetical Bookes", key="ot_prophetical", page=1, box=(0.0, 0.0, 1.0, 0.44),
         text="THE FOVRTH PART OF THE OLD TESTAMENT CONTAINING PROPHETICAL BOOKES. "
              "The argument of Prophetical bookes in general (leaf printed p.442)"),
]


def testament_of(section: str) -> str:
    return "NT" if section.startswith("nt") else "OT"


def _eebo_witness(key: str, page: int, sha: str) -> dict[str, Any]:
    return {"authority": "eebo", "witness": "eebo_" + EEBO[key][:8], "md5": EEBO[key],
            "sha256": sha, "page": page, "content": EEBO_CONTENT[key]}


def _ao_witness(alias: str, page: int, sha: str) -> dict[str, Any]:
    return {"authority": "archive.org", "witness": "ao_" + alias, "alias": alias,
            "sha256": sha, "page": page, "content": AO_ALIASES[alias]}


def build_placements(apparatus: dict) -> tuple[list[dict], dict]:
    placements: list[dict] = []
    counts = {"grounded": 0, "co-located": 0, "unlocatable": 0, "inventoried": 0}
    CROPS_DIR.mkdir(exist_ok=True)
    for section in ("ot_front", "ot_back", "nt_front", "nt_back"):
        for item in apparatus.get(section, []):
            name = item["name"]
            testament = testament_of(section)
            front_back = "front" if section.endswith("front") else "back"
            slot = f"{testament.lower()}-{name}"
            rec: dict[str, Any] = {
                "slot": slot,
                "apparatus_order_ref": {"section": section, "position": item.get("position"),
                                        "name": name},
                "testament": testament, "tome_position": f"{front_back} · {testament}"}
            g = GROUNDED.get((section, name))
            gao = GROUNDED_AO.get((section, name))
            col = CO_LOCATED.get((section, name))
            unl = UNLOCATABLE.get((section, name))
            inv = INVENTORIED.get((section, name))
            if g:
                _, sha = eebo_pdf(g["key"])
                crop_rel = f"placement-crops/{slot}.png"
                render_eebo_crop(g["key"], g["page"], g["box"], HERE / crop_rel)
                ow, oo = g["ocr"]
                rec.update(status="grounded", source=_eebo_witness(g["key"], g["page"], sha),
                           crop_image=crop_rel, identifying_text=g["text"],
                           ocr_second_proof={"witness": ow, "char_offset": oo})
                counts["grounded"] += 1
            elif gao:
                _, sha = ao_pdf(gao["alias"])
                crop_rel = f"placement-crops/{slot}.png"
                render_ao_crop(gao["alias"], gao["page"], gao["box"], HERE / crop_rel)
                rec.update(status="grounded", source=_ao_witness(gao["alias"], gao["page"], sha),
                           crop_image=crop_rel, identifying_text=gao["text"],
                           ocr_second_proof={"witness": gao["alias"], "char_offset": gao["djvu"]})
                counts["grounded"] += 1
            elif col:
                key = col.get("key")
                crop_rel: Optional[str]
                if col.get("crop_box") and key:
                    _, sha = eebo_pdf(key)
                    crop_rel = f"placement-crops/{slot}.png"
                    render_eebo_crop(key, col["page"], col["crop_box"], HERE / crop_rel)
                    src: Optional[dict[str, Any]] = _eebo_witness(key, col["page"], sha)
                elif col.get("crop_of"):
                    crop_rel = f"placement-crops/{col['crop_of']}.png"
                    src = ({**_eebo_witness(key, col["page"], eebo_pdf(key)[1])}
                           if key else None)
                else:
                    crop_rel, src = None, None
                rec.update(status="co-located", source=src, crop_image=crop_rel,
                           identifying_text=col["text"], note=col["note"])
                counts["co-located"] += 1
            elif unl:
                rec.update(status="unlocatable", crop_image=None,
                           identifying_text=name.replace("-", " "), note=unl["reason"])
                counts["unlocatable"] += 1
            elif inv:
                rec.update(status="inventoried", crop_image=None,
                           identifying_text=inv["text"],
                           ocr_second_proof={"witness": None, "char_offset": None},
                           note=inv["note"])
                counts["inventoried"] += 1
            else:
                # every apparatus-order slot should be explicitly handled above.
                raise SystemExit(f"unhandled apparatus slot: {section}/{name}")
            placements.append(rec)
    return placements, counts


def build_layout() -> list[dict]:
    CROPS_DIR.mkdir(exist_ok=True)
    out = []
    for i, lf in enumerate(LAYOUT_LEAVES):
        _, sha = eebo_pdf(lf["key"])
        crop_rel = f"placement-crops/layout-{i:02d}-{lf['key']}.png"
        render_eebo_crop(lf["key"], lf["page"], lf["box"], HERE / crop_rel)
        out.append({"order": i, "section": lf["section"], "tome": lf["tome"], "part": lf["part"],
                    "title_leaf": {"witness": "eebo_" + EEBO[lf["key"]][:8], "sha256": sha,
                                   "page": lf["page"], "content": EEBO_CONTENT[lf["key"]]},
                    "identifying_text": lf["text"], "crop_image": crop_rel})
    return out


def main() -> int:
    apparatus = json.loads(APPARATUS_ORDER.read_text())
    scripture_layout = build_layout()
    placements, counts = build_placements(apparatus)
    scan_sources: dict[str, Any] = {}
    for key, md5 in EEBO.items():
        pdf, sha = eebo_pdf(key)
        scan_sources["eebo_" + md5[:8]] = {
            "authority": "eebo", "key": key, "md5": md5, "sha256": sha,
            "file": str(pdf.relative_to(REPO)), "content_verified": EEBO_CONTENT[key],
            "verified_via": "rendered title leaf (pdftoppm) — P1.4 visual inspection 2026-07-06"}
    for alias in AO_ALIASES:
        pdf, sha = ao_pdf(alias)
        scan_sources["ao_" + alias] = {
            "authority": "archive.org", "alias": alias, "sha256": sha,
            "file": str(pdf.relative_to(REPO)), "content": AO_ALIASES[alias],
            "verified_via": "OCR text-layer page lookup (pdftotext) + rendered header crop"}
    doc = {
        "artifact": "layout-map", "phase": "P1.4", "idx": 108,
        "generated_by": "build_layout_map.py",
        "note": "Scan-grounded layout & apparatus placement. EEBO facsimile PDFs = primary layout "
                "authority; archive.org full-tome scans (searchable text layer) = fallback "
                "authority for the back-matter tables absent from the partial EEBO facsimiles. "
                "Each grounded leaf/slot carries a committed header crop + transcribed "
                "identifying_text + source sha256, with an OCR offset as second proof where "
                "available. Statuses are honest: grounded / co-located / unlocatable / inventoried. "
                "The EEBO OT scans are the 1635 Rouen reissue (Cousturier, 'Permissu Superiorum'), "
                "not 1609/1610; and the ot_prophetical (55c87902 = Fourth Part) and ot_secondtome "
                "(8ff9c022 = Second Tome title) scans were swapped in the earlier mapping and are "
                "corrected here. Phase-0 seal UNAFFECTED (seal never used EEBO).",
        "scan_sources": scan_sources,
        "scripture_layout": scripture_layout,
        "apparatus_placements": placements,
        "summary": {"apparatus_slots": len(placements), **counts,
                    "scripture_layout_leaves": len(scripture_layout)},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"layout-map.json  ·  {len(placements)} apparatus slots {counts}  ·  "
          f"{len(scripture_layout)} layout leaves  ·  crops -> {CROPS_DIR.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
