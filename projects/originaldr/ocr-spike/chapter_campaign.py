#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chapter_campaign.py — drive `CHAPTER-WORKFLOW.md` across MANY chapters (Sir's order, 2026-07-29).

THE ORDER: every chapter of Genesis to the standard chapters 1 and 16 reached — every verse of every source
against EACH of the four references at >=0.90, every ſ-surface closed. Two chapters were brought there by hand;
48 remain, so the workflow has to run as a pipeline with the hand-work concentrated where it is actually needed.

WHAT THIS AUTOMATES, and what it deliberately does not:

  Phase 0  word boxes                 AUTOMATED (`gen1_wordboxes.py --chapter N`, ~150s/chapter, cached per leaf)
  Phase 1  reference audit            AUTOMATED AS A DETECTOR — the signature (one reference's mean far below the
                                      others') is computed and reported. Encoding a correction into
                                      `ref_renumber.CORRECTIONS` stays a judgement, never automatic.
  Phase 2  cold matrix                AUTOMATED (`gen1_matrix.build`)
  Phase 3  LOOK AT THE PAGES          NOT AUTOMATED. Cannot be: every layout finding in this project came from
                                      rendering a leaf and reading it. This driver's job is to say WHICH leaf.
  Phase 5  Rung 3 on the residual     AUTOMATED but EXPENSIVE (20-60s per crop, local olmOCR-2 via MLX), so it is
                                      a separate `--phase r3` pass run only on chapters whose residual is small
                                      enough to be recognition rather than structure.
  Phase 7  exit criteria              AUTOMATED as a check, reported per chapter.

**BREADTH BEFORE DEPTH, on the project's own evidence.** Genesis 16 cold-started at 73.8% with ZERO chapter
tuning, which says the generalizable rules carry most of the load and only outliers need hand-work. So the
campaign measures EVERY chapter cold first and triages from the result, rather than perfecting chapter 2 while 48
chapters remain unmeasured. A cold matrix is minutes; a hand-worked chapter is hours.

TRIAGE CLASSES (per chapter, from the cold matrix — these decide what happens next):
  CLEAN        every cell >=0.90 already. Verify ſ surface, then close.
  R3-READY     few open cells, spread across sources -> recognition residual -> Phase 5.
  REF-SUSPECT  one reference's mean far below the others -> Phase 1 FIRST (in both worked chapters the
               governing archaic reference was defective and it looked exactly like an OCR problem).
  SOURCE-SKEW  one source far below its siblings -> that witness's layout/leaf model -> Phase 3 on those leaves.
  VERTICAL     many verses failing in EVERY source -> not a recognizer problem: addressing, localization or
               reference. Phase 3 + the localizer, not R3.
  NO-LEAVES    the localizer offers no leaves for this chapter -> upstream addressing gap, blocks everything.

Usage:
  ../ocr-venv/bin/python chapter_campaign.py --chapters 2-50 --phase measure [--workers 4]
  ../ocr-venv/bin/python chapter_campaign.py --chapters 2,3,4 --phase r3
  ../ocr-venv/bin/python chapter_campaign.py --report
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE / ".campaign"
PY = str(HERE.parent / "ocr-venv" / "bin" / "python")

REF_OUTLIER_GAP = 0.06      # one reference's mean this far below the best -> Phase 1 before anything else
SOURCE_SKEW_GAP = 0.10      # one source's pass rate this far below the best -> that witness's layout
VERTICAL_FRAC = 0.25        # this fraction of verses failing in EVERY source -> vertical, not recognition


