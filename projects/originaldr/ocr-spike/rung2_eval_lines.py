#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_eval_lines.py — line-level CER / ſ-fidelity for a kraken recognizer, on PNG + .gt.txt pairs.

WHY NOT `ketos test`. It fails on this project's arrows with `ValueError: No test data in dataset` — the same
raw-bbox defect that makes `ketos train` report "No training data" (`im_transforms=None` reaching
`ArrowIPCRecognitionDataset.add`, documented at length in `rung2_finetune_kraken.py`). The data is fine; the CLI
path is not. So evaluation goes through the Python API on the line images directly, which also means the numbers
are computed on exactly the crops a training run would see.

TWO METRICS, because this project cares about two different things:
  * CONTENT — character accuracy over `fold_archaic` (ſ folded to s), i.e. did it read the letters;
  * SURFACE — ſ recall/precision against the target's ſ, i.e. did it read the ARCHAIC LONG S. A recognizer that
    silently modernizes ſ scores well on the first and is useless to this pipeline, which is why R3's otherwise
    better readings still need `s_arbiter`.

Usage:
  ../ocr-venv/bin/python rung2_eval_lines.py --model models/reichenau_dr.mlmodel --dir .rung2-chapters --split val
  ../ocr-venv/bin/python rung2_eval_lines.py --model A.mlmodel --model B.mlmodel --dir .rung2-chapters --split val
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None

from char_identity import edit_ratio, fold_archaic        # noqa: E402
from kraken import rpred                                 # noqa: E402
from kraken.containers import BaselineLine, Segmentation  # noqa: E402
from kraken.lib import models                            # noqa: E402


def _one_line_seg(im) -> Segmentation:
    """A single-line 'page' whose one line IS the whole crop — no segmentation, so the evaluation measures the
    RECOGNIZER and nothing else. (Segmentation quality is a separate axis, already measured elsewhere.)"""
    # THE POLYGON MUST BE STRICTLY INSIDE THE IMAGE. At (w, h) kraken rejects it with "Line polygon outside of
    # image bounds", the extraction returns nothing, and every line scores 0.000 — which reads exactly like a
    # useless model. Fifth instance this project has seen of a dead metric impersonating a verdict, so: 1px inset.
    w, h = im.size
    x0, y0, x1, y1 = 1, 1, w - 2, h - 2
    return Segmentation(
        type="baselines", imagename="crop", text_direction="horizontal-lr", script_detection=False,
        lines=[BaselineLine(id="l0", baseline=[(x0 + 1, int(h * 0.75)), (x1 - 1, int(h * 0.75))],
                            boundary=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)])])


def read_line(model, png: Path) -> str:
    im = Image.open(png).convert("L")
    recs = list(rpred.rpred(model, im, _one_line_seg(im)))
    return " ".join(str(r) for r in recs).strip()


