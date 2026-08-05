#!/usr/bin/env python3
"""gt_review_server.py — local ground-truth review + correction tool (Jarvis, 2026-07-12).

Serves a browse/correct UI for Sir to compare a page raster against Jarvis's diplomatic
ground-truth transcription, edit any line, and SUBMIT corrections that are written straight
to disk into ground-truth/corrections/<slug>.corrections.json — a structured file Jarvis
reads back to clean up the ground truth.

Stdlib only (no Flask). Binds 127.0.0.1 only. Locus-parameterized: the dropdown lists every
*.json in ground-truth/ (excluding corrections/), so the same server serves all pages.

Run:  ocr-venv/bin/python ocr-spike/gt_review_server.py [--port 8099]
Then: open http://localhost:8099
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SPIKE = Path(__file__).resolve().parent          # ocr-spike/
ROOT = SPIKE.parent                              # originaldr-project/
GT_DIR = SPIKE / "ground-truth"
CORR_DIR = GT_DIR / "corrections"
HTML = SPIKE / "gt_review.html"
CORR_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SPIKE))  # so `import jp2_page` (sibling) resolves regardless of CWD

_SLUG_OK = re.compile(r"^[A-Za-z0-9._-]+$")


def _gt_files() -> list[Path]:
    return sorted(p for p in GT_DIR.glob("*.json") if p.is_file())


def _slug(p: Path) -> str:
    return p.stem  # e.g. "scripture-genesis-24"


def _find_gt(slug: str) -> Path | None:
    if not _SLUG_OK.match(slug):
        return None
    p = GT_DIR / f"{slug}.json"
    return p if p.is_file() else None


def _record_pages(d: dict) -> list[int]:
    """The page(s) a GT record declares — page_index as [ints] (multi-page matter) or a single int."""
    pi = d.get("page_index")
    if isinstance(pi, list):
        return [int(x) for x in pi if x is not None]
    return [int(pi)] if pi is not None else []


def _render_jp2_png(d: dict, maxw: int = 1800, page=None) -> bytes | None:
    """Render a curated jp2 page for a GT record ON DEMAND — no pre-rendered PNG needed.

    This is why newly-added pages (drafts, new matter) that never got a `raster` PNG now display:
    we load the jp2 straight from (ocr_dir, page_index) via jp2_page (curated S1/S3/S4/S6/S8/S9 only).

    `page` (int or None): a multi-page matter section (page_index is a LIST) can request any ONE of its
    declared pages — the review UI stacks all of them (Issue 2 fix: show the whole section across its pages,
    page-aligned, so nothing is 'off-page'). A requested page NOT in the record's declared set is refused
    (returns None → 404) so the endpoint can't be used to render arbitrary pages. `page=None` → first page.
    Returns None if the address is unresolved (page_index null → needs the address fix first)."""
    try:
        import jp2_page  # sibling; curated-source gate lives here (KeyError on non-curated)
        from PIL import Image
    except Exception:
        return None
    od = d.get("ocr_dir")
    pages = _record_pages(d)
    if page is not None:
        try:
            target = int(page)
        except (TypeError, ValueError):
            return None
        if pages and target not in pages:      # only render pages THIS section declares (defense-in-depth)
            return None
    else:
        target = pages[0] if pages else None
    if not od or target is None:
        return None
    try:
        im = jp2_page.load(od, int(target)).convert("L")
    except Exception:
        return None
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    server_version = "gtreview/1.0"

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def log_message(self, format, *args):  # noqa: A002  # quieter console
        pass

    def do_GET(self) -> None:
        u = urlparse(self.path)
        q = parse_qs(u.query)
        path = u.path

        if path in ("/", "/index.html"):
            if not HTML.is_file():
                return self._send(500, b"gt_review.html missing", "text/plain")
            return self._send(200, HTML.read_bytes(), "text/html; charset=utf-8")

        if path == "/api/loci":
            out = []
            for p in _gt_files():
                try:
                    d = json.loads(p.read_text())
                except Exception:
                    continue
                out.append({
                    "slug": _slug(p),
                    "locus": d.get("locus", _slug(p)),
                    "page_label": d.get("page_label_printed", ""),
                    "scan": d.get("scan", ""),
                    "has_corrections": (CORR_DIR / f"{_slug(p)}.corrections.json").is_file(),
                })
            return self._json(out)

        if path == "/api/gt":
            slug = (q.get("locus") or [""])[0]
            gt = _find_gt(slug)
            if not gt:
                return self._json({"error": "unknown locus"}, 404)
            d = json.loads(gt.read_text())
            # attach any existing corrections so a re-open shows prior edits
            corr = CORR_DIR / f"{slug}.corrections.json"
            d["_existing_corrections"] = json.loads(corr.read_text()) if corr.is_file() else None
            return self._json(d)

        if path == "/raster":
            slug = (q.get("locus") or [""])[0]
            gt = _find_gt(slug)
            if not gt:
                return self._send(404, b"unknown locus", "text/plain")
            d = json.loads(gt.read_text())
            page_q = (q.get("page") or [None])[0]     # optional: a specific page of a multi-page section
            # 1) pre-rendered PNG fast-path — ONLY when `raster` is a STRING path to an actual .png that
            #    resolves, and no specific page was requested. A LIST-valued `raster` (multi-page sections
            #    store a list) or a descriptive string is NOT a path: the old code did `SPIKE / raster` on it
            #    and raised TypeError → the handler crashed → broken-image icon (Issue 3). We now skip straight
            #    to the on-demand jp2→PNG render, which handles every case uniformly. Non-.png rasters (e.g.
            #    .jp2, which browsers can't display) also fall through to be rendered as PNG.
            raster = d.get("raster", "")
            if isinstance(raster, str) and raster and page_q is None:
                rp = (SPIKE / raster).resolve()
                if not rp.is_file():
                    rp = (ROOT / raster).resolve()
                if ROOT in rp.parents and rp.is_file() and rp.suffix.lower() == ".png":
                    return self._send(200, rp.read_bytes(), "image/png")
            # 2) on-demand jp2 render (curated-source-gated). `page_q` selects one page of a multi-page section.
            png = _render_jp2_png(d, page=page_q)
            if png is not None:
                return self._send(200, png, "image/png")
            return self._send(404, b"raster unavailable: page_index unresolved/non-curated, or requested "
                                    b"page not declared by this section", "text/plain")

        return self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if u.path != "/api/submit":
            return self._send(404, b"not found", "text/plain")
        n = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._json({"error": f"bad json: {e}"}, 400)

        slug = payload.get("slug", "")
        if not _find_gt(slug):
            return self._json({"error": "unknown locus"}, 400)

        payload["submitted_at"] = datetime.now(timezone.utc).isoformat()
        out = CORR_DIR / f"{slug}.corrections.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        # timestamped archive copy so no submission is ever silently overwritten
        stamp = payload["submitted_at"].replace(":", "").replace("-", "").replace(".", "")[:15]
        (CORR_DIR / f"{slug}.{stamp}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        n_corr = len(payload.get("corrections", [])) + len(payload.get("marginalia_corrections", []))
        return self._json({"ok": True, "written": str(out.relative_to(ROOT)), "n_corrections": n_corr})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"GT review server on http://localhost:{args.port}  (ground-truth: {GT_DIR})")
    print(f"corrections written to: {CORR_DIR}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
