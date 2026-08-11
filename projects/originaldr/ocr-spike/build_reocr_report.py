#!/usr/bin/env python3
"""build_reocr_report.py -- statistical, data-visual methods/results report for the OriginalDR re-OCR work.

Reads the verse-grain double-bind audit (coverage-audit-verse.json) as PRIMARY, and the chapter-grain
baseline (coverage-audit.json) for the phase-progression comparison. Renders a SELF-CONTAINED, offline,
interactive HTML report (inline SVG, no matplotlib, no CDN, no server) in a light journal-review tone.

Purpose (Sir 2026-07-10): present and reveal the REAL data from every iterating phase of the re-OCR work
so approach-redesign is directed from evidence. Every figure declares its GRAIN (book / chapter /
verse-element); pass rates are shown under three gates (archaic-preeminent governing, modern-only, old
AND-gate) toggled live from the same per-verse scores.

Versioning: each run archives the prior reocr-report.html into reports-archive/ before writing, so no
render is ever overwritten (Sir 2026-07-10).

Run: core/.venv/bin/python projects/originaldr/ocr-spike/build_reocr_report.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/"
             "mask_engine/originaldr_reconstruction")
ARCHIVE = HERE / "reports-archive"
VERSIONS = ARCHIVE / "versions.json"
BASELINE = HERE / "coverage-audit.json"          # chapter-grain P2 baseline (phase-progression compare)
APPARATUS = HERE / "coverage-audit-apparatus.json"
LIFT = HERE / "reocr-lift.json"                  # REP-2/REP-4: base->R2->R3->arbiter ladder, gold-anchored
MATTER = HERE / "matter-scoring-summary.json"    # REP-5: matter sections scored as first-class books
SLEDGER = HERE / ".s-arbiter" / "_open_ledger.json"   # live OPEN worklist (post-arbiter; blocks the deliverable)
# Book-grain cross-witness audits (`book_audit.py <book>`), one file per book audited. READ, never recomputed:
# the audit module owns these numbers, and a renderer that re-derives them can silently disagree with them.
BOOK_AUDITS = sorted(HERE.glob("book-audit-*.json"))
# Anatomy of the ALL-FAIL verses per book (`allfail_anatomy.py <book>`) — the contrast against verses that
# pass in EVERY witness. Read, never recomputed.
ALLFAIL_ANATOMY = sorted(HERE.glob("allfail-anatomy-*.json"))
# Single-chapter deep rescore (`gen1_rescore.py`): every verse of every witness against ALL FOUR references
# rather than the one governing reference, classified by cause. Read, never recomputed.
CHAPTER_RESCORES = sorted(HERE.glob("gen-rescore-*.json"))
BASELINE_AUDIT = HERE / "coverage-audit-verse.json.detect-baseline"   # the pre-Stage-1 operating point
SRCINDEX = HERE / "source-index.json"
BAR = 0.90

sys.path.insert(0, str(HERE))
import version_compare as VC  # noqa: E402  # type: ignore[import-not-found]  # sibling spike module
import curated_sources as CS  # noqa: E402  # REP-1 belt-and-suspenders: never render a banned SCAN source

# Display label for THIS build (Sir's v9 batch). The archive/manifest keep the monotonic INT version
# (so lineage never collides), but the banner/headline DISPLAY this human label.
VERSION_LABEL = "9"

# Pilot scope guardrail (== qc_audit.PILOT_BOOKS). The pilot report must not silently drift out of these
# five books; build_data FAILS LOUDLY if a pilot audit's scope exceeds this set (Sir: "stick to it").
PILOT_SCOPE = frozenset({"psalms", "genesis", "matthew", "john", "apocalypse"})

# Stage presets: point the report at any stage's verse-grain audit without editing code. Override with
# --stage / --input / --out on the CLI (see parse_config). Ready for iterating P3/P4 stages — add a key.
STAGES = {
    "pilot":     "coverage-audit-verse.json",            # 4-book pilot (validated)
    "fullscope": "coverage-audit-verse-fullscope.json",  # full 76-book authority
}

# Populated by parse_config() at startup (kept module-global for build_data()).
STAGE: str = "pilot"
VERSE: Path = HERE / STAGES["pilot"]
OUT: Path = HERE / "reocr-report-pilot.html"
VERSION: int = 0
BOOK_TESTAMENT: dict[str, str] = {}


CAMPAIGN_NOTE: str = ""
CAMPAIGN_DIR = HERE / ".campaign"
PROGRESSION = CAMPAIGN_DIR / "progression.jsonl"


def pipeline_provenance() -> dict[str, Any]:
    """WHICH PANELS MOVE WHEN A CHAPTER IS WORKED, AND WHICH CANNOT — with the dates, not a promise.

    Campaign work IS re-OCR work: fixing a page-model bound is "read the page better", the same rung as a
    recognizer fine-tune, and a reader is right to expect the whole report to reflect it. It does not, and the
    reason is mechanical rather than conceptual. Two pipelines produce this page and only one of them can see
    a campaign fix:

      * `.campaign/matrix-genesis-N.json`  <- `chapter_campaign.py` -> `gen1_matrix` -> `gen1_pagemodel`
        This is the live board. Every geometry fix, PAGE_OVERRIDE, R2 attestation and R3 adoption lands here.

      * `coverage-audit-verse.json`        <- `qc_audit.py` -> `detect_our_ocr` -> `reconstruction/reads`
        This is EVERYTHING ELSE on the page. It carries its own layout model (`marginalia-geometry.json`,
        `skeleton.json`) and imports nothing from `gen1_pagemodel` — verified by grep across the whole
        reconstruction module set. No campaign fix can reach it, and rebuilding this report will not change
        a single figure below the board no matter how much the board moves.

    So the honest thing a renderer can do is DATE both inputs and say which is which. A report that showed a
    rising board above a frozen corpus figure, with no note, would invite exactly the false inference this
    project has already had to correct once — that a gain measured at one grain has been realised at another."""
    def stamp(p: Path) -> dict[str, Any]:
        if not p.exists():
            return {"path": p.name, "exists": False}
        return {"path": p.name, "exists": True,
                "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "mb": round(p.stat().st_size / 1e6, 1)}
    mats = sorted(CAMPAIGN_DIR.glob("matrix-genesis-*.json"), key=lambda p: p.stat().st_mtime)
    return {
        "board": {**(stamp(mats[-1]) if mats else {"exists": False}),
                  "label": "campaign matrices", "n": len(mats),
                  "chain": "chapter_campaign.py -> gen1_matrix -> gen1_pagemodel"},
        "rest": {**stamp(VERSE), "label": "pilot verse audit",
                 "chain": "qc_audit.py -> detect_our_ocr -> reconstruction/reads"},
    }


def campaign_books() -> list[dict[str, Any]]:
    """Every Douay-Rheims division the campaign COULD cover, whether or not it has a board yet.

    The list is read from `skeleton.json` (76 scripture books, the canonical authority for order and chapter
    counts) plus `matter-scoring-summary.json` (30 front- and back-matter sections, which this project scores
    as first-class divisions rather than as trimmings). It is NOT the list of books with data.

    EVERY ENTRY CARRIES `has_board`, AND MOST ARE FALSE. Genesis is the only division with campaign matrices.
    A picker that silently listed only Genesis would misrepresent the campaign as nearly complete; one that
    listed all 106 without marking which are empty would misrepresent it as far more advanced than it is. So
    the entry states which it is, and the panel says "no board yet" rather than drawing an empty grid — an
    empty grid reads as "measured and found perfect", which is the opposite of the truth."""
    out: list[dict[str, Any]] = []
    have = {int(p.stem.split("-")[-2]) if False else p.stem.split("-")[1]
            for p in CAMPAIGN_DIR.glob("matrix-*-*.json")}
    try:
        sk = json.loads((RECON / "skeleton.json").read_text())
        for b in sk.get("books", []):
            out.append({"slug": b["slug"], "label": b["slug"].replace("-", " ").title(),
                        "kind": "appendix" if b.get("is_appendix") else b.get("testament", "OT"),
                        "chapters": b.get("chapters", 0), "has_board": b["slug"] in have})
    except Exception as e:                                    # a missing skeleton must not kill the report
        out.append({"slug": "genesis", "label": "Genesis", "kind": "OT", "chapters": 50,
                    "has_board": "genesis" in have, "note": f"skeleton unread: {e}"})
    try:
        mb = json.loads(MATTER.read_text()).get("books", [])
        for b in (mb if isinstance(mb, list) else list(mb.values())):
            slug = b.get("book") or b.get("slug")
            if not slug:
                continue
            out.append({"slug": slug, "kind": "matter", "chapters": 0, "has_board": slug in have,
                        "label": slug.replace("matter-", "").replace("-", " ").title()})
    except Exception:
        pass
    return out


def campaign_block(note: str = "") -> dict[str, Any]:
    """The LIVE Genesis campaign board, verse by verse and cell by cell, plus its history.

    WHY THIS IS SEPARATE FROM EVERYTHING ELSE IN THIS REPORT. The rest of the file renders
    `coverage-audit-verse.json` — the 5-book P3 pilot audit, a different pipeline at a different grain, which
    does not move when a Genesis chapter is closed. Sir asked to watch chapter and verse status change with
    each step of improvement, and the artifact that actually changes is `.campaign/matrix-genesis-N.json`.
    Rendering the campaign from the pilot audit would have shown a board that never moved.

    The cell grid is RECONSTRUCTED, not stored: a matrix lists only the OPEN cells, so every (verse, source)
    pair not named there is a pass — except where a reference is absent, which blocks the whole verse for
    every source and must be shown as BLOCKED rather than as a failure anyone can fix.

    A snapshot is appended to `.campaign/progression.jsonl` only when the totals actually differ from the last
    one, so rebuilding the report to look at it does not manufacture history."""
    chapters: list[dict] = []
    totals: dict[str, Any] = {"cells": 0, "pass": 0, "achievable": 0, "blocked": 0, "closed": 0}
    for f in sorted(CAMPAIGN_DIR.glob("matrix-genesis-*.json"), key=lambda p: int(p.stem.split("-")[-1])):
        m = json.loads(f.read_text())
        ch, nv = m["chapter"], m.get("n_verses", 0)
        blocked_verses = {int(x["verse"]) for x in (m.get("ref_coverage") or {}).get("incomplete", [])}
        open_by = {}
        for c in m.get("open", []):
            open_by[(int(c["verse"]), c["src"])] = c
        grid = []
        for v in range(1, nv + 1):
            row = {"v": v, "blocked": v in blocked_verses, "cells": []}
            for s in ("S1", "S3", "S6", "S9"):
                c = open_by.get((v, s))
                row["cells"].append({"s": s, "ok": c is None, "worst": (c or {}).get("worst"),
                                     # the FULL text: a preview that silently shortens the evidence fabricates symptoms
                                     # (a complete span read as "cut short mid-sentence" off a 120-char slice)
                                     "page": (c or {}).get("from"), "text": (c or {}).get("text") or ""})
            grid.append(row)
        closed = m.get("triage") == "CLEAN" and not m.get("blocked_cells")
        chapters.append({"ch": ch, "verses": nv, "cells": m.get("n_cells", 0), "pass": m.get("n_pass", 0),
                         "rate": m.get("rate", 0), "open": m.get("n_open", 0),
                         "all_fail": m.get("n_all_fail", 0), "triage": m.get("triage", "?"),
                         "blocked": m.get("blocked_cells", 0), "achievable": m.get("achievable", 0),
                         "src_rates": m.get("src_rates", {}), "ref_gaps": m.get("ref_gaps", []),
                         "closed": closed, "short": max(0, m.get("achievable", 0) - m.get("n_pass", 0)),
                         "grid": grid,
                         # The stacked verse view needs the text of PASSING cells too, which `open` never
                         # holds. Absent on any matrix written before 2026-08-01; the panel says so rather
                         # than rendering an empty stack that looks like "this verse has no witnesses".
                         "cellgrid": m.get("cellgrid") or {},
                         "refs_by_verse": m.get("refs_by_verse") or {},
                         "janvier_by_verse": m.get("janvier_by_verse") or {}})
        totals["cells"] += m.get("n_cells", 0)
        totals["pass"] += m.get("n_pass", 0)
        totals["achievable"] += m.get("achievable", 0)
        totals["blocked"] += m.get("blocked_cells", 0)
        totals["closed"] += 1 if closed else 0
    totals["rate_achievable"] = round(totals["pass"] / totals["achievable"], 4) if totals["achievable"] else 0

    hist = []
    if PROGRESSION.exists():
        hist = [json.loads(x) for x in PROGRESSION.read_text().splitlines() if x.strip()]
    key = (totals["pass"], totals["achievable"], totals["closed"])
    if not hist or (hist[-1]["pass"], hist[-1]["achievable"], hist[-1]["closed"]) != key:
        entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": note, **totals}
        with PROGRESSION.open("a") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        hist.append(entry)
    elif note and hist:
        hist[-1]["note"] = hist[-1].get("note") or note
    # COLLATION FLAGS — cells that fail because the witness and the reference are different EDITIONS. They
    # are still counted as failing above; this only carries the evidence so a reader can check the claim
    # instead of trusting the word "divergence".
    flags = []
    fp = HERE / "collation-flags.json"
    if fp.exists():
        flags = json.loads(fp.read_text()).get("flags", [])
    return {"chapters": chapters, "totals": totals, "history": hist, "collation_flags": flags}


def load_book_testament() -> dict[str, str]:
    """Book slug -> testament from the reconstruction skeleton (all 76 books), replacing the old
    hardcoded 4-book pilot dict so ANY stage's scope classifies correctly."""
    sk = json.loads((RECON / "skeleton.json").read_text())
    return {b["slug"]: b["testament"] for b in sk["books"]}


def parse_config(argv: list[str]) -> None:
    """Resolve which stage's audit to render + where to write, from CLI args. No hardcoded pilot."""
    global STAGE, VERSE, OUT, BOOK_TESTAMENT
    ap = argparse.ArgumentParser(description="Build the OriginalDR re-OCR report from a stage's verse audit.")
    ap.add_argument("--stage", choices=list(STAGES), default="pilot",
                    help="which stage's verse-grain audit to render (default: pilot)")
    ap.add_argument("--input", help="explicit path to a coverage-audit-verse JSON (overrides --stage)")
    ap.add_argument("--out", help="explicit output HTML path (default: reocr-report-<stage>.html)")
    ap.add_argument("--campaign-note", default="",
                    help="label this build's campaign snapshot (e.g. 'closed ch8') — recorded in the "
                         "progression log only when the totals actually changed")
    a = ap.parse_args(argv)
    global CAMPAIGN_NOTE
    CAMPAIGN_NOTE = a.campaign_note
    STAGE = a.stage
    VERSE = Path(a.input) if a.input else HERE / STAGES[a.stage]
    if not VERSE.is_absolute():
        VERSE = HERE / VERSE
    OUT = Path(a.out) if a.out else HERE / f"reocr-report-{STAGE}.html"
    if not OUT.is_absolute():
        OUT = HERE / OUT
    BOOK_TESTAMENT = load_book_testament()

# reference-source lineage (per reference_construction): archaic = s_dismas ?? odr_com;
# modern = sabates_a ?? madueke_b. Used to color/sort transcribed sources by preeminence.
ARCHAIC_REFS = {"s_dismas", "odr_com"}
MODERN_REFS = {"sabates_a", "madueke_b"}


def ref_class(sid: str) -> str | None:
    if sid in ARCHAIC_REFS:
        return "archaic"
    if sid in MODERN_REFS:
        return "modern"
    return None


def _r(x: Any, n: int = 3) -> Any:
    return round(x, n) if isinstance(x, (int, float)) else x


def pass_under(r: dict, gate: str) -> bool:
    """Whether a source record passes under a named gate. Transcriptions pass all gates (references)."""
    if r.get("kind") == "transcription":
        return True
    m = (r.get("modern_id") or 0.0) >= BAR
    a = (r.get("archaic_id") or 0.0) >= BAR
    aref = r.get("archaic_ref_exists")
    if gate == "modern":
        return m
    if gate == "archaic":
        return a if aref else m           # archaic-preeminent single gate
    if gate == "both":
        return m and (a if aref else True)   # old modern-primary AND-gate
    return bool(r.get("passed"))          # governing (== archaic-preeminent)


def _baseline_wdepth() -> dict | None:
    """Witness-depth histogram from the PRE-Stage-1 audit, so V4 can show the shift instead of a snapshot."""
    if not BASELINE_AUDIT.exists():
        return None
    d = json.loads(BASELINE_AUDIT.read_text())
    out: dict[str, dict[str, int]] = {g: {} for g in ("archaic", "modern", "both")}
    for _locus, rec in d["verses"].items():
        srcs = [r for r in (rec.get("sources") or {}).values() if r.get("kind") == "scan"]
        for g in out:
            n = sum(1 for r in srcs if pass_under(r, g))
            out[g][str(n)] = out[g].get(str(n), 0) + 1
    return out


def _governance(verses: dict) -> dict:
    """Which INSTRUMENT actually governed each scan record, and how often the archaic one was withdrawn.

    This replaces the retired 'old AND-gate' arm of V5. That arm compared the current gate against a scheme
    abandoned before this phase began, which answers a question nobody is asking any more. The live question,
    now that the reference policy is implemented, is *which witness is judging this verse and why* — archaic
    where it carries the verse's own text, modern where the archaic reference was withdrawn as not-this-verse,
    and the residual that has no valid yardstick at all."""
    g = {"archaic": 0, "modern": 0, "needs-in-family-reference": 0, "needs-reference": 0}
    withdrawn = passed_after_withdrawal = 0
    for _locus, rec in verses.items():
        for r in (rec.get("sources") or {}).values():
            if r.get("kind") != "scan":
                continue
            inst = (r.get("routing") or {}).get("governing_instrument", "needs-reference")
            g[inst] = g.get(inst, 0) + 1
            if r.get("archaic_reference_invalid_here"):
                withdrawn += 1
                if r.get("passed_effective"):
                    passed_after_withdrawal += 1
    return {"by_instrument": g, "archaic_withdrawn": withdrawn,
            "passed_after_withdrawal": passed_after_withdrawal}


