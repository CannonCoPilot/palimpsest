#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""walkthrough.py — the ENFORCER for the end-to-end Genesis walkthrough (Sir, 2026-08-01).

THE ORDER. Every Genesis chapter under 100% gets at least one, preferably two, FULL chapter-workflow efforts
(`CHAPTER-WORKFLOW.md` Phases 0-7 plus the round template's router). R2/R3 and any other approach may run in
the background; they do not substitute for the per-chapter walkthrough and cannot mark a chapter worked.

WHY THIS IS A PROGRAM AND NOT A CHECKLIST IN A MARKDOWN FILE. A checklist maintained by the same agent doing
the work will drift toward "visited" meaning "done" — that is exactly the silent-degradation failure this
project forbids, wearing a project-management costume. So COMPLETION IS COMPUTED, NOT ASSERTED:

  * the before/after rates are read from `.campaign/matrix-genesis-N.json`, never typed in;
  * a pass must name which ROUTER SIGNALS fired and which DIAGNOSTIC was run for each — a pass that ran no
    diagnostic is not a pass, however much was learned;
  * a pass must end in a RULE or an explicit ALERT. `CHAPTER-WORKFLOW.md` B5 is categorical: "stop when hand
    work stops producing rules" is a trap, and finding no rule is an alert to redesign the APPROACH, never a
    reason the chapter is finished;
  * `--record` REFUSES anything missing those, and refuses a second pass identical to the first.

WHAT A PASS IS NOT. It is not "I looked at the matrix and the cells are recognizer damage." That verdict has
already been wrong twice in this campaign at the same site (ch41: the right-margin audit concluded RECOGNIZER
by elimination, and the left bound it never varied was worth +19 there and +57 book-wide). A pass that ends in
"nothing to do here" must record the diagnostics that establish it, and it counts as an ALERT, not a rule.

BLOCKED CHAPTERS ARE STILL WALKED. ch23 cannot reach 100% (odr_com lacks a verse) and it is still worked, its
block documented, its cell left OPEN, and an ACQUISITION item raised. A reference gap is a reason a chapter
cannot close; it is never a reason not to look at it.

Usage:
  ../ocr-venv/bin/python walkthrough.py --status
  ../ocr-venv/bin/python walkthrough.py --next
  ../ocr-venv/bin/python walkthrough.py --start 39
  ../ocr-venv/bin/python walkthrough.py --record 39 --signals 4,5 --diagnostics leaf_diag,left_strip_probe \
      --rule "p131 left bound" --changed-text --audited --notes "..."
  ../ocr-venv/bin/python walkthrough.py --record 39 --signals 5 --diagnostics s6_causes --alert "no lever left"
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMP = HERE / ".campaign"
STATE = CAMP / "walkthrough.json"
TARGET_PASSES = 2          # "at least one, preferably two" -> two is the target; one is the floor
FLOOR_PASSES = 1


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def matrices() -> dict[int, dict]:
    out = {}
    for f in CAMP.glob("matrix-genesis-*.json"):
        m = json.loads(f.read_text())
        out[m["chapter"]] = m
    return out


def load() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"created": now(), "chapters": {}}


def save(s: dict) -> None:
    s["updated"] = now()
    STATE.write_text(json.dumps(s, indent=1))


def rate_of(m: dict) -> tuple[int, int]:
    return m.get("n_pass", 0), m.get("achievable", m.get("n_cells", 0))


def status(s: dict, mats: dict[int, dict]) -> list[dict]:
    rows = []
    for ch in sorted(mats):
        m = mats[ch]
        p, a = rate_of(m)
        rec = s["chapters"].get(str(ch), {})
        passes = rec.get("passes", [])
        rows.append({"ch": ch, "pass": p, "achievable": a,
                     "rate": (p / a) if a else 0.0,
                     "closed": p >= a and a > 0,
                     "blocked": m.get("blocked_cells", 0),
                     "ref_gaps": m.get("ref_gaps", []),
                     "n_passes": len(passes),
                     "open_pass": bool(rec.get("in_progress")),
                     "last": passes[-1]["at"] if passes else None})
    return rows


