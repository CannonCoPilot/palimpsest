#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_finetune_kraken.py — Kraken PYTHON-API fine-tuner for Rung 2 (per-typeface DR recognizer).

WHY THIS EXISTS: the `ketos train` CLI is broken for our raw-bbox arrow. Root cause (diagnosed
2026-07-22): VGSLRecognitionDataModule._build_dataset (kraken/train/vgsl.py:124) passes
`im_transforms=None` to ArrowIPCRecognitionDataset; for raw-bbox data, .add() then executes
`self.transforms.valid_norm = True` (kraken/lib/dataset/recognition.py:180) → AttributeError, which
vgsl.py:133 swallows into a warning, leaving an EMPTY dataset → the misleading "No training data in
dataset." The DATA is 100% valid (ArrowIPCRecognitionDataset(split_filter='train') loads 264 rows).

THE FIX (DRDataModule below): override ONLY the buggy `_build_dataset` to give the dataset a real
ImageInputTransforms (so .valid_norm has a home; setup() overwrites it with the correctly-sized transform
anyway); the parent __init__'s explicit-eval branch then builds train from dr_train.arrow (264 lines) and
val from dr_val.arrow (47) — a verified-disjoint curated split. Everything else replicates the proven CLI
wiring (kraken/ketos/recognition.py:140-254): load reichenau_lat weights, resize='union' to extend its
codec with DR-only glyphs while keeping the learned strokes, KrakenTrainer.fit, best-val checkpoint.

SURFACE SAFETY (non-negotiable): normalization=NFC (NEVER NFKC — NFKC folds ſ→s); resize='union' keeps
the ſ-faithful reichenau base weights and only ADDS glyphs; NO dictionary/LM. ſ preserved by construction.
Base = reichenau_lat (ſ-faithful). catmus (ſ→s) is rejected.

