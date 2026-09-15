#!/usr/bin/env python3
"""score_box_bias.py — what Sir's corrections say about the director's box placement.

Every corrected leaf in plates/gold-layout.json holds both the director's claim and Sir's box for
the same region. Subtract the two — after carrying the claim through the leaf's own skew and dewarp,
so levelling is never counted as a correction — and the residual is the director's placement error,
measured rather than guessed.

    python3 score_box_bias.py                 # summary
    python3 score_box_bias.py --json out.json # machine-readable, for the roadmap record

Output is a BRIEF, not a patch. It never rewrites a cold-read box: a systematic shift applied blind
would launder Sir's corrections back into the claim and destroy the only independent signal we have.
"""
import argparse, collections, json, statistics as st, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import plate_gold as PG

MOVE_EPS = 0.004          # a box within this of the carried claim was not touched by hand
GROW_EPS = 0.05           # area ratio outside 1±this counts as resized


def load(record=None, sample=None):
    rec = json.load(open(record or HERE / "plates" / "gold-layout.json"))
    px = {l["id"]: l.get("px") for l in json.load(open(sample or HERE / "cold-read" / "sample-B.json"))["leaves"]}
    return rec, px


def pairs(rec, px):
    """Yield (leaf, class, claim_box_carried, sir_box) for every agent region Sir kept."""
    for lid, L in sorted(rec["leaves"].items()):
        rv = L.get("review") or {}
        if rv.get("verdict") != "corrected":
            continue
        ag = L.get("agent", {}).get("regions", [])
        deg = rv.get("skew_deg", 0) or 0
        w, h = px.get(lid) or (1100, 1500)
        for x in rv.get("regions", []):
            if x["origin"] != "agent" or x.get("agent_index") is None:
                continue
            if x["agent_index"] >= len(ag):
                continue
            exp = PG.transform_box(ag[x["agent_index"]]["box"], w, h, deg)
            if rv.get("dewarp"):
                exp = PG.transform_box_dewarp(exp, rv["dewarp"], w, h)
            yield lid, x["class"], exp, x["box"]


def analyse(rec, px):
    edges = collections.defaultdict(list)          # (class|'*', edge) -> deltas
    area = collections.defaultdict(list)
    touched = collections.Counter(); total = collections.Counter()
    for lid, c, exp, b in pairs(rec, px):
        total["n"] += 1; total[c] += 1
        if max(abs(a - d) for a, d in zip(exp, b)) > MOVE_EPS:
            touched["n"] += 1; touched[c] += 1
        for i, e in enumerate(("x0", "y0", "x1", "y1")):
            edges[("*", e)].append(b[i] - exp[i]); edges[(c, e)].append(b[i] - exp[i])
        ea = (exp[2]-exp[0]) * (exp[3]-exp[1])
        if ea > 0:
            area["*"].append(((b[2]-b[0]) * (b[3]-b[1])) / ea)
            area[c].append(((b[2]-b[0]) * (b[3]-b[1])) / ea)
    added = deleted = 0
    for lid, L in rec["leaves"].items():
        rv = L.get("review") or {}
        if rv.get("verdict") != "corrected":
            continue
        regs = rv.get("regions", [])
        added += sum(1 for x in regs if x["origin"] == "human")
        deleted += len(L.get("agent", {}).get("regions", [])) - sum(1 for x in regs if x["origin"] == "agent")
    return edges, area, touched, total, added, deleted


def brief(edges, area, touched, total, added, deleted):
    out = {"regions": total["n"], "touched": touched["n"], "added_by_hand": added, "deleted": deleted,
           "overall": {}, "by_class": {}}
    for e in ("x0", "y0", "x1", "y1"):
        v = edges[("*", e)]
        out["overall"][e] = {"mean": round(st.mean(v), 5), "median": round(st.median(v), 5)}
    out["overall"]["area_median"] = round(st.median(area["*"]), 3)
    out["overall"]["height_change_mean"] = round(st.mean([d1 - d0 for d0, d1 in zip(edges[("*", "y0")], edges[("*", "y1")])]), 5)
    out["overall"]["width_change_mean"] = round(st.mean([d1 - d0 for d0, d1 in zip(edges[("*", "x0")], edges[("*", "x1")])]), 5)
    for c, v in area.items():
        if c == "*" or len(v) < 8:
            continue
        ed = {e: round(st.mean(edges[(c, e)]), 5) for e in ("x0", "y0", "x1", "y1")}
        worst = max(ed.items(), key=lambda kv: abs(kv[1]))
        out["by_class"][c] = {"n": len(v), "area_median": round(st.median(v), 3),
                              "grew": sum(1 for a in v if a > 1 + GROW_EPS),
                              "shrank": sum(1 for a in v if a < 1 - GROW_EPS),
                              "edges": ed, "worst_edge": worst[0], "worst_shift": worst[1],
                              "touched": touched[c], "of": total[c]}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--record"); ap.add_argument("--sample"); ap.add_argument("--json")
    a = ap.parse_args()
    rec, px = load(a.record, a.sample)
    res = brief(*analyse(rec, px))
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1); print("wrote", a.json)
    o = res["overall"]
    print(f"{res['touched']}/{res['regions']} kept boxes moved by hand beyond levelling "
          f"· {res['added_by_hand']} added · {res['deleted']} deleted")
    print(f"edges (Sir − claim, fraction of page; − is up/left): "
          f"y0 {o['y0']['median']:+.4f}  y1 {o['y1']['median']:+.4f}  "
          f"x0 {o['x0']['median']:+.4f}  x1 {o['x1']['median']:+.4f}")
    print(f"height {o['height_change_mean']:+.4f}  width {o['width_change_mean']:+.4f}  "
          f"area median ×{o['area_median']:.2f}")
    print(f"\n{'class':5} {'n':>4} {'area':>6} {'grew':>5} {'shrank':>7}  worst edge")
    for c, v in sorted(res["by_class"].items(), key=lambda kv: -abs(kv[1]["worst_shift"])):
        print(f"{c:5} {v['n']:4d} ×{v['area_median']:5.2f} {v['grew']:5d} {v['shrank']:7d}  "
              f"{v['worst_edge']} {v['worst_shift']:+.4f}")


if __name__ == "__main__":
    main()
