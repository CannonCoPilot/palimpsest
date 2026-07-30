#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s_lexicon.py — an ATTESTED ſ lexicon per edition, built from the human ground truth (2026-07-29).

THE PROBLEM IT SOLVES. `s_arbiter` can only close a verse's ſ surface with an OBSERVATION, and the only
observation it has is R2's reading of that same verse. Where R2 dropped a word or misread it badly, R3's token
has no attested surface and the cell stays OPEN — `1 ſ kept, 2 unresolved: therefore, seventh`. Across two
worked chapters that cost 44 hand-reads (§13 Q35); across fifty it is ~1,000, which does not scale.

WHAT THIS IS, AND WHY IT IS NOT `long_s_rule.restore_long_s`. The rejected rule GUESSED from position (~90.4%
accurate — about one invented glyph in ten published as the printed surface). This is not a rule and does not
guess: it is a COUNT OF OBSERVATIONS from `ground-truth/`, the 2,611 hand-transcribed diplomatic lines, keyed by
EDITION because the editions differ (`shal`/`she` are ROUND in 1609 and LONG in 1635 — the project measured
that). A word is answered only where the human transcriptions are overwhelmingly consistent about it; anything
else is left for an eye, exactly as before.

THE GUIDELINES WARN THAT THE SAME WORD IS SET BOTH WAYS ON ONE PAGE, so a lexicon can be wrong in an individual
instance. That is why:
  * it reports its own accuracy on HELD-OUT GT lines rather than asserting it (`--validate`), and
  * a closure it supplies is provenanced `ſ-lexicon`, never `R2-observed`, so it is auditable and ablatable, and
  * `MIN_OBS` / `MIN_AGREE` are deliberately strict: a word with a real minority form is NOT answered.

Usage:
  ../ocr-venv/bin/python s_lexicon.py --build --validate
  ../ocr-venv/bin/python s_lexicon.py --lookup therefore --edition 1609
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

GT = HERE / "ground-truth"
OUT = HERE / ".s-lexicon.json"
MIN_OBS = 4              # a word must be attested this many times in the edition before it is answered
MIN_AGREE = 0.97         # ...and this consistently. A word with a genuine minority form stays unanswered.
_WORD = re.compile(r"[A-Za-zſ]+")

# Which edition each witness directory is. The 1609 first edition and the 1635 second edition set ſ differently,
# so the lexicon is keyed by edition and never pooled across them.
EDITION = {
    "archive-ot1-1609": 1609, "pdf-S03a": 1609, "archive-holiebible-ot1": 1609,
    "archive-ot2-1610": 1609, "archive-nt-1582": 1582,
    "jp2-S06": 1635, "jp2-S04": 1635, "jp2-S08": 1635, "jp2-S09ot2": 1635,
    "pdf-S03b": 1609, "pdf-S09nt": 1635,
}


def excluded(word: str) -> str | None:
    """Words the lexicon must REFUSE to answer, on the guidelines' own evidence rather than on this test's errors.

    1. ALL-CAPS / display words. There is no capital long-ſ, so `EPIST` and `GOSPEL` can never take one — yet a
       lexicon keyed on the lowercase skeleton happily returns `Epiſt`/`Goſpel`. Refuse anything with no
       lowercase letters.
    2. The `sh` CLUSTER. `ground-truth/GUIDELINES.md` §long-ſ states outright that this compositor mixes forms
       here and that the SAME word (`shal`) appears both ways ON ONE PAGE — `shal ſay`, `she shal anſwere`. A
       count over a page that sets it both ways cannot answer an instance, so `shew`/`ſhe`/`shal` are left to an
       eye. This is the one place a majority is known to be the wrong instrument."""
    if not any(c.islower() for c in word):
        return "display capitals: there is no capital long-ſ"
    if re.search(r"[sſ]h", word, re.I):
        return "sh cluster: §long-ſ says this compositor mixes forms within a page"
    return None


def skel(word: str) -> str:
    """The key: the word with every s-form collapsed, lowercased. `ſeuenth`, `seuenth` and `Seventh` share a key
    only if their other letters match — the lexicon answers SPELLING OF THE s, not spelling in general."""
    return word.replace("ſ", "s").lower()


