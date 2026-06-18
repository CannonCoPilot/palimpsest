#!/usr/bin/env python
"""A3 scorer — metric vector + ordinal rating for mask-detection ground truth.

Replaces the harness's scalar composite (0.3*prec + 0.3*cover + 0.2*cat +
0.2*meta) with a metric VECTOR plus a rule-based ordinal rating, so a high
cheap-rubric score can no longer hide gross mis-segmentation -- the "mirage"
the composite is structurally blind to (e.g. idx100: composite 100 over 73
book containers and ZERO chapters vs a gold of 1334).

Inputs (both pure JSON -- no detector/harness import needed):
  * gold/work-<idx>.json   -- hand-verified ground truth (co-located, tracked)
  * .scratch/mask-eval/diagnostics/work-<idx>.json -- harness detector output

The rating is a 2x2 of the cheap-rubric verdict against the ground-truth recall
verdict:
    rubric-pass + recall-pass  -> OPTIMIZED
    rubric-pass + recall-fail  -> MIRAGE          (the score lies)
    rubric-fail + recall-fail  -> COARSE
    gold declares minimal struct -> LOW-STRUCTURE  (earned, never a fallback)
with two refinements that fall forward instead of guessing:
  * Only REPEATING gold annotations (chapters/poems/letters -- a work's primary
    structure) drive the rating. SINGULAR ones (colophon/addendum) are reported
    as presence checks; a work whose only gold is singular is UNRATED-PRIMARY,
    which deliberately surfaces missing structural-contract gold rather than
    inventing a verdict.
  * When expected_count is null, recall is uncomputable, so the structure-
    PRESENCE test (does the proxy detector type appear at all?) stands in.

Detection of the 4 new mask types (chapter_heading/letter/poetry/colophon) is
deferred to Phase B, so the detector cannot emit them yet. Segmentation recall
is therefore scored through a stopgap PROXY map -- the existing detector type
each structure currently resolves to. TYPE correctness for the new types is a
known Phase-B gap, reported per annotation, not folded into the rating.

Usage:
  a3_score.py            # score every gold work, print report + write a3_scores.json
  a3_score.py <idx>      # score one work
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # core/tests/fixtures/gold
REPO = HERE.parents[3]
GOLD = HERE
DIAG = REPO / ".scratch" / "mask-eval" / "diagnostics"  # machine-local harness output

# Stopgap gold-type -> detector-type proxy. The 4 new types are not emitted yet
# (Phase B), so segmentation recall counts the existing type each structure
# currently resolves to: chapter_heading tracks chapters 1:1; poems are mis-typed
# as `chapter`; letters/colophons have no detector equivalent yet (-> recall 0).
PROXY: dict[str, list[str]] = {
    "chapter_heading": ["chapter"],
    "poetry": ["chapter"],
    "letter": [],
    "colophon": [],
    "addendum": [],
}

OPT_COMPOSITE = 90.0  # cheap-rubric "pass" line
OPT_RECALL = 0.90  # recall "pass" line
MIRAGE_RECALL = 0.50  # below this, with a passing rubric, the score is a mirage


def _found(by_type: dict, gold_type: str) -> int:
    # New types route through the stopgap proxy; existing detector types
    # (book/chapter/...) count themselves (identity) for full-contract gold.
    targets = PROXY.get(gold_type, [gold_type])
    return sum(by_type.get(t, 0) for t in targets)


def score_work(idx: int) -> dict:
    gpath = GOLD / f"work-{idx}.json"
    dpath = DIAG / f"work-{idx}.json"
    gold = json.loads(gpath.read_text())
    if not dpath.exists():
        return {"idx": idx, "work": gold.get("work", "?"),
                "error": f"no diagnostics — run: harness.py eval {idx}"}
    diag = json.loads(dpath.read_text())
    by_type = diag["by_type"]
    composite = diag["scores"]["composite"]
    text_len = diag["text_len"] or 1
    uncovered = diag["counts"].get("uncovered_chars", 0)
    big = diag.get("biggest_uncovered") or []
    largest_uncovered_frac = round(big[0]["len"] / text_len, 3) if big else 0.0

    anns: list[dict] = []
    repeating_recalls: list[float] = []  # PRIMARY level only — drives the rating
    presence_flags: list[bool] = []
    notes: list[str] = []
    has_primary_repeating = False
    for a in gold["annotations"]:
        t = a["type"]
        structure = a.get("structure")
        role = a.get("role", "primary")  # secondary = grouping level, reported not rated
        exp = a.get("expected_count")
        found = _found(by_type, t)
        rec = (found / exp) if (isinstance(exp, int) and exp) else None
        present = found > 0
        proxy = PROXY.get(t, [t])
        type_emitted = t in by_type
        anns.append({
            "type": t, "structure": structure, "role": role, "expected": exp,
            "proxy": proxy, "found": found,
            "recall": round(rec, 3) if rec is not None else None,
            "present": present, "type_emitted": type_emitted,
        })
        if structure != "repeating":
            continue
        if role == "primary":
            has_primary_repeating = True
            if rec is not None:
                repeating_recalls.append(rec)
            else:
                presence_flags.append(present)
            if found > 0 and not type_emitted:
                notes.append(f"{t}: segmented as {proxy} but detector cannot emit "
                             f"`{t}` yet (Phase-B retype gap)")
            if found == 0:
                notes.append(f"{t}: UNDETECTED (expected {exp}, proxy {proxy or '—'})")
            elif rec is not None and rec < 1.0:
                notes.append(f"{t}: partial recall {found}/{exp} = {rec:.2f}")
        elif found == 0:
            notes.append(f"{t} (secondary): 0/{exp} — grouping level not segmented")
        elif rec is not None and rec < OPT_RECALL:
            notes.append(f"{t} (secondary): {found}/{exp} = {rec:.2f} — under-detected")

    has_repeating = has_primary_repeating
    rubric_pass = composite >= OPT_COMPOSITE
    recall_min = min(repeating_recalls) if repeating_recalls else None

    if gold.get("low_structure"):
        rating = "LOW-STRUCTURE"
    elif not has_repeating:
        rating = "UNRATED-PRIMARY"
        # surface the likely verdict from the detector's own evidence, to motivate
        # adding the missing structural-contract gold (full-contract scope).
        if by_type.get("book", 0) > 0 and by_type.get("chapter", 0) == 0 and rubric_pass:
            notes.append("SUSPECTED MIRAGE: coarse containers (book>0, chapter=0) at "
                         f"composite {composite} — add chapter_heading gold to confirm")
    elif recall_min is not None:
        if recall_min >= OPT_RECALL and rubric_pass:
            rating = "OPTIMIZED"
        elif rubric_pass and recall_min < MIRAGE_RECALL:
            rating = "MIRAGE"
        else:
            rating = "COARSE"
    else:  # repeating but every count null -> structure-presence test
        all_present = all(presence_flags) if presence_flags else False
        if all_present and rubric_pass:
            rating = "PRESENT-OK"  # count unverified
        elif rubric_pass and not all_present:
            rating = "MIRAGE"  # rubric high but structure absent
        else:
            rating = "COARSE"

    return {
        "idx": idx,
        "work": gold.get("work", "?"),
        "rating": rating,
        "vector": {
            "composite": composite,
            "recall_min": round(recall_min, 3) if recall_min is not None else None,
            "leaf_coverage": diag["scores"].get("coverage"),
            "undetected_frac": round(uncovered / text_len, 3),
            "largest_uncovered_frac": largest_uncovered_frac,
            "masked_frac": diag["counts"].get("masked_fraction"),
        },
        "annotations": anns,
        "notes": notes,
    }


_RATING_ORDER = ["OPTIMIZED", "PRESENT-OK", "COARSE", "MIRAGE", "UNRATED-PRIMARY",
                 "LOW-STRUCTURE", "ERROR"]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        idxs = [int(args[0])]
    else:
        idxs = sorted(int(p.stem.split("-")[1]) for p in GOLD.glob("work-*.json"))

    results = [score_work(i) for i in idxs]
    print(f"{'idx':>4} {'rating':<16} {'comp':>5} {'recall':>7} {'cover':>6} "
          f"{'unc%':>5}  work")
    print("-" * 78)
    for r in results:
        if "error" in r:
            print(f"{r['idx']:>4} {'ERROR':<16} {'':>5} {'':>7} {'':>6} {'':>5}  "
                  f"{r['work'][:30]} :: {r['error']}")
            continue
        v = r["vector"]
        rec = f"{v['recall_min']:.2f}" if v["recall_min"] is not None else "—"
        print(f"{r['idx']:>4} {r['rating']:<16} {v['composite']:>5} {rec:>7} "
              f"{v['leaf_coverage']:>6} {int(v['undetected_frac']*100):>4}%  {r['work'][:30]}")
    print()
    for r in results:
        if r.get("notes"):
            print(f"[{r['idx']}] {r['work'][:40]}")
            for n in r["notes"]:
                print(f"    · {n}")

    tally: dict[str, int] = {}
    for r in results:
        tally[r.get("rating", "ERROR")] = tally.get(r.get("rating", "ERROR"), 0) + 1
    print("\nratings:", " ".join(f"{k}={tally[k]}" for k in _RATING_ORDER if k in tally))

    out = DIAG / "a3_scores.json"
    if DIAG.exists():
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
