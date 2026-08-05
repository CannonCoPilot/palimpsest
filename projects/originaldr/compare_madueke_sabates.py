#!/usr/bin/env python
"""String-level comparison of the modern OriginalDR text between its two witnesses:

  - Madueke_A : olprint "Augmented Bible" HTML (codeberg), the authoritative upstream.
                Text lives in books/<N>.html as <div class='roleText'> segments with
                inline <sup>V</sup> verse markers; chapters run Genesis 1 .. Apocalypse 22.
  - Sabates_A : janvier-s/original-douay-rheims structured JSON (derived from Madueke).

Even though Madueke has provenance preeminence, we verify accuracy verse-by-verse, catalog
discrepancy frequencies, and surface substantive differences that may warrant correction.

Writes madueke_sabates_diff.json and prints a summary.
"""
from __future__ import annotations
import html, json, re, unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
MADA = HERE / "sources/madueke-a/books"
SAB = HERE.parents[1] / ".scratch/bible-ingest/repos/original-douay-rheims/bible/raw"

# Sabates OT+NT slug order (no 3-book appendix — Madueke has none), from gen_dr_original.py.
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
SAB_ORDER = OT + NT  # 73 books

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    """Bare-scripture normalization for fair comparison: drop markup + note anchors."""
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"<(?:cr|na|mn)>.*?</(?:cr|na|mn)>|<(?:cr|na|mn)/?>", "", s)  # Sabates note tags
    s = _TAG.sub(" ", s)                       # any remaining markup
    s = html.unescape(s)                       # &amp; -> &, &lt; -> < (Madueke HTML entities)
    s = s.replace("^", "").replace("*", "")    # Madueke marginal/word-explication anchors
    for a, b in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"), ("—", "-"), ("–", "-")):
        s = s.replace(a, b)
    return _WS.sub(" ", s).strip()


def alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fold_lig(s: str) -> str:
    """Fold æ/œ ligatures to ae/oe so ligature-convention diffs don't read as wording diffs."""
    for a, b in (("æ", "ae"), ("Æ", "Ae"), ("œ", "oe"), ("Œ", "Oe")):
        s = s.replace(a, b)
    return s


# ---- parse Madueke_A ----
def parse_madueke():
    """Return {book_display: {chapter:int -> {verse:int -> text}}} plus file order."""
    books: dict[str, dict[int, dict[int, str]]] = {}
    order: list[str] = []
    files = sorted(MADA.glob("*.html"), key=lambda p: int(p.stem))
    for p in files:
        html = p.read_text(encoding="utf-8")
        mt = re.search(r"<title>(.*?)</title>", html)
        if not mt:
            continue
        title = mt.group(1).strip()
        mm = re.match(r"^(.*?)\s+(\d+)$", title)
        book, ch = mm.group(1).strip(), int(mm.group(2))
        joined = " ".join(re.findall(r"class='roleText'[^>]*>(.*?)</div>", html, re.S))
        parts = re.split(r"<sup>(\d+)</sup>", joined)
        verses: dict[int, str] = {}
        i = 1
        while i < len(parts):
            vn = int(parts[i]); vt = parts[i + 1] if i + 1 < len(parts) else ""
            # a verse number can recur if segments interleave; concatenate faithfully
            verses[vn] = (verses.get(vn, "") + " " + vt).strip() if vn in verses else vt
            i += 2
        if book not in books:
            books[book] = {}; order.append(book)
        books[book][ch] = verses
    return books, order


