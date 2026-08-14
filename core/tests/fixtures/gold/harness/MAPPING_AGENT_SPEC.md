# Gold Masking-Map Completion — Agent Spec (ONE work per agent)

## Mission
Build the COMPLETE masking map of ONE Gold-Set work: every mask element typed
CORRECTLY (accuracy) with EXACT boundaries (precision), such that **every character
is covered by ≥1 GENERIC and ≥1 SPECIFIC mask-type**. This is the GOLD's own
ground-truth map from close reading of the actual text — NOT the detector's output.
Do not run or reference the detector.

## THREE GATING REQUIREMENTS (non-negotiable, cover to cover)
1. **100% accurate** — every region carries its CORRECT type. No catch-all `header`/`body`
   stand-ins. Apparatus (footnotes, commentary, notes) must NOT be absorbed into the
   content type that contains it — it gets its own typed, bounded element ON TOP of the tile.
2. **100% precise** — exact element boundaries (start AND end land on the real edges).
3. **Two-layer everywhere** — NO segment generic-only, NO segment specific-only, NO uncovered.
   `coverage_pct` MUST be `{'COVERED': 100.0}` exactly.

## NO DEFERRALS
Do NOT omit, defer, or "flag for later" ANY masking. If a footnote/commentary/part/apparatus
region exists, materialize and type it NOW. A count you cannot verify is fine — type the REGION
as a bounded element of the correct type (you do not need a per-note integer). But the region
must be present, correctly typed, and exactly bounded. "Covered by the surrounding tile" is NOT
acceptable for apparatus — the apparatus needs its own typed element. If you find any error or
incompletion, FIX IT in your returned RULES/SUPPLEMENT; do not surface it as a flag.

## Environment
- Repo root: `/Users/nathanielcannon/Claude/Projects/palimpsest` (run ALL commands from here).
- Python: `.venv/bin/python`. (pymupdf/bs4 Pyright "could not be resolved" = stale-LSP noise, ignore.)
- Engines (read them): `core/tests/fixtures/gold/harness/instance_edges.py`, `core/tests/fixtures/gold/harness/masking_map.py`.
- Existing gold contract: `core/tests/fixtures/gold/work-<IDX>.json` — PRIOR close reading.
  Its `count_cue` fields describe each repeating delimiter; `exemplars` give sample anchors;
  non-repeating ("single") masks in it are read automatically. Treat counts as claims to VERIFY.

## Taxonomy (34 types)
- GENERIC = {body, volume, book, part}.  SPECIFIC = the other 30, INCLUDING `chapter`.
- Two-layer rule: every char needs ≥1 generic + ≥1 specific. `body [0,EOF]` is auto-added as the
  base generic, so your job is to ensure the SPECIFIC layer TILES 100% of the text:
  front matter → content instances (chapters/poems/verses/letters/translations) → back matter,
  contiguous, no gaps. Any gap shows up as GENERIC_ONLY (sparse) in the audit.

## How the materialized map is built
`masking_map.build_elements(idx)` combines: body[0,EOF] + gold singular masks + your
`SUPPLEMENT[idx]` singular masks + `instance_edges.RULES[idx]` repeating instances (tiled).

### Repeating-rule kinds (in instance_edges.materialize)
- `roman_in_span`: {type, kind:"roman_in_span", span_start, span_end, extra_anchors:[...], expected_count}
  — bare `^[IVXLC]+$` lines inside the [span_start,span_end) anchors; extra_anchors add non-numbered instances.
- `title_list`: {type, kind:"title_list", titles:[...], expected_count}
  — each "Title\n\n" body occurrence (text is \xa0→space normalized). For short/ambiguous titles it
  falls back to "\n\nTitle\n\n".
- `regex_in_span`: {type, kind:"regex_in_span", pattern:r"(?m)^...", at:"start"|"end",
  span_start?, span_end?, tile?, expected_count}
  — header regex. `at:"end"` anchors the instance at the content AFTER the header (e.g. an epigraph).
  `tile`:True (default) = contiguous partition (chapters/poems/verses); `tile`:False = thin markers
  (a heading line; spans to the next \n\n) — use for `chapter_heading`-style markers that should NOT
  swallow the body.
If none fit, DESCRIBE the rule you need and return a `materialize()` snippet — but try hard to use these.

### SUPPLEMENT singular masks (front/back/apparatus the gold omits)
`masking_map.SUPPLEMENT[idx] = [{"type":..., "start_anchor":..., "end_anchor":..., "resolve"?:"last"}]`
Anchors must resolve EXACTLY once. `<<BOF>>`=0, `<<EOF>>`=len. Use these to type title pages,
prefaces, TOC, introductions, indexes, glossaries, colophons, appendices, pooled footnotes, etc.

## Modeling guidance (match the done examples)
- Scripture (see idx5 RULES+SUPPLEMENT): book tiled (generic) + chapter tiled (specific, covers verses)
  + optional chapter_heading markers (tile:False) + front_matter/appendix/glossary supplements.
- Poetry (idx102 roman / idx103 title_list) + part (generic). Novels (idx71 title_list).
- Scholarly anthologies: part (generic) + per-text translation/introduction/bibliography (tiled specific,
  usually `regex_in_span` on a recurring header like `\n\nBibliography\n\n`, or `title_list` of TOC titles)
  + pooled footnotes as a SUPPLEMENT block + front/back matter.
- A tiled CONTENT element (chapter/translation/poetry) is what gives the body its SPECIFIC layer; make sure
  one tiles the whole main matter.

## Verify (do NOT edit the shared engines — monkeypatch in a scratch script)
Write `core/tests/fixtures/gold/harness/_verify_<IDX>.py`:
```
import sys; sys.path.insert(0,'core/tests/fixtures/gold/harness')
import instance_edges, masking_map
instance_edges.RULES[<IDX>] = [ ...your rules... ]
masking_map.SUPPLEMENT[<IDX>] = [ ...your supplement... ]
a = masking_map.audit(<IDX>)
print("coverage:", a["coverage_pct"])
print("counts:", {k:v for k,v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
for r in a["sparse_regions"][:10]: print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head","")[:60]))
```
Run `.venv/bin/python core/tests/fixtures/gold/harness/_verify_<IDX>.py`. Iterate until:
- coverage COVERED ≥ 99.5% (aim 100%); no UNRESOLVED masks;
- every repeating rule's materialized count == expected_count (the count gate).
VERIFY every count programmatically against `project_for(<IDX>).reference_text()`. If a gold count is
wrong, CORRECT it with evidence (state old→new + why). NEVER fabricate a count or force a fake green.

## Honesty standard
Vet by eye + programmatically. Flag OCR garble, ambiguous counts, type judgment calls. If a region
can't be cleanly typed, say so and scope to what's defensible. Do not guess silently.

## RETURN (concise, structured)
1. Final `RULES[<IDX>] = [...]` and `SUPPLEMENT[<IDX>] = [...]` as copy-pasteable Python.
2. audit `coverage_pct` + nonzero `type_counts`.
3. Count corrections (old→new + evidence), if any.
4. One-line type justification per element kind (text evidence).
5. Flagged approximate/uncertain regions (coords + why).
Keep prose tight. The Python blocks + audit numbers are the deliverable.
