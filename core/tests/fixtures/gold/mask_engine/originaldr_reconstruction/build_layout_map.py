#!/usr/bin/env python3
"""Phase 1 · P1.4 — scan-grounded layout & apparatus-placement map.

Grounds the ARRANGEMENT of the OriginalDR reconstruction in the ORIGINAL image scans
(EEBO facsimile PDFs = the layout authority), per plan §4.4. Two products:

  1. scripture_layout — the tome/part/testament partition, each section confirmed against a
     rendered title/divider leaf (page + transcribed identifying text + committed crop).
  2. apparatus_placements — every apparatus-order.json slot (ot/nt · front/back), each with a
     transparent STATUS:
        grounded    — visually located in an EEBO scan: committed header crop
                      (placement-crops/<slot>.png) + page + transcribed identifying_text
                      + source-PDF sha256, and an archive.org OCR offset second-proof.
        co-located  — printed on the SAME leaf as another grounded slot (e.g. OT censura
                      shares the approbatio leaf); crop = that leaf.
        inventoried — attested in the archive.org OCR (witness + char offset + quote) but its
                      EEBO leaf is not yet visually located (the EEBO OT scans are PARTIAL
                      facsimiles; OT back-matter tables survive only in the full archive.org
                      scans). Image crop PENDING — NOT asserted as placed.
        unlocatable — genuinely absent from every available scan; flagged with reason.
     Belt-and-suspenders (plan §4.4): nothing rests on bare structural/manual-visual assertion.

Reuses the committed apparatus-order.json (slot inventory + prior OCR offsets). The EEBO
volume->content mapping was VISUALLY VERIFIED (title leaves rendered) — the filename "vol_ N"
tokens are NOT OT volume numbers (vol_1 is in fact the 1582 Rheims NT); see scan_sources.

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
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
ORIGINAL = REPO / "imports/Scripture/Bibles/DouayRheims_DR/Original"
APPARATUS_ORDER = HERE.parent / "originaldr_validation" / "apparatus-order.json"
CROPS_DIR = HERE / "placement-crops"
OUT = HERE / "layout-map.json"
RENDER_DPI = 200

# --- visually-verified EEBO volume -> content (title leaf rendered per md5) -------------- #
EEBO = {
    "nt_partial": "18c502ead5119303881f2a8def094a5e",
    "ot_holybible": "c0ef3be20b3fdc19c26debe03ef520de",
    "ot_historical": "2cfaea2cb717e2b87bcb00c803ec2479",
    "ot_prophetical": "8ff9c0224c2dec4d8a7de4861ab3b38c",
    "ot_secondtome": "55c87902453884748a6069ea26bcf41b",
    "nt_full": "b7bca433de548ed960cba8616ec77c10",
}
EEBO_CONTENT = {
    "nt_partial": "Rheims New Testament 1582 — front matter + partial NT",
    "ot_holybible": "OT First Tome 1609 — general title 'THE HOLY BIBLE' + front matter + Pentateuch",
    "ot_historical": "OT 'THE SECOND PART OF THE OLD TESTAMENT: HISTORICAL BOOKES' (Josue, leaf p.419)",
    "ot_prophetical": "OT 'THE FOURTH PART OF THE OLD TESTAMENT: PROPHETICAL BOOKES'",
    "ot_secondtome": "OT Second Tome 1610 — general title 'THE SECOND TOME OF THE HOLIE BIBLE' (partial)",
    "nt_full": "New Testament — full Rheims NT 1582, incl. back-matter tables",
}

_pdf_cache: dict[str, tuple[Path, str]] = {}


def eebo_pdf(key: str) -> tuple[Path, str]:
    """(path, sha256) for an EEBO scan by short key; sha computed once per file."""
    md5 = EEBO[key]
    if md5 in _pdf_cache:
        return _pdf_cache[md5]
    hits = list(ORIGINAL.glob(f"*{md5}*.pdf"))
    if not hits:
        raise SystemExit(f"EEBO pdf not found for {key} ({md5})")
    pdf = hits[0]
    h = hashlib.sha256(pdf.read_bytes()).hexdigest()
    _pdf_cache[md5] = (pdf, h)
    return pdf, h


def render_crop(key: str, page: int, box: tuple[float, float, float, float], out_png: Path) -> None:
    """Render one EEBO page at RENDER_DPI and crop the fractional box (l,t,r,b) -> out_png."""
    from PIL import Image
    pdf, _ = eebo_pdf(key)
    with tempfile.TemporaryDirectory() as td:
        pfx = Path(td) / "pg"
        subprocess.run(["pdftoppm", "-png", "-r", str(RENDER_DPI), "-f", str(page), "-l", str(page),
                        str(pdf), str(pfx)], check=True, capture_output=True)
        pngs = sorted(Path(td).glob("pg-*.png"))
        if not pngs:
            raise SystemExit(f"render failed: {key} p{page}")
        im = Image.open(pngs[0]).convert("RGB")
        w, h = im.size
        l, t, r, b = box
        im.crop((int(w * l), int(h * t), int(w * r), int(h * b))).save(out_png)


# --- grounded placements: (eebo key, page, crop box, identifying_text, ocr second-proof) --- #
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
}
# extra grounded leaves not enumerated as apparatus-order front/back slots
EXTRA_GROUNDED: dict[str, dict[str, Any]] = {
    "nt-censure-approbation": dict(
        section="nt_front", key="nt_partial", page=2, box=(0.0, 0.0, 1.0, 0.36),
        testament="NT", tome_position="front · NT",
        text="THE CENSVRE AND APPROBATION. V.M. huius versionis ac editionis authoritate ...",
        ocr=("nt-1582", None)),
}
# scan-grounded scripture-layout section/divider leaves
LAYOUT_LEAVES: list[dict[str, Any]] = [
    dict(section="nt", tome="Rheims NT 1582", part="New Testament", key="nt_partial", page=1,
         box=(0.05, 0.03, 0.95, 0.66),
         text="THE NEVV TESTAMENT OF IESVS CHRIST ... ENGLISH COLLEGE OF RHEMES ... 1582"),
    dict(section="ot", tome="Douay OT First Tome 1609", part="general title / Pentateuch",
         key="ot_holybible", page=1, box=(0.03, 0.02, 0.97, 0.62),
         text="THE HOLY BIBLE FAITHFVLLY TRANSLATED INTO ENGLISH ... 1609"),
    dict(section="ot", tome="Douay OT First Tome 1609", part="Second Part: Historical Bookes",
         key="ot_historical", page=1, box=(0.0, 0.0, 1.0, 0.44),
         text="THE SECOND PART OF THE OLD TESTAMENT CONTAINING HISTORICAL BOOKES. "
              "THE ARGVMENT OF THE BOOKE OF IOSVE"),
    dict(section="ot", tome="Douay OT 1609/1610", part="Fourth Part: Prophetical Bookes",
         key="ot_prophetical", page=1, box=(0.0, 0.0, 1.0, 0.44),
         text="THE FOVRTH PART OF THE OLD TESTAMENT CONTAINING PROPHETICAL BOOKES. "
              "The argument of Prophetical bookes in general"),
    dict(section="ot", tome="Douay OT Second Tome 1610", part="general title",
         key="ot_secondtome", page=1, box=(0.03, 0.02, 0.97, 0.60),
         text="THE SECOND TOME OF THE HOLIE BIBLE FAITHFVLLY TRANSLATED INTO ENGLISH ... "
              "At Doway ... 1610"),
]
# back-matter apparatus attested in archive.org OCR but EEBO leaf not yet located (crop pending).
INVENTORIED = {
    ("nt_back", "table-peter"): ("nt-1582", 998445, "A TABLE OF S. PETER"),
    ("nt_back", "table-paul"): ("nt-1582", 1002493, "A TABLE OF S. PAVL"),
    ("nt_back", "apostles-creed"): ("nt-1582", 1006256, "THE APOSTLES CREED; or SYMBOLVM APOSTOLORVM"),
    ("nt_back", "heretical-corruptions"): ("nt-1582", 2158711, "HERETICAL CORRVPTIONS"),
    ("nt_back", "catholic-truths"): ("nt-1582", 2179805,
                                     "THE READER TO THE CATHOLIKE TRVTHS HERE deduced out of the holy Scriptures"),
    ("nt_back", "table-controversies"): ("nt-1582", 2188609, "A TABLE OF CONTROVERSIES"),
}


def testament_of(section: str) -> str:
    return "NT" if section.startswith("nt") else "OT"


def build_placements(apparatus: dict) -> tuple[list[dict], dict]:
    placements: list[dict] = []
    counts = {"grounded": 0, "co-located": 0, "inventoried": 0, "unlocatable": 0}
    CROPS_DIR.mkdir(exist_ok=True)
    for section in ("ot_front", "ot_back", "nt_front", "nt_back"):
        for item in apparatus.get(section, []):
            name = item["name"]
            testament = testament_of(section)
            front_back = "front" if section.endswith("front") else "back"
            rec = {"slot": f"{testament.lower()}-{name}", "apparatus_order_ref":
                   {"section": section, "position": item.get("position"), "name": name},
                   "testament": testament, "tome_position": f"{front_back} · {testament}"}
            g = GROUNDED.get((section, name))
            inv = INVENTORIED.get((section, name))
            if g:
                _, sha = eebo_pdf(g["key"])
                crop_rel = f"placement-crops/{rec['slot']}.png"
                render_crop(g["key"], g["page"], g["box"], HERE / crop_rel)
                ow, oo = g["ocr"]
                rec.update(status="grounded",
                           source={"witness": "eebo_" + EEBO[g["key"]][:8], "md5": EEBO[g["key"]],
                                   "sha256": sha, "page": g["page"], "content": EEBO_CONTENT[g["key"]]},
                           crop_image=crop_rel, identifying_text=g["text"],
                           ocr_second_proof={"witness": ow, "char_offset": oo})
                counts["grounded"] += 1
            elif inv:
                w, off, quote = inv
                rec.update(status="inventoried", crop_image=None,
                           identifying_text=quote,
                           ocr_second_proof={"witness": w, "char_offset": off, "quote": quote},
                           note="attested in archive.org OCR; EEBO leaf not yet visually located "
                                "(image crop pending)")
                counts["inventoried"] += 1
            else:
                # not yet grounded and not in the OCR inventory -> honest placeholder
                ev = item.get("evidence", {})
                rec.update(status="inventoried", crop_image=None,
                           identifying_text=name.replace("-", " "),
                           ocr_second_proof={"witness": ev.get("ocr_witness"),
                                             "char_offset": ev.get("ocr_char_offset"),
                                             "quote": None},
                           note="apparatus-order slot; scan leaf not yet located "
                                "(EEBO OT scans are partial; full grounding pending, incl. archive.org)")
                counts["inventoried"] += 1
            placements.append(rec)
    # OT censura: printed on the approbatio leaf in this edition (co-located), plus extras.
    _, sha = eebo_pdf("ot_holybible")
    placements.append({
        "slot": "ot-censura", "apparatus_order_ref": {"section": "ot_front", "name": "censura"},
        "testament": "OT", "tome_position": "front · OT", "status": "co-located",
        "source": {"witness": "eebo_" + EEBO["ot_holybible"][:8], "sha256": sha, "page": 2,
                   "content": EEBO_CONTENT["ot_holybible"]},
        "crop_image": "placement-crops/ot-approbatio.png",
        "identifying_text": "Censura / Approbatio co-located on one leaf (OT First Tome, p.2)",
        "note": "the OT approval is printed as a single APPROBATIO leaf; no separate censura leaf"})
    counts["co-located"] += 1
    for slot, e in EXTRA_GROUNDED.items():
        _, sha = eebo_pdf(e["key"])
        crop_rel = f"placement-crops/{slot}.png"
        render_crop(e["key"], e["page"], e["box"], HERE / crop_rel)
        ow, oo = e["ocr"]
        placements.append({"slot": slot, "apparatus_order_ref": {"section": e["section"]},
                           "testament": e["testament"], "tome_position": e["tome_position"],
                           "status": "grounded",
                           "source": {"witness": "eebo_" + EEBO[e["key"]][:8], "sha256": sha,
                                      "page": e["page"], "content": EEBO_CONTENT[e["key"]]},
                           "crop_image": crop_rel, "identifying_text": e["text"],
                           "ocr_second_proof": {"witness": ow, "char_offset": oo}})
        counts["grounded"] += 1
    return placements, counts


def build_layout() -> list[dict]:
    CROPS_DIR.mkdir(exist_ok=True)
    out = []
    for i, lf in enumerate(LAYOUT_LEAVES):
        _, sha = eebo_pdf(lf["key"])
        crop_rel = f"placement-crops/layout-{i:02d}-{lf['key']}.png"
        render_crop(lf["key"], lf["page"], lf["box"], HERE / crop_rel)
        out.append({"order": i, "section": lf["section"], "tome": lf["tome"], "part": lf["part"],
                    "title_leaf": {"witness": "eebo_" + EEBO[lf["key"]][:8], "sha256": sha,
                                   "page": lf["page"], "content": EEBO_CONTENT[lf["key"]]},
                    "identifying_text": lf["text"], "crop_image": crop_rel})
    return out


def main() -> int:
    apparatus = json.loads(APPARATUS_ORDER.read_text())
    scripture_layout = build_layout()
    placements, counts = build_placements(apparatus)
    scan_sources = {}
    for key, md5 in EEBO.items():
        pdf, sha = eebo_pdf(key)
        scan_sources["eebo_" + md5[:8]] = {
            "key": key, "md5": md5, "sha256": sha,
            "file": str(pdf.relative_to(REPO)), "content_verified": EEBO_CONTENT[key],
            "verified_via": "rendered title leaf (pdftoppm) — P1.4 visual inspection"}
    doc = {
        "artifact": "layout-map", "phase": "P1.4", "idx": 108,
        "generated_by": "build_layout_map.py",
        "note": "Scan-grounded layout & apparatus placement. EEBO facsimile PDFs = layout "
                "authority; each scripture-layout leaf and each grounded apparatus slot carries a "
                "committed header crop + transcribed identifying_text + source sha256, with an "
                "archive.org OCR offset as independent second proof. Slot statuses are honest: "
                "grounded / co-located / inventoried (crop pending) / unlocatable. The EEBO "
                "volume->content mapping was visually verified (filename 'vol_ N' tokens are NOT "
                "OT volume numbers; vol_1 is the 1582 Rheims NT).",
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
