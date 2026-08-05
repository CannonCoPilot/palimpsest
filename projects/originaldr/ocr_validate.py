#!/usr/bin/env python
"""3-way OCR validation: independent witness on the ORIGINAL PUBLISHED SCANS.

Madueke_A and Sabates_A share a transcription lineage (Sabates derives from Madueke),
so their agreement (see compare_madueke_sabates.py: 0 substantive wording diffs) could in
principle inherit a common transcription error. This script adds a genuinely independent
third witness: our OWN tesseract OCR of the original 1582/1609/1610 printed editions
(Anna's Archive EEBO reproductions), to confirm the shared text matches what was PRINTED.

Method (per sampled chapter/verse-range):
  1. Render the scan page(s) -> PNG (pdftoppm 300dpi) -> tesseract OCR (done externally).
  2. Extract the SCRIPTURE REGION of the page: after the running head, before "ANNOTATIONS".
  3. Archaic-fold every token to a comparison skeleton (long-s/uv/ij/vv/ligature/-e/doubled).
  4. Attestation recall (OCR -> Madueke chapter): fraction of real OCR scripture tokens that
     have a fuzzy match in Madueke's text for that chapter. Same vs Sabates.
  5. Verse exhibits: raw OCR span vs Madueke vs Sabates for visual confirmation.

We deliberately do NOT count archaic spelling / typographic / OCR-noise differences as textual
discrepancies; we confirm WORD CORRESPONDENCE. Residual non-attested tokens are dumped for triage.
"""
from __future__ import annotations
import html as _html, json, re, subprocess, unicodedata
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
MADA = HERE / "sources/madueke-a/books"
SAB = HERE.parents[1] / ".scratch/bible-ingest/repos/original-douay-rheims/bible/raw"
OCRDIR = HERE / "ocr-validation/ocr"
PAGEDIR = HERE / "ocr-validation/pages"
ANNO = SAB.parent.parent / "annotations"   # per-chapter apparatus JSON (Sabates repo)
EDITION = HERE / "sources/madueke-b/merged.txt"   # full-edition transcription (scripture+apparatus)
ORIG = HERE.parents[2] / "imports/Scripture/Bibles/DouayRheims_DR/Original"

_EDITION_SKEL: set[str] | None = None

# --- Sabates canonical slug order (from gen_dr_original.py) to map Madueke file-order -> slug ---
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

# Volume PDF filename (glob suffix) per volume number.
VOL_GLOB = {
    1: "Original Douay-Rheims Bible (vol_ 1)*Anna’s Archive.pdf",
    2: "Original Douay-Rheims Bible (vol_ 2)*Anna’s Archive.pdf",
    3: "Original Douay-Rheims Bible (vol_ 3)*Anna’s Archive.pdf",
    4: "Original Douay-Rheims Bible (vol_ 4)*Anna’s Archive.pdf",
    5: "Original Douay-Rheims Bible (vol_ 5)*Anna’s Archive.pdf",
}


# ---------- archaic / OCR skeleton fold ----------
_LIG = (("æ", "ae"), ("œ", "oe"), ("ﬀ", "ff"), ("ﬁ", "fi"), ("ﬂ", "fl"))

def skel(word: str) -> str:
    """Collapse a token to an archaic/OCR-insensitive skeleton for fuzzy matching."""
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    for a, b in _LIG:
        w = w.replace(a, b)
    w = w.replace("vv", "w")
    w = re.sub(r"[^a-z]", "", w)          # keep letters only
    w = w.replace("v", "u").replace("j", "i")   # u/v, i/j equivalence
    w = w.replace("f", "s")               # long-s (OCR reads ſ as f) <-> s, symmetric both sides
    w = re.sub(r"e$", "", w)              # archaic silent trailing -e
    w = re.sub(r"(.)\1+", r"\1", w)       # collapse doubled letters
    return w


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÆæŒœ]+", text)


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


# ---------- source loaders ----------
def norm_src(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"<(?:cr|na|mn)>.*?</(?:cr|na|mn)>|<(?:cr|na|mn)/?>", "", s)
    s = _TAG.sub(" ", s)
    s = _html.unescape(s)
    s = s.replace("^", "").replace("*", "")
    return _WS.sub(" ", s).strip()


