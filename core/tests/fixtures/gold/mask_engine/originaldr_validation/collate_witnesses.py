#!/usr/bin/env python
"""Durable, git-tracked witness collation for the modern Original Douay-Rheims (idx 108).

This is the AUDITABLE migration of the scratch-only ``compare_madueke_sabates.py``. Its job is
to record, in a committed JSON artifact (``collation-3way.json``), the agreement between the
reconstruction's witnesses so that every headline discrepancy statistic in the report traces to
a reproducible artifact rather than an unfalsifiable claim.

THREE WITNESSES, TWO LEGS -- and we are explicit about what each leg actually proves:

  Leg 1 -- EXACT verse collation   Madueke_A (HTML)  <->  Sabates_A (JSON)
      Both are verse-keyed, so this is a true per-verse string comparison, classified:
      identical / ligature-only (ae<->ae) / punct-or-space-only / substantive.
      HONEST CAVEAT: Madueke_A is the authoritative upstream and Sabates_A derives from it, so
      this leg measures TRANSCRIPTION FIDELITY between two lineage-related digital editions --
      NOT independent corroboration. The genuinely independent witness is the print OCR
      (see ocr_sample.py), which reads the original 1582/1609/1610 scans.

  Leg 2 -- FORMAT-FIDELITY token recall   Madueke_A  <->  Madueke_B
      Madueke_A (HTML) and Madueke_B (the GitLab PDFs -> merged.txt) are the SAME Madueke edition
      in two formats. merged.txt is a two-column pdftotext flattening (scripture, marginal notes,
      and the facing table-of-contents column interleaved line-by-line); it is NOT verse-parseable,
      so we CANNOT align it verse-by-verse. Instead we measure, at edition-global granularity, what
      fraction of Madueke_A's scripture word-types are attested in Madueke_B's full token set. High
      recall confirms the HTML extraction faithfully represents the PDF edition. This is deliberately
      COARSE and is reported as a format-fidelity check, NOT as an independent third witness.
      NORMALIZATION: both editions are modern-spelling, so Leg 2 uses only LIGHT normalization
      (lowercase, entity-unescape, ae/oe ligature fold, letters-only). It deliberately does NOT use
      the aggressive archaic skeleton fold (long-s, silent-e, doubled-letter collapse) that Leg 3's
      OCR of the *archaic print* requires -- applying that here would over-collapse distinct modern
      words and dishonestly inflate recall.

Copyrighted / large source binaries are not committed; their content is pinned by sha256 in the
artifact so any number here is reproducible from git + the local corpus.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent  # .../originaldr_validation
# HERE.parents: [0]mask_engine [1]gold [2]fixtures [3]tests [4]core [5]<repo>
REPO = HERE.parents[5]

MADA = REPO / "core/.scratch/originaldr-project/sources/madueke-a/books"
SAB = REPO / ".scratch/original-douay-rheims/bible/raw"          # repo-root copy (generator's source)
MADB = REPO / "core/.scratch/originaldr-project/sources/madueke-b/merged.txt"
OUT = HERE / "collation-3way.json"

# Sabates canonical slug order (OT+NT, 73 books), mirrored from gen_dr_original.py.
OT = ["genesis", "exodus", "leviticus", "numbers", "deuteronomy", "josue", "judges",
      "ruth", "1-kings", "2-kings", "3-kings", "4-kings", "1-paralipomenon",
      "2-paralipomenon", "1-esdras", "2-esdras", "tobias", "judith", "esther", "job",
      "psalms", "proverbs", "ecclesiastes", "canticle-of-canticles", "wisdom",
      "ecclesiasticus", "isaie", "jeremie", "lamentations", "baruch", "ezechiel",
      "daniel", "osee", "joel", "amos", "abdias", "jonas", "micheas", "nahum",
      "habacuc", "sophonias", "aggeus", "zacharias", "malachie", "1-machabees", "2-machabees"]
NT = ["matthew", "mark", "luke", "john", "acts", "romans", "1-corinthians",
      "2-corinthians", "galatians", "ephesians", "philippians", "colossians",
      "1-thessalonians", "2-thessalonians", "1-timothy", "2-timothy", "titus",
      "philemon", "hebrews", "james", "1-peter", "2-peter", "1-john", "2-john",
      "3-john", "jude", "apocalypse"]
SAB_ORDER = OT + NT

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


# --------------------------------------------------------------------------- #
# Leg 1 normalization (bare scripture, verse-level string comparison)
# --------------------------------------------------------------------------- #
def norm(s: str) -> str:
    """Bare-scripture normalization: drop markup + Sabates note tags + Madueke anchors."""
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"<(?:cr|na|mn)>.*?</(?:cr|na|mn)>|<(?:cr|na|mn)/?>", "", s)  # Sabates note tags
    s = _TAG.sub(" ", s)                       # any remaining markup
    s = html.unescape(s)                       # &amp; -> & (Madueke HTML entities)
    s = s.replace("^", "").replace("*", "")    # Madueke marginal/word-explication anchors
    for a, b in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"),
                 ("—", "-"), ("–", "-")):
        s = s.replace(a, b)
    return _WS.sub(" ", s).strip()


def alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fold_lig(s: str) -> str:
    """Fold ae/oe ligatures so ligature-convention diffs don't read as wording diffs."""
    for a, b in (("æ", "ae"), ("Æ", "Ae"), ("œ", "oe"), ("Œ", "Oe")):
        s = s.replace(a, b)
    return s


