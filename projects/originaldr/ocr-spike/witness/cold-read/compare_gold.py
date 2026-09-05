"""Score the cold read against GOLD-HEADBAND (409, 412) and against the live bundle (all 5).

Gold entries are head-band ROWS with page-fraction extents. A gold entry is addressed to the
cold-read region with the largest area overlap, then labels are compared. Reported per entry so
a disagreement can be looked at rather than averaged away.

  ../ocr-venv/bin/python witness/cold-read/compare_gold.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parent
cold = json.loads((HERE / "cold-read.json").read_text())["leaves"]
gold = json.loads((W / "gold" / "head_regions_OT1-1609-B_400-419.json").read_text())
bundle = {p["id"]: p for p in json.loads((W / "plates" / "bundle.json").read_text())["plates"]}

# gold labels → cold-read classes
MAP = {"RH": "RH", "MN": "MN", "MT": "MT", "CH": "CH", "PN": "PN", "AR": "AR"}


def ov(a, b):
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return w * h


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


print("=== GOLD-HEADBAND vs cold read, per entry (leaves 409, 412) ===")
tot = hit = 0
for e in gold["labels"]:
    if "xlf" not in e or e["leaf"] not in (409, 412):
        continue
    lid = f"OT1-1609-B_{e['leaf']:04d}"
    gb = [e["xlf"], e["y0f"], e["xrf"], e["y1f"]]
    best, bo = None, 0.0
    for r in cold[lid]["regions"]:
        o = ov(gb, r["box"]) / max(1e-9, area(gb))
        if o > bo:
            best, bo = r, o
    got = best["class"] if best else "—"
    ok = got == MAP.get(e["label"], e["label"])
    tot += 1; hit += ok
    flag = "  " if ok else "🔴"
    print(f"{flag} {lid} row{e['row']} gold {e['label']:<3} cold {got:<3} cover {bo:.2f}  '{e['text'][:40]}'")
print(f"\nagreement {hit}/{tot}")

print("\n=== live bundle (Surya+cascade, post-R16.20) vs cold read, frame only ===")
for lid, c in cold.items():
    p = bundle[lid]
    m = p["measure"]
    print(f"{lid:<18} cold measure {c['measure']}  live {tuple(round(v,3) for v in m)}  "
          f"live head/foot {p['head_y']:.3f}/{p['foot_y']:.3f}  live archetype {p['archetype']}  "
          f"live boxes {len(p['boxes'])} (+{len(p.get('withheld', []))} withheld)")

print("\n=== live labels vs cold read on the same leaves: what the cascade called each of MY regions ===")
for lid, c in cold.items():
    p = bundle[lid]
    print(f"\n{lid}")
    for r in c["regions"]:
        # cascade box with the largest overlap with my region
        best, bo = None, 0.0
        for b in p["boxes"]:
            bb = [b["x0"], b["y0"], b["x1"], b["y1"]]
            o = ov(r["box"], bb) / max(1e-9, area(r["box"]))
            if o > bo:
                best, bo = b, o
        got = best["label"] if best else "—"
        surya = best["surya"] if best else "—"
        mark = "  " if got == r["class"] else ("⚠️" if bo < 0.3 else "🔴")
        print(f"  {mark} cold {r['class']:<3} live {got:<3} (surya {surya:<13} cover {bo:.2f})  {r['why'][:50]}")
