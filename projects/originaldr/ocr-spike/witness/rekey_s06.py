#!/usr/bin/env python3
"""rekey_s06.py — R7.5a: split the `jp2-S06` record set into its two settings.

`jp2-S06` names a FILE, not a witness.  S06 is one 2,872-leaf package carrying the
**1635 Rouen Old Testament** and the **1582 Rheims New Testament** -- two settings 53
years apart -- which the registry holds as `OT-1635-M` and `NT-1582-M`.  Every record
keyed `jp2-S06` therefore names a setting only by accident of which half it fell in.

This does the re-key, and it also removes an off-by-one that was sitting underneath it.

THE OFF-BY-ONE.  The OCR corpus for S06 is **1-based** (`S06_0001` .. `S06_2872`) while
every raster rendering of it -- the JP2 package, the JPEG re-acquisition and `S06.pdf`
-- is **0-based** (`0000` .. `2871`).  So OCR page N is package leaf N-1, and nothing
recorded that: `JP2_INDEX_OFFSET` had no entry for `jp2-S06`, which asserts alignment.
Text and image therefore disagreed by one leaf for all 2,872 pages, silently, exactly
as the roadmap warns for `jp2-S09ot2` (which DOES carry its verified -1).

Verified at two points ~1,000 leaves apart, on content that cannot be mistaken:
  * OCR `S06_2071` reads `FAVLTS ESCAPED IN THE PRINTING`; package leaf **2070** is
    that page (rendered and read).
  * OCR `S06_1029` reads `THE SECOND TOME OF THE HOLIE BIBLE`; package leaf **1028**
    is that page.  And OCR `S06_1028` is empty where package **1027** is blank.
An ink-fraction correlation was tried first and is a DEAD METRIC here -- r <= 0.13 at
every offset from -3 to +3, including the true one.  A null from it is not evidence,
and it would have "preferred" +1.  Reading the leaf is what settled it.

So the re-key does not add two offset-table entries.  It **renumbers the files to be
witness-relative and 0-based**, like every other volume, which removes the offset
rather than recording it.  An offset that does not need to exist is one that cannot be
dropped in a later refactor.

  jp2-S06/S06_0001 .. S06_2071   ->  jp2-S06ot/S06ot_0000 .. S06ot_2070   (2071 leaves)
  jp2-S06/S06_2072               ->  the BLANK DIVIDER, in neither witness (held aside)
  jp2-S06/S06_2073 .. S06_2872   ->  jp2-S06nt/S06nt_0000 .. S06nt_0799   (800 leaves)

The divider is MOVED ASIDE, not deleted.  It is a real leaf of a real book; what it is
not is a leaf of either setting.  Deleting it would make the package unreconstructible
from the corpus, and "we dropped one leaf because it was blank" is the kind of note
nobody writes down.

Run with --apply to move files; the default is a dry run.  Every move is recorded in
`.rekey-s06-manifest.json` so the split is reversible with --revert.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(HERE))
import witnesses as W  # noqa: E402

CORPUS = SPIKE.parent / "sources" / "our-ocr-diplomatic"
SRC = CORPUS / "jp2-S06"
DST = {"OT": CORPUS / "jp2-S06ot", "NT": CORPUS / "jp2-S06nt"}
ASIDE = CORPUS / ".jp2-S06-divider"
MANIFEST = SPIKE / ".rekey-s06-manifest.json"

# The witness-relative leaf index each half starts at, in PACKAGE coordinates.
BASE = {"OT": 0, "NT": W.S06_FIRST_NT_LEAF}
STEM = {"OT": "S06ot", "NT": "S06nt"}


def plan() -> tuple[list[tuple[pathlib.Path, pathlib.Path, str]], list[str]]:
    """(moves, problems). A move is (src, dst, half)."""
    moves, problems = [], []
    files = sorted(SRC.glob("*.json"))
    if not files:
        problems.append(f"{SRC} holds no page files -- nothing to re-key "
                        f"(already split, or the corpus is not where this expects)")
        return moves, problems
    if len(files) != 2872:
        problems.append(f"{SRC} holds {len(files)} page files, expected 2872; the "
                        f"package boundary was verified against a 2872-leaf file and "
                        f"a different count means this plan is not about that file")
    for f in files:
        n = int(f.stem.split("_")[-1])          # 1-based OCR page number
        pkg = n - 1                             # -> 0-based package leaf (verified)
        try:
            half = W.s06_volume(pkg)
        except ValueError:                      # the blank divider
            moves.append((f, ASIDE / f.name, "DIVIDER"))
            continue
        except IndexError as e:
            problems.append(f"{f.name}: {e}")
            continue
        leaf = pkg - BASE[half]                 # witness-relative, 0-based
        moves.append((f, DST[half] / f"{STEM[half]}_{leaf:04d}.json", half))
    return moves, problems


def check(moves) -> list[str]:
    """Post-conditions the split must satisfy, asserted before anything is moved."""
    bad = []
    per = {"OT": [], "NT": [], "DIVIDER": []}
    for _s, d, half in moves:
        per[half].append(d)
    for half in ("OT", "NT"):
        want = W.WITNESSES[(half, "M")]["leaves"]
        got = len(per[half])
        if got != want:
            bad.append(f"{half}: {got} leaves, registry says {want}")
        idx = sorted(int(p.stem.split('_')[-1]) for p in per[half])
        if idx and idx != list(range(len(idx))):
            bad.append(f"{half}: indices are not a contiguous 0..{len(idx)-1} run")
    if len(per["DIVIDER"]) != 1:
        bad.append(f"expected exactly 1 blank divider, planned {len(per['DIVIDER'])}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually move the files")
    ap.add_argument("--revert", action="store_true", help="undo using the manifest")
    a = ap.parse_args(argv)

    if a.revert:
        if not MANIFEST.exists():
            print(f"no manifest at {MANIFEST}; nothing to revert")
            return 1
        m = json.loads(MANIFEST.read_text())
        n = 0
        for src, dst, _half in m["moves"]:
            if pathlib.Path(dst).exists():
                pathlib.Path(src).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(dst, src)
                n += 1
        print(f"reverted {n} file(s) to {SRC}")
        return 0

    moves, problems = plan()
    for p in problems:
        print(f"PROBLEM: {p}")
    if problems:
        return 1

    bad = check(moves)
    counts = {h: sum(1 for _s, _d, x in moves if x == h) for h in ("OT", "NT", "DIVIDER")}
    print(f"planned: OT {counts['OT']} · NT {counts['NT']} · divider {counts['DIVIDER']}"
          f"  (total {len(moves)})")
    for h in ("OT", "NT", "DIVIDER"):
        ex = [(s.name, d.name) for s, d, x in moves if x == h]
        if ex:
            print(f"  {h:8} {ex[0][0]} -> {ex[0][1]}   ...   {ex[-1][0]} -> {ex[-1][1]}")
    if bad:
        print("\nREFUSING -- the plan does not satisfy the registry:")
        for b in bad:
            print(f"  {b}")
        return 1
    print("post-conditions hold: both halves match the registry's leaf counts and are "
          "contiguous from 0")

    if not a.apply:
        print("\ndry run. re-run with --apply to move the files.")
        return 0

    for d in list(DST.values()) + [ASIDE]:
        d.mkdir(parents=True, exist_ok=True)
    for src, dst, _h in moves:
        # The page file carries its own stem as `"page"`. Nothing reads it today, which
        # is exactly why it would be left stale -- and a file named S06ot_0000 that says
        # it is S06_0001 inside is a contradiction waiting to be believed by whichever
        # of the two a later reader happens to check.
        try:
            d = json.loads(src.read_text())
            if isinstance(d, dict) and "page" in d:
                d["page"] = dst.stem
                src.write_text(json.dumps(d, ensure_ascii=False))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARN {src.name}: page id not rewritten ({e})")
        shutil.move(str(src), str(dst))
    MANIFEST.write_text(json.dumps(
        {"step": "R7.5a", "note": "jp2-S06 split into its two settings; OCR page N was "
                                  "package leaf N-1, so files are renumbered 0-based and "
                                  "witness-relative and need no index offset",
         "moves": [[str(s), str(d), h] for s, d, h in moves]}, indent=1))
    left = list(SRC.glob("*.json"))
    if not left:
        SRC.rmdir()
    print(f"\nmoved {len(moves)} file(s); manifest -> {MANIFEST.name}"
          + (f"; {len(left)} file(s) left in {SRC.name}" if left else f"; {SRC.name} removed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
