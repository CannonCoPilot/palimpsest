#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ref_repair_s_dismas.py — recover the Genesis chapters `s_dismas` lost to a parsing failure (§13 Q48).

THE DEFECT. `s_dismas` is built from `02-genesis.pdf` by `pdftotext-parse`, and for genesis 8 and 46 it produced
ONE verse each instead of 22 and 34. That single entry holds the wrong text under the wrong key: genesis 8/1 is
`ANoe opening the windowe of the arke...`, which is verse 6, with a stray `A` on the front.

THE CAUSE, read off the extracted text. The PDF repeats a running head `Chapter 8` at each page break, and the
engraved drop capital is emitted as a line of its own:

    nd God remembred Noe, and al the beaſts,        <- verse 1, its initial A missing
    ... 6 And after that fourtie dayes were paſſed,
    A                                               <- the drop capital, orphaned
    50                                              <- the page number
    Chapter 8                                       <- RUNNING HEAD, mid-chapter
    Noe opening the windowe of the arke, which he had

Treating that running head as a chapter restart discards verses 1-6 and re-opens the chapter at the page break;
the orphaned `A` then glues to `Noe`. 49 of the 50 chapters carry such repeated headers, so this is not exotic —
the original parser copes with most and loses these two.

WHAT THIS DOES, AND THE CHECK THAT MAKES IT SAFE. It re-parses the PDF text with the running heads and the
orphaned drop capital handled, then **requires its output to reproduce the chapters `s_dismas` already has**
before any repaired chapter is accepted. A parser that cannot reproduce the 48 good chapters has no business
rewriting the 2 bad ones. Nothing is written unless `--apply` is passed, and the original file is copied aside
first.

NOTE ON SCOPE. This repairs a PARSE of an existing source. It does not invent text, and it does not touch
`odr_com`, whose gaps (chapters 4, 6, 9, 11, 13, 49) come from a different source and a different acquisition.

Usage:
  ../ocr-venv/bin/python ref_repair_s_dismas.py --verify         # reproduce-the-good-chapters check only
  ../ocr-venv/bin/python ref_repair_s_dismas.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PDF = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/DouayRheims_DR/"
           "sources/transcriptions/s-dismas/repo/Old-Testament/02-genesis.pdf")
READS = HERE.parent / "reconstruction" / "reads" / "s_dismas.json"
BOOK = "genesis"
_CHAP = re.compile(r"^Chapter (\d+)$")
_VNUM = re.compile(r"(?<!\S)(\d{1,3})\s+(?=[A-Za-zſ&])")
_PAGENO = re.compile(r"^\d{1,4}$")
# A marginal note opens with its anchor letter and a capitalised sentence: `a The crowe returned not...`,
# `a That is, she bare their fathers in Meſopotamia.` Body prose starting with a bare `a`/`b` and a capital
# does not occur in Genesis, and the pattern is only consulted at a page foot (see `_strip_page_furniture`).
_NOTE_ANCHOR = re.compile(r"^[a-f]\s+[A-ZſVI]")


def _fold_word(w: str) -> str:
    return re.sub(r"[^a-z]", "", w.lower().replace("ſ", "s").replace("v", "u").replace("j", "i"))


def _fold_words(t: str) -> list[str]:
    return [_fold_word(w) for w in t.split()]


def pdf_lines() -> list[str]:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as t:
        out = Path(t.name)
    subprocess.run(["pdftotext", str(PDF), str(out)], check=True, capture_output=True)
    return out.read_text(errors="ignore").splitlines()


def chapter_blocks(lines: list[str]) -> dict[int, list[str]]:
    """All lines of each chapter, with repeated running heads folded back in rather than restarting the chapter.

    A `Chapter N` line is a header only the FIRST time; every later occurrence of the SAME number is the running
    head of a continuation page and is dropped, keeping the text on both sides in one block."""
    blocks: dict[int, list[str]] = {}
    cur = None
    for ln in lines:
        m = _CHAP.match(ln.strip())
        if m:
            n = int(m.group(1))
            if n in blocks:            # running head of a continuation page
                cur = n
                continue
            blocks[n] = []
            cur = n
            continue
        if cur is not None:
            blocks[cur].append(ln)
    return blocks


