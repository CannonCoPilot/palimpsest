# Cross-Document Consistency Review — Palimpsest Domain Synthesis

**Date**: 2026-06-08 (v1.0); 2026-06-10 (v1.1 — addendum for Roadmap v4.0 alignment)
**Scope**: All domain synthesis documents (00–28), WALKTHROUGH.md, master-bibliography.md, reports 01–05, genome browser research
**Purpose**: Stage 2c of the back-to-drawing-board overhaul (doc 00 §Stage 2c). Identify inconsistencies, terminology drift, architectural contradictions, and version staleness across the document corpus.
**Reviewer**: Code Review agent (AC-03 Level 1 technical review)

> **v1.1 Addendum (2026-06-10)**: Roadmap v4.0 (doc 28) introduces new milestone numbering. Old M2→M3, old M3→M4, old M4→M5, old M5→M6. New M2 = "Interactive Workbench". Documents 12, 14, 23 are now SUPERSEDED. Documents 22, 24, 26, 27 have been updated to v1.1/v1.2 with v4.0 references. The Tauri/Rust/WebGPU architecture from doc 14 v4.0 was abandoned; current stack is Python+React. New terminology canon entries: M1.5 (Browser Foundation Sprint), F-BRW-007 through F-BRW-012, F-TRK-013, "Interactive Workbench" (M2). Bibliography expanded to 122+ sources (was 118). Nine genome browser papers added.

---

## 1. Executive Summary

The Palimpsest document corpus spans approximately 22 primary documents written across a compressed period (2026-06-06 through 2026-06-08) during rapid iterative development. The documents are substantively coherent at the architectural level — the core vision is consistent — but exhibit significant terminology drift, format hierarchy inversions that were corrected mid-corpus without full back-propagation, and a pronounced staleness divide between pre-research-expansion documents (written with a 49-source corpus) and post-expansion documents (written with 118 sources).

**Summary counts**:
- Terminology inconsistencies: 14
- Architectural contradictions: 7
- Citation format issues: 4
- Version-stale documents: 9
- Total issues identified: 34

---

## 2. Inconsistency Table

### 2.1 Terminology Inconsistencies

| # | Concept | Term Variant A | Term Variant B | Term Variant C | Documents Using A | Documents Using B | Documents Using C | Severity |
|---|---------|----------------|----------------|----------------|-------------------|-------------------|-------------------|----------|
| T1 | The HMM-based passage state classifier | `ModeHMM` | `PassageStateHMM` | `LitHMM` | 12, 14 (§5.2 note), 16 (E2) | 07 (§1.3), 09 (§1.3) | 19 (§3.1, §5.2), 18 | **HIGH** |
| T2 | The platform's per-text extension system | `Palimpsest-X` | `X` (unqualified) | — | 11, 19 (§5.2), 12a | 14, 12, 13, 13a | — | **LOW** |
| T3 | The primary annotation storage format | `PAF` (primary) | W3C Web Annotation (primary) | JSONL | 13, 13a, 12a, 12b | 14, 08, 09, 11, 07 | WALKTHROUGH | **HIGH** |
| T4 | The vocabulary for literary features | `LFO` (Literary Feature Ontology) | `NFL` (Narrative Function Library) | — | 07, 08, 09, 12, 13, 14, 19 | 09 (§MAPLE section only) | — | **MEDIUM** |
| T5 | The genome-analogue NLP pipeline | `NarrativeMAKER` | `EvidenceSegmenter` | — | 09 (§1.1) | 07 (§1.1) | — | **LOW** |
| T6 | The discrete passage encoding | `narrative alphabet` | `structural alphabet` | `16-letter structural encoding` | 01, 02, 03, 11, 19 | 01 (§1.4, quoting Foldseek) | 02 (table description) | **LOW** |
| T7 | The 15-dimensional narrative signature | `Boyd 15-dimensional arc` | `15-dim vector (3 dim × 5 segments)` | `narrative arc` (unqualified) | 11, 19, 12 | 03 | 02, 14 | **LOW** |
| T8 | The universal platform layer | `Palimpsest Base` | `Base platform` | `Base tracks` | 11, 19 | 12, 14 | 02, 13 | **LOW** |
| T9 | The human annotation environment | `ScholiaApollo` | `CollabReader` | Apollo-analogue (unnamed) | 09 (§1.5) | 07 (§1.5) | 08 | **LOW** |
| T10 | Chromatin states → literary passage states | `functional passage states` | `passage functional state` | `structural mode` | 07, 19 | 11 (table row label) | 11 (track table `Structural mode` column) | **MEDIUM** |
| T11 | The 3D text similarity matrix concept | `TextHiC` | `NarrativeFold` | `Self-Similarity Matrix` | 19, 18 | 07 (§1.3) | 02, 11 | **MEDIUM** |
| T12 | Evidence levels for annotations | `E1-E5` | `evidence levels` (generic) | `confidence scores` | 14 (§3.0 v3 note), WALKTHROUGH | 07, 09 | 12, 13 | **MEDIUM** |
| T13 | The text-equivalent of the genome annotation pipeline | `MAKER evidence model` | `evidence-based annotation` | `three-source evidence architecture` | 07, 09, 19 | 08, 11 | 19 (§6.3 novel contributions) | **LOW** |
| T14 | The annotation format during Phase 1 instability | `PAF Instability Policy` | `Format Instability Policy` | — | 13 (§0.2 heading) | 14 (§0.2 heading) | — | **LOW** |