def parse_madueke():
    books, order = {}, []
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
        verses, i = {}, 1
        while i < len(parts):
            vn = int(parts[i]); vt = parts[i + 1] if i + 1 < len(parts) else ""
            verses[vn] = (verses.get(vn, "") + " " + vt).strip() if vn in verses else vt
            i += 2
        if book not in books:
            books[book] = {}
            order.append(book)
        books[book][ch] = verses
    return books, order


def load_sab_chapter(slug: str, chapter: int) -> dict[int, str]:
    sab = json.loads((SAB / f"{slug}.json").read_text())
    for c in sab["chapters"]:
        if int(c["chapter"]) == chapter:
            return {int(v["verse"]): v["text"] for v in c["verses"]}
    return {}


def edition_skel() -> set[str]:
    """Skeleton set of EVERY token in the full Madueke edition (scripture + arguments +
    all annotations). A scan word absent from this set is a word the Madueke lineage never
    transcribed anywhere -> the only real candidate for a genuine omission/discrepancy."""
    global _EDITION_SKEL
    if _EDITION_SKEL is None:
        text = EDITION.read_text(encoding="utf-8", errors="replace")
        _EDITION_SKEL = {s for s in (skel(t) for t in tokens(text)) if len(s) >= 2}
    return _EDITION_SKEL


def load_sab_annotations(slug: str, chapters: list[int]) -> str:
    """Concatenated apparatus text (annotation title+body) for the given chapters, if present."""
    parts = []
    for ch in chapters:
        f = ANNO / slug / f"{ch:03d}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        for a in d.get("annotations", []):
            parts.append(norm_src(a.get("title", "") + " " + a.get("text", "")))
    return " ".join(parts)


# ---------- OCR page handling ----------
def vol_pdf(vol: int) -> Path:
    return next(iter(sorted(ORIG.glob(VOL_GLOB[vol]))))


def ensure_ocr(vol: int, page: int) -> str:
    """Render+OCR page on demand; return OCR text. Filenames: vol{V}-{PPP}.png/.txt."""
    stem = f"vol{vol}-{page:03d}"
    txt = OCRDIR / f"{stem}.txt"
    if not txt.exists():
        png = PAGEDIR / f"{stem}.png"
        if not png.exists():
            subprocess.run(["pdftoppm", "-png", "-r", "300", "-f", str(page), "-l", str(page),
                            str(vol_pdf(vol)), str(PAGEDIR / f"vol{vol}")], check=True)
            # pdftoppm names as vol{V}-<page>.png (no zero pad if <10 differs); normalize
            cand = sorted(PAGEDIR.glob(f"vol{vol}-*{page}.png"))
            if not png.exists() and cand:
                cand[0].rename(png)
        subprocess.run(["tesseract", str(png), str(OCRDIR / stem), "-l", "eng", "--psm", "3"],
                       check=True, stderr=subprocess.DEVNULL)
    return txt.read_text(encoding="utf-8", errors="replace")


def scripture_region(ocr_text: str) -> str:
    """Lines after running head (line 1) until the ANNOTATIONS apparatus block."""
    lines = ocr_text.splitlines()
    body = lines[1:] if lines else []
    out = []
    for ln in body:
        if re.search(r"ANNOTATION", ln, re.I):
            break
        out.append(ln)
    return " ".join(out)


# ---------- attestation ----------
NOISE = {"chap", "cap", "cua", "cra", "the", "gospel", "according", "prophecie",
         "iosve", "iof", "iue"}

def _skel_set(text: str) -> set[str]:
    s = {skel(t) for t in tokens(text)}
    s.discard("")
    return s


def attest(ocr_region: str, target_text: str, thresh: float = 0.80):
    """Fraction of real OCR scripture tokens fuzzy-attested in target_text.
    Returns (n_ok, n_total, [unattested_raw_tokens])."""
    tgt_list = list(_skel_set(target_text))
    ok, total, miss = 0, 0, []
    for raw in tokens(ocr_region):
        s = skel(raw)
        if len(s) < 2 or raw.lower() in NOISE:
            continue
        total += 1
        if s in tgt_list or any(sim(s, t) >= thresh for t in tgt_list):
            ok += 1
        else:
            miss.append(raw)
    return ok, total, miss