def pick_next(rows: list[dict]) -> dict | None:
    """WORST-FIRST WITHIN THE LEAST-WALKED TIER. Sir's standing order is worst-first; the walkthrough's order
    is completeness. Combining them naively (pure worst-first) would pour every hour into the bottom chapters
    and leave the 90% band with zero passes, so the tier comes first: no chapter gets a SECOND pass while any
    chapter still lacks a FIRST. Within a tier, worst-first — that is where generalizable defects live."""
    live = [r for r in rows if not r["closed"] or r["n_passes"] < FLOOR_PASSES]
    if not live:
        return None
    tier = min(r["n_passes"] for r in live)
    return sorted([r for r in live if r["n_passes"] == tier], key=lambda r: r["rate"])[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--start", type=int)
    ap.add_argument("--record", type=int)
    ap.add_argument("--signals", default="", help="comma list of router signals that FIRED (1-6), or 'none'")
    ap.add_argument("--diagnostics", default="", help="comma list of tools actually RUN")
    ap.add_argument("--rule", default="", help="the generalizable rule this pass produced")
    ap.add_argument("--alert", default="", help="why no rule was found — an ALERT to redesign, not a stop")
    ap.add_argument("--changed-text", action="store_true")
    ap.add_argument("--audited", action="store_true", help="faithfulness_audit.py was run and READ")
    ap.add_argument("--notes", default="")
    a = ap.parse_args(argv)

    s, mats = load(), matrices()
    rows = status(s, mats)

    if a.status or not any([a.next, a.start, a.record]):
        done = sum(1 for r in rows if r["n_passes"] >= TARGET_PASSES)
        one = sum(1 for r in rows if r["n_passes"] >= FLOOR_PASSES)
        tot = sum(r["pass"] for r in rows)
        ach = sum(r["achievable"] for r in rows)
        print(f"WALKTHROUGH — {one}/{len(rows)} chapters have >=1 pass, {done}/{len(rows)} have {TARGET_PASSES}")
        print(f"board {tot}/{ach} = {tot/ach:.4f}\n")
        print(f"{'ch':>3}{'rate':>8}{'pass/ach':>11}{'walks':>7}  flags")
        for r in sorted(rows, key=lambda r: (r["n_passes"], r["rate"])):
            fl = []
            if r["closed"]:
                fl.append("CLOSED")
            if r["ref_gaps"]:
                fl.append("REF-GAP " + ",".join(r["ref_gaps"]))
            if r["open_pass"]:
                fl.append("PASS IN PROGRESS")
            pa = f"{r['pass']}/{r['achievable']}"
            print(f"{r['ch']:>3}{r['rate']:>8.3f}{pa:>11}{r['n_passes']:>7}  {' '.join(fl)}")
        return 0

    if a.next:
        n = pick_next(rows)
        if not n:
            print("NOTHING LEFT AT THIS TIER — every chapter has its floor of passes.")
            return 0
        print(f"NEXT: chapter {n['ch']}  rate {n['rate']:.3f}  {n['pass']}/{n['achievable']}  "
              f"walks so far {n['n_passes']}" + ("  REF-GAP " + ",".join(n["ref_gaps"]) if n["ref_gaps"] else ""))
        return 0

    if a.start:
        ch = a.start
        m = mats.get(ch)
        if not m:
            print(f"no matrix for chapter {ch} — run --phase measure first")
            return 2
        p, ach = rate_of(m)
        rec = s["chapters"].setdefault(str(ch), {"passes": []})
        rec["in_progress"] = {"at": now(), "pass_before": p, "achievable_before": ach}
        save(s)
        print(f"STARTED walk of chapter {ch} at {p}/{ach}. Record it with --record {ch}.")
        return 0

    ch = a.record
    rec = s["chapters"].setdefault(str(ch), {"passes": []})
    ip = rec.get("in_progress")
    if not ip:
        print(f"REFUSED: no --start recorded for chapter {ch}. The before-rate must be captured BEFORE the "
              f"work, or the pass cannot be shown to have changed anything.")
        return 3
    sig = [x.strip() for x in a.signals.split(",") if x.strip()]
    dia = [x.strip() for x in a.diagnostics.split(",") if x.strip()]
    if not sig:
        print("REFUSED: --signals is required. Name the router signals that fired, or 'none' explicitly.")
        return 3
    if not dia:
        print("REFUSED: --diagnostics is required. A pass that ran no diagnostic is not a pass — the verdict "
              "'this is recognizer damage' has been reached twice by elimination in this campaign and been "
              "wrong both times.")
        return 3
    if not a.rule and not a.alert:
        print("REFUSED: a pass ends in a RULE or an ALERT. Finding no rule is an ALERT to redesign the "
              "approach (CHAPTER-WORKFLOW B5) — it is never silently 'done'.")
        return 3
    if a.changed_text and not a.audited:
        print("REFUSED: this pass edited text and did not run faithfulness_audit.py. That gate has caught "
              "eleven rules in this tree, one of them written by me.")
        return 3
    m = mats.get(ch, {})
    p, ach = rate_of(m)
    entry = {"at": now(), "pass_before": ip["pass_before"], "pass_after": p, "achievable": ach,
             "delta": p - ip["pass_before"], "signals": sig, "diagnostics": dia,
             "rule": a.rule, "alert": a.alert, "changed_text": bool(a.changed_text),
             "audited": bool(a.audited), "notes": a.notes}
    prior = rec["passes"]
    if prior and prior[-1].get("diagnostics") == dia and prior[-1].get("signals") == sig and entry["delta"] == 0:
        print("REFUSED: this pass ran the same diagnostics on the same signals as the previous one and moved "
              "nothing. A second walk must differ from the first, or it is a re-read, not a pass.")
        return 3
    prior.append(entry)
    rec.pop("in_progress", None)
    save(s)
    print(f"RECORDED walk {len(prior)} of chapter {ch}: {ip['pass_before']} -> {p} ({p-ip['pass_before']:+d}) "
          f"of {ach}. signals={','.join(sig)} diagnostics={','.join(dia)}")
    if a.alert:
        print(f"  ⚠ ALERT: {a.alert}\n    This chapter stays OPEN and blocks the deliverable. The alert is a "
              f"call to redesign the APPROACH, not an acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
