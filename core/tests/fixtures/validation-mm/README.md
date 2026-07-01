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

A richer **6-way** collection (`matthew-mark-6way`) adds the KJV as a third translation and splits
each translation into single-book Matthew-only / Mark-only members — the substrate for the
corpus-graph over-merge / score-gate and the synoptic precision/recall oracle. See
[The 6-way collection](#the-6-way-collection-matthewmark--three-translations) below.

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

## Embed the collection (optional)

Chunk + embed both members so the embedding-gated paths (cosine metric-congruence, cross-translation
probe) work. Requires a live embedding service — MLX at `http://localhost:8000` serving
`mlx-community/Qwen3-Embedding-4B-4bit-DWQ` (dim 2560) by default; edit the `EMBED_*` constants in
`build.py` for the Ollama fallback. Run **after** the collection exists (the step reads its
membership); both tracks are content-addressed, so re-running is idempotent (same labels, no
duplicate layers).

```sh
core/.venv/bin/python core/tests/fixtures/validation-mm/build.py embed
```

Without this step the members are word-method only: cosine congruence reports *incongruent* (missing
embedding layer) and probe fails loud — the honest deferral paths. The `collection_workbench_c7`
e2e asserts the embedded state, and its `beforeAll` guard points here if the collection isn't embedded.

## The 6-way collection (Matthew/Mark × three translations)

A richer collection, `matthew-mark-6way`, splits each translation's Matthew+Mark subtext into a
Matthew-only and a Mark-only single-book member (6 members total). It is the substrate for the
corpus-graph over-merge / score-gate, the phyletic tree, and the synoptic precision/recall oracle
(`score_synoptic.py`). Building it also needs the KJV as a third translation. Requires the KJV EPUB
in `imports/Scripture/Bibles/` in addition to the DR + Geneva sources above. After the `dr` and
`geneva-*` steps, from the repo root (`V=core/.venv/bin/python`):

```sh
# 3rd translation: the KJV, verse-paragraph patched (see manifest kjv_note), Mt+Mk+Lk superset layout
$V core/tests/fixtures/validation-mm/build.py kjv-complete
$V core/tests/fixtures/validation-mm/build.py kjv-layout
$V core/tests/fixtures/validation-mm/build.py kjv-verses
$V core/tests/fixtures/validation-mm/build.py kjv-mm
# derive the 6 single-book members + create the matthew-mark-6way collection, then assert them
$V core/tests/fixtures/validation-mm/build.py split
$V core/tests/fixtures/validation-mm/build.py validate-splits
# analysis substrate: word-align every pair + build the corpus graph
$V core/tests/fixtures/validation-mm/build.py align
$V core/tests/fixtures/validation-mm/build.py graph
```

The MM parents are discovered by glob (never by hardcoded content-hash id), and each split child's
id is a function of parent + book container, so every step is idempotent. Expected per-member verse
counts are in `manifest.json` under `companion_collections`; `validate-splits` asserts them.

For a genuine phyletic **outgroup**, add the KJV Luke subtext and build the 7-member variant:

```sh
$V core/tests/fixtures/validation-mm/build.py kjv-luke
$V core/tests/fixtures/validation-mm/build.py kjv-luke-validate
$V core/tests/fixtures/validation-mm/build.py luke-collection   # creates matthew-mark-luke-7way
```

## Validate

```sh
core/.venv/bin/python core/tests/fixtures/validation-mm/validate.py
```

Prints a validation report for the Geneva-MM member: membership, per-book chapter/verse counts,
verse-number masking, and the absence of chapter arguments, cross-references, and other books
(each confirmed present in the full parent). Expected metrics for both members are in
`manifest.json`.

## Score synoptic detection (precision/recall)

`validate.py` checks the *builder* output; `score_synoptic.py` scores the *analysis* against the
`synoptic-ground-truth.json` oracle. It maps each oracle pericope's book/chapter:verse refs to
paragraph indices via `tracks/verses.jsonl`, reads the collection's cross-book alignment edges, and
reports: pooled recall over the 101 shared pericopes (TP), record-level precision, the true-negative
false-link rate over the 51 unique passages (TN), and — with `--min-score` — a corpus-graph
`edge_min_score` sweep showing whether the two source texts separate into distinct backbones.

Run against a locally-built, verse-tracked collection (e.g. `matthew-mark-6way`):

```sh
core/.venv/bin/python core/tests/fixtures/validation-mm/score_synoptic.py matthew-mark-6way --min-score 10
```

The scorer's logic is regression-tested on synthetic data in `core/tests/test_synoptic_scorer.py`
(the text bodies are gitignored, so the scorer is a CLI, not a CI test). Empirical results on the
6-way (word method) and the resolution of the corpus-graph over-merge are recorded in
`docs/development/collections-tier-build-journal.md`.
