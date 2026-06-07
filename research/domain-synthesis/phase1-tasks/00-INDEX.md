# Phase 1 Task Index

**Total tasks**: 37
**Total estimated effort**: ~200 hours (~10 weeks at 4h/day productive coding)
**Reference plan**: `14-phase1-plan-revised.md` (v3.0)

---

## Dependency Graph

```
T01 ─────────────────────────────────────────────────────────────────┐
T02 ─────────────────────────────────────────────────────────────────┤
T03 ──┬──────────────────────────────────────────────────────────────┤
T04 ──┤                                                             │
      ├── T05 ──┬── T06 ── T07 ── T08 ─────────── T10 ─────────────┤ M1.1
      │         │                                   ↑               │
      │         │         T09 ──────────────────────┘               │
      │         │                                                   │
      ├── T11 ──┤                                                   │
      ├── T12 ──┤                                                   │
      ├── T13 ──┼── T15 ── T16 ── T17 ─────────────────────────────┤ M1.2
      ├── T14 ──┤          │                                        │
      │         │          └── T18 ── T19 ── T20 ───────────────────┤
      │         │                                                   │
      │         ├── T21 ── T22                                      │
      │         │    └──── T23                                      │ M1.3a
      │         ├── T24                                             │
      │         └── T25 (depends on T11,T12,T14,T24)                │
      │                                                             │
      │         T26 (depends on T07,T13)                            │ M1.3b
      │         T27 (depends on T23,T09)                            │
      │         T28 (depends on T27,T19)                            │
      │         T29 ───────────────────────────────────────────────┤
      │                                                             │
      │         T30 (depends on T09)                                │
      │         T31 (depends on T30)                                │ M1.4
      │         T32 (depends on T24,T25,T14)                        │
      │         T33 (depends on T19,T18)                            │
      │         T34 (depends on T10,T27,T21)                        │
      │         T35 (depends on T03,T11-T14)                        │
      │         T36 ────────────────────────────────────────────────┤
      │         T37 ────────────────────────────────────────────────┘
```

## Implementation Order (Linear)

Execute tasks in this order for clean sequential implementation. Tasks within the same milestone can be parallelized where dependencies allow, but this linear ordering is always safe.

### Milestone 1.1 — Foundation (Week 1-2)

| Task | Title | Est. | Day |
|---|---|---|---|
| T01 | Project Scaffolding + Code Quality Tooling | 6h | 1 |
| T02 | Test Fixtures + Public Domain Texts | 3h | 2 |
| T03 | W3C Annotation Model + Body Types + JSONL Serializer | 6h | 2 |
| T04 | TrackExtractor Protocol + TrackRegistry | 4h | 2 |
| T05 | Ingestion Pipeline (Extractor + Normalizer + Segmenter) | 6h | 3 |
| T06 | Project Directory Manager + Metadata Schema | 4h | 3 |
| T07 | Entity Track Extractor + Signal I/O | 5h | 4 |
| T08 | CLI (ingest, info, analyze) + Pipeline Provenance | 4h | 5 |
| T09 | Browser Scaffolding (React + Zustand + Layout) | 8h | 6-7 |
| T10 | Annotation Overlay + Detail Panel + Keyboard + Server | 8h | 8-10 |

### Milestone 1.2 — Five Tracks + AI Summary (Week 3-5)

| Task | Title | Est. | Day |
|---|---|---|---|
| T11 | Sentiment Track | 4h | 11 |
| T12 | Lexical Track | 3h | 12 |
| T13 | Dialogue Track | 5h | 13 |
| T14 | Topics Track + Distribution Signal | 5h | 14 |
| T15 | Registry-Driven Pipeline Orchestration + CLI Progress | 4h | 15 |
| T16 | Ollama Service Manager + Clients | 4h | 16-17 |
| T17 | LLM Summarizer (API + Browser) | 4h | 18 |
| T18 | Text Search (Browser) | 5h | 19 |
| T19 | TrackPanel + OverviewBar + LoadingOverlay | 7h | 20-22 |
| T20 | Milestone 1.2 Testing + Smoke Test | 6h | 23-25 |

### Milestone 1.3a — Signals + Embeddings (Week 5-7)

| Task | Title | Est. | Day |
|---|---|---|---|
| T21 | VectorStore Protocol + SqliteVecStore + Embedding Pipeline | 6h | 26-27 |
| T22 | Similarity Search API Endpoint | 3h | 27 |
| T23 | Self-Similarity Matrix Track | 4h | 28-29 |
| T24 | Narrative Arc + RQA Tracks | 5h | 30-31 |
| T25 | Alphabet Track (K-means Placeholder) | 3h | 31 |

### Milestone 1.3b — BookNLP + DotplotView (Week 7-8)

| Task | Title | Est. | Day |
|---|---|---|---|
| T26 | BookNLP Integration | 5h | 32-33 |
| T27 | DotplotView (Canvas Renderer + Interaction) | 8h | 34-36 |
| T28 | Linked Views (Zustand Selection State) | 4h | 37 |
| T29 | Milestone 1.3 Smoke Test | 3h | 37 |

### Milestone 1.4 — Full Browser + Export (Week 8-10)

| Task | Title | Est. | Day |
|---|---|---|---|
| T30 | Virtualized Scrolling | 8h | 38-40 |
| T31 | Semantic Zoom | 5h | 41-42 |
| T32 | Signal Visualizations | 6h | 43-44 |
| T33 | OverviewBar Enhancements | 4h | 45 |
| T34 | Multi-Project Serving + Cross-Text Dotplot | 8h | 46-47 |
| T35 | Export (W3C + PAF + CSV) | 6h | 48 |
| T36 | Final Documentation + Specs | 5h | 49 |
| T37 | Phase 1 Regression Tests + Exit Smoke Test | 5h | 50 |

## Cross-Cutting Conventions

See `00-CONVENTIONS.md` for naming standards, dependency resolution rules, and known errata.

## Errata

See `00-ERRATA.md` for the full list of reviewed issues with fixes.
