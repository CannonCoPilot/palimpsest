#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""corpus_localize.py — STAGE 1: run the improved localizer over the STORED corpus stream (2026-07-27).

THE GAP THIS CLOSES. `qc_audit` — the authority behind every headline number in the report — localizes verses
with `detect_our_ocr.detect_book`, and imports NONE of `verse_locate`, `xsrc_gate`, `r3_route`, `s_arbiter`.
So the report has been showing the BEFORE state on 6438 verses and the AFTER state on 16 gold pages, and never
joining them. The `corpus_wire_probe` measured what closing that gap is worth, on gold:

    base (the stream every headline scores)        mean 0.7213   pass 40%
    stored + body-isolation only                   mean 0.7720   pass 43%    (25% of the lift)
    stored + body-isolation + HYBRID LOCALIZER     mean 0.8724   pass 60%    (74% of the lift)
    live-R2 (re-running kraken per page)           mean 0.9256   pass 68%

**74% of the lift is recoverable from what is already on disk** — the corpus stream was already recognised
with `reichenau_lat` and every stored line carries a bbox — so this pass re-recognises NOTHING. It re-reads the
pages we already have and localizes them properly.

WHAT MAKES IT POSSIBLE NOW. The localizer needs to know which (book, chapter) a page belongs to, and taking
that from an address was exactly what mis-addressed colossians-3. `page_address` now assigns every page of
every volume by monotone alignment (10,540 pages, 100% coverage, 1251/1251 held-out chapter labels, GT 16/16),
so each page arrives with a small validated chapter interval and, where the printed heading survives, exact
line ranges. A page whose interval holds two chapters is localized under BOTH and the per-verse `janvier_fit`
selector — the same gold-free selector `best_spans` already uses to choose between segmenters — decides.

OUTPUT: `.corpus-localize-<ocr_dir>.json` = {"book/ch/v": {text, fit, page}} — a drop-in replacement for the
vmap `qc_audit` builds from `detect_book`, and cached so the audit re-runs offline.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import os                                  # noqa: E402
import layout as _layout                    # noqa: E402
import reocr_core as _core                  # noqa: E402
import verse_locate                        # noqa: E402
import verse_seg as VS                     # noqa: E402
from corpus_wire_probe import stored_page  # noqa: E402
import witness_inventory as _WI            # noqa: E402  # why a volume localizes nothing, from the registry
sys.path.insert(0, str(HERE / "witness"))
import witnesses as _W                     # noqa: E402  # the artefact must NAME the witness it localized

PILOT_BOOKS = ["psalms", "genesis", "matthew", "john", "apocalypse"]


def _line_range(rec: dict, chapter: int):
    """The line range this chapter occupies on the page, when the printed heading pinned one.

    Without it, `verse_seg.segment`'s documented contract is violated on every multi-chapter page — every verse
    of both chapters competes for every position, which is the runaway the anchor-walk exists to prevent,
    reintroduced at page level (§13 Q5). With no surviving heading there is no honest range and the whole page
    is offered; the selector then resolves it per verse.

    MEASURED DEFECT, FIXED HERE (2026-07-28). This took only the FIRST `printed-heading` pin, which is wrong
    in both directions once the headings are actually readable:

    * **TRUNCATION (3,006 pages, 67,284 body lines discarded).** A chapter can occupy TWO pin segments on one
      page — a `carry-in` run before its heading and a `printed-heading` run after it — whenever the heading
      falls mid-page (a second column, or a chapter reopening). `jp2-S04` p680 is all Apocalypse 1 across 83
      lines with `CHA P. I.` at line 44, so this returned (44, 82) and threw away lines 0–43, taking real
      verses (Apoc 1:11–15, janvier fit 0.79–0.98) out of scope with them.
    * **OVER-CLAIM (275 pages).** A chapter with only a `carry-in` pin returned None, so the WHOLE page was
      offered — the very runaway this function exists to prevent, on the pages that straddle a boundary.

    Both vanish under the honest definition: a chapter's range is the union of EVERY pin that names it. The
    `printed-heading` source stays authoritative for where a chapter STARTS; it was never authoritative for
    where the chapter's text on this page ENDS or begins."""
    lo = hi = None
    for s in rec.get("pins") or []:
        if s.get("chapter") != chapter:
            continue
        lo = s["lo"] if lo is None else min(lo, s["lo"])
        hi = s["hi"] if hi is None else max(hi, s["hi"])
    return None if lo is None else (lo, hi)


