# Per-source reOCR pipeline — build state (2026-07-21)

> **UPDATE 2026-07-22 — RUNG 2 BUILT (blocker RESOLVED, both engines trained).** The `ketos train` bug was
> `im_transforms=None` on raw-bbox data (swallowed AttributeError → empty dataset), NOT the data. Fixed via
> the Kraken Python-API trainer `rung2_finetune_kraken.py` (`DRDataModule` overrides `_build_dataset`).
> **Kraken fine-tuned `reichenau_dr.mlmodel`: val 0.9396 (CER 0.060); genesis-24 content 0.9448 / surface
> 0.451.** Calamari from-scratch (1.0.7, stack-unblocked): val 83.94%. Kraken wins → it is the R2 recognizer.
> Full side-by-side + root-cause: **`RUNG2-ENGINE-COMPARISON-2026-07-21.md`**.

Executing the approved redesign. Consensus is OUT; each rung improves ONE source's OCR vs gold, scored at the
grain-correct metric (page + ~20-word window + ſ-count), never the deflating per-verse metric.

## BUILT + WORKING
- **`reocr_pipeline.py`** — orchestrates the ladder on a (source,page) via a gold slug, scores each rung.
  Runs end-to-end NOW: `ocr-venv/bin/python ocr-spike/reocr_pipeline.py scripture-genesis-24`
  - `base (existing OCR)`  content **0.8997**, ſ 55/51
  - `R1 preprocess+base`   content **0.9114** (beats baseline), ſ 55/51 — kraken segment+recognize w/ reichenau_lat
  - `R2 fine-tuned`        slot ready (`--r2-model`), pending the trained model (see BLOCKER)
  - `R2.5 within-image vote` token-level, surface-safe (activates once R2 exists)
  - `R3 vision-LLM`        rasterizes + hooks a Claude/CHURRO pass; validated 0.95–0.99 surface (genesis-24/psalms-118)
  - NOTE: the low *surface* track on R1 is real signal — the recognizer emits running-header/marginalia the gold
    body excludes; that is Rung-1's layout-separation job (body-region typing) and a known next refinement.
- **`rung2_prepare.py`** — segment gold page → recognize (base) → align to gold body by folded-similarity (greedy
  1:1) → emit line-image ↔ diplomatic-gold-text pairs. Produced **311 valid pairs** (219 with ſ) in `.rung2-data/`.
- **`rung2_finetune.py`** — compiles pairs → binary arrow, patches split/counts, invokes `ketos train` from the
  reichenau base (`--resize both` to extend the codec with DR glyphs; `-u NFC` — NEVER NFKC, which folds ſ→s).
- Base models present: `reichenau_lat` (ſ-faithful), `catmus-print-large` (ſ-modernizing — reject for surface).

## ~~BLOCKER~~ RESOLVED 2026-07-22 → see `RUNG2-ENGINE-COMPARISON-2026-07-21.md`
Root cause was `im_transforms=None` on raw-bbox data (train/vgsl.py:124 → recognition.py:180 valid_norm
AttributeError, swallowed at vgsl.py:133). Bypassed via Kraken Python-API (`rung2_finetune_kraken.py`,
`DRDataModule`). The historical analysis below is retained for the record.

### (historical) kraken 7.0.2 `ketos train` datamodule
`ketos train` builds an EMPTY train_set from a PROVEN-VALID dataset → "No training data in dataset."
Diagnosed exhaustively — the DATA is correct, the CLI is broken:
- `dr_split.arrow`: 311 rows, type `kraken_recognition_bbox`, boolean split cols set (train=264/val=47), counts
  metadata patched to match, records = `{text, im→PIL (1336×75, L) OK}`.
- **`ArrowIPCRecognitionDataset(split_filter='train')` loads 264 rows + builds a 79-char codec in PYTHON.**
- But `VGSLRecognitionDataModule` (the CLI's Lightning wrapper, kraken/train/vgsl.py) yields len(train_set)==0,
  both with `--load`+`--resize` and from-scratch → not the codec path, a datamodule-wiring bug in this version.

### Unblock options (focused, data is 100% ready)
1. **kraken Python-API training** — bypass ketos CLI: construct `VGSLRecognitionModel.load_from_weights(reichenau)`
   + a datamodule (or custom Lightning loop) fed by the WORKING `ArrowIPCRecognitionDataset` splits, then `fit`.
   (kraken.train: KrakenTrainer, VGSLRecognitionModel; kraken.configs: VGSLRecognitionTrainingConfig/DataConfig.)
2. **kraken version** — try a kraken where `ketos compile`→`train` round-trips (5.2.x / eScriptorium-tested),
   in a separate venv; the arrow + prep are format-stable.
3. **Calamari** — alternate engine; `calamari-cross-fold-train` on the same line pairs (also gives R2.5 voting).

Once R2 trains, expected (per verified research): CER toward ≤0.10 on the target typeface with these ~264 lines
(transfer-learning: −26–43% error at 60–150 lines; OCRopus/Calamari on period GT hit 0.02–0.10). Then wire the
R2 model into `reocr_pipeline.py --r2-model` and run 1–2 docs base→R1→R2→R2.5→R3 to see the full progression.
