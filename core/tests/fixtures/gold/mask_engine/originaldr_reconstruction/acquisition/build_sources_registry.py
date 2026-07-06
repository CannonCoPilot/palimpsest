#!/usr/bin/env python3
"""Phase 0 · P0.5 — provenance registry (the single source index every later phase reads).

Consolidates the four acquisition manifests + the EEBO original-scan PDFs into one
committed `sources-registry.json`: per source — id, witness family, provenance
(remote/commit | URL | archive identifier | file), format(s), spelling & typeset class,
testament coverage, lineage + independence flag, acquisition date, and file sha256(s)
where the upstream manifest carries them. It also emits the `independence_axes` grouping
that P1.3 consensus weighting uses, so lineage collapsing is defined in exactly one place.

Deterministic: pulls every field from the pinned manifests (no network, no clock) —
dates come from the manifests themselves, shas from the download/pin records.

Run:  core/.venv/bin/python <thisfile>   (from repo root or anywhere)
Gate P0 expects our-ocr-manifest.json status == "complete"; until then the our-ocr
witness is recorded as "pending" and the registry prints a NOT-YET-SEALED warning.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent           # .../reconstruction/acquisition
REPO = HERE.parents[6]                            # .../palimpsest
ORIGINAL = REPO / "imports/Scripture/Bibles/DouayRheims_DR/Original"
OUT = HERE / "sources-registry.json"

PINS = json.loads((HERE / "digital-witness-pins.json").read_text())
ARCHIVE = json.loads((HERE / "archive-scans-manifest.json").read_text())
ODR = json.loads((HERE / "odr-scrape-manifest.json").read_text())


def load_our_ocr() -> dict | None:
    p = HERE / "our-ocr-manifest.json"
    return json.loads(p.read_text()) if p.exists() else None


def from_pins() -> list[dict]:
    out = []
    for wid, w in PINS["witnesses"].items():
        out.append({
            "id": wid.replace("-", "_"),
            "family": w.get("provenance", "").split(" ")[0] or wid,
            "provenance": w.get("provenance", ""),
            "remote": w.get("remote", ""),
            "commit": w.get("commit", ""),
            "acquisition_date": w.get("commit_date", PINS.get("pinned_on", "")),
            "form": w.get("form", ""),
            "spelling": w.get("spelling", ""),
            "typeset": w.get("typeset", ""),
            "coverage": w.get("coverage", ""),
            "lineage": w.get("lineage", wid),
            "independent": w.get("independent", wid in ("s-dismas",)),
            "detail_manifest": "digital-witness-pins.json",
        })
    return out


def from_odr() -> dict:
    t = ODR.get("totals", {})
    return {
        "id": "odr_com",
        "family": "originaldouayrheims.com",
        "provenance": "originaldouayrheims.com web edition",
        "remote": ODR.get("base_url", ""),
        "commit": "",
        "acquisition_date": ODR.get("scraped_on", ""),
        "form": "HTML scrape (39 books, %d chapters, %d verses)" % (
            t.get("chapters", 0), t.get("verses", 0)),
        "spelling": "archaic",
        "typeset": "modern",
        "coverage": "12 OT + 27 NT; mean folded agreement %.4f vs Madueke_A" % (
            t.get("mean_folded_agreement", 0.0)),
        "lineage": "odr-com",
        "independent": True,
        "detail_manifest": "odr-scrape-manifest.json",
    }


def from_archive() -> list[dict]:
    main = {"ot1-1609", "ot2-1610", "nt-1582"}
    out = []
    for alias, it in ARCHIVE["items"].items():
        assets = [{"name": f["name"], "sha256": f.get("sha256", ""),
                   "size": f.get("actual_size", f.get("expected_size", 0))}
                  for f in it.get("files", [])]
        testament = "NT" if alias in ("nt-1582", "newtestament") else "OT"
        out.append({
            "id": alias.replace("-", "_"),
            "family": "archive.org (%s)" % ("main" if alias in main else "supplementary"),
            "provenance": "archive.org/details/%s" % it.get("identifier", alias),
            "remote": "https://archive.org/details/%s" % it.get("identifier", alias),
            "commit": "",
            "acquisition_date": ARCHIVE.get("downloaded_on", "2026-07-05"),
            "form": "page scans (jp2) + OCR layers (%s)" % ", ".join(
                sorted({a["name"].rsplit("_", 1)[-1].split(".")[0] for a in assets})),
            "spelling": "archaic",
            "typeset": "archaic",
            "coverage": testament + " print scan",
            "lineage": "archive-%s" % alias,
            "independent": True,
            "detail_manifest": "archive-scans-manifest.json",
            "assets": assets,
        })
    return out


def from_original() -> list[dict]:
    """EEBO original image-scan PDFs (vol 1-5 + NT) — the layout/apparatus authority for P1.4.
    Only the canonical Anna's-Archive-named facsimiles are registered (their filename embeds
    a 32-hex md5); the merged/small Madueke_B PDFs and truncated partial re-downloads sharing
    this directory are excluded (Madueke_B is pinned separately). Deduped by md5; recorded
    without re-hashing GBs."""
    out, seen = [], set()
    if not ORIGINAL.is_dir():
        return out
    for pdf in sorted(ORIGINAL.glob("*.pdf")):
        name = pdf.name
        md5 = next((tok.lower() for tok in name.replace("--", " ").split()
                    if len(tok) == 32 and all(c in "0123456789abcdef" for c in tok.lower())), "")
        if not md5 or md5 in seen:      # skip non-canonical (Madueke_B / partial) + duplicates
            continue
        seen.add(md5)
        low = name.lower()
        if "new testament" in low:
            cov = "NT"
        elif "vol_" in low:
            vol = low.split("vol_", 1)[1].lstrip(" ")[:1]
            cov = f"OT volume {vol}"
        else:
            cov = "OT/NT facsimile"
        out.append({
            "id": "eebo_" + md5[:8],
            "family": "EEBO original image-scan PDF",
            "provenance": "Anna's Archive (EEBO Editions / ProQuest facsimile)",
            "file": str(pdf.relative_to(REPO)),
            "md5_annas": md5,
            "size": pdf.stat().st_size,
            "spelling": "archaic",
            "typeset": "archaic",
            "coverage": cov,
            "lineage": "eebo-original",
            "independent": True,
            "role": "layout & apparatus placement authority (P1.4)",
            "detail_manifest": "(filename-embedded md5)",
        })
    return out


def our_ocr_entry(m: dict | None) -> dict:
    if m is None:
        return {"id": "ocr_consensus", "family": "our fresh OCR (tesseract)",
                "status": "pending", "spelling": "archaic", "typeset": "archaic",
                "lineage": "our-ocr", "independent": True,
                "detail_manifest": "our-ocr-manifest.json"}
    return {
        "id": "ocr_consensus",
        "family": "our fresh OCR (tesseract 5.5.2, majority-consensus)",
        "provenance": "derived: fresh tesseract of archive.org jp2 scans, fused with djvu + hOCR",
        "status": m.get("status", "unknown"),
        "form": "whole-tome page OCR (%d/%d pages)" % (
            m.get("total_done", 0), m.get("total_pages", 0)),
        "spelling": "archaic",
        "typeset": "archaic",
        "coverage": "all 6 archive.org scan sets (OT + NT)",
        "lineage": "our-ocr",
        "independent": True,
        "detail_manifest": "our-ocr-manifest.json",
    }


INDEPENDENCE_AXES = {
    "modern-madueke": ["madueke_a", "madueke_b", "sabates_a"],
    "odr-com": ["odr_com"],
    "s-dismas": ["s_dismas"],
    "archive-scans": ["ot1_1609", "ot2_1610", "nt_1582",
                      "holiebible_ot1", "holiebible_ot2", "newtestament"],
    "our-ocr": ["ocr_consensus"],
    "eebo-original": ["eebo-*"],
    "_note": ("Lineage independence for §4.3 consensus weighting: the modern-Madueke family "
              "(Madueke_A/_B two formats + Madueke-derived Sabates_A) collapses to ONE independent "
              "axis; odr-com, s-dismas, our majority OCR, and each archive.org scan set are "
              "independent. Sabates is NOT independent of Madueke."),
}


def main() -> int:
    ocr_m = load_our_ocr()
    witnesses = (from_pins() + [from_odr()] + from_archive()
                 + from_original() + [our_ocr_entry(ocr_m)])
    sealed = ocr_m is not None and ocr_m.get("status") == "complete"
    registry = {
        "_note": "P0.5 provenance registry — single source index for the OriginalDR reconstruction.",
        "phase0_sealed": sealed,
        "generated_from": ["digital-witness-pins.json", "archive-scans-manifest.json",
                           "odr-scrape-manifest.json", "our-ocr-manifest.json",
                           "imports/.../DouayRheims_DR/Original/*.pdf"],
        "witness_count": len(witnesses),
        "independence_axes": INDEPENDENCE_AXES,
        "witnesses": witnesses,
    }
    OUT.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
    print(f"sources-registry.json · {len(witnesses)} witnesses · phase0_sealed={sealed}")
    for w in witnesses:
        print(f"  {w['id']:16} {w.get('family','')[:44]:44} indep={w.get('independent','?')}")
    if not sealed:
        print("\n⚠ Phase 0 NOT yet sealed — our-ocr manifest is absent or in_progress. "
              "Re-run after ocr_fulltome.py completes to finalize the registry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