def _better(cand_fit: float, cand_text: str, incumbent: dict | None, ref_len: int,
            ref_text: str | None = None) -> bool:
    """Is this span a better claim on the verse than the one already held?

    Fit decides whenever it can. When it CANNOT — and on the failures that matter it usually cannot — length
    sanity breaks the tie.

    MEASURED, `archive-holiebible-ot1` genesis 1. Page 30 (the volume's front matter) and page 31 (the real
    text) both carry chapter 1 in their interval, so both are offered. For verses 4, 5, 6, 9 and 11 page 30
    produces a ONE-TOKEN span and page 31 produces an 18-, 13-, 19-, 20- and 26-token span — and BOTH score
    `janvier_fit` 0.0, because the page-31 text is real but too corrupt to match. The old test was a strict
    `fit > incumbent`, so the tie went to whichever page was visited first, which is the front matter. Five
    verses of Genesis 1 were represented by a single word while a full span sat unused on the next leaf.

    This changes only which CANDIDATE is kept; no score is altered and nothing is dropped, so a verse that is
    genuinely unreadable still fails — it now fails holding its real text instead of one token of somebody
    else's."""
    if incumbent is None:
        return True
    if cand_fit > incumbent["fit"] + 1e-9:
        return True
    if cand_fit < incumbent["fit"] - 1e-9:
        return False
    # §13 Q30 (2026-07-29, DEFAULT OFF under ODR_PARTIAL_FIT). The tie above is not rare and it is not noise:
    # corpus-wide, 4.8% of contested verses have EVERY candidate at fit 0.000, so the length proxy — not the
    # selector — decides them. The proxy is a proxy: `matthew/19/9` keeps a 38-token span whose partial-tolerant
    # F1 against janvier is 0.20 over a 23-token span at 0.51. `verse_locate.partial_fit` measures the thing the
    # length ratio only gestures at, and unlike `gen1_r3.span_fit` alone it cannot be gamed by a fragment (that
    # pathology fired for real here: a 1-token span at precision 1.000 beating a 12-token span at 0.58).
    #
    # THE LENGTH BAND IS THE FIRST KEY, NOT A FALLBACK. Measured on `archive-ot1-1609` (2026-07-29): F1 used
    # alone here moved `genesis/1/1` to page 4, the volume's FRONT MATTER (`in banisliment. The Slauonians and
    # Gothes`) — a SHORT fragment can out-score a long, badly-garbled reading of the real page, which is exactly
    # the failure this function's length rule was written to prevent. So a candidate inside the sane length band
    # beats one outside it unconditionally, and F1 decides only among candidates that are plausibly the whole
    # verse. On the cases the length ratio got wrong (`matthew/19/9`: 38 tokens vs 23 against a ~24-token
    # reference) that ordering is enough on its own — the 38-token span is out of band.
    if ref_text and verse_locate._rescue_partial("better"):
        rl = len((ref_text or "").split())

        def _in_band(t):
            n = len((t or "").split())
            return bool(rl) and 0.5 <= (n / rl) <= 1.5

        cb, ib = _in_band(cand_text), _in_band(incumbent.get("text", ""))
        if cb != ib:
            return cb
        cf = verse_locate.partial_fit(cand_text, ref_text)[2]
        inf = verse_locate.partial_fit(incumbent.get("text", ""), ref_text)[2]
        if abs(cf - inf) > 1e-9:
            return cf > inf
    if not ref_len:
        return False
    def _off(t):                                  # distance from the reference length, symmetric in ratio
        n = len((t or "").split())
        return abs((n / ref_len) - 1.0) if n else 9.9
    return _off(cand_text) < _off(incumbent.get("text", ""))


