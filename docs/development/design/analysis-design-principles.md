# Palimpsest Analysis Design Principles

**Status:** Active design contract · **Created:** 2026-06-23 · **Owner:** core/analysis
**Companion:** [`../audits/analysis-paradigm-audit-2026-06.md`](../audits/analysis-paradigm-audit-2026-06.md) — current-state evidence and remediation plan.

> This document defines the **durable contract** every analysis track, tool, and pipeline stage in
> Palimpsest must satisfy. It exists because a 2026-06 audit found the project's analysis principles
> were being honored *instance-by-instance* (on the handful of tracks someone happened to harden)
> rather than enforced as *invariants*. The next development phase walks each analysis layer
> incrementally; this document is the checklist each layer is held to.

---

## 1. The Five Principles

These are the user's stated design goals for analysis, restated as **testable** contracts. "Testable"
means: for each principle there is a mechanical check that can pass or fail, not a vibe.

| # | Principle | Testable form |
|---|-----------|---------------|
| **P1** | **Full transparency of mechanics** | Every parameter and algorithm choice that affects output is *named, reported, and visible at the point of consumption* (UI + on-disk), not just in source. |
| **P2** | **Transparency + guards for data shape / preprocessing** | Before a run, the user is shown what the input will be reshaped into (chunk count, matrix size, cost) and is rejected-or-warned on shapes that cannot work — no silent reshape, no silent skip. |
| **P3** | **Reporting + storage for visualization & auditability** | From the stored artifact **alone**, you can reconstruct *exactly* what parameters produced it. Disk never lies and never omits. |
| **P4** | **Flexibility for novel/varying approaches** | A new analysis of a *similar conceptual type* (a new similarity metric, a new clustering method, a new chunker, **a new operand topology such as cross-text or corpus comparison**) can be added by satisfying a declared interface — without re-deriving the parameter/validation/persistence/remap machinery. |
| **P5** | **The user controls everything and sees everything** | No output-affecting value is fixed where the user cannot set it; no failure or fallback is invisible. Control and visibility are the same requirement applied to inputs and outputs respectively. |

### The unifying rule

> **No hidden defaults. Validate-and-reject. Fail loud. Echo back — to disk, not just the wire.**

The audit's central lesson: this rule was applied to the *parameters a human noticed* (chunk size,
`n_topics`, embedding config) and not to the layer beneath (random seeds, iteration caps, calibration
thresholds, masking cutoffs). **A principle that depends on remembering is not enforced.** The
contracts below replace memory with structure.

---

## 2. The Parameter Contract

Every analysis unit (track or pipeline stage) that has *any* tunable behavior MUST implement a single
declarative parameter contract. The current codebase has four tracks each hand-rolling
`set_params`/`validate_params`/`parameters()` with per-track ranges and **two divergent reporting
paths** (HTTP echoes live values; CLI echoes module constants — see audit §A). That is exactly the
structure that lets the next track silently reintroduce the bugs the remediation just fixed.

### 2.1 Declared, not coded

A track declares its parameters as data:

```python
PARAMS = [
    Param("n_topics", type=int, required=True, range=(2, 50)),
    Param("method",   type=str, required=True, choices=("lda", "nmf")),
    Param("random_state", type=int, required=False, default=42, locked=False),  # see §6
    Param("max_iter",     type=int, required=False, default=20,  locked=False),
    Param("min_df",       type=int, required=False, default=2,   locked=False),
]
```

The base class derives `set_params`, `validate_params`, and `resolved_params()` from this declaration.
Hand-written per-track validation is removed. Benefits, mapped to principles:

- **P5/P1:** *every* output-affecting value appears in the declaration — including the seeds and
  caps currently buried as module constants (`RANDOM_STATE`, `MAX_ITER`, `MIN_DF`, KMeans `n_init`,
  the LASTZ calibration cutoffs, the boundary-detection HMM matrices). If it changes output, it is a
  declared `Param`. A value may be `locked=True` (not user-settable yet) but it is still *declared
  and reported* — locked ≠ hidden.
- **P4:** a new method adds a `Param` row; it cannot forget store-raw / reject-unknown / reject-range
  / echo, because the base class owns all four.
- **Unknown-key rejection** becomes automatic: a param not in the declaration is a 400, not a silent
  drop (today every track silently ignores unknown keys).

### 2.2 One resolved-params source of truth

`resolved_params()` returns the **live, post-resolution** values and is the *only* provenance source.
`validate_params()` returns it; the HTTP echo returns it; the CLI provenance file writes it; the
on-disk manifest stores it. There is exactly one function, so the HTTP and CLI paths **cannot
disagree** (today `topics.parameters()` returns `n_topics=10` constant while `validate_params()`
returns the live value — audit §A2).

### 2.3 No post-validation clamps

