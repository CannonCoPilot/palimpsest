#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coverage_figure.py — which parts of the Douay-Rheims does each reference actually cover?

WHY THIS EXISTS. Every coverage claim in this project so far has been a single number ("s_dismas: 25,892
loci"), and a single number cannot answer the question that matters — *which* parts are missing, and do the
gaps in one reference coincide with the gaps in another. The pseudo-archaic build (§4) is sized entirely by
that question, and the answer is a shape, not a scalar.

WHAT IT MEASURES, INDEPENDENTLY PER REFERENCE. For each of the 76 book names attested across the four
references, and each chapter within it, the figure records how many verses that reference holds. The
denominator is the **union across all four references**, stated as such — there is no external canonical
verse-count table in this project, so a chapter's expected length is taken to be the largest count any
reference reports for it. That is a lower bound on the true text, and any cell showing 100% may still be
short if *every* reference is short. This is stated on the figure itself rather than left for a reader to
assume.

Output: a standalone HTML page with an SVG grid per reference, plus the per-book table underneath.
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ref_renumber as RR                       # noqa: E402

REFS = ("s_dismas", "odr_com", "sabates_a", "madueke_b")
ARM = {"s_dismas": "ARCHAIC", "odr_com": "ARCHAIC", "sabates_a": "MODERN", "madueke_b": "MODERN"}

# Douay-Rheims order, grouped as the volumes were actually bound. Names are the project's slugs; the
# ALTERNATES map records the forms a reader may expect, because the DR's names are not the modern ones and a
# figure that silently uses only our slugs is unreadable to anyone who knows the book as "Isaiah".
ORDER = [
    ("OT1 — Pentateuch & Historical", [
        "genesis", "exodus", "leviticus", "numbers", "deuteronomy", "josue", "judges", "ruth",
        "1-kings", "2-kings", "3-kings", "4-kings", "1-paralipomenon", "2-paralipomenon",
        "1-esdras", "2-esdras", "3-esdras", "4-esdras", "tobias", "judith", "esther", "job"]),
    ("OT2 — Wisdom & Prophets", [
        "psalms", "proverbs", "ecclesiastes", "canticle-of-canticles", "wisdom", "ecclesiasticus",
        "isaie", "jeremie", "lamentations", "baruch", "ezechiel", "daniel", "osee", "joel", "amos",
        "abdias", "jonas", "micheas", "nahum", "habacuc", "sophonias", "aggeus", "zacharias",
        "malachie", "1-machabees", "2-machabees", "prayer-of-manasses"]),
    ("NT", [
        "matthew", "mark", "luke", "john", "acts", "romans", "1-corinthians", "2-corinthians",
        "galatians", "ephesians", "philippians", "colossians", "1-thessalonians", "2-thessalonians",
        "1-timothy", "2-timothy", "titus", "philemon", "hebrews", "james", "1-peter", "2-peter",
        "1-john", "2-john", "3-john", "jude", "apocalypse"]),
]

ALTERNATES = {
    "1-kings": "1 Samuel", "2-kings": "2 Samuel", "3-kings": "1 Kings", "4-kings": "2 Kings",
    "1-paralipomenon": "1 Chronicles", "2-paralipomenon": "2 Chronicles",
    "1-esdras": "Ezra", "2-esdras": "Nehemiah", "3-esdras": "1 Esdras (apocr.)",
    "4-esdras": "2 Esdras (apocr.)", "isaie": "Isaiah", "jeremie": "Jeremiah",
    "ezechiel": "Ezekiel", "osee": "Hosea", "abdias": "Obadiah", "jonas": "Jonah",
    "micheas": "Micah", "habacuc": "Habakkuk", "sophonias": "Zephaniah", "aggeus": "Haggai",
    "zacharias": "Zechariah", "malachie": "Malachi", "canticle-of-canticles": "Song of Songs",
    "ecclesiasticus": "Sirach", "apocalypse": "Revelation", "tobias": "Tobit",
    "josue": "Joshua", "prayer-of-manasses": "Pr. of Manasseh",
}


def load() -> tuple[dict, dict, dict]:
    """-> per-reference {(book,chapter): nverses}, the union denominator, and the chapter list per book."""
    per = {r: collections.Counter() for r in REFS}
    for r in REFS:
        for k in RR.load_corrected(r):
            if not k.startswith("scripture/"):
                continue
            _, b, c, _v = k.split("/")
            per[r][(b, int(c))] += 1
    union = collections.Counter()
    for r in REFS:
        for key, n in per[r].items():
            union[key] = max(union[key], n)
    chapters = collections.defaultdict(set)
    for b, c in union:
        chapters[b].add(c)
    return per, union, {b: sorted(cs) for b, cs in chapters.items()}


def svg_grid(ref: str, per: dict, union: dict, chapters: dict) -> str:
    """One row per book, one cell per chapter, shaded by fraction of the union's verses this ref holds."""
    CW, RH, LEFT, TOP = 9, 13, 210, 26
    maxch = max((len(v) for v in chapters.values()), default=1)
    books = [b for _sec, bs in ORDER for b in bs if b in chapters]
    extra = sorted(set(chapters) - set(books))
    books += extra
    H = TOP + RH * (len(books) + len(ORDER)) + 16
    W = LEFT + CW * maxch + 60
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" role="img" '
           f'aria-label="chapter coverage for {html.escape(ref)}">']
    y = TOP
    for sec, bs in ORDER:
        present = [b for b in bs if b in chapters]
        if not present:
            continue
        out.append(f'<text x="4" y="{y + 9}" class="sec">{html.escape(sec)}</text>')
        y += RH
        for b in present:
            alt = ALTERNATES.get(b)
            label = b.replace("-", " ")
            lab = f"{label}" + (f"  ({alt})" if alt else "")
            out.append(f'<text x="4" y="{y + 9}" class="bk">{html.escape(lab)}</text>')
            for i, c in enumerate(chapters[b]):
                u = union[(b, c)]
                have = per[ref].get((b, c), 0)
                frac = (have / u) if u else 0.0
                cls = "z" if have == 0 else ("f" if frac >= 0.999 else ("p" if frac >= 0.5 else "q"))
                out.append(f'<rect x="{LEFT + i * CW}" y="{y}" width="{CW - 1}" height="{RH - 2}" '
                           f'class="{cls}"><title>{html.escape(b)} {c}: {have}/{u} verses</title></rect>')
            y += RH
        y += 2
    out.append("</svg>")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reference-coverage.html")
    a = ap.parse_args(argv)
    per, union, chapters = load()
    total_u = sum(union.values())

    summary = []
    for r in REFS:
        have = sum(min(per[r].get(k, 0), union[k]) for k in union)
        chs_full = sum(1 for k in union if per[r].get(k, 0) >= union[k])
        chs_none = sum(1 for k in union if per[r].get(k, 0) == 0)
        summary.append((r, have, 100 * have / total_u, chs_full, chs_none, len(union)))

    css = """
    body{font:13px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:24px;
         background:#faf9f7;color:#1a1a1a}
    @media (prefers-color-scheme: dark){body{background:#16161a;color:#e8e6e3}}
    h1{font-size:20px;margin:0 0 4px} h2{font-size:15px;margin:26px 0 6px}
    .note{max-width:900px;color:#555;font-size:12px;margin:0 0 18px}
    @media (prefers-color-scheme: dark){.note{color:#a8a5a0}}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:22px}
    .panel{border:1px solid #ddd;border-radius:8px;padding:12px;background:#fff;overflow-x:auto}
    @media (prefers-color-scheme: dark){.panel{background:#1e1e24;border-color:#33333c}}
    text.sec{font:600 10px sans-serif;fill:#888} text.bk{font:9.5px sans-serif;fill:#444}
    @media (prefers-color-scheme: dark){text.bk{fill:#bbb}}
    rect.f{fill:#2f6f4e} rect.p{fill:#7aa87f} rect.q{fill:#d9b26a} rect.z{fill:#e6e3df}
    @media (prefers-color-scheme: dark){rect.z{fill:#2c2c34}}
    table{border-collapse:collapse;font-size:12.5px} th,td{padding:5px 10px;text-align:right;
      border-bottom:1px solid #e5e5e5} th:first-child,td:first-child{text-align:left}
    @media (prefers-color-scheme: dark){th,td{border-color:#33333c}}
    .key span{display:inline-block;width:11px;height:11px;vertical-align:-1px;margin:0 4px 0 12px;border-radius:2px}
    """
    body = [f"<style>{css}</style>",
            "<h1>Douay-Rheims reference coverage — by book and chapter</h1>",
            '<p class="note"><b>What the denominator is.</b> This project holds no external canonical '
            'verse-count table, so a chapter\'s expected length is the largest count any of the four '
            'references reports for it. Coverage is therefore measured against the <b>union of the four</b>, '
            'which is a <i>lower bound</i> on the true text: a chapter shown as complete may still be short '
            'if every reference is short. Book names are the Douay-Rheims forms; the modern equivalent is '
            'given in parentheses where it differs.</p>',
            '<p class="key">Key:<span style="background:#2f6f4e"></span>complete'
            '<span style="background:#7aa87f"></span>&ge;50%<span style="background:#d9b26a"></span>&lt;50%'
            '<span style="background:#e6e3df"></span>absent</p>',
            "<h2>Per-reference summary</h2>", "<table><tr><th>reference</th><th>arm</th>"
            "<th>verses held</th><th>% of union</th><th>chapters complete</th><th>chapters absent</th></tr>"]
    for r, have, pct, full, none, nch in summary:
        body.append(f"<tr><td>{r}</td><td>{ARM[r]}</td><td>{have:,}</td><td>{pct:.1f}%</td>"
                    f"<td>{full:,} / {nch:,}</td><td>{none:,}</td></tr>")
    body.append("</table>")
    body.append('<h2>Chapter grids</h2><div class="grid">')
    for r in REFS:
        body.append(f'<div class="panel"><b>{r}</b> <span style="color:#888">({ARM[r]})</span>'
                    + svg_grid(r, per, union, chapters) + "</div>")
    body.append("</div>")

    out = HERE / a.out
    out.write_text("\n".join(body))
    (HERE / ".campaign/reference-coverage.json").write_text(json.dumps(
        {"union_verses": total_u,
         "per_reference": {r: {"verses": h, "pct": round(p, 2), "chapters_complete": f,
                               "chapters_absent": z} for r, h, p, f, z, _ in summary}}, indent=1))
    print(f"{'reference':12} {'arm':8} {'verses':>8} {'% union':>8} {'ch complete':>12} {'ch absent':>10}")
    for r, h, p, f, z, nch in summary:
        print(f"{r:12} {ARM[r]:8} {h:>8,} {p:>7.1f}% {f:>7,}/{nch:<5,} {z:>10,}")
    print(f"\nunion denominator: {total_u:,} verses across {len(union):,} chapters")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
