# Signal Format — Specification v0.1

**Date**: 2026-06-09
**Status**: Active

## 1. Overview

Signals are numerical data products produced by track extractors that don't map directly to span annotations. They include matrices, vectors, metadata, and configuration files stored in the `signals/` and `cache/` directories.

## 2. Signal Files

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

## 3. Cache Files

### cache/embeddings.db
SQLite database with sqlite-vec extension. Contains paragraph-level embeddings.

Schema:
- `embeddings` virtual table: `id TEXT PRIMARY KEY, embedding FLOAT32[{dim}]`
- ID format: `{project_id}:para:{paragraph_index}`
- Dimension: matches embedding model (2560 for Qwen3-Embedding-4B)

### cache/spacy_*.pickle
Cached spaCy Doc objects for the reference text. Model-versioned.

## 4. Coordinates

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
