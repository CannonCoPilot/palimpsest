#!/usr/bin/env python
"""Mask-detection evaluation harness for the Palimpsest *Detect* pipeline.

Drives the REAL pipeline (``ingest_file`` -> ``detect_layout_sections``) on each
EPUB under ``imports/`` (full corpus, recursive) and scores the resulting mask
elements against four criteria:
  (1) localization precision  — do interval start/stop land on real boundaries?
  (2) categorical accuracy     — does each element's type match its text?
  (3) coverage                 — is body text left untyped that should be typed?
  (4) metadata richness        — do elements carry structured metadata?

Ingest (slow) is cached on disk; eval (fast) re-runs detection every iteration,
so refining ``layout.py`` only needs an ``eval`` pass, not a re-ingest. Cached
Bible ingests from the prior Bibles-only run are reused (matched by source_file).

Usage:
  harness.py order                 # print the fixed randomized work order
  harness.py ingest [idx|all]      # Step 1: ingest EPUB(s) into the eval workspace
  harness.py eval   [idx|all]      # Steps 2-4: detect + score (writes diagnostics)
  harness.py report                # regenerate the cross-work markdown report
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from pathlib import Path

# R11.1: this file is TRACKED and lives at core/tests/fixtures/gold/harness/.
# Its ~2 GB of ingest workspaces and diagnostics are NOT, and stay machine-local.
CODE = Path(__file__).resolve().parent
REPO = CODE.parents[4]  # harness -> gold -> fixtures -> tests -> core -> repo root
sys.path.insert(0, str(REPO / "core"))

from palimpsest.layout import (  # noqa: E402
    DEFAULT_MASK_BY_TYPE,
    _STRUCTURAL,
    detect_layout_sections,
    masked_intervals,
)
from palimpsest.project import Project, ingest_file  # noqa: E402
from palimpsest.masking import _endnote_separator, _layout_boundaries  # noqa: E402

# ── Machine-local DATA root (outputs; overridable) ────────────────────────────
# Separate from CODE so the harness is checkable on any checkout (§0.2 rule 6).
# Absence RAISES with the path named -- it must never degrade to an empty result
# and report it as a clean one (R1.4, and `_empty_because` in §1.4).
DATA = Path(os.environ.get("MASK_EVAL_DATA", REPO / ".scratch" / "mask-eval")).resolve()


def require_data() -> Path:
    """The data root, or a raise that names it and says how to point elsewhere."""
    if not DATA.is_dir():
        raise FileNotFoundError(
            f"mask-eval DATA root not found: {DATA}\n"
            f"It holds ingest workspaces and diagnostics (~2 GB) and is machine-local "
            f"by design -- only the code beside this file is tracked.\n"
            f"Set MASK_EVAL_DATA=/path/to/mask-eval to point at it elsewhere."
        )
    return DATA


WS = DATA / "ws"
DIAG = DATA / "diagnostics"
IMPORTS = REPO / "imports"  # full corpus (recursive), not just Bibles
REPORT = DATA / "report.md"
# The idx -> work pin. ALREADY TRACKED at mask_engine/order.json since before R11,
# byte-identical to the copy that sat in .scratch -- so it is READ FROM THERE, not
# duplicated here. Regenerating it from a differently-populated imports/ silently
# renumbers every work, so every gold file keyed by idx would name a different book.
# (Two copies of one fact is the defect this project keeps re-finding: R7.5b, R9.6.)
ORDER_FILE = CODE.parent / "mask_engine" / "order.json"
SEED = 1729  # fixed: reproducible randomized order across sessions


# ── Work order ────────────────────────────────────────────────────────────────
def work_order() -> list[Path]:
    """Fixed seed-1729 randomized order over every EPUB under imports/.

    order.json stores import-relative POSIX paths (basenames collide across author
    folders); resolve each back to an absolute path here.
    """
    if ORDER_FILE.exists():
        return [IMPORTS / rel for rel in json.loads(ORDER_FILE.read_text())]
    # R11.1: regeneration is now EXPLICIT. The order is a seeded shuffle over
    # whatever imports/ happens to contain, so silently rebuilding it on a
    # differently-populated corpus renumbers every work -- and every gold file,
    # diagnostic and report keyed by idx would then name a different book while
    # continuing to look valid. A missing pin is refused, never recomputed.
    raise FileNotFoundError(
        f"order.json is missing: {ORDER_FILE}\n"
        f"It pins idx -> work for every gold file and is TRACKED; restore it from "
        f"git rather than regenerating.\n"
        f"To rebuild deliberately (this RENUMBERS every work): "
        f"harness.py rebuild-order"
    )


def rebuild_order() -> list[Path]:
    """Rebuild the seed-1729 order from imports/. Renumbers every work -- see above."""
    rels = sorted(p.relative_to(IMPORTS).as_posix() for p in IMPORTS.rglob("*.epub"))
    rng = random.Random(SEED)
    rng.shuffle(rels)
    ORDER_FILE.write_text(json.dumps(rels, indent=2, ensure_ascii=False))
    return [IMPORTS / rel for rel in rels]


def category(idx: int) -> str:
    """Top-level corpus bucket for a work (author folder, or Scripture/<sub>)."""
    rel = work_order()[idx].relative_to(IMPORTS).parts
    if rel and rel[0] in ("Scripture", "Bibles") and len(rel) > 2:
        return f"{rel[0]}/{rel[1]}"
    return rel[0] if rel else "?"


def short(name_or_path: str | Path) -> str:
    """A compact human handle for a verbose Anna's-Archive filename."""
    base = Path(name_or_path).name
    return base.split(" -- ")[0].strip()[:48]


