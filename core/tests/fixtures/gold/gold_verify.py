#!/usr/bin/env python
"""Gold-annotation verifier/resolver for the mask-detection methodology overhaul.

Loads every gold/work-<idx>.json (co-located with this file), resolves its text
anchors against the live ``reference_text()`` of the ingested work, and checks
each annotation for internal consistency:

  * type is a registered SECTION_TYPE
  * mask matches the committed DEFAULT_MASK_BY_TYPE (flags intentional overrides)
  * every start_anchor / end_anchor / exemplar anchor resolves uniquely
  * resolved spans are well-formed (0 <= start < end <= len)

This is the ground-truth side of the future structure-presence gate (A3): it
turns anchored gold into concrete [start,end] spans + expected counts that
detector output can be scored against, without ever storing brittle offsets.

The gold JSONs are durable, version-controlled fixtures and are self-contained
(each carries its own ``source_file`` basename). Live anchor RESOLUTION, however,
requires the eval harness (``harness/harness.py``, co-located and TRACKED since
R11.1) plus its ingested-workspace CACHE, which is machine-local (~2 GB, under
``.scratch/mask-eval`` or ``$MASK_EVAL_DATA``). The code travels with the repo;
the cache does not, so run this from a machine where the cache exists.

Usage:
  gold_verify.py            # verify all gold/work-*.json, print a report
  gold_verify.py <idx>      # verify one work
  gold_verify.py --resolve  # also dump every resolved span (for inspection)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent  # core/tests/fixtures/gold
REPO = HERE.parents[3]  # repo root
sys.path.insert(0, str(REPO / "core"))  # palimpsest package
sys.path.insert(0, str(HERE / "harness"))  # eval harness (R11.1: tracked, beside this file)

from harness import project_for, work_order  # noqa: E402

from palimpsest.layout import DEFAULT_MASK_BY_TYPE, SECTION_TYPES  # noqa: E402

GOLD = HERE


def _resolve(text: str, anchor: str, mode: str = "first") -> tuple[int, int]:
    """Resolve an anchor to (offset, count). count != 1 is a problem."""
    if anchor == "<<EOF>>":
        return len(text), 1
    count = text.count(anchor)
    off = text.rfind(anchor) if mode == "last" else text.find(anchor)
    return off, count


def verify_work(idx: int, dump: bool = False) -> list[str]:
    """Return a list of problem strings ([] == clean)."""
    problems: list[str] = []
    path = GOLD / f"work-{idx}.json"
    doc = json.loads(path.read_text())
    proj = project_for(idx)
    if proj is None:
        return [f"idx {idx}: work not ingested"]
    text = proj.reference_text()
    n = len(text)

    # source_file sanity: gold should track the same file the order maps to
    expected_src = Path(work_order()[idx].name).name
    if doc.get("source_file") != expected_src:
        problems.append(
            f"idx {idx}: source_file mismatch "
            f"gold={doc.get('source_file')!r} order={expected_src!r}"
        )

    for a in doc.get("annotations", []):
        t = a["type"]
        tag = f"idx {idx} {t}"
        if t not in SECTION_TYPES:
            problems.append(f"{tag}: unregistered type")
            continue
        # mask consistency vs committed taxonomy
        default_mask = DEFAULT_MASK_BY_TYPE[t]
        if a.get("mask") != default_mask:
            problems.append(
                f"{tag}: mask={a.get('mask')} differs from taxonomy "
                f"default {default_mask} (override?)"
            )

        mode = a.get("resolve", "first")
        if a.get("structure") == "repeating":
            ec = a.get("expected_count")
            if not isinstance(ec, int) and ec is not None:
                problems.append(f"{tag}: expected_count not int/None")
            for ex in a.get("exemplars", []):
                off, c = _resolve(text, ex["start_anchor"], mode)
                if c != 1:
                    problems.append(
                        f"{tag}: exemplar anchor resolves {c}x "
                        f"({ex.get('note','')[:40]}) :: {ex['start_anchor'][:40]!r}"
                    )
                elif dump:
                    print(f"    {tag} exemplar @ {off}: {ex.get('note','')[:50]}")
        else:
            so, sc = _resolve(text, a["start_anchor"], mode)
            eo, ec = _resolve(text, a["end_anchor"], mode) if a.get("end_anchor") else (n, 1)
            if sc != 1:
                problems.append(f"{tag}: start_anchor resolves {sc}x :: {a['start_anchor'][:40]!r}")
            if a.get("end_anchor") and a["end_anchor"] != "<<EOF>>" and ec != 1:
                problems.append(f"{tag}: end_anchor resolves {ec}x")
            if sc == 1 and not (0 <= so < eo <= n):
                problems.append(f"{tag}: malformed span [{so},{eo}] (n={n})")
            elif dump and sc == 1:
                print(f"    {tag} span [{so},{eo}] ({eo-so}c) mask={a.get('mask')}")
    return problems


def main() -> None:
    dump = "--resolve" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        idxs = [int(args[0])]
    else:
        idxs = sorted(int(p.stem.split("-")[1]) for p in GOLD.glob("work-*.json"))

    total_problems = 0
    for idx in idxs:
        doc = json.loads((GOLD / f"work-{idx}.json").read_text())
        ntypes = {a["type"] for a in doc.get("annotations", [])}
        print(f"[{idx}] {doc.get('work','?')[:46]} — types: {sorted(ntypes)}")
        probs = verify_work(idx, dump=dump)
        for p in probs:
            print(f"    PROBLEM: {p}")
        total_problems += len(probs)
    summary = "OK — all gold consistent" if total_problems == 0 else f"{total_problems} PROBLEM(S)"
    print(f"\n{summary} across {len(idxs)} work(s)")


if __name__ == "__main__":
    main()
