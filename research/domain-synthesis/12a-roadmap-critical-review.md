# Critical Review: Palimpsest Development Roadmap v1.0

**Date**: 2026-06-06
**Purpose**: Identify gaps, glosses, over-simplifications, and departures from project aims in the v1.0 roadmap before rewriting.

---

## 1. Departures from Project Aims

### 1.1 The Roadmap Front-Loads Infrastructure, Back-Loads the Vision

The vision document's core insight is that Palimpsest is a **self-rewriting platform** where AI agents and human readers co-create analytical capabilities. But the roadmap buries this in Phase 2 (weeks 13-21) and doesn't fully realize it until Phase 4 (week 35). A reader following this roadmap for 13 weeks would build a competent but conventional NLP pipeline + text viewer — not the "self-rewriting palimpsest" promised by the vision.

**The fix**: LLM integration should not be Phase 2. It should be woven into Phase 1 from the start. The Base tracks should already use LLM services where they add value (e.g., LLM-assisted entity disambiguation, LLM-generated passage summaries). The "AI assistant" experience is the product differentiator; deferring it to Phase 2 means Phase 1 delivers a product that looks like every other DH tool.

### 1.2 Phase 0 Is a Waterfall Trap

The roadmap states "no code in this phase — only documents." This violates Principle 1 ("vertical slices over horizontal layers"). Spending 2-3 weeks on ontologies and format specs before writing any code is waterfall planning dressed up as agile. The LFO and PAF specs will be wrong in ways that only become visible when you try to use them.

**The fix**: Phase 0 should produce a *working prototype* alongside the specs. Define the LFO and PAF by building them — implement a minimal pipeline that ingests one chapter of IJ, produces PAF output, and renders it in a 100-line HTML viewer. The spec is the code + a lightweight document explaining the decisions.

### 1.3 The Roadmap Treats Alignment as Phase 3 — But the Product Is Named "Palimpsest"

The core product metaphor is about uncovering hidden layers — which is an alignment/annotation operation. But alignment doesn't appear until Phase 3 (week 21+). A user who downloads Palimpsest after Phase 1 gets a text viewer. After Phase 2, a text annotator. They don't get the *palimpsest* experience until Phase 3. That's too late for the product to establish its identity.

**The fix**: Include a lightweight intra-text alignment (self-similarity) in Phase 1, and a basic cross-text alignment (even just SBERT cosine at paragraph level) in Phase 2. The full Smith-Waterman + Gumbel significance engine can wait for Phase 3, but the *experience* of seeing two texts aligned should come earlier.

---

## 2. Gaps

### 2.1 No Testing Strategy

The roadmap specifies acceptance criteria per milestone but has no systematic testing strategy:
- No mention of unit tests, integration tests, or end-to-end tests
- No CI/CD pipeline
- No regression testing plan (critical when Base tracks must be recomputable and deterministic)
- No benchmark suite (how do you know if a code change makes the pipeline slower?)
- No testing of the active learning loop (does retraining actually improve, or does it overfit?)

### 2.2 No Data Pipeline Architecture

The roadmap describes individual tools but not how they compose into a pipeline:
- What orchestrates the sequence: ingest → normalize → segment → features → tracks?
- Is it a DAG (directed acyclic graph) with dependency tracking? A simple sequential script? A workflow engine?
- What happens when a new Base track is added — does it rerun only that track, or recompute everything?
- How are intermediate results cached? If entity detection takes 30 seconds, do you rerun it when adding a sentiment track?

### 2.3 No Error Handling / Degraded Mode

