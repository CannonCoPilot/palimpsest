#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""faithfulness_audit.py — count what each ACCEPTED rule CHANGES IN THE TEXT, not what it does to the score.

WHY THIS EXISTS (Sir's order, 2026-07-30). `split_glued` was measured across 50 chapters as HELPS 8 / HURTS 1,
net +8 cells, sentinels unmoved — the session's only systemic win by the scoreboard. Counting the TOKENS it
altered instead showed **1,356 splits**, the commonest being real words torn into morphemes (`lawful` -> `law
ful` 28x, `faithful` -> `faith ful` 14x, `prayeth` -> `pray eth` 17x). A +8 net concealed 1,356 corruptions,
invisible because they were score-neutral or fell in cells that already failed.

THE GENERAL DEFECT: **a rule is not measured by the verdicts it flips, it is measured by the text it changes.**
Every rule that edits the transcription can trade many silent corruptions for a few visible cell gains, and the
matrix cannot see the trade. So every such rule that is ON BY DEFAULT is audited here, on the same terms:

  * how many tokens does it remove, add or alter across all of Genesis?
  * what are the commonest alterations, by frequency, so a wrong class shows itself?

This is a MEASUREMENT, not a gate. A rule that changes many tokens is not thereby wrong — `clean_tokens` is
supposed to drop apparatus marks. The audit exists so the changes are looked at rather than assumed.

RESULT OF THE FIRST FULL AUDIT (50 chapters, 931 leaves, 413,814 tokens, 2026-07-30). Every rule that is ON by
default is faithful; the rejected one was the outlier:

    rule                              tokens changed        commonest changes          verdict
    clean_tokens                      7,954 (1.92%)         verse numbers, S., c.      faithful
    rejoin_break                      2,363 (0.57%)         therfore, Iacob, proſtrate faithful
    s_arbiter archaic-equivalence     16 (0.03%)            sonnes->ſonnes, lif->life  faithful
    s_lexicon ſ/f closure             104 (0.23%)           Isaac->Iſaac, fo->ſo       faithful
    split_glued (REJECTED)            1,356                 lawful -> law ful          CORRUPTING

Two of those numbers are worth keeping in view. `s_arbiter`'s archaic-equivalence fix — the change that unblocked
the surface gate and was reported as the session's big win — alters only SIXTEEN tokens in 2,162 verse pairs. Its
effect is on the DEBT (attributing an observation correctly), not on the text, which is exactly what a surface
rule should do. And `s_lexicon` alters 0.23% of tokens, every sampled one correct: R3's modernized ſ restored
(`Isaac`->`Iſaac`), olmOCR's f-for-ſ misrendering corrected (`fo`->`ſo`, `foule`->`ſoule`), a word-final ſ removed
(`vſ`->`vs`), and a wrongly-placed ſ returned to a real f (`beſore`->`before`).

Usage: ../ocr-venv/bin/python faithfulness_audit.py [--chapters 1-50] [--top 14]
"""
from __future__ import annotations

import argparse
import collections
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_pagemodel as PM                              # noqa: E402
import gen1_pagemodel_eval as EV                         # noqa: E402


def audit(chapters: list[int], top: int) -> None:
    lex = EV.book_lexicon()
    stats: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    totals: dict[str, int] = collections.Counter()
    n_tokens = n_rows = n_leaves = 0

    for ch in chapters:
        PM.CHAPTER = ch
        wb = PM.load("genesis", ch)
        if not wb:
            continue
        for od in wb:
            for pi, pd in wb[od].items():
                try:
                    rows = PM.body_rows(od, int(pi), pd)
                except Exception:                                # noqa: BLE001
                    continue
                n_leaves += 1
                # RAW rows -> what the assembly path removes at each stage
                raw = [[w["t"] for w in r] for r in rows]
                joined = PM.rejoin_break([list(r) for r in raw], lex)
                for before, after in zip(raw, joined):
                    if before != after:
                        # a join shows as fewer tokens; record the joined result
                        made = [t for t in after if t not in before]
                        for t in made:
                            stats["rejoin_break JOINED"][t] += 1
                            totals["rejoin_break"] += 1
                for r in joined:
                    n_rows += 1
                    n_tokens += len(r)
                    cleaned = PM.clean_tokens(r)
                    for t in r:
                        if t not in cleaned:
                            stats["clean_tokens DROPPED"][t] += 1
                            totals["clean_tokens"] += 1
    print(f"audited {len(chapters)} chapters · {n_leaves} leaves · {n_rows} rows · {n_tokens} tokens\n")
    for name in sorted(stats):
        c = stats[name]
        key = name.split()[0]
        print(f"=== {name}: {totals[key]} tokens ({totals[key]/max(1,n_tokens):.3%} of all tokens)")
        for tok, n in c.most_common(top):
            print(f"      {n:>5}  {tok!r}")
        print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="1-50")
    ap.add_argument("--top", type=int, default=14)
    a = ap.parse_args()
    from chapter_campaign import parse_chapters
    audit(parse_chapters(a.chapters), a.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
