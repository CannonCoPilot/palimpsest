#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selector_probe.py — is `best_spans`'s janvier_fit selector DEAD at the verses it matters most for? (§13 Q30)

Q30 established that `verse_locate.janvier_fit` returns **0.000 for any partial span** because it delegates to
`char_identity.evaluate_locus`, which compares a WHOLE verse to its reference. `best_spans` selects between the
walk and the aligner with exactly that function:

    if wf > af + switch_margin:  take the walk   else:  take the aligner

So whenever BOTH arms produce a partial — the straddling / boundary case, historically the all-fail class — the
comparison is `0.0 > 0.0`, the selector is silent, and the hybrid degenerates to the incumbent aligner without
saying so. That was a HYPOTHESIS at handoff. This measures it, on the 13 gold pages, against the GOLD (via
`gold_grid`, the printed-marker cut) — a standard independent of both the selector and either engine.

Reported, per verse:
  * `wf`/`af`   the incumbent selector's two scores, and whether it was DEAD (both 0.0) or TIED
  * `swf`/`saf` `gen1_r3.span_fit`, the partial-tolerant replacement
  * gold `archaic_id` of each arm, so each policy can be scored on the axis that decides the deliverable

Policies compared (identical machinery, only the selection rule differs):
  incumbent   wf > af                        (production today)
  spanfit     swf > saf                      (Q30's replacement, used alone)
  rescue      wf > af, and where the incumbent is DEAD fall back to span_fit  (minimal, surgical change)
  oracle      max of the two arms' gold id   (the ceiling; not a deliverable)

Usage: ../ocr-venv/bin/python selector_probe.py [--verbose] [slug ...]
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verse_seg as VS                                # noqa: E402
import verse_locate                                   # noqa: E402
import gold_grid                                      # noqa: E402
from char_identity import evaluate_locus              # noqa: E402
from gate_calibrate import LOCI, gold_by_chapter      # noqa: E402
from gen1_r3 import span_fit                          # noqa: E402

CACHE = HERE / ".page-cache"
GT = HERE / "ground-truth"
DEAD_EPS = 1e-9


def page_result(slug):
    d = json.loads((CACHE / f"{slug}.json").read_text())
    return {"page_px": tuple(d["page_px"]), "r2_body": d["r2_body"], "lines": d["lines"]}


def probe_page(slug, verbose=False):
    book = LOCI.get(slug)
    if not book or not (CACHE / f"{slug}.json").exists():
        return []
    gt = json.loads((GT / f"{slug}.json").read_text())
    pr = page_result(slug)
    rows = []
    for ch, _gold_text in sorted(gold_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        grid = gold_grid.build_grid(gt, ch, book)
        gold_j = {v: t for v, t in grid["verses"].items() if t}
        walk = verse_locate.locate(pr, book, ch)["verses"]
        align = VS.segment_book_chapter(pr["r2_body"], book, ch, drop_apparatus=True)
        for v in sorted(gold_j):
            g = gold_j[v]
            jv = janv.get(v)
            wtxt = (walk.get(v) or {}).get("text", "") or ""
            atxt = (align.get(v) or {}).get("text", "") or ""
            # Mirror best_spans's own emission rule so the population matches production exactly.
            if v not in align and (walk.get(v) or {}).get("tok_lo") is None:
                continue
            wf, af = verse_locate.janvier_fit(wtxt, jv), verse_locate.janvier_fit(atxt, jv)
            swf, saf = span_fit(wtxt, jv), span_fit(atxt, jv)
            wid = evaluate_locus(wtxt, jv, g)["archaic_id"] if wtxt else 0.0
            aid = evaluate_locus(atxt, jv, g)["archaic_id"] if atxt else 0.0
            # THE JUDGE HAS THE SAME DEFECT AS THE THING IT JUDGES, and on exactly the rows in question.
            # `evaluate_locus` is whole-verse, and `gold_grid` cuts the gold per PAGE, so a verse straddling
            # two gold pages is a PARTIAL on each side and both arms score ~0.000 against it — which is why
            # the one dead row below reads 0.000/0.000 and looks like "no gain available" when in fact nothing
            # was measured. `partial_fit` against the GOLD (not janvier) is the partial-tolerant judge: gold is
            # truth, so an F1 against it is independent of every selector being compared.
            wgf = verse_locate.partial_fit(wtxt, g)[2]
            agf = verse_locate.partial_fit(atxt, g)[2]
            rows.append({
                "slug": slug, "ch": ch, "v": v,
                "wf": wf, "af": af, "swf": swf, "saf": saf,
                "wid": wid, "aid": aid, "wgf": wgf, "agf": agf,
                "fwf": verse_locate.partial_fit(wtxt, jv)[2],
                "faf": verse_locate.partial_fit(atxt, jv)[2],
                "dead": wf <= DEAD_EPS and af <= DEAD_EPS,
                "tied": abs(wf - af) <= DEAD_EPS,
                "wtxt": wtxt, "atxt": atxt,
            })
            if verbose and rows[-1]["dead"]:
                print(f"    DEAD {slug} {ch}:{v}  span_fit walk {swf:.3f} align {saf:.3f}  "
                      f"gold walk {wid:.3f} align {aid:.3f}")
    return rows


# ---------------------------------------------------------------------------- #
# selection policies — each returns the chosen arm's gold id
# ---------------------------------------------------------------------------- #
def _arm(r, take_walk, judge):
    """The chosen arm's score under `judge` ('id' = whole-verse archaic_id, 'gf' = partial-tolerant gold F1)."""
    return r["wid" if judge == "id" else "wgf"] if take_walk else r["aid" if judge == "id" else "agf"]


def pick_incumbent(r, judge="id"):
    return _arm(r, r["wf"] > r["af"], judge)


def pick_spanfit(r, judge="id"):
    return _arm(r, r["swf"] > r["saf"], judge)


def pick_f1(r, judge="id"):
    return _arm(r, r["fwf"] > r["faf"], judge)


def pick_rescue(r, judge="id"):
    """The SURGICAL policy: leave the incumbent alone wherever it is alive, decide only the dead rows.

    Justified by the two measurements together — on the gold pages `span_fit` used ALONE changed 18 verses and
    every one got worse, so the incumbent is right where it can see; corpus-wide it is dead on 42% of spans,
    where it sees nothing at all. Rescue changes only the second set."""
    if r["dead"]:
        return _arm(r, r["fwf"] > r["faf"], judge)
    return _arm(r, r["wf"] > r["af"], judge)


def pick_oracle(r, judge="id"):
    return max(r["wid"], r["aid"]) if judge == "id" else max(r["wgf"], r["agf"])


POLICIES = (("incumbent (production)", pick_incumbent),
            ("span_fit alone", pick_spanfit),
            ("partial_fit F1 alone", pick_f1),
            ("rescue dead only (F1)", pick_rescue),
            ("oracle (uses gold)", pick_oracle))


def report(rows):
    n = len(rows)
    dead = [r for r in rows if r["dead"]]
    tied = [r for r in rows if r["tied"] and not r["dead"]]
    print("\n" + "=" * 92)
    print(f"POPULATION  n={n} verses over {len({r['slug'] for r in rows})} gold pages")
    print(f"  selector DEAD (both arms janvier_fit 0.000): {len(dead)}/{n} = {len(dead)/n:.1%}")
    print(f"  selector TIED at a non-zero value:           {len(tied)}/{n}")
    print(f"  span_fit dead on the same rows:              "
          f"{sum(1 for r in dead if r['swf'] <= DEAD_EPS and r['saf'] <= DEAD_EPS)}/{len(dead) or 1}")
    for judge, jlabel in (("id", "whole-verse archaic_id vs gold (the deliverable's own metric)"),
                          ("gf", "partial-tolerant F1 vs gold (valid at page boundaries)")):
        print(f"\nPOLICY COMPARISON — judge: {jlabel}")
        print(f"  {'policy':<24} {'mean':>7} {'pass>=0.90':>12}    {'mean on DEAD':>13} {'pass on DEAD':>13}")
        base = None
        for label, fn in POLICIES:
            vals = [fn(r, judge) for r in rows]
            dvals = [fn(r, judge) for r in dead]
            m = mean(vals)
            if base is None:
                base = m
            dm = f"{mean(dvals):.4f}" if dvals else "-"
            dp = f"{sum(1 for x in dvals if x >= 0.9)}/{len(dvals)}" if dvals else "-"
            print(f"  {label:<24} {m:>7.4f} {sum(1 for x in vals if x>=0.9):>6}/{len(vals):<5}    "
                  f"{dm:>13} {dp:>13}")
        print("  disagreements with production:")
        for label, fn in POLICIES[1:-1]:
            diff = [r for r in rows if abs(fn(r, judge) - pick_incumbent(r, judge)) > 1e-9]
            better = sum(1 for r in diff if fn(r, judge) > pick_incumbent(r, judge))
            print(f"    {label:<24} changed {len(diff):>3}   better {better:>3}   worse {len(diff)-better:>3}"
                  f"   Δmean {mean([fn(r, judge) for r in rows]) - base:+.4f}")
    if dead:
        print("\nTHE DEAD ROWS, one line each (arm gold ids, span_fit):")
        for r in sorted(dead, key=lambda r: (r["slug"], r["ch"], r["v"])):
            print(f"  {r['slug']:<27} {r['ch']:>4}:{r['v']:<3} walk id {r['wid']:.3f} sf {r['swf']:.3f} | "
                  f"align id {r['aid']:.3f} sf {r['saf']:.3f}")


def main():
    args = sys.argv[1:]
    verbose = "--verbose" in args
    slugs = [a for a in args if not a.startswith("--")] or sorted(LOCI)
    rows = []
    for slug in slugs:
        rows += probe_page(slug, verbose)
    if not rows:
        print("no rows — is .page-cache/ populated?")
        return 1
    report(rows)
    out = HERE / "selector-probe.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"\n[wrote] {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
