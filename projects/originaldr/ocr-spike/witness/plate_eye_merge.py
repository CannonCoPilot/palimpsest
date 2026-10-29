#!/usr/bin/env python
"""Merge Jarvis's eye-review findings into the plate book's flag channel.

The review tool reads ONE highlight channel, `plates/review-flags.json`. The structural
screen writes entries there with sev `note`/`warn`; this writes the findings that only
came from LOOKING, with sev `eye`. Keeping them in one channel is deliberate — Sir works
through a single list per leaf rather than reconciling two files.

Idempotent and safe with no arguments: it drops every existing `eye` entry and rewrites
from `plates/eye-findings.json`, so re-running never duplicates and never touches the
structural entries. If the findings file is absent it is a no-op.

An eye finding is MY claim about LECTOR's claim. It is not adjudicated. Nothing here may
be read back as ground truth until a human records a verdict in the tool.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLATES = os.path.join(HERE, "plates")
FLAGS = os.path.join(PLATES, "review-flags.json")
FINDINGS = os.path.join(PLATES, "eye-findings.json")


def main():
    if not os.path.exists(FINDINGS):
        print(f"no findings file at {FINDINGS} — nothing to merge")
        return 0
    if not os.path.exists(FLAGS):
        print(f"FAIL no flag file at {FLAGS}", file=sys.stderr)
        return 1

    findings = json.load(open(FINDINGS))["leaves"]
    flags = json.load(open(FLAGS))

    # drop prior eye entries first, so a re-run replaces rather than accumulates
    for leaf, entries in flags.items():
        flags[leaf] = [e for e in entries if e.get("sev") != "eye"]

    added = 0
    for leaf, notes in findings.items():
        flags.setdefault(leaf, [])
        for n in notes:
            kind = "SEEN BY EYE"
            if n.startswith("GOOD") or n.startswith("BEST"):
                kind = "SEEN BY EYE — CORRECT"
            flags[leaf].append({"kind": kind, "sev": "eye", "what": n})
            added += 1

    # keep leaves with no entries present but empty, so the tool can tell
    # "screened, nothing found" from "never screened"
    json.dump(flags, open(FLAGS, "w"), indent=1, ensure_ascii=False)
    print(f"merged {added} eye findings across {len(findings)} leaves -> {FLAGS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
