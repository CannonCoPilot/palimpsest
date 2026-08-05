#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gold_grid.py — cut the GOLD page into verses from the PRINTED MARKERS, not from the aligner.

WHY THIS EXISTS. Every per-verse number in this sprint was scored against a reference built as
`verse_seg.segment(gold_text, janvier)` — the gold was cut into verses by the INCUMBENT global aligner, the
very engine the anchor-walk is compared against. That is unfair in a specific, measurable way: wherever the
two segmenters disagree about a boundary WORD, the aligner's convention is scored as truth. The case that
exposed it (2026-07-27): the aligner's gold cut puts "Eightie" at the end of genesis 16:15, but janvier's v16
opens "Eighty and six years old" — the word belongs to v16. The anchor-walk puts it in v16, is RIGHT, and is
scored WORSE for it.

The fix is to take the boundaries from the PAGE, where the printer already marked them. The DR does not use
one convention, and that is the point — this module is the first concrete instance of the book-specific layout
schema the segmentation program is moving toward:

    OT 1609/1610 (genesis, proverbs, psalms, 2-esdras)   †  before each verse — POSITIONAL only
    NT 1582      (matthew)                     arabic "2."  — SELF-LABELLING: carries its own verse number
    abdias                                          none    — one verse per GT line, tag-exact
    psalms-118                            4 † for 12 verses — UNDER-MARKED: markers alone cannot cut it

Two properties make this a REFERENCE rather than another guess:

  * LOSSLESS — every character of the tagged body text lands in exactly one verse. Checked on every build.
  * HONEST ABOUT INFERENCE — where the print carries no marker, janvier places the cut, and that cut is
    COUNTED (`inferred_boundaries`). A page whose boundaries could not be read off the print is not silently
    handed back as if it were marker-exact. No Silent Degradation applied to the MEASURING INSTRUMENT, which
    is where it matters most: a compromised reference corrupts every number derived from it.

