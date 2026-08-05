#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s_arbiter_run.py — drive `s_arbiter` over the RESCUED_CONTENT_S_OPEN debts (§12.5 Tier C2).

WHY THIS EXISTS AS A SEPARATE PASS. `.r3-stats/` recorded each debt's SCORES but not its TEXTS, so the ſ-surface
work has nothing to operate on. This re-runs the same page path (cached kraken + one olmOCR pass per region, the
identical code r3_stats drove) and PERSISTS r2_text / r3_span / crop per verse to `.s-arbiter/<slug>.json`. That
cache is the point: the transfer, the visual residue and the re-verdict then all run offline and instantly, and
a future session never pays the olmOCR cost again.

Three stages, each idempotent:
  --extract   re-run the debt pages, persist texts+crops                       (needs MLX; ~1 pass per region)
  --transfer  s_arbiter.transfer per verse -> per-verse verdict + the RESIDUE  (offline, free)
  --apply F   fold a readings file {locus: {token_index: "ſpelling"}} in, re-verdict, rewrite the ledger

The residue is the ONLY thing a human/vision pass must look at: tokens R3 corrected, whose ſ no recognizer has
attested. Everything else transfers from R2's observed surface. Nothing is ever positionally restored.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gate_calibrate as calib      # noqa: E402
import r3_route                     # noqa: E402
import s_arbiter                    # noqa: E402
import verse_geom                   # noqa: E402
import verse_locate                 # noqa: E402
import verse_seg as VS              # noqa: E402
import xsrc_gate                    # noqa: E402
from gate_calibrate import LOCI, gold_by_chapter   # noqa: E402

R3_STATS = HERE / ".r3-stats"
OUT = HERE / ".s-arbiter"
GT = HERE / "ground-truth"
S_STATE = "RESCUED_CONTENT_S_OPEN"


def debts() -> dict:
    """{slug: [(ch, v), ...]} — the ſ-surface debts, read from the r3_stats checkpoints."""
    out: dict = {}
    for f in sorted(R3_STATS.glob("*.json")):
        if f.name.startswith("_"):
            continue
        for r in json.loads(f.read_text()):
            if r.get("state") == S_STATE:
                out.setdefault(r["slug"], []).append((r["ch"], r["v"]))
    return out


