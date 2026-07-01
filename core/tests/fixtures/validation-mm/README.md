# Matthew-Mark Cross-Translation Validation Collection

The **standing validation collection** for Palimpsest: two Matthew+Mark subtexts drawn from
different English Bible translations, used as ground truth for similarity, masking, alignment,
and collection-tier validation.

| Member | Translation | Verses | Chapters |
|---|---|---|---|
| DR-MM | Douay-Rheims (1582-1610) | 1747 | Mt 28 / Mk 16 |
| Geneva-MM | 1599 Geneva | 1749 | Mt 28 / Mk 16 |

Two independent translations of the same two gospels give known true-positive alignments
(shared synoptic pericopes) and true-negatives (unique material), plus genuine versification
variance (Geneva has +1 verse in each gospel vs the Vulgate-versified Douay-Rheims).

## Why the text bodies are not committed

The source editions (Douay-Rheims 2018 reprint; 1599 Geneva, Tolle Lege Press 2013 modernized
spelling) carry edition copyright, and this repo never commits text bodies (`imports/` and any
`reference.txt` are gitignored; the gold fixtures commit maps, not text). So this fixture commits
the **reproducible generator + validator + manifest** — the subtexts are regenerated locally.

## Regenerate

Requires the local sources: the gold Douay-Rheims ingested under `.scratch/demo/` and the Geneva
EPUB in `imports/Scripture/Bibles/`. From the repo root:

```sh
V=core/.venv/bin/python
$V core/tests/fixtures/validation-mm/build.py dr
$V core/tests/fixtures/validation-mm/build.py geneva-complete
$V core/tests/fixtures/validation-mm/build.py geneva-layout
$V core/tests/fixtures/validation-mm/build.py geneva-verses
$V core/tests/fixtures/validation-mm/build.py geneva-mm
```

Outputs land in `.scratch/validation-mm/` (gitignored).

## Create the collection

```sh
core/.venv/bin/python - <<'PY'
from pathlib import Path
from palimpsest.collections import create_collection
WS = Path(".scratch/validation-mm")
dr = next(WS.glob("douay-rheims-*chapter-in-book-*")).name
gv = next(WS.glob("1599-geneva-*chapter-in-book-*")).name
create_collection(WS, "Matthew-Mark Cross-Translation Validation",
                  project_ids=[dr, gv], collection_id="matthew-mark-validation")
PY
```

## Validate

```sh
core/.venv/bin/python core/tests/fixtures/validation-mm/validate.py
```

Prints a validation report for the Geneva-MM member: membership, per-book chapter/verse counts,
verse-number masking, and the absence of chapter arguments, cross-references, and other books
(each confirmed present in the full parent). Expected metrics for both members are in
`manifest.json`.
