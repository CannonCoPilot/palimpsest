# -*- coding: utf-8 -*-
"""GENESIS 1 ON THE RE-RECOGNIZED STREAM — what the kraken re-run actually buys, per verse, per reference.

WHAT THE WORD BOXES DID AND DID NOT SETTLE. They were fetched to make the apparatus/scripture column split
MEASURED instead of estimated, and on that question the answer is negative and worth recording: the columns
are not separable at word grain either. Labelling every word on a page by whether it anchors to the chapter's
archaic reference and then asking for an x threshold that divides them gives, at x >= 0.78 of the page width,
only 42-46% of the apparatus caught for 17-19% of the scripture lost — and on `jp2-S06` the threshold is worse
than useless. kraken's baseline segmentation merges the two columns into single lines, and within those lines
the apparatus words occupy the same x range as the scripture. No geometry available at any grain separates
them, which retires the whole family of estimators this project has tried.

WHAT THE RE-RUN DID BUY IS THE TEXT. The stored corpus stream was recognized once, long ago, and never revised;
re-running the fine-tuned recognizer over these twelve leaves produces visibly better readings — the verse
marker is recovered as `†` where the stored stream has `F`, and lines that were fragmentary come back whole
("light, Day, and the darkenes, Night : and there was euening"). That is measurable, and this module measures
it: Genesis 1, every verse, every witness, scored against ALL FOUR references, stored stream vs re-recognized.

Usage:  python gen1_rerecog_eval.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import corpus_localize as CL                 # noqa: E402  # Gate 0f route to the localization artefact
import layout                                # noqa: E402
import qc_audit as QC                        # noqa: E402
import verse_locate                          # noqa: E402
import verse_seg as VS                       # noqa: E402
from char_identity import evaluate_locus      # noqa: E402

WB = HERE / ".gen1-wordboxes.json"
REFS = ("s_dismas", "odr_com", "sabates_a", "madueke_b")
WITS = {"S1": "archive-ot1-1609", "S3": "pdf-S03a",
        "S9": "archive-holiebible-ot1", "S6": "jp2-S06"}
BAR = 0.90


class _Shim:
    __slots__ = ("boundary", "baseline")

    def __init__(self, bbox):
        x0, y0, x1, y1 = bbox
        self.boundary = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self.baseline = [(x0, y1), (x1, y1)]


def page_from_wordboxes(pd: dict) -> dict:
    """A `stored_page`-shaped dict built from the re-recognized page, so the same localizer can read it.

    Roles come from `layout.type_lines` on the new boxes — the same body-isolation the stored path uses, so
    the only thing that differs between the two arms is the recognition itself."""
    raw = [l for l in pd["lines"] if l.get("text") and l.get("bbox")]
    if not raw:
        return {}
    W, H = pd["page_px"]
    roles = layout.type_lines([_Shim(l["bbox"]) for l in raw], W, H)
    lines = [{"text": l["text"], "conf": 1.0, "role": r, "bbox": tuple(l["bbox"])}
             for l, r in zip(raw, roles)]
    body = [l for l in lines if l["role"] == "body"]
    return {"page_px": (W, H), "lines": lines,
            "r2_body": layout.strip_verse_numbers(" ".join(l["text"] for l in body)),
            "n_body": len(body), "n_lines": len(lines)}


def main():
    wb = json.loads(WB.read_text())
    refs = {n: QC.load_reads_verse(n) for n in REFS}
    janv = VS.chapter_verses("genesis", 1, VS.JANVIER) or {}
    stored = {s: CL.load_verses(d) for s, d in WITS.items()}   # R9.2c: through Gate 0f, not around it

    new: dict[str, dict[int, dict]] = {}
    for s, od in WITS.items():
        best: dict[int, dict] = {}
        for pi, pd in sorted(wb.get(od, {}).items(), key=lambda kv: int(kv[0])):
            page = page_from_wordboxes(pd)
            if not page:
                continue
            page["page_index"] = int(pi)
            try:
                spans = verse_locate.best_spans(page, "genesis", 1)
            except Exception:                                  # noqa: BLE001
                continue
            for v, sp in (spans or {}).items():
                t = (sp or {}).get("text") or ""
                if not t.strip():
                    continue
                f = verse_locate.janvier_fit(t, janv.get(v))
                if v not in best or f > best[v]["fit"]:
                    best[v] = {"text": t, "fit": f, "page": int(pi)}
        new[s] = best

    rows = []
    print(f"=== GENESIS 1 — stored stream vs RE-RECOGNIZED, all four references (bar {BAR}) ===\n")
    hdr = f"{'v':>3} {'wit':>3} | " + " ".join(f"{r[:9]:>9}" for r in REFS) + "  verdict"
    for v in sorted(janv):
        for s in WITS:
            got_old = (stored[s].get(f"genesis/1/{v}") or {}).get("text", "")
            got_new = (new[s].get(v) or {}).get("text", "")
            so, sn = {}, {}
            for r in REFS:
                ref = refs[r].get(f"scripture/genesis/1/{v}")
                so[r] = round(evaluate_locus(got_old, ref, ref)["archaic_id"], 3) if (got_old and ref) else None
                sn[r] = round(evaluate_locus(got_new, ref, ref)["archaic_id"], 3) if (got_new and ref) else None
            rows.append({"verse": v, "wit": s, "stored": so, "rerecog": sn,
                         "n_old": len(got_old.split()), "n_new": len(got_new.split())})
    (HERE / "gen1-rerecog-eval.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))

    for r in REFS:
        o = [x["stored"][r] for x in rows if x["stored"][r] is not None]
        n = [x["rerecog"][r] for x in rows if x["rerecog"][r] is not None]
        po = sum(1 for x in o if x >= BAR)
        pn = sum(1 for x in n if x >= BAR)
        print(f"{r:>10}  stored mean {statistics.mean(o):.3f} pass {po:3d}/{len(o):3d}"
              f"   |  re-recog mean {statistics.mean(n):.3f} pass {pn:3d}/{len(n):3d}")
    # per-verse support on the governing archaic reference, both arms
    def support(arm):
        h = {}
        for v in sorted(janv):
            k = [x for x in rows if x["verse"] == v]
            h[v] = sum(1 for x in k if (x[arm]["s_dismas"] or 0) >= BAR or (x[arm]["odr_com"] or 0) >= BAR)
        return h
    so, sn = support("stored"), support("rerecog")
    print(f"\n{'v':>3} {'stored':>7} {'re-recog':>9}")
    for v in sorted(janv):
        mark = "  <<<" if sn[v] > so[v] else ("  (down)" if sn[v] < so[v] else "")
        print(f"{v:>3} {so[v]:>7} {sn[v]:>9}{mark}")
    print(f"\nverses at >=3/4 support — stored {sum(1 for v in so if so[v]>=3)}/31, "
          f"re-recognized {sum(1 for v in sn if sn[v]>=3)}/31")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