The roadmap assumes everything works. What happens when:
- BookNLP fails on a text with unusual formatting?
- The embedding model produces garbage for a non-English text?
- The LLM service is not running (user didn't start it)?
- A PDF extraction produces garbled text for a scanned document?

Each of these should have a documented degradation path: "If BookNLP fails, fall back to spaCy NER; if spaCy NER fails, mark the entities track as unavailable."

### 2.4 No Internationalization Plan

The vision document lists "sacred text (Bible, Quran)" and "oral epic (Iliad, Beowulf)" as target text types. These imply multilingual support:
- spaCy and BookNLP are English-only (or English-primary)
- Sentiment dictionaries (hedonometer, VADER) are English-only
- LFO terms are defined in English
- The roadmap doesn't address any of this

This isn't a Phase 8 problem — it's a Phase 0 data model decision. If the annotation format assumes English (e.g., using English POS tags as features), retrofitting multilingual support will be expensive.

### 2.5 No Import/Export Interoperability Plan

The roadmap mentions W3C Web Annotation export but doesn't address:
- TEI-XML import (the dominant format in digital humanities)
- Import from existing annotation tools (INCEpTION exports, Recogito exports)
- Export for publication (annotated edition as PDF, HTML, or EPUB)
- Compatibility with existing DH infrastructure (IIIF for manuscript images, Zotero for bibliographic metadata)

### 2.6 ModeHMM Training Corpus Not Specified

Milestone 5.2 says "train on 60+ texts" but doesn't specify:
- What texts? From where? In what languages?
- How are the 5-8 binarized features selected?
- What validation data exists for rhetorical mode annotation?
- How do you evaluate whether the learned states are meaningful?

This is the most technically ambitious component in the entire platform and it gets less specification than the text normalization step.

---

## 3. Over-Simplifications

### 3.1 "BookNLP Integration (1 week)"

BookNLP is a complex pipeline with known failure modes:
- It's a Java-based Python wrapper (dependency hell)
- Character name clustering has a 15% error rate on challenging texts
- Coreference resolution degrades significantly beyond ~50K tokens
- Quote attribution is ~63% accurate on implicit quotes

One week to integrate, test, handle failures, and merge output with existing PAF tracks is optimistic. This should be 2-3 weeks with explicit acceptance criteria for each sub-component.

### 3.2 "Embedding Service Indexes a 300-Page Novel in <60 Seconds"

This depends heavily on the model and hardware. Qwen3-Embedding-4B on Apple Silicon (M1 base) processing 1000 paragraphs at 2048 dim would take closer to 3-5 minutes. On M4 Max, maybe 60 seconds. The acceptance criterion should specify hardware, or state relative performance (e.g., "proportional to text length, <0.2s per paragraph").

### 3.3 "Custom Annotation Track from Schema Proposal to First Pass Takes <10 Minutes"

This conflates several steps:
1. User describes the feature (30 seconds)
2. LLM proposes a schema (5-10 seconds)
3. User reviews and modifies (2-3 minutes)
4. Detection pipeline configured (1-2 minutes)
5. Detection runs on full text (30-300 seconds depending on text size and method)
6. Results presented for review (instant)

Step 5 alone could exceed 10 minutes for a long text with LLM-based verification. The criterion should be "schema definition in <5 minutes; first-pass detection queued and running within 10 minutes; results available within 1 hour for a 300-page text."

### 3.4 Time Estimates Generally

The roadmap estimates 12-16 months for a single developer across 8 phases. But the phases include:
- A complete SvelteKit web application with linked multi-view visualization
- A Smith-Waterman alignment engine with Gumbel significance testing
- An HMM training pipeline comparable to ChromHMM
- An LLM agent orchestration framework
- A collaborative real-time annotation server

Each of these is a significant engineering project on its own. 12-16 months is realistic only if the developer has deep experience in ALL of: NLP, bioinformatics algorithms, frontend web development (SvelteKit/React + D3), ML training, and distributed systems (WebSocket sync). More realistically, this is 18-24 months for a strong full-stack developer, or 9-12 months for a 2-person team (one backend/algorithms, one frontend/visualization).

---

## 4. Structural Problems

### 4.1 Phase 4 (IJ) and Phase 6 (Correspondent) Are Too Late

The Base/X architecture is the core innovation. But it isn't tested until Phase 4 (week 35). If the X plugin architecture has a fundamental design flaw, you won't discover it until 8 months in.

**The fix**: Move a lightweight X test into Phase 2. After building the annotation UI and schema builder, immediately test it by defining one IJ-specific annotation type. This validates the extension mechanism at week 21 instead of week 35.

### 4.2 Phases 7 and 8 Are Stretch Goals, Not Core Roadmap

Collaboration (Phase 7) and advanced visualization (Phase 8) are important but not essential to the product's core value proposition. They should be explicitly labeled as stretch goals, with the core product being complete at Phase 6.

### 4.3 No "Walking Skeleton" Milestone

The roadmap doesn't identify the point at which the entire system works end-to-end, even minimally. There should be an explicit "walking skeleton" milestone — perhaps at the end of Phase 1 — where you can import a text, see Base tracks, make an annotation, and export it. This end-to-end path should work before any individual component is polished.

---

## 5. Glosses

### 5.1 "SvelteKit or React" Is Not a Decision

ADR-003 says "SvelteKit for frontend" but the roadmap still says "SvelteKit or React" in places. This needs to be resolved. The choice affects:
- State management (MobX-state-tree is React-native; Svelte has stores)
- Component libraries (JBrowse 2 is React; Recogito is React)
- Rendering strategy (Svelte's compile-time approach vs React's virtual DOM)
- Developer pool (React has 10x the community)

Given that JBrowse 2 is React/TypeScript and its architecture is explicitly the model for the text browser, React is the more pragmatic choice. Using Svelte means rewriting JBrowse patterns instead of adapting them.

### 5.2 "Qdrant for Vector Store" Is Under-Justified

Qdrant is an excellent vector store but introduces a Docker dependency for a local-first application. Alternatives:
- `sqlite-vec` — embeds in the SQLite database already used for metadata; zero additional infrastructure
- `faiss` — in-process Python library; no server needed
- `lance` / `lancedb` — embedded database with vector support

For a local-first platform where minimizing infrastructure is a priority, an embedded solution (sqlite-vec or faiss) is more appropriate than a server-based solution (Qdrant). Reserve Qdrant for multi-user/cloud deployments.

### 5.3 The Active Learning Loop Is Hand-Waved

Milestone 2.4 describes an active learning loop but doesn't specify:
- What model architecture is retrained? (You can't fine-tune a 7B LLM on 50 examples.)
- Is it a small classifier sitting on top of embeddings? A prompt-engineering update? A retrieval index?
- How is the training data stored and versioned?
- What happens when the retrained model is worse? (Regression detection, rollback)

The realistic implementation is probably: corrections update a few-shot example bank in the LLM prompt, and adjust a lightweight classifier (logistic regression on embeddings) for threshold-based detection. This should be specified explicitly.

---

## 6. Summary of Required Changes for v2.0

1. **Merge Phase 0 into Phase 1**: spec-by-building, not spec-then-build
2. **Weave LLM integration into Phase 1**: the AI assistant is the product, not a bolt-on
3. **Add lightweight alignment to Phase 1-2**: self-similarity dotplot + basic cross-text comparison
4. **Include an early X validation in Phase 2**: one custom track on IJ to test the extension mechanism
5. **Add a testing strategy section**: unit/integration/e2e/regression/benchmark
6. **Add a pipeline architecture section**: DAG, caching, partial recomputation
7. **Add an error handling section**: degradation paths for each component failure
8. **Resolve SvelteKit vs React**: commit to React given JBrowse 2 dependency
9. **Replace Qdrant with embedded vector store**: sqlite-vec or faiss for local-first
10. **Specify the active learning mechanism**: it's prompt few-shot + embedding classifier, not fine-tuning
11. **Specify the ModeHMM training corpus**: 60 Project Gutenberg texts, selected how, validated how
12. **Label Phases 7-8 as stretch goals**
13. **Add a "walking skeleton" milestone** at end of Phase 1
14. **Adjust time estimates upward**: 18-24 months solo, 9-12 months for a 2-person team
15. **Add internationalization decision to Phase 0**: at minimum, ensure data model doesn't assume English
