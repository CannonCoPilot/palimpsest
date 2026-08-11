#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_diagnose.py — why do the residual failures fail? Per-source, per-book, then pooled (2026-07-27).

Stage 1 moved `pass_rate_archaic` 0.1291 -> 0.5133, so the remaining question stops being "does the pipeline
work" and becomes "what exactly is still wrong, and is it one thing or many". This answers the five diagnostic
questions Sir set, each per-source AND per-book AND pooled, from the audit artifact plus the localized text:

  A  REGRESSION   the 4,174 locus×source pairs the hybrid attests that `detect_book` did not — and the 694 of
                  them that were PASSING before. A verse the old localizer found and the new one does not is a
                  loss whatever the aggregate says.
  B  SUB-0.2      verses scoring under 0.2 identity. Near-zero is not "a bad reading" — a bad reading of the
                  right text still scores ~0.6 — so these are structural: nothing found, or the wrong text.
  C  SPLIT-AXIS   >0.9 modern & <0.8 archaic, and <0.8 modern & >0.9 archaic. The two references disagree
                  about the same OCR, which means one of the two REFERENCES is wrong for that locus, not the
                  OCR — the most expensive class of false alarm.
  D  ABSENT       why S3 shows nothing for psalms and S9 nothing for genesis.
  E  RED CHAPTERS every chapter with no passing scan: localized-but-far-below vs not-localized, with the
                  dominant cause named per chapter.

Nothing here re-runs OCR; it reads `coverage-audit-verse.json` + `.corpus-localize-*.json`.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verse_seg as VS               # noqa: E402
import corpus_localize as CL         # noqa: E402

AUDIT = HERE / "coverage-audit-verse.json"
BASE = HERE / "coverage-audit-verse.json.detect-baseline"
_W = re.compile(r"[A-Za-zſ]+")


def pairs(path: Path) -> dict:
    d = json.loads(path.read_text())
    out = {}
    for locus, rec in d["verses"].items():
        for wid, r in (rec.get("sources") or {}).items():
            if r.get("kind") == "scan":
                out[(locus, wid)] = r
    return out


def _split(locus: str):
    p = locus.split("/")
    return p[1], int(p[2]), int(p[3])


def _texts() -> dict:
    """{(ocr_dir, book, ch, v): text} for every localized span — the evidence behind a score.

    R9.2c. This was a bare `HERE.glob(".corpus-localize-*.json")`, which is the shape the R9.2c guard
    exists to catch: it is a SWEEP, so it cannot raise on the first inadmissible witness, but skipping
    one silently would let this diagnosis describe a corpus it did not read. `iter_localizations` drops
    the `none`-scope volumes and PRINTS the drop above the tables below — the pattern `qc_audit` set.

    It also stops the glob swallowing the `.heldout` pseudo-volumes (`archive-ot2-1610.heldout` was
    arriving here as if it were a witness) — though MEASURED, all 12 of those artefacts hold zero
    verses, so that half changes no figure here. See `corpus_localize.localized_dirs`.

    PAIRED MEASUREMENT, same tree, only the gate differing: 27,816 spans over 12 `ocr_dir`s -> 21,437
    over 10. The two dropped are `jp2-S06ot` (4,045) and `jp2-S08` (2,334); every span of every
    surviving volume is identical (21,437 compared). The gate removed evidence it was meant to remove
    and touched nothing else.
    """
    out = {}
    for _od, d in CL.iter_localizations():
        for key, rec in d["verses"].items():
            b, c, v = key.rsplit("/", 2)
            out[(d["ocr_dir"], b, int(c), int(v))] = rec
    return out


def _tab(rows: list, keyfn, label: str, top: int = 12):
    c = Counter(keyfn(r) for r in rows)
    print(f"    by {label}: " + " · ".join(f"{k}={v}" for k, v in c.most_common(top)))
    return c