def main():
    mad, mad_order = parse_madueke()
    print(f"Madueke_A: {len(mad_order)} books, "
          f"{sum(len(ch) for ch in mad.values())} chapters, "
          f"{sum(len(v) for ch in mad.values() for v in ch.values())} verses")
    print(f"Sabates order: {len(SAB_ORDER)} books\n")

    # align Madueke book (file order) to Sabates slug (canonical order)
    if len(mad_order) != len(SAB_ORDER):
        print(f"!! book-count mismatch: Madueke {len(mad_order)} vs Sabates {len(SAB_ORDER)}")
    book_map = dict(zip(mad_order, SAB_ORDER))

    stats = Counter()
    struct = {"book_ct_mismatch": [], "missing_ch": [], "missing_verse": [], "extra_verse": []}
    substantive = []            # (ref, madueke, sabates)
    punct_only = []
    for mad_book, sab_slug in book_map.items():
        sab = json.loads((SAB / f"{sab_slug}.json").read_text())
        sab_ch = {int(c["chapter"]): c for c in sab["chapters"]}
        mad_ch = mad[mad_book]
        # structural: chapter-count comparison (Sabates raw may carry the spurious Tobias ch0)
        sab_nums = sorted(sab_ch); mad_nums = sorted(mad_ch)
        if sab_nums != mad_nums:
            struct["book_ct_mismatch"].append(
                {"book": sab_slug, "madueke": mad_nums[:3] + ["..."] + mad_nums[-1:],
                 "sabates": sab_nums[:3] + ["..."] + sab_nums[-1:],
                 "mad_n": len(mad_nums), "sab_n": len(sab_nums)})
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
                    stats["sab_verse_absent_in_madueke"] += 1
                    continue
                m_norm = norm(mv[vn])
                stats["compared"] += 1
                if m_norm == s_norm:
                    stats["identical"] += 1
                elif fold_lig(m_norm) == fold_lig(s_norm):
                    stats["ligature_only"] += 1
                elif alnum(fold_lig(m_norm)) == alnum(fold_lig(s_norm)):
                    stats["punct_or_space_only"] += 1
                    if len(punct_only) < 40:
                        punct_only.append((f"{sab_slug} {cn}:{vn}", mv[vn], v["text"]))
                else:
                    stats["substantive"] += 1
                    if len(substantive) < 200:
                        substantive.append((f"{sab_slug} {cn}:{vn}", m_norm, s_norm))
            # verses present in Madueke but absent in Sabates
            for vn in mv:
                if not any(int(x["verse"]) == vn for x in cobj["verses"]):
                    struct["extra_verse"].append(f"{sab_slug} {cn}:{vn}")

    print("=== STRING-LEVEL COMPARISON (normalized, note-anchors stripped) ===")
    for k in ("compared", "identical", "ligature_only", "punct_or_space_only", "substantive",
              "sab_verse_absent_in_madueke"):
        print(f"  {k:32} {stats[k]:>7,}")
    if stats["compared"]:
        print(f"  identical rate: {stats['identical']/stats['compared']*100:.3f}%")
        print(f"  substantive-diff rate: {stats['substantive']/stats['compared']*100:.4f}%")
    print("\n=== STRUCTURAL ===")
    print(f"  chapter-count mismatches: {len(struct['book_ct_mismatch'])}")
    for b in struct["book_ct_mismatch"]:
        print(f"    {b['book']}: Madueke {b['mad_n']} ch vs Sabates {b['sab_n']} ch")
    print(f"  Sabates chapters absent in Madueke: {len(struct['missing_ch'])} {struct['missing_ch'][:6]}")
    print(f"  Sabates verses absent in Madueke:   {len(struct['missing_verse'])} {struct['missing_verse'][:6]}")
    print(f"  Madueke verses absent in Sabates:   {len(struct['extra_verse'])} {struct['extra_verse'][:6]}")

    print("\n=== SAMPLE SUBSTANTIVE DIFFS (first 15) ===")
    for ref, m, s in substantive[:15]:
        print(f"  [{ref}]\n    MAD: {m[:150]}\n    SAB: {s[:150]}")

    out = {"stats": dict(stats), "structural": struct,
           "substantive_samples": substantive, "punct_samples": punct_only,
           "book_map": book_map}
    (HERE / "madueke_sabates_diff.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nwrote {HERE/'madueke_sabates_diff.json'}")


if __name__ == "__main__":
    main()