def build_data(version: int = 0, stamp: str | None = None) -> dict[str, Any]:
    V = json.loads(VERSE.read_text())
    verses: dict[str, Any] = V["verses"]
    scope = V["scope_books"]
    gates = ["archaic", "modern", "both"]

    # SCOPE GUARDRAIL (pilot only): refuse to render a pilot report whose audited scope has drifted beyond
    # the declared five-book pilot. This is a hard failure, not a warning — a drifted build must not ship.
    if STAGE == "pilot":
        drift = set(scope) - PILOT_SCOPE
        if drift:
            raise SystemExit(f"PILOT SCOPE DRIFT: {sorted(drift)} not in declared pilot {sorted(PILOT_SCOPE)}. "
                             f"Fix the audit's scope_books or the pilot declaration before building.")

    # scan provenance flags (re-OCR / stub) from the master source list, for the V6 table
    msl_path = HERE / "master-source-list.json"
    reocr_flag: dict[str, dict[str, Any]] = {}
    if msl_path.exists():
        for w in json.loads(msl_path.read_text()).get("witnesses", []):
            if w.get("kind") == "scan":
                reocr_flag[w["source"]] = {
                    "reocr_needed": bool(w.get("reocr_needed")),
                    "coverage": w.get("coverage") or w.get("span") or "",
                }

    # ---- per-source accumulation (split OT/NT for grouped histograms) ----
    src: dict[str, dict[str, Any]] = {}

    def sacc(sid: str) -> dict[str, Any]:
        return src.setdefault(sid, {
            "id": sid, "kind": None, "ocr_dir": None, "testaments": set(), "n_attested": 0,
            "pass": {g: 0 for g in gates}, "worklist_hits": 0,
            "mod_OT": [], "arch_OT": [], "mod_NT": [], "arch_NT": [],
        })

    # ---- per (book) scatter + witness-depth + grain rollups ----
    scatter: dict[str, list[list[float]]] = {b: [] for b in scope}
    scatter_srcs: dict[str, list[str]] = {b: [] for b in scope}
    verse_index: dict[str, list[list[Any]]] = {}
    wdepth_verse: dict[str, dict[int, int]] = {g: {} for g in gates}

    for c in verses.values():
        book, ch, v, test = c["book"], c["chapter"], c["verse"], c["testament"]
        clocus = f"scripture/{book}/{ch}"
        passed_sids_gov: list[str] = []
        for g in gates:
            wc = sum(1 for r in c["sources"].values() if pass_under(r, g))
            wdepth_verse[g][wc] = wdepth_verse[g].get(wc, 0) + 1
        for sid, r in c["sources"].items():
            a = sacc(sid)
            a["kind"] = r["kind"]
            if r.get("ocr_dir"):
                a["ocr_dir"] = r["ocr_dir"]
            a["testaments"].add(test)
            a["n_attested"] += 1
            for g in gates:
                if pass_under(r, g):
                    a["pass"][g] += 1
            if r["kind"] == "scan" and r.get("modern_id") is not None:
                (a["mod_NT"] if test == "NT" else a["mod_OT"]).append(_r(r["modern_id"]))
                if r.get("archaic_id") is not None:
                    (a["arch_NT"] if test == "NT" else a["arch_OT"]).append(_r(r["archaic_id"]))
                if sid not in scatter_srcs[book]:
                    scatter_srcs[book].append(sid)
                si = scatter_srcs[book].index(sid)
                scatter[book].append([_r(r["modern_id"]), _r(r.get("archaic_id")),
                                      si, int(bool(r.get("passed"))), int((r.get("modern_id") or 0) >= BAR)])
            if pass_under(r, "archaic") and r["kind"] == "scan":
                passed_sids_gov.append(sid)
        verse_index.setdefault(clocus, []).append(
            [v, c["witness_count"], int(bool(c["shortfall_flag"])), passed_sids_gov])

    # finalize source rows
    def med(xs: list[float]) -> Any:
        return _r(st.median(xs)) if xs else None

    sources = []
    for sid, a in src.items():
        allmod = a["mod_OT"] + a["mod_NT"]
        allarch = a["arch_OT"] + a["arch_NT"]
        sources.append({
            "id": sid, "kind": a["kind"], "ocr_dir": a["ocr_dir"], "ref_class": ref_class(sid),
            "testaments": sorted(a["testaments"]), "n_attested": a["n_attested"],
            "pass_archaic": a["pass"]["archaic"], "pass_modern": a["pass"]["modern"], "pass_both": a["pass"]["both"],
            "mod_med": med(allmod), "arch_med": med(allarch),
            "mod_OT": a["mod_OT"], "arch_OT": a["arch_OT"], "mod_NT": a["mod_NT"], "arch_NT": a["arch_NT"],
            "worklist_hits": 0,
            "reocr_needed": reocr_flag.get(sid, {}).get("reocr_needed", False),
            "coverage": reocr_flag.get(sid, {}).get("coverage", ""),
        })

    def strength(s: dict) -> float:
        return s["mod_med"] if s["mod_med"] is not None else -1.0

    # sort by PREEMINENCE: archaic references first, then modern references, then scans (by strength).
    def sort_key(s: dict) -> tuple[int, float, str]:
        if s["kind"] == "scan":
            return (2, -strength(s), s["id"])
        return (0 if s["ref_class"] == "archaic" else 1, 0.0, s["id"])
    sources.sort(key=sort_key)
    source_order = [s["id"] for s in sources]
    scan_ids = [s["id"] for s in sources if s["kind"] == "scan"]

    # ---- chapter rollups per gate (for heatmap + intensity + drill-down) ----
    chapters: dict[str, dict] = {}
    for c in verses.values():
        clocus = f"scripture/{c['book']}/{c['chapter']}"
        ch = chapters.setdefault(clocus, {
            "locus": clocus, "book": c["book"], "chapter": c["chapter"], "testament": c["testament"],
            "E_v": c["E_v"], "n_verses": 0, "verses_shortfall": 0, "sources": {}})
        ch["n_verses"] += 1
        if c["shortfall_flag"]:
            ch["verses_shortfall"] += 1
        for sid, r in c["sources"].items():
            # REP-1 belt-and-suspenders: a banned SCAN source must never render. Reference/transcription
            # witnesses (s_dismas, sabates_a, madueke_b, odr_com) are NOT scan sources and are kept.
            if r.get("kind") == "scan" and not CS.is_curated(sid):
                continue
            sd = ch["sources"].setdefault(sid, {
                "kind": r["kind"], "ref_class": ref_class(sid),
                "n_att": 0, "pass_archaic": 0, "pass_modern": 0, "pass_both": 0,
                "gov": [], "mod": [], "arch": []})
            sd["n_att"] += 1
            for g in gates:
                if pass_under(r, g):
                    sd["pass_" + g] += 1
            if r["kind"] == "scan":
                g = r.get("archaic_id") if r.get("archaic_ref_exists") else r.get("modern_id")
                if g is not None:
                    sd["gov"].append(g)
                if r.get("modern_id") is not None:
                    sd["mod"].append(r["modern_id"])
                if r.get("archaic_id") is not None:
                    sd["arch"].append(r["archaic_id"])
    for ch in chapters.values():
        need = max(1, ch["n_verses"] - 1)   # chapter-pass bar: >= (m-1) of m verses (Sir, 2026-07-10)
        ch["pass_need"] = need
        for sid, sd in ch["sources"].items():
            sd["mean_gov"] = med(sd.pop("gov"))
            sd["mean_mod"] = med(sd.pop("mod"))
            sd["mean_arch"] = med(sd.pop("arch"))
            for g in gates:
                sd["chpass_" + g] = sd["pass_" + g] >= need

    # ---- book rollups per gate ----
    books = []
    for b in scope:
        bverses = [c for c in verses.values() if c["book"] == b]
        E_v = bverses[0]["E_v"] if bverses else None
        row = {"slug": b, "testament": BOOK_TESTAMENT.get(b, "?"), "E_v": E_v,
               "n_verses": len(bverses),
               "n_chapters": len({c["chapter"] for c in bverses}),
               "sources": {}}
        for sid in source_order:
            recs = [c["sources"][sid] for c in bverses if sid in c["sources"]]
            if not recs:
                continue
            row["sources"][sid] = {
                "kind": recs[0]["kind"], "n_att": len(recs),
                "pass_archaic": sum(1 for r in recs if pass_under(r, "archaic")),
                "pass_modern": sum(1 for r in recs if pass_under(r, "modern")),
                "pass_both": sum(1 for r in recs if pass_under(r, "both")),
            }
        books.append(row)

    # ---- regime + grain breakout (scan records only) ----
    def scan_records() -> list[dict]:
        return [r for c in verses.values() for r in c["sources"].values() if r["kind"] == "scan"]

    srecs = scan_records()
    regimes = {g: sum(1 for r in srecs if pass_under(r, g)) for g in gates}
    regimes["records"] = len(srecs)

    # grain breakout: fraction of loci where >=1 scan passes, at each grain, per gate
    def loci_with_scan_pass(level: str, gate: str) -> tuple[int, int]:
        if level == "verse":
            hit = tot = 0
            for c in verses.values():
                sc = [r for r in c["sources"].values() if r["kind"] == "scan"]
                if not sc:
                    continue
                tot += 1
                if any(pass_under(r, gate) for r in sc):
                    hit += 1
            return hit, tot
        if level == "chapter":
            # chapter "passes" iff a scan passes >= (m-1) of the chapter's m verses (strict rule)
            hit = tot = 0
            for ch in chapters.values():
                sc = [sd for sd in ch["sources"].values() if sd["kind"] == "scan"]
                if not sc:
                    continue
                tot += 1
                if any(sd["chpass_" + gate] for sd in sc):
                    hit += 1
            return hit, tot
        hit = tot = 0
        for b in books:
            sc = [sd for sd in b["sources"].values() if sd["kind"] == "scan"]
            if not sc:
                continue
            tot += 1
            if any(sd["pass_" + gate] > 0 for sd in sc):
                hit += 1
        return hit, tot

    grain_breakout = {lvl: {g: loci_with_scan_pass(lvl, g) for g in gates}
                      for lvl in ("verse", "chapter", "book")}

    # ---- worklist (from authority) ----
    worklist = V.get("reocr_worklist", [])
    wl_hits: dict[str, int] = {}
    for w in worklist:
        for sid in w.get("localized_but_failed", []):
            wl_hits[sid] = wl_hits.get(sid, 0) + 1
    for s in sources:
        s["worklist_hits"] = wl_hits.get(s["id"], 0)

    # ---- phase progression vs chapter-grain baseline ----
    phases = [{
        "phase": "P2-verse-archaic-preeminent", "grain": "verse", "gating": "archaic-preeminent",
        "scan_pass": regimes["archaic"], "records": regimes["records"], "note": "current"}]
    if BASELINE.exists():
        B = json.loads(BASELINE.read_text())
        bch = B.get("chapters", {})
        bpass = sum(1 for cc in bch.values() for s in cc["sources"].values()
                    if s.get("kind") == "scan" and s.get("passed"))
        brec = sum(1 for cc in bch.values() for s in cc["sources"].values() if s.get("kind") == "scan")
        phases.insert(0, {
            "phase": "P2-baseline", "grain": "chapter", "gating": "modern-primary (madueke_a ref)",
            "scan_pass": bpass, "records": brec, "note": "superseded — chapter grain, pre-fix references"})

    prior = sorted([p.name for p in ARCHIVE.glob(f"reocr-report-{STAGE}-*.html")]) if ARCHIVE.exists() else []
    # prior recorded version of THIS stage (history[-1] — _record_version has not yet appended this build),
    # used to compute the banner's what-changed delta (verses/books/scope/input-sha).
    _vhist = json.loads(VERSIONS.read_text()).get(STAGE, {}).get("history", []) if VERSIONS.exists() else []
    prior_version = _vhist[-1] if _vhist else None

    # v7: per-book V3 track filter. A source row shows under a book iff the source is EXPECTED to contain the
    # book (source-index expected_witnesses) OR it actually attests >=1 locus there. This hides tracks a book
    # should not carry (NT-only scans under an OT book, and vice versa) WITHOUT hiding expected-but-failed
    # sources (those stay visible as a genuine gap — No Silent Degradation).
    _si = json.loads(SRCINDEX.read_text()) if SRCINDEX.exists() else {}
    _exp_by_book = {b: set(v.get("expected_witnesses", []))
                    for b, v in _si.get("loci_ev", {}).get("scripture_books", {}).items()}
    _attest_by_book: dict[str, set] = {}
    for _c in chapters.values():
        _attest_by_book.setdefault(_c["book"], set()).update(_c["sources"].keys())
    v3_tracks = {}
    for b in scope:
        allow = _exp_by_book.get(b, set()) | _attest_by_book.get(b, set())
        v3_tracks[b] = [sid for sid in source_order if sid in allow] if allow else list(source_order)
    ot_n = sum(1 for b in scope if BOOK_TESTAMENT.get(b) == "OT")
    nt_n = sum(1 for b in scope if BOOK_TESTAMENT.get(b) == "NT")
    ap_n = sum(1 for b in scope if BOOK_TESTAMENT.get(b) == "APPENDIX")

    apparatus = json.loads(APPARATUS.read_text()) if APPARATUS.exists() else None

    # ---- INVENTORY (scope guardrail, made visible): the exact books + apparatus elements this report
    # covers, so a reader can see at a glance that it stays inside the P3 pilot and never drifts. Pure
    # data — derived from the audited books and the apparatus summary, not narrative. ----
    ap_summary = (apparatus or {}).get("summary", {}) if apparatus else {}
    ap_elements = (apparatus or {}).get("elements", {}) if apparatus else {}
    inventory = {
        "declared_pilot": sorted(PILOT_SCOPE),
        "books": [{"slug": b["slug"], "testament": b["testament"], "E_v": b["E_v"],
                   "n_verses": b["n_verses"], "n_chapters": b["n_chapters"]} for b in books],
        "apparatus": {
            "built": [{"locus": k, "E_v": e.get("E_v"), "witness_count": e.get("witness_count"),
                       "score_grain": e.get("score_grain")} for k, e in ap_elements.items()],
            "open_slots": ap_summary.get("open_slots"),
            "open_needs_build": ap_summary.get("open_needs_build"),
            "reocr_worklist": ap_summary.get("reocr_worklist"),
        },
    }

    # ---- v9: rung-0 sign-off from the ladder's diag-reocr/index.json (see RUNG0-SIGNOFF-v9.md) ----
    signoff_path = HERE / "diag-reocr" / "index.json"
    rung0_signoff: dict[str, Any] | None = None
    if signoff_path.exists():
        _idx = json.loads(signoff_path.read_text())
        if _idx.get("signoff"):
            rung0_signoff = {
                "gate": _idx.get("gate"),
                "signoff": _idx["signoff"],
                "records": [
                    {"locus": r["locus"], "scan": r.get("scan"), "domain": r["domain"],
                     "recall": r.get("recall"), "best_archaic_id": r.get("best_archaic_id"),
                     "inspection": r.get("inspection")}
                    for r in _idx.get("records", [])
                    if r.get("inspection")
                ],
            }

    return {
        "campaign": campaign_block(CAMPAIGN_NOTE),
        "campaign_books": campaign_books(),
        "pipelines": pipeline_provenance(),
        "meta": {
            "generated_at": stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stage": STAGE, "version": version,
            "phase": V["phase"], "grain": V["grain"], "gating": V["gating"],
            "scope_books": scope, "threshold": BAR,
            "scope_summary": f"{ot_n} OT + {nt_n} NT" + (f" + {ap_n} appendix" if ap_n else "") + " books",
            "metric": V["identity_bar"].get("metric", "char-level difflib.ratio"),
            "reference_construction": V.get("reference_construction", {}),
            "source_file": VERSE.name,
            "source_sha256": hashlib.sha256(VERSE.read_bytes()).hexdigest()[:16],
            "n_verses": len(verses), "n_chapters": len(chapters), "n_books": len(books),
            "n_scan_sources": len(scan_ids), "prior_reports": prior,
            "prior_version": prior_version, "changelog": CHANGELOG,
            "version_label": VERSION_LABEL,
        },
        "status": STATUS,
        "inventory": inventory,
        "regimes": regimes,
        "grain_breakout": grain_breakout,
        "books": books, "sources": sources, "source_order": source_order, "scan_ids": scan_ids,
        "v3_tracks": v3_tracks,
        "scatter": scatter, "scatter_srcs": scatter_srcs,
        "chapters": list(chapters.values()),
        "wdepth_verse": wdepth_verse,
        "verse_index": verse_index,
        "worklist": worklist,
        "source_defects": V.get("source_defects", []),
        "routing_summary": V.get("scoped_reocr_routing", {}),
        "phases": phases,
        "book_testament": BOOK_TESTAMENT,
        "apparatus": apparatus,
        # REP-2/4/5 + the live ledger are READ, never recomputed here: the harnesses that validated these
        # numbers own them, and a renderer that re-derives its own can silently disagree with the evidence.
        # V4/V5 need the BEFORE state to show a shift rather than a snapshot. Read from the archived
        # pre-Stage-1 audit; absent, the figures degrade to the current distribution only and say so.
        "wdepth_verse_baseline": _baseline_wdepth(),
        "governance": _governance(verses),
        "lift": json.loads(LIFT.read_text()) if LIFT.exists() else None,
        "matter": json.loads(MATTER.read_text()) if MATTER.exists() else None,
        "ledger": json.loads(SLEDGER.read_text()) if SLEDGER.exists() else None,
        "rung0_signoff": rung0_signoff,
        # {book -> audit}. Empty until a book is audited; the section renders nothing rather than
        # implying a book was checked and came back clean.
        "book_audits": {p.stem.replace("book-audit-", ""): json.loads(p.read_text())
                        for p in BOOK_AUDITS},
        "allfail_anatomy": {p.stem.replace("allfail-anatomy-", ""): json.loads(p.read_text())
                            for p in ALLFAIL_ANATOMY},
        "chapter_rescores": [json.loads(p.read_text()) for p in CHAPTER_RESCORES],
    }


# Session status folded into the Methods "completed vs pending" subsection (Sir 2026-07-10).
STATUS = {
    "fixes_applied": [
        "Modern reference now backfills from madueke_b (was the madueke_a localization-aid) — corrects the "
        "scoring reference in char_identity/qc_audit.",
        "char_identity.evaluate_locus reworked to ARCHAIC-PREEMINENT: where an archaic ref exists it governs "
        "(archaic_id >= 0.90); modern_id is recorded but does not gate; else modern governs; neither -> "
        "needs-reference OPEN.",
        "detect_our_ocr NT-localization bug fixed: is_nt_alias now recognizes real OCR-dir names and "
        "candidate_aliases falls back to all present streams — NT books (Matthew, Apocalypse) previously "
        "could never localize (0 witnesses).",
        "detect_s_dismas.py confirmed() parse bug fixed (drop-cap scanned before the first-verse fallback), "
        "recovering headings the interleaved Annotations/'briefe remonstrance' runs mis-rejected. Reference "
        "NOT regenerated: a full re-extraction from the current source degrades ~15 OT books, so the "
        "complete original s_dismas is retained and odr_com backfills the gaps (Genesis 8 etc.).",
        "Identity metric swapped to normalized Levenshtein (edit_ratio = 1 - editdist/max(len)) as the gate "
        "(char_identity.py); difflib.ratio retained only as a fast <0.80 skip-prefilter. difflib over-scored, "
        "so under the correct metric pass rates drop materially — the numbers below are stricter and more "
        "honest, widening (not hiding) the OCR-quality gap that re-OCR must close.",
    ],
    "completed": [
        "Verse/element-grain scoring (uniform), archaic-preeminent gating.",
        "Backfilled references: archaic = s_dismas else odr_com; modern = sabates_a else madueke_b.",
        "Scope extended: + Matthew, + John, + Apocalypse (3 NT books).",
        "Re-ran pilot (Psalms, Genesis, Matthew, John, Apocalypse — 5 books) -> coverage-audit-verse.json.",
        "Genesis + Psalms spliced into the s_dismas reference from the drop-cap-anchored re-parse: Genesis 26 "
        "(misprinted 'Chapter 25') and Psalms 52 (heading severed by a leading running header) recovered with "
        "clean verse content; the other 50 books left byte-identical (reads 25792 -> 25833).",
        "Chapter-pass rule tightened (Sir): a source passes a chapter iff it passes >= (m-1) of the m "
        "verses — a strict early-benchmark bar (<= 1 verse of error) coupling completeness and faithfulness.",
        "Apparatus pulled forward (Sir): s_dismas 01-front-matter.pdf (OT + NT) parsed into element-grain "
        "archaic references — OT approbatio + OT preface + NT preface — and content-localized in the OT and "
        "NT scans (apparatus_audit.py, V8). The OT approbatio boundary was corrected (p9 only; p10 is the "
        "Preface opening), lifting it from 0 to 6 passing witnesses.",
        "Report: V2 scatter click-to-zoom; V3 heatmap colours references by lineage (archaic vs modern) "
        "and sorts rows by preeminence; S2 flagged as a 10-of-1135-page stub (needs full re-OCR).",
    ],
    "pending": [
        "Front/back-matter apparatus is tracked on the worklist, not silently accepted. V8 pulls the s_dismas "
        "front-matter forward for BOTH testaments: the OT approbatio (single Latin page) now scores whole and "
        "attests in 6/9 OT scans (>= 0.90 archaic) — still short of E(v)=9, so it stays OPEN; the OT preface "
        "(12 pp) and NT preface (41 pp) localize (OT 9/9, NT 6/8) but their full char-level identity cannot be "
        "run whole (a pure-Python O(n.m) edit DP does not terminate at 90k chars, and the s_dismas re-typeset "
        "pagination makes page-grain alignment invalid), so only the aligned OPENING window is scored so far "
        "(best archaic ~0.75 OT / ~0.80 NT, all below 0.90) — a sample that never credits a witness; full "
        "aligned scoring is a P5 task. INVENTORY finding (image-verified): the s_dismas typeset edition carries "
        "ONLY approbatio + preface (OT) and the preface (NT) — it has NO distinct archaic title-page / privilege "
        "/ censura (OT) or title-page / censure (NT) surface, so those 5 front slots stay OPEN and are never "
        "fabricated. The MODERN reference (janvier-s reference/, original DR apparatus in modern spelling, keyed "
        "1:1) exists for every slot, so all 23 remaining open slots are needs-build, not needs-reference; the "
        "gap is the diplomatic ARCHAIC surface (needs scan re-OCR at P4 for the 5 absent front slots, and the "
        "partial odr-com twin for the 18 back-matter slots).",
        "s_dismas Class-A source defects (auto-detected): after the drop-cap-anchored re-parse + splice, "
        "Genesis 26 and Psalms 52 are RECOVERED (clean content) and drop out of the defect set — the live "
        "count is now 3. Acts 25 is interim-covered by odr_com; Leviticus 3 and Proverbs 25 are the only "
        "genuine OPEN scripture defects (odr_com carries no Leviticus 3 / no Proverbs). Genesis 8 localizes "
        "but pdftotext emits its drop-cap glyph AFTER the verse-1 text, blobbing verses 1-6 — a verse-content "
        "(layout) defect deferred to P4 layout-aware re-OCR, held OPEN, never accepted.",
        "P3/P4 re-OCR ladder (layout-aware / region / vision-LLM) is a worklist only — NOT implemented. Its "
        "design must include a diagnostic step that rasterizes low-scoring pages for visual inspection (by "
        "Jarvis) before any OCR-method redesign.",
    ],
}


