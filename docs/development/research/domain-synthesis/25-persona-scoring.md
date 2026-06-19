# Adversarial Persona Scoring — Docs 21-24

**Date**: 2026-06-08
**Purpose**: Formal review of Stage 3 deliverables against the five adversarial personas defined in doc 00 §Stage 4. Each document scored 1-5 per persona's dimension. Threshold: ≥4/5 on all applicable dimensions.

> **NOTE (2026-06-10)**: This scoring covers docs 21-24 as of v3.0 roadmap. Doc 28 (Roadmap v4.0) adds M1.5 and M2 (Interactive Workbench). A rescore against the new M2 features (heatmap interactivity, character system, analysis workbench, multi-tab layout) should be conducted during M1.5 implementation.

---

## Scoring Criteria

| Score | Meaning |
|-------|---------|
| 5 | Exceeds expectations — no concerns |
| 4 | Meets expectations — minor concerns noted but non-blocking |
| 3 | Below threshold — specific remediation required before proceeding |
| 2 | Significant gaps — major revision needed |
| 1 | Fundamentally inadequate |

---

## Doc 21: Vision Document

| Persona | Score | Assessment |
|---------|-------|------------|
| **Dr. Marchetti** (Genomics) | **4/5** | Genomic analogies are structurally grounded, not superficial. The isomorphism table (§2.1) correctly maps NW→text alignment, ChromHMM→LitHMM, SO→LFO, JBrowse→PTB. §2.2 honestly addresses where the analogy breaks (intentionality, ambiguity, aesthetic purpose). *Minor concern*: the chromatin state → literary state mapping table (§4.5) could benefit from empirical validation — currently theoretical. |
| **Dr. Okonkwo** (Architecture) | **4/5** | Technology stack is clearly specified. JBrowse 2 adapter/track/display/renderer pattern correctly adopted. Performance addressed in endnotes (Rust text processing, web workers, virtual scrolling). *Minor concern*: no explicit latency targets stated in the vision — the PRD (doc 22 NFR-001) fills this gap. |
| **Prof. Blackwood** (CL / Comp Lit) | **4/5** | Base/X architecture correctly separates machine reduction from human judgment. Perspectival modeling (Underwood 2019) embedded throughout. Piper's iterative cycle (§3.2) frames computation as tool, not authority. *Minor concern*: the document leans heavily on the genome metaphor — some CL scholars may resist the biologistic framing. The "where the analogy breaks" section (§2.2) is the right mitigation but could be more prominent. |
| **Dr. Patel** (Visualization) | **5/5** | Four views (linear, circular, dotplot, network) well-justified with research citations. Bertin, Tufte, Munzner, Furnas all referenced. Semantic zooming table (§5.2) covers five zoom levels. Design principles (§5.3) include phenomenological fidelity, data-ink ratio, progressive disclosure, CMV. No concerns. |
| **Alex Chen** (Power User) | **4/5** | Corpus-scale operations specified in §8.1. Narrative alphabet alignment enables fast structural search. 50-novel comparison scenario described. *Minor concern*: the vision doesn't quantify "fast" — the roadmap (doc 23) and PRD (doc 22) provide the concrete targets. |

**Doc 21 verdict**: **PASS** (4.2/5 average, all ≥4)

---

## Doc 22: Product Requirements Document

| Persona | Score | Assessment |
|---------|-------|------------|
| **Dr. Marchetti** (Genomics) | **4/5** | Every genomic analogue correctly mapped in the feature tables. MAKER evidence model (F-EXT-002/003) formally specified. LFO requirement (F-FMT-002) specifies OWL/RDF serialization. *Minor concern*: no requirement for validation that LitHMM states correspond to meaningful literary categories — should add an acceptance criterion involving literary scholar evaluation. |
| **Dr. Okonkwo** (Architecture) | **5/5** | 39 requirements with clear acceptance criteria. NFR-001 specifies concrete performance targets (5 min full-novel ingest, 60fps, <3s dotplot). Stack decisions resolved. Plugin architecture (NFR-004) specified. Degradation paths mentioned for each ML dependency. No concerns. |
| **Prof. Blackwood** (CL / Comp Lit) | **4/5** | F-AI-004 (perspectival modeling) is a first-class requirement. User narratives (§10) ground features in realistic scholarly workflows. F-EXT-001 (custom schema creation) ensures the platform adapts to literary diversity. *Minor concern*: the PRD could include a requirement for annotation provenance — "who annotated this and when" — critical for scholarly citation. Adding to remediation list. |
| **Dr. Patel** (Visualization) | **5/5** | F-BRW-001 through F-BRW-006 comprehensively cover the four views, CMV, and semantic zooming. Each has concrete acceptance criteria. D3 + Canvas rendering choices justified. No concerns. |
| **Alex Chen** (Power User) | **4/5** | NFR-001 and NFR-002 address performance and scale. UN-004 describes the 50-novel corpus scenario. *Minor concern*: no requirement for batch export of analyses — Alex wants to export his structural clustering to a CSV for his DH paper. Adding to remediation list. |

**Doc 22 verdict**: **PASS** (4.4/5 average, all ≥4)

**Remediation items**:
- Add F-TRK-008 acceptance criterion: "LitHMM states validated by literary scholar as corresponding to meaningful passage categories"
- Add F-FMT-004: Annotation provenance (who, when, tool, confidence)
- Add F-BRW-007 or extend F-ALN: Batch export of analysis results (CSV, JSON, BibTeX)

---

