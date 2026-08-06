"""Build the stable witness tree as a symlink farm.

Copying would duplicate ~11 GB and create a second thing that can drift from
the first.  Symlinks give the stable path without a second copy, and a broken
link is a loud failure rather than a silent stale duplicate.
"""
import os, sys, json, hashlib
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import witnesses as W

ROOT = Path("/Users/nathanielcannon/Claude/Projects/Palimpsest/imports/Scripture/"
            "Bibles/DouayRheims_DR/sources/witnesses")

def build(dry=False):
    manifest = {}
    for (vol, sig), rec in W.WITNESSES.items():
        wid = W.wid(vol, sig)
        d = ROOT / vol / wid
        src = rec["jp2"]
        if not src.is_dir():
            print(f"  !! missing source for {wid}: {src}"); continue
        if not dry:
            d.mkdir(parents=True, exist_ok=True)
            link = d / "leaves"
            if link.is_symlink() or link.exists():
                if link.is_symlink(): link.unlink()
            os.symlink(src, link)
        manifest[wid] = dict(volume=vol, siglum=sig, year=rec["year"],
                             role=rec["role"], legacy=rec["legacy"],
                             repository=W.COPIES[sig],
                             leaves=rec["leaves"], source=str(src),
                             path=str(d / "leaves"))
        print(f"  {wid:14s} -> {src.name[:52]}")
    if not dry:
        ROOT.mkdir(parents=True, exist_ok=True)
        (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    return manifest

def verify():
    """A witness path must resolve, and its leaf count must match the registry."""
    bad = []
    for (vol, sig), rec in W.WITNESSES.items():
        wid = W.wid(vol, sig)
        p = ROOT / vol / wid / "leaves"
        if not p.is_dir():
            bad.append(f"{wid}: path does not resolve"); continue
        n = len(list(p.glob("*.jp2")))
        if n != rec["leaves"]:
            bad.append(f"{wid}: {n} leaves, registry says {rec['leaves']}")
    for b in bad: print("  FAIL", b)
    print(f"  {len(W.WITNESSES) - len(bad)}/{len(W.WITNESSES)} witnesses verified")
    return not bad

if __name__ == "__main__":
    print("building witness tree:"); build()
    print("verifying:");            sys.exit(0 if verify() else 1)