def triage(ocr_region: str, mad_text: str, summary_text: str, anno_text: str, edition: set[str]):
    """Classify every real OCR scripture token in reading order. A residual is a genuine
    candidate discrepancy ONLY if it is none of: OCR-noise of a scripture word, a split
    fragment that rejoins its neighbor, chapter-argument furniture, apparatus/annotation text
    that tesseract interleaved from the margins, or any word transcribed ANYWHERE in the full
    Madueke edition (scripture or apparatus).

    buckets: attested | ocr_noise | split | argument | annotation | edition | candidate"""
    mad = list(_skel_set(mad_text))
    arg = list(_skel_set(summary_text))
    ann = list(_skel_set(anno_text))
    toks = [t for t in tokens(ocr_region) if len(skel(t)) >= 2 and t.lower() not in NOISE]
    counts = {"attested": 0, "ocr_noise": 0, "split": 0, "argument": 0,
              "annotation": 0, "edition": 0, "candidate": 0}
    candidates = []
    n = len(toks)
    for i, raw in enumerate(toks):
        s = skel(raw)
        if s in mad or any(sim(s, t) >= 0.80 for t in mad):
            counts["attested"] += 1
        elif any(sim(s, t) >= 0.66 for t in mad):
            counts["ocr_noise"] += 1               # OCR corruption of an attested scripture word
        elif i + 1 < n and any(sim(skel(raw + toks[i + 1]), t) >= 0.80 for t in mad):
            counts["split"] += 1                   # word split across an OCR space (comman+deth)
        elif s in arg or any(sim(s, t) >= 0.78 for t in arg):
            counts["argument"] += 1                # chapter-argument / summary furniture
        elif s in ann or any(sim(s, t) >= 0.80 for t in ann):
            counts["annotation"] += 1              # apparatus (Sabates) bled in from the page
        elif s in edition:
            counts["edition"] += 1                 # printed somewhere in the full Madueke edition
        else:
            counts["candidate"] += 1
            candidates.append(raw)
    return counts, candidates


# curated sample: (label, vol, page, sab_slug, chapter)   -- page = 1-based PDF page index.
# Pages verified scripture-dominant by eyeballing the OCR (not chapter-argument or annotation pages).
SAMPLE = [
    ("Matthew 10 (NT / gospel, vol1)",   1, 55, "matthew", 10),
    ("Genesis 17 (Pentateuch, vol2)",    2, 79, "genesis", 17),
    ("Josue 11 (historical, vol3)",      3, 21, "josue", 11),
    ("Psalm 109 (Psalter, vol4)",        4, 200, "psalms", 109),
    ("Isaie 33 (prophetic, vol5)",       5, 45, "isaie", 33),
]


def madueke_display_for(mad, order, slug):
    bmap = dict(zip(order, SAB_ORDER))
    inv = {v: k for k, v in bmap.items()}
    return inv.get(slug)


def load_sab_summary(slug: str, chapter: int) -> str:
    sab = json.loads((SAB / f"{slug}.json").read_text())
    for c in sab["chapters"]:
        if int(c["chapter"]) == chapter:
            return c.get("summary", "")
    return ""


