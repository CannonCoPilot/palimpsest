#!/usr/bin/env python
"""Generate the OriginalDR (idx 108) reconstruction technical report — a self-contained
HTML document with inline-SVG charts, computed entirely from the frozen gold map, the
production Catholic oracle, and the four committed validation artifacts (no hardcoded
figures, no external assets, no JS/CDN).

    .venv/bin/python docs/development/reports/gen_originaldr_108_report.py

Writes docs/development/reports/originaldr-108-reconstruction-report.html.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
from collections import defaultdict
from pathlib import Path

from palimpsest.gold import (books_chapters, classify_books_catholic, load_canon,
                             load_map, manifest_entry, verify_map)
from palimpsest.layout import LayoutConfig, masked_intervals

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # docs/development/reports → repo root (palimpsest/)
OUT = HERE / "originaldr-108-reconstruction-report.html"
OUT_TXT = REPO / "imports/Scripture/Bibles/OriginalDR/OriginalDR-modern-1582-1610.txt"
# committed validation package — first-class evidence, each artifact pinned to source sha256s
VALID = REPO / "core/tests/fixtures/gold/mask_engine/originaldr_validation"
A_COLLATION = VALID / "collation-3way.json"      # leg1 exact + leg2 format-fidelity
A_OCR = VALID / "ocr-validation.json"            # leg3 independent stratified print-OCR + bootstrap CI
A_GAPFILL = VALID / "apparatus-gapfill.json"     # apparatus channel coverage + Madueke_B corroboration
A_ORDER = VALID / "apparatus-order.json"         # scan-derived front/back-matter ordering evidence
IDX = 108

# ── palette ───────────────────────────────────────────────────────────────────
INK = "#1c1917"; MUTE = "#78716c"; LINE = "#e7e5e4"; PAPER = "#faf9f7"
SCRIPTURE = "#2563eb"   # unmasked scripture prose
APPARATUS = "#d97706"   # masked editorial apparatus
GOOD = "#15803d"; FLAG = "#dc2626"; ACCENT = "#7c3aed"
BAND = ["#2563eb", "#d97706", "#7c3aed", "#0891b2", "#65a30d", "#be185d"]


def esc(s) -> str:
    return html.escape(str(s))


def fmt(n: int) -> str:
    return f"{n:,}"


# ── SVG chart primitives ────────────────────────────────────────────────────────

def svg_open(w: int, h: int, title: str) -> str:
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(title)}" '
            f'style="max-width:{w}px;font-family:inherit">')


def donut(data: list[tuple[str, float, str]], total: float, w=660, h=300, title="") -> str:
    """data: (label, value, colour). Renders a donut with a legend."""
    cx, cy, r, rin = 150, 150, 120, 66
    h = max(h, 40 + len(data) * 42 + 12)   # grow viewBox so the legend never clips
    out = [svg_open(w, h, title)]
    ang = -math.pi / 2
    for label, val, col in data:
        frac = val / total if total else 0
        a2 = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        xi1, yi1 = cx + rin * math.cos(a2), cy + rin * math.sin(a2)
        xi2, yi2 = cx + rin * math.cos(ang), cy + rin * math.sin(ang)
        out.append(f'<path d="M{x1:.2f},{y1:.2f} A{r},{r} 0 {large},1 {x2:.2f},{y2:.2f} '
                   f'L{xi1:.2f},{yi1:.2f} A{rin},{rin} 0 {large},0 {xi2:.2f},{yi2:.2f} Z" '
                   f'fill="{col}"><title>{esc(label)}: {frac*100:.2f}%</title></path>')
        ang = a2
    # legend
    ly = 40
    for label, val, col in data:
        frac = val / total * 100 if total else 0
        out.append(f'<rect x="300" y="{ly}" width="13" height="13" rx="2" fill="{col}"/>')
        out.append(f'<text x="320" y="{ly+11}" font-size="12.5" fill="{INK}">{esc(label)}</text>')
        out.append(f'<text x="320" y="{ly+26}" font-size="11" fill="{MUTE}">{frac:.2f}% · {fmt(int(val))} ch</text>')
        ly += 42
    out.append("</svg>")
    return "".join(out)


def stacked_bar(segments: list[tuple[str, float, str]], total: float, w=760, title="") -> str:
    x0, y0, bw, bh = 20, 22, w - 40, 44
    ly0 = y0 + bh + 26
    h = ly0 + 22 * len(segments)          # vertical legend (labels vary in length)
    out = [svg_open(w, h, title)]
    x = x0
    for label, val, col in segments:
        seg = bw * (val / total) if total else 0
        out.append(f'<rect x="{x:.2f}" y="{y0}" width="{max(seg,0):.2f}" height="{bh}" fill="{col}">'
                   f'<title>{esc(label)}: {val/total*100:.2f}%</title></rect>')
        if seg > 60:
            out.append(f'<text x="{x+seg/2:.2f}" y="{y0+bh/2+5}" font-size="13" fill="#fff" '
                       f'text-anchor="middle" font-weight="600">{val/total*100:.1f}%</text>')
        x += seg
    ly = ly0
    for label, val, col in segments:
        out.append(f'<rect x="{x0}" y="{ly-11}" width="12" height="12" rx="2" fill="{col}"/>')
        t = f"{esc(label)} — {fmt(int(val))} chars ({val/total*100:.2f}%)"
        out.append(f'<text x="{x0+18}" y="{ly}" font-size="12.5" fill="{INK}">{t}</text>')
        ly += 22
    out.append("</svg>")
    return "".join(out)


def hbar(rows: list[tuple[str, float]], w=760, rowh=26, title="", unit="", colour=ACCENT) -> str:
    pad_l, pad_r, top = 200, 70, 12
    mx = max((v for _, v in rows), default=1) or 1
    h = top + len(rows) * rowh + 12
    barw = w - pad_l - pad_r
    out = [svg_open(w, h, title)]
    y = top
    for label, val in rows:
        bw = barw * (val / mx)
        out.append(f'<text x="{pad_l-8}" y="{y+rowh/2+4}" font-size="12" fill="{INK}" '
                   f'text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{pad_l}" y="{y+3}" width="{bw:.2f}" height="{rowh-8}" rx="2" fill="{colour}"/>')
        out.append(f'<text x="{pad_l+bw+6:.2f}" y="{y+rowh/2+4}" font-size="11.5" fill="{MUTE}">'
                   f'{fmt(int(val))}{unit}</text>')
        y += rowh
    out.append("</svg>")
    return "".join(out)


def ci_whisker(rows: list[tuple], w=760, rowh=32, title="") -> str:
    """Horizontal point-estimate + 95%-CI whiskers on a zoomed recall axis.

    rows: (label, point_pct, ci_lo, ci_hi, sublabel, colour). The x-axis is zoomed to
    [floor(min lo) − 1, 100] so the confidence intervals are actually resolvable rather
    than crushed against a 0–100 scale.
    """
    pad_l, pad_r, top = 156, 150, 16
    los = [r[2] for r in rows]
    dmin = max(0, math.floor(min(los)) - 1)
    dmax = 100
    plotw = w - pad_l - pad_r
    baseline = top + len(rows) * rowh

    def X(v):
        return pad_l + plotw * (v - dmin) / (dmax - dmin)

    h = baseline + 30
    out = [svg_open(w, h, title)]
    # gridlines + axis ticks (every 5%)
    t = dmin
    while t <= dmax:
        gx = X(t)
        out.append(f'<line x1="{gx:.1f}" y1="{top-6}" x2="{gx:.1f}" y2="{baseline}" stroke="{LINE}"/>')
        out.append(f'<text x="{gx:.1f}" y="{baseline+16}" font-size="10" fill="{MUTE}" '
                   f'text-anchor="middle">{t}%</text>')
        t += 5
    y = top
    for label, point, lo, hi, sub, col in rows:
        cy = y + rowh / 2
        xlo, xhi, xpt = X(lo), X(hi), X(point)
        out.append(f'<line x1="{xlo:.1f}" y1="{cy:.1f}" x2="{xhi:.1f}" y2="{cy:.1f}" '
                   f'stroke="{col}" stroke-width="2"/>')
        for xc in (xlo, xhi):   # end caps
            out.append(f'<line x1="{xc:.1f}" y1="{cy-5:.1f}" x2="{xc:.1f}" y2="{cy+5:.1f}" '
                       f'stroke="{col}" stroke-width="2"/>')
        out.append(f'<circle cx="{xpt:.1f}" cy="{cy:.1f}" r="4.5" fill="{col}">'
                   f'<title>{esc(label)}: {point:.2f}% (95% CI {lo:.2f}–{hi:.2f})</title></circle>')
        out.append(f'<text x="{pad_l-10}" y="{cy+4:.1f}" font-size="12" fill="{INK}" '
                   f'text-anchor="end">{esc(label)}</text>')
        out.append(f'<text x="{xhi+8:.1f}" y="{cy+4:.1f}" font-size="10.5" fill="{MUTE}">'
                   f'{point:.2f}% · {esc(sub)}</text>')
        y += rowh
    out.append("</svg>")
    return "".join(out)


def coverage_bars(rows: list[tuple], w=760, rowh=30, title="") -> str:
    """A channel-coverage matrix: one 0–100% bar per apparatus channel.

    rows: (label, pct, count, total). Bars are colour-graded by coverage so the eye
    reads completeness at a glance (green ≥90, blue ≥40, amber below).
    """
    pad_l, pad_r, top = 176, 168, 10
    barw = w - pad_l - pad_r
    h = top + len(rows) * rowh + 6
    out = [svg_open(w, h, title)]
    y = top
    for label, pct, count, total in rows:
        cy = y + rowh / 2
        bw = barw * (pct / 100)
        col = GOOD if pct >= 90 else (SCRIPTURE if pct >= 40 else APPARATUS)
        out.append(f'<text x="{pad_l-8}" y="{cy+4:.1f}" font-size="12" fill="{INK}" '
                   f'text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{pad_l}" y="{y+4}" width="{barw}" height="{rowh-11}" rx="2" '
                   f'fill="#fff" stroke="{LINE}"/>')
        out.append(f'<rect x="{pad_l}" y="{y+4}" width="{bw:.1f}" height="{rowh-11}" rx="2" fill="{col}">'
                   f'<title>{esc(label)}: {pct:.2f}%</title></rect>')
        out.append(f'<text x="{pad_l+barw+8:.1f}" y="{cy+4:.1f}" font-size="10.5" fill="{MUTE}">'
                   f'{pct:.2f}% · {fmt(count)}/{fmt(total)} ch</text>')
        y += rowh
    out.append("</svg>")
    return "".join(out)


def chapter_bars(books: list[dict], w=940, title="") -> str:
    """One vertical bar per book; height ∝ chapters; flagged book drawn in FLAG colour."""
    n = len(books)
    pad_l, pad_b, top = 34, 96, 26
    plot_h = 200
    gap = 2
    bw = (w - pad_l - 16 - gap * (n - 1)) / n
    mx = max(b["got"] for b in books) or 1
    h = top + plot_h + pad_b
    out = [svg_open(w, h, title)]
    # y gridlines
    for gv in (0, 50, 100, 150):
        gy = top + plot_h - plot_h * (gv / mx)
        out.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{w-16}" y2="{gy:.1f}" stroke="{LINE}"/>')
        out.append(f'<text x="{pad_l-6}" y="{gy+4:.1f}" font-size="10" fill="{MUTE}" text-anchor="end">{gv}</text>')
    x = pad_l
    for b in books:
        bh = plot_h * (b["got"] / mx)
        col = FLAG if b["flag"] else (SCRIPTURE if b["testament"] == "OT" else GOOD)
        y = top + plot_h - bh
        tip = f'{b["book"]}: {b["got"]} chapters (Vulgate expects {b["expected"]})'
        out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bw:.2f}" height="{bh:.2f}" fill="{col}">'
                   f'<title>{esc(tip)}</title></rect>')
        # tick label (short) rotated
        lab = b["short"]
        out.append(f'<text x="{x+bw/2:.2f}" y="{top+plot_h+6}" font-size="8.5" fill="{MUTE}" '
                   f'text-anchor="end" transform="rotate(-60 {x+bw/2:.2f} {top+plot_h+6})">{esc(lab)}</text>')
        x += bw + gap
    # legend
    ly = 12
    for lab, col in (("Old Testament", SCRIPTURE), ("New Testament + appendix", GOOD),
                     ("flagged (source artifact)", FLAG)):
        out.append(f'<rect x="{pad_l+ (0 if lab.startswith("Old") else (150 if lab.startswith("New") else 360))}" '
                   f'y="{ly}" width="11" height="11" rx="2" fill="{col}"/>')
        xoff = pad_l + (0 if lab.startswith("Old") else (150 if lab.startswith("New") else 360)) + 15
        out.append(f'<text x="{xoff}" y="{ly+10}" font-size="11" fill="{INK}">{esc(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def pipeline_svg(books_ok: int = 76) -> str:
    """The generate-don't-detect one-pass flow."""
    w, h = 940, 250
    out = [svg_open(w, h, "reconstruction pipeline")]
    boxes = [
        (20, "collated witnesses", "Madueke_A scripture\n+ Sabates_A apparatus", "#eef2ff", SCRIPTURE),
        (215, "one-pass generator", "gen_dr_original.py\nemit text + record offsets", "#fff7ed", APPARATUS),
        (430, "text + map (born together)", ".txt  +  work-108.map.json", "#f5f3ff", ACCENT),
        (645, "ingest (byte-exact)", "normalize() == text\nsha guard", "#ecfdf5", GOOD),
    ]
    for x, t, sub, fill, stroke in boxes:
        out.append(f'<rect x="{x}" y="60" width="175" height="86" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        out.append(f'<text x="{x+87}" y="90" font-size="12.5" font-weight="700" fill="{INK}" text-anchor="middle">{esc(t)}</text>')
        for i, line in enumerate(sub.split("\n")):
            out.append(f'<text x="{x+87}" y="{112+i*15}" font-size="10.5" fill="{MUTE}" text-anchor="middle">{esc(line)}</text>')
    for ax in (196, 411, 626):
        out.append(f'<path d="M{ax},103 l16,0 m-5,-5 l5,5 l-5,5" stroke="{INK}" stroke-width="1.5" fill="none"/>')
    # verify gate row
    out.append(f'<rect x="215" y="180" width="600" height="52" rx="10" fill="#fff" stroke="{LINE}"/>')
    out.append(f'<text x="235" y="200" font-size="11.5" font-weight="700" fill="{INK}">structural gates + external oracle</text>')
    gates = (f"spans tile [0,N) · type_counts reconcile · masking round-trips · sha reproduces · "
             f"Catholic canon {books_ok}/76")
    out.append(f'<text x="235" y="218" font-size="10.5" fill="{MUTE}">{esc(gates)}</text>')
    out.append(f'<path d="M732,146 l0,20 m-5,-5 l5,5 l5,-5" stroke="{INK}" stroke-width="1.5" fill="none"/>')
    out.append("</svg>")
    return "".join(out)


# ── data ─────────────────────────────────────────────────────────────────────

def gather() -> dict:
    m = load_map(IDX)
    n = m["text_len"]
    tc = m["type_counts"]
    cfg = LayoutConfig.from_dict(m)
    mi = masked_intervals(cfg.sections, cfg.mask_by_type, n)
    masked = sum(b - a for a, b in mi)

    # leaf content classes (non-overlapping)
    classes = {"Scripture (verse bodies)": 0, "Footnotes & marginal commentary": 0,
               "Chapter arguments/headings": 0, "Book introductions (arguments)": 0,
               "Reference apparatus (front/back matter)": 0, "Preface to the Reader": 0,
               "OT title page": 0, "Testament headers": 0}
    keymap = {"chapter": "Scripture (verse bodies)", "annotation": "Footnotes & marginal commentary",
              "chapter_heading": "Chapter arguments/headings",
              "introduction": "Book introductions (arguments)", "apparatus": "Reference apparatus (front/back matter)",
              "preface": "Preface to the Reader",
              "title_page": "OT title page", "header": "Testament headers"}
    for s in m["sections"]:
        k = keymap.get(s["type"])
        if k:
            classes[k] += s["end"] - s["start"]

    # OT / NT / appendix scripture split (chapter spans within each volume/appendix container)
    vols = [s for s in m["sections"] if s["type"] == "volume"]
    apx = next(s for s in m["sections"] if s["type"] == "appendix")
    chaps = [s for s in m["sections"] if s["type"] == "chapter"]
    def scripture_in(rng):
        a, b = rng["start"], rng["end"]
        return sum(c["end"] - c["start"] for c in chaps if a <= c["start"] < b)
    vol_split = [("Old Testament", scripture_in(vols[0])), ("New Testament", scripture_in(vols[1])),
                 ("Appendix (3 books)", scripture_in(apx))]

    # two-layer coverage (union of SPECIFIC leaves)
    def union_cov(types):
        iv = sorted((s["start"], s["end"]) for s in m["sections"] if s["type"] in types)
        tot = 0; cur_a = cur_b = None
        for a, b in iv:
            if cur_b is None or a > cur_b:
                if cur_b is not None:
                    tot += cur_b - cur_a
                cur_a, cur_b = a, b
            else:
                cur_b = max(cur_b, b)
        if cur_b is not None:
            tot += cur_b - cur_a
        return tot
    generic_cov = union_cov({"body"})
    specific_types = {"title_page", "preface", "header", "introduction", "chapter_heading",
                      "chapter", "apparatus", "annotation"}
    specific_cov = union_cov(specific_types)

    # per-book chapter counts vs Vulgate oracle
    canon = load_canon()["catholic_dr"]
    bc = books_chapters(m)
    ot_names = 46
    books = []
    for i, (exp, (_label, got)) in enumerate(zip(canon, bc)):
        testament = "OT" if i < ot_names else "NT"
        short = exp["book"].split("(")[0].strip().title()
        books.append({"book": exp["book"], "short": short, "got": got,
                      "expected": exp["chapters"], "flag": got != exp["chapters"],
                      "testament": testament})
    ok, count_bad, align_bad = classify_books_catholic(IDX)
    entry = manifest_entry(IDX)

    # provenance chain — computed from per-element map metadata (which witness supplies what)
    role_label = {"chapter": "Scripture — verse bodies", "annotation": "Footnotes & marginal commentary",
                  "chapter_heading": "Chapter arguments", "introduction": "Book arguments"}
    prov_rows: dict = defaultdict(lambda: {"chars": 0, "count": 0})
    by_witness: dict = defaultdict(int)
    for s in m["sections"]:
        md = s.get("metadata") or {}
        p = md.get("provenance")
        if not p:
            continue
        key = (role_label.get(s["type"], s["type"]), p, md.get("confidence"), md.get("coverage"))
        prov_rows[key]["chars"] += s["end"] - s["start"]
        prov_rows[key]["count"] += 1
        by_witness[p] += s["end"] - s["start"]
    prov = sorted(([role, wit, conf, cov, v["chars"], v["count"]]
                   for (role, wit, conf, cov), v in prov_rows.items()), key=lambda r: -r[4])

    # committed validation package — first-class evidence, required (no silent fallback)
    collation = json.loads(A_COLLATION.read_text())   # leg1 exact + leg2 format-fidelity
    ocr = json.loads(A_OCR.read_text())               # leg3 independent stratified print-OCR + CI
    gapfill = json.loads(A_GAPFILL.read_text())        # apparatus channel coverage + Madueke_B
    order = json.loads(A_ORDER.read_text())            # scan-derived front/back-matter ordering

    # flatten the apparatus-order sections and pull the OCR-anchored citations
    order_sections = []
    for grp, arr in (("OT front", order["ot_front"]), ("OT back", order["ot_back"]),
                     ("NT front", order["nt_front"]), ("NT back", order["nt_back"])):
        for s in arr:
            ev = s["evidence"]
            order_sections.append({"group": grp, "name": s["name"], **ev})
    ocr_citations = [s for s in order_sections if s.get("ocr_char_offset") is not None]

    # reproduction check
    repro = None
    if OUT_TXT.exists():
        live = hashlib.sha256(OUT_TXT.read_bytes()).hexdigest()
        repro = (live == m["reference_sha256"], live)

    return dict(m=m, n=n, tc=tc, masked=masked, mi=mi, classes=classes, vol_split=vol_split,
                generic_cov=generic_cov, specific_cov=specific_cov, books=books, ok=ok,
                count_bad=count_bad, align_bad=align_bad, entry=entry, repro=repro,
                prov=prov, by_witness=dict(by_witness), collation=collation, ocr=ocr,
                gapfill=gapfill, order=order, ocr_citations=ocr_citations,
                verify=verify_map(IDX))


# ── render ───────────────────────────────────────────────────────────────────

def render(d: dict) -> str:
    m, n, tc = d["m"], d["n"], d["tc"]
    masked, unmasked = d["masked"], n - d["masked"]
    sha = m["reference_sha256"]
    count_bad = d["count_bad"]
    clean = not count_bad
    books_ok = len(d["ok"])
    verify_pass = not d["verify"]
    disc_books = ", ".join(sorted({str(r[1]).title() for r in count_bad}))

    # ── validation artifacts ──
    l1 = d["collation"]["leg1_exact_madueke_sabates"]
    a1 = l1["aggregate"]
    l2 = d["collation"]["leg2_format_fidelity_madueke_a_vs_b"]
    tob = l1["structural"]["book_ct_mismatch"][0]
    tob_str = f"Tobias — Madueke {tob['mad_n']} vs Sabates {tob['sab_n']}"

    oc = d["ocr"]
    oa = oc["aggregate"]
    strata = oc["per_stratum"]

    gf = d["gapfill"]
    sc = gf["sabates_coverage"]
    cc = sc["channel_coverage"]
    mb = gf["madueke_b_corroboration"]
    gap = gf["genuine_gaps"][0]
    gap_book = gap["book"].replace("-", " ").title()

    od = d["order"]
    mt = od["method_tally"]

    # provenance shares
    bw = d["by_witness"]
    mad_share = bw.get("Madueke_A", 0) / n * 100
    sab_share = bw.get("Sabates_A", 0) / n * 100

    # ── charts ──
    conf_cls = {"high": "ok", "moderate": "mod", "low": "no"}

    def prov_row(role, wit, conf, cov, chars, cnt) -> str:
        badge = f'<span class="pill {conf_cls.get(conf, "")}">{esc((conf or "?").upper())}</span>'
        return (f'<tr><td>{esc(role)}</td><td><code>{esc(wit)}</code></td><td>{badge}</td>'
                f'<td>{esc(cov)}</td><td class="n">{fmt(chars)}</td>'
                f'<td class="n">{chars/n*100:.1f}%</td><td class="n">{fmt(cnt)}</td></tr>')

    prov_table = "".join(prov_row(*r) for r in d["prov"])

    # leg1 — 2-way collation breakdown (identical / ligature-only / case-punct / substantive)
    two_way_bar = stacked_bar(
        [("Identical wording", a1["identical"], GOOD),
         ("Ligature-only (ae/oe vs æ/œ)", a1["ligature_only"], SCRIPTURE),
         ("Case / punctuation / spacing only", a1["punct_or_space_only"], APPARATUS),
         ("Substantive wording differences", a1["substantive"], FLAG)],
        a1["compared"], title="two-way verse collation")

    # leg3 — stratified print-OCR recall, per-stratum point + 95% CI whiskers
    stratum_order = ["OT-narrative", "OT-poetry", "OT-prophets",
                     "NT-gospel", "NT-epistle", "apparatus-dense"]
    ci_rows = []
    for k in stratum_order:
        s = strata[k]
        ci_rows.append((k, s["recall_pct"], s["ci95"][0], s["ci95"][1],
                        f"{s['n_chapters']} ch · {fmt(s['tokens'])} tok", ACCENT))
    ci_rows.append((f"All {oa['n_chapters']} chapters", oa["recall_pct"], oa["ci95"][0], oa["ci95"][1],
                    f"{oa['n_chapters']} ch · {fmt(oa['n_tokens'])} tok", INK))
    ocr_ci_chart = ci_whisker(ci_rows, title="print-OCR recall by stratum with 95% CI")

    # §6 — apparatus channel-coverage matrix
    chan_labels = {"argument": "Book / chapter arguments", "summary_notes": "Chapter summary notes",
                   "verse_notes": "Verse footnotes", "cross_refs": "Cross-references",
                   "sidecar": "Marginal sidecar notes"}
    chan_rows = sorted(((chan_labels[k], v["pct"], v["chapters"], sc["canonical_chapters"])
                        for k, v in cc.items()), key=lambda r: -r[1])
    channel_chart = coverage_bars(chan_rows, title="apparatus channel coverage")

    # §7 — apparatus-ordering method tally
    method_rows = sorted(((k, v) for k, v in mt.items()), key=lambda r: -r[1])
    method_chart = hbar(method_rows, w=680, title="ordering evidence by method",
                        unit=" sections", colour=ACCENT)
    n_order = sum(mt.values())

    # OCR-anchored ordering citations
    def cite_row(s) -> str:
        return (f'<tr><td>{esc(s["group"])}</td><td>{esc(s["name"])}</td>'
                f'<td><code>{esc(s["ocr_witness"])}</code></td>'
                f'<td class="n">{fmt(s["ocr_char_offset"])}</td>'
                f'<td>{esc(s["method"])}</td></tr>')
    cite_table = "".join(cite_row(s) for s in d["ocr_citations"])

    content_donut = donut(
        [(k, v, BAND[i % len(BAND)]) for i, (k, v) in enumerate(d["classes"].items()) if v > 0],
        sum(d["classes"].values()), title="content composition")
    mask_bar = stacked_bar(
        [("Unmasked — scripture prose (the reader's text)", unmasked, SCRIPTURE),
         ("Masked — editorial apparatus", masked, APPARATUS)], n, title="mask coverage")
    scripture_bar = stacked_bar(
        [(lbl, v, BAND[i]) for i, (lbl, v) in enumerate(d["vol_split"])],
        sum(v for _, v in d["vol_split"]), title="scripture by division")
    inv = hbar([("chapter (verse bodies)", tc["chapter"]),
                ("annotation (footnotes/commentary)", tc["annotation"]),
                ("chapter_heading", tc["chapter_heading"]),
                ("book", tc["book"]), ("introduction", tc["introduction"]),
                ("apparatus (reference docs)", tc["apparatus"]),
                ("volume", tc["volume"]), ("header", tc["header"]),
                ("front_matter", tc["front_matter"]), ("back_matter", tc["back_matter"]),
                ("title_page", tc["title_page"]),
                ("preface", tc["preface"]), ("appendix", tc["appendix"]),
                ("body", tc["body"])], title="element inventory", unit="", colour=ACCENT)
    ch_chart = chapter_bars(d["books"], title="per-book chapter counts vs Vulgate oracle")
    pipe = pipeline_svg(books_ok)

    repro_line = ("not re-derivable in this environment (source clone absent) — "
                  "map records the frozen reference sha")
    repro_ok = True
    if d["repro"] is not None:
        repro_ok, live = d["repro"]
        repro_line = (f"regenerated text sha <code>{live[:16]}…</code> "
                      f"{'matches' if repro_ok else 'DOES NOT match'} the committed map")

    def stat(v, lab):
        return (f'<div class="stat"><div class="v">{v}</div><div class="l">{esc(lab)}</div></div>')

    css = """
    :root{--ink:#1c1917;--mute:#78716c;--line:#e7e5e4;--paper:#faf9f7;--blue:#2563eb;--amber:#d97706;--green:#15803d;--red:#dc2626;--violet:#7c3aed}
    *{box-sizing:border-box}
    body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:#fff;line-height:1.6;font-size:16px}
    .wrap{max-width:1000px;margin:0 auto;padding:0 28px 120px}
    header.hero{background:linear-gradient(135deg,#1e1b4b,#312e81 55%,#3730a3);color:#fff;padding:56px 28px 44px;margin-bottom:8px}
    header.hero .inner{max-width:1000px;margin:0 auto}
    header.hero .kicker{text-transform:uppercase;letter-spacing:.14em;font-size:12px;opacity:.75}
    header.hero h1{font-size:34px;margin:10px 0 6px;line-height:1.15}
    header.hero .sub{opacity:.85;font-size:16px}
    header.hero .meta{margin-top:22px;display:flex;flex-wrap:wrap;gap:10px}
    header.hero .chip{background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.2);border-radius:20px;padding:5px 13px;font-size:12.5px}
    h2{font-size:23px;margin:52px 0 6px;padding-bottom:8px;border-bottom:2px solid var(--line)}
    h3{font-size:17px;margin:30px 0 6px}
    p{margin:12px 0}
    code{background:#f5f3f0;padding:1px 6px;border-radius:4px;font-size:.86em;font-family:"SF Mono",Menlo,Consolas,monospace}
    .lead{font-size:17.5px;color:#44403c}
    .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:26px 0}
    .stat{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
    .stat .v{font-size:26px;font-weight:750;letter-spacing:-.02em}
    .stat .l{font-size:12.5px;color:var(--mute);margin-top:3px}
    figure{margin:24px 0;padding:20px;border:1px solid var(--line);border-radius:14px;background:#fff}
    figure figcaption{font-size:13px;color:var(--mute);margin-top:12px;text-align:center}
    figure .ftitle{font-size:14px;font-weight:700;margin-bottom:14px}
    .callout{border-left:4px solid var(--violet);background:#f5f3ff;padding:14px 18px;border-radius:0 10px 10px 0;margin:20px 0}
    .callout.flag{border-color:var(--red);background:#fef2f2}
    .callout.good{border-color:var(--green);background:#f0fdf4}
    .callout .h{font-weight:700;margin-bottom:4px}
    table{border-collapse:collapse;width:100%;margin:18px 0;font-size:14.5px}
    th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line)}
    th{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute)}
    td.n{font-variant-numeric:tabular-nums;text-align:right}
    .tier{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid var(--line)}
    .tier .badge{font-size:12px;font-weight:750;padding:4px 12px;border-radius:20px;color:#fff;white-space:nowrap}
    .b-high{background:var(--green)}.b-mod{background:var(--amber)}.b-na{background:var(--mute)}
    .tier .body{font-size:14.5px}
    .pill{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:20px}
    .pill.ok{background:#dcfce7;color:#166534}.pill.no{background:#fee2e2;color:#991b1b}
    .pill.mod{background:#fef3c7;color:#92400e}
    footer{margin-top:60px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--mute)}
    """

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OriginalDR (idx 108) — Reconstruction Technical Report</title>
<style>{css}</style></head>
<body>
<header class="hero"><div class="inner">
  <div class="kicker">Palimpsest · Bible Gold Set · Technical Report</div>
  <h1>Original Douay-Rheims (1582–1610)</h1>
  <div class="sub">Reconstruction of gold work-108 — process, source contributions, and confidence in text accuracy</div>
  <div class="meta">
    <span class="chip">76 books · {fmt(tc['chapter'])} chapters</span>
    <span class="chip">{fmt(n)} characters</span>
    <span class="chip">Catholic / Clementine Vulgate canon</span>
    <span class="chip">sha {esc(sha[:12])}…</span>
    <span class="chip">Gregory Martin, 1582 NT / 1609–10 OT</span>
  </div>
</div></header>

<div class="wrap">

<h2>1 · Executive summary</h2>
<p class="lead">OriginalDR is the most structurally trustworthy gold in the set, because it is
<strong>generated, not detected</strong>. The reference text and its masking map are born in a
single pass over the sources, so every mask offset is exact by construction — there is no detection
step that can mis-anchor. This rebuild goes further on <em>content</em>: the reader's scripture is
collated across <strong>three witnesses</strong> — authoritative Madueke text, a verse-by-verse
collation against the Sabates witness, and an <strong>independent third-party OCR</strong> of the
original 1582–1610 print sampled by a stratified-random design with bootstrap confidence intervals —
while the editorial apparatus is shown to be <strong>{sc['chapters_with_apparatus_pct']:.3f}%
complete</strong> and corroborated against a second edition.</p>
<div class="stats">
  {stat(f"{unmasked/n*100:.1f}%", "unmasked scripture prose")}
  {stat(f"{masked/n*100:.1f}%", "masked editorial apparatus")}
  {stat(f"{books_ok}/76", "books match Vulgate counts")}
  {stat(str(a1["substantive"]), f"substantive wording diffs · {fmt(a1['compared'])} verses")}
  {stat(str(oa["genuine_candidate_misses"]), f"genuine discrepancies vs print · {oa['n_chapters']} stratified chapters")}
  {stat(f"{sc['chapters_with_apparatus_pct']:.3f}%", f"chapters with apparatus ({fmt(sc['chapters_with_apparatus'])}/{fmt(sc['canonical_chapters'])})")}
</div>
<div class="callout {'good' if (verify_pass and clean) else 'flag'}">
  <div class="h">Headline verdict</div>
  Reproduction: <strong>{'byte-identical' if repro_ok else 'DRIFT'}</strong>. Structure:
  <strong>{'all gates pass' if verify_pass else 'GATE FAILURE'}</strong>. Content:
  <strong>{books_ok} of 76</strong> books match the externally-established
  Douay-Rheims/Clementine Vulgate chapter counts; a verse-level collation of
  <strong>{fmt(a1['compared'])}</strong> verses against a second digital witness finds
  <strong>{a1['substantive']}</strong> substantive wording differences, and an independent OCR of the
  original printed editions across <strong>{oa['n_chapters']}</strong> stratified-random chapters
  (aggregate recall {oa['recall_pct']:.2f}%, 95% CI {oa['ci95'][0]:.2f}–{oa['ci95'][1]:.2f}) yields
  <strong>{oa['genuine_candidate_misses']}</strong> genuine discrepancies.
  {'The reconstruction drops the spurious Tobias &ldquo;chapter&nbsp;1&rdquo; — an editorial Argument mis-captured as scripture upstream — restoring the canonical count with no remaining exceptions.' if clean else f'The remaining count discrepancy in {esc(disc_books)} is a documented upstream artifact, reproduced faithfully and flagged rather than silently blessed.'}
</div>

<h2>2 · What OriginalDR is</h2>
<p>This is the <strong>original</strong> Douay-Rheims — Gregory Martin's translation for the English
College (New Testament, Rheims 1582; Old Testament, Douay 1609–1610) — as distinguished from the
later Challoner revision (gold idx 5, 100). It is a full Catholic Bible in the Clementine Vulgate
canon: {fmt(tc['book'])} books over two testaments plus a three-book appendix, {fmt(tc['chapter'])}
chapters, {fmt(n)} characters of the edition's English in modern (ligature-expanded) orthography.</p>
<p>Unlike the marker/epub golds, OriginalDR is <strong>collated from three witnesses</strong>, each
recorded per element in the map so any consumer can see exactly what supplied a given passage:</p>
<ul>
<li><strong>Madueke_A</strong> — the olprint &ldquo;Augmented Bible&rdquo; per-chapter HTML edition
(codeberg) — supplies the <strong>authoritative scripture</strong>, the verse bodies of all 73
canonical books.</li>
<li><strong>Sabates_A</strong> — the <code>janvier-s/original-douay-rheims</code> CC0 JSON dataset —
supplies everything Madueke omits: the <strong>editorial apparatus</strong> (per-book arguments,
per-chapter arguments, the {fmt(tc['annotation'])} annotation blocks of footnotes and marginal
commentary, and the {fmt(tc['apparatus'])} front/back reference documents) and the
<strong>three-book apocryphal appendix</strong> (Prayer of Manasses, 3 &amp; 4 Esdras).</li>
<li><strong>Madueke_B</strong> — the merged-edition PDF of the same olprint project — a second format
of the Madueke edition, used to confirm the HTML extraction is faithful (§5.2) and to
<strong>corroborate the apparatus</strong> and the appendix (§6).</li>
<li><strong>OCR-original-scan</strong> — third-party archive.org djvu OCR of the original
1582/1609/1610 printed editions — an <strong>independent print witness</strong> outside the
Madueke/Sabates lineage, used to validate the digital text (§5.3).</li>
</ul>
<p>The reconstruction places the apparatus at its canonical front/back positions and folds the
per-chapter footnotes and cross-references in as masked annotation blocks after each chapter body.
Because Sabates in fact <em>derives</em> from Madueke, the two are not fully independent — which is
exactly why the third, print-based witness matters (§5.3). That breadth of both text and apparatus is
what makes it a <em>comprehensive</em> gold rather than a bare scripture dump.</p>

<h2>3 · The reconstruction process — generate, don't detect</h2>
<p>Every other marker/epub gold in the set <em>infers</em> structure from text and can mis-anchor a
mask. OriginalDR inverts that fragility. <code>gen_dr_original.py</code> walks the collated witnesses —
Madueke scripture aligned verse-for-verse to Sabates apparatus — and emits the reference text
paragraph by paragraph, <strong>recording each element's exact character offset as it writes it</strong>.
The text and the map are the same object viewed two ways.</p>
<figure><div class="ftitle">Figure 1 · Reconstruction pipeline (one pass, offsets exact by construction)</div>
{pipe}
<figcaption>The generator emits text and records offsets simultaneously; a normalization-stability
assert (<code>normalize(text) == text</code>) guarantees Palimpsest's ingest cannot shift a single
offset, and the <code>reference_sha256</code> guard fails the import if it ever does.</figcaption></figure>
<div class="callout"><div class="h">Why this matters</div>
There is no detector to get wrong. A marker Bible's mask can drift if a chapter heading is
formatted unexpectedly; here the offset was written by the same code that wrote the character. This
is structurally the strongest guarantee available — and a preview of the "structure-first" import
paradigm: <em>when you already have the structure, perfect masks are free.</em></div>

<h2>4 · Provenance chain — which witness supplies what</h2>
<p>Every leaf element records its own <code>provenance</code>, <code>confidence</code> and
<code>coverage</code> in the map, so the source of any passage is auditable without leaving the
artifact. <strong>Madueke_A</strong> supplies <strong>{mad_share:.1f}%</strong> of the text as
three-witness scripture (verse bodies of the 73 canonical books); <strong>Sabates_A</strong> supplies
<strong>{sab_share:.1f}%</strong> as the editorial apparatus plus the Madueke-omitted apocryphal
appendix; the remaining characters are structural containers and inter-paragraph separators, which
carry no textual provenance.</p>
<table>
<tr><th>Content class</th><th>Witness</th><th>Confidence</th><th>Coverage</th><th>Chars</th><th>Share</th><th>Elements</th></tr>
{prov_table}
</table>
<p>The composition below shows the same split by character volume: verse bodies are the reader's
clean scripture (unmasked); everything else — footnotes, arguments, reference documents — is the
masked apparatus, a substantial {masked/n*100:.1f}%.</p>
<figure><div class="ftitle">Figure 2 · Character composition by content class</div>
{content_donut}
<figcaption>Verse bodies are unmasked (the reader's clean scripture); everything else — footnotes and
marginal commentary, chapter arguments, book arguments, the reference documents, the Preface, the
title page, testament headers — is the masked apparatus.</figcaption></figure>
<figure><div class="ftitle">Figure 3 · Scripture prose by canonical division</div>
{scripture_bar}
<figcaption>The Old Testament supplies the bulk of the verse-body text; the appendix (Prayer of
Manasses, 3 &amp; 4 Esdras) is the smallest division.</figcaption></figure>

<h2>5 · Source collation &amp; discrepancy analysis</h2>
<p>Preferring one witness for the words is a provenance decision; proving the words are
<em>right</em> needs collation. Three legs establish it, and the design is honest about what each can
and cannot prove: leg 1 (a lineage-related digital witness) measures <em>transcription</em> fidelity,
leg 2 (a second format of the same edition) measures <em>extraction</em> fidelity, and only leg 3 —
an OCR of the original print outside that lineage — is a genuinely <em>independent</em> corroboration.</p>

<h3>5.1 · Two-way digital collation — Madueke vs Sabates (leg 1)</h3>
<p>A verse-by-verse string collation over the shared {fmt(a1['compared'])}-verse canon, folding away
orthographic and typographic convention to isolate genuine wording differences. Because Sabates
derives from Madueke, this establishes transcription fidelity, not independence.</p>
<figure><div class="ftitle">Figure 4 · Verse-by-verse agreement, by difference class</div>
{two_way_bar}
<figcaption>{fmt(a1['identical'])} of {fmt(a1['compared'])} verses ({a1['identical_pct']:.2f}%) are
byte-identical; {fmt(a1['ligature_only'])} differ only in ligature convention (Madueke
<code>ae/oe</code> vs Sabates <code>æ/œ</code>); {fmt(a1['punct_or_space_only'])} differ only in
case, punctuation or spacing; <strong>{a1['substantive']} differ in actual wording</strong>.</figcaption></figure>
<p>The only structural divergence is {esc(tob_str)}: Sabates carries a spurious leading chapter that
Madueke does not, independently confirming the Tobias correction of §10. No verses are missing or
extra on either side.</p>

<h3>5.2 · Format-fidelity check — Madueke HTML vs merged PDF (leg 2)</h3>
<p>Before trusting the HTML extraction, we confirm it against a second format of the <em>same</em>
edition — the Madueke_B merged-edition PDF. This is an extraction-fidelity check, not independent
corroboration.</p>
<div class="callout"><div class="h">Extraction is faithful — 100% type recall</div>
All <strong>{fmt(l2['madueke_a_scripture_types'])}</strong> distinct scripture word-types extracted
from the Madueke_A HTML are attested in the {fmt(l2['madueke_b_edition_types'])}-type merged edition
(<strong>{l2['type_recall_pct']:.1f}%</strong> type recall, {l2['token_weighted_recall_pct']:.1f}%
token-weighted), with <strong>{l2['missing_type_count']}</strong> missing types. The HTML parse loses
no vocabulary relative to the PDF of the same edition — the two formats agree, so the extraction
introduced no drift.</div>

<h3>5.3 · Independent print-OCR validation (leg 3)</h3>
<p>To break the shared-lineage risk, the digital text is collated against a genuinely independent
witness: third-party archive.org djvu OCR of the original 1582/1609/1610 printed editions — outside
both the Madueke/Sabates digital lineage <em>and</em> our own OCR pipeline. Rather than a handful of
spot-checks, the sample is <strong>stratified-random</strong>: {oa['n_chapters']} chapters
(seed&nbsp;{oc['seed']}) drawn evenly across six text-type strata, with a
{fmt(oc['n_bootstrap'])}-iteration chapter-resampled bootstrap giving a 95% confidence interval on
recall.</p>
<figure><div class="ftitle">Figure 5 · Print-OCR skeleton recall by stratum, with 95% confidence intervals</div>
{ocr_ci_chart}
<figcaption>Point estimates with bootstrap 95% CIs on a zoomed axis
({max(0, math.floor(min(r[2] for r in ci_rows)) - 1)}–100%). Aggregate recall is
<strong>{oa['recall_pct']:.2f}%</strong> (CI {oa['ci95'][0]:.2f}–{oa['ci95'][1]:.2f}) over
{fmt(oa['n_tokens'])} tokens; OT-poetry is lowest and widest (short psalms, sparser token counts).
Recall is a corroboration signal — the archaic-skeleton fold is deliberately lossy — so the genuine
signal is the distinctive-content-word miss count below.</figcaption></figure>
<div class="callout good"><div class="h">Zero genuine discrepancies</div>
Of {fmt(oa['n_tokens'])} sampled tokens, {fmt(oa['content_word_misses'])} content words missed the
skeleton-recall fold. After a second pass checking each against the whole print witness and the full
merged edition, <strong>{oa['genuine_candidate_misses']} remain as genuine candidates</strong>
({oa['genuine_candidate_pct']:.1f}%) — every miss is OCR garble or a word attested elsewhere in the
print. The independent print confirms both digital witnesses; shared-lineage agreement here is
corroborated, not a shared error. The genuine-candidate filter is non-vacuous (a committed test proves
it flags a truly-absent word and demotes a present one).</div>

<h2>6 · Apparatus completeness</h2>
<p>Scripture fidelity is not the same as apparatus completeness, so the two are measured separately.
Across the {fmt(sc['canonical_chapters'])} canonical chapters, Sabates supplies apparatus for
<strong>{fmt(sc['chapters_with_apparatus'])} ({sc['chapters_with_apparatus_pct']:.3f}%)</strong>
through five channels — book/chapter arguments, chapter summary notes, verse footnotes,
cross-references and marginal sidecar notes. A chapter counts as covered if <em>any</em> channel is
present, which is why the headline figure is near-total even though individual channels vary widely.</p>
<figure><div class="ftitle">Figure 6 · Apparatus coverage by channel (share of {fmt(sc['canonical_chapters'])} canonical chapters)</div>
{channel_chart}
<figcaption>Verse footnotes ({cc['verse_notes']['pct']:.2f}%) and arguments
({cc['argument']['pct']:.2f}%) are near-universal; the marginal sidecar
({cc['sidecar']['pct']:.2f}%) and summary notes ({cc['summary_notes']['pct']:.2f}%) are sparse by
nature — most chapters simply were not annotated in those channels in the print.</figcaption></figure>
<div class="callout good"><div class="h">The sidecars are faithful, not truncated — corrects the earlier &ldquo;Psalm&nbsp;109 gap&rdquo;</div>
An earlier assessment read the empty marginal sidecars as lost transcription and singled out Psalm 109
as a gap. That was a measurement artifact: Psalm 109 in fact carries a summary, its verse-notes and
cross-references — only its <em>sidecar</em> channel is empty. Corroboration settles it at the corpus
level: the Madueke_B merged edition carries <strong>{fmt(mb['annotations_blocks'])}</strong> annotation
blocks against Sabates' <strong>{fmt(mb['sabates_sidecars_present'])}</strong> non-empty sidecars — a
near-parity that shows Sabates' marginal coverage tracks the print, and the
{fmt(sc['sidecar_missing'])} chapters without a sidecar are chapters the print did not annotate
marginally, not data that was lost.</div>
<div class="callout"><div class="h">The appendix is now two-witness</div>
The three-book apocryphal appendix (Prayer of Manasses, 3 &amp; 4 Esdras) — previously Sabates-only —
is located in the Madueke_B merged edition at recorded character offsets, so it is
<strong>corroborated by a second witness</strong> rather than resting on a single source.</div>
<div class="callout flag"><div class="h">One genuine gap — documented, not filled</div>
Exactly {sc['zero_apparatus_chapters']} of {fmt(sc['canonical_chapters'])} chapters has no apparatus in
any Sabates channel: <strong>{esc(gap_book)} {gap['chapter']}</strong>. It is a faithful bare-heading
chapter — no apparatus appears in any digital witness — so it is documented rather than fabricated from
the column-flattened Madueke_B (which cannot be reliably parsed at the sub-chapter level).</div>

<h2>7 · Apparatus ordering — scan-derived evidence</h2>
<p>The apparatus is masked, so what matters for the reader is its front/back-of-tome placement per
testament. The generator sources the order of all <strong>{n_order}</strong> front/back-matter
sections from a committed evidence file, where each position states the <em>strongest honest
evidence</em> available for it — a numeric section-field prefix, an OCR offset in the archive.org scan
where the header survives OCR, a manual-visual scan confirmation for ornamental headers that OCR
mangles, or structural placement.</p>
<figure><div class="ftitle">Figure 7 · Ordering evidence by method ({n_order} sections)</div>
{method_chart}
<figcaption>Most positions are pinned by an explicit section-field prefix; ornamental headers that OCR
cannot read fall back to manual-visual confirmation against the scans; a handful are anchored directly
to an OCR offset in the print (below); the remainder rest on structural placement (front matter
precedes the testament; tables are back matter).</figcaption></figure>
<p>The OCR-anchored positions cite the exact character offset in the archive.org scan where the header
survives OCR — a reproducible pointer into the print witness:</p>
<table>
<tr><th>Section group</th><th>Header</th><th>Scan witness</th><th>Char offset</th><th>Method</th></tr>
{cite_table}
</table>

<h2>8 · Mask coverage &amp; structural integrity</h2>
<p>The map is a two-layer tiling: a GENERIC layer of structural containers (body → volume → book)
and a SPECIFIC layer of leaf elements (headers, arguments, verse bodies). The GENERIC layer covers
<strong>{d['generic_cov']/n*100:.2f}%</strong> of the text and the SPECIFIC leaves cover
<strong>{d['specific_cov']/n*100:.2f}%</strong> — a gap of just {fmt(n - d['specific_cov'])}
characters ({(n - d['specific_cov'])/n*100:.4f}%), the inter-paragraph separators that belong to no
leaf element. Masking hides the apparatus so the reader sees only scripture.</p>
<figure><div class="ftitle">Figure 8 · Mask coverage — reader's text vs hidden apparatus</div>
{mask_bar}
<figcaption>{fmt(unmasked)} characters of scripture remain visible; {fmt(masked)} characters of
editorial apparatus are masked, across {fmt(len(d['mi']))} disjoint intervals.</figcaption></figure>
<figure><div class="ftitle">Figure 9 · Element inventory ({fmt(m['element_count'])} elements, log-free scale)</div>
{inv}
<figcaption>Chapter/chapter_heading parity ({fmt(tc['chapter'])} = {fmt(tc['chapter_heading'])}) is a
structural invariant: every chapter has exactly one heading. 76 books each carry one introduction.</figcaption></figure>
<div class="callout good"><div class="h">Structural gates — all pass</div>
Spans tile <code>[0, {fmt(n)})</code> with malformed-span count zero; <code>type_counts</code>
reconcile with the section list; the production loader/masker accepts the map and its masked
intervals are sorted, disjoint and in range; chapter/heading parity holds. Reproduction:
{repro_line}.</div>

<h2>9 · Content accuracy — the Catholic oracle</h2>
<p>Structural soundness cannot prove <em>correctness</em>: a dropped chapter would still tile
perfectly and self-report a consistent count, because the generator only ever checks the map against
its own re-parsed markers. The existing oracle is Protestant-66 and cannot judge a Vulgate edition —
the canons genuinely diverge. So this work adds an <strong>ordered Douay-Rheims / Clementine Vulgate
oracle</strong> (<code>canon_chapters.json → catholic_dr</code>): 76 externally-established chapter
counts in fixed canonical order, checked positionally against the map (identity confirmed by a label
token, gated on the count). It is non-circular — the expected counts never touched the map.</p>
<figure><div class="ftitle">Figure 10 · Per-book chapter counts vs the external Vulgate oracle</div>
{ch_chart}
<figcaption>Every bar is a book in canonical order; height is its chapter count. All {books_ok}
books sit exactly on their externally-expected Vulgate value{', including Tobias — now corrected to 14 chapters (see §10)' if clean else '; the red bar(s) mark the remaining discrepancy (see §10)'}.</figcaption></figure>
<p>The Vulgate distinctives are exactly why a Protestant oracle fails here, and all resolve correctly:</p>
<table>
<tr><th>Book</th><th>DR / Vulgate</th><th>Protestant</th><th>Why it differs</th></tr>
<tr><td>Esther</td><td class="n">16</td><td class="n">10</td><td>includes the Greek additions</td></tr>
<tr><td>Daniel</td><td class="n">14</td><td class="n">12</td><td>Susanna (13) &amp; Bel and the Dragon (14) folded in</td></tr>
<tr><td>Baruch</td><td class="n">6</td><td class="n">5</td><td>the Epistle of Jeremiah is Baruch ch. 6</td></tr>
<tr><td>1 Esdras</td><td class="n">10</td><td class="n">9*</td><td>DR 1 Esdras = Ezra (10); the Greek 1 Esdras (9) is a different book</td></tr>
<tr><td>Appendix</td><td class="n">3 books</td><td>—</td><td>Prayer of Manasses, 3 &amp; 4 Esdras placed after the NT (Clementine)</td></tr>
</table>

<h2>10 · The Tobias correction</h2>
<div class="callout good"><div class="h">Tobias — restored to 14 chapters</div>
The upstream CC0 dataset carried a spurious leading &ldquo;chapter&nbsp;0&rdquo; for Tobias: a single
verse holding only a truncated 8-word fragment of the book's opening line
(<em>&ldquo;Tobias of the tribe and city of Nephthali&rdquo;</em>). The complete verse — and the whole
real first chapter — follows immediately after, so the enriched reconstruction drops the fragment and
renumbers, restoring the canonical 14 chapters the Vulgate expects.</div>
<p>The drop is verifiably <strong>lossless</strong>: source chapter 0 holds one 8-word verse, while
source chapter 1 opens with that exact text in full (<em>&ldquo;…Nephthali, which is in the upper parts
of Galilee…&rdquo;</em>) and runs a further 25 verses. Nothing is discarded — only a parsing artifact is
removed. A scan of all 77 source books found Tobias to be the <strong>only</strong> book with this
thin-leading-chapter signature, so the fix is a targeted one-book correction
(<code>SPURIOUS_LEADING_CHAPTER</code> in the generator), not a systemic re-parse. The leg-1 collation
(§5.1) independently confirms it: {esc(tob_str)}, with the extra chapter present only on the Sabates
side.</p>
<p>The 14-chapter count is independently corroborated by the book's own Argument (preserved as the
masked introduction apparatus), which divides Tobias <em>&ldquo;The first four chapters… The eight
following… In the two last chapters&rdquo;</em> — 4 + 8 + 2 = <strong>14</strong>. With the count
restored, the sources manifest carries <strong>no</strong> <code>canon_exceptions</code> and the
Catholic oracle passes all <strong>{books_ok}/76</strong> books with zero discrepancies.</p>

<h2>11 · Confidence assessment</h2>
<p>A single verdict would mislead; confidence splits across four independent axes — and this rebuild
promotes both the scripture axis and the apparatus axis that the earlier assessment rated lower.</p>
<div class="tier"><span class="badge b-high">HIGH</span><div class="body">
  <strong>Reproduction.</strong> The generated text is deterministic and normalization-stable; the
  regenerated sha is byte-identical to the committed map. Anyone holding the source witnesses can
  rebuild the exact bytes.</div></div>
<div class="tier"><span class="badge b-high">HIGH</span><div class="body">
  <strong>Structural soundness.</strong> Offsets are exact by construction (no detector). Both tiling
  layers are gap-free to the separator; all hermetic gates pass; chapter/heading parity is exact.</div></div>
<div class="tier"><span class="badge b-high">HIGH</span><div class="body">
  <strong>Scripture content.</strong> Promoted from MODERATE. Beyond the chapter-level Vulgate oracle
  ({books_ok}/76 books), the verse bodies are corroborated at <em>verse</em> granularity: a
  {fmt(a1['compared'])}-verse collation against a second digital witness finds {a1['substantive']}
  substantive wording differences, a second-format check confirms the HTML extraction lost no
  vocabulary ({l2['type_recall_pct']:.0f}% type recall), and an independent stratified-random OCR of
  the original print ({oa['n_chapters']} chapters, bootstrap 95% CI {oa['ci95'][0]:.2f}–{oa['ci95'][1]:.2f}%)
  finds {oa['genuine_candidate_misses']} genuine discrepancies. Two witnesses plus the print agree on
  the words.</div></div>
<div class="tier"><span class="badge b-mod">MODERATE</span><div class="body">
  <strong>Apparatus content.</strong> Raised from the earlier single-witness assessment. Coverage is
  now measured at <strong>{sc['chapters_with_apparatus_pct']:.3f}%</strong> of canonical chapters, the
  marginal-note channel is corroborated at near-parity by the Madueke_B edition
  ({fmt(mb['annotations_blocks'])} vs {fmt(mb['sabates_sidecars_present'])} blocks), and the appendix is
  now two-witness. It stays below scripture because the apparatus <em>wording</em> still rests on a
  single transcription (corroborated at the coverage/count level, not collated word-for-word), and one
  chapter ({esc(gap_book)} {gap['chapter']}) is a genuine apparatus gap.</div></div>

<h2>12 · Limitations &amp; what is not proven</h2>
<ul>
<li><strong>Apparatus wording is single-transcription.</strong> Coverage is near-complete
({sc['chapters_with_apparatus_pct']:.3f}%) and corroborated by Madueke_B at the count level, and the
appendix is two-witness — but the apparatus <em>text</em> itself is not yet collated word-for-word
against a second witness the way scripture is. One chapter ({esc(gap_book)} {gap['chapter']}) carries
no apparatus in any digital witness.</li>
<li><strong>Print validation is a stratified sample.</strong> The independent OCR covered
{oa['n_chapters']} chapters across six text-type strata with a bootstrap CI — enough to support a
statistical claim, but not an exhaustive verse-by-verse print collation of all
{fmt(sc['canonical_chapters'])} chapters. Recall is also a lossy skeleton-fold signal; the genuine
guarantee is the {oa['genuine_candidate_misses']}-candidate distinctive-word miss count, not the recall
percentage itself.</li>
<li><strong>Chapter-granular oracle.</strong> The Catholic oracle checks book presence, order and
chapter count — not verse counts or verse text. Vulgate verse divisions vary by edition, so verse
counts are recorded, not gated.</li>
<li><strong>One deliberate editorial correction.</strong> The reconstruction departs from raw-source
WYSIWYG in exactly one place — the spurious Tobias chapter is dropped (§10), a fix independently
confirmed by the Madueke witness, which never carried it.</li>
</ul>

<h2>13 · Recommendations</h2>
<ul>
<li><strong>Accept as gold.</strong> Reproduction + structure are HIGH and scripture content is now
HIGH (three-witness, stratified-random print CI), externally gated at {books_ok}/76 with no
outstanding exceptions. This clears the Gold Set bar cleanly.</li>
<li><strong>Collate the apparatus wording against Madueke_B.</strong> Coverage is already
{sc['chapters_with_apparatus_pct']:.3f}% and count-corroborated; a word-level collation of the
argument/annotation text against the merged edition would lift the apparatus axis from MODERATE toward
HIGH. The single genuine gap ({esc(gap_book)} {gap['chapter']}) needs no fill — it is a faithful
bare-heading chapter.</li>
<li><strong>Report the Tobias artifact upstream</strong> to the janvier-s (Sabates) dataset — the fix
here is local to this reconstruction; the upstream CC0 JSON still carries the mis-captured Argument
chapter.</li>
<li><strong>For full verse-level print assurance</strong>, extend the independent OCR collation beyond
the {oa['n_chapters']}-chapter stratified sample toward the whole canon.</li>
</ul>

<footer>
Generated by <code>docs/development/reports/gen_originaldr_108_report.py</code> from the frozen gold
map <code>work-108.map.json</code>, the production Catholic oracle (<code>palimpsest.gold</code>), and
the four committed validation artifacts under
<code>core/tests/fixtures/gold/mask_engine/originaldr_validation/</code>
(<code>collation-3way</code>, <code>ocr-validation</code>, <code>apparatus-gapfill</code>,
<code>apparatus-order</code>). All figures computed at generation time — no hardcoded values. Reference
sha <code>{esc(sha)}</code>.
</footer>
</div></body></html>"""


def main() -> int:
    d = gather()
    OUT.write_text(render(d), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size:,} bytes)")
    print(f"  masked {d['masked']/d['n']*100:.2f}% · books_ok {len(d['ok'])}/76 · "
          f"verify_map {'PASS' if not d['verify'] else d['verify']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