# --------------------------------------------------------------------------- #
# Leg 2 normalization (LIGHT -- modern-vs-modern token type)
# --------------------------------------------------------------------------- #
_LIG2 = (("æ", "ae"), ("œ", "oe"), ("ﬀ", "ff"), ("ﬁ", "fi"), ("ﬂ", "fl"))


def mnorm(word: str) -> str:
    """Light word-type normalization for a modern-spelling token (no archaic folding)."""
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    for a, b in _LIG2:
        w = w.replace(a, b)
    return re.sub(r"[^a-z]", "", w)


def word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÆæŒœ]+", text)


# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #
def parse_madueke() -> tuple[dict, list]:
    """Return ({book_display: {chapter:int -> {verse:int -> text}}}, file_order)."""
    books: dict[str, dict[int, dict[int, str]]] = {}
    order: list[str] = []
    for p in sorted(MADA.glob("*.html"), key=lambda p: int(p.stem)):
        h = p.read_text(encoding="utf-8")
        mt = re.search(r"<title>(.*?)</title>", h)
        if not mt:
            continue
        mm = re.match(r"^(.*?)\s+(\d+)$", mt.group(1).strip())
        if not mm:
            continue
        book, ch = mm.group(1).strip(), int(mm.group(2))
        joined = " ".join(re.findall(r"class='roleText'[^>]*>(.*?)</div>", h, re.S))
        parts = re.split(r"<sup>(\d+)</sup>", joined)
        verses: dict[int, str] = {}
        i = 1
        while i < len(parts):
            vn = int(parts[i])
            vt = parts[i + 1] if i + 1 < len(parts) else ""
            verses[vn] = (verses.get(vn, "") + " " + vt).strip() if vn in verses else vt
            i += 2
        if book not in books:
            books[book] = {}
            order.append(book)
        books[book][ch] = verses
    return books, order


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def dir_digest(path: Path, pattern: str) -> tuple[int, str]:
    """Content-pin a directory: (n_files, sha256 over sorted 'name<TAB>filesha' lines)."""
    files = sorted(path.glob(pattern), key=lambda p: p.name)
    manifest = "\n".join(f"{p.name}\t{sha256_file(p)}" for p in files)
    return len(files), hashlib.sha256(manifest.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Leg 1 -- exact verse collation Madueke_A <-> Sabates_A
# --------------------------------------------------------------------------- #
def leg1_exact(mad: dict, mad_order: list) -> dict:
    if len(mad_order) != len(SAB_ORDER):
        print(f"!! book-count mismatch: Madueke {len(mad_order)} vs Sabates {len(SAB_ORDER)}",
              file=sys.stderr)
    book_map = dict(zip(mad_order, SAB_ORDER))

    agg = Counter()
    per_book: list[dict] = []
    struct = {"book_ct_mismatch": [], "missing_ch": [], "missing_verse": [], "extra_verse": []}
    substantive: list[dict] = []
    punct_samples: list[dict] = []

    for mad_book, sab_slug in book_map.items():
        sab = json.loads((SAB / f"{sab_slug}.json").read_text())
        sab_ch = {int(c["chapter"]): c for c in sab["chapters"]}
        mad_ch = mad[mad_book]
        b = Counter()

        sab_nums, mad_nums = sorted(sab_ch), sorted(mad_ch)
        if sab_nums != mad_nums:
            struct["book_ct_mismatch"].append(
                {"book": sab_slug, "mad_n": len(mad_nums), "sab_n": len(sab_nums),
                 "madueke": mad_nums[:3] + ["..."] + mad_nums[-1:],
                 "sabates": sab_nums[:3] + ["..."] + sab_nums[-1:]})

        for cn, cobj in sab_ch.items():
            if cn not in mad_ch:
                struct["missing_ch"].append(f"{sab_slug} {cn}")
                continue
            mv = mad_ch[cn]
            for v in cobj["verses"]:
                vn = int(v["verse"])
                s_norm = norm(v["text"])
                if vn not in mv:
                    struct["missing_verse"].append(f"{sab_slug} {cn}:{vn}")
                    agg["sab_verse_absent_in_madueke"] += 1
                    continue
                m_norm = norm(mv[vn])
                b["compared"] += 1
                if m_norm == s_norm:
                    b["identical"] += 1
                elif fold_lig(m_norm) == fold_lig(s_norm):
                    b["ligature_only"] += 1
                elif alnum(fold_lig(m_norm)) == alnum(fold_lig(s_norm)):
                    b["punct_or_space_only"] += 1
                    if len(punct_samples) < 40:
                        punct_samples.append({"ref": f"{sab_slug} {cn}:{vn}",
                                              "madueke": mv[vn], "sabates": v["text"]})
                else:
                    b["substantive"] += 1
                    if len(substantive) < 200:
                        substantive.append({"ref": f"{sab_slug} {cn}:{vn}",
                                            "madueke": m_norm, "sabates": s_norm})
            for vn in mv:
                if not any(int(x["verse"]) == vn for x in cobj["verses"]):
                    struct["extra_verse"].append(f"{sab_slug} {cn}:{vn}")

        agg.update(b)
        per_book.append({"book": sab_slug, **{k: b[k] for k in
                        ("compared", "identical", "ligature_only",
                         "punct_or_space_only", "substantive")}})

    compared = agg["compared"] or 1
    return {
        "granularity": "verse",
        "relationship": "lineage-related (Sabates_A derives from Madueke_A) -> transcription "
                        "fidelity, NOT independent corroboration",
        "aggregate": {
            **{k: agg[k] for k in ("compared", "identical", "ligature_only",
                                   "punct_or_space_only", "substantive",
                                   "sab_verse_absent_in_madueke")},
            "identical_pct": round(100 * agg["identical"] / compared, 4),
            "ligature_only_pct": round(100 * agg["ligature_only"] / compared, 4),
            "punct_or_space_only_pct": round(100 * agg["punct_or_space_only"] / compared, 4),
            "substantive_pct": round(100 * agg["substantive"] / compared, 6),
        },
        "per_book": per_book,
        "structural": {
            "book_ct_mismatch": struct["book_ct_mismatch"],
            "sab_chapters_absent_in_madueke": struct["missing_ch"],
            "sab_verses_absent_in_madueke_count": len(struct["missing_verse"]),
            "sab_verses_absent_in_madueke_sample": struct["missing_verse"][:12],
            "mad_verses_absent_in_sabates_count": len(struct["extra_verse"]),
            "mad_verses_absent_in_sabates_sample": struct["extra_verse"][:12],
        },
        "substantive_samples": substantive,
        "punct_or_space_samples": punct_samples,
        "book_map": book_map,
    }


# --------------------------------------------------------------------------- #
# Leg 2 -- format-fidelity token recall Madueke_A <-> Madueke_B
# --------------------------------------------------------------------------- #
def leg2_format_fidelity(mad: dict) -> dict:
    a_freq: Counter = Counter()
    for chapters in mad.values():
        for verses in chapters.values():
            for text in verses.values():
                for tok in word_tokens(norm(text)):
                    m = mnorm(tok)
                    if len(m) >= 2:
                        a_freq[m] += 1
    a_types = set(a_freq)

    b_text = MADB.read_text(encoding="utf-8", errors="replace")
    b_types = {m for m in (mnorm(t) for t in word_tokens(b_text)) if len(m) >= 2}

    present = a_types & b_types
    missing = sorted(a_types - b_types)
    total_tok = sum(a_freq.values()) or 1
    weighted_present = sum(f for t, f in a_freq.items() if t in b_types)

    return {
        "granularity": "edition-global word-type recall",
        "caveat": "Madueke_A and Madueke_B are the SAME edition in two formats; this confirms "
                  "HTML-extraction fidelity, NOT independent corroboration. merged.txt is a "
                  "column-flattened pdftotext dump and is not verse-parseable, so recall is "
                  "measured at edition granularity, not per verse.",
        "normalization": "light modern-spelling fold (lowercase, ae/oe ligature, letters-only); "
                         "NO archaic skeleton fold",
        "madueke_a_scripture_types": len(a_types),
        "madueke_b_edition_types": len(b_types),
        "types_attested_in_b": len(present),
        "type_recall_pct": round(100 * len(present) / (len(a_types) or 1), 4),
        "token_weighted_recall_pct": round(100 * weighted_present / total_tok, 4),
        "missing_type_count": len(missing),
        "missing_type_sample": missing[:60],
    }


# --------------------------------------------------------------------------- #
def main() -> int:
    for label, path in (("Madueke_A", MADA), ("Sabates_A", SAB), ("Madueke_B", MADB)):
        if not path.exists():
            print(f"!! source missing ({label}): {path}\n"
                  "   This script needs the local (gitignored) OriginalDR corpus. "
                  "Committed artifact is reproducible only where the corpus is present.",
                  file=sys.stderr)
            return 2

    mad, mad_order = parse_madueke()
    n_ch = sum(len(c) for c in mad.values())
    n_v = sum(len(v) for c in mad.values() for v in c.values())
    print(f"Madueke_A: {len(mad_order)} books, {n_ch} chapters, {n_v} verses")

    a_files, a_digest = dir_digest(MADA, "*.html")
    s_files, s_digest = dir_digest(SAB, "*.json")

    leg1 = leg1_exact(mad, mad_order)
    print(f"Leg 1 (exact A<->Sabates): compared={leg1['aggregate']['compared']:,} "
          f"identical={leg1['aggregate']['identical_pct']}% "
          f"substantive={leg1['aggregate']['substantive']} "
          f"({leg1['aggregate']['substantive_pct']}%)")

    leg2 = leg2_format_fidelity(mad)
    print(f"Leg 2 (format-fidelity A<->B): type-recall={leg2['type_recall_pct']}% "
          f"token-weighted={leg2['token_weighted_recall_pct']}% "
          f"missing-types={leg2['missing_type_count']}")

    artifact = {
        "artifact": "collation-3way",
        "generated_by": "collate_witnesses.py",
        "idx": 108,
        "method": {
            "leg1": "EXACT verse-by-verse string collation Madueke_A(HTML) <-> Sabates_A(JSON); "
                    "lineage-related (fidelity, not independent).",
            "leg2": "FORMAT-FIDELITY edition-global token-recall Madueke_A <-> Madueke_B(merged.txt); "
                    "same edition, two formats (extraction fidelity, not independent).",
            "leg3_note": "The independent print witness (OCR of the 1582/1609/1610 scans) is "
                         "measured separately in ocr_sample.py -> ocr-validation.json.",
        },
        "sources": {
            "madueke_a": {"path": str(MADA.relative_to(REPO)), "n_files": a_files,
                          "digest_sha256": a_digest},
            "sabates_a": {"path": str(SAB.relative_to(REPO)), "n_files": s_files,
                          "digest_sha256": s_digest},
            "madueke_b": {"path": str(MADB.relative_to(REPO)),
                          "sha256": sha256_file(MADB), "bytes": MADB.stat().st_size},
        },
        "leg1_exact_madueke_sabates": leg1,
        "leg2_format_fidelity_madueke_a_vs_b": leg2,
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
