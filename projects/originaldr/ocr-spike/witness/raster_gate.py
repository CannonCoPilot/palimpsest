#!/usr/bin/env python3
"""raster_gate.py -- R5.2a, Gate 0d: no derivative leaf enters the recognition chain.

Master Plan §2: *"No leaf entering the recognition chain may be a derivative of another leaf
already in it: bit depth > 1, grey levels > 64, and dimensions matching the witness's raster
manifest, asserted at load time."*  `X` is the worked case -- twice `B`'s pixels and none of `B`'s
information -- and `S06`'s superseded JPEG render is the second.

🔴 **This gate was specified in three documents and implemented in none.** §2, this roadmap's R5
and the Walkthrough all described a guard that ran and had merely never refused anything; a search
for any bit-depth, grey-level, `.mode` or dimension assertion returned nothing, and the devlog had
recorded a session as *"Discharges … Gate 0d"*.  "No proven negative" and "does not exist" are
different states.  This module is the second one being corrected.

Lives beside `witnesses.py` rather than inside it: `curated_sources` imports the registry at every
source-ingest boundary, and **a pure allowlist must not drag in PIL** (R7.5c's argument -- a heavy
guard is a guard someone finds a reason to skip).  PIL is imported lazily here for the same reason.

Three clauses, reported separately, because they fail for different reasons and a caller that sees
only "inadmissible" cannot tell a bitonal scan from a mis-sized one.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import witnesses as W  # noqa: E402

MANIFEST_PATH = HERE / "raster-manifest.json"

MIN_GREY_LEVELS = 64        # §2. A render of a bitonal PDF lands far below; a scan far above.
_MANIFEST: dict | None = None


class RasterAdmissibilityError(PermissionError):
    """Raised when a leaf entering the recognition chain is a derivative, not a capture."""


def manifest() -> dict:
    global _MANIFEST
    if _MANIFEST is None:
        _MANIFEST = (json.loads(MANIFEST_PATH.read_text())
                     if MANIFEST_PATH.exists() else {"witnesses": {}})
    assert _MANIFEST is not None
    return _MANIFEST


def measure(im) -> dict:
    """Mode, bit depth, distinct grey levels and size of an open PIL image."""
    bit_depth = 1 if im.mode == "1" else 8 * len(im.getbands())
    return {
        "mode": im.mode,
        "bit_depth": bit_depth,
        "grey_levels": sum(1 for c in im.convert("L").histogram() if c),
        "width": im.width,
        "height": im.height,
    }


def check(ocr_dir: str, im, leaf_name: str | None = None) -> tuple[bool, list[str], list[str]]:
    """(admissible, failures, unknowns) for one open leaf. Never raises; `assert_admissible` does.

    `unknowns` is returned SEPARATELY and is never folded into `failures`. A clause that could not
    be evaluated is not a clause that passed -- that collapse is R1.4, and it is exactly how a
    missing manifest would have turned the dimension check into a silent yes.
    """
    m = measure(im)
    fails: list[str] = []
    unknown: list[str] = []

    if m["bit_depth"] <= 1:
        fails.append(f"bit depth {m['bit_depth']} (mode {m['mode']!r}) — bitonal; §2 requires > 1")
    if m["grey_levels"] <= MIN_GREY_LEVELS:
        fails.append(f"{m['grey_levels']} distinct grey levels — §2 requires > {MIN_GREY_LEVELS}; "
                     f"this is the signature of a render of a binarised source, not a capture")

    entry = None
    try:
        vol, sig = W.witness_of(ocr_dir)
        wrec = manifest()["witnesses"].get(W.wid(vol, sig))
        if wrec and leaf_name:
            entry = wrec["leaves"].get(leaf_name)
    except KeyError:
        pass

    if entry is None:
        unknown.append("dimensions: no manifest entry for this leaf (R5.1 unbuilt or incomplete) "
                       "— NOT CHECKED, and not thereby passed")
    elif (entry["width"], entry["height"]) != (m["width"], m["height"]):
        fails.append(f"dimensions {m['width']}x{m['height']} do not match the manifest's "
                     f"{entry['width']}x{entry['height']} for this leaf")

    return (not fails), fails, unknown


def assert_admissible(ocr_dir: str, im, leaf_name: str | None = None, *, path=None):
    """Gate 0d at the point of reading. Raises naming the clause and the witness.

    UNKNOWN clauses are PRINTED, never swallowed: a gate that cannot evaluate a clause must say so
    where the figures are, or its silence reads as an assurance it never gave.
    """
    ok, fails, unknown = check(ocr_dir, im, leaf_name)
    for u in unknown:
        print(f"[gate0d] UNKNOWN {ocr_dir}/{leaf_name or '?'}: {u}", flush=True)
    if ok:
        return
    try:
        vol, sig = W.witness_of(ocr_dir)
        who = f"{W.wid(vol, sig)} (ocr_dir {ocr_dir})"
    except KeyError:
        who = f"ocr_dir {ocr_dir}"
    raise RasterAdmissibilityError(
        f"Gate 0d refuses {who}"
        + (f" leaf {leaf_name}" if leaf_name else "")
        + (f" at {path}" if path else "") + ":\n  - " + "\n  - ".join(fails) +
        "\n  A derivative leaf still LOOKS like a page, which is why this is asserted rather than "
        "noticed. If this witness is admitted for attestation but not for glyph work, that is "
        "Gate 0f's `collation` scope and this read should not be happening (Master Plan §2)."
    )
