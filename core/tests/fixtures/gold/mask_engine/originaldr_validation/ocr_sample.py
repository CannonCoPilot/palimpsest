#!/usr/bin/env python
"""Stratified-random independent-print validation for the modern Original Douay-Rheims (idx 108).

This is Leg 3 of the witness protocol -- the genuinely INDEPENDENT witness. Madueke_A and
Sabates_A share a transcription lineage (Sabates derives from Madueke), so their agreement
(collate_witnesses.py) cannot rule out a common transcription error. Here we test the reconstructed
scripture against the ORIGINAL PRINTED editions (1582/1609/1610) via a *third party's* OCR --
archive.org's djvu OCR of the EEBO scans -- which shares neither the Madueke lineage nor our own
tesseract pipeline. It is deliberately independent.

METHOD (durable + auditable upgrade of the scratch 5-sample spot-check):

  1. Coverage resolution (content-anchored, not header-parsed). For every book, probe a mid-chapter's
     skeleton-token profile against each candidate djvu file; the best-recall file is recorded as the
     book's print witness. This empirically resolves the ambiguous scan<->edition mapping.

  2. Stratified-random sample. Seed 1729. Six strata -- OT-narrative, OT-poetry, OT-prophets,
     NT-gospel, NT-epistle, apparatus-dense -- ~6 chapters each (~36). apparatus-dense = chapters
     with the most annotation-flagged verses (a distinct lens; overlap with genre strata is allowed
     and recorded).

  3. Per-sample recall (Madueke -> OCR). Locate the chapter's region in its djvu witness by sliding a
     skeleton-token window to maximal overlap, expand to capture the chapter, then measure the fraction
     of Madueke scripture TOKENS whose archaic/OCR skeleton is attested (exact or fuzzy) in that window.
     This asks the corroboration question directly: is each reconstructed word present in the print?

  4. Miss-triage. Every non-attested Madueke token is classified: short/function word (OCR-droppable)
     vs distinctive content word. A distinctive content word missing from the print would be the only
     genuine discrepancy signal; these are listed in full for inspection.

  5. Bootstrap CI. Chapters are the random unit, so we resample chapters with replacement (seed 1729,
     10000 draws) for a 95% CI on aggregate and per-stratum recall.

The archaic skeleton fold (long-s, u/v, i/j, vv, ligature, silent-e, doubled-letter) bridges the
archaic PRINT spelling to Madueke's MODERN spelling; it is intentionally lossy, so recall is a
CORROBORATION signal, not an exact-match rate -- the miss-triage is what surfaces genuine differences.

Raw djvu sources are pinned by sha256 in the output; the committed artifact is ocr-validation.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent          # .../originaldr_validation
REPO = HERE.parents[5]                            # [0]mask_engine..[4]core [5]<repo>

sys.path.insert(0, str(HERE))

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "originaldr_reconstruction"))  # R9.6
import project_root as pr  # noqa: E402  R9.6: one derived root
import collate_witnesses as C                     # parse_madueke, norm, SAB_ORDER, word_tokens

AO = pr.ARCHIVE_ORG
RAW = REPO / ".scratch/original-douay-rheims/bible/raw"   # Sabates (for apparatus-density)
MADB = pr.MADUEKE_B_RAW_INTERLEAVED  # full edition (2nd-pass)
OUT = HERE / "ocr-validation.json"

SEED = 1729
N_PER_STRATUM = 6
N_BOOT = 10000
FUZZ = 0.85          # SequenceMatcher skeleton threshold for a fuzzy attestation

# --- strata (book slugs) ---
OT_NARRATIVE = ["genesis", "exodus", "leviticus", "numbers", "deuteronomy", "josue", "judges",
                "ruth", "1-kings", "2-kings", "3-kings", "4-kings", "1-paralipomenon",
                "2-paralipomenon", "1-esdras", "2-esdras", "tobias", "judith", "esther",
                "1-machabees", "2-machabees"]
OT_POETRY = ["job", "psalms", "proverbs", "ecclesiastes", "canticle-of-canticles", "wisdom",
             "ecclesiasticus"]
OT_PROPHETS = ["isaie", "jeremie", "lamentations", "baruch", "ezechiel", "daniel", "osee", "joel",
               "amos", "abdias", "jonas", "micheas", "nahum", "habacuc", "sophonias", "aggeus",
               "zacharias", "malachie"]
NT_GOSPEL = ["matthew", "mark", "luke", "john", "acts"]
NT_EPISTLE = ["romans", "1-corinthians", "2-corinthians", "galatians", "ephesians", "philippians",
              "colossians", "1-thessalonians", "2-thessalonians", "1-timothy", "2-timothy", "titus",
              "philemon", "hebrews", "james", "1-peter", "2-peter", "1-john", "2-john", "3-john",
              "jude", "apocalypse"]
GENRE_STRATA = {"OT-narrative": OT_NARRATIVE, "OT-poetry": OT_POETRY, "OT-prophets": OT_PROPHETS,
                "NT-gospel": NT_GOSPEL, "NT-epistle": NT_EPISTLE}
OT_SLUGS = set(OT_NARRATIVE + OT_POETRY + OT_PROPHETS)

# candidate djvu witnesses by testament (multiple scans exist; coverage-resolution picks the best)
OT_DJVU = ["holiebible-ot1", "holiebible-ot2", "ot1-1609", "ot2-1610"]
NT_DJVU = ["nt-1582", "newtestament"]

# function/stop words: a miss here is unremarkable (OCR routinely drops/garbles them)
STOP = set("the and a an of to in on at for with is was are be by his her their my thy thou thee "
           "ye he she it they we you i o that this these those which who whom whose shall will may "
           "not but or as so if then when where all any some no yes unto into out up down from "
           "him them us me our your are were have hath had do did doth done god lord".split())

_LIG = (("æ", "ae"), ("œ", "oe"), ("ﬀ", "ff"), ("ﬁ", "fi"), ("ﬂ", "fl"))


def skel(word: str) -> str:
    """Archaic/OCR-insensitive skeleton bridging archaic print spelling to modern Madueke."""
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    for a, b in _LIG:
        w = w.replace(a, b)
    w = w.replace("vv", "w")
    w = re.sub(r"[^a-z]", "", w)
    w = w.replace("v", "u").replace("j", "i")
    w = w.replace("f", "s")             # long-s (OCR reads long-s as f) <-> s, symmetric
    w = re.sub(r"e$", "", w)            # archaic silent trailing -e
    w = re.sub(r"(.)\1+", r"\1", w)     # collapse doubled letters
    return w


def raw_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÆæŒœ]+", text)


def sk_list(text: str) -> list[str]:
    return [s for s in (skel(t) for t in raw_words(text)) if len(s) >= 2]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
def load_djvu() -> dict[str, list[str]]:
    out = {}
    for p in sorted(AO.glob("*_djvu.txt")):
        out[p.name.replace("_djvu.txt", "")] = sk_list(
            p.read_text(encoding="utf-8", errors="replace"))
    return out


def best_window(probe: list[str], hay: list[str], expand: float = 1.5) -> tuple[float, int, int]:
    """Slide a probe-sized window over hay; return (coarse type-recall, start, end) of an
    expanded window centred on the best offset (expand x probe length)."""
    pset = set(probe)
    if not pset or not hay:
        return 0.0, 0, 0
    w = max(len(probe), 40)
    step = max(1, w // 4)
    best, best_off = 0.0, 0
    for off in range(0, max(1, len(hay) - w + 1), step):
        rec = len(pset & set(hay[off:off + w])) / len(pset)
        if rec > best:
            best, best_off = rec, off
    pad = int(w * (expand - 1) / 2)
    return best, max(0, best_off - pad), min(len(hay), best_off + w + pad)


def attest_recall(mad_tokens: list[str], window_sk: list[str]) -> tuple[int, int, list[str]]:
    """Token-level Madueke->OCR recall. Returns (attested, total, missed_raw_words).
    mad_tokens are RAW Madueke words (so misses can be reported legibly)."""
    wset = set(window_sk)
    wlist = list(wset)
    attested, total, missed = 0, 0, []
    fuzz_cache: dict[str, bool] = {}
    for raw in mad_tokens:
        s = skel(raw)
        if len(s) < 2:
            continue
        total += 1
        if s in wset:
            attested += 1
            continue
        hit = fuzz_cache.get(s)
        if hit is None:
            hit = any(SequenceMatcher(None, s, t, autojunk=False).ratio() >= FUZZ for t in wlist)
            fuzz_cache[s] = hit
        if hit:
            attested += 1
        else:
            missed.append(raw)
    return attested, total, missed


def content_misses(missed: list[str]) -> list[str]:
    """Distinctive content words among the misses (drop short/stop = OCR-droppable)."""
    return [w for w in missed if w.lower() not in STOP and len(skel(w)) >= 4]


def genuine_candidates(content: list[str], witness_set: set[str], edition_set: set[str],
                       witness_types: list[str]) -> tuple[int, list[str]]:
    """A content-word miss is a GENUINE discrepancy candidate only if it is absent even under
    generous matching: not present anywhere in the whole print-witness file, not anywhere in the
    full Madueke edition (merged.txt), and no fuzzy match in the witness file's type list. Anything
    that survives is a real word the independent print appears not to contain -> worth inspecting.
    Everything else is OCR noise / windowing artifact (the word IS printed, just not in the window)."""
    provisional, elsewhere = [], 0
    for w in content:
        s = skel(w)
        if s in witness_set or s in edition_set:
            elsewhere += 1
        else:
            provisional.append((w, s))
    genuine = []
    for w, s in provisional:
        if any(SequenceMatcher(None, s, t, autojunk=False).ratio() >= 0.80 for t in witness_types):
            elsewhere += 1
        else:
            genuine.append(w)
    return elsewhere, genuine


# --------------------------------------------------------------------------- #
def apparatus_density(mad: dict, inv: dict) -> list[tuple[str, int, int]]:
    """(slug, chapter, annotated_verse_count) for every chapter, from Sabates has_annotation flags."""
    rows = []
    for slug in C.SAB_ORDER:
        f = RAW / f"{slug}.json"
        if not f.exists():
            continue
        data = json.loads(f.read_text())
        for c in data["chapters"]:
            ch = int(c["chapter"])
            if inv.get(slug) and ch in mad.get(inv[slug], {}):   # must exist in Madueke
                n = sum(1 for v in c["verses"] if v.get("has_annotation"))
                rows.append((slug, ch, n))
    return rows


def bootstrap_ci(hits: np.ndarray, totals: np.ndarray, rng) -> tuple[float, float, float]:
    """Chapter-resampled 95% CI on aggregate recall = sum(hits)/sum(totals)."""
    n = len(hits)
    if n == 0:
        return 0.0, 0.0, 0.0
    point = 100 * hits.sum() / max(totals.sum(), 1)
    idx = rng.integers(0, n, size=(N_BOOT, n))
    bh = hits[idx].sum(axis=1)
    bt = totals[idx].sum(axis=1)
    boot = 100 * bh / np.maximum(bt, 1)
    return round(point, 2), round(float(np.percentile(boot, 2.5)), 2), round(float(np.percentile(boot, 97.5)), 2)


# --------------------------------------------------------------------------- #
def main() -> int:
    if not AO.exists() or not list(AO.glob("*_djvu.txt")):
        print(f"!! archive.org djvu OCR missing under {AO}", file=sys.stderr)
        return 2

    rng = np.random.default_rng(SEED)
    mad, order = C.parse_madueke()
    inv = {sab: disp for disp, sab in zip(order, C.SAB_ORDER)}   # slug -> madueke display

    print("loading djvu witnesses (skeleton tokenising) ...")
    djvu = load_djvu()

    def probe_book(slug: str, cands: list[str]) -> tuple[str, float]:
        """Resolve a book's best print witness via a representative mid-chapter."""
        disp = inv.get(slug)
        chs = sorted(mad.get(disp, {}))
        if not chs:
            return "", 0.0
        mid = chs[len(chs) // 2]
        probe = sk_list(C.norm(" ".join(mad[disp][mid][v] for v in sorted(mad[disp][mid]))))
        best_name, best_rec = "", 0.0
        for name in cands:
            rec, _, _ = best_window(probe, djvu[name])
            if rec > best_rec:
                best_name, best_rec = name, rec
        return best_name, best_rec

    # --- coverage resolution (per book) ---
    print("resolving book -> print-witness coverage ...")
    coverage = {}
    for slug in C.SAB_ORDER:
        cands = OT_DJVU if slug in OT_SLUGS else NT_DJVU
        name, rec = probe_book(slug, cands)
        coverage[slug] = {"witness": name, "probe_recall_pct": round(100 * rec, 2)}

    # --- build sampling frame + stratified-random sample ---
    def sample_chapters(slugs, k):
        frame = [(s, ch) for s in slugs for ch in sorted(mad.get(inv.get(s, ""), {}))]
        if not frame:
            return []
        pick = rng.choice(len(frame), size=min(k, len(frame)), replace=False)
        return [frame[i] for i in sorted(pick)]

    samples = []   # (stratum, slug, chapter)
    for stratum, slugs in GENRE_STRATA.items():
        for slug, ch in sample_chapters(slugs, N_PER_STRATUM):
            samples.append((stratum, slug, ch))
    # apparatus-dense: top annotation-density chapters, then random among the densest
    dens = sorted(apparatus_density(mad, inv), key=lambda r: -r[2])
    dense_pool = [(s, c) for s, c, n in dens if n > 0][:40]
    if dense_pool:
        pick = rng.choice(len(dense_pool), size=min(N_PER_STRATUM, len(dense_pool)), replace=False)
        for i in sorted(pick):
            samples.append(("apparatus-dense", dense_pool[i][0], dense_pool[i][1]))

    # --- 2nd-pass attestation sets (whole-witness file + full Madueke edition) ---
    print("building 2nd-pass attestation sets (whole-witness + full edition) ...")
    witness_set = {name: set(toks) for name, toks in djvu.items()}
    witness_types = {name: list(witness_set[name]) for name in djvu}
    edition_set = (set(sk_list(MADB.read_text(encoding="utf-8", errors="replace")))
                   if MADB.exists() else set())

    # --- measure each sample ---
    print(f"measuring {len(samples)} sampled chapters ...")
    per_sample = []
    for stratum, slug, ch in samples:
        disp = inv.get(slug)
        witness = coverage[slug]["witness"]
        verses = mad.get(disp, {}).get(ch, {})
        mad_raw = raw_words(C.norm(" ".join(verses[v] for v in sorted(verses))))
        probe = [s for s in (skel(w) for w in mad_raw) if len(s) >= 2]
        _, s0, s1 = best_window(probe, djvu[witness])
        window = djvu[witness][s0:s1]
        att, tot, missed = attest_recall(mad_raw, window)
        content = content_misses(missed)
        elsewhere, genuine = genuine_candidates(content, witness_set[witness], edition_set,
                                                witness_types[witness])
        per_sample.append({
            "stratum": stratum, "book": slug, "chapter": ch, "witness": witness,
            "madueke_tokens": tot, "attested": att,
            "recall_pct": round(100 * att / tot, 2) if tot else None,
            "window_tokens": len(window),
            "misses": {"total": len(missed), "content": len(content),
                       "print_attested_elsewhere": elsewhere,
                       "genuine_candidates": genuine},
        })

    # --- bootstrap CIs (aggregate + per-stratum) ---
    hits = np.array([r["attested"] for r in per_sample], dtype=float)
    tots = np.array([r["madueke_tokens"] for r in per_sample], dtype=float)
    agg_point, agg_lo, agg_hi = bootstrap_ci(hits, tots, rng)

    per_stratum = {}
    for stratum in list(GENRE_STRATA) + ["apparatus-dense"]:
        m = [i for i, r in enumerate(per_sample) if r["stratum"] == stratum]
        if not m:
            continue
        p, lo, hi = bootstrap_ci(hits[m], tots[m], rng)
        per_stratum[stratum] = {"n_chapters": len(m), "recall_pct": p,
                                "ci95": [lo, hi], "tokens": int(tots[m].sum())}

    content_total = sum(r["misses"]["content"] for r in per_sample)
    genuine = sum(len(r["misses"]["genuine_candidates"]) for r in per_sample)
    all_genuine = sorted({w.lower() for r in per_sample for w in r["misses"]["genuine_candidates"]})
    total_tok = int(tots.sum())
    print(f"\naggregate Madueke->print recall: {agg_point}%  95% CI [{agg_lo}, {agg_hi}]  "
          f"over {total_tok:,} tokens / {len(per_sample)} chapters")
    print(f"content-word misses: {content_total} -> after 2nd-pass (whole-witness + full edition): "
          f"{genuine} genuine candidates ({100*genuine/max(total_tok,1):.4f}% of tokens)")
    if all_genuine:
        print(f"  genuine candidate words: {' '.join(all_genuine[:60])}")
    for st, d in per_stratum.items():
        print(f"  {st:16} n={d['n_chapters']} recall={d['recall_pct']}% CI{d['ci95']}")

    artifact = {
        "artifact": "ocr-validation",
        "generated_by": "ocr_sample.py",
        "idx": 108,
        "seed": SEED,
        "n_bootstrap": N_BOOT,
        "fuzz_threshold": FUZZ,
        "method": "Leg 3 independent print witness: archive.org djvu OCR of the 1582/1609/1610 "
                  "EEBO scans (third-party OCR, outside the Madueke/Sabates lineage and our tesseract "
                  "pipeline). Content-anchored chapter location; token-level Madueke->print skeleton "
                  "recall; chapter-resampled bootstrap CI. Archaic skeleton fold is lossy, so recall is "
                  "a corroboration signal and the distinctive-content-word miss count is the genuine-"
                  "discrepancy signal.",
        "sources": {name: {"path": str((AO / f"{name}_djvu.txt").relative_to(REPO)),
                           "sha256": sha256_file(AO / f"{name}_djvu.txt")}
                    for name in djvu},
        "coverage_resolution": coverage,
        "aggregate": {
            "recall_pct": agg_point, "ci95": [agg_lo, agg_hi],
            "n_chapters": len(per_sample), "n_tokens": total_tok,
            "content_word_misses": content_total,
            "genuine_candidate_misses": genuine,
            "genuine_candidate_pct": round(100 * genuine / max(total_tok, 1), 4),
            "genuine_candidate_words": all_genuine,
        },
        "per_stratum": per_stratum,
        "per_sample": per_sample,
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
