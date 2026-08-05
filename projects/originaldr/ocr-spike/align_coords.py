#!/usr/bin/env python3
"""align_coords.py — coordinate rehabilitation (Sir, 2026-07-18).

Re-cut any transcription (OCR output OR Gold Transcript) to CANONICAL book/chapter/verse boundaries taken
from the best available reference: s_dismas -> odr_com -> janvier (modern USFM). "Trim and join" the input
so verse[i] covers the same span the reference's verse[i] does. MUST run before any OCR-vs-Any comparison,
and applied to the GT it snaps line-crossing text onto clean verse coordinates (a truer gold standard).

Method: fold both streams to a common normalized form (so ſ/vv/f-noise and archaic-vs-modern spelling don't
block matching), align tokens with difflib, map each reference verse boundary onto the input token stream,
and re-cut the ORIGINAL (unfolded) tokens there — every archaic glyph preserved, only the CUTS move.
"""
from __future__ import annotations
import json, re, difflib
from pathlib import Path

SPIKE = Path(__file__).resolve().parent
ROOT = SPIKE.parent
READS = ROOT / "reconstruction/reads"
JANVIER = ROOT.parent / "bible-ingest/repos/original-douay-rheims/usfm"  # fixed 2026-07-19 (was nonexistent core/imports/…)

def _fold(t: str) -> str:
    """normalize a token for ALIGNMENT only (never emitted): collapses archaic glyphs + light modern bridge."""
    t = t.lower().replace("ſ", "s").replace("æ", "ae").replace("œ", "oe").replace("vv", "w")
    t = t.replace("v", "u").replace("j", "i")
    t = re.sub(r"[^a-z0-9]", "", t)           # drop punctuation/markers/†
    t = t.replace("ff", "f")                  # OCR ſ->f noise leniency (double)
    return t

_WORD = re.compile(r"\S+")
def _toks(s: str): return _WORD.findall(s or "")

# ---- reference verse sources (cascade) ----
_CACHE = {}
def _reads(name):
    if name not in _CACHE:
        d = json.loads((READS / f"{name}.json").read_text())
        _CACHE[name] = {e["skeleton_id"]: e.get("surface", "") for e in d["reads"] if e.get("present")}
    return _CACHE[name]

_USFM_TAG = re.compile(r"\\(\w+)\*?")
def _strip_usfm(s: str) -> str:
    s = re.sub(r"\\(x|f)\b.*?\\\1\*", "", s)               # drop \x..\x*  \f..\f* (refs/footnotes)
    s = re.sub(r"\\(sc|add|nd|wj|qs|bk)\*?", "", s)        # keep inner text of char styles
    s = _USFM_TAG.sub("", s)
    return re.sub(r"\s+", " ", s).strip()

def _janvier_chapter(book: str, chapter: int) -> dict:
    f = JANVIER / f"{book}.usfm"
    if not f.is_file(): return {}
    out, inch = {}, False
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        cm = re.match(r"\\c\s+(\d+)", line)
        if cm: inch = int(cm.group(1)) == chapter; continue
        if not inch: continue
        vm = re.match(r"\\v\s+(\d+)\s*(.*)", line)
        if vm: out[int(vm.group(1))] = _strip_usfm(vm.group(2))
    return out

def ref_verses(book: str, chapter: int) -> tuple[dict, str]:
    """ordered {verse:int -> surface}, plus which source supplied it. s_dismas > odr_com > janvier."""
    for name in ("s_dismas", "odr_com"):
        d = _reads(name)
        vs = {}
        for k, surf in d.items():
            m = re.match(rf"scripture/{re.escape(book)}/{chapter}/(\d+)$", k)
            if m: vs[int(m.group(1))] = surf
        if vs: return dict(sorted(vs.items())), name
    jv = _janvier_chapter(book, chapter)
    if jv: return dict(sorted(jv.items())), "janvier"
    return {}, "none"

