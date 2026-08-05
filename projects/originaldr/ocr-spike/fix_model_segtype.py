# -*- coding: utf-8 -*-
"""CORRECT THE MISLABELLED `seg_type` ON THE FINE-TUNED RECOGNIZER — a metadata repair, not a retrain.

WHAT IS WRONG. `reichenau_dr.mlmodel`, the R2 production recognizer this project fine-tuned, records
`seg_type: bbox`. Its own base model `reichenau_lat.mlmodel` records `baselines`, so the label was introduced
by our fine-tune — the fingerprint of the Python-API bypass the training had to use, since kraken 7.0.2's
`ketos train` fails with `im_transforms=None` on raw bboxes. The consequence is a warning on EVERY recognition
call in `reocr_core`:

    Recognizers with segmentation types {'bbox'} will be applied to segmentation of type baselines —
    this will likely result in severely degraded performance.

WHY THIS IS SAFE, AND WHY IT CHANGES NOTHING AT RUNTIME. `rpred.mm_rpred` raises that warning by comparing the
model's DECLARED seg_type against the segmentation's type, and does nothing else with it: the line-extraction
path is selected by `bounds.type == 'baselines'`. So the field is advisory, and correcting it cannot alter a
transcript. `kraken_segtype_probe.py` established which value is TRUE by asking the model — recognizing the
same `blla` lines both ways over 7 Genesis 1 leaves:

    baselines (current)   conf 0.9735   chapter recall 0.4042
    bbox (as declared)    conf 0.9016   chapter recall 0.1898      (-0.2144)

The model reads dewarped polygons far better than rectangles, so it was trained on them. `baselines` is the
correct label; `bbox` is the false one.

THE POINT OF FIXING IT. Not performance — there is none to gain. A recognizer that misreports how it was
trained is a live trap: it spent this entire sprint advertising itself as the largest unexplained defect in
the project, and it would have gone on doing so for every future session. A wrong label is worse than no
label, because it invites exactly the retrain this measurement shows would be pointless.

HOW IT IS DONE, AND HOW IT MUST NOT BE. The obvious route — `TorchVGSLModel.load_model` -> set
`user_metadata['seg_type']` -> `save_model` — **corrupts the model.** It rebuilds the whole coreml container
from the loaded net and writes `model_type: 'r'` where the original says `'recognition'`, after which
`kraken.lib.models.load_any` refuses the file outright:

    ValueError: Models of type r are not supported by TorchSeqRecognizer

That was tried, it broke the R2 recognizer, and it was restored from backup. Do not repeat it. kraken keeps
all of its metadata in ONE JSON blob at `description.metadata.userDefined['kraken_meta']`, so the repair is to
parse that blob, change the single key, and write it back — every other byte of the container, weights
included, is left exactly as it was.

Usage:  ../ocr-venv/bin/python fix_model_segtype.py [--model PATH] [--check]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / "models" / "reichenau_dr.mlmodel"
WANT = "baselines"


def read_seg_type(path: Path) -> str:
    from kraken.lib import models
    return models.load_any(str(path)).seg_type


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(DEFAULT))
    ap.add_argument("--check", action="store_true", help="report the declared seg_type and exit")
    a = ap.parse_args()
    path = Path(a.model)

    before = read_seg_type(path)
    print(f"{path.name}: declared seg_type = {before!r}")
    if a.check:
        return 0
    if before == WANT:
        print("already correct — nothing to do")
        return 0

    import json

    from coremltools.proto import Model_pb2
    from kraken.lib import models

    bak = path.with_suffix(path.suffix + ".bak-segtype")
    if not bak.exists():
        shutil.copy2(path, bak)
        print(f"backup -> {bak.name}")

    raw = path.read_bytes()
    proto = Model_pb2.Model()
    proto.ParseFromString(raw)
    meta = json.loads(proto.description.metadata.userDefined["kraken_meta"])
    keep = {k: meta.get(k) for k in ("model_type", "one_channel_mode", "legacy_polygons")}
    meta["seg_type"] = WANT
    proto.description.metadata.userDefined["kraken_meta"] = json.dumps(meta)
    path.write_bytes(proto.SerializeToString())

    # Reload through the SAME entry point `reocr_core` uses. The failure mode this guards against is real and
    # was observed: a rewrite that leaves the file parseable but no longer loadable as a recognizer.
    chk = Model_pb2.Model()
    chk.ParseFromString(path.read_bytes())
    meta2 = json.loads(chk.description.metadata.userDefined["kraken_meta"])
    after = read_seg_type(path)
    m = models.load_any(str(path))
    codec_ok = len(m.codec.c2l) if getattr(m, "codec", None) else None
    unchanged = all(meta2.get(k) == v for k, v in keep.items())
    print(f"now declared: {after!r}   model_type {meta2.get('model_type')!r}   codec entries {codec_ok}")
    if not (after == WANT and unchanged and codec_ok):
        shutil.copy2(bak, path)
        print("VERIFICATION FAILED — restored from backup", file=sys.stderr)
        return 1
    print("OK — label corrected; no runtime behaviour changes (the field is advisory in rpred.mm_rpred)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
