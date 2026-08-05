#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_split_v3.py — VERIFIED train/val arrows for the item-2 R2 experiment (§13 Q38/Q39, 2026-07-29).

Three filters, in this order, each with its own justification:

1. **PER-PAIR VERIFICATION** (`rung2_pair_verify.py`). Every crop re-read; a pair is kept only if its GT is the
   right LENGTH for the pixels and is the best-matching gold line in its file. Validated against 40 hand-read
   lines: catches 82% of mislabelled pairs, retains 90% of good ones. 1,848 -> 1,394.

2. **WHOLE-FILE EXCLUSION FOR TABLE-LIKE GT**, chosen from the drop rate rather than from filenames. A GT file
   whose pairs the verifier rejects at a high rate is one whose structure breaks the harvester's core assumption
   (one GT entry = one visual line): a table row set across two columns, or an entry wrapped over two lines.
   Guessing "table" from a slug would have mis-sorted `matter-ot1-summe-of-old-testament` (52% dropped, reads as
   prose by name) and `matter-nt-signification-or-meaning` (clean, sounds like a glossary). The measurement knows;
   the filename does not.

3. **LEAF/FILE-LEVEL VAL SPLIT.** Whole scripture GT files are held out, so no line of a val page can appear in
   training in any form. See `rung2_split_v2.py` for why a line-level split leaks here.

The val set is verified too: a mislabelled val line penalises both arms at random and only adds noise to the
comparison the experiment exists to make.

Usage: ../ocr-venv/bin/python rung2_split_v3.py [--drop-rate 0.30] [--val-files 4]
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KETOS = str(HERE.parent / "ocr-venv" / "bin" / "ketos")


def compile_arrow(pngs: list[Path], out: Path) -> int:
    if out.exists():
        out.unlink()
    if not pngs:
        print(f"  ! nothing to compile for {out.name}")
        return 1
    print(f"  compiling {len(pngs)} lines -> {out.name} …", flush=True)
    rc = subprocess.run([KETOS, "compile", "-f", "path", "--force-type", "bbox", "-o", str(out)]
                        + [str(p) for p in pngs], cwd=str(HERE), capture_output=True, text=True)
    if rc.returncode != 0:
        print(f"  FAILED:\n{rc.stderr[-1200:]}", file=sys.stderr)
        return rc.returncode
    print(f"  ok ({out.stat().st_size/1e6:.1f} MB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".rung2-data-v2")
    ap.add_argument("--verify", default="rung2-pair-verify.json")
    ap.add_argument("--drop-rate", type=float, default=0.30,
                    help="exclude a GT file wholesale above this verifier drop rate (table-like structure)")
    ap.add_argument("--val-files", type=int, default=4)
    a = ap.parse_args()
    d = HERE / a.data
    rows = json.loads((HERE / a.verify).read_text())

    tot = collections.Counter()
    dropped = collections.Counter()
    for r in rows:
        tot[r["slug"]] += 1
        if not r["keep"]:
            dropped[r["slug"]] += 1
    table_like = {s for s in tot if dropped[s] / tot[s] > a.drop_rate}
    print(f"TABLE-LIKE GT FILES excluded wholesale (drop rate > {a.drop_rate:.0%}):")
    for s in sorted(table_like):
        print(f"  {s:<46} {dropped[s]}/{tot[s]} = {dropped[s]/tot[s]:.0%}")
    prose_kept = [r for r in rows if r["keep"] and r["slug"] not in table_like]
    print(f"\nsurviving pairs: {len(prose_kept)} of {len(rows)}")

    scripture = sorted({r["slug"] for r in prose_kept if r["slug"].startswith("scripture-")})
    matter = sorted({r["slug"] for r in prose_kept if not r["slug"].startswith("scripture-")})
    step = max(1, len(scripture) // a.val_files)
    val_slugs = set(scripture[::step][:a.val_files])
    print(f"scripture files {len(scripture)} (val: {sorted(val_slugs)})")
    print(f"matter PROSE files {len(matter)}")

    def pngs(pred):
        return [d / f"line_{r['id']:04d}.png" for r in prose_kept if pred(r)]

    sets = {
        "v3_val_scripture": pngs(lambda r: r["slug"] in val_slugs),
        "v3_train_scripture": pngs(lambda r: r["slug"].startswith("scripture-") and r["slug"] not in val_slugs),
        "v3_train_matter_prose": pngs(lambda r: not r["slug"].startswith("scripture-")),
    }
    for k, v in sets.items():
        print(f"  {k:<24} {len(v)} lines")
    rc = 0
    for k, v in sets.items():
        rc |= compile_arrow(v, d / f"{k}.arrow")
    (HERE / "rung2-split-v3.json").write_text(json.dumps(
        {"table_like_excluded": sorted(table_like), "val_slugs": sorted(val_slugs),
         "counts": {k: len(v) for k, v in sets.items()}}, indent=1))
    print("\nARM A: --train-arrow v3_train_scripture.arrow")
    print("ARM B: --train-arrow v3_train_scripture.arrow,v3_train_matter_prose.arrow")
    print("both:  --val-arrow v3_val_scripture.arrow")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
