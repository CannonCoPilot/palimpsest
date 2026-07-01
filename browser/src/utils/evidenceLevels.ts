// Canonical E1–E5 evidence hierarchy (research doc 07 §4.1, "annotation framework").
// One source of truth so every surface — annotation DetailPanel, analysis-track table —
// glosses a level identically instead of drifting into contradictory labels.
export const EVIDENCE_DESCRIPTIONS: Record<string, string> = {
  E1: 'Explicit in text',
  E2: 'Human annotator',
  E3: 'Cross-text homology',
  E4: 'ML prediction',
  E5: 'Rule-based/statistical',
};