# ── Ingest (cached) ─────────────────────────────────────────────────────────────
def ingest(idx: int, force: bool = False) -> Project:
    epub = work_order()[idx]
    WS.mkdir(parents=True, exist_ok=True)
    # ingest_file derives a deterministic slug; detect the existing project to skip.
    # Match by basename so the prior Bibles-only cache (source_file=basename) is reused.
    existing = [d for d in WS.iterdir() if d.is_dir() and (d / "metadata.json").exists()]
    for d in existing:
        meta = json.loads((d / "metadata.json").read_text())
        if meta.get("source_file") == epub.name and not force:
            return Project.load(d)
    proj = ingest_file(epub, WS, source_name=epub.name, overwrite=True)
    return proj


def project_for(idx: int) -> Project | None:
    epub = work_order()[idx]
    if not WS.exists():
        return None
    for d in WS.iterdir():
        if d.is_dir() and (d / "metadata.json").exists():
            meta = json.loads((d / "metadata.json").read_text())
            if meta.get("source_file") == epub.name:
                return Project.load(d)
    return None


# ── Scoring ─────────────────────────────────────────────────────────────────────
# Verse-ish leading number: "1 In the beginning", "23:4", "1. ". A proxy signal for
# scripture / translation density, NOT a parser.
_VERSE_RE = re.compile(r"(?:^|\n|\s)(\d{1,3})(?:[:.]\d{1,3})?[\s ]+[A-Z“‘(]")
_WS_RE = re.compile(r"\s+")


def verse_density(seg: str) -> float:
    """Verse-like markers per 1000 chars (scripture/translation proxy signal)."""
    if not seg:
        return 0.0
    return len(_VERSE_RE.findall(seg)) / (len(seg) / 1000.0)


def line_stats(seg: str) -> tuple[int, float]:
    lines = [ln for ln in seg.split("\n") if ln.strip()]
    if not lines:
        return 0, 0.0
    avg = sum(len(ln) for ln in lines) / len(lines)
    return len(lines), avg


def elem_flags(text: str, s) -> list[str]:
    """Precision / category flags for one element."""
    n = len(text)
    seg = text[s.start:s.end]
    flags: list[str] = []
    if s.start > 0 and text[s.start - 1].isalnum() and text[s.start].isalnum():
        flags.append("mid_word_start")
    if 0 < s.end < n and text[s.end - 1].isalnum() and text[s.end].isalnum():
        flags.append("mid_word_end")
    if s.type == "header":
        body = seg.strip()
        if "\n" in body:
            flags.append("header_multiline")
        if len(body) > 200:
            flags.append("header_too_long")
    nlines, avg = line_stats(seg)
    # TOC smell: many short lines packed together but typed as a real division.
    if s.type in _STRUCTURAL and nlines >= 8 and avg < 60 and (s.end - s.start) < 4000:
        flags.append("looks_like_toc")
    # Scripture sitting in a NON-structural container (front/back matter) is a real
    # miscategorization — scripture inside a chapter is correctly typed, so excluded.
    # (Genuinely-missing scripture is caught by uncovered-run verse density instead.)
    if s.type in ("front_matter", "back_matter") and verse_density(seg) >= 6 and (s.end - s.start) > 2000:
        flags.append("scripture_miscategorized")
    return flags