def localize_volume(ocr_dir: str, books: list[str], *, limit: int | None = None, verbose: bool = True) -> dict:
    """Localize every page of `ocr_dir` that `page_address` assigned to one of `books`."""
    af = HERE / f".page-address-{ocr_dir}.json"
    if not af.exists():
        raise FileNotFoundError(f"{af.name} missing — run page_address_eval.py --ocr-dir {ocr_dir} first")
    recs = [r for r in json.loads(af.read_text())["records"] if r["book"] in books]
    if limit:
        recs = recs[:limit]
    out: dict = {}
    t0, n_calls = time.time(), 0
    for k, rec in enumerate(recs):
        page = stored_page(ocr_dir, rec["page_index"])
        if not page:
            continue
        page["page_index"] = rec["page_index"]
        for ch in rec["chapters_on_page"] or [rec["chapter"]]:
            if not ch:
                continue
            janv = VS.chapter_verses(rec["book"], ch, VS.JANVIER) or {}
            if not janv:
                continue
            # BOOK-SPECIFIC VARIATION (Sir, 2026-07-29). There is no rule that every book runs identical code;
            # a book is handled by a VARIATION of the shared logic, tuned to how that book is actually set. The
            # generic path above and in `layout`/`verse_seg` is left untouched as the reference implementation.
            # Genesis's variation is in `genesis_tuned`: its apparatus filter anchors on the ARCHAIC reference
            # (s_dismas/odr_com) rather than modern janvier, so the archaic spellings the DR prints stop
            # looking like apparatus and the run threshold can come down from 8 to 2.
            pg_for_ch = page
            # DEFAULT OFF — built, wired, measured, NOT yet net-positive. Best Genesis state without it is
            # S1 67.5 / S3 75.5 / S9 76.1 / S6 77.7, all-pass 799. With it: min_run=2 gives 518 all-pass
            # (near-misses explode: S6 102->302 — it deletes scripture like the hyphen-split "fir. ment");
            # min_run=3 gives 753, S9 +0.9 but S6 -3.1. The ANCHOR insight underneath it is validated and
            # worth keeping (archaic anchoring cuts archaic-spelling false positives 3,282 -> 838); the
            # RUN-LENGTH rule on top of it is not yet good enough to spend scripture on.
            # Set ODR_GENESIS_TUNED=1 (with ODR_GEN_MINRUN) to continue the sweep.
            if rec["book"] == "genesis" and os.environ.get("ODR_GENESIS_TUNED", "0") != "0":
                import genesis_tuned as GT
                cleaned = GT.clean_page_lines(page["lines"], ch)
                lines2 = [{**l, "text": t} for l, t in zip(page["lines"], cleaned)]
                body2 = [l for l in lines2 if l.get("role") == "body"]
                pg_for_ch = {**page, "lines": lines2,
                             "r2_body": _layout.strip_verse_numbers(
                                 _core._norm(" ".join(l["text"] for l in body2)))}
            try:
                spans = verse_locate.best_spans(pg_for_ch, rec["book"], ch, line_range=_line_range(rec, ch))
            except Exception:                              # noqa: BLE001
                continue
            n_calls += 1
            for v, sp in (spans or {}).items():
                text = (sp or {}).get("text") or ""
                if not text.strip():
                    continue
                fit = verse_locate.janvier_fit(text, janv.get(v))
                key = f"{rec['book']}/{ch}/{v}"
                # ADJACENT PAGES' INTERVALS OVERLAP BY DESIGN, so two pages can both offer a verse. Keep the
                # better-fitting span rather than the later one: `janvier_fit` is the same gold-free selector
                # `best_spans` uses internally, so the choice is made on the same evidence, not on page order.
                if _better(fit, text, out.get(key), len((janv.get(v) or "").split()), janv.get(v)):
                    out[key] = {"text": text, "fit": round(fit, 4), "page": rec["page_index"], "chapter": ch}
        if verbose and (k + 1) % 50 == 0:
            print(f"  {ocr_dir} {k+1}/{len(recs)} pages · {len(out)} verses · {time.time()-t0:.0f}s", flush=True)

    # ---- SPAN-LENGTH REJECTION AND RETRY -------------------------------------------------------------
    # A verse is only ever offered by pages whose `chapters_on_page` lists its chapter, so a verse whose real
    # page does not list it gets no candidate at all and settles for whatever a neighbouring page produced.
    # MEASURED on Genesis 1: comparing verses ≥3 witnesses pass against those ≤2 pass, **11 of 18 low-support
    # verses carry a span under half or over 1.5x the reference length, and 0 of 13 high-support verses do**.
    # The MEAN ratio does not separate them (1.07 vs 1.01) — only the extremes. `janvier_fit` is length-aware
    # (a one-token span scores 0.0, not 1.0), so these spans did not out-score a better one; nothing better
    # was ever offered.
    #
    # So the remedy is to WIDEN THE CANDIDATE SET, not to change the selector: re-offer each suspect verse on
    # the pages either side of where it landed, whatever those pages' chapter intervals claim, and keep the
    # existing janvier-fit choice between them.
    #
    # NOTHING IS EVER DROPPED. A rejected span whose retry finds nothing better is KEPT, so the verse stays
    # attested and fails visibly. Deleting it would make the verse un-localized, remove it from the
    # denominator, and RAISE the pass rate by hiding the failure — the exact laundering this project forbids.
    n_retry = n_better = 0
    if recs:
        all_recs = {r["page_index"]: r for r in json.loads(af.read_text())["records"]}
        chapters = {}
        for key in list(out):
            b, c, v = key.split("/")
            chapters.setdefault((b, int(c)), {})[int(v)] = out[key]
        want = []                                        # (book, ch, verse, incumbent_fit, candidate pages)
        for (b, c), got in chapters.items():
            janv = VS.chapter_verses(b, c, VS.JANVIER) or {}
            if not janv:
                continue
            seen_pages = {d["page"] for d in got.values()}
            for v, ref in janv.items():
                rl = len((ref or "").split())
                if not rl:
                    continue
                cur = got.get(v)
                if cur is not None:
                    ratio = len((cur["text"] or "").split()) / rl
                    if 0.5 <= ratio <= 1.5:
                        continue
                    near = {cur["page"] - 1, cur["page"] + 1}
                else:
                    near = {p + d for p in seen_pages for d in (-1, 1)}
                want.append((b, c, v, (cur or {}).get("fit", -1.0), near))
        # group the retries by (page, chapter) so each page is segmented once, not once per verse
        jobs = {}
        for b, c, v, fit, near in want:
            for pi in near:
                if pi in all_recs:
                    jobs.setdefault((pi, b, c), []).append((v, fit))
        for (pi, b, c), vs in jobs.items():
            rec = all_recs[pi]
            page = stored_page(ocr_dir, pi)
            if not page:
                continue
            page["page_index"] = pi
            janv = VS.chapter_verses(b, c, VS.JANVIER) or {}
            try:
                spans = verse_locate.best_spans(page, b, c, line_range=_line_range(rec, c))
            except Exception:                              # noqa: BLE001
                continue
            n_retry += 1
            for v, incumbent in vs:
                text = ((spans or {}).get(v) or {}).get("text") or ""
                if not text.strip():
                    continue
                fit = verse_locate.janvier_fit(text, janv.get(v))
                key = f"{b}/{c}/{v}"
                if _better(fit, text, out.get(key), len((janv.get(v) or "").split()), janv.get(v)):
                    out[key] = {"text": text, "fit": round(fit, 4), "page": pi, "chapter": c, "retry": True}
                    n_better += 1
        if verbose:
            print(f"  {ocr_dir}: length-retry — {len(want)} suspect verses, {n_retry} page-chapter re-segments, "
                  f"{n_better} improved", flush=True)
    if verbose:
        print(f"  {ocr_dir}: {len(recs)} pages, {n_calls} best_spans calls, {len(out)} verses, "
              f"{time.time()-t0:.0f}s", flush=True)
    # The artefact names its witness, and an EMPTY result says why it is empty. `load()` returns {}
    # both for a volume that was never localized and for one that was localized and yielded nothing,
    # so without this the two are indistinguishable downstream -- an unmeasured thing presenting as a
    # measurement (R1.4). The reason is read from the registry rather than written by hand: a tome in
    # its source's `drop_tomes` is not expected to carry verse text, and that is a declaration the
    # registry owns. Hand-written, the note would be a claim this file cannot support.
    meta = {"ocr_dir": ocr_dir, "witness": _W.wid(*_W.witness_of(ocr_dir)),
            "books": books, "n_pages": len(recs), "verses": out}
    if not out:
        sid = _WI.ocr_dir_tome()[ocr_dir][0]
        dropped = sorted(set(_WI.WITNESSES[sid].get("drop_tomes") or []) & set(_WI.tomes_for(ocr_dir)))
        # THREE different zeroes, and they must not be allowed to read as each other. `pages_read == 0`
        # means no page of this volume is addressed to any sought book, so nothing was attempted -- that
        # is a statement about SCOPE, not a measurement of the volume, and calling it a measured absence
        # would be the same move as the `_empty_because` note this replaces (R7.5a-3: `jp2-S06nt` was
        # recorded as carrying no verse text "as a property of the corpus"; on corrected addressing it
        # localizes 2,344 verses. The narrative attached to the null is what stopped anyone re-running it).
        if not recs:
            why = ("no page of this volume is addressed to any of the books sought, so no verse was "
                   "attempted here. This is a statement of SCOPE, not a measurement of the volume: it "
                   "says nothing about whether the volume carries these books.")
        elif dropped:
            why = (f"{sid} declares drop_tomes={dropped}: this volume's verse text is not counted as a "
                   f"witness. Note that the drop is a SCORING rule -- it does not stop localization, so "
                   f"{len(recs)} pages were read and still yielded nothing, which is a measured null and "
                   f"is NOT explained by the drop.")
        else:
            why = (f"no declared reason -- {len(recs)} pages were read and no verse of the sought books "
                   f"was localized in them. This is a measured absence and an OPEN question, not a pass.")
        meta["empty"] = {
            "measured": bool(recs), "pages_read": len(recs), "books_sought": books,
            "dropped_tomes": dropped, "why": why,
        }
    (HERE / f".corpus-localize-{ocr_dir}.json").write_text(json.dumps(meta, ensure_ascii=False))
    return out


