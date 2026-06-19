# Palimpsest — Development Documentation

Consolidated home for all design, planning, roadmap, research, report, audit, and specification
documents. Reorganized 2026-06-19; previously these were scattered across the repo root, `docs/`,
`research/`, `specs/`, and `core/`.

## Layout

| Folder | Contents |
|---|---|
| [`audits/`](audits/) | Quality audits. **[`masking-map/`](audits/masking-map/)** — character-level masking-map coverage audit of all 20 gold-set works (one report per work + cross-work index + `METHODOLOGY.md`). **`gold-ratification-results.md`** — the prior by-eye gold-set ratification record (Phase A + the 11-work expansion + idx101 promotion). |
| [`architecture/`](architecture/) | Architecture Decision Records (ADRs) — annotation format, JBrowse2 patterns. |
| [`design/`](design/) | System design documents (`palimpsest_system_design.md`). |
| [`specs/`](specs/) | Formal specifications — annotation model, PAF export, LFO, signals. |
| [`diagrams/`](diagrams/) | Mermaid class/sequence diagrams (current + phase2 + legacy root copies). |
| [`research/`](research/) | The full research corpus — domain synthesis (28 deep-reads + roadmaps), phase-1 task specs (T01–T37), reports, bibliography, UI/design-token studies, development history. |
| [`guides/`](guides/) | Developer guides (`live-testing-guide.md`). |
| [`archive/`](archive/) | Superseded pre-research material (early PRD, implementation plans, prototype designs). |

## Entry points

- **Current masking-map state of the gold set:** [`audits/masking-map/README.md`](audits/masking-map/README.md)
- **How masking coverage is defined & measured:** [`audits/masking-map/METHODOLOGY.md`](audits/masking-map/METHODOLOGY.md)
- **Original M1 plan:** `research/domain-synthesis/26-m1-design-philosophy-exit-criteria.md`,
  `research/domain-synthesis/27-m1-completion-implementation-plan.md`
- **Phase-1 task specs:** `research/domain-synthesis/phase1-tasks/00-INDEX.md`

## Conventions

- Package-level `README.md` files (repo root, `core/`, `browser/`) stay at their package roots — they
  are not development docs and were not moved here.
- The gold contracts and their verifier scripts remain code-adjacent at
  `core/tests/fixtures/gold/`; only the human-readable *report* (`ratification-results.md`) moved here.
- Audit reports are generated, not hand-edited — regenerate with
  `.scratch/mask-eval/masking_audit.py all && .scratch/mask-eval/masking_audit.py index`.
