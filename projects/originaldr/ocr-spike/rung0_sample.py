#!/usr/bin/env python3
"""rung0_sample.py — stratified sample for rung-0 mode discovery (Sir, 2026-07-18).

Beyond the 10-worst: one representative page per BOOK (all 52 reference books) + 6 apparatus strata
(OT1/OT2/NT × front/back), EACH pulled from TWO different source scans, with EVERY physical source used
>=1. Rasterizes each so Jarvis can scan for failure modes the worst-10 missed.
"""
from __future__ import annotations
import json, re, sys, random
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, ".")
import reocr_ladder as R

random.seed(1610)  # reproducible stratified draw (DR OT first edition year)
HERE = Path(__file__).resolve().parent
OUT = HERE / "diag-reocr" / "sample"; OUT.mkdir(parents=True, exist_ok=True)

# ---- books by volume (DR: First Tome Gen-Job; Second Tome Psalms->; NT) ----
NT = ["matthew","mark","luke","john","acts","romans","1-corinthians","2-corinthians","galatians",
      "ephesians","philippians","colossians","1-thessalonians","2-thessalonians","1-timothy","2-timothy",
      "titus","philemon","hebrews","james","1-peter","2-peter","1-john","2-john","3-john","jude","apocalypse"]
OT1 = ["genesis","exodus","leviticus","numbers","deuteronomy","josue","judges","ruth","1-kings","2-kings",
       "3-kings","4-kings","1-paralipomenon","2-paralipomenon","1-esdras","2-esdras","tobias","judith","esther","job"]
OT2 = ["psalms","proverbs","ecclesiastes","canticle-of-canticles","wisdom"]
VOL = {**{b:"NT" for b in NT}, **{b:"OT1" for b in OT1}, **{b:"OT2" for b in OT2}}

# ---- source -> ocr_dir per volume (from master-source-list) ----
NT_SRC  = {"S1":"archive-nt-1582","S4":"jp2-S04","S5":"pdf-S05","S6":"jp2-S06","S8":"jp2-S08",
           "S9":"pdf-S09nt","S10":"eebo-nt","S11":"eebo-vol1"}
OT1_SRC = {"S1":"archive-ot1-1609","S2":"pdf-S02","S3":"pdf-S03a","S6":"jp2-S06",
           "S9":"archive-holiebible-ot1","S12":"eebo-vol2","S13":"eebo-vol3"}
OT2_SRC = {"S1":"archive-ot2-1610","S3":"pdf-S03b","S6":"jp2-S06","S9":"archive-holiebible-ot2",
           "S14":"eebo-vol4","S15":"eebo-vol5"}
VOL_SRC = {"NT":NT_SRC,"OT1":OT1_SRC,"OT2":OT2_SRC}
# narrow sources that cover only ONE reference book -> force-assign to guarantee they appear
FORCE = {"S12":("genesis","OT1"), "S13":("josue","OT1"), "S14":("psalms","OT2"),
         "S15":("wisdom","OT2"), "S11":("matthew","NT"), "S2":("job","OT1")}

# ---- reference: books -> chapters present ----
sd = json.loads((R.HERE.parent/"reconstruction/reads/s_dismas.json").read_text())
chapters = defaultdict(set)
for e in sd["reads"]:
    m = re.match(r"scripture/([^/]+)/(\d+)/", e.get("skeleton_id",""))
    if m: chapters[m.group(1)].add(int(m.group(2)))

def rep_chapter(book):
    chs = sorted(chapters.get(book, [1]))
    return chs[len(chs)//2] if len(chs) > 2 else chs[0]   # mid-book (skip title/argument leaf)

# ---- assignment: 2 sources per book, spread, all sources used ----
assign = defaultdict(list)          # book -> [source,...]
used = set()
# 1) force narrow sources first
for src,(book,vol) in FORCE.items():
    if src in VOL_SRC[vol] and src not in assign[book]:
        assign[book].append(src); used.add(src)
# 2) round-robin the broad sources per volume to fill each book to 2
broad = {"NT":["S1","S6","S9","S4","S8","S10","S5"], "OT1":["S1","S3","S6","S9"], "OT2":["S1","S3","S6","S9"]}
ptr = {"NT":0,"OT1":0,"OT2":0}
allbooks = NT+OT1+OT2
random.shuffle(allbooks)
for book in allbooks:
    vol = VOL[book]; pool = broad[vol]
    while len(assign[book]) < 2:
        cand = pool[ptr[vol] % len(pool)]; ptr[vol]+=1
        if cand not in assign[book]:
            assign[book].append(cand); used.add(cand)
# 3) safety: any physical source still unused -> attach to a compatible book
ALLSRC = set(NT_SRC)|set(OT1_SRC)|set(OT2_SRC)
for src in ALLSRC - used:
    for vol,srcs in VOL_SRC.items():
        if src in srcs:
            b = next(bk for bk in assign if VOL[bk]==vol)
            assign[b].append(src); used.add(src); break

# ---- rasterize each (book, source) ----
o2p = R.ocrdir_to_pdf()
manifest = []
for book in sorted(assign, key=lambda b:(VOL[b], allbooks.index(b) if b in allbooks else 0)):
    ch = rep_chapter(book)
    anc = R.chapter_anchor(book, ch)
    for src in assign[book]:
        ocr_dir = VOL_SRC[VOL[book]][src]
        pages = R.load_pages(ocr_dir)
        bp = R.best_page(anc, pages) if (anc and pages) else None
        png = OUT / f"{VOL[book]}-{book}-ch{ch}-{src}.png"
        ok = False
        if bp and ocr_dir in o2p:
            ok = R.rasterize(o2p[ocr_dir]["pdf"], bp["page_index"], png, dpi=150)
        manifest.append({"stratum":VOL[book],"book":book,"chapter":ch,"source":src,"ocr_dir":ocr_dir,
                         "page_index":bp.get("page_index") if bp else None,
                         "recall":round(bp.get("recall"),3) if bp else None,
                         "png":str(png.relative_to(HERE)) if ok else None})
    print(f"  {book:22} ch{ch:<3} -> {assign[book]}")

(OUT/"sample-manifest.json").write_text(json.dumps({"n":len(manifest),"sources_used":sorted(used),
    "manifest":manifest}, indent=1))
print(f"\n{len(manifest)} rasters; sources used ({len(used)}): {sorted(used)}")
print(f"unused physical sources: {sorted(ALLSRC-used)}")
print(f"rasterized OK: {sum(1 for m in manifest if m['png'])}/{len(manifest)}")
