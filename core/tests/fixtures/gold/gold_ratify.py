#!/usr/bin/env python
"""Empirical ratification harness for the Gold Set masks.

Where ``gold_verify.py`` proves a contract is internally *consistent* (anchors
resolve uniquely, masks match the taxonomy), THIS tool produces the evidence a
human needs to judge the contract *correct* — accuracy AND precision:

  * PRECISION — every declared span is resolved and the REAL text at each
    boundary is printed (±context), so bleed / mid-word / off-by-a-heading
    errors are eye-checkable.
  * ACCURACY  — every repeating ``expected_count`` is re-derived from raw
    evidence by an INDEPENDENT route, never trusted from the contract:
      - the full EPUB heading track (``_layout_boundaries``) is dumped, so
        nav-derived counts (Bible chapters, Roman-numeral chapters) are checked
        against the actual nav labels (incl. source corruptions);
      - text-derived counts (epistolary salutations) are re-counted by regex.
    Declared vs nav vs text-recount are reconciled and mismatches FLAGGED.

Run from a machine with the eval harness + ingested-workspace cache.

Usage:
  gold_ratify.py            # ratify all gold works
  gold_ratify.py <idx>      # ratify one work
  gold_ratify.py --full     # show every heading-track label (not just a sample)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # core/tests/fixtures/gold
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "core"))
sys.path.insert(0, str(REPO / ".scratch" / "mask-eval"))

from harness import project_for  # noqa: E402

from palimpsest.layout import (  # noqa: E402
    DEFAULT_MASK_BY_TYPE,
    detect_layout_sections,
)
from palimpsest.masking import _endnote_separator, _layout_boundaries  # noqa: E402

GOLD = HERE

# Roman numeral, possibly with FUSED trailing digits from endnote refs
# (the idx70 'XXI11' / 'XXXI18' corruption). Captures the roman + the junk.
_ROMAN_RE = re.compile(r"^\s*((?:X{0,3})(?:IX|IV|V?I{0,3}))(\d*)\b")
# Line-start epistolary salutation: "Dear X," / "My dear X," etc.
_SALUTATION_RE = re.compile(
    r"(?m)^[ \t]{0,4}(Dear|Dearest|My dear|My dearest|My darling)\b[^\n]{0,70}?,[ \t]*$"
)
# Douay apparatus heading: a line STARTING "<Book> Chapter N" (book name begins with a
# capital, so the parenthetical "(Psalm Chapter 10 ...)" note is excluded). The summary
# may run inline on the same line (Job 39) and the number may carry a trailing "." (1
# Machabees 2), so we do NOT anchor the line end.
_DOUAY_CH_RE = re.compile(r"(?m)^\s*(?:[1-4] )?[A-Z][\w’.]+(?: of [A-Z][\w’.]+)? Chapter \d+\b")
# "Book NN – <Name>" running-head form (Global Grey Challoner).
_BOOK_NN_RE = re.compile(r"(?m)^\s*Book \d+\s*[–-]\s*\S")
# A whole line that is a bare Roman numeral (poem/chapter marker). Over-counts standalone
# "I" pronoun lines — reported as a raw signal, not a clean count.
_ROMAN_LINE_RE = re.compile(r"(?m)^[ \t]*[IVXLCDM]+[ \t]*$")


def _ctx(text: str, off: int, before: int = 55, after: int = 85) -> str:
    """One-line visible-whitespace context window around an offset (┃ = the offset)."""
    lo, hi = max(0, off - before), min(len(text), off + after)
    pre = text[lo:off].replace("\n", "⏎").replace("\t", "→")
    post = text[off:hi].replace("\n", "⏎").replace("\t", "→")
    return f"…{pre}┃{post}…"


def _resolve(text: str, anchor: str, mode: str = "first") -> tuple[int, int]:
    if anchor == "<<EOF>>":
        return len(text), 1
    count = text.count(anchor)
    off = text.rfind(anchor) if mode == "last" else text.find(anchor)
    return off, count


def ratify_work(idx: int, full: bool = False) -> dict:
    doc = json.loads((GOLD / f"work-{idx}.json").read_text())
    proj = project_for(idx)
    if proj is None:
        print(f"[{idx}] NOT INGESTED — skipping")
        return {"idx": idx, "flags": ["not ingested"]}
    text = proj.reference_text()
    n = len(text)
    bnds = _layout_boundaries(proj)
    secs = detect_layout_sections(bnds, n, _endnote_separator(proj.path), text=text)
    by_type: dict[str, int] = {}
    for s in secs:
        by_type[s.type] = by_type.get(s.type, 0) + 1

    flags: list[str] = []
    print(f"\n{'='*78}\n[{idx}] {doc.get('work','?')}  ({n:,} chars)")
    print(f"  detector section types: {by_type}")
    print(f"  heading-track entries: {len(bnds)}")

    # ── raw nav evidence: roman-numeral headings (+ corruption) ──────────────
    roman_labels = []
    for (_s, _e, label) in bnds:
        m = _ROMAN_RE.match(label or "")
        if m and m.group(1):
            roman_labels.append((label, m.group(1), m.group(2)))
    if roman_labels:
        corrupt = [lbl for (lbl, _r, junk) in roman_labels if junk]
        print(f"  nav roman-numeral headings: {len(roman_labels)}"
              + (f"  (CORRUPTED labels w/ fused digits: {corrupt})" if corrupt else ""))

    # ── raw text signals (transparent independent counters) ──────────────────
    signals = {
        "salutations": len(_SALUTATION_RE.findall(text)),
        "douay_chapter_headings": len(_DOUAY_CH_RE.findall(text)),
        "book_nn_dash": len(_BOOK_NN_RE.findall(text)),
        "roman_lines_raw": len(_ROMAN_LINE_RE.findall(text)),
        "nav_roman_headings": len(roman_labels),
        "detector_chapter": by_type.get("chapter", 0),
        "detector_book": by_type.get("book", 0),
    }
    nz = {k: v for k, v in signals.items() if v}
    print(f"  raw count signals: {nz}")

    if full:
        print("  --- full heading track ---")
        for (s, _e, label) in bnds:
            print(f"    [{s:>7}] {label!r}")

    # ── per-annotation ratification ──────────────────────────────────────────
    for a in doc.get("annotations", []):
        t = a["type"]
        role = a.get("role", "-")
        mask = a.get("mask")
        dmask = DEFAULT_MASK_BY_TYPE.get(t)
        mask_note = "" if mask == dmask else f"  ⚠ override (taxonomy default={dmask})"
        print(f"\n  ── {t}  role={role} mask={mask}{mask_note}")
        mode = a.get("resolve", "first")

        if a.get("structure") == "repeating":
            ec = a.get("expected_count")
            print(f"     declared expected_count={ec}")
            print(f"     count_cue: {a.get('count_cue','')[:200]}")
            # exemplars w/ real context
            ex_offs: list[int] = []
            for ex in a.get("exemplars", []):
                off, c = _resolve(text, ex["start_anchor"], mode)
                tag = "OK" if c == 1 else f"⚠ resolves {c}x"
                print(f"     exemplar [{tag}] {ex.get('note','')[:48]}")
                if c >= 1:
                    print(f"        {_ctx(text, off)}")
                    ex_offs.append(off)
                if c != 1:
                    flags.append(f"idx{idx} {t}: exemplar resolves {c}x")
            # nav heading-track entries spanning first→last exemplar (titled-poem route)
            nav_in_span = 0
            if len(ex_offs) >= 2:
                lo, hi = min(ex_offs), max(ex_offs)
                nav_in_span = sum(1 for (s, _e, _l) in bnds if lo <= s <= hi)
            # independent recount reconciliation — surface every transparent
            # signal plausibly relevant to this structure; let the data reconcile.
            candidates: list[tuple[str, int]] = []
            if t == "letter":
                candidates.append(("text salutations", signals["salutations"]))
            if t in ("chapter", "chapter_heading"):
                if signals["douay_chapter_headings"]:
                    candidates.append(("'<Book> Chapter N'", signals["douay_chapter_headings"]))
                if signals["nav_roman_headings"]:
                    candidates.append(("nav roman headings", signals["nav_roman_headings"]))
            if t == "book":
                if signals["book_nn_dash"]:
                    candidates.append(("'Book NN –' headings", signals["book_nn_dash"]))
                candidates.append(("detector book sections", signals["detector_book"]))
            if t == "poetry":
                if signals["nav_roman_headings"]:
                    candidates.append(("nav roman headings", signals["nav_roman_headings"]))
                if nav_in_span:
                    candidates.append(("nav entries first→last poem", nav_in_span))
                candidates.append(("bare roman lines (over-counts)", signals["roman_lines_raw"]))
                candidates.append(("detector content sections", signals["detector_chapter"]))
            if not candidates:
                print("     INDEPENDENT recount: (no transparent route — manual)")
            else:
                for name, val in candidates:
                    if not isinstance(ec, int):
                        mark = "(declared null — signal informational)"
                    elif val == ec:
                        mark = "MATCH"
                    elif abs(val - ec) <= 2:
                        mark = f"≈ (Δ={val - ec:+d})"
                    else:
                        mark = f"MISMATCH (Δ={val - ec:+d})"
                    print(f"     recount[{name}] = {val}  → {mark} vs declared {ec}")
                # flag only when NO candidate lands within ±2 of an integer declared
                # count. role=secondary levels are grouping (reported, not rated) and
                # are often canon/nav-derived with no clean text cue → informational.
                if isinstance(ec, int) and all(abs(v - ec) > 2 for _, v in candidates):
                    sig = f"({{ {', '.join(f'{n}={v}' for n, v in candidates)} }})"
                    if role == "secondary":
                        print(f"     NOTE: no transparent text signal for this secondary "
                              f"grouping level — count is canon/nav-grounded {sig}")
                    else:
                        flags.append(
                            f"idx{idx} {t}: declared {ec}, no transparent signal within ±2 {sig}"
                        )
        else:
            so, sc = _resolve(text, a["start_anchor"], mode)
            eo, ec = _resolve(text, a["end_anchor"], mode) if a.get("end_anchor") else (n, 1)
            ok = sc == 1 and (a.get("end_anchor") in (None, "<<EOF>>") or ec == 1)
            print(f"     span [{so},{eo}] len={eo-so}  resolve(start={sc}x,end={ec}x)"
                  + ("" if ok else "  ⚠ NON-UNIQUE"))
            print(f"     START {_ctx(text, so)}")
            print(f"     END   {_ctx(text, eo)}")
            if not ok:
                flags.append(f"idx{idx} {t}: anchor non-unique (start {sc}x end {ec}x)")
            if sc == 1 and not (0 <= so < eo <= n):
                flags.append(f"idx{idx} {t}: malformed span [{so},{eo}]")

    return {"idx": idx, "flags": flags}


def main() -> None:
    full = "--full" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    idxs = [int(args[0])] if args else sorted(
        int(p.stem.split("-")[1]) for p in GOLD.glob("work-*.json")
    )
    all_flags: list[str] = []
    for idx in idxs:
        r = ratify_work(idx, full=full)
        all_flags += r.get("flags", [])
    print(f"\n{'='*78}\nRATIFICATION FLAGS ({len(all_flags)}):")
    for f in all_flags:
        print(f"  ⚠ {f}")
    if not all_flags:
        print("  (none — every span resolved uniquely and every recountable count matched)")


if __name__ == "__main__":
    main()
