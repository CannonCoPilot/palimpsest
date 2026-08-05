# Rung-2 recognizer — Kraken vs Calamari, side-by-side (2026-07-21)

**Task:** build the per-typeface DR recognizer (Rung 2) TWO ways and compare, so we're not hostage to one
buggy tool. Both trained on the SAME 264/47 line split; ſ kept surface-safe (NFC, no dictionary/LM);
ſ-count checked on every output.

## TL;DR — Kraken fine-tuned WINS; ship `reichenau_dr.mlmodel` as R2.

| grain | metric | **Kraken fine-tuned** | Calamari from-scratch | base (reichenau_lat) |
|---|---|---|---|---|
| **line** (47 held-out val crops, identical inputs — the FAIR head-to-head) | char-accuracy | **93.96%** (CER 0.060) | 83.94% (CER 0.161) | ~93.0% |
| **page** genesis-24 | content edit_ratio | **0.9448** | 0.5689 † | 0.9114 (R1) |
| **page** genesis-24 | surface (exact) | **0.4509** | 0.0870 † | 0.0382 (R1) |

† Calamari's PAGE number is depressed by a train/score crop mismatch (see Limitations) — its FAIR
recognizer quality is the **line-level 83.94%**, still 10 pts below Kraken.

**Decision:** Kraken `reichenau_dr` is the Rung-2 recognizer. It lifts genesis-24 content 0.8997 (base) →
0.9114 (R1) → **0.9448 (R2)** and surface 0.083 → 0.038 → **0.451**, ſ preserved (54/51).

## Why Kraken wins: transfer >> from-scratch
Kraken fine-tunes from **reichenau_lat** — a strong, ſ-faithful Latin base (≈millions of chars) — so 264 DR
lines only need to *refine* it (`resize='union'` extended the codec 223→233, adding 10 DR-only glyphs while
keeping the base's learned strokes). Calamari, constrained to 1.0.7 (see below) with **no compatible
ſ-faithful warmstart base**, learns entirely from 264 lines → plateaus at 83.9% val while its train ler
keeps falling to 0.12 (textbook small-data overfitting). An ensemble (cross-fold) of weak-base models can't
erase a 10-pt gap, so the conclusion is robust.

Both engines are honest on surface: Calamari DID learn ſ/†/archaic spelling (e.g. `8. Looke to your ſehues,
that you loſe not…` — ſ intact), it's just lower-accuracy.

## Track 1 — Kraken Python-API trainer (`rung2_finetune_kraken.py`): the `ketos train` bug, DIAGNOSED & FIXED
The blocker was NOT the data. Root cause (kraken 7.0.2):
- `VGSLRecognitionDataModule._build_dataset` (train/vgsl.py:124) passes `im_transforms=None` to
  `ArrowIPCRecognitionDataset`.
- For **raw-bbox** data, `.add()` then runs `self.transforms.valid_norm = True`
  (lib/dataset/recognition.py:180) → `AttributeError: 'NoneType'…`.
- That exception is **swallowed** by `try/except: logger.warning` (train/vgsl.py:133) → empty dataset →
  the misleading "No training data in dataset." (A silent-degradation trap: a real error laundered into a
  benign-looking empty result. DEBUG logging exposed it.)
- Only triggers for `image_type == 'raw'` bbox datasets — which is why it isn't a universal kraken bug and
  prior sessions couldn't see it.

**Fix (`DRDataModule`):** override ONLY `_build_dataset` to pass a real `ImageInputTransforms` (setup()
reassigns the model-sized transform afterward); re-raise `.add()` failures instead of swallowing them. The
parent's explicit-eval branch then builds train from `dr_train.arrow` (264) + val from `dr_val.arrow` (47).
Everything else replicates the proven CLI wiring (ketos/recognition.py:140-254): `load_from_weights`,
`resize='union'`, `KrakenTrainer.fit`, EarlyStopping auto-wired via the model's `configure_callbacks`.

Result: best epoch 6, **val_accuracy 0.9396 (CER 0.060)**, verified loadable by `models.load_any`, saved to
`models/reichenau_dr.mlmodel`. (Only the coreml `.mlmodel` format loads via `load_any` in this build;
safetensors converts but is rejected — the finalizer tries both and picks the one that verifies.)

## Track 2 — Calamari: stack version-hell, UNBLOCKED
pip on Python 3.12 can only resolve **calamari 1.0.7** (2.x needs `ocrd-fork-tfaip` → old TF w/o 3.12
wheels). 1.0.7 (≈2020) fights the modern stack; two env vars patch it (MANDATORY for train AND predict):
- `TF_USE_LEGACY_KERAS=1` — Keras-3 forbids calamari's `K.cast` on symbolic tensors (needs tf-keras/Keras-2).
- `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` — calamari's generated `_pb2.py` needs protobuf ≤3.20.

Trained from scratch, 264/47 split (matching Kraken), `--n_augmentations 5`, `--text_normalization NFC`,
early-stop → best **val 83.94%**. Model: `models/calamari-dr/dr_best.ckpt(.json/.h5)`.

## Artifacts
- `ocr-spike/rung2_finetune_kraken.py` — Kraken Python-API trainer (bug-bypass). Output `models/reichenau_dr.mlmodel`.
- `ocr-spike/score_engines.py` — fair page-level cross-engine scorer (same seg, native recognition each).
- `ocr-spike/.scratch/probe_datamodule.py` — the diagnostic that nailed the `im_transforms=None` root cause.
- `calamari-venv/` — isolated py3.12 venv (calamari 1.0.7 + TF 2.21 + tf-keras).

## Limitations / honest caveats
- **Calamari page-level (0.57) is mismatch-penalized**, not pure recognizer quality: it trained on
  `rung2_prepare` crops (from full-res 3334px pages) but is scored on `extract_polygons` crops from the
  2200px-downscaled page with baseline-polygon masking. Its fair number is the line-level 83.94%.
- **Asymmetric comparison**: Kraken = transfer from a strong base; Calamari = from-scratch (no compatible
  ſ-faithful 1.0.7 warmstart base available). This is a real methodological difference, reported not hidden.
- **psalms-118 stays ~0.43 for ALL rungs** — layout-confounded (recognizer emits verse-numbers/marginalia
  the gold body excludes). That's the known Rung-1 body-region-typing gap, not a recognizer failure.
- Held-out scripture pages (colossians-3, proverbs-16) lack `page_index`; loadable held-out pages (nt-marke)
  have empty gold body — so page-level scoring uses training pages (partial overlap, labeled), while the
  CLEAN generalization signal is the 47 held-out val line-crops (line-level table above).
