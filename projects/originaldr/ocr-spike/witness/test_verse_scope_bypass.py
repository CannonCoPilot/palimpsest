#!/usr/bin/env python3
"""test_verse_scope_bypass.py -- R9.2c: Gate 0f is only as strong as its narrowest route.

`corpus_localize.load()` refuses a witness the corpus does not admit for verse text (R9.2).  That
refusal guards every consumer that calls it -- and **nothing else**.  A module that opens
`.corpus-localize-<dir>.json` and reads `["verses"]` itself has the same data with none of the gate.

The R9.2 plan asserted that `load()` was "the function every verse consumer already goes through."
It was not, and the way that claim was reached is worth recording: the check was a grep for modules
*mentioning* `corpus_localize`, which is a test of imports, not of call sites.  Nine modules read the
path directly.  **Two routes to the data, one guarded, is R7.5 exactly** -- the defect where
`OCR_DIR_TO_JP2` and `pixel_source()` both reached the pixels and only one was checked.

This guard exits 1 while any direct reader remains, and names them.  It does not attempt to rewrite
them: converting a consumer is a judgement about what that consumer is for -- `integrity_sweep` reads
the artefact to COUNT it, which is bookkeeping and legitimately outside the gate, while `gen1_rescore`
reads it to SCORE with, which is not.  The list is the worklist.

R9.2c DISCHARGED (2026-08-10).  Seven evidential readers now go through `corpus_localize.load_verses`
and the `audit_diagnose` sweep through `iter_localizations`; `source_inventory_audit` is exempt because
it reads the artefact FILENAMES and never opens one.  `load()` itself was NOT the conversion target:
it returns `{(book, ch, verse): text}` and discards `page`/`fit`, which is precisely what every direct
reader wanted, so converting to it would have made the gate cost evidence -- and a gate that costs
evidence is routed around, which is this defect restated one turn later.  The gated route has to be
the cheapest one, not the most expensive.

Exit 0 when every verse-grain reader outside `corpus_localize` goes through one of its gated readers,
and every STRUCTURAL_EXEMPT module still satisfies the claim its exemption rests on.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent

# The artefact path, built by f-string or by name. Both forms are how the direct readers spell it.
DIRECT = re.compile(r'\.corpus-localize-')


def direct_reads(src: str) -> int:
    """How many times this module NAMES the artefact path in executable code.

    Counted over string constants via `ast`, with docstrings excluded, rather than over raw text.
    A raw grep counts PROSE: this guard's first version fired on the very docstring that recorded a
    reader's conversion away from the path, because the docstring quoted the glob it had removed. A
    check that a comment can trip is one that gets satisfied by rewording, and it then measures
    vocabulary instead of call sites -- the `audit_s06_keys` lesson (a check that reads NAMES cannot
    see CONTENTS) with the two sides swapped.

    Fails CLOSED: a module that will not parse is counted by the raw regex, prose and all, because an
    unreadable file must not come back as clean.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return len(DIRECT.findall(src))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return sum(1 for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and id(n) not in docstrings and DIRECT.search(n.value))

# `corpus_localize` itself must read and write the path -- it is the module that owns it.
OWNER = {"corpus_localize.py"}

# Readers that are legitimately OUTSIDE the gate, each with the reason. Bookkeeping is not evidence:
# scope governs what a verse may COUNT AS, not whether a file may be counted (R9.2b). Anything added
# here must state why the read is not a verse-grain evidential read.
STRUCTURAL_EXEMPT = {
    "integrity_sweep.py": "C10 reconciles each verse's key and `page` against the page address; "
                          "never reads the verse text, so it scores nothing (R9.2b)",
    "source_inventory_audit.py": "globs the artefact FILENAMES to inventory which volumes have been "
                                 "localized; never opens one, so no verse is read at all (R9.2c)",
}

# THE EXEMPTION IS CHECKED, NOT TRUSTED (R9.2c). Every exemption above rests on the same claim -- "this
# read is bookkeeping, not evidence" -- and this project's standing lesson is that a filter cannot enforce
# a distinction it cannot express. Here the distinction IS expressible: scoring a verse requires its
# `text`, reconciling or counting one does not. `integrity_sweep` reads `key` and `rec["page"]`;
# `source_inventory_audit` reads filenames. Neither touches a `text` field, and if either ever starts to,
# its exemption is void and this guard says so instead of waiting for a reader to re-derive the argument.
#
# Deliberately conservative: it fires on ANY verse-`text` read in an exempt module, including one from a
# different source. An exemption that has to be re-argued because the module grew a second responsibility
# is the correct cost; the failure this prevents is a standing permission outliving its reason, which is
# exactly the shape of the `drop_tomes` rule that was cited for months and read by nothing.
TEXT_FIELD = re.compile(r'\[["\']text["\']\]|\.get\(["\']text["\']')


def main() -> int:
    offenders: dict[str, int] = {}
    exempt_seen: set[str] = set()
    void: dict[str, int] = {}       # exempt modules that read a verse `text` -- exemption forfeited
    for p in sorted(SPIKE.rglob("*.py")):
        rel = str(p.relative_to(SPIKE))
        if "__pycache__" in rel or rel.startswith(".superseded") or rel.startswith("witness/"):
            continue
        if p.name in OWNER:
            continue
        try:
            t = p.read_text()
        except OSError:
            continue
        n = direct_reads(t)
        if not n:
            continue
        if p.name in STRUCTURAL_EXEMPT:
            exempt_seen.add(p.name)
            nt = len(TEXT_FIELD.findall(t))
            if nt:
                void[rel] = nt
            continue
        offenders[rel] = n

    print("Gate 0f — routes to the localization artefact:")
    print(f"  owner (may read the path directly): {sorted(OWNER)}")
    for name in sorted(exempt_seen):
        print(f"  exempt  {name:26} {STRUCTURAL_EXEMPT[name]}")
    stale = sorted(set(STRUCTURAL_EXEMPT) - exempt_seen)
    if stale:
        # An exemption for a file that no longer reads the path is a standing permission with no
        # subject -- exactly the shape of the drop rule that was cited for months and read by nothing.
        print(f"  ⚠ stale exemption(s), no longer reading the artefact: {stale} — remove them")

    if void:
        print("\nEXEMPTION FORFEITED — an exempt module reads a verse `text` field, which is the read the")
        print("exemption claims it does not make. Either route it through the gate or restate the reason:")
        for f, n in sorted(void.items()):
            print(f"  {n:3}  {f}")

    if not offenders and not void:
        print("\nevery verse-grain reader goes through corpus_localize's gated readers "
              "(`load` / `load_verses` / `load_raw` / `iter_localizations`); the gate has one route.")
        return 0

    if offenders:
        print(f"\nBYPASSING the gate — {len(offenders)} module(s), {sum(offenders.values())} direct read(s):")
        for f, n in sorted(offenders.items(), key=lambda kv: -kv[1]):
            print(f"  {n:3}  {f}")
        print("\nOPEN (R9.2c) — these read the localization artefact without passing Gate 0f. Two routes to\n"
              "the data with one guarded is R7.5 restated: the guard is not wrong, it is merely not on the\n"
              "path the caller took. Route each through `corpus_localize.load_verses` (or `load_raw` for\n"
              "the whole artefact, `iter_localizations` for a sweep), or add it to STRUCTURAL_EXEMPT with\n"
              "the reason its read is not evidential. Exit 1 until then.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
