#!/usr/bin/env python
"""R11.3a -- acquire and VERIFY the Sabates_A apparatus witness at its pinned commit.

WHY THIS EXISTS. `SRC` -- the janvier-s/original-douay-rheims clone -- is the sole
source for every book argument, chapter argument, footnote, cross-reference, marginal
annotation, the 26 front/back reference documents, and the three-book apocryphal
appendix. Until now it lived only as an unpinned clone in one machine's gitignored
`.scratch/`, which is the same exposure R11.1 removed for the eval harness: **the
apparatus was reproducible by exactly one person, on exactly one disk.** §0.2 rule 6
says every reading is addressable and checkable; a source nobody else can obtain at
the version that was read is neither.

WHAT IS PINNED. `sabates-a-pin.json`, tracked beside this file, records the remote,
the commit, and a content hash of each tree actually read. **The commit alone is not
enough** -- it proves which revision was requested, not which bytes arrived. The tree
hashes are taken over sorted `(relpath, sha256(content))` pairs, so they are stable
against filesystem ordering and exact against content.

VERIFIED 2026-08-14: `git ls-remote` shows the pinned SHA at both `HEAD` and
`refs/heads/main`, 0 commits behind, and the local clone's working tree is clean.

USAGE
  acquire_sabates_a.py --verify           # check an existing clone against the pin
  acquire_sabates_a.py --clone [DEST]     # clone at the pinned commit, then verify
  acquire_sabates_a.py --repin            # rewrite the pin from the current clone

⚠️ `--repin` is deliberately a separate, explicit action. Re-pinning to whatever HEAD
happens to be today would make the apparatus unreproducible in exactly the way this
step exists to prevent -- the pin must move because someone decided to move it, and
the emitted text must be re-derived and re-checked when it does.

Exit 0 = the tree on disk is the tree that was pinned. Exit 1 = it is not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN_FILE = HERE / "sabates-a-pin.json"
# HERE.parents = [0]originaldr_reconstruction [1]mask_engine [2]gold [3]fixtures [4]tests [5]core [6]<repo>
REPO = HERE.parents[6]
DEFAULT_DEST = REPO / ".scratch" / "original-douay-rheims"


def load_pin() -> dict:
    if not PIN_FILE.exists():
        raise FileNotFoundError(f"pin file missing: {PIN_FILE}")
    return json.loads(PIN_FILE.read_text())


def tree_hash(root: Path, base: Path) -> dict:
    """sha256 over sorted (relpath, sha256(content)) -- order-stable, content-exact."""
    h = hashlib.sha256()
    n = nb = 0
    for p in sorted(q for q in root.rglob("*") if q.is_file()):
        data = p.read_bytes()
        h.update(p.relative_to(base).as_posix().encode())
        h.update(hashlib.sha256(data).digest())
        n += 1
        nb += len(data)
    return {"files": n, "bytes": nb, "tree_sha256": h.hexdigest()}


def verify(dest: Path, pin: dict) -> int:
    problems: list[str] = []
    if not dest.is_dir():
        print(f"FAIL -- no clone at {dest}\n  run: {Path(__file__).name} --clone")
        return 1

    got_sha = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    if got_sha != pin["commit"]:
        problems.append(f"  commit {got_sha or '<none>'} != pinned {pin['commit']}")
    else:
        print(f"commit  OK  {got_sha}")

    dirty = subprocess.run(["git", "-C", str(dest), "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        problems.append(f"  working tree is DIRTY ({len(dirty.splitlines())} paths) -- "
                        f"the commit no longer describes what is on disk")
    else:
        print("tree    OK  working tree clean")

    for sub, want in pin["trees"].items():
        root = dest / sub
        if want is None:
            continue
        if not root.is_dir():
            problems.append(f"  {sub}: MISSING")
            continue
        got = tree_hash(root, dest)
        if got["tree_sha256"] != want["tree_sha256"]:
            problems.append(
                f"  {sub}: content differs\n"
                f"      pinned {want['tree_sha256'][:16]}… ({want['files']} files, {want['bytes']:,} B)\n"
                f"      found  {got['tree_sha256'][:16]}… ({got['files']} files, {got['bytes']:,} B)")
        else:
            print(f"{sub:<12} OK  {got['files']} files, {got['bytes']:,} B")

    if problems:
        print("\nFAIL -- the tree on disk is not the tree that was pinned:")
        print("\n".join(problems))
        print("\nRe-acquire with --clone, or --repin ONLY if the pin is meant to move "
              "(and then re-derive and re-check the emitted text).")
        return 1
    print("\nOK -- clone matches the pin exactly")
    return 0


def clone(dest: Path, pin: dict) -> int:
    if dest.exists():
        print(f"refusing to clone over an existing path: {dest}")
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"cloning {pin['remote']} -> {dest}")
    subprocess.run(["git", "clone", "--quiet", pin["remote"], str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", pin["commit"]], check=True)
    print(f"checked out {pin['commit']}\n")
    return verify(dest, pin)


def repin(dest: Path) -> int:
    sha = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    pin = load_pin()
    old = pin["commit"]
    pin["commit"] = sha
    for k in ("commit_date", "commit_subject"):
        fmt = "%cI" if k == "commit_date" else "%s"
        pin[k] = subprocess.run(["git", "-C", str(dest), "log", "-1", f"--format={fmt}"],
                                capture_output=True, text=True).stdout.strip()
    for sub in pin["trees"]:
        root = dest / sub
        pin["trees"][sub] = tree_hash(root, dest) if root.is_dir() else None
    PIN_FILE.write_text(json.dumps(pin, indent=2) + "\n")
    print(f"REPINNED {old} -> {sha}")
    print("⚠️  The apparatus source has moved. Re-derive the emitted text and re-run "
          "the gold checks: a pin change is an EDITION change until proven otherwise.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--verify", action="store_true", help="check an existing clone (default)")
    ap.add_argument("--clone", nargs="?", const=str(DEFAULT_DEST), metavar="DEST")
    ap.add_argument("--repin", action="store_true")
    ap.add_argument("--dest", default=str(DEFAULT_DEST))
    a = ap.parse_args()
    pin = load_pin()
    if a.clone:
        return clone(Path(a.clone), pin)
    if a.repin:
        return repin(Path(a.dest))
    return verify(Path(a.dest), pin)


if __name__ == "__main__":
    sys.exit(main())