@__import__("functools").lru_cache(maxsize=None)
def load(ocr_dir: str, scope_check: bool = True) -> dict:
    """{(book, chapter, verse): text} for a volume, from cache. {} when the volume has not been localized.

    R9.2 -- REFUSES a volume whose witness is `verse_scope: "none"` (Gate 0f). The refusal sits here
    rather than in each consumer so that a consumer written next month, by someone who never read R9,
    fails loudly instead of quietly scoring an inadmissible witness. Strict by default -- the pattern
    R7.5b established for `jp2_page`.

    ⚠️ R9.2 ORIGINALLY CLAIMED, HERE, that this was "the function every verse consumer already goes
    through" (`qc_audit`, `book_audit`, `audit_diagnose`, `selector_corpus_probe`, `genesis_tuned`).
    IT WAS NOT, and the claim is left standing above only in this correction because how it was reached
    is the lesson: the check was a grep for modules *mentioning* `corpus_localize`, which tests imports,
    not call sites. Nine modules opened `.corpus-localize-*.json` and read `["verses"]` themselves --
    the same data with none of the gate. `test_verse_scope_bypass.py` now measures the thing the grep
    only gestured at, and R9.2c converted the readers to `load_verses`/`iter_localizations` below.

    `scope_check=False` is for tooling that audits the localization ARTEFACT rather than scoring the text,
    and the caller has to say so. Returning `{}` instead of raising was considered and rejected: `{}` is
    already what a never-localized volume returns, so a silent scope refusal would be indistinguishable
    from missing data -- the R1.4 hole this module closed for empty results one commit ago.
    """
    if scope_check:
        _W.assert_verse_admitted(ocr_dir)
    f = HERE / f".corpus-localize-{ocr_dir}.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text())
    out = {}
    for key, rec in d["verses"].items():
        b, c, v = key.rsplit("/", 2)
        out[(b, int(c), int(v))] = rec["text"]
    return out


