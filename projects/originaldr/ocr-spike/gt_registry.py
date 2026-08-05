#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gt_registry.py — ONE canonical registry of the ground-truth set, derived from the GT files themselves.

WHY THIS EXISTS (found 2026-07-27 when Sir asked "is GT-3 really only 15 pages?"). It was not. Three separate
hand-maintained `LOCI` dicts had drifted apart, and each harness silently measured a DIFFERENT subset while
printing its subset's number as "the" number:

    gate_calibrate.LOCI   14 entries   — never saw scripture-2john or scripture-colossians-3
    reocr_lift.LOCI       15 entries   — never saw scripture-abdias-01
    r3_stats              inherits gate_calibrate's

`scripture-abdias-01` is a completed, Sir-reviewed GT page that was excluded from every lift number I reported,
because a dict I hand-typed lacked one line. The harness printed "no book/page" and moved on. **A skipped input
that reports as a blank line is indistinguishable from an input that passed** — the same silent-degradation
class the ledger exists to prevent, applied to the measuring apparatus.

THE FIX IS TO STOP HAND-MAINTAINING IT. Every GT file already carries `locus: "scripture/<book>/<chapter>"`
plus `ocr_dir` and `page_index`, so the mapping was always in the data. This module reads it, and a GT file
that cannot be mapped RAISES instead of being skipped.

    records()     -> [GTRecord] for the requested kinds (scripture / matter / nt)
    loci()        -> {slug: book}, the drop-in replacement for the old LOCI dicts
    audit()       -> the full inventory, including what is NOT reachable and why
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
GT = HERE / "ground-truth"
RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/mask_engine/"
             "originaldr_reconstruction")

# CANONICAL BOOK SLUGS come from the skeleton — the same oracle `validate_completeness` uses. A GT `locus`
# writes the book by hand ("2john"), and the canon spells it "2-john"; resolving that by a plain dict lookup
# fails SILENTLY and drops the page, which is the exact defect this module exists to remove. So the mapping is
# validated against the canon and an unresolvable book RAISES.
_CANON = [b["slug"] for b in json.loads((RECON / "skeleton.json").read_text())["books"]]
_CANON_KEY = {re.sub(r"[^a-z0-9]", "", b.lower()): b for b in _CANON}


def canonical_book(token: str) -> str:
    """Canonical book slug for a GT locus token; raises if it does not resolve to a book in the skeleton."""
    key = re.sub(r"[^a-z0-9]", "", (token or "").lower())
    if key in _CANON_KEY:
        return _CANON_KEY[key]
    raise ValueError(f"GT book token {token!r} does not resolve to any canonical book slug "
                     f"(normalised {key!r}). Fix the GT locus or extend the canon — do not skip it.")

# Backups and editor artifacts are NOT ground truth; they are prior states kept for provenance.
_SKIP_SUFFIX = (".pre-review", ".pre-vvfix", ".pre-P0", ".pre-gt2", ".bak")
# Live locus forms in the GT: "scripture/<book>/<ch>", "matter/<vol>/<name>", "nt/<book>/<part>#p<NN>".
# The '#p' fragment is a legitimate page qualifier, not a defect.
# A chapter token may be "16", "115+116" (a genuinely multi-chapter page), or absent.
_LOCUS = re.compile(r"^(scripture|matter|apparatus|nt)/([^/#]+)(?:/([^#]*))?(?:#.*)?$")
# Three matter files carry a HYPHEN locus ("matter-nt-table") instead of a path. That is malformed data, but
# the slug encodes the same information, so the registry NORMALISES it and FLAGS that it did — rather than
# silently rewriting Sir-reviewed GT files, or dropping three real sections.
_SLUG_LOCUS = re.compile(r"^(scripture|matter|apparatus|nt)-([^-]+)-(.+)$")


@dataclass(frozen=True)
class GTRecord:
    slug: str
    kind: str              # scripture | matter | apparatus
    book: str              # book slug for scripture; section slug for matter
    chapter: int | None    # declared chapter (None for matter / chapter-less sections)
    ocr_dir: str | None
    page_index: int | None
    pages: tuple           # every declared page (multi-page sections declare a list)
    path: Path
    locus_normalized: bool = False   # True = locus was salvaged from the slug; the GT file wants fixing
    chapters: tuple = ()             # every chapter the locus declares ("115+116" -> (115, 116))


def _pages(d: dict) -> tuple:
    """Declared pages, normalised. `page_index` is a LIST on multi-page matter sections and a scalar on
    single-page scripture — both shapes are live in the GT, so both are accepted here rather than one of them
    crashing (or worse, being skipped) in every consumer."""
    for key in ("pages", "page_index"):
        p = d.get(key)
        if isinstance(p, list):
            return tuple(int(x) for x in p if str(x).lstrip("-").isdigit())
        if p is not None and str(p).lstrip("-").isdigit():
            return (int(p),)
    return ()


