#!/usr/bin/env python
"""Gold masking-map completion for work idx 19 — The Correspondent (Virginia Evans, 2025).

Epistolary novel. The body is tiled by LETTERS delimited by salutations. The gold's 102
count was a PROXY LOWER BOUND from line-start 'Dear X,' salutations only. This script
resolves the TRUE letter count by detecting the full salutation pattern (Dear-forms AND
name-forms) with a signoff discriminator, and tiles every letter so the body is covered.

Monkeypatch only — does NOT edit the shared engines.

True count resolution (evidence printed below):
  * greeting-prefix salutations (Dear/Dearest/Hello/Hi/Greetings/Good morning/To[:]/My dear),
    line-start, comma-terminated, standalone paragraph   -> 115
  * bare-NAME salutations (Felix,/Syb,/Sybil,/Basam,) followed by a substantial (>80c) body
    [excludes signoffs like 'Your neighbor,'/'Fondly,'/'Regards,' which precede a short
     signature paragraph]                                 -> 9
  -> 124 letters total (old gold proxy 102 -> resolved 124)
"""
import re
import sys

import instance_edges  # noqa: E402
import masking_map  # noqa: E402

# ── salutation detector (the TRUE letter delimiter) ──────────────────────────────
_SAL_PARA = re.compile(r"(?m)^([A-Z][^\n]{0,60}?,)\n\n")
_GREETING = re.compile(
    r"^(Dear |Dearest |Hello|Hi |Greetings|Good morning|Good day|To:? |My dear )", re.I
)
_SIGNOFF_KW = re.compile(
    r"\b(regards|love|sincerely|yours|neighbou?r|friend|sister|best|wishes|"
    r"response|writing|xoxo|fondly)\b",
    re.I,
)
# 'Felix, my dear brother,' is a salutation though it contains 'brother'; whitelist it.
_BARE_WHITELIST = {"Felix, my dear brother,"}


def _is_bare_name_salutation(line: str) -> bool:
    if line in _BARE_WHITELIST:
        return True
    inner = line[:-1]  # strip trailing comma
    if _SIGNOFF_KW.search(inner):
        return False
    words = inner.replace(",", " ").split()
    return 1 <= len(words) <= 2 and all(w[0].isupper() for w in words if w)


def _salutation_starts(text: str) -> list[int]:
    starts: list[int] = []
    for m in _SAL_PARA.finditer(text):
        line = m.group(1)
        body = text[m.end() : m.end() + 400].split("\n\n")[0]
        if _GREETING.match(line):
            starts.append(m.start())  # greeting form: a salutation regardless of body length
        elif _is_bare_name_salutation(line) and len(body) > 80:
            starts.append(m.start())  # bare-name form: salutation only if a real body follows
    # The first letter opens with a recipient ADDRESS+DATE header block before the salutation
    # ('Felix Stone\n\n7 Rue de la Papillon\n\n...\n\nJune 2, 2012\n\n'). Anchor the first
    # letter at that header so the preface ends cleanly at the header, not mid-letter.
    hdr = text.find("Felix Stone\n\n7 Rue")
    if hdr >= 0 and starts and starts[0] > hdr:
        starts[0] = hdr
    return sorted(set(starts))


# ── monkeypatch materialize to understand a "salutation" rule kind ───────────────
_orig_materialize = instance_edges.materialize


def _materialize(text, rule):
    if rule.get("kind") == "salutation":
        return _salutation_starts(text)
    return _orig_materialize(text, rule)


instance_edges.materialize = _materialize
masking_map.materialize = _materialize  # build_elements imported it by name

# ── RULES: the 124-letter tiling (specific layer over the body) ──────────────────
instance_edges.RULES[19] = [
    {
        "type": "letter",
        "kind": "salutation",
        "expected_count": 124,  # old gold 102 (Dear-only proxy) -> resolved 124 (Dear + name forms)
    }
]

# ── SUPPLEMENT: front matter + back matter (preface is the only narrative non-letter) ──
masking_map.SUPPLEMENT[19] = [
    # FRONT MATTER (granular, correctly typed)
    {"type": "copyright", "start_anchor": "<<BOF>>",
     "end_anchor": "Contents\n\nDedication\n\nEpigraph"},
    {"type": "contents", "start_anchor": "Contents\n\nDedication\n\nEpigraph",
     "end_anchor": "_150929195_\n\nTo Mark, with love"},
    {"type": "dedication", "start_anchor": "_150929195_\n\nTo Mark, with love",
     "end_anchor": "What I have made for myself is personal, but is not exactly peace…."},
    {"type": "epigraph",
     "start_anchor": "What I have made for myself is personal, but is not exactly peace….",
     "end_anchor": "A Preface\n\nAt last, on Monday"},
    {"type": "preface", "start_anchor": "A Preface\n\nAt last, on Monday",
     "end_anchor": "Felix Stone\n\n7 Rue de la Papillon\n\n84220 Gordes\n\nFRANCE\n\n"
                   "June 2, 2012\n\nFelix, my dear brother"},
    # (letters [Felix Stone header .. Acknowledgments) tiled by the RULE above)
    # BACK MATTER
    {"type": "acknowledgments", "start_anchor": "Acknowledgments\n\nWhen I was still in early draft",
     "end_anchor": "The Correspondent\n\nVirginia Evans\n\nDiscussion Questions"},
    {"type": "discussion", "start_anchor": "The Correspondent\n\nVirginia Evans\n\nDiscussion Questions",
     "end_anchor": "About the Author\n\nVirginia Evans is from"},
    {"type": "about_author", "start_anchor": "About the Author\n\nVirginia Evans is from",
     "end_anchor": "<<EOF>>"},
]

# ── audit ────────────────────────────────────────────────────────────────────────
a = masking_map.audit(19)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("n_elements:", a["n_elements"], " text_len:", a["text_len"])
for r in a["sparse_regions"][:12]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:70]))

# letter-count gate
text = masking_map.project_for(19).reference_text()
starts = _salutation_starts(text)
print("\nLETTER COUNT GATE: materialized", len(starts), "expected 124 ->",
      "GREEN" if len(starts) == 124 else "RED")
print("first 3 letter starts:", starts[:3], " last 3:", starts[-3:])