## Doc 23: Development Roadmap v3.0

| Persona | Score | Assessment |
|---------|-------|------------|
| **Dr. Marchetti** (Genomics) | **4/5** | Genomic analogues maintained in milestone descriptions. LitHMM positioned correctly in M1.4 (after feature tracks are available to train on). *Minor concern*: no explicit milestone for LFO formalization — it grows organically through M1-M3 but should have a checkpoint. |
| **Dr. Okonkwo** (Architecture) | **5/5** | Vision-gated milestones are the right pattern. Risk register identifies the key technical risks with concrete mitigations. Gantt chart provides realistic timeline (39 weeks). Dependency ordering is sound. No concerns. |
| **Prof. Blackwood** (CL / Comp Lit) | **4/5** | Vision gates describe demonstrated capability, not just code completion — this is the right approach. M3 (X Architecture) correctly positions human-AI collaboration as the differentiating feature. *Minor concern*: no milestone specifically for literary scholar user testing — should be part of M3 or M5 gates. |
| **Dr. Patel** (Visualization) | **4/5** | M2.3 (Circular + Dotplot views) has a strong vision gate ("a Palimpsest version of Swinehart's All Those Footnotes"). M1.3 covers full browser with semantic zooming. *Minor concern*: HiGlass-style zoomable heatmap not explicitly in any milestone — it's implied by dotplot but not specified. |
| **Alex Chen** (Power User) | **5/5** | M4 (Corpus Scale) directly addresses Alex's demands. The vision gate ("50 Victorian novels, structural clustering, 3 distinct shapes, Brontë discovery") is exactly the kind of result Alex would publish. The 39-week timeline is aggressive but Alex would say "that's too slow" regardless. No concerns. |

**Doc 23 verdict**: **PASS** (4.4/5 average, all ≥4)

**Remediation items**:
- Add LFO formalization checkpoint to M3.1
- Add literary scholar user testing to M3 or M5 vision gate
- Specify HiGlass-style zoomable heatmap in M2.3 deliverables

---

## Doc 24: M1 Roadmap-PRD

| Persona | Score | Assessment |
|---------|-------|------------|
| **Dr. Marchetti** (Genomics) | **4/5** | M1.4 correctly positions LitHMM after feature tracks are computed (can't train HMM without features). TextHiC (self-similarity matrix) and thematic compartments (A/B decomposition) correctly specified. *Minor concern*: the TAD-like domain detection (Dixon method) acceptance criteria should specify a statistical significance threshold for boundary calls. |
| **Dr. Okonkwo** (Architecture) | **5/5** | Phase decomposition is clean. Each phase has concrete deliverables and acceptance criteria. Dependency ordering is sound (entity track before coreference, features before LitHMM). Performance targets specified (5s ingest, 60fps, <3s dotplot). No concerns. |
| **Prof. Blackwood** (CL / Comp Lit) | **4/5** | The M1 vision gate narrative (Dr. Amara discovering dramatic peaks via LitHMM) is compelling and grounded. *Minor concern*: the narrative focuses on IJ — should also include a simpler text (P&P) to demonstrate Base tracks work on a more conventional novel. |
| **Dr. Patel** (Visualization) | **4/5** | Visualization deliverables per phase are clear. Dotplot in M1.4 uses Canvas-based tiled rendering. *Minor concern*: no wireframe or mockup of the final M1 browser layout — would help implementers understand the spatial arrangement of tracks. |
| **Alex Chen** (Power User) | **4/5** | Full P&P novel at 60fps is good. LitHMM on full IJ is ambitious. *Minor concern*: what happens when LitHMM discovers 15 states and they're all meaningless? Need a fallback: try different feature subsets, different state counts. The acceptance criterion "states are interpretable" needs a concrete evaluation protocol. |

**Doc 24 verdict**: **PASS** (4.2/5 average, all ≥4)

**Remediation items**:
- Add TAD boundary significance threshold to M1.4 acceptance criteria
- Add P&P validation alongside IJ in M1 vision gate
- Add LitHMM fallback protocol when states are uninterpretable
- Create browser layout wireframe for M1 implementers

---

## Summary

| Document | Marchetti | Okonkwo | Blackwood | Patel | Chen | Average | Verdict |
|----------|-----------|---------|-----------|-------|------|---------|---------|
| Doc 21 (Vision) | 4 | 4 | 4 | 5 | 4 | 4.2 | **PASS** |
| Doc 22 (PRD) | 4 | 5 | 4 | 5 | 4 | 4.4 | **PASS** |
| Doc 23 (Roadmap) | 4 | 5 | 4 | 4 | 5 | 4.4 | **PASS** |
| Doc 24 (M1 Plan) | 4 | 5 | 4 | 4 | 4 | 4.2 | **PASS** |

**All documents PASS the ≥4/5 threshold on all applicable dimensions.**

---

## Consolidated Remediation List

These items should be addressed during implementation, not as document revisions:

1. LitHMM states validated by literary scholar (empirical, not just feature-distribution description)
2. Annotation provenance metadata (who, when, tool, confidence) as a formal requirement
3. Batch export of analysis results (CSV, JSON, BibTeX)
4. LFO formalization checkpoint in M3.1
5. Literary scholar user testing gate in M3 or M5
6. HiGlass-style zoomable heatmap in M2.3
7. TAD boundary significance threshold in M1.4
8. P&P validation alongside IJ in M1 vision gate
9. LitHMM fallback protocol for uninterpretable states
10. Browser layout wireframe for M1 implementers