# ---- the aligner ----
def realign(text: str, refv: dict) -> dict:
    """re-cut `text` to the verse boundaries of refv (ordered {verse:surface}). -> {verse:int -> text}."""
    verses = list(refv.items())
    if not verses: return {}
    ref_tok, ref_vidx = [], []                         # folded ref tokens + their verse index
    for vi, (_, surf) in enumerate(verses):
        for t in _toks(surf):
            ft = _fold(t)
            if ft: ref_tok.append(ft); ref_vidx.append(vi)
    raw = _toks(text)
    in_tok = [_fold(t) for t in raw]
    keep = [i for i, ft in enumerate(in_tok) if ft]     # drop empty-folded (pure punctuation/marker) tokens
    in_f = [in_tok[i] for i in keep]
    sm = difflib.SequenceMatcher(a=ref_tok, b=in_f, autojunk=False)
    ref2in = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n): ref2in[a + k] = b + k        # ref-token -> in_f index
    # first-ref-token index for each verse
    first = {}
    for i, vi in enumerate(ref_vidx): first.setdefault(vi, i)
    # input start position (index into `keep`) for each verse = aligned pos of nearest ref token >= first
    starts = []
    for vi in range(len(verses)):
        pos, i = None, first.get(vi)
        while i is not None and i < len(ref_tok):
            if i in ref2in: pos = ref2in[i]; break
            i += 1
        starts.append(pos)
    # forward-fill None starts; enforce monotonic non-decreasing
    last = 0
    for vi in range(len(verses)):
        if starts[vi] is None or starts[vi] < last: starts[vi] = last
        last = starts[vi]
    out = {}
    for vi, (v, _) in enumerate(verses):
        s_in = starts[vi]
        e_in = starts[vi + 1] if vi + 1 < len(verses) else len(in_f)
        raw_lo = keep[s_in] if s_in < len(keep) else len(raw)
        raw_hi = keep[e_in] if e_in < len(keep) else len(raw)
        out[v] = " ".join(raw[raw_lo:raw_hi]).strip()
    return out


if __name__ == "__main__":
    # demo/apply on GT scripture loci: re-segment body -> verses_aligned, report boundary fixes
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?"); ap.add_argument("--book"); ap.add_argument("--apply-gt", action="store_true")
    a = ap.parse_args()
    GT = SPIKE / "ground-truth"
    LOCI = {"scripture-genesis-24":"genesis","scripture-genesis-16-p081":"genesis","scripture-genesis-16-p082":"genesis",
            "scripture-psalms-001":"psalms","scripture-psalms-074-p137":"psalms","scripture-psalms-074-p138":"psalms",
            "scripture-psalms-115-116":"psalms","scripture-psalms-118":"psalms","scripture-psalms-150-p265":"psalms",
            "scripture-psalms-150-p266":"psalms","scripture-matthew-28-p102":"matthew","scripture-2john":"2-john"}
    slugs = [a.slug] if a.slug else list(LOCI)
    for slug in slugs:
        d = json.loads((GT / f"{slug}.json").read_text())
        book = a.book or LOCI.get(slug)
        if not book:
            print(f"  {slug}: no book mapping — skip (pass --book)"); continue
        # group body by (chapter) using the verse tag "ch:v"
        by_ch = {}
        for L in d.get("body", []):
            if L.get("role") in ("excluded", "catchword"): continue
            m = re.match(r"(\d+):(\d+)", L.get("verse") or "")
            if m: by_ch.setdefault(int(m.group(1)), []).append(L.get("text", "") if isinstance(L.get("text"), str) else "")
        aligned = {}
        for ch, lines in by_ch.items():
            refv, src = ref_verses(book, ch)
            al = realign(" ".join(lines), refv)
            for v, t in al.items(): aligned[f"{ch}:{v}"] = t
            print(f"  {slug} ch{ch}: {len(al)} verses aligned from {src}")
        if a.apply_gt:
            d["verses_aligned"] = aligned
            d["_aligned_note"] = "coordinate-rehabilitated per align_coords.py (s_dismas>odr_com>janvier boundaries)"
            (GT / f"{slug}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2))
    print("done" + (" (verses_aligned written)" if a.apply_gt else " (dry run — pass --apply-gt to write)"))
