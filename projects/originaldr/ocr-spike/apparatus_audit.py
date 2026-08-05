"""OriginalDR apparatus (front/back-matter) pilot audit — pulls s_dismas 01-front-matter.pdf
forward as the ARCHAIC reference for front-matter elements, localizes each element in the OT
scans by content overlap over their front pages, scores char-identity under the archaic-
preeminent gate, and emits an element-grain apparatus audit.

Sir (2026-07-10): "Fixing apparatus is the biggest gap. Definitely use s-dismas. Pull forward
01-front-matter.pdf so we iterate these early stages with a little apparatus input. This may help
the bulk of apparatus land softer at P5." The MODERN apparatus reference is the janvier-s reference/
set — the original Douay-Rheims apparatus in modern spelling, keyed 1:1 to the apparatus slots (there
is NO Confraternity `conf` dir here; the prior 'Confraternity 1941' note was a mislabel). It is the
same source the reconstruction masks per commit 3806656, and is wired here as modern_ref. s_dismas
front-matter remains the archaic (governing) reference where it exists; otherwise the modern janvier
reference governs. Every below-bar element stays OPEN (No Silent Degradation).

Run from palimpsest root:  core/.venv/bin/python projects/originaldr/ocr-spike/apparatus_audit.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF  # type: ignore[import-not-found]

HERE = Path(__file__).resolve().parent
PALIMPSEST = Path("/Users/nathanielcannon/Claude/Projects/palimpsest")
RECON = PALIMPSEST / "core/tests/fixtures/gold/mask_engine/originaldr_reconstruction"
SDISMAS_REPO = (PALIMPSEST / "imports/Scripture/Bibles/DouayRheims_DR/sources/"
                "transcriptions/s-dismas/repo")
JANVIER_REF = PALIMPSEST / ".scratch/original-douay-rheims/reference"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(RECON))
import detect_our_ocr as D          # noqa: E402  # type: ignore[import-not-found]
import char_identity as CI          # noqa: E402  # type: ignore[import-not-found]

MSL = HERE / "master-source-list.json"
SRC_INDEX = HERE / "source-index.json"
OUT = HERE / "coverage-audit-apparatus.json"

FRONT_SEARCH_PAGES = 60      # front-matter sits at the very front of a volume scan
LOCALIZE_FLOOR = 0.18        # min content-token overlap (recall vs the reference) to attest


# --------------------------------------------------------------------------------------------------
# Reference parse: s_dismas 01-front-matter.pdf -> {element_name: archaic surface text}
# --------------------------------------------------------------------------------------------------
def _page_texts(pdf: Path) -> list[str]:
    doc = fitz.open(pdf)
    return [str(doc.load_page(i).get_text()) for i in range(doc.page_count)]


def _first_line(t: str) -> str:
    for ln in t.splitlines():
        if ln.strip():
            return ln.strip().lower()
    return ""


def _first_lines(t: str, n: int = 3) -> str:
    """First n non-empty lines, lowercased + joined — for headings that print as a title line rather
    than a running header (e.g. 'The Preface to the Reader', 'The Books of the New Testament')."""
    out: list[str] = []
    for ln in t.splitlines():
        if ln.strip():
            out.append(ln.strip())
        if len(out) >= n:
            break
    return "\n".join(out).lower()


def parse_ot_frontmatter() -> dict[str, list[str]]:
    """Segment the OT front-matter (s_dismas Old-Testament/01-front-matter.pdf, 22 pp) into the
    apparatus elements this typeset edition actually carries, returned as PAGE LISTS (scoring is
    page/opening-aligned, never whole-blob at multi-page scale — see score_element).

    INVENTORY (v8, image-verified): pp0-8 are the modern editor's own front-matter (dedication,
    'Read This', citations) — NOT DR apparatus; p9 is the one-page Latin 'approbatio.' (Estius et al.,
    'Duaci. 8. Nouembris. 1609'); the Preface CONTENT begins p10 ('to the right vvelbeloved english
    reader') — one page ahead of the first 'Preface' running header (p11). This edition carries NO
    distinct archaic title-page / privilege / censura surface, so those slots stay OPEN and are never
    fabricated (No Silent Degradation)."""
    pages = _page_texts(SDISMAS_REPO / "Old-Testament" / "01-front-matter.pdf")
    heads = [_first_line(t) for t in pages]
    appr_pages = [i for i, h in enumerate(heads) if h.startswith("approbatio")]
    elems: dict[str, list[str]] = {}
    if appr_pages:
        lo = min(appr_pages)
        pref_start = lo + 1  # approbatio is a single page; the Preface content starts on the next page
        elems["apparatus/ot-front/approbatio"] = pages[lo:pref_start]
        elems["apparatus/ot-front/preface"] = pages[pref_start:]
    return {k: v for k, v in elems.items() if "".join(v).strip()}


def parse_nt_frontmatter() -> dict[str, list[str]]:
    """Segment the NT front-matter (s_dismas New-Testament/01-front-matter.pdf, 58 pp), as PAGE LISTS.

    INVENTORY (v8, image-verified): pp0-9 are the modern editor's front-matter; the archaic 'Preface
    to the Reader' runs p10-49 (heading 'The Preface to the Reader / Treating of These Three Points');
    p50-55 are the 'Books of the New Testament' canon list and p56-57 'The Svmme of the New Testament'
    — neither is a skeleton nt-front apparatus slot (title-page / preface / censure), so neither is
    emitted. This edition carries NO archaic nt title-page or censure surface, so those slots stay OPEN
    and are never fabricated."""
    pages = _page_texts(SDISMAS_REPO / "New-Testament" / "01-front-matter.pdf")
    lows = [_first_lines(t) for t in pages]
    pref_start = next((i for i, s in enumerate(lows) if "preface to the reader" in s), None)
    if pref_start is None:
        return {}
    pref_end = next((i for i in range(pref_start + 1, len(pages))
                     if "books of the new testament" in lows[i] or "svmme of the new" in lows[i]),
                    len(pages))
    seg = pages[pref_start:pref_end]
    return {"apparatus/nt-front/preface": seg} if "".join(seg).strip() else {}


# --------------------------------------------------------------------------------------------------
# Modern apparatus reference: janvier-s reference/ (original DR apparatus, modern spelling)
# --------------------------------------------------------------------------------------------------
def _harvest_strings(obj: Any) -> list[str]:
    """Recursively collect prose from a janvier reference doc (schema varies: paragraphs / entries /
    columns / closing). Skip the structural 'section' key."""
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for k, v in obj.items() if k != "section" for s in _harvest_strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _harvest_strings(v)]
    return []


def load_janvier_apparatus() -> dict[tuple[str, str], str]:
    """janvier-s reference/ IS the original Douay-Rheims apparatus in MODERN spelling (there is no
    `conf` dir; the top level is annotations/bible/reference/usfm). Commit 3806656 confirms the
    reconstruction masks this same janvier-s apparatus. Returns {(testament, slot_name): modern_text}
    for every reference/{ot,nt}/*.json, with <...> tags (e.g. marginal-note anchors) stripped."""
    out: dict[tuple[str, str], str] = {}
    for testament in ("ot", "nt"):
        tdir = JANVIER_REF / testament
        if not tdir.is_dir():
            continue
        for f in sorted(tdir.glob("*.json")):
            try:
                d = json.loads(f.read_text())
            except Exception:
                continue
            text = re.sub(r"<[^>]+>", " ", " ".join(_harvest_strings(d)))
            out[(testament, f.stem)] = re.sub(r"\s+", " ", text).strip()
    return out


def janvier_modern(janvier: dict[tuple[str, str], str], slot_id: str, region: str | None) -> str | None:
    """Map an apparatus slot to its janvier modern reference by (testament, last-path-component)."""
    name = slot_id.split("/")[-1]
    if region and region.startswith("ot"):
        return janvier.get(("ot", name))
    if region and region.startswith("nt"):
        return janvier.get(("nt", name))
    return None


# --------------------------------------------------------------------------------------------------
# Scan front pages
# --------------------------------------------------------------------------------------------------
def scan_front_text_by_page(ocr_dir: str, limit: int = FRONT_SEARCH_PAGES) -> list[str]:
    d = D.DIPL_ROOT / ocr_dir
    if not d.is_dir():
        return []
    pages = sorted(d.glob("*.json"))[:limit]
    out: list[str] = []
    for p in pages:
        try:
            rec = json.loads(p.read_text())
        except Exception:
            out.append("")
            continue
        out.append(" ".join(ln.get("text", "") for ln in rec.get("lines", [])))
    return out


def _tokens(text: str) -> list[str]:
    return CI.fold_modern(text).split()


def localize_element(ref_pages: list[str], page_texts: list[str]) -> tuple[list[str], float]:
    """Content-anchored localization: score each scan front page by content-token recall of the
    reference, take the contiguous run of above-half-peak pages as the element region. Returns
    (region_pages, recall) where recall = |ref∩region| / |ref| on folded content tokens. The region
    is returned PAGE-WISE so scoring can work on a bounded, aligned window rather than the whole blob."""
    ref_set = set(_tokens("\n".join(ref_pages)))
    if not ref_set or not page_texts:
        return [], 0.0
    page_tok = [set(_tokens(t)) for t in page_texts]
    # per-page overlap fraction against the reference token set
    scores = [len(pt & ref_set) / len(pt) if pt else 0.0 for pt in page_tok]
    peak = max(range(len(scores)), key=lambda i: scores[i])
    if scores[peak] == 0.0:
        return [], 0.0
    thr = scores[peak] * 0.5
    lo = hi = peak
    while lo - 1 >= 0 and scores[lo - 1] >= thr:
        lo -= 1
    while hi + 1 < len(scores) and scores[hi + 1] >= thr:
        hi += 1
    region = page_texts[lo:hi + 1]
    covered = ref_set & set(_tokens("\n".join(region)))
    recall = len(covered) / len(ref_set)
    return region, round(recall, 4)


# --------------------------------------------------------------------------------------------------
# Element identity scoring. char_identity.edit_ratio is a pure-Python O(n·m) edit DP — fine for a
# verse (~100 chars) but it does NOT terminate on a 40-page apparatus blob (~90k chars), and the
# s_dismas edition is a modern RE-TYPESETTING whose pagination/line-breaks differ from the original
# scans, so page-to-page char alignment is invalid too. So: single-page elements are scored WHOLE
# (exact, witness-eligible); multi-page elements are scored on their ALIGNED OPENING WINDOW — the
# exact edit-identity of the first SAMPLE_FOLD folded chars, a representative sample that is labelled
# as such and NEVER credits a witness. Full aligned (banded) scoring of whole prefaces is a P5 task.
# The 0.90 gate is unchanged; below-bar / sampled elements stay OPEN (No Silent Degradation).
# --------------------------------------------------------------------------------------------------
SAMPLE_FOLD = 4000  # folded-char window for multi-page elements (bounds each edit DP to ~SAMPLE_FOLD^2)


def score_element(ref_pages: list[str], region_pages: list[str],
                  m_ref: str | None) -> tuple[dict[str, Any], bool]:
    """Return (verdict, witness_eligible). Small (single-page) elements: exact whole-element verdict
    via char_identity.evaluate_locus, witness-eligible. Large (multi-page) elements: exact edit-
    identity of the aligned opening SAMPLE_FOLD folded chars for both archaic and modern refs, marked
    score_grain='opening-sample', passed=False, witness_eligible=False (a sample never credits a
    witness). Gating stays archaic-preeminent (archaic_ref always exists for these elements)."""
    ref_blob = "\n".join(ref_pages)
    region_blob = " ".join(region_pages)
    fa_ref = CI.fold_archaic(ref_blob)
    if len(fa_ref) <= SAMPLE_FOLD:
        verdict = CI.evaluate_locus(region_blob, modern_ref=m_ref, archaic_ref=ref_blob)
        verdict["floor_modern"] = CI.floor_modern(ref_blob, m_ref)
        verdict["score_grain"] = "whole-element"
        return verdict, True
    fa_reg = CI.fold_archaic(region_blob)
    arc = round(CI.edit_ratio(fa_ref[:SAMPLE_FOLD], fa_reg[:SAMPLE_FOLD]), 4)
    mod: float | None = None
    if m_ref:
        mod = round(CI.edit_ratio(CI.fold_modern(ref_blob)[:SAMPLE_FOLD],
                                  CI.fold_modern(region_blob)[:SAMPLE_FOLD]), 4)
    verdict = {
        "modern_id": mod, "archaic_id": arc,
        "modern_ref_exists": m_ref is not None, "archaic_ref_exists": True,
        "modern_pass": mod is not None and mod >= CI.THRESHOLD, "archaic_pass": arc >= CI.THRESHOLD,
        "governing_gate": "archaic", "passed": False, "threshold": CI.THRESHOLD, "floor_modern": None,
        "score_grain": "opening-sample", "sample_fold_chars": SAMPLE_FOLD,
        "score_note": (
            f"multi-page element ({len(fa_ref)} folded chars): the full char-level identity is a pure-"
            f"Python O(n·m) edit DP that does not terminate whole, and s_dismas re-pagination invalidates "
            f"page-grain alignment; archaic_id is the EXACT edit-identity of the aligned opening "
            f"{SAMPLE_FOLD} folded chars — a representative sample that does NOT credit a witness. Banded "
            f"full-element scoring is a P5 task."),
    }
    return verdict, False


# --------------------------------------------------------------------------------------------------
def main() -> int:
    msl = json.loads(MSL.read_text())
    by_source = {w["source"]: w for w in msl["witnesses"]}
    src_index = json.loads(SRC_INDEX.read_text())
    fb_ev = src_index["loci_ev"]["front_back_matter"]

    refs = {**parse_ot_frontmatter(), **parse_nt_frontmatter()}
    print(f"parsed front-matter elements: {list(refs)}", file=sys.stderr)

    janvier = load_janvier_apparatus()
    print(f"janvier modern apparatus refs: {len(janvier)} slots", file=sys.stderr)

    # Per-scan front-matter OCR dir, by testament. OT front-matter is at the front of the OT vol-1
    # (first existing NON-NT dir). NT front-matter is at the front of a SEPARATE NT volume: prefer an
    # is_nt_alias dir, else — for an NT-only scan — its first existing dir. A combined OT+NT scan with
    # no separate NT volume (S6/jp2-S06) is NOT front-addressable for NT; it is recorded with a reason
    # and surfaces as an expected-but-unlocalized gap, never silently dropped (mirrors the V3 union).
    def _existing(dirs: list[str]) -> list[str]:
        return [d for d in dirs if (D.DIPL_ROOT / d).is_dir()]

    ot_scans: dict[str, str] = {}
    nt_scans: dict[str, str] = {}
    nt_unaddressable: dict[str, str] = {}
    for sid, w in by_source.items():
        if w["kind"] != "scan":
            continue
        dirs = [v["ocr_dir"] for v in w.get("volumes", []) if v.get("ocr_dir")]
        if "OT" in w.get("testaments", []):
            ot_dirs = _existing([d for d in dirs if not D.is_nt_alias(d)])
            if ot_dirs:
                ot_scans[sid] = ot_dirs[0]
        if "NT" in w.get("testaments", []):
            nt_alias = _existing([d for d in dirs if D.is_nt_alias(d)])
            if nt_alias:
                nt_scans[sid] = nt_alias[0]
            elif w.get("testaments") == ["NT"]:
                nt_only = _existing(dirs)
                if nt_only:
                    nt_scans[sid] = nt_only[0]
                else:
                    nt_unaddressable[sid] = "no OCR data on disk for this NT scan (never OCR'd)"
            else:
                nt_unaddressable[sid] = ("combined OT+NT scan with no separate NT volume; the NT front-"
                                         "matter sits mid-volume, not front-addressable (deep-scan deferred)")

    front_cache: dict[str, list[str]] = {}
    elements_out: dict[str, Any] = {}
    for slot_id, ref_pages in refs.items():
        ev_info = fb_ev.get(slot_id, {})
        region = ev_info.get("region")
        E_v = ev_info.get("E_v")
        expected = set(ev_info.get("expected_witnesses", []))
        is_nt = (region or "").startswith("nt")
        scan_map = nt_scans if is_nt else ot_scans
        unaddr = nt_unaddressable if is_nt else {}
        m_ref = janvier_modern(janvier, slot_id, region)
        ref_blob = "\n".join(ref_pages)
        sources: dict[str, Any] = {}
        witness_count = 0
        # union over the AUTHORITATIVE expected set: every expected witness is visible; one with no
        # front-addressable dir shows as a localized=False gap with a reason (No Silent Degradation).
        cand = sorted(expected) if expected else sorted(scan_map)
        for sid in cand:
            ocr_dir = scan_map.get(sid)
            if ocr_dir is None:
                sources[sid] = {
                    "kind": "scan", "ocr_dir": None, "localized": False, "probe_recall": 0.0,
                    "unaddressable_reason": unaddr.get(sid, "no front-addressable OCR dir for this witness"),
                    "modern_id": None, "archaic_id": None, "archaic_ref_exists": True,
                    "modern_ref_exists": m_ref is not None, "governing_gate": "archaic",
                    "passed": False, "threshold": CI.THRESHOLD,
                }
                continue
            if ocr_dir not in front_cache:
                front_cache[ocr_dir] = scan_front_text_by_page(ocr_dir)
            region_pages, recall = localize_element(ref_pages, front_cache[ocr_dir])
            localized = recall >= LOCALIZE_FLOOR
            rec: dict[str, Any] = {
                "kind": "scan", "ocr_dir": ocr_dir, "localized": localized,
                "probe_recall": recall, "n_front_pages": len(front_cache[ocr_dir]),
            }
            if localized:
                verdict, witness_eligible = score_element(ref_pages, region_pages, m_ref)
                rec.update(verdict)
                if witness_eligible and by_source.get(sid, {}).get("counts_as_witness") and rec["passed"]:
                    witness_count += 1
            else:
                rec.update({"modern_id": None, "archaic_id": None, "archaic_ref_exists": True,
                            "modern_ref_exists": m_ref is not None, "governing_gate": "archaic",
                            "passed": False, "threshold": CI.THRESHOLD})
            sources[sid] = rec
        grains = {s.get("score_grain") for s in sources.values() if s.get("localized")}
        elements_out[slot_id] = {
            "slot_id": slot_id, "region": region, "testament": ev_info.get("testament"),
            "grain": "element", "E_v": E_v, "archaic_ref_source": "s_dismas",
            "archaic_ref_chars": len(ref_blob), "archaic_ref_pages": len(ref_pages),
            "score_grain": (next(iter(grains)) if len(grains) == 1 else ("mixed" if grains else None)),
            "modern_ref_source": "janvier-s reference/" if m_ref else None,
            "modern_ref_chars": len(m_ref) if m_ref else 0,
            "witness_count": witness_count,
            "shortfall_flag": (E_v is not None) and (witness_count < E_v),
            "sources": sources,
        }

    # ---- re-OCR worklist: localized-but-failed elements (scan finds the apparatus, OCR fails the bar) ----
    reocr_worklist: list[dict[str, Any]] = []
    for slot_id, e in elements_out.items():
        if not e["shortfall_flag"]:
            continue
        localized_failed = sorted(sid for sid, s in e["sources"].items()
                                  if s.get("localized") and not s.get("passed"))
        best = max((s.get("archaic_id") or 0.0 for s in e["sources"].values() if s.get("localized")),
                   default=0.0)
        sampled = e.get("score_grain") == "opening-sample"
        reocr_worklist.append({
            "locus": slot_id, "grain": "element", "region": e["region"], "E_v": e["E_v"],
            "score_grain": e.get("score_grain"),
            "witness_count": e["witness_count"], "missing": max(0, (e["E_v"] or 0) - e["witness_count"]),
            "localized_but_failed": localized_failed, "best_archaic_id": round(best, 4),
            "disposition": (
                "re-OCR + P5 full-element scoring (multi-page: localizes, but only the aligned opening "
                "is scored so far — best opening archaic below the 0.90 bar; the element is never accepted)"
                if sampled else
                "re-OCR (archaic reference exists; scans localize but OCR fails the 0.90 bar)"),
        })

    # ---- OPEN apparatus slots: every skeleton apparatus region not yet scored, with honest disposition.
    # Every slot HAS a modern reference (janvier-s reference/, 1:1 by slot name), so none is "needs-
    # reference": a governing reference exists (modern gates where archaic is absent). The remaining work
    # is the P5 build (localize + score). The archaic diplomatic surface is a separate enhancement —
    # s_dismas front-matter for front regions; odr-com (partial, archaic-spelling, ~39/76 books per commit
    # 3806656) for back regions. Nothing is silently dropped.
    open_slots: list[dict[str, Any]] = []
    for slot_id, info in fb_ev.items():
        if slot_id in elements_out:
            continue
        is_front = info.get("region", "") in ("ot_front", "nt_front")
        m_ref = janvier_modern(janvier, slot_id, info.get("region"))
        open_slots.append({
            "slot_id": slot_id, "region": info.get("region"), "testament": info.get("testament"),
            "E_v": info.get("E_v"),
            "modern_ref_available": m_ref is not None,
            "modern_ref_source": "janvier-s reference/" if m_ref else None,
            "modern_ref_chars": len(m_ref) if m_ref else 0,
            # v8: every element s_dismas actually carries (OT approbatio + OT preface + NT preface) is
            # now built + scored above, so whatever remains OPEN has NO diplomatic archaic surface in
            # s_dismas — front slots included (image-verified inventory), not just back-matter.
            "archaic_ref_available": False,
            "archaic_ref_note": (
                "s_dismas 01-front-matter.pdf inventoried (v8): it carries only the approbatio + preface "
                "(OT) and the preface (NT). This front slot (title-page / privilege / censura / censure) "
                "has no distinct archaic surface there — its archaic diplomatic text needs a scan re-OCR "
                "of that region at P4. Modern janvier reference exists."
                if is_front else
                "no diplomatic s_dismas back-matter; the odr-com archaic-spelling twin is partial (~39/76 books)"),
            "status": "OPEN-needs-build",
            "reason": "modern reference available (janvier-s); build the archaic surface + score at P4/P5",
        })

    out = {
        "_doc": "OriginalDR apparatus (front/back-matter) pilot. Archaic (governing) reference = "
                "s_dismas 01-front-matter.pdf (OT + NT), segmented by running header/heading into the "
                "elements the typeset edition actually carries: OT approbatio + OT preface + NT preface. "
                "MODERN reference = janvier-s reference/ (the original DR apparatus in modern spelling, "
                "keyed 1:1 to slots; the same source the reconstruction masks per commit 3806656 — NOT "
                "the Confraternity revision). Gating is archaic-preeminent: archaic governs where it "
                "exists, else the modern janvier reference governs. Content-anchored localization over "
                "scan front pages; identity is scored WHOLE for single-page elements and on the aligned "
                "OPENING WINDOW for multi-page prefaces (the whole-blob char DP is infeasible and the "
                "s_dismas re-pagination invalidates page-grain alignment; full aligned scoring is P5). "
                "Below-bar / sampled / absent elements stay OPEN (No Silent Degradation).",
        "phase": "P2-apparatus-pilot",
        "grain": "element",
        "gating": "archaic-preeminent",
        "scope": "OT+NT front-matter (OT approbatio + OT preface + NT preface); title-page / privilege / "
                 "censura / censure absent from s_dismas -> OPEN (need scan re-OCR at P4)",
        "identity_bar": {"threshold": CI.THRESHOLD, "localize_floor": LOCALIZE_FLOOR},
        "elements": elements_out,
        "reocr_worklist": reocr_worklist,
        "open_slots": open_slots,
        "summary": {
            "elements": len(elements_out),
            "elements_shortfall": sum(1 for e in elements_out.values() if e["shortfall_flag"]),
            "scans_localized": {k: sum(1 for s in e["sources"].values() if s["localized"])
                                for k, e in elements_out.items()},
            "reocr_worklist": len(reocr_worklist),
            "open_slots": len(open_slots),
            "open_needs_build": sum(1 for s in open_slots if s["status"] == "OPEN-needs-build"),
            "open_with_modern_ref": sum(1 for s in open_slots if s.get("modern_ref_available")),
            "open_without_diplomatic_archaic": sum(1 for s in open_slots if not s.get("archaic_ref_available")),
        },
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    for slot, e in elements_out.items():
        loc = sum(1 for s in e["sources"].values() if s["localized"])
        print(f"  {slot}: E(v)={e['E_v']} witnesses={e['witness_count']} "
              f"localized={loc}/{len(e['sources'])} ref_chars={e['archaic_ref_chars']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
