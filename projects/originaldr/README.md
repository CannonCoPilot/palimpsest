# OriginalDR

Recovering a faithful documentary transcript of the **first-edition Douay-Rheims Bible** — the 1582 Rheims
New Testament and the 1609/1610 Douai Old Testament — in archaic typeset and archaic spelling, from
photographic surrogates.

Moved here from `core/.scratch/originaldr-project/` on 2026-08-05. It was previously in a gitignored scratch
directory and therefore unprotected; everything a human typed is now under version control.

## Layout

| path | what |
|---|---|
| `ocr-spike/` | the working pipeline — recognition, alignment, collation, campaign tooling |
| `ocr-spike/ground-truth/` | hand-made ground truth and the transcription `GUIDELINES.md` |
| `ocr-spike/.rung2-data-v2/` | 1,848 hand-corrected line transcriptions (`*.gt.txt`) — the fine-tuning corpus |
| `ocr-spike/.campaign/` | campaign state and board history |
| `ocr-spike/tests/` | test suite |
| `ocr-venv/` · `calamari-venv/` · `ocr-mlx-venv/` | virtualenvs (untracked; rebuild from requirements) |

## The plan

Read in this order:

1. `ocr-spike/OCR-EXECUTIVE-SUMMARY.md` — what is being built, what it costs, open decisions
2. `ocr-spike/OCR-OVERVIEW.md` — the architecture and why it has that shape
3. `ocr-spike/OCR-WALKTHROUGH.md` — a leaf becoming a transcript line, gate by gate
4. `ocr-spike/OCR-MASTERPLAN.md` — the plan itself

Campaign operating documents: `CAMPAIGN-STATUS.md` · `CHAPTER-WORKFLOW.md` · `WALKTHROUGH-PROTOCOL.md`.
Superseded planning documents and their critique records are kept in `ocr-spike/archive/` for provenance.

## Source scans

The scans live in the Palimpsest corpus, outside this directory:

```
palimpsest/imports/Scripture/Bibles/DouayRheims_DR/sources/scans/
```

**Three volumes, three copies of each** — all of one first-edition printing per volume:

| volume | copies |
|---|---|
| **NT 1582** (Rheims) | `S01_1582-first-edition-3vol/nt-1582.pdf` · `S08_1582-rhemes-nt-hires/S08.pdf` · `S09_nevv-testament-mart-3vol/nevvtestamentofi00mart-NT.pdf` |
| **OT1 1609** (Douai) | `S01_.../ot1-1609.pdf` · `S03_holie-bible-engl-ot-vol1/S03a.pdf` · `S09_.../holiebiblefaithf00mart_0-OT1.pdf` |
| **OT2 1610** (Douai) | `S01_.../ot2-1610.pdf` · `S03_holie-bible-engl-ot-vol2/S03b.pdf` · `S09_.../holiebiblefaithf00mart-OT2.pdf` |

**Excluded**: `S04_1633-rheims-nt` (second edition) and `S06_1610-facsimile-whole`.

## Running

```bash
cd ocr-spike
../ocr-venv/bin/python walkthrough.py --status   # campaign board
../ocr-venv/bin/python walkthrough.py --next     # next chapter to work
```

## What is tracked

**If a human typed it, it is tracked. If a script emitted it, it is not.** Line transcriptions, ground
truth, source, docs, manifests and campaign state are in version control; rasters, crops, model weights,
arrow datasets, audit dumps and virtualenvs are not — all are rebuildable from the source PDFs or from a
pipeline run. See `.gitignore`.
