# Matter Transcription Agent Brief — OriginalDR Gold Transcripts
You are a diplomatic transcription agent for the OriginalDR project (computational restoration of the
1582/1609/1610/1635 Douay-Rheims Bible). You transcribe ONE front/back-matter section into a Gold Transcript.

## Paths & tools
- Working dir: `/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr`
- Python venv: `ocr-venv/bin/python`
- **Rules you MUST read + follow first**: `ocr-spike/ground-truth/GUIDELINES.md` — especially §long-ſ
  (GLYPH-DRIVEN, decide ſ vs round-s per glyph by zooming, NEVER by position), §typos (preserve as printed),
  §catchwords (EXCLUDE from body, record separately), §w-regime (PER-INSTANCE visual call — do not apply a
  uniform rule; OT roman body is usually real `w`, small/italic apparatus may be genuine `vv`; decide per
  glyph and flag ambiguous ones), §glyph-repertoire (ligatures, s-variants), §structure, §uncertain.
- **Schema examples**: `ocr-spike/ground-truth/matter-ot1-approbatio.json` (prose/latin),
  `matter-nt-preface.json` (prose), `matter-ot2-table-epistles.json` (table).

## ⚡ EFFICIENCY (MANDATORY — 2026-07-20) — read in a FEW large bands, NOT dozens of micro-crops
Token/time budget is real. The failure mode to avoid: reading a page as many tiny quadrant/band crops
(dozens per page). Instead: render the page ONCE, then read it in **3–5 large horizontal bands** (top→bottom)
at a legible zoom (e.g. crop full-width × ~1/4-height, upscale ~1.5–2×). Resolve the great majority of glyphs
from those bands. Take a **targeted micro-crop ONLY for an individual glyph you genuinely cannot resolve**
from the band. Do not re-crop the same region repeatedly to "re-verify" — decide, flag if uncertain, move on.
A short single-page section should take a handful of reads, not 40. Prefer fewer, larger reads.

## Rendering source pages (to locate + read your section)
Render any page of a source to PNG, then Read the PNG:
```
ocr-venv/bin/python ocr-spike/jp2_page.py <ocr_dir> <page_index>   # writes a PNG, prints its path
```
Page through the given region until you find your section (identify by heading, running header, content).
Front matter ≈ first ~55 pages of a volume; back matter ≈ last ~55 pages. Always use the jp2 (highest raster).

## Transcribe the WHOLE section — diplomatic, as-printed
- A section may span multiple pages — transcribe ALL of them; note continuation + every printed page label.
- long-ſ per glyph; w/vv per instance; preserve typos, abbreviations (macrons/tildes ō/ē), French spacing,
  punctuation as printed. Latin sections: transcribe the Latin exactly. Exclude catchwords from body.

## REQUIRED — interval coordinates (the matter analog of verses)
Matter has no verses, so you MUST split the section into canonical **intervals** for scoring + inventory.
Emit an `intervals` array — ordered, 0-based, reading order:
```json
"intervals": [
  {"idx": 0, "kind": "heading",   "text": "THE ARGVMENT OF GENESIS.", "lines": [0]},
  {"idx": 1, "kind": "paragraph", "text": "Moyses the author of this booke ...(full de-hyphenated paragraph)...", "lines": [1,2,3,4]},
  {"idx": 2, "kind": "paragraph", "text": "...next paragraph...", "lines": [5,6,7]}
]
```
- `kind` ∈ `title_block` | `heading` | `subtitle` | `paragraph` | `table_row` | `list_item` | `colophon_line`.
- **paragraphs**: group consecutive prose/latin lines into paragraphs by the breaks you SEE on the page
  (indentation, drop-caps, spacing, a sentence closing then a new lead). One paragraph = one interval.
- **tables**: one interval per row (kind `table_row`).
- **display titles**: group the multi-line display title into one `title_block` (or a few) as printed.
- `text` = the interval's FULL canonical text: join its lines, de-hyphenate word-splits at line ends, keep
  diplomatic glyphs. Do NOT include catchwords or quire-signatures as scoring intervals (omit or kind-tag).
- `lines` = the body `line_index` values that compose the interval.

## Output — WRITE the GT to a FILE, then return a SHORT summary (do NOT paste the full JSON)
Use the **Write tool** to save your complete GT JSON to the exact path given in your task prompt
(`ocr-spike/ground-truth/matter-<vol>-<slug>.json`). GT fields: `locus` ("matter/<vol>/<slug>"),
`page_index` (or list), `ocr_dir`, `scan`, `page_label_printed`, `running_header` {left,center,right},
`layout_note`, `body` [{line_index, role, text, +drop_cap/marks}], `intervals` [as above], `uncertain`,
`observer` ("agent:<slug>"), `observed_at`, `method` (state your 4 validations here), `confidence`,
`glyph_regime_resolved`.
Then your FINAL message = a SHORT confirmation ONLY: the file path written; locus; page labels; #body lines;
#intervals (and #paragraphs); your top 3–5 uncertains; and PASS/NOTE for each of localization / identity /
placement / completeness. **Do NOT paste the full JSON** — it is already on disk (this keeps orchestration lean).

## VALIDATE before returning (state each explicitly in `method`/`confidence`)
1. **Localization** — you found the CORRECT section, not a lookalike (confirm by heading + content).
2. **Identity** — correct volume/edition (e.g. 1609 OT1 vs 1635 facsimile) — matches the requested source.
3. **Placement** — record printed page label(s) + running headers so the section can be placed in the book.
4. **Completeness** — you transcribed the ENTIRE section (all its pages); if it continues, say where.
Return ONLY the final GT JSON object.