### 2.2 Architectural Contradictions

| # | Issue | Description | Documents in Conflict | Severity |
|---|-------|-------------|----------------------|----------|
| A1 | PAF vs. W3C annotation format hierarchy | Doc 13 (original Phase 1 plan) declares PAF as the primary storage format and W3C Web Annotation as an export target. Doc 14 (revised plan) reverses this hierarchy: W3C JSON-LD/JSONL is primary, PAF is a computational export. Doc 12a §1.3 identifies this as a problem. Doc 14 v3.0 Key Corrections explicitly states the v2.0 had a "hierarchy inversion." However, WALKTHROUGH.md, which reflects the actual built system, describes output as `.jsonl` tracks (consistent with W3C primary), but section 5 CLI says `--format w3c` as one export option (implying W3C is still one of several). | 13, 12, 12b vs. 14, 07, 08, 11; WALKTHROUGH is ambiguous | **HIGH** |
| A2 | Technology stack: Python+React+Browser vs. Tauri+Rust+WebGPU | Doc 12 (roadmap v2.0) resolves the stack as Python/FastAPI backend + React/TypeScript frontend. Doc 15 (performance architecture) then replaces this with Tauri 2.0 + Rust core + WebGPU. Doc 14 (revised plan v4.0) incorporates the v4.0 redesign. But WALKTHROUGH.md describes a two-terminal workflow (Python backend + npm dev server) with no Tauri binary and no Rust commands — the actual system is the Python+React stack, not the Tauri+Rust stack. | 15, 14 (intent) vs. WALKTHROUGH.md (reality) | **HIGH** |
| A3 | Document storage format: JSONL vs. GFF3-analogue TSV | Doc 09 (genome annotation methods) describes outputs as "GFF3-analogue annotation file" with `chrom`, `start`, `end`, `type` columns throughout. Doc 07 references "GFF3/GTF/BED formats" as the target. Doc 08 (CL frameworks) and doc 11 (vision synthesis) settle on W3C Web Annotation JSON-LD. Doc 14 §0.2 clarifies: JSONL is the storage serialization of W3C JSON-LD. GFF3 is referenced only as an analogy, not an actual format. This analogy-to-reality slippage occurs across 09, 07, and 01 without a clear disclaimer. | 09, 07, 01 vs. 14, 11, 08 | **MEDIUM** |
| A4 | Track count in Phase 1 Base | Doc 02 (PRD) §Layer 2 lists 9 analysis components. Doc 11 (vision) §1.1 lists 12 Base tracks in its table. Doc 19 (conceptual foundation) §5.2 lists 12 Base tracks. Doc 14 (revised plan) describes "10 tracks/signals" as actually built. The checkpoint review (doc 16) confirms "10 tracks/signals" in the executive summary but the M1.4 deliverables table lists items still unbuilt. | 02, 11, 19 (12 tracks) vs. 14, 16 (10 tracks built) | **MEDIUM** |
| A5 | ChromHMM → LitHMM naming and conceptual scope | Doc 04 (genomics deep read) calls this a "ChromHMM-equivalent." Doc 07 calls it `PassageStateHMM`. Doc 12 and 14 call it `ModeHMM`. Doc 19 introduces `LitHMM` as the canonical name. The doc 16 checkpoint review finding E2 flags that `alphabet.py` still contains a stub comment calling the K-means step a "Phase 1 placeholder for ModeHMM (Phase 2)." Three different names for one concept across five documents, with the actual code using yet a fourth implicit name (`alphabet`). | 04, 07, 09 vs. 12, 14 vs. 19 vs. 16 (code) | **HIGH** |
| A6 | Whether Tauri/Rust code is built | Doc 14 and 15 describe a Tauri 2.0 + Rust core architecture. Doc 16 (checkpoint review) finding C5 reports `tauri.conf.json` pointing to wrong frontend path, and finding W18 notes Rust (`palimpsest-tauri`) has zero tests. But WALKTHROUGH.md has zero Rust commands — setup and run instructions are entirely Python + npm. Either Rust/Tauri is built but not exposed in WALKTHROUGH, or WALKTHROUGH reflects a state before the Tauri migration. | 14, 15 (design) vs. 16 (code findings) vs. WALKTHROUGH (user-facing) | **HIGH** |
| A7 | Signal format storage: `.npz` vs. `.bin` vs. `.json+.bin` | Doc 13a §1.4 identifies that `.npz` files cannot be loaded in a browser and recommends `.bin` + JSON manifest as the solution. Doc 14 does not explicitly resolve this. WALKTHROUGH §3 says `signals/` contains `narrative_arc.json + .bin`, `rqa.json + .bin`, `alphabet.json`, `topics_dist.json + .bin` — which matches the `.json+.bin` pattern. But doc 12b §2.3 proposes `PAF-Signal` as a separate JSON/NPZ format. The resolved format (JSON manifest + raw float32 binary) is described only implicitly in WALKTHROUGH. | 13a, 12b (proposals) vs. WALKTHROUGH (implementation) | **MEDIUM** |