def uncovered_runs(sections, body_span: tuple[int, int]) -> list[tuple[int, int]]:
    """Spans inside the body not covered by any more-specific (non-body) element."""
    bs, be = body_span
    pts = sorted({bs, be} | {s.start for s in sections} | {s.end for s in sections})
    runs: list[tuple[int, int]] = []
    for a, b in zip(pts, pts[1:]):
        if a < bs or b > be or a >= b:
            continue
        covered = any(
            s.type != "body" and s.start <= a and s.end >= b for s in sections
        )
        if not covered:
            if runs and a - runs[-1][1] <= 1:
                runs[-1] = (runs[-1][0], b)
            else:
                runs.append((a, b))
    return runs


def evaluate(idx: int) -> dict:
    proj = project_for(idx)
    if proj is None:
        raise SystemExit(f"work {idx} not ingested yet — run: harness.py ingest {idx}")
    text = proj.reference_text()
    text_len = len(text)
    sections = detect_layout_sections(
        _layout_boundaries(proj), text_len, _endnote_separator(proj.path), text=text
    )
    by_type: dict[str, int] = {}
    for s in sections:
        by_type[s.type] = by_type.get(s.type, 0) + 1

    flagged = []
    for s in sections:
        fl = elem_flags(text, s)
        if fl:
            seg = text[s.start:s.end]
            flagged.append({
                "type": s.type, "start": s.start, "end": s.end, "len": s.end - s.start,
                "flags": fl, "label": s.label[:60],
                "head": _WS_RE.sub(" ", seg[:90]).strip(),
            })

    body = next((s for s in sections if s.type == "body"), None)
    body_span = (body.start, body.end) if body else (0, text_len)
    runs = uncovered_runs(sections, body_span)
    big_runs = sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:8]
    big_runs_info = [{
        "start": a, "end": b, "len": b - a,
        "verse_density": round(verse_density(text[a:b]), 1),
        "head": _WS_RE.sub(" ", text[a:b][:90]).strip(),
    } for a, b in big_runs]

    chapters = [s for s in sections if s.type == "chapter"]
    ch_with_num = sum(1 for s in chapters if s.metadata.get("number"))
    ch_with_name = sum(1 for s in chapters if s.metadata.get("name"))
    # Metadata richness = a chapter carries a number OR a descriptive name. Number-only
    # under-credits editions whose chapters are titled (e.g. "I Go to Sea"), which are
    # metadata-rich by name even though they have no chapter number.
    ch_with_meta = sum(
        1 for s in chapters if s.metadata.get("number") or s.metadata.get("name")
    )

    total = len(sections)
    n_precision = sum(
        1 for s in sections
        if any(f in ("mid_word_start", "mid_word_end", "header_multiline", "header_too_long")
               for f in elem_flags(text, s))
    )
    n_cat = sum(1 for f in flagged if any(x in ("looks_like_toc", "scripture_miscategorized") for x in f["flags"]))
    body_len = body_span[1] - body_span[0]
    uncovered_len = sum(b - a for a, b in runs)
    coverage = 1 - (uncovered_len / body_len) if body_len else 0.0

    precision_score = 100 * (1 - n_precision / total) if total else 0
    coverage_score = 100 * coverage
    metadata_score = 100 * (ch_with_meta / len(chapters)) if chapters else 100.0
    category_score = 100 * (1 - n_cat / total) if total else 0
    composite = round(0.3 * precision_score + 0.3 * coverage_score
                      + 0.2 * category_score + 0.2 * metadata_score, 1)

    mi = masked_intervals(sections, DEFAULT_MASK_BY_TYPE, text_len)
    masked_frac = sum(b - a for a, b in mi) / text_len if text_len else 0

    diag = {
        "idx": idx,
        "work": short(work_order()[idx].name),
        "category": category(idx),
        "file": work_order()[idx].name,
        "text_len": text_len,
        "n_sections": total,
        "by_type": by_type,
        "scores": {
            "composite": composite,
            "precision": round(precision_score, 1),
            "coverage": round(coverage_score, 1),
            "category": round(category_score, 1),
            "metadata": round(metadata_score, 1),
        },
        "counts": {
            "precision_violations": n_precision,
            "category_suspects": n_cat,
            "chapters": len(chapters),
            "chapters_with_number": ch_with_num,
            "chapters_with_name": ch_with_name,
            "uncovered_runs": len(runs),
            "uncovered_chars": uncovered_len,
            "masked_fraction": round(masked_frac, 3),
        },
        "biggest_uncovered": big_runs_info,
        "flagged": flagged[:40],
        "n_flagged": len(flagged),
    }
    DIAG.mkdir(parents=True, exist_ok=True)
    (DIAG / f"work-{idx}.json").write_text(json.dumps(diag, indent=2, ensure_ascii=False))
    return diag


