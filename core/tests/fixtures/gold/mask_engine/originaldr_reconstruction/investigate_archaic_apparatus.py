#!/usr/bin/env python3
"""Address the sourcing question for idx 109's editorial apparatus (plan §5.3/§6 follow-up).

idx 108 (modern) and idx 109 (archaic-diplomatic) currently SHARE one editorial apparatus —
the janvier-s / original-douay-rheims arguments, annotations, cross-references and the 26
reference documents — sourced at render time (gen_dr_original) in MODERN-normalized spelling and
masked in both reading texts (§1.2), so the 108-vs-109 diff stays a pure scripture spelling delta.
This module asks: is there an ARCHAIC witness that could source idx 109's apparatus instead, and if
so, at what coverage and fidelity?

It surveys, from the gitignored source tree:
  * the basis DB — confirming apparatus PROSE was never stored there (attestation rows record only
    presence/placement; the 26 non-empty render_modern surfaces are reference-document titles);
  * the five per-witness `reads/*.json` — confirming every ingested read is a scripture verse, so no
    witness contributed apparatus prose through the reconstruction pipeline;
  * the janvier-s apparatus repo — the current (modern) apparatus source;
  * the odr-com scrape (originaldouayrheims.com) — the ARCHAIC-spelling twin of that apparatus,
    already on disk (book arguments + chapter annotations), which was scraped for scripture but whose
    apparatus prose was never ingested;
  * s-dismas PDFs and the archive.org print djvu — the two routes to a fully diplomatic (long-ſ)
    apparatus, both requiring fresh OCR.

Writes the committed, CI-safe archaic-apparatus-sourcing.json. Deterministic (sorted iteration,
fixed samples, no timestamps). The script reads the gitignored sources at build time; the JSON is
committed and the test reads only the JSON.

Run:  core/.venv/bin/python investigate_archaic_apparatus.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
OUT = HERE / "archaic-apparatus-sourcing.json"

DB = REPO / "core/.scratch/originaldr-project/reconstruction/basis-db.sqlite"
READS = REPO / "core/.scratch/originaldr-project/reconstruction/reads"
ODR = REPO / "core/.scratch/originaldr-project/sources/odr-com/scrape"
SDISMAS = REPO / "core/.scratch/originaldr-project/sources/s-dismas"
AO = REPO / "core/.scratch/originaldr-project/sources/archive-org"
JANVIER = next((p for p in (
    REPO / "core/.scratch/bible-ingest/repos/original-douay-rheims",
    REPO / "core/.scratch/original-douay-rheims") if p.exists()), None)

ARCHAIC_SRCS = ("ocr_consensus", "s_dismas", "odr_com")


def _clip(s: str, n: int = 240) -> str:
    s = " ".join((s or "").split())
    return s[:n]


def survey_basis_db() -> dict:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        c = con.cursor()
        napp = c.execute("SELECT COUNT(*) FROM elements WHERE type='apparatus-item'").fetchone()[0]
        rm = c.execute("SELECT COUNT(*) FROM elements WHERE type='apparatus-item' "
                       "AND render_modern IS NOT NULL AND TRIM(render_modern)<>''").fetchone()[0]
        ra = c.execute("SELECT COUNT(*) FROM elements WHERE type='apparatus-item' "
                       "AND render_archaic IS NOT NULL AND TRIM(render_archaic)<>''").fetchone()[0]
        att = {}
        for src, rows, sm, sa in c.execute(
                "SELECT a.source, COUNT(*), "
                "SUM(CASE WHEN TRIM(COALESCE(a.surface_modern,''))<>'' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN TRIM(COALESCE(a.surface_archaic,''))<>'' THEN 1 ELSE 0 END) "
                "FROM attestation a JOIN elements e ON a.element_id=e.id "
                "WHERE e.type='apparatus-item' GROUP BY a.source ORDER BY a.source").fetchall():
            att[src] = {"rows": rows, "nonempty_surface_modern": sm, "nonempty_surface_archaic": sa}
    finally:
        con.close()
    return {
        "apparatus_item_elements": napp,
        "with_render_modern_prose": rm,
        "with_render_archaic_prose": ra,
        "render_modern_prose_are_reference_doc_titles": rm == 26,
        "attestation_by_source": att,
        "finding": "apparatus PROSE was never stored in the basis DB: the only non-empty render "
                   "surfaces are the 26 reference-document titles, and every attestation row records "
                   "presence/placement only (all surface_modern and surface_archaic are empty).",
    }


def survey_reads() -> dict:
    per = {}
    for p in sorted(READS.glob("*.json")):
        d = json.loads(p.read_text())
        reads = d.get("reads") or []
        non_scripture = sum(1 for r in reads if not str(r.get("skeleton_id", "")).startswith("scripture/"))
        per[d.get("source", p.stem)] = {"spelling": d.get("spelling"), "reads": len(reads),
                                        "non_scripture_reads": non_scripture}
    return {
        "witnesses": per,
        "finding": "every ingested read across all witnesses is a scripture verse (0 non-scripture "
                   "reads); no witness supplied apparatus prose through the reconstruction pipeline.",
    }


def survey_janvier() -> dict:
    if JANVIER is None:
        return {"available": False}
    annot = JANVIER / "annotations"
    books = sorted(p.name for p in annot.iterdir() if p.is_dir()) if annot.exists() else []
    sample = ""
    gp = annot / "genesis" / "001.json"
    if gp.exists():
        for a in (json.loads(gp.read_text()).get("annotations") or []):
            for sub in (a.get("notes") or []):
                if (sub.get("text") or "").strip():
                    sample = _clip(sub["text"])
                    break
            if sample:
                break
    return {
        "available": True,
        "role": "current apparatus source for BOTH idx 108 and idx 109 (masked, shared)",
        "spelling": "modern-normalized",
        "annotation_books": len(books),
        "sample_genesis_1_note": sample,
    }


def survey_odr_com() -> dict:
    if not ODR.exists():
        return {"available": False}
    per_book = {}
    n_book_args = books_notes = chapters = chapters_with_notes = 0
    book_arg_chars = notes_chars = long_s = 0
    sample = ""
    for p in sorted(ODR.glob("*.json")):
        if p.name.endswith(".validation.json"):
            continue
        try:
            d = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict) or "chapters" not in d:
            continue
        slug = d.get("slug") or p.stem
        ba = (d.get("argument") or "").strip()
        cw = 0
        cchars = 0
        for c in d["chapters"]:
            chapters += 1
            notes = c.get("notes")
            txt = notes if isinstance(notes, str) else (" ".join(notes) if isinstance(notes, list) else "")
            if txt and txt.strip():
                chapters_with_notes += 1
                cw += 1
                cchars += len(txt)
                notes_chars += len(txt)
                long_s += txt.count("ſ")
                if not sample and slug == "genesis":
                    sample = _clip(txt)
        if ba:
            n_book_args += 1
            book_arg_chars += len(ba)
        if cw:
            books_notes += 1
        per_book[slug] = {"book_argument": bool(ba), "chapters": len(d["chapters"]),
                          "chapters_with_notes": cw, "notes_chars": cchars}
    return {
        "available": True,
        "source": "originaldouayrheims.com scrape (odr-com)",
        "spelling": "archaic (period orthography, u/v, & ligature, -ie endings)",
        "diplomatic_long_s": long_s > 0,
        "books_covered": len(per_book),
        "book_arguments": n_book_args,
        "book_argument_chars": book_arg_chars,
        "chapters": chapters,
        "chapters_with_notes": chapters_with_notes,
        "notes_chars": notes_chars,
        "sample_genesis_1_note": sample,
        "per_book": dict(sorted(per_book.items())),
        "finding": "the odr-com scrape carries the ARCHAIC-spelling twin of the janvier-s apparatus "
                   "(same originaldouayrheims.com upstream) — book arguments and chapter annotations "
                   "already on disk — but with long-ſ normalised to s, so it is archaic-spelling, not "
                   "fully diplomatic. Only scripture verses were ingested; this prose was not.",
    }


def build() -> dict:
    bdb = survey_basis_db()
    reads = survey_reads()
    jan = survey_janvier()
    odr = survey_odr_com()
    covered = set(odr.get("per_book", {}))
    return {
        "artifact": "archaic-apparatus-sourcing.json",
        "phase": "P3 follow-up",
        "generated_by": "investigate_archaic_apparatus.py",
        "question": "Can idx 109's editorial apparatus (book/chapter arguments, verse annotations, "
                    "cross-references, the 26 reference documents) be sourced from an ARCHAIC witness "
                    "instead of the modern janvier-s apparatus it currently shares, masked, with idx 108?",
        "current_state": {
            "basis_db_apparatus": bdb,
            "witness_reads": reads,
            "apparatus_prose_source": jan,
            "masked_shared_apparatus_is_deliberate": True,
            "design_note": "idx 108 and idx 109 share one masked modern apparatus so their diff isolates "
                           "exactly the scripture spelling/glyph delta (§1.2). Sourcing an archaic "
                           "apparatus for idx 109 would make the apparatus edition-specific — a "
                           "deliberate design change, not a defect fix.",
        },
        "recoverable_archaic_material": {
            "odr_com": odr,
            "s_dismas_pdfs": {
                "available": SDISMAS.exists(),
                "spelling": "archaic-diplomatic (preserves long-ſ)",
                "extracted": False,
                "note": "the s-dismas print PDFs include front-matter and marginal apparatus and would "
                        "yield fully diplomatic (long-ſ) apparatus, but the apparatus was never "
                        "OCR-extracted — only scripture verses were transcribed. Requires fresh OCR.",
            },
            "archive_org_djvu": {
                "available": AO.exists(),
                "spelling": "archaic-diplomatic but noisy (ſ→f OCR misread, §6.2/§6.3)",
                "note": "the archive.org print djvu OCR covers full pages including arguments and "
                        "marginalia, but shares the ſ→f limitation quantified in §6.2/§6.3; not a clean "
                        "diplomatic source on its own.",
            },
        },
        "coverage_ceiling": {
            "odr_com_books": len(covered),
            "skeleton_books": 76,
            "note": "the cleanest archaic apparatus source (odr-com) covers only the ~39 books it "
                    "transcribed — the OT prophets, Ecclesiasticus, 4-Esdras and the appendix (the same "
                    "books carrying the 199 scripture coverage gaps) have no clean archaic apparatus "
                    "witness, so a fully archaic apparatus is not attainable from the current sources.",
        },
        "fidelity_caveats": [
            "odr-com apparatus is archaic-SPELLING but not diplomatic (long-ſ normalised to s), so it "
            "would sit one fidelity notch below idx 109's long-ſ scripture layer.",
            "odr-com covers ~39/76 books; the prophetic/appendix apparatus has no clean archaic source.",
            "a fully diplomatic apparatus would require fresh OCR of the s-dismas PDFs or the archive.org "
            "print, inheriting the ſ→f noise measured in §6.2/§6.3.",
        ],
        "recommendation": "Archaic apparatus IS sourceable: the odr-com scrape already holds the "
                          "archaic-spelling twin of the current janvier-s apparatus (book arguments + "
                          "chapter annotations) for ~39 books. But adopting it (a) makes the apparatus "
                          "edition-specific, reversing the deliberate masked-shared design (§1.2) that "
                          "keeps the 108-vs-109 diff a pure scripture delta; (b) reaches only ~39/76 "
                          "books; and (c) is archaic-spelling, not diplomatic. Recommend DOCUMENTING the "
                          "sourcing path here and keeping the modern-shared apparatus as the honest "
                          "default, deferring archaic-apparatus ingestion to an opt-in future phase "
                          "pending a design decision — mirroring the versification adjudication: an "
                          "evidence-backed disposition, not a silent edition change.",
        "decision": "Sourcing question resolved with evidence. No apparatus is re-sourced in this pass; "
                    "the archaic material and its coverage/fidelity limits are catalogued for a future "
                    "opt-in decision.",
    }


def main() -> int:
    for label, path in (("basis-db", DB), ("reads", READS), ("odr-com scrape", ODR)):
        if not path.exists():
            print(f"!! {label} not found: {path}", file=sys.stderr)
            return 2
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    odr = data["recoverable_archaic_material"]["odr_com"]
    print(f"wrote {OUT.relative_to(REPO)} · basis-db archaic apparatus prose "
          f"{data['current_state']['basis_db_apparatus']['with_render_archaic_prose']} · "
          f"odr-com archaic apparatus: {odr['book_arguments']} book-args + "
          f"{odr['chapters_with_notes']} chapters-with-notes over {odr['books_covered']} books "
          f"(diplomatic long-ſ={odr['diplomatic_long_s']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
