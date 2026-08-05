#!/usr/bin/env python
"""EXPLORATORY (scratch, not committed): can we locate a chapter in the archive.org djvu OCR
by skeleton-token content-anchoring, and which djvu file covers which books?

If this works, A1b's stratified-random validation over the independent print witness is tractable
without rendering 1467 image pages. Throwaway de-risking probe.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

sys.path.insert(0, "core/tests/fixtures/gold/mask_engine/originaldr_validation")
import collate_witnesses as C   # reuse parse_madueke, skel-style helpers

AO = Path("projects/originaldr/sources/archive-org")
DJVU = {p.name.replace("_djvu.txt", ""): p for p in AO.glob("*_djvu.txt")}


# archaic/OCR skeleton fold (from ocr_validate.py) -- bridges archaic print <-> modern Madueke
import unicodedata
_LIG = (("æ", "ae"), ("œ", "oe"), ("ﬀ", "ff"), ("ﬁ", "fi"), ("ﬂ", "fl"))
def skel(word: str) -> str:
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    for a, b in _LIG:
        w = w.replace(a, b)
    w = w.replace("vv", "w")
    w = re.sub(r"[^a-z]", "", w)
    w = w.replace("v", "u").replace("j", "i")
    w = w.replace("f", "s")            # long-s (OCR reads ſ as f) <-> s
    w = re.sub(r"e$", "", w)
    w = re.sub(r"(.)\1+", r"\1", w)
    return w

def sk_tokens(text: str) -> list[str]:
    return [s for s in (skel(t) for t in re.findall(r"[A-Za-zÆæŒœ]+", text)) if len(s) >= 2]


def djvu_sk(name: str) -> list[str]:
    return sk_tokens(DJVU[name].read_text(encoding="utf-8", errors="replace"))


def locate(probe_sk: list[str], hay_sk: list[str]) -> tuple[float, int]:
    """Slide a window (len ~ probe) over hay; return (best recall, offset). Recall = fraction of
    probe skeleton-token TYPES present in the best window."""
    pset = set(probe_sk)
    if not pset:
        return 0.0, -1
    w = max(len(probe_sk), 40)
    best, best_off = 0.0, -1
    step = max(1, w // 4)
    for off in range(0, max(1, len(hay_sk) - w + 1), step):
        window = set(hay_sk[off:off + w])
        rec = len(pset & window) / len(pset)
        if rec > best:
            best, best_off = rec, off
    return best, best_off


def main():
    mad, order = C.parse_madueke()
    bmap = dict(zip(order, C.SAB_ORDER))
    inv = {v: k for k, v in bmap.items()}  # slug -> madueke display

    tests = [("genesis", 1), ("genesis", 17), ("psalms", 23), ("isaie", 33),
             ("matthew", 5), ("john", 1), ("romans", 8)]
    # preload djvu skeleton token lists
    print("djvu files:", list(DJVU))
    dj = {name: djvu_sk(name) for name in DJVU}
    for name, toks in dj.items():
        print(f"  {name}: {len(toks):,} skeleton tokens")
    print()
    for slug, ch in tests:
        disp = inv.get(slug)
        verses = mad.get(disp, {}).get(ch, {})
        probe = sk_tokens(" ".join(verses[v] for v in sorted(verses)))
        row = []
        for name in DJVU:
            rec, off = locate(probe, dj[name])
            row.append((name, rec, off))
        row.sort(key=lambda r: -r[1])
        top = row[0]
        print(f"{slug} {ch} (probe {len(probe)} sk-toks): BEST {top[0]} rec={top[1]:.2%} off={top[2]}"
              f"  | 2nd {row[1][0]} {row[1][1]:.2%}")


if __name__ == "__main__":
    raise SystemExit(main())
