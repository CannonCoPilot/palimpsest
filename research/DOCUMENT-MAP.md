# Palimpsest Project Documentation Map

**Last updated**: 2026-06-10
**Total documents**: 33 domain synthesis docs + 40 phase-1 task docs + 5 reports + 8 genome browser reports + bibliography + WALKTHROUGH + this map

---

## Reading Order

For a new contributor, read in this order:

1. **This map** — you're here
2. **Doc 19** (Conceptual Foundation) — the intellectual core
3. **Doc 21** (Vision Document) — what we're building and why
4. **Doc 22** (PRD) — every feature specified
5. **Doc 28** (Roadmap v4) — how we build it, milestone by milestone (supersedes doc 23)
6. **Doc 24** (M1 Roadmap-PRD) — Phase 1 in detail
7. **Doc 26** (Design Philosophy & Exit Criteria) — FDD/BDD methodology, user stories, M1 exit gates
8. **Doc 27** (M1 Completion Plan) — EPUB pipeline + 41 atomized tasks for remaining M1 work
9. **WALKTHROUGH.md** — how to run what's already built
10. **Bibliography** — the research corpus (122+ sources)

For domain-specific deep dives, consult the source material documents below.

---

## Primary Document Chain (force-load in Jarvis sessions)

These are the authoritative current documents. All others are source material or historical.

| Doc | Title | Role | Size |
|-----|-------|------|------|
| **19** | [Conceptual Foundation](domain-synthesis/19-conceptual-foundation.md) | Intellectual backbone — synthesizes all research into unified framework | ~6K words |
| **21** | [Vision Document](domain-synthesis/21-vision-document.md) | What Palimpsest is, why it matters, how it works | ~8K words |
| **22** | [Product Requirements](domain-synthesis/22-product-requirements.md) | 39 feature requirements + 5 NFRs + 4 user narratives | ~6K words |
| **23** | [Development Roadmap v3](domain-synthesis/23-development-roadmap-v3.md) | 5 milestones, 39 weeks, vision-gated (SUPERSEDED by doc 28) | ~4K words |
| **28** | [Development Roadmap v4](domain-synthesis/28-development-roadmap-v4.md) | 6 milestones, 49 weeks, enriched with UI redesign + genome browser research | ~8K words |
| **24** | [M1 Roadmap-PRD](domain-synthesis/24-m1-roadmap-prd.md) | Phase 1 detailed plan with acceptance criteria | ~4K words |
| **26** | [M1 Design Philosophy & Exit Criteria](domain-synthesis/26-m1-design-philosophy-exit-criteria.md) | FDD/BDD methodology, user stories, exit criteria, quality standards | ~6K words |
| **27** | [M1 Completion Implementation Plan](domain-synthesis/27-m1-completion-implementation-plan.md) | EPUB pipeline design + 41 atomized tasks across 8 phases (~96h) | ~8K words |
| — | [Master Bibliography](bibliography/master-bibliography.md) | 122+ sources organized by domain (+ dot plot + genome browser papers) | ~5K words |
| — | [Genome Browser UI Reports](UI/genome-browser-reports/00-index.md) | 8 platform analyses for UI design patterns | ~4K words |

---

## Source Material: Research Deep Reads

These documents provide the scholarly depth behind the primary chain. Consult when implementing specific features.

| Doc | Title | Domain | Key Content |
|-----|-------|--------|-------------|
| **00** | [Alignment Convergence Thesis](domain-synthesis/00-alignment-convergence-thesis.md) | Cross-domain | The isomorphism: genome ↔ protein ↔ text alignment |
| **01** | [Conceptual Framework](domain-synthesis/01-conceptual-framework.md) | Cross-domain | Structure, alignment, discovery — the deep questions |
| **03** | [Deep Read: NLP & Narrative](domain-synthesis/03-deep-read-nlp-narrative.md) | CL/NLP | GNAT, BookNLP, event chains, RQA — paper-by-paper analysis |
| **04** | [Deep Read: Genomics](domain-synthesis/04-deep-read-genomics.md) | Genomics | Hi-C, TADs, ENCODE, ChromHMM — genomic analogy foundations |
| **05** | [Deep Read: Literary Studies](domain-synthesis/05-deep-read-literary-studies.md) | DH/CL | Piper, Underwood, Moretti, Eve — book-by-book analysis |
| **06** | [Deep Read: Visualization](domain-synthesis/06-deep-read-visualization.md) | Visualization | StoryRibbons, network viz, JBrowse patterns |
| **17** | [Swinehart Deep Analysis](domain-synthesis/17-swinehart-deep-analysis.md) | Visualization | Swinehart's design principles + transferable patterns |

---

## Source Material: Annotation Architecture

These documents define how annotation works — the most architecturally load-bearing part of the system.

