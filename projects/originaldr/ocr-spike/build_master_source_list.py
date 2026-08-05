#!/usr/bin/env python3
"""Master source list — QC-framework witness denominator (Revision 2026-07-08).

Rewritten for the locus-level QC contract (sparkling §0′ / partitioned-watching-dijkstra.md):

  * COVERAGE = individual physical source counts as ONE witness per locus, iff it localizes AND
    passes the char-level identity bar (the pass/fail itself is decided per-locus by qc_audit.py in
    Phase 1 — here we enumerate the *structural* witness roster + its expected depth E(v)).
  * Each source carries its highest-resolution raster designation (best_raster) grounded in the
    manifest v2 measured resolution verdicts (2026-07-07), plus its current diplomatic-OCR status and
    a reocr_needed flag where the best-raster OCR is a gap/benched/locate-failure.
  * Madueke_a is DEMOTED to a localization-aid for Madueke_b (NOT an independent witness).
  * The downloaded pre-existing archive.org machine OCR (`downloaded-ocr/`, ſ-normalized) is EXCLUDED
    from coverage + consensus until further notice (parked on disk). NB: this is DISTINCT from our own
    diplomatic OCR dirs named `archive-*` (produced from jp2 masters via the retired archive: adapter)
    — those are best-raster diplomatic witnesses and are KEPT.
  * S03 (OT, 2 vols) + S04 (NT) are GROUPED as one whole-bible witness.
  * Per-testament E(v): NT=12, OT=6 baseline (ranges to ~10 for early-OT books).

Supersedes the R10 usage-denominator MSL; that output is preserved as master-source-list.json.pre-QC-framework.
Emits: master-source-list.json + a human-readable console report.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Any

DR = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/DouayRheims_DR")
SCRATCH = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr")
OCR_ROOT = SCRATCH / "sources/our-ocr-diplomatic"
READS = SCRATCH / "reconstruction/reads"
SUMMARY = SCRATCH / "ocr-spike/consensus-full/_summary.json"  # old consensus (informational only)
MANIFEST = DR / "sources/dr-sources-manifest.json"
OUT = Path(os.environ["MSL_OUT"]) if os.environ.get("MSL_OUT") else SCRATCH / "ocr-spike/master-source-list.json"

# Expected witness count per locus (warn/flag, not a cap) — QC contract §1.1.
E_V = {"NT": 12, "OT": {"baseline": 6, "range": [6, 10]}, "apparatus_min_unblock": 3}

# ---------------------------------------------------------------------------------------------------
# Per-volume witness table. Keyed (manifest source, file-stem|None) to match iter_scan_volumes().
# best_raster + dims are the machine-readable distillation of the manifest v2 measured resolution
# prose (2026-07-07). ocr_dir = the best-raster diplomatic OCR namespace under our-ocr-diplomatic/.
# reocr = None means the best-raster OCR is present & adequate; a string states the required re-OCR.
# ---------------------------------------------------------------------------------------------------
VOL = {
    ("S1", "ot1-1609"): dict(raster="jp2-master", dims="3334x4684", ocr_dir="archive-ot1-1609",
                             reocr=None, note="jp2-derived diplomatic OCR (retired archive: adapter) = best raster"),
    ("S1", "ot2-1610"): dict(raster="jp2-master", dims="3334x4684", ocr_dir="archive-ot2-1610",
                             reocr=None, note="jp2-derived diplomatic OCR = best raster"),
    ("S1", "nt-1582"): dict(raster="master(low)", dims="800x1124", ocr_dir="archive-nt-1582",
                            reocr=None, note="jp2 master itself is 800x1124 low-res — no higher raster exists; NT locate-recall low (R10)"),
    ("S2", None): dict(raster="pdf-content", dims="2262x3116", ocr_dir="pdf-S02",
                       reocr="full diplomatic OCR from pdf-content 2262x3116 (only 10pp benched)"),
    ("S3", "S03a"): dict(raster="pdf-content", dims="2262x3116", ocr_dir="pdf-S03a", reocr=None),
    ("S3", "S03b"): dict(raster="pdf-content", dims="2196x2999", ocr_dir="pdf-S03b",
                         reocr=None, note="vol2 locate-recall low (R10)"),
    ("S4", None): dict(raster="jp2-master", dims="3659x5134", ocr_dir="jp2-S04", reocr=None),
    ("S5", None): dict(raster="pdf-content", dims="2439x3423", ocr_dir="pdf-S05",
                       reocr="full diplomatic OCR from pdf-content 2439x3423 (never OCR'd; 'archive-newtestament' was a 16pp benched stub)"),
    ("S6", None): dict(raster="jp2-master", dims="5100x6601", ocr_dir="jp2-S06",
                       reocr=None, note="bitonal→grayscale jp2 aids ſ/f disambiguation"),
    ("S8", None): dict(raster="jp2-master", dims="6070x8672", ocr_dir="jp2-S08", reocr=None),
    ("S9", "nevvtestamentofi00mart-NT"): dict(raster="pdf-content", dims="3148x4342", ocr_dir="pdf-S09nt", reocr=None),
    ("S9", "holiebiblefaithf00mart_0-OT1"): dict(raster="pdf-content", dims="3148x4342",
                                                 ocr_dir="archive-holiebible-ot1", reocr=None,
                                                 note="OT vol1 under-recalled (R10)"),
    ("S9", "holiebiblefaithf00mart-OT2"): dict(raster="pdf-content", dims="3148x4342",
                                               ocr_dir="archive-holiebible-ot2",
                                               reocr="full diplomatic OCR from pdf-content 3148x4342 (mart OT vol2 never OCR'd)"),
    ("S10", None): dict(raster="eebo-scan", dims="1024x1415", ocr_dir="eebo-nt",
                        reocr=None, note="low-res 72ppi reprint"),
    ("S11", None): dict(raster="eebo-scan", dims="500ppi-bitonal", ocr_dir="eebo-vol1",
                        reocr=None, note="partial sampler: NT front + Matthew only"),
    ("S12", None): dict(raster="eebo-scan", dims="2862x4143", ocr_dir="eebo-vol2",
                        reocr=None, note="Genesis + OT front only"),
    ("S13", None): dict(raster="eebo-scan", dims="bitonal", ocr_dir="eebo-vol3",
                        reocr=None, note="josue only"),
    ("S14", None): dict(raster="eebo-scan", dims="bitonal", ocr_dir="eebo-vol4",
                        reocr="LAYOUT-AWARE re-OCR: Psalms columnar/inline-annotation locate failure (R7) — PILOT target"),
    ("S15", None): dict(raster="eebo-scan", dims="bitonal", ocr_dir="eebo-vol5",
                        reocr=None, note="isaie only"),
}

# Per-source witness metadata. group = witness-grouping id (S3+S4 are ONE whole-bible witness).
WITNESS_META: dict[str, dict[str, Any]] = {
    "S1": dict(ev_role="whole-bible", testaments=["OT", "NT"], group="S1"),
    "S2": dict(ev_role="ot-additional", testaments=["OT"], group="S2", span="Genesis-Job (OT part 1)"),
    "S3": dict(ev_role="whole-bible", testaments=["OT"], group="S3+S4"),
    "S4": dict(ev_role="whole-bible", testaments=["NT"], group="S3+S4"),
    "S6": dict(ev_role="whole-bible", testaments=["OT", "NT"], group="S6"),
    "S9": dict(ev_role="whole-bible", testaments=["OT", "NT"], group="S9"),
    "S5": dict(ev_role="nt-additional", testaments=["NT"], group="S5"),
    "S8": dict(ev_role="nt-additional", testaments=["NT"], group="S8"),
    "S10": dict(ev_role="nt-additional", testaments=["NT"], group="S10"),
    "S11": dict(ev_role="nt-additional", testaments=["NT"], group="S11", span="Matthew (partial sampler)"),
    "S12": dict(ev_role="ot-additional", testaments=["OT"], group="S12", span="Genesis"),
    "S13": dict(ev_role="ot-additional", testaments=["OT"], group="S13", span="josue"),
    "S14": dict(ev_role="ot-additional", testaments=["OT"], group="S14", span="psalms"),
    "S15": dict(ev_role="ot-additional", testaments=["OT"], group="S15", span="isaie"),
}

# Structural witness roster (individual-source count). Grouped: S03+S04 = one whole-bible witness.
WITNESS_ROSTER = {
    "whole_bible": ["sabates_a", "madueke_b", "S1", "S3+S4", "S6", "S9"],
    "nt_additional": ["S5", "S8", "S10", "S11", "s_dismas", "odr_com"],
    "ot_additional": ["S2", "S12", "S13", "S14", "S15", "s_dismas", "odr_com"],
    "localization_aid": ["madueke_a"],
    "excluded": ["downloaded-ocr x6 (archive.org machine OCR, ſ-normalized)",
                 "S7 (byte-dup of S6)", "Haydock", "Challoner", "stray dups"],
}

# ---------------------------------------------------------------------------------------------------
# Provenance spine (P0, rev 2026-07-08): lineage_group + independent on every witness.
#   * lineage_group ∈ LINEAGE_ENUM — the correlated-source family a witness belongs to.
#   * independent = False for the modern Madueke/Sabates/Janvier lineage (they count as ONE vote for
#     the cross-lineage ≥3-witness apparatus unblock, dijkstra §1.5 / sparkling §4.3); True for the
#     print scans and the archaic-print-line (s_dismas/odr_com) — i.e. "outside the modern lineage".
# ---------------------------------------------------------------------------------------------------
LINEAGE_ENUM = ("madueke-family", "sabates-derived", "archaic-print-line",
                "scan-archive-org", "scan-eebo")
LINEAGE: dict[str, tuple[str, bool]] = {
    "S1": ("scan-archive-org", True), "S2": ("scan-archive-org", True),
    "S3": ("scan-archive-org", True), "S4": ("scan-archive-org", True),
    "S5": ("scan-archive-org", True), "S6": ("scan-archive-org", True),
    "S8": ("scan-archive-org", True), "S9": ("scan-archive-org", True),
    "S10": ("scan-eebo", True), "S11": ("scan-eebo", True), "S12": ("scan-eebo", True),
    "S13": ("scan-eebo", True), "S14": ("scan-eebo", True), "S15": ("scan-eebo", True),
    "sabates_a": ("sabates-derived", False),
    "madueke_a": ("madueke-family", False), "madueke_b": ("madueke-family", False),
    "s_dismas": ("archaic-print-line", True), "odr_com": ("archaic-print-line", True),
}


def lineage_for(source: str) -> tuple[str, bool]:
    """(lineage_group, independent) for a witness source id. MADUEKE-src(...) → madueke-family."""
    if source in LINEAGE:
        return LINEAGE[source]
    if source.startswith("MADUEKE-src"):
        return ("madueke-family", False)
    raise KeyError(f"no lineage mapping for witness {source!r}")


def base_record(source: str, kind: str, counts_as_witness: bool, ev_role: str | None,
                testaments: list[str] | None, witness_group: str | None,
                sha: str | None) -> dict:
    """The common join-core every witness record shares (P0 schema unification).

    Before P0 the three witness kinds (scan / transcription / madueke-source) each hand-built
    heterogeneous dicts, so no single key set could join them. This yields the shared spine —
    {source, kind, counts_as_witness, ev_role, testaments, witness_group, sha256, lineage_group,
    independent} — onto which each kind then .update()s its kind-specific fields."""
    lineage_group, independent = lineage_for(source)
    assert lineage_group in LINEAGE_ENUM, f"lineage {lineage_group!r} not in LINEAGE_ENUM"
    return {
        "source": source,
        "kind": kind,
        "counts_as_witness": counts_as_witness,
        "ev_role": ev_role,
        "testaments": testaments or [],
        "witness_group": witness_group or source,
        "sha256": sha,
        "lineage_group": lineage_group,
        "independent": independent,
    }


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rollup_sha(shas: list[str | None]) -> str | None:
    """Deterministic witness-level content hash (mini-Merkle root) from its volume shas.
    None if no shas present; the single hash if exactly one; else the sha256 of the sorted,
    '|'-joined volume hashes — sort makes it order-independent so a multi-volume witness always
    yields one join-stable value regardless of manifest volume ordering."""
    present = [s for s in shas if s]
    if not present:
        return None
    if len(present) == 1:
        return present[0]
    return hashlib.sha256("|".join(sorted(present)).encode()).hexdigest()


def ocr_pages(dirname: str | None) -> int:
    if not dirname:
        return -1
    d = OCR_ROOT / dirname
    if not d.is_dir():
        return -1
    return sum(1 for p in d.glob("*.json") if not p.name.startswith("_"))


def ocr_status(pages: int, reocr: str | None) -> str:
    if reocr:
        if "layout-aware" in reocr.lower() or "R7" in reocr:
            return "LOCATE_FAILED"
        return "BENCHED/PARTIAL" if pages > 0 else "NOT_OCR'D"
    return "OK" if pages > 20 else ("BENCHED/PARTIAL" if pages >= 0 else "NOT_OCR'D")


def iter_scan_volumes(src: dict):
    """Yield one dict per volume: {stem, coverage, role, archive_item, sha256, file}.

    Multi-volume sources (S1/S3/S9) carry volumes[] each with its own sha256; flat single-volume
    sources (S2/S4/S5/S6/S8/S10–S15) carry the fields at the top level. Flat volumes yield stem=None
    so the (source, None) VOL-table key matches (the VOL table keys flat sources by None, not by their
    file stem). sha256 here is the manifest's REAL per-volume content hash — propagated, not fabricated."""
    vols = src.get("volumes")
    if vols:
        for v in vols:
            yield {"stem": Path(v.get("file", "")).stem or None,
                   "coverage": v.get("coverage"), "role": v.get("role"),
                   "archive_item": v.get("archive_item"), "sha256": v.get("sha256"),
                   "file": v.get("file")}
    else:
        yield {"stem": None, "coverage": src.get("coverage"), "role": src.get("role"),
               "archive_item": src.get("archive_item"), "sha256": src.get("sha256"),
               "file": src.get("file")}


