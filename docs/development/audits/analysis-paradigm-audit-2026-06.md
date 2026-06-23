# Analysis Paradigm Audit & Remediation — 2026-06

**Date:** 2026-06-23 · **Scope:** all analysis tracks + the chunking/embedding stage + the
analyze/visualize pipeline · **Method:** adversarial review of the R1–R10 chunking/embedding
remediation, hardened by three parallel code investigations (param-contract, transparency/errors,
storage/auditability). All findings carry `file:line` evidence; claims are marked **CONFIRMED**
(verified in source) or **UNCERTAIN** (inferred / depends on out-of-repo behavior).

**Companion (target contracts):** [`../design/analysis-design-principles.md`](../design/analysis-design-principles.md).

## Summary

The R1–R10 remediation correctly hardened the `self_similarity` chunking/embedding *stage*. But the
underlying principles were applied **instance-by-instance, not structurally**. The audit found the
"no hidden defaults / validate / echo" posture covers **4 of 14 tracks**, that the headline params
were hardened while the *secondary* algorithm knobs (seeds, caps, calibration cutoffs, masking
thresholds) remain hidden constants, and that the transparency, storage, and remap machinery have
systemic gaps that the upcoming incremental walk-through will hit on nearly every layer.

Severity: **S1** = silently wrong results or disk lies · **S2** = principle violation a user would
notice / can't audit · **S3** = latent risk / cleanup.

---

## Part A — Parameter contract & hidden defaults

### Track contract table (CONFIRMED)

14 registered tracks. Only the **bold** four have a parameter contract; the rest are
un-parameterizable (no knob to set or reject).

| Track | set_params | validate_params | parameters() returns | output |
|---|:-:|:-:|---|---|
| **self_similarity** | ✓ | ✓ | live | signal |
| **topics** | ✓ | ✓ | **constants** (`N_TOPICS` etc.) | annotation |
| **sentiment** | ✓ | ✓ | **constant** `"vader"`, drops granularity | annotation |
| **lithmm** | ✓ | ✓ | live (`n_states`) | annotation |
| lexical, dialogue, entities, syntax, coreference, alphabet, narrative_arc, compartments, rqa, boundary_detection | ✗ | ✗ | constants | mixed |

`TrackExtractor` protocol (`tracks/base.py:19-63`) omits the param methods entirely — they are bolted
on, which is why coverage is partial.

### A1 — `parameters()` vs `validate_params()` divergence (S1, CONFIRMED)
`topics.validate_params()` returns live `{"n_topics": self._n_topics, ...}` (`topics.py:44`) but
`topics.parameters()` returns module constants `{"topics.n_topics": N_TOPICS, ...}` (`topics.py:171-177`).
`sentiment.parameters()` returns a hardcoded `{"sentiment.model": "vader"}` (`sentiment.py:116`) even
when `method=hedonometer` was validated. The HTTP path echoes the live values; the CLI provenance
path (`cli.py:221` → `pipeline_run.json`) writes the constants. **Same analysis, different provenance
by entry point.**

### A2 — Post-validation silent clamps (S1, CONFIRMED)
After validate echoes the requested value, `extract()` shrinks it:
`topics.py:74` `n_topics = min(self._n_topics, len(paragraphs))` (and again `:87-88`);
`lithmm.py:181` `n_states = min(self._n_states, max(2, n_paras//2))`;
`alphabet.py:99` `n_clusters = min(N_CLUSTERS, n_paras)`. The echoed/stored value can disagree with
what actually ran.

### A3 — Output-affecting constants not declared (S2, CONFIRMED — selected; full list in agent report)
Seed-like (reproducibility): `topics RANDOM_STATE=42` (`:16`), `MAX_ITER=20`, `MIN_DF=2`,
`MAX_FEATURES=10000` (not even reported); `alphabet RANDOM_STATE=42`, `N_CLUSTERS=16`, `n_init=10`;
`lithmm n_iter=100, random_state=42, n_init=10` (`:189-207`, unreported);
`self_similarity np.random.default_rng(42)` calibration shuffle (`:244`).
Tuning knobs that change results: `self_similarity` LASTZ identity-threshold calibration
(`:240,267,269` — `n_samples=1000`, p95 cutoff, `0.3` fallback — **sets the alignment cutoff**),
exact-repeat masking `min_words=3, min_occurrences=3` (`:535`) and `>0.5` coverage (`:621`) — **these
decide which text is masked out of analysis**; `boundary_detection` HMM emission/transition matrices
fully hardcoded (`:152-163`); `compartments window=5, threshold=0.3` (`:42,65`); `rqa` threshold/window
(`:18-22`); `dialogue` per-pattern confidences `0.92/0.85/0.60/0.70` (`:11-16`); `entities`/`syntax`
fixed confidences `0.85`/`0.90`. The "fully transparent, user-controls-everything" similarity track
reports *none* of its masking/calibration constants — the highest-leverage P1/P5 violation.