# Short human-set "what changed" line for the CURRENT build, shown in the version banner alongside the
# mechanical data-delta. Update this each time the report is bumped so every render self-identifies.
CHANGELOG = (
    "V9 batch (rung-0 sign-off — the meaty ladder step): (1) The re-OCR ladder's MANDATORY rung-0 diagnostic "
    "gate has FIRED — 9 worst-scoring loci rasterized, all 9 visually inspected by Jarvis, verdicts recorded "
    "into diag-reocr/index.json (per-record inspection field + top-level signoff block). Gate CLEARED. (2) "
    "Substantive finding: 8/9 loci route to RUNG 1 (layout/region typing: Surya + YOLOv11-OBB + XY-Cut++); "
    "ZERO rung-2 (glyph-targeted) candidates — every scan's print is legible, long-ſ / u/v / ligatures render "
    "consistently, so a Kraken/CATMuS-Print archaic-glyph fine-tune is not warranted by the first wave. Zero "
    "rung-3 (vision-LLM) candidates. (3) NO-SILENT-DEGRADATION flag: S14 approbatio pairing DELISTED — S14 "
    "(eebo-vol4) is Psalms-only; its page 2 is a Psalms proemial, not the whole-Bible approbatio; the 0.9676 "
    "archaic_id passes only because it scored the WRONG TARGET (the exact pathology the rung-0 gate exists to "
    "catch). The apparatus/ot-front/approbatio locus stays OPEN for the whole-Bible witness set. (4) Sign-off "
    "artifact: RUNG0-SIGNOFF-v9.md — durable, citable audit record for downstream rung-1 execution. Verse + "
    "apparatus audit data are unchanged from v8.1."
)


def _next_version(stage: str) -> int:
    versions = json.loads(VERSIONS.read_text()) if VERSIONS.exists() else {}
    return int(versions.get(stage, {}).get("version", 0)) + 1


def _record_version(stage: str, entry: dict) -> None:
    versions = json.loads(VERSIONS.read_text()) if VERSIONS.exists() else {}
    st_ = versions.setdefault(stage, {"version": 0, "history": []})
    st_["version"] = entry["version"]
    st_["history"].append(entry)
    VERSIONS.write_text(json.dumps(versions, indent=2))


def main() -> int:
    parse_config(sys.argv[1:])
    ARCHIVE.mkdir(exist_ok=True)
    version = _next_version(STAGE)
    stamp_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp_file = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    input_sha = hashlib.sha256(VERSE.read_bytes()).hexdigest()[:16]
    data = build_data(version=version, stamp=stamp_iso)

    # ---- empirical version comparison (Sir v8.1): measure THIS build's metrics from DATA and compare to
    # the prior recorded version's metrics — never from the changelog narrative. Prefer the prior version's
    # stored snapshot; else recompute from the prior on-disk report. This drives the Results — Headline. ----
    cur_metrics = VC.metrics_from_data(data)
    prev_metrics: dict[str, Any] | None = None
    _hist = json.loads(VERSIONS.read_text()).get(STAGE, {}).get("history", []) if VERSIONS.exists() else []
    if _hist and _hist[-1].get("metrics"):
        prev_metrics = _hist[-1]["metrics"]
    elif OUT.exists():
        prev_metrics = VC.metrics_from_html(OUT)
    if prev_metrics and isinstance(prev_metrics.get("source_fail"), dict):
        # REP-1: a stored PRE-curation prior snapshot may carry banned scan sources in source_fail — strip
        # them so the historical delta is curated-clean (recompute mean/worst on the curated subset).
        _cur = {"S1", "S3", "S4", "S6", "S8", "S9"}
        _sf = {k: v for k, v in prev_metrics["source_fail"].items() if k in _cur}
        prev_metrics = {**prev_metrics, "source_fail": _sf,
                        "source_fail_mean": round(sum(_sf.values()) / len(_sf), 4) if _sf else None,
                        "source_fail_worst": max(_sf.values()) if _sf else None}
    data["version_compare"] = VC.compare(prev_metrics, cur_metrics) if prev_metrics else None

    # per-stage version lineage: archive the prior render of THIS stage before overwriting (never lose one)
    if OUT.exists():
        psha = hashlib.sha256(OUT.read_bytes()).hexdigest()[:8]
        dest = ARCHIVE / f"reocr-report-{STAGE}-v{version - 1:03d}-{stamp_file}-{psha}.html"
        shutil.copy2(OUT, dest)
        print(f"archived prior {STAGE} render -> {dest.name}")

    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    m, rg, gb = data["meta"], data["regimes"], data["grain_breakout"]
    _record_version(STAGE, {
        "version": version, "version_label": VERSION_LABEL, "stamp": stamp_iso, "out": OUT.name,
        "input": VERSE.name, "input_sha256": input_sha,
        "n_verses": m["n_verses"], "n_books": m["n_books"], "scope_summary": m["scope_summary"],
        "metrics": cur_metrics,
    })
    if data["version_compare"]:
        print("headline verdict: " + VC.summarize(data["version_compare"]))
    print(f"=== {STAGE} report v{version:03d} (label {VERSION_LABEL}): {OUT.name} "
          f"({OUT.stat().st_size // 1024} KB) from {VERSE.name} ===")
    print(f"phase={m['phase']} grain={m['grain']} scope={m['scope_summary']} "
          f"verses={m['n_verses']} scans={m['n_scan_sources']}")
    print(f"scan-verse passes: archaic(gov)={rg['archaic']} modern={rg['modern']} both(old-AND)={rg['both']} "
          f"of {rg['records']}")
    for lvl in ("verse", "chapter", "book"):
        h, t = gb[lvl]["archaic"]
        print(f"  grain {lvl:<8}: {h}/{t} loci have >=1 scan passing the governing gate")
    return 0