def parse_chapters(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def wordboxes(ch: int, timeout: int = 1800) -> tuple[bool, str]:
    """Phase 0. Idempotent: the cache is per leaf, so a re-run only fills gaps."""
    p = HERE / (".gen1-wordboxes.json" if ch == 1 else f".wordboxes-genesis-{ch}.json")
    if p.exists():
        try:
            d = json.loads(p.read_text())
            if sum(len(v) for v in d.values()) > 0:
                return True, "cached"
        except Exception:                                        # noqa: BLE001
            pass
    r = subprocess.run([PY, "gen1_wordboxes.py", "--chapter", str(ch)], cwd=str(HERE),
                       capture_output=True, text=True, timeout=timeout)
    if "no leaves found" in (r.stderr or ""):
        return False, "no-leaves"
    return (p.exists(), (r.stdout or "").strip().splitlines()[-1] if r.stdout else "")


def measure(ch: int, use_r3: bool = True) -> dict:
    """Phase 2/4/7 in one call: build the matrix and reduce it to a decision."""
    import gen1_matrix as MX
    import gen1_pagemodel_eval as EV
    EV.set_locus("genesis", ch)
    board = MX.build(use_r3=use_r3)
    cells, verses = board["cells"], board["verses"]
    refs = list(MX.REFS)
    per_ref = {r: [] for r in refs}
    per_src = {s: {"pass": 0, "n": 0} for s in MX.WITS}
    open_cells, all_fail = [], []
    for v in verses:
        vfail = 0
        for s in MX.WITS:
            c = cells.get((s, v)) or {}
            sc = c.get("score") or {}
            vals = [sc.get(r) for r in refs if sc.get(r) is not None]
            if not vals:
                open_cells.append({"src": s, "verse": v, "worst": None, "reason": "no-score"})
                per_src[s]["n"] += 1
                vfail += 1
                continue
            for r in refs:
                if sc.get(r) is not None:
                    per_ref[r].append(sc[r])
            per_src[s]["n"] += 1
            if min(vals) >= 0.90:
                per_src[s]["pass"] += 1
            else:
                vfail += 1
                open_cells.append({"src": s, "verse": v, "worst": round(min(vals), 3),
                                   # THE FULL TEXT, not a 120-character preview. The truncation was invisible
                                   # in a log line and actively misleading anywhere else: reading genesis
                                   # 8:1/S3 and 8:13/S3 off the matrix, both looked like SPANS CUT SHORT
                                   # mid-sentence (`...cleane minished vpo`) — a structural geometry defect
                                   # worth chasing — when the spans are complete and the cut was this slice.
                                   # A diagnostic field that silently shortens the evidence is worse than
                                   # absent, because it fabricates a symptom.
                                   "from": c.get("from"), "text": c.get("text") or ""})
        if vfail == len(MX.WITS):
            all_fail.append(v)
    n_cells = sum(1 for v in verses for s in MX.WITS)
    n_pass = sum(1 for v in verses for s in MX.WITS
                 if (lambda sc: sc and all(sc.get(r) is not None for r in refs)
                     and min(sc[r] for r in refs) >= 0.90)((cells.get((s, v)) or {}).get("score")))
    ref_means = {r: (round(mean(v), 4) if v else None) for r, v in per_ref.items()}
    src_rates = {s: (round(d["pass"] / d["n"], 4) if d["n"] else None) for s, d in per_src.items()}

    # EVERY CELL, WITH ITS TEXT AND ITS FOUR SCORES — not only the open ones. The `open` list answers "what is
    # failing"; it cannot answer "what did each source actually print for this verse", because a PASSING cell
    # appears nowhere in it. Any reader that wants the four witnesses stacked beside the references has to have
    # the passing text too, and re-deriving it means rebuilding the board, so it is stored once here.
    #
    # The references and the Janvier segmentation are stored PER VERSE for the same reason. Janvier is the cut
    # the matrix is built on, not a fifth reference, and is labelled as such so nothing downstream scores it.
    janv = board.get("janvier") or {}
    refs_by_verse = {}
    for v in verses:
        loc = f"scripture/genesis/{ch}/{v}"
        refs_by_verse[str(v)] = {r: (board["refs"][r].get(loc) or "") for r in refs}
    cellgrid = {}
    for v in verses:
        cellgrid[str(v)] = {s: {"text": (cells.get((s, v)) or {}).get("text") or "",
                                "from": (cells.get((s, v)) or {}).get("from"),
                                "score": (cells.get((s, v)) or {}).get("score") or {}}
                            for s in MX.WITS}

    return {"chapter": ch, "n_verses": len(verses), "n_cells": n_cells, "n_pass": n_pass,
            "rate": round(n_pass / n_cells, 4) if n_cells else 0.0,
            "ref_means": ref_means, "src_rates": src_rates,
            "n_all_fail": len(all_fail), "all_fail": all_fail[:40],
            # NOT TRUNCATED ANY MORE. `open[:60]` silently dropped the tail on exactly the chapters that need
            # it most: ch41 reported n_open 65 and listed 60, so anything reconstructing the grid from this
            # file — the report's board does precisely that, treating "not named here" as a pass — rendered
            # five FAILING cells as passing. The same reasoning as the `text` field above: a diagnostic that
            # silently shortens the evidence is worse than absent, because it fabricates a clean result.
            "n_open": len(open_cells), "open": open_cells,
            "cellgrid": cellgrid, "refs_by_verse": refs_by_verse,
            "janvier_by_verse": {str(v): (janv.get(v) or "") for v in verses}}


def stale_adoptions(ch: int) -> list[dict]:
    """R3 adoptions that no longer beat the page model's own reading (§13 Q44).

    An adoption is gated on beating the incumbent AT THE TIME IT WAS MADE, and the store records what was
    adopted but never what it beat. So every improvement to the page model silently ages every prior adoption:
    tonight's catchword and `head_frac` fixes made the incumbent better, and three cells in the HAND-WORKED
    chapters now publish an R3 reading inferior to the page model's (ch16 S9 v9 0.978 -> 0.919; ch1 S3/S9 v23
    0.930 -> 0.926). They still clear the bar, so nothing else reports them.

    RE-RUNNING R3 DOES NOT CLEAR THESE, and that is the mechanism worth recording: the adoption store is
    APPEND-ONLY. `gen1_r3` adds an adoption when the gate passes and never retires one, so a decision made
    against a worse incumbent survives every later run — chapters 1 and 16 were re-run under the current page
    model and all three stale cells remained.

    THEY ARE STILL NOT AUTO-REVERTED, on the standard's own terms. A cell must clear 0.90 on CONTENT and have a
    CLOSED ſ surface. The adopted text carries a surface every glyph of which is attested; the page model's text
    scores better on content but has no surface verification at all. Dropping the adoption would trade a
    verified transcription for a better number — the exact trade this project forbids — so the honest state is
    to KEEP the adoption and REPORT the content regression, which is what this function does. All three cells
    clear the bar, so the deliverable is intact; what is owed is a surface verification of the page-model
    reading, after which the better content could be adopted with its surface closed."""
    import gen1_matrix as MX
    import gen1_pagemodel_eval as EV
    store = HERE / (".gen1-r3-adopted.json" if ch == 1 else f".r3-adopted-genesis-{ch}.json")
    if not store.exists():
        return []
    EV.set_locus("genesis", ch)
    with_r3 = MX.build(use_r3=True)["cells"]
    no_r3 = MX.build(use_r3=False)["cells"]
    refs = list(MX.REFS)
    out = []
    for key in json.loads(store.read_text()):
        s_, v = key.split(":")
        v = int(v)
        a = (with_r3.get((s_, v)) or {}).get("score") or {}
        b = (no_r3.get((s_, v)) or {}).get("score") or {}
        va = [a[r] for r in refs if a.get(r) is not None]
        vb = [b[r] for r in refs if b.get(r) is not None]
        if va and vb and min(va) < min(vb) - 1e-9:
            out.append({"src": s_, "verse": v, "page_model": round(min(vb), 3),
                        "adopted": round(min(va), 3)})
    return out


def ref_coverage(ch: int) -> dict:
    """Per-VERSE reference completeness — the chapter's true ceiling (§13 Q41).

    THE STANDARD IS ">=0.90 AGAINST EACH OF FOUR REFERENCES", so a verse missing any one of them cannot produce a
    passing cell however good the OCR is, and the matrix scores the absence as 0.000 — which reads as a
    catastrophic recogniser failure. Measured over Genesis: **836 of 6,120 cells (13.7%) sit on a verse missing at
    least one reference**, and only **33 of 50 chapters** have all four present for every verse.

    An earlier version of this function used a <50%-of-chapter threshold and so missed the partial cases entirely
    — genesis 12 has `odr_com` for 13 of 20 verses, passed the threshold, and quietly carried 28 unreachable
    cells that were being read as an S6 layout problem. The threshold was the bug: for THIS standard, one missing
    verse matters.

    Reported per chapter as `blocked_cells`, so `achievable = n_cells - blocked_cells` is what the campaign can
    actually close. The gaps still BLOCK and are never passed silently; they are simply attributed to acquisition
    rather than to the recognizer."""
    import ref_renumber as RR
    import verse_seg as VS
    names = ("s_dismas", "odr_com", "sabates_a", "madueke_b")
    janv = VS.chapter_verses("genesis", ch, VS.JANVIER) or {}
    have = {r: RR.load_corrected(r) for r in names}
    per_ref = {r: 0 for r in names}
    incomplete = []
    for v in janv:
        absent = [r for r in names
                  if not (have[r].get(f"scripture/genesis/{ch}/{v}") or "").strip()]
        for r in names:
            if r not in absent:
                per_ref[r] += 1
        if absent:
            incomplete.append({"verse": v, "absent": absent})
    return {"janvier": len(janv), "have": per_ref,
            "n_incomplete_verses": len(incomplete), "incomplete": incomplete[:40],
            "blocked_cells": len(incomplete) * 4,
            "gaps": [r for r, n in per_ref.items() if janv and n < len(janv)]}


def triage(m: dict) -> str:
    # REF-GAP is reported when the reference gap is what dominates the chapter; a chapter with one incomplete
    # verse is still an OCR story and is triaged as one, with its blocked cells reported beside the rate.
    cov = m.get("ref_coverage") or {}
    if cov.get("blocked_cells") and m.get("n_cells") and \
            cov["blocked_cells"] >= 0.15 * m["n_cells"]:
        return "REF-GAP"
    if m.get("error") == "no-leaves":
        return "NO-LEAVES"
    if m["n_cells"] == 0:
        return "NO-VERSES"
    if m["n_pass"] == m["n_cells"]:
        return "CLEAN"
    means = [v for v in m["ref_means"].values() if v is not None]
    if means and (max(means) - min(means)) >= REF_OUTLIER_GAP:
        return "REF-SUSPECT"
    if m["n_verses"] and m["n_all_fail"] / m["n_verses"] >= VERTICAL_FRAC:
        return "VERTICAL"
    rates = [v for v in m["src_rates"].values() if v is not None]
    if rates and (max(rates) - min(rates)) >= SOURCE_SKEW_GAP:
        return "SOURCE-SKEW"
    return "R3-READY"


def run_measure(chapters: list[int]) -> None:
    OUT.mkdir(exist_ok=True)
    for ch in chapters:
        t0 = time.time()
        f = OUT / f"matrix-genesis-{ch}.json"
        ok, note = wordboxes(ch)
        if not ok:
            rec = {"chapter": ch, "error": "no-leaves", "note": note, "n_cells": 0, "n_pass": 0,
                   "n_verses": 0, "n_all_fail": 0, "n_open": 0, "ref_means": {}, "src_rates": {}}
            rec["triage"] = "NO-LEAVES"
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            print(f"ch {ch:>2}: NO-LEAVES ({note})", flush=True)
            continue
        try:
            m = measure(ch)
        except Exception as e:                                    # noqa: BLE001
            m = {"chapter": ch, "error": f"{type(e).__name__}: {e}", "n_cells": 0, "n_pass": 0,
                 "n_verses": 0, "n_all_fail": 0, "n_open": 0, "ref_means": {}, "src_rates": {}}
        try:
            rc = ref_coverage(ch)
            m["ref_coverage"] = rc
            m["ref_gaps"] = rc["gaps"]
        except Exception as e:                                    # noqa: BLE001
            m["ref_coverage_error"] = str(e)
        m["blocked_cells"] = (m.get("ref_coverage") or {}).get("blocked_cells", 0)
        m["achievable"] = max(0, m["n_cells"] - m["blocked_cells"])
        m["triage"] = triage(m)
        m["secs"] = round(time.time() - t0, 1)
        f.write_text(json.dumps(m, ensure_ascii=False, indent=1))
        print(f"ch {ch:>2}: {m['triage']:<12} {m['n_pass']}/{m['n_cells']} = "
              f"{m.get('rate', 0):.3f}  verses {m['n_verses']}  all-fail {m['n_all_fail']}  "
              f"refs {m['ref_means']}  {m['secs']}s", flush=True)


def report() -> None:
    rows = []
    for f in sorted(OUT.glob("matrix-genesis-*.json"), key=lambda p: int(p.stem.split("-")[-1])):
        rows.append(json.loads(f.read_text()))
    if not rows:
        print("no campaign measurements yet")
        return
    by = {}
    for r in rows:
        by.setdefault(r.get("triage", "?"), []).append(r["chapter"])
    print(f"{'ch':>3} {'triage':<12} {'cells':>11} {'rate':>6} {'all-fail':>8}  sources")
    for r in rows:
        print(f"{r['chapter']:>3} {r.get('triage','?'):<12} {r['n_pass']:>5}/{r['n_cells']:<5} "
              f"{r.get('rate',0):>6.3f} {r['n_all_fail']:>8}  "
              + " ".join(f"{k}={v}" for k, v in (r.get('src_rates') or {}).items()))
    print("\nBY CLASS:")
    for k, v in sorted(by.items()):
        print(f"  {k:<12} {len(v):>3} chapters: {v}")
    tot_c = sum(r["n_cells"] for r in rows)
    tot_p = sum(r["n_pass"] for r in rows)
    print(f"\nTOTAL {tot_p}/{tot_c} = {tot_p/max(1,tot_c):.4f} of cells at >=0.90 across "
          f"{len(rows)} measured chapters")
    # TWO TRACKS, REPORTED APART. A chapter missing a reference cannot meet a standard defined as ">=0.90
    # against EACH of four references, so counting its cells as OCR failures misattributes an acquisition defect
    # to the recogniser. Both still BLOCK — nothing is passed silently — but the remedy differs.
    gap_rows = [r for r in rows if r.get("ref_gaps")]
    ok_rows = [r for r in rows if not r.get("ref_gaps")]
    gc = sum(r["n_cells"] for r in gap_rows); gp = sum(r["n_pass"] for r in gap_rows)
    oc = sum(r["n_cells"] for r in ok_rows); op = sum(r["n_pass"] for r in ok_rows)
    ach = sum(r.get("achievable", r["n_cells"]) for r in rows)
    blk = sum(r.get("blocked_cells", 0) for r in rows)
    print(f"  ACHIEVABLE cells (a verse with all four references): {ach}/{tot_c}; "
          f"BLOCKED by an absent reference: {blk}")
    print(f"  against the achievable set: {tot_p}/{ach} = {tot_p/max(1,ach):.4f}")
    # TWO DIFFERENT CLAIMS, AND ONLY THE FIRST IS "THE CHAPTER IS DONE". `100% of achievable` on a chapter whose
    # references cover 2 of 32 verses is 8 cells out of 128 and reads as a triumph — precisely the laundering
    # this project forbids (genesis 49 does exactly that). So a chapter counts as CLOSED only when its references
    # are COMPLETE and every cell passes; anything else is reported with its achievable fraction in view.
    closed = [r["chapter"] for r in rows
              if r["n_cells"] and r.get("achievable") == r["n_cells"] and r["n_pass"] == r["n_cells"]]
    partial = [(r["chapter"], r["n_pass"], r.get("achievable"), r["n_cells"]) for r in rows
               if r["n_cells"] and r.get("achievable", r["n_cells"]) < r["n_cells"]
               and r["n_pass"] >= r.get("achievable", 10**9)]
    print(f"  CHAPTERS CLOSED (references complete AND every cell >=0.90): {len(closed)} -> {closed}")
    if partial:
        print(f"  chapters at 100% of a REDUCED achievable set (not closed — the gap still blocks):")
        for ch, np_, ach, nc in partial:
            print(f"    ch {ch:>2}: {np_}/{ach} achievable, but achievable is only {ach}/{nc} of the chapter")
    print(f"  REACHABLE (all four references present): {op}/{oc} = {op/max(1,oc):.4f} "
          f"over {len(ok_rows)} chapters")
    print(f"  BLOCKED BY A REFERENCE GAP: {gp}/{gc} over {len(gap_rows)} chapters "
          f"{[r['chapter'] for r in gap_rows]}")
    for r in gap_rows:
        cov = r.get("ref_coverage") or {}
        print(f"    ch {r['chapter']:>2}: janvier {cov.get('janvier')} verses, have {cov.get('have')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="")
    ap.add_argument("--phase", default="measure", choices=["measure", "wordboxes", "r3"])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--improve-below", default="0.95")
    a = ap.parse_args()
    if a.report:
        report()
        return 0
    chs = parse_chapters(a.chapters)
    if not chs:
        print("give --chapters, e.g. 2-50")
        return 2
    if a.phase == "wordboxes":
        for ch in chs:
            ok, note = wordboxes(ch)
            print(f"ch {ch}: {'ok' if ok else 'FAILED'} {note}", flush=True)
    elif a.phase == "measure":
        run_measure(chs)
    elif a.phase == "r3":
        for ch in chs:
            print(f"=== R3 chapter {ch} ===", flush=True)
            r = subprocess.run([PY, "gen1_r3.py", "--chapter", str(ch),
                                "--improve-below", a.improve_below], cwd=str(HERE),
                               capture_output=True, text=True)
            print((r.stdout or "")[-2500:], flush=True)
            if r.returncode != 0:
                print(f"  R3 FAILED rc={r.returncode}\n{(r.stderr or '')[-800:]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
