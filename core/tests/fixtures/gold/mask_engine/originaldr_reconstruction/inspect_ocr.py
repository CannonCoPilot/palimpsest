#!/usr/bin/env python3
"""Manual inspector for the diplomatic OCR output as it streams in (read-only; no torch).

    core/.venv/bin/python inspect_ocr.py progress
        per-line page counts + long-ſ density + newest-page timestamp (watch the run advance).

    core/.venv/bin/python inspect_ocr.py page archive-ot1-1609 0026
        region-typed dump of ONE page: BODY (scripture) lines vs MARGIN (apparatus) lines,
        long-ſ shown literally, so you can eyeball segmentation + diplomatic fidelity.

    core/.venv/bin/python inspect_ocr.py book archive matthew [--limit 12]
        run the real detect on ONE book against whatever pages exist right now, printing each
        attested verse's diplomatic surface + the attestation rate. (line = archive | annas)

Reuses detect_our_ocr.py's region-typing + attestation, so what you see is what the witness
will store. Runs under core/.venv (pure JSON reads); the OCR run itself is untouched.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import detect_our_ocr as D  # type: ignore[import]  # noqa: E402  — region-typing + attestation reused


def _band_and_width(alias: str, lines: list[dict]) -> tuple[tuple[float, float], float]:
    band = D._GEOM_BODY.get(alias, D.DEFAULT_BODY)
    gw = D._GEOM_WIDTH.get(alias)
    width = float((gw * 2) if gw else max((l["bbox"][2] for l in lines), default=1)) or 1.0
    return band, width


def cmd_progress(args: argparse.Namespace) -> int:
    root = D.DIPL_ROOT
    dirs = sorted(d for d in root.glob("*-*") if d.is_dir())
    if not dirs:
        print(f"(no diplomatic-OCR dirs yet under {root})")
        return 0
    print(f"{'line-dir':30s} {'pages':>6s} {'ſ (sampled)':>12s}   newest page")
    grand = 0
    for d in dirs:
        pages = [p for p in d.glob("*.json") if not p.name.startswith("_")]
        grand += len(pages)
        s = sum(p.read_text(errors="replace").count("ſ") for p in pages[: args.sample])
        newest = max((p.stat().st_mtime for p in pages), default=0)
        ts = time.strftime("%H:%M:%S", time.localtime(newest)) if newest else "—"
        print(f"{d.name:30s} {len(pages):>6d} {s:>12,}   {ts}  (last {min(len(pages), args.sample)}pg)")
    print(f"{'TOTAL':30s} {grand:>6d}   / ~6116 archive pages")
    return 0


def cmd_page(args: argparse.Namespace) -> int:
    d = D.DIPL_ROOT / args.dir
    if not d.is_dir():
        raise SystemExit(f"no such line dir: {d}  (try `progress`)")
    hits = sorted(p for p in d.glob("*.json")
                  if not p.name.startswith("_") and args.page in p.name)
    if not hits:
        raise SystemExit(f"no page matching {args.page!r} in {args.dir}")
    import json
    doc = json.loads(hits[0].read_text(errors="replace"))
    lines = doc.get("lines", [])
    alias = args.dir.split("-", 1)[1] if "-" in args.dir else args.dir
    band, width = _band_and_width(alias, lines)
    body, margin = [], []
    for l in lines:
        b = l["bbox"]
        frac = ((b[0] + b[2]) / 2.0) / width
        (body if band[0] <= frac <= band[1] else margin).append((b[1], b[0], l.get("text", "")))
    body.sort(); margin.sort()
    print(f"# {hits[0].name}")
    print(f"# band x∈[{band[0]},{band[1]}] width≈{width:.0f}px · {len(body)} body / {len(margin)} margin lines")
    print(f"\n=== BODY (scripture) ===")
    for _, _, t in body:
        print(f"  {t}")
    print(f"\n=== MARGIN (apparatus) ===")
    for _, _, t in margin:
        print(f"  {t}")
    return 0


def cmd_book(args: argparse.Namespace) -> int:
    prefix = D.LINE_PREFIX[args.line]
    streams = {}
    for d in sorted(D.DIPL_ROOT.glob(f"{prefix}*")):
        if not d.is_dir():
            continue
        a = d.name[len(prefix):]
        if D.is_nt_alias(a) == (D._BOOK_TESTAMENT.get(args.book) == "NT"):
            streams[a] = D.load_stream(d, a, 2)
    if not streams:
        raise SystemExit(f"no {args.line} streams loaded for {args.book} — has OCR reached it?")
    anchor = D.anchor_by_book(D.load_anchor())
    chapters = anchor.get(args.book)
    if not chapters:
        raise SystemExit(f"no modern anchor for book {args.book!r}")
    reads, app, stats = D.detect_book(args.book, chapters, args.line, streams)
    print(f"# {args.book} via {args.line}: alias={stats['alias'] or '—'} "
          f"attested={stats['attested_verses']}/{stats['expected_verses']} "
          f"({stats['attestation_rate']}) agree={stats['folded_agreement_vs_anchor']} "
          f"apparatus_chapters={stats['apparatus_chapters']}")
    for r in reads[: args.limit]:
        print(f"  {r['skeleton_id']:28s} [{r['local_confidence']:8s}] {r['surface'][:110]}")
    if app:
        print(f"\n  apparatus sample: {app[0]['skeleton_id']} → {app[0]['surface'][:100]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="inspect diplomatic OCR output")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("progress"); p.add_argument("--sample", type=int, default=150)
    p = sub.add_parser("page"); p.add_argument("dir"); p.add_argument("page")
    p = sub.add_parser("book")
    p.add_argument("line", choices=sorted(D.LINE_PREFIX)); p.add_argument("book")
    p.add_argument("--limit", type=int, default=12)
    args = ap.parse_args()
    return {"progress": cmd_progress, "page": cmd_page, "book": cmd_book}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