# ── Report ───────────────────────────────────────────────────────────────────────
def build_report() -> str:
    diags = []
    for i in range(len(work_order())):
        p = DIAG / f"work-{i}.json"
        if p.exists():
            diags.append(json.loads(p.read_text()))
    lines = ["# Mask-Detection Eval — Cross-Work Report", ""]
    lines.append("| # | Work | cat | chars | secs | composite | prec | cover | cat | meta | masked% |")
    lines.append("|---|------|-----|-------|------|-----------|------|-------|-----|------|---------|")
    for d in diags:
        s = d["scores"]; c = d["counts"]
        lines.append(
            f"| {d['idx']} | {d['work']} | {d.get('category','?')} | {d['text_len']:,} | {d['n_sections']} | "
            f"**{s['composite']}** | {s['precision']} | {s['coverage']} | {s['category']} "
            f"| {s['metadata']} | {int(c['masked_fraction']*100)} |"
        )
    lines.append("")
    for d in diags:
        lines.append(f"## [{d['idx']}] {d['work']} ({d.get('category','?')})")
        lines.append(f"- types: `{d['by_type']}`")
        c = d["counts"]
        lines.append(
            f"- precision_violations={c['precision_violations']} category_suspects="
            f"{c['category_suspects']} chapters={c['chapters']} "
            f"(num {c['chapters_with_number']}/name {c['chapters_with_name']}) "
            f"uncovered_runs={c['uncovered_runs']} ({c['uncovered_chars']:,} chars)"
        )
        if d["biggest_uncovered"]:
            lines.append("- biggest uncovered runs:")
            for r in d["biggest_uncovered"][:5]:
                lines.append(f"    - [{r['start']}-{r['end']}] {r['len']:,}c vd={r['verse_density']} · {r['head'][:70]!r}")
        if d["flagged"]:
            lines.append(f"- flagged ({d['n_flagged']}); first few:")
            for f in d["flagged"][:6]:
                lines.append(f"    - {f['type']} [{f['start']}-{f['end']}] {f['flags']} · {f['head'][:60]!r}")
        lines.append("")
    REPORT.write_text("\n".join(lines))
    return "\n".join(lines[:14])


# ── CLI ──────────────────────────────────────────────────────────────────────────
def _resolve(arg: str) -> list[int]:
    return list(range(len(work_order()))) if arg == "all" else [int(arg)]


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "order"
    arg = sys.argv[2] if len(sys.argv) > 2 else "all"
    if cmd == "order":
        for i, p in enumerate(work_order()):
            print(f"{i:>3}: [{category(i)}] {short(p.name)}")
    elif cmd == "ingest":
        for i in _resolve(arg):
            proj = ingest(i)
            print(f"ingested {i}: {short(work_order()[i].name)} -> {len(proj.reference_text()):,} chars")
    elif cmd == "eval":
        for i in _resolve(arg):
            if project_for(i) is None:
                print(f"[{i}] {short(work_order()[i].name)}: SKIP (not ingested)")
                continue
            d = evaluate(i)
            print(f"[{i}] {d['work']}: composite={d['scores']['composite']} "
                  f"(prec {d['scores']['precision']} cover {d['scores']['coverage']} "
                  f"cat {d['scores']['category']} meta {d['scores']['metadata']}) "
                  f"secs={d['n_sections']} flagged={d['n_flagged']}")
        build_report()
    elif cmd == "report":
        print(build_report())
    elif cmd == "rebuild-order":
        rels = rebuild_order()
        print(f"REBUILT {ORDER_FILE} over {len(rels)} works -- every idx may now "
              f"name a different work; re-check every gold file keyed by idx.")
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