def extract(slug: str, want: list) -> dict:
    """Re-run the debt page and persist the TEXTS the ſ arbitration needs (r2_text, r3_span) + the crop.

    Identical path to r3_stats.page_stats — cached kraken page, one hybrid localization, one olmOCR pass per
    region — so the strings recorded here are the very strings the ledger's verdicts were computed from."""
    gt = json.loads((GT / f"{slug}.json").read_text())
    book, od, pi = LOCI.get(slug), gt.get("ocr_dir"), gt.get("page_index")
    r = calib.cached_page(slug, od, pi)
    recs: dict = {}
    for ch in sorted({c for c, _ in want}):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        spans = verse_locate.best_spans(r, book, ch)
        scores = xsrc_gate.cross_source_verse_scores(r["r2_body"], book, ch, spans=spans)
        flagged = [v for v in scores if scores[v].get("escalate")]
        if not flagged:
            continue
        crops = verse_geom.verse_crops(r, book, ch, spans=spans)
        regions = verse_geom.region_crops(r, book, ch, flagged, spans=spans)["regions"]
        rr = r3_route.rescue_flagged(od, pi, book, ch, scores, crops, regions=regions)
        for (c, v) in want:
            if c != ch:
                continue
            vd = rr["verses"].get(v, {})
            recs[f"{book}/{ch}/{v}"] = {
                "slug": slug, "book": book, "ch": ch, "v": v, "ocr_dir": od, "page_index": pi,
                "state": vd.get("state"), "r2_text": scores[v].get("r2_text"), "r3_span": vd.get("r3_span"),
                "crop": vd.get("crop"), "r2_s": vd.get("r2_s_count"), "r3_s": vd.get("r3_s_count"),
            }
    OUT.mkdir(exist_ok=True)
    (OUT / f"{slug}.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    return recs


def _cached() -> dict:
    recs: dict = {}
    for f in sorted(OUT.glob("*.json")):
        if not f.name.startswith("_"):
            recs.update(json.loads(f.read_text()))
    return recs


def transfer_all(readings: dict | None = None) -> dict:
    """Run the surface transfer over every extracted debt; return per-locus verdicts + the visual residue."""
    readings = readings or {}
    out, residue = {}, []
    for key, rec in sorted(_cached().items()):
        r2, r3 = rec.get("r2_text") or "", rec.get("r3_span") or ""
        if not r3:
            out[key] = {"state": "OPEN", "reason": "no-r3-span"}
            continue
        t = s_arbiter.transfer(r2, r3)
        given = {int(k): v for k, v in (readings.get(key) or {}).items()}
        if given:
            t = s_arbiter.arbitrate(t, given)
        v = s_arbiter.verdict(t, r2)
        out[key] = {**v, "text": t["text"], "crop": rec.get("crop"), "slug": rec["slug"],
                    "unresolved": t["unresolved"]}
        for u in t["unresolved"]:
            residue.append({"locus": key, "slug": rec["slug"], "crop": rec.get("crop"), **u})
    summary = {
        "n_debts": len(out),
        "n_closed": sum(1 for v in out.values() if v.get("state") == "CLOSED"),
        "n_open": sum(1 for v in out.values() if v.get("state") == "OPEN"),
        "n_alert": sum(1 for v in out.values() if v.get("state") == "ALERT"),
        "n_content_open": sum(1 for v in out.values() if v.get("state") == "CONTENT_OPEN"),
        "content_errors": [{"locus": k, **e} for k, v in out.items() for e in (v.get("content_errors") or [])],
        "n_residue_tokens": len(residue),
    }
    res = {"summary": summary, "verdicts": out, "residue": residue}
    OUT.mkdir(exist_ok=True)
    (OUT / "_transfer.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res


def rewrite_ledger(res: dict) -> dict:
    """Fold the arbiter's verdicts into a NEW ledger at `.s-arbiter/_open_ledger.json`.

    `.r3-stats/_open_ledger.json` is left untouched as the PRE-ARBITER record — the two side by side are the
    evidence that the ſ debts closed by observation rather than by moving a bar. Each debt either disappears
    (CLOSED, its surface now provenanced) or is REWRITTEN with the reason the arbiter actually found; a debt is
    never removed for any other cause."""
    led = json.loads((R3_STATS / "_open_ledger.json").read_text())
    verdicts = res["verdicts"]
    entries, closed = [], []
    for e in led["entries"]:
        v = verdicts.get(e["locus_key"])
        if not e["reason"].startswith("s-surface") or v is None:
            entries.append(e)                                  # untouched: not a ſ debt
            continue
        if v["state"] == "CLOSED":
            closed.append(e["locus_key"])
            continue
        errs = v.get("content_errors") or []
        entries.append({**e, "rungs_tried": e["rungs_tried"] + ["R3-arbiter"],
                        "reason": ("content-error-found-by-arbiter: "
                                   + "; ".join(f"{x['r3']!r} should read {x['printed']!r}" for x in errs))
                                  if errs else f"s-surface-unresolved ({v['n_undecided']} token(s) unread)",
                        "state": "OPEN"})
    out = {**led, "generated_by": led["generated_by"] + " + s_arbiter (ſ-faithful in-agent arbiter, Tier C2)",
           "n_open": len(entries), "blocks_deliverable": bool(entries),
           "by_reason": {r: sum(1 for e in entries if e["reason"] == r) for r in sorted({e["reason"] for e in entries})},
           "s_debts_closed_by_arbiter": closed, "entries": entries}
    (OUT / "_open_ledger.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def render(res: dict) -> list:
    """Rasterise each residue crop once, at high resolution, for the in-session visual read.

    Distinct crops are deduped: several residue tokens usually share one region crop, and reading the band once
    settles all of them. The PNG is the ONLY evidence admitted for a `vision-observed` glyph."""
    import reocr_r3
    OUT.mkdir(exist_ok=True)
    seen, out = {}, []
    for r in res["residue"]:
        key = (r["slug"], tuple(r["crop"] or ()))
        if key in seen or not r["crop"]:
            if key in seen:
                seen[key]["tokens"].append(f"{r['locus']}#{r['i']}={r['token']}")
            continue
        rec = _cached()[r["locus"]]
        png = OUT / f"crop-{r['slug']}-{len(seen):02d}.png"
        reocr_r3._render_page_png(rec["ocr_dir"], rec["page_index"], str(png), maxw=2600, crop=r["crop"])
        seen[key] = {"png": str(png), "slug": r["slug"], "crop": r["crop"],
                     "tokens": [f"{r['locus']}#{r['i']}={r['token']}"]}
        out.append(seen[key])
    (OUT / "_crops.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true", help="re-run the debt pages and persist texts (needs MLX)")
    ap.add_argument("--transfer", action="store_true", help="surface transfer + verdicts (offline)")
    ap.add_argument("--render", action="store_true", help="rasterise the residue crops for the visual read")
    ap.add_argument("--apply", metavar="READINGS.json", help="fold in-session visual readings, then re-verdict")
    ap.add_argument("slugs", nargs="*")
    a = ap.parse_args(argv)

    d = debts()
    if a.extract:
        for slug, want in sorted(d.items()):
            if a.slugs and slug not in a.slugs:
                continue
            print(f"[extract] {slug}: {len(want)} debt(s)", flush=True)
            extract(slug, want)
    if a.transfer or a.apply or a.render:
        readings = json.loads(Path(a.apply).read_text()) if a.apply else None
        res = transfer_all(readings)
        print(json.dumps(res["summary"], indent=1))
        for r in res["residue"]:
            print(f"  RESIDUE {r['locus']:>22}  tok[{r['i']}] = {r['token']!r}")
        if a.apply:
            L = rewrite_ledger(res)
            print("LEDGER", json.dumps({"n_open": L["n_open"], "closed_by_arbiter": len(L["s_debts_closed_by_arbiter"]),
                                        "by_reason": L["by_reason"]}, indent=1))
        if a.render:
            for c in render(res):
                print(f"  CROP {c['png']}  <- {', '.join(c['tokens'])}")
    if not (a.extract or a.transfer or a.apply or a.render):
        print(json.dumps({s: len(v) for s, v in sorted(d.items())}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
