#!/usr/bin/env python3
"""audit_s06_keys.py — R7.5a: nothing may still be keyed `jp2-S06`.

`jp2-S06` names a FILE, not a witness: one 2,872-leaf package carrying the 1635 Rouen
Old Testament and the 1582 Rheims New Testament, two settings 53 years apart.  R7.5a
re-keyed the AUTHORITATIVE record sets -- the OCR corpus, the ground truth, and the
addressing artefacts -- to `jp2-S06ot` / `jp2-S06nt`.

Derived artefacts built BEFORE that split still carry the old id.  They are not patched,
because patching a derived file is how a stale artefact acquires the appearance of being
current (R7.5d, where the retired routing table's OUTPUT went on routing for eleven days
after the table was deleted).  They must be REGENERATED from the re-keyed corpus.

This audit exits 1 while any remain.  An audit that starts passing before its remedy
lands has stopped looking -- which is why the count is printed, and why the list is
grouped by what has to be re-run rather than merely enumerated.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(HERE))
import witnesses as W  # noqa: E402

CORPUS = SPIKE.parent / "sources" / "our-ocr-diplomatic"
AMBIG = W.S06_AMBIGUOUS


def main() -> int:
    fatal, stale = [], {}

    # ---- 1. the authoritative record sets. These are re-keyed; a regression here is a
    #         defect, not a backlog item, so it is reported separately and first.
    print("authoritative record sets must be re-keyed:")
    d = CORPUS / AMBIG
    ok = not d.exists()
    print(f"  {'ok  ' if ok else 'FAIL'}  the OCR corpus has no {AMBIG}/ directory")
    if not ok:
        fatal.append(f"{d} still exists with {len(list(d.glob('*.json')))} page files")
    for half, od in (("OT", "jp2-S06ot"), ("NT", "jp2-S06nt")):
        want = W.WITNESSES[(half, "M")]["leaves"]
        got = len(list((CORPUS / od).glob("*.json")))
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'}  {od}/ holds {got} leaves (registry: {want})")
        if not ok:
            fatal.append(f"{od}: {got} leaves on disk, registry says {want}")

    gt = sorted((SPIKE / "ground-truth").glob("*.json"))
    bad_gt = []
    for f in gt:
        if f.name.endswith((".pre-review", ".pre-vvfix", ".pre-primary-raster")):
            continue
        try:
            if json.loads(f.read_text()).get("ocr_dir") == AMBIG:
                bad_gt.append(f.name)
        except json.JSONDecodeError:
            continue
    print(f"  {'ok  ' if not bad_gt else 'FAIL'}  no ground-truth file is keyed {AMBIG}"
          + (f"  {bad_gt}" if bad_gt else ""))
    fatal += [f"ground truth still keyed {AMBIG}: {b}" for b in bad_gt]

    # Every VARIANT, not just the plain one. The first version of this audit checked
    # `.page-address-jp2-S06.json` and passed while `.page-address-jp2-S06.heldout.json`
    # sat beside it, un-re-keyed and still feeding page_address_eval -- a check that
    # names one file cannot notice a sibling. It globs now.
    # `jp2-S06` NOT followed by the volume letters -- `jp2-S06ot` / `jp2-S06nt` are the
    # well-formed ids this step creates, and a check that flagged them would fail
    # precisely because the remedy had been applied.
    bare = re.compile(rf"{re.escape(AMBIG)}(?![a-z])")
    stragglers = sorted(p for p in SPIKE.glob("*.json")
                        if bare.search(p.name) and not p.name.startswith(".superseded"))
    ok = not stragglers
    print(f"  {'ok  ' if ok else 'FAIL'}  no addressing artefact is named for {AMBIG}"
          + (f"  {[p.name for p in stragglers]}" if stragglers else ""))
    fatal += [f"{p.name} still present and un-re-keyed" for p in stragglers]

    # A check that reads NAMES cannot see CONTENTS. The name check above passed while
    # `.page-address-jp2-S06ot.json` declared `"ocr_dir": "jp2-S06"` inside itself -- the
    # re-key renamed the file and re-indexed the records and left the field, so the artefact
    # said one thing on its cover and another on its first page. Read the field, and make
    # the registry adjudicate it: `witness_of` RAISES on the ambiguous id, so the volume
    # that cannot be named is a failure here rather than an unnamed record downstream.
    # (The invariant is general -- an addressing artefact names the volume it addressed --
    # and is enforced here because R7.5a is what made the ambiguity nameable.)
    mismatched = []
    for p in sorted(SPIKE.glob(".page-address-*.json")) + sorted(SPIKE.glob(".corpus-localize-*.json")):
        if p.name.startswith(".superseded"):
            continue
        stem = p.name.split("-", 2)[2].removesuffix(".json").removesuffix(".heldout")
        try:
            d = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        # The two generators disagree on whether the held-out split belongs in the id
        # (`corpus_localize` writes 'jp2-S08.heldout'). Normalise; the disagreement is a
        # naming convention, not a routing claim, and is recorded rather than adjudicated here.
        declared = str(d.get("ocr_dir", "")).removesuffix(".heldout")
        if declared != stem:
            mismatched.append(f"{p.name} declares ocr_dir={declared!r}, filename says {stem!r}")
            continue
        got = d.get("witness")
        if got is None:
            continue                     # only the S06 artefacts carry it yet; absence is backlog, not defect
        try:
            want = W.wid(*W.witness_of(declared))
        except KeyError as e:
            mismatched.append(f"{p.name}: {e.args[0].splitlines()[0]}")
            continue
        if got != want:
            mismatched.append(f"{p.name} declares witness={got!r}, registry says {want!r}")
    print(f"  {'ok  ' if not mismatched else 'FAIL'}  every addressing artefact's ocr_dir "
          f"matches its filename and the registry")
    for m in mismatched:
        print(f"          {m}")
    fatal += mismatched

    # ---- 2. derived artefacts. These are the backlog: regenerate, do not patch.
    for p in sorted(SPIKE.rglob("*.json")):
        s = str(p)
        if "__pycache__" in s or "/.git/" in s or "/ground-truth/" in s:
            continue
        if p.name.startswith(".superseded"):
            continue                     # kept deliberately, as the pre-split originals
        try:
            t = p.read_text()
        except OSError:
            continue
        n = len(re.findall(rf'"{re.escape(AMBIG)}"', t))
        if n:
            stale[str(p.relative_to(SPIKE))] = n

    print(f"\nderived artefacts still carrying {AMBIG!r}: {len(stale)} file(s), "
          f"{sum(stale.values())} occurrence(s)")
    for f, n in sorted(stale.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {n:7}  {f}")
    if len(stale) > 12:
        print(f"  ... and {len(stale) - 12} more")

    print()
    if fatal:
        print(f"FAILED — {len(fatal)} defect(s) in the authoritative record sets:")
        for f in fatal:
            print(f"  {f}")
        return 2
    if stale:
        print(f"OPEN (R7.5a-2) — the authoritative sets are re-keyed and correct; "
              f"{len(stale)} derived artefact(s) predate the split and must be "
              f"REGENERATED, not edited. Exit 1 is the healthy state until they are.")
        return 1
    print("all record sets name a witness and a setting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