def build() -> dict:
    """{edition: {skeleton: {form: count}}} over every hand-transcribed body line."""
    table: dict[str, dict[str, collections.Counter]] = {}
    files = 0
    for f in sorted(GT.glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:                                        # noqa: BLE001
            continue
        ed = EDITION.get(d.get("ocr_dir") or "")
        if not ed:
            continue
        files += 1
        for b in (d.get("body") or []):
            if b.get("role") in ("catchword", "signature"):
                continue
            for w in _WORD.findall(b.get("text") or ""):
                if "s" not in w.lower() and "ſ" not in w:
                    continue
                if excluded(w):
                    continue
                table.setdefault(str(ed), {}).setdefault(skel(w), collections.Counter())[w] += 1
    return {"files": files,
            "table": {ed: {k: dict(v) for k, v in t.items()} for ed, t in table.items()}}


def decide(table: dict, edition: int, word: str) -> tuple[str | None, dict]:
    """The attested form of `word` in this edition, or None if the evidence does not answer it."""
    t = (table.get("table") or {}).get(str(edition)) or {}
    why = excluded(word)
    if why:
        return None, {"reason": why}
    counts = t.get(skel(word))
    if not counts:
        return None, {"reason": "unattested"}
    total = sum(counts.values())
    form, n = max(counts.items(), key=lambda kv: kv[1])
    ev = {"total": total, "top": form, "top_n": n, "agree": round(n / total, 4), "forms": counts}
    if total < MIN_OBS:
        return None, {**ev, "reason": f"only {total} observations (need {MIN_OBS})"}
    if n / total < MIN_AGREE:
        return None, {**ev, "reason": f"forms disagree ({n}/{total})"}
    # PRESERVE THE QUERY'S OWN CASE: the lexicon answers where the ſ goes, not whether a word is capitalised.
    if word[:1].isupper():
        form = form[:1].upper() + form[1:]
    return form, ev


def validate(table: dict, holdout_every: int = 4) -> None:
    """Score the lexicon on HELD-OUT GT lines: build from 3/4 of the files, test on the rest.

    The question is narrow and is the only one that matters for closure: given a word whose s-placement the
    lexicon claims to know, does it produce the form the human transcribed?"""
    files = [f for f in sorted(GT.glob("*.json")) if EDITION.get(
        (json.loads(f.read_text()).get("ocr_dir") or ""), None)]
    test = set(files[::holdout_every])
    tr: dict[str, dict[str, collections.Counter]] = {}
    for f in files:
        if f in test:
            continue
        d = json.loads(f.read_text())
        ed = str(EDITION[d["ocr_dir"]])
        for b in (d.get("body") or []):
            if b.get("role") in ("catchword", "signature"):
                continue
            for w in _WORD.findall(b.get("text") or ""):
                if "s" not in w.lower() and "ſ" not in w or excluded(w):
                    continue
                tr.setdefault(ed, {}).setdefault(skel(w), collections.Counter())[w] += 1
    trained = {"table": {ed: {k: dict(v) for k, v in t.items()} for ed, t in tr.items()}}
    ok = bad = unans = 0
    wrong: list[tuple[str, str]] = []
    for f in sorted(test):
        d = json.loads(f.read_text())
        ed = EDITION[d["ocr_dir"]]
        for b in (d.get("body") or []):
            if b.get("role") in ("catchword", "signature"):
                continue
            for w in _WORD.findall(b.get("text") or ""):
                if "s" not in w.lower() and "ſ" not in w:
                    continue
                got, _ev = decide(trained, ed, w)
                if got is None:
                    unans += 1
                elif got == w or got.lower() == w.lower():
                    ok += 1
                else:
                    bad += 1
                    if len(wrong) < 14:
                        wrong.append((w, got))
    n = ok + bad
    print(f"\n=== VALIDATION on {len(test)} held-out GT files ===")
    print(f"  answered {n} s-bearing tokens, left {unans} unanswered ({unans/(n+unans):.1%} of them)")
    if n:
        print(f"  CORRECT {ok}/{n} = {ok/n:.4f}   wrong {bad}")
    print(f"  (for scale: `long_s_rule.restore_long_s`, the REJECTED positional rule, measured ~0.904)")
    for w, g in wrong:
        print(f"    human {w!r} -> lexicon {g!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--lookup")
    ap.add_argument("--edition", type=int, default=1609)
    a = ap.parse_args()
    if a.build or not OUT.exists():
        t = build()
        OUT.write_text(json.dumps(t, ensure_ascii=False))
        n = sum(len(v) for v in t["table"].values())
        print(f"built from {t['files']} GT files: {n} word-keys across editions "
              f"{sorted(t['table'])} -> {OUT.name}")
    table = json.loads(OUT.read_text())
    if a.lookup:
        form, ev = decide(table, a.edition, a.lookup)
        print(f"{a.lookup!r} in {a.edition}: {form!r}  {ev}")
    if a.validate:
        validate(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