### A4 — Unknown params silently ignored (S2, CONFIRMED)
Every track reads only keys it knows (`if "x" in params`); an unknown key is neither stored nor
rejected. FastAPI signature binding likewise drops unknown query params. A typo'd parameter runs the
default and says nothing.

### A5 — `set_params` int/float coercion raises a 500, not a 400 (S2, CONFIRMED)
`self_similarity.set_params` does `int(params["chunk_size"])` (`:900`) at `server.py:1016`, *outside*
the `validate_params` try/except (`:1024-1027`). A non-numeric value becomes an uncaught 500 instead
of the intended 400-with-reason.

---

## Part B — Transparency & error handling

### B1 — Validate/extract divergence breaks the "told before you run" guarantee (S2, CONFIRMED)
`validate_params()` is advertised as the synchronous pre-flight 400. But it does not execute chunking,
embedding, or span resolution, so these fail only async: smart-mode unit-span unavailability
(`self_similarity.py:1066`, `chunking.py:321` — `validate_params` builds the config but never checks
spans exist), embedding-service unreachability (`embedding.py:55,84`), empty-chunk input
(`embedding.py:84`), per-metric missing size (`self_similarity.py:1130`). "Validated" ≠ "will run".

### B2 — Error label is wrong 100% of the time, and the user never sees it (S1, CONFIRMED)
`server.py:1042-1047` labels **every** extract `ValueError` as `"Matrix too large: {exc}"`. There is
**no actual matrix-size error** anywhere (the only size logic is warn-only — B4), so the label is
always wrong. httpx errors (embedding down) aren't `ValueError` and fall through to the generic
handler (`:1060-1061`). Worse, the user sees neither: `/analysis/status` reports a *failed* job as
`"running"` (any present job is truthy → `status="running"`, `server.py:895`), then it silently
reverts to `"pending"` after the 30s cleanup; the frontend `TrackStatus` has no error field and the
`failed` branch renders only a Retry button (`AnalysisPanel.tsx:64-72,845-852`); `DotplotView`
discards `d.error` and shows a generic "matrix not available" (`DotplotView.tsx:312-313,830-838`).
**Ready template:** the cross-text alignment path already surfaces `status.error`
(`comparisonStore.ts:117`).

### B3 — R9's `alignment_refinement` honesty is written then discarded (S1, CONFIRMED)
The label is in the manifest (`self_similarity.py:1194`) but **not** on individual alignment records
(`_extend_alignment` returns no such field, `:510-525`). The frontend reads `metric_info` into a
dead slot — `const [, setMetricInfo] = useState(...)` (`DotplotView.tsx:247`); the value is never read
and the type doesn't include the field. Zero frontend references to `alignment_refinement`. A
slide/smart-mode dotplot shows approximate-boundary alignments identical to exact ones. The honesty
work exists only on disk, invisible.

### B4 — Matrix guard is warn-only; no pre-run cost shown (S2, CONFIRMED)
`WARN_MATRIX_DIM=16000` logs and proceeds (`self_similarity.py:1138-1143`); matrix builders allocate
`n×n` unconditionally. At N=16000 that's ~1 GB *per metric*. The param dialog
(`AnalysisPanel.tsx:224-424`) shows no chunk-count/matrix-dim/memory/time estimate before "Run". A
user can launch a multi-GB, multi-minute run with no forewarning and (per B2) no error if it OOMs.

### B5 — Silent fallbacks that change the method/result (S1–S2, CONFIRMED)
- `lithmm` swaps HMM→KMeans on import/fit failure, fabricating one-hot posteriors
  (`lithmm.py:197-211`); the UI still labels it "Hidden Markov Model" (`AnalysisPanel.tsx:130-133`).
  Disk *is* honest (`method: "KMeans-fallback"`, `lithmm.py:229`) — the gap is at the UI.
- `compartments` returns `np.zeros(n)` on `LinAlgError` (`compartments.py:36-37`) — a failed
  eigenvector becomes a silent all-zero signal.
- `topics` returns `[]` on vectorizer `ValueError` (`topics.py:84`) — degenerate corpus reads as
  "computed, 0 annotations."
- Assorted swallowed `catch`/`except` in status polling and matrix loading
  (`AnalysisPanel.tsx:516`, `DotplotView.tsx:283-293`).

---

## Part C — Storage, auditability, remap

