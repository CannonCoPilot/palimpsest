# PAF Export Format — Specification (DRAFT)

<!-- See §2.9 of Phase 1 plan for PAF GFF3-analogue TSV export format. To be expanded in T36. -->

The current export format (single-text, GFF3-analogue annotation TSV) is specified in
[`paf-v0.1.md`](./paf-v0.1.md). This draft is the placeholder for its expansion.

## Forward note — two-frame (cross-text) export

"PAF" is overloaded (see `paf-v0.1.md` §"Naming"). Today's export is the **Palimpsest Annotation
Format**: a flat dump of one text's annotations. The cross-text direction (P10 / FR-21) needs the
*other* sense — minimap2's genuine **Pairwise Alignment Format**, recording an alignment between a
query (operand) text and a target (root backbone) text with coordinates in **both** frames.

When cross-text export is built, it should be a **separate format** carrying query/target start/end
columns (mirroring the `axes[]` row/col coordinate frames in the signal manifest, see
`signals.md §2`), not an overload of the single-text annotation export. The alignment it serializes is
the `OffsetMap` of an operand onto the root backbone — the same coordinate math as masking, a second
target frame.
