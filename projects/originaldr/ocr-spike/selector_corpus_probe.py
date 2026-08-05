#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selector_corpus_probe.py — how often is the janvier_fit selector DEAD in the LIVE corpus path? (§13 Q30)

Q30 proved `verse_locate.janvier_fit` returns 0.000 for any PARTIAL span, and left an unmeasured hypothesis:
`verse_locate.best_spans` selects with that same function, so it may be blind at exactly the boundary verses
the M-series measured as the historic all-fail class. `selector_probe.py` answered it on the 14 gold pages
(1/165 rows dead) — but the gold pages are whole-verse pages by construction, so that is a WEAK test of a
claim about boundaries. This replays the LIVE localize loop over entire witnesses, where straddling pages are
the ordinary case.

NO GOLD IS AVAILABLE AT THIS SCALE, so nothing here is scored as better or worse. Two things are counted, and
they are both facts about the selector rather than about the output:

  1. **INTRA-PAGE (`best_spans`)** — per verse-span emitted: are BOTH arms 0.000 (selector dead), and do the
     two arms actually DIFFER? A dead selector on identical arms costs nothing; a dead selector on differing
     arms is a coin flip resolved silently in the incumbent aligner's favour. `gen1_r3.span_fit` is scored on
     the same pair, so its ability to separate them is measured on the real population.

  2. **CROSS-PAGE (`corpus_localize._better`)** — adjacent pages' intervals overlap by design, so two pages can
     both offer a verse. That contest is also decided by `janvier_fit`, with a length-sanity tiebreak added for
     the fit-0 case (its docstring's `archive-holiebible-ot1` genesis 1 measurement). How often does the
     tiebreak have to carry the decision, and would `span_fit` have decided it on evidence instead of on a
     length proxy?

This deliberately re-implements the localize loop rather than importing it: `localize_volume` writes the
production `.corpus-localize-*.json`, and a probe must not be able to touch a deliverable.

Usage: ../ocr-venv/bin/python selector_corpus_probe.py [--limit N] [--books a,b] [ocr_dir ...]
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from collections import Counter
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verse_locate                              # noqa: E402
import verse_seg as VS                           # noqa: E402
import corpus_localize as CL                     # noqa: E402
from corpus_wire_probe import stored_page         # noqa: E402
from gen1_r3 import span_fit                     # noqa: E402

EPS = 1e-9
ALL_DIRS = sorted(p.name.split("page-address-")[1][:-5]
                  for p in HERE.glob(".page-address-*.json") if ".heldout." not in p.name)


def probe_volume(ocr_dir: str, books: list[str], limit: int | None = None) -> dict:
    af = HERE / f".page-address-{ocr_dir}.json"
    recs = [r for r in json.loads(af.read_text())["records"] if r["book"] in books]
    if limit:
        recs = recs[:limit]
    rows: list[dict] = []
    offers: dict[str, list[dict]] = {}
    t0 = time.time()
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
            lr = CL._line_range(rec, ch)
            # Re-derive both arms exactly as best_spans does, including its line_range restriction, so the
            # measured pair is the pair production selects between and not an approximation of it.
            pg = page
            if lr is not None:
                lo_l, hi_l = lr
                pg = {**page, "lines": [l for i, l in enumerate(page["lines"]) if lo_l <= i < hi_l]}
                import verse_geom
                pg["r2_body"] = verse_geom.build_body_tokmap(pg["lines"])[0]
            try:
                walk = verse_locate.locate(pg, rec["book"], ch)["verses"]
                align = VS.segment_book_chapter(pg["r2_body"], rec["book"], ch, drop_apparatus=True)
            except Exception:                                  # noqa: BLE001
                continue
            for v in sorted(set(walk) | set(align)):
                if v not in align and (walk.get(v) or {}).get("tok_lo") is None:
                    continue
                jv = janv.get(v)
                wtxt = (walk.get(v) or {}).get("text", "") or ""
                atxt = (align.get(v) or {}).get("text", "") or ""
                if not (wtxt.strip() or atxt.strip()):
                    continue
                wf, af_ = verse_locate.janvier_fit(wtxt, jv), verse_locate.janvier_fit(atxt, jv)
                swf, saf = span_fit(wtxt, jv), span_fit(atxt, jv)
                fwf, faf = verse_locate.partial_fit(wtxt, jv)[2], verse_locate.partial_fit(atxt, jv)[2]
                chosen = wtxt if wf > af_ else atxt
                rows.append({"dir": ocr_dir, "book": rec["book"], "ch": ch, "v": v,
                             "page": rec["page_index"],
                             "wf": wf, "af": af_, "swf": swf, "saf": saf,
                             "differ": wtxt.strip() != atxt.strip(),
                             "dead": wf <= EPS and af_ <= EPS,
                             "sf_dead": swf <= EPS and saf <= EPS,
                             "sf_agrees": (swf > saf) == (wf > af_),
                             "fwf": fwf, "faf": faf,
                             "f1_dead": fwf <= EPS and faf <= EPS,
                             "f1_agrees": (fwf > faf) == (wf > af_)})
                key = f"{rec['book']}/{ch}/{v}"
                offers.setdefault(key, []).append(
                    {"page": rec["page_index"], "text": chosen,
                     "fit": max(wf, af_), "sf": span_fit(chosen, jv),
                     "f1": verse_locate.partial_fit(chosen, jv)[2],
                     "ntok": len(chosen.split()), "reflen": len((jv or "").split())})
        if (k + 1) % 200 == 0:
            print(f"  {ocr_dir} {k+1}/{len(recs)} pages · {len(rows)} spans · {time.time()-t0:.0f}s",
                  flush=True)
    return {"rows": rows, "offers": offers, "pages": len(recs), "secs": time.time() - t0}


def _length_pick(cands: list[dict]) -> dict:
    """`corpus_localize._better`'s decision, replayed: fit first, then distance from the reference length."""
    best = None
    for c in cands:
        if best is None:
            best = c
            continue
        if c["fit"] > best["fit"] + EPS:
            best = c
        elif c["fit"] >= best["fit"] - EPS and c["reflen"]:
            def off(x):
                return abs((x["ntok"] / x["reflen"]) - 1.0) if x["ntok"] else 9.9
            if off(c) < off(best):
                best = c
    return best or {}


def report(res: dict):
    rows, offers = res["rows"], res["offers"]
    n = len(rows)
    if not n:
        print("no spans measured")
        return
    dead = [r for r in rows if r["dead"]]
    dead_diff = [r for r in dead if r["differ"]]
    differ = [r for r in rows if r["differ"]]
    print("\n" + "=" * 96)
    print(f"1 · INTRA-PAGE SELECTOR  ({n} verse-spans over {res['pages']} pages, {res['secs']:.0f}s)")
    print(f"  arms DIFFER (the selector actually decides):   {len(differ):>6}/{n} = {len(differ)/n:.1%}")
    print(f"  selector DEAD (both janvier_fit 0.000):        {len(dead):>6}/{n} = {len(dead)/n:.1%}")
    print(f"  DEAD *and* arms differ — a SILENT COIN FLIP:   {len(dead_diff):>6}/{n} = {len(dead_diff)/n:.1%}"
          f"   ({len(dead_diff)/max(len(differ),1):.1%} of all real decisions)")
    if dead_diff:
        live = [r for r in dead_diff if not r["sf_dead"]]
        sep = [r for r in live if abs(r["swf"] - r["saf"]) > 0.01]
        print(f"  of those, span_fit is NOT dead:               {len(live):>6}/{len(dead_diff)}"
              f" = {len(live)/len(dead_diff):.1%}")
        print(f"  ...and SEPARATES the arms by >0.01:           {len(sep):>6}/{len(dead_diff)}"
              f" = {len(sep)/len(dead_diff):.1%}")
        print(f"  mean span_fit on those pairs: walk {mean(r['swf'] for r in dead_diff):.3f} "
              f"align {mean(r['saf'] for r in dead_diff):.3f}")
        pref = Counter("walk" if r["swf"] > r["saf"] + 0.01 else
                       ("align" if r["saf"] > r["swf"] + 0.01 else "tie") for r in dead_diff)
        print(f"  span_fit would prefer: {dict(pref)}   (production takes ALIGN on every one of these)")
        f1live = [r for r in dead_diff if not r["f1_dead"]]
        f1sep = [r for r in f1live if abs(r["fwf"] - r["faf"]) > 0.01]
        f1pref = Counter("walk" if r["fwf"] > r["faf"] + 0.01 else
                         ("align" if r["faf"] > r["fwf"] + 0.01 else "tie") for r in dead_diff)
        print(f"  partial_fit F1 not dead {len(f1live)}/{len(dead_diff)}, separates {len(f1sep)}"
              f"/{len(dead_diff)} = {len(f1sep)/len(dead_diff):.1%}, would prefer: {dict(f1pref)}")
    live_dec = [r for r in differ if not r["dead"]]
    if live_dec:
        for lbl, key in (("span_fit", "sf_agrees"), ("partial_fit F1", "f1_agrees")):
            k = sum(1 for r in live_dec if r[key])
            print(f"  where the incumbent IS alive, {lbl:<14} agrees with it on {k}/{len(live_dec)}"
                  f" = {k/len(live_dec):.1%}")

    contested = {k: c for k, c in offers.items() if len(c) > 1}
    print(f"\n2 · CROSS-PAGE ARBITRATION  ({len(contested)} verses offered by >1 page, "
          f"of {len(offers)} localized)")
    if contested:
        zero = {k: c for k, c in contested.items() if all(x["fit"] <= EPS for x in c)}
        print(f"  every candidate at fit 0.000 (length tiebreak decides): {len(zero)}/{len(contested)}"
              f" = {len(zero)/len(contested):.1%}")
        if zero:
            for lbl, key in (("span_fit", "sf"), ("partial_fit F1", "f1")):
                disagree = [k for k, c in zero.items()
                            if _length_pick(c).get("page") != max(c, key=lambda x: x[key])["page"]]
                print(f"  ...where {lbl:<14} would keep a DIFFERENT page's span: {len(disagree)}/{len(zero)}"
                      f" = {len(disagree)/len(zero):.1%}")
                for k in sorted(disagree)[:8]:
                    c = zero[k]
                    lp, sp = _length_pick(c), max(c, key=lambda x: x[key])
                    print(f"    {k:<22} length->p{lp['page']} ({lp['ntok']}tok {key} {lp[key]:.2f})  "
                          f"{lbl}->p{sp['page']} ({sp['ntok']}tok {key} {sp[key]:.2f})")


def main():
    args = sys.argv[1:]
    limit = None
    books = CL.PILOT_BOOKS
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--limit":
            limit = int(args[i + 1]); i += 2
        elif a == "--books":
            books = args[i + 1].split(","); i += 2
        else:
            rest.append(a); i += 1
    dirs = rest or ALL_DIRS
    merged = {"rows": [], "offers": {}, "pages": 0, "secs": 0.0}
    for od in dirs:
        print(f"[probe] {od}  books={','.join(books)}  limit={limit}", flush=True)
        r = probe_volume(od, books, limit)
        merged["rows"] += r["rows"]
        merged["pages"] += r["pages"]
        merged["secs"] += r["secs"]
        for k, v in r["offers"].items():          # keys are per-witness; namespace them
            merged["offers"][f"{od}:{k}"] = v
        report(r)
    if len(dirs) > 1:
        print("\n\n########## MERGED ##########")
        report(merged)
    (HERE / "selector-corpus-probe.json").write_text(json.dumps(
        {"rows": merged["rows"], "pages": merged["pages"]}, ensure_ascii=False))
    print("\n[wrote] selector-corpus-probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
