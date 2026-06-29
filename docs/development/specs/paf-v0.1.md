# Palimpsest Annotation Format (PAF) v0.1

PAF is a tab-separated values (TSV) export format inspired by GFF3 and PAF (minimap2).
It provides a flat, tool-friendly representation of W3C JSONL annotations for
interoperability with genomics tools and spreadsheets.

## Columns

| # | Name | Type | Description |
|---|------|------|-------------|
| 1 | `annotation_id` | string | Unique annotation URN |
| 2 | `track` | string | Track name (e.g., "entities", "sentiment") |
| 3 | `lfo_type` | string | LFO term (e.g., "entity.character") |
| 4 | `start` | int | Start character offset (0-based, inclusive) |
| 5 | `end` | int | End character offset (0-based, exclusive) |
| 6 | `confidence` | float | Confidence score [0.0, 1.0] |
| 7 | `evidence_level` | string | E1–E5 evidence classification |
| 8 | `creator` | string | Creator identifier |
| 9 | `value` | string | Primary body value (truncated to 200 chars) |
| 10 | `attributes` | string | Semicolon-separated key=value pairs for extra body fields |

## Example

```tsv
urn:palimpsest:pp:entities:a1b2	entities	entity.character	0	12	0.85	E4	spacy/en_core_web_lg	Mr. Bennet	entityType=PER;canonicalName=Mr. Bennet
urn:palimpsest:pp:sentiment:c3d4	sentiment	signal.sentiment	0	116	0.90	E3	vader/0.1		valence=0.4215;arousal=0.0
```

## Notes

- Header line begins with `#` and lists column names.
- Empty values are represented as `.` (GFF3 convention).
- The `attributes` column uses semicolon-delimited `key=value` pairs.
- Character offsets reference the `reference.txt` canonical text.
- PAF files use `.paf` extension.

## Validator

`palimpsest validate <file.paf>` checks:
1. Correct column count (10)
2. Valid LFO type against `specs/lfo-v0.1.json`
3. `start < end` and both non-negative
4. Confidence in [0.0, 1.0]
5. Evidence level in {E1, E2, E3, E4, E5}

## Naming: two senses of "PAF"

The acronym is overloaded, and the distinction matters for the cross-text direction:

- **PAF here = Palimpsest Annotation Format** — a flat, single-text TSV *export* of W3C annotations
  (the columns above). Every row's `start`/`end` address one text's `reference.txt`.
- **PAF in minimap2 = Pairwise Alignment Format** — a genuine record of an alignment *between two
  sequences*, with coordinates in both frames.

Today Palimpsest only emits the first sense. The forward cross-text work (P10 / FR-21) introduces the
*second* sense as a distinct concern: a cross-text alignment is a mapping from an operand text onto a
**root backbone** — an `OffsetMap` into the root frame, the same excise/remap math used for masking,
pointed at a second target. That alignment is the LFO `signal.cross_text_similarity` layer (E3
evidence), **not** an annotation-export row. When cross-text export lands, it should adopt minimap2's
genuine two-frame PAF columns (query/target start/end) rather than overloading this single-text export
format. See `PAF-export.md` and `../design/wave0-analysis-suite-vision.md §10`.
