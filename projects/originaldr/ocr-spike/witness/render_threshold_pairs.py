"""Render the SAME leaf at two detection floors, side by side.

The claim under test is visual, so it is delivered as a picture (Masterplan §0.2a).
Left panel = what the pipeline sees today at FAST_LAYOUT_CONFIDENCE_THRESHOLD = 0.40.
Right panel = the same forward pass, kept at 0.10. Nothing else differs: one detector,
one image, one inference; only the floor applied to the returned scores.

  rubric #A32B22  a detection whose area >= 0.25 of the leaf  (a BODY BLOCK)
  slate  #3A5A6B  every other detection
  each body block is captioned with its own score

  ../ocr-venv/bin/python witness/render_threshold_pairs.py --out DIR
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PLATES = HERE / "plates"
SLATE, RUBRIC = "#3A5A6B", "#A32B22"
BODY_AREA = 0.25
W = 620

# leaf, floor-pair, why it is here
PAIRS = [
    ("OT1-1609-P_1011", "recovered", "Nehemias. Body scores 0.3934 -- cut by 0.0066."),
    ("OT2-1610-P_0024", "recovered", "Psalms. Body scores 0.3953 -- cut by 0.0047."),
    ("OT2-1610-P_0666", "recovered", "Lamentations acrostic. Body area 0.918 at score 0.2287."),
    ("NT-1582-B_0009", "residue", "Lowering the floor does NOT help: nothing over 0.24 is ever proposed."),
    ("NT-1582-B_0032", "residue", "Same. The largest proposal is 0.239 at score 0.962 -- confident, and small."),
]


def draw(img, dets, floor):
    im = img.copy()
    w, h = im.size
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    except Exception:
        f = ImageFont.load_default()
    keep = [x for x in dets if x["score"] > floor]
    nbody = 0
    for x in keep:
        box = [x["x0"] * w, x["y0"] * h, x["x1"] * w, x["y1"] * h]
        if x["area"] >= BODY_AREA:
            nbody += 1
            d.rectangle(box, outline=RUBRIC, width=4)
            t = f"{x['label']} {x['score']:.4f}"
            tb = d.textbbox((0, 0), t, font=f)
            d.rectangle([box[0], max(0, box[1] - 19), box[0] + tb[2] + 8, max(0, box[1] - 19) + 19],
                        fill=RUBRIC)
            d.text((box[0] + 4, max(0, box[1] - 19)), t, fill=(255, 255, 255), font=f)
        else:
            d.rectangle(box, outline=SLATE, width=2)
    return im, len(keep), nbody


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path.cwd() / "threshold-pairs"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    bundle = {p["id"]: p for p in json.loads((PLATES / "bundle.json").read_text())["plates"]}
    from surya.fast_layout import FastLayoutPredictor
    pred = FastLayoutPredictor()

    meta = []
    for lid, kind, why in PAIRS:
        p = bundle[lid]
        img = Image.open(PLATES / p["img"]).convert("RGB")
        iw, ih = img.size
        res = pred([img], threshold=0.01)[0]
        dets = []
        for b in res.bboxes:
            x0, y0, x1, y1 = b.bbox
            dets.append({"x0": x0 / iw, "y0": y0 / ih, "x1": x1 / iw, "y1": y1 / ih,
                         "area": max(0., (x1 - x0) / iw) * max(0., (y1 - y0) / ih),
                         "score": float(getattr(b, "confidence", None) or 0.0),
                         "label": b.label})
        small = img.resize((W, round(ih * W / iw)), Image.LANCZOS)
        row = {"id": lid, "kind": kind, "why": why}
        for tag, floor in (("live", 0.40), ("low", 0.10)):
            im, n, nb = draw(small, dets, floor)
            fn = out / f"{lid}_{tag}.jpg"
            im.save(fn, "JPEG", quality=52, optimize=True, progressive=True)
            row[tag] = {"boxes": n, "body": nb, "file": fn.name}
            print(f"  {lid:<22} {tag:<5} floor {floor:.2f}  {n:>3} boxes  {nb} body")
        meta.append(row)
    (out / "pairs.json").write_text(json.dumps(meta, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