Validation is the *only* place a value is accepted or rejected. A track MUST NOT silently shrink a
validated value at compute time (today `topics.py:74` does `n_topics = min(self._n_topics, len(paras))`
*after* the echo already promised the larger number — audit §A6). If a value is infeasible for the
actual input, **reject at validate time** (the input size is known) or **record the effective value
in the stored provenance** so the echo and the artifact agree. Never both promise X and run Y silently.

---

## 3. The Provenance / Storage Contract (P3)

**Invariant:** *from the stored artifact alone, reconstruct the run.*

1. **Every run writes resolved params to disk**, on both the HTTP and CLI paths. Today the server
   never writes a provenance file for annotation tracks at all (only the CLI writes
   `pipeline_run.json`), and `manifest()` is display-only — so a UI-driven run leaves **no** param
   record (audit §C1). Fix: the run handler persists `resolved_params()` next to the output.
2. **Stored provenance records the *effective* value, never a constant.** `topics` writes
   `n_topics=10` (the module constant) to its signal manifest even when you ran 25 (audit §C1b);
   `lithmm` writes the clamped value with no note that a clamp occurred (§C1d). Both violate "disk
   never lies."
3. **Provenance identifies the *content* of external dependencies, not just their name.** The
   embedding cache and manifest record the model *name* (`qwen3-embedding:4b`) but no version/digest
   (§C2d). If the served model is re-pulled under the same name, cached vectors silently mismatch the
   live model and nothing detects it. Record a model digest (or an explicit "model identity" the
   server returns) in provenance and in the cache key.
4. **Writes are atomic and runs are transactional.** All signal/track/manifest/`.bin` writes today
   truncate-in-place (§C5a) and multi-output `extract()` writes per-metric files *before* the manifest
   (§C3) — a mid-run failure leaves orphan `.bin` files that filename-scanning readers surface as
   valid results. Contract: write to a temp path and `os.replace`; stage a run's outputs and commit
   them together (or clean up on failure). A half-written run must be invisible to readers.
5. **Re-running with different params does not leave stale siblings.** Today a new `chunk_size`
   writes a new `self_similarity_cs{N}/` dir and the old one survives, so the UI advertises chunk
   sizes whose matrices no longer match the current manifest (§C5c). A run either supersedes prior
   outputs or namespaces them under a provenance id that the reader filters by.

---

## 4. The Coordinate-Remap Contract (P4)

Text-deriving analyses run on the **analyzable stream** (masked spans and verse-number tokens excised)
and their outputs are remapped back to original document coordinates. Today this remap handles exactly
**three shapes** — `TextPositionSelector` annotations, a top-level `segment_offsets` list, and a
top-level array of `char_*_a/char_*_b` records — and the contract is **implicit and unenforced**
(audit §C4). A novel output (a graph, an edge-list, offsets nested under `metadata.spans`, or a
different key name) passes through with **analyzable coordinates silently retained, mislabeled as
original**. This is the single biggest landmine for P4: the moment a new analysis type emits a new
shape, its results are silently wrong with no error.

**Contract:** an analysis declares the coordinate-bearing fields of its output (or implements a
`remap(omap)` method). The pipeline **asserts** every emitted offset has been remapped — an
unrecognized shape is a hard error at write time, not a silent passthrough. "I added a new output
shape and forgot to remap it" must fail loudly, like every other principle here.

### 4.1 Coordinate frames are explicit (the cross-text generalization)

Today every coordinate-bearing field means one thing implicitly: *a span in this project's original
`reference.txt`*. That implicit single frame is the last assumption standing between the current
analyses and **cross-text** comparison, where a result's two axes live in **two different documents'**
coordinate systems. The remap contract generalizes by making the frame *explicit* rather than assumed:

- An analysis declares, per coordinate-bearing field, **which coordinate frame** it is expressed in —
  today always the operand's own original coordinates; for a cross-text result, the *row* axis and the
  *column* axis name different operands.
- A comparison of two texts may designate one as the **root** (the coordinate backbone) and express the
  other's contributions in the root's frame. **The alignment that maps comparison text B into root text
  A's frame is itself an `OffsetMap`** — the exact machinery §4 already governs — so a cross-text
  layer's offsets are remapped *operand→root* by the same assert-or-fail discipline that remaps
  *analyzable→original* today. No new coordinate math; one additional remap target.
- **Self-similarity is the degenerate single-frame case** (`A = B`: row and column are the same
  operand; the root is the text itself). Designing the two-frame contract and treating self as its
  one-frame instance is what keeps the genome-browser–style multi-text view — a root backbone with
  other texts' similarity layers drawn as tracks against it — a *configuration*, not a separate
  subsystem. This is the P4 flexibility requirement applied to **operands**: a resemblance operator
  `R(A, B)` whose modes (auto `A=A`, cross `A×B`, probe `q×corpus`, corpus N-way) are chosen, not
  rebuilt.

---

## 5. The Transparency-of-Consumption Contract (P1/P5)

Transparency metadata is worthless if it stops at the manifest. Two concrete current failures define
the contract:

