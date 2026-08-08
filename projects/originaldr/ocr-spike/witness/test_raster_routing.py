"""R7.5 — there is ONE route to the pixels, and the guard is on it.

The defect this test exists to prevent, stated exactly: `jp2_page.py` held a
hand-written `ocr_dir` -> raster-directory table, `witnesses.py` held
`pixel_source()`, and **the table never called the guard**.  Both routes worked.
Only one of them refused an inadmissible image.  Commit c44ba20 *verified* that the
table was the mechanism that routed 48 of 51 ground-truth transcriptions to the
wrong raster, and the table was still routing when this test was written -- so a
verified defect can stay live indefinitely, and what stops that is a test, not a
finding.

What it checks:
  1. `jp2_page` no longer defines a raster-directory table at all.  Not "the table
     is correct now" -- the table is the defect, because a second mapping can always
     drift from the registry.  A revived `OCR_DIR_TO_JP2` FAILS.
  2. Every legacy `ocr_dir` resolves to a registered witness.
  3. Every witness barred from glyph work RAISES on the pixel route, and does so
     for all of its `ocr_dir` aliases -- an alias that skips the guard is the
     defect in miniature.
  4. The same witnesses still WORK on the structure route.  The guard must not
     have been bought by making a render inaccessible for page counting, which is
     legitimate and which the R1/R2/R3 work depends on.
  5. The pixel route resolves inside the artefact the registry names.  This is the
     `jp2-S04` case: the old table pointed at the retired MRC composite while the
     registry resolved the acquired Princeton original, and both paths existed on
     disk, so nothing failed.
  6. `JP2_INDEX_OFFSET` for `jp2-S09ot2` survives.  It is a verified off-by-one
     (OCR page 40 is leaf 0039); losing it in a refactor silently returns the NEXT
     LEAF for every page of S9's entire Old Testament volume 2.
  7. The ambiguous `jp2-S06` raises rather than guessing a volume, and names the
     two well-formed ids.
  8. `GLYPH_BARRED` has exactly one definition in the tree.
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SPIKE))

import witnesses as W          # noqa: E402
import jp2_page as J           # noqa: E402

FAILURES = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILURES.append(f"{label}: {detail}")


def main():
    print("the second routing table must not exist:")
    check("jp2_page has no OCR_DIR_TO_JP2", not hasattr(J, "OCR_DIR_TO_JP2"),
          "a second ocr_dir -> raster-directory mapping is back; it can drift from "
          "the registry, which is R7.5 itself")
    src = (SPIKE / "jp2_page.py").read_text()
    check("jp2_page defines no raster dir literals",
          not re.search(r'^\s*"(archive|jp2|pdf)-[^"]*":\s*\(\s*"S\d', src, re.M),
          "an ocr_dir is mapped to a ('Sn', 'path/...') pair again")

    print("\nevery legacy ocr_dir resolves to a REGISTERED witness:")
    registered = set(W.WITNESSES)
    for od, key in sorted(J.OCR_DIR_TO_WITNESS.items()):
        check(f"{od:26s} -> {key}", key in registered, "not in the registry")

    barred, ok_glyph = [], []
    for od, key in sorted(J.OCR_DIR_TO_WITNESS.items()):
        try:
            W.glyph_source(*key)
            ok_glyph.append((od, key))
        except ValueError:
            barred.append((od, key))

    # The bar set is asserted, not merely reported.
    #
    # An earlier version of this test only checked that whatever was barred refused
    # pixels and whatever was not resolved cleanly -- which is self-consistent and
    # therefore useless: deleting `F` from GLYPH_BARRED moved it from one list to the
    # other and the test still PASSED. Proven by injection, and it is the exact shape
    # of the four-month error (a check that adapts to the claim it should be testing).
    # These two are barred for reasons recorded in 1.2 and 1.1a; removing either is a
    # decision that must be made deliberately, and changing this line is how it is made.
    EXPECT_BARRED = {"F", "X"}
    print(f"\nthe bar set must be exactly {sorted(EXPECT_BARRED)}:")
    check(f"GLYPH_BARRED == {sorted(EXPECT_BARRED)}",
          set(W.GLYPH_BARRED) == EXPECT_BARRED,
          f"got {sorted(W.GLYPH_BARRED)} -- a witness was barred or un-barred without "
          f"this test being updated, so the change was not deliberate")

    print(f"\nall {len(barred)} barred alias(es) must RAISE on the pixel route:")
    check("at least one witness is barred", bool(barred),
          "nothing is barred, so this test cannot show the guard works at all")
    for od, key in barred:
        try:
            J.pixel_path(od, 100)
            check(f"{od:26s} ({W.wid(*key)}) refuses pixels", False,
                  "returned a path for a witness barred from glyph work")
        except J.InadmissibleRaster:
            check(f"{od:26s} ({W.wid(*key)}) refuses pixels", True)
        except Exception as e:
            check(f"{od:26s} ({W.wid(*key)}) refuses pixels", False,
                  f"raised {type(e).__name__}, not InadmissibleRaster: {e}")

    print("\n...and must still WORK on the structure route (page order is admissible):")
    for od, key in barred:
        try:
            p = J.structure_path(od, 100)
            check(f"{od:26s} structure_path -> {p.name[:34]}", p.exists(),
                  "resolved to a path that does not exist")
        except Exception as e:
            check(f"{od:26s} structure_path", False,
                  f"{type(e).__name__}: {e} -- the guard must not break page counting")

    print("\nthe pixel route must resolve INSIDE the artefact the registry names:")
    for od, key in ok_glyph:
        kind, named = W.glyph_source(*key)
        try:
            got = J.pixel_path(od, 100)
        except Exception as e:
            check(f"{od:26s} resolves", False, f"{type(e).__name__}: {e}")
            continue
        if kind == "jp2":
            inside = Path(named) == got.parent
            check(f"{od:26s} -> {got.parent.name[:38]}", inside,
                  f"resolved outside the registry's artefact: registry says "
                  f"{Path(named).name}, got {got.parent.name}")
        else:
            # PDF-primary: the leaf is extracted, so it lives in the cache, not in
            # the PDF. What matters is that it came from the named PDF's witness.
            check(f"{od:26s} -> extracted from {Path(named).name}",
                  W.wid(*key) in str(got), f"extraction path {got} does not name the witness")

    print("\nthe verified S09ot2 off-by-one must survive any refactor:")
    check("jp2-S09ot2 offset is -1", J.JP2_INDEX_OFFSET.get("jp2-S09ot2") == -1,
          "the offset is gone; page N now silently returns the NEXT LEAF for every "
          "page of S9's Old Testament volume 2")
    try:
        p = J.pixel_path("jp2-S09ot2", 40)
        check(f"jp2-S09ot2 page 40 -> {p.name}", p.stem.endswith("_0039"),
              f"expected a leaf ending _0039, got {p.name}")
    except Exception as e:
        check("jp2-S09ot2 page 40 resolves", False, f"{type(e).__name__}: {e}")

    print("\nan ocr_dir that names a FILE spanning two settings must not be guessed:")
    try:
        J.pixel_path(J.S06_AMBIGUOUS, 100)
        check(f"{J.S06_AMBIGUOUS} refuses to pick a volume", False,
              "resolved to one of two settings 53 years apart")
    except KeyError as e:
        msg = str(e)
        check(f"{J.S06_AMBIGUOUS} refuses to pick a volume", True)
        check("   ...and names the well-formed ids",
              all(k in msg for k in J.S06_SPLIT),
              f"refusal does not name {sorted(J.S06_SPLIT)}")
    except Exception as e:
        check(f"{J.S06_AMBIGUOUS} refuses to pick a volume", False,
              f"raised {type(e).__name__}: {e}")

    print("\nand the bar list must have exactly one definition in the tree:")
    defs = []
    for root, _dirs, files in os.walk(SPIKE):
        if "/.git" in root or "__pycache__" in root or "/.scratch" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            p = Path(root) / f
            try:
                if re.search(r"^\s*(BARRED|GLYPH_BARRED)\s*=\s*\{", p.read_text(), re.M):
                    defs.append(str(p.relative_to(SPIKE)))
            except OSError:
                continue
    check(f"one definition of the bar list, found {defs}", len(defs) == 1,
          "two copies of 'which witnesses are barred' will drift, which is R7.5 "
          "one level up")

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}\n---")
        for f in FAILURES:
            print(f"  {f}")
        return 1
    print(f"all checks passed — {len(J.OCR_DIR_TO_WITNESS)} ocr_dirs route through the "
          f"registry; {len(barred)} barred alias(es) refuse pixels and still serve structure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