Run: ocr-venv/bin/python ocr-spike/rung2_finetune_kraken.py [--device cpu|mps] [--lag 10] [--epochs 100]
Output: models/reichenau_dr.mlmodel (or .safetensors) — verified loadable by kraken.lib.models.load_any.
"""
from __future__ import annotations
import argparse, logging, shutil, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
BASE = HERE / "models" / "reichenau_lat.mlmodel"
DATA = HERE / ".rung2-data"
TRAIN_ARROW = DATA / "dr_train.arrow"   # 264 lines (curated split; disjoint from val)
VAL_ARROW = DATA / "dr_val.arrow"       # 47 lines

from lightning.pytorch.callbacks import ModelCheckpoint
from kraken.train import KrakenTrainer, VGSLRecognitionModel, VGSLRecognitionDataModule
from kraken.train.utils import KrakenOnExceptionCheckpoint
from kraken.configs import VGSLRecognitionTrainingConfig, VGSLRecognitionTrainingDataConfig
from kraken.lib.dataset import ImageInputTransforms

logger = logging.getLogger("rung2_kraken")


class DRDataModule(VGSLRecognitionDataModule):
    """Minimal fix for the kraken 7.0.2 datamodule bug. `_build_dataset` (parent, vgsl.py:124) passes
    `im_transforms=None` to ArrowIPCRecognitionDataset; on raw-bbox data, .add() then runs
    `self.transforms.valid_norm = True` (recognition.py:180) → AttributeError → swallowed → empty dataset.
    We override ONLY that method to pass a real ImageInputTransforms (setup() reassigns the model-sized
    transform afterward) and, per our No-Silent-Degradation guardrail, re-raise .add() failures instead of
    swallowing them. The parent __init__ (native save_hyperparameters + the explicit-eval branch that
    builds train from dr_train.arrow and val from dr_val.arrow) is otherwise untouched."""

    def _build_dataset(self, DatasetClass, training_data, **kwargs):
        dc = self.hparams.data_config
        # geometry is irrelevant here — setup() overwrites transforms; we only need a settable .valid_norm
        placeholder = ImageInputTransforms(1, 120, 0, 1, (dc.padding, 0), valid_norm=False)
        dataset = DatasetClass(
            normalization=dc.normalization,                 # 'NFC' — ſ-safe
            whitespace_normalization=dc.normalize_whitespace,
            reorder=dc.bidi_reordering,
            im_transforms=placeholder,                      # THE FIX (was None)
            **kwargs,                                        # e.g. augmentation=<data_config.augment>
        )
        for sample in training_data:
            try:
                dataset.add(**sample)
            except Exception as e:
                logger.error("dataset.add(%s) failed: %s", sample, e)
                raise  # NOT swallowed — a failed add on our single arrow is fatal, not skippable
        if dc.format_type == "binary" and (dc.normalization or dc.normalize_whitespace or dc.bidi_reordering):
            dataset.rebuild_alphabet()
        logger.info("built dataset: %d lines, alphabet=%d chars, ſ present=%s",
                    len(dataset), len(dataset.alphabet), "ſ" in dataset.alphabet)
        return dataset


def _finalize(checkpoint_cb, outdir, model_name="reichenau_dr"):
    """Convert the best-val checkpoint into a model file kraken.lib.models.load_any can read.
    Tries safetensors (kraken-native) first; falls back to legacy .mlmodel. Verifies loadability."""
    from kraken.models.convert import convert_models
    from kraken.lib import models
    best = checkpoint_cb.best_model_path
    score = checkpoint_cb.best_model_score
    if not best or score is None:
        logger.error("no best checkpoint recorded — inspect %s", outdir)
        return None
    score = float(score)
    logger.info(f"best checkpoint: {best}  (val_accuracy={score:.4f})")

    candidates = []
    # coreml (.mlmodel) FIRST — the only format kraken.lib.models.load_any parses in this build
    # (safetensors converts fine but load_any rejects it: "not loadable by any parser"). We still try
    # safetensors as a fallback so this self-heals if a future kraken adds a safetensors reader.
    for fmt, ext in (("coreml", ".mlmodel"), ("safetensors", ".safetensors")):
        try:
            op = convert_models([best], Path(best).with_name(f"best_{score:.4f}{ext}"), weights_format=fmt)
            candidates.append(Path(op))
        except Exception as e:
            logger.warning(f"{fmt} convert failed: {e}")

    # verify each candidate loads via the SAME path reocr_pipeline.py uses
    chosen = None
    for c in candidates:
        if not c.exists():
            continue
        try:
            m = models.load_any(str(c))
            n = len(m.nn.codec.c2l) if getattr(m.nn, "codec", None) else "?"
            logger.info(f"VERIFIED loadable: {c.name} (codec={n})")
            chosen = c
            break
        except Exception as e:
            logger.warning(f"{c.name} not loadable by load_any: {e}")

    if chosen is None:
        logger.error("no loadable model produced — inspect %s", outdir)
        return None
    dest = HERE / "models" / f"{model_name}{chosen.suffix}"
    shutil.copy2(chosen, dest)
    logger.info(f"FINAL Rung-2 model → {dest}  (val_accuracy={score:.4f}, CER≈{1-score:.4f})")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="models/reichenau_dr", help="checkpoint dir")
    # COMMA-SEPARATED LISTS (2026-07-29, item 2): the chapter harvest (`rung2_chapter_pairs.py`) is a SECOND
    # arrow, and kraken's config already takes a list of training files. Composing them beats recompiling the
    # original, which would risk quietly reshuffling the 264/47 split the current reichenau_dr was measured on.
    ap.add_argument("--train-arrow", default=str(TRAIN_ARROW),
                    help="training arrow(s), comma-separated (default: the original 264-line split)")
    ap.add_argument("--val-arrow", default=str(VAL_ARROW), help="validation arrow(s), comma-separated")
    ap.add_argument("--model-name", default="reichenau_dr", help="output model basename in models/")
    ap.add_argument("--epochs", type=int, default=100, help="max epochs (early-stops via --lag)")
    ap.add_argument("--min-epochs", type=int, default=8)
    ap.add_argument("--lag", type=int, default=10, help="early-stop patience (epochs w/o val gain)")
    ap.add_argument("--lrate", type=float, default=1e-3)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--resize", default="union", choices=["union", "new", "fail"],
                    help="union = extend reichenau codec w/ DR glyphs, keep base weights")
    ap.add_argument("--quit", default="early", choices=["early", "fixed"])
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    train_arrows = [Path(x) for x in a.train_arrow.split(",") if x.strip()]
    val_arrows = [Path(x) for x in a.val_arrow.split(",") if x.strip()]
    for arr in train_arrows + val_arrows:
        if not arr.exists():
            logger.error("missing %s — run rung2_prepare.py / rung2_chapter_compile.py first", arr); return 1
    logger.info("train arrows: %s", ", ".join(p.name for p in train_arrows))
    logger.info("val   arrows: %s", ", ".join(p.name for p in val_arrows))
    if not BASE.exists():
        logger.error("missing base model %s", BASE); return 1

    outdir = HERE / a.out
    outdir.mkdir(parents=True, exist_ok=True)
    accel, devices = (a.device, 1)

    # params fed to BOTH configs (each pops what it needs; mirrors the CLI passing full params to both)
    params = dict(
        format_type="binary",
        normalization="NFC",              # ſ-SAFE (NFKC banned)
        normalize_whitespace=True,
        bidi_reordering=True,
        training_data=[str(p) for p in train_arrows],
        evaluation_data=[str(p) for p in val_arrows],
        partition=1,
        resize=a.resize,                  # 'union' extends codec, keeps ſ-faithful base weights
        quit=a.quit,
        lag=a.lag,
        min_epochs=a.min_epochs,
        epochs=a.epochs,
        lrate=a.lrate,
        batch_size=a.batch_size,
        num_workers=0,                    # macOS: avoid arrow+multiprocessing deadlocks
        weights_format="safetensors",
        checkpoint_path=str(outdir),
    )
    dm_config = VGSLRecognitionTrainingDataConfig(**params)
    m_config = VGSLRecognitionTrainingConfig(**params)

    data_module = DRDataModule(dm_config)

    abort_cb = KrakenOnExceptionCheckpoint(dirpath=str(outdir), filename="checkpoint_abort")
    checkpoint_cb = ModelCheckpoint(dirpath=str(outdir), save_top_k=5, monitor="val_metric",
                                    mode="max", auto_insert_metric_name=False,
                                    filename="checkpoint_{epoch:02d}-{val_metric:.4f}")

    trainer = KrakenTrainer(
        accelerator=accel, devices=devices, precision="32-true",
        max_epochs=a.epochs,   # hard ceiling (circuit-breaker); EarlyStopping (quit='early') stops sooner on plateau
        min_epochs=a.min_epochs,
        enable_progress_bar=True, enable_summary=False,
        deterministic=False,
        accumulate_grad_batches=1, gradient_clip_val=1.0,
        num_sanity_val_steps=0, check_val_every_n_epoch=1,
        callbacks=[abort_cb, checkpoint_cb],
    )

    logger.info(f"fine-tuning reichenau_lat → DR (device={a.device}, resize={a.resize}, lag={a.lag}, "
                f"bs={a.batch_size}, lr={a.lrate})")
    with trainer.init_module(empty_init=False):
        model = VGSLRecognitionModel.load_from_weights(str(BASE), config=m_config)

    trainer.fit(model, data_module)

    dest = _finalize(checkpoint_cb, outdir, model_name=a.model_name)
    return 0 if dest else 1


if __name__ == "__main__":
    raise SystemExit(main())
