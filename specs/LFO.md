# Literary Feature Ontology (LFO) — Specification v0.1

**Date**: 2026-06-09
**Status**: Active
**Machine-readable**: `lfo-v0.1.json`

## 1. Overview

The Literary Feature Ontology (LFO) is a controlled vocabulary for Palimpsest annotation body types, modeled on the [Sequence Ontology](http://www.sequenceontology.org/) used in genome annotation. It provides standardized terms for literary features that can be detected, measured, or assigned to text spans.

## 2. Namespace

```
https://palimpsest.dev/ns/lfo/
```

All terms are referenced via the `palimpsest:lfoType` property in annotation bodies.

## 3. Term Categories

### structural — Document structure elements
| Term | Label | Description |
|------|-------|-------------|
| `structural.sentence` | Sentence | A single sentence boundary unit |
| `structural.paragraph` | Paragraph | A paragraph boundary unit |
| `structural.section` | Section | A section or chapter boundary |
| `structural.boundary` | Boundary | A generic structural boundary marker |
| `structural.dialogue.quote` | Dialogue Quote | A quoted speech span with optional speaker attribution |
| `structure.section_boundary` | Section Boundary | Section boundary from document structure (EPUB headings) |
| `structure.endnote` | Endnote | Endnote/footnote with bidirectional call-site link |
| `structure.heading` | Heading | A heading element with level and text |

### entity — Named entities and references
| Term | Label | Description |
|------|-------|-------------|
| `entity.character` | Character | A named character or person entity |
| `entity.place` | Place | A geographic location or setting |
| `entity.organization` | Organization | A named organization or institution |
| `entity.work` | Literary Work | A referenced literary or artistic work |
| `entity.coreference_link` | Coreference Link | A mention linked to a coreference chain |

### signal — Quantitative features and state assignments
| Term | Label | Description |
|------|-------|-------------|
| `signal.sentiment` | Sentiment | Valence and arousal scores |
| `signal.lexical_density` | Lexical Features | TTR, hapax count, Yule's K, word length |
| `signal.syntactic_complexity` | Syntactic Complexity | Tree depth, subordination, sentence length |
| `signal.topic_assignment` | Topic Assignment | LDA topic distribution |
| `signal.narrative_arc` | Narrative Arc | Function-word arc dimensions |
| `signal.self_similarity` | Self-Similarity | Passage-pair cosine similarity |
| `signal.rqa` | RQA Metrics | Recurrence quantification: RR, DET, LAM |
| `signal.narrative_alphabet` | Narrative Alphabet | Discrete state label from K-means |
| `signal.lithmm_state` | LitHMM State | Passage state from multivariate HMM |
| `signal.compartment` | Thematic Compartment | A/B compartment from eigenvector decomposition |
| `signal.domain_boundary` | Domain Boundary | TAD-like domain from directionality index |

## 4. Relationships

| Relationship | Meaning |
|-------------|---------|
| `is_a` | Subtype relationship (e.g., `structure.heading` is_a `structure.section_boundary`) |
| `part_of` | Containment (e.g., a sentence is part_of a paragraph) |
| `derives_from` | Computed from (e.g., `signal.lithmm_state` derives_from multiple signals) |

## 5. JSON Schema

The machine-readable LFO is stored in `specs/lfo-v0.1.json`. Each term entry:
```json
{
  "label": "Human-readable name",
  "description": "What this term represents",
  "category": "structural|entity|signal|structure",
  "is_a": "parent_term (optional)"
}
```

## 6. Extensibility

Custom X-track schemas can define new LFO terms under user-defined categories. These terms are stored in the project's `x-config/schemas/` directory and are not part of the base LFO. When an X-term proves broadly useful, it can be promoted to the base LFO in a future version.
