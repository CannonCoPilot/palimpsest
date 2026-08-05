#!/usr/bin/env python3
"""gt_ocr_diag_report.py — figure-rich HTML report: OCR rung-0 diagnosis + GT-anchored baseline (Sir 2026-07-18)."""
from __future__ import annotations
import json, html
from pathlib import Path
from collections import Counter, defaultdict
from statistics import mean, median

H = Path(__file__).resolve().parent
def load(p, d=None):
    f = H / p
    return json.loads(f.read_text()) if f.is_file() else d

BASE = load("gt-rescore-baseline.json", {})
W10 = load("diag-reocr/rung0-worst10-signoff.json", {}).get("worst10", [])
SAMP = load("diag-reocr/sample/sample-manifest.json", {})
FIGS = load("diag-reocr/report-figs.json", {})
SCAN = load("diag-reocr/sample/sample-scan-results.json", {})   # aggregated agent output (optional)

MODE_LABEL = {"M1":"M1 marginalia-bleed","M2":"M2 interleaved-annotation","M3":"M3 ſ→f glyph",
              "M4":"M4 localization / non-text","M5":"M5 scan-degraded"}
MODE_COLOR = {"M1":"#e8833a","M2":"#c0433e","M3":"#4c8fbf","M4":"#8a6bb5","M5":"#6aa84f",
              "NEW":"#d64f9a","other":"#888"}
RUNG_OF = {"M1":"1 layout-aware","M2":"1 layout-aware","M3":"2 region/glyph","M4":"localization fix","M5":"2 / rescan"}

def esc(s): return html.escape(str(s))

def bar_chart(pairs, w=560, bh=26, gap=8, unit="", cmap=None):
    if not pairs: return "<p><em>pending</em></p>"
    mx = max(v for _, v in pairs) or 1
    rows = []
    y = 0
    lblw = 170
    for k, v in pairs:
        bw = int((w - lblw - 60) * v / mx)
        col = (cmap or {}).get(k, "#5a7fa3")
        rows.append(
            f'<text x="0" y="{y+bh*0.68}" class="lbl">{esc(k)}</text>'
            f'<rect x="{lblw}" y="{y}" width="{bw}" height="{bh-gap}" rx="3" fill="{col}"/>'
            f'<text x="{lblw+bw+6}" y="{y+bh*0.68}" class="val">{v}{unit}</text>')
        y += bh
    return f'<svg viewBox="0 0 {w} {y}" width="100%" style="max-width:{w}px">{"".join(rows)}</svg>'

