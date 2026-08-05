#!/usr/bin/env python3
"""qc_audit.py -- locus×source double-bind coverage AUTHORITY (OriginalDR QC contract).

REVISED 2026-07-10 (Sir): ARCHAIC-PREEMINENT gating at uniform VERSE/element grain.

For every scripture VERSE locus (scripture/{book}/{ch}/{v}) it records, per contributing source, a
double-bind verdict:

  FORWARD gate  -- a scan witness counts for a verse iff it LOCALIZES the verse (detect_book attests it)
                   AND passes the char-level identity bar under the GOVERNING gate: where an archaic
                   reference exists, PASS iff archaic_id >= 0.90 (archaic-preeminent -- modern_id is
                   recorded as a signal but does not gate); else PASS iff modern_id >= 0.90; neither
                   reference -> needs-reference (OPEN, never a silent pass). Transcriptions auto-pass
                   identity (they are the references) but must still localize (carry a read for the verse).
  BACKWARD gate -- realized witness_count vs E(v) (source-index loci_ev; verse inherits its book E_v).
                   witness_count < E_v raises shortfall_flag -> the re-OCR / investigate worklist.

References (built once, verse grain, per Sir 2026-07-10 -- FIXES the prior madueke_a bug: the modern
backfill is madueke_b, not the madueke_a localization-aid):
  archaic_ref[locus] = s_dismas[locus] if present else odr_com[locus]       (s_dismas preeminent)
  modern_ref[locus]  = sabates_a[locus] if present else madueke_b[locus]    (Janvier preeminent)

Verse records are the AUTHORITY; chapter and book rollups are emitted for the report's grain breakouts.
Scope = book slugs passed as argv (default = PILOT_BOOKS). Emits coverage-audit-verse.json next to this
script; the chapter-grain baseline coverage-audit.json is left intact as the P2-baseline phase artifact.

Run: core/.venv/bin/python .../ocr-spike/qc_audit.py [book_slug ...]
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PALIMPSEST = Path("/Users/nathanielcannon/Claude/Projects/palimpsest")
SCRATCH = PALIMPSEST / "projects/originaldr"
RECON = PALIMPSEST / "core/tests/fixtures/gold/mask_engine/originaldr_reconstruction"
READS = SCRATCH / "reconstruction/reads"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(RECON))
import detect_our_ocr as D          # noqa: E402  # type: ignore[import-not-found]
import char_identity as CI          # noqa: E402  # type: ignore[import-not-found]
import long_s_rule as LS            # noqa: E402  # type: ignore[import-not-found]
import verse_seg as VS              # noqa: E402  # janvier-cut re-segmentation (REPLACES align_coords 2026-07-22)
import curated_sources as CS        # noqa: E402  # REP-1 allowlist guard (drop S2,S5,S7,S10-S15 leak)
import corpus_localize as CL       # noqa: E402  # STAGE 1: the hybrid localizer's corpus vmap

# WHICH LOCALIZER PRODUCES THE VERSE MAP THE AUDIT SCORES.
#   "detect" — legacy `detect_our_ocr.detect_book`; the operating point every report before v019 measured.
#   "hybrid" — `page_address` + `verse_locate.best_spans` over the SAME stored stream (STAGE 1). No page is
#              re-recognised; the pages already on disk are addressed and localized properly.
# Kept switchable because the whole point of Stage 1 is a BEFORE/AFTER on identical inputs. Measured on gold
# (corpus_wire_probe): base mean 0.7213 / 40% pass -> hybrid 0.8724 / 60% pass = 74% of the full live-R2 lift,
# with zero re-recognition.
LOCALIZER = os.environ.get("ODR_LOCALIZER", "hybrid")

# Realign the archaic reference's verse indexing to janvier before scoring (see build_refs).
REALIGN_ARCHAIC = os.environ.get("ODR_REALIGN_ARCHAIC", "1") != "0"

# THE PREDICATE BEHIND THE DAY-1 RULE. `char_identity.evaluate_locus` already implements Sir's policy — the
# archaic witness governs where it has text, the modern witness governs otherwise — but its predicate is
# "the archaic slot holds a NON-EMPTY STRING", which is not the same as "the archaic witness has text OF ITS
# OWN for this verse". A slot holding the neighbouring verse satisfies the string test and then governs, and
# fails, a verse the OCR read correctly.
#
# CALIBRATED, NOT PICKED (floor_modern = archaic-ref vs modern-ref, no OCR involved):
#     archaic_id > 0.9 (reference demonstrably right)   floor_modern < 0.5 on     0 / 4714
#     archaic<0.2 & modern<0.2 (OCR at fault)           floor_modern < 0.5 on   104 /  998
#     archaic<0.2 & modern>0.9 (reference at fault)     floor_modern < 0.5 on   504 /  517
# 0.50 therefore excludes essentially no sound reference and catches 97% of the demonstrably wrong ones.
ARCHAIC_VALID_FLOOR = float(os.environ.get("ODR_ARCHAIC_FLOOR", "0.50"))

ALIGN_COORDS = os.environ.get("NO_ALIGN_COORDS") != "1"  # janvier-cut re-seg on by default; NO_ALIGN_COORDS=1 off

MSL = HERE / "master-source-list.json"
SRC_INDEX = HERE / "source-index.json"
SKELETON = RECON / "skeleton.json"
OUT = HERE / "coverage-audit-verse.json"

# Pilot scope: Psalms (columnar poster child) + Genesis (clean OT spine) + Matthew (richest NT, incl. the
# S11 sampler) + John (2nd major NT gospel; discourse-heavy prose layout, distinct from Matthew's) +
# Apocalypse (last NT book -> stresses end-of-volume localization). All five carry an s_dismas archaic
# reference, so archaic-preeminent gating actually engages.
PILOT_BOOKS = ["psalms", "genesis", "matthew", "john", "apocalypse"]

UPSCALE = 2


# --------------------------------------------------------------------------------------------------
# Verse-grain reference construction (task 8)
# --------------------------------------------------------------------------------------------------
def load_reads_verse(name: str) -> dict[str, str]:
    """reads/{name}.json -> {skeleton_id: surface} at scripture VERSE grain (4-part loci only)."""
    p = READS / f"{name}.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    out: dict[str, str] = {}
    for r in d.get("reads", []):
        sk = r.get("skeleton_id", "")
        parts = sk.split("/")
        if len(parts) == 4 and parts[0] == "scripture" and parts[2].isdigit() and parts[3].isdigit():
            surf = r.get("surface", "")
            if surf and surf.strip():
                out[sk] = surf
    return out


def build_refs() -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """(archaic_ref, modern_ref, archaic_src, modern_src) at verse grain, with backfill + provenance."""
    sd = load_reads_verse("s_dismas")
    oc = load_reads_verse("odr_com")
    sa = load_reads_verse("sabates_a")
    mb = load_reads_verse("madueke_b")
    archaic: dict[str, str] = dict(oc)
    archaic.update(sd)                      # s_dismas preeminent, odr_com backfills
    modern: dict[str, str] = dict(mb)
    modern.update(sa)                       # sabates_a preeminent, madueke_b backfills
    archaic_src = {k: ("s_dismas" if k in sd else "odr_com") for k in archaic}
    modern_src = {k: ("sabates_a" if k in sa else "madueke_b") for k in modern}

    # REALIGN THE ARCHAIC REFERENCE BEFORE IT IS USED. s_dismas does not count the Psalm superscription as
    # verse 1 where janvier does, so every verse of such a psalm is indexed one behind; 27 chapters across 13
    # books are shifted this way (see archaic_ref_align.py — the offset profiles peak sharply at one shift and
    # sit at 0.0 at every other, which is what distinguishes a shift from a genuine textual divergence).
    # Uncorrected, those verses fail the archaic gate while the OCR agrees with janvier above 0.9, i.e. a
    # REFERENCE indexing artifact reported as an OCR failure. Realigning RECOVERS the diplomatic reference
    # rather than discarding it, which is what a project about the archaic surface actually needs.
    if REALIGN_ARCHAIC:
        import archaic_ref_align as ARA
        shifts = ARA.detect(archaic, modern)
        if shifts:
            archaic, archaic_src = ARA.apply(archaic, archaic_src, shifts)
        # SECOND PASS — the shift that begins MID-CHAPTER, which the whole-chapter fit above cannot see.
        # `detect` scores one offset across every verse of a chapter, so an aligned head averages a shifted
        # tail away: Genesis 1 is aligned for 25 verses and shifted for 6, and was therefore declared sound
        # while those 6 were scored against the neighbouring verse. Genesis 26 is 32 verses shifted, with the
        # offset itself growing from -1 to -2 part-way down. Found by the book-grain cross-witness audit —
        # all four witnesses failing the SAME verses is the signature of a reference defect, never a
        # recognizer one. Still scored on archaic-vs-modern only, so no OCR can influence the alignment.
        pieces = ARA.detect_piecewise(archaic, modern)
        if pieces:
            archaic, archaic_src = ARA.apply_piecewise(archaic, archaic_src, pieces)
    return archaic, modern, archaic_src, modern_src


def detect_source_defects(ordinals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """s_dismas Class-A defects: interior chapters s_dismas is MISSING inside a book it otherwise covers
    (duplicated/absent chapter-heading in the source PDF/OCR). Auto-discovered so the set is not hand-
    maintained. Each defect carries its odr_com backfill status — a gap odr_com fills is interim-covered;
    one it does not is a genuine OPEN archaic-reference gap (never silently assumed covered)."""
    sd = load_reads_verse("s_dismas")
    oc = load_reads_verse("odr_com")

    def chapters_of(reads: dict[str, str], book: str) -> set[int]:
        pref = f"scripture/{book}/"
        out: set[int] = set()
        for k in reads:
            if k.startswith(pref):
                p = k.split("/")
                if len(p) == 4 and p[2].isdigit():
                    out.add(int(p[2]))
        return out

    sd_books = {k.split("/")[1] for k in sd if k.startswith("scripture/") and len(k.split("/")) == 4}
    defects: list[dict[str, Any]] = []
    for book in sorted(sd_books):
        binfo = ordinals.get(book)
        if not binfo:
            continue
        sd_ch = chapters_of(sd, book)
        oc_ch = chapters_of(oc, book)
        if not sd_ch:
            continue
        hi = min(max(sd_ch), binfo["chapters"])           # interior only: up to s_dismas's own top chapter
        for c in range(1, hi + 1):
            if c in sd_ch:
                continue
            covered = c in oc_ch
            defects.append({
                "locus": f"scripture/{book}/{c}", "source": "s_dismas",
                "reason": "missing-chapter (duplicated/absent chapter-heading in source PDF/OCR)",
                "backfill": "odr_com" if covered else None,
                "status": "interim-covered-odr_com" if covered else "OPEN-needs-archaic-reference",
            })
    return defects


def verse_texts_from_reads(reads: list[dict], book: str) -> dict[tuple[int, int], str]:
    """detect_book scan reads -> {(chapter, verse): surface} for one book."""
    out: dict[tuple[int, int], str] = {}
    for r in reads:
        parts = r.get("skeleton_id", "").split("/")
        if len(parts) < 4 or parts[0] != "scripture" or parts[1] != book:
            continue
        ch, v = parts[2], parts[3]
        if not (ch.isdigit() and v.isdigit()):
            continue
        surf = r.get("surface", "")
        if surf and surf.strip():
            out[(int(ch), int(v))] = surf
    return out


# --------------------------------------------------------------------------------------------------
def load_book_ordinals() -> dict[str, dict[str, Any]]:
    sk = json.loads(SKELETON.read_text())
    return {b["slug"]: b for b in sk["books"]}


# stream cache -- load each source's diplomatic OCR once, reuse across books.
_stream_cache: dict[str, Any] = {}


def stream_for(ocr_dir: str) -> Any | None:
    if ocr_dir in _stream_cache:
        return _stream_cache[ocr_dir]
    dip = D.DIPL_ROOT / ocr_dir
    stm = D.load_stream(dip, ocr_dir, UPSCALE) if dip.is_dir() else None
    _stream_cache[ocr_dir] = stm
    return stm


def scan_ocr_dirs(witness: dict) -> list[str]:
    return [v["ocr_dir"] for v in witness.get("volumes", []) if v.get("ocr_dir")]


def _mean(xs: list[float]) -> float | None:
    return round(st.mean(xs), 4) if xs else None


# Chronically-divergent books (plan §1.4 sub-rule 2; empirical s_dismas-vs-madueke_a token agreement < 0.80):
# the modern edition genuinely diverges from the 1582/1610 print here, so modern_id is a signal, not a gate.
CHRONIC_DIVERGENT = {"acts", "2-paralipomenon", "2-esdras", "romans", "mark", "psalms"}


def route_locus(book: str, verdict: dict[str, Any], floor_mod: float | None,
                ls_suspect: dict[str, Any], archaic_valid: bool = True) -> dict[str, Any]:
    """§1.4 scoped re-OCR routing for one scan record — which instrument GATES this locus and whether re-OCR
    should fire. The archaic (in-edition) gate is the real quality bar; the modern gate is used only where it
    is a VALID yardstick (floor_modern >= 0.90 and the book is not chronically divergent). Never accepts a
    locus on an invalid modern number, never burns re-OCR chasing one (No Silent Degradation)."""
    aid, mid = verdict["archaic_id"], verdict["modern_id"]
    aref, mref = verdict["archaic_ref_exists"], verdict["modern_ref_exists"]
    # `floor_modern` compares the ARCHAIC reference to the MODERN one, so a low value can mean either
    # "the modern edition diverges from the print" (invalidating modern) OR "the archaic entry is not this
    # verse" (invalidating archaic). It cannot mean both at the same locus. Once the archaic reference has
    # been WITHDRAWN as not-this-verse, the comparison it came from is void and cannot also condemn modern —
    # otherwise the verse ends up with no valid yardstick at all and can never pass, which is precisely what
    # happened when the predicate fix landed: 1752 records fell to `needs-in-family-reference` while only 16
    # reached the modern gate. Sir's policy is explicit that where the archaic witness has gaps, janvier and
    # madueke ARE primary for content and surface.
    modern_valid = (not archaic_valid) or (floor_mod is None) or (floor_mod >= CI.THRESHOLD)
    susp = ls_suspect["suspected_long_s_as_f"]
    if aref:
        fire = (aid is None) or (aid < CI.THRESHOLD)
        return {"governing_instrument": "archaic", "modern_is_signal": True,
                "modern_yardstick_valid": modern_valid, "reocr_fire": fire,
                "reocr_reason": "archaic_id < 0.90" if fire else "", "suspected_long_s_as_f": susp}
    if mref:
        if (not modern_valid) or (book in CHRONIC_DIVERGENT):
            reason = ("modern yardstick invalid (floor_modern < 0.90) and no archaic ref"
                      if not modern_valid else
                      "chronically-divergent book with no archaic ref")
            return {"governing_instrument": "needs-in-family-reference", "modern_is_signal": True,
                    "modern_yardstick_valid": modern_valid, "reocr_fire": False,
                    "reocr_reason": reason + " — needs in-edition reference (OPEN)",
                    "suspected_long_s_as_f": susp}
        fire = (mid is None) or (mid < CI.THRESHOLD)
        return {"governing_instrument": "modern", "modern_is_signal": False,
                "modern_yardstick_valid": True, "reocr_fire": fire,
                "reocr_reason": "modern_id < 0.90" if fire else "", "suspected_long_s_as_f": susp}
    return {"governing_instrument": "needs-reference", "modern_is_signal": False,
            "modern_yardstick_valid": modern_valid, "reocr_fire": False,
            "reocr_reason": "no reference (needs-reference OPEN)", "suspected_long_s_as_f": susp}


# --------------------------------------------------------------------------------------------------
def realign_vmap(vmap: dict[tuple[int, int], str], book: str) -> dict[tuple[int, int], str]:
    """Coordinate rehabilitation via verse_seg (janvier-cut) — REPLACES align_coords (2026-07-22, §5 linchpin).

    Re-cut the localized per-verse OCR to the JANVIER grid (sabates_a, the machine-precise interval authority),
    so archaic_id/modern_id measure recognition fidelity, not verse-boundary spillover. This is the fix that
    removes the boundary artifact align_coords produced (whole-chapter drift + circular s_dismas-as-ruler).
    Coverage semantics preserved: verse_seg localizes to the source's covered span. `drop_apparatus` is OFF
    here on purpose: the input is `detect_book`'s ALREADY verse-localized reads (not a raw page with
    interleaved footnotes), so on noisy base OCR a run of garbled-but-real words could be mis-read as
    apparatus and silently excised — the filter stays in the raw-page R2 stream where it is validated. No
    Silent Degradation: on a no-locate the original per-verse read is kept (surfaced as-is), never dropped."""
    by_ch: dict[int, dict[int, str]] = {}
    for (ch, v), txt in vmap.items():
        by_ch.setdefault(ch, {})[v] = txt
    out: dict[tuple[int, int], str] = {}
    for ch, vts in by_ch.items():
        vs = sorted(vts)
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if len(vs) < 2 or not janv:
            for v in vs:
                out[(ch, v)] = vts[v]
            continue
        seg = VS.segment(" ".join(vts[v] for v in vs), janv, drop_apparatus=False)
        if not seg:                                     # no-locate -> keep original reads (never silent-drop)
            for v in vs:
                out[(ch, v)] = vts[v]
            continue
        for v, d in seg.items():
            out[(ch, v)] = d["text"]
    return out


def main(argv: list[str]) -> int:
    # "all" sentinel expands to every skeleton book INSIDE python — robust against shell word-splitting
    # (zsh does not field-split unquoted $VAR, so a shell-joined slug list would arrive as one bad arg).
    if len(argv) == 1 and argv[0] == "all":
        argv = [b["slug"] for b in json.loads(SKELETON.read_text())["books"]]
    books = argv or PILOT_BOOKS
    # optional output override (QC_OUT) so a full-scope run cannot clobber the validated pilot artifact
    out_path = OUT
    if os.environ.get("QC_OUT"):
        p = Path(os.environ["QC_OUT"])
        out_path = p if p.is_absolute() else HERE / p
    msl = json.loads(MSL.read_text())
    by_source: dict[str, dict] = {w["source"]: w for w in msl["witnesses"]}

    src_index = json.loads(SRC_INDEX.read_text())
    loci_ev = src_index["loci_ev"]["scripture_books"]

    ordinals = load_book_ordinals()
    anchor_bb = D.anchor_by_book(D.load_anchor())            # localization anchor {book:{ch:{v:text}}}
    archaic_ref, modern_ref, archaic_src, modern_src = build_refs()
    source_defects = detect_source_defects(ordinals)

    verses_out: dict[str, Any] = {}
    chapters_out: dict[str, Any] = {}
    books_out: dict[str, Any] = {}
    worklist: list[dict] = []

    for book in books:
        binfo = ordinals.get(book)
        if not binfo:
            print(f"  ! skip {book!r}: not in skeleton", file=sys.stderr)
            continue
        ev_entry = loci_ev.get(book, {})
        E_v = ev_entry.get("E_v")
        # REP-1: hard allowlist filter — a banned source (e.g. S14) must never enter the audit via
        # expected_witnesses. filter_curated keeps only S1/S3/S4/S6/S8/S9 (No Silent Degradation on curation).
        expected = CS.filter_curated(ev_entry.get("expected_witnesses", []))
        testament = binfo["testament"]
        anchor_ch = anchor_bb.get(book, {})

        # verse locus universe: union of modern + archaic references restricted to this book
        pref = f"scripture/{book}/"
        locus_keys = {k for k in modern_ref if k.startswith(pref)} | {k for k in archaic_ref if k.startswith(pref)}

        def cv(k: str) -> tuple[int, int]:
            p = k.split("/")
            return (int(p[2]), int(p[3]))

        loci = sorted(locus_keys, key=cv)

        # ---- per (locus -> source -> verdict) accumulation ----
        per_locus: dict[str, dict[str, Any]] = {k: {} for k in loci}

        # scan witnesses that ought to contain this book
        for wid in expected:
            w = by_source.get(wid)
            if not w or w.get("kind") != "scan":
                continue
            best: dict[str, Any] | None = None
            if LOCALIZER == "hybrid":
                # The volume was addressed page-by-page (page_address, 100% coverage / 1251-of-1251 held-out)
                # and localized with best_spans; pick the volume that actually attests the most of this book.
                for ocr_dir in scan_ocr_dirs(w):
                    vm = CL.load(ocr_dir)
                    vmap = {(ch, v): t for (b, ch, v), t in vm.items() if b == book}
                    if not vmap:
                        continue
                    if best is None or len(vmap) > len(best["vmap"]):
                        best = {"meta": {"probe_recall": None}, "vmap": vmap, "ocr_dir": ocr_dir}
                if best is None:
                    continue
                # NO realign_vmap here: best_spans already cut these spans with verse_seg/the anchor walk, and
                # re-segmenting the result would discard exactly the localization Stage 1 exists to deliver.
            else:
                for ocr_dir in scan_ocr_dirs(w):
                    stm = stream_for(ocr_dir)
                    if stm is None:
                        continue
                    streams = {ocr_dir: stm}
                    reads, _, meta = D.detect_book(book, anchor_ch, wid, streams)
                    if not meta.get("covered"):
                        continue
                    if best is None or (meta.get("probe_recall") or 0) > (best["meta"].get("probe_recall") or 0):
                        best = {"meta": meta, "vmap": verse_texts_from_reads(reads, book), "ocr_dir": ocr_dir}
                if best is None:
                    continue
                if ALIGN_COORDS:
                    best["vmap"] = realign_vmap(best["vmap"], book)   # rehabilitate boundaries pre-scoring
            probe_recall = best["meta"].get("probe_recall")
            for (ch, v), ocr_text in best["vmap"].items():
                locus = f"scripture/{book}/{ch}/{v}"
                if locus not in per_locus:
                    per_locus[locus] = {}
                m_ref = modern_ref.get(locus)
                a_ref = archaic_ref.get(locus)
                # The archaic witness is primary ONLY where it carries this verse's own text. Where its
                # entry disagrees with the modern reference below the calibrated floor, it is not a valid
                # yardstick for this locus and the modern witness governs (Sir's stated policy, with the
                # predicate corrected). The verdict still REPORTS both scores; only the gate changes.
                _fm = CI.floor_modern(a_ref, m_ref)
                _archaic_valid = (_fm is None) or (_fm >= ARCHAIC_VALID_FLOOR)
                verdict = CI.evaluate_locus(ocr_text, m_ref, a_ref if _archaic_valid else None)
                verdict["archaic_id"] = CI.archaic_identity(ocr_text, a_ref) if (a_ref or "").strip() else None
                verdict["archaic_reference_invalid_here"] = not _archaic_valid
                rule_pass = LS.rule_pass(ocr_text) if not verdict["archaic_ref_exists"] else None
                floor_mod = CI.floor_modern(a_ref, m_ref)
                ls_suspect = CI.suspected_long_s_as_f(ocr_text, a_ref)
                routing = route_locus(book, verdict, floor_mod, ls_suspect, archaic_valid=_archaic_valid)
                # backward gate counts a scan only on a VALID pass: a modern pass on an invalid yardstick
                # (needs-in-family-reference / needs-reference) does not count (§1.4 sub-rules 2-3).
                passed_eff = bool(verdict["passed"]
                                  and routing["governing_instrument"] in ("archaic", "modern"))
                per_locus[locus][wid] = {
                    "kind": "scan", "localized": True, "ocr_dir": best["ocr_dir"],
                    "probe_recall": round(probe_recall, 4) if probe_recall is not None else None,
                    "archaic_rule_pass": rule_pass, "floor_modern": floor_mod,
                    "suspected_long_s_as_f": ls_suspect["suspected_long_s_as_f"],
                    "routing": routing, "passed_effective": passed_eff, **verdict,
                }

        # transcription witnesses: auto-pass identity, must localize (carry a read for the verse)
        for wid in expected:
            w = by_source.get(wid)
            if not w or w.get("kind") != "transcription" or not w.get("counts_as_witness"):
                continue
            reads_v = load_reads_verse(wid)
            for locus in reads_v:
                if not locus.startswith(pref):
                    continue
                if locus not in per_locus:
                    per_locus[locus] = {}
                per_locus[locus][wid] = {
                    "kind": "transcription", "localized": True, "auto_identity": True,
                    "modern_id": None, "archaic_id": None,
                    "modern_ref_exists": locus in modern_ref, "archaic_ref_exists": locus in archaic_ref,
                    "modern_pass": True, "archaic_pass": True,
                    "governing_gate": "reference", "passed": True, "passed_effective": True,
                }

        # ---- aggregate per verse (backward gate) ----
        book_src_scores: dict[str, dict[str, list[float]]] = {}
        book_shortfall = 0
        for locus in loci:
            ch, v = cv(locus)
            sources = per_locus.get(locus, {})
            counting = [s for s, r in sources.items()
                        if by_source.get(s, {}).get("counts_as_witness") and r.get("passed_effective")]
            witness_count = len(counting)
            shortfall = (E_v is not None) and (witness_count < E_v)
            if shortfall:
                book_shortfall += 1
            verses_out[locus] = {
                "book": book, "chapter": ch, "verse": v, "testament": testament,
                "grain": "verse", "E_v": E_v, "witness_count": witness_count,
                "counting_witnesses": sorted(counting),
                "archaic_ref_source": archaic_src.get(locus),
                "modern_ref_source": modern_src.get(locus),
                "shortfall_flag": bool(shortfall), "sources": sources,
            }
            for sid, r in sources.items():
                acc = book_src_scores.setdefault(sid, {"mod": [], "arch": []})
                if r.get("modern_id") is not None:
                    acc["mod"].append(r["modern_id"])
                if r.get("archaic_id") is not None:
                    acc["arch"].append(r["archaic_id"])

        # ---- chapter rollups (display grain) ----
        n_chapters = binfo["chapters"]
        for ch in range(1, n_chapters + 1):
            ch_loci = [k for k in loci if cv(k)[0] == ch]
            if not ch_loci:
                continue
            clocus = f"scripture/{book}/{ch}"
            n_verses = len(ch_loci)
            per_src: dict[str, Any] = {}
            src_ids = set()
            for k in ch_loci:
                src_ids |= set(verses_out[k]["sources"].keys())
            for sid in src_ids:
                mod: list[float] = []
                arch: list[float] = []
                gov: list[float] = []
                n_att = n_pass = 0
                kind = "scan"
                for k in ch_loci:
                    r = verses_out[k]["sources"].get(sid)
                    if not r:
                        continue
                    kind = r["kind"]
                    n_att += 1
                    if r.get("passed"):
                        n_pass += 1
                    if r.get("modern_id") is not None:
                        mod.append(r["modern_id"])
                    if r.get("archaic_id") is not None:
                        arch.append(r["archaic_id"])
                    g = r.get("archaic_id") if r.get("archaic_ref_exists") else r.get("modern_id")
                    if g is not None:
                        gov.append(g)
                per_src[sid] = {
                    "kind": kind, "n_attested": n_att, "n_passed": n_pass,
                    "pass_frac": round(n_pass / n_att, 4) if n_att else 0.0,
                    # chapter-pass rule (2026-07-10, Sir): a source passes a chapter iff it passes
                    # n >= (m-1) of the chapter's m verses -- a strict bar allowing at most one verse
                    # of error, coupling completeness (must attest >= m-1) with faithfulness. max(1,.)
                    # keeps a single-verse chapter from degenerately passing on zero passes.
                    "chapter_pass": n_pass >= max(1, n_verses - 1),
                    "mean_modern": _mean(mod), "mean_archaic": _mean(arch),
                    "mean_governing": _mean(gov),
                }
            # chapter witness_count = counts_as_witness sources that PASS the chapter (n >= m-1 verses)
            ch_witnesses = [s for s, d in per_src.items()
                            if by_source.get(s, {}).get("counts_as_witness")
                            and d["n_attested"] > 0
                            and d["chapter_pass"]]
            med_wc = int(st.median([verses_out[k]["witness_count"] for k in ch_loci]))
            chapters_out[clocus] = {
                "book": book, "chapter": ch, "testament": testament, "grain": "chapter",
                "E_v": E_v, "n_verses": n_verses,
                "median_verse_witness_count": med_wc,
                "verses_shortfall": sum(1 for k in ch_loci if verses_out[k]["shortfall_flag"]),
                "chapter_witness_count": len(ch_witnesses),
                "chapter_shortfall": (E_v is not None) and (len(ch_witnesses) < E_v),
                "sources": per_src,
            }
            if (E_v is not None) and (len(ch_witnesses) < E_v):
                localized_failed = sorted(
                    s for s, d in per_src.items()
                    if d["kind"] == "scan" and d["n_attested"] > 0 and not d["chapter_pass"])
                worklist.append({
                    "locus": clocus, "book": book, "chapter": ch, "grain": "chapter",
                    "E_v": E_v, "witness_count": len(ch_witnesses),
                    "missing": max(0, (E_v or 0) - len(ch_witnesses)),
                    "verses_shortfall": chapters_out[clocus]["verses_shortfall"],
                    "localized_but_failed": localized_failed,
                })

        # ---- book rollup ----
        n_verses_book = len(loci)
        book_src_roll: dict[str, Any] = {}
        for sid, acc in book_src_scores.items():
            n_att = sum(1 for k in loci if sid in verses_out[k]["sources"])
            n_pass = sum(1 for k in loci if verses_out[k]["sources"].get(sid, {}).get("passed"))
            book_src_roll[sid] = {
                "kind": by_source.get(sid, {}).get("kind", "?"),
                "n_attested": n_att, "n_passed": n_pass,
                "pass_frac": round(n_pass / n_att, 4) if n_att else 0.0,
                "mean_modern": _mean(acc["mod"]), "mean_archaic": _mean(acc["arch"]),
            }
        books_out[book] = {
            "slug": book, "testament": testament, "grain": "book", "E_v": E_v,
            "n_chapters": n_chapters, "n_verses": n_verses_book,
            "verses_shortfall": book_shortfall,
            "verses_meet_ev": n_verses_book - book_shortfall,
            "sources": book_src_roll,
        }

    scored = len(verses_out)
    shortfalls = sum(1 for c in verses_out.values() if c["shortfall_flag"])
    # §1.4 scoped re-OCR routing rollup across scan records
    routing_counts = {"scan_records": 0, "reocr_fire": 0, "needs_in_family_reference": 0,
                      "needs_reference": 0, "modern_yardstick_invalid": 0, "suspected_long_s_as_f": 0}
    for vd in verses_out.values():
        for r in vd["sources"].values():
            if r.get("kind") != "scan":
                continue
            routing_counts["scan_records"] += 1
            rt = r.get("routing", {})
            gi = rt.get("governing_instrument")
            if rt.get("reocr_fire"):
                routing_counts["reocr_fire"] += 1
            if gi == "needs-in-family-reference":
                routing_counts["needs_in_family_reference"] += 1
            if gi == "needs-reference":
                routing_counts["needs_reference"] += 1
            if not rt.get("modern_yardstick_valid", True):
                routing_counts["modern_yardstick_invalid"] += 1
            if r.get("suspected_long_s_as_f"):
                routing_counts["suspected_long_s_as_f"] += 1
    out = {
        "_doc": "Locus×source double-bind coverage audit (QC contract authority), ARCHAIC-PREEMINENT, "
                "VERSE grain. FORWARD = localize + char-identity pass under the governing gate (archaic "
                "where a ref exists, else modern); BACKWARD = witness_count vs E(v). Verse records are the "
                "authority; chapter/book rollups are for reporting. Supersedes the chapter-grain baseline.",
        "phase": "P3-verse-archaic-preeminent-routed",
        "grain": "verse",
        "gating": "archaic-preeminent + §1.4 scoped re-OCR routing",
        "scope_books": books,
        "E_v_source": "source-index.json loci_ev.scripture_books[*].E_v (verse inherits book E_v)",
        "reference_construction": {
            "archaic": "s_dismas[locus] else odr_com[locus] (s_dismas preeminent)",
            "modern": "sabates_a[locus] else madueke_b[locus] (FIXED: madueke_b, not the madueke_a "
                      "localization-aid used by the prior chapter-grain baseline)",
        },
        "identity_bar": {"threshold": CI.THRESHOLD,
                         "metric": "char-level normalized Levenshtein (edit_ratio = 1 - editdist/max(len)) "
                                   "on folded streams; difflib ratio retained only as a <0.80 skip-prefilter",
                         "archaic_rule_signal": "long_s_rule.rule_pass (auxiliary; gate where no archaic ref)"},
        "summary": {"verses_scored": scored, "verses_shortfall": shortfalls,
                    "chapters_rolled": len(chapters_out), "books": len(books_out),
                    "source_defects": len(source_defects),
                    "source_defects_open": sum(1 for d in source_defects if d["status"].startswith("OPEN"))},
        "scoped_reocr_routing": {
            "_doc": "§1.4: archaic (in-edition) gate is the quality bar; the modern gate governs only where "
                    "it is a VALID yardstick (floor_modern >= 0.90 and book not chronically divergent). Per "
                    "scan record: routing.governing_instrument, modern_is_signal, modern_yardstick_valid, "
                    "reocr_fire, suspected_long_s_as_f. passed = forward identity verdict (archaic-preeminent); "
                    "passed_effective = backward-gate-valid pass (excludes modern passes on an invalid "
                    "yardstick) and is what witness_count counts. No modern pass is silently accepted.",
            "chronic_divergent_books": sorted(CHRONIC_DIVERGENT),
            "counts": routing_counts,
        },
        "verses": verses_out,
        "chapters": chapters_out,
        "books": books_out,
        "reocr_worklist": worklist,
        "source_defects": source_defects,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    # ---- console report ----
    print(f"=== QC COVERAGE AUDIT (ARCHAIC-PREEMINENT, VERSE grain) — books: {', '.join(books)} ===\n")
    for book in books:
        b = books_out.get(book)
        if not b:
            continue
        print(f"  {book:<12} E(v)={b['E_v']}  verses={b['n_verses']:>4}  "
              f"meet_E(v)={b['verses_meet_ev']:>4}  shortfall={b['verses_shortfall']:>4}")
        scans = [(s, d) for s, d in b["sources"].items() if d["kind"] == "scan"]
        for sid, d in sorted(scans, key=lambda x: -(x[1]["mean_archaic"] or x[1]["mean_modern"] or 0)):
            print(f"       {sid:<5} attested={d['n_attested']:>4} passed={d['n_passed']:>4} "
                  f"mod={d['mean_modern']} arc={d['mean_archaic']}")
    print(f"\nverses scored: {scored}  |  verse shortfalls: {shortfalls}  |  worklist: {len(worklist)}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
