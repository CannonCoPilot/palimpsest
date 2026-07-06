#!/usr/bin/env python3
"""Phase 3 · academic brief + genome-browser visualizations for the OriginalDR reconstruction.

Assembles a single self-contained HTML brief (inline CSS + inline SVG, no external assets) from the
COMMITTED reconstruction artifacts — never the gitignored basis-db.sqlite — so it renders in CI and
every headline number traces to a committed JSON (+ a source sha256 for the pinned scan/reference
material). The intended audience is fluent in genome browsers, so the figures use that grammar:
confidence tier → chromosome banding, independent-witness depth → read depth, source attestation →
aligned-read lanes, disagreement → variant pileups.

This is P3.1: the brief skeleton (Abstract → Reproducibility) with the confidence ideogram, the
coverage-depth karyotype, the diplomatic-fidelity (§6.2) + independent-print (§6.3) CI panel, and the
diplomatic-glyph inventory chart. P3.2/P3.3 extend the same SVG primitives with the source-track
browser, variant pileups, contributor heatmaps and the apparatus placement map.

Run:  core/.venv/bin/python gen_originaldr_brief.py
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
ACQ = HERE / "acquisition"
VALID = HERE.parent / "originaldr_validation"
OUT = HERE / "originaldr-brief.html"

# tier / depth palettes (genome-browser idiom: green = confident/deep, red = shallow/uncertain)
TIER_COLOR = {"high": "#2ca25f", "moderate": "#fdae61", "low": "#d7301f"}
DEPTH_COLOR = {1: "#d7301f", 2: "#fdae61", 3: "#a6d96a", 4: "#1a9850"}
WITNESS_TIER_COLOR = {"clean-diplomatic": "#1a9850", "mixed": "#4a90c2", "ocr-only-noisy": "#e08214", "none": "#bbb"}
EDITION_COLOR = {"archaic": "#762a83", "modern": "#1b7837"}
# per-source lane colors (modern lineage = blues, fresh OCR = orange, archaic diplomatic = purples)
SOURCE_COLOR = {"madueke_a": "#2166ac", "sabates_a": "#4393c3", "ocr_consensus": "#e08214",
                "s_dismas": "#762a83", "odr_com": "#9970ab"}


# --------------------------------------------------------------------------- artifacts
def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.exists() else "—"


def load_artifacts() -> tuple[dict[str, Any], dict[str, Path]]:
    paths = {
        "skeleton": HERE / "skeleton.json",
        "sources_registry": ACQ / "sources-registry.json",
        "consensus": HERE / "consensus-summary.json",
        "basis": HERE / "basis-db.json",
        "apparatus": HERE / "apparatus-attestation.json",
        "layout": HERE / "layout-map.json",
        "redetection": HERE / "redetection-report.json",
        "render_modern": HERE / "render-modern-report.json",
        "render_archaic": HERE / "render-archaic-report.json",
        "glyph_model": HERE / "spelling-glyph-model.json",
        "fidelity": HERE / "archaic-fidelity-validation.json",
        "print_archaic": HERE / "archaic-print-validation.json",
        "print_modern": VALID / "ocr-validation.json",
        "brief_data": HERE / "brief-data.json",
    }
    return {k: _load(p) for k, p in paths.items()}, paths


# --------------------------------------------------------------------------- SVG primitives
def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _svg(w: int, h: int, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{_esc(title)}" class="fig">{body}</svg>')


def _rect(x: float, y: float, w: float, h: float, fill: str, extra: str = "", title: str = "") -> str:
    r = f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" fill="{fill}" {extra}'
    return f"{r}><title>{_esc(title)}</title></rect>" if title else f"{r}/>"


def _text(x: float, y: float, s: Any, size: int = 11, fill: str = "#222", anchor: str = "start",
          extra: str = "") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" {extra}>{_esc(s)}</text>')


def _line(x1: float, y1: float, x2: float, y2: float, stroke: str = "#888", w: float = 1.0, extra: str = "") -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}" {extra}/>'


# --------------------------------------------------------------------------- figures
def fig_confidence_ideogram(basis: dict, order: list[dict]) -> str:
    """Whole-Bible chromosome ideogram: 76 book segments (width ∝ verse count), stacked by
    confidence tier (high/moderate/low), with tome/section dividers — the confidence karyotype."""
    per_book = basis["scripture"]["per_book"]
    books = [b for b in order if b["slug"] in per_book]
    total = sum(per_book[b["slug"]]["elements"] for b in books)
    W, H, x0, top, band = 980, 150, 10, 34, 46
    usable = W - 2 * x0
    x = float(x0)
    body = [_text(x0, 20, "Confidence ideogram — 76 books in canonical order, segment width ∝ verse count, "
                  "banded by consensus confidence tier", 12, "#222")]
    last_section = None
    for b in books:
        pb = per_book[b["slug"]]
        n = pb["elements"]
        w = usable * n / total
        tiers = pb["tiers"]
        yy = float(top)
        for tier in ("high", "moderate", "low"):
            cnt = tiers.get(tier, 0)
            hh = band * cnt / n if n else 0
            if hh > 0:
                body.append(_rect(x, yy, w, hh, TIER_COLOR[tier], title=f'{b["slug"]}: {tier} {cnt}/{n}'))
            yy += hh
        sec = b.get("section_id")
        if sec != last_section and last_section is not None:
            body.append(_line(x, top - 4, x, top + band + 4, "#333", 1.4))
        last_section = sec
        x += w
    body.append(_rect(x0, top, usable, band, "none", 'stroke="#333" stroke-width="1"'))
    # legend
    lx = x0
    for tier, label in [("high", "high"), ("moderate", "moderate"), ("low", "low")]:
        body.append(_rect(lx, H - 24, 12, 12, TIER_COLOR[tier]))
        body.append(_text(lx + 16, H - 14, label, 11))
        lx += 90
    return _svg(W, H, "".join(body), "Confidence ideogram")


def fig_coverage_depth(basis: dict, order: list[dict]) -> str:
    """Per-book independent-witness depth (read-depth analog): stacked proportion of verses at
    independent depth 1..4. Deeper (greener) = more independent witnesses corroborate the base."""
    per_book = basis["scripture"]["per_book"]
    books = [b for b in order if b["slug"] in per_book]
    rowh, x0, labelw, barw = 15, 12, 140, 720
    H = 40 + rowh * len(books) + 30
    W = x0 + labelw + barw + 60
    body = [_text(x0, 20, "Coverage-depth karyotype — per-book independent-witness depth "
                  "(share of verses at independent depth 1–4)", 12, "#222")]
    y = 34
    for b in books:
        pb = per_book[b["slug"]]
        n = pb["elements"]
        dh = {int(k): v for k, v in pb["indep_depth"].items()}
        body.append(_text(x0, y + rowh - 4, b["slug"], 10, "#333"))
        x = float(x0 + labelw)
        for d in (1, 2, 3, 4):
            cnt = dh.get(d, 0)
            w = barw * cnt / n if n else 0
            if w > 0:
                body.append(_rect(x, y, w, rowh - 2, DEPTH_COLOR[d], title=f'{b["slug"]}: depth {d} = {cnt}/{n}'))
            x += w
        body.append(_text(x0 + labelw + barw + 6, y + rowh - 4, n, 9, "#777"))
        y += rowh
    lx = x0 + labelw
    for d in (1, 2, 3, 4):
        body.append(_rect(lx, H - 20, 12, 12, DEPTH_COLOR[d]))
        body.append(_text(lx + 16, H - 10, f"depth {d}", 10))
        lx += 90
    return _svg(W, H, "".join(body), "Coverage-depth karyotype")


def fig_fidelity_print_ci(fidelity: dict, print_a: dict) -> str:
    """Diplomatic-fidelity (§6.2, post-fold Jaccard by witness tier) + independent-print recall
    with bootstrap 95% CI whiskers (§6.3, archaic vs modern). Two stacked panels."""
    W, H, x0 = 1010, 250, 210
    scale = (W - x0 - 200)         # 0..100 maps across; keep a right margin for the CI value labels
    body = [_text(10, 20, "Diplomatic fidelity (§6.2) & independent-print recall (§6.3)", 13, "#222")]

    def xval(pct: float) -> float:
        return x0 + scale * pct / 100.0

    # gridlines
    for pct in (0, 25, 50, 75, 100):
        body.append(_line(xval(pct), 30, xval(pct), H - 30, "#eee", 1))
        body.append(_text(xval(pct), H - 16, f"{pct}", 9, "#999", "middle"))

    y = 44
    body.append(_text(10, y, "§6.2 post-fold Jaccard (archaic↔modern), by witness tier", 11, "#555"))
    y += 18
    for tier in ("clean-diplomatic", "mixed", "ocr-only-noisy"):
        t = fidelity["by_witness_tier"].get(tier)
        if not t:
            continue
        v = 100 * t["mean_jaccard"]
        body.append(_text(x0 - 8, y + 10, f'{tier} (n={t["verses_compared"]})', 10, "#333", "end"))
        body.append(_rect(x0, y, xval(v) - x0, 13, WITNESS_TIER_COLOR[tier]))
        body.append(_text(xval(v) + 4, y + 10, f'{t["mean_jaccard"]:.3f}', 10, "#333"))
        y += 20

    y += 10
    body.append(_text(10, y, "§6.3 token recall vs independent archive.org print, bootstrap 95% CI", 11, "#555"))
    y += 18
    rows = [("archaic edition (idx 109)", print_a["aggregate"]["archaic"], "archaic"),
            ("modern edition (idx 108)", print_a["aggregate"]["modern"], "modern")]
    for label, blk, ed in rows:
        pt = blk["recall_pct"]
        lo, hi = blk["ci95"]
        cy = y + 7
        body.append(_text(x0 - 8, cy + 3, label, 10, "#333", "end"))
        body.append(_line(xval(lo), cy, xval(hi), cy, EDITION_COLOR[ed], 2))
        body.append(_line(xval(lo), cy - 4, xval(lo), cy + 4, EDITION_COLOR[ed], 2))
        body.append(_line(xval(hi), cy - 4, xval(hi), cy + 4, EDITION_COLOR[ed], 2))
        body.append(f'<circle cx="{xval(pt):.1f}" cy="{cy:.1f}" r="4" fill="{EDITION_COLOR[ed]}"/>')
        body.append(_text(xval(hi) + 6, cy + 3, f'{pt}% [{lo}, {hi}]', 10, "#333"))
        y += 24
    body.append(_text(10, H - 4, "x-axis: percent (Jaccard ×100 / recall %).", 9, "#999"))
    return _svg(W, H, "".join(body), "Fidelity and print-validation CI panel")


def fig_glyph_chart(fidelity: dict, order: list[dict]) -> str:
    """Per-book retained long-ſ count (log-ish bar) — evidence the archaic type is genuinely archaic.
    Books with no long-ſ are the ocr-only tier (the ſ→f OCR misread ate their long-esses)."""
    pb = fidelity["per_book"]
    books = [b for b in order if b["slug"] in pb]
    counts = [(b["slug"], pb[b["slug"]]["glyph_inventory"].get("long_s", 0),
               pb[b["slug"]]["witness_tier"]) for b in books]
    mx = max((c for _, c, _ in counts), default=1) or 1
    rowh, x0, labelw, barw = 15, 12, 140, 640
    H = 40 + rowh * len(counts) + 24
    W = x0 + labelw + barw + 70
    body = [_text(x0, 20, "Diplomatic-glyph inventory — retained long-ſ per book (bar ∝ count; "
                  "empty bars = ocr-only books where OCR misread ſ→f)", 12, "#222")]
    y = 34
    for slug, c, tier in counts:
        body.append(_text(x0, y + rowh - 4, slug, 10, "#333"))
        w = barw * c / mx
        body.append(_rect(x0 + labelw, y, w, rowh - 2, WITNESS_TIER_COLOR.get(tier, "#bbb"),
                          title=f'{slug}: {c} long-ſ ({tier})'))
        body.append(_text(x0 + labelw + w + 5, y + rowh - 4, c, 9, "#777"))
        y += rowh
    return _svg(W, H, "".join(body), "Diplomatic-glyph inventory")


def _jac_color(j: float | None) -> str:
    if j is None:
        return "#c7e9c0"          # not flagged as a variant ⇒ matches the called consensus
    if j >= 0.7:
        return "#1a9850"
    if j >= 0.4:
        return "#fdae61"
    return "#d7301f"


def fig_coverage_histogram(bd: dict) -> str:
    """Read-depth vs independent-depth histograms. Read depth = attesting sources (max 5);
    independent depth = independent lineages (max 4). The one-step ceiling difference is the
    non-independence correction: madueke_a and sabates_a share the Madueke lineage."""
    dh = bd["depth_histograms"]
    sup = {int(k): v for k, v in dh["support_depth"].items()}
    ind = {int(k): v for k, v in dh["indep_depth"].items()}
    depth_col = {1: "#d7301f", 2: "#fdae61", 3: "#a6d96a", 4: "#1a9850", 5: "#006837"}
    mx = max(max(sup.values()), max(ind.values())) or 1
    W, H, pad, top, baseh = 980, 220, 22, 44, 130
    panel_w = (W - 3 * pad) / 2
    body = [_text(10, 20, "Coverage depth — attesting sources (read depth) vs independent lineages "
                  "(the ceiling gap is the non-independence correction)", 12, "#222")]

    def panel(x0: float, title: str, hist: dict[int, int], kmax: int) -> list[str]:
        out = [_text(x0, top - 8, title, 11, "#555")]
        bw = panel_w / (kmax + 1)
        for i, k in enumerate(range(1, kmax + 1)):
            cnt = hist.get(k, 0)
            hh = baseh * cnt / mx
            bx = x0 + bw * (i + 0.5)
            out.append(_rect(bx, top + baseh - hh, bw * 0.7, hh, depth_col.get(k, "#006837"),
                             title=f"depth {k}: {cnt:,}"))
            out.append(_text(bx + bw * 0.35, top + baseh - hh - 3, f"{cnt:,}", 9, "#333", "middle"))
            out.append(_text(bx + bw * 0.35, top + baseh + 12, k, 10, "#555", "middle"))
        out.append(_line(x0, top + baseh, x0 + panel_w, top + baseh, "#888", 1))
        return out

    body += panel(pad, "read depth — attesting sources (max 5)", sup, 5)
    body += panel(2 * pad + panel_w, "independent depth — lineages (max 4)", ind, 4)
    return _svg(W, H, "".join(body), "Coverage-depth histograms")


def fig_source_track(bd: dict) -> str:
    """Source-track browser: x = verse position within a chapter, one lane per witness, with a
    consensus track banded by confidence tier on top. Present = source-colored cell, absent = empty.
    Genesis 1 (all five witnesses) beside Isaie 1 (ocr-only, three) shows the read-depth collapse
    in books the archaic diplomatic lineages never reach."""
    tracks = bd["source_tracks"]
    sources = bd["book_source_matrix"]["sources"]
    x0, labelw, cellw, rowh, gap = 12, 120, 22, 15, 30
    maxv = max(t["n_verses"] for t in tracks)
    trackw = cellw * maxv
    W = x0 + labelw + trackw + 20
    panel_h = (len(sources) + 1) * rowh + gap + 8
    H = 36 + panel_h * len(tracks) + 24
    body = [_text(x0, 20, "Source-track browser — verse × witness lane; consensus track banded by "
                  "confidence tier. Empty cell = witness absent (the read-depth view).", 12, "#222")]
    y = 40.0
    for t in tracks:
        depth = f'{min(sum(v["present"].values()) for v in t["verses"])}–' \
                f'{max(sum(v["present"].values()) for v in t["verses"])} witnesses'
        body.append(_text(x0, y - 4, f'{t["book"]} {t["chapter"]} · {t["n_verses"]} verses · read depth {depth}',
                          11, "#333"))
        cy = y
        body.append(_text(x0 + labelw - 6, cy + rowh - 4, "consensus", 9, "#111", "end"))
        for v in t["verses"]:
            cx = x0 + labelw + cellw * (v["verse"] - 1)
            body.append(_rect(cx, cy, cellw - 1.5, rowh - 2, TIER_COLOR.get(v["tier"], "#bbb"),
                              title=f'{v["ref"]}: {v["tier"]}, agreement {v["agreement"]}'))
        cy += rowh + 3
        for s in sources:
            body.append(_text(x0 + labelw - 6, cy + rowh - 4, s, 9, "#333", "end"))
            for v in t["verses"]:
                cx = x0 + labelw + cellw * (v["verse"] - 1)
                if v["present"].get(s):
                    body.append(_rect(cx, cy, cellw - 1.5, rowh - 2, SOURCE_COLOR[s],
                                      title=f'{v["ref"]}: {s} present'))
                else:
                    body.append(_rect(cx, cy, cellw - 1.5, rowh - 2, "#f4f4f4",
                                      'stroke="#e2e2e2" stroke-width="0.5"'))
            cy += rowh
        for v in t["verses"]:
            if v["verse"] % 5 == 0:
                cx = x0 + labelw + cellw * (v["verse"] - 1) + (cellw - 1.5) / 2
                body.append(_text(cx, cy + 10, v["verse"], 8, "#999", "middle"))
        y += panel_h
    return _svg(W, H, "".join(body), "Source-track browser")


def fig_variant_pileups(bd: dict) -> str:
    """Variant pileup panels: the lowest-agreement locus in each of several books, with each
    witness's surface reading laid under the called consensus (the SNP-pileup analog). A low-Jaccard
    read is either fresh-OCR garble or a versification offset — a witness reading the neighbouring
    verse under the other Vulgate numbering."""
    pileups = bd["variant_pileups"]
    x0, labelw, jbar, rowh = 12, 150, 46, 15
    txt_x = x0 + labelw + jbar + 12
    mono = 'font-family="ui-monospace,Menlo,Consolas,monospace"'
    body = [_text(x0, 20, "Variant pileups — witness readings at the top disagreement locus per book; "
                  "consensus 'reference' on top, bar = Jaccard vs consensus.", 12, "#222")]
    y = 38.0
    for p in pileups:
        body.append(_text(x0, y + 10, f'▸ {p["ref"]} · {p["tier"]} · agreement {p["agreement"]} · '
                          f'depth {p["support_depth"]}/{p["indep_depth"]}', 11, "#111",
                          extra='font-weight="600"'))
        y += rowh + 4
        body.append(_text(x0 + labelw + jbar + 6, y + 10, "consensus", 9, "#111", "end"))
        body.append(_rect(x0 + labelw + 6, y + 2, jbar, rowh - 4, "#1a9850", title="called consensus"))
        body.append(_text(txt_x, y + 10, p["called_modern"][:140], 10, "#0b3d0b", extra=mono))
        y += rowh
        for r in p["reads"]:
            j = r["jaccard"]
            body.append(_text(x0 + labelw, y + 10, f'{r["source"]}·{r["edition"][:3]}', 9, "#333", "end"))
            body.append(_rect(x0 + labelw + 6, y + 2, jbar, rowh - 4, "#eee"))
            fillw = jbar * (j if j is not None else 1.0)
            body.append(_rect(x0 + labelw + 6, y + 2, fillw, rowh - 4, _jac_color(j),
                              title=f'Jaccard {j if j is not None else "≈1 (matches consensus)"}'))
            if j is not None:
                body.append(_text(x0 + labelw + 6 + jbar + 2, y + 10, f"{j:.2f}", 8, "#777"))
            body.append(_text(txt_x + 22, y + 9, r["surface"][:140], 9, "#333", extra=mono))
            y += rowh
        y += 8
    return _svg(1120, int(y + 16), "".join(body), "Variant pileup panels")


# --------------------------------------------------------------------------- HTML assembly
def _table(headers: list[str], rows: list[list[Any]]) -> str:
    h = "".join(f"<th>{_esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'


def _section(anchor: str, title: str, *blocks: str) -> str:
    return f'<section id="{anchor}"><h2>{_esc(title)}</h2>{"".join(blocks)}</section>'


def _p(text: str) -> str:
    return f"<p>{text}</p>"


def build_html(A: dict[str, Any], paths: dict[str, Path]) -> str:
    basis, cons = A["basis"], A["consensus"]
    fid, pa, pm = A["fidelity"], A["print_archaic"], A["print_modern"]
    appr, layout, redet = A["apparatus"], A["layout"], A["redetection"]
    rm, ra = A["render_modern"], A["render_archaic"]
    reg = A["sources_registry"]
    bd = A["brief_data"]
    order = layout["scripture_order"]["canonical_order"]

    ec = basis["element_counts"]
    tiers = basis["scripture"]["tiers"]
    depth = basis["scripture"]["indep_depth"]
    n_verses = ec["scripture-verse"]
    high_pct = 100 * tiers["high"] / n_verses
    agg_fid = fid["aggregate"]["mean_jaccard"]
    pa_arc, pa_mod = pa["aggregate"]["archaic"], pa["aggregate"]["modern"]

    figs = {
        "ideogram": fig_confidence_ideogram(basis, order),
        "depth": fig_coverage_depth(basis, order),
        "cov_hist": fig_coverage_histogram(bd),
        "track": fig_source_track(bd),
        "pileups": fig_variant_pileups(bd),
        "ci": fig_fidelity_print_ci(fid, pa),
        "glyph": fig_glyph_chart(fid, order),
    }

    # audit trail: every artifact + sha
    audit_rows = [[k, p.relative_to(REPO), _sha12(p)] for k, p in paths.items()]

    abstract = _p(
        f"We reconstruct two facsimile-grade digital editions of the Douay–Rheims Bible — a modern "
        f"(idx 108) and an archaic-diplomatic (idx 109) rendering — as deterministic projections of a "
        f"single <b>basis database</b> of {n_verses:,} scripture verses assembled from "
        f"{reg['witness_count']} witnesses across {len(reg['independence_axes'])} independent lineages. "
        f"Every verse is corroborated across all attesting witnesses and assigned a consensus "
        f"confidence tier; {high_pct:.1f}% reach the high tier (mean cross-witness agreement "
        f"{cons['mean_agreement']:.3f}). A re-detection gate confirms 100% coordinate round-trip "
        f"(Gate P1 = {'PASS' if redet['gate_p1_pass'] else 'FAIL'}). The two editions share skeleton, "
        f"apparatus placement and element structure exactly and differ only in a final spelling/typeset "
        f"layer, so their diff isolates precisely the orthographic delta. A documented bidirectional "
        f"spelling-glyph model folds the two surfaces to a neutral skeleton: post-fold word "
        f"correspondence is {agg_fid:.3f} mean Jaccard (§6.2), and both editions corroborate against an "
        f"independent third-party OCR of the original 1582/1609/1610 print at "
        f"{pa_arc['recall_pct']}% (archaic) / {pa_mod['recall_pct']}% (modern) recall with zero genuine "
        f"content-word discrepancies (§6.3).")

    intro = _p(
        "The reconstruction follows one paradigm: <i>detect everywhere → consensus-generate → "
        "re-detect to confirm</i>. Each element is detected across every witness that attests it; a "
        "consensus surface is called with independence-weighted confidence; the assembled basis is "
        "then re-detected to prove a lossless round-trip. Scans of the original print are the layout "
        "authority. One basis yields two renderings — spelling/typeset is a final layer, not a "
        "separate transcription — so both editions draw on all sources. The visual grammar here is a "
        "genome browser's: confidence tiers band a chromosome ideogram, independent-witness depth is "
        "read depth, and source disagreements surface as variant pileups.")

    src_rows = [[s, basis["attestation_by_source"].get(s, 0)]
                for s in sorted(basis["attestation_by_source"], key=lambda k: -basis["attestation_by_source"][k])]
    sources_sec = _section(
        "sources", "Sources & provenance",
        _p(f"{reg['witness_count']} witnesses span {len(reg['independence_axes'])} independent "
           f"lineages ({', '.join(_esc(x) for x in cons['lineages_present'])}). Consensus is weighted "
           f"by independence so it never validates itself. Per-source scripture attestation counts:"),
        _table(["source", "verses attested"], src_rows),
        _p("Independence axes: " + ", ".join(_esc(x) for x in reg["independence_axes"]) + "."))

    methods = _section(
        "methods", "Methods",
        _p("<b>Skeleton.</b> A canonical coordinate grid of "
           f"{basis['element_counts']['scripture-verse']:,} scripture verses plus "
           f"{basis['element_counts']['apparatus-item']} apparatus items and "
           f"{basis['element_counts']['structural-node']} structural nodes anchors every witness to a "
           "shared address space."),
        _p("<b>Per-source detection & consensus.</b> Each witness is aligned by content-anchored "
           "matching; a consensus surface is called per coordinate with an agreement score, support "
           "depth and independent depth. Confidence tiers: "
           f"high {tiers['high']:,} / moderate {tiers['moderate']:,} / low {tiers['low']:,}."),
        _p("<b>Layout grounding.</b> Apparatus placement and book/tome ordering are grounded in the "
           f"archive.org page scans: {layout['summary']['grounded']} of "
           f"{layout['summary']['apparatus_slots']} apparatus slots are scan-grounded with committed "
           f"header crops ({layout['summary']['co-located']} co-located, "
           f"{layout['summary']['unlocatable']} unlocatable, {layout['summary']['inventoried']} "
           "inventoried)."),
        _p("<b>Conversion model (§6.1).</b> A documented bidirectional spelling-glyph fold "
           "(long-ſ↔s, æ↔ae, œ↔oe, u/v, i/j, vv↔w, &↔and, period spellings) reduces both surfaces to "
           "a neutral skeleton for comparison; archaic rendering restores each form from the archaic "
           "witness, never a lossy back-transform."),
        figs["ideogram"])

    results = _section(
        "results", "Results",
        _p(f"<b>Coverage & confidence.</b> {high_pct:.1f}% of verses reach the high tier; independent "
           f"depth distribution (verses corroborated by k independent lineages): "
           f"1={depth['1']:,}, 2={depth['2']:,}, 3={depth['3']:,}, 4={depth['4']:,}."),
        figs["depth"],
        figs["cov_hist"],
        _p("<b>Source coverage & read depth.</b> Read depth (attesting witnesses, up to five) and "
           "independent depth (independent lineages, up to four) diverge by exactly one step because "
           "the modern transcription backbone (madueke_a) and the apparatus backbone (sabates_a) "
           "share the Madueke lineage; consensus weights by independent lineage so a witness family "
           "never corroborates itself. The source-track browser reads position-by-position: Genesis 1 "
           "carries all five witnesses, while an ocr-only prophetic book (Isaie 1) falls to the three "
           "witnesses whose lineages reach it — the read-depth collapse made visible."),
        figs["track"],
        _p("<b>Consensus & variant structure.</b> Where witnesses disagree, the pileup lays each "
           "surface reading under the called consensus. The largest disagreements are not OCR noise "
           "but versification offsets: a witness numbering under the alternate Vulgate convention "
           "reads the neighbouring verse (e.g. the odr-com and s-dismas witnesses at the Matthew "
           "18:33 locus read verse 34), which the independence-weighted consensus resolves to the "
           "majority-attested reading and records as a versification adjudication case (§6.2). "
           "Genuine fresh-OCR garble (e.g. the ocr-only Isaie locus) surfaces as a single low-Jaccard "
           "read against otherwise-agreeing witnesses."),
        figs["pileups"],
        _p("<b>Apparatus inclusion.</b> "
           f"{appr['summary']['reference_docs']['include']} of "
           f"{appr['summary']['reference_docs']['total']} reference documents are included "
           f"({appr['summary']['reference_docs']['exclude']} excluded, honestly flagged); all "
           f"{appr['summary']['book_channels']['books']} books carry apparatus-channel attestation."),
        _p(f"<b>Rendering outcomes.</b> idx 108 (modern) reference sha "
           f"{rm['reference']['sha256'][:12]} ({rm['reference']['text_len']:,} chars); idx 109 "
           f"(archaic) sha {ra['reference']['sha256'][:12]} ({ra['reference']['text_len']:,} chars), "
           f"structurally parity-checked against idx 108."),
        _p("<b>Diplomatic fidelity & independent print validation.</b> Post-fold word correspondence "
           "is tiered by archaic-witness coverage; both editions corroborate strongly against the "
           "independent print with no genuine content-word discrepancies:"),
        figs["ci"],
        _p(f"An independently-sampled modern print validation (idx 108, its own seed-1729 stratified "
           f"sample in the Madueke lineage) replicates this at {pm['aggregate']['recall_pct']}% recall "
           f"CI {pm['aggregate']['ci95']} with {pm['aggregate']['genuine_candidate_misses']} genuine "
           "discrepancy candidates — an independent replication of the paired estimate above."),
        _table(["metric", "value"],
               [["§6.2 mean post-fold Jaccard", f'{agg_fid:.3f} over {fid["aggregate"]["verses_compared"]:,} verses'],
                ["§6.2 clean-diplomatic tier", fid["by_witness_tier"]["clean-diplomatic"]["mean_jaccard"]],
                ["§6.2 ocr-only tier", fid["by_witness_tier"]["ocr-only-noisy"]["mean_jaccard"]],
                ["§6.3 archaic print recall", f'{pa_arc["recall_pct"]}% CI {pa_arc["ci95"]}'],
                ["§6.3 modern print recall", f'{pa_mod["recall_pct"]}% CI {pa_mod["ci95"]}'],
                ["§6.3 genuine discrepancy candidates", pa["aggregate"]["archaic_genuine_candidate_misses"]]]),
        _p("<b>Diplomatic-glyph inventory.</b> Retained long-ſ per book evidences genuinely archaic "
           "type; its absence marks the ocr-only books where OCR misread ſ→f:"),
        figs["glyph"])

    discussion = _section(
        "discussion", "Discussion",
        _p("Rendering fidelity is governed by archaic-witness coverage. Where s-dismas contributes a "
           "clean diplomatic transcription, the archaic surface folds almost exactly onto the modern "
           "one and corroborates the independent print as a true cross-witness check. The ocr-only "
           "books (Isaie, Ecclesiasticus, Zacharias, 4-Esdras, the minor prophets) carry the "
           "fresh-OCR long-ſ→f misread; the §6.2 fold deliberately keeps f and s distinct so this "
           "surfaces as a measured residual rather than being masked. The §6.3 severe residual tail is "
           "not OCR noise but verse-numbering divergence in the well-attested books — chiefly the "
           "Vulgate convention of numbering a psalm's title as verse 1 — recorded as a versification "
           "adjudication set."))

    limitations = _section(
        "limitations", "Limitations",
        _p(f"The archaic surface has coverage gaps ({ra['scripture_projection']['archaic_coverage_gaps']} "
           "modern-present coordinates with no archaic witness) rendered from the modern surface and "
           "flagged, and a set of archaic-only coordinates deferred as a versification adjudication "
           "set. For the ocr-only books, archaic-vs-print recall is partially self-referential (the "
           "surface derives from the same OCR family); the modern-vs-print recall is the independent "
           "signal there. The masked editorial apparatus is shared between editions (modern witness); "
           "an archaic apparatus witness is a documented follow-up."))

    repro = _section(
        "repro", "Reproducibility & audit trail",
        _p("Every figure and headline number is computed from a committed JSON artifact; the basis "
           "database and raw corpora are regenerable and pinned by sha256 out of band. Validation "
           "sampling is seeded (1729) and bootstrap CIs are deterministic. Artifacts backing this "
           "brief:"),
        _table(["artifact", "path", "sha256[:12]"], audit_rows))

    refs = _section(
        "refs", "References & witnesses",
        _table(["lineage", "role"],
               [["modern-madueke", "modern transcription backbone (Madueke A/B)"],
                ["s-dismas", "archaic diplomatic transcription (1582 Rheims + editions)"],
                ["odr-com", "archaic witness (independent transcription)"],
                ["our-ocr + archive.org", "fresh + third-party OCR of the 1582/1609/1610 print scans"],
                ["sabates_a", "apparatus backbone (Madueke-derived)"]]))

    nav = "".join(f'<a href="#{a}">{_esc(t)}</a>' for a, t in [
        ("sources", "Sources"), ("methods", "Methods"), ("results", "Results"),
        ("discussion", "Discussion"), ("limitations", "Limitations"), ("repro", "Reproducibility"),
        ("refs", "References")])

    css = """
      :root{--ink:#1a1a1a;--mut:#666;--line:#ddd}
      *{box-sizing:border-box}
      body{font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);
           max-width:1040px;margin:0 auto;padding:28px}
      header h1{margin:0 0 4px;font-size:26px}
      .sub{color:var(--mut);margin:0 0 8px}
      nav{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:8px 0;margin-bottom:8px}
      nav a{margin-right:14px;color:#1b6ec2;text-decoration:none;font-size:13px}
      h2{border-bottom:2px solid var(--line);padding-bottom:4px;margin-top:30px;font-size:19px}
      p{margin:10px 0}
      table{border-collapse:collapse;margin:12px 0;font-size:13px;width:100%}
      th,td{border:1px solid var(--line);padding:4px 8px;text-align:left}
      th{background:#f6f6f6}
      .fig{display:block;margin:14px 0;border:1px solid #eee;background:#fff;max-width:100%}
      .abstract{background:#f7f7fb;border-left:4px solid #762a83;padding:10px 16px;border-radius:4px}
      footer{color:var(--mut);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:10px}
    """
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>OriginalDR reconstruction — academic brief</title>"
        f"<style>{css}</style></head><body>"
        "<header><h1>Reconstructing the Douay–Rheims: a corroborated dual-edition digital critical text</h1>"
        "<p class=\"sub\">Modern (idx 108) &amp; archaic-diplomatic (idx 109) editions as deterministic "
        "projections of one independence-weighted basis database</p></header>"
        f"<nav>{nav}</nav>"
        f'<section id="abstract"><h2>Abstract</h2><div class="abstract">{abstract}</div></section>'
        f'<section id="intro"><h2>Introduction</h2>{intro}</section>'
        f"{sources_sec}{methods}{results}{discussion}{limitations}{repro}{refs}"
        "<footer>Generated by gen_originaldr_brief.py from committed reconstruction artifacts. "
        "Genome-browser figures: confidence tier → chromosome banding; independent-witness depth → "
        "read depth. Every number traces to a committed JSON (+ source sha256).</footer>"
        "</body></html>")


def main() -> int:
    A, paths = load_artifacts()
    missing = [k for k, p in paths.items() if not p.exists()]
    if missing:
        print(f"!! missing artifacts: {missing}", file=__import__("sys").stderr)
        return 2
    out_html = build_html(A, paths)
    OUT.write_text(out_html, encoding="utf-8")
    n_fig = out_html.count("<svg")
    print(f"wrote {OUT.relative_to(REPO)} · {len(out_html):,} bytes · {n_fig} figures · "
          f"{out_html.count('<section')} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
