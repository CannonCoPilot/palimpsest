#!/usr/bin/env python3
"""consensus_v2.py -- accreting multi-witness consensus OCR with MSA conservation confidence.

Per Sir's directive (2026-07-07):
  * ALL transcribed witnesses stay IN the alignment/correction mix (none held out):
    sabates_a(Janvier), madueke_a, madueke_b, s_dismas, odr_com.
  * Confidence = sequence conservation across the multiple alignment (how clean the
    agreement / how messy the disagreement), NOT an independent validation.
  * TWO-LAYER output per token: a modern-spelling reading and an archaic/diplomatic
    (long-s preserving) reading.
  * Convergence gates (used as refinement targets, witnesses NOT held out):
      modern_match%  = token similarity of the modern layer vs sabates_a (Janvier)
      archaic_match% = token similarity of the archaic layer vs s_dismas
    Target: both >= 0.90 on the refined anchors.

Reuses detect_our_ocr primitives (Stream/anchor/locate). Loads EVERY scan source that
covers a book (coverage-gated), keeps them all separate, and fuses them column-by-column
with the text witnesses.

Run:  core/.venv/bin/python consensus_v2.py --book genesis --chapters 1
      core/.venv/bin/python consensus_v2.py --book psalms  --chapters 1,2,3
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/"
             "mask_engine/originaldr_reconstruction")
sys.path.insert(0, str(RECON))
import detect_our_ocr as D  # noqa: E402  # type: ignore[import-not-found]
import curated_sources as CS  # noqa: E402  # REP-1 allowlist -- this module is named in it as a MUST-filter
sys.path.insert(0, str(Path(__file__).resolve().parent / "witness"))
import witnesses as W  # noqa: E402  # Gate 0f verse scope, keyed on the WITNESS not the directory name

# Sources dropped before fusion, with the reason. Recorded and printed: a source that merely
# failed to appear would be indistinguishable from one with no data (R1.4).
_EXCLUDED_STREAMS: dict[str, str] = {}

UPSCALE = getattr(D, "UPSCALE", 2)
# COVER_FLOOR (book-level source gate) REMOVED per QC contract (Sir 2026-07-08, plan §Part 3).
# There is NO book-level accept/reject anywhere. A source contributes to a book iff it contributes
# individual VERSES that each clear the per-verse gate (extract_source_verses -> ATTEST_THRESHOLD);
# a book present-but-mangled keeps whatever verses it can attest instead of being laundered to zero.
# Presence/absence of a book in a source is decided by the source-index (ought-to-contain) + the
# backward E(v) gate in qc_audit — never by a mid-chapter recall floor here. (guard_no_book_gates.py)

# All transcribed witnesses stay in the mix. sabates_a = modern baseline; s_dismas = archaic
# baseline. madueke_b appended once ingested (harness tolerates its absence).
TEXT_WITNESSES = ["sabates_a", "madueke_a", "madueke_b", "s_dismas", "odr_com"]
MODERN_REF = "sabates_a"    # Janvier: current-best modern reading (convergence target, not GT)
ARCHAIC_REF = "s_dismas"    # diplomatic long-s reading (convergence target, not GT)

ARCHAIC_MARKERS = ("ſ", "æ", "œ", "ꝓ", "⁊", "ꝫ")
_MODERNIZE = {"ſ": "s", "æ": "ae", "œ": "oe", "⁊": "and", "ꝫ": "us"}


# --------------------------------------------------------------------------- #
# folding / tokenizing
# --------------------------------------------------------------------------- #
def fold_tok(text: str) -> list[str]:
    """Aggressive modern fold for VOTING + modern-similarity (glyph/uv/ij agnostic)."""
    t = (text.lower().replace("ſ", "s").replace("æ", "ae").replace("œ", "oe")
         .replace("⁊", "and").replace("ꝫ", "us").replace("v", "u").replace("j", "i"))
    return re.findall(r"[a-z]+", t)


def fold1(word: str) -> str:
    f = fold_tok(word)
    return f[0] if f else ""


def archaic_tok(text: str) -> list[str]:
    """Fold for ARCHAIC-layer similarity vs s_dismas. Keeps ſ/æ/œ (the meaningful archaic-spelling
    signal) but folds vv->w and u/v, i/j: these are positional TYPOGRAPHY in early-modern print
    (compositors set u/v and i/j by position, not phoneme; vv is a w ligature), i.e. glyph noise,
    not spelling differences. Mirrors the modern fold's u/v/i/j collapse so the archaic metric is
    not penalised for typography that the modern metric already ignores. Metric-only (the archaic
    OUTPUT surface is built separately and still preserves ſ/v/j verbatim)."""
    t = text.lower().replace("vv", "w").replace("v", "u").replace("j", "i")
    return re.findall(r"[a-zſæœ]+", t)


def modernize(word: str) -> str:
    out = word
    for k, v in _MODERNIZE.items():
        out = out.replace(k, v)
    return out


def archaic_score(w: str) -> int:
    return sum(w.count(c) for c in ARCHAIC_MARKERS)


def sim(a_tokens: list[str], b_tokens: list[str]) -> float:
    if not a_tokens and not b_tokens:
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    return difflib.SequenceMatcher(a=a_tokens, b=b_tokens, autojunk=False).ratio()


# --------------------------------------------------------------------------- #
# witness surfaces (text scaffold) from reads/<src>.json
# --------------------------------------------------------------------------- #
def load_reads_surfaces(name: str) -> dict[str, str]:
    p = D.READS_DIR / f"{name}.json"
    out: dict[str, str] = {}
    if not p.exists():
        return out
    for r in json.loads(p.read_text()).get("reads", []):
        sk = r.get("skeleton_id", "")
        if sk.startswith("scripture/"):
            out[sk] = r.get("surface", "")
    return out


def ref_chapter_tokens(name: str, book: str, ch: int, fold_fn,
                       text_surf: dict[str, dict[str, str]]) -> list[str]:
    """All of witness `name`'s verses for one chapter, in verse order, folded to a token stream.
    Compared as a CONCATENATED chapter (not per-verse-by-coord) so that a witness with a different
    verse division (s_dismas/odr_com diverge from the skeleton) still scores on textual agreement."""
    prefix = f"scripture/{book}/{ch}/"
    items: list[tuple[int, str]] = []
    for k, s in text_surf.get(name, {}).items():
        if k.startswith(prefix):
            try:
                items.append((int(k.rsplit("/", 1)[1]), s))
            except ValueError:
                continue
    toks: list[str] = []
    for _, s in sorted(items):
        toks += fold_fn(s)
    return toks


# --------------------------------------------------------------------------- #
# per-source scan verse extraction (chapter-level global alignment; from proven spike)
# --------------------------------------------------------------------------- #
def extract_source_verses(book: str, chapters: dict[int, dict[int, str]],
                          st) -> dict[tuple[int, int], tuple[str, float]]:
    folded, raw = st.fold, st.raw
    out: dict[tuple[int, int], tuple[str, float]] = {}
    cursor = 0
    maxch = D._BOOK_CH.get(book, 0)
    for ch in sorted(chapters):
        if maxch and ch > maxch:
            continue
        verses = chapters[ch]
        vlist = sorted(verses)
        ref: list[str] = []
        bounds: list[tuple[int, int]] = []
        for v in vlist:
            bounds.append((v, len(ref)))
            ref.extend(fold_tok(verses[v]))
        bounds.append((-1, len(ref)))
        if not ref:
            continue
        _, a, b = D.locate_region(D._probe(" ".join(verses[v] for v in vlist)), folded, cursor)
        ca = max(0, a - D.CHAP_PAD)
        cb = min(len(folded), b + D.CHAP_PAD)
        cursor = a
        scan = folded[ca:cb]
        ref2scan: dict[int, int] = {}
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                a=ref, b=scan, autojunk=False).get_opcodes():
            if tag in ("equal", "replace"):
                for k in range(min(i2 - i1, j2 - j1)):
                    ref2scan[i1 + k] = j1 + k

        def scan_at(ref_idx: int, default: int) -> int:
            for r in range(ref_idx, len(ref) + 1):
                if r in ref2scan:
                    return ref2scan[r]
            return default

        for i, (v, rstart) in enumerate(bounds[:-1]):
            rend = bounds[i + 1][1]
            s0 = scan_at(rstart, 0)
            s1 = scan_at(rend, len(scan))
            if s1 <= s0:
                s1 = min(len(scan), s0 + (rend - rstart))
            surface = " ".join(raw[ca + s0:ca + s1]).strip()
            vset = set(fold_tok(verses[v]))
            got = set(scan[s0:s1])
            rec = len(vset & got) / len(vset) if vset else 0.0
            if surface and rec >= D.ATTEST_THRESHOLD:
                out[(ch, v)] = (surface, round(rec, 3))
    return out


def book_coverage(chapters: dict[int, dict[int, str]], st) -> float:
    chs = sorted(chapters)
    if not chs or not st.fold:
        return 0.0
    mid = chs[len(chs) // 2]
    probe = D._probe(" ".join(chapters[mid][v] for v in sorted(chapters[mid])))
    if not probe:
        return 0.0
    r, _, _ = D.locate_region(probe, st.fold)
    return round(r, 3)


# --------------------------------------------------------------------------- #
# alignment to the anchor frame
# --------------------------------------------------------------------------- #
def align_to_anchor(anchor_folds: list[str], surface: str) -> list[str | None]:
    wtoks = surface.split()
    wfolds = [fold1(w) for w in wtoks]
    res: list[str | None] = [None] * len(anchor_folds)
    sm = difflib.SequenceMatcher(a=anchor_folds, b=wfolds, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("equal", "replace"):
            for k in range(min(i2 - i1, j2 - j1)):
                res[i1 + k] = wtoks[j1 + k]
    return res


# --------------------------------------------------------------------------- #
# conservation / messiness (MSA column statistics)
# --------------------------------------------------------------------------- #
def conservation(folded_symbols: list[str]) -> dict:
    """folded_symbols: one per witness at a column; '-' = gap (witness missing this token).
    Returns bounded messiness/agreement stats in MSA-conservation terms."""
    n = len(folded_symbols)
    if n == 0:
        return {"n": 0, "distinct": 0, "agreement": 0.0, "entropy_norm": 1.0,
                "conservation": 0.0, "ic_bits": 0.0, "consensus_fold": ""}
    counts = Counter(folded_symbols)
    top, topn = counts.most_common(1)[0]
    H = -sum((c / n) * math.log2(c / n) for c in counts.values())
    Hmax = math.log2(n) if n > 1 else 0.0
    entropy_norm = (H / Hmax) if Hmax > 0 else 0.0
    return {
        "n": n, "distinct": len(counts),
        "agreement": round(topn / n, 3),          # plurality fraction
        "entropy_norm": round(entropy_norm, 3),    # 0=clean agreement, 1=maximal mess
        "conservation": round(1 - entropy_norm, 3),
        "ic_bits": round(Hmax - H, 3),             # information content (bits), sequence-logo style
        "consensus_fold": top,
    }


# --------------------------------------------------------------------------- #
# two-layer consensus over the anchor frame
# --------------------------------------------------------------------------- #
def consensus(anchor_text: str, scan_wit: list[tuple[str, str]],
              text_wit: list[tuple[str, str]]) -> dict:
    """Fuse all witnesses column-by-column. Returns modern reading, archaic reading,
    per-token columns with conservation, and the aligned witness matrix."""
    anchor_folds = fold_tok(anchor_text)
    all_wit = scan_wit + text_wit
    modern_labels = {lab for lab, _ in text_wit}  # text witnesses provide modern surfaces
    aligned = {lab: align_to_anchor(anchor_folds, surf) for lab, surf in all_wit}

    modern_out: list[str] = []
    archaic_out: list[str] = []
    cols: list[dict] = []
    for i, af in enumerate(anchor_folds):
        # collect per-witness surface at this column (bind non-None so types narrow)
        present: list[tuple[str, str]] = []
        for lab in aligned:
            w = aligned[lab][i]
            if w:
                present.append((lab, w))
        symbols = [fold1(w) or "-" for _, w in present]
        # pad gaps for witnesses that had no token here (so absence registers as mess)
        gaps = ["-"] * (len(all_wit) - len(present))
        cons = conservation(symbols + gaps)
        win_fold = cons["consensus_fold"]

        winners = [(lab, w) for lab, w in present if fold1(w) == win_fold]
        if winners:
            # archaic layer: most long-s-rich surface among fold-winners
            arch = max(winners, key=lambda lw: archaic_score(lw[1]))[1]
            # modern layer: prefer a text-witness (modern) surface among winners, else modernize
            modern_pick = next((w for lab, w in winners if lab in modern_labels), None)
            modern = modernize(modern_pick if modern_pick is not None else arch)
        else:
            arch, modern = af, af
        modern_out.append(modern)
        archaic_out.append(arch)
        cols.append({
            "fold": win_fold, "modern": modern, "archaic": arch,
            "agreement": cons["agreement"], "conservation": cons["conservation"],
            "ic_bits": cons["ic_bits"], "n": cons["n"], "distinct": cons["distinct"],
        })
    return {
        "modern_reading": " ".join(modern_out),
        "archaic_reading": " ".join(archaic_out),
        "columns": cols,
        "mean_conservation": round(sum(c["conservation"] for c in cols) / len(cols), 3) if cols else 0.0,
        "mean_agreement": round(sum(c["agreement"] for c in cols) / len(cols), 3) if cols else 0.0,
    }


# --------------------------------------------------------------------------- #
# module-level caches: load streams / text witnesses / anchor ONCE, reuse across all books
# --------------------------------------------------------------------------- #
_STREAMS: dict | None = None
_TEXT_SURF: dict[str, dict[str, str]] | None = None
_ANCHOR: dict | None = None
_STRIP_PREFIXES = ("archive-", "eebo-", "pdf-", "jp2-")
# a jp2-<key> re-OCR supersedes its low-res twin only once it is >= this fraction as complete
_SUPERSEDE_MIN_FRACTION = 0.98


def _dir_key(name: str) -> str:
    """Strip a line-prefix (archive-/eebo-/pdf-/jp2-) to the bare source key."""
    for pfx in _STRIP_PREFIXES:
        if name.startswith(pfx):
            return name[len(pfx):]
    return name


def load_all_streams() -> dict:
    """Fold every OCR'd scan source under DIPL_ROOT ONCE (whole-Bible driver reuses this).

    A jp2-<key> re-OCR (hi-res master) SUPERSEDES its lower-res twin (pdf-/eebo-/archive-<key>)
    of the SAME physical copy, so one copy is never double-counted as two witnesses. The
    supersession is COMPLETION-GATED: the jp2 dir must hold >= _SUPERSEDE_MIN_FRACTION of the
    twin's page count, so an in-progress jp2 re-OCR never evicts a full twin and drops coverage.
    """
    global _STREAMS
    if _STREAMS is not None:
        return _STREAMS
    dirs = [d for d in sorted(D.DIPL_ROOT.glob("*")) if d.is_dir()]
    pages = {d.name: sum(1 for p in d.glob("*.json") if not p.name.startswith("_")) for d in dirs}
    jp2_pages = {d.name[len("jp2-"):]: pages[d.name] for d in dirs if d.name.startswith("jp2-")}
    superseded = {
        d.name for d in dirs
        if not d.name.startswith("jp2-")
        and _dir_key(d.name) in jp2_pages
        and pages[d.name] > 0
        and jp2_pages[_dir_key(d.name)] >= _SUPERSEDE_MIN_FRACTION * pages[d.name]
    }
    streams = {}
    for d in dirs:
        if d.name in superseded:
            continue
        # R9.4b — TWO gates this glob never had, and it is a GLOB, which is precisely the
        # re-entry route `curated_sources` was written to close ("a banned folder can never
        # re-enter by a directory glob"). This module is named in that file as a builder that
        # MUST filter, and it did not import it at all: `consensus-full/matthew.json` records
        # `scan_sources` including **eebo-nt** and **eebo-vol1**, which are S10-S15, BANNED.
        #
        # The supersession above is the same idea reached by a route that cannot see far
        # enough: it de-duplicates a jp2 re-OCR against its pdf/eebo/archive twin OF THE SAME
        # COPY, keyed on the FILENAME. `X` (jp2-S08) and `B` (pdf-S09nt) are the same copy under
        # two unrelated keys, so the key test cannot express the relation and X entered as an
        # independent seventh witness. A filter cannot enforce a distinction it cannot state --
        # which is why the scope gate is keyed on the WITNESS, not on the directory name.
        # The reason is graded, because a BAN and an ABSENCE FROM THE ALLOWLIST are different
        # claims and this module was making the stronger one about both. `curated_sources` warns
        # about exactly this in its own note on `jp2-S06`: reading a curated folder as BANNED is
        # "a false accusation, not a stricter gate". `is_curated()` returns False for a banned
        # source AND for a directory it simply does not know, so it cannot tell them apart --
        # the ban must be read from `BANNED_OCR_DIRS`, which states it.
        why = None
        if d.name in CS.BANNED_OCR_DIRS:
            why = "BANNED (REP-1): S2/S5/S7/S10-S15 or a derivative"
        elif not CS.is_curated(d.name):
            # NOT a ban. Two live cases land here and both need adjudicating, not assuming:
            # `.jp2-S06-divider` (the blank leaf in neither setting, set aside by R7.5a -- a
            # deliberate non-source) and `pdf-S06` (curated S6 material whose directory the
            # registry does not know: the UNSPLIT whole-file PDF spanning both settings, the
            # same ambiguity R7.5a resolved for the jp2 and has not yet resolved here).
            why = ("not in the curated allowlist -- NOT a ban: either a deliberate non-source or "
                   "curated material whose directory is unregistered (see R7.5a)")
        else:
            try:
                if not W.verse_admitted(d.name):
                    vol, sig = W.witness_of(d.name)
                    why = (f"{W.wid(vol, sig)} role={W.WITNESSES[(vol, sig)]['role']} "
                           f"-> verse_scope 'none' (Gate 0f)")
            except KeyError:
                why = ("curated acquisition but UNADDRESSABLE: the id names a file, not a witness "
                       "(R7.5a) -- it cannot be scoped, so it cannot be admitted")
        if why:
            _EXCLUDED_STREAMS[d.name] = why
            continue
        st = D.load_stream(d, _dir_key(d.name), UPSCALE)
        if getattr(st, "n_body_lines", 0) > 0:
            streams[d.name] = st
    if _EXCLUDED_STREAMS:
        print(f"[consensus] EXCLUDED {len(_EXCLUDED_STREAMS)} source(s) before fusion:", flush=True)
        for k, v in sorted(_EXCLUDED_STREAMS.items()):
            print(f"[consensus]   {k:20} {v}", flush=True)
    _STREAMS = streams
    return streams


def text_surfaces() -> dict[str, dict[str, str]]:
    global _TEXT_SURF
    if _TEXT_SURF is None:
        _TEXT_SURF = {w: load_reads_surfaces(w) for w in TEXT_WITNESSES}
    return _TEXT_SURF


def anchor_all() -> dict:
    global _ANCHOR
    if _ANCHOR is None:
        _ANCHOR = dict(D.anchor_by_book(D.load_anchor()))
    return _ANCHOR


def load_scan_sources(chapters: dict[int, dict[int, str]]):
    """Return ALL cached scan streams + their recorded mid-chapter coverage recall.
    NO book-level gate: every source is offered to every book; the per-verse ATTEST gate inside
    extract_source_verses decides contribution. `cov` is a RECORDED signal (reporting + backward
    E(v) visibility), never a filter."""
    streams = load_all_streams()
    cov = {sid: book_coverage(chapters, st) for sid, st in streams.items()}
    return streams, cov


def _mean(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def run_book(book: str, want_ch: set[int] | None = None,
             keep_columns: bool = True) -> tuple[dict, list]:
    """Fuse ALL witnesses for one book -> (summary, per-verse records). want_ch=None => all."""
    anchor = anchor_all().get(book, {})
    chapters = {ch: vs for ch, vs in anchor.items() if (want_ch is None or ch in want_ch)}
    if not chapters:
        return {"book": book, "verses_scored": 0, "error": "no anchor text"}, []

    streams, cov = load_scan_sources(chapters)
    scan_verses: dict[str, dict] = {}
    for sid in streams:  # every source attempts every book; per-verse ATTEST gate self-selects
        ext = extract_source_verses(book, chapters, streams[sid])
        if ext:
            scan_verses[sid] = ext

    text_surf = text_surfaces()
    present_text = [w for w in TEXT_WITNESSES if text_surf[w]]

    records = []
    conservs: list[float] = []
    ch_con_mod: dict[int, list[str]] = {}
    ch_con_arch: dict[int, list[str]] = {}
    for ch in sorted(chapters):
        for v in sorted(chapters[ch]):
            sk = f"scripture/{book}/{ch}/{v}"
            anchor_text = chapters[ch][v]
            scan_wit = [(sid, scan_verses[sid][(ch, v)][0])
                        for sid in scan_verses if (ch, v) in scan_verses[sid]]
            text_wit = [(w, text_surf[w][sk]) for w in present_text if sk in text_surf[w]]
            if not scan_wit and not text_wit:
                continue
            con = consensus(anchor_text, scan_wit, text_wit)

            # Accrue this verse's consensus into its chapter's concatenated token stream.
            # The convergence metric is computed per-CHAPTER (numbering-agnostic) below,
            # since s_dismas/odr_com use a verse division that diverges from the skeleton
            # (e.g. s_dismas splits Gen 1:25 -> +1 shift), which made a verse-N-vs-verse-N
            # comparison score non-corresponding verses against each other.
            ch_con_mod.setdefault(ch, []).extend(fold_tok(con["modern_reading"]))
            ch_con_arch.setdefault(ch, []).extend(archaic_tok(con["archaic_reading"]))
            conservs.append(con["mean_conservation"])

            rec = {
                "coord": sk, "anchor": anchor_text,
                "n_scan": len(scan_wit), "n_text": len(text_wit),
                "modern_reading": con["modern_reading"],
                "archaic_reading": con["archaic_reading"],
                "mean_conservation": con["mean_conservation"],
                "mean_agreement": con["mean_agreement"],
                "diplomatic_layer": {sid: s for sid, s in scan_wit},
            }
            if keep_columns:
                rec["columns"] = con["columns"]
            records.append(rec)

    # Chapter-level convergence: compare each chapter's concatenated consensus stream
    # against the reference witness's concatenated chapter stream (order-aware,
    # numbering-agnostic). modern layer folds with fold_tok vs MODERN_REF; archaic layer
    # folds with archaic_tok (long-s preserving) vs ARCHAIC_REF.
    per_chapter_match: dict[str, dict] = {}
    mod_sims, arch_sims = [], []
    for ch in sorted(ch_con_mod):
        mref_toks = ref_chapter_tokens(MODERN_REF, book, ch, fold_tok, text_surf)
        aref_toks = ref_chapter_tokens(ARCHAIC_REF, book, ch, archaic_tok, text_surf)
        mod_sim = sim(ch_con_mod[ch], mref_toks) if mref_toks else None
        arch_sim = sim(ch_con_arch.get(ch, []), aref_toks) if aref_toks else None
        if mod_sim is not None:
            mod_sims.append(mod_sim)
        if arch_sim is not None:
            arch_sims.append(arch_sim)
        per_chapter_match[str(ch)] = {
            "modern": round(mod_sim, 4) if mod_sim is not None else None,
            "archaic": round(arch_sim, 4) if arch_sim is not None else None,
        }

    summary = {
        "book": book, "chapters": sorted(chapters),
        "scan_sources": sorted(scan_verses), "text_witnesses": present_text,
        "coverage_recall": {k: cov[k] for k in sorted(cov)},  # ALL sources recorded (backward-gate)
        "modern_ref": MODERN_REF, "archaic_ref": ARCHAIC_REF,
        "verses_scored": len(records),
        "modern_match_mean": _mean(mod_sims), "archaic_match_mean": _mean(arch_sims),
        "per_chapter_match": per_chapter_match,
        "mean_conservation": _mean(conservs),
        "gate_modern_0.90": (_mean(mod_sims) or 0) >= 0.90,
        "gate_archaic_0.90": (_mean(arch_sims) or 0) >= 0.90,
    }
    return summary, records


def run_all(out_dir: Path) -> int:
    """Whole-Bible driver: every book in skeleton order, RESUMABLE (skips written books)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    books = D._BOOK_ORDER
    load_all_streams()  # warm the stream cache once for the whole run
    manifest = []
    for i, book in enumerate(books, 1):
        bp = out_dir / f"{book}.json"
        if bp.exists():
            s = json.loads(bp.read_text()).get("summary", {})
            manifest.append(s)
            print(f"[{i:2d}/{len(books)}] {book:22s} CACHED "
                  f"mod={s.get('modern_match_mean')} arch={s.get('archaic_match_mean')}", flush=True)
            continue
        summary, records = run_book(book, None, keep_columns=True)
        bp.write_text(json.dumps({"summary": summary, "verses": records},
                                 ensure_ascii=False, indent=2))
        manifest.append(summary)
        print(f"[{i:2d}/{len(books)}] {book:22s} v={summary.get('verses_scored'):>4} "
              f"src={len(summary.get('scan_sources', []))} "
              f"mod={summary.get('modern_match_mean')} arch={summary.get('archaic_match_mean')} "
              f"cons={summary.get('mean_conservation')}", flush=True)
    (out_dir / "_summary.json").write_text(json.dumps({
        "books": manifest,
        "modern_match_overall": _mean([m.get("modern_match_mean") for m in manifest]),
        "archaic_match_overall": _mean([m.get("archaic_match_mean") for m in manifest]),
        "mean_conservation_overall": _mean([m.get("mean_conservation") for m in manifest]),
        "total_verses": sum(m.get("verses_scored", 0) for m in manifest),
    }, ensure_ascii=False, indent=2))
    print("\nwrote", out_dir / "_summary.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="genesis")
    ap.add_argument("--chapters", default="1", help="comma list e.g. 1,2 ; or 'all'")
    ap.add_argument("--all", action="store_true", help="run EVERY book in skeleton order")
    ap.add_argument("--out", default=str(Path(__file__).with_name("consensus-v2.json")))
    args = ap.parse_args()

    if args.all:
        return run_all(Path(args.out).with_name("consensus-full"))

    want_ch = None if args.chapters == "all" else {int(c) for c in args.chapters.split(",")}
    summary, records = run_book(args.book, want_ch)
    Path(args.out).write_text(json.dumps({"summary": summary, "verses": records},
                                         ensure_ascii=False, indent=2))
    print("\n===== CONSENSUS v2: %s ch%s =====" % (args.book, args.chapters))
    print("scan sources :", summary.get("scan_sources"))
    print("text witness :", summary.get("text_witnesses"))
    print("verses scored:", summary.get("verses_scored"))
    print("modern  match vs %-9s : %s  (gate>=0.90: %s)"
          % (MODERN_REF, summary.get("modern_match_mean"), summary.get("gate_modern_0.90")))
    print("archaic match vs %-9s : %s  (gate>=0.90: %s)"
          % (ARCHAIC_REF, summary.get("archaic_match_mean"), summary.get("gate_archaic_0.90")))
    print("mean conservation (0..1) :", summary.get("mean_conservation"))
    if records:
        r = records[0]
        print("\nsample:", r["coord"], "| n_scan=%d n_text=%d" % (r["n_scan"], r["n_text"]))
        print("  modern :", r["modern_reading"][:90])
        print("  archaic:", r["archaic_reading"][:90])
    print("\nwrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
