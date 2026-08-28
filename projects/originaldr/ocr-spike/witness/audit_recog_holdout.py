#!/usr/bin/env python3
"""R2.1b PREREQUISITE -- prove the selection set is HELD OUT from all five recognisers.

⚠️ THIS RUNS BEFORE ANY SCORE, AND IT IS NOT A FORMALITY. R2.1b exists because the five models'
headline figures are NOT COMPARABLE: each is a per-arm validation accuracy on its OWN split, and the
Roadmap says so in terms -- *"`0.9739 > 0.9396` IS NOT A FINDING AND MUST NOT BE QUOTED AS ONE ...
comparability is UNKNOWN, and establishing it is precisely what this step is for."* The only way to
make them comparable is one fixed set none of them trained on. **A selection made on a set some
model has seen selects that model**, and the result would look exactly like a measurement.

WHAT IS CHECKED, against the training manifests actually on disk:

  1. `.rung2-data/_manifest.json`    -- the line corpus behind `reichenau_dr`, `dr_armA`, `dr_v3_*`
  2. `.rung2-chapters/_manifest.json`-- the chapter-aligned corpus, with `page` and `ocr_dir` per line
  3. `rung2-split-v3.json`           -- the v3 val slugs
  4. `rung2_holdout_prep.HELDOUT_SLUGS` -- what `reichenau_dr_ho` was built to exclude

⚠️ AND THE BOUND IS STATED RATHER THAN THE SCOPE CLAIMED. This proves the eval leaves appear in no
training manifest ON THIS DISK. A model trained from a manifest that is not on this disk would be
invisible to this check, and that is reported as a limit, not papered over -- the same discipline
`audit_label_sources.py` had to learn twice, once when its bound was a DIRECTORY and once when its
bound was a FIELD NAME.

    ../ocr-venv/bin/python witness/audit_recog_holdout.py

Exit 0 when every eval leaf is held out from every manifest. Exit 1 on ANY overlap -- an overlap is
not a caveat to record beside a score, it invalidates the score.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

# The five models R2.1b must choose between, named here so "all five" is a checked claim rather
# than a reading of a directory listing. ⚠️ Their headline figures are recorded ONLY as the
# incomparable numbers they are; this file never ranks by them.
MODELS = {
    "reichenau_dr":    ("models/reichenau_dr/best_0.9396.mlmodel", 0.9396),
    "dr_v3_armA":      ("models/dr_v3_armA/best_0.9739.mlmodel", 0.9739),
    "dr_v3_armB":      ("models/dr_v3_armB/best_0.9694.mlmodel", 0.9694),
    "dr_armA":         ("models/dr_armA/best_0.9349.mlmodel", 0.9349),
    "reichenau_dr_ho": ("models/reichenau_dr_ho/best_0.9230.mlmodel", 0.9230),
}

# The selection set: the agent's own window. ⚠️ CHOSEN FOR A REASON, not for convenience -- it is
# the population where the confirming read is actually needed (R14.10b/c), and it is Numbers, which
# no training slug names.
EVAL_WITNESS = "OT1-1609-B"
EVAL_LEAVES = set(range(400, 420))
EVAL_BOOK_WORDS = {"numeri", "numbers"}

FAILURES: list[str] = []


def check(label: str, ok: bool, why: str = "") -> bool:
    print(f"  {'ok   ' if ok else '🔴 FAIL'}  {label}")
    if not ok:
        print(f"          {why}")
        FAILURES.append(f"{label}: {why}")
    return ok


def main() -> int:
    print("R2.1b PREREQUISITE — is the selection set held out from ALL FIVE recognisers?\n")

    print(f"the five models must each exist on disk:")
    for name, (rel, acc) in MODELS.items():
        p = SPIKE / rel
        check(f"{name:16s} {rel}", p.is_file(), "named by R2.1b but not on disk")
    print("  ⚠️ their headline accuracies are NOT compared here and must not be ranked: they are")
    print("     per-arm figures on DIFFERENT splits. Making them comparable is what R2.1b is for.\n")

    slugs: set[str] = set()
    pages: set[int] = set()
    dirs: set[str] = set()

    m1 = SPIKE / ".rung2-data" / "_manifest.json"
    if m1.is_file():
        for e in json.loads(m1.read_text()):
            slugs.add(e.get("slug", ""))
    m2 = SPIKE / ".rung2-chapters" / "_manifest.json"
    if m2.is_file():
        for e in json.loads(m2.read_text()).get("lines", []):
            pages.add(int(e["page"]))
            dirs.add(str(e.get("ocr_dir", "")))
    sp = SPIKE / "rung2-split-v3.json"
    if sp.is_file():
        d = json.loads(sp.read_text())
        slugs |= set(d.get("val_slugs", [])) | set(d.get("table_like_excluded", []))
    try:
        import rung2_holdout_prep as HP
        slugs |= set(HP.HELDOUT_SLUGS)
    except Exception:
        pass

    print(f"training material found on disk: {len(slugs)} slug(s), {len(pages)} page(s), "
          f"source dirs {sorted(dirs)}")

    # ── 1. no training slug names the eval book ───────────────────────────────────────────────
    hit_book = sorted(s for s in slugs if any(w in s.lower() for w in EVAL_BOOK_WORDS))
    check("no training slug names NUMBERS (the eval book)", not hit_book,
          f"these slugs name it: {hit_book}")

    # ── 2. no training page is an eval leaf ───────────────────────────────────────────────────
    hit_page = sorted(pages & EVAL_LEAVES)
    check(f"no training page falls in leaves {min(EVAL_LEAVES)}-{max(EVAL_LEAVES)}", not hit_page,
          f"these pages overlap: {hit_page}")
    if pages:
        print(f"          training pages span {min(pages)}-{max(pages)}; the eval window starts at "
              f"{min(EVAL_LEAVES)}")

    # ── 3. the books the training corpus DOES cover, named so the gap is legible ───────────────
    books = sorted({re.sub(r"^(scripture|matter)-", "", s).split("-")[0] for s in slugs if s})
    print(f"\n  training corpus covers: {books}")
    print(f"  the eval set is {EVAL_WITNESS} leaves {min(EVAL_LEAVES)}-{max(EVAL_LEAVES)} "
          f"(NUMERI), which is in none of them.")

    print("\n⚠️ THE BOUND, STATED. This proves the eval leaves appear in no training manifest ON")
    print("   THIS DISK. A model trained from a manifest not on this disk is invisible to this")
    print("   check. That is a limit of the check, not a property of the models — and it is said")
    print("   here because a bounded search returns 'not found' in the same shape an exhaustive")
    print("   one does, which this project has now paid for twice in `audit_label_sources.py`.")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)}")
        for f in FAILURES:
            print(f"  {f}")
        print("\n🔴 AN OVERLAP DOES NOT GET RECORDED BESIDE THE SCORE — IT INVALIDATES THE SCORE.")
        return 1
    print("\n✅ the selection set is held out from every training manifest on disk; R2.1b may score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