1. **Honesty must reach the visualization.** The `alignment_refinement: "approximate"|"exact"` label
   (added to warn that slide/smart-mode alignment boundaries are approximate) is written to the
   manifest, read into the frontend, and **discarded** — `const [, setMetricInfo] = useState(...)`
   reads into an empty slot (audit §B3, `DotplotView.tsx:247`), and the individual alignment records
   never carry the flag at all. A user sees approximate alignments rendered identically to exact ones.
   Contract: a caveat that affects interpretation travels **with the data to the point it is
   displayed**, and the consuming component renders it.

2. **Failures and fallbacks are visible.** Three current violations:
   - The async job handler labels **every** extraction `ValueError` as `"Matrix too large"` — and
     there is no actual matrix-size error in the code, so the label is wrong 100% of the time (§B2).
   - The `/analysis/status` endpoint reports a *failed* job as `"running"` (any present job is truthy →
     `"running"`), then silently reverts to `"pending"` after cleanup — the error string is never
     surfaced and the UI has no error field (§B2).
   - `lithmm` silently swaps a Gaussian HMM for KMeans with fabricated one-hot posteriors while the UI
     label still says "Hidden Markov Model" (§B5a). (The *disk* honestly records `KMeans-fallback`;
     the *UI* does not — so this is a consumption-layer failure, not a storage one.)

   Contract: every failure surfaces its real message to the user; every algorithmic fallback that
   changes the method or degrades the result is reported at the point of consumption, not only in a
   log line the user never reads.

---

## 6. The "Acceptable Default" Rule

The audit found a genuine paradigm tension: the remediation made chunking params *required* (no
default) but also, in the same breath, added `mask_verse_numbers=True` as a *default*. Without a rule,
the next author rationalizes `random_state=42` the same way. The rule:

> **A default is acceptable only for a parameter that is structural/coordinate-level — one with a
> single correct value for a given document, independent of the analytical question being asked
> (masking layers, the analyzable separator, coordinate handling). A default is BANNED for any
> analytical knob whose value changes the result for a fixed input (seeds, iteration counts,
> df/feature thresholds, cluster/topic/state counts, similarity cutoffs, window sizes).**

Corollaries:
- An analytical knob may be `locked` to a fixed value during early development, but it must be
  **declared and reported** (§2.1). Locked ≠ hidden. A user can *see* `random_state=42` and a future
  release can *unlock* it without changing the contract.
- `mask_verse_numbers` passes the rule (structural: verse-number markers are document structure, not
  an analytical choice). `random_state`, `max_iter`, `min_df`, the LASTZ calibration cutoffs, and the
  boundary-detection HMM matrices fail it — they must be declared params, not module constants.

---

## 7. What "done" looks like for a layer in the walk-through

When the next phase reaches an analysis layer, it satisfies this checklist before moving on:

- [ ] **P1/P5** every output-affecting value is a declared `Param` (locked or open), reported live in `resolved_params()`, and visible in the UI.
- [ ] **P2** the UI shows a pre-run shape/cost estimate (chunk count, matrix dims, memory) and rejects/​warns on infeasible shapes; no silent skip or clamp.
- [ ] **P3** the run writes resolved params to disk atomically; the stored artifact alone reconstructs the run; external-dependency identity is captured by digest.
- [ ] **P4** the output's coordinate-bearing fields are declared/remapped and the pipeline asserts the remap; adding the layer required no copy-pasted param/validation/persistence machinery.
- [ ] **P5** every failure and every algorithmic fallback is surfaced to the user with its real message.

---

## Appendix A — Track contract status (2026-06-23 snapshot)

> **Superseded by Wave-0 (2026-06).** This snapshot predates the layer-track work: `chunking`,
> `embedding`, `repeats`, `repeat_mask`, and `profile` now ship as parameterized layer-tracks
> (`ParameterizedTrack`, with `set_params`/`validate_params`). Treat the counts below as historical.

14 registered tracks; **only 4** (`topics`, `sentiment`, `lithmm`, `self_similarity`) implement
`set_params`/`validate_params`. The other 10 (`lexical`, `dialogue`, `entities`, `syntax`,
`coreference`, `alphabet`, `narrative_arc`, `compartments`, `rqa`, `boundary_detection`) are
**un-parameterizable** — they run on fixed constants with no knob to set or reject. The
`TrackExtractor` protocol (`tracks/base.py:19-63`) does not even include the param methods; they are
bolted on. Full table and the hidden-constant inventory live in the companion audit, §A.

## Appendix B — Relationship to existing docs

- `palimpsest_system_design.md` (this dir) is the current system-architecture reference (filesystem
  projects + sqlite-vec, FastAPI server, React/zustand browser, the layer-track producer/consumer
  model). It defers to *this* document for the analysis paradigm and the coordinate-frame contract.
- `../WALKTHROUGH.md` is the user-facing feature walkthrough the next phase exercises layer-by-layer.
- `../audits/analysis-paradigm-audit-2026-06.md` holds the evidence and the sequenced remediation.
