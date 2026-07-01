# Collections Tier — Vision & Requirements (the cross-text analytical tier)

**Status:** As-built — Collections tier C1–C7 shipped (see the [build journal](../collections-tier-build-journal.md))
**Date:** 2026-06-30
**Companion (engine pre-stage):** [wave0-analysis-suite-vision.md §10](./wave0-analysis-suite-vision.md) (the resemblance operator `R(A,B)`, FR-18…22) and [wave0-analysis-suite-plan.md](./wave0-analysis-suite-plan.md) (P9 seam-lift landed; P10/P11 cross-text build).
**Builds on:** [analysis-design-principles.md §4.1](./analysis-design-principles.md) (coordinate frames are explicit; alignment = `OffsetMap`), [ADR-005-jbrowse2-patterns.md](../architecture/ADR-005-jbrowse2-patterns.md) (cross-text = `LinearSyntenyView`), and `core/palimpsest/collections.py` (the current CRUD stub this tier grows from).
**Reference imagery:** `../research/UI/screenshots/` — UCSC Genome Browser (single-genome tracks), JAX Synteny Browser (block-view + dotplot + ribbons + Circos), the comparative-genomics idiom this tier is modeled on.

---

## 1. Purpose & scope

Wave 0 made a **single text's** pre-analysis substrate first-class: chunking, embedding, repeats, profile, and integrity became named, reusable, provenance-stamped layers over one analyzable stream. The Collections tier is the **multi-text** layer above it. It answers a question Wave 0 deliberately deferred (§8): *what does it mean to group texts and analyze them as a corpus, not one at a time?*

This is the home the deferred cross-text engine (`R(A,B)`, FR-21/22) and the synteny UI plug into. But it is **more than** the engine: the engine compares two operands; the *tier* defines what a Collection is, how texts enter and leave it, what corpus-level analyses run *over* the whole set, how masking and tracks generalize across members, and the workbench that drives all of it.

### 1.1 The organizing analogy: a Collection is a comparative-genomics workspace

The project's existing framing (ADR-005, vision §10.3) already borrows the genome browser. The Collections tier completes the analogy, and it is load-bearing, not decorative — each genomics layer has a precise text counterpart and a proven visualization:

| Genomics | Palimpsest | Established viewer |
|---|---|---|
| Annotate one assembly (tracks over one reference) | A **Project**: tracks/masks over one analyzable text | UCSC Genome Browser (Wave-0 track browser — *exists*) |
| Whole-genome alignment of two assemblies (dotplot, synteny blocks, rearrangements) | **Pairwise cross-text** `R(A,B)`: alignment, quotation, translation, structural borrowing | JAX Synteny Browser block-view + dotplot; ACT ribbons |
| Comparative / pangenome analysis across many genomes (conserved elements, core/accessory, synteny network) | **Corpus** `{R(Ai,Aj)}`: formula diffusion, stemma, influence graph, shared-vs-unique passages | Circos chord plot; Mauve LCB block-map |

A Collection *is* the alignment-set: the genomes you chose to compare, the alignment between them, and the comparative results that fall out.

### 1.2 In scope

The object model (Text / Imported Text / Project / Collection and their membership lattice, including subtext-extraction); membership lifecycle (import / re-import / re-run) and non-destructive versioning that keep cross-text results honest; the cross-text & corpus analytics catalog; cross-text masking, cross-text tracks, and annotation/mask **liftover**; the multi-text visualization suite (collection overview + phyletic tree → pairwise heatmap + local-alignment dotplot + ribbon → single text); the Collection workbench UI; and the **operational tooling** to *prep for and perform* these analyses (metric-congruence reconciliation, operand binding, alignment prep, candidate-generation recall dial, cost estimation, export).

### 1.3 Out of scope (this doc)

The literary interpretation itself; re-deriving any Wave-0 machinery; the specific NLP of each cross-text metric beyond the operand/alignment contract the engine needs; general document-asset management (this is not a citation manager or a DAM); and automatic *discovery* that two files are "the same Work" (Work identity is user-asserted first — §2, OQ-2).

---

## 2. The object model

The gap analysis found this is the deepest hole: the codebase has a `Project` and a thin `Collection`, but no vocabulary that separates *the work*, *the edition*, *the analytical view*, and *the comparison set*. Cross-text analysis is impossible to reason about safely without it — translation alignment is precisely the act of comparing two *editions of the same work* under *different masking*, and the system must be able to say so without conflating them.

### 2.1 Four distinct objects

