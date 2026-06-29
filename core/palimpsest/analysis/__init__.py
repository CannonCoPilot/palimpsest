"""palimpsest.analysis — descriptive text analytics + substrate integrity checks (Wave-0 P4).

Leaf modules with no dependency on the track system, so the track system and the server can both
import them without a cycle:

  * ``textstats``  — deterministic descriptive/distributional statistics (FR-8).
  * ``integrity``  — runs the existing substrate contract validators and reports pass/violation (FR-9).

Everything here is descriptive-of-this-text (NFR-7): no reference corpus, no inferential claim.
"""
