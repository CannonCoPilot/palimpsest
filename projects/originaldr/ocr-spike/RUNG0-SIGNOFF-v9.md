# v9 rung-0 sign-off — OriginalDR re-OCR ladder

**Iteration:** v9 (Batch v9 per `jazzy-forging-charm.md`)
**Observer:** Jarvis (visual multimodal read of rasterized PNGs)
**Gate:** `CLEARED` — 8/9 loci unblocked for rung 1; 1/9 delisted (LOCALIZATION_GAP)
**Source of record:** `diag-reocr/index.json` (per-record `inspection` fields + top-level `signoff` block)
**Skill grounding:** `AI_OCR` skill invoked per the mandatory P3 OCR-improvement protocol (spine plan §0′).

## The substantive finding

**Every routed locus goes to rung 1 (layout / region typing). Zero rung-2 (glyph-targeted) candidates. Zero rung-3 (vision-LLM).** Every raster inspected shows well-preserved period print: long-ſ, u/v swap, `vv`=w and ligatures rendered cleanly and consistently by the plate. What is breaking the OCR is **segmentation**, not recognition — marginalia bleeding into body flow, multi-body pages (scripture + `ANNOTATIONS Chap. N` blocks) treated as one column, running headers straddling the top, drop-cap frames and decorative woodcut borders un-masked.

This narrows the first-wave re-OCR compute sharply: **Surya (layout + reading order) + YOLOv11-OBB (region typing) + XY-Cut++ (body reading order) with running-header suppression and marginalia/annotation regions typed out of the body flow.** A Kraken v5 + CATMuS-Print archaic-glyph fine-tune (rung 2) is **not** warranted by this evidence — it would burn compute on a problem that isn't there.

Empirical, not guessed. Exactly the point of the rung-0 gate.

## Per-locus verdicts

| Locus | Scan | Rec. rung | Failure class | Region set (what rung 1 must type) |
|---|---|:-:|---|---|
| scripture/psalms/118 | S1 archive-ot1-1610 | 1 | layout_marginalia_bleed | body / marginalia_right_narrow / verse_number_rail / inline_reference_glyphs / section_marker_heading |
| scripture/matthew/26 | S10 eebo-NT | 1† | layout_multi_region + scan_degradation | body / annotations_block / marginalia_left_narrow / running_header (†preprocessing: Sauvola/Wolf binarization) |
| scripture/john/6 | S1 archive-nt-1582 | 1 | layout_multi_region_dense | body / thematic_sidebar_left / cross_refs_right / annotations_block / verse_number_rail |
| scripture/psalms/77 | S1 archive-ot1-1610 | 1 | layout_marginalia_prose_blocks | body / marginalia_left_prose_wide / verse_number_rail / inline_reference_letters |
| scripture/genesis/24 | S1 archive-ot1-1609 | 1 | layout_header_and_marginalia | body / running_header / marginalia_right_small_font / signature_word_left |
| scripture/matthew/27 | S1 archive-nt-1582 | 1 | layout_column_and_marginalia | body / annotation_column_left / verse_number_rail_with_xrefs / running_header |
| apparatus/ot-front/preface | S1 archive-ot1-1609 | 1 | layout_dropcap_and_marginalia | body / dropcap_frame / decorative_border_top / marginalia_right_section_titles / signature_bottom |
| apparatus/nt-front/preface | S1 archive-nt-1582 | 1 | layout_dropcap_woodcut_and_marginalia | body / dropcap_frame / decorative_woodcut_border / marginalia_right_multiline / signature_bottom |
| **apparatus/ot-front/approbatio** | **S14 eebo-vol4** | **0 → DELIST** | **localization_gap** | *(see No-Silent-Degradation flag below)* |

## No-Silent-Degradation flag — S14 approbatio

The S14 (`eebo-vol4`) raster of page 2 reads **`PROEMIAL ANNOTATIONS VPON THE BOOKE of Psalmes`** — a Psalms-specific proemial. The whole-Bible approbatio the `s_dismas` reference targets is **not on this page and not in this scan** (S14 is Psalms-only). The `best_archaic_id` of **0.9676** crosses the ≥0.90 identity bar **only because it is scored against the wrong target — "good OCR of the wrong page."** This is the exact localization pathology the ladder's docstring names as the reason the rung-0 gate exists.

**Verdict:** DELIST the S14/approbatio pairing. No rung 1/2/3 fires. The apparatus locus `ot-front/approbatio` stays **OPEN** on the worklist — the whole-Bible approbatio is not attested by S14, so a bar-crossing score against S14 must not "count." Attestation must come from a scan that actually contains the whole-Bible approbatio.

Per the spine's No-Silent-Degradation invariant: this is a fired safeguard alerting for approach-redesign (localization must exclude scope-mismatched scan/element pairings), never a terminal acceptance.

## What this unblocks

Rung 1 execution may proceed for the **8** loci above with the following recipe (from the `AI_OCR` skill, verify tools/models before build):

1. **Preprocessing**: deskew → 300+ DPI (upsample if scan is lower) → binarize (Sauvola/Wolf for the Matthew 26 case, else Otsu) → despeckle.
2. **Region typing (YOLOv11-OBB)**: label every region seen above — body, running header, marginalia (multiple flavors: narrow single-line, prose blocks, multi-line, section-titles), verse-number rails, cross-reference rails, drop-cap frames, decorative borders, `ANNOTATIONS Chap. N` blocks.
3. **Reading order (XY-Cut++ on BODY regions only)**: suppress non-body regions before ordering so drop-cap frames and `ANNOTATIONS` blocks don't bridge the gutter.
4. **Recognition**: existing engines suffice on these pages (no glyph fine-tune needed). Only after per-region OCR is complete may re-scoring happen.
5. **Dual-track CER at recompute**: content CER (NFKC-normalized) *and* surface CER (raw). Reject any correction that raises surface CER even if content CER falls.

## References

- Ladder tool: `reocr_ladder.py` (rung 0 implementation + rasterizer + content-anchored page resolution).
- Skill: `~/.claude/skills/AI_OCR/SKILL.md` (SOTA method map); `reference/sota-findings.md` (citations — treat every model/paper as unverified until URL resolves).
- Spine wiring: `sparkling-petting-gosling.md:58` (MANDATORY OCR-improvement protocol at P3/P4/P5).
- No-Silent-Degradation invariant: `partitioned-watching-dijkstra.md` (Sir, 2026-07-10).
- Machine-readable sign-off: `diag-reocr/index.json` (`records[*].inspection` + top-level `signoff` block).
