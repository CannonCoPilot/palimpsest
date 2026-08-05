# -*- coding: utf-8 -*-
"""IS THE KRAKEN SEGMENTATION-TYPE WARNING COSTING US ANYTHING? — a decisive A/B, not an inspection.

THE WARNING. Every recognition call in `reocr_core` prints

    Recognizers with segmentation types {'bbox'} will be applied to segmentation of type baselines —
    this will likely result in severely degraded performance.

and it has never been investigated, though if real it would depress every rung of the ladder corpus-wide.

WHAT IS ACTUALLY DECLARED. The base recognizer `reichenau_lat.mlmodel` says `seg_type: baselines`. The
FINE-TUNED `reichenau_dr.mlmodel` — the R2 production recognizer this project trained — says `seg_type: bbox`.
The mismatch is therefore ours, introduced by the fine-tune, and consistent with the Python-API bypass the
training had to use (kraken 7.0.2's `ketos train` fails with `im_transforms=None` on raw bboxes).

WHY INSPECTION CANNOT SETTLE IT. In `rpred.mm_rpred` the warning is raised by comparing the model's DECLARED
seg_type against the segmentation's type, and nothing else: the line-extraction path is chosen by
`bounds.type == 'baselines'`, never by the model. So kraken feeds baseline-dewarped polygons either way, and
the declaration tells us only what the trainer wrote down — which is exactly the thing under suspicion. The
question "was this model trained on dewarped polygons or on raw rectangles?" can only be answered by asking
the model, and the way to ask it is to feed it both and see which it reads better.

THE TEST. For each Genesis 1 leaf: segment once with `blla` (baselines), then recognize twice — once on that
segmentation as it stands, and once on a `bbox`-type Segmentation built from the same lines' bounding boxes,
which is what the model claims to want. Score both body transcripts against the archaic references. If the
bbox arm wins, the warning is real and the fix is a re-run; if the baseline arm wins or ties, the model was
trained on polygons and the metadata is simply mislabelled — the fix is one metadata field and the warning
was never a lever at all.

THE ANSWER (2026-07-29, 7 Genesis 1 leaves, all four witnesses). The bbox arm is worse on every leaf and on
every axis:

    baselines   mean conf 0.9735   mean chapter recall 0.4042
    bbox        mean conf 0.9016   mean chapter recall 0.1898      (-0.2144)

and its token yield collapses where the leaf is warped — `archive-holiebible-ot1` p32 falls from 601 tokens to
96. The model reads dewarped polygons far better than rectangles, so it WAS trained on polygons and only its
`seg_type` field is wrong. **The warning is cosmetic. It is not the largest lever in the project; it is not a
lever at all**, and the ladder is already running the model the way it was trained. The remedy is to rewrite
that one metadata field on `reichenau_dr.mlmodel` so the warning stops misdirecting future sessions — left
undone here deliberately, because rewriting a trained model artifact is not a change to make while the sprint
is under a commit hold.

Usage:  ../ocr-venv/bin/python kraken_segtype_probe.py [--pages N]
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jp2_page                                # noqa: E402
import qc_audit as QC                          # noqa: E402
import reocr_core as RC                        # noqa: E402

# The Genesis 1 leaves, per witness — the same set the page model uses.
LEAVES = {"archive-ot1-1609": [21, 22], "pdf-S03a": [25, 26],
          "archive-holiebible-ot1": [31, 32], "jp2-S06": [18]}
ARCHAIC = ("s_dismas", "odr_com")


def to_bbox_segmentation(seg):
    """The same lines, declared and carried as `bbox` — what the R2 model's metadata says it was trained on.

    The bounding box of a baseline line's boundary polygon is the rectangle a bbox-trained model would have
    been shown. Nothing else about the page changes, so the two arms differ ONLY in how the line image is cut
    out: dewarped along the baseline, or cropped as a rectangle."""
    from kraken.containers import BBoxLine, Segmentation
    lines = []
    for i, l in enumerate(seg.lines):
        pts = getattr(l, "boundary", None) or []
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        lines.append(BBoxLine(id=f"bx{i}", bbox=(min(xs), min(ys), max(xs), max(ys)),
                              text_direction="horizontal-lr"))
    return Segmentation(type="bbox", imagename=seg.imagename, text_direction=seg.text_direction,
                        script_detection=seg.script_detection, lines=lines, regions={},
                        line_orders=[])


def body_of(recs) -> str:
    return " ".join(r["text"] for r in recs if r["text"])


def chapter_recall(txt: str, ref: str) -> float:
    """Fraction of the chapter's archaic tokens this transcript recovers, in order.

    `char_identity.evaluate_locus` is the project's identity metric and it is the RIGHT metric for a verse
    against its own reference — but it returns 0.000 for both arms here, because a whole leaf against a whole
    chapter is not the comparison it is built for. Resting the verdict on it would have meant reading a
    dead metric as a tie. A longest-common-subsequence recall over normalized tokens is the honest measure for
    "how much of the chapter did this page-level transcript actually recover", which is the question the two
    arms differ on."""
    import difflib
    a = [t.strip(" .,;:·†‡*()[]").lower().replace("ſ", "s") for t in txt.split()]
    b = [t.strip(" .,;:·†‡*()[]").lower().replace("ſ", "s") for t in ref.split()]
    a = [t for t in a if t]
    b = [t for t in b if t]
    if not b:
        return 0.0
    m = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return sum(bl.size for bl in m.get_matching_blocks()) / len(b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=99, help="leaves per witness")
    a = ap.parse_args()

    refs = {n: QC.load_reads_verse(n) for n in ARCHAIC}
    # One reference string per witness-leaf is not available, so score against the whole chapter's archaic
    # text: a transcription that reads the page better scores higher against it regardless of verse bounds.
    chapter = {r: " ".join(v for k, v in refs[r].items()
                           if k.startswith("scripture/genesis/1/") and v) for r in ARCHAIC}

    res: dict[str, list] = {"baselines": [], "bbox": []}
    for od, pages in LEAVES.items():
        for pi in pages[:a.pages]:
            try:
                pim = RC.preprocess(jp2_page.load(od, pi))
            except Exception as e:                              # noqa: BLE001
                print(f"  ! {od} p{pi}: {type(e).__name__}: {e}", file=sys.stderr)
                continue
            seg = RC.segment(pim, cache_key=f"{od}:{pi}")
            for arm, s in (("baselines", seg), ("bbox", to_bbox_segmentation(seg))):
                try:
                    recs = RC.recognize_lines(RC.R2_MODEL, pim, s)
                except Exception as e:                          # noqa: BLE001
                    print(f"  ! {od} p{pi} [{arm}]: {type(e).__name__}: {e}", file=sys.stderr)
                    continue
                txt = body_of(recs)
                conf = statistics.mean([r["conf"] for r in recs if r["nchars"]] or [0.0])
                sc = statistics.mean([chapter_recall(txt, chapter[r]) for r in ARCHAIC])
                res[arm].append({"leaf": f"{od} p{pi}", "conf": conf, "id": sc, "n": len(txt.split())})
                print(f"{od:24s} p{pi:<3} {arm:>9}  conf {conf:.4f}  chapter_recall {sc:.4f}  {len(txt.split()):>4} tok")

    print("\n=== VERDICT ===")
    for arm in ("baselines", "bbox"):
        xs = res[arm]
        if xs:
            print(f"{arm:>9}  mean conf {statistics.mean(x['conf'] for x in xs):.4f}"
                  f"   mean recall {statistics.mean(x['id'] for x in xs):.4f}   n={len(xs)}")
    if res["baselines"] and res["bbox"]:
        d = statistics.mean(x["id"] for x in res["bbox"]) - statistics.mean(x["id"] for x in res["baselines"])
        print(f"\nbbox - baselines = {d:+.4f} chapter recall")
        print("The warning is REAL — re-run the ladder on bbox segmentation." if d > 0.005 else
              "The warning is a MISLABEL — the model reads dewarped polygons at least as well as rectangles,\n"
              "so it was trained on them and only its `seg_type` metadata is wrong. Not a lever.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