| Doc | Title | Focus |
|-----|-------|-------|
| **07** | [Annotation Framework](domain-synthesis/07-annotation-framework.md) | The five annotation types, coordinate systems, MAKER model |
| **08** | [CL Annotation Frameworks](domain-synthesis/08-annotation-cl-frameworks.md) | UIMA, GATE, W3C WADM, INCEpTION, standoff annotation |
| **09** | [Genome Annotation Methods](domain-synthesis/09-annotation-genome-methods.md) | MAKER, BRAKER, Prokka, ChromHMM — tool-by-tool literary mapping |
| **10** | [Annotation Visualization](domain-synthesis/10-annotation-visualization.md) | JBrowse 2 architecture, IGV, zoom strategies, Circos patterns |

---

## Planning & Review History

| Doc | Title | Status |
|-----|-------|--------|
| **00-btdb** | [Back to Drawing Board Process](domain-synthesis/00-back-to-drawing-board.md) | Master process doc for the overhaul |
| **02** | [PRD Outline](domain-synthesis/02-PRD-outline.md) | **Superseded** by doc 22. Format note added re: W3C primary. |
| **11** | [Vision Synthesis v1](domain-synthesis/11-palimpsest-vision-synthesis.md) | **Superseded** by doc 21. Still useful for Base/X detail. |
| **12** | [Roadmap v2](domain-synthesis/12-development-roadmap.md) | **Superseded** by doc 23. Tech decisions table still accurate. |
| **12a** | [Roadmap Critical Review](domain-synthesis/12a-roadmap-critical-review.md) | Review of doc 12. Findings incorporated into doc 23. |
| **12b** | [Roadmap v2 Review](domain-synthesis/12b-roadmap-v2-review.md) | Second review pass. |
| **13** | [Phase 1 Plan v1](domain-synthesis/13-phase1-plan.md) | **Superseded** by doc 14. |
| **13a** | [Phase 1 Critical Review](domain-synthesis/13a-phase1-critical-review.md) | Review of doc 13. |
| **14** | [Phase 1 Plan Revised v4.1](domain-synthesis/14-phase1-plan-revised.md) | Most detailed implementation plan. 37 task docs reference this. |
| **15** | [Performance Architecture v4](domain-synthesis/15-performance-architecture-v4.md) | **Design spec** — Tauri/Rust/WebGPU. Partially scaffolded only. |
| **16** | [Checkpoint Review M1.3b](domain-synthesis/16-checkpoint-review-m13b.md) | Adversarial review of built system. 47 findings. |
| **18** | [Stage 1 Gap Analysis](domain-synthesis/18-stage1-completion-gap-analysis.md) | Research expansion coverage assessment. |
| **20** | [Consistency Review](domain-synthesis/20-consistency-review.md) | 32 issues across all docs. Terminology canon. |
| **25** | [Persona Scoring](domain-synthesis/25-persona-scoring.md) | All 4 primary docs PASS at ≥4/5. 10 remediation items. |
| **26** | [M1 Design Philosophy & Exit Criteria](domain-synthesis/26-m1-design-philosophy-exit-criteria.md) | FDD/BDD methodology shift. 6 user stories. 24 exit criteria. Quality standards. |
| **27** | [M1 Completion Implementation Plan](domain-synthesis/27-m1-completion-implementation-plan.md) | EPUB pipeline + 41 tasks + 8 phases. Supersedes T30-T37 for final M1 sprint. |

---

## Implementation Documents

| Location | Contents |
|----------|----------|
| `domain-synthesis/phase1-tasks/` | 37 atomized task docs (T01-T37) + index + conventions + errata |
| `domain-synthesis/phase1-tasks/00-INDEX.md` | Dependency graph + linear execution order + time estimates |
| `WALKTHROUGH.md` | Hands-on guide to running the current built system |

---

## Research Corpus

| Location | Contents |
|----------|----------|
| `bibliography/master-bibliography.md` | 117 entries across 7 sections |
| `papers/alignment/` | 7 PDFs — alignment algorithms + textbooks |
| `papers/genomics/` | 31 PDFs — sequence analysis, annotation, chromatin, 3D genome |
| `papers/nlp-narrative/` | 53 PDFs — CL, NLP, narrative structure, DH, literary theory |
| `papers/visualization/` | 27 PDFs — theory, genome browsers, narrative viz |
| `reports/` | 5 research catalogs (alignment, NLP, Swinehart, annotated index, genomics) |
| `datasets/swinehart/` | IJ Infinite Digest CSVs, CYOA data, CPudney annotations |
| `download-paper.py` | Robust download script with 7-strategy fallback chain |

---

## Terminology Canon

(Definitive terms from doc 20 §4)

| Concept | Canonical Term |
|---------|---------------|
| HMM passage state classifier | **LitHMM** |
| Literary feature vocabulary | **Literary Feature Ontology (LFO)** |
| Primary annotation format | **W3C Web Annotation JSONL** |
| Computational export format | **PAF** |
| Passage-pair similarity matrix | **TextHiC** |
| Evidence integration pipeline | **MAKER evidence model** |
| Discrete passage encoding | **narrative alphabet** |
| Per-text extension system | **Palimpsest-X** |
| Universal analysis layer | **Palimpsest Base** |
| Evidence classification | **E1–E5 evidence levels** |
