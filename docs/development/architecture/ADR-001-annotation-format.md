# ADR-001: W3C Web Annotation Data Model as Primary Format

**Status**: Accepted
**Date**: 2026-06-06
**Deciders**: Project lead

## Context

Palimpsest needs a primary annotation storage format for the multi-track feature extraction pipeline. The format must support:
- Overlapping annotations (a passage can simultaneously be a scene boundary, thematic tag, and entity mention)
- Multiple selector types (character offset for speed, text quote for robustness)
- Extensibility (custom annotation types per text without modifying core code)
- Browser-native loading (the React frontend fetches annotation data via HTTP)
- Interoperability with external annotation tools

### Options Considered

1. **Custom PAF (Palimpsest Annotation Format)** — A GFF3-analogue TSV format designed for columnar operations and grep-friendliness. Proposed in research document 07 §3.5.
2. **W3C Web Annotation Data Model (JSON-LD)** — The 2017 W3C Recommendation for web-native annotations. Evaluated in research documents 07 §6.2 and 08 §Recommendations.
3. **Custom binary format** — Maximum performance, minimum interoperability.

## Decision

**W3C Web Annotation (JSON-LD) stored as JSONL (one annotation per line)** is the primary format. PAF is retained as an export format for computational operations (filtering, intersection, coverage) where columnar access is beneficial.

## Rationale

Research documents 07 §6.2, 08 §Recommendations, and 11 §5.2 converge on this decision:

- Doc 07 §6.2: *"The W3C Web Annotation Data Model replaces our ad-hoc PAF format from §3.5."*
- Doc 08 §Recommendations: *"Build Palimpsest's data model around the W3C Web Annotation Data Model (JSON-LD)."*
- Doc 11 §5.2: *"All annotations use the W3C Web Annotation Data Model (JSON-LD)... For genome-style track operations, annotations can be exported to a PAF."*

The W3C model provides:
- **Overlapping annotations** as independent JSON objects (no XML nesting conflicts)
- **TextPositionSelector** (fast offset) and **TextQuoteSelector** (edit-robust), combinable via RefinedBy
- **Multiple bodies** per annotation (classification + comment + link simultaneously)
- **Interoperability** with Hypothes.is, INCEpTION, Annotation Studio, Recogito
- **Browser-native** wire format (JSON via fetch())
- **Extensibility** via Palimpsest-namespaced body types (palimpsest:EntityAnnotation, etc.)

JSONL storage (one annotation per line) adds:
- Streamability (process line by line)
- grep-friendliness (`grep "Mr. Bennet" tracks/entities.jsonl`)
- Simple append operations

## Consequences

- Track files use `.jsonl` extension, stored in `tracks/` directory
- Browser uses `fetch()` + split-by-newline + `JSON.parse()` per line
- `annotation/paf_export.py` converts W3C → PAF on demand for export
- All annotations carry `palimpsest:evidenceLevel` (E1-E5) and `palimpsest:confidence` at the annotation root
- Custom body types are defined in `annotation/bodies.py`

## Amendment (2026-06-29) — "PAF" has two senses; cross-text targets

- **"PAF" is overloaded.** The export named here is the *Palimpsest Annotation Format* — a single-text,
  flat annotation dump. minimap2's PAF is a *Pairwise Alignment Format* recording an alignment between
  two sequences. The deferred cross-text direction (P10 / FR-21) needs the latter as a **distinct**
  format (query/target coordinates in both frames), not an overload of this annotation export. See
  `../specs/paf-v0.1.md` ("Naming") and `../specs/PAF-export.md`.
- **Second-source / root-frame targets.** The W3C `target.source` field — which text a selector's
  offsets address — is the seam for cross-text. A cross-text alignment annotation is expressed in the
  **root** text's coordinate frame (the operand span mapped via an `OffsetMap`, the same excise/remap
  math as masking) while retaining the operand source for provenance; it rides E3 ("Cross-text
  alignment evidence") with no new selector type. The single-source assumption is therefore a default,
  not a structural constraint. See `../specs/annotation-model.md §5`.