def find_pdf(patterns: list[str]) -> Path | None:
    for pat in patterns:
        hits = sorted(DR.glob(pat))
        if hits:
            return max(hits, key=lambda x: x.stat().st_size)
    return None


def main() -> int:
    man = json.loads(MANIFEST.read_text())
    # old consensus is informational only under the QC framework; tolerate its absence
    used_scan: set[str] = set()
    used_text: set[str] = set()
    if SUMMARY.exists():
        summ = json.loads(SUMMARY.read_text())
        for b in summ["books"]:
            used_scan |= set(b.get("scan_sources", []))
            used_text |= set(b.get("text_witnesses", []))

    witnesses: list[dict] = []
    excluded: list[dict] = []

    # ---- scan witnesses (individual-source count; best-raster designation) ----
    for src in man["scan_sources"]:
        sid = src["source"]
        if str(src.get("status", "")).startswith("EXCLUDE") or sid == "S7":
            excluded.append({"source": sid, "kind": "scan-exclusion",
                             "reason": src.get("finding") or src.get("status") or "byte-dup of S6"})
            continue
        meta = WITNESS_META.get(sid, {})
        vol_entries = []
        for vd in iter_scan_volumes(src):
            stem = vd["stem"]
            vm = VOL.get((sid, stem), {})
            ocrname = vm.get("ocr_dir")
            pages = ocr_pages(ocrname)
            vol_entries.append({
                "role": vd["role"], "coverage": vd["coverage"], "file_stem": stem,
                "archive_item": vd["archive_item"], "file": vd["file"], "sha256": vd["sha256"],
                "best_raster": vm.get("raster"), "raster_dims": vm.get("dims"),
                "ocr_dir": ocrname, "ocr_pages": pages,
                "ocr_status": ocr_status(pages, vm.get("reocr")),
                "reocr_needed": vm.get("reocr"),
                "note": vm.get("note"),
                "in_old_consensus": bool(ocrname and ocrname in used_scan),
            })
        witness_sha = rollup_sha([v["sha256"] for v in vol_entries])
        rec = base_record(sid, "scan", True, meta.get("ev_role"), meta.get("testaments"),
                          meta.get("group", sid), witness_sha)
        rec.update({
            "title": src.get("title"), "span": meta.get("span"),
            "coverage": src.get("coverage"), "apparatus": src.get("apparatus"),
            "reocr_needed": any(v["reocr_needed"] for v in vol_entries),
            "volumes": vol_entries,
        })
        witnesses.append(rec)

    # ---- transcription witnesses (auto-pass identity, must still localize per QC §1.2) ----
    TRANS_META: dict[str, dict[str, Any]] = {
        "sabates_a": dict(ev_role="whole-bible", role="modern baseline (Janvier)", identity="modern-gold",
                          witness=True, testaments=["OT", "NT"]),
        "madueke_a": dict(ev_role="localization-aid", role="localization aid for madueke_b ONLY (not an independent witness)",
                          identity="n/a", witness=False, testaments=[]),
        "madueke_b": dict(ev_role="whole-bible", role="modern transcription (apparatus-rich)", identity="modern",
                          witness=True, testaments=["OT", "NT"]),
        "s_dismas": dict(ev_role="archaic-ref", role="archaic ſ-diplomatic reference (Genesis→Wisdom + NT)",
                         identity="archaic-gold", witness=True, testaments=["OT", "NT"]),
        "odr_com": dict(ev_role="archaic-ref", role="archaic-spelling ſ-normalized (partial; weak ſ ref)",
                        identity="archaic-weak", witness=True, testaments=["OT", "NT"]),
    }
    for name, tm in TRANS_META.items():
        p = READS / f"{name}.json"
        if not p.exists():
            rec = base_record(name, "transcription", tm["witness"], tm["ev_role"],
                              tm["testaments"], name, None)
            rec.update({"status": "MISSING", "role": tm["role"], "identity_class": tm["identity"]})
            witnesses.append(rec)
            continue
        d = json.loads(p.read_text())
        books = {r["skeleton_id"].split("/")[1] for r in d.get("reads", [])
                 if r.get("skeleton_id", "").startswith("scripture/")}
        marks = sum(sum(r.get("surface", "").count(m) for m in "ſæœ") for r in d.get("reads", []))
        rec = base_record(name, "transcription", tm["witness"], tm["ev_role"],
                          tm["testaments"], name, sha256(p))
        rec.update({
            "role": tm["role"], "identity_class": tm["identity"],
            "n_reads": len(d.get("reads", [])), "n_books": len(books), "archaic_marks": marks,
            "in_old_consensus": name in used_text,
        })
        witnesses.append(rec)

    # ---- Madueke source PDFs (grouped under Madueke; madueke_a source = localization aid) ----
    mad_b = find_pdf(["sources/transcriptions/madueke/madueke-b__Original-Douay-Rheims-Bible-Merged.pdf"])
    mad_a = find_pdf(["sources/transcriptions/madueke/madueke-a__Original-Douay-Rheims-Bible.pdf"])
    for f, who in ((mad_b, "madueke_b"), (mad_a, "madueke_a")):
        if f:
            rec = base_record(f"MADUEKE-src({who})", "scan-source-of-transcription", False,
                              "source-doc", [], f"MADUEKE({who})", sha256(f))
            rec.update({"role": f"source document for {who}", "disk_file": str(f),
                        "size_mb": round(f.stat().st_size / 1e6, 1)})
            witnesses.append(rec)

    # ---- EXCLUDED: downloaded pre-existing archive.org machine OCR (parked per QC §1.2) ----
    for d in man.get("downloaded_ocr_sources", []):
        excluded.append({"source": f"downloaded-ocr:{d.get('maps_to')}", "kind": "downloaded-ocr",
                         "status": "EXCLUDED (parked until further notice)",
                         "reason": "third-party archive.org machine OCR, ſ-normalized (modern spelling); "
                                   "not a diplomatic witness — held out of coverage + consensus per QC contract §1.2",
                         "location": d.get("location"), "spelling": d.get("spelling")})

    # ---- EXCLUDED on disk (Haydock/Challoner + stray dups) ----
    for pat, why in [("Haydock/*.pdf", "Haydock 2014 annotated edition — NOT a source (Sir)"),
                     ("**/*halloner*.pdf", "Challoner revision — NOT the original DR text (Sir)"),
                     ("sources/_excluded/*.pdf", "quarantined byte-dup / bad download (audit trail)")]:
        for f in sorted(DR.glob(pat)):
            excluded.append({"source": f"EXCLUDE:{f.name[:40]}", "kind": "exclusion",
                             "reason": why, "disk_file": str(f),
                             "size_mb": round(f.stat().st_size / 1e6, 1)})

    master = {
        "_doc": "Master source list — QC-framework witness denominator (Revision 2026-07-08, "
                "P0 provenance spine). Individual-source witness count; best-raster designation; "
                "E(v) per testament; downloaded-ocr + madueke_a excluded from coverage. P0: every "
                "witness record now shares a unified join-core (base_record) carrying a real content "
                "sha256 (per-volume manifest hash, rolled up mini-Merkle for multi-volume witnesses) "
                "plus lineage_group∈LINEAGE_ENUM and independent (cross-lineage vote eligibility). "
                "Supersedes the R10 usage denominator.",
        "framework": "locus-level QC (sparkling §0′ / partitioned-watching-dijkstra.md)",
        "generated_from": ["dr-sources-manifest.json v2", "our-ocr-diplomatic/", "reads/",
                            "consensus-full/_summary.json (informational)"],
        "E_v": E_V,
        "witness_roster": WITNESS_ROSTER,
        "witnesses": witnesses,
        "excluded": excluded,
    }
    OUT.write_text(json.dumps(master, ensure_ascii=False, indent=2))

    # ---------------- console report ----------------
    print("=== MASTER SOURCE LIST — QC-framework witness denominator (2026-07-08) ===\n")
    print(f"E(v): NT={E_V['NT']}  OT={E_V['OT']['baseline']} (range {E_V['OT']['range']})  "
          f"apparatus min-unblock={E_V['apparatus_min_unblock']}\n")
    print("SCAN WITNESSES (best-raster · current diplomatic OCR):")
    print(f"  {'src':<5}{'ev_role':<15}{'test':<8}{'group':<8}{'best_raster':<13} vols(pages · reocr?)")
    reocr_list = []
    for w in witnesses:
        if w["kind"] != "scan":
            continue
        vols = "  ".join(
            f"{v['ocr_dir'] or '-'}={v['ocr_pages']}"
            + ("[REOCR]" if v["reocr_needed"] else "") for v in w["volumes"])
        rasters = "/".join(sorted({v["best_raster"] or "?" for v in w["volumes"]}))
        print(f"  {w['source']:<5}{str(w['ev_role']):<15}{'/'.join(w['testaments'] or []):<8}"
              f"{w['witness_group']:<8}{rasters:<13} {vols}")
        for v in w["volumes"]:
            if v["reocr_needed"]:
                reocr_list.append((w["source"], v.get("role") or w.get("span"), v["reocr_needed"]))
    print("\nTRANSCRIPTION WITNESSES:")
    for w in witnesses:
        if w["kind"] == "transcription":
            flag = "" if w.get("counts_as_witness") else "  << NOT a witness (localization aid)"
            print(f"  {w['source']:<12} {str(w.get('ev_role')):<16} "
                  f"books={w.get('n_books')} identity={w.get('identity_class')}{flag}")
    print(f"\nWITNESS ROSTER (individual-source count):")
    for k, v in WITNESS_ROSTER.items():
        print(f"  {k:<17} {v}")
    print(f"\n>>> RE-OCR WORKLIST (best-raster gaps — the Phase-3 seed): {len(reocr_list)}")
    for s, span, why in reocr_list:
        print(f"    {s} [{span}] — {why}")
    print(f"\nEXCLUDED ({len(excluded)}): downloaded-ocr(parked) + S7 dup + Haydock/Challoner + stray dups")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