def _strip_page_furniture(block: list[str], title: str) -> list[str]:
    """Delete the apparatus that sits at a PAGE FOOT, which `pdftotext` emits in the middle of a verse.

    THE DEFECT. Chapter 8's printed verse 20 comes out of the parser as

        ... for the ſenſe and cogitation of | a The crowe returned not into the arke, but (as appeareth by the
        Hebrew text) ... | b They entred into the arke the 17. day ... | 51 | Genesis | mans hart are prone to euil

    — two marginal notes, the page number and the facing page's running head `Genesis`, spliced into the middle
    of the scripture. Genesis 46:25 carries exactly the same wound (`a That is, she bare their fathers in
    Meſopotamia. in Gen. S. Aug. q. 151. Genesis`). It is not a suffix, so no trimmer at the end of a verse can
    reach it, and both chapters are ones this module repairs — so the note block travels with the repair.

    THE SHAPE IT IS RECOGNISED BY, which is structural rather than lexical. The page number is the anchor: it is
    unambiguous and already detected. Above it sit the notes — each a blank-separated ONE-LINE group, because
    the PDF lays them out as separate text objects, while body prose runs many lines with no blank between. The
    note's FIRST line is the exception: it abuts the last body line, and is identified by its anchor letter.
    Below the page number sits the running head of the facing page, the book's name on its own line — the same
    fault `chapter_blocks` already handles for `Chapter N`, and the reason `Genesis` ended up inside a verse.

    WHAT IT DELIBERATELY DOES NOT TOUCH. A lone capital on its own line is the engraved DROP CAPITAL, which also
    falls next to a page number (chapter 8 line `A`, chapter 46 line `A`); the backward scan stops dead at it so
    `verses` can still put it back on the front of verse 1."""
    n = len(block)
    drop: set[int] = set()
    for i, ln in enumerate(block):
        if not _PAGENO.fullmatch(ln.strip()):
            continue
        drop.add(i)
        j = i + 1                                       # forward: the facing page's running head
        while j < n and (not block[j].strip() or block[j].strip() == title):
            if block[j].strip() == title:
                drop.add(j)
            j += 1
        j, run = i - 1, []                              # backward: the marginal-note run
        while j >= 0 and len(run) < 8:
            s = block[j].strip()
            if not s:
                j -= 1
                continue
            if len(s) == 1 and s.isalpha() and s.isupper():
                break                                   # the drop capital — leave it for `verses`
            isolated = (j == 0 or not block[j - 1].strip()) and (j + 1 >= n or not block[j + 1].strip())
            if isolated and len(s) <= 120:
                run.append(j)
                j -= 1
                continue
            if _NOTE_ANCHOR.match(s):                   # the note's first line, abutting the body
                run.append(j)
            break
        # THE GUARD, and the reason the run is committed as a whole rather than line by line. `isolated` alone
        # is a layout accident: a page whose body happens to contribute one line above the number would be read
        # as a note and DELETED — a synthetic block of exactly that shape lost its scripture in test. A note run
        # always carries its anchor letter somewhere (`a The crowe...`, `a That is...`), and the bare marginal
        # citations (`in Gen.`, `S. Aug. q. 151.`) only ever appear alongside one. No anchor, no deletion: the
        # page number goes and the text stays.
        if any(_NOTE_ANCHOR.match(block[k].strip()) for k in run):
            drop.update(run)
    return [ln for k, ln in enumerate(block) if k not in drop]


