"""The roadmap's "Verification standard" block must describe reality.

Finding, 2026-08-07: that block claimed `make_witness_tree.py -> 10/10 verified`
when the tree verifies **12/12**, and listed none of the four guards nor the
ground-truth audit.  The block sits under the sentence *"a step is DONE when its
acceptance test runs and passes on demand"* -- so a stale command list there is
not cosmetic, it is the standard misdescribing itself.

`test_counts_vs_doc.py` already binds the masterplan's 1.1 table to the registry.
Nothing bound the ROADMAP to anything, which is how R0.1's "all 10 files" and
R0.2's "10/10" survived the corpus growing to eleven files and twelve records.
This is the same guard, one document over.

What it checks:
  1. every command named in the block exists on disk;
  2. every `-> N/M verified` claim in the block matches what that command prints
     when actually run;
  3. the block names every guard that exists -- so adding a guard and forgetting
     to document it FAILS, which is the direction the last drift went;
  4. commands the block presents as passing exit 0, and commands it presents as
     expected-to-fail exit non-zero.  An audit that starts passing before its
     remedy lands is a defect too: it means the audit stopped looking.

Deliberately NOT checked: prose.  This test reads the fenced command blocks and
the arrows in them, nothing else.  A test that tried to verify the paragraphs
would fail on rewording and be switched off, which is worse than no test.
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent
ROADMAP = SPIKE / "OCR-ROADMAP.md"
PY = SPIKE.parent / "ocr-venv" / "bin" / "python"

SECTION = "## Verification standard for this roadmap"

# Guards live here and are expected to be named in the block.  Audits are listed
# separately because their healthy state is FAILURE while their step is open.
GUARD_GLOB = "test_*.py"
AUDIT_SCRIPTS = {"audit_gt_rasters.py"}
# This file is the guard doing the checking; it must be named in the block like
# any other, but it must not recurse into running itself.
SELF = Path(__file__).name

FAILURES = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILURES.append(f"{label}: {detail}")


def block_text():
    """The verification-standard section of the roadmap, or None if it is gone."""
    text = ROADMAP.read_text()
    if SECTION not in text:
        return None
    return text.split(SECTION, 1)[1]


def commands(section):
    """(script, claim) for every `witness/<script>.py` line inside a fenced block.

    `claim` is the `-> ...` trailing assertion if the line carries one.
    """
    out = []
    for fence in re.findall(r"```(.*?)```", section, re.S):
        for line in fence.splitlines():
            m = re.search(r"witness/(\S+\.py)", line)
            if not m:
                continue
            claim = None
            if "->" in line:
                claim = line.split("->", 1)[1].strip()
            out.append((m.group(1), claim))
    return out


def run(script):
    p = subprocess.run([str(PY), f"witness/{script}"], cwd=SPIKE,
                       capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    section = block_text()
    if section is None:
        check(f"roadmap still has a {SECTION!r} section", False,
              "the section this test binds to has been removed or renamed; either "
              "restore it or retire this test deliberately, do not let it vanish")
        return 1

    named = commands(section)
    print(f"the block names {len(named)} command(s); each must exist:")
    for script, _ in named:
        check(f"witness/{script:32s} exists", (HERE / script).is_file(),
              "named in the verification standard but not on disk")

    named_set = {s for s, _ in named}

    print("\nand every guard and audit on disk must be named in the block:")
    on_disk = {p.name for p in HERE.glob(GUARD_GLOB)} | {
        a for a in AUDIT_SCRIPTS if (HERE / a).is_file()}
    for script in sorted(on_disk):
        check(f"witness/{script:32s} is documented", script in named_set,
              "exists but the verification standard does not list it -- a guard "
              "nobody is told to run is a guard nobody runs")

    print("\nevery claim of the form `-> N/M verified` must match what runs:")
    ran = {}
    for script, claim in named:
        if not (HERE / script).is_file():
            continue
        if script == SELF:
            print(f"  ok    witness/{script:32s} (self -- not re-run)")
            continue
        # Only commands this test can hold to account are run: the guards, the
        # audits, and anything carrying an explicit `-> N/M` claim.  The
        # inventory and reconciliation scripts are named in the block because a
        # reader needs them, but they walk all eleven witnesses and take many
        # minutes, and a guard slow enough to be skipped is a guard that does not
        # run.  They are checked for EXISTENCE above, not executed here.
        if not (script.startswith("test_") or script in AUDIT_SCRIPTS or claim):
            print(f"  --    witness/{script:32s} (not executed: no claim to check)")
            continue
        if script not in ran:
            ran[script] = run(script)
        code, out = ran[script]
        if claim:
            m = re.search(r"(\d+)\s*/\s*(\d+)", claim)
            if m:
                pat = rf"{m.group(1)}\s*/\s*{m.group(2)}"
                check(f"witness/{script:32s} prints {m.group(1)}/{m.group(2)}",
                      re.search(pat, out) is not None,
                      f"claim {claim!r} not found in output; the block is stale")

    print("\nguards must exit 0; audits are expected to FAIL while their step is open:")
    for script in sorted(ran):
        code, _ = ran[script]
        if script in AUDIT_SCRIPTS:
            check(f"witness/{script:32s} exits non-zero (step still open)", code != 0,
                  "this audit now passes -- either its remedy is complete and the "
                  "block must say so, or the audit has stopped looking")
        else:
            check(f"witness/{script:32s} exits 0", code == 0, f"exit {code}")

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}\n---")
        for f in FAILURES:
            print(f"  {f}")
        return 1
    print(f"all checks passed — the roadmap's verification standard names "
          f"{len(named_set)} command(s) and describes what they actually do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