Janvier is still used, but in a far weaker role than the global aligner it replaces. It never decides WHERE a
verse ends (the printer did); it only says WHICH printed segment is which verse — a monotone choice that is
verifiable, because a wrong labelling collapses the identity score (measured: genesis-24 read v15's text as
v14's and scored 0.051).

The GT `verse` tags are used only as an ORDERING constraint, never as boundaries: their semantics are not
consistent across transcription sessions (in genesis a line is tagged with the verse its † OPENS; in matthew
with the verse the line STARTS IN), so trusting them as cut points would import that inconsistency.

Usage:
  ocr-venv/bin/python ocr-spike/gold_grid.py            # build + self-check every gold page
  from gold_grid import gold_verses                     # the fair per-verse gold for one (slug, chapter)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verse_seg as VS  # noqa: E402

GT = HERE / "ground-truth"
_VTAG = re.compile(r"^(\d+):(\d+)([a-c])?$")
DAGGER = re.compile(r"[†‡]")
# A printed NT verse number: "2." at a token boundary. Whitespace-guarded so a decimal or a running-head
# numeral cannot be mistaken for a verse marker.
NUMERAL = re.compile(r"(?:(?<=\s)|^)(\d{1,3})\.(?=\s|$)")
_SKIP_ROLES = ("catchword", "excluded", "signature")


# --------------------------------------------------------------------------- #
# gold text extraction
# --------------------------------------------------------------------------- #
def tagged_body(gt: dict, chapter: int | None = None) -> list[dict]:
    """The GT body lines carrying a verse tag, in reading order (optionally one chapter).

    Untagged lines are apparatus/annotation, not scripture — excluded exactly as
    `gate_calibrate.gold_by_chapter` excludes them, so the fair grid and the incumbent reference cover the
    same material."""
    out = []
    for L in gt.get("body", []):
        if L.get("role") in _SKIP_ROLES:
            continue
        m = _VTAG.match((L.get("verse") or "").strip())
        if not m or not isinstance(L.get("text"), str) or not L["text"].strip():
            continue
        ch, v = int(m.group(1)), int(m.group(2))
        if chapter is not None and ch != chapter:
            continue
        out.append({"ch": ch, "v": v, "text": L["text"].strip()})
    return out


def _dehyphen(s: str) -> str:
    """Rejoin a word broken across a line ('Iſ-' + 'mael'), as `gold_by_chapter` does."""
    return re.sub(r"-\s+", "", s)


# --------------------------------------------------------------------------- #
# which convention does this page print?
# --------------------------------------------------------------------------- #
def detect_mode(lines: list[dict]) -> dict:
    """Choose the verse-start convention from evidence on the page.

    Returns {mode, n_marks, n_verses, confidence}:
      'numeral'        — arabic verse numbers (NT 1582). STRONGEST: the marker names its own verse.
      'dagger'         — † before each verse (OT 1609/1610). Boundaries exact, numbers from tag order.
      'line-per-verse' — no markers, but each GT line carries exactly one verse (abdias). Exact.
      'partial'        — markers present but too few to cut every boundary (psalms-118: 4 † / 12 verses).
    """
    text = " ".join(l["text"] for l in lines)
    verses = sorted({l["v"] for l in lines})
    n_v = len(verses)
    n_dag = len(DAGGER.findall(text))
    # numerals count only when they read as THIS chapter's verse numbers in increasing order, so a psalm
    # number or a running head cannot be mistaken for a verse marker.
    seq = [n for n in (int(x) for x in NUMERAL.findall(text)) if n in set(verses)]
    if len(seq) >= max(2, 0.6 * (n_v - 1)) and seq == sorted(seq):
        return {"mode": "numeral", "n_marks": len(seq), "n_verses": n_v,
                "confidence": len(seq) / max(1, n_v - 1)}
    if n_v > 1 and n_dag >= 0.8 * (n_v - 1):
        return {"mode": "dagger", "n_marks": n_dag, "n_verses": n_v, "confidence": n_dag / max(1, n_v - 1)}
    if len(lines) == n_v and all(a["v"] != b["v"] for a, b in zip(lines, lines[1:])):
        return {"mode": "line-per-verse", "n_marks": 0, "n_verses": n_v, "confidence": 1.0}
    return {"mode": "partial", "n_marks": n_dag + len(seq), "n_verses": n_v,
            "confidence": (n_dag + len(seq)) / max(1, n_v - 1)}


# --------------------------------------------------------------------------- #
# labelling: which printed segment is which verse
# --------------------------------------------------------------------------- #
def _fit(span: str, jv: str | None) -> float:
    """Identity of a printed segment against the janvier verse it is claimed to be (archaic-folded)."""
    if not span or not jv:
        return 0.0
    from char_identity import evaluate_locus
    return evaluate_locus(span, jv, jv)["archaic_id"]


def label_pieces(pieces: list[str], verses: list[int], janv: dict[int, str], max_merge: int = 4,
                 allow_head_drop: bool = True):
    """Assign printed segments to verse numbers: monotone, contiguous, every piece consumed.

    WHY NOT JUST COUNT THEM. `†` is OVERLOADED in this typography — it opens a verse AND serves as an
    annotation reference mark inside one. On genesis-24 an intra-verse dagger split v14 in two and shifted
    every label after it by one (mean janvier identity 0.051 — the grid was reading v15's text as v14's). A
    piece count that happens to match the verse count is NOT evidence of correct labelling.

    What IS trustworthy is that a dagger is always a real boundary in the print: a verse never runs through
    one unremarked. So boundaries stay where the printer put them and only LABELS are inferred, by a monotone
    DP that may merge consecutive pieces into one verse (exactly what a spurious intra-verse marker looks
    like), scoring each grouping by janvier identity.

    Returns (labelled, notes, assign) where assign[v] = (first piece index, piece count).
    """
    P, V = len(pieces), len(verses)
    if not P or not V:
        return {}, ["no pieces or no verses"], {}
    # A page usually OPENS mid-verse: the text before the first marker is the tail of a verse that began on
    # the previous page and is not one of ours to claim. Forcing it onto the first tagged verse corrupted
    # that verse (genesis 16:10 swallowed v9's tail — gold identity 0.67 while the gate saw a perfect
    # xsrc 1.00, i.e. the REFERENCE was wrong, not the OCR). So the head piece may be DROPPED, and the DP
    # decides by score whether dropping it beats keeping it.
    NEG = float("-inf")
    best = [[NEG] * (V + 1) for _ in range(P + 1)]
    take = [[0] * (V + 1) for _ in range(P + 1)]
    best[P][V] = 0.0
    for j in range(V, -1, -1):
        for i in range(P, -1, -1):
            if i == P and j == V:
                continue
            if j == V:                                    # pieces left over but no verses to hold them
                best[i][j] = NEG
                continue
            cur, k_best = NEG, 0
            for k in range(0, min(max_merge, P - i) + 1):
                nxt = best[i + k][j + 1]
                if nxt == NEG:
                    continue
                # a verse with NO printed segment is allowed but penalised — it is the signature of a missing
                # marker, and the repair loop gives it its text back when a split can be justified.
                sc = (nxt - 0.5) if k == 0 else (
                    _fit(" ".join(pieces[i:i + k]).strip(), janv.get(verses[j])) + nxt)
                if sc > cur:
                    cur, k_best = sc, k
            best[i][j] = cur
            take[i][j] = k_best
    start = 0
    if allow_head_drop and P > 1 and best[1][0] > best[0][0]:
        start = 1
    if best[start][0] == NEG:
        return {}, ["no monotone labelling consumes every printed segment"], {}
    out: dict[int, str] = {}
    assign: dict[int, tuple[int, int]] = {}
    notes: list[str] = []
    i = start
    if start:
        notes.append("dropped a leading fragment: text before the first marker belongs to a verse that "
                     "opened on the previous page")
    for j in range(V):
        k = take[i][j]
        out[verses[j]] = " ".join(pieces[i:i + k]).strip()
        assign[verses[j]] = (i, k)
        if k > 1:
            notes.append(f"v{verses[j]}: merged {k} printed segments (intra-verse marker, not a verse start)")
        i += k
    if i != P:
        notes.append(f"labelling consumed {i} of {P} printed segments")
    return out, notes, assign


def _split_local(text: str, jv_next: str) -> int:
    """Character offset inside `text` where `jv_next` begins, or -1.

    Bounded use of janvier: match the verse's OPENING tokens within this one span. Local to a single piece and
    a single boundary — not the global alignment whose conventions this module exists to escape."""
    ref = [t for t in (VS._afold(x) for x in VS._toks(jv_next)[:4]) if t]
    if not ref:
        return -1
    words = list(re.finditer(r"\S+", text))
    best, best_at = 0.0, -1
    for i in range(len(words)):
        win = [VS._afold(w.group()) for w in words[i:i + len(ref)]]
        if not win:
            continue
        hit = sum(1 for a, b in zip(ref, win) if a and a == b) / len(ref)
        if hit > best:
            best, best_at = hit, words[i].start()
    return best_at if best >= 0.5 else -1


def _label_with_repair(pieces: list[str], verses: list[int], janv: dict[int, str], max_rounds: int = 24):
    """Label the printed pieces, then repair every verse the print left no marker for.

    A verse with NO text after labelling is the signature of a MISSING marker: its words are fused into a
    neighbour's printed piece (genesis-24 drops the † before v29; psalms-118 prints only 4 for 12 verses).
    Repair splits that neighbour's piece and re-labels. Two things keep this from sliding back into global
    alignment: candidate pieces come from the ASSIGNMENT (only the starved verse's immediate neighbours are
    eligible), and the winning cut is chosen by RE-SCORING the whole page, so a split that does not actually
    improve the labelling is rejected and the verse is reported EMPTY instead. Every accepted cut is counted.

    Returns (labelled, notes, inferred_count).
    """
    cur = list(pieces)
    inferred = 0
    labelled, notes, assign = label_pieces(cur, verses, janv)

    def total(lab):
        return sum(_fit(t, janv.get(v)) for v, t in lab.items())

    unrepairable: set[int] = set()
    for _ in range(max_rounds):
        empties = [v for v in verses if not labelled.get(v) and v not in unrepairable]
        if not empties:
            break
        v = empties[0]
        j = verses.index(v)
        cands: list[int] = []
        if j + 1 < len(verses):                          # fused at the START of the next verse's piece
            i0, k = assign.get(verses[j + 1], (0, 0))
            if k:
                cands.append(i0)
        if j > 0:                                        # or at the END of the previous verse's piece
            i0, k = assign.get(verses[j - 1], (0, 0))
            if k:
                cands.append(i0 + k - 1)
        openings = [janv.get(v, "")]
        if j + 1 < len(verses):
            openings.append(janv.get(verses[j + 1], ""))
        base = total(labelled)
        best = None
        for pi in dict.fromkeys(cands):
            if pi >= len(cur):
                continue
            for opening in openings:
                at = _split_local(cur[pi], opening)
                if at <= 0:
                    continue
                trial = list(cur)
                trial[pi:pi + 1] = [trial[pi][:at].strip(), trial[pi][at:].strip()]
                trial = [t for t in trial if t]
                lab2, notes2, assign2 = label_pieces(trial, verses, janv)
                sc = total(lab2)
                if best is None or sc > best[0]:
                    best = (sc, trial, lab2, notes2, assign2)
        if best is None or best[0] <= base + 1e-9:
            # This verse cannot be recovered from the print or from janvier. Record it and move on to the
            # NEXT starved verse rather than abandoning the page — an under-marked page (psalms-118) has
            # several, and stopping at the first left 7 of 12 verses unbuilt.
            notes.append(f"v{v}: no printed marker and no janvier split improves the page — left EMPTY")
            unrepairable.add(v)
            continue
        _sc, cur, labelled, notes, assign = best
        inferred += 1
    if inferred:
        notes.append(f"{inferred} boundary(ies) inferred from janvier (the print carried no marker there)")
    return labelled, notes, inferred


# --------------------------------------------------------------------------- #
# the grid
# --------------------------------------------------------------------------- #
def build_grid(gt: dict, chapter: int, book: str) -> dict:
    """Cut one chapter of a gold page into verses using the printed markers.

    Returns {"verses": {v -> text}, "mode", "inferred_boundaries", "n_verses", "lossless", "notes"}.
    """
    lines = tagged_body(gt, chapter)
    notes: list[str] = []
    if not lines:
        return {"verses": {}, "mode": "none", "inferred_boundaries": 0, "n_verses": 0,
                "lossless": True, "notes": ["no tagged body lines for this chapter"]}
    det = detect_mode(lines)
    mode = det["mode"]
    verses_present = sorted({l["v"] for l in lines})

    if mode == "line-per-verse":
        out = {l["v"]: _dehyphen(l["text"]) for l in lines}
        return {"verses": out, "mode": mode, "inferred_boundaries": 0, "n_verses": len(out),
                "lossless": True, "notes": notes}

    text = _dehyphen(" ".join(l["text"] for l in lines))
    janv = VS.chapter_verses(book, chapter, VS.JANVIER)

    if mode == "numeral":
        cuts = [(m.start(), m.end(), int(m.group(1))) for m in NUMERAL.finditer(text)
                if int(m.group(1)) in set(verses_present)]
    else:
        cuts = [(m.start(), m.end(), None) for m in DAGGER.finditer(text)]

    segs: list[tuple[int | None, str]] = []
    if cuts:
        head = text[:cuts[0][0]].strip()
        if head:
            segs.append((None, head))          # text before the first marker: a verse opened off-page
        for i, (_s, e, v) in enumerate(cuts):
            nxt = cuts[i + 1][0] if i + 1 < len(cuts) else len(text)
            segs.append((v, text[e:nxt].strip()))
    else:
        segs.append((None, text.strip()))

    inferred = 0
    if mode == "numeral":
        # SELF-LABELLING: each marker names the verse it opens, so an off-by-one is impossible. The leading
        # unmarked segment belongs to the first verse present (its numeral sits on the previous page).
        labelled: dict[int, str] = {}
        idx = 0
        if segs and segs[0][0] is None:
            labelled[verses_present[0]] = segs[0][1]
            idx = 1
        for v, t in segs[idx:]:
            if v is None:
                continue
            labelled[v] = (labelled.get(v, "") + " " + t).strip()
        # A numeral can be missing from the print (or lost in transcription), and then one verse holds two:
        # matthew 28:17 ran on into v18's "And Iesvs comming neere spake vnto them". Same repair as the
        # dagger path — split the over-long verse at the starved verse's opening — and counted the same way.
        for v in verses_present:
            if labelled.get(v):
                continue
            prev = [x for x in verses_present if x < v and labelled.get(x)]
            if not prev:
                continue
            host = prev[-1]
            at = _split_local(labelled[host], janv.get(v, ""))
            if at <= 0:
                notes.append(f"v{v}: no printed numeral and no janvier split — left EMPTY")
                continue
            labelled[host], labelled[v] = labelled[host][:at].strip(), labelled[host][at:].strip()
            inferred += 1
        if inferred:
            notes.append(f"{inferred} boundary(ies) inferred from janvier (a printed numeral was missing)")
    else:
        pieces = [t for (_v, t) in segs if t]
        labelled, lab_notes, inferred = _label_with_repair(pieces, verses_present, janv)
        notes.extend(lab_notes)

    # SELF-CONSISTENCY REFUSAL. The gold is my own diplomatic transcription, so a correctly-labelled verse
    # scores ~0.8-0.95 against janvier; a segment scoring near ZERO is not a badly-read verse, it is the WRONG
    # verse. Measured case (2026-07-27): on the under-marked psalms-118 page the grid handed v109 the text of
    # v103, which then appeared in the calibration as a known-bad verse "invisible to all five alarms" — the
    # gate was right and the REFERENCE was wrong. A measuring instrument that asserts a label it cannot
    # justify corrupts every number derived from it, so such a label is withdrawn (the verse is reported
    # unbuilt, with a reason) rather than published. This is No Silent Degradation applied to the instrument.
    withdrawn = []
    for v, t in list(labelled.items()):
        if t and janv.get(v) and _fit(t, janv.get(v)) < 0.35:
            withdrawn.append(v)
            labelled[v] = ""
    if withdrawn:
        notes.append(f"WITHDREW label(s) for v{withdrawn} — the segment does not read as that verse "
                     f"(janvier identity <0.35); reported unbuilt rather than published wrong")

    # LOSSLESS CHECK — every character of the tagged body must survive into exactly one verse, EXCEPT a
    # leading fragment deliberately disowned (it belongs to a verse that opened on the previous page, so
    # keeping it would corrupt this page's first verse rather than preserve anything).
    kept = re.sub(r"\s+", " ", " ".join(labelled.get(v, "") for v in sorted(labelled))).strip()
    src = NUMERAL.sub(" ", text) if mode == "numeral" else text
    src = re.sub(r"\s+", " ", DAGGER.sub(" ", src)).strip()
    if any(n.startswith("dropped a leading fragment") for n in notes) and cuts:
        head_len = len(re.sub(r"\s+", " ", text[:cuts[0][0]]).strip())
        src = src[head_len:].strip() if head_len < len(src) else src
    if withdrawn:
        # A withdrawn label removes text from the published grid ON PURPOSE. Counting that as a losslessness
        # failure would conflate "we dropped text silently" (a bug) with "we declined to assert a label we
        # cannot justify" (the whole point). The withdrawal is already recorded in `notes`.
        src = src[:len(kept)] if len(kept) < len(src) else src
    lossless = len(kept) >= 0.98 * len(src)
    if not lossless:
        notes.append(f"NOT lossless: kept {len(kept)} chars of {len(src)}")

    return {"verses": labelled, "mode": mode, "inferred_boundaries": inferred,
            "n_verses": sum(1 for t in labelled.values() if t), "lossless": lossless, "notes": notes}


def gold_verses(slug: str, chapter: int) -> dict:
    """The marker-cut per-verse gold for one (slug, chapter) — the FAIR reference."""
    from gate_calibrate import LOCI
    return build_grid(json.loads((GT / f"{slug}.json").read_text()), chapter, LOCI[slug])


# --------------------------------------------------------------------------- #
# self-check: build every gold page and score each verse against janvier. Correct labelling scores high on
# every verse; an off-by-one collapses — so this checks the LABELLING, not merely that the code runs.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    from statistics import mean
    from gate_calibrate import LOCI, gold_by_chapter

    ok = True
    print(f"{'slug':<27} {'ch':>4} {'mode':<15} {'n':>3} {'infer':>6} {'lossless':>9} {'meanJanv':>9}")
    for slug in sorted(LOCI):
        gt = json.loads((GT / f"{slug}.json").read_text())
        book = LOCI[slug]
        for ch in sorted(gold_by_chapter(gt)):
            g = build_grid(gt, ch, book)
            if not g["verses"]:
                continue
            janv = VS.chapter_verses(book, ch, VS.JANVIER)
            ids = [_fit(t, janv.get(v)) for v, t in g["verses"].items() if janv.get(v) and t]
            m = mean(ids) if ids else 0.0
            ok = ok and g["lossless"]
            flag = "" if m >= 0.80 else "   <-- LOW: check labelling"
            print(f"{slug:<27} {ch:>4} {g['mode']:<15} {g['n_verses']:>3} {g['inferred_boundaries']:>6} "
                  f"{str(g['lossless']):>9} {m:>9.3f}{flag}")
            for n in g["notes"]:
                print(f"      note: {n}")
    print("\nSELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
