# Genome Browser UI Research Reports

**Date**: 2026-06-10
**Purpose**: Design pattern extraction from genome browsers to inform Palimpsest UI redesign

## Reports

1. [JBrowse 2](./01-jbrowse2.md) — React/TypeScript, plugin architecture, 8 view types, dotplot, session sharing
2. [NCBI GDV + MCGV](./02-ncbi.md) — Dual-search, color-by dropdown, zoom gating, floating action cards
3. [GIVE](./03-give.md) — Web Components embedding, track groups, arc overlays
4. [IGB](./04-igb.md) — Zoom stripe, Color by, threshold slider, animated semantic zoom
5. [IGV](./05-igv.md) — Data tiling, pluggable renderers, 3-layer architecture, igv.js embeddable
6. [Hutton Tools](./06-hutton.md) — Tablet minimap, Flapjack genotype matrix, Strudel synteny ribbons
7. [Artemis](./07-artemis.md) — Suite decomposition, six-frame display, circular maps
8. [Dot Plot Tools](./08-dotplot-tools.md) — ModDotPlot, D-GENIES, Dotplotic, ComplexHeatmap

## Tools Evaluated

- **designlang** (v12.16.0) — Playwright-based design extraction MCP/CLI. Installed at `.scratch/design-extract/`. Use: `node .scratch/design-extract/bin/design-extract.js <url> -o <outdir>`
- **website-design-systems-mcp** — Evaluated and rejected (static HTTP fetch only, fails on JS-heavy SPAs)

## Extracted Design Tokens

- UCSC Genome Browser: `UI/design-tokens/ucsc/` (30+ files)
