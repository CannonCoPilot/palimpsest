#!/usr/bin/env python3
"""Spike scorer: rank a candidate OCR output against s-dismas diplomatic GT (Matthew 1).

Comparative harness — all candidates score against the SAME page (nt-1582 jp2_idx 0028)
and the SAME GT, so the page-vs-verse recall offset is uniform and cancels in the ranking.

Money metrics:
  long_s              raw count of ſ (U+017F) emitted (stock tesseract -> 0; target ~61)
  long_s_word_recall  fraction of GT tokens containing ſ that appear VERBATIM (with ſ) in OCR
                      -> the diplomatic signal; distinguishes ſ-preserving from ſ→f/ſ→s
  token_recall_fold   |OCR ∩ GT| / |GT| after ſ→s fold (did it read the WORDS, spelling-agnostic)
  token_recall_dipl   same WITHOUT fold (did it read the DIPLOMATIC form)
"""
from __future__ import annotations
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = json.loads((HERE / "gt_matthew1.json").read_text())


def fold_s(t: str) -> str:
    # long-s -> s ; strip combining; lowercase
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.replace("ſ", "s").lower()


def toks(t: str, fold: bool) -> set[str]:
    if fold:
        t = fold_s(t)
    else:
        t = t.lower()
    return {w for w in re.findall(r"[^\W\d_]+", t, re.UNICODE) if len(w) >= 2}


def score(ocr_text: str) -> dict:
    gt = GT["concat"]
    long_s = ocr_text.count("ſ")
    # GT tokens that carry a long-s, in DIPLOMATIC (unfolded, lowercased) form
    gt_s_words = {w for w in re.findall(r"[^\W\d_]+", gt.lower(), re.UNICODE) if "ſ" in w}
    ocr_dipl = toks(ocr_text, fold=False)
    ls_recall = (len(gt_s_words & ocr_dipl) / len(gt_s_words)) if gt_s_words else 0.0
    gt_f, ocr_f = toks(gt, fold=True), toks(ocr_text, fold=True)
    gt_d = toks(gt, fold=False)
    return {
        "chars": len(ocr_text),
        "long_s": long_s,
        "f_count": ocr_text.count("f"),
        "ae": ocr_text.count("æ"),
        "long_s_word_recall": round(ls_recall, 4),
        "gt_s_words_n": len(gt_s_words),
        "token_recall_fold": round(len(gt_f & ocr_f) / len(gt_f), 4),
        "token_recall_dipl": round(len(gt_d & ocr_dipl) / len(gt_d), 4),
    }


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "?"
    text = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace") if len(sys.argv) > 2 else sys.stdin.read()
    print(json.dumps({"label": label, **score(text)}, ensure_ascii=False))
