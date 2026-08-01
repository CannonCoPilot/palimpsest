#!/usr/bin/env python3
"""P4.1 · Diplomatic OCR generator — the ſ-preserving replacement for the ſ→f djvu ocr_consensus.

METHOD (decided by the P4.1 spike, see ocr-method-spike.json): kraken 7.x baseline
segmentation + the ``reichenau_lat_cat`` recognition model (zenodo 11113737, "Latin
Incunabula/Early Prints"). That model natively preserves long-ſ / æ / œ / u-v / i-j on
early-modern Roman/Antiqua type (fold word-acc 0.78, ſ-word recall 0.73-0.91 vs s-dismas
GT) — unlike stock tesseract (ſ→f) or CATMuS-Print (ſ→s normalized, disqualified because
§6.1 forbids restoring ſ from a lossy inverse).

This script is the GENERATOR half: it emits per-page line records (text + bbox) so a later
detect step (mirroring detect_ocr_consensus.py) can region-type each line (body=scripture
vs marginal band=apparatus, via marginalia-geometry.json) and align to the verse skeleton.
Keeping generation (hours of OCR) separate from alignment lets each iterate independently.

RUNS UNDER THE ISOLATED OCR VENV (has kraken/torch; kept out of core/.venv so the app test
suite is untouched):
    core/.scratch/originaldr-project/ocr-venv/bin/python <thisfile> <alias|pdf-line> [...]

Design: deterministic + RESUMABLE + DETACHABLE. Each page's line records cache to
    sources/our-ocr-diplomatic/<line>/<page-stem>.json     (gitignored scratch)
and a page is skipped if its cache exists, so the job survives interruption/JICM clears.
The recognition model is loaded ONCE and reused across a whole batch (kraken multi-input),
amortizing the ~seconds model-load that dominates per-page CLI cost.

    nohup env OCR_SCALE_TO=2400 OCR_UPSCALE=1 .../ocr-venv/bin/python <thisfile> jp2:S03a >> <log> 2>&1 &

SOURCE LAYOUT (post-2026-07-07 reorg): scan sources live under
``imports/Scripture/Bibles/DouayRheims_DR/sources/scans/S01..S15/`` (see
``sources/dr-sources-manifest.json`` v2). THREE image adapters:
  - ``pdf:<key>``  — render a source PDF via pdftoppm (SOURCE_PDFS).
  - ``eebo:<key>`` — the EEBO/ProQuest reprint PDFs S10-S15 (EEBO_DIRS).
  - ``jp2:<key>``  — the archive.org ``*_jp2.zip`` scan MASTERS (JP2_SOURCES). MEASURED ~4x the
    linear resolution of the download PDFs, so these are the preferred input for the low-res-PDF
    sources (S03/S04/S05/S09). Run with OCR_SCALE_TO=2400 to downscale the masters for kraken.
Each adapter caches under its own OUT_ROOT namespace (pdf-/eebo-/jp2-), plus the legacy archive-*
caches (S1 etc., already jp2-derived) — the consensus layer reads whatever witness dirs exist.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[6]  # .../palimpsest
DR_BASE = REPO / "imports/Scripture/Bibles/DouayRheims_DR"
SCANS = DR_BASE / "sources/scans"    # 15 photographic scan sources S01-S15 (post-reorg layout)
OUT_ROOT = REPO / "core/.scratch/originaldr-project/sources/our-ocr-diplomatic"

# Canonical scan PDFs, rendered via pdftoppm and OCR'd with our ſ-preserving diplomatic kraken.
# Paths mirror sources/dr-sources-manifest.json v2 per-source "file" fields. The cache line-key is
# "pdf-<key>" (see resolve()), so the seven pre-reorg keys (S02/S03a/S03b/S04/S06/S08/S09nt) are
# kept verbatim to reuse their existing pdf-* OCR caches. The S01/S05/S09-OT entries are the
# canonical PDFs of the formerly-jp2 sources: their archive-* caches (from the now-gone higher-res
# jp2) are retained as-is, and these entries exist only for provenance / a deliberate re-OCR (which
# would land in NEW pdf-* dirs, no collision). S07 is a byte-dup of S06 and is deliberately absent.
SOURCE_PDFS = {
    "S02":    SCANS / "S02_1609-douay-ot-hires/S02.pdf",
    "S03a":   SCANS / "S03_holie-bible-engl-ot-vol1/S03a.pdf",
    "S03b":   SCANS / "S03_holie-bible-engl-ot-vol2/S03b.pdf",
    "S04":    SCANS / "S04_1633-rheims-nt/S04.pdf",
    "S06":    SCANS / "S06_1610-facsimile-whole/S06.pdf",
    "S08":    SCANS / "S08_1582-rhemes-nt-hires/S08.pdf",
    "S09nt":  SCANS / "S09_nevv-testament-mart-3vol/nevvtestamentofi00mart-NT.pdf",
    "S01ot1": SCANS / "S01_1582-first-edition-3vol/ot1-1609.pdf",
    "S01ot2": SCANS / "S01_1582-first-edition-3vol/ot2-1610.pdf",
    "S01nt":  SCANS / "S01_1582-first-edition-3vol/nt-1582.pdf",
    "S05":    SCANS / "S05_newtestament-engl-nt/newtestamentofie00engl.pdf",
    "S09ot1": SCANS / "S09_nevv-testament-mart-3vol/holiebiblefaithf00mart_0-OT1.pdf",
    "S09ot2": SCANS / "S09_nevv-testament-mart-3vol/holiebiblefaithf00mart-OT2.pdf",
}

# EEBO/ProQuest reprint scans (S10-S15). Each lives in its own scans/ dir with a single hash-suffixed
# PDF, so map the volume key -> dir and glob that dir's lone *.pdf. Cache line-key stays "eebo-<key>".
EEBO_DIRS = {
    "nt":   SCANS / "S10_eebo-nt",
    "vol1": SCANS / "S11_eebo-vol1-nt",
    "vol2": SCANS / "S12_eebo-vol2-ot-genesis",
    "vol3": SCANS / "S13_eebo-vol3-ot-joshua",
    "vol4": SCANS / "S14_eebo-vol4-ot-psalms",
    "vol5": SCANS / "S15_eebo-vol5-ot-isaiah",
}
EEBO_ALL = list(EEBO_DIRS)

# archive.org jp2 scan MASTERS, co-located as scans/S0N/<name>_jp2.zip (fetched by fetch_jp2.py).
# These are the real full-res scans — MEASURED ~4x the linear resolution of the download PDFs
# (S1 jp2 3334x4684 vs PDF 800x1124), so they are the preferred OCR input for the sources whose
# PDFs are low-res derivatives (S03/S04/S05/S09). Key -> (scans subdir, exact jp2.zip filename);
# multi-volume dirs (S01, S09) hold several zips, hence the explicit filename. Cache line-key is
# "jp2-<key>" (see resolve()) — a fresh namespace, so re-OCR here never collides with the existing
# pdf-*/archive-* caches; the consensus layer picks up whichever witness dirs exist.
JP2_SOURCES = {
    "S01ot1": ("S01_1582-first-edition-3vol", "1582 Douai Rheims Douay Rheims First Edition  1 of 3 1609 Old Testament_jp2.zip"),
    "S01ot2": ("S01_1582-first-edition-3vol", "1582 Douai Rheims Douay Rheims First Edition  2 of 3 1610 Old Testament_jp2.zip"),
    "S01nt":  ("S01_1582-first-edition-3vol", "1582 Douai Rheims Douay Rheims First Edition  3 of 3 1582 New Testament_jp2.zip"),
    "S02":    ("S02_1609-douay-ot-hires", "1635 Douay Old Testament 1_jp2.zip"),
    "S03a":   ("S03_holie-bible-engl-ot-vol1", "holiebiblefaithf01engl_jp2.zip"),
    "S03b":   ("S03_holie-bible-engl-ot-vol2", "holiebiblefaithf02engl_jp2.zip"),
    "S04":    ("S04_1633-rheims-nt", "1582 Douay Rheims NT_jp2.zip"),
    "S05":    ("S05_newtestament-engl-nt", "newtestamentofie00engl_jp2.zip"),
    "S06":    ("S06_1610-facsimile-whole", "Douay-Rheims-1610-Bible_jp2.zip"),
    "S08":    ("S08_1582-rhemes-nt-hires", "1582_Rhemes_New_Testament_jp2.zip"),
    "S09nt":  ("S09_nevv-testament-mart-3vol", "nevvtestamentofi00mart_jp2.zip"),
    "S09ot1": ("S09_nevv-testament-mart-3vol", "holiebiblefaithf00mart_0_jp2.zip"),
    "S09ot2": ("S09_nevv-testament-mart-3vol", "holiebiblefaithf00mart_jp2.zip"),
}

OCRVENV = REPO / "core/.scratch/originaldr-project/ocr-venv/bin"
KRAKEN = str(OCRVENV / "kraken")
MODEL = REPO / "core/.scratch/originaldr-project/ocr-spike/models/reichenau_lat.mlmodel"

UPSCALE = int(os.environ.get("OCR_UPSCALE", "1"))  # PDF pages arrive pre-sized via pdftoppm -scale-to;
#                                                     set >1 only to upscale genuinely tiny inputs
SCALE_TO = int(os.environ.get("OCR_SCALE_TO", "0"))  # >0: prep_image resizes longest side to this many px
#   — used to DOWNSCALE the hi-res jp2 masters (~3300x4700) to an OCR-friendly ~2400px. Takes
#   precedence over UPSCALE. (iter_pdf_pages reads the same var for pdftoppm, so a PDF run already
#   sized to N is a no-op here.) Recommended for jp2 runs: OCR_SCALE_TO=2400 OCR_UPSCALE=1.
BATCH = int(os.environ.get("OCR_BATCH", "20"))      # pages per kraken invocation (amortizes model load)
WORKERS = int(os.environ.get("OCR_WORKERS", "10"))  # concurrent single-threaded kraken procs (<= cores)
MAX_PAGES = int(os.environ.get("OCR_MAX_PAGES", "0"))  # 0 = no cap (validation aid)
# each kraken proc pinned single-threaded so WORKERS procs don't oversubscribe the CPU
_CHILD_ENV = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
              "OPENBLAS_NUM_THREADS": "1", "PYTORCH_ENABLE_MPS_FALLBACK": "1"}


def prep_image(data: bytes, dst: Path) -> None:
    """Load a page image (jp2/any), grayscale, resize, save PNG to dst.

    OCR_SCALE_TO (longest-side px), when set, takes precedence — it DOWNSCALES the hi-res jp2
    masters to an OCR-friendly size. Otherwise OCR_UPSCALE multiplies (legacy small-input path)."""
    im = Image.open(io.BytesIO(data)).convert("L")
    if SCALE_TO:
        m = max(im.size)
        if m != SCALE_TO:
            r = SCALE_TO / m
            im = im.resize((round(im.width * r), round(im.height * r)), Image.Resampling.LANCZOS)
    elif UPSCALE != 1:
        im = im.resize((im.width * UPSCALE, im.height * UPSCALE), Image.Resampling.LANCZOS)
    im.save(dst)


def find_jp2_zip(key: str) -> Path | None:
    ent = JP2_SOURCES.get(key)
    if ent is None:
        return None
    p = SCANS / ent[0] / ent[1]
    return p if p.exists() else None


def iter_jp2_pages(zip_path: Path, key: str, out_dir: Path):
    """Stream jp2 page images out of an archive.org ``*_jp2.zip`` master, in page order.

    Stems are ``<key>_NNNN`` (1-based over the sorted .jp2 entries) so detect_our_ocr's
    ``_\\d+$`` page parser works and the cache is a fresh jp2-* namespace. Already-OCR'd pages
    are skipped WITHOUT decompressing the entry, so a resume is cheap."""
    with zipfile.ZipFile(zip_path) as zf:
        entries = sorted(n for n in zf.namelist() if n.lower().endswith(".jp2"))
        for i, e in enumerate(entries, 1):
            stem = f"{key}_{i:04d}"
            if (out_dir / f"{stem}.json").exists():
                continue
            yield stem, zf.read(e)


def alto_to_records(alto_path: Path) -> list[dict] | None:
    """Parse a kraken ALTO file -> [{bbox:[x0,y0,x1,y1], text}] in reading order.

    Returns None when the ALTO is missing or unparseable — i.e. kraken failed for this
    page (typically a segmentation OOM/crash under memory pressure). The caller must then
    leave the page uncached so a later run retries it. An empty [] is reserved for pages
    whose ALTO parsed cleanly but held no text lines (a genuinely blank leaf)."""
    import xml.etree.ElementTree as ET
    if not alto_path.exists():
        return None
    try:
        root = ET.parse(alto_path).getroot()
    except ET.ParseError:
        return None

    def num(el, key: str) -> float:
        v = el.get(key)
        return float(v) if v is not None else 0.0

    recs: list[dict] = []
    for line in root.iter():  # namespace-agnostic: match by localname
        if not line.tag.endswith("TextLine"):
            continue
        words = [w.get("CONTENT", "") for w in line if w.tag.endswith("String")]
        text = " ".join(t for t in words if t)
        if not text:
            continue
        x0, y0 = int(num(line, "HPOS")), int(num(line, "VPOS"))
        bbox = [x0, y0, x0 + int(num(line, "WIDTH")), y0 + int(num(line, "HEIGHT"))]
        recs.append({"bbox": bbox, "text": text})
    return recs


def run_batch(pairs: list[tuple[Path, Path]]) -> None:
    """OCR a batch of prepared PNGs -> ALTO, one single-threaded kraken process."""
    cmd = [KRAKEN]
    for png, alto in pairs:
        cmd += ["-i", str(png), str(alto)]
    cmd += ["-f", "image", "-a", "segment", "-bl", "ocr", "-m", str(MODEL)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   env=_CHILD_ENV, check=False)


def process_batch(items: list[tuple[str, bytes]], out_dir: Path) -> int:
    """Prep + OCR one batch (own temp dir) and write per-page line-record caches."""
    with tempfile.TemporaryDirectory() as td:
        trip = []
        for stem, data in items:
            png, alto = Path(td) / f"{stem}.png", Path(td) / f"{stem}.alto"
            prep_image(data, png)
            trip.append((png, alto, stem))
        run_batch([(p, a) for p, a, _ in trip])
        written = 0
        for _, alto, stem in trip:
            recs = alto_to_records(alto)
            if recs is None:
                # kraken produced no parseable ALTO for this page (OOM/crash). Do NOT write a
                # cache file: an empty {lines:[]} here would be indistinguishable from a real
                # blank and would be skip-cached forever (line ~189). Leave it uncached so the
                # next run retries it.
                continue
            (out_dir / f"{stem}.json").write_text(
                json.dumps({"page": stem, "lines": recs}, ensure_ascii=False))
            written += 1
    return written


def find_eebo_pdf(volkey: str) -> Path | None:
    d = EEBO_DIRS.get(volkey)
    if d is None or not d.is_dir():
        return None
    hits = sorted(d.glob("*.pdf"))
    return hits[0] if hits else None


def _pdf_page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=False)
    for ln in out.stdout.splitlines():
        if ln.startswith("Pages:"):
            try:
                return int(ln.split()[1])
            except (IndexError, ValueError):
                return 0
    return 0


def iter_pdf_pages(pdf: Path, key: str, out_dir: Path):
    """Render a PDF one page at a time via pdftoppm (grayscale). Per-page rendering bounds
    memory/disk (vs whole-PDF burst) and lets a resume SKIP already-OCR'd pages WITHOUT
    re-rendering them — critical for the multi-hundred-MB whole-tome PDFs. Stems are
    `<key>_NNNN` so detect_our_ocr's _PAGENUM ( _\\d+$ ) parses the page index."""
    import glob
    # -scale-to normalizes the LONGEST side to a fixed pixel count regardless of the PDF's
    # media-box / embedded-image resolution, so hi-res and low-res sources both land at an
    # OCR-friendly ~2400px (no 2x upscale needed -> set OCR_UPSCALE=1 for PDF passes).
    scale = os.environ.get("OCR_SCALE_TO", "2400")
    n = _pdf_page_count(pdf)
    for i in range(1, n + 1):
        stem = f"{key}_{i:04d}"
        if (out_dir / f"{stem}.json").exists():
            continue  # already OCR'd — don't spend a render on it
        with tempfile.TemporaryDirectory() as td:
            base = f"{td}/{key}"
            subprocess.run(["pdftoppm", "-scale-to", scale, "-gray", "-png",
                            "-f", str(i), "-l", str(i), str(pdf), base],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            pngs = sorted(glob.glob(f"{base}*.png"))
            if not pngs:
                continue
            yield stem, Path(pngs[0]).read_bytes()


def process_line(line_key: str, page_iter) -> dict:
    """Stream pages into batches, OCR up to WORKERS batches concurrently (bounded memory)."""
    from concurrent.futures import FIRST_COMPLETED, wait
    out_dir = OUT_ROOT / line_key
    out_dir.mkdir(parents=True, exist_ok=True)
    done = skipped = seen = 0
    t0 = time.time()
    batch: list[tuple[str, bytes]] = []
    pending: set = set()

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        def drain() -> None:
            nonlocal pending, done
            if not pending:
                return
            fin, pending = wait(pending, return_when=FIRST_COMPLETED)
            for f in fin:
                done += f.result()
            print(f"[{line_key}] done={done} skipped={skipped} inflight={len(pending)} "
                  f"{done / max(1e-6, time.time() - t0):.2f} pg/s", flush=True)

        for stem, data in page_iter:
            if MAX_PAGES and seen >= MAX_PAGES:
                break
            seen += 1
            if (out_dir / f"{stem}.json").exists():
                skipped += 1
                continue
            batch.append((stem, data))
            if len(batch) >= BATCH:
                pending.add(ex.submit(process_batch, batch, out_dir))
                batch = []
                while len(pending) >= WORKERS:      # backpressure: cap in-flight bytes
                    drain()
        if batch:
            pending.add(ex.submit(process_batch, batch, out_dir))
        while pending:
            drain()

    dt = round(time.time() - t0, 1)
    print(f"[{line_key}] COMPLETE done={done} skipped={skipped} {dt}s "
          f"{done / max(1e-6, dt):.2f} pg/s", flush=True)
    return {"line": line_key, "done": done, "skipped": skipped, "seconds": dt}


def resolve(target: str):
    if target.startswith("jp2:"):
        jkey = target.split(":", 1)[1]
        zp = find_jp2_zip(jkey)
        key = f"jp2-{jkey}"
        if zp is None:
            print(f"jp2.zip not found for key {jkey!r} "
                  f"(known: {', '.join(JP2_SOURCES)})", file=sys.stderr)
            return key, iter(())
        return key, iter_jp2_pages(zp, jkey, OUT_ROOT / key)
    if target.startswith("eebo:"):
        volkey = target.split(":", 1)[1]
        pdf = find_eebo_pdf(volkey)
        key = f"eebo-{volkey}"
        if pdf is None:
            print(f"EEBO volume not found for key {volkey!r} "
                  f"(known: {', '.join(EEBO_ALL)})", file=sys.stderr)
            return key, iter(())
        return key, iter_pdf_pages(pdf, volkey, OUT_ROOT / key)
    # "pdf:<key>" or a bare "<key>" => SOURCE_PDFS
    skey = target.split(":", 1)[1] if target.startswith("pdf:") else target
    pdf = SOURCE_PDFS.get(skey)
    key = f"pdf-{skey}"
    if pdf is None or not pdf.exists():
        print(f"source PDF not found for key {skey!r} "
              f"(known: {', '.join(SOURCE_PDFS)})", file=sys.stderr)
        return key, iter(())
    return key, iter_pdf_pages(pdf, skey, OUT_ROOT / key)


def main() -> int:
    if not MODEL.exists():
        print(f"MODEL MISSING: {MODEL}", file=sys.stderr)
        return 2
    targets = sys.argv[1:] or (
        [f"pdf:{k}" for k in SOURCE_PDFS] + [f"eebo:{k}" for k in EEBO_ALL])
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for tgt in targets:
        key, it = resolve(tgt)
        results.append(process_line(key, it))
    (OUT_ROOT / "_manifest.json").write_text(json.dumps(
        {"model": MODEL.name, "upscale": UPSCALE, "lines": results}, indent=2) + "\n")
    print("DONE ·", json.dumps(results), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