# ------------------------------------------------------------------ A. the coverage regression
def diagnose_regression(A: dict, B: dict, addr: dict):
    lost = [(k, A[k]) for k in set(A) - set(B)]
    lost_pass = [(k, r) for k, r in lost if r.get("passed_effective")]
    print(f"\n{'='*100}\nA. COVERAGE REGRESSION — {len(lost)} pairs lost, {len(lost_pass)} of them previously PASSING\n")
    for name, rows in (("ALL LOST", lost), ("LOST-AND-WAS-PASSING", lost_pass)):
        print(f"  {name} ({len(rows)}):")
        _tab(rows, lambda kr: kr[0][1], "source")
        _tab(rows, lambda kr: _split(kr[0][0])[0], "book")
    # Why: was the chapter inside any page's address interval for that volume?
    reach = defaultdict(set)
    for od, recs in addr.items():
        for r in recs:
            for c in r["chapters_on_page"] or []:
                reach[(od, r["book"])].add(c)
    causes = Counter()
    for k, r in lost_pass:
        book, ch, _v = _split(k[0])
        od = r.get("ocr_dir")
        causes["chapter outside every page's address interval" if ch not in reach.get((od, book), set())
               else "chapter addressed, verse not localized within it"] += 1
    print(f"\n  CAUSE of the {len(lost_pass)} lost-and-passing:")
    for c, n in causes.most_common():
        print(f"    {n:5}  {c}")
    return {"lost": len(lost), "lost_passing": len(lost_pass), "causes": dict(causes)}


# ------------------------------------------------------------------ B. the sub-0.2 set
def diagnose_sub02(B: dict, texts: dict):
    rows = [(k, r) for k, r in B.items()
            if r.get("archaic_id") is not None and r["archaic_id"] < 0.20]
    print(f"\n{'='*100}\nB. SUB-0.2 IDENTITY — {len(rows)} locus×source records\n")
    _tab(rows, lambda kr: kr[0][1], "source")
    _tab(rows, lambda kr: _split(kr[0][0])[0], "book")
    feat = Counter()
    lens = []
    for k, r in rows:
        book, ch, v = _split(k[0])
        rec = texts.get((r.get("ocr_dir"), book, ch, v))
        t = (rec or {}).get("text") or ""
        janv = VS.chapter_verses(book, ch, VS.JANVIER).get(v) or ""
        nt, nr = len(_W.findall(t)), len(_W.findall(janv))
        lens.append((nt, nr))
        if not t.strip():
            feat["EMPTY span (nothing localized)"] += 1
        elif nr and nt < 0.35 * nr:
            feat["span far SHORTER than the reference (truncated / partial)"] += 1
        elif nr and nt > 2.5 * nr:
            feat["span far LONGER than the reference (runaway / merged verses)"] += 1
        elif (rec or {}).get("fit", 0) < 0.35:
            feat["length ok but janvier_fit < 0.35 (WRONG TEXT located)"] += 1
        else:
            feat["length ok, fit ok — genuine misread"] += 1
    print("\n  SHAPE of the failure:")
    for f, n in feat.most_common():
        print(f"    {n:5} ({100*n/max(1,len(rows)):4.1f}%)  {f}")
    if lens:
        print(f"    mean span words {mean(x for x, _ in lens):.1f} vs reference {mean(y for _, y in lens):.1f}")
    return {"n": len(rows), "shape": dict(feat)}


# ------------------------------------------------------------------ C. the split-axis sets
def diagnose_split_axis(B: dict, texts: dict):
    hi_mod = [(k, r) for k, r in B.items()
              if (r.get("modern_id") or 0) > 0.9 and (r.get("archaic_id") is not None) and r["archaic_id"] < 0.8]
    hi_arc = [(k, r) for k, r in B.items()
              if (r.get("archaic_id") or 0) > 0.9 and (r.get("modern_id") is not None) and r["modern_id"] < 0.8]
    print(f"\n{'='*100}\nC. SPLIT-AXIS — the two references disagree about the SAME OCR\n")
    out = {}
    for name, rows in (("modern>0.9 & archaic<0.8", hi_mod), ("archaic>0.9 & modern<0.8", hi_arc)):
        print(f"  {name}: {len(rows)} records")
        _tab(rows, lambda kr: kr[0][1], "source")
        _tab(rows, lambda kr: _split(kr[0][0])[0], "book")
        srcs = Counter()
        for k, r in rows[:4000]:
            book, ch, v = _split(k[0])
            srcs[(json.loads(AUDIT.read_text())["verses"][k[0]].get("archaic_ref_source"),
                  json.loads(AUDIT.read_text())["verses"][k[0]].get("modern_ref_source"))] += 1
            break                                   # reference sources are per-locus and uniform; one probe
        out[name] = len(rows)
        print()
    return out