def _load(path: Path) -> GTRecord:
    d = json.loads(path.read_text())
    slug = path.stem
    locus = (d.get("locus") or "").strip()
    m = _LOCUS.match(locus)
    normalized = False
    if not m:
        m = _SLUG_LOCUS.match(slug)          # hyphen-locus salvage (see _SLUG_LOCUS)
        normalized = bool(m)
    if not m:
        # FAIL LOUD. A GT file with no parseable locus cannot be scored, and skipping it silently is exactly
        # the defect this module was written to remove.
        raise ValueError(f"{slug}: unmappable GT — locus={locus!r}. Fix the GT file; do not skip it.")
    kind, book, ch = m.group(1), m.group(2), m.group(3)
    pages = _pages(d)
    chapters = tuple(int(x) for x in re.findall(r"\d+", ch or ""))
    ch = chapters[0] if chapters else None
    if kind == "scripture":
        book = canonical_book(book)          # validated, never a silent miss
    return GTRecord(slug=slug, kind=kind, book=book, chapter=int(ch) if ch else None,
                    ocr_dir=d.get("ocr_dir"), page_index=(pages[0] if pages else None),
                    pages=pages, path=path, locus_normalized=normalized, chapters=chapters)


def records(kind: str | tuple = "scripture", *, require_page: bool = True) -> list[GTRecord]:
    """Every GT record of the requested kind(s). `require_page` keeps only records a page harness can score."""
    kinds = (kind,) if isinstance(kind, str) else tuple(kind)
    out = []
    for f in sorted(GT.glob("*.json")):
        if f.name.endswith(_SKIP_SUFFIX) or any(s in f.name for s in _SKIP_SUFFIX):
            continue
        r = _load(f)
        if r.kind not in kinds:
            continue
        if require_page and (r.ocr_dir is None or not r.pages):
            continue
        out.append(r)
    return out


def loci(kind: str = "scripture") -> dict:
    """{slug: book} — the drop-in replacement for the three divergent hand-typed LOCI dicts."""
    return {r.slug: r.book for r in records(kind)}


def audit() -> dict:
    """Full inventory INCLUDING what is unreachable and why — so the size of the GT set is never guessed."""
    all_recs, unreachable, malformed = [], [], []
    for f in sorted(GT.glob("*.json")):
        if f.name.endswith(_SKIP_SUFFIX) or any(s in f.name for s in _SKIP_SUFFIX):
            continue
        try:
            r = _load(f)
        except ValueError as e:
            # audit REPORTS every defect (records() still refuses) — one malformed file must not hide the rest.
            malformed.append(str(e))
            continue
        all_recs.append(r)
        if r.ocr_dir is None or not r.pages:
            unreachable.append({"slug": r.slug, "kind": r.kind,
                                "why": "no ocr_dir" if r.ocr_dir is None else "no declared page"})
    by_kind: dict = {}
    for r in all_recs:
        k = by_kind.setdefault(r.kind, {"files": 0, "pages": 0, "books": set()})
        k["files"] += 1
        k["pages"] += len(r.pages)
        k["books"].add(r.book)
    return {"total_files": len(all_recs),
            "total_declared_pages": sum(len(r.pages) for r in all_recs),
            "by_kind": {k: {"files": v["files"], "pages": v["pages"], "distinct_books": len(v["books"])}
                        for k, v in sorted(by_kind.items())},
            "unreachable": unreachable, "malformed": malformed,
            "locus_normalized": [r.slug for r in all_recs if r.locus_normalized]}


if __name__ == "__main__":
    a = audit()
    print(json.dumps(a, indent=1))
    scr = records("scripture")
    print(f"\nscripture records reachable by a page harness: {len(scr)}")
    for r in scr:
        print(f"  {r.slug:30} {r.book:12} ch={r.chapter} {r.ocr_dir} p{r.page_index}")
    # SELF-CHECK: the registry must be a strict SUPERSET of every hand-typed dict it replaces.
    ok = True
    try:
        import gate_calibrate as gc
        import reocr_lift as rl
        mine = set(loci())
        for name, old in (("gate_calibrate", set(gc.LOCI)), ("reocr_lift", set(rl.LOCI))):
            missing = old - mine
            gained = mine - old
            print(f"\nvs {name}: registry gains {sorted(gained)}; would LOSE {sorted(missing) or 'nothing'}")
            ok &= not missing
    except Exception as e:                                  # noqa: BLE001
        print("comparison skipped:", e)
    print("SELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
