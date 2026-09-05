#!/usr/bin/env python3
"""plate_gold.py — the READER for the Plate Tool's record (SIR-REVIEW-2026-09-01 Finding 5, T0).

The record is `plates/gold-layout.json`, written by `plate_tool.py` on every change. This module is
the only sanctioned way to consume it. It refuses a record whose source read has changed underneath
it, refuses accepted leaves that still carry `??`, and refuses classes outside the register.

    from plate_gold import load, is_gold, accepted
    g = load()                      # raises GoldError on any violation
    is_gold("OT1-1609-B", 412)      # True only for a leaf Sir ACCEPTED
    accepted()                      # {id: review} for every accepted leaf

CLI:  python3 plate_gold.py [--record plates/gold-layout.json] [--quiet]
"""
import argparse, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).parent
RECORD = HERE / "plates" / "gold-layout.json"

# The class register (cold-read rounds 1-3 + the B rebuild, 2026-09-05). Codes only; the meanings are
# in witness/cold-read/register-build/build_register_B.py and the live Class Register artifact.
TEXT = ["MT","MN","RH","PN","VN","CH","AR","DC","SG","CW",
        "AN","LM","IG","GK","BT","HD","CR","IX","TB","FN","AT","LR"]
NONTEXT = ["OR","RL","MS","XP","AP","ST","CT"]
STATES = ["BL","BP","EC"]          # blank leaf · blank lower page · empty table cell
ABSTAIN = "??"
CLASSES = TEXT + NONTEXT + STATES
VERDICTS = ("accept", "corrected", "defect")


class GoldError(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _box_ok(b):
    return (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)
            and 0 <= b[0] < b[2] <= 1 and 0 <= b[1] < b[3] <= 1)


def validate(rec, check_source=True):
    """Raise GoldError on the first violation. Returns the record unchanged."""
    if rec.get("format") != "plate-gold/1":
        raise GoldError(f"unknown record format {rec.get('format')!r}")
    src = rec.get("source", {})
    if check_source:
        p = Path(src.get("path", ""))
        if not p.is_absolute(): p = HERE / p
        if not p.exists():
            raise GoldError(f"source read missing: {p}")
        if sha256(p) != src.get("sha256"):
            raise GoldError(f"source read has CHANGED since the record was written: {p}. "
                            "Corrections were made against a different claim; re-open in plate_tool.")
    for lid, L in rec.get("leaves", {}).items():
        rv = L.get("review") or {}
        v = rv.get("verdict")
        if v is not None and v not in VERDICTS:
            raise GoldError(f"{lid}: verdict {v!r} not in {VERDICTS}")
        for i, r in enumerate(rv.get("regions", [])):
            c = r.get("class")
            if c != ABSTAIN and c not in CLASSES:
                raise GoldError(f"{lid} region {i}: class {c!r} not in the register")
            if not _box_ok(r.get("box")):
                raise GoldError(f"{lid} region {i}: bad box {r.get('box')!r}")
            if r.get("origin") not in ("agent", "human"):
                raise GoldError(f"{lid} region {i}: origin must be agent|human")
        if v == "accept":
            bad = [i for i, r in enumerate(rv.get("regions", [])) if r.get("class") == ABSTAIN]
            if bad:
                raise GoldError(f"{lid}: ACCEPTED but regions {bad} are still '??' — "
                                "an accepted leaf has no open abstentions")
            if not rv.get("regions"):
                raise GoldError(f"{lid}: ACCEPTED with zero regions — a blank leaf is BL, not empty")
    return rec


_cache = {}
def load(record=RECORD, check_source=True):
    record = Path(record)
    key = (str(record), record.stat().st_mtime if record.exists() else None)
    if key in _cache: return _cache[key]
    if not record.exists():
        raise GoldError(f"no record at {record}; nothing has been reviewed")
    rec = validate(json.load(open(record)), check_source)
    _cache.clear(); _cache[key] = rec
    return rec


def accepted(record=RECORD):
    return {lid: L["review"] for lid, L in load(record)["leaves"].items()
            if (L.get("review") or {}).get("verdict") == "accept"}


def is_gold(witness, leaf, record=RECORD):
    lid = f"{witness}_{int(leaf):04d}"
    return lid in accepted(record)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--record", default=str(RECORD))
    ap.add_argument("--no-source-check", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    try:
        rec = load(a.record, check_source=not a.no_source_check)
    except GoldError as e:
        print(f"GOLD REFUSED: {e}", file=sys.stderr); sys.exit(2)
    leaves = rec["leaves"]
    by = {}
    for L in leaves.values():
        by[(L.get("review") or {}).get("verdict")] = by.get((L.get("review") or {}).get("verdict"), 0) + 1
    if not a.quiet:
        print(f"record OK · {len(leaves)} leaves touched · " +
              " · ".join(f"{k or 'unreviewed'} {v}" for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))))
        for lid in sorted(accepted(a.record)):
            print("  gold:", lid)
    sys.exit(0)


if __name__ == "__main__":
    main()