### C1 — Stored artifact cannot reconstruct the run (S1, CONFIRMED)
`manifest()` is display-only for all tracks; the server writes only `manifests/{track}.manifest.json`
from it (`server.py:1054-1058`) and **never** writes a resolved-params file (`pipeline_run.json` is
CLI-only). So a UI-driven annotation-track run has **no param record on disk**. Where params *are*
embedded in a self-written signal manifest, two tracks record the wrong value: `topics` writes the
constant `N_TOPICS=10` and `source="sklearn-lda/10topics"` even when you ran `n_topics=25, method=nmf`
(`topics.py:135-158`) — **disk lies**; `lithmm` writes the *clamped* `n_states` with no note of the
clamp (`lithmm.py:224-233`); `sentiment` writes nothing about method/granularity (and `granularity`
is validated but never actually consumed — `sentiment.py:80` always uses sentence spans — an inert
knob). `self_similarity` is best-case but omits per-metric chunk sizes, smart-mode tuning, batch size,
and separator from its manifest.

### C2 — Embedding cache integrity (S2–S3)
- **Orphan growth (CONFIRMED, S3):** label = `sha256(provider+endpoint+model+chunk_texts)[:16]`
  (`self_similarity.py:806-811`); any content change → new label → new `cache/embeddings_{label}.db`;
  the old file is unlinked only on a *same-label count mismatch* (`:836`), so `cache/` grows unbounded
  across edits/re-runs. No cap, no LRU.
- **Model identity (CONFIRMED, S2):** provenance is the model *name*, no version/digest
  (`embedding.py:48-50`). Re-pulling the model under the same name silently reuses stale vectors.
- **batch_size excluded from the key (UNCERTAIN, S2):** the comment asserts batch-invariance
  (`:803`); the external MLX server is out-of-repo and the only in-repo guard checks vector *count*,
  not value stability under per-batch padding/normalization. If the server pads/normalizes per batch,
  two `batch_size` values collide on one cache entry with different vectors. Verify empirically or
  fold `batch_size` into the key.
- **Read-order fragility (UNCERTAIN, S2):** chunk vectors are stored with `chunk_index` but no
  `para_index`, so `get_all_vectors()` orders by an all-ties `para_index=-1` (`sqlite_vec.py:134`);
  correct order relies on SQLite tie-order coinciding with insertion order — not contractual. A wrong
  order silently corrupts the similarity matrix.

### C3 — Partial-failure leaves orphans; no transactionality (S1, CONFIRMED)
`self_similarity.extract()` writes per-metric `.bin` inside the metric loop (`:1165-1166`) but the
master manifest only at the end (`:1272`). A later-metric embedding failure leaves orphan `.bin` files
and a stale/absent manifest; filename-scanning readers (`_discover_chunk_sizes` `:82-93`, the
`chunk_sizes` endpoint `server.py:1087-1094`) surface them as valid. No temp-then-rename, no rollback.
All writes are non-atomic truncate-in-place (`:1165`, `serializer.py:37`, `signals.py:74`), so a crash
or a concurrent UI poll can read a torn file.

### C4 — Remap contract is implicit, unenforced, 3-shape (S1, CONFIRMED)
`_extract_masked` → `_remap_signal_dir` (`server.py:138-150`) handles only a top-level
`segment_offsets` dict key or a top-level list of `char_*_a/char_*_b` records
(`derive.py:243-255`); annotations remap only `TextPositionSelector` (`derive.py:205`). Any other
shape — offsets nested elsewhere, a different key name, a graph/edge-list, or a signal whose filename
omits the producer's name — passes through with **analyzable coordinates retained, mislabeled as
original**, with no error. Nothing asserts the remap happened. This is the primary P4 landmine.

### C5 — Stale siblings on re-run (S2, CONFIRMED)
A re-run with a different `chunk_size` writes a new `self_similarity_cs{N}/` dir and leaves the old;
the chunk-sizes endpoint then advertises sizes whose matrices no longer match the current manifest.
Masked-analysis signals are written into the live project dir (`project.py:321` shares `self.path`),
so pre-remap analyzable-coordinate artifacts sit beside remapped originals, indistinguishable on
failure.

---

## Part D — Remediation plan