| Object | What it is | Filesystem reality | Genomics analogue |
|---|---|---|---|
| **Work** | The abstract intellectual work a human *means* ("the Gospel of Matthew", "Paradise Lost"). Identity only — not an analyzable thing. | A user-asserted `work_id` tag (no heavy entity; see OQ-2) | A **taxon** ("mouse") |
| **Imported Text** (Source / Edition) | A concrete ingested artifact: one file (PDF/EPUB/HTML/TXT), one edition/translation, content-hashed. | The normalized `reference.txt` + content digest | A specific **assembly/sequence** (GRCh38 vs hg19) |
| **Project** | A Palimpsest workspace over one Imported Text under one *analytical configuration* — masking policy, structural detection, the analyzable frame and its `OffsetMap`. **This is the operand of analysis.** | The project directory: `reference.txt`, `layout_sections.json`, `tracks/`, `signals/`, `cache/`, provenance | An **annotated assembly under a specific track/masking hub** |
| **Collection** | A named, persisted grouping of Projects assembled for co-analysis, *plus* the collection-level policy and artifacts: shared embedding-space contract, the alignment graph, cross-text/corpus results, collection masking. | `collections.json` (membership, today) + `collections/{id}/` (artifacts, new — §6 FR-32) | The **comparative-genomics workspace / alignment set** |

