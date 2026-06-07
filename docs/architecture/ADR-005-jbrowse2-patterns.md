# ADR-005: JBrowse 2 Adapter/Track/Display/Renderer as Architectural Reference

**Status**: Accepted
**Date**: 2026-06-06
**Deciders**: Project lead

## Context

Palimpsest's central architectural thesis is Base/X: the Base platform computes universal feature tracks for any text, and Palimpsest-X adds per-text custom tracks without modifying Base code. This requires a browser extensibility system where new track types can be added without editing existing React components.

The research identified JBrowse 2 (a genome browser built with React + TypeScript + MobX-state-tree) as the closest architectural precedent. Research documents 09 §4.3, 10, and 11 §7 recommend adopting its patterns.

## Decision

Adopt JBrowse 2's **adapter/track/display/renderer** hierarchy as the architectural reference for Palimpsest's extensibility system. JBrowse 2 is used as a **design pattern**, not as a code dependency.

## Mapping

| JBrowse 2 Concept | Palimpsest Equivalent | Description |
|---|---|---|
| `TrackAdapter` | `TrackExtractor` (Python) | Reads source data, produces structured annotations or signals |
| `PluginManager.addTrackType()` | `TrackRegistry.register()` | Registers new track types without modifying core code |
| `Track` | JSONL file or signal binary | The computed annotation/signal data |
| `Display` | `TrackManifest` (JSON) | Rendering configuration (colors, style, view strategy) |
| `Renderer` | `TrackRendererRegistry` (TypeScript) | Maps manifest to React rendering components |

## Rationale

- JBrowse 2 solves the same extensibility problem for genomics annotations that Palimpsest solves for literary annotations
- Its plugin system has been proven at scale with dozens of third-party track types
- The adapter/track/display/renderer separation cleanly maps to Palimpsest's pipeline (extract → store → configure → render)
- React + TypeScript alignment (JBrowse 2 uses the same frontend stack)
- MIT-licensed, well-documented architecture

## Consequences

- Every track extractor implements the `TrackExtractor` protocol (Python Protocol class)
- `TrackRegistry` uses auto-discovery (via `__subclasses__()`) rather than explicit configuration
- Browser reads `manifests/*.manifest.json` for rendering configuration
- Unknown/X tracks fall back to a generic gray highlight + density barcode renderer
- Phase 2's X tracks register via the same mechanism as Base tracks but from `x-config/detectors/`
- Zustand is used for Phase 1 state management (JBrowse 2 uses MST; evaluate MST at Phase 2 start)