def load_raw(ocr_dir: str, *, scope_check: bool = True, missing_ok: bool = False) -> dict:
    """The localization ARTEFACT for a volume, whole, with Gate 0f applied.

    R9.2c. `load()` above returns `{(book, ch, verse): text}` and throws away `page`, `fit` and the
    `empty`/`witness` metadata, so it is NOT a drop-in for the nine modules that were opening the file
    themselves -- every one of them wanted a field `load()` discards. Converting them to `load()` would
    have meant re-deriving `page` from somewhere else, i.e. making the gate cost evidence; a gate that
    costs evidence is a gate that gets routed around, which is the defect R9.2c exists to close, restated
    one turn later. So the gate goes in FRONT of the read the callers were already doing, and the gated
    route is the cheapest one available rather than the most expensive.

    `missing_ok=True` returns `{"verses": {}, ...}` for a volume that was never localized -- the shape
    a caller can keep indexing. It is OFF by default: several callers guarded the read with `p.exists()`
    for no stated reason, and an absent artefact is usually a pipeline-order mistake, not a fact.
    """
    if scope_check:
        _W.assert_verse_admitted(ocr_dir)
    f = HERE / f".corpus-localize-{ocr_dir}.json"
    if not f.exists():
        if missing_ok:
            return {"ocr_dir": ocr_dir, "verses": {}, "_absent": str(f.name)}
        raise FileNotFoundError(
            f"{f.name} missing -- run `corpus_localize.py {ocr_dir}` first. (Pass missing_ok=True only "
            f"if a never-localized volume is a legitimate state for this caller, not a pipeline-order "
            f"mistake: `{{}}` and 'not yet built' are the two things R1.4 exists to keep apart.)")
    return json.loads(f.read_text())


