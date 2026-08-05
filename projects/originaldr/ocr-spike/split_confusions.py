# -*- coding: utf-8 -*-
"""WHAT THE SPLIT VERSES SAY — the recognizer's own error modes, read off its siblings.

A SPLIT verse is one some witnesses pass and others fail. That makes it the most informative case in the
corpus and the exact complement of the all-fail set:

    ALL-FAIL  → no witness can read it → the defect is VERTICAL (addressing, pinning, reference, gating)
    SPLIT     → a sibling DID read it  → the defect is HORIZONTAL, and the sibling supplies the answer

Because a passing witness is by definition within 0.90 of the archaic reference, its text can stand as the
correct reading for the failing witness's *same verse of the same edition*. Aligning the two gives the
recognizer's substitutions directly, without gold and without a human transcription — the failing volume is
graded against its own twin.

WHAT THIS IS NOT. It is not a correction mechanism. Nothing here rewrites a failing witness with its sibling's
text: that would manufacture agreement between independent copies and destroy the very redundancy the whole
audit depends on. The output is a DIAGNOSIS — which glyph pairs the recognizer confuses, how often, and
whether the confusions concentrate in one volume — so that a recognizer or post-correction pass can be aimed
at something real.

Usage:  python split_confusions.py genesis [--out split-confusions-genesis.json]
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import book_audit as BA                      # noqa: E402
import verse_seg as VS                       # noqa: E402


def _words(s: str) -> list[str]:
    return (s or "").split()


def analyse(book: str) -> dict:
    rep = BA.audit_book(book)
    wits = rep["witnesses"]
    aud = json.loads((HERE / "coverage-audit-verse.json").read_text())["verses"]
    loc = {s: json.loads((HERE / f".corpus-localize-{d}.json").read_text())["verses"]
           for s, d in wits.items()}

    char_conf = collections.Counter()          # (from, to) at character grain, failing -> passing
    word_conf = collections.Counter()          # whole-token substitutions
    fail_count = collections.Counter()         # which witness is the one failing
    pass_count = collections.Counter()
    minority = collections.Counter()           # verses where exactly ONE witness fails
    n_split = 0
    lengths = collections.defaultdict(list)

    for ch in range(1, rep["n_chapters"] + 1):
        for v in (VS.chapter_verses(book, ch, VS.JANVIER) or {}):
            r = aud.get(f"scripture/{book}/{ch}/{v}")
            if not r:
                continue
            got = [s for s in wits if (r["sources"].get(s) or {}).get("localized")]
            ok = [s for s in got if (r["sources"][s] or {}).get("passed")]
            bad = [s for s in got if s not in ok]
            if not ok or not bad:
                continue
            n_split += 1
            for s in bad:
                fail_count[s] += 1
            for s in ok:
                pass_count[s] += 1
            if len(bad) == 1:
                minority[bad[0]] += 1
            # reference reading = the PASSING sibling with the highest archaic_id
            best = max(ok, key=lambda s: (r["sources"][s] or {}).get("archaic_id") or 0)
            ref = (loc[best].get(f"{book}/{ch}/{v}") or {}).get("text", "")
            for s in bad:
                got_t = (loc[s].get(f"{book}/{ch}/{v}") or {}).get("text", "")
                if not got_t or not ref:
                    continue
                lengths[s].append(len(_words(got_t)) / max(1, len(_words(ref))))
                a, b = _words(ref), _words(got_t)
                for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
                    if tag != "replace":
                        continue
                    for wa, wb in zip(a[i1:i2], b[j1:j2]):
                        if wa == wb:
                            continue
                        word_conf[(wa, wb)] += 1
                        # character grain inside the substituted pair
                        for t2, k1, k2, l1, l2 in difflib.SequenceMatcher(None, wa, wb).get_opcodes():
                            if t2 == "replace" and (k2 - k1) <= 2 and (l2 - l1) <= 2:
                                char_conf[(wa[k1:k2], wb[l1:l2])] += 1
    return {
        "book": book, "n_split": n_split, "witnesses": wits,
        "fails_in_split": dict(fail_count), "passes_in_split": dict(pass_count),
        "sole_failer": dict(minority),
        "length_ratio_vs_passing_sibling": {s: round(statistics.mean(x), 4) for s, x in lengths.items() if x},
        "char_confusions": [{"from": a, "to": b, "n": n} for (a, b), n in char_conf.most_common(40)],
        "word_confusions": [{"from": a, "to": b, "n": n} for (a, b), n in word_conf.most_common(30)],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    r = analyse(a.book)
    (Path(a.out) if a.out else HERE / f"split-confusions-{a.book}.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=1))
    print(f"=== SPLIT-VERSE DIAGNOSIS — {a.book.upper()} · {r['n_split']} split verses ===\n")
    print("who fails when the witnesses disagree (a high SOLE column is a volume-specific defect):")
    for s in r["witnesses"]:
        print(f"   {s:<3} fails {r['fails_in_split'].get(s,0):>4}   passes {r['passes_in_split'].get(s,0):>4}"
              f"   SOLE failer {r['sole_failer'].get(s,0):>4}"
              f"   length vs passing sibling {r['length_ratio_vs_passing_sibling'].get(s,float('nan')):.3f}")
    print("\ntop CHARACTER confusions (correct -> what the failing witness read):")
    for c in r["char_confusions"][:22]:
        print(f"   {c['from']!r:>10} -> {c['to']!r:<10} {c['n']:>5}")
    print("\ntop WHOLE-WORD confusions:")
    for c in r["word_confusions"][:12]:
        print(f"   {c['from']!r:>16} -> {c['to']!r:<16} {c['n']:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
