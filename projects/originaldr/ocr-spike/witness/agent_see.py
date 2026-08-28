#!/usr/bin/env python3
"""R14.7 -- DRAW WHAT THE AGENT SEES, on the actual leaf.

Sir, 2026-08-26: *"I really really need to SEE what's being done on these leafs. If we're talking
about rows, boxes, leans, classes and archetypes, I really really need this incremental work
accompanied by intermittent visual diagrams of what the pipeline sees and does in plain terms right
on the pages."*

⚠️ AND IT IS NOT A COURTESY. This project has spent four span rules and five pre-registered bars on
a boundary problem, and every one of those was reasoned about in NUMBERS. `region_head` scores
MarginNote 17/19 and Surya scores 0/19 on the same 19 entries -- a reader of either number alone
cannot tell what either model is actually doing to the page. A picture of the SAME decision the
scorer scored is the cheapest possible defence against optimising a metric off the page.

WHAT IS DRAWN, and it is drawn from the AGENT'S OWN OUTPUT, never from a parallel reimplementation
(that would be the R14.0 defect: a second code path that can silently disagree with the first):

  the MEASURE          two vertical rules -- the body column the agent derived FROM THIS LEAF. Every
                       naming cue is relative to these, so if they are wrong, everything is wrong,
                       and that is visible at a glance rather than after a scoring run.
  the HEAD FLOOR       one horizontal rule at the top of the body block.
  each REGION          a box in its class colour, captioned `LABEL conf CAUSE` in plain terms.
  each GOLD entry      a thin dashed box. Where the agent AGREES it is quiet; where it DISAGREES the
                       gold box is drawn in red and captioned `gold: X / agent: Y`.
  the ARCHETYPE        printed at the head of the page with the evidence that decided it.

    ../ocr-venv/bin/python witness/agent_see.py              # all cached leaves -> PNG + index.html
    ../ocr-venv/bin/python witness/agent_see.py 412 403      # only these leaves

Output: `witness/see/leaf-NNN.png` and `witness/see/index.html`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W                                                   # noqa: E402
import visual_agent as VA                                               # noqa: E402
from score_head_regions import GOLD                                     # noqa: E402

OUT = _HERE / "see"
WIDTH = 1100          # render width; the leaf is scaled to this so captions stay legible

COLOUR = {
    "RH": (0, 140, 255),      # running head — blue
    "MN": (255, 0, 170),      # marginal note — magenta, the class this edition is built around
    "MT": (40, 180, 60),      # main text — green
    "CH": (255, 150, 0),      # chapter head — orange
    # R14.10a. ⚠️ DELIBERATELY FAR FROM BOTH `MT` AND `CH` IN HUE, because those are the two names
    # this class was misfiled into and the drawing has to make the correction legible at a glance.
    "AR": (150, 60, 220),     # the chapter's argument — violet
    "SG": (110, 90, 60),      # gathering signature — brown, foot furniture
    "CW": (110, 90, 60),      # catchword — the same, it is the same band
    "??": (150, 150, 150),    # abstention — grey, and it must LOOK like an abstention
}
PLAIN = {
    "RH": "running head",
    "MN": "MARGINAL NOTE",
    "MT": "body text",
    "CH": "chapter heading",
    "AR": "ARGUMENT (italic)",
    "SG": "gathering signature",
    "CW": "catchword",
    "??": "ABSTAINED",
}


def _font(sz):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def _label(dr, xy, text, fill, font, bg=(255, 255, 255)):
    x, y = xy
    try:
        box = dr.textbbox((x, y), text, font=font)
        dr.rectangle([box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2], fill=bg)
    except Exception:
        pass
    dr.text((x, y), text, fill=fill, font=font)


def draw_leaf(lf, gold_entries, leaves_paths) -> Path:
    from PIL import Image, ImageDraw

    im = Image.open(str(leaves_paths[lf.leaf])).convert("RGB")
    w0, h0 = im.size
    scale = WIDTH / w0
    im = im.resize((WIDTH, int(h0 * scale)))
    Wp, Hp = im.size
    # A pale wash so the ink does not fight the overlay; the page is still legible underneath.
    im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.45)
    dr = ImageDraw.Draw(im)
    f_big, f_med, f_sm = _font(21), _font(15), _font(12)

    ml, mr = lf.measure

    # ---- the frame the agent derived FROM THIS LEAF
    for x, tag in ((ml, "measure L"), (mr, "measure R")):
        px = x * Wp
        dr.line([(px, 0), (px, Hp)], fill=(0, 0, 0), width=2)
        _label(dr, (px + 4, Hp - 26), tag, (0, 0, 0), f_sm)
    hy = lf.head_y * Hp
    dr.line([(0, hy), (Wp, hy)], fill=(120, 0, 200), width=2)
    _label(dr, (6, hy + 3), "head floor — top of the body block", (120, 0, 200), f_sm)

    # ---- what the agent decided, box by box
    for b in lf.boxes:
        c = COLOUR.get(b.label, (0, 0, 0))
        x0, y0, x1, y1 = b.x0 * Wp, b.y0 * Hp, b.x1 * Wp, b.y1 * Hp
        wdt = 4 if b.label in ("MN", "AR") else 2
        dr.rectangle([x0, y0, x1, y1], outline=c, width=wdt)
        _label(dr, (x0 + 3, max(0, y0 - 17)),
               f"{PLAIN.get(b.label, b.label)}  {b.conf:.2f}", c, f_med)
        if b.label in ("MN", "??", "CH", "AR"):
            _label(dr, (x0 + 3, y1 + 2), b.cause[:78], c, f_sm)

    # ---- the gold, and every disagreement called out in red
    agree = disagree = 0
    for e in gold_entries:
        gx0, gy0 = e["xlf"] * Wp, e["y0f"] * Hp
        gx1, gy1 = e["xrf"] * Wp, e["y1f"] * Hp
        b, _ = VA._bind(e, lf.boxes)
        got = b.label if b else "—"
        if got == e["label"]:
            agree += 1
            dr.rectangle([gx0, gy0, gx1, gy1], outline=(120, 120, 120), width=1)
        else:
            disagree += 1
            dr.rectangle([gx0 - 2, gy0 - 2, gx1 + 2, gy1 + 2], outline=(220, 0, 0), width=3)
            _label(dr, (gx1 + 5, gy0), f"gold {e['label']} / agent {got}", (220, 0, 0), f_sm)

    # ---- the header strip: archetype, evidence, tally
    strip = 78
    from PIL import Image as _I
    canvas = _I.new("RGB", (Wp, Hp + strip), (255, 255, 255))
    canvas.paste(im, (0, strip))
    dr2 = ImageDraw.Draw(canvas)
    arch_name = VA.ARCHETYPES.get(lf.archetype, {}).get("name", "?")
    dr2.text((10, 6), f"leaf {lf.leaf}   ARCHETYPE {lf.archetype} — {arch_name}  "
                      f"(confidence {lf.arch_conf:.2f})", fill=(0, 0, 0), font=f_big)
    dr2.text((10, 32), f"decided because: {lf.arch_cause}", fill=(60, 60, 60), font=f_med)
    dr2.text((10, 52), f"gold on this leaf: {agree} agree · {disagree} DISAGREE     "
                       f"boxes seen: {len(lf.boxes)}", fill=(180, 0, 0) if disagree else (0, 120, 0),
             font=f_med)

    OUT.mkdir(exist_ok=True)
    p = OUT / f"leaf-{lf.leaf}.png"
    canvas.save(p)
    return p


def main() -> int:
    want = [int(a) for a in sys.argv[1:] if a.isdigit()]
    leaves = {lf.leaf: lf for lf in VA.load_leaves()}
    gold = json.loads(GOLD.read_text())
    by_leaf: dict[int, list] = {}
    for e in gold["labels"]:
        if "xlf" in e:
            by_leaf.setdefault(e["leaf"], []).append(e)

    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == VA.WITNESS][0]
    paths = W.leaves(vol, sig)

    todo = want or sorted(leaves)
    rows = []
    for i in todo:
        lf = leaves.get(i)
        if lf is None:
            print(f"  leaf {i}: not in the perception cache — skipped")
            continue
        ents = by_leaf.get(i, [])
        p = draw_leaf(lf, ents, paths)
        dis = sum(1 for e in ents
                  if (lambda b: (b.label if b else "—"))(VA._bind(e, lf.boxes)[0]) != e["label"])
        rows.append((i, lf, len(ents), dis, p))
        print(f"  leaf {i}: archetype {lf.archetype:2s}  {len(lf.boxes):2d} boxes  "
              f"{len(ents):2d} gold  {dis:2d} disagree  -> {p.name}")

    # An index, so the twenty pages can be read as a sequence rather than opened one at a time.
    html = ["<meta charset='utf-8'><title>what the agent sees</title>",
            "<style>body{font:14px/1.5 system-ui;margin:2rem;background:#111;color:#eee}"
            "img{width:100%;border:1px solid #444;margin:.5rem 0}"
            "h2{margin-top:2rem}.bad{color:#f66}.ok{color:#6f6}</style>",
            "<h1>What the adaptive visual agent sees</h1>",
            "<p>Black rules = <b>the measure</b>, derived from this leaf's own boxes. "
            "Purple rule = top of the body block. Coloured boxes = the agent's call, captioned with "
            "its confidence and its reason. Thin grey boxes = gold it agreed with. "
            "<span class=bad>Red boxes = gold it got wrong.</span></p>"]
    for i, lf, n, dis, p in rows:
        cls = "bad" if dis else "ok"
        html.append(f"<h2>leaf {i} — archetype {lf.archetype} "
                    f"({VA.ARCHETYPES.get(lf.archetype, {}).get('name', '?')}) "
                    f"— <span class={cls}>{dis} of {n} wrong</span></h2>")
        html.append(f"<p><i>{lf.arch_cause}</i></p><img src='{p.name}'>")
    (OUT / "index.html").write_text("\n".join(html))
    print(f"\n{len(rows)} leaf diagram(s) -> {OUT.relative_to(_HERE.parent)}/  (open index.html)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