def evaluate(model_path: Path, pairs: list[tuple[Path, str]]) -> dict:
    model = models.load_any(str(model_path))
    rows = []
    for png, gt in pairs:
        try:
            got = read_line(model, png)
        except Exception as e:                                     # noqa: BLE001
            print(f"  ! {png.name}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        rows.append({"png": png.name, "gt": gt, "got": got,
                     "content": edit_ratio(fold_archaic(got), fold_archaic(gt)),
                     "s_gt": gt.count("ſ"), "s_got": got.count("ſ")})
    if not rows:
        return {"n": 0}
    s_gt = sum(r["s_gt"] for r in rows)
    s_got = sum(r["s_got"] for r in rows)
    # ſ RECALL is computed per line and floored at the line's own target count, so a line that over-produces ſ
    # cannot pay for another line that dropped one — an aggregate ratio would hide exactly that.
    s_hit = sum(min(r["s_gt"], r["s_got"]) for r in rows)
    return {"n": len(rows), "content_mean": mean(r["content"] for r in rows),
            "content_median": sorted(r["content"] for r in rows)[len(rows) // 2],
            "cer": 1 - mean(r["content"] for r in rows),
            "s_gt": s_gt, "s_got": s_got,
            "s_recall": (s_hit / s_gt) if s_gt else None,
            "lines": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True, help="repeat to compare models")
    ap.add_argument("--dir", default=".rung2-chapters")
    ap.add_argument("--split", default="val", choices=["val", "train", "all"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--slugs", default="", help="restrict to these GT slugs (rung2_prepare manifests)")
    ap.add_argument("--ids-file", default="", help="JSON list of manifest ids — the exact lines to score, so an "
                    "evaluation can be restricted to the VERIFIED pairs a training val arrow was built from")
    ap.add_argument("--json-out")
    a = ap.parse_args()

    d = HERE / a.dir
    man_path = d / "_manifest.json"
    pairs: list[tuple[Path, str]] = []
    man = json.loads(man_path.read_text()) if man_path.exists() else None
    want = {x.strip() for x in a.slugs.split(",") if x.strip()} if a.slugs else None
    want_ids = set(json.loads(Path(a.ids_file).read_text())) if a.ids_file else None
    if isinstance(man, dict):
        # `rung2_chapter_pairs` format:each line carries its own leaf-level split
        for m in man["lines"]:
            if a.split != "all" and m.get("split") != a.split:
                continue
            png, gt = d / f"{m['stem']}.png", d / f"{m['stem']}.gt.txt"
            if png.exists() and gt.exists():
                pairs.append((png, gt.read_text().strip()))
    elif isinstance(man, list):
        # `rung2_prepare` format: a flat list of {id, slug, sim, text, kind}. There is no split in the file —
        # the split lives in `rung2_split_v2.py`, which holds out whole GT FILES — so selection is by `--slugs`.
        for m in man:
            if want is not None and m["slug"] not in want:
                continue
            if want_ids is not None and m["id"] not in want_ids:
                continue
            png = d / f"line_{m['id']:04d}.png"
            gt = d / f"line_{m['id']:04d}.gt.txt"
            if png.exists() and gt.exists():
                pairs.append((png, gt.read_text().strip()))
    else:
        for png in sorted(d.glob("*.png")):
            gt = png.with_suffix("").with_suffix(".gt.txt")
            if gt.exists():
                pairs.append((png, gt.read_text().strip()))
    if a.limit:
        pairs = pairs[:a.limit]
    print(f"[eval] {len(pairs)} lines from {a.dir} (split={a.split})\n")
    out = {}
    for mp in a.model:
        p = Path(mp) if Path(mp).is_absolute() else HERE / mp
        print(f"=== {p.name} ===")
        r = evaluate(p, pairs)
        if not r.get("n"):
            print("  no lines evaluated")
            continue
        print(f"  lines            {r['n']}")
        print(f"  content accuracy {r['content_mean']:.4f}   (CER {r['cer']:.4f}, median "
              f"{r['content_median']:.4f})")
        print(f"  ſ in targets     {r['s_gt']}   ſ produced {r['s_got']}   ſ recall "
              f"{('%.4f' % r['s_recall']) if r['s_recall'] is not None else '-'}")
        worst = sorted(r["lines"], key=lambda x: x["content"])[:3]
        for w in worst:
            print(f"    worst {w['content']:.3f}  GT  {w['gt'][:72]}")
            print(f"                 GOT {w['got'][:72]}")
        out[p.name] = {k: v for k, v in r.items() if k != "lines"}
        out[p.name]["lines"] = r["lines"]
    if a.json_out:
        (HERE / a.json_out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"\n[wrote] {a.json_out}")
    if len(out) > 1:
        names = list(out)
        print("\n=== HEAD-TO-HEAD (same lines, same crops) ===")
        for n in names:
            print(f"  {n:<34} content {out[n]['content_mean']:.4f}  ſ recall "
                  f"{out[n]['s_recall'] if out[n]['s_recall'] is None else round(out[n]['s_recall'], 4)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
