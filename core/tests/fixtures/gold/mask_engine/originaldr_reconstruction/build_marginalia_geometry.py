#!/usr/bin/env python3
"""Phase 1 · P1.4 (residual) — marginalia geometry from the archive.org hOCR word boxes.

Measures WHERE the print puts the scripture body column versus the marginal apparatus
(verse-note numbers, cross-references, sidecar annotations), so the archaic diplomatic
rendering (P2b) can reproduce the page's spatial organization rather than guessing it.

Method (deterministic): for each archive.org main tome (nt-1582, ot1-1609, ot2-1610) parse
the committed hOCR, sample scripture-body pages evenly across the middle of the volume (front
and back matter are single-column and would skew the column model), collect every ocrx_word
bounding box, and build a normalized horizontal density profile of word centres. The dominant
contiguous mode is the scripture text column; the lighter bands to its outer/inner sides are
the margins where the printed notes sit. Reports the column and margin bands as fractions of
the page width, plus the share of ink that falls in the margins.

Grounded in the same scans the layout map cites (sha256-pinned). No corpus mutation.

Run:  core/.venv/bin/python build_marginalia_geometry.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
ARCHIVE_ORG = REPO / "imports/Scripture/Bibles/DouayRheims_DR/archive-org"
OUT = HERE / "marginalia-geometry.json"

# tome alias -> (approx scripture-body page span to sample, human label). The spans avoid the
# front/back matter (single-column) so the two-zone body/margin model is not skewed.
TOMES = {
    "nt-1582": dict(body=(40, 700), label="Rheims New Testament 1582 (archive.org)"),
    "ot1-1609": dict(body=(60, 900), label="Douay OT First Tome 1609 (archive.org)"),
    "ot2-1610": dict(body=(60, 1000), label="Douay OT Second Tome 1610 (archive.org)"),
}
N_SAMPLE = 60           # pages sampled per tome
NBINS = 100             # horizontal density bins across the page width
_PAGE_RE = re.compile(r"class=['\"]ocr_page['\"][^>]*title=['\"]([^'\"]*)['\"]")
_WORD_RE = re.compile(r"class=['\"]ocrx_word['\"][^>]*bbox (\d+) (\d+) (\d+) (\d+)")
_BBOX_RE = re.compile(r"bbox (\d+) (\d+) (\d+) (\d+)")


def hocr_path(alias: str) -> Path:
    hits = list((ARCHIVE_ORG / alias).glob("*hocr.html"))
    if not hits:
        raise SystemExit(f"hOCR not found for {alias}")
    return hits[0]


def split_pages(text: str) -> list[str]:
    """Chunk the hOCR into per-page slices at each ocr_page marker."""
    idxs = [m.start() for m in re.finditer(r"class=['\"]ocr_page['\"]", text)]
    idxs.append(len(text))
    return [text[idxs[i]:idxs[i + 1]] for i in range(len(idxs) - 1)]


def page_width(chunk: str) -> int:
    m = _PAGE_RE.search(chunk)
    if m:
        b = _BBOX_RE.search(m.group(1))
        if b:
            return int(b.group(3)) or 800
    return 800


def profile_tome(alias: str, spec: dict) -> dict[str, Any]:
    path = hocr_path(alias)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    pages = split_pages(path.read_text(encoding="utf-8", errors="replace"))
    lo, hi = spec["body"]
    hi = min(hi, len(pages))
    idxs = [int(lo + (hi - lo) * k / (N_SAMPLE - 1)) for k in range(N_SAMPLE)] if hi > lo else []
    idxs = sorted(set(i for i in idxs if 0 <= i < len(pages)))
    bins = [0] * NBINS
    total_words = 0
    pw = 800
    for i in idxs:
        chunk = pages[i]
        pw = page_width(chunk)
        for m in _WORD_RE.finditer(chunk):
            x0, _, x1, _ = (int(g) for g in m.groups())
            cx = (x0 + x1) / 2 / pw
            if 0.0 <= cx < 1.0:
                bins[min(NBINS - 1, int(cx * NBINS))] += 1
                total_words += 1
    band = _dominant_band(bins)
    col_lo, col_hi = band
    margins = _margin_bands(bins, band)
    in_body = sum(bins[col_lo:col_hi + 1])
    return {
        "alias": alias, "label": spec["label"], "sha256": sha,
        "pages_total": len(pages), "pages_sampled": len(idxs),
        "page_width_px": pw, "words_measured": total_words,
        "text_column": {"x_lo": round(col_lo / NBINS, 3), "x_hi": round((col_hi + 1) / NBINS, 3),
                        "share_of_words": round(in_body / total_words, 3) if total_words else 0.0},
        "marginal_bands": margins,
        "density_profile": [round(b / total_words, 4) if total_words else 0.0 for b in bins],
    }


def _dominant_band(bins: list[int]) -> tuple[int, int]:
    """The scripture body column = the highest-mass contiguous run of above-threshold bins."""
    total = sum(bins) or 1
    thr = total / len(bins) * 0.6           # 60% of the mean-per-bin
    best = (0, 0, -1)                        # (lo, hi, mass)
    i = 0
    n = len(bins)
    while i < n:
        if bins[i] >= thr:
            j = i
            while j + 1 < n and bins[j + 1] >= thr:
                j += 1
            mass = sum(bins[i:j + 1])
            if mass > best[2]:
                best = (i, j, mass)
            i = j + 1
        else:
            i += 1
    return (best[0], best[1])


def _margin_bands(bins: list[int], body: tuple[int, int]) -> list[dict[str, Any]]:
    """Above-threshold runs outside the body column = the margins where notes sit."""
    total = sum(bins) or 1
    thr = total / len(bins) * 0.15          # lighter bar: marginal notes are sparser than body
    n = len(bins)
    out: list[dict[str, Any]] = []
    i = 0
    while i < n:
        if bins[i] >= thr and not (body[0] <= i <= body[1]):
            j = i
            while j + 1 < n and bins[j + 1] >= thr and not (body[0] <= j + 1 <= body[1]):
                j += 1
            mass = sum(bins[i:j + 1])
            mid = (i + j) / 2 / n
            out.append({"x_lo": round(i / n, 3), "x_hi": round((j + 1) / n, 3),
                        "side": "inner/left" if mid < body[0] / n else "outer/right",
                        "share_of_words": round(mass / total, 3)})
            i = j + 1
        else:
            i += 1
    return out


def main() -> int:
    tomes = {alias: profile_tome(alias, spec) for alias, spec in TOMES.items()}
    doc = {
        "artifact": "marginalia-geometry", "phase": "P1.4", "idx": 108,
        "generated_by": "build_marginalia_geometry.py",
        "note": "Horizontal page geometry measured from the archive.org hOCR word boxes: the "
                "scripture body column vs the margin bands where the printed apparatus "
                "(verse-note numbers, cross-references, sidecar annotations) sits. Feeds the "
                "archaic diplomatic rendering's spatial layout (plan §4.4/§5.3). Sampled from "
                "the scripture-body page span of each tome (front/back matter excluded, being "
                "single-column). density_profile is the normalized word-centre histogram "
                f"({NBINS} bins across the page width).",
        "tomes": tomes,
        "summary": {a: {"text_column": t["text_column"],
                        "n_marginal_bands": len(t["marginal_bands"])}
                    for a, t in tomes.items()},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    for a, t in tomes.items():
        tc = t["text_column"]
        print(f"{a}: body x[{tc['x_lo']}-{tc['x_hi']}] {tc['share_of_words']*100:.0f}% ink · "
              f"{len(t['marginal_bands'])} margin band(s) · {t['words_measured']} words / "
              f"{t['pages_sampled']} pp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
