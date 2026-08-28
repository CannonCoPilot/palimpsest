#!/usr/bin/env python3
"""R2.1b ACCEPTANCE -- choose the recogniser on MEASURED CER over a set held out from all five.

⚠️ WHAT THIS STEP EXISTS TO STOP. Five fine-tunes sit on this disk carrying headline accuracies of
0.9739, 0.9694, 0.9396, 0.9349 and 0.9230, and the Roadmap forbids reading them as a ranking in
terms: *"`0.9739 > 0.9396` IS NOT A FINDING AND MUST NOT BE QUOTED AS ONE ... comparability is
UNKNOWN, and establishing it is precisely what this step is for."* Each is a per-arm validation
accuracy on its OWN split. **A number that is higher on a different held-out set is not a better
model.** R13.1 may not wire a model until one has been chosen on evidence, because wiring an
unselected model replaces "no model" with "an arbitrary model" -- the harder defect to see.

THE SET. `witness/build_recog_gold.py` cuts one crop per REGION SEGMENT from OT1-1609-B leaves
400-419, named by the agent's own class, and truth is **hand-keyed from the page**. It is held out
from every training manifest on disk -- proven separately by `witness/audit_recog_holdout.py`, which
must pass before this runs. ⚠️ Truth is NOT taken from GOLD-HEADBAND's `text` field, which is the
INCUMBENT RECOGNISER'S OUTPUT and visibly wrong in places (leaf 402's running head reads `NVMENE`);
scoring candidates against it would measure agreement with the instrument being replaced.

═══════════════════════════════════════════════════════════════════════════════════════════════
THE SELECTION RULE, PRE-REGISTERED -- written into this file BEFORE it was first run.

  V  ſ-SURFACE VETO, APPLIED FIRST AND ABSOLUTELY. A model whose ſ recall over the keyed set is
     below 0.90 is EXCLUDED FROM SELECTION whatever its CER. ⚠️ This is not a tiebreak. This
     edition's whole re-OCR ladder exists to recover the archaic long s; a recogniser that silently
     modernises it scores well on content and is USELESS HERE, which is why `rung2_eval_lines`
     carries two metrics rather than one. A vetoed model with the best CER is still vetoed.

  S  SELECT ON CLASS WINS, NOT ON A POOLED MEAN. Among un-vetoed models, the selected model is the
     one best-or-tied on the MOST region classes by mean content accuracy. ⚠️ A pooled figure would
     be a MainText benchmark wearing a per-class label -- scripture outnumbers every other class on
     the page -- and R14.4 already states the policy: *recognition reported PER REGION CLASS, never
     as one page figure.*

  T  TIES are broken by pooled character accuracy over every keyed line.

  N  NO SELECTION IS A PERMITTED OUTCOME AND IS NOT A FAILURE OF THE RUN. If the top two un-vetoed
     models tie on class wins AND on the tiebreak, R2.1b records NO SELECTION and stays OPEN.
     ⚠️ Picking a winner out of a tie would be choosing on noise and calling it a measurement --
     and R13.1 would then wire a model this step did not actually select.

  ⚠️ EVERY MODEL'S NUMBERS ARE REPORTED, WINNERS AND LOSERS ALIKE (§0.2 rule 1, applied to a
     component). A selection whose rejected candidates are not published cannot be checked.
═══════════════════════════════════════════════════════════════════════════════════════════════

    ../ocr-venv/bin/python witness/score_recognisers.py

Exit 0 when a model is selected under the rule above; exit 1 while R2.1b is unresolved -- including
the honest NO SELECTION outcome, which leaves the step OPEN and therefore blocks R13.1.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

from audit_recog_holdout import MODELS                     # noqa: E402
from build_recog_gold import OUT, MANIFEST                 # noqa: E402

S_VETO = 0.90
RESULT = _HERE / "recog-selection.json"


def main() -> int:
    import rung2_eval_lines as EV

    man = json.loads(MANIFEST.read_text())
    lines = [e for e in man["lines"] if not e.get("excluded")]
    pairs, cls_of = [], {}
    for e in lines:
        p = OUT / f"{e['stem']}.png"
        g = OUT / f"{e['stem']}.gt.txt"
        if not (p.is_file() and g.is_file() and g.read_text().strip()):
            print(f"🔴 UNKEYED: {e['stem']} has no truth. R2.1b cannot score against a blank — that")
            print("   would report a total failure as a perfect score. Key it or exclude it with a")
            print("   reason. Run: ../ocr-venv/bin/python witness/build_recog_gold.py --check")
            return 1
        pairs.append((p, g.read_text().strip()))
        cls_of[p.name] = e["cls"]

    classes = sorted({e["cls"] for e in lines})
    print("R2.1b — RECOGNISER SELECTION on a set held out from all five")
    print(f"{man['witness']} leaves 400-419; {len(pairs)} hand-keyed lines over "
          f"{len(classes)} region classes")
    print(f"keying: {man['keying']['operator']}")
    n_char = {c: sum(len(g) for p, g in pairs if cls_of[p.name] == c) for c in classes}
    print("\n  the set, per class — ⚠️ THE CHARACTER COUNTS ARE PRINTED because a CER over a dozen")
    print("  characters is a real number about very little, and the honest handling is to show n:")
    for c in classes:
        n = sum(1 for p, _ in pairs if cls_of[p.name] == c)
        print(f"    {c:3s} {n:3d} line(s)  {n_char[c]:5d} char(s)")
    print(f"  ⚠️ {sum(1 for e in man['lines'] if e.get('excluded'))} further crop(s) were EXCLUDED "
          f"with stated reasons — see the manifest.")
    print("  ⚠️ MN IS THE THINNEST CLASS AND IT IS THE ONE THIS EDITION IS BUILT AROUND: the cutter")
    print("     fails hardest exactly there (merged margin columns, clipped sorts). Stated, not hidden.")

    scored = {}
    for name, (rel, headline) in MODELS.items():
        path = SPIKE / rel
        print(f"\n=== {name} ({rel}) ===", flush=True)
        r = EV.evaluate(path, pairs)
        if not r.get("n"):
            print("  🔴 produced nothing — reported, never silently skipped")
            scored[name] = None
            continue
        per = {}
        for c in classes:
            rows = [x for x in r["lines"] if cls_of[x["png"]] == c]
            per[c] = mean(x["content"] for x in rows) if rows else None
        scored[name] = {"headline": headline, "pooled": r["content_mean"],
                        "cer": r["cer"], "s_recall": r["s_recall"],
                        "s_gt": r["s_gt"], "s_got": r["s_got"], "per": per,
                        "worst": sorted(r["lines"], key=lambda x: x["content"])[:3]}
        print(f"  pooled content {r['content_mean']:.4f} (CER {r['cer']:.4f})   "
              f"ſ recall {r['s_recall'] if r['s_recall'] is None else round(r['s_recall'], 4)}"
              f"  ({r['s_got']} produced / {r['s_gt']} in truth)")
        print("  per class: " + "  ".join(
            f"{c}={per[c]:.4f}" if per[c] is not None else f"{c}=—" for c in classes))

    live = {k: v for k, v in scored.items() if v}
    print("\n" + "=" * 96)
    print("V — THE ſ-SURFACE VETO, applied FIRST and absolutely:")
    ok = {}
    for k, v in sorted(live.items()):
        s = v["s_recall"]
        passed = s is not None and s >= S_VETO
        print(f"    {k:16s} ſ recall {('—' if s is None else f'{s:.4f}'):8s} "
              f"{'ok' if passed else f'🔴 VETOED (< {S_VETO:.2f}) — modernises the long s'}")
        if passed:
            ok[k] = v
    if not ok:
        print("\n🔴 EVERY MODEL IS VETOED ON ſ. That is a finding about the fine-tunes, not about")
        print("   this set — and it BLOCKS R13.1 rather than being worked around by dropping the")
        print("   veto, which exists because this edition's whole ladder is about the long s.")
        RESULT.write_text(json.dumps({"selected": None, "why": "all vetoed", "scored": _clean(scored)},
                                     indent=1, ensure_ascii=False))
        return 1

    print("\nS — CLASS WINS among un-vetoed models (best-or-tied per class, ties shared):")
    wins = {k: 0 for k in ok}
    for c in classes:
        vals = {k: v["per"][c] for k, v in ok.items() if v["per"][c] is not None}
        if not vals:
            continue
        best = max(vals.values())
        w = [k for k, x in vals.items() if abs(x - best) < 1e-9]
        for k in w:
            wins[k] += 1
        print(f"    {c:3s} best {best:.4f}  -> {', '.join(sorted(w))}")
    order = sorted(wins.items(), key=lambda kv: (-kv[1], -ok[kv[0]]["pooled"]))
    print("\n    class wins: " + ", ".join(f"{k} {n}" for k, n in order))

    top, second = order[0], (order[1] if len(order) > 1 else (None, -1))
    tied = second[0] is not None and second[1] == top[1] and \
        abs(ok[top[0]]["pooled"] - ok[second[0]]["pooled"]) < 1e-9
    print("\nT — tiebreak, pooled content accuracy: " +
          ", ".join(f"{k} {ok[k]['pooled']:.4f}" for k, _ in order))

    print("\n" + "=" * 96)
    if tied:
        print("N — NO SELECTION. The top two tie on class wins AND on the tiebreak, and the")
        print("    pre-registered rule forbids picking a winner out of a tie: that would be")
        print("    choosing on noise and calling it a measurement. R2.1b stays OPEN and R13.1")
        print("    stays BLOCKED. ⚠️ This is a permitted outcome, not a failed run.")
        RESULT.write_text(json.dumps({"selected": None, "why": "tie", "scored": _clean(scored)},
                                     indent=1, ensure_ascii=False))
        return 1

    sel = top[0]
    print(f"✅ SELECTED: {sel}  ({MODELS[sel][0]})")
    print(f"   on {top[1]} class win(s) of {len(classes)}, pooled content "
          f"{ok[sel]['pooled']:.4f}, ſ recall {ok[sel]['s_recall']:.4f}")
    print("\n   THE REJECTED CANDIDATES, RECORDED (§0.2 rule 1 — a selection whose losers are not")
    print("   published cannot be checked):")
    for k, n in order[1:]:
        print(f"     {k:16s} {n} class win(s), pooled {ok[k]['pooled']:.4f}, "
              f"ſ recall {ok[k]['s_recall']:.4f}")
    for k, v in sorted(scored.items()):
        if v and k not in ok:
            print(f"     {k:16s} VETOED on ſ ({v['s_recall']:.4f}) — its pooled content "
                  f"{v['pooled']:.4f} is NOT a reason to reinstate it")

    print("\n⚠️ WHAT THIS DOES AND DOES NOT ESTABLISH. It establishes a COMPARABLE ranking on one")
    print("   held-out set of one witness, per region class, with the losers published. It does NOT")
    print("   establish that the winner is good enough for any gate: rows 10a/10b and row 11 are")
    print("   reserved for GOLD-LAYOUT and Gate 11, and the headline validation accuracies these")
    print("   models carry remain NON-COMPARABLE and must still never be quoted as a ranking.")
    RESULT.write_text(json.dumps({"selected": sel, "rel": MODELS[sel][0],
                                 "why": f"{top[1]} class wins", "veto": S_VETO,
                                  "scored": _clean(scored)}, indent=1, ensure_ascii=False))
    print(f"\n   selection recorded -> {RESULT.relative_to(SPIKE)}")
    return 0


def _clean(scored):
    out = {}
    for k, v in scored.items():
        if not v:
            out[k] = None
            continue
        d = dict(v)
        d["worst"] = [{"gt": w["gt"], "got": w["got"], "content": round(w["content"], 4)}
                      for w in v["worst"]]
        out[k] = d
    return out


if __name__ == "__main__":
    raise SystemExit(main())
