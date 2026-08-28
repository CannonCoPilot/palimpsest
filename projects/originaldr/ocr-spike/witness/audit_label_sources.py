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
# 🔴 THREE FALSE ABSENCES, ONE DISEASE: A BOUNDED SEARCH REPORTED AS AN EXHAUSTIVE ONE.
# v1 of this audit searched `reconstruction/reads/` ONLY, found no side-note text, and concluded
# "no transcribed side-note corpus is on this disk". Separately I looked for the SRC clone under
# `ocr-spike/.scratch/` when it lives at `palimpsest/.scratch/`, and reported it missing. Then I ran
# `find ~/Claude -maxdepth 7` for the Madueke source, which sits at DEPTH 8, and wrote "searched ALL
# of ~/Claude". Every one of those returned "not found" in EXACTLY the shape an exhaustive search
# returns it: no error, no warning, nothing distinguishing "it is not there" from "I stopped looking
# before I reached it". ⚠️ AN ABSENCE IS A CLAIM and inherits the evidential standard of any other
# claim -- the Executive Summary already records this project excluding a witness on a mistaken
# one-line description and producing a false "nothing survives" verdict at the most consequential
# point in the New Testament. ⚠️ STATE THE BOUND OR DO NOT CLAIM THE SCOPE.
#
# The corpora below are the TRACKED homes under `imports/.../sources/transcriptions/`, not working
# copies: `.scratch/original-douay-rheims` was verified byte-identical to `janvier` (394 files, 0
# differences), so counting it as a second witness would have double-counted one corpus.
IMPORTS = (ODR.parents[1] / "imports/Scripture/Bibles/DouayRheims_DR/sources/transcriptions")
SRC = IMPORTS / "janvier/original-douay-rheims-repo"
ODRCOM = IMPORTS / "originaldouayrheims-com/apparatus"

ADMISSIBLE, CIRCULAR, ABSENT = "ADMISSIBLE", "🟡 CIRCULAR", "🔴 ABSENT"
# 🔴 R14.10c — A FOURTH STATE, ADDED BECAUSE A THREE-WAY VERDICT COULD NOT SAY WHAT IS TRUE OF
# ANNOTATION. The class HAS a corpus on disk — so `ABSENT` is false — and that corpus does not
# reach the volume the whole programme is scored on, so `ADMISSIBLE` is worse than false: it would
# read as a green while the class stays unlabellable exactly where it is needed. ⚠️ `PARTIAL`
# BLOCKS, on the same footing as `ABSENT`. A source that covers the wrong books is a source whose
# coverage must be stated, never one whose existence is enough.
PARTIAL = "🟠 PARTIAL"


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


