"""R14.6a -- can distant supervision actually label each region class? Audit the SOURCES first.

Masterplan §3.2 item 2 names a text source per region class, and R14.6 is built on the claim that
those sources make the agent's training labels affordable without a hand-labelling campaign. **That
claim had never been checked against the disk.** This checks it, per class, and reports three states:

  ADMISSIBLE  -- the source is present AND independent of our own geometry.
  CIRCULAR    -- the source exists but was PRODUCED BY the incumbent region typing. Training on it
                 teaches the model to reproduce `layout.type_lines`' decisions, errors included. The
                 gold's own `labelling_basis` forbids exactly this shape: labels must come from what
                 the text SAYS, never from where the incumbent put it.
  ABSENT      -- no source on this disk.

⚠️ EXIT 1 WHILE ANY CLASS LACKS AN ADMISSIBLE SOURCE. That is the healthy state while R14.6 is open;
an audit that exits 0 before its remedy is done would mean it stopped looking.

⚠️ WHY THIS IS NOT BOOKKEEPING. R14.1 is a class-inventory fine-tune, and a fine-tune can only teach
the classes its labels cover. A class with no admissible source is a class the fine-tuned model will
not be able to emit -- which is precisely the defect R14.0 measured in Surya off the shelf. Discovering
that after training is discovering it expensively.

    ../ocr-venv/bin/python witness/audit_label_sources.py
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

ODR = _HERE.parents[1]                 # .../projects/originaldr
READS = ODR / "reconstruction/reads"
SPIKE = _HERE.parent
CROSSMAP = SPIKE / "apparatus-cross-map.json"

ADMISSIBLE, CIRCULAR, ABSENT = "ADMISSIBLE", "🟡 CIRCULAR", "🔴 ABSENT"


def _reads_count():
    """-> (n_witness_files, total verse reads). The MainText label source."""
    n_files, n_reads = 0, 0
    for p in sorted(READS.glob("*.json")):
        if p.name.count(".") > 1:        # .pre-* backups are not sources
            continue
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("reads"), list):
            n_files += 1
            n_reads += len(d["reads"])
    return n_files, n_reads


def _apparatus_kinds():
    """-> Counter of `kind` over every transcribed apparatus block on disk."""
    from collections import Counter
    c = Counter()
    for p in sorted(READS.glob("*.json")):
        if p.name.count(".") > 1:
            continue
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        for b in (d.get("apparatus_blocks") or []) if isinstance(d, dict) else []:
            c[b.get("kind")] += 1
    return c


def main() -> int:
    print("R14.6a -- LABEL SOURCE AUDIT, per region class (Masterplan §3.2 item 2)\n")

    n_files, n_reads = _reads_count()
    kinds = _apparatus_kinds()
    n_arg = kinds.get("argument", 0)
    n_note = sum(v for k, v in kinds.items() if k in ("annotation", "note", "marginalia", "margin"))

    crossmap_ok = CROSSMAP.exists()
    scan_words = 0
    if crossmap_ok:
        try:
            scan_words = json.loads(CROSSMAP.read_text())["totals"]["scan_marginal_words"]
        except Exception:
            pass

    rows = [
        # (class, named source, state, evidence)
        ("MainText", "archaic-reference verse text, by alignment", ADMISSIBLE if n_reads else ABSENT,
         f"{n_reads} verse reads across {n_files} witness read-files in reconstruction/reads/"),
        ("Argument", "transcribed apparatus blocks", ADMISSIBLE if n_arg else ABSENT,
         f"{n_arg} blocks, every one kind='argument'"),
        ("Marginalia", "§3.2 item 2 names 'the 1,334 transcribed apparatus blocks'", ABSENT,
         "🔴 THOSE 1,334 BLOCKS ARE ARGUMENTS, NOT MARGINAL NOTES -- "
         f"{n_arg} argument / {n_note} note. No transcribed side-note corpus is on this disk"),
        ("Marginalia (alt)", "apparatus-cross-map `scan_marginal`", CIRCULAR if scan_words else ABSENT,
         f"{scan_words} words, but produced by `margin_by_page` -- the INCUMBENT region typer's own "
         "output (apparatus_crossmap.scan_marginalia). Training on it reproduces its errors"),
        ("RunningHead", "self-verifying positional-and-text test", ADMISSIBLE,
         "collation_read reads the head; R2.1g scores it directly, RunningHead recall 20/20"),
        ("Catchword / Signature", "self-verifying positional-and-text test", ADMISSIBLE,
         "collation_read carries them as separate fields with stated abstain reasons (R2.1c); "
         "the catchword half reads 0.87-1.00"),
        ("VerseNumber", "numeral matches the adjacent verse", ADMISSIBLE if n_reads else ABSENT,
         "derivable from the same verse reads as MainText"),
    ]

    w = max(len(r[0]) for r in rows)
    for cls, src, state, ev in rows:
        print(f"  {cls:<{w}}  {state:<12}  {src}")
        print(f"  {'':<{w}}  {'':<12}  └─ {ev}")

    blocked = [r[0] for r in rows if r[2] is ABSENT and not r[0].endswith("(alt)")]
    circ = [r[0] for r in rows if r[2] is CIRCULAR]

    print("\n" + "=" * 100)
    print("🔴 THE ONE CLASS THAT CANNOT BE LABELLED IS THE ONE THE WHOLE PROGRAMME IS BLOCKED ON.")
    print("   Marginalia is the class Surya scores 0/19 on (R14.0), the class the MN gap is about,")
    print("   and the class R2.2's four refuted span rules were chasing. Distant supervision cannot")
    print("   label it, because no transcribed side-note text exists to align against.")
    print("\n   ⚠️ AND THE PLAN SAYS OTHERWISE. Masterplan §3.2 item 2 and Roadmap R14.6 both read")
    print("   'Marginalia from the 1,334 transcribed apparatus blocks'. Measured here: all 1,334 are")
    print("   ARGUMENTS -- the italic prose summary before a chapter, which is a DIFFERENT region")
    print("   class (§3.2a archetype C REQUIRES Argument; MarginNote is archetype B's class).")
    print("\n   ⚠️ THE NAMED REMEDY ALREADY EXISTS IN THE PROJECT'S OWN NOTE, UNEXECUTED.")
    print("   apparatus-cross-map records: 'odr_com apparatus = raw scrape follow-up (not in")
    print("   odr_com.json)'. The marginal-note transcription was identified as a follow-up scrape")
    print("   and never run. That is R14.6b.")
    print("=" * 100)

    # ⚠️ THE REPRESENTATIVE FRACTION LEADS, and it is the unflattering one. Both of the two sources
    # this project holds for Marginalia fail -- one is absent, one is circular -- and that 0 is the
    # audit's finding. Leading with `5/7` would put the best number in the run on the status line of
    # a run whose result is that the class the programme is blocked on cannot be labelled at all.
    n_marg = len([r for r in rows if r[0].startswith("Marginalia")])
    n_marg_ok = len([r for r in rows if r[0].startswith("Marginalia") and r[2] is ADMISSIBLE])
    n_ok = len([r for r in rows if r[2] is ADMISSIBLE])
    print(f"\nMARGINALIA label sources ADMISSIBLE : {n_marg_ok}/{n_marg}   <- the finding")
    print(f"region classes with a source        : {n_ok}/{len(rows)}")
    print(f"CIRCULAR sources                    : {len(circ)}  {circ}")
    print(f"BLOCKED classes                     : {len(blocked)}  {blocked}")

    if not blocked and not circ:
        print("\n✅ every region class has an admissible, independent label source.")
        return 0
    print("\n🔴 R14.6a: distant supervision covers MainText, Argument, RunningHead, Catchword,")
    print("   Signature and VerseNumber -- and CANNOT cover Marginalia. R14.1's fine-tune may")
    print("   therefore teach every class EXCEPT the one it was redirected to fix.")
    print("   ⚠️ Do NOT substitute `scan_marginal`: a circular label is worse than a missing one,")
    print("      because it trains a model to agree with the instrument it was meant to replace,")
    print("      and the agreement then reads as validation.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
