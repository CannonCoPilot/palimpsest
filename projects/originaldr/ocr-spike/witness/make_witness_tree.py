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
            # Clear whatever is there: the link may have been a directory
            # symlink on a previous run and a link farm on this one.
            if link.is_symlink():
                link.unlink()
            elif link.is_dir():
                for f in link.iterdir():
                    f.unlink()
                link.rmdir()
            if "leaf_range" in rec:
                # A witness that is a SLICE of a package cannot be one directory
                # symlink -- that would address the whole package, which for S06
                # means pooling a 1635 Rouen OT with a 1582 Rheims NT.  Link the
                # slice leaf by leaf instead, renumbered from zero so the
                # witness's own leaf indices start where the witness does.
                link.mkdir()
                for k, f in enumerate(W.leaves(vol, sig)):
                    os.symlink(f, link / f"{wid}_{k:04d}{f.suffix}")
            else:
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
