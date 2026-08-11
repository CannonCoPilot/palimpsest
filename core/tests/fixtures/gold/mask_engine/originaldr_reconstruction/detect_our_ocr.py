#!/usr/bin/env python3
"""Phase 4 · P4.1 — diplomatic-OCR archaic witness (region-typed, ſ-preserving).

Successor to ``detect_ocr_consensus.py``. Consumes the FRESH diplomatic OCR produced by
``ocr_pipeline.py`` (kraken + reichenau_lat), which natively preserves long-ſ — replacing the
stock-tesseract ``ocr_consensus`` witness whose ſ→f collapse fed the §6.2/§6.3 defect.

Two advances over ``detect_ocr_consensus`` (everything else is deliberately identical):
  1. DIPLOMATIC SURFACE — the stored ``surface`` is raw kraken text with ſ/æ/etc intact.
     The old witness stored tesseract ``eng`` text where the ENGINE had already lost ſ→f, so
     no downstream fold could recover it (spelling_glyph_model §6.1 forbids restoring ſ from a
     lossy inverse). This witness carries the glyph natively.
  2. REGION-TYPING — every OCR line carries a bbox, so each page is split into the scripture
     BODY column vs the marginal APPARATUS bands (marginalia-geometry.json §4.4). Scripture is
     attested against the modern anchor; the marginal text is captured as a first archaic
     apparatus witness instead of being blended into the verse token stream.

Anchoring is UNCHANGED from ``detect_ocr_consensus``: content-anchored attestation against the
modern anchor (madueke_a + sabates_a) using the shared SYMMETRIC ``ocr_sample.skel`` fold and a
monotone chapter cursor. We do NOT segment verses from scratch — the fold only LOCATES a verse;
the stored surface is always raw (diplomatic) OCR text sliced by the located window.

Processes ONE scan line at a time (its diplomatic-OCR output lives under
``sources/our-ocr-diplomatic/<line>-<alias>/``), emitting one reads file:

    detect_our_ocr.py archive  → reads/our_ocr_archive.json   (archive.org jp2 line)
    detect_our_ocr.py annas    → reads/our_ocr_annas.json     (annas EEBO pdf line)

The two lines are fused downstream (build_consensus / §6.4) for ≥2× archaic depth. This script
writes a NEW reads file and NEVER overwrites the existing ocr_consensus witness (HOLD per §11).

Run:  core/.venv/bin/python detect_our_ocr.py archive --no-wait   # dev against current pages
      core/.venv/bin/python detect_our_ocr.py archive             # gate on OCR completion
      core/.venv/bin/python detect_our_ocr.py archive --book isaie  # single book (debug)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # .../originaldr_reconstruction
MASK_ENGINE = HERE.parent
sys.path.insert(0, str(MASK_ENGINE))
sys.path.insert(0, str(MASK_ENGINE / "originaldr_validation"))

# shared archaic<->modern skeleton fold + windowing (same primitives detect_ocr_consensus uses).
from ocr_sample import skel, raw_words, best_window  # type: ignore[import]  # noqa: E402

# repo root: HERE.parents = [0]mask_engine [1]gold [2]fixtures [3]tests [4]core [5]<repo>
REPO = HERE.parents[5]
# The OCR project left gitignored scratch in `2633cbb` ("move OCR project out of gitignored
# scratch into projects/originaldr"). This constant was not moved with it, so every path below
# resolved into a directory that no longer exists -- and resolved SILENTLY, because the readers
# below guarded on `.exists()` and skipped. See R9.6: five further modules still restate this
# root, two of which `mkdir(parents=True)` and WRITE the anchor reads into the dead tree.
ORIGINALDR = REPO / "projects/originaldr"
DIPL_ROOT = ORIGINALDR / "sources/our-ocr-diplomatic"
READS_DIR = ORIGINALDR / "reconstruction/reads"

GEOM = json.loads((HERE / "marginalia-geometry.json").read_text())
SKELETON = json.loads((HERE / "skeleton.json").read_text())
_BOOK_CH = {b["slug"]: b["chapters"] for b in SKELETON["books"]}
_BOOK_ORDER = [b["slug"] for b in SKELETON["books"]]
_BOOK_TESTAMENT = {b["slug"]: b["testament"] for b in SKELETON["books"]}

MADUEKE_READS = READS_DIR / "madueke_a.json"
SABATES_READS = READS_DIR / "sabates_a.json"   # covers the 3 appendix books madueke lacks

# scan lines → the prefix of their per-alias diplomatic-OCR output dirs under DIPL_ROOT.
# The annas line's dirs are named eebo-<volkey> by ocr_pipeline.py (vol1..vol5, nt).
LINE_PREFIX = {"archive": "archive-", "annas": "eebo-"}


def is_nt_alias(alias: str) -> bool:
    """True if the alias names a New-Testament scan. Handles both bare aliases (nt, nt-1582,
    newtestament) and the real diplomatic-OCR dir names (archive-nt-1582, eebo-nt, pdf-S09nt)."""
    a = alias.lower()
    return (a == "nt" or a.startswith("nt-") or a.endswith("-nt") or a.endswith("nt")
            or "-nt-" in a or "newtestament" in a)

# region-typing geometry (§4.4). The three measured tomes carry exact bands; unmeasured aliases
# (holiebible-*, newtestament, EEBO) fall back to a shared default that generalises them well.
_GEOM_WIDTH = {k: v["page_width_px"] for k, v in GEOM["tomes"].items()}
_GEOM_BODY = {k: (v["text_column"]["x_lo"], v["text_column"]["x_hi"]) for k, v in GEOM["tomes"].items()}
DEFAULT_BODY = (0.11, 0.88)

# --- tunables (mirror detect_ocr_consensus; single-product so depth is 0/1) ---
ATTEST_THRESHOLD = 0.5     # folded type-recall in the located window to call a verse attested
# BOOK_ALIAS_FLOOR (book-level presence gate) REMOVED per QC contract (Sir 2026-07-08, plan §Part 3).
# resolve_alias now returns its best-scoring alias unconditionally; a book is NEVER dropped by a mid-
# chapter probe recall. Quality lives at the per-verse ATTEST_THRESHOLD gate above and the char-level
# identity gate in qc_audit; genuine absence is decided by the source-index (ought-to-contain) + the
# backward E(v) gate — not here. This is the gate that once laundered eebo-vol4 Psalms to 0-located.
# (enforced by guard_no_book_gates.py)
NEIGHBOURHOOD = 1200       # fallback chapter-window width when a chapter has no probe tokens
CHAP_PAD = 400             # tokens padded either side of a located chapter window
MANIFEST_POLL_S = 30
MANIFEST_MAX_WAIT_S = 16 * 3600   # the full diplomatic run is multi-hour

# archaic-gap OT books: OCR is their SOLE archaic corroboration (no s-dismas / odr-com coverage).
ARCHAIC_GAP_OT = ["ecclesiasticus", "isaie", "jeremie", "ezechiel", "osee", "joel", "amos",
                  "abdias", "micheas", "nahum", "habacuc", "aggeus", "zacharias", "malachie"]

_WORD_RE = re.compile(r"[A-Za-zÆæŒœſ]+")   # include long-ſ so raw surfaces keep the glyph
_PAGENUM = re.compile(r"_(\d+)$")

# Inline apparatus markers: Rheims marginal-note keys printed INSIDE the body column as "(n) ...".
# They sit within the geometry body band (x-centre ~0.42-0.51 on eebo-vol4) so a purely geometric mask
# cannot separate them; folded into the verse stream they interleave BETWEEN verses and split each
# chapter's verse span (the eebo-vol4 Psalms 0-located failure). A CONTENT signal atop the geometry mask:
# a verse line starts with a verse NUMBER, an inline annotation starts with a single parenthetical letter
# key. Specific enough that scripture never matches (verses do not begin "(n) ").
_INLINE_ANNOT = re.compile(r"^\s*\(?[a-zſ]\)\s+\S")


def _is_inline_annotation(text: str) -> bool:
    """True if a body-band line is an inline apparatus/annotation line (single parenthetical letter key at
    line start, e.g. '(n) The whole Church...'), NOT scripture. Routed to the apparatus stream so the
    verse fold stays contiguous. Verse lines start with a verse number and never match."""
    return bool(_INLINE_ANNOT.match(text))


# ------------------------------------------------------------------ #
# Anchor (expected modern text per skeleton coordinate) — identical to detect_ocr_consensus
# ------------------------------------------------------------------ #
def load_anchor() -> dict[str, str]:
    anchor: dict[str, str] = {}
    missing = [p for p in (SABATES_READS, MADUEKE_READS) if not p.exists()]
    if missing:
        # This was `continue`, and the skip is how the `2633cbb` migration stayed invisible:
        # with both reads gone the anchor came back EMPTY, `run_book` reported the well-formed
        # summary `{"verses_scored": 0, "error": "no anchor text"}` for every book, and a
        # `--all` regeneration would have written 77 empty files over `consensus-full/`.
        # An absent anchor is not an anchor with no verses in it (R1.4).
        raise FileNotFoundError(
            "anchor reads missing: " + ", ".join(str(p) for p in missing) +
            ". The anchor is the skeleton every book is scored against; without it every book "
            "scores zero verses, which is indistinguishable from a book that genuinely has no "
            "witness. Do not run a regeneration until this resolves. If the OCR project moved "
            "again, fix ORIGINALDR in this module (and see R9.6 for the modules that restate it)."
        )
    for path in (SABATES_READS, MADUEKE_READS):      # madueke last → wins on overlap
        blob = json.loads(path.read_text())
        for r in blob.get("reads", []):
            sk = r.get("skeleton_id", "")
            if sk.startswith("scripture/"):
                anchor[sk] = r.get("surface", "")
    return anchor


def anchor_by_book(anchor: dict[str, str]) -> dict[str, dict[int, dict[int, str]]]:
    out: dict[str, dict[int, dict[int, str]]] = defaultdict(lambda: defaultdict(dict))
    for sk, surf in anchor.items():
        parts = sk.split("/")
        if len(parts) != 4:
            continue
        _, book, ch, v = parts
        try:
            out[book][int(ch)][int(v)] = surf
        except ValueError:
            continue
    return out


# ------------------------------------------------------------------ #
# Region-typing: split each page's lines into body-scripture vs marginal-apparatus by
# normalised x-centre against the tome's measured column geometry (§4.4).
# ------------------------------------------------------------------ #
def _page_index(stem: str) -> int:
    m = _PAGENUM.search(stem)
    return int(m.group(1)) if m else 0


def _fold_words(text: str) -> tuple[list[str], list[str]]:
    """(folded_tokens, raw_words) index-aligned; drop tokens whose fold is <2 chars so window
    bounds line up with probe tokens (matches ocr_sample.sk_list's len>=2 filter)."""
    folded: list[str] = []
    kept: list[str] = []
    for w in _WORD_RE.findall(text):
        s = skel(w)
        if len(s) >= 2:
            folded.append(s)
            kept.append(w)
    return folded, kept


class Stream:
    """One scan alias, region-typed into an index-aligned body token stream plus the raw
    marginal words grouped by page (the apparatus capture)."""

    __slots__ = ("alias", "fold", "raw", "page", "margin_by_page", "n_pages",
                 "n_body_lines", "n_margin_lines", "n_inline_annot_lines", "long_s")

    def __init__(self, alias: str):
        self.alias = alias
        self.fold: list[str] = []           # folded body tokens (for anchoring)
        self.raw: list[str] = []            # index-aligned raw body words (diplomatic surface)
        self.page: list[str] = []           # index-aligned page id per body token
        self.margin_by_page: dict[str, list[str]] = defaultdict(list)
        self.n_pages = 0
        self.n_body_lines = 0
        self.n_margin_lines = 0
        self.n_inline_annot_lines = 0       # body-band lines rerouted to apparatus by the content signal
        self.long_s = 0                     # ſ count across all raw text (diplomatic-health probe)


def _reading_order(body_lines: "list[tuple[int, int, float, str]]") -> list[str]:
    """Order one page's body lines (y_top, x_left, x_centre, text) for sequential reading.

    A single global (y_top, x_left) sort INTERLEAVES the two text columns of a poetic/columnar
    page (L1,R1,L2,R2,...), scrambling reading order and defeating the downstream verse locate.
    Detect a two-column page by a wide vertical gutter in the line x-centres; when found, read the
    LEFT column fully (top->bottom) then the RIGHT column. Otherwise fall back to the plain sort,
    so ordinary single-column pages are untouched (no regression)."""
    if len(body_lines) < 6:
        return [t for _, _, _, t in sorted(body_lines, key=lambda r: (r[0], r[1]))]
    centres = sorted(cx for _, _, cx, _ in body_lines)
    span = centres[-1] - centres[0]
    best_gap, split = 0.0, None
    lo, hi = int(len(centres) * 0.15), int(len(centres) * 0.85) + 1
    for i in range(max(1, lo), min(len(centres), hi)):
        gap = centres[i] - centres[i - 1]
        if gap > best_gap:
            best_gap, split = gap, (centres[i - 1] + centres[i]) / 2.0
    if split is not None and span > 0 and best_gap / span > 0.25:
        left = sorted((y, x0, t) for y, x0, cx, t in body_lines if cx < split)
        right = sorted((y, x0, t) for y, x0, cx, t in body_lines if cx >= split)
        if len(left) >= 3 and len(right) >= 3:
            return [t for _, _, t in left] + [t for _, _, t in right]
    return [t for _, _, _, t in sorted(body_lines, key=lambda r: (r[0], r[1]))]


def load_stream(dip_dir: Path, alias: str, upscale: int) -> Stream:
    st = Stream(alias)
    band = _GEOM_BODY.get(alias, DEFAULT_BODY)
    geom_w = _GEOM_WIDTH.get(alias)
    pages = sorted((p for p in dip_dir.glob("*.json") if not p.name.startswith("_")),
                   key=lambda p: _page_index(p.stem))
    st.n_pages = len(pages)
    for p in pages:
        try:
            d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001  — a half-written page mid-run: skip, re-run later
            continue
        lines = d.get("lines", [])
        if not lines:
            continue
        pageid = d.get("page", p.stem)
        # normaliser: measured tomes use page_width_px×upscale; others use this page's max x1
        # (already in upscaled pixels), so the band fractions still apply.
        width = (geom_w * upscale) if geom_w else max((l["bbox"][2] for l in lines), default=1)
        width = float(width) or 1.0
        body_lines: list[tuple[int, int, float, str]] = []
        for l in lines:
            b = l["bbox"]
            cx = (b[0] + b[2]) / 2.0
            frac = cx / width
            text = l.get("text", "")
            st.long_s += text.count("ſ")
            if band[0] <= frac <= band[1]:
                if _is_inline_annotation(text):   # content signal atop geometry: inline apparatus key
                    st.n_inline_annot_lines += 1
                    st.margin_by_page[pageid].extend(_WORD_RE.findall(text))
                else:
                    body_lines.append((b[1], b[0], cx, text))  # (y_top, x_left, x_centre, text)
            else:
                st.n_margin_lines += 1
                st.margin_by_page[pageid].extend(_WORD_RE.findall(text))
        ordered = _reading_order(body_lines)  # column-aware: 2-col pages read L-col then R-col
        st.n_body_lines += len(ordered)
        for text in ordered:
            fo, rw = _fold_words(text)
            st.fold.extend(fo)
            st.raw.extend(rw)
            st.page.extend([pageid] * len(fo))
    return st


# ------------------------------------------------------------------ #
# Content-anchored windowing (monotone chapter cursor; fresh per-verse window) — as consensus.
# ------------------------------------------------------------------ #
def _probe(text: str) -> list[str]:
    return [s for s in (skel(w) for w in raw_words(text)) if len(s) >= 2]


def _recall(probe: list[str], hay: list[str], start: int, end: int) -> float:
    pset = set(probe)
    if not pset:
        return 0.0
    return len(pset & set(hay[start:end])) / len(pset)


def locate_region(probe: list[str], folded: list[str], lo: int = 0) -> tuple[float, int, int]:
    sub = folded[lo:]
    _, s, e = best_window(probe, sub)
    a, b = lo + s, lo + e
    return _recall(probe, folded, a, b), a, b


def tight_window(probe: list[str], folded: list[str], lo: int, hi: int) -> tuple[float, int, int]:
    hi = min(hi, len(folded))
    if lo >= hi:
        return 0.0, lo, lo
    pset = set(probe)
    if not pset:
        return 0.0, lo, lo
    w = max(len(probe), 12)
    step = max(1, w // 6)
    best_rec, best_off = 0.0, lo
    for off in range(lo, max(lo + 1, hi - w + 1), step):
        rec = len(pset & set(folded[off:off + w])) / len(pset)
        if rec > best_rec:
            best_rec, best_off = rec, off
    return best_rec, best_off, min(hi, best_off + w)


def candidate_aliases(book: str, present: list[str]) -> list[str]:
    """Aliases to probe for a book, filtered to those actually loaded. Appendix apocrypha are
    printed at the END of the OT volumes, so they search the OT aliases (per consensus note).

    FALLBACK: some NT scan dirs encode no testament in their name (jp2-S04, jp2-S08, eebo-vol1), so
    name-classification would wrongly exclude every present stream for an NT book. When the filter
    yields nothing, probe all present streams — the per-verse ATTEST_THRESHOLD + char-identity gates
    decide quality, so a book is never dropped by an alias-name heuristic (QC contract, no book-drop)."""
    is_nt = _BOOK_TESTAMENT.get(book) == "NT"
    same = [a for a in present if is_nt_alias(a) == is_nt]
    return same or list(present)


def resolve_alias(book: str, chapters: dict[int, dict[int, str]],
                  streams: dict[str, Stream]) -> tuple[str, float]:
    """Pick the alias whose mid-chapter probe-recall is highest. NO floor: the best alias is returned
    unconditionally (empty only when no same-testament stream has any token overlap at all). Per-verse
    ATTEST_THRESHOLD + qc_audit char-identity gate quality; this never drops a book."""
    chs = sorted(chapters)
    if not chs:
        return "", 0.0
    mid = chs[len(chs) // 2]
    probe = _probe(" ".join(chapters[mid][v] for v in sorted(chapters[mid])))
    if not probe:
        return "", 0.0
    best_a, best_r = "", 0.0
    for a in candidate_aliases(book, list(streams)):
        st = streams[a]
        if not st.fold:
            continue
        r, _, _ = locate_region(probe, st.fold)
        if r > best_r:
            best_a, best_r = a, r
    return best_a, round(best_r, 4)  # no floor — best alias always returned; quality gated per-verse


# ------------------------------------------------------------------ #
# Folded agreement (surface vs modern anchor) — as consensus
# ------------------------------------------------------------------ #
def _fold_multiset(text: str) -> Counter:
    return Counter(s for s in (skel(w) for w in raw_words(text)) if len(s) >= 2)


def _token_agreement(a: str, b: str) -> tuple[int, int]:
    ta, tb = _fold_multiset(a), _fold_multiset(b)
    inter = sum((ta & tb).values())
    denom = max(sum(ta.values()), sum(tb.values())) or 1
    return inter, denom


def confidence_for(recall: float) -> str:
    """Single-product confidence keys off the located-window recall (no corroboration depth)."""
    if recall >= 0.75:
        return "high"
    if recall >= 0.6:
        return "moderate"
    return "low"


def scripture_record(skid: str, surface: str, locus: str, conf: str, evidence: str) -> dict:
    return {"skeleton_id": skid, "present": True, "surface": surface, "spelling": "archaic",
            "locus": locus, "method": "our-ocr-diplomatic", "region": "scripture",
            "local_confidence": conf, "evidence_ptr": evidence}


def apparatus_record(book: str, ch: int, alias: str, pages: list[str], words: list[str]) -> dict:
    """Chapter-level marginal capture: raw region-typed apparatus text (ſ preserved). NOT a
    skeleton-grid apparatus attestation — a capture keyed to the chapter its pages carry, for
    P4.2 to align to real apparatus ids. Distinct 'apparatus-marginal/' namespace on purpose."""
    span = f"{pages[0]}..{pages[-1]}" if pages else "?"
    return {"skeleton_id": f"apparatus-marginal/{book}/{ch}", "present": True,
            "surface": " ".join(words).strip(), "spelling": "archaic",
            "locus": f"{alias} pages[{span}]", "method": "our-ocr-diplomatic",
            "region": "apparatus-marginal", "local_confidence": "capture",
            "evidence_ptr": f"our_ocr:{alias}:margin:{book}:{ch}",
            "n_pages": len(pages), "n_words": len(words)}


# ------------------------------------------------------------------ #
# Per-book detection
# ------------------------------------------------------------------ #
def detect_book(book: str, chapters: dict[int, dict[int, str]], line: str,
                streams: dict[str, Stream]) -> tuple[list[dict], list[dict], dict]:
    alias, probe_recall = resolve_alias(book, chapters, streams)
    n_expected = sum(len(vs) for vs in chapters.values())
    if not alias:
        return [], [], {"book": book, "testament": _BOOK_TESTAMENT.get(book),
                        "alias": "", "probe_recall": probe_recall, "covered": False,
                        "expected_verses": n_expected, "attested_verses": 0,
                        "attestation_rate": 0.0, "folded_agreement_vs_anchor": None,
                        "apparatus_chapters": 0, "apparatus_words": 0}
    st = streams[alias]
    folded, raw, page = st.fold, st.raw, st.page

    reads: list[dict] = []
    app_reads: list[dict] = []
    n_attested = 0
    agree_matched = agree_denom = 0
    app_words_total = 0
    cursor = 0
    maxch = _BOOK_CH.get(book, 0)

    for ch in sorted(chapters):
        if maxch and ch > maxch:
            continue
        verses = chapters[ch]
        chap_probe = _probe(" ".join(verses[v] for v in sorted(verses)))
        if chap_probe:
            _, a, b = locate_region(chap_probe, folded, cursor)
            ca = max(0, a - CHAP_PAD)
            cb = min(len(folded), b + CHAP_PAD)
            cursor = a
        else:
            ca = cursor
            cb = min(len(folded), cursor + NEIGHBOURHOOD)

        # apparatus capture: the marginal words on the pages this chapter's body window spans.
        pages_span: list[str] = []
        seen: set[str] = set()
        for i in range(ca, min(cb, len(page))):
            pg = page[i]
            if pg not in seen:
                seen.add(pg)
                pages_span.append(pg)
        app_words: list[str] = []
        for pg in pages_span:
            app_words.extend(st.margin_by_page.get(pg, []))
        if app_words:
            app_reads.append(apparatus_record(book, ch, alias, pages_span, app_words))
            app_words_total += len(app_words)

        for v in sorted(verses):
            probe = _probe(verses[v])
            if not probe:
                continue
            rec, wa, wb = tight_window(probe, folded, ca, cb)
            if rec < ATTEST_THRESHOLD:
                continue
            n_attested += 1
            surface = " ".join(raw[wa:wb]).strip()
            reads.append(scripture_record(
                f"scripture/{book}/{ch}/{v}", surface, f"{alias} tok[{wa}:{wb}]",
                confidence_for(rec), f"our_ocr_{line}:{book}:{ch}:{v}"))
            m, d = _token_agreement(surface, verses[v])
            agree_matched += m
            agree_denom += d

    stats = {
        "book": book, "testament": _BOOK_TESTAMENT.get(book),
        "alias": alias, "probe_recall": probe_recall, "covered": True,
        "expected_verses": n_expected, "attested_verses": n_attested,
        "attestation_rate": round(n_attested / n_expected, 4) if n_expected else None,
        "folded_agreement_vs_anchor": round(agree_matched / agree_denom, 4) if agree_denom else None,
        "apparatus_chapters": len(app_reads), "apparatus_words": app_words_total,
    }
    return reads, app_reads, stats


# ------------------------------------------------------------------ #
def coverage(reads: list[dict]) -> dict:
    chapters, verses, out_of_grid, books = set(), 0, [], set()
    for r in reads:
        parts = r["skeleton_id"].split("/")
        if len(parts) != 4 or parts[0] != "scripture":
            continue
        _, book, ch, _ = parts
        verses += 1
        books.add(book)
        chapters.add((book, int(ch)))
        maxch = _BOOK_CH.get(book)
        if maxch is None or int(ch) > maxch:
            out_of_grid.append(r["skeleton_id"])
    return {"books": len(books), "chapters": len(chapters), "verses": verses,
            "out_of_grid": out_of_grid[:20], "out_of_grid_count": len(out_of_grid)}


def manifest_status(dip_dirs: list[Path]) -> dict:
    """Aggregate the per-alias _manifest.json signals + a live page count."""
    root_manifest = DIPL_ROOT / "_manifest.json"
    info = {"root_manifest": None, "pages_present": {}}
    if root_manifest.exists():
        try:
            info["root_manifest"] = json.loads(root_manifest.read_text())
        except Exception:  # noqa: BLE001
            pass
    for d in dip_dirs:
        info["pages_present"][d.name] = sum(
            1 for p in d.glob("*.json") if not p.name.startswith("_"))
    return info


def wait_for_completion(dip_dirs: list[Path], no_wait: bool) -> dict:
    """Gate on the OCR run finishing. 'complete' = the root manifest reports every line done.
    With --no-wait we finalise against whatever pages exist and report coverage honestly."""
    if no_wait:
        return {"gated": False, "status": manifest_status(dip_dirs),
                "note": "--no-wait: finalised against current pages (may be partial)"}
    t0 = time.time()

    def done() -> bool:
        rm = (DIPL_ROOT / "_manifest.json")
        if not rm.exists():
            return False
        try:
            m = json.loads(rm.read_text())
        except Exception:  # noqa: BLE001
            return False
        return bool(m.get("complete"))

    while not done() and time.time() - t0 < MANIFEST_MAX_WAIT_S:
        counts = {d.name: sum(1 for p in d.glob('*.json') if not p.name.startswith('_'))
                  for d in dip_dirs}
        print(f"  [wait] OCR not complete elapsed={int(time.time()-t0)}s pages={counts}", flush=True)
        time.sleep(MANIFEST_POLL_S)
    return {"gated": True, "waited_s": round(time.time() - t0, 1),
            "complete": done(), "status": manifest_status(dip_dirs)}


# ------------------------------------------------------------------ #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("line", choices=sorted(LINE_PREFIX), help="which scan line to detect")
    ap.add_argument("--book", help="restrict to a single slug (debug)")
    ap.add_argument("--no-wait", action="store_true",
                    help="do not gate on OCR completion (develop against current pages)")
    ap.add_argument("--no-validate", action="store_true")
    args = ap.parse_args()

    prefix = LINE_PREFIX[args.line]
    upscale = 2
    dip_dirs = sorted(d for d in DIPL_ROOT.glob(f"{prefix}*") if d.is_dir())
    if not dip_dirs:
        raise SystemExit(f"no diplomatic-OCR dirs under {DIPL_ROOT} for line {args.line!r} "
                         f"(prefix {prefix!r}) — has ocr_pipeline.py run?")

    READS_DIR.mkdir(parents=True, exist_ok=True)
    gate = wait_for_completion(dip_dirs, args.no_wait)
    print(f"OCR gate: {gate.get('note', 'complete=%s' % gate.get('complete'))}")

    print("loading + region-typing diplomatic OCR (fold once per alias) ...", flush=True)
    streams: dict[str, Stream] = {}
    for d in dip_dirs:
        alias = d.name[len(prefix):]
        st = load_stream(d, alias, upscale)
        streams[alias] = st
        print(f"  {alias:18s} pages={st.n_pages:>4d} body_lines={st.n_body_lines:>6d} "
              f"margin_lines={st.n_margin_lines:>6d} body_tok={len(st.fold):>7,} ſ={st.long_s:>6,}",
              flush=True)

    anchor = anchor_by_book(load_anchor())
    books = _BOOK_ORDER if not args.book else [args.book]
    if args.book and args.book not in _BOOK_CH:
        raise SystemExit(f"no such book slug: {args.book}")

    all_reads: list[dict] = []
    all_app: list[dict] = []
    per_book: list[dict] = []
    for book in books:
        chapters = anchor.get(book)
        if not chapters:
            per_book.append({"book": book, "testament": _BOOK_TESTAMENT.get(book),
                             "expected_verses": 0, "attested_verses": 0,
                             "note": "no modern anchor"})
            continue
        reads, app, stats = detect_book(book, chapters, args.line, streams)
        all_reads.extend(reads)
        all_app.extend(app)
        per_book.append(stats)
        print(f"{book:22s} {stats['attested_verses']:5d}/{stats['expected_verses']:<5d} "
              f"({stats['attestation_rate']}) alias={stats['alias'] or '—':14s} "
              f"agree={stats['folded_agreement_vs_anchor']} app_ch={stats['apparatus_chapters']}",
              flush=True)

    cov = coverage(all_reads)
    out = {"source": f"our_ocr_{args.line}", "lineage": "our-ocr-diplomatic", "independent": True,
           "spelling": "archaic", "engine": "kraken+reichenau_lat", "count": len(all_reads),
           "apparatus_count": len(all_app), "coverage": cov,
           "reads": all_reads + all_app}
    out_reads = READS_DIR / f"our_ocr_{args.line}.json"
    out_reads.write_text(json.dumps(out, ensure_ascii=False))
    print(f"\nreads → {out_reads.relative_to(REPO)}  "
          f"({cov['books']} books · {cov['chapters']} chapters · {cov['verses']} verses "
          f"· {len(all_app)} apparatus-marginal captures)")

    if not args.no_validate:
        val = build_validation(args.line, per_book, cov, gate, streams, len(all_app), bool(args.book))
        out_valid = HERE / f"our-ocr-{args.line}-validation.json"
        out_valid.write_text(json.dumps(val, ensure_ascii=False, indent=2) + "\n")
        agg = val["aggregate"]
        print(f"\nvalidation: attested {agg['attested_verses']}/{agg['expected_verses']} "
              f"({agg['attestation_rate']}) · agree={agg['folded_agreement_vs_anchor']}")
        ag = val["archaic_gap_ot"]
        print(f"  archaic-gap OT: {ag['attested_verses']}/{ag['expected_verses']} "
              f"({ag['attestation_rate']}) · long-ſ preserved total={val['diplomatic']['long_s_total']:,}")
        print(f"validation → {out_valid.relative_to(REPO)}")
    return 0


def build_validation(line: str, per_book: list[dict], cov: dict, gate: dict,
                     streams: dict[str, Stream], n_apparatus: int, single_book: bool) -> dict:
    scored = [b for b in per_book if b.get("expected_verses")]
    exp = sum(b["expected_verses"] for b in scored)
    att = sum(b["attested_verses"] for b in scored)
    am = ad = 0
    for b in scored:
        fa = b.get("folded_agreement_vs_anchor")
        if fa is not None:
            am += round(fa * b["attested_verses"])
            ad += b["attested_verses"]

    def _gap_agg() -> dict:
        gb = [b for b in per_book if b["book"] in ARCHAIC_GAP_OT and b.get("expected_verses")]
        e = sum(b["expected_verses"] for b in gb)
        a = sum(b["attested_verses"] for b in gb)
        return {"expected_verses": e, "attested_verses": a,
                "attestation_rate": round(a / e, 4) if e else None,
                "books_covered": [b["book"] for b in gb if b["attested_verses"] > 0],
                "books_missing": [b for b in ARCHAIC_GAP_OT
                                  if b not in {x["book"] for x in gb if x["attested_verses"] > 0}],
                "per_book": [{"book": b["book"], "expected": b["expected_verses"],
                              "attested": b["attested_verses"], "alias": b.get("alias"),
                              "attestation_rate": b["attestation_rate"],
                              "folded_agreement_vs_anchor": b.get("folded_agreement_vs_anchor")}
                             for b in gb]}

    weak = sorted([b for b in scored if (b["attestation_rate"] or 0) < 0.5],
                  key=lambda b: (b["attestation_rate"] or 0))

    return {
        "witness": f"our_ocr_{line} (fresh diplomatic OCR of the original scans, ſ-preserving)",
        "supersedes": "ocr_consensus (stock tesseract -l eng; ſ→f collapse — see §6.2/§6.3)",
        "engine": "kraken 7.0.2 + reichenau_lat_cat mlmodel (2x Lanczos, baseline seg)",
        "modern_anchor": "madueke_a (+ sabates_a for the 3 appendix books)",
        "method": {
            "approach": "content-anchored attestation identical to detect_ocr_consensus — anchor "
                        "on the modern text and corroborate each verse; NOT from-scratch verse "
                        "segmentation. Only the stored SURFACE (diplomatic, ſ intact) and the "
                        "bbox REGION-TYPING are new.",
            "region_typing": "each OCR line's bbox x-centre is normalised by the tome's page "
                             "width (2× for the upscale) and classified against the "
                             "marginalia-geometry §4.4 text-column band: inside = body scripture, "
                             "outside = marginal apparatus. Body feeds verse attestation; marginal "
                             "text is captured per chapter (apparatus-marginal/<book>/<ch>).",
            "fold": "shared SYMMETRIC ocr_sample.skel (long-s / u-v / i-j / vv-w / ligature / "
                    "silent-e / doubled-letter) — used ONLY to locate the verse window; the "
                    "diplomatic ſ is preserved in the raw stored surface, never folded.",
            "attest_threshold": ATTEST_THRESHOLD,
            "surface": "raw kraken window text of the best alias (long-ſ preserved).",
            "apparatus_note": "apparatus-marginal captures are chapter-granular raw marginal text, "
                              "NOT verse-aligned apparatus attestations — they feed P4.2 alignment.",
            "determinism": "no randomness; identical inputs → identical output.",
        },
        "gate": gate,
        "streams": {a: {"pages": s.n_pages, "body_lines": s.n_body_lines,
                        "margin_lines": s.n_margin_lines, "body_tokens": len(s.fold),
                        "long_s": s.long_s} for a, s in streams.items()},
        "diplomatic": {"long_s_total": sum(s.long_s for s in streams.values()),
                       "note": "long-ſ present in the raw surfaces is the headline improvement "
                               "over ocr_consensus (which had ſ=0 on every page)."},
        "coverage": cov,
        "apparatus_marginal_captures": n_apparatus,
        "aggregate": {
            "books_with_anchor": len(scored),
            "expected_verses": exp, "attested_verses": att,
            "attestation_rate": round(att / exp, 4) if exp else None,
            "folded_agreement_vs_anchor": round(am / ad, 4) if ad else None,
            "single_book_debug_run": single_book,
        },
        "archaic_gap_ot": _gap_agg(),
        "weak_books": [{"book": b["book"], "testament": b.get("testament"), "alias": b.get("alias"),
                        "expected_verses": b["expected_verses"], "attested_verses": b["attested_verses"],
                        "attestation_rate": b["attestation_rate"],
                        "folded_agreement_vs_anchor": b.get("folded_agreement_vs_anchor")}
                       for b in weak],
        "caveats": [
            "Recall is a CORROBORATION signal, not an exact-match rate: the archaic<->modern fold "
            "is lossy and blackletter OCR is noisy.",
            "The stored surface is a raw OCR window sliced by folded-token bounds; it may over/under-"
            "run the verse extent. It is a diplomatic attestation snippet, not a clean verse.",
            "Region-typing is geometric: a short body line dipping into a margin band (or a merged "
            "body+margin OCR line) can be mis-typed; the band thresholds are per-tome measured.",
            "Coverage depends on the diplomatic OCR run; if incomplete at finalisation (see gate), "
            "affected books fall to whatever pages exist.",
        ],
        "per_book": per_book,
    }


if __name__ == "__main__":
    sys.exit(main())
