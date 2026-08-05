#!/usr/bin/env python3
"""Fetch archive.org jp2.zip scan masters into scans/S0N dirs. Resumable + size-verified.

Reads jp2-fetch-map.json (produced by the metadata probe). Skips S7-DUP (byte-dup of S6,
messy multi-work item). Reuses any jp2.zip already on disk (e.g. the ot1 master Sir placed at
sources/ root) instead of re-downloading. curl -L -C - with retries; verifies final byte size
against the archive.org metadata size and warns on any mismatch/failure.
"""
import json, os, subprocess, glob

ROOT = "/Users/nathanielcannon/Claude/Projects/palimpsest"
MAP = os.path.join(ROOT, "projects/originaldr/ocr-spike/jp2-fetch-map.json")
SOURCES = os.path.join(ROOT, "imports/Scripture/Bibles/DouayRheims_DR/sources")

m = json.load(open(MAP))
done, warned = [], []

def find_existing(name):
    """Locate a same-named jp2.zip already anywhere under sources/ (e.g. root drop)."""
    hits = glob.glob(os.path.join(SOURCES, "**", name), recursive=True)
    return hits[0] if hits else None

for r in m["resolved"]:
    label, note = r["label"], r.get("note", "")
    if note == "dup-of-S6":
        print(f"[{label}] SKIP ({note})", flush=True); continue
    dest_dir = os.path.join(ROOT, r["dest_dir"])
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, r["jp2_name"])
    want = int(r["size"])

    if os.path.exists(dest) and os.path.getsize(dest) == want:
        print(f"[{label}] already present + size-verified ({want//1048576} MB)", flush=True)
        done.append(label); continue

    # reuse a same-named copy sitting elsewhere under sources/ (avoid re-download)
    ex = find_existing(r["jp2_name"])
    if ex and os.path.abspath(ex) != os.path.abspath(dest) and os.path.getsize(ex) == want:
        print(f"[{label}] moving existing {ex} -> {dest}", flush=True)
        os.replace(ex, dest); done.append(label); continue

    print(f"[{label}] downloading {want//1048576} MB -> {dest}", flush=True)
    rc = subprocess.run(["curl", "-L", "-f", "-C", "-", "--retry", "5", "--retry-delay", "5",
                         "-o", dest, r["url"]],
                        env={**os.environ}, check=False).returncode
    got = os.path.getsize(dest) if os.path.exists(dest) else 0
    if rc != 0 or got != want:
        warned.append(f"{label}: curl rc={rc} got={got//1048576}MB want={want//1048576}MB url={r['url']}")
        print(f"[{label}] ⚠️ FAILED rc={rc} got={got//1048576}MB want={want//1048576}MB", flush=True)
    else:
        print(f"[{label}] OK ({got//1048576} MB)", flush=True); done.append(label)

print("\n==== FETCH SUMMARY ====", flush=True)
print(f"downloaded/present: {len(done)} -> {', '.join(done)}", flush=True)
if warned:
    print("WARNINGS:", flush=True)
    for w in warned: print("  ⚠️ ", w, flush=True)
else:
    print("no warnings — all resolved jp2.zip present + size-verified", flush=True)
print("DONE ·", flush=True)