### 2.3 Citation Consistency Issues

| # | Issue | Description | Documents Affected | Severity |
|---|-------|-------------|-------------------|----------|
| C1 | JBrowse 2 paper citation inconsistency | Doc 10 (visualization) references "JBrowse 2 2023" and "Diesh et al., 2024" in different sections of the same document (Finding 1 sources vs. §2.5). Bibliography lists `Diesh et al. (2023)`. | 10, 17 (§2.5), bibliography | **LOW** |
| C2 | Genette citation — two books conflated | Doc 07, 09, 11, 17, 19 all reference Genette's narratological categories (order, duration, frequency, mood, voice). Some cite "Narrative Discourse" (1972/1983), others cite "Palimpsests" (1982/1997). The narratological categories belong to "Narrative Discourse"; "Palimpsests" covers intertextuality. Doc 19 §2.4 correctly cites both with parenthetical disambiguation. Earlier docs conflate them. | 07, 09, 11 vs. 19, 17 | **MEDIUM** |
| C3 | Boyd et al. (2020) year inconsistency | Doc 03 (NLP deep read) §6 states Boyd et al., Science Advances 2020. Doc 11 §1.1 table cites "Boyd 15-dimensional function-word arc" with no year. Doc 19 §1.3 and §5.2 cites "Boyd et al. 2020" correctly. Doc 04 does not cite Boyd at all (it's a genomics doc, appropriate). Bibliography entry not checked but inconsistent citation practice exists. | 03, 11 vs. 19 | **LOW** |
| C4 | Claims without bibliography entries | Doc 00 (alignment convergence thesis) references "Reagan et al. (2016)" for emotional arcs in §3.2. This paper is in the bibliography (as a report 02 entry in the NLP catalog). However, doc 00 also references "Goyal et al." for plot units in §3.2 — this is not in the master bibliography and appears to be the Goyal et al. 2010 ACL paper on plot units from automated text analysis. Not in bibliography. | 00 | **LOW** |

### 2.4 Conceptual Consistency — Genomic Analogies

| # | Analogy | How Doc 04 Maps It | How Doc 07/09 Maps It | How Doc 19 Maps It | Consistent? | Severity |
|---|---------|-------------------|----------------------|-------------------|-------------|----------|
| G1 | ChromHMM → Literary equivalent | "chromatin state HMM applied to text" (§ENCODE section) | `PassageStateHMM` (§1.3 table) | `LitHMM` (§3.1, §5.2, §6.4) | Same concept, three names — see T1/A5 above | **HIGH** |
| G2 | Hi-C contact matrix → Text similarity | `TextHiC` passage-pair similarity matrix (§1) | `NarrativeFold` (§1.3 table) | `TextHiC` (§1.2, §4.2, §6.2) | Inconsistent name (NarrativeFold in 07 only) | **MEDIUM** |
| G3 | TADs → Narrative units | "TAD-like self-interacting domains" (§2) | `NarrativeFold` includes TAD detection (§1.3) | `TextHiC and Thematic Compartmentalization` (§6.2) | Conceptually aligned; naming inconsistency only | **LOW** |
| G4 | MAKER pipeline → Annotation pipeline | Not covered (genomics doc doesn't reverse-map) | `NarrativeMAKER` / `EvidenceSegmenter` (§1.1) | "MAKER evidence model" (§2.2, §2.3, §6.3) | Doc 07 uses EvidenceSegmenter; doc 09 uses NarrativeMAKER for the same concept | **MEDIUM** |
| G5 | Foldseek 3Di alphabet → narrative alphabet | Not covered (Foldseek in report 01, not doc 04) | Not covered | `narrative alphabet` via Foldseek analogy (§1.3) | Only doc 19 makes this explicit; earlier docs use the analogy without citing Foldseek | **MEDIUM** |
| G6 | Sequence Ontology → Literary Feature Ontology | Not covered | `Literary Feature Ontology (LFO)` introduced (§4) | `Literary Feature Ontology (LFO)` (§2.4) | Consistent between 07 and 19; earlier docs (01, 02, 12) use "LFO" without defining it | **LOW** |
| G7 | Epigenetic patterning → style/register | Doc 01 §2.2 table maps this | Doc 07 maps `PassageStateHMM` to this layer | Doc 19 §2.3 maps "style, register, and voice" to epigenetic patterning | Three documents agree; consistent | **NONE** |

---

## 3. Version Staleness Assessment

### 3.1 Pre-Research-Expansion Documents (written before 2026-06-07 expansion; reference ~49-source corpus)

These documents were written before the research corpus grew from 49 to 118 sources. They may reference the research landscape incompletely, use informal citations where formal ones now exist, or miss key conceptual sources that later documents build on.

| Document | Staleness Issues | Priority for Update |
|----------|-----------------|---------------------|
| **00-alignment-convergence-thesis.md** | References "Reagan et al." and "Goyal et al." informally. Does not cite Gale-Church, CollateX, GNAT, or Büchler — all now in corpus. The "search strategy" framing is pre-research and now superseded by Stage 1 completion. §5 "Key Authors" list is incomplete relative to the expanded corpus. | MEDIUM |
| **01-conceptual-framework.md** | Cites "Mäkinen et al." correctly (already in corpus). References Foldseek, GNAT, and Pial & Skiena informally — these now have formal bibliography entries. Does not cite ChromHMM (Ernst & Kellis) which is now foundational to the LitHMM concept it introduces. Introduced the narrative alphabet concept without the Foldseek citation that would later ground it. | MEDIUM |
| **02-PRD-outline.md** | Pre-dates the annotation format resolution (PAF as primary, not W3C). Layer 3 §Alignment describes "Sequence Alignment" as "GNAT-inspired" but doesn't cite GNAT formally. Layer 5 mentions TEI-XML without reference to the TEI Standoff solution documented in doc 08. Status tags (`Built`, `Not built`) are now outdated given M1.3b completion. | HIGH |
| **03-deep-read-nlp-narrative.md** | Written with a 12-paper set before the 30-paper CL expansion. Does not reference: Vaswani/Transformers, Devlin/BERT, CollateX, INCEpTION, Artstein inter-annotator agreement, PDTB, Hearst TextTiling — all now in corpus and relevant to narrative NLP. | MEDIUM |
| **04-deep-read-genomics.md** | Written with 7 genomics papers. Does not reference: Needleman-Wunsch, Smith-Waterman, BLAST (all now in corpus and referenced in 19). Sequence Ontology and Gene Ontology not covered despite being in the bibliography. The ChromHMM discussion (ENCODE §) is correct but does not cite Ernst & Kellis (2010, 2012) by name — only says "ChromHMM" without citation. | MEDIUM |
| **05-deep-read-literary-studies.md** | Pre-dates corpus expansion. The eight books covered are still the core literary studies corpus. No staleness issue with the content, but post-expansion sources like Genette/Narrative Discourse, Kristeva, Burrows Delta, and Eder/stylo are now in the bibliography and could enrich the "development implications" sections. | LOW |
| **06-deep-read-visualization.md** | References 4 papers + 2 books. Post-expansion now has 25 visualization sources. StoryRibbons (2025), Jänicke et al. (2015 survey), Kim/StoryCurves (2018), NetworkNarratives (2023) — all now in corpus and directly relevant but absent from this document. HiGlass not referenced here though it is in the bibliography. | HIGH |
| **07-annotation-framework.md** | Substantively strong. Post-expansion adds Artstein & Poesio (2008) and Pustejovsky & Stubbs (2012) to the annotation theory background it should cite. The W3C WADM discussion is correct and matches doc 08's analysis. Minor: uses "GFF3-analogue" throughout as a shorthand, but this risks being read as an actual format choice — needs a disclaimer. | LOW |
| **08-annotation-cl-frameworks.md** | Very strong and consistent with later documents. Established the W3C WADM primacy that doc 14 v3.0 codifies. Minor: references "Recogito Studio (2024)" — this is not in the master bibliography. | LOW |
| **09-annotation-genome-methods.md** | Strong content but uses the GFF3 format as actual proposed output format throughout, not just as analogy. Doc 14 later clarifies GFF3 is an analogy and W3C JSONL is the actual format. This inversion — GFF3 analogy treated as implementation target — is the primary staleness issue. Also uses `NarrativeMAKER` vs doc 07's `EvidenceSegmenter`. | MEDIUM |

### 3.2 Research-Expansion-Era Documents (written 2026-06-07 during/after expansion)

These documents are substantively current but may reference the expansion incompletely or be inconsistent with each other.

| Document | Staleness Issues | Priority for Update |
|----------|-----------------|---------------------|
| **11-palimpsest-vision-synthesis.md** | Written 2026-06-06 (labeled "integrates documents 00-10, 366KB, 140+ citations"). The citation count of 140+ is inconsistent with the actual 118-source bibliography; this appears to be counting reports and web resources separately. References `ModeHMM` (the old name) in §1.1 track table row header. Does not reference LitHMM, which doc 19 establishes as the canonical name. | MEDIUM |
| **12-development-roadmap.md** | Written 2026-06-06. Technology decisions table is still accurate (React, Python, W3C). However, the `frontend framework` row says "React + TypeScript / JBrowse 2 is React/TypeScript; adopting the same stack enables adapter/renderer reuse" — this is aspirational framing that conflicts with WALKTHROUGH.md's simpler two-server setup. | LOW |
| **13-phase1-plan.md** | Explicitly superseded by doc 14 per its header. Retained for reference. Primary staleness: still uses PAF as the primary format (the hierarchy inversion), day-level scheduling is moot. | SUPERSEDED — no update needed |
| **14-phase1-plan-revised.md** | Most authoritative planning document. v4.1 incorporates M1.3b checkpoint. The WALKTHROUGH.md suggests the built system doesn't implement the Tauri/Rust layer described in §v4.0 architecture summary — see A2 and A6 above. | MEDIUM (verify Tauri reality) |
| **15-performance-architecture-v4.md** | The design document for Tauri+Rust. WALKTHROUGH contradicts its "current" status. Needs either a "design intent" or "partially implemented" header. | HIGH (status unclear) |
| **16-checkpoint-review-m13b.md** | Accurately reflects codebase state at M1.3b. No staleness issues — it IS a snapshot. References `ModeHMM` in finding E2. | LOW |
| **17-swinehart-deep-analysis.md** | Written 2026-06-08, most current. References `JBrowse 2 (Diesh et al., 2024)` while bibliography has 2023; minor. Otherwise consistent with doc 19. | LOW |
| **18-stage1-completion-gap-analysis.md** | Written 2026-06-08. Accurate and current. | NONE |
| **19-conceptual-foundation.md** | Written 2026-06-08. Most conceptually current document. Introduces `LitHMM` as the canonical name. References Pial & Skiena 2023 (GNAT) correctly. Contains no architectural contradictions. Minor: "118 sources in the master bibliography" — the bibliography confirms this. | NONE (reference document) |

---

## 4. Terminology Canon

The following table establishes the definitive term for each concept, with rationale. When revising documents, use these canonical terms.

| Concept | **Canonical Term** | Rationale | Retire |
|---------|-------------------|-----------|--------|
| The HMM-based passage state classifier (ChromHMM analogue for text) | **LitHMM** | Introduced in doc 19 (the most current, most grounded document). "ModeHMM" conflates with "mode" in the narrative modes sense. "PassageStateHMM" is accurate but verbose. "LitHMM" is parallel to ChromHMM in the exact same way that "LFO" is parallel to SO. | ModeHMM, PassageStateHMM |
| The controlled vocabulary of literary features (Sequence Ontology analogue) | **Literary Feature Ontology (LFO)** | Established consistently across 07, 08, 09, 12, 13, 14, 19. The single exception is "NFL" (Narrative Function Library) in doc 09 §MAPLE section, which is a local coinage for the KAAS analogy and should be footnoted as a sub-component of LFO, not an alternative name. | NFL (as alternative to LFO) |
| The primary annotation storage format | **W3C Web Annotation JSON-LD serialized as JSONL** | Established by doc 14 v3.0 Key Correction #1, grounded in docs 07 and 08. PAF (GFF3-analogue TSV) is an export/computational format only. WALKTHROUGH.md confirms: `tracks/*.jsonl` is the actual output. | PAF (as primary format label) |
| The export/computational annotation format (GFF3-analogue) | **PAF (Palimpsest Annotation Format)** | Retained as the name for the TSV export. Docs 12b and 14 both use this consistently for the export format. | GFF3-analogue (should always be called PAF when referring to Palimpsest's specific format) |
| The passage-pair similarity matrix (Hi-C analogue) | **TextHiC** | Used in docs 19, 18, and doc 01. The name "NarrativeFold" (doc 07 §1.3) appears only once and should be retired. TextHiC mirrors the genomic naming convention (HiC → TextHiC) used for LitHMM and LFO. | NarrativeFold |
| The 15-state chromatin model applied to text passage states | **passage functional states** (as noun); **functional state** (as adjective for a track or annotation) | Used in docs 07 and 19. "Structural mode" in doc 11's track table is a display label for the same concept and should be harmonized. | Structural mode (as a concept name; acceptable as a UI display label if clearly annotated) |
| The universal annotation evidence framework | **MAKER evidence model** | Used in docs 07, 09, 19 consistently. "Evidence-based annotation" is the general field practice; "MAKER evidence model" is Palimpsest's specific adoption of the pattern. | Evidence-based annotation (acceptable as description, not as a proper name for Palimpsest's architecture) |
| The three evidence streams in the MAKER model | **ab initio predictions, textual evidence, cross-text parallels** | Doc 19 §2.2 establishes the clearest mapping. Doc 07 §0 uses slightly different labels. These should be harmonized. | Alternative labelings in 07 (transcript evidence / protein homology) are pedagogically useful as the genomic mapping but should be footnoted, not used as Palimpsest's own vocabulary |
| The K-means narrative encoding (Foldseek 3Di analogue) | **narrative alphabet** | Consistent across 01, 02, 03, 11, 19. "Structural alphabet" in doc 01 is used in the Foldseek context (correctly) and should not replace "narrative alphabet" as Palimpsest's term. | structural alphabet (as Palimpsest's term; acceptable when describing the Foldseek inspiration) |
| The evidence level system for annotations | **evidence levels E1–E5** | Established in doc 14 v3.0 Key Correction #3 and confirmed in WALKTHROUGH §7.3. Earlier docs using "confidence scores" alone should add the E1-E5 framework. | confidence scores (acceptable as a supplemental metric; should not replace E1-E5 as the primary evidence classification) |
| The per-text adaptive extension system | **Palimpsest-X** | Used consistently in 11, 12, 19. Shortened to "X" in some contexts — acceptable where context is clear. | No retirement needed; "X" is acceptable shorthand |
| The overall platform | **Palimpsest Base** (universal layer) and **Palimpsest-X** (per-text extension) | Established in doc 11 and carried through 12, 14, 19. | Base platform (acceptable variant); Base/X architecture (acceptable collective reference) |

---

## 5. Stale References — Documents Needing Update

### Priority 1 (HIGH — architectural contradictions that will confuse implementers)

**02-PRD-outline.md**: Status tags (`Built`, `Not built`, `Partial`) reflect the state as of 2026-06-06, before M1.3b completion. The PAF-as-primary hierarchy inversion is embedded in Layer 1–3 descriptions. Any engineer reading this as the current PRD will get wrong format guidance. This document should be updated to reflect M1.3b completion status and the W3C-primary format decision, or superseded by a new PRD (Stage 3b of the overhaul).

**15-performance-architecture-v4.md**: Describes the Tauri 2.0 + Rust core + WebGPU architecture as the current design. WALKTHROUGH.md describes a Python+npm two-server stack with no Tauri binary. Either the Tauri layer is partially built and WALKTHROUGH hasn't been updated, or the Tauri design is aspirational. The document needs a status header clarifying: "Design intent — partially implemented as of M1.3b; see doc 16 for implementation state."

**06-deep-read-visualization.md**: Written with a 4-paper visualization corpus. The 25-source visualization corpus now available (Jänicke survey 2015, StoryRibbons 2025, Kim/StoryCurves 2018, NetworkNarratives 2023, L'Yi/Gosling 2022 grammar) substantially changes the landscape assessment. The development implications in this document should be revised against the full visualization corpus.

### Priority 2 (MEDIUM — terminology or format issues that create confusion)

**09-annotation-genome-methods.md**: The GFF3 format is used as both analogy and implementation target throughout. Every output description (e.g., "Outputs. A GFF3-analogue annotation file: each scene/episode as a span record with `chrom` = document ID...") risks being read as specifying actual Palimpsest output rather than illustrating the analogy. Each such section needs a parenthetical disambiguating "this describes the structural analogy; actual Palimpsest output uses W3C JSONL."

**11-palimpsest-vision-synthesis.md**: Uses "ModeHMM" in the Base track table (§1.1). Should be updated to "LitHMM" per the terminology canon. The claim "integrates all prior research (documents 00-10, 366KB, 140+ citations)" should be updated or qualified — the post-expansion corpus is 118 sources, and doc 19 (conceptual foundation) now supersedes this document as the most citation-dense synthesis.

**04-deep-read-genomics.md**: The ChromHMM discussion correctly identifies the analogy but does not cite Ernst & Kellis (2010, 2012) by name — only says "ChromHMM" without a bibliographic reference. Doc 19 correctly cites these. The deep read doc should be updated with the formal citations now in the bibliography.

**00-alignment-convergence-thesis.md**: The §5 "Key Authors to Track" list is a pre-research artifact. It lists 12 authors but is missing key figures now central to the corpus: Ernst & Kellis (ChromHMM), Eilbeck (Sequence Ontology), Pial & Skiena (GNAT), Genette (narratology), Kristeva, Devlin (BERT), Vaswani (Transformers). The section should be updated to reflect the full research corpus or replaced with a reference to the bibliography.

**WALKTHROUGH.md**: Written to describe the M1.3b built system. It does not reference the Tauri/Rust architecture at all. If the Tauri build exists, the WALKTHROUGH should include how to build and run it. If it does not exist, the discrepancy with docs 14 and 15 should be documented. Currently the WALKTHROUGH is the most accurate picture of what actually runs, but it conflicts with the architectural aspiration documented elsewhere.

### Priority 3 (LOW — citation completeness and minor harmonization)

**08-annotation-cl-frameworks.md**: References "Recogito Studio (2024)" without a bibliography entry. Should add citation or remove the year.

**03-deep-read-nlp-narrative.md**: Does not reference post-expansion corpus additions (Vaswani/Transformers, Devlin/BERT, CollateX, INCEpTION). The "Summary Architecture" at the top predates the richer analytic stack described in doc 19. Worth a revision pass once doc 19 is stable.

**13a-phase1-critical-review.md** and **12a-roadmap-critical-review.md**: These are critical reviews of superseded documents. They retain historical value but should each receive a header note indicating which version they reviewed and whether their findings were incorporated.

---

## 6. Specific High-Priority Fixes

The following items require targeted fixes before the Stage 3 (Vision/PRD/Roadmap) documents are written. Fixing these will prevent the contradictions from propagating into the authoritative planning documents.

### Fix 1: Establish a canonical "Current Architecture" document

The stack description is currently split across: doc 12 (tech decisions table), doc 15 (Tauri design), doc 14 (v4.0 architecture summary), and WALKTHROUGH (actual system). Stage 3 documents (Vision, PRD, Roadmap) need a single authoritative source for "what is the current implementation state vs. future design target." Recommend a dedicated architecture decision record (ADR) that clearly labels: (a) what is built and working, (b) what is designed but not yet built, (c) what is aspirational design.

### Fix 2: Resolve PAF-primary vs. W3C-primary in doc 02

The PRD outline (doc 02) is the document most likely to be read as a specification by new contributors. It must reflect the W3C-primary format decision. A single note at the top of Layer 1 ("Note: format decisions were revised in doc 14 v3.0 — W3C JSON-LD/JSONL is primary; PAF is computational export only") and updated status tags are the minimum required fix.

### Fix 3: Propagate LitHMM terminology

"ModeHMM" appears in doc 16 finding E2 (quoting actual code comments) and doc 11's track table. The code comment is the most important fix — the `alphabet.py` module's `SignalManifest` note saying "placeholder for ModeHMM (Phase 2)" should be updated to "placeholder for LitHMM (Phase 2)". The doc 11 table can be updated in the next revision pass.

### Fix 4: Clarify Tauri build status

Add a single-sentence status header to doc 15: "Status: Design specification. As of M1.3b, the Rust/Tauri core is partially scaffolded (palimpsest-core crate exists, palimpsest-tauri crate exists with zero tests per doc 16 W18) but the production interface remains the Python+React stack described in WALKTHROUGH.md."

### Fix 5: Consolidate the annotation evidence model vocabulary

Docs 07 and 19 both describe the MAKER three-source evidence model but use slightly different labels for the three evidence streams. Doc 19's labels should be treated as canonical: (1) ab initio predictions, (2) textual evidence, (3) cross-text parallels. A footnote in doc 07 pointing to doc 19 §2.2 for the authoritative mapping would suffice.

---

## 7. Summary Scorecard

| Category | Issues Found | High | Medium | Low |
|----------|-------------|------|--------|-----|
| Terminology inconsistencies | 14 | 3 | 4 | 7 |
| Architectural contradictions | 7 | 4 | 3 | 0 |
| Citation format issues | 4 | 0 | 1 | 3 |
| Conceptual mapping inconsistencies | 7 | 1 | 3 | 3 |
| **Total** | **32** | **8** | **11** | **13** |

**Overall corpus health**: Architecturally coherent at the vision level. The core conceptual framework (text-as-genome, annotation-as-tracks, genome-browser-as-interface, Base/X) is consistent across all documents. The inconsistencies are primarily the product of rapid iterative writing across a 3-day period with decisions being revised mid-corpus (most critically: the PAF/W3C format hierarchy inversion). The Tauri/Rust architecture state is the most significant unresolved contradiction because it affects what the WALKTHROUGH describes, what the plan documents promise, and what the checkpoint review confirms was and wasn't built.

---

## 8. Reading Order for the Revised Corpus

After fixes are applied, the intended reading order for a new contributor should be:

1. **doc 00** (alignment convergence thesis) — entry point, topology of the problem space
2. **doc 19** (conceptual foundation) — the authoritative conceptual synthesis, post-expansion
3. **doc 11** (vision synthesis) — product vision (read alongside doc 19; use doc 19 where they conflict)
4. **doc 07** (annotation framework) — annotation architecture deep dive
5. **doc 09** (genome annotation methods) — implementation analogies (read with disclaimer about GFF3 as analogy)
6. **doc 12** (development roadmap v2.0) — development plan
7. **doc 14** (phase 1 plan revised v4.1) — implementation specification
8. **doc 16** (checkpoint review M1.3b) — current state assessment
9. **WALKTHROUGH.md** — hands-on system verification
10. **docs 17, 18** — Swinehart analysis + Stage 1 completion gap analysis (reference documents)

---

*This document is the Stage 2c deliverable specified in 00-back-to-drawing-board.md §Stage 2: Domain Synthesis Revision §2c Cross-Document Consistency. It supersedes no prior document and should be read alongside all the documents it reviews.*
