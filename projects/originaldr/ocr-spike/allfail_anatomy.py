# -*- coding: utf-8 -*-
"""ANATOMY OF THE ALL-FAIL VERSES — what a verse no witness can read actually looks like on the page.

An ALL-FAIL verse is one where every witness carrying the book is below the bar. By the book-audit's control
logic that rules out any single volume's recognizer, so the cause is VERTICAL and the question becomes: what
do these verses have in common that the passing ones do not?

This module answers that on six axes, each measured against a matched control — the verses that pass in every
witness, from the same book. Every number below is a CONTRAST, never a bare rate: "37% of all-fail verses are
page-initial" means nothing until you know the figure for verses that pass.

  PLACEMENT     where the verse sits in the page's line range, and whether it opens/closes a page or chapter
  LINE-SPLIT    how many lines it spans, and whether it is broken across a page boundary
  TYPESETTING   soft-hyphen breaks, drop-capital openings, verse-number markers
  LAYOUT        the marginal-apparatus load on the page the verse sits on
  VOCABULARY    length, rare tokens, proper nouns, numerals in the reference text
  CONTENT       the reference itself — is it short, is it a name-list, is it a formula

Usage:  python allfail_anatomy.py genesis [--out allfail-anatomy-genesis.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import book_audit as BA                      # noqa: E402
import qc_audit as QC                        # noqa: E402
import verse_seg as VS                       # noqa: E402
from corpus_wire_probe import stored_page    # noqa: E402

SOFT_HYPHEN = re.compile(r"[¬\-]\s*$")
VNUM = re.compile(r"^\d{1,3}[.,]?$")
CAPWORD = re.compile(r"^[A-ZÆŒ][a-zæœſ]")


def _page_of(loc: dict, key: str):
    r = loc.get(key)
    return int(r["page"]) if r and r.get("page") is not None else None


def anatomy(book: str) -> dict:
    rep = BA.audit_book(book)
    wits = rep["witnesses"]
    aud = json.loads((HERE / "coverage-audit-verse.json").read_text())["verses"]
    sd, oc = QC.load_reads_verse("s_dismas"), QC.load_reads_verse("odr_com")
    archaic = dict(oc)
    archaic.update(sd)
    loc = {s: json.loads((HERE / f".corpus-localize-{d}.json").read_text())["verses"]
           for s, d in wits.items()}
    addr = {s: {r["page_index"]: r
                for r in json.loads((HERE / f".page-address-{d}.json").read_text())["records"]}
            for s, d in wits.items()}

    allfail = set(rep["cross_witness"]["all_fail_loci"])
    # CONTROL: verses that pass in EVERY witness. Same book, same pipeline, same references — so any axis on
    # which the two groups agree is an axis that does NOT explain the failure, which is as useful as one that does.
    control = []
    for ch in range(1, rep["n_chapters"] + 1):
        for v in (VS.chapter_verses(book, ch, VS.JANVIER) or {}):
            r = aud.get(f"scripture/{book}/{ch}/{v}")
            if not r:
                continue
            got = [s for s in wits if (r["sources"].get(s) or {}).get("localized")]
            if got and all((r["sources"][s] or {}).get("passed") for s in got):
                control.append(f"{ch}:{v}")

    pages = {}                                   # (wit, page_index) -> page, cached

    def page(w, pi):
        if (w, pi) not in pages:
            pages[(w, pi)] = stored_page(wits[w], pi)
        return pages[(w, pi)]

    def measure(loci: list[str]) -> dict:
        acc = collections.defaultdict(list)
        for k in loci:
            ch, v = map(int, k.split(":"))
            ref = archaic.get(f"scripture/{book}/{ch}/{v}") or ""
            rt = VS._toks(ref)
            cvs = VS.chapter_verses(book, ch, VS.JANVIER) or {}
            # ---- CONTENT / VOCABULARY (reference-side: independent of any witness)
            acc["ref_tokens"].append(len(rt))
            acc["ref_chars"].append(len(ref))
            if rt:
                acc["frac_capitalised"].append(sum(1 for t in rt if CAPWORD.match(t)) / len(rt))
                acc["frac_numeric"].append(sum(1 for t in rt if any(c.isdigit() for c in t)) / len(rt))
                acc["mean_token_len"].append(statistics.mean(len(t) for t in rt))
            acc["is_chapter_first"].append(v == 1)
            acc["is_chapter_last"].append(v == max(cvs) if cvs else False)
            # ---- per-witness page-side axes, averaged over the witnesses that localized it
            spans, splits, hyph, initial, final, marg, ncols, vnum = [], [], [], [], [], [], [], []
            for w in wits:
                rec = loc[w].get(f"{book}/{ch}/{v}")
                if not rec:
                    continue
                pi = _page_of(loc[w], f"{book}/{ch}/{v}")
                pg = page(w, pi) if pi is not None else None
                if not pg:
                    continue
                body = [i for i, l in enumerate(pg["lines"]) if l.get("role") == "body"]
                if not body:
                    continue
                txt = rec.get("text") or ""
                nl = max(1, round(len(txt.split()) / 9))          # ~9 tokens per printed line in this setting
                spans.append(nl)
                # placement: where in the page's body run does this verse's text first appear?
                first = None
                head = " ".join(txt.split()[:3])
                for i in body:
                    if head and head[:12] and head[:12] in (pg["lines"][i].get("text") or ""):
                        first = i
                        break
                if first is not None:
                    pos = body.index(first) / max(1, len(body) - 1)
                    initial.append(pos < 0.10)
                    final.append(pos > 0.90)
                # LINE-SPLIT: does the neighbouring verse sit on a different page? (cross-page fragment)
                pv = _page_of(loc[w], f"{book}/{ch}/{v-1}") if v > 1 else None
                nx = _page_of(loc[w], f"{book}/{ch}/{v+1}") if (v + 1) in cvs else None
                splits.append(bool((pv is not None and pv != pi) or (nx is not None and nx != pi)))
                # TYPESETTING: soft-hyphen breaks inside the span's own text
                hyph.append(sum(1 for t in txt.split() if SOFT_HYPHEN.search(t)))
                vnum.append(sum(1 for t in txt.split() if VNUM.fullmatch(t)))
                # LAYOUT: marginal load on the page
                roles = collections.Counter(l.get("role") for l in pg["lines"])
                marg.append(roles.get("marginalia", 0) / max(1, len(pg["lines"])))
                xs = sorted((l["bbox"][0] for l in pg["lines"] if l.get("role") == "body" and l.get("bbox")))
                ncols.append(len({round(x / 400) for x in xs}))
            for name, vals in (("lines_spanned", spans), ("cross_page", splits), ("soft_hyphens", hyph),
                               ("page_initial", initial), ("page_final", final),
                               ("marginalia_frac", marg), ("x_clusters", ncols), ("verse_numbers", vnum)):
                if vals:
                    acc[name].append(statistics.mean(float(x) for x in vals))
        out = {}
        for k, v in acc.items():
            if v:
                out[k] = round(statistics.mean(float(x) for x in v), 4)
        out["n"] = len(loci)
        return out

    return {"book": book, "n_all_fail": len(allfail), "n_control": len(control),
            "all_fail": measure(sorted(allfail)), "control": measure(control),
            "all_fail_loci": sorted(allfail, key=lambda k: tuple(map(int, k.split(":"))))}


AXES = [
    ("CONTENT", [("ref_tokens", "reference length, tokens"), ("ref_chars", "reference length, characters"),
                 ("mean_token_len", "mean token length")]),
    ("VOCABULARY", [("frac_capitalised", "capitalised tokens (names)"), ("frac_numeric", "tokens with digits")]),
    ("PLACEMENT", [("page_initial", "verse opens the page body"), ("page_final", "verse closes the page body"),
                   ("is_chapter_first", "verse 1 of its chapter"), ("is_chapter_last", "last verse of chapter")]),
    ("LINE-SPLIT", [("lines_spanned", "printed lines spanned"), ("cross_page", "neighbour on another page")]),
    ("TYPESETTING", [("soft_hyphens", "soft-hyphen breaks in span"), ("verse_numbers", "verse-number tokens in span")]),
    ("LAYOUT", [("marginalia_frac", "marginalia share of page lines"), ("x_clusters", "distinct body x-starts")]),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    r = anatomy(a.book)
    (Path(a.out) if a.out else HERE / f"allfail-anatomy-{a.book}.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=1))
    af, ct = r["all_fail"], r["control"]
    print(f"=== ALL-FAIL ANATOMY — {a.book.upper()} ===")
    print(f"all-fail verses: {r['n_all_fail']}   control (pass in EVERY witness): {r['n_control']}\n")
    print(f"{'axis':<34}{'ALL-FAIL':>10}{'CONTROL':>10}{'ratio':>9}   reading")
    for group, keys in AXES:
        print(f"-- {group}")
        for k, label in keys:
            if k not in af or k not in ct:
                continue
            x, y = af[k], ct[k]
            # A DEGENERATE AXIS IS NOT A FINDING. Where both groups sit at ~0 the ratio is 0 or infinite and
            # would print as the strongest signal on the page while carrying no information at all — the
            # numeric shape of a false positive. Say so instead of ranking it.
            if max(x, y) < 0.005:
                print(f"   {label:<31}{x:>10.3f}{y:>10.3f}{'  n/a':>9}   both ~0 — axis carries no signal")
                continue
            rat = (x / y) if y else float("inf")
            mark = "  <<<" if (rat > 1.35 or rat < 0.74) else ""
            print(f"   {label:<31}{x:>10.3f}{y:>10.3f}{rat:>9.2f}{mark}")
    print("\n<<< marks an axis where the two groups differ by more than a third — the ones that explain something.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