# ==================================================================================================
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OriginalDR re-OCR — methods &amp; results</title>
<style>
:root{
 --bg:#ffffff;--page:#f5f6f8;--panel:#ffffff;--ink:#1a1d21;--mut:#5b6470;--faint:#8a929e;
 --line:#d9dee4;--rule:#c3cad2;
 --accent:#1f5c8b;--accent2:#0b6b6b;
 --pass:#1a9850;--fail:#f16913;--faildeep:#b2182b;--ref:#4575b4;--refarc:#6a3d9a;--absent:#e9edf1;--unloc:#8073ac;
 --chip:#eef2f6;
}
*{box-sizing:border-box}
html{font-size:16px}
body{margin:0;background:var(--page);color:var(--ink);
 font:1rem/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
h1,h2,h3,h4{font-family:Georgia,"Times New Roman",serif;color:var(--ink);line-height:1.25}
header{padding:26px 34px 20px;background:var(--bg);border-bottom:3px solid var(--accent)}
h1{margin:0 0 6px;font-size:1.7rem;font-weight:700}
h2{font-size:1.28rem;margin:0 0 4px;color:var(--accent)}
h3{font-size:1.02rem;margin:18px 0 6px;color:var(--accent2)}
h4{font-size:.95rem;margin:12px 0 4px;color:var(--ink)}
.sub{color:var(--mut);font-size:.86rem}
#verbanner{margin-top:10px}
.vb-badge{display:inline-block;background:var(--accent);color:#fff;font-weight:700;font-size:.82rem;padding:2px 9px;border-radius:5px;letter-spacing:.02em}
.vb-built{margin-left:10px;color:var(--mut);font-size:.8rem}
.vb-delta{margin-top:7px;font-size:.9rem;font-weight:600;color:var(--accent2)}
.vb-log{margin-top:5px;font-size:.85rem;color:var(--ink);background:var(--chip);border-left:3px solid var(--accent);padding:7px 11px;border-radius:0 5px 5px 0;max-width:1000px}
.wrap{max-width:1180px;margin:0 auto;padding:0 34px 90px}
section{margin:26px 0;background:var(--panel);border:1px solid var(--line);border-radius:8px;
 padding:22px 26px;box-shadow:0 1px 2px rgba(20,30,45,.04)}
.figtitle{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--line);
 padding-bottom:8px;margin-bottom:12px}
.grain{font:600 .72rem/1 -apple-system,sans-serif;letter-spacing:.4px;text-transform:uppercase;
 padding:3px 8px;border-radius:4px;background:var(--chip);color:var(--accent);border:1px solid #d3dde7}
.grain.verse{background:#eaf5ee;color:#1a7a44;border-color:#bfe3cd}
.grain.chapter{background:#eaf0f7;color:#25507a;border-color:#c5d6e8}
.grain.book{background:#f5eef6;color:#7a3a80;border-color:#e0cbe3}
.grain.elem{background:#f3eefa;color:#5a3a90;border-color:#d9cbe9}
.grain.gold{background:#fbf3e0;color:#8a6212;border-color:#ecd9a8}
.track{font:600 .70rem/1 -apple-system,sans-serif;letter-spacing:.5px;text-transform:uppercase;
 padding:3px 8px;border-radius:4px;border:1px solid}
.track.corpus{background:#eef4fb;color:#20548a;border-color:#c3d8ee}
.track.dev{background:#fdf1ec;color:#9a4a22;border-color:#f0cfbe}
.tracks{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0 4px}
.tcard{border:1px solid #d9e2ea;border-radius:8px;padding:12px 14px;background:#fff}
.tcard h3{margin:0 0 6px;font-size:1rem}
.tcard .big{font:700 1.5rem/1.1 -apple-system,sans-serif;color:#20548a}
@media(max-width:760px){.tracks{grid-template-columns:1fr}}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.up{color:#1a7a44;font-weight:600} td.down{color:#a3311f;font-weight:600}
tr.confound{background:#fdf4f2}
/* The ledger's reason is the whole point of the row — never let it clip off the scroll edge. */
#ledger td:last-child{white-space:normal;min-width:22rem;line-height:1.35}
#ledger td:last-child .ce{color:#a3311f;font-weight:600}
.pill.open{background:#fbe9e6;color:#a3311f;border:1px solid #f0c8c0}
.pill.closed{background:#eaf5ee;color:#1a7a44;border:1px solid #bfe3cd}
.controls{position:sticky;top:0;z-index:30;display:flex;gap:20px;align-items:center;flex-wrap:wrap;
 background:rgba(255,255,255,.96);backdrop-filter:blur(4px);border-bottom:1px solid var(--rule);padding:12px 34px}
.controls .grp{display:flex;gap:6px;align-items:center}
label.lbl{font-size:.84rem;color:var(--mut);margin-right:2px}
button.tog{background:#fff;color:var(--ink);border:1px solid var(--rule);border-radius:6px;
 padding:6px 12px;cursor:pointer;font-size:.86rem}
button.tog.on{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600}
select{background:#fff;color:var(--ink);border:1px solid var(--rule);border-radius:6px;padding:6px 9px;font-size:.86rem}
.cards{display:flex;gap:14px;flex-wrap:wrap}
.card{flex:1;min-width:158px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card .big{font-size:1.7rem;font-weight:700;font-family:Georgia,serif}
.card .lbl{color:var(--mut);font-size:.82rem}
.delta.up{color:var(--pass)}.delta.down{color:var(--faildeep)}
.cg-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:6px;margin-top:8px}
.cg-t{border:1px solid var(--line);border-radius:6px;padding:6px 4px;text-align:center;cursor:pointer;background:var(--bg)}
.cg-t:hover{border-color:var(--accent)}
.cg-n{font-weight:700;font-family:Georgia,serif}
.cg-r{font-size:1.05rem}
.cg-s{font-size:.68rem;color:var(--mut)}
.cg-closed{background:#eaf7ee;border-color:#9ccfae}
.cg-near{background:#fffbe8;border-color:#e8d48a}
.cg-blk{background:#f3f0fa;border-color:#c5b8e0}
.cg-sel{outline:2px solid var(--accent);outline-offset:1px}
.cg-d{font-size:.72rem;color:var(--pass)}
.cg-tab{width:auto;min-width:320px;margin-top:6px}
.cg-tab th{font-size:.75rem;color:var(--mut);padding:2px 8px}
.cg-v{color:var(--mut);text-align:right;padding-right:8px;font-size:.78rem}
.cg-c{text-align:center;padding:2px 8px;font-size:.76rem;border:1px solid var(--line)}
.cg-p{background:#eaf7ee;color:#2e7d4f}
.cg-f{background:#fdecec;color:#b2182b;cursor:pointer}
.cg-f:hover{outline:1px solid var(--fail)}
.cg-b{background:#f3f0fa;color:#6a5aa0}
.cg-txt{font-family:Georgia,serif;margin-top:6px;line-height:1.45}
/* The grid and the stacked verse view sit side by side: the grid says WHICH cell is short, the stack says
   what each witness actually printed. Reading them together is the whole diagnostic act, so they must not be
   separated by a scroll. `minmax(0,1fr)` (not `1fr`) keeps a long verse from forcing the grid off-screen. */
.cg-split{display:grid;grid-template-columns:auto minmax(0,1fr);gap:22px;align-items:start}
@media(max-width:900px){.cg-split{grid-template-columns:1fr}}
.cg-stack{position:sticky;top:12px;border-left:3px solid var(--accent);padding-left:14px}
.cg-row{margin:0 0 11px}
.cg-row .who{font-size:.72rem;letter-spacing:.04em;text-transform:uppercase;color:var(--mut)}
.cg-row .who b{color:var(--ink);letter-spacing:0}
.cg-row .t{font-family:Georgia,serif;line-height:1.45;margin-top:2px}
.cg-row.ref .t{color:#334}
.cg-row.jan .t{color:#555;font-style:italic}
.cg-sep{border-top:1px dashed #ccc;margin:13px 0 11px;font-size:.72rem;color:var(--mut);
        letter-spacing:.04em;text-transform:uppercase;padding-top:9px}
.cg-v{cursor:pointer}
.cg-v:hover{text-decoration:underline}
.cg-v.sel{font-weight:700;color:var(--ink)}
.cg-sc{font-size:.7rem;color:var(--mut);font-weight:400;letter-spacing:0;text-transform:none}
.cg-bad{color:#a11}
table{border-collapse:collapse;width:100%;font-size:.83rem}
th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);cursor:pointer;user-select:none;position:sticky;top:0;background:var(--panel);
 border-bottom:2px solid var(--rule)}
tr:hover td{background:#f2f6fa}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.92em}
.note{color:var(--mut);font-size:.86rem;margin:8px 0}
.callout{background:#fff6ef;border:1px solid #f2c9a3;border-left:4px solid var(--fail);border-radius:6px;
 padding:11px 15px;margin:12px 0}
.callout b{color:var(--faildeep)}
.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--mut);font-size:.82rem;margin:8px 0}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.scrollx{overflow-x:auto;position:relative;border:1px solid var(--line);border-radius:6px;background:#fff}
.scrollx::after{content:"⇄ scroll";position:sticky;right:6px;bottom:6px;float:right;font-size:.7rem;
 color:var(--faint);background:rgba(255,255,255,.85);padding:2px 7px;border:1px solid var(--line);border-radius:10px}
.scrollhint{font-size:.74rem;color:var(--faint);margin:2px 0 6px}
.gridwrap{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.otnt-head{font:700 .82rem/1 Georgia,serif;color:var(--accent2);margin:14px 0 4px;padding-bottom:3px;
 border-bottom:1px solid var(--line)}
.mini{background:var(--bg);border:1px solid var(--line);border-radius:7px;padding:10px 12px;cursor:zoom-in}
.mini:hover{border-color:var(--accent)}
svg text{fill:var(--ink)}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.72rem;font-weight:600}
.pill.pass{background:#e6f4ec;color:var(--pass)}
.pill.fail{background:#fdece0;color:var(--fail)}
.statuscols{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.statuscols ul{margin:4px 0;padding-left:18px}
.statuscols li{font-size:.86rem;margin:4px 0}
#drill{position:fixed;right:0;top:0;bottom:0;width:400px;background:var(--panel);border-left:1px solid var(--rule);
 padding:20px;overflow:auto;transform:translateX(100%);transition:transform .18s;z-index:60;box-shadow:-10px 0 30px rgba(20,30,45,.18)}
#drill.open{transform:none}
#drill .x{float:right;cursor:pointer;color:var(--mut);font-size:20px}
#modal{position:fixed;inset:0;background:rgba(15,20,28,.55);z-index:80;display:none;align-items:center;justify-content:center}
#modal.open{display:flex}
#modalbox{background:#fff;border-radius:10px;padding:20px 24px;max-width:94vw;max-height:92vh;overflow:auto;box-shadow:0 12px 40px rgba(0,0,0,.35)}
#modalbox .x{float:right;cursor:pointer;color:var(--mut);font-size:22px}
.toc{columns:2;font-size:.86rem;color:var(--accent)}
.toc a{display:block;margin:2px 0}
</style></head>
<body>
<header>
  <h1>OriginalDR — re-OCR statistical report <span class="grain" id="phaseTag"></span></h1>
  <div class="sub" id="hdrsub"></div>
  <div id="verbanner"></div>
</header>

<div class="controls">
  <div class="grp"><label class="lbl">Gate</label>
    <button class="tog" id="g-archaic" onclick="setGate('archaic')">Archaic-preeminent</button>
    <button class="tog" id="g-modern" onclick="setGate('modern')">Modern-only</button>
    <button class="tog" id="g-both" onclick="setGate('both')">Old AND-gate</button>
  </div>
  <div class="grp"><label class="lbl">Book</label><select id="bookSel" onchange="setBook(this.value)"></select></div>
  <div class="grp sub" id="gateExplain"></div>
</div>

<div class="wrap">

<section id="s-head">
  <h2>Results — headline</h2>
  <div id="vercompare"></div>
  <div class="cards" id="cards"></div>
  <div class="callout" id="callout"></div>
</section>


<section id="s-campaign">
  <div class="figtitle" style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap">
    <h2>The Live Board: chapter by chapter and verse by verse</h2>
    <span style="font-size:13px;color:#555">Book
      <select id="cg-book" onchange="cgBook(this.value)" style="font-size:13px;padding:2px 6px"></select>
    </span>
  </div>
  <div class="note"><b>This section is the only one on this page that moves when a chapter is worked.</b>
  Everything below it renders the 5-book P3 pilot audit (<code>coverage-audit-verse.json</code>), a different
  pipeline at a different grain, which does not change when a Genesis chapter closes. This one reads
  <code>.campaign/matrix-genesis-N.json</code> &mdash; the artifact the campaign actually moves.
  A cell is one <b>verse &times; source</b> scored against <b>all four</b> references; it passes only at
  &ge;&thinsp;0.90 against <b>each</b> of them. <span class="cg-b">Blocked</span> means a reference is absent
  for that verse, so no recognizer can close it &mdash; it is excluded from the achievable denominator and
  stays open.</div>
  <div id="cg-prov"></div>
  <div class="cards" id="cg-cards"></div>
  <div id="cg-prog"></div>
  <div class="figtitle" style="margin-top:18px" id="cg-boardhdr"><h3>Chapters &mdash; click one for its verse grid</h3></div>
  <div id="cg-board"></div>
  <div id="cg-detail"></div>
  <div id="cg-flags"></div>
</section>


<section id="s-tracks">
  <div class="figtitle"><h2>How to read this report — two tracks that must not be confused</h2></div>
  <div class="note">This report measures two different things, and conflating them has previously made real
  progress look like none and vice versa. <b>Every figure below is labelled with the track it belongs to.</b></div>
  <div class="tracks">
    <div class="tcard">
      <h3><span class="track corpus">Corpus-wide</span> &nbsp;the deliverable</h3>
      <div class="big" id="trk-corpus">—</div>
      <div class="note" style="margin:6px 0 0">Every verse of the pilot books &times; every admitted witness
      volume, scored <b>witness-anchored</b> (against the reference editions — what production can actually do
      at runtime, with no gold available). This is the number that says whether the Douay-Rheims is being
      transcribed. It moves only when the pipeline is <b>applied to the corpus</b>, which is why it sat flat
      for weeks while the ladder improved: the improved localizer was never wired into the audit.</div>
    </div>
    <div class="tcard">
      <h3><span class="track dev">Dev set (GT)</span> &nbsp;the instrument</h3>
      <div class="big" id="trk-dev">—</div>
      <div class="note" style="margin:6px 0 0">The Jarvis diplomatic <b>Gold Transcript</b> pages, scored
      <b>gold-anchored</b> — the truth, not a proxy. This is where a re-OCR rung or arm is developed and
      validated. <b>It is a comparative baseline, NOT the authority</b> on localization, presence, interval
      alignment or verse/line — janvier and madueke are primary for those, and the gold itself may need
      standardising against janvier's structure. A gain here is a gain in the INSTRUMENT; it becomes a gain in
      the deliverable only once it is wired through and the corpus figure moves.</div>
    </div>
  </div>
  <div id="trk-note" class="note"></div>
</section>

<section id="s-inventory">
  <div class="figtitle"><h2>Inventory — what this report covers</h2><span class="grain book">book</span><span class="grain elem">element</span></div>
  <div class="note">The exact scope of this pilot render: the <b>books</b> and <b>apparatus elements</b> it measures, and nothing else. The build fails if the audited scope drifts beyond the declared P3 pilot, so this table is a guardrail made visible — a reader can confirm at a glance that the report stays in-scope.</div>
  <div id="inventory"></div>
</section>

<section id="s-grain">
  <div class="figtitle"><h2>Pass rate by grain</h2><span class="grain book">book</span><span class="grain chapter">chapter</span><span class="grain verse">verse</span></div>
  <div class="note">The SAME per-verse scores, aggregated at three grains — fraction of loci where at least one scan witness passes: at <b>verse</b> grain, that verse; at <b>chapter</b> grain, <b>≥ (m−1) of the chapter's m verses</b> (strict rule, ≤ 1 verse of error); at <b>book</b> grain, any verse. Verse grain rescues faithful verses that a bad chapter-average would bury — the core reason the rework moved to verse/element grain.</div>
  <div id="grainbreak"></div>
</section>

<section id="s-methods">
  <h2>Methods</h2>
  <div id="methods"></div>
</section>

<section id="s-rung0">
  <div class="figtitle"><h2>Rung-0 sign-off — visual diagnosis of the worst-scoring loci</h2><span class="grain elem">element</span></div>
  <div class="note">The re-OCR ladder's <b>MANDATORY rung-0 diagnostic gate</b>: for each worst-scoring locus, the ladder rasterizes the source page and Jarvis visually inspects it, naming the failure mode and the recommended rung, <b>before</b> any OCR method is chosen. Score alone says a page FAILED, never WHY — the eye distinguishes "bad OCR of the right page" from "good OCR of the wrong page". A rung ≥ 1 may not fire without a rung-0 verdict for the locus. Source of record: <span class="mono">diag-reocr/index.json</span> · durable artifact: <span class="mono">RUNG0-SIGNOFF-v9.md</span>.</div>
  <div id="rung0"></div>
</section>

<section id="s-v1">
  <div class="figtitle"><h2>V1 · Identity-score distributions per scan source</h2><span class="track corpus">Corpus-wide</span><span class="grain verse">verse</span></div>
  <div class="note">Char-level identity of each scan's OCR vs its references, one panel per witness, grouped by Old / New Testament. Blue = modern_id (vs Janvier/Sabates←Madueke_b); orange = archaic_id (vs s_dismas←odr_com). Dashed line = 0.90 bar. X-axis auto-fits each panel's data range. <b>Click a panel to zoom.</b></div>
  <div class="legend"><span><i style="background:var(--ref)"></i>modern_id</span><span><i style="background:var(--fail)"></i>archaic_id</span><span><i style="background:var(--accent)"></i>0.90 bar</span></div>
  <div id="v1"></div>
</section>

<section id="s-v2">
  <div class="figtitle"><h2>V2 · Modern vs archaic identity</h2><span class="track corpus">Corpus-wide</span><span class="grain verse">verse</span></div>
  <div class="note">One point per scan × verse; Genesis, Psalms, Matthew and Apocalypse plotted separately. x = modern_id, y = archaic_id; quadrant lines at 0.90; diagonal = equal. Colour = source; larger markers pass the shown gate. <b>Click any panel to zoom (⤢).</b></div>
  <div class="gridwrap" id="v2"></div>
</section>

<section id="s-v3">
  <div class="figtitle"><h2>V3 · Pass / fail heatmap</h2><span class="track corpus">Corpus-wide</span><span class="grain chapter">chapter</span></div>
  <div class="note">Every chapter, exhaustively. Rows = witnesses sorted by preeminence: <span style="color:var(--refarc);font-weight:600">archaic references</span> first, then <span style="color:var(--ref);font-weight:600">modern references</span>, then scans (strongest→weakest). <b>Tracks are limited per book</b> to the witnesses that should carry it (source-index expected coverage) plus any that actually attest — a source that legitimately lacks a book is omitted rather than shown as an empty "missing" row, while an <i>expected-but-failed</i> witness still appears (a real gap, never hidden). Columns = chapters. A scan cell is <span style="color:var(--pass);font-weight:600">green</span> when it passes <b>≥ (m−1) of the chapter's m verses</b> (strict rule: at most one verse of error); a <b>localized-but-failed</b> cell is shaded by how close its median score sits to 0.90 (deeper red = further below). Click a cell to inspect. Recolours with the gate toggle.</div>
  <div class="legend">
    <span><i style="background:var(--pass)"></i>pass (majority of verses)</span>
    <span><i style="background:var(--fail)"></i>localized, near miss</span>
    <span><i style="background:var(--faildeep)"></i>localized, far below</span>
    <span><i style="background:var(--ref)"></i>reference (auto-pass)</span>
    <span><i style="background:var(--absent)"></i>absent</span>
  </div>
  <div class="scrollhint">wide figure — scroll horizontally →</div>
  <div class="scrollx" id="v3"></div>
</section>

<section id="s-v4">
  <div class="figtitle"><h2>V4 · Witness depth vs E(v)</h2><span class="track corpus">Corpus-wide</span><span class="grain verse">verse</span></div>
  <div class="note">Backward gate at verse grain: realized witness_count per verse under the current gate, shown as a MOVEMENT — <b>grey = the pre-re-OCR baseline, blue = current</b> — because a snapshot of this histogram cannot distinguish a pipeline that never ran from one that ran and failed. The figure to take away is in the caption beneath the chart.</div>
  <div id="v4"></div>
</section>

<section id="s-v5">
  <div class="figtitle"><h2>V5 · Gate comparison &amp; phase progression</h2><span class="track corpus">Corpus-wide</span><span class="grain verse">verse</span></div>
  <div class="note">Left: passing scan&times;verse records under each gate, per source — archaic-preeminent vs modern-only vs the old AND-gate, from identical scores. <b>The AND-gate arm is retained for continuity only: it compares against a scheme abandoned before this phase and answers a question no longer being asked.</b> The live question is below. Right: phase progression from the chapter-grain baseline to this verse-grain phase (note the grain change; counts are not directly comparable, hence both denominators are shown).</div>
  <div id="v5"></div>
  <div id="governance" class="note"></div>
  <div id="phaseprog" class="note"></div>
</section>

<section id="s-v6">
  <div class="figtitle"><h2>V6 · Per-source summary</h2><span class="track corpus">Corpus-wide</span><span class="grain verse">verse</span></div>
  <div class="scrollx"><table id="v6"><thead></thead><tbody></tbody></table></div>
</section>

<section id="s-apparatus">
  <div class="figtitle"><h2>V7 · Apparatus (front / back-matter) — pilot</h2><span class="track corpus">Corpus-wide</span><span class="grain elem">element</span></div>
  <div class="note"><b>V8 pull-forward:</b> the <span class="mono">s_dismas</span> <span class="mono">01-front-matter.pdf</span> is parsed for <b>both</b> testaments into element-grain <b>archaic</b> references — OT approbatio + OT preface + <b>NT preface</b> (41 pp) — and content-localized in the OT and NT scans. The <b>modern</b> apparatus reference is the <span class="mono">janvier-s reference/</span> set — the original DR apparatus in modern spelling, keyed 1:1 to the slots (the same source the reconstruction masks; not a Confraternity revision). Gating stays archaic-preeminent: archaic governs where it exists, else modern governs. Bars show each scan's archaic_id vs the 0.90 gate; grey = not localized. The single-page <b>approbatio</b> is scored whole (attests in 6/9 OT scans after its boundary was corrected); the multi-page <b>prefaces</b> are scored on their aligned <b>opening window</b> only (the whole-blob char DP is infeasible and the s_dismas re-pagination invalidates page alignment — full scoring is a P5 task), so they are marked <span class="mono">sample</span> and never credit a witness. The inventory carries no archaic title-page / privilege / censura / censure, so those slots stay OPEN. Every below-bar / sampled / absent element stays <b>OPEN</b> and feeds P4/P5.</div>
  <div id="apparatus"></div>
</section>

<section id="s-lift">
  <div class="figtitle"><h2>V9 · Re-OCR stream ladder — base &rarr; R2 &rarr; R3 &rarr; &#383;-arbiter</h2><span class="track dev">Dev set (GT)</span><span class="grain verse">verse</span><span class="grain gold">gold-anchored</span></div>
  <div class="note"><b>REP-2 + REP-4.</b> Every other figure in this report is <b>witness-anchored</b> (scored against reference editions, which is what production can do at runtime). This one is <b>GOLD-anchored</b>: each verse is scored against the Jarvis diplomatic transcription of that very page, janvier-cut, archaic-preeminent — the truth, not a proxy. That is why it is the only place the reOCR mandate can actually be verified rather than asserted. Columns are the escalation ladder in order: <span class="mono">base</span> (the legacy scan OCR this report baselines), <span class="mono">R2</span> (fine-tuned kraken, the production re-OCR), <span class="mono">R3</span> (olmOCR re-read of the verse's pixel crop, for verses the gate flagged), <span class="mono">&#383;</span> (the in-agent &#383;-faithful arbiter's terminal state for the diplomatic surface). A blank cell means that rung was never reached for that verse, never that it passed. <b>Pages whose R2 collapses far below base are FLAGGED as confounds and excluded from the representative aggregate</b> — with the reason shown — because such a collapse is an addressing/layout failure, not recognizer quality; No Silent Degradation cuts both ways, so a false BAD is reported too. Residual R2 &lt; 0.90 is exactly the R3 escalation set, and whatever R3 and the arbiter fail to lift stays <b>OPEN</b> in the ledger below.</div>
  <div id="liftagg"></div>
  <div class="scrollx"><table id="lift"><thead></thead><tbody></tbody></table></div>
</section>

<section id="s-matter">
  <div class="figtitle"><h2>V10 · Matter as first-class books</h2><span class="track corpus">Corpus-wide</span><span class="grain elem">section &times; source</span></div>
  <div class="note"><b>REP-5.</b> The front/back matter — tables, prefaces, arguments, catenae — is <b>not apparatus around the text; it is text</b>, and this report treats each curated matter section as a book with its own row per source. Scores are the window-grain PARA pool and the interval-grain APPARATUS pool from <span class="mono">matter_match_report.py</span>, measured against the Jarvis matter ground truth. <b>The honest headline is that almost nothing passes</b>: matter is set in dense italic with heavy abbreviation and the legacy OCR barely reads it, which mirrors the scripture baseline exactly and is the same re-OCR mandate stated for a different body of text. Every row below the bar is flagged for re-OCR and stays OPEN; none is accepted. <span class="mono">own</span> marks the source the ground truth was transcribed from — it is scored like any other and given no credit for being the origin.</div>
  <div id="mattersum" class="note"></div>
  <div class="scrollx"><table id="matter"><thead></thead><tbody></tbody></table></div>
</section>

<section id="s-bookaudit">
  <div class="figtitle"><h2>V12 &middot; Book-grain cross-witness audit</h2><span class="track corpus">Corpus-wide</span><span class="grain verse">book &times; witness</span></div>
  <div class="note"><b>One book, every witness that should carry it, each defect attributed to one stack layer.</b> Chasing a single source's gaps wherever they fall mixes defects that have nothing to do with each other. Holding the BOOK fixed and varying the WITNESS makes the witnesses controls for one another, and one question then splits two entirely different classes of defect: <b>if every witness fails the same verse, no witness's recognizer is at fault</b> &mdash; the defect is VERTICAL (addressing, pinning, segmentation, reference, gating); <b>if one witness fails a verse its siblings read correctly</b>, it is HORIZONTAL &mdash; that volume's scan, layout or recognizer head. Both defect&nbsp;#8 (line-range truncation) and defect&nbsp;#9 (page furniture read as a heading) presented as recognition problems and were neither; a sibling witness reading the same verse correctly is what exposed them. Failure modes are decomposed by the shape of the diff against the archaic reference, and each mode names the layer that owns it.</div>
  <div id="vstack" class="note"></div>
  <div id="bookauditsum" class="note"></div>
  <div class="scrollx"><table id="bookaudit"><thead></thead><tbody></tbody></table></div>
  <div class="note"><b>Anatomy of the ALL-FAIL verses.</b> A verse no witness can read is compared against the verses that pass in EVERY witness, from the same book and the same pipeline. An axis on which the two groups AGREE is as informative as one where they differ: it rules a cause out. Axes where both groups sit at ~0 are reported as carrying no signal rather than ranked, because a ratio of 0 or infinity there would print as the strongest finding on the page while meaning nothing.</div>
  <div id="anatomy"></div>
  <div class="note"><b>Single-chapter rescore &mdash; every verse against ALL FOUR references.</b> The gate consults ONE governing reference, which merges causes that live in different layers. Scoring each witness against s_dismas, odr_com, sabates_a and madueke_b separates them, and exposes the case the gate cannot see by construction: <b>the witnesses and both modern references agree, and the archaic reference is the outlier</b>. Classes are decided first-applicable-wins, because they are not independent and the earliest is the one worth fixing.</div>
  <div id="rescore"></div>
</section>

<section id="s-ledger">
  <div class="figtitle"><h2>V11 · OPEN ledger — what blocks the deliverable</h2><span class="track corpus">Corpus-wide</span><span class="grain verse">verse</span></div>
  <div class="note"><b>The terminal worklist.</b> A unit that never reached its threshold is never converted into an accepted state so a pipeline can report success. It lands here, and while this list is non-empty <b>the deliverable is blocked</b>. Each row names the locus, the rungs actually tried, the best score any rung achieved, and the reference it was judged against. <span class="mono">content-error-found-by-arbiter</span> rows are the most instructive: the verse passed the per-verse content gate, and reading its crop to settle the long-&#383; surface exposed a single wrong word riding through underneath — evidence that a per-verse threshold cannot see a per-token misread, which is an open design question about the gate's grain, not four incidents.</div>
  <div id="ledgersum" class="note"></div>
  <div class="scrollx"><table id="ledger"><thead></thead><tbody></tbody></table></div>
</section>

<section id="s-interp">
  <h2>Interpretation &amp; limits</h2>
  <div id="interp"></div>
</section>

<section id="s-wl">
  <div class="figtitle"><h2>Re-OCR / investigate worklist</h2><span class="grain chapter">chapter</span></div>
  <div class="note">Chapters below E(v), worst-first, with the localized-but-failed scans that re-OCR must lift and how many verses fall short. This is what P3 consumes. (Placed last, as the actionable appendix.)</div>
  <div class="scrollx"><table id="wl"><thead></thead><tbody></tbody></table></div>
</section>

</div>

<div id="drill"><span class="x" onclick="closeDrill()">✕</span><div id="drillBody"></div></div>
<div id="modal" onclick="if(event.target.id==='modal')closeModal()"><div id="modalbox"><span class="x" onclick="closeModal()">✕</span><div id="modalBody"></div></div></div>

<script>
const DATA = __DATA_JSON__;
let GATE = 'archaic';
let BOOK = '__all__';
const GATES = {archaic:'pass_archaic', modern:'pass_modern', both:'pass_both'};
const C = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const COL = {pass:C('--pass'),fail:C('--fail'),faildeep:C('--faildeep'),ref:C('--ref'),refarc:C('--refarc'),absent:C('--absent'),
 unloc:C('--unloc'),accent:C('--accent'),mut:C('--mut'),ink:C('--ink')};
const SRCCOL=['#1f5c8b','#1a9850','#f16913','#8073ac','#0b6b6b','#b2182b','#d6604d','#4393c3','#66a61e','#e08214','#5e3c99'];
function el(t,a,txt){const e=document.createElementNS('http://www.w3.org/2000/svg',t);for(const k in(a||{}))e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e;}
function svg(w,h){return el('svg',{width:w,height:h,viewBox:`0 0 ${w} ${h}`});}
function fmt(v){return v==null?'—':(+v).toFixed(3);}
function clamp(v,lo,hi){return v<lo?lo:(v>hi?hi:v);}
function scanColorMap(){const m={};DATA.scan_ids.forEach((s,i)=>m[s]=SRCCOL[i%SRCCOL.length]);return m;}

/* ---------- Genesis campaign: the live board (see the section note for why it is separate) ---------- */
const CG = DATA.campaign || {chapters:[],totals:{},history:[]};
let CGSEL = null;
function cgPct(x){return (100*x).toFixed(1)+'%';}
function cgCards(){
  const t = CG.totals||{}, h = CG.history||[];
  const prev = h.length>1 ? h[h.length-2] : null;
  const d = prev ? (t.pass - prev.pass) : 0;
  const delta = prev ? ` <span class="cg-d">${d>=0?'+':''}${d} since ${prev.at.slice(5,16).replace('T',' ')}</span>` : '';
  document.getElementById('cg-cards').innerHTML =
   [['cells &ge; 0.90 of ACHIEVABLE', `${t.pass}/${t.achievable}`, cgPct(t.rate_achievable||0)+delta],
    ['chapters CLOSED', `${t.closed}/${(CG.chapters||[]).length}`, 'every cell &ge;0.90 and no reference gap'],
    ['cells BLOCKED by an absent reference', `${t.blocked}`, 'no recognizer can close these'],
    ['cells still short of the bar', `${(t.achievable||0)-(t.pass||0)}`, 'the actual remaining work']]
   .map(([k,v,s])=>`<div class="card"><div class="lbl">${k}</div><div class="big">${v}</div><div class="lbl">${s}</div></div>`).join('');
}
function cgProg(){
  const h = (CG.history||[]).slice(-40);
  if(h.length<2){document.getElementById('cg-prog').innerHTML=''; return;}
  const W=Math.max(560, h.length*46), H=150, P=34;
  const lo=Math.min(...h.map(e=>e.pass)), hi=Math.max(...h.map(e=>e.pass));
  const span=Math.max(1,hi-lo);
  const x=i=>P+ i*(W-2*P)/Math.max(1,h.length-1);
  const y=e=>H-P-((e.pass-lo)/span)*(H-2*P);
  let s=`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="max-width:100%">`;
  s+=`<polyline fill="none" stroke="${COL.accent}" stroke-width="2" points="${h.map((e,i)=>x(i)+','+y(e)).join(' ')}"/>`;
  h.forEach((e,i)=>{ s+=`<circle cx="${x(i)}" cy="${y(e)}" r="3.5" fill="${COL.accent}"><title>${e.at}
${e.pass}/${e.achievable} = ${(100*e.rate_achievable).toFixed(2)}%  closed ${e.closed}${e.note?'\\n'+e.note:''}</title></circle>`; });
  s+=`<text x="${P}" y="14" font-size="11" fill="${COL.mut}">cells at &ge;0.90 over time — ${lo} to ${hi}; hover a point for its note</text></svg>`;
  document.getElementById('cg-prog').innerHTML = s;
}
function cgBoard(){
  const cs = CG.chapters||[];
  document.getElementById('cg-board').innerHTML = '<div class="cg-grid">' + cs.map(c=>{
    const cls = c.closed ? 'cg-closed' : (c.blocked ? 'cg-blk' : (c.short<=8 ? 'cg-near' : ''));
    return `<div class="cg-t ${cls}${CGSEL===c.ch?' cg-sel':''}" onclick="cgPick(${c.ch})">
      <div class="cg-n">${c.ch}</div>
      <div class="cg-r">${(100*c.rate).toFixed(0)}%</div>
      <div class="cg-s">${c.closed?'CLOSED':(c.short+' short')}</div></div>`;
  }).join('') + '</div>';
}
function cgPick(ch){ CGSEL = (CGSEL===ch? null : ch); CGVERSE = null; cgBoard(); cgDetail(); }
/* ---- book picker ------------------------------------------------------------------------------------
   All 106 divisions the campaign could cover — 76 scripture books from `skeleton.json` plus the 30 matter
   sections this project scores as first-class rather than as trimmings. Only Genesis has matrices, and the
   picker SAYS SO on every other entry instead of drawing an empty board. An empty grid reads as "measured
   and found perfect"; the truth is "not measured", and those must never look alike.                     */
let CGBOOK = 'genesis';
function cgBookList(){
  const bs = DATA.campaign_books || [];
  const sel = document.getElementById('cg-book'); if(!sel) return;
  const groups = [['OT','Old Testament'],['NT','New Testament'],['appendix','Appendix'],['matter','Front &amp; back matter']];
  sel.innerHTML = groups.map(([k,lbl])=>{
    const items = bs.filter(b=>b.kind===k);
    if(!items.length) return '';
    return `<optgroup label="${lbl}">` + items.map(b=>
      `<option value="${b.slug}"${b.slug===CGBOOK?' selected':''}>${b.label}${b.has_board?'':' — no board yet'}</option>`
    ).join('') + '</optgroup>';
  }).join('');
}
function cgBook(slug){ CGBOOK = slug; CGSEL = null; CGVERSE = null; cgRender(); }
function cgNoBoard(){
  const b = (DATA.campaign_books||[]).find(x=>x.slug===CGBOOK) || {label:CGBOOK};
  return `<div class="callout"><b>${b.label} has no campaign board yet.</b>
    The campaign has produced matrices for <b>Genesis only</b>; nothing has been measured at cell grain for
    this division, so there is nothing to show. This is a statement about the WORK, not about the text —
    ${b.label} is not passing, failing, or blocked here, it is <b>unmeasured</b>.
    ${b.chapters?`It has ${b.chapters} chapters awaiting a board.`:''}
    <div class="note" style="margin-top:8px">To open one:
    <code>chapter_campaign.py --chapters 1-${b.chapters||1} --phase measure</code> against
    <code>${b.slug}</code>.</div></div>`;
}
function cgDetail(){
  const box = document.getElementById('cg-detail');
  if(CGSEL==null){ box.innerHTML=''; return; }
  const c = (CG.chapters||[]).find(x=>x.ch===CGSEL);
  if(!c){ box.innerHTML=''; return; }
  const srcs=['S1','S3','S6','S9'];
  let s = `<div class="figtitle" style="margin-top:16px"><h3>Genesis ${c.ch} &mdash; ${c.pass}/${c.cells} cells,
    ${c.short} short of the bar${c.blocked?`, ${c.blocked} blocked (${(c.ref_gaps||[]).join(', ')} absent)`:''}</h3></div>`;
  s += `<div class="note">Per source: ` + srcs.map(k=>`<b>${k}</b> ${((c.src_rates||{})[k]!=null)?(100*c.src_rates[k]).toFixed(0)+'%':'—'}`).join(' &nbsp;·&nbsp; ')
     + `. Click a <b>verse number</b> for every witness stacked beside the references; click a failing cell for
        that one source.</div>`;
  s += '<div class="cg-split"><div>';
  s += '<table class="cg-tab"><thead><tr><th>v</th>' + srcs.map(k=>`<th>${k}</th>`).join('') + '</tr></thead><tbody>';
  for(const row of c.grid){
    s += `<tr><td class="cg-v${CGVERSE===row.v?' sel':''}" onclick="cgVerse(${row.v})"
             title="click for all witnesses of this verse">${row.v}</td>`;
    for(const cell of row.cells){
      if(row.blocked) s += `<td class="cg-c cg-b" title="a reference is absent for this verse">blk</td>`;
      else if(cell.ok) s += `<td class="cg-c cg-p">&#10003;</td>`;
      else s += `<td class="cg-c cg-f" onclick="cgCell(${c.ch},${row.v},'${cell.s}')" title="click to read">${fmt(cell.worst)}</td>`;
    }
    s += '</tr>';
  }
  s += '</tbody></table></div><div id="cg-stack" class="cg-stack"></div></div><div id="cg-cell"></div>';
  box.innerHTML = s;
  cgStack();
}
/* ---- the stacked verse view -------------------------------------------------------------------------
   All four witnesses, then the segmentation the matrix is cut on, then the references, for ONE verse. The
   order is deliberate: what the scans say, then what cut them, then what they are judged against. Reading
   the judgement first is how a reference defect gets mistaken for a reading failure — the error that cost
   this campaign 20 cells before the signal-6 correction.
   Passing cells are shown too. A view that hid them would answer "why did this fail" but never "is the one
   that PASSED actually right", and those are the same question asked of different cells.                */
let CGVERSE = null;
function cgVerse(v){ CGVERSE = (CGVERSE===v ? null : v); cgDetail(); }
function esc(t){return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function cgStack(){
  const box=document.getElementById('cg-stack'); if(!box) return;
  if(CGVERSE==null){
    box.innerHTML = `<div class="note" style="margin:34px 0 0">Select a <b>verse number</b> in the left column
      to stack every contributing source here beside the Janvier segmentation and the archaic references.</div>`;
    return;
  }
  const c=(CG.chapters||[]).find(x=>x.ch===CGSEL); if(!c) return;
  const key=String(CGVERSE);
  const cg=(c.cellgrid||{})[key], rf=(c.refs_by_verse||{})[key], jn=(c.janvier_by_verse||{})[key];
  if(!cg){
    box.innerHTML = `<div class="note" style="margin:34px 0 0"><b>This chapter's matrix predates the stacked
      view.</b> It was written before the per-cell text was stored, so the passing cells' readings are not in
      the artifact — re-run <code>chapter_campaign.py --chapters ${c.ch} --phase measure</code> to populate it.
      Nothing is inferred here; an empty stack would read as "no witnesses", which is not what this means.</div>`;
    return;
  }
  const row=(c.grid||[]).find(r=>r.v===CGVERSE)||{};
  let s=`<div class="figtitle" style="margin:0 0 10px"><h3>Genesis ${c.ch}:${CGVERSE}</h3></div>`;
  if(row.blocked) s+=`<div class="note"><b>Blocked</b> — a reference is absent for this verse, so no
     recognizer can close it. It stays open and is out of the achievable denominator.</div>`;
  for(const k of ['S1','S3','S6','S9']){
    const d=cg[k]; if(!d) continue;
    const sc=d.score||{}; const vals=Object.values(sc).filter(x=>x!=null);
    const worst=vals.length?Math.min(...vals):null;
    const bad=(worst!=null&&worst<0.90);
    s+=`<div class="cg-row"><div class="who"><b>${k}</b>${d.from?` &middot; ${esc(d.from)}`:''}
        <span class="cg-sc${bad?' cg-bad':''}">${worst!=null?('worst '+worst.toFixed(3)):'no score'}</span></div>
        <div class="t">${esc(d.text)||'<span class="sub">(not localized on this source)</span>'}</div></div>`;
  }
  s+=`<div class="cg-sep">Janvier &mdash; the segmentation this matrix is cut on, not a reference</div>`;
  s+=`<div class="cg-row jan"><div class="t">${esc(jn)||'<span class="sub">(absent)</span>'}</div></div>`;
  s+=`<div class="cg-sep">References &mdash; archaic governs the gate; modern is signal only</div>`;
  for(const k of ['s_dismas','odr_com','sabates_a','madueke_b']){
    const t=(rf||{})[k];
    s+=`<div class="cg-row ref"><div class="who"><b>${k}</b> <span class="cg-sc">${
        (k==='s_dismas'||k==='odr_com')?'archaic':'modern'}</span></div>
        <div class="t">${esc(t)||'<span class="sub">(absent for this verse)</span>'}</div></div>`;
  }
  box.innerHTML=s;
}
function cgCell(ch,v,src){
  const c=(CG.chapters||[]).find(x=>x.ch===ch); const row=c.grid.find(r=>r.v===v);
  const cell=row.cells.find(z=>z.s===src);
  document.getElementById('cg-cell').innerHTML =
    `<div class="callout"><b>Genesis ${ch}:${v} &mdash; ${src}</b> worst-of-four ${fmt(cell.worst)}
     ${cell.page?`&nbsp;·&nbsp; from <code>${cell.page}</code>`:''}
     <div class="cg-txt">${(cell.text||'(no text — this verse was never localized on this source)')
       .replace(/&/g,'&amp;').replace(/</g,'&lt;')}</div></div>`;
}
function cgFlags(){
  const f = CG.collation_flags || [];
  const box = document.getElementById('cg-flags');
  if(!f.length){ box.innerHTML=''; return; }
  box.innerHTML = `<div class="figtitle" style="margin-top:18px"><h3>Collation flags &mdash; ${f.length} cell(s)
    failing because the witness and the reference are different EDITIONS</h3></div>
    <div class="note"><b>These cells are still counted as failing.</b> Nothing here is subtracted from any
    denominator &mdash; the register carries the evidence so the claim can be checked rather than trusted.</div>`
    + f.map(x=>`<div class="callout"><b>${x.locus} &mdash; ${x.source}</b> worst ${fmt(x.worst_score)},
       leaf ${x.leaf}
       <div class="cg-txt">${x.our_text}</div>
       <div class="note" style="margin-top:8px"><b>Read off the leaf:</b> ${x.visual_read}</div>
       <div class="note"><b>The split:</b> ${x.the_divergence}</div>
       <div class="note"><b>Why no recognizer closes it:</b> ${x.why_no_recognizer_closes_it}</div>
       <div class="note"><b>What would resolve it:</b> ${x.what_would_resolve_it}</div></div>`).join('');
}
function cgProv(){
  const p=DATA.pipelines||{}, b=p.board||{}, r=p.rest||{};
  const box=document.getElementById('cg-prov'); if(!box) return;
  box.innerHTML = `<div class="callout" style="border-left:3px solid var(--accent)">
    <b>Campaign work is re-OCR work &mdash; but only this panel can show it.</b>
    Fixing a page-model bound is &ldquo;read the page better&rdquo;, the same rung as a recognizer fine-tune.
    Two pipelines render this document and only one of them can see such a fix.
    <div class="note" style="margin-top:8px">
      <b>This panel</b> &mdash; ${b.n||0} campaign matrices, newest
      <b>${b.mtime||'—'}</b> &middot; <code>${b.chain||''}</code><br>
      <b>Everything below</b> &mdash; <code>${r.path||'coverage-audit-verse.json'}</code>${r.mb?` (${r.mb} MB)`:''},
      built <b>${r.mtime||'—'}</b> &middot; <code>${r.chain||''}</code>
    </div>
    <div class="note" style="margin-top:8px">The second pipeline carries its OWN layout model
    (<code>marginalia-geometry.json</code>, <code>skeleton.json</code>) and imports nothing from
    <code>gen1_pagemodel</code>. <b>No campaign fix reaches it</b>, and rebuilding this report will not move a
    single figure below the board however far the board rises. Propagating campaign gains report-wide requires
    re-running <code>qc_audit.py</code> over reads regenerated <i>through</i> the campaign page model &mdash; a
    path that does not exist today. The dates above are printed so the gap is visible rather than assumed.</div>
  </div>`;
}
function cgRender(){
  cgBookList(); cgProv();
  if(CGBOOK!=='genesis'){
    // Blank the live panels rather than leaving Genesis's numbers under another book's name — the worst
    // failure mode here is a board that looks like it belongs to the book named above it.
    document.getElementById('cg-cards').innerHTML='';
    document.getElementById('cg-prog').innerHTML='';
    document.getElementById('cg-boardhdr').style.display='none';
    document.getElementById('cg-board').innerHTML=cgNoBoard();
    document.getElementById('cg-detail').innerHTML='';
    document.getElementById('cg-flags').innerHTML='';
    return;
  }
  document.getElementById('cg-boardhdr').style.display='';
  cgCards(); cgProg(); cgBoard(); cgDetail(); cgFlags();
}
function booksInScope(){return DATA.scope_books?DATA.scope_books:DATA.meta.scope_books;}
function scopeBooks(){return DATA.meta.scope_books.filter(b=>BOOK==='__all__'||b===BOOK);}

// ---------- headline ----------
function renderHead(){
  const m=DATA.meta;
  const build=String(m.version).padStart(3,'0');
  const vlabel=m.version_label?('v'+m.version_label):('v'+build);   // human label; build int kept for lineage
  document.getElementById('phaseTag').textContent=m.grain+' grain';
  document.getElementById('hdrsub').innerHTML=
    `Generated ${m.generated_at} · phase <b>${m.phase}</b> · source <span class="mono">${m.source_file}</span> (sha ${m.source_sha256}) · `
    +`stage: ${m.stage} ${vlabel} (build ${build}) · scope: ${m.scope_books.length<=8?m.scope_books.join(', '):m.scope_summary} · gating: ${m.gating} · bar ≥ ${m.threshold}`
    +(m.prior_reports.length?` · <span class="sub">${m.prior_reports.length} prior render(s) archived</span>`:'');
  // ---- version banner: prominent version id + what-changed delta vs the prior recorded version ----
  const p=m.prior_version;
  const sgn=x=>(x>0?'+':'')+x;
  let delta;
  if(p){
    const dv=m.n_verses-(p.n_verses||0), db=m.n_books-(p.n_books||0);
    const dataChg=p.input_sha256!==m.source_sha256;
    delta=`vs v${String(p.version).padStart(3,'0')}: verses ${sgn(dv)} · books ${sgn(db)} · `
      +(dataChg?`input data CHANGED (sha ${String(p.input_sha256).slice(0,8)} → ${m.source_sha256.slice(0,8)})`
               :`same input data (presentation-only change)`)
      +(p.scope_summary&&p.scope_summary!==m.scope_summary?` · scope ${p.scope_summary} → ${m.scope_summary}`:'');
  } else { delta='first recorded version'; }
  document.getElementById('verbanner').innerHTML=
    `<span class="vb-badge">${m.stage} ${vlabel}</span>`
    +`<span class="vb-built">build ${build} · built ${m.generated_at} · input <span class="mono">${m.source_file}</span> · sha ${m.source_sha256.slice(0,8)} · scope ${m.scope_summary} · bar ≥ ${m.threshold}</span>`
    +`<div class="vb-delta">${delta}</div>`
    +(m.changelog?`<div class="vb-log"><b>What changed:</b> ${m.changelog}</div>`:'');
}

// ---------- empirical version comparison (Results — Headline) ----------
function renderVersionCompare(){
  const host=document.getElementById('vercompare');
  const vc=DATA.version_compare;
  if(!vc){host.innerHTML='';return;}
  const badge=(v)=>{const c={improved:'var(--pass)',regressed:'var(--faildeep)',frozen:'var(--mut)',
    'scope-changed':'var(--fail)',flat:'var(--mut)','n/a':'var(--faint)',mixed:'var(--fail)'}[v]||'var(--accent)';
    return `<span style="display:inline-block;background:${c};color:#fff;font-weight:700;font-size:.78rem;padding:2px 8px;border-radius:5px">${v}</span>`;};
  // per-metric rate rows (only the verdict-driving rates; raw counts shown as context underneath)
  const rateKeys=[['pass_rate_archaic','archaic pass rate'],['verse_cover_rate','verse coverage'],
    ['books_failing_rate','books failing'],['source_fail_mean','mean source-fail'],
    ['apparatus_witness_rate','apparatus witness rate'],['apparatus_localize_rate','apparatus localize rate']];
  const arrow={improved:'↑',regressed:'↓',flat:'=','n/a':'·','scope-changed':'~'};
  const rows=rateKeys.map(([k,lbl])=>{const e=vc.metrics[k];if(!e||(e.prev==null&&e.cur==null))return '';
    const a=arrow[e.verdict]||'?';
    return `<tr><td>${lbl}</td><td class="mono">${e.prev==null?'—':(+e.prev).toFixed(4)}</td>`
      +`<td class="mono">${e.cur==null?'—':(+e.cur).toFixed(4)}</td>`
      +`<td class="mono">${e.delta==null?'—':((e.delta>0?'+':'')+(+e.delta).toFixed(4))}</td>`
      +`<td>${a} ${e.verdict}</td></tr>`;}).join('');
  const ctx=(vc.context||{});
  const ctxKeys=[['apparatus_witnesses','apparatus witnesses'],['apparatus_worklist','apparatus worklist'],
    ['apparatus_open_slots','apparatus open slots'],['books_failing','books failing (count)']];
  const ctxLine=ctxKeys.map(([k,lbl])=>{const e=ctx[k];if(!e||(e.prev==null&&e.cur==null))return null;
    return `${lbl} ${e.prev==null?'—':e.prev}→${e.cur==null?'—':e.cur}`;}).filter(Boolean).join(' · ');
  const notes=(vc.notes||[]).map(n=>`<div class="note" style="margin:3px 0">▪ ${n}</div>`).join('');
  host.innerHTML=
    `<div class="callout" style="border-left-color:var(--accent)">`
    +`<div style="font-size:1.02rem;margin-bottom:6px"><b>Empirical verdict — v${vc.prev_version} → v${vc.cur_version}:</b> `
    +`${badge(vc.overall)} &nbsp; scripture ${badge(vc.scripture_verdict)} &nbsp; apparatus ${badge(vc.apparatus_verdict)}</div>`
    +`<div class="note" style="margin:2px 0 8px">Measured from report DATA only — pass/coverage/failing RATES, not the changelog. A scope change is labelled, never scored as a gain or loss.</div>`
    +`<table style="max-width:760px"><thead><tr><th>rate metric</th><th>prev</th><th>cur</th><th>Δ</th><th>verdict</th></tr></thead><tbody>${rows}</tbody></table>`
    +(ctxLine?`<div class="note" style="margin-top:6px"><b>context (raw counts, not scored):</b> ${ctxLine}</div>`:'')
    +notes
    +(vc.frozen_violation&&vc.frozen_violation.length?`<div class="note" style="color:var(--faildeep)"><b>⚠ frozen-input invariant violated:</b> ${vc.frozen_violation.join(', ')}</div>`:'')
    +`</div>`;
}

// ---------- inventory (scope guardrail, visible) ----------
function renderInventory(){
  const host=document.getElementById('inventory');const inv=DATA.inventory;if(!inv){host.innerHTML='';return;}
  const brows=inv.books.map(b=>`<tr><td class="mono">${b.slug}</td><td>${b.testament}</td>`
    +`<td>${b.E_v==null?'—':b.E_v}</td><td>${b.n_chapters}</td><td>${b.n_verses}</td></tr>`).join('');
  const ap=inv.apparatus||{};
  const arows=(ap.built||[]).map(e=>`<tr><td class="mono">${e.locus.replace('apparatus/','')}</td>`
    +`<td>${e.E_v==null?'—':e.E_v}</td><td>${e.witness_count==null?'—':e.witness_count}</td>`
    +`<td class="mono">${e.score_grain||'—'}</td></tr>`).join('')
    ||'<tr><td colspan="4" class="note">none built</td></tr>';
  host.innerHTML=
    `<div style="display:flex;gap:26px;flex-wrap:wrap">`
    +`<div style="flex:1;min-width:320px"><h4>Books in scope (${inv.books.length}) — declared pilot: ${inv.declared_pilot.join(', ')}</h4>`
    +`<table><thead><tr><th>book</th><th>testament</th><th>E(v)</th><th>chapters</th><th>verses</th></tr></thead><tbody>${brows}</tbody></table></div>`
    +`<div style="flex:1;min-width:320px"><h4>Apparatus built (${(ap.built||[]).length}) · ${ap.open_slots==null?'—':ap.open_slots} open slots · ${ap.reocr_worklist==null?'—':ap.reocr_worklist} on re-OCR worklist</h4>`
    +`<table><thead><tr><th>element</th><th>E(v)</th><th>witnesses</th><th>score grain</th></tr></thead><tbody>${arows}</tbody></table></div>`
    +`</div>`;
}
function renderCards(){
  const rg=DATA.regimes, key=GATE;
  const gv=DATA.grain_breakout.verse[key], gc=DATA.grain_breakout.chapter[key];
  const oth = key==='archaic'?'modern':'archaic';
  const d = rg[key]-rg[oth];
  const card=(big,lbl,ex)=>`<div class="card"><div class="big">${big}</div><div class="lbl">${lbl}</div>${ex||''}</div>`;
  document.getElementById('cards').innerHTML=
    card(`${rg[key]}`,'scan×verse records passing',`<div class="sub">of ${rg.records} · ${(100*rg[key]/rg.records).toFixed(1)}%</div>`)
   +card(`${gv[0]}/${gv[1]}`,'verses with ≥1 scan passing',`<div class="sub">${(100*gv[0]/gv[1]).toFixed(1)}% at verse grain</div>`)
   +card(`${gc[0]}/${gc[1]}`,'chapters with ≥1 scan passing',`<div class="sub">${(100*gc[0]/gc[1]).toFixed(1)}% at chapter grain</div>`)
   +card(`${DATA.meta.n_verses}`,'verses scored',`<div class="sub delta ${d>=0?'up':'down'}">${d>=0?'+':''}${d} vs ${oth} gate</div>`);
  document.getElementById('callout').innerHTML=
    `<b>Every one of ${DATA.meta.n_verses} verses is below E(v).</b> No locus reaches its expected witness count — `
    +`current OCR cannot yet serve as sufficient quality witnesses, so the P3/P4 re-OCR ladder is load-bearing. `
    +`Every shortfall verse stays OPEN and blocks the deliverable; none is parked or accepted degraded.`;
}

// ---------- grain breakout ----------
function renderGrain(){
  const host=document.getElementById('grainbreak');host.innerHTML='';
  const levels=['book','chapter','verse'];const colr={book:C('--unloc'),chapter:C('--ref'),verse:C('--pass')};
  const W=Math.min(820,window.innerWidth-90),H=150,padL=64,padB=28,padT=10;
  const g=svg(W,H);
  const bw=(W-padL-40)/levels.length;
  levels.forEach((lv,i)=>{
    const [h,t]=DATA.grain_breakout[lv][GATE];const frac=t?h/t:0;
    const x=padL+i*bw;const barw=bw*0.5;
    const y=padT+(H-padT-padB)*(1-frac);
    g.appendChild(el('rect',{x:x,y:y,width:barw,height:(H-padB)-y,fill:colr[lv],opacity:.85,rx:2}));
    g.appendChild(el('text',{x:x+barw/2,y:H-padB+16,'font-size':12,fill:COL.ink,'text-anchor':'middle'},lv));
    g.appendChild(el('text',{x:x+barw/2,y:y-6,'font-size':12,fill:COL.ink,'text-anchor':'middle','font-weight':600},`${(100*frac).toFixed(1)}%`));
    g.appendChild(el('text',{x:x+barw/2,y:y-20,'font-size':10,fill:COL.mut,'text-anchor':'middle'},`${h}/${t}`));
  });
  [0,.5,1].forEach(f=>{const y=padT+(H-padT-padB)*(1-f);g.appendChild(el('line',{x1:padL,y1:y,x2:W-40,y2:y,stroke:C('--line')}));
    g.appendChild(el('text',{x:padL-8,y:y+3,'font-size':10,fill:COL.mut,'text-anchor':'end'},(100*f)+'%'));});
  host.appendChild(g);
}

// ---------- V1 histograms (grouped OT/NT, auto x-axis, click-zoom) ----------
function panelData(s){
  const useNT = BOOK==='__all__'? null : (DATA.book_testament[BOOK]==='NT');
  let mod,arch;
  if(useNT===null){mod=s.mod_OT.concat(s.mod_NT);arch=s.arch_OT.concat(s.arch_NT);}
  else if(useNT){mod=s.mod_NT;arch=s.arch_NT;}
  else{mod=s.mod_OT;arch=s.arch_OT;}
  return {mod,arch};
}
function histBins(vals,binN,lo,hi){const b=new Array(binN).fill(0);vals.forEach(v=>{let i=Math.floor((v-lo)/(hi-lo)*binN);if(i<0)i=0;if(i>=binN)i=binN-1;b[i]++;});return b;}
function drawHist(s,mod,arch,W,H,big){
  const all=mod.concat(arch);
  let lo=Math.min(...all),hi=Math.max(...all);
  if(!isFinite(lo)){lo=0;hi=1;}
  const pad=(hi-lo)*0.06||0.02; lo=Math.max(0,lo-pad); hi=Math.min(1,hi+pad);
  if(hi-lo<0.05){hi=Math.min(1,lo+0.05);}
  const binN=big?40:22, padL=34,padB=24,padT=8,padR=8;
  const g=svg(W,H);
  const hm=histBins(mod,binN,lo,hi),ha=histBins(arch,binN,lo,hi);
  const mx=Math.max(1,...hm,...ha);const bw=(W-padL-padR)/binN;
  const yy=v=>H-padB-(v/mx)*(H-padB-padT);const xx=i=>padL+i*bw;
  g.appendChild(el('line',{x1:padL,y1:H-padB,x2:W-padR,y2:H-padB,stroke:COL.mut}));
  const ticks=4;for(let k=0;k<=ticks;k++){const t=lo+(hi-lo)*k/ticks;const px=padL+(W-padL-padR)*k/ticks;
    g.appendChild(el('text',{x:px,y:H-8,'font-size':big?11:9,fill:COL.mut,'text-anchor':'middle'},t.toFixed(2)));}
  for(let i=0;i<binN;i++){
    if(hm[i]>0)g.appendChild(el('rect',{x:xx(i),y:yy(hm[i]),width:bw*0.92,height:(H-padB)-yy(hm[i]),fill:COL.ref,opacity:.6}));
    if(ha[i]>0)g.appendChild(el('rect',{x:xx(i)+bw*0.12,y:yy(ha[i]),width:bw*0.92,height:(H-padB)-yy(ha[i]),fill:COL.fail,opacity:.55}));
  }
  if(0.90>=lo&&0.90<=hi){const xb=padL+(0.90-lo)/(hi-lo)*(W-padL-padR);
    g.appendChild(el('line',{x1:xb,y1:padT,x2:xb,y2:H-padB,stroke:COL.accent,'stroke-width':1.4,'stroke-dasharray':'4 3'}));}
  return g;
}
function renderV1(){
  const host=document.getElementById('v1');host.innerHTML='';
  const groups=BOOK==='__all__'?[['Old Testament witnesses','OT'],['New Testament witnesses','NT']]
    :[[(DATA.book_testament[BOOK]==='NT'?'New':'Old')+' Testament witnesses',DATA.book_testament[BOOK]]];
  groups.forEach(([title,test])=>{
    const scans=DATA.sources.filter(s=>s.kind==='scan'&&s.testaments.includes(test));
    if(!scans.length)return;
    const hd=document.createElement('div');hd.className='otnt-head';hd.textContent=title;host.appendChild(hd);
    const grid=document.createElement('div');grid.className='gridwrap';host.appendChild(grid);
    scans.forEach(s=>{
      const useNT=test==='NT';
      const mod=useNT?s.mod_NT:s.mod_OT, arch=useNT?s.arch_NT:s.arch_OT;
      if(!mod.length&&!arch.length)return;
      const div=document.createElement('div');div.className='mini';
      div.innerHTML=`<div><b>${s.id}</b> <span class="sub">${s.ocr_dir||''} · n=${mod.length}</span></div>`;
      div.appendChild(drawHist(s,mod,arch,320,140,false));
      const passcnt=s['pass_'+GATE];
      const cap=document.createElement('div');cap.className='sub';
      cap.innerHTML=`mod med ${fmt(s.mod_med)} · arc med ${fmt(s.arch_med)} · pass ${passcnt}/${s.n_attested}`;
      div.appendChild(cap);
      div.onclick=()=>zoomHist(s,mod,arch,test);
      grid.appendChild(div);
    });
  });
}
function zoomHist(s,mod,arch,test){
  const b=document.getElementById('modalBody');
  const W=Math.min(900,window.innerWidth-120),H=Math.min(520,window.innerHeight-200);
  b.innerHTML=`<h3>${s.id} — ${test} identity distribution <span class="grain verse">verse</span></h3>`+
    `<div class="sub">${s.ocr_dir||''} · ${mod.length} verses · modern median ${fmt(s.mod_med)} · archaic median ${fmt(s.arch_med)}</div>`;
  b.appendChild(drawHist(s,mod,arch,W,H,true));
  const lg=document.createElement('div');lg.className='legend';lg.innerHTML=`<span><i style="background:${COL.ref}"></i>modern_id</span><span><i style="background:${COL.fail}"></i>archaic_id</span><span><i style="background:${COL.accent}"></i>0.90 bar</span>`;
  b.appendChild(lg);
  document.getElementById('modal').classList.add('open');
}
function closeModal(){document.getElementById('modal').classList.remove('open');}

// ---------- V2 scatter per book ----------
function drawScatter(book,W,H,big){
  const pts=DATA.scatter[book]||[];const srcs=DATA.scatter_srcs[book]||[];const cmap=scanColorMap();
  const pad=big?54:38,lo=0.4,hi=1.0;
  const g=svg(W,H);
  const X=v=>pad+(clamp(v,lo,hi)-lo)/(hi-lo)*(W-2*pad);
  const Y=v=>H-pad-(clamp(v,lo,hi)-lo)/(hi-lo)*(H-2*pad);
  g.appendChild(el('rect',{x:X(0.9),y:Y(1.0),width:X(1.0)-X(0.9),height:Y(0.9)-Y(1.0),fill:'rgba(26,152,80,.08)'}));
  g.appendChild(el('line',{x1:X(0.9),y1:pad,x2:X(0.9),y2:H-pad,stroke:COL.accent,'stroke-dasharray':'4 3'}));
  g.appendChild(el('line',{x1:pad,y1:Y(0.9),x2:W-pad,y2:Y(0.9),stroke:COL.accent,'stroke-dasharray':'4 3'}));
  g.appendChild(el('line',{x1:X(lo),y1:Y(lo),x2:X(hi),y2:Y(hi),stroke:COL.mut,'stroke-width':.6,opacity:.5}));
  [0.4,0.6,0.8,1.0].forEach(t=>{g.appendChild(el('text',{x:X(t),y:H-pad+13,'font-size':big?11:9,fill:COL.mut,'text-anchor':'middle'},t.toFixed(1)));
    g.appendChild(el('text',{x:pad-6,y:Y(t)+3,'font-size':big?11:9,fill:COL.mut,'text-anchor':'end'},t.toFixed(1)));});
  g.appendChild(el('text',{x:W/2,y:H-4,'font-size':big?12:10,fill:COL.mut,'text-anchor':'middle'},'modern_id →'));
  g.appendChild(el('text',{x:11,y:H/2,'font-size':big?12:10,fill:COL.mut,'text-anchor':'middle',transform:`rotate(-90 11 ${H/2})`},'archaic_id →'));
  pts.forEach(p=>{
    const [mod,arch,si,pg,pm]=p; if(arch==null)return;
    const passShown = GATE==='modern'?pm:(GATE==='archaic'?pg:(pg&&pm));
    const c=el('circle',{cx:X(mod),cy:Y(arch),r:passShown?(big?3.6:2.6):(big?2.6:1.9),fill:cmap[srcs[si]]||COL.mut,
      opacity:passShown?0.9:0.4,stroke:passShown?'#fff':'none','stroke-width':passShown?0.4:0});
    g.appendChild(c);
  });
  return g;
}
function scatterLegend(book){
  const cmap=scanColorMap();const srcs=DATA.scatter_srcs[book]||[];
  const lg=document.createElement('div');lg.className='legend';
  lg.innerHTML=srcs.map(s=>`<span><i style="background:${cmap[s]||COL.mut}"></i>${s}</span>`).join('');
  return lg;
}
function zoomScatter(book){
  const b=document.getElementById('modalBody');
  const test=DATA.book_testament[book];const pts=DATA.scatter[book]||[];
  const W=Math.min(760,window.innerWidth-120),H=Math.min(560,window.innerHeight-180);
  b.innerHTML=`<h3>${book} — modern_id vs archaic_id <span class="grain verse">verse</span></h3>`+
    `<div class="sub">${pts.length} scan×verse · ${test} · gate: ${GATE} · larger marker = passes the shown gate · green box = both ≥ 0.90</div>`;
  b.appendChild(drawScatter(book,W,H,true));
  b.appendChild(scatterLegend(book));
  document.getElementById('modal').classList.add('open');
}
function renderV2(){
  const host=document.getElementById('v2');host.innerHTML='';
  scopeBooks().forEach(book=>{
    const pts=DATA.scatter[book]||[];
    const div=document.createElement('div');div.className='mini';div.style.cursor='zoom-in';
    div.title='click to zoom';div.onclick=()=>zoomScatter(book);
    const test=DATA.book_testament[book];
    div.innerHTML=`<div><b>${book}</b> <span class="sub">${pts.length} scan×verse · ${test} ⤢</span></div>`;
    div.appendChild(drawScatter(book,320,300,false));
    div.appendChild(scatterLegend(book));
    host.appendChild(div);
  });
}

// ---------- V3 heatmap chapter grain, intensity by score ----------
function cellFill(sd){
  if(!sd)return {f:COL.absent,o:0.5};
  // transcribed references coloured by lineage: archaic (preeminent) vs modern
  if(sd.kind==='transcription')return {f: sd.ref_class==='archaic'?COL.refarc:COL.ref, o:0.85};
  // scan passes the chapter iff it passes >= (m-1) of the m verses (strict rule)
  if(sd['chpass_'+GATE])return {f:COL.pass,o:0.9};
  // localized but failed: intensity by how far the median governing score is below 0.90
  const sc = GATE==='modern'?sd.mean_mod:(GATE==='archaic'?sd.mean_gov:sd.mean_mod);
  if(sc==null)return {f:COL.absent,o:0.5};
  const gap=Math.max(0,0.90-sc); // 0..~0.6
  const tnorm=Math.min(1,gap/0.30); // 0 (near) .. 1 (far)
  // interpolate fail(orange)->faildeep(red)
  return {f:tnorm>0.5?COL.faildeep:COL.fail, o:0.45+0.5*tnorm};
}
function renderV3(){
  const host=document.getElementById('v3');host.innerHTML='';
  const order=DATA.source_order;
  const books=scopeBooks();
  const cs=17,gap=1,labW=86,rowH=17,W0=labW+6;
  books.forEach(b=>{
    const chs=DATA.chapters.filter(c=>c.book===b).sort((x,y)=>x.chapter-y.chapter);
    if(!chs.length)return;
    const rows=(DATA.v3_tracks&&DATA.v3_tracks[b])?DATA.v3_tracks[b]:order;
    const cols=chs.length;const W=W0+cols*(cs+gap)+12,H=26+rows.length*rowH+14;
    const wrap=document.createElement('div');wrap.style.padding='8px 8px 4px';
    wrap.innerHTML=`<div class="sub" style="margin:2px 0 4px"><b>${b}</b> · ${cols} chapters · E(v)=${chs[0].E_v} <span class="grain chapter">chapter</span></div>`;
    const g=svg(W,H);
    chs.forEach((c,ci)=>{if(c.chapter%10===0||c.chapter===1)g.appendChild(el('text',{x:W0+ci*(cs+gap)+cs/2,y:16,'font-size':9,fill:COL.mut,'text-anchor':'middle'},c.chapter));});
    rows.forEach((sid,ri)=>{
      const y=24+ri*rowH;
      g.appendChild(el('text',{x:labW,y:y+12,'font-size':10,fill:COL.ink,'text-anchor':'end'},sid));
      chs.forEach((c,ci)=>{
        const sd=c.sources[sid];const {f,o}=cellFill(sd);
        const rct=el('rect',{x:W0+ci*(cs+gap),y:y,width:cs,height:rowH-2,fill:f,opacity:o,rx:2});
        if(sd){rct.style.cursor='pointer';rct.addEventListener('click',()=>drillChapter(c,sid));}
        g.appendChild(rct);
      });
    });
    wrap.appendChild(g);host.appendChild(wrap);
  });
}

// ---------- V4 witness depth histogram ----------
function renderV4(){
  const host=document.getElementById('v4');host.innerHTML='';
  const now=DATA.wdepth_verse[GATE], base=DATA.wdepth_verse_baseline?DATA.wdepth_verse_baseline[GATE]:null;
  const keys=[...new Set([...Object.keys(now),...(base?Object.keys(base):[])])].map(Number).sort((a,b)=>a-b);
  const mx=Math.max(...keys.map(k=>Math.max(now[k]||0,base?(base[k]||0):0)));
  const W=Math.min(820,window.innerWidth-90),H=230,padL=52,padB=44,padT=14;
  const gw=Math.min(96,(W-padL-20)/keys.length);
  const g=svg(Math.max(W,padL+keys.length*gw+20),H);
  const y=v=>H-padB-(v/mx)*(H-padT-padB);
  keys.forEach((k,i)=>{
    const x=padL+i*gw, bw=(gw-14)/(base?2:1);
    if(base){
      const b=base[k]||0;
      g.appendChild(el('rect',{x:x,y:y(b),width:bw-2,height:(H-padB)-y(b),fill:COL.mut,opacity:.35,rx:2}));
      g.appendChild(el('text',{x:x+bw/2,y:y(b)-4,'font-size':9,fill:COL.mut,'text-anchor':'middle'},b));
    }
    const n=now[k]||0, xn=x+(base?bw+2:0);
    g.appendChild(el('rect',{x:xn,y:y(n),width:bw-2,height:(H-padB)-y(n),fill:COL.ref,opacity:.85,rx:2}));
    g.appendChild(el('text',{x:xn+bw/2,y:y(n)-4,'font-size':10,fill:COL.ink,'text-anchor':'middle'},n));
    g.appendChild(el('text',{x:x+gw/2-7,y:H-padB+16,'font-size':11,fill:COL.ink,'text-anchor':'middle'},k));
  });
  g.appendChild(el('text',{x:padL,y:H-8,'font-size':11,fill:COL.mut},
    base?'witness_count per verse (x) — # verses (y). GREY = pre-re-OCR baseline · BLUE = current.'
        :'witness_count per verse (x) — # verses (y). No baseline artifact present.'));
  host.appendChild(g);
  // The headline is the SHIFT in depth, stated as a number rather than left to the eye.
  const mean=o=>{let n=0,d=0;for(const k in o){n+=Number(k)*o[k];d+=o[k];}return d?n/d:0;};
  const sum=o=>Object.values(o).reduce((a,b)=>a+b,0);
  const deep=o=>Object.entries(o).filter(([k])=>Number(k)>=2).reduce((a,[,v])=>a+v,0);
  const cap=document.createElement('div');cap.className='note';
  cap.innerHTML=base
    ? `<b>Mean witness depth ${mean(base).toFixed(2)} &rarr; ${mean(now).toFixed(2)}</b> per verse; verses with `
      +`<b>&ge;2</b> passing witnesses ${deep(base)} &rarr; <b>${deep(now)}</b> of ${sum(now)}. `
      +`E(v) is 9&ndash;12, so <b>every verse is still below E(v)</b> and the backward gate still fails everywhere — `
      +`the shortfall is narrower, not closed, and no verse is yet witness-complete.`
    : 'No pre-re-OCR baseline available; this is a snapshot, not a movement.';
  host.appendChild(cap);
}

// ---------- V5 gate comparison + phase progression ----------
function renderV5(){
  const host=document.getElementById('v5');host.innerHTML='';
  const scans=DATA.sources.filter(s=>s.kind==='scan');
  const H=280,padT=16,padB=44,padL=40,gw=Math.max(70,(Math.min(880,window.innerWidth-90)-padL)/scans.length);
  const mx=Math.max(1,...scans.map(s=>Math.max(s.pass_archaic,s.pass_modern,s.pass_both)));
  const W=padL+scans.length*gw+16;
  const g=svg(W,H);const y=v=>H-padB-(v/mx)*(H-padT-padB);
  const trio=[['pass_modern',C('--ref')],['pass_archaic',C('--pass')],['pass_both',C('--mut')]];
  scans.forEach((s,i)=>{
    const x0=padL+i*gw;const bw=(gw-16)/3;
    trio.forEach(([key,col],j)=>{const x=x0+j*bw;
      g.appendChild(el('rect',{x:x,y:y(s[key]),width:bw-2,height:(H-padB)-y(s[key]),fill:col,opacity:.88}));});
    g.appendChild(el('text',{x:x0+(gw-16)/2,y:H-padB+15,'font-size':10.5,fill:COL.ink,'text-anchor':'middle'},s.id));
  });
  g.appendChild(el('text',{x:padL,y:12,'font-size':11,fill:COL.mut},'blue = modern-only · green = archaic-preeminent · grey = old AND-gate (passing scan×verse per source)'));
  host.appendChild(g);
  const rows=DATA.phases.map(p=>`<tr><td>${p.phase}</td><td><span class="grain ${p.grain}">${p.grain}</span></td><td>${p.gating}</td><td style="text-align:right">${p.scan_pass}/${p.records}</td><td style="text-align:right">${(100*p.scan_pass/p.records).toFixed(1)}%</td><td>${p.note}</td></tr>`).join('');
  document.getElementById('phaseprog').innerHTML=
    `<h4>Phase progression</h4><table><thead><tr><th>phase</th><th>grain</th><th>gating</th><th style="text-align:right">scan pass</th><th style="text-align:right">rate</th><th>note</th></tr></thead><tbody>${rows}</tbody></table>`
    +`<div class="sub" style="margin-top:6px">Grain differs between phases, so raw counts are not directly comparable — the rate column normalizes within each grain. The verse-grain rate is far higher because per-verse scoring rescues faithful verses a chapter-average buries.</div>`;
}

// ---------- V6 table ----------
function renderV6(){
  const cols=[['id','source'],['kind','kind'],['ocr_dir','ocr dir'],['testaments','test'],['n_attested','attested'],
    ['pass_archaic','pass·arc'],['pass_modern','pass·mod'],['pass_both','pass·AND'],
    ['mod_med','mod med'],['arch_med','arc med'],['worklist_hits','wl hits'],['reocr_needed','re-OCR']];
  const tb=document.getElementById('v6');
  tb.querySelector('thead').innerHTML='<tr>'+cols.map(c=>`<th onclick="sortTable('v6','${c[0]}')">${c[1]}</th>`).join('')+'</tr>';
  tb.querySelector('tbody').innerHTML=DATA.sources.map(r=>'<tr>'+cols.map(c=>{
    let v=r[c[0]];
    if(['mod_med','arch_med'].includes(c[0]))v=fmt(v);
    if(c[0]==='testaments')v=(v||[]).join('+');
    if(c[0]==='reocr_needed')return `<td>${v?`<span class="pill fail" title="${(r.coverage||'').replace(/"/g,'')}">⚠ re-OCR</span>`:''}</td>`;
    return `<td>${v==null?'—':v}</td>`;}).join('')+'</tr>').join('');
}

// ---------- worklist ----------
function renderWL(){
  const cols=[['locus','locus'],['E_v','E(v)'],['witness_count','witnesses'],['missing','missing'],['verses_shortfall','verses short'],['localized_but_failed','localized-but-failed scans']];
  const tb=document.getElementById('wl');
  tb.querySelector('thead').innerHTML='<tr>'+cols.map(c=>`<th onclick="sortTable('wl','${c[0]}')">${c[1]}</th>`).join('')+'</tr>';
  const rows=DATA.worklist.filter(w=>BOOK==='__all__'||w.book===BOOK).slice().sort((a,b)=>b.missing-a.missing||b.verses_shortfall-a.verses_shortfall);
  tb.querySelector('tbody').innerHTML=rows.map(w=>'<tr>'+
    `<td class="mono">${w.locus}</td><td>${w.E_v}</td><td>${w.witness_count}</td><td>${w.missing}</td><td>${w.verses_shortfall||'—'}</td>`+
    `<td>${(w.localized_but_failed||[]).join(', ')||'—'}</td>`+'</tr>').join('');
}
let _ss={};
function sortTable(id,key){
  const asc=_ss[id+key]=!_ss[id+key];const tbl=document.getElementById(id);
  const tb=tbl.querySelector('tbody');const rows=[...tb.rows];
  const idx=[...tbl.querySelectorAll('th')].findIndex(th=>th.getAttribute('onclick').includes(`'${key}'`));
  rows.sort((a,b)=>{let x=a.cells[idx].textContent,y=b.cells[idx].textContent;const nx=parseFloat(x),ny=parseFloat(y);
    if(!isNaN(nx)&&!isNaN(ny)){x=nx;y=ny;}return (x<y?-1:x>y?1:0)*(asc?1:-1);});
  rows.forEach(r=>tb.appendChild(r));
}

// ---------- drilldown ----------
function drillChapter(c,sid){
  const b=document.getElementById('drillBody');
  const sd=c.sources[sid]||{};
  const verses=(DATA.verse_index[c.locus]||[]).sort((a,z)=>a[0]-z[0]);
  const srows=Object.entries(c.sources).map(([k,v])=>{
    const frac=v.n_att?(v['pass_'+GATE]/v.n_att):0;
    return `<tr><td>${k}</td><td style="text-align:right">${v.kind==='scan'?fmt(v.mean_gov):'ref'}</td><td style="text-align:right">${v['pass_'+GATE]}/${v.n_att} <span class="pill ${frac>=0.5?'pass':'fail'}">${(100*frac).toFixed(0)}%</span></td></tr>`;}).join('');
  const vrows=verses.map(v=>`<tr><td>v${v[0]}</td><td style="text-align:right">${v[1]} wit${v[2]?' · short':''}</td><td>${(v[3]||[]).join(',')||'—'}</td></tr>`).join('');
  b.innerHTML=`<h3>${c.locus} <span class="grain chapter">chapter</span></h3>`
    +`<div class="sub">${c.book} ch ${c.chapter} · ${c.testament} · E(v)=${c.E_v} · ${c.n_verses} verses · ${c.verses_shortfall} short</div>`
    +`<h4>per-source (gate: ${GATE})</h4><table><thead><tr><th>source</th><th style="text-align:right">med gov</th><th style="text-align:right">verses pass</th></tr></thead><tbody>${srows}</tbody></table>`
    +`<h4>verses — witness depth &amp; passing scans</h4><table><thead><tr><th>verse</th><th style="text-align:right">depth</th><th>passing scans</th></tr></thead><tbody>${vrows}</tbody></table>`;
  document.getElementById('drill').classList.add('open');
}
function closeDrill(){document.getElementById('drill').classList.remove('open');}

// ---------- methods + interp ----------
function renderMethods(){
  const m=DATA.meta, s=DATA.status;
  const li=a=>a.map(x=>`<li>${x}</li>`).join('');
  document.getElementById('methods').innerHTML=`
   <h3>1 · Data model &amp; grain</h3>
   <p>The authority is a per-<b>verse</b> double-bind record (<span class="mono">scripture/{book}/{ch}/{v}</span>). Chapter and book figures are aggregations of the same verse scores; every figure is tagged with its grain. Scope: ${m.scope_books.length<=8?m.scope_books.join(', '):m.scope_books.length+' books'} (${m.scope_summary}).</p>
   <h3>2 · How the OCR is produced</h3>
   <p>Diplomatic OCR is generated by <span class="mono">kraken</span> baseline segmentation with the <span class="mono">reichenau_lat</span> MLX recognition model, chosen because it preserves early-modern glyphs (long-ſ, æ/œ, u/v, i/j) that stock engines destroy (tesseract ſ→f, CATMuS ſ→s). Output is ALTO XML parsed to per-line bbox+text. Preprocessing is minimal and deterministic: grayscale + resize (downscale long side to ~2400px for PDFs; upscale tiny inputs). No binarization/deskew. Raster is chosen per volume by measuring jp2-master vs PDF content resolution (win if jp2 out-resolves by &gt;1.3× linear, or if the PDF is bitonal and loses ſ/f signal). <b>The re-OCR escalation ladder (layout-aware → region → vision-LLM) is a worklist only — not yet implemented.</b></p>
   <h3>3 · Localization / model-fitting</h3>
   <p>Localization is content-anchored, not from-scratch segmentation. Each OCR line is region-typed body-vs-margin by its x-centre against the measured text column (fallback band 0.11–0.88); inline <span class="mono">(x)</span> annotation lines are rerouted to apparatus so verse spans stay contiguous; columnar pages are read in reading order across a detected gutter. A book is located by the alias with highest mid-chapter probe-recall (no floor — a book is never dropped by a probe); each verse is attested iff located-window folded type-recall ≥ 0.5. <span class="mono">detect_book</span> returns verse-grain reads.</p>
   <h3>4 · Reference construction (changed this revision)</h3>
   <p><b>Archaic</b> reference = <span class="mono">s_dismas</span> content, backfilled per-locus from <span class="mono">odr_com</span> (ſ-diplomatic, same edition family as the 1582 print). <b>Modern</b> reference = <span class="mono">sabates_a</span> (Janvier), backfilled from <span class="mono">madueke_b</span>. Folds: the modern fold is a modern-neutral skeleton (collapses archaic/modern spellings) measuring content; the archaic (light) fold keeps archaic spelling (trailing -e, doubles, y) measuring surface, with ſ-placement scored separately by a reference-free long-ſ rule.</p>
   ${(DATA.source_defects&&DATA.source_defects.length)?`<p><b>s_dismas Class-A source defects</b> (auto-detected — interior chapters the source PDF/OCR drops via duplicated/absent chapter-headings): ${DATA.source_defects.map(d=>`<span class="mono">${d.locus.replace('scripture/','')}</span> <span class="pill ${d.backfill?'pass':'fail'}">${d.backfill||'OPEN'}</span>`).join(' · ')}. Defects odr_com covers are interim-backfilled; the <b>OPEN</b> ones carry <i>no</i> archaic reference from either source (odr_com has no such chapter) and are held OPEN, never assumed covered. The s_dismas re-parse is the harder fix, tracked OPEN.</p>`:''}
   <h3>5 · Gating (changed this revision)</h3>
   <p>Char-level identity bar = ${m.threshold} (metric: ${m.metric}). <b>Archaic-preeminent:</b> where an archaic reference exists it governs (PASS iff archaic_id ≥ ${m.threshold}); modern_id is recorded but does not gate, so a faithful 1582 reading is not failed for diverging from a modern edition. Modern governs only where no archaic reference exists; neither → <span class="mono">needs-reference</span> (OPEN). Backward gate: realized witness_count vs E(v) per verse; shortfall stays OPEN and blocks ship.</p>
   ${(DATA.routing_summary&&DATA.routing_summary.counts)?`<p><b>§1.4 scoped re-OCR routing.</b> The archaic (in-edition) gate is the quality bar; the modern gate governs only where it is a <i>valid</i> yardstick — <span class="mono">floor_modern</span> (transcribed-archaic vs Janvier, references only) ≥ ${m.threshold} and the book is not chronically divergent (${(DATA.routing_summary.chronic_divergent_books||[]).join(', ')}). Across ${DATA.routing_summary.counts.scan_records} scan×verse records: <b>${DATA.routing_summary.counts.reocr_fire}</b> route to re-OCR (below the governing bar); <b>${DATA.routing_summary.counts.modern_yardstick_invalid}</b> sit where the modern yardstick itself diverges from the print (redirected to the archaic / in-family instrument — never accepted on the modern number, never re-OCR'd to chase it); <b>${DATA.routing_summary.counts.needs_in_family_reference}</b> have no valid in-edition reference (held OPEN); <b>${DATA.routing_summary.counts.suspected_long_s_as_f}</b> show a suspected ſ→f misread routed to re-OCR. <span class="mono">witness_count</span> counts only backward-gate-valid passes.</p>`:''}
   <h3>6 · Fixes applied this revision</h3><ul>${li(s.fixes_applied)}</ul>
   <h3>7 · Status — completed vs pending</h3>
   <div class="statuscols"><div><h4>Completed</h4><ul>${li(s.completed)}</ul></div>
   <div><h4>Pending / OPEN</h4><ul>${li(s.pending)}</ul></div></div>`;
}
function renderRung0Signoff(){
  const R = DATA.rung0_signoff;
  const host = document.getElementById('rung0');
  if (!R || !R.signoff){
    host.innerHTML = '<div class="note">No rung-0 sign-off present — the gate has not fired for this build. Run <span class="mono">reocr_ladder.py</span> and inspect the resulting PNGs before any rung ≥ 1 work.</div>';
    return;
  }
  const S = R.signoff, sum = S.summary || {};
  const rungClass = n => n === 1 ? 'pass' : n === 0 ? 'fail' : 'ref';
  const rows = (R.records||[]).map(r => {
    const insp = r.inspection || {};
    const rung = insp.recommended_rung;
    const rungLabel = rung === 0 ? '0 · DELIST' : ('' + rung);
    const flag = insp.no_silent_degradation ? ' <span class="pill fail">NO-SILENT-DEGRADATION</span>' : '';
    const regions = (insp.regions_needed || []).length ? `<div class="note" style="margin:4px 0 0">regions: ${insp.regions_needed.map(x=>`<span class="mono">${x}</span>`).join(' · ')}</div>` : '';
    return `<tr><td class="mono">${r.locus.replace('scripture/','').replace('apparatus/','')}</td>
      <td class="mono">${r.scan||''}</td>
      <td style="text-align:center"><span class="pill ${rungClass(rung)}">${rungLabel}</span>${flag}</td>
      <td class="mono">${insp.failure_class||''}</td>
      <td style="text-align:left">${insp.note||''}${regions}</td></tr>`;
  }).join('');
  const flagged = (S.no_silent_degradation && S.no_silent_degradation.flagged) || [];
  host.innerHTML = `
    <div class="callout"><b>Gate: ${R.gate || 'CLEARED'}.</b> Iteration ${S.iteration||'?'} · observer ${S.observer||'?'} · ${S.observed_at||''} · method: ${S.method||''}.</div>
    <div class="cards">
      <div class="card"><div class="big">${sum.total_loci||0}</div><div class="lbl">loci inspected</div></div>
      <div class="card"><div class="big">${sum.rung1_layout||0}</div><div class="lbl">→ rung 1 (layout)</div></div>
      <div class="card"><div class="big">${sum.rung2_glyph||0}</div><div class="lbl">→ rung 2 (glyph)</div></div>
      <div class="card"><div class="big">${sum.rung3_vision_llm||0}</div><div class="lbl">→ rung 3 (vision-LLM)</div></div>
      <div class="card"><div class="big">${sum.delisted_localization_gap||0}</div><div class="lbl">DELISTED (localization)</div></div>
    </div>
    <p><b>Substantive finding.</b> ${S.substantive_finding||''}</p>
    ${flagged.length ? `<div class="callout"><b>No-Silent-Degradation flag:</b> ${flagged.join(', ')} — ${S.no_silent_degradation.reason||''}</div>` : ''}
    <div class="scrollx"><table><thead><tr>
      <th style="text-align:left">Locus</th><th style="text-align:left">Scan</th>
      <th style="text-align:center">Rec. rung</th><th style="text-align:left">Failure class</th>
      <th style="text-align:left">Note</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
function renderInterp(){
  const rg=DATA.regimes;
  document.getElementById('interp').innerHTML=`
   <p>1. <b>The floor is real and universal.</b> 0% of verses reach E(v). Current diplomatic OCR cannot serve as sufficient quality witnesses; the re-OCR ladder is load-bearing, not optional.</p>
   <p>2. <b>Verse grain is the larger lever.</b> Scoring per verse rescues faithful verses that a chapter-average buries — the verse-grain pass rate is far above the chapter-grain baseline for the same scans.</p>
   <p>3. <b>Archaic surface fidelity is the harder bar, and the metric is now honest.</b> Under normalized Levenshtein (not the prior over-scoring difflib.ratio) scan identity drops materially: scans still capture modern <i>content</i> better than archaic <i>surface</i>, so the archaic-preeminent gate is the stricter one and re-OCR must target ſ-placement and archaic spelling, not just legibility. Passing scan×verse: archaic ${rg.archaic} vs modern ${rg.modern} vs old AND-gate ${rg.both} of ${rg.records}.</p>
   <p>4. <b>No silent degradation.</b> Front-matter apparatus HAS archaic references (s_dismas OT approbatio + OT preface + NT preface): the single-page approbatio attests in 6/9 OT scans yet is still short of E(v)=9, so it stays OPEN; the multi-page prefaces localize (OT 9/9, NT 6/8) but only their aligned opening window is scored so far (a labelled sample that never credits a witness — full char-level scoring of a 41-page element is a P5 task, the whole-blob edit DP being infeasible), so they too stay on the re-OCR worklist, not accepted. The s_dismas inventory carries no archaic title-page / privilege / censura / censure, so those 5 front slots are held OPEN (need scan re-OCR at P4) — never fabricated. Genuinely unreferenced loci — all back-matter, and the odr_com-uncovered s_dismas defects (Leviticus 3, Proverbs 25) — are held OPEN, never assumed covered. Every shortfall element and verse stays OPEN.</p>`;
}

// ---------- wiring ----------
function setGate(g){GATE=g;['archaic','modern','both'].forEach(k=>document.getElementById('g-'+k).classList.toggle('on',k===g));
  document.getElementById('gateExplain').textContent={archaic:'PASS = archaic_id ≥ 0.90 where an archaic ref exists (modern is signal only); else modern_id ≥ 0.90.',
    modern:'PASS = modern_id ≥ 0.90 (content only).',both:'PASS = modern_id ≥ 0.90 AND (archaic_id ≥ 0.90 where an archaic ref exists) — old modern-primary AND-gate.'}[g];
  renderAll();}
function setBook(b){BOOK=b;renderAll();}
// ---------- the two tracks: the deliverable vs the instrument ----------
function renderTracks(){
  const c=document.getElementById('trk-corpus'), d=document.getElementById('trk-dev');
  if(!c) return;
  const gr=DATA.grain_breakout && DATA.grain_breakout.verse ? DATA.grain_breakout.verse[GATE] : null;
  const cards=DATA.cards||{};
  const pr=(cards.pass_rate_archaic!=null)?cards.pass_rate_archaic:null;
  c.textContent = gr ? `${gr[0]} / ${gr[1]} verses` : (pr!=null?`${(100*pr).toFixed(1)}%`:'—');
  const L=DATA.lift;
  d.textContent = L ? `base ${L.aggregate.base_mean} → R2 ${L.aggregate.r2_mean}` : '—';
  const n=document.getElementById('trk-note');
  if(n) n.innerHTML = (gr?`<b>Corpus-wide:</b> ${gr[0]} of ${gr[1]} verse loci have at least one witness passing `
      +`the governing gate. `:'')
    +(L?`<b>Dev set:</b> ${L.aggregate.verses} gold-anchored verses on ${L.aggregate.pages} pages; `
      +`pass-rate ${Math.round(100*L.aggregate.base_pass/L.aggregate.verses)}% → `
      +`${Math.round(100*L.aggregate.r2_pass/L.aggregate.verses)}%. `:'')
    +`The dev set is <b>${L?L.aggregate.pages:'~16'} pages</b> against a corpus of <b>${gr?gr[1]:'~6400'} verse loci</b> — `
    +`roughly ${L&&gr?((100*L.aggregate.verses/gr[1]).toFixed(1)):'3'}% of it. A rung validated on the dev set is `
    +`<b>evidence about the method, not about the corpus</b>, until the corpus figure moves.`;
}

// ---------- V5b: which INSTRUMENT governed, now that the reference policy is implemented ----------
function renderGovernance(){
  const host=document.getElementById('governance'); if(!host) return;
  const G=DATA.governance; if(!G){host.innerHTML='';return;}
  const tot=Object.values(G.by_instrument).reduce((a,b)=>a+b,0)||1;
  const row=(k,v)=>`<span class="mono">${k}</span> <b>${v}</b> (${(100*v/tot).toFixed(1)}%)`;
  host.innerHTML=`<b>Which witness actually judged each record.</b> `
    +Object.entries(G.by_instrument).filter(([,v])=>v).map(([k,v])=>row(k,v)).join(' &middot; ')
    +`. <b>The archaic reference was WITHDRAWN at ${G.archaic_withdrawn} records</b> — loci where its entry `
    +`disagrees with the modern reference below the calibrated floor, i.e. it is not this verse's own text and `
    +`cannot govern a failure verdict; <b>${G.passed_after_withdrawal}</b> of those then pass under the modern `
    +`witness. This is the day-1 policy (archaic primary where it has text, modern otherwise) with its predicate `
    +`corrected from "the slot holds a non-empty string" to "the slot holds THIS verse".`;
}

// ---------- V9 stream ladder (REP-2 / REP-4): the ONLY gold-anchored figure in the report ----------
function renderLift(){
  const host=document.getElementById('liftagg'), tb=document.getElementById('lift');
  const L=DATA.lift;
  if(!L){ if(host) host.innerHTML='<div class="note">No lift artifact — run <span class="mono">reocr_lift.py</span> to populate.</div>'; return; }
  const a=L.aggregate, r=L.representative;
  const pct=(x,n)=>`${Math.round(100*x/n)}%`;
  host.innerHTML=`<b>Gold-anchored aggregate</b> (${a.verses} verses on ${a.pages} pages, bar ${L.bar}): `
    +`base mean <b>${a.base_mean}</b> &rarr; R2 mean <b>${a.r2_mean}</b> `
    +`<span class="mono">(${(a.r2_mean-a.base_mean>=0?'+':'')+(a.r2_mean-a.base_mean).toFixed(3)})</span>; `
    +`pass-rate <b>${pct(a.base_pass,a.verses)}</b> &rarr; <b>${pct(a.r2_pass,a.verses)}</b>. `
    +`Representative (${r.pages} pages, confounds excluded): base <b>${r.base_mean}</b> &rarr; R2 <b>${r.r2_mean}</b>. `
    +(L.flagged_confounds.length? `<br><span class="pill open">${L.flagged_confounds.length} FLAGGED confound</span> `
        +L.flagged_confounds.map(f=>`<span class="mono">${f.slug}</span> (base ${f.base_mean} &rarr; R2 ${f.r2_mean}) — ${f.reason}`).join(' · ')
      : '');
  const cols=[['slug','page'],['book','book'],['n','verses'],['base_mean','base'],['r2_mean','R2'],
              ['lift','lift'],['base_pass','base pass'],['r2_pass','R2 pass'],['r3','R3 lifted'],['s','&#383; closed'],['open','still OPEN']];
  tb.querySelector('thead').innerHTML='<tr>'+cols.map(c=>`<th>${c[1]}</th>`).join('')+'</tr>';
  tb.querySelector('tbody').innerHTML=(L.pages||[]).map(p=>{
    const lift=(p.r2_mean||0)-(p.base_mean||0);
    const rows=p.rows||[];
    const r3=rows.filter(x=>x.r3_gold!=null&&x.r3_gold>=L.bar).length;
    const r3n=rows.filter(x=>x.r3_gold!=null).length;
    const sc=rows.filter(x=>x.s_state==='CLOSED').length;
    const sn=rows.filter(x=>x.s_state!=null).length;
    return `<tr class="${p.flagged?'confound':''}"><td class="mono">${p.slug.replace('scripture-','')}</td>`
      +`<td>${p.book}</td><td class="num">${p.n}</td>`
      +`<td class="num">${p.base_mean}</td><td class="num">${p.r2_mean}</td>`
      +`<td class="num ${lift>=0?'up':'down'}">${(lift>=0?'+':'')+lift.toFixed(3)}</td>`
      +`<td class="num">${p.base_pass[0]}/${p.base_pass[1]}</td><td class="num">${p.r2_pass[0]}/${p.r2_pass[1]}</td>`
      +`<td class="num">${r3n?`${r3}/${r3n}`:'—'}</td><td class="num">${sn?`${sc}/${sn}`:'—'}</td>`
      +`<td class="num">${p.still_open.length}</td></tr>`;
  }).join('');
}

// ---------- V10 matter as first-class books (REP-5) ----------
function renderMatter(){
  const tb=document.getElementById('matter'), sum=document.getElementById('mattersum');
  const M=DATA.matter;
  if(!M){ if(sum) sum.innerHTML='No matter scoring artifact — run <span class="mono">matter_scoring_run.py</span>.'; return; }
  const bar=Math.round(100*M.pass_threshold);
  let tot=0,pass=0,loc=0;
  (M.books||[]).forEach(b=>(b.sources||[]).forEach(sc=>{tot++; if(sc.located)loc++; if((sc.overall_pct??-1)>=bar)pass++;}));
  sum.innerHTML=`<b>${(M.books||[]).length}</b> matter sections &times; their testament's curated sources = <b>${tot}</b> rows; `
    +`<b>${loc}</b> located, <b>${pass}</b> at or above the ${bar}% bar &rarr; <b>${tot-pass}</b> flagged for re-OCR and held OPEN. `
    +`PARA pool is scored on ~${M.window_words}-word windows, APPARATUS pool at interval grain.`;
  const cols=['section','testament','intervals','source','located','overall','para','apparatus','verdict'];
  tb.querySelector('thead').innerHTML='<tr>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr>';
  const out=[];
  (M.books||[]).forEach(b=>(b.sources||[]).slice().sort((x,y)=>(y.overall_pct??-1)-(x.overall_pct??-1)).forEach((sc,i)=>{
    const own=(sc.ocr_dir===b.own_source);
    // A NOT-LOCATED row carries no scores at all — the section could not be found in that scan. That is
    // evidence (the witness does not attest this matter), not a missing datum, so the row is rendered with
    // the absence stated rather than dropped or scored as zero.
    const pool=(pct,pair)=>pct==null?'<span class="sub">n/a</span>':`${pct}% <span class="sub">${pair[0]}/${pair[1]}</span>`;
    const met=(sc.overall_pct!=null && sc.overall_pct>=bar);
    out.push(`<tr><td class="mono">${i?'':b.locus.replace('matter/','')}</td><td>${i?'':b.testament.toUpperCase()}</td>`
      +`<td class="num">${i?'':b.n_intervals}</td>`
      +`<td class="mono">${sc.scan}${own?' <span class="sub">own</span>':''}</td>`
      +`<td>${sc.located?'yes':'<b>not located</b>'}</td>`
      +`<td class="num">${sc.overall_pct==null?'<span class="sub">n/a</span>':sc.overall_pct+'%'}</td>`
      +`<td class="num">${pool(sc.para_pct,sc.para)}</td>`
      +`<td class="num">${pool(sc.app_pct,sc.app)}</td>`
      +`<td><span class="pill ${met?'closed':'open'}">${met?'met':'OPEN'}</span></td></tr>`);
  }));
  tb.querySelector('tbody').innerHTML=out.join('');
}

// ---------- V11 OPEN ledger: the terminal worklist that blocks the deliverable ----------
function renderLedger(){
  const tb=document.getElementById('ledger'), sum=document.getElementById('ledgersum');
  const G=DATA.ledger;
  if(!G){ if(sum) sum.innerHTML='No ledger artifact present.'; return; }
  sum.innerHTML=`<span class="pill ${G.blocks_deliverable?'open':'closed'}">${G.blocks_deliverable?'BLOCKS THE DELIVERABLE':'clear'}</span> `
    +`<b>${G.n_open}</b> open unit(s)`+(G.s_debts_closed_by_arbiter?` &middot; <b>${G.s_debts_closed_by_arbiter.length}</b> &#383;-surface debt(s) closed by the arbiter (by observation, not by moving the bar)`:'')
    +`. By reason: `+Object.entries(G.by_reason||{}).map(([k,v])=>`<span class="mono">${k}</span> &times;${v}`).join(' &middot; ')+'.';
  const cols=['locus','source','page','rungs tried','best','reference','&tau;x','reason'];
  tb.querySelector('thead').innerHTML='<tr>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr>';
  tb.querySelector('tbody').innerHTML=(G.entries||[]).map(e=>
    `<tr><td class="mono">${e.locus_key}</td><td class="mono">${e.source}</td><td class="num">${e.page_index}</td>`
    +`<td class="mono">${(e.rungs_tried||[]).join(' &rarr; ')}</td><td class="num">${e.best_score}</td>`
    +`<td class="mono">${e.reference_used} <span class="sub">${e.reference_axis}</span></td><td class="num">${e.taux}</td>`
    +`<td>${e.reason.startsWith('content-error')?`<span class="ce">${e.reason}</span>`:e.reason}</td></tr>`).join('');
}

// ---------- V7 apparatus (front/back-matter) pilot: archaic-only bars per element ----------
function renderApparatus(){
  const host=document.getElementById('apparatus');if(!host)return;
  const A=DATA.apparatus;
  if(!A||!A.elements){host.innerHTML='<div class="note">No apparatus audit present — run apparatus_audit.py to populate.</div>';return;}
  host.className='gridwrap';host.innerHTML='';
  Object.values(A.elements).forEach(e=>{
    const ids=Object.keys(e.sources).sort();
    const loc=ids.filter(k=>e.sources[k].localized).length;
    const card=document.createElement('div');card.className='mini';card.style.minWidth='430px';
    card.innerHTML=`<div><b>${e.slot_id.replace('apparatus/','')}</b> <span class="sub">${e.testament} · E(v)=${e.E_v} · witnesses ${e.witness_count}/${e.E_v} · localized ${loc}/${ids.length} · archaic ref ${e.archaic_ref_chars} ch${e.score_grain==='opening-sample'?' · opening-sample (not witness-crediting; full scoring P5)':''}</span> <span class="pill ${e.shortfall_flag?'fail':'pass'}">${e.shortfall_flag?'OPEN':'met'}</span></div>`;
    const W=Math.max(320,ids.length*48+40),H=158,padB=42,padL=28,padT=12;
    const g=svg(W,H);
    const y=v=>padT+(1-v)*(H-padB-padT);
    g.appendChild(el('line',{x1:padL,y1:y(0.9),x2:W-6,y2:y(0.9),stroke:COL.accent,'stroke-dasharray':'4 3'}));
    g.appendChild(el('text',{x:W-6,y:y(0.9)-3,'font-size':9,fill:COL.accent,'text-anchor':'end'},'0.90'));
    ids.forEach((sid,i)=>{
      const s=e.sources[sid];const x=padL+i*48+8;const bw=32;const v=s.archaic_id;
      if(v!=null){
        g.appendChild(el('rect',{x:x,y:y(v),width:bw,height:(H-padB)-y(v),fill:s.passed?COL.pass:(v>=0.5?COL.fail:COL.faildeep),opacity:.85,rx:2}));
        g.appendChild(el('text',{x:x+bw/2,y:y(v)-3,'font-size':9,fill:COL.mut,'text-anchor':'middle'},v.toFixed(2)));
      } else {
        g.appendChild(el('rect',{x:x,y:H-padB-7,width:bw,height:7,fill:COL.absent,opacity:.7,rx:2}));
      }
      g.appendChild(el('text',{x:x+bw/2,y:H-padB+14,'font-size':9,fill:COL.ink,'text-anchor':'middle'},sid));
      g.appendChild(el('text',{x:x+bw/2,y:H-padB+25,'font-size':8,fill:COL.mut,'text-anchor':'middle'},s.localized?('r '+s.probe_recall.toFixed(2)):'no loc'));
    });
    card.appendChild(g);host.appendChild(card);
  });
  // OPEN apparatus surface + re-OCR worklist (front/back-matter tracking; No Silent Degradation)
  const wl=A.reocr_worklist||[], os=A.open_slots||[];
  const nb=os.filter(s=>s.status==='OPEN-needs-build').length;
  const mref=os.filter(s=>s.modern_ref_available).length;
  const noarch=os.filter(s=>!s.archaic_ref_available).length;
  const sum=document.createElement('div');sum.className='note';sum.style.gridColumn='1 / -1';
  sum.innerHTML=`<b>Apparatus re-OCR worklist &amp; OPEN surface.</b> On the worklist (localizes but below the 0.90 archaic bar → feeds P4/P5): ${wl.map(w=>`<span class="mono">${w.locus.replace('apparatus/','')}</span> (best archaic ${w.best_archaic_id}${w.score_grain==='opening-sample'?', opening-sample':''}, ${w.localized_but_failed.length} scans)`).join(' · ')||'—'}. `
    +`<b>${os.length}</b> further skeleton apparatus regions remain unbuilt — all <b>${nb} needs-build</b> (a governing modern reference — the janvier-s reference/ set, original DR apparatus in modern spelling, keyed 1:1 — exists for <b>${mref}/${os.length}</b>). The gap is the diplomatic ARCHAIC surface: <b>${noarch}</b> slots have none in s_dismas — the remaining front slots (title-page / privilege / censura / censure) need a scan re-OCR at P4, and the back-matter slots have only the partial odr-com twin (~39/76 books). Building the archaic surface + full scoring is P4/P5. Nothing silently dropped.`;
  host.appendChild(sum);
}
function renderBookAudit(){
  const BA=DATA.book_audits||{};
  const host=document.getElementById('bookaudit'), sum=document.getElementById('bookauditsum'),
        vs=document.getElementById('vstack');
  const books=Object.keys(BA);
  if(!books.length){
    // Render nothing rather than an empty table: a blank grid reads as "audited, came back clean".
    sum.innerHTML='<b>No book has been audited yet.</b> Run <span class="mono">book_audit.py &lt;book&gt;</span>; this section appears once a book-audit artifact exists.';
    document.getElementById('s-bookaudit').querySelector('.scrollx').style.display='none';
    return;
  }
  const st=BA[books[0]].stack||[];
  vs.innerHTML='<b>The operational vertical stack.</b> A defect is attributed to the LOWEST layer that can explain it &mdash; calling a truncated span "recognition" is how defect&nbsp;#8 survived three rounds. '
    +st.map(l=>`<span class="mono"><b>${l.id}</b> ${l.name}</span>`).join(' &rarr; ')
    +'<br><br>'+st.map(l=>`<b>${l.id} ${l.name}</b> &mdash; <span class="mono">${l.modules}</span>. ${l.fault}`).join('<br>');
  const KIND=[['A','extra','V3'],['B','missing','V4'],['C','substituted','V5'],['D','near-miss','V5'],['E','no-ref','V6']];
  host.querySelector('thead').innerHTML='<tr><th>book</th><th>witness</th><th>volume</th><th>localized</th><th>passed</th><th>pass rate</th>'
    +KIND.map(k=>`<th>${k[0]} &middot; ${k[1]}<br><span class="mono">${k[2]}</span></th>`).join('')+'<th>misses<br><span class="mono">V4</span></th></tr>';
  const rows=[]; const notes=[];
  for(const b of books){
    const A=BA[b], per=A.per_witness||{};
    const order=Object.keys(per).sort((x,y)=>per[y].pass_rate-per[x].pass_rate);
    order.forEach((w,i)=>{
      const d=per[w], k=d.kinds||{};
      rows.push(`<tr><td>${i?'':`<b>${b}</b>`}</td><td><b>${w}</b></td><td class="mono">${A.witnesses[w]}</td>`
        +`<td>${d.localized}/${A.n_verses}</td><td>${d.passed}</td><td><b>${(100*d.pass_rate).toFixed(1)}%</b></td>`
        +KIND.map(x=>`<td>${k[x[0]]||0}</td>`).join('')
        +`<td>${(d.localization_misses||[]).length}</td></tr>`);
    });
    const cw=A.cross_witness||{}, tot=(cw.all_pass||0)+(cw.split||0)+(cw.all_fail||0);
    notes.push(`<b>${b}</b>: ${A.n_chapters} chapters, ${A.n_verses} verses, ${Object.keys(per).length} witnesses. `
      // R9.2c. `100*null` is 0 in JavaScript, so a spread that could NOT be computed would render as
      // "0.0 points" — the absence of a comparison printed as a perfect one, which is the R1.4 collapse
      // `book_audit` now refuses to make in Python, re-made one layer out. Null is stated, never coerced.
      // The basis is shown too: a spread is only as meaningful as the set it was taken over.
      +(A.parity_spread==null
          ? `Parity spread <b>not computed</b> (${(A.parity_spread_basis||{}).why||'fewer than two witnesses read anything'}). `
          : `Parity spread <b>${(100*A.parity_spread).toFixed(1)} points</b>`
            +(((A.parity_spread_basis||{}).over||[]).length
                ? ` over ${A.parity_spread_basis.over.join('+')}` : '')
            +((((A.parity_spread_basis||{}).excluded_localized_nothing)||[]).length
                ? `, excluding ${A.parity_spread_basis.excluded_localized_nothing.join('+')} (localized nothing)` : '')
            +`. `)
      +`Cross-witness &mdash; all pass <b>${cw.all_pass}</b> (${(100*cw.all_pass/tot).toFixed(1)}%), split <b>${cw.split}</b> (${(100*cw.split/tot).toFixed(1)}%), `
      +`<b>ALL FAIL ${cw.all_fail}</b> (${(100*cw.all_fail/tot).toFixed(1)}%) &mdash; that last figure is the honest size of the VERTICAL problem: no recognizer improvement reaches those verses. `
      +`V0 alien attestations: <b>${Object.keys(A.v0_alien_attestations||{}).length?JSON.stringify(A.v0_alien_attestations):'none'}</b>. `
      +`V1 chapter gaps: <b>${Object.keys(A.v1_chapter_gaps||{}).length?JSON.stringify(A.v1_chapter_gaps):'none'}</b>.`);
  }
  host.querySelector('tbody').innerHTML=rows.join('');
  sum.innerHTML=notes.join('<br><br>');
  renderAnatomy();
  renderRescore();
}
function renderRescore(){
  const RS=DATA.chapter_rescores||[]; const host=document.getElementById('rescore'); if(!host) return;
  if(!RS.length){ host.innerHTML=''; return; }
  const CLS=[['PASS','at or above the bar','&mdash;'],
             ['L4-MISS','no span at all','V4'],
             ['L4-SHORT','span under half the reference length','V4'],
             ['L4-LONG','span over 1.5&times; &mdash; swallowed a neighbour','V4'],
             ['V3-APPARATUS','interleaved annotation inside the span','V3'],
             ['V6-REF','witnesses + modern agree; archaic dissents','V6'],
             ['V5-RECOG','words present, misrecognised','V5']];
  let out='';
  for(const R of RS){
    const tot=Object.values(R.classes).reduce((a,b)=>a+b,0);
    out+=`<div class="note"><b>${R.book} ${R.chapter}</b> &mdash; ${R.verses.length} verses &times; ${Object.keys(R.witnesses).length} witnesses = <b>${tot}</b> source-verses, scored against <span class="mono">${R.references.join('</span>, <span class="mono">')}</span>. `
      +`Support histogram (witnesses passing per verse): ${Object.entries(R.support_hist).sort().map(([k,v])=>`<b>${v}</b> verses at ${k}/4`).join(' &middot; ')}. `
      +`Archaic-reference outliers: <b>${R.archaic_reference_outliers.length?R.archaic_reference_outliers.map(v=>R.chapter+':'+v).join(', '):'none'}</b>.</div>`
      +'<div class="scrollx"><table><thead><tr><th>class</th><th>what it is</th><th>layer</th><th>source-verses</th><th>share</th></tr></thead><tbody>'
      +CLS.filter(c=>R.classes[c[0]]).map(c=>{
        const n=R.classes[c[0]];
        return `<tr${c[0]==='PASS'?'':' style="font-weight:600"'}><td class="mono">${c[0]}</td><td>${c[1]}</td><td class="mono">${c[2]}</td><td>${n}</td><td>${(100*n/tot).toFixed(1)}%</td></tr>`;
      }).join('')+'</tbody></table></div>';
    // per-verse detail
    out+='<div class="scrollx"><table><thead><tr><th>verse</th><th>ref tok</th><th>support</th>'
      +Object.keys(R.witnesses).map(w=>`<th>${w}<br><span class="mono">s_dis / odr / sab</span></th>`).join('')
      +'</tr></thead><tbody>'
      +R.verses.map(v=>`<tr><td><b>${R.chapter}:${v.verse}</b></td><td>${v.ref_tokens}</td><td>${v.support}/4</td>`
        +Object.keys(R.witnesses).map(w=>{const d=v.witnesses[w],s=d.scores;
           const f=x=>x==null?'&ndash;':x.toFixed(2);
           return `<td${d.passed?'':' style="opacity:.75"'}>${f(s.s_dismas)} / ${f(s.odr_com)} / ${f(s.sabates_a)}<br><span class="mono">${d.class}${d.length_ratio!=null?' &middot; '+d.length_ratio+'&times;':''}</span></td>`;
         }).join('')+'</tr>').join('')
      +'</tbody></table></div>';
  }
  host.innerHTML=out;
}
function renderAnatomy(){
  const AN=DATA.allfail_anatomy||{}; const books=Object.keys(AN);
  const host=document.getElementById('anatomy'); if(!host) return;
  if(!books.length){ host.innerHTML=''; return; }
  // Axis -> [label, group, the layer a difference on this axis implicates]
  const AX=[['ref_tokens','reference length (tokens)','CONTENT','—'],
            ['mean_token_len','mean token length','CONTENT','—'],
            ['frac_capitalised','capitalised tokens (names)','VOCABULARY','—'],
            ['page_initial','verse opens the page body','PLACEMENT','V3/V4'],
            ['page_final','verse closes the page body','PLACEMENT','V3/V4'],
            ['is_chapter_first','verse 1 of its chapter','PLACEMENT','V3'],
            ['is_chapter_last','last verse of its chapter','PLACEMENT','V3'],
            ['lines_spanned','printed lines spanned','LINE-SPLIT','—'],
            ['cross_page','neighbour verse on another page','LINE-SPLIT','V4'],
            ['soft_hyphens','soft-hyphen breaks in the span','TYPESETTING','V5'],
            ['marginalia_frac','marginalia share of page lines','LAYOUT','V3'],
            ['x_clusters','distinct body x-starts (columns)','LAYOUT','V3']];
  let out='';
  for(const b of books){
    const A=AN[b], af=A.all_fail||{}, ct=A.control||{};
    out+=`<div class="note"><b>${b}</b> — ${A.n_all_fail} all-fail verses against ${A.n_control} that pass in EVERY witness. `
      +`Each axis is a CONTRAST: a bare rate means nothing until you know the control's.</div>`
      +'<div class="scrollx"><table><thead><tr><th>group</th><th>axis</th><th>all-fail</th><th>control</th><th>ratio</th><th>implicates</th></tr></thead><tbody>'
      +AX.filter(a=>af[a[0]]!=null&&ct[a[0]]!=null).map(a=>{
          const x=af[a[0]], y=ct[a[0]];
          if(Math.max(x,y)<0.005) return `<tr><td>${a[2]}</td><td>${a[1]}</td><td>${x.toFixed(3)}</td><td>${y.toFixed(3)}</td><td>n/a</td><td>both ~0 — no signal</td></tr>`;
          const r=y?x/y:Infinity, hot=(r>1.35||r<0.74);
          return `<tr${hot?' style="font-weight:600"':''}><td>${a[2]}</td><td>${a[1]}</td><td>${x.toFixed(3)}</td><td>${y.toFixed(3)}</td><td>${r.toFixed(2)}${hot?' &lt;&lt;&lt;':''}</td><td>${hot?a[3]:'—'}</td></tr>`;
        }).join('')
      +'</tbody></table></div>';
  }
  host.innerHTML=out;
}
function renderAll(){
  // Each section is isolated: one section throwing must not blank every section after it. (Measured: an
  // undefined score on a not-located matter row aborted renderAll and silently removed the whole OPEN
  // ledger from the report — a rendering failure that read as 'nothing is blocking'.)
  const secs=[['campaign',cgRender],['tracks',renderTracks],['cards',renderCards],['grain',renderGrain],['V1',renderV1],['V2',renderV2],['V3',renderV3],
              ['V4',renderV4],['V5',renderV5],['V5b-governance',renderGovernance],['V6',renderV6],['V9-lift',renderLift],['V10-matter',renderMatter],
              ['V12-bookaudit',renderBookAudit],['V11-ledger',renderLedger],['worklist',renderWL]];
  for(const [name,fn] of secs){ try{ fn(); }catch(e){ console.error('render failed:',name,e); } }
}
function init(){
  const sel=document.getElementById('bookSel');
  sel.innerHTML='<option value="__all__">all books</option>'+DATA.meta.scope_books.map(b=>`<option value="${b}">${b}</option>`).join('');
  renderHead();renderVersionCompare();renderInventory();renderMethods();renderRung0Signoff();renderInterp();renderApparatus();setGate('archaic');
}
init();
</script>
</body></html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