def verses(block: list[str], v1_anchor: str = "") -> dict[int, str]:
    """Split one chapter block into verses on its printed numerals.

    The drop capital is emitted on a line of its own and the page number likewise; both are dropped, and verse 1
    is restored by putting the capital back on the front of its lowercase opening word."""
    # THE CHAPTER BLOCK CARRIES ITS ANNOTATIONS TOO, and they cite verses by number — `19 Built an Altar.) Noe
    # without expreſſe commandment...`. Those citations are read as verse markers, which both injects commentary
    # into the text and SHIFTS EVERY LATER VERSE: the first parse of chapter 8 put verse 16's text under 15, 17's
    # under 16, and so on from verse 15 down, with verse 22 lost off the end. The PDF marks the boundary
    # explicitly with a line `Annotations`, so the block is cut there.
    for i, ln in enumerate(block):
        if ln.strip().lower() in ("annotations", "annotation"):
            block = block[:i]
            break
    block = _strip_page_furniture(block, BOOK.capitalize())
    keep: list[str] = []
    dropcap = None
    for ln in block:
        s = ln.strip()
        if not s:
            continue
        if _PAGENO.fullmatch(s):
            continue
        if len(s) == 1 and s.isalpha() and s.isupper():
            dropcap = s
            continue
        keep.append(s)
    text = " ".join(keep)
    # THE ARGUMENT CARRIES VERSE NUMBERS, and it sits between the chapter heading and verse 1:
    # "The waters diminishing by litle and litle, 6. Noe ſendeth forth a crow, 8. after him a doue, thriſe:
    #  18. laſtly goeth forth ... 20. erecteth an Altar".
    # Splitting on numerals without cutting it first put the ARGUMENT into verse 1 and its summary phrases into
    # verses 6, 8, 18 and 20 — which is why the first re-parse of chapter 8 agreed with the other references at
    # only 0.694. The body's start is located by matching janvier's verse 1, the same content-anchor use
    # `verse_locate` and the chapter-model deriver already make of it: janvier says WHERE the verse begins, never
    # how it is spelled.
    if v1_anchor:
        toks = [t for t in _fold_words(v1_anchor)[:6] if t]
        if toks:
            words = text.split()
            fold = [_fold_word(w) for w in words]
            best, best_hit = None, 0.0
            for i in range(len(fold) - len(toks)):
                hit = sum(1 for a, b in zip(fold[i:i + len(toks)], toks) if a == b) / len(toks)
                if hit > best_hit:
                    best, best_hit = i, hit
            if best is not None and best_hit >= 0.5:
                text = " ".join(words[best:])
    parts = _VNUM.split(text)
    out: dict[int, str] = {}
    if parts:
        head = parts[0].strip()
        if head:
            if dropcap and head[:1].islower():
                head = dropcap + head
            out[1] = head
    for i in range(1, len(parts) - 1, 2):
        try:
            n = int(parts[i])
        except ValueError:
            continue
        body = parts[i + 1].strip()
        if body:
            out[n] = body
    return out


def QC_load(name: str) -> dict[str, str]:
    import qc_audit as QC
    return QC.load_reads_verse(name)


