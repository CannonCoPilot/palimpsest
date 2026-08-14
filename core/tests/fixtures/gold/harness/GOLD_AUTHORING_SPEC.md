# Gold-Set Authoring Spec (Palimpsest mask-detection ratification)

You are authoring a **gold ground-truth contract** for ONE work, to the same standard as the
existing 9 gold contracts. Your job: read the work's text by eye, identify EVERY structural mask
element and its type, and encode them as anchored annotations that verify cleanly.

## Repo / environment
- Repo root: `/Users/nathanielcannon/Claude/Projects/palimpsest` (run all commands from here).
- Python: `.venv/bin/python` (pymupdf/bs4 Pyright "could not be resolved" = stale-LSP noise, ignore).
- Gold contracts live in `core/tests/fixtures/gold/work-<idx>.json`.

## Step 1 — get the text (the SAME stream the verifier resolves against)
```
.venv/bin/python core/tests/fixtures/gold/harness/dump_work.py text <idx>    # -> core/tests/fixtures/gold/harness/text/work-<idx>.txt
.venv/bin/python core/tests/fixtures/gold/harness/harness.py eval <idx>      # detector diagnostics (by_type, uncovered runs, flagged)
```
Read `text/work-<idx>.txt` (use Read with offset/limit; files can be multi-MB). The detector
diagnostics in `core/tests/fixtures/gold/harness/diagnostics/work-<idx>.json` show what the CURRENT detector finds
(by_type counts, biggest uncovered runs, flagged elements) — a starting map, NOT ground truth.

## Step 2 — study the existing contracts as TEMPLATES
Read these for the schema + style (counts, count_cue wording, honest caveats):
- `core/tests/fixtures/gold/work-100.json` (scripture: book/chapter_heading/colophon, primary/secondary)
- `core/tests/fixtures/gold/work-70.json`  (novel: volume/chapter/endnotes/colophon)
- `core/tests/fixtures/gold/work-103.json` (poetry anthology: contents/preface/dedication/index/back_matter)
- `core/tests/fixtures/gold/work-101.json` (composite, per-instance edges note, footnotes/insert)

## Schema (each annotation)
```jsonc
{
  "type": "<one of the 34 SECTION_TYPES>",
  "mask": <bool — MUST equal DEFAULT_MASK_BY_TYPE[type]; gold_verify flags mismatches>,
  "structure": "repeating" | "single",
  "role": "primary" | "secondary",   // primary drives the A3 rating; secondary = grouping level
  // repeating:
  "expected_count": <int | null>,
  "count_cue": "<how the count is derived/verified — be specific & honest>",
  "exemplars": [ {"start_anchor": "<unique substring>", "note": "<which instance>"} ],
  // single:
  "resolve": "first" | "last",       // optional, default first; 'last' uses rfind
  "start_anchor": "<unique substring>",
  "end_anchor": "<unique substring>" | "<<EOF>>",
  "note": "<observations, type rationale, caveats>"
}
```
Top-level keys: `schema` (copy the standard string from work-100), `idx`, `source_file` (basename
from `harness.py order` — MUST match), `work` (short title), `annotations`.

## SECTION_TYPES (34) and mask defaults
Get them authoritatively:
```
.venv/bin/python -c "import sys;sys.path.insert(0,'core');from palimpsest.layout import SECTION_TYPES,DEFAULT_MASK_BY_TYPE,_UNMASKED_TYPES;print(sorted(SECTION_TYPES));print('UNMASKED',sorted(_UNMASKED_TYPES));print(DEFAULT_MASK_BY_TYPE)"
```
`_UNMASKED_TYPES` (mask=False): body, volume, book, part, chapter, letter, commentary, poetry.
All other registered types default mask=True. **Set `mask` to match** or gold_verify flags it.

This corpus especially needs these types where present (often missing/under-annotated elsewhere):
`translation`, `commentary`, `introduction`, `footnotes`, `epigraph`, `bibliography`, `preface`,
`foreword`, `appendix`, `glossary`, `index`, `title_page`, `copyright`, `front_matter`, `back_matter`.

## Anchor rules (CRITICAL)
- Every `start_anchor` / `end_anchor` / exemplar anchor MUST resolve **exactly once** in the text.
- Verify counts PROGRAMMATICALLY (the text has `\xa0`, thin spaces, dropcaps — `grep` will mislead):
```
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0,'core/tests/fixtures/gold/harness')
from harness import project_for
t = project_for(<idx>).reference_text()
for a in ["candidate anchor 1","candidate anchor 2"]:
    print(t.count(a), repr(a))
PY
```
- Dropcaps often split the first letter ("T\nhe Book..."), so start anchors a few chars in.
- For repeating structures, pick 1–3 exemplars that resolve uniquely; the count lives in expected_count.

## Step 3 — verify (must pass before you're done)
```
.venv/bin/python core/tests/fixtures/gold/gold_verify.py <idx>   # MUST print "OK — all gold consistent"
.venv/bin/python core/tests/fixtures/gold/a3_score.py <idx>      # record the rating
```
Iterate until gold_verify is GREEN (no PROBLEM lines). If an anchor resolves 0× or >1×, fix it.

## Honesty standard (non-negotiable)
- Vet by eye. Note mistyping, untyped sections, misalignments. Flag anything you're unsure of in the
  `note`/`count_cue` rather than guessing a clean number.
- Do NOT fabricate counts or anchors. If a layer isn't cleanly extractable (e.g. PDF Arabic glyphs as
  garbage), say so explicitly and scope the contract to what IS extractable.
- Cross-check counts against external truth where it exists (canonical chapter/surah counts, the TOC).

## Deliverable (return to the orchestrator)
1. The written `work-<idx>.json` (gold_verify GREEN).
2. A concise report (≤400 words): work structure, annotation types + counts, the A3 rating, anchors
   used, and any uncertainties / pending items / type judgment calls you made.
