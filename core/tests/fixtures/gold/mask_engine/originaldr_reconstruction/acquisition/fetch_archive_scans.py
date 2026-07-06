#!/usr/bin/env python3
"""Phase 0 · P0.3 — acquire archive.org scan assets (full tome).

For each of the six archive.org witness items (three main 1609/1610/1582
originals + three supplementary independent scans) download the page-image
archive (`_jp2.zip`), the word-boxed OCR (`_hocr.html`), and the text PDF
(`_text.pdf`) when present. Binaries land under the gitignored imports tree
(preserve-don't-push); this script + the emitted sha-pinned manifest are the
tracked, reproducible provenance record.

Idempotent + resumable: skips a file already present at the metadata-reported
size; otherwise resumes via `wget -c`. Writes archive-scans-manifest.json
(identifier, server/dir, per-file name/size/sha256/url) next to nothing — it is
returned to the tracked reconstruction dir by the caller.

Usage:
    python fetch_archive_scans.py [--dest DIR] [--manifest PATH] [--only ALIAS...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# alias -> archive.org identifier. Aliases match the local *_djvu.txt naming.
ITEMS: dict[str, str] = {
    "ot1-1609": "1582DouaiRheimsDouayRheimsFirstEdition1Of31609OldTestament",
    "ot2-1610": "1582DouaiRheimsDouayRheimsFirstEdition2Of31610OldTestament",
    "nt-1582": "1582DouaiRheimsDouayRheimsFirstEdition3Of31582NewTestament",
    "newtestament": "newtestamentofie00engl",
    "holiebible-ot1": "holiebiblefaithf00mart_0",
    "holiebible-ot2": "holiebiblefaithf00mart",
}

# file-name suffixes we want, in priority order. jp2.zip + hocr required;
# text.pdf optional (not every item has one).
WANT_SUFFIXES = ("_jp2.zip", "_hocr.html", "_text.pdf")

META_URL = "https://archive.org/metadata/{id}"
DL_URL = "https://archive.org/download/{id}/{name}"


def fetch_metadata(identifier: str) -> dict:
    url = META_URL.format(id=urllib.parse.quote(identifier))
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def wanted_files(meta: dict) -> list[dict]:
    out = []
    for f in meta.get("files", []):
        name = f.get("name", "")
        if name.endswith(WANT_SUFFIXES):
            out.append(f)
    return out


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(identifier: str, name: str, dest: Path, attempts: int = 4) -> None:
    """Resumable download with retry on transient archive.org failures. wget exit 8
    (server error response, e.g. a transient 503 under load) is retried with backoff;
    a persistent failure raises so the caller can log-and-continue rather than abort."""
    url = DL_URL.format(id=urllib.parse.quote(identifier), name=urllib.parse.quote(name))
    dest.parent.mkdir(parents=True, exist_ok=True)
    # -c resume; retry network AND transient HTTP error codes; follow redirects to a data node
    cmd = ["wget", "-c", "--tries=10", "--timeout=60", "--waitretry=5",
           "--retry-on-http-error=408,429,500,502,503,504",
           "-q", "--show-progress", "-O", str(dest), url]
    last = None
    for i in range(attempts):
        r = subprocess.run(cmd)
        if r.returncode == 0:
            return
        last = r.returncode
        print(f"        wget rc={last} (attempt {i+1}/{attempts}); backing off", flush=True)
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"wget failed rc={last} after {attempts} attempts: {name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="imports/Scripture/Bibles/DouayRheims_DR/archive-org")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--only", nargs="*", help="restrict to these aliases")
    args = ap.parse_args()

    dest_root = Path(args.dest).resolve()
    aliases = args.only or list(ITEMS)
    manifest: dict = {"items": {}}

    for alias in aliases:
        identifier = ITEMS[alias]
        print(f"\n=== {alias}  ({identifier}) ===", flush=True)
        meta = fetch_metadata(identifier)
        files = wanted_files(meta)
        rec = {
            "identifier": identifier,
            "server": meta.get("server"),
            "dir": meta.get("dir"),
            "files": [],
        }
        item_dir = dest_root / alias
        for f in files:
            name = f["name"]
            size = int(f.get("size", 0))
            dest = item_dir / name
            url = DL_URL.format(id=urllib.parse.quote(identifier), name=urllib.parse.quote(name))
            try:
                if dest.exists() and dest.stat().st_size == size and size > 0:
                    print(f"  [skip] {name} ({size/1048576:.0f} MB) present", flush=True)
                else:
                    print(f"  [get ] {name} ({size/1048576:.0f} MB)", flush=True)
                    download(identifier, name, dest)
                got = dest.stat().st_size
                ok = got == size
                digest = sha256_of(dest)
                rec["files"].append({
                    "name": name, "expected_size": size, "actual_size": got,
                    "size_ok": ok, "sha256": digest, "md5_archive": f.get("md5"),
                    "status": "ok" if ok else "size-mismatch", "url": url,
                })
                print(f"        sha256={digest[:16]}…  size_ok={ok}", flush=True)
            except Exception as e:  # log-and-continue: one file must not abort the fleet
                rec["files"].append({"name": name, "expected_size": size,
                                     "status": "failed", "error": str(e), "url": url})
                print(f"  [FAIL] {name}: {e}", flush=True)
        manifest["items"][alias] = rec

    manifest_path = Path(args.manifest) if args.manifest else \
        Path(__file__).resolve().parent / "archive-scans-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nmanifest → {manifest_path}", flush=True)
    allfiles = [fr for it in manifest["items"].values() for fr in it["files"]]
    total = sum(fr.get("actual_size", 0) for fr in allfiles)
    failed = [fr for fr in allfiles if fr.get("status") != "ok"]
    print(f"total downloaded across {len(manifest['items'])} items: {total/1048576:.0f} MB", flush=True)
    if failed:
        print(f"⚠ {len(failed)} file(s) not OK:", flush=True)
        for fr in failed:
            print(f"    {fr['name']}: {fr.get('status')} {fr.get('error','')}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