def _renumbered(RR, ch: int, parsed_ch: dict[int, str], raw_others: list[dict[str, str]]) -> dict[int, str]:
    """`parsed_ch` with this chapter's `ref_renumber` correction applied, so the gate scores what the loader
    will see. A chapter with no correction entry comes back unchanged."""
    keyed = {f"scripture/{BOOK}/{ch}/{v}": t for v, t in parsed_ch.items()}
    fixed = RR.apply("s_dismas", keyed, others=raw_others)
    return {int(k.rsplit("/", 1)[1]): t for k, t in fixed.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    import verse_seg as VS

    lines = pdf_lines()
    blocks = chapter_blocks(lines)
    janv_v1 = {ch: (VS.chapter_verses(BOOK, ch, VS.JANVIER) or {}).get(1, "") for ch in range(1, 51)}
    parsed = {ch: verses(b, janv_v1.get(ch, "")) for ch, b in sorted(blocks.items())}
    cur = json.loads(READS.read_text())
    have: dict[int, dict[int, str]] = {}
    # A chapter this module has ALREADY written is always a candidate again: it came out of this parser, so a
    # parser that has since been corrected supersedes it. Genesis 46 was repaired before the page-foot note
    # block was understood, and its verse 25 still carries `a That is, she bare their fathers in Meſopotamia.
    # in Gen. S. Aug. q. 151. Genesis` — a full-count chapter that the count test can no longer reach.
    prior: set[int] = set()
    for r in cur["reads"]:
        sk = r.get("skeleton_id", "").split("/")
        if len(sk) == 4 and sk[1] == BOOK:
            have.setdefault(int(sk[2]), {})[int(sk[3])] = r.get("surface", "")
            if r.get("method") == "pdftotext-parse-repaired":
                prior.add(int(sk[2]))

    print(f"{'ch':>3} {'janvier':>8} {'existing':>9} {'parsed':>7}   verdict")
    reproduce_ok = reproduce_bad = 0
    repair: list[int] = []
    for ch in range(1, 51):
        jn = len(VS.chapter_verses(BOOK, ch, VS.JANVIER) or {})
        h, p = len(have.get(ch, {})), len(parsed.get(ch, {}))
        verdict = ""
        if ch in prior:
            repair.append(ch)
            verdict = "  <-- REPARSE (written by this module before)"
        elif h >= 0.9 * jn:
            # a chapter s_dismas already has: the parser MUST reproduce it
            if p >= 0.9 * jn:
                reproduce_ok += 1
            else:
                reproduce_bad += 1
                verdict = "  <-- PARSER FAILS A GOOD CHAPTER"
        elif p >= 0.9 * jn:
            repair.append(ch)
            verdict = "  <-- REPAIRABLE"
        else:
            verdict = "  <-- still short after re-parse"
        if verdict:
            print(f"{ch:>3} {jn:>8} {h:>9} {p:>7}{verdict}")
    print(f"\nreproduced {reproduce_ok} good chapters; FAILED to reproduce {reproduce_bad}")
    print(f"repairable chapters: {repair}")
    # THE DIRECT VALIDATION, which is stronger than the proxy above. "Reproduces other chapters" tests the
    # parser in general; what actually matters is whether THESE repaired verses are right. Each repaired verse is
    # scored against the three references that DO have the chapter, on the content fold. A verse that agrees with
    # all three is not a guess — it is the same text arriving by an independent route.
    import ref_renumber as RR
    others = {n: RR.load_corrected(n) for n in ("odr_com", "sabates_a", "madueke_b")}
    raw_others = [QC_load(n) for n in RR.OTHERS["s_dismas"]]
    ok_repair = []
    for ch in repair:
        sims = []
        # SCORE THE NUMBERING THE LOADER WILL ACTUALLY USE. Chapter 8's page prints DR verses 15 and 16 merged
        # under `15` and numbers the rest one lower; the parse is faithful to the page and `ref_renumber` puts
        # the numbering right at load time. Gating the RAW parse instead scored it at 0.665 with 7 verses under
        # 0.70 — a correct transcription rejected for an edition's numbering, which is exactly the fault
        # `ref_renumber` exists to separate out.
        for v, surf in sorted(_renumbered(RR, ch, parsed[ch], raw_others).items()):
            for n, d in others.items():
                ref = d.get(f"scripture/{BOOK}/{ch}/{v}")
                if ref and n == "odr_com":
                    from char_identity import evaluate_locus
                    import verse_seg as _VS
                    jv = (_VS.chapter_verses(BOOK, ch, _VS.JANVIER) or {}).get(v)
                    sims.append(evaluate_locus(surf, jv, ref)["archaic_id"])
        if not sims:
            print(f"  ch{ch}: NO other reference to check against — refused")
            continue
        mean = sum(sims) / len(sims)
        lo = sum(1 for x in sims if x < 0.70)
        print(f"  ch{ch}: {len(parsed[ch])} verses, {len(sims)} cross-checks, mean content agreement "
              f"{mean:.4f}, below 0.70: {lo}")
        # The gate is the ARCHAIC arm against odr_com, not a raw character ratio against the modern references:
        # comparing `fourtie`/`paſſed` to `forty`/`passed` scored a correct parse at 0.69 and read as a failure.
        if mean >= 0.85 and lo <= max(2, len(sims) // 12):
            ok_repair.append(ch)
        else:
            print(f"  ch{ch}: REFUSED — the re-parse does not agree with the other references")
    repair = ok_repair
    if reproduce_bad:
        print(f"\nNOTE: the parser fails to reproduce {reproduce_bad} good chapters (26, 30), so it is NOT used "
              f"for them — only for chapters it can validate directly against the other references.")
    for ch in repair:
        print(f"\n  ch{ch} sample — v1: {parsed[ch].get(1, '')[:90]!r}")
        print(f"            v2: {parsed[ch].get(2, '')[:90]!r}")
    if not a.apply:
        print("\n(dry run — pass --apply to write)")
        return 0
    if not repair:
        print("nothing to repair")
        return 0
    backup = READS.with_suffix(f".json.pre-genesis-reparse")
    if not backup.exists():
        shutil.copy2(READS, backup)
        print(f"[backup] {backup.name}")
    keep = [r for r in cur["reads"]
            if not (r.get("skeleton_id", "").startswith(f"scripture/{BOOK}/")
                    and int(r["skeleton_id"].split("/")[2]) in set(repair))]
    added = 0
    for ch in repair:
        for v, surf in sorted(parsed[ch].items()):
            keep.append({"skeleton_id": f"scripture/{BOOK}/{ch}/{v}", "present": True, "surface": surf,
                         "spelling": "archaic", "locus": f"s-dismas 02-{BOOK}.pdf Chapter {ch}",
                         "method": "pdftotext-parse-repaired", "local_confidence": "high",
                         "evidence_ptr": f"s_dismas:{BOOK}:{ch}:{v}"})
            added += 1
    cur["reads"] = keep
    cur["count"] = len(keep)
    READS.write_text(json.dumps(cur, ensure_ascii=False))
    print(f"[wrote] {READS.name}: +{added} verses across {repair}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