def _side_notes():
    """-> (n_note_objects, n_mn_anchors, n_books) from the SRC clone. The Marginalia label source.

    `annotations/{book}/{chapter}.json` carries `notes` objects (marker + text) hung off an
    annotation that names the VERSE it is anchored to -- so the note arrives with its attachment
    already made, which is Gate 10e/S5's relation for free. `bible/tagged/` carries `<mn>` anchors
    and per-chapter `summary_notes`.
    """
    import re
    if not SRC.exists():
        return 0, 0, 0
    n_notes = n_mn = 0
    books = set()
    for f in SRC.glob("annotations/*/*.json"):
        books.add(f.parent.name)
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for a in d.get("annotations", []):
            n_notes += len(a.get("notes") or [])
            n_mn += len(re.findall(r"<mn>", a.get("text", "") or ""))
    for f in SRC.glob("bible/tagged/*.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for ch in d.get("chapters") or []:
            n_notes += len(ch.get("summary_notes") or [])
    return n_notes, n_mn, len(books)


def _odrcom_annotations():
    """-> (n_blocks, n_ot_chapters, n_nt_chapters, ot_books). The ANNOTATION label source.

    🔴 THIS FUNCTION EXISTS BECAUSE THE AUDIT WAS BLIND TO THE FIELD IT MOST NEEDED TO READ.
    R14.10c asked whether the Annotation class has a source, and this file answered from
    `apparatus_blocks[kind]` — where the count is **0**, because all 1,334 of those blocks are
    `kind='argument'`. Meanwhile the odr-com scrape beside it carries a top-level `annotations`
    field, chapter by chapter, **with the printed `ANNOTATIONS. Chap. I.` head in the text**, and
    nothing here looked at it. `_odrcom_notes` reads `marginal_notes` and `inline_notes` from the
    very same documents and steps straight past it.

    ⚠️ SO THE AUDIT WOULD HAVE REPORTED A SECOND FALSE ABSENCE, in the same shape as the one it
    already records at the foot of its own output: *a bounded search returns "not found" in the same
    shape as an exhaustive one.* The bound the first time was a DIRECTORY; this time it was a
    FIELD NAME. Stating the bound is what makes the difference visible.
    """
    if not ODRCOM.exists():
        return 0, 0, 0, 0
    n = ot = nt = ot_books = 0
    for f in sorted(ODRCOM.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        an = d.get("annotations") or {}
        if not an:
            continue
        is_ot = str(d.get("testament", "")).upper().startswith("O")
        n += len(an)
        if is_ot:
            ot += len(an)
            ot_books += 1
        else:
            nt += len(an)
    return n, ot, nt, ot_books


def _odrcom_notes():
    """-> (n_marginal_notes, n_inline_notes, n_books). A SECOND, partly independent transcription.

    ⚠️ NOT equivalent to the janvier corpus and must not be pooled with it: these are 165
    CHAPTER-anchored structural markers ("THE FIRST part of: the infancie...") against janvier's
    VERSE-anchored polemical side-notes ("Saints be present at their tombs and relics."). Reported
    separately so the difference stays visible; corroboration, not volume.
    """
    if not ODRCOM.exists():
        return 0, 0, 0
    n_mn = n_in = 0
    books = 0
    for f in sorted(ODRCOM.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        books += 1
        n_mn += len(d.get("marginal_notes") or [])
        n_in += len(d.get("inline_notes") or [])
    return n_mn, n_in, books


def main() -> int:
    print("R14.6a -- LABEL SOURCE AUDIT, per region class (Masterplan §3.2 item 2)\n")

    n_files, n_reads = _reads_count()
    kinds = _apparatus_kinds()
    n_arg = kinds.get("argument", 0)
    n_note = sum(v for k, v in kinds.items() if k in ("annotation", "note", "marginalia", "margin"))

    n_side, n_mn, n_sbooks = _side_notes()
    n_ocmn, n_ocin, n_ocbooks = _odrcom_notes()
    n_an, n_an_ot, n_an_nt, n_an_books = _odrcom_annotations()

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
        ("Marginalia", "janvier repo: annotation `notes` + `<mn>` anchors, aligned by TEXT",
         ADMISSIBLE if n_side else ABSENT,
         f"{n_side} side-note objects, {n_mn} <mn> anchors, {n_sbooks} books (OT 1609 + NT 1582, CC0 "
         f"-- THIS EDITION). ⚠️ §3.2 item 2's named source, 'the 1,334 transcribed apparatus blocks', "
         f"is NOT this: those {n_arg} blocks are all kind='argument' ({n_note} note), another class"),
        ("Marginalia (2nd)", "originaldouayrheims-com apparatus scrape -- ALREADY DONE, on disk",
         ADMISSIBLE if n_ocmn else ABSENT,
         f"{n_ocmn} marginal_notes + {n_ocin} inline_notes over {n_ocbooks} books. ⚠️ CORROBORATION, "
         "NOT VOLUME: chapter-anchored structural markers, not janvier's verse-anchored side-notes. "
         "Do NOT pool the two counts"),
        # 🔴 R14.10c. The class the agent cannot name, and the row this audit never carried.
        ("Annotation", "originaldouayrheims-com apparatus scrape, `annotations` field",
         PARTIAL if n_an else ABSENT,
         f"{n_an} chapter-anchored annotation blocks, each carrying its printed 'ANNOTATIONS. Chap. "
         f"N.' head — but {n_an_nt} of them are NEW TESTAMENT and the Old Testament holds only "
         f"{n_an_ot} chapters across {n_an_books} books (Genesis, Exodus). ⚠️ NUMBERS HAS NONE, and "
         f"Numbers is the volume every region figure in this project is measured on (OT1-1609-B "
         f"leaves 400-419). ⚠️ ALSO NOTE `apparatus_blocks` CANNOT SUPPLY THIS: its {n_arg} blocks "
         f"are ALL kind='argument' and it holds {n_note} annotation blocks — this audit read that "
         f"field and not the one above, which would have been a SECOND false absence"),
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

    # ⚠️ `PARTIAL` BLOCKS ALONGSIDE `ABSENT`. A source that exists but does not reach the volume the
    # class is needed in leaves the class unlabellable there, and a status line that counted it as
    # covered would be the laundering §0.5 exists to prevent.
    blocked = [r[0] for r in rows if r[2] in (ABSENT, PARTIAL) and not r[0].endswith("(alt)")]
    circ = [r[0] for r in rows if r[2] is CIRCULAR]

    print("\n" + "=" * 100)
    print("🔴 THIS AUDIT REPORTED A FALSE ABSENCE, AND THAT IS THE MORE USEFUL FINDING.")
    print("   v1 searched `reconstruction/reads/` only and concluded 'no transcribed side-note corpus")
    print("   is on this disk'. It was true of ONE DIRECTORY and false of the disk. Two sibling errors")
    print("   followed the same shape: the SRC clone was sought under ocr-spike/.scratch when it lives")
    print("   at palimpsest/.scratch, and the Madueke source was sought with `find -maxdepth 7` when it")
    print("   sits at DEPTH 8 -- reported as 'searched ALL of ~/Claude'.")
    print("   ⚠️ A BOUNDED SEARCH RETURNS 'NOT FOUND' IN THE SAME SHAPE AS AN EXHAUSTIVE ONE.")
    print("      State the bound, or do not claim the scope.")
    print("\n   ⚠️ AND `.scratch/original-douay-rheims` IS A BYTE-IDENTICAL COPY OF `janvier`")
    print("   (394 files, 0 differences), so counting both would have double-counted one corpus.")
    print("   The tracked homes under imports/.../sources/transcriptions/ are what this audit reads.")
    print("\n   ⚠️ TWO RUN-1 FINDINGS SURVIVE UNCHANGED:")
    print("   (a) §3.2 item 2 NAMES THE WRONG SOURCE -- its 1,334 blocks are ARGUMENTS, another class.")
    print("   (b) `scan_marginal` IS STILL POISON: the incumbent typer's own output, so training on it")
    print("       teaches agreement with the instrument being replaced, and that reads as validation.")
    print("=" * 100)

    # ⚠️ THE REPRESENTATIVE FRACTION LEADS. Marginalia is the class the programme is blocked on, so
    # its source count is the headline even now that it PASSES -- a status line reading `6/7` would
    # hide that one of the two Marginalia sources on disk is circular and must never be used.
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
    if not blocked:
        print("\n🟡 R14.6a: every region class HAS an admissible source -- Marginalia included, from")
        print("   the janvier corpus with odr-com corroborating -- but a CIRCULAR alternative is still")
        print("   on disk beside them and must never be substituted. Exit 1 stands while it is")
        print("   unguarded. ⚠️ R14.6c must still prove these labels LAND ON THE RIGHT INK: they are")
        print("   verse- and chapter-addressed, never leaf- or pixel-addressed, so alignment is the")
        print("   step that turns them into layout labels -- and that is scored against the hand gold.")
        return 1
    print("\n🔴 R14.6a: a region class has no admissible label source; R14.1's fine-tune cannot teach")
    print("   a class its labels do not cover.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