Three layers, sequenced so the **structural guard-rails land before** the walk-through builds more
surface on the current patterns. Build the guard-rail, then migrate tracks onto it layer-by-layer
during the walk-through (the migration *is* the walk-through's hardening step).

### D1 — Guard-rails (structural; prevent recurrence) — do these FIRST

| G | Guard-rail | Kills findings | Sketch |
|---|---|---|---|
| **G1** | **Declarative `ParameterizedTrack` base** — params declared as data; base derives store-raw / reject-unknown / reject-range / `resolved_params()`. | A1, A3, A4, A5 | Add `PARAMS: list[Param]` to the protocol; one `resolved_params()` is the sole provenance source for HTTP + CLI + disk. Hand-rolled per-track validation deleted. |
| **G2** | **"Acceptable default" rule + `locked` params** — analytical knobs must be declared (locked or open); only structural params may default silently. | A3 | Encode `locked: bool` on `Param`; lint/test rejects an output-affecting module constant that isn't a declared `Param`. |
| **G3** | **Run-provenance write + atomic/transactional outputs** — the run handler persists `resolved_params()` atomically; multi-output runs stage-then-commit; writes use temp+`os.replace`. | C1, C3, C5 | One `write_run(outputs, provenance)` helper used by server and CLI. |
| **G4** | **Enforced remap contract** — outputs declare coordinate-bearing fields (or a `remap(omap)`); pipeline asserts every offset remapped; unknown shape is a hard error. | C4 | Replace the 3-shape `if/elif` with a registered output-schema + post-remap assertion. |
| **G5** | **Job-error propagation contract** — failures carry their real message end-to-end; `/analysis/status` reports `failed` + message; UI renders it (clone `comparisonStore.ts:117`). | B1, B2, B5 | Add `error`/`failed` to the status payload and `TrackStatus`; narrow/remove the "Matrix too large" relabel. |

### D2 — Refactors (fix existing violations)

Apply as each track is reached in the walk-through (G1–G5 make these mechanical):

1. **topics** (S1): migrate to G1; expose `random_state/max_iter/min_df/max_features` as
   `locked`-or-open params; stop writing constants to the signal manifest (record resolved values);
   replace the post-validation clamp with a validate-time feasibility check or recorded effective
   value; surface the `except ValueError → []` as an explicit "insufficient corpus" status.
2. **sentiment** (S1/S2): migrate to G1; either consume `granularity` (`sentiment.py:80`) or remove
   the inert knob; persist resolved method/granularity; fix `parameters()` constant.
3. **lithmm** (S2): expose HMM/KMeans `n_iter/random_state/n_init`; surface the HMM→KMeans fallback in
   the UI (the disk already records it); do not present fabricated one-hot posteriors as probabilities.
4. **self_similarity** (S1/S2): declare the masking/calibration constants (`:240,535,621` …) as
   `locked` params and record them in the manifest; add model digest to cache key + provenance
   (C2); decide batch-size cache treatment (C2); fix `set_params` coercion to 400 not 500 (A5);
   resolve the `get_all_vectors` ordering fragility (store/sort by chunk index).
5. **alignment_refinement consumption** (S1): render the exact/approximate distinction in
   `DotplotView`/`ComparativeDotplot` (read the dead `metricInfo` slot; tag alignment records).
6. **The 10 un-parameterized tracks** (S2): as each is walked, declare its constants as
   `locked` params via G1 so they are visible and reportable even before they're user-settable.
7. **Pre-run cost estimate** (S2/P2): the param dialog computes and shows chunk count + matrix dims +
   memory estimate before "Run"; warn (not block) past a threshold, per "user controls everything."

### D3 — Sequencing for the incremental walk-through

1. **Phase 0 (before walking any layer):** G1 + G2 (param base + default rule), G5 (error
   propagation), G3 (provenance write). These are cross-cutting; landing them first means every
   subsequent layer is *migrated onto* the guard-rail rather than re-deriving it. Milestone-review
   gate: a new sample track added in <30 min with zero hand-written validation.
2. **Phase 1 (walk each track):** for each layer in `WALKTHROUGH.md` order, run the §7 checklist from
   the design doc; apply the relevant D2 refactor; migrate its constants onto G1. G4 (remap) is
   exercised the first time a layer emits a non-standard shape.
3. **Phase 2 (storage/cache hardening):** C2 (model digest, cache retention, batch-size decision,
   ordering) and C5 (stale-sibling cleanup) once provenance (G3) is the source of truth.

### D4 — Quick wins (low-risk, high-clarity; can land immediately)

- Narrow `except ValueError → "Matrix too large"` to the real condition (or include the exception
  type) — stops the 100%-wrong label (B2).
- Add `error` to `/analysis/status` and `TrackStatus`; render it — makes failures visible (B2).
- Move `self_similarity.set_params` numeric coercion inside the validated path → 400 not 500 (A5).
- Read the `metricInfo` slot and show approximate/exact in the dotplot legend (B3).

---

## Appendix — Investigation provenance

Findings hardened by three parallel read-only code investigations (param-contract, transparency/errors,
storage/auditability) on 2026-06-23, then the highest-impact claims (B2 status endpoint, B3 dead
`setMetricInfo` slot, C1 topics-constants-on-disk, A2 post-validation clamp, B5 lithmm swap) were
re-verified directly against source. UNCERTAIN items (C2 batch-size vector dependence, C2 read-order)
depend on the out-of-repo MLX embedding server and SQLite tie-ordering respectively and need an
empirical check, not a code read.