# ------------------------------------------------------------------ D. absent source×book
def diagnose_absent(B: dict, addr: dict):
    print(f"\n{'='*100}\nD. ABSENT source×book (S3/psalms, S9/genesis)\n")
    present = defaultdict(int)
    for (locus, wid), r in B.items():
        present[(wid, _split(locus)[0])] += 1
    for wid, book in (("S3", "psalms"), ("S9", "genesis"), ("S3", "genesis"), ("S9", "psalms")):
        print(f"  {wid} × {book}: {present.get((wid, book), 0)} localized verse records")
    print("\n  what the ADDRESSING found in each volume (pages assigned to that book):")
    for od, recs in sorted(addr.items()):
        c = Counter(r["book"] for r in recs)
        for book in ("psalms", "genesis"):
            if c.get(book):
                print(f"    {od:22} {book:8} {c[book]:4} pages")
    return {}


# ------------------------------------------------------------------ E. red chapters
def diagnose_red_chapters():
    d = json.loads(AUDIT.read_text())
    by_ch = defaultdict(list)
    for locus, rec in d["verses"].items():
        book, ch, _v = _split(locus)
        for wid, r in (rec.get("sources") or {}).items():
            if r.get("kind") == "scan":
                by_ch[(book, ch)].append(r)
    red = {k: rs for k, rs in by_ch.items() if not any(r.get("passed_effective") for r in rs)}
    print(f"\n{'='*100}\nE. RED CHAPTERS — {len(red)} of {len(by_ch)} chapters have NO passing scan\n")
    causes = Counter()
    detail = []
    for (book, ch), rs in sorted(red.items()):
        loc = [r for r in rs if r.get("localized")]
        ids = [r["archaic_id"] for r in loc if r.get("archaic_id") is not None]
        best = max(ids) if ids else None
        if not loc:
            cause = "NOT LOCALIZED by any source"
        elif best is None:
            cause = "localized but no archaic reference"
        elif best < 0.2:
            cause = "localized, best archaic_id < 0.2 (structural: wrong/empty text)"
        elif best < 0.7:
            cause = "localized, best archaic_id 0.2-0.7 (heavy misread)"
        else:
            cause = "localized, best archaic_id 0.7-0.9 (near miss)"
        causes[cause] += 1
        detail.append({"book": book, "chapter": ch, "n_src": len(rs), "n_localized": len(loc),
                       "best_archaic": round(best, 4) if best is not None else None, "cause": cause})
    for c, n in causes.most_common():
        print(f"    {n:5}  {c}")
    print("\n  by book:")
    bb = defaultdict(Counter)
    for x in detail:
        bb[x["book"]][x["cause"]] += 1
    for b, c in sorted(bb.items()):
        print(f"    {b:12} " + " · ".join(f"{k.split('(')[0].strip()}={v}" for k, v in c.most_common()))
    return {"n_red": len(red), "causes": dict(causes), "detail": detail}


def main():
    A = pairs(BASE) if BASE.exists() else {}
    B = pairs(AUDIT)
    addr = {}
    for f in HERE.glob(".page-address-*.json"):
        d = json.loads(f.read_text())
        addr[d["ocr_dir"]] = d["records"]
    texts = _texts()
    out = {}
    if A:
        out["regression"] = diagnose_regression(A, B, addr)
    out["sub02"] = diagnose_sub02(B, texts)
    out["split_axis"] = diagnose_split_axis(B, texts)
    out["absent"] = diagnose_absent(B, addr)
    out["red_chapters"] = diagnose_red_chapters()
    (HERE / "audit-diagnosis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n-> wrote audit-diagnosis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
