#!/usr/bin/env python3
"""build_raster_manifest.py -- R5.1: what each admitted leaf actually IS, measured once.

Gate 0d asserts three things about every leaf entering the recognition chain: bit depth > 1,
distinct grey levels > 64, and dimensions matching this manifest.  The third clause had no data
source: **this manifest had never been built**, so Gate 0d could not have been fully enforced even
had its guard existed -- and until 2026-08-10 the guard did not exist either, while three documents
described it as merely lacking a negative test.

Built through `witnesses.pixel_source()` rather than by globbing a directory, so the manifest
cannot describe a raster the corpus would refuse to serve.  A manifest assembled by a second route
would be a second opinion about which file is the witness, which is R7.5 exactly.

Records what is measured and NOTHING inferred: mode, bit depth, distinct grey levels after an L
conversion, pixel dimensions, and a content hash.  Grey levels are counted from the histogram, not
sampled, because the number is a threshold input and a sampled estimate would put a guess inside a
gate.

Run:  ../ocr-venv/bin/python witness/build_raster_manifest.py            # base exemplars
      ../ocr-venv/bin/python witness/build_raster_manifest.py --all      # every jp2-primary witness
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SPIKE))
import witnesses as W  # noqa: E402

from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

OUT = HERE / "raster-manifest.json"
RASTER_EXT = {".jp2", ".jpf", ".tif", ".tiff", ".png", ".jpg", ".jpeg"}


def measure(path: pathlib.Path) -> dict:
    """Everything Gate 0d needs about one leaf, measured. No inference."""
    with Image.open(path) as im:
        im.load()
        mode, (w, h) = im.mode, im.size
        # `1` is one bit per pixel; PIL reports 8 for L and 24/32 for RGB(A).
        bit_depth = 1 if mode == "1" else 8 * len(im.getbands())
        grey_levels = sum(1 for c in im.convert("L").histogram() if c)
    return {
        "path": str(path),
        "width": w,
        "height": h,
        "mode": mode,
        "bit_depth": bit_depth,
        "grey_levels": grey_levels,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def leaves_of(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.iterdir()
                  if p.is_file() and p.suffix.lower() in RASTER_EXT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="every jp2-primary witness, not only the three base exemplars")
    ap.add_argument("--limit", type=int, default=0,
                    help="measure only the first N leaves per witness (SMOKE RUN -- the manifest "
                         "records the truncation and Gate 0d treats a missing leaf as UNKNOWN, "
                         "never as a pass)")
    # R5.1's acceptance requires that regenerating the manifest twice be byte-identical, and with a
    # single hard-coded output path there was no way to run the second build without destroying the
    # first -- an acceptance clause that cannot be executed is not an acceptance clause.
    ap.add_argument("--out", default=str(OUT),
                    help="where to write the manifest (default the canonical path); used to build a "
                         "second copy for the determinism check without overwriting the first")
    args = ap.parse_args()
    out = pathlib.Path(args.out)

    wanted = []
    for (vol, sig), rec in sorted(W.WITNESSES.items()):
        if not args.all and rec["role"] != "base":
            continue
        try:
            root = pathlib.Path(W.pixel_source(vol, sig))
        except ValueError as e:
            # A witness the corpus refuses to serve pixels for is RECORDED as refused, with the
            # registry's own reason. Silently skipping it would make "not measured" and "not
            # admissible" the same entry, which is the distinction this manifest exists to keep.
            print(f"  --    {W.wid(vol, sig):14} REFUSED: {str(e).split(':', 1)[1].strip()[:80]}")
            wanted.append((vol, sig, None, str(e)))
            continue
        wanted.append((vol, sig, root, None))

    manifest: dict = {"witnesses": {}, "truncated": bool(args.limit)}
    for vol, sig, root, refused in wanted:
        widx = W.wid(vol, sig)
        if refused:
            manifest["witnesses"][widx] = {"pixel_source": None, "refused": refused, "leaves": {}}
            continue
        ls = leaves_of(root)
        if args.limit:
            ls = ls[:args.limit]
        print(f"  ..    {widx:14} {len(ls)} leaf/leaves under {root.name}", flush=True)
        # flush: without it a redirected log shows NOTHING until the first 200-leaf marker, so a
        # run that died on witness 1 would look identical to one that had not started (R5.1).
        entries = {}
        for i, p in enumerate(ls):
            entries[p.name] = measure(p)
            if (i + 1) % 200 == 0:
                print(f"        {widx} {i + 1}/{len(ls)}", flush=True)
        manifest["witnesses"][widx] = {
            "pixel_source": str(root), "refused": None, "leaves": entries,
        }
        print(f"  ok    {widx:14} {len(entries)} leaves measured")

    out.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    total = sum(len(w["leaves"]) for w in manifest["witnesses"].values())
    print(f"\nwrote {out.name}: {len(manifest['witnesses'])} witness(es), {total} leaves"
          + ("  ⚠️ TRUNCATED SMOKE RUN" if args.limit else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