**Why four and not three.** The `Work → Imported Text → Project` chain is what lets a user hold "the same text, a different edition, a different masking" in mind without the system silently equating them. A Douay-Rheims/KJV translation alignment is two *Imported Texts* of (arguably) one *Work*, each its own *Project* with its own masking — and the comparison is meaningful *because* they are distinguished. Collapsing the chain (today's implicit "a Project is a text") makes the most important cross-text workflow unrepresentable.

### 2.2 The membership lattice (many-to-many at every level)

This is a DAG, not a tree:

- a **Work** has many **Imported Texts** (editions, translations, recensions);
- an **Imported Text** backs many **Projects** (different masking / sectioning → different analyzable views);
- a **Project** belongs to many **Collections** (already true: `collections_for_project()`, `collections.py:135`);
- a **Project** may **derive from a parent Project** by subtext extraction (a saved mask/filter), parent + children auto-forming a derived Collection (FR-43).

Every edge is navigable in both directions, and the inverse navigations are first-class UI affordances (§5): *which collections is this Project in? which Projects share this Work? which editions of this Work exist? which Projects in this Collection derive from the same Imported Text?* A Project is referenced from a Collection by **stable `project_id`** (never embedded), so one Project participates in many comparisons without duplication — the genomics "one assembly, many alignment sets" pattern.

**Collection-local role.** A Collection annotates each member with a **role**. Per the **OQ-1 decision (reference-free default, §9)**, members are **co-equal by default** — the corpus is an alignment graph with no privileged axis (§3.2). Roles:
- **member** (default) — participates co-equally in the alignment graph and all corpus-level (N-way) analyses; no privileged axis.
- **root** (optional, a *per-view lens*) — a member temporarily designated the coordinate backbone for a synteny / pairwise / translation view. Cross-text layers project *operand→root* into its frame (principles §4.1) **for that view only**. The root is not the corpus's ground truth; it is a projection computed from the graph on demand (§4.2).

Role is collection-local metadata, not a property of the Project — the same Project is a co-equal member here and a chosen root lens there.

### 2.3 Membership lifecycle: import, re-import, re-run & the staleness contract

Three operations conflated in an earlier draft are now distinct (2026-06-30 review):

- **Import** creates a Project from a source. **Re-import** creates a *second, independent* Project instance of the same source — it **never replaces** the first. Its purposes: holding two Projects of one text under *different ground-truth masking schemas*, or keeping a clean backup if a Project's space gets corrupted. Re-import invalidates nothing.
- **Re-run** changes masking / chunking / repeats / any analysis *within* an existing Project and recomputes. This — not re-import — is the normal edit loop.

Result validity follows the **"disk never lies"** posture (principles §3), generalized to corpora:

- **Results are content-addressed by operand identity** — `(project_id, analyzable_digest, layer_label, method_params)` — the Wave-0 content-addressing extended across projects.
- **Non-destructive re-analysis (the default).** Re-running an analysis *keeps* prior results alongside the new one; each version carries run-metadata (params, timestamp, provenance id) surfaced in the UI, and the user deletes versions manually (§5, FR-41). Nothing is silently destroyed.
- **Ground-truth masks are the one exception (singleton-supersede).** Structural and Content mask annotations are *ground truth*; a new structural/content mask **replaces** the prior one (no accumulation of "chapter" mask variants). All *other* analyses (repeats, sentiment, topic, embeddings, chunkings, …) accumulate versions.
- **The staleness trigger is a ground-truth-masking re-run, not a re-import.** Changing a Project's structural/content masking changes its analyzable frame, so cross-text/corpus results computed against the *old* frame are **stale-flagged** (surfaced, recomputable), never silently rendered against moved coordinates. (This is *why* two different ground-truth maskings require two Projects — i.e. a re-import.)
- **Removal orphans, it does not delete.** Removing a Project from a Collection leaves referencing results **tombstoned** ("references a member no longer in this collection"), recomputable or archivable.

---

## 3. What a Collection unlocks — the cross-text & corpus analytics catalog

Organized by operand topology (vision §10.1's four modes), each item paired with its genomics analogue and the structural signal it reveals.

### 3.1 Pairwise cross-text — `R(A, B)` (the whole-genome-alignment analogue)

Pairwise comparison produces **two distinct, inter-mappable products** (2026-06-30 review):

1. **The chunk-distance heatmap** — the M×N matrix whose cell *(i, j)* is a (Mi − Nj)-family score over a *congruent* per-chunk metric (§3.5), or a direct pairwise score (edit distance, vector cosine). It shows *every* chunk-pair relationship, weak ones included; it is dense, cheap for broadcast metrics, and rendered as a heatmap.
2. **The local-alignment dotplot** — only the *high-scoring local alignments* discovered by an **end-to-end find-and-extend pass** (the LASTZ seed-extend / Smith-Waterman engine, the cross generalization of the self kernel with the `_is_self` diagonal guard dropped; FR-21/FR-40). Each alignment is scored *score = f(length × [matchiness − gappiness])*; an empirically-chosen cutoff on the **score distribution** decides which render. It shows structure, not noise.

**They map to each other through character coordinates** — a chunk spans character positions, and a local alignment carries character coordinates — so alignment streaks overlay onto the heatmap *and* chunk-distance scores paint onto the dotplot, bidirectionally. As chunk character-length shrinks, the heatmap's granularity rises until it converges on the dotplot. **Both products, and the overlay, are wanted.**

The analyses this unlocks, and how to read the dotplot's geometry:

- **Translation / recension alignment** (verse-to-verse, edition-to-edition) ≈ *orthologous region mapping*; the alignment blocks are **synteny blocks**.
- **Quotation / allusion detection** (directional: who borrowed from whom) ≈ *horizontal transfer of a segment*.
- **Paraphrase vs. verbatim** — the **metric-gap signal** (vision §10.1): embedding-high ∧ lexical-low ⇒ paraphrase/translation; both-high ⇒ verbatim quotation ≈ *synonymous vs. identical substitution*.
- **Structural rearrangement**, read off the dotplot as in WGA: main-diagonal streaks = collinear correspondence; anti-diagonals = **inversions** (chiasmus across texts); off-diagonal blocks = **transpositions**; parallel offset diagonals = **duplications**; breaks/gaps = **insertions/deletions**.

Self-comparison `R(A, A)` produces the same two products for one text and lives in that **Project's TextHiC tab** (not the Collection) — the Collection is for `R(A, B)` with distinct operands.

### 3.2 Corpus / N-way — `{R(Ai, Aj)}` (the comparative / pangenome analogue)

**The default corpus model is reference-free (OQ-1, decided 2026-06-30).** No member is a privileged backbone: the corpus is a **co-equal alignment graph** (the pangenome idiom) whose edges are the pairwise alignments of §3.1 and whose nodes are passage spans. A single-text "root" view is a *projection* of this graph (§4.2), never its ground truth. The N-way analyses run over that graph:

- **Formula / topos diffusion** across the corpus ≈ *conserved elements across genomes* (an epithet or legal formula tracked through every member).
- **Near-duplicate detection & stemma reconstruction** ≈ *phylogeny from shared derived characters* (which recension descends from which).
- **Influence / text-graph** ≈ *synteny network / ortholog graph* (nodes = texts or passages, edges = resemblance).
- **Corpus-level repeats** — a phrase recurring *across* members, not merely within one — ≈ *multi-genome conserved motifs*. This is the cross-text generalization of Wave-0's text-level `repeats` track (gap item 4), and it feeds collection masking (§3.4).
- **Pangenome passage classification**: every passage tagged **core** (present in all members) / **shell** (some) / **cloud/singleton** (one) ≈ *core/accessory/cloud genome*. A compact, powerful corpus summary.
- **Corpus weighting** (FR-22): IDF/BM25 over the collection down-weights ubiquitous passages so genuinely distinctive resemblances surface ≈ *masking ubiquitous repeats before calling synteny*.

### 3.3 Probe — `R(q, Corpus)` (retrieval)

"Find passages like this one" across the collection's shared embedding space — ANN over `SqliteVecStore.search`, the two-stage candidate→exact strategy of FR-22. The collection is the natural retrieval scope.

### 3.4 Cross-text masking & cross-text tracks (gap items 4 & 5)

Two ideas Wave-0 had only in single-text form now generalize:

- **Cross-text masking.** Mask corpus-level repeats (a shared liturgical refrain present in both A and B) *before* cross-text similarity, so boilerplate does not dominate the alignment — the multi-text twin of Wave-0 repeat masking, riding the same excise/remap path (`OffsetMap`), now driven by a *corpus*-repeat layer (§3.2). A second mode: **low-correspondence masking** (hide regions of B with no match in A) to focus a dense dotplot.
- **Cross-text tracks.** A cross-text similarity layer, once remapped *operand→root*, **is an ordinary root-frame track** (vision §10.3) — so the existing `OverviewBar` lane machinery draws it with no new renderer. The Collection therefore introduces a new *class* of track: one **defined by a comparison** but **rendered against one root axis**. Plus **collection-level annotation tracks**: a mask or feature defined once and applied to every member (e.g., "mask verse numbers in all members," "highlight every member's direct-discourse spans") — a single declaration, N applications, each remapped into its own member's frame.

### 3.5 Metric congruence — when two chunk-sets are comparable

A (Mi − Nj) cell is meaningful only when Mi and Nj are the *same kind of metric*: both sentiment scores from the same analysis, both vectors from the same embedding model + parameters, both topic loadings from the same model — or the cell is a direct pairwise function (edit distance) needing no per-chunk value. Palimpsest therefore tags every per-chunk metric with a **congruence key** (analysis-type + model/params + dimensionality + the analyzable digest it was computed against). Two member chunk-sets are *comparable on metric X* iff their X-keys match. Embedding-model identity is one field of that key, not the whole of it — congruence is required for **every** post-chunking metric (sentiment, topic, syntax, …), not only embeddings. The Collection surfaces, per metric, which member pairs are congruent and therefore available for cross-text comparison (FR-39); incongruent pairs get an explicit reconcile action (re-embed / re-run the metric to a common key), never a silent comparison (FR-27).

---

## 4. The visualization suite — three zoom tiers

The three reference screenshots are not three options; they are three **zoom levels** of one workspace. The Collection viewer is a coordinated zoom from corpus → pair → single text.

### 4.1 Collection overview (the Circos / block-map tier) — entry point

Every member is an **arc** (Circos) or a horizontal **lane** (Mauve block-map); the strongest cross-text correspondences are drawn as **chords/ribbons** between them; passages are **painted by pangenome class** (core/shell/singleton, §3.2) or by which root section they map to (the JAX "mosaic" paint). This is the bird's-eye "how does this corpus relate?" view and the launch pad into pairs. Crossing ribbons immediately signal rearrangement; a color-key sidebar maps the palette to members or root sections (the JAX Rat-Genome-Key idiom).

### 4.2 Pairwise deep-dive (heatmap + dotplot + ribbon tier)

The workhorse, and the smallest reach from existing code. The two §3.1 products render on the same character-coordinate plane and overlay:

- **Chunk-distance heatmap** — the dense M×N matrix (§3.1 product 1), row/col = the two operands' chunks, cell = the congruent-metric distance. The existing `DotplotView` is in fact a *heatmap* renderer (despite its name) and generalizes from square `R(A,A)` to rectangular `R(A,B)`.
- **Local-alignment dotplot** — the thresholded high-scoring local alignments (§3.1 product 2) drawn as streaks. **Overlay toggle:** alignment streaks over the heatmap, or chunk-distance shading under the dotplot (the two are inter-mappable via character coordinates). Brushable: drag over a streak to open the two passages side by side; a **direction toggle** distinguishes inversions (anti-diagonals) from collinear matches.
- **Ribbon comparison panel** (ACT idiom) — the two texts as bars with filled ribbons connecting aligned spans, color-coded by match type; crossed ribbons = reordering.
- **Mosaic / painted bar** (JAX block-view) — each compared text painted segment-by-segment by which section of the chosen root lens it aligns to; a segment painted three colors is a composite/centonized passage.

### 4.3 Single-text (the existing Wave-0 track browser) — the floor

Unchanged: the UCSC-style multi-track view over one Project. Cross-text tracks (§3.4) stack here against the root, alongside the member's own Wave-0 layers.

### 4.4 Cross-cutting views

- **Phyletic / stemma tree** — a cladogram of the collection's texts for root selection and corpus structure (FR-38). *Manual-first*: the user assigns the root taxon and groups text-taxa into clades as a working hypothesis (classical stemmatics). *Distance-driven later*: once inter-text distances exist, the tree is recomputed (neighbor-joining / nearest-neighbor), the optimal root auto-suggested, and the user overrides only then. It is a reading of the reference-free graph's distance structure and lives in the Overview tab beside the Circos/graph view.
- **Stacked linear comparative view** (JBrowse 2 `LinearSyntenyView`, ADR-005): 2–6 member panels stacked, trapezoid connectors between matched spans, synchronized or independent scroll.
- **Graph / bubble view** (a *primary* corpus surface under the reference-free default, OQ-1): the co-equal alignment graph drawn as a DAG — a shared backbone with text-specific material as bubbles, no privileged axis. With the Circos overview (§4.1) this is the default entry to a corpus; the root-projected synteny browser (§4.2) is the per-view lens, not the other way round.

(Self-comparison `R(A, A)` is a single-text feature and lives in the Project's TextHiC tab, §3.1 — not a Collection view.)

---

## 5. The Collection workbench (UX vision)

Parallel to the Wave-0 Stage-1 suite (vision §5), organized around **members and comparisons as the currency of work**.

- **Header:** collection identity + member count + a **metric-congruence compatibility badge** (FR-39) — the cross-text precondition made legible, *per metric*: *do the members share a congruence key (same model/params/dim) for the metric being compared?* Embedding-space agreement is the common case; the badge generalizes to every metric (§3.5). One click explains any mismatch. (The multi-text analogue of Wave-0's substrate-integrity badge.)
- **Members tab:** manage the membership lattice (§2.2). Add/remove Projects; assign **role** (root / compared / member); see each member's Work → Edition → masking provenance; the many-to-many indicator ("also in collections X, Y"); re-import/staleness flags (§2.3); the inverse navigations (sibling editions, shared Work).
- **Overview tab:** the Circos / block-map collection overview (§4.1).
- **Compare tab (pairwise):** pick root + compared (or any two), pick methods, run, see dotplot + ribbon + mosaic (§4.2).
- **Corpus tab (N-way):** influence graph, pangenome core/shell/singleton, formula diffusion, stemma (§3.2).
- **Masking & Tracks tab:** collection-level masks and shared tracks; corpus-repeat detection; cross-text masking policy (§3.4).
- **Composition affordances** threaded throughout: "promote this alignment to a root-frame track," "export alignment (PAF)," "use this collection's embedding space," "open this pair in the dotplot."

### 5.1 Operational tooling — *prep for and perform the complex operations*

Cross-text analysis has real prerequisites; the workbench makes each an explicit, costed, fail-loud operation rather than a hidden precondition:

- **Metric-congruence reconciliation.** A cross-text matrix on metric X requires both members to carry metric X under the *same congruence key* (§3.5): same embedding model+params, same sentiment/topic model, etc. The workbench detects per-metric mismatch (the compatibility badge, FR-39) and offers an **explicit, costed** reconcile (re-embed / re-run the metric to a common key, NFR-C4), never an auto-run. (Embedding-space reconciliation is the most common instance.)
- **Operand binding & alignment prep.** Per member, choose the chunk layer (resolver-checked, FR-7); choose the metric(s); optionally choose a root lens. A **pre-run cost estimate** — pairs × M×N × per-metric cost → predicted memory + wall-time, with the `O(T²)` pair count for corpus mode — shown before anything runs (principle P2; NFR-C4).
- **Candidate-generation as a recall dial (optional, dimension-driven).** Small M×N defaults to **exhaustive/dense** (no missed signal). Large matrices *recommend* (never force) candidate generation — ANN over embeddings (HNSW `efSearch` / IVF `nprobe` / multi-probe LSH / over-fetch-then-rerank for high recall) or MinHash-LSH over shingles for lexical similarity; the alignment family's dial is seed sensitivity. The mode spans **exhaustive ↔ high-recall ↔ fast**, with an **estimated-recall readout** and a forced-exhaustive escape hatch. The workbench never silently caps — it reports what it pruned (FR-22, FR-35).
- **Run/version manager.** List every analysis run with its metadata (params, timestamp, provenance), keep variants non-destructively, delete selectively — ground-truth masks excepted (they supersede) (FR-41).
- **Liftover.** Once an A↔B alignment exists, project A's masks / annotations / score-tracks onto B's coordinates via the alignment's `AlignmentMap` (the cross-text sibling of the single-text excision `OffsetMap`; see FR-42), producing new remapped track versions on B — additive, nothing destroyed (FR-42).

### 5.2 Example user journeys

- *Recension alignment:* import Douay-Rheims and KJV (two Imported Texts, asserted same Work) → one Project each, verse-numbers masked → new Collection, DR as root → reconcile embeddings into one space → run `cross` → read the verse-to-verse synteny, with the metric-gap layer flagging where KJV paraphrases vs. quotes.
- *Formula diffusion:* a corpus of epic texts → corpus-repeat detection finds a shared epithet → painted across the overview Circos → "core" in the pangenome classification → the influence graph orders who transmits it.
- *Source criticism:* a gospel synopsis collection → pairwise dotplots reveal the shared-order backbone (triple tradition) as a strong diagonal, with each text's unique material as gaps (single tradition).

---

## 6. Requirements

Continues the project FR sequence (Wave-0 ended at FR-22; the cross-text *engine* FR-18…22 are the substrate this tier consumes).

### Functional requirements

- **FR-23 — Object model is explicit.** The system distinguishes Work, Imported Text, Project, and Collection (§2.1). Imported Text records a content digest and an optional user-asserted `work_id`; a Project records the Imported Text it derives from and its masking/sectioning config; a Collection references Projects by stable `project_id`.
- **FR-24 — Membership lattice & inverse navigation.** Many-to-many at every level (§2.2), every edge navigable in both directions, exposed in the API and the Members tab. Extends `collections.py` (`collections_for_project`, `link_derived`) with edition- and work-level queries.
- **FR-25 — Collection-local role.** Each member carries a collection-local role (`root | compared | member`); a Collection has zero or one root. Role drives axis assignment in analyses and the viewer and is not a property of the Project.
- **FR-26 — Operand resolution across projects.** A `resolve_operand(collection, project_ref, requirements)` binds a member's layers (chunk + optional embedding + repeat-mask) into an `Operand` (vision FR-18), fail-loud and resolver-checked (FR-7), reusing existing layers across projects — never silently auto-producing.
- **FR-27 — Metric-congruence contract.** Every per-chunk metric carries a **congruence key** (analysis-type + model/params + dimensionality + analyzable digest, §3.5). A cross-text/corpus method on metric X requires matching X-keys across operands and **fails loud** when unmet, with an explicit reconcile action (§5.1). Embedding-space compatibility is one instance; the contract covers all metrics. No silent cross-key comparison.
- **FR-28 — Lifecycle: import / re-import / re-run & staleness.** Re-import creates an independent Project instance (never replaces); re-run edits within a Project. Results are content-addressed by operand identity; a **ground-truth-masking re-run** (not a re-import) stale-flags referencing results, and Project removal tombstones them (§2.3). No result is ever rendered against a mismatched analyzable frame.
- **FR-29 — Cross-text masking.** Corpus-repeat masking and low-correspondence masking (§3.4) are assembled as cross-corpus interval sets (corpus-repeat ∪ low-correspondence) and applied through the existing per-member excise/remap masking path (`analysis_view` `extra_masked`, riding the single-text `OffsetMap` machinery); the masking policy is declared, reported, and never a silent mutation. *(As built C5: interval assembly is cross-corpus; per-member excision reuses the Wave-0 mask path unchanged.)*
- **FR-30 — Cross-text & collection tracks.** A cross-text similarity layer is projected onto the chosen root's coordinate frame (`project_to_root`) and rendered as a root-frame conservation lane. *(As built C5: the cross-text track is **collection-scoped** — persisted under `collections/{id}/tracks/` and drawn by a dedicated conservation lane in the Corpus view, deliberately **not** injected into the root Project's per-project FR-13 track registry, to keep cross-text artifacts out of single-project readers/persist paths — lower blast radius. The FR-13 lane loop remains the mechanism for genuine per-project root-frame tracks.)* Collection-level annotation tracks are declared once and applied per member (each remapped into its member frame).
- **FR-31 — Corpus analyses.** Pairwise (`R(A,B)`), corpus (`{R(Ai,Aj)}`), and probe (`R(q,Corpus)`) modes (§3); pangenome classification and corpus weighting (§3.2) as first-class collection outputs.
- **FR-32 — Collection artifact store & provenance.** Collection-level artifacts (alignments, cross-text/corpus result manifests, the alignment graph, collection masks) persist under `collections/{id}/`, atomically (NFR-5), provenance-stamped so the result reconstructs from disk alone (principle P3) — including the identity of every operand.
- **FR-33 — Visualization suite.** The three zoom tiers (§4): collection overview (Circos / graph-bubble / block-map / phyletic tree), pairwise **heatmap + local-alignment dotplot + overlay + ribbon + mosaic** (heatmap and dotplot inter-mappable via character coordinates, both wanted; generalizing `DotplotView` + `OverviewBar`), and the single-text browser; plus the stacked-linear view. Self-comparison `R(A,A)` is a Project/TextHiC feature, not a Collection view.
- **FR-34 — Collection workbench UI.** Header compatibility badge + Members / Overview / Compare / Corpus / Masking-&-Tracks tabs (§5), integrated into the existing app frame (extends the Compare tab `collections.py` already references).
- **FR-35 — Operational tooling.** Metric-congruence reconciliation, operand binding, pre-run cost estimate (pairs × M×N × per-metric cost → memory + time), and a **candidate-generation recall dial** (optional, dimension-driven: exhaustive ↔ high-recall ANN ↔ fast, with estimated-recall readout and forced-exhaustive escape; never a silent cap) (§5.1), each explicit and costed.
- **FR-36 — Alignment export.** Cross-text alignments export as PAF (`specs/paf-v0.1.md`), the format's genuine use (vision §10.3).
- **FR-37 — CLI/HTTP parity.** Every collection operation (create, bind, run, export) is available on both the CLI and HTTP paths with one resolved-params source of truth (principle §2.2).
- **FR-38 — Phyletic / stemma tree.** A cladogram of the collection's texts: manual-first (user assigns root + groups taxa) as a hypothesis; distance-driven recompute (neighbor-joining / nearest-neighbor) once inter-text distances exist, auto-suggesting the optimal root with user override (§4.4). The root-selection aid for 3+ texts; lives in the Overview tab.
- **FR-39 — Metric-congruence surface.** The Collection UI shows, per metric, which member chunk-sets share a congruence key and are therefore available for cross-text comparison; incongruent pairs surface the reconcile action (§3.5, §5.1). The UI manifestation of FR-27.
- **FR-40 — Local-alignment discovery & dotplot thresholding.** An end-to-end find-and-extend pass (LASTZ seed-extend / Smith-Waterman, the cross generalization of the self kernel) discovers local alignments between two texts; each is scored *f(length × [matchiness − gappiness])*; an empirically-chosen cutoff on the score distribution selects which render as the dotplot (§3.1). Seed sensitivity is the recall dial.
- **FR-41 — Non-destructive run versioning.** Every analysis re-run is kept as a metadata-tagged version (params, timestamp, provenance), user-deletable via a run/version manager. **Exception:** Structural and Content masks are ground truth and supersede (no version accumulation). Makes principles §3.5's supersede-or-namespace deterministic (§2.3, §5.1).
- **FR-42 — Annotation / mask liftover.** Given an A↔B alignment, project A's masks / annotations / score-tracks onto B's coordinates, producing new remapped track versions on B. Purely additive; built on the same assert-or-fail remap discipline as analyzable→original (principles §4). *(As built C5: the coordinate map is a purpose-built `AlignmentMap` (`alignment/liftover.py`), the cross-text sibling of `OffsetMap` — `OffsetMap` models single-text excision (analyzable↔original within one text); liftover models cross-text A↔B block correspondence. It is **block-granular**: an interval lifts to the whole aligned paragraph block, not a proportional sub-span — it refuses a char-precision the paragraph-level alignment never established; intervals touching no aligned block are reported `dropped`.)*
- **FR-43 — Subtext extraction (Project-derives-from-Project).** A Project may be derived from a parent Project by a saved mask/filter extracting a sub-region (the Octapla / Adam-and-Eve / poem-in-a-volume case); parent + children auto-form a derived Collection (`collections.py kind="derived"`). The object model gains one edge: `Project.derived_from: project_id?`.

### Non-functional requirements

- **NFR-C1 — Backward compatibility (additive).** `collections.json` membership stays valid; all collection artifacts are new, additive paths. Existing single-text projects are unaffected.
- **NFR-C2 — Provenance & auditability (P1/P3).** A collection result names every operand by content identity; from the artifact alone the comparison reconstructs.
- **NFR-C3 — Fail-loud (G2/G4/G5).** Incompatible embedding spaces, unmet operand requirements, stale operands, and unmapped cross-text coordinates all raise descriptive errors. No silent fallback, no silent cross-model comparison, no silent coordinate retention.
- **NFR-C4 — Cost transparency (P2).** Every expensive collection operation (re-embedding, `O(N²)` pair sweeps, dense matrices) surfaces a pre-run estimate and never auto-runs.
- **NFR-C5 — Reuse over recompute.** Member layers are content-addressed and shared across collections; a result reuses compatible cached layers and prior alignments.
- **NFR-C6 — Coordinate honesty.** Every cross-text offset is remapped operand→root by the assert-or-fail discipline of principles §4; the root axis is the single coordinate backbone.
- **NFR-C7 — Honest visualization (P5).** Alignment-quality caveats (approximate vs. exact, similarity thresholds, pruning) travel with the data to the point of display.

---

## 7. Integration with existing architecture

| Collections-tier element | Rests on (existing mechanism) |
|---|---|
| Collection membership & many-to-many | `core/palimpsest/collections.py` (CRUD, `collections_for_project`, `link_derived`) — extended, not replaced |
| Operand & two-operand comparison | `ComparisonSpec(op_a, op_b, methods)` + `Operand` (P9 seam-lift, `tracks/bundles.py`) |
| Layer reuse across members | the resolver (`tracks/requirements.py` + `tracks/bundles.py`, FR-7) generalized to `resolve_operand` |
| Root projection of a track = coordinate map | `project_to_root` operand→root remap over the corpus graph (analysis-design-principles §4.1 discipline) |
| Cross-text A↔B liftover = coordinate map | purpose-built `AlignmentMap` (`alignment/liftover.py`) — block-granular A↔B correspondence, the cross-text sibling of the single-text `OffsetMap` |
| Multi-axis result manifest | `axes: [...]` + `mode`/`symmetric`/`storage` discriminators (vision FR-20, `specs/signals.md`) |
| Pairwise dotplot | `DotplotView` generalized from square `R(A,A)` to rectangular `R(A,B)` |
| Per-project root-frame tracks | the FR-13 `rendering`-descriptor lane loop + `OverviewBar` (no new renderer) |
| Cross-text conservation track | collection-scoped (`collections/{id}/tracks/`) + a dedicated Corpus-view conservation lane — kept out of the per-project registry (blast-radius; as built C5) |
| Probe / candidate generation | `SqliteVecStore.search` (ANN over the shared embedding space) |
| Alignment kernel | LASTZ seed-and-extend (`_extend_alignment`) with the `_is_self` diagonal guard dropped → Smith-Waterman cross-text |
| Export | `specs/paf-v0.1.md` (minimap2 PAF) |
| Synteny view pattern | ADR-005 / JBrowse 2 `LinearSyntenyView` |

The tier is an **extension of the same adapter/track/display/renderer hierarchy** (ADR-005 amendment): the only genuinely new structural pieces are a second coordinate axis (already specced as `axes[]`), the collection artifact store, and the object-model vocabulary. Everything else is promotion and generalization of machinery Wave 0 and P9 already built.

---

## 8. Non-goals

- We do **not** build a general document-asset manager, citation manager, or library catalog. A Collection is an analysis workspace, not a bibliography.
- We do **not** auto-detect that two Imported Texts are the same Work (Work identity is user-asserted; OQ-2).
- We do **not** re-derive any Wave-0 or P9 machinery; the tier consumes the operand/alignment/axes substrate as-is.
- We do **not** make any member the privileged "canonical" text of a Work; root is a collection-local, per-analysis choice (§2.2).
- We do **not** build a de-novo N-way multiple-alignment of the whole corpus in one pass. The reference-free graph (OQ-1, the default model) is **assembled from pairwise edges** (C2 → C3) — correspondences composed, not a new simultaneous aligner.

---

## 9. Open decisions for human review

Flagged inline above; collected here with a recommendation each.

1. **OQ-1 — DECIDED (2026-06-30): reference-free.** The default corpus model is the **co-equal alignment graph** (pangenome): no member is a privileged backbone (§2.2, §3.2). A **root-backbone projection** (the `OffsetMap`/`axes[]`/`DotplotView` synteny browser) is an explicit **per-view lens** computed from the graph (§4.2), used for pairwise synteny, translation/recension alignment, and "map onto text X" views. *(Superseded recommendation: reference-based default — chosen against, to avoid imposing a false source-hierarchy on a literary corpus; the higher build cost of graph construction + graph viz is accepted.)*
2. **OQ-2 — DECIDED (2026-06-30): Work = lightweight user-asserted tag.** A `work_id` string (possibly multi-level: Work ⊃ sub-work, or a series), with edition-sibling navigation derived from it; promote to an entity only if workflows demand it. Validated by the Adam-and-Eve / Octapla / Bibles cases (§2.1, FR-23).
3. **OQ-3 — DECIDED (2026-06-30): non-destructive versioning + ground-truth-mask supersede.** Analyses accumulate user-deletable versions (FR-41); Structural/Content masks supersede; staleness is triggered by a ground-truth-masking re-run, not a re-import (§2.3, FR-28). Project removal tombstones referencing results.
4. **OQ-4 — DECIDED (2026-06-30): metric-congruence, fail-loud + explicit reconcile.** Generalized beyond embeddings to all metrics (FR-27, §3.5): fail loud on incongruent metric keys, offer an explicit costed reconcile, never silently compare or re-embed.
5. **OQ-5 — DECIDED (2026-06-30): union (additive).** A collection-level mask *unions* with a member's own project mask — it never un-masks what the project masked. Both layers are surfaced distinctly so the user sees collection-scope vs project-scope masking (§4.4, FR-29).
6. **OQ-6 — DECIDED (2026-06-30): `workspace/collections/{id}/`.** Collection artifacts (alignments, result manifests, collection masks) live under `workspace/collections/{id}/`, paralleling the per-project layout so they are as inspectable, atomic, and content-addressable as project artifacts (FR-32, NFR-C2).
7. **OQ-7 — DECIDED (2026-06-30): sequence = plan → doc-review → object-model foundation → visible pairwise → remaining implied components.** The object model (FR-23…28) + operand resolution + embedding-compat (FR-26/27) land first (the "collection tier" P10 was gated on); the pairwise engine/dotplot follows; corpus graph, overview viz, masking/tracks, corpus analyses, and the workbench fan out after. Phasing detailed in the companion [collections-tier-plan.md](./collections-tier-plan.md).

**All decided (2026-06-30):** OQ-1…OQ-7 ratified. The design is gated only by the C1 build go-ahead.

---

## 10. Relationship to the development plan

This doc fills the gap [wave0-analysis-suite-vision.md §8](./wave0-analysis-suite-vision.md) named as out of scope ("the collection analytical tier") and the prerequisite [§10.3] named for the cross-text UI. The companion build plan — phasing, done-criteria, risk register — is now authored: [collections-tier-plan.md](./collections-tier-plan.md). The cross-text *engine* phases (P10/P11) in the existing Wave-0 plan are **reframed there as consumers of this tier**, not independent work: the pairwise engine + synteny lens (≈ P10) and the reference-free corpus graph + corpus mode (≈ P11) build over the object model defined here, with the corpus model **reference-free by default** (OQ-1).
