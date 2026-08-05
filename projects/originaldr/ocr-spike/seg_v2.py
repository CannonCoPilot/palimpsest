"""seg_v2.py — Phase 2a segmentation: classify each page line body-vs-apparatus, evaluate vs GT.

The advance over rung1_surya.py: we now have human-reviewed GROUND TRUTH with per-line ROLES
(body / annotation / marginalia / section_marker / catchword / signature / header). So instead of
scoring through detect_book (which localizes against s_dismas and carries the alignment artifact), we
score classification DIRECTLY against the GT:

  * For each recognized line, its TRUE role = the role of the GT text-unit it best matches (by folded
    edit_ratio). This isolates SEGMENTATION/CLASSIFICATION quality from RECOGNITION quality.
  * classification metrics: body precision/recall, apparatus leak into body.
  * end-to-end: body-only-OCR concat vs GT-body concat edit_ratio (combined seg+recognition effect).

Classifier is intentionally simple + inspectable first (Surya body-region membership), then iterated
with PER-LAYOUT geometric/content rules — never one uniform x/y band (that regressed, see AI_OCR skill).

Usage: ocr-venv/bin/python ocr-spike/seg_v2.py <gt-slug> [dpi]  (default dpi 300)
       ocr-venv/bin/python ocr-spike/seg_v2.py scripture-genesis-24 300
Writes ocr-spike/.seg-eval-<slug>.json and prints a per-line table + summary.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rung1_surya as R  # noqa: E402  # kraken_lines, surya_regions, pick_body_regions, surya_body_lines
from char_identity import edit_ratio, fold_archaic  # noqa: E402
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("rl", str(HERE / "reocr_ladder.py"))
RL = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(RL)  # type: ignore

GT_DIR = HERE / "ground-truth"
ROOT = HERE.parent


# --------------------------------------------------------------------------- #
# GT units (text + role) for matching
# --------------------------------------------------------------------------- #
def gt_units(gt: dict) -> list[dict]:
    """Every GT text line paired with its ROLE, for OCR-line -> role matching."""
    units = []
    for L in gt["body"]:
        units.append({"text": L["text"], "role": L.get("role", "body"), "src": f"body[{L['line_index']}]"})
    for i, ap in enumerate(gt.get("apparatus", [])):
        for j, ln in enumerate(ap["text"].split("\n")):
            if ln.strip():
                units.append({"text": ln, "role": ap.get("role", "annotation"), "src": f"ap[{i}].{j}"})
        if ap.get("gloss"):
            units.append({"text": ap["gloss"], "role": "section_marker", "src": f"ap[{i}].gloss"})
    for i, m in enumerate(gt.get("marginalia", [])):
        for j, ln in enumerate(m["text"].split("\n")):
            if ln.strip():
                units.append({"text": ln, "role": "marginalia", "src": f"marg[{i}].{j}"})
    if gt.get("catchword"):
        units.append({"text": gt["catchword"]["text"], "role": "catchword", "src": "catchword"})
    rh = gt.get("running_header", {})
    for k in ("left", "center", "right"):
        if rh.get(k):
            units.append({"text": rh[k], "role": "header", "src": f"header.{k}"})
    return units


_LEAD_NUM = re.compile(r"^\s*\d{1,3}\s*")
_LEAD_REF = re.compile(r"^\s*[a-zA-Z]\s+")


def norm_for_match(text: str) -> str:
    """Strip leading verse-number and reference-letter so an OCR body line matches the cleaned GT body."""
    t = _LEAD_NUM.sub("", text)
    t = _LEAD_REF.sub("", t)
    return t


def best_gt_match(text: str, units: list[dict]) -> dict:
    ft = fold_archaic(norm_for_match(text))
    if not ft.strip():
        return {"role": "empty", "ratio": 0.0, "src": "", "gt_text": ""}
    best = {"role": None, "ratio": 0.0, "src": "", "gt_text": ""}
    for u in units:
        r = edit_ratio(ft, fold_archaic(u["text"]))
        if r > best["ratio"]:
            best = {"role": u["role"], "ratio": round(r, 3), "src": u["src"], "gt_text": u["text"]}
    return best


# --------------------------------------------------------------------------- #
# geometry helpers (normalized 0..1 by page W,H)
# --------------------------------------------------------------------------- #
def norm_bbox(b, W, H):
    return [b[0] / W, b[1] / H, b[2] / W, b[3] / H]


def region_for_line(nb, regions_norm):
    """Surya region label whose box contains the line centroid (else largest-overlap, else None)."""
    cx, cy = (nb[0] + nb[2]) / 2, (nb[1] + nb[3]) / 2
    for r in regions_norm:
        x0, y0, x1, y1 = r["bbox"]
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            return r["label"]
    return None


# --------------------------------------------------------------------------- #
# BASELINE classifier v0: Surya body-region membership (what rung1_surya did)
# --------------------------------------------------------------------------- #
def classify_v0(klines, regions, W, H) -> list[str]:
    body_regions = R.pick_body_regions(regions)
    body_ids = set(id(l) for l in R.surya_body_lines(klines, body_regions))
    return ["body" if id(l) in body_ids else "apparatus" for l in klines]


# --------------------------------------------------------------------------- #
# classifier v1: content/typographic cues + reading-order continuation.
# Motivation: Surya region typing SOLVES Gen24 (apparatus lives in the right
# margin, a distinct region) but COLLAPSES on Psalms 118, where italic footnote
# annotations are interleaved in the SAME central column as body verses — Surya
# labels the whole column one "Text" region. The page still carries the split in
# the *text*: body verses lead with a verse-NUMBER, footnotes lead with a single
# ref-KEY letter, Hebrew octonary headers are short CENTERED lines, marginalia
# sit in the right margin. Wrapped continuation lines (no lead cue) inherit the
# role of the preceding central-column line in reading order.
# NB: not one uniform x/y band (that regressed before) — a *layered* decision:
# self-identifying geometry first, then per-line content cues, then inheritance.
# --------------------------------------------------------------------------- #
_VERSE_START = re.compile(r"^[^0-9A-Za-z]{0,3}\d")           # optional stray punct, then a digit
_REF_KEY = re.compile(r"^\s*([A-Za-z])[^A-Za-z]")           # a single leading letter, then non-letter
_NEXT_WORD = re.compile(r"^\s*[A-Za-z][^A-Za-z]+([A-Za-z]\S*)")
_KEY_LETTERS = set("abcdefgh")                               # plausible footnote keys on one page
_PRONOUNS = {"i", "o"}                                       # English single-letter words → never a key


def _is_verse_start(t: str) -> bool:
    return bool(_VERSE_START.match(t))


def _is_ref_key(t: str) -> bool:
    """Leading single letter that is a footnote key (a–h), followed by a Capitalized word.
    Excludes body pronouns 'I'/'l'/'i'/'o' at line-start (e.g. 'I hated…', 'l haue…')."""
    m = _REF_KEY.match(t)
    if not m:
        return False
    key = m.group(1)
    if key.lower() not in _KEY_LETTERS or key.lower() in _PRONOUNS:
        return False
    nxt = _NEXT_WORD.match(t)
    return bool(nxt and nxt.group(1)[:1].isupper())          # key must precede a Capitalized content word


def classify_v1(klines, regions, W, H) -> list[str]:
    regions_norm = [{"label": r["label"], "bbox": norm_bbox(r["bbox"], W, H)} for r in regions]
    nbs = [norm_bbox(l["bbox"], W, H) for l in klines]
    roles: list[str | None] = [None] * len(klines)

    # Pass 1 — self-identifying geometry (header/footer, right-margin, centered-short)
    for i, (l, nb) in enumerate(zip(klines, nbs)):
        t = l["text"].strip()
        x0, _, x1, _ = nb
        surya = region_for_line(nb, regions_norm)
        if surya in ("PageHeader", "PageFooter"):
            roles[i] = "apparatus"; continue
        if x0 >= 0.66:                                        # right-margin marginalia (Gen24 0.72+, Ps 0.81)
            roles[i] = "apparatus"; continue
        words = t.split()
        if 0.28 <= x0 and (x1 - x0) <= 0.45 and len(words) <= 3 and not _is_verse_start(t):
            roles[i] = "apparatus"; continue                 # centered short line: Hebrew octonary header / gloss

    # Pass 2 — content cues + reading-order continuation on the central column
    central = sorted((i for i in range(len(klines)) if roles[i] is None),
                     key=lambda i: (round(nbs[i][1], 3), nbs[i][0]))
    last = "body"                                            # seed: pages open with body
    for i in central:
        t = klines[i]["text"].strip()
        if _is_verse_start(t):
            roles[i] = last = "body"
        elif _is_ref_key(t):
            roles[i] = last = "apparatus"
        else:
            roles[i] = last                                 # wrapped continuation inherits prior role
    return [r or "apparatus" for r in roles]


CLASSIFIERS = {"v0": classify_v0, "v1": classify_v1}

APPARATUS_ROLES = {"annotation", "marginalia", "section_marker", "catchword", "signature", "header"}


def evaluate(slug: str, dpi: int = 300, clf: str = "v1") -> dict:
    gt = json.loads((GT_DIR / f"{slug}.json").read_text())
    pdf = RL.ocrdir_to_pdf()[gt["ocr_dir"]]["pdf"]
    import fitz
    doc = fitz.open(pdf)
    pix = doc.load_page(gt["page_index"]).get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    W, H = im.size

    klines = R.kraken_lines(im)
    regions = R.surya_regions(im)
    regions_norm = [{"label": r["label"], "bbox": norm_bbox(r["bbox"], W, H)} for r in regions]
    units = gt_units(gt)

    pred = CLASSIFIERS[clf](klines, regions, W, H)
    rows = []
    for l, p in zip(klines, pred):
        nb = norm_bbox(l["bbox"], W, H)
        m = best_gt_match(l["text"], units)
        true_role = "body" if m["role"] == "body" else ("apparatus" if m["role"] in APPARATUS_ROLES else m["role"])
        rows.append({"text": l["text"], "nb": [round(v, 3) for v in nb],
                     "surya": region_for_line(nb, regions_norm), "pred": p,
                     "true": true_role, "true_role": m["role"], "match": m["ratio"], "gt_src": m["src"]})

    # metrics (ignore weak matches < 0.45 as "unmatched/noise")
    conf = {"body->body": 0, "body->app": 0, "app->body": 0, "app->app": 0, "weak": 0}
    for r in rows:
        if r["match"] < 0.45:
            conf["weak"] += 1; continue
        t = "body" if r["true"] == "body" else "app"
        p = "body" if r["pred"] == "body" else "app"
        conf[f"{t}->{p}"] += 1
    tp, fp, fn = conf["body->body"], conf["app->body"], conf["body->app"]
    body_prec = tp / (tp + fp) if (tp + fp) else 0.0
    body_rec = tp / (tp + fn) if (tp + fn) else 0.0

    # end-to-end: classified-body OCR concat vs GT-body concat
    body_ocr = " ".join(norm_for_match(l["text"]) for l, p in zip(klines, pred) if p == "body")
    gt_body = re.sub(r"-\s+", "", " ".join(L["text"] for L in gt["body"] if L.get("role", "body") == "body"))
    e2e = edit_ratio(fold_archaic(body_ocr), fold_archaic(gt_body))

    summary = {"slug": slug, "dpi": dpi, "clf": clf, "W": W, "H": H, "kraken_lines": len(klines),
               "surya_regions": sorted({r["label"] for r in regions_norm}),
               "confusion": conf, "body_precision": round(body_prec, 3), "body_recall": round(body_rec, 3),
               "e2e_body_concat_vs_GT": round(e2e, 4), "gt_body_chars": len(gt_body), "body_ocr_chars": len(body_ocr)}
    out = {"summary": summary, "rows": rows}
    (HERE / f".seg-eval-{slug}-{clf}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main() -> int:
    slug = sys.argv[1]
    dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    clf = sys.argv[3] if len(sys.argv) > 3 else "v1"
    out = evaluate(slug, dpi, clf)
    s = out["summary"]
    print(f"\n=== seg_v2 eval: {slug} @ {dpi}dpi  clf={s['clf']} ({s['W']}x{s['H']}) ===")
    print(f"kraken lines: {s['kraken_lines']}   surya region labels: {s['surya_regions']}")
    print(f"confusion (true->pred): {s['confusion']}")
    print(f"BODY precision={s['body_precision']}  recall={s['body_recall']}")
    print(f"E2E classified-body-OCR vs GT-body: {s['e2e_body_concat_vs_GT']}  "
          f"(ocr {s['body_ocr_chars']}c vs gt {s['gt_body_chars']}c)")
    print("\nper-line (text | norm-bbox | surya | pred | true | match):")
    for r in out["rows"]:
        flag = "  ⚠" if (r["match"] >= 0.45 and (r["pred"] == "body") != (r["true"] == "body")) else ""
        print(f"  [{r['pred'][:4]:>4}|{r['true'][:4]:>4}|{r['match']:.2f}] {r['surya'] or '-':<12} "
              f"y{r['nb'][1]:.2f}-{r['nb'][3]:.2f} x{r['nb'][0]:.2f}-{r['nb'][2]:.2f}  {r['text'][:60]}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
