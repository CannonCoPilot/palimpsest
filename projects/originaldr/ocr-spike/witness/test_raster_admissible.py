#!/usr/bin/env python3
"""test_raster_admissible.py -- R5.2b: Gate 0d must REFUSE, and be seen to refuse.

Master Plan §2 names two worked cases for this gate: `NT-1582-X`, which is `B` upscaled 2.000x --
"twice `B`'s pixels and none of `B`'s information" -- and `S06`'s superseded JPEG render.  Both are
*silent* defects: a rendered leaf still looks like a page.

🔴 **The gate this tests did not exist until 2026-08-10**, though §2, roadmap R5 and the Walkthrough
all described it as a guard merely lacking a negative test.  This file is that negative test, and it
is written first-class rather than as an afterthought because R5's own note has said since it was
drafted: *"a guard that has never rejected anything is not known to work."*

Four cases, and the fourth is the one that keeps the other three honest:

  (i)   bitonal (1-bit)            -> refused on the bit-depth clause
  (ii)  few grey levels            -> refused on the grey-level clause (the render signature)
  (iii) dimensions off the manifest-> refused on the dimension clause
  (iv)  a REAL base-exemplar leaf  -> **admitted**

Without (iv) a gate that refuses everything passes (i)-(iii) perfectly.  That is the exact failure
`test_raster_routing.py` shipped with in Session 11 -- a self-consistent check constrains nothing --
and the remedy is the same: assert both directions.

Exit 0 when the gate holds. Exit 1 naming what broke.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SPIKE))
import witnesses as W  # noqa: E402
import raster_gate as RG  # noqa: E402

from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def _refused(ocr_dir, im, leaf, want: str) -> tuple[bool, str]:
    """(did it refuse for the RIGHT clause, message)."""
    try:
        RG.assert_admissible(ocr_dir, im, leaf_name=leaf)
    except RG.RasterAdmissibilityError as e:
        return (want in str(e)), str(e).replace("\n", " ")[:110]
    return False, "ADMITTED (no exception)"


def main() -> int:
    fail: list[str] = []

    man = RG.manifest()["witnesses"]
    if not man:
        fail.append("no raster manifest -- build it with build_raster_manifest.py (R5.1). "
                    "Case (iii) cannot run and this guard must not pass without it")
        print("  FAIL  no manifest; the dimension clause is untestable")
        return _report(fail)

    # A real, admitted leaf: the control for (iv) and the base for (iii)'s mutation.
    ctrl_wid = next(w for w, r in man.items() if r["leaves"])
    ctrl_leaf, ctrl_entry = next(iter(man[ctrl_wid]["leaves"].items()))
    ctrl_dir = next(od for od, (v, s) in W.OCR_DIR_TO_WITNESS.items() if W.wid(v, s) == ctrl_wid)
    print(f"control: {ctrl_wid} via ocr_dir {ctrl_dir!r}, leaf {ctrl_leaf}")

    with Image.open(ctrl_entry["path"]) as real:
        real.load()

        # ---- (iv) FIRST, deliberately. If the real leaf is refused, every refusal below is
        # meaningless and this guard would otherwise report four confident passes.
        print("\n(iv) a real base-exemplar leaf is ADMITTED:")
        try:
            RG.assert_admissible(ctrl_dir, real, leaf_name=ctrl_leaf)
            print(f"  ok    {ctrl_wid} {ctrl_leaf} admitted")
        except RG.RasterAdmissibilityError as e:
            fail.append(f"the REAL base leaf {ctrl_leaf} was refused: {e}. Every refusal below "
                        f"passes for the wrong reason until this does.")
            print(f"  FAIL  {ctrl_wid} {ctrl_leaf} REFUSED — {str(e)[:120]}")

        m = RG.measure(real)
        print(f"        measured {m['width']}x{m['height']} mode={m['mode']} "
              f"bits={m['bit_depth']} grey={m['grey_levels']}")

        print("\n(i)-(iii) inadmissible rasters are refused, each on its own clause:")
        # (i) bitonal — the shape of `M`'s CCITT and of any binarised source
        bit = real.convert("1")
        ok, msg = _refused(ctrl_dir, bit, ctrl_leaf, "bit depth")
        _mark(ok, "bitonal (mode '1')", msg, fail)

        # (ii) few grey levels — the render signature: 8-bit, but quantised
        few = real.convert("L").quantize(colors=8).convert("L")
        ok, msg = _refused(ctrl_dir, few, ctrl_leaf, "grey levels")
        _mark(ok, "8 grey levels", msg, fail)

        # (iii) dimensions disagreeing with the manifest
        small = real.resize((real.width // 2, real.height // 2))
        ok, msg = _refused(ctrl_dir, small, ctrl_leaf, "dimensions")
        _mark(ok, "half-size vs manifest", msg, fail)

    # ---- the UNKNOWN path must not read as a pass (R1.4)
    print("\na leaf with no manifest entry is UNKNOWN, not admitted-by-silence:")
    with Image.open(ctrl_entry["path"]) as real2:
        real2.load()
        _, fails, unknown = RG.check(ctrl_dir, real2, leaf_name="no-such-leaf.jp2")
        ok = bool(unknown) and not fails
        if not ok:
            fail.append(f"an unmanifested leaf produced failures={fails} unknown={unknown}; it "
                        f"must produce an UNKNOWN and no failure")
        print(f"  {'ok  ' if ok else 'FAIL'}  unknown={len(unknown)} failure={len(fails)}")

    # ---- R5.2c: the WIRING, asserted by calling the real entry point.
    #
    # Everything above calls `assert_admissible` directly, which proves the gate and proves
    # nothing about whether anything reaches it. A gate nothing calls guards nothing -- that
    # sentence is already in this repository twice (`assert_same_setting` had no caller;
    # `drop_tomes` had no consumer), and checking the wiring by READING `jp2_page.load` would be
    # the third time. So: drive the real function, with a synthetic leaf behind it.
    print("\nR5.2c — Gate 0d is reached from jp2_page.load(), proven by CALLING it:")
    import tempfile
    import jp2_page as JP

    real_jp2_path = JP.jp2_path
    with tempfile.TemporaryDirectory() as td:
        bad = pathlib.Path(td) / "0000.tif"
        Image.new("1", (64, 64), 1).save(bad)
        good = pathlib.Path(td) / "0001.tif"
        Image.open(ctrl_entry["path"]).convert("RGB").resize((64, 64)).save(good)

        try:
            JP.jp2_path = lambda ocr_dir, page_index, structure=False: (   # type: ignore[assignment]
                bad if page_index == 0 else good)

            # (a) the pixel route must REFUSE the bitonal leaf
            try:
                JP.load(ctrl_dir, 0)
            except Exception as e:                                          # noqa: BLE001
                ok = isinstance(e, RG.RasterAdmissibilityError)
                if not ok:
                    fail.append(f"jp2_page.load raised {type(e).__name__}, not a Gate 0d refusal: {e}")
                print(f"  {'ok  ' if ok else 'FAIL'}  pixel route refuses a bitonal leaf "
                      f"({type(e).__name__})")
            else:
                fail.append("jp2_page.load ADMITTED a bitonal leaf — Gate 0d is not on the read path")
                print("  FAIL  pixel route ADMITTED a bitonal leaf")

            # (b) the STRUCTURE route must still serve it. Scope and curation govern evidence,
            # never denominators (R9.2b): an inadmissible leaf still has to be counted.
            try:
                JP.load(ctrl_dir, 0, structure=True)
                print("  ok    structure route still serves it (bookkeeping is not gated)")
            except RG.RasterAdmissibilityError:
                fail.append("the STRUCTURE route was gated; 0d governs the recognition chain, not "
                            "leaf counting — gating it would hide an inadmissible volume instead "
                            "of excluding it (R7.5d)")
                print("  FAIL  structure route was gated")

            # (c) and an admissible leaf must still come back, or (a) passes for the wrong reason
            try:
                JP.load(ctrl_dir, 1)
                print("  ok    an admissible leaf still loads (the gate is not refusing all)")
            except RG.RasterAdmissibilityError as e:
                fail.append(f"jp2_page.load refused an admissible leaf: {e}")
                print(f"  FAIL  admissible leaf refused — {str(e)[:100]}")
        finally:
            JP.jp2_path = real_jp2_path

    return _report(fail)


def _mark(ok: bool, label: str, msg: str, fail: list[str]) -> None:
    if not ok:
        fail.append(f"{label}: {msg}")
    print(f"  {'ok  ' if ok else 'FAIL'}  {label:24} {msg}")


def _report(fail: list[str]) -> int:
    print()
    if fail:
        print(f"FAILED — {len(fail)} defect(s):")
        for f in fail:
            print(f"  {f}")
        return 1
    print("Gate 0d holds: three inadmissible rasters refused on three distinct clauses, a real "
          "base-exemplar leaf admitted, and an unmeasurable clause reported as UNKNOWN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
