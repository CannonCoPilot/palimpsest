#!/usr/bin/env python3
"""Phase 1 · P1.3 — multi-source consensus calling (assemble).

Reads every per-source aligned read set (`reads/*.json` from detect_sources.py + the
standalone archaic detectors), groups reads by skeleton coordinate, folds each surface
to a spelling/glyph-neutral lemma (§6.1 model, via the shared ocr_sample.skel fold),
and calls an INDEPENDENCE-WEIGHTED consensus per element with a retained variant
pileup.

Non-circular (plan §4.3): the consensus token set is a *majority vote* across witnesses;
agreement is then measured against that call, but every per-source reading is retained
in `variant_pileup` and never silently dropped — the consensus never defines the truth
it is measured against. Witnesses are weighted by *lineage independence*, not raw count:
the modern-Madueke family (madueke_a/_b + Madueke-derived sabates_a) is ONE independent
axis; odr-com, s-dismas, and our majority-consensus OCR are each independent. The
confidence tier keys off independent-axis depth × post-normalization agreement.

Consensus surfaces are stored neutrally (folded lemma) with BOTH a modern surface (from
a modern witness) and an archaic surface (from an archaic witness) attached, enabling the
deterministic modern/archaic rendering in Phase 2.

Bulky per-book consensus goes to scratch (regenerable); a compact, TRACKED
`consensus-summary.json` (coverage + tier/agreement/depth distributions) is emitted for
review + CI, mirroring reads-coverage.json.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASK_ENGINE = HERE.parent
sys.path.insert(0, str(MASK_ENGINE))
sys.path.insert(0, str(MASK_ENGINE / "originaldr_validation"))
import gen_dr_original as gen  # type: ignore[import]  # noqa: E402
from ocr_sample import skel, raw_words  # type: ignore[import]  # noqa: E402

READS_DIR = gen.REPO / "core/.scratch/originaldr-project/reconstruction/reads"
CONSENSUS_DIR = gen.REPO / "core/.scratch/originaldr-project/reconstruction/consensus"
SUMMARY = HERE / "consensus-summary.json"

# Lineage independence (§4.3): sources sharing a lineage collapse to one independent axis.
LINEAGE = {
    "madueke_a": "modern-madueke", "madueke_b": "modern-madueke", "sabates_a": "modern-madueke",
    "odr_com": "odr-com", "s_dismas": "s-dismas", "ocr_consensus": "our-ocr",
}
# Which surface form each source contributes.
SPELLING = {
    "madueke_a": "modern", "madueke_b": "modern", "sabates_a": "modern",
    "odr_com": "archaic", "s_dismas": "archaic", "ocr_consensus": "archaic",
}
# Preference order when picking a representative surface per spelling class.
MODERN_PREF = ["madueke_a", "sabates_a", "madueke_b"]
ARCHAIC_PREF = ["s_dismas", "odr_com", "ocr_consensus"]


def fold_tokens(text: str) -> list[str]:
    return [s for s in (skel(w) for w in raw_words(text)) if len(s) >= 2]


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def confidence_tier(indep_depth: int, agreement: float) -> str:
    """Independence-weighted tier. Independent-axis depth dominates; agreement modulates.
    - high:     >=3 independent axes agreeing well, or 2 axes in near-perfect agreement
    - moderate: 2 independent axes, or >=3 with weaker agreement
    - low:      a single independent axis (uncorroborated) — reported, not trusted
    """
    if indep_depth >= 3 and agreement >= 0.67:
        return "high"
    if indep_depth >= 2 and agreement >= 0.85:
        return "high"
    if indep_depth >= 2:
        return "moderate"
    return "low"


def call_element(skid: str, reads_by_source: dict[str, dict]) -> dict:
    """Assemble one skeleton element from all sources that attest it."""
    attest = []
    folded: dict[str, set[str]] = {}   # source -> set(folded tokens)
    for src, rd in reads_by_source.items():
        surf = rd.get("surface", "")
        toks = fold_tokens(surf)
        folded[src] = set(toks)
        attest.append({
            "source": src, "present": True,
            "spelling": SPELLING.get(src, rd.get("spelling", "?")),
            "surface": surf, "locus": rd.get("locus", ""),
            "method": rd.get("method", ""), "local_confidence": rd.get("local_confidence", ""),
            "evidence_ptr": rd.get("evidence_ptr", ""),
        })

    # Majority-vote consensus token set (a token is in the consensus if it appears in
    # >= half of the attesting sources). Single-witness elements take that witness's tokens.
    n = len(folded)
    tally: Counter[str] = Counter()
    for toks in folded.values():
        tally.update(toks)
    threshold = math.ceil(n / 2)
    consensus_tokens: set[str] = {t for t, c in tally.items() if c >= threshold}
    if not consensus_tokens:                 # high-divergence element: no token hit the majority
        for toks in folded.values():
            consensus_tokens |= toks

    # post-normalization agreement = mean Jaccard(source tokens, consensus tokens)
    if consensus_tokens:
        agreement = sum(jaccard(toks, consensus_tokens) for toks in folded.values()) / max(1, n)
    else:
        agreement = 0.0

    lineages: set[str] = {LINEAGE[s] if s in LINEAGE else s for s in folded}
    indep_depth = len(lineages)

    # representative surfaces for deterministic rendering
    def pick(pref: list[str]) -> str:
        for s in pref:
            if s in reads_by_source:
                return reads_by_source[s].get("surface", "")
        return ""
    surface_modern = pick(MODERN_PREF)
    surface_archaic = pick(ARCHAIC_PREF)

    # variant pileup: sources whose folded tokens diverge from the consensus
    pileup = [{"source": s, "surface": reads_by_source[s].get("surface", ""),
               "jaccard": round(jaccard(folded[s], consensus_tokens), 3)}
              for s in folded if jaccard(folded[s], consensus_tokens) < 0.999]

    return {
        "id": skid,
        "type": "scripture-verse",
        "attestation": attest,
        "consensus": {
            "lemma_neutral": " ".join(sorted(consensus_tokens)),
            "agreement": round(agreement, 4),
            "support_depth": n,
            "independent_depth": indep_depth,
            "independent_lineages": sorted(lineages),
            "confidence_tier": confidence_tier(indep_depth, agreement),
            "variant_pileup": pileup,
        },
        "render": {"modern_form": surface_modern, "archaic_form": surface_archaic},
    }


def load_reads() -> dict[str, dict[str, dict]]:
    """source_name -> {skeleton_id: read record}."""
    out: dict[str, dict[str, dict]] = {}
    for p in sorted(READS_DIR.glob("*.json")):
        src = p.stem
        blob = json.loads(p.read_text())
        recs = blob if isinstance(blob, list) else blob.get("reads", [])
        # First-wins on a repeated skeleton id: deterministic, and consistent with the generator +
        # detectors, which keep the first (canonical) occurrence of a duplicated verse number.
        d: dict[str, dict] = {}
        for r in recs:
            sid = r.get("skeleton_id", "")
            if sid.startswith("scripture/") and sid not in d:
                d[sid] = r
        out[src] = d
    return out


def main() -> int:
    CONSENSUS_DIR.mkdir(parents=True, exist_ok=True)
    reads = load_reads()
    sources = sorted(reads)
    # union of all attested scripture skeleton ids
    all_ids: set[str] = set()
    for m in reads.values():
        all_ids.update(m)

    per_book: dict[str, list[dict]] = defaultdict(list)
    tier_counts: Counter[str] = Counter()
    depth_counts: Counter[int] = Counter()
    agr_sum = 0.0
    for skid in all_ids:
        rbs = {src: reads[src][skid] for src in sources if skid in reads[src]}
        el = call_element(skid, rbs)
        book = skid.split("/")[1]
        per_book[book].append(el)
        tier_counts[el["consensus"]["confidence_tier"]] += 1
        depth_counts[el["consensus"]["independent_depth"]] += 1
        agr_sum += el["consensus"]["agreement"]

    for book, els in per_book.items():
        els.sort(key=lambda e: [int(x) if x.isdigit() else x for x in e["id"].split("/")[1:]])
        (CONSENSUS_DIR / f"{book}.json").write_text(
            json.dumps({"book": book, "elements": els}, ensure_ascii=False))

    total = len(all_ids)
    summary = {
        "sources": sources,
        "lineages_present": sorted({LINEAGE.get(s, s) for s in sources}),
        "elements": total,
        "books": len(per_book),
        "confidence_tiers": dict(tier_counts),
        "independent_depth_hist": {str(k): v for k, v in sorted(depth_counts.items())},
        "mean_agreement": round(agr_sum / max(1, total), 4),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"consensus: {total} elements · {len(per_book)} books · sources={sources}")
    print(f"  tiers={dict(tier_counts)}  indep_depth={dict(sorted(depth_counts.items()))}"
          f"  mean_agreement={summary['mean_agreement']}")
    print(f"  per-book → {CONSENSUS_DIR}  ·  summary → {SUMMARY.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
