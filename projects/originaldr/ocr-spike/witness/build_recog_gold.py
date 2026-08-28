#!/usr/bin/env python3
"""R2.1b -- cut the FIXED SELECTION SET: one line crop per printed line, named by region class.

⚠️ WHY THIS HAS TO BE HAND-KEYED, AND WHY THE OBVIOUS SHORTCUT IS POISON. GOLD-HEADBAND carries a
`text` field for all 121 of its entries and it is tempting to score CER against it. **It is the
INCUMBENT RECOGNISER'S OUTPUT**, kept so a human could assign a LABEL to each token -- the gold's own
`_doc` says so (*"tokens the recogniser returned empty for are NOT labelled"*), and its errors are
visible on inspection: leaf 402's running head reads `NVMENE` for NVMERI, leaf 400's side-note reads
`X. Og Alaine.` where the page prints `K. Og ſlaine.` Scoring five candidate recognisers against that
would measure AGREEMENT WITH THE INSTRUMENT BEING REPLACED and read as validation -- the identical
defect `audit_label_sources.py` records for `scan_marginal`. **So truth is keyed from the page.**

⚠️ AND THE SELECTION SET IS CUT PER REGION CLASS, WHICH IS A DEPARTURE FROM R2.1b AS FILED AND IS
ARGUED RATHER THAN SLIPPED IN. That row says the model is chosen *"on measured CER over
direction-line tokens"* -- signature and catchword, two tokens a page. But R13.1 wires the chosen
model into an arm that must read scripture, running heads, side-notes and section heads, and R14.10b/c
need it to answer *"is this a numeral"* and *"is this head ANNOTATIONS or CHAP."*. **Selecting on a
two-token-a-page population and deploying on all of them is measuring the wrong population** -- this
project's most repeated defect. R14.4 already states the remedy as policy: *recognition reported PER
REGION CLASS, never as one page figure.* This file cuts every class and the scorer never pools them.

WHAT IS CUT. For each declared leaf, the agent names the boxes (S1-S4); `collation_read` supplies the
printed rows; each row is assigned to the SMALLEST box containing it -- the same nesting rule
`attach_fount` uses, and for the same reason. Crops are taken at NATIVE page resolution, never from
the 1400-wide band, because a band-scale line is ~40px tall and a recogniser handed that is being
tested on the resampling.

    ../ocr-venv/bin/python witness/build_recog_gold.py           # cut crops + keying sheets
    ../ocr-venv/bin/python witness/build_recog_gold.py --check   # report keying progress

⚠️ THE `.gt.txt` FILES ARE EMITTED EMPTY and the manifest records `keyed: false`. Nothing may be
scored until they are keyed; `score_recognisers.py` refuses to run on an unkeyed set rather than
scoring against blanks, which would report a perfect failure as a perfect score.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import witnesses as W                    # noqa: E402
import collation_read as CR              # noqa: E402
import visual_agent as VA                # noqa: E402

OUT = _HERE / "recog-gold"
SHEETS = OUT / "sheets"
MANIFEST = OUT / "_manifest.json"

# How many lines per region class. ⚠️ CAPPED PER CLASS ON PURPOSE: MainText outnumbers every other
# class on the page by an order of magnitude, so an uncapped cut would be a scripture benchmark
# wearing a per-class label, and the classes the confirming read actually needs would be noise.
CAPS = {VA.MT: 12, VA.MN: 12, VA.AR: 12, VA.RH: 10, VA.CH: 8, VA.SIG: 6, VA.CAT: 6}
PAD_X, PAD_Y = 0.009, 0.004      # page fractions of padding. ⚠️ PAD_X was 0.004 and CLIPPED the
                                 # leading glyph of a line ("eople of Chamos"): `glyph_boxes` can
                                 # miss a partly-inked first sort, and a crop that cuts a character
                                 # asks every model to read something the page does not print.
                                 # 0.009 of page width is ~28px, far under the region gap (one line
                                 # pitch, ~90px), so it cannot re-admit a neighbouring region.


def cut() -> int:
    from PIL import Image
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == VA.WITNESS][0]
    paths = W.leaves(vol, sig)
    leaves = {lf.leaf: lf for lf in VA.load_leaves()}

    OUT.mkdir(parents=True, exist_ok=True)
    SHEETS.mkdir(parents=True, exist_ok=True)
    taken: dict[str, int] = {}
    rows_out = []
    n = 0
    for i in sorted(leaves):
        lf = leaves[i]
        rows, frame, p, why = CR.page_type_rows(paths[i])
        if rows is None:
            print(f"  leaf {i}: ABSTAIN — {why}")
            continue
        im = Image.open(str(paths[i]))
        im.draft("RGB", (3200, 4500))
        im = im.convert("RGB")
        Wp, Hp = im.size
        # 🔴 SEGMENTS, NOT ROWS, AND THE FIRST CUT GOT THIS WRONG UNTIL A SHEET WAS LOOKED AT.
        # Cutting by ROW produced a crop labelled `RH` that actually held `8 · NVMERI. · K. Og
        # ſlaine. · Bala` — a page number, the running head AND a side-note, in one image. A row is
        # NOT HOMOGENEOUS IN REGION; that is `region_head`'s founding observation and the reason
        # `region_segments` exists, recorded there on exactly this population: *"leaf 414 row 0 is a
        # running head, a wide run of white, and a side-note. Read as one crop the recogniser
        # returned 'NVMERI.' and stopped."* A per-class selection set cut by row would have carried
        # three classes inside one crop and scored the recogniser on the boundary, not the class.
        segs = [s for r in rows for s in CR.region_segments(r, p)]
        for r in segs:
            x0 = CR.page_x_frac(frame, min(g[2] for g in r))
            x1 = CR.page_x_frac(frame, max(g[3] for g in r))
            y0 = CR.page_y_frac(frame, min(g[0] for g in r))
            y1 = CR.page_y_frac(frame, max(g[1] for g in r))
            cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            hold = [b for b in lf.boxes if b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1]
            if not hold:
                continue
            b = min(hold, key=lambda z: z.area)
            cls = b.label
            if cls not in CAPS or taken.get(cls, 0) >= CAPS[cls]:
                continue
            # ⚠️ A ROW TOO SHORT TO CARRY A CER IS NOT A LINE -- but the FLOOR IS PER CLASS, and
            # the first cut got that wrong in a way worth recording. A single floor of 4 glyphs
            # admitted 0 signatures and 1 catchword, because a gathering signature IS two or three
            # sorts (`Z z 2`) and a catchword is one word. That silently deleted R2.1b's ORIGINAL
            # population -- the direction line -- from the set built to serve R2.1b.
            # ⚠️ They are admitted here and their CHARACTER COUNTS are reported by the scorer, so
            # the smallness is visible rather than hidden: a CER over three characters is a real
            # number about very little, and the honest handling is to show the n, not to drop the
            # class or to let it pass as an equal.
            floor = 2 if cls in (VA.SIG, VA.CAT) else 4
            span = 0.01 if cls in (VA.SIG, VA.CAT) else 0.03
            if (x1 - x0) < span or len(r) < floor:
                continue
            taken[cls] = taken.get(cls, 0) + 1
            n += 1
            stem = f"line_{n:04d}"
            px = (max(0, int((x0 - PAD_X) * Wp)), max(0, int((y0 - PAD_Y) * Hp)),
                  min(Wp, int((x1 + PAD_X) * Wp)), min(Hp, int((y1 + PAD_Y) * Hp)))
            im.crop(px).save(OUT / f"{stem}.png")
            (OUT / f"{stem}.gt.txt").write_text("")
            rows_out.append({"stem": stem, "leaf": i, "cls": cls, "surya": b.surya,
                             "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                             "n_glyphs": len(r), "keyed": False})
        print(f"  leaf {i}: {sum(1 for e in rows_out if e['leaf'] == i)} crop(s)", flush=True)

    MANIFEST.write_text(json.dumps({
        "witness": VA.WITNESS,
        "_doc": ("R2.1b's FIXED SELECTION SET. Truth is HAND-KEYED from the page, never taken from "
                 "GOLD-HEADBAND's `text`, which is the incumbent recogniser's output. Held out from "
                 "all five models — see witness/audit_recog_holdout.py. Classes are the agent's."),
        "caps": CAPS, "lines": rows_out,
    }, indent=1))
    print(f"\n{n} crop(s) over {len(taken)} class(es): "
          + ", ".join(f"{k} {v}" for k, v in sorted(taken.items())))
    sheets()
    return 0


def sheets() -> None:
    """Render numbered keying sheets, so truth is keyed by READING THE PAGE, not a text field."""
    from PIL import Image, ImageDraw
    man = json.loads(MANIFEST.read_text())
    lines = man["lines"]
    per = 10
    Wd = 1500
    for s in range(0, len(lines), per):
        chunk = lines[s:s + per]
        ims = []
        for e in chunk:
            im = Image.open(OUT / f"{e['stem']}.png")
            sc = min(1.0, (Wd - 300) / im.width)
            ims.append(im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc)))))
        H = sum(i.height + 26 for i in ims) + 20
        sheet = Image.new("RGB", (Wd, H), (255, 255, 255))
        dr = ImageDraw.Draw(sheet)
        y = 10
        for e, im in zip(chunk, ims):
            dr.text((6, y + 6), f"{e['stem'][5:]} [{e['cls']}] leaf {e['leaf']}", fill=(200, 0, 0))
            sheet.paste(im, (250, y))
            y += im.height + 26
            dr.line([(0, y - 13), (Wd, y - 13)], fill=(220, 220, 220))
        p = SHEETS / f"sheet_{s // per + 1:02d}.png"
        sheet.save(p)
        print(f"  sheet -> {p.relative_to(_HERE)}  ({len(chunk)} lines)")


def check() -> int:
    """Report keying progress. ⚠️ AN EXCLUSION IS A STATE, NOT A MISSING FILE.

    A crop can be neither keyed nor pending: it can be REFUSED, because the cut produced something
    that is not a single printed line. Those carry a reason in the manifest and their `.gt.txt` is
    removed so no evaluator can pair them. Counting them as 'unkeyed' would make the set look
    perpetually unfinished; counting them as keyed would score against truth that was never written.
    """
    man = json.loads(MANIFEST.read_text())
    lines = man["lines"]

    def gt(e):
        p = OUT / f"{e['stem']}.gt.txt"
        return p.read_text().strip() if p.is_file() else ""

    per: dict[str, list[int]] = {}
    for e in lines:
        per.setdefault(e["cls"], [0, 0, 0])
        if e.get("excluded"):
            per[e["cls"]][2] += 1
            continue
        per[e["cls"]][1] += 1
        if gt(e):
            per[e["cls"]][0] += 1
    keyed = sum(v[0] for v in per.values())
    pend = sum(v[1] for v in per.values()) - keyed
    exc = sum(v[2] for v in per.values())
    print(f"R2.1b selection set: {keyed} keyed · {pend} pending · {exc} EXCLUDED "
          f"(of {len(lines)} cut)")
    print(f"{'cls':>5}  {'keyed':>6} {'of':>3} {'in-scope':>8}   excluded")
    for c in sorted(per):
        k, t, x = per[c]
        print(f"{c:>5}  {k:>6} {'/':>3} {t:>8}   {x}")
    print("\n  ⚠️ EXCLUSIONS ARE CROP DEFECTS, and each carries its reason in the manifest — two "
          "baselines\n     in one image, a clipped first or last sort, or two margin columns "
          "merged. Keying one\n     would invent truth no recogniser could produce and penalise "
          "all five for the cutter.")
    for e in lines:
        if e.get("excluded"):
            print(f"       {e['stem']} [{e['cls']}] leaf {e['leaf']}: {e['excluded']}")
    return 0 if pend == 0 else 1


if __name__ == "__main__":
    # 🔴 THE DEFAULT IS THE SAFE PATH, AND IT IS DEFAULT BECAUSE THE OTHER ONE DESTROYED THE WORK.
    # The verification standard runs every command it names WITHOUT ARGUMENTS -- `run()` invokes
    # `[PY, f"witness/{script}"]` and drops whatever the claim line wrote after the filename. This
    # file was enrolled as `build_recog_gold.py --check`, so the suite ran it BARE, took the cutting
    # path, and rewrote all 51 hand-keyed `.gt.txt` files as empty. The keying had to be redone.
    # ⚠️ A COMMAND IN THAT BLOCK IS A COMMAND WITHOUT ITS ARGUMENTS, so a script whose no-argument
    # behaviour is destructive WILL be run destructively. Cutting is now opt-in and refuses to
    # clobber existing truth even then; `--force` is the only way through, and it has to be typed.
    if "--cut" in sys.argv:
        keyed = [q for q in OUT.glob("*.gt.txt") if q.read_text().strip()] if OUT.is_dir() else []
        if keyed and "--force" not in sys.argv:
            print(f"🔴 REFUSING TO CUT: {len(keyed)} keyed truth file(s) already exist and cutting "
                  f"would blank them.\n   Re-cutting is only correct when the leaf set or the "
                  f"cutting rule changes, and it costs the keying.\n   Pass --force if that is "
                  f"genuinely what you mean.")
            raise SystemExit(1)
        raise SystemExit(cut())
    raise SystemExit(check())