def main():
    mad, order = parse_madueke()
    edition = edition_skel()
    rows, results = [], []
    for label, vol, page, slug, ch in SAMPLE:
        disp = madueke_display_for(mad, order, slug)
        # A scan page holds a contiguous text run that can cross chapter boundaries, so the
        # correct comparison target is the chapter NEIGHBOURHOOD (ch-1, ch, ch+1), not one chapter.
        nbr = [ch - 1, ch, ch + 1]
        mad_text = norm_src(" ".join(
            mad.get(disp, {}).get(k, {})[v]
            for k in nbr for v in sorted(mad.get(disp, {}).get(k, {}))))
        sab_text = norm_src(" ".join(
            load_sab_chapter(slug, k)[v] for k in nbr for v in sorted(load_sab_chapter(slug, k))))
        summary = " ".join(load_sab_summary(slug, k) for k in nbr)
        anno = load_sab_annotations(slug, nbr)
        ocr = ensure_ocr(vol, page)
        region = scripture_region(ocr)
        m_ok, m_tot, _ = attest(region, mad_text)
        s_ok, s_tot, _ = attest(region, sab_text)
        counts, cands = triage(region, mad_text, summary, anno, edition)
        rows.append((label, disp, ch, m_ok, m_tot, s_ok, s_tot, counts, cands, region))
        results.append({"label": label, "madueke_book": disp, "chapter": ch,
                        "recall_madueke_pct": round(100 * m_ok / m_tot, 2) if m_tot else None,
                        "recall_sabates_pct": round(100 * s_ok / s_tot, 2) if s_tot else None,
                        "triage": counts, "candidates": cands})

    print("=== 3-WAY OCR ATTESTATION (independent tesseract OCR of original scan) ===")
    print("recall = fraction of real OCR scripture tokens fuzzy-attested in Madueke / Sabates\n")
    tot_ok = tot_n = 0
    agg = {"attested": 0, "ocr_noise": 0, "split": 0, "argument": 0,
           "annotation": 0, "edition": 0, "candidate": 0}
    for label, disp, ch, mo, mt, so, st, c, cands, _ in rows:
        mr = 100 * mo / mt if mt else 0
        sr = 100 * so / st if st else 0
        tot_ok += mo; tot_n += mt
        for k in agg:
            agg[k] += c[k]
        print(f"  {label:32} Mad {mo:3}/{mt:3}={mr:5.1f}%  Sab {so:3}/{st:3}={sr:5.1f}%")

    print("\n=== RESIDUAL TRIAGE (every non-attested OCR token classified) ===")
    print("  a genuine textual discrepancy would appear as a 'candidate' that is a real scripture word\n")
    for label, disp, ch, mo, mt, so, st, c, cands, _ in rows:
        print(f"  {label:32} attest={c['attested']:3} ocr={c['ocr_noise']:3} split={c['split']:2} "
              f"arg={c['argument']:2} anno={c['annotation']:3} edtn={c['edition']:3} CAND={c['candidate']:2}")
        if cands:
            print(f"      candidates: {' '.join(cands)}")
    print(f"\n  AGGREGATE  attested={agg['attested']}  ocr_noise={agg['ocr_noise']}  split={agg['split']}  "
          f"argument={agg['argument']}  annotation={agg['annotation']}  edition={agg['edition']}  "
          f"candidate={agg['candidate']}")
    print(f"  strict scripture-recall: {tot_ok}/{tot_n} = {100*tot_ok/tot_n:.2f}%")
    denom = sum(agg.values())
    print(f"  residual-after-triage (candidates / all scripture tokens): "
          f"{agg['candidate']}/{denom} = {100*agg['candidate']/denom:.2f}%")

    print("\n=== VERSE-REGION EXHIBITS (raw OCR vs two lineage witnesses) ===")
    for label, disp, ch, mo, mt, so, st, c, cands, region in rows:
        mtext = norm_src(" ".join(mad.get(disp, {}).get(ch, {})[v]
                                  for v in sorted(mad.get(disp, {}).get(ch, {}))))
        print(f"\n[{label}]")
        print(f"  OCR : {region.strip()[:210]}")
        print(f"  MAD : {mtext[:210]}")

    out = {"method": "independent tesseract OCR of Anna's Archive EEBO scans of the original "
                     "1582/1609/1610 editions; OCR->lineage attestation with residual triage",
           "sample": results,
           "aggregate": {"strict_scripture_recall_pct": round(100 * tot_ok / tot_n, 2) if tot_n else None,
                         "triage_totals": agg,
                         "genuine_candidate_rate_pct": round(100 * agg["candidate"] / denom, 2) if denom else None}}
    (HERE / "ocr_validation_result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nwrote {HERE/'ocr_validation_result.json'}")


if __name__ == "__main__":
    main()
