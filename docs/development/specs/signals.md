# Signal Format — Specification v0.1

**Date**: 2026-06-09
**Status**: Active

## 1. Overview

Signals are numerical data products produced by track extractors that don't map directly to span annotations. They include matrices, vectors, metadata, and configuration files stored in the `signals/` and `cache/` directories.

## 2. Signal Manifests

Every dense signal layer is a binary matrix/vector (`signals/{name}.bin`, float32 little-endian)
paired with a JSON manifest (`signals/{name}.json`). The manifest is the source of truth for how to
read the bytes and how each cell maps back to text. Manifest-only signals (no `.bin`) are valid
(e.g. `alphabet`).

```json
{
  "type": "self_similarity",
  "name": "self_similarity_cosine",
  "source": "urn:palimpsest:{project}",
  "reference_sha256": "<sha256 of reference.txt>",
  "dimensions": [365, 365],
  "dtype": "float32",
  "segment_offsets": [[0, 22], [24, 150], ...],   // span in reference.txt per matrix index
  "metadata": { "metric_info": { ... } }
}
```

`segment_offsets[i]` gives the character span (into `reference.txt`) that row/column `i` represents —
this is what lets a matrix cell address text. Offsets are remapped analyzable→original at write time
(the coordinate-frame contract, see `../design/analysis-design-principles.md §4`).

### Coordinate-frame fields (forward design — cross-text pre-stage)

Self-similarity is the `A = B` degenerate case of a two-operand resemblance operator `R(A, B)`
(Vision §10). To make cross-text **additive rather than a rewrite**, the manifest generalizes the
single coordinate frame into an explicit list of **axes** (P9 / FR-20, behavior-neutral for self):

```json
{
  "mode": "auto",            // auto (A=A) | cross (A×B) | probe | corpus
  "symmetric": true,         // self matrices are symmetric; cross need not be
  "storage": "dense",        // dense | sparse-topk (scale modes, P11)
  "axes": [
    {"role": "row", "project_id": "...", "ref_sha256": "...", "segment_offsets": [...], "label": "..."},
    {"role": "col", "project_id": "...", "ref_sha256": "...", "segment_offsets": [...], "label": "..."}
  ]
}
```

For `mode: "auto"` (today) `axes` has length 1, and the legacy top-level
`segment_offsets`/`reference_sha256`/`dimensions` keep **mirroring `axes[0]`** — so existing readers
(`DotplotView`, `/analysis/status`) need no change. A cross-text matrix (P10 / FR-21) carries two
axes, where the `col` axis is a second operand coordinate-mapped onto the `row` (root) backbone via an
`OffsetMap` into the root frame.

## 3. Signal Files

### lithmm_meta.json
```json
{
  "n_states": 10,
  "state_descriptions": {
    "0": "High dialogue ratio, high NE density, high sentiment volatility...",
    "1": "Low lexical density, low dialogue..."
  },
  "feature_names": [
    "lexical_density", "dialogue_ratio", "ne_density",
    "sentiment_volatility", "sentence_length_variance", "topic_entropy"
  ],
  "method": "GaussianHMM"
}
```
Produced by the LitHMM track extractor. Contains auto-generated state descriptions based on feature distributions relative to global means.

### topics_dist.json
```json
{
  "n_topics": 20,
  "topic_terms": {
    "0": ["word1", "word2", "word3"],
    "1": ["word4", "word5", "word6"]
  },
  "document_topic_matrix": [[0.1, 0.05, ...], ...]
}
```
Produced by the topics track extractor. Contains the full topic-term and document-topic distributions.

### narrative_arc.json
```json
{
  "dimensions": ["staging", "progression", "tension"],
  "values": [[0.12, 0.34, 0.56], ...],
  "window_size": 1000,
  "step_size": 100
}
```
Boyd et al. 15-D function-word arc, reduced to 3 dimensions.

### rqa_metrics.json
```json
{
  "recurrence_rate": 0.032,
  "determinism": 0.456,
  "laminarity": 0.234,
  "threshold": 0.5,
  "embedding_dim": 2560
}
```
Recurrence Quantification Analysis metrics from the self-similarity matrix.

## 4. Cache Files

The embedding store comes in **two families**, both sqlite-vec databases under `cache/`:

### cache/embeddings.db
Paragraph-level embeddings for whole-text search. Keyed by paragraph index (`para_index` ≥ 0).
- `vec_items` virtual table: `embedding FLOAT32[{dim}]` (cosine); `vec_meta`: `rowid, id, para_index, metadata`
- Dimension matches the embedding model (e.g. 2560 for Qwen3-Embedding-4B).

### cache/embeddings_{label}.db
Chunk-level embeddings produced by the **EmbeddingTrack** layer (Wave-0). `{label}` is a
content-addressed hash of `provider + endpoint + model + chunk_texts`, so re-running with the same
inputs reuses the cache and distinct configs coexist. Chunk rows carry `para_index = -1`; row order
(`rowid`) is insertion = chunk order and is load-bearing for matrix reconstruction.

### cache/spacy_*.pickle
Cached spaCy Doc objects for the reference text. Model-versioned.

## 5. Coordinates

### coordinates.json
```json
{
  "character_offset": {
    "type": "linear",
    "label": "Character Offset",
    "total": 142791
  },
  "paragraph_index": {
    "type": "discrete",
    "label": "Paragraph",
    "total": 365,
    "offsets": [[0, 22], [24, 150], ...]
  },
  "section_index": {
    "type": "discrete",
    "label": "Section",
    "total": 13,
    "offsets": [[0, 5000], [5000, 12000], ...]
  },
  "sentence_index": {
    "type": "discrete",
    "label": "Sentence",
    "total": 1132
  },
  "endnote_region": {
    "type": "boolean",
    "label": "Endnote Region",
    "separator_offset": 900000
  }
}
```

Coordinate systems map between different indexing schemes. The `character_offset` system is the canonical reference; all other systems provide mappings to/from character offsets.