def hist_chart(vals, buckets, w=560, h=180):
    counts = [0]*len(buckets)
    for v in vals:
        for i,(lo,hi,_) in enumerate(buckets):
            if lo <= v < hi: counts[i]+=1; break
    mx = max(counts) or 1
    bw = (w-40)/len(buckets); bars=[]
    for i,c in enumerate(counts):
        bh = int((h-30)*c/mx); x=20+i*bw
        col = "#c0433e" if buckets[i][0]<0.10 else ("#6aa84f" if buckets[i][0]>=0.70 else "#e8a13a")
        bars.append(f'<rect x="{x+4}" y="{h-20-bh}" width="{bw-8}" height="{bh}" rx="2" fill="{col}"/>'
                    f'<text x="{x+bw/2}" y="{h-20-bh-4}" class="val" text-anchor="middle">{c}</text>'
                    f'<text x="{x+bw/2}" y="{h-6}" class="tick" text-anchor="middle">{buckets[i][2]}</text>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">{"".join(bars)}</svg>'

def diverge_chart(rows, w=600):
    # rows: (label, A_ocr, B_sd, C_odr) each 0..1 ; draw 3 dots per row
    bh=22; y=0; out=[]; x0=175; xw=w-x0-30
    out.append(f'<text x="{x0}" y="10" class="tick">0.5</text><text x="{x0+xw*0.8}" y="10" class="tick">0.9(bar)</text>')
    out.append(f'<line x1="{x0+xw*(0.9-0.5)/0.5}" y1="14" x2="{x0+xw*(0.9-0.5)/0.5}" y2="{14+bh*len(rows)}" stroke="#c0433e" stroke-dasharray="3 3"/>')
    for lab,a,b,c in rows:
        yy=14+y*bh+bh*0.6
        def px(v): return x0+xw*max(0,(v-0.5))/0.5
        out.append(f'<text x="0" y="{yy}" class="lbl">{esc(lab)}</text>')
        for v,col,t in [(b,"#4c8fbf","s"),(c,"#8a6bb5","o"),(a,"#e8833a","O")]:
            if v is not None: out.append(f'<circle cx="{px(v):.0f}" cy="{yy-4:.0f}" r="5" fill="{col}"><title>{t}={v:.3f}</title></circle>')
        y+=1
    return f'<svg viewBox="0 0 {w} {24+bh*len(rows)}" width="100%" style="max-width:{w}px">{"".join(out)}</svg>'

def fig(key, cap):
    if key not in FIGS: return ""
    return f'<figure><img src="{FIGS[key]}" alt="{esc(cap)}"/><figcaption>{esc(cap)}</figcaption></figure>'

def card(big, label, sub=""):
    return f'<div class="card"><div class="big">{big}</div><div class="clab">{esc(label)}</div><div class="csub">{esc(sub)}</div></div>'

# ---- assemble ----
ov = BASE.get("overall", {})
items = [e for e in SAMP.get("manifest", []) if e.get("png")]
recs = [e["recall"] for e in items if e.get("recall") is not None]
w10modes = Counter(w["mode"] for w in W10)

# sample mode distribution (from agents, if present)
scan_rows = SCAN.get("results", [])
samp_modes = Counter(r.get("primary_mode") for r in scan_rows) if scan_rows else Counter()
samp_qual = Counter(r.get("scan_quality") for r in scan_rows) if scan_rows else Counter()
anomalies = [r for r in scan_rows if r.get("anomaly")]
KW={"drop-cap":"drop-cap opening","argument":"chapter-argument","genealog":"name-list","census":"name-list",
    "name-list":"name-list","tabular":"table/index","lectionary":"table/index","index":"table/index","table":"table/index",
    "greek":"mixed-script Greek/Hebrew","hebrew":"mixed-script Greek/Hebrew","poetry":"running-poetry","aphorism":"running-poetry",
    "per-line":"running-poetry","per-verse":"running-poetry","display":"display-title","masthead":"display-title",
    "colophon":"display-title","blank":"blank leaf","engraving":"engraving plate","plate":"engraving plate",
    "mismatch":"misregistration","misregist":"misregistration","latin":"non-English apparatus"}
fam=Counter()
for a in anomalies:
    d=(a.get("anomaly_desc") or "").lower()+" "+(a.get("notes") or "").lower()
    for v in {KW[k] for k in KW if k in d} or {"other"}: fam[v]+=1

P = []
P.append(f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OriginalDR OCR Rung-0 Diagnostic</title><style>
:root{{--ground:#efe7d6;--panel:#f7f1e4;--ink:#2a2016;--mut:#786c56;--line:#ddd0b6;
  --rubric:#9e2b22;--wash:#39617f;--good:#5c7d3a;--warn:#b8791f;--rule:#c9b892;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:-apple-system,"Segoe UI",Roboto,Helvetica,sans-serif}}
@media(prefers-color-scheme:dark){{:root{{--ground:#1b1712;--panel:#241f18;--ink:#e9dfca;--mut:#a99a7e;
  --line:#3a3227;--rubric:#d76a5f;--wash:#7aa6c4;--good:#9cbe6f;--warn:#d8a44e;--rule:#4a4030}}}}
:root[data-theme="dark"]{{--ground:#1b1712;--panel:#241f18;--ink:#e9dfca;--mut:#a99a7e;
  --line:#3a3227;--rubric:#d76a5f;--wash:#7aa6c4;--good:#9cbe6f;--warn:#d8a44e;--rule:#4a4030}}
:root[data-theme="light"]{{--ground:#efe7d6;--panel:#f7f1e4;--ink:#2a2016;--mut:#786c56;
  --line:#ddd0b6;--rubric:#9e2b22;--wash:#39617f;--good:#5c7d3a;--warn:#b8791f;--rule:#c9b892}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font:15px/1.6 var(--sans);
  font-variant-numeric:tabular-nums}}
.wrap{{max-width:880px;margin:0 auto;padding:44px 22px 96px}}
h1{{font:600 30px/1.15 var(--serif);margin:0 0 6px;text-wrap:balance;letter-spacing:-.01em}}
h2{{font:600 22px/1.2 var(--serif);margin:46px 0 12px;padding-bottom:7px;text-wrap:balance;
  border-bottom:1px solid var(--line);position:relative}}
h2::after{{content:"";position:absolute;left:0;bottom:-1px;width:64px;height:3px;background:var(--rubric)}}
h3{{font:600 15px/1.3 var(--sans);margin:26px 0 9px;color:var(--rubric);
  text-transform:uppercase;letter-spacing:.06em}}
.sub{{color:var(--mut);margin:0 0 22px;max-width:64ch}}
.cards{{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}}
.card{{flex:1;min-width:132px;background:var(--panel);border:1px solid var(--line);
  border-top:3px solid var(--rubric);border-radius:3px;padding:15px 16px}}
.big{{font:700 27px/1 var(--serif);color:var(--ink)}}
.clab{{font-size:12px;font-weight:600;margin-top:4px}}.csub{{font-size:11px;color:var(--mut);margin-top:2px}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:13px}}
th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{color:var(--mut);font-weight:600;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em}}
tbody tr:hover td,tr:hover td{{background:color-mix(in srgb,var(--rubric) 6%,transparent)}}
.lbl{{font-size:12px;fill:var(--ink)}}.val{{font-size:12px;fill:var(--mut);font-weight:600}}.tick{{font-size:10px;fill:var(--mut)}}
figure{{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:9px}}
figure img{{width:100%;border-radius:2px;display:block;filter:sepia(.04)}}
figcaption{{font-size:12px;color:var(--mut);margin-top:7px;line-height:1.45}}
.figrow{{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0}}.figrow figure{{flex:1;min-width:238px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--wash);
  border-radius:3px;padding:16px 18px;margin:16px 0}}
.tag{{display:inline-block;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;color:#fff;white-space:nowrap}}
.key{{font-size:12.5px;color:var(--mut);margin:8px 0}}
.legend span{{margin-right:16px;font-size:12px}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}}
blockquote{{margin:14px 0;padding:12px 18px;border-left:3px solid var(--rubric);
  background:color-mix(in srgb,var(--rubric) 7%,transparent);border-radius:0 3px 3px 0;color:var(--ink)}}
blockquote b{{color:var(--rubric)}}
code{{background:color-mix(in srgb,var(--wash) 14%,transparent);padding:1px 5px;border-radius:3px;
  font-size:12px;font-family:"SF Mono",ui-monospace,Menlo,monospace}}
svg text{{font-family:var(--sans)}}
</style></head><body><div class="wrap">""")

P.append(f"""<h1>OriginalDR re-OCR — Rung-0 Diagnostic &amp; Gold-anchored Baseline</h1>
<p class="sub">Jarvis · 2026-07-18 · pilot data <code>coverage-audit-verse.json</code> (v10) + Gold Transcripts (25 loci) + stratified page sample</p>
<div class="cards">
{card(f"{ov.get('A_ocr_vs_gt',0):.2f}","OCR vs Gold (mean)","ocr_consensus, folded edit-ratio")}
{card(f"{ov.get('B_sdismas_vs_gt',0):.2f}","s_dismas vs Gold","reference faithfulness")}
{card(f"{len(items)}","pages sampled","{} sources, all books".format(len(SAMP.get('sources_used',[]))))}
{card(f"{sum(1 for r in recs if r<0.10)}","localization-fails","near-zero recall in sample")}
{card((str(len(anomalies)) if scan_rows else "—"),"anomaly flags","candidate new modes")}
</div>
<blockquote><b>Headline.</b> The scans are mostly <b>clean</b>; OCR fails not on legibility but on <b>apparatus bleed</b>
(marginalia + interleaved annotations invading the verse stream) and <b>long-ſ→f</b> glyph errors. The references
(s_dismas / odr_com) are faithful where aligned (≈0.8–0.95), so the low pilot pass-rate is <b>genuine OCR failure,
routed to layout-aware re-OCR (rung 1)</b>, not merely measurement noise.</blockquote>""")

# ---- Part A ----
P.append(f"""<h2>1 · Gold-anchored baseline &amp; reference divergence</h2>
<p class="sub">{BASE.get('n_verses','?')} complete verses across 11 GT-covered loci, metric = fold_archaic + edit_ratio (pilot metric).</p>
<div class="legend"><span><span class="dot" style="background:#e8833a"></span>O = OCR vs Gold</span>
<span><span class="dot" style="background:#4c8fbf"></span>s = s_dismas vs Gold</span>
<span><span class="dot" style="background:#8a6bb5"></span>o = odr_com vs Gold</span> · red line = 0.90 bar</div>""")
# per-locus diverge chart
by_loc = defaultdict(list)
for r in BASE.get("rows", []): by_loc[r["locus"].replace("scripture-","")].append(r)
drows=[]
def _avg(rows,k):
    v=[x[k] for x in rows if x.get(k) is not None]; return mean(v) if v else None
for loc,rs in by_loc.items():
    drows.append((loc[:22], _avg(rs,"A_ocr_gt"), _avg(rs,"B_sd_gt"), _avg(rs,"C_oc_gt")))
P.append(diverge_chart(drows))
P.append(f"""<div class="panel"><b>Reading it.</b> s (blue) and o (purple) sit far right (≈0.8–1.0) on most psalms → the references are
faithful there; they fall left on <code>genesis</code> &amp; <code>matthew</code> (≈0.65) → real reference divergence on those books.
O (orange) is left of both almost everywhere → the OCR is the weak link. s_dismas diverges {100*(1-ov.get('B_sdismas_vs_gt',0.8)):.0f}% from Gold overall,
odr_com {100*(1-ov.get('C_odrcom_vs_gt',0.81)):.0f}% — but a caveat: the line-based GT crosses verse boundaries, deflating absolute numbers a few points,
and <code>ocr_consensus</code> is a degraded merge (pessimistic proxy for the best single witness).</div>""")

# ---- Part B worst-10 ----
P.append(f"""<h2>2 · Rung-0 sweep — 10 worst-scoring chapters</h2>
<p class="sub">Each failing chapter anchored to its source page, rasterized (150 DPI) and visually inspected.</p>""")
P.append('<div class="figrow">'
         + fig("M2_psalms118","M2 · Psalm 118 (S1): verse lines interleaved with italic annotation + inline keys a–f — clean scan")
         + fig("M1_john6","M1 · John 6 (S1): verse body flanked by liturgical + cross-ref marginalia, annotations block below")
         + '</div><div class="figrow">'
         + fig("M3_genesis24","M3 · Genesis 24 (S1): clean single-column body; failure is long-ſ→f glyph, not layout")
         + fig("M4_john8_plate","M4 · 'John 8' (S1): anchored to a full-page engraving plate — localization failure (recall 0.011)")
         + '</div>')
P.append(bar_chart([(MODE_LABEL[m], c) for m,c in w10modes.most_common()], cmap={MODE_LABEL[k]:MODE_COLOR[k] for k in MODE_COLOR if k in MODE_LABEL}))
P.append("<table><tr><th>chapter</th><th>scan</th><th>pg</th><th>recall</th><th>mode</th><th>scan</th><th>→rung</th><th>observation</th></tr>")
for w in W10:
    col=MODE_COLOR.get(w["mode"],"#888")
    P.append(f'<tr><td>{esc(w["locus"].replace("scripture/",""))}</td><td>{esc(w["scan"])}</td><td>{w["page"]}</td>'
             f'<td>{w["recall"]}</td><td><span class="tag" style="background:{col}">{w["mode"]}</span></td>'
             f'<td>{esc(w.get("scan_quality"))}</td><td>{esc(w.get("rung"))}</td><td>{esc(w["note"])}</td></tr>')
P.append("</table>")

# ---- Part C stratified sample ----
P.append(f"""<h2>3 · Stratified sample — hunting new modes beyond the worst-10</h2>
<p class="sub">One representative page per book (all 52 reference books) + apparatus, each from 2+ sources, all usable sources represented.
{len(items)} rasters classified.</p>""")
bysrc = Counter(e["source"] for e in items)
P.append("<h3>Rasters per source (coverage)</h3>")
P.append(bar_chart(sorted(bysrc.items()), unit=""))
P.append("<h3>Localization recall distribution</h3>")
P.append(hist_chart(recs, [(0,0.10,"<.10"),(0.10,0.30,".1–.3"),(0.30,0.50,".3–.5"),(0.50,0.70,".5–.7"),(0.70,1.01,"≥.7")]))
P.append(f'<p class="key">mean {mean(recs):.2f} · median {median(recs):.2f} · <b>{sum(1 for r in recs if r<0.10)} pages near-zero recall</b> (localization failures / wrong-page anchoring — a mode invisible in the curated worst-10).</p>')
if scan_rows:
    P.append(f"<h3>Primary failure-mode distribution ({len(scan_rows)} pages, 8 parallel classifiers)</h3>")
    P.append(bar_chart([(MODE_LABEL.get(m,m), c) for m,c in samp_modes.most_common()],
                       cmap={MODE_LABEL.get(k,k):MODE_COLOR.get(k,"#888") for k in list(MODE_COLOR)}))
    P.append(f'<p class="key">M3 (long-ſ→f glyph) is also the <b>secondary</b> mode on {Counter(r.get("secondary_mode") for r in scan_rows).get("M3",0)} pages — the archaic-glyph load is near-universal beneath the layout problem.</p>')
    P.append("<h3>Scan quality — legibility is mostly fine</h3>")
    P.append(bar_chart([(k,v) for k,v in samp_qual.most_common()], cmap={"clean":"#6aa84f","moderate":"#e8a13a","degraded":"#c0433e"}))
    P.append(f'<p class="key">Only {samp_qual.get("degraded",0)}/{len(scan_rows)} pages are genuinely degraded → the OCR problem is <b>layout + glyph, not scan quality</b>.</p>')
    P.append("<h3>New signatures the worst-10 missed (anomaly families)</h3>")
    P.append(bar_chart(fam.most_common(), cmap={"drop-cap opening":"#e8833a","chapter-argument":"#c0433e","display-title":"#8a6bb5",
             "mixed-script Greek/Hebrew":"#d64f9a","table/index":"#4c8fbf","running-poetry":"#6aa84f","name-list":"#b58a2c",
             "misregistration":"#999","blank leaf":"#aaa","engraving plate":"#777","non-English apparatus":"#5b8f8f"}))
    P.append("""<div class="panel"><b>⚠ Sampling caveat — read before interpreting M4.</b> The 23 M4 "non-text" pages and the
    18 near-zero-recall pages are <b>mostly sampling artifacts, not pipeline failures</b>: physical <b>blank versos</b> (many in
    source S3), a recurring <b>Pentecost engraving plate</b> that my single-page anchor latched onto for romans/1-cor/2-cor/philemon,
    and <b>off-by-chapter / wrong-book misregistration</b> (e.g. "esther/S9" is Numbers 10; "wisdom/S15" is Isaiah 13 — S15 is the
    Isaiah volume). That misregistration reflects my <b>ad-hoc mid-chapter anchoring</b> (a single best-page match), <em>not</em>
    the production localizer. On pages that <em>do</em> contain their target text, the modes are M1/M2/M3 — consistent with the worst-10.</div>""")
else:
    P.append('<div class="panel"><em>Sample failure-mode distribution + anomaly review pending agent aggregation.</em></div>')

# apparatus figures
P.append("<h3>Apparatus strata (front/back matter, all 3 volumes)</h3>")
P.append('<div class="figrow">'
         + fig("apparatus_nt_title","NT title page — display caps (VV for W), engraving border: M4 non-text/display")
         + fig("apparatus_nt_table","NT 'Table' — two-column index/list: TABULAR layout")
         + fig("apparatus_ot1_colophon","OT1 colophon — end-matter block")
         + '</div>')

# ---- taxonomy + routing ----
P.append("""<h2>4 · Mode taxonomy → rung routing</h2>
<table><tr><th>mode</th><th>signature</th><th>where</th><th>→ rung</th></tr>""")
TAX=[("M1","central verse column + flanking marginalia (liturgical/cross-ref/commentary) + inline markers + annotation block","Gospels, Epistles, most books (65% of sample)","1 layout-aware: column/margin separation, strip inline keys"),
     ("M2","verse lines interleaved line-by-line with italic annotation + embedded footnote-keys + Hebrew headers","Psalms (150 ch), commentary pages","1 layout-aware: verse/annotation de-interleave (hardest)"),
     ("M3","clean single-column body, pervasive long-ſ mis-read as f, vv/ligatures","OT narrative (Genesis, Kings…); secondary on ~half of all pages","2 region/glyph: archaic-aware ſ recognizer"),
     ("M4","full-page engraving/plate, ornate title page, blank verso, or wrong-page anchor","plates/openings + (mostly) sampling artifacts","localization fix: plate/blank detection + robust re-anchor"),
     ("M5","faint/low-contrast/skewed scan or physical damage","source-specific (S3 blanks, S8/S10 faint)","2 / rescan: contrast-normalize or swap witness")]
for m,sig,where,rung in TAX:
    P.append(f'<tr><td><span class="tag" style="background:{MODE_COLOR[m]}">{m}</span></td><td>{esc(sig)}</td><td>{esc(where)}</td><td>{esc(rung)}</td></tr>')
P.append("</table>")
P.append("""<h3>New sub-signatures surfaced by the stratified sample (beyond the worst-10)</h3>
<table><tr><th>signature</th><th>what it is</th><th>where</th><th>→ handling</th></tr>""")
NEW=[("chapter-opening disruptor","historiated woodcut drop-cap initial + set-apart italic chapter-argument block at every chapter start (drop-cap reorders the OCR glyph stream)","near-universal (37/57 anomaly pages)","rung 1: drop-cap anchoring + argument as its own element"),
     ("mixed-script Greek/Hebrew","Greek (occasionally Hebrew) words set in the margins/glosses — Latin OCR cannot read them","Epistles (Col, 2-Thess, Titus, Acts, James)","rung 2/3: script-aware OCR or explicit drop+flag"),
     ("proper-name / genealogy list","dense enumerations of non-dictionary names + counts ('the children of Ater…') — no lexicon support","Esdras/Nehemias, Paralipomenon (Chronicles), Numbers censuses","rung 2: name-aware model; expect higher residual error"),
     ("tabular / index apparatus","lectionary tables (feast→reference), reference indices, the NT 'Table' — columnar, non-linear reading order","back-matter, NT table","rung 1: table/column-aware segmentation"),
     ("running-poetry + gloss column","one aphorism/stich per line with an aligned per-verse topical gloss column","Proverbs, Canticles","rung 1: poetry line model + gloss-column separation"),
     ("non-English apparatus","Latin approbatio / plate captions in humanist italic","front-matter (approbatio), plate banners","language-aware OCR (Latin)")]
for sig,what,where,h in NEW:
    P.append(f'<tr><td><span class="tag" style="background:#d64f9a">{esc(sig)}</span></td><td>{esc(what)}</td><td>{esc(where)}</td><td>{esc(h)}</td></tr>')
P.append("</table>")

P.append(f"""<h2>5 · What this means for the ladder</h2>
<blockquote><b>Rung 1 (layout-aware segmentation) is the primary lever.</b> Apparatus-bleed (M1+M2) is the dominant
failure across Gospels and Psalms — the bulk of the corpus. This is exactly what the Phase-2a <code>classify_v1</code>
body-vs-apparatus segmenter targets. <b>Rung 2 (archaic-ſ recognizer)</b> is the secondary lever for the clean-but-glyph-noisy
OT narrative. <b>Rung 3 (vision-LLM)</b> is <em>not</em> indicated — the pages are legible. A distinct <b>localization/engraving
handler</b> is needed for the M4 near-zero-recall pages ({sum(1 for r in recs if r<0.10)} in the sample alone).</blockquote>
<p class="sub">Also surfaced: source <b>S5</b> has no diplomatic OCR (<code>pdf-S05</code> absent); <b>S9's OT2 volume</b> was never OCR'd
(<code>archive-holiebible-ot2</code> absent) — coverage gaps to close before those witnesses can count.</p>
</div></body></html>""")

(H / "diag-reocr" / "rung0-diagnostic-report.html").write_text("".join(P))
print("wrote diag-reocr/rung0-diagnostic-report.html", f"({len(''.join(P))//1024} KB)")
print("sample modes:", dict(samp_modes) if scan_rows else "PENDING agents")