def load_verses(ocr_dir: str, *, scope_check: bool = True, missing_ok: bool = False) -> dict:
    """`{"book/ch/v": {text, fit, page, ...}}` -- the sub-map every direct reader was reaching for."""
    return load_raw(ocr_dir, scope_check=scope_check, missing_ok=missing_ok).get("verses", {})


def localized_dirs(*, heldout: bool = False) -> list[str]:
    """Every `ocr_dir` with a localization artefact on disk.

    `.corpus-localize-<dir>.heldout.json` is EXCLUDED by default. Those files came from
    `page_address_eval`'s held-out run mode and carry `ocr_dir` values like `archive-ot1-1610.heldout`,
    which name no witness in the registry: a pseudo-volume cannot be scoped, `witnesses.witness_of`
    raises on the id, and the honest answer to "what may this witness attest?" is that it is not a
    witness. Pass `heldout=True` only to AUDIT those files, never to score with them.

    ⚠️ MEASURED, so the exclusion is not overstated: all 12 held-out artefacts currently hold **zero
    verses**, so no consumer's figures move by excluding them and nothing here fixes a live defect. The
    exclusion is a guard against the state where that run mode is used again, not a correction of one.
    (The pseudo-volumes DID reach the file-COUNTING audits, which is a separate open item.)
    """
    out = []
    for p in sorted(HERE.glob(".corpus-localize-*.json")):
        name = p.name[len(".corpus-localize-"):-len(".json")]
        if name.endswith(".heldout") != heldout:
            continue
        out.append(name)
    return out


def iter_localizations(*, scope_check: bool = True, announce=print):
    """Yield `(ocr_dir, artefact)` for every localized volume, Gate 0f applied -- the SWEEP route.

    A sweep cannot simply raise on the first inadmissible witness (it would report nothing at all) and it
    must not silently skip one (a dropped witness that leaves no trace is how an audit comes to describe a
    corpus it did not read). So it does what `qc_audit.scan_ocr_dirs` established as the pattern in R9.2:
    it DROPS the witness and PRINTS the drop, with the registry's own reason, ABOVE the figures the caller
    is about to produce. The reader of the output learns the corpus was narrowed; nothing has to be
    remembered for that to happen.
    """
    admitted, dropped = [], []
    for od in localized_dirs():
        if scope_check and not _W.verse_admitted(od):
            vol, sig = _W.witness_of(od)
            dropped.append((od, _W.wid(vol, sig), _W.WITNESSES[(vol, sig)]["role"]))
        else:
            admitted.append(od)
    # Resolved BEFORE the first yield, deliberately: a generator that announced its drops after the loop
    # would print them below the figures they qualify, and a caveat that arrives after the number it
    # qualifies has already been read is not a caveat.
    if dropped and announce:
        announce(f"[Gate 0f] {len(dropped)} localized volume(s) DROPPED from this sweep -- verse_scope "
                 f"'none', their text is not evidence at any grain (OCR-MASTERPLAN.md 2):")
        for od, w, role in dropped:
            announce(f"          {od:28} {w:12} role {role!r}")
    for od in admitted:
        yield od, load_raw(od, scope_check=scope_check)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("ocr_dirs", nargs="*")
    ap.add_argument("--books", default=",".join(PILOT_BOOKS))
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    books = [b for b in a.books.split(",") if b]
    dirs = a.ocr_dirs or [p.name.replace(".page-address-", "").replace(".json", "")
                          for p in sorted(HERE.glob(".page-address-*.json"))]
    for d in dirs:
        print(f"[localize] {d}", flush=True)
        localize_volume(d, books, limit=a.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
