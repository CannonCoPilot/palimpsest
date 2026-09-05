#!/usr/bin/env python3
"""LECTOR Class Register, rebuilt from the B-witness cold read alone.

Source: ../cold-read-B.json (54 leaves, 665 regions) + ../img-B/*.jpg (1100 px).
Output: lector-class-register-B.html  (self-contained; republish to the SAME artifact url
        5e285c57-44a0-4f26-b6e9-639e4a70b2d1).

Steps folded in (the README's steps 1-3): exemplar crops, page build, full-leaf lightbox.
No f-string templating for the big page: placeholders are substituted with str.replace so
CSS/JS braces stay literal.
"""
import base64, collections, html, io, json
from pathlib import Path
from PIL import Image, ImageDraw

SP = Path(__file__).parent
CR = SP.parent
IMG = CR / "img-B"
D = json.load(open(CR / "cold-read-B.json"))
LEAVES = D["leaves"]

LEAF_W, LEAF_Q = 800, 55      # lightbox leaves
CROP_W, CROP_Q = 720, 60      # exemplar crops
THUMB_W = 200                 # locator
PAD = 0.012                   # 1.2 % pad around a crop


def esc(s): return html.escape(s, quote=True)
def vol(leaf): return leaf.split("_")[0]
def b64(im, q):
    b = io.BytesIO(); im.save(b, "JPEG", quality=q, optimize=True)
    return base64.b64encode(b.getvalue()).decode()

# ------------------------------------------------------------------ counts
counts = collections.Counter()
per_leaf = collections.defaultdict(set)
for lid, l in LEAVES.items():
    for r in l["regions"]:
        counts[r["class"]] += 1; per_leaf[r["class"]].add(lid)
N_REG = sum(counts.values()); N_LEAF = len(LEAVES)

# ------------------------------------------------------------------ exemplar picks
# hand picks where the choice carries the point; (leaf, box-prefix) - box matched by first two coords
PICK = {
 "MT": [("OT1-1609-B_0412", (0.16, 0.065)), ("NT-1582-B_0028", (0.2, 0.05))],
 "LR": [("NT-1582-B_0254", (0.11, 0.465)), ("NT-1582-B_0307", (0.74, 0.09))],
 "OR": [("OT2-1610-B_0011", (0.03, 0.04)), ("NT-1582-B_0119", (0.15, 0.06))],
 "MS": [("OT2-1610-B_0012", (0.13, 0.63)), ("OT2-1610-B_0011", (0.13, 0.0))],
 "HD": [("OT2-1610-B_0012", (0.3, 0.16))],
 "AT": [("OT2-1610-B_0012", (0.2, 0.69))],
 "ST": [("NT-1582-B_0706", (0.2, 0.78)), ("OT2-1610-B_0279", (0.25, 0.03))],
 "CT": [("NT-1582-B_0119", (0.16, 0.855))],
 "TB": [("OT2-1610-B_1088", (0.06, 0.055)), ("OT2-1610-B_1093", (0.06, 0.135))],
 "IX": [("NT-1582-B_0781", (0.27, 0.765)), ("OT2-1610-B_1116", (0.57, 0.06))],
 "BT": [("OT2-1610-B_0011", (0.19, 0.14)), ("OT1-1609-B_0352", (0.19, 0.06))],
 "CR": [("NT-1582-B_0254", (0.81, 0.035)), ("NT-1582-B_0119", (0.04, 0.04))],
 "GK": [("OT2-1610-B_0026", (0.06, 0.415)), ("OT2-1610-B_0027", (0.82, 0.06))],
 "IG": [("OT2-1610-B_0026", (0.21, 0.44)), ("OT2-1610-B_0039", (0.3, 0.06))],
 "LM": [("OT1-1609-B_0296", (0.19, 0.35))],
 "??": [("OT2-1610-B_0670", (0.88, 0.065)), ("NT-1582-B_0254", (0.1, 0.88))],
 # reportable states (drawn from the '??' regions)
 "BL": [("OT2-1610-B_1140", (0.0, 0.0))],
 "BP": [("NT-1582-B_0254", (0.1, 0.88)), ("OT1-1609-B_0982", (0.05, 0.89))],
 "EC": [("OT2-1610-B_1088", (0.58, 0.72)), ("OT2-1610-B_1089", (0.78, 0.115))],
}
STATE_SRC = {"BL": "??", "BP": "??", "EC": "??"}   # states are recorded as ?? in the read

def find(leaf, pre, cls):
    for r in LEAVES[leaf]["regions"]:
        if r["class"] == cls and abs(r["box"][0]-pre[0]) < 1e-6 and abs(r["box"][1]-pre[1]) < 1e-6:
            return r
    raise SystemExit(f"pick not found: {leaf} {cls} {pre}")

def auto(cls):
    """two regions on different leaves, different volumes if possible, mid-sized, best-described"""
    cands = []
    for lid, l in LEAVES.items():
        for r in l["regions"]:
            if r["class"] != cls: continue
            b = r["box"]; a = (b[2]-b[0])*(b[3]-b[1])
            cands.append((a, len(r["why"]), lid, r))
    good = [c for c in cands if 0.002 <= c[0] <= 0.45] or cands
    good.sort(key=lambda c: -c[1])
    out, vols, leaves = [], set(), set()
    for a, n, lid, r in good:
        if lid in leaves: continue
        if vol(lid) in vols and len(good) > 3: continue
        out.append((lid, r)); vols.add(vol(lid)); leaves.add(lid)
        if len(out) == 2: break
    if len(out) < 2:
        for a, n, lid, r in good:
            if lid not in leaves: out.append((lid, r)); leaves.add(lid)
            if len(out) == 2: break
    return out

_img_cache = {}
def leaf_img(lid):
    if lid not in _img_cache: _img_cache[lid] = Image.open(IMG / f"{lid}.jpg").convert("RGB")
    return _img_cache[lid]

def exemplar(lid, r):
    im = leaf_img(lid); W, H = im.size; b = r["box"]
    x0 = max(0, int((b[0]-PAD)*W)); y0 = max(0, int((b[1]-PAD)*H))
    x1 = min(W, int((b[2]+PAD)*W)); y1 = min(H, int((b[3]+PAD)*H))
    crop = im.crop((x0, y0, x1, y1))
    if crop.width > CROP_W: crop = crop.resize((CROP_W, round(crop.height*CROP_W/crop.width)), Image.LANCZOS)
    th = im.resize((THUMB_W, round(H*THUMB_W/W)), Image.LANCZOS)
    dr = ImageDraw.Draw(th)
    dr.rectangle([b[0]*th.width, b[1]*th.height, b[2]*th.width, b[3]*th.height], outline=(163, 43, 34), width=3)
    return {"leaf": lid, "box": b, "why": r["why"], "crop": b64(crop, CROP_Q), "thumb": b64(th, 70)}

# ------------------------------------------------------------------ the register (B read only)
# code, name, status, what, how, ruling
C = [
 # A. in the inventory today
 ("MT","Main text","existing",
  "The body: scripture verses, or the prose of a prelim. The densest regular block of roman type; its left edge is a hard line of aligned line-starts. 47 regions on B, on every kind of leaf except tables, indexes and the blank one.",
  "Find the aligned left edge; it is the largest regular block. On verse pages the numeral column hugs one side of it. Where a rule crosses the measure, the block below it is AN, not MT.",
  "A multi-paragraph prose prelim: ONE block or one per paragraph? (NT 0009, 0011; OT1 0015)"),
 ("MN","Marginal note","existing",
  "Text outside the measure in a smaller fount. 183 of 665 regions on B, 28 % of everything a reader marks. Summary notes, italic citations, alternate readings, dating glosses, numbered side-marks keying a list (OT1 0033, 0339).",
  "Smaller fount, outside the measure, aligned to a body line. Read a few words: prose summary, italic citation, a variant reading, or a bare numeral.",
  "Sub-kinds in §D need a ruling: one class with an attribute, or several? And is LR (below) one more sub-kind, or its own class?"),
 ("RH","Running head","existing",
  "The headline: book name in spaced caps, centred over the measure. On OT leaves a second, topical headline ('Creation.', 'Iacob.', 'Festiual daies.') sits at the GUTTER side — the same slot the NT gives to CR.",
  "Centred over the measure, spaced caps, one line: read it, it names the book. The gutter-side topical title is the same size and sits in the same strip.",
  "Is the gutter-side topical headline RH, MN, or its own class? The 208-plate gold says MN on OT1 0412; I read RH. Now seen on every OT leaf that has one."),
 ("PN","Page number","existing",
  "Arabic numeral at the FORE-EDGE corner of the headline strip, on every paginated leaf. Decides recto/verso, and so decides which side every other thing sits on.",
  "Top corner, fore-edge side, 1–4 digits alone. Recto → right, verso → left. The headline is [gutter: topical or CHA. n.] [centre: book] [fore-edge: number].",
  "Prelims and end-matter have none (OT2 0011, 0012; 1140). A hand-inked number is MS, not PN — confirm."),
 ("VN","Verse number","existing",
  "Thin column of numerals hugging one edge of the measure, one per verse, monotone. Sits gutter-side or fore-edge-side by setting and by recto/verso.",
  "Column of 1–2 digit numerals at the measure edge; check monotone. Never inside the measure.",
  "None. The cascade never separates it from MT; on the 10 scoreable B leaves it mislabelled 5 of them."),
 ("CH","Chapter head","existing",
  "'CHAP. XXVIII.' centred, small caps, above an argument. Twice on B the head and its argument are the LAST thing on the leaf and the chapter opens overleaf (OT1 0982, NT 0564).",
  "Centred, short, reads as CHAP./PSALME./ANNOTATIONS + numeral. A head with nothing under it is still a head.",
  "Sub-kinds (§D): psalm head, annotation-section head, two-line head. Same class?"),
 ("AR","Argument","existing",
  "Italic summary under a chapter head, or a whole italic page at book level (OT1 0352 'THE ARGVMENT OF THE BOOKE OF NVMERI', NT 0617, 0706).",
  "Italic fount, follows a head or a BT, summarises. Read the first words.",
  "Chapter-level and book-level argument: one class or two?"),
 ("DC","Drop capital","existing",
  "The initial opening a chapter, book or index letter: 2-line typographic, 6–8-line woodcut, or a two-sort 'VV'. The index columns open each letter with a 2-line initial too (OT2 1116, NT 0802).",
  "Large glyph at the top-left of a body block, body text set beside it.",
  "Sub-kinds (§D): typographic / woodcut / two-sort. Same class? The cascade mislabelled 6 of them on B."),
 ("SG","Gathering signature","existing",
  "Letter formula on a recto: 'Zz', 'Wwww 3', 'a iij'. Usually at the foot; on B twice set directly under the last text line mid-page or under a tailpiece (NT 0777, 0705).",
  "Letter(s) + optional numeral, below the last line of the measure — wherever that line falls.",
  "Dagger-series prelim signatures included? And is 'below the last line' the rule, rather than 'at the foot'?"),
 ("CW","Catchword","existing",
  "The next page's first word, right-aligned below the last line. On B it can carry the next line's leading sort: '22. Concerning' (NT 0404), '† Shadowes' (OT1 1138).",
  "Single word or syllable at the foot right, may be hyphenated. If a numeral or a cross precedes it, that is part of the catchword.",
  "None. The cascade missed 2 of the scoreable ones."),
 ("??","Abstain with cause","existing",
  "A region the reader sees but the inventory cannot name, or a blank area reported as blank. 24 on B: 20 are blank lower pages, 2 are empty table columns, 1 is a blank leaf, 1 is the acrostic marker column in Lamentations (OT2 0670).",
  "Never force. Name the cause. The three blank causes are proposed as first-class states in §E.",
  "Keep the acrostic markers as a ?? cause, or name them?"),
 # B. text classes invented on the leaves
 ("AN","Annotation body","proposed",
  "Commentary prose in a smaller fount, lemma-led paragraphs, below a rule. 20 regions on B; the pipeline files every one as MT.",
  "Smaller body fount than scripture, no verse numbers, paragraphs open with an italic lemma ending in ']'. The rule above it is the MT/AN boundary.",
  "ACCEPT / MERGE into MT / REJECT"),
 ("LM","Lemma","proposed",
  "The quoted verse words that open an annotation: italic, verse number, closing bracket. One drawn on B (OT1 0296); present at every AN paragraph start.",
  "Italic run at a paragraph start, ends in ']'. The anchor that links AN to the verse.",
  "Region, or an attribute of AN?"),
 ("IG","Interleaved gloss","proposed",
  "Italic gloss lines set BETWEEN roman verse lines inside the measure, Psalter only. Letter-keyed. On OT2 0027 and 0039 the italic lines run past the measure into the margin.",
  "Fount alternates roman/italic line by line within one column; italic lines carry superscript letters.",
  "ACCEPT — a paragraph detector shreds these leaves"),
 ("GK","Gloss-key column","proposed",
  "Lettered notes 'a … b … c …' in a margin column that the IG letters point to. LEFT on 0026/0028, RIGHT on 0027/0039/0279: the side follows recto/verso.",
  "Margin column whose entries begin with single letters in sequence.",
  "Own class, or MN with an attribute?"),
 ("BT","Book / section title","proposed",
  "Display caps naming a book, part, table or age: 'THE BOOKE OF PROVERBES', 'THE END OF THE SECOND AGE' spanning a table, the index letter-heads 'F.' 'H' 'V' 'W', and the whole title page (OT2 0011: six display blocks, imprint, date).",
  "Larger than RH, follows an ornament or a rule, names a thing rather than heading a text.",
  "Is a one-letter index head BT? Is the imprint a BT sub-kind or its own class?"),
 ("HD","Display heading","proposed",
  "Title of a prelim document. On B: 'APPROBATIO.' set INSIDE a woodcut cartouche (OT2 0012) — a heading carried by an ornament.",
  "Multi-line or single-line display type at the head of a prelim; not a book name.",
  "Merge into BT?"),
 ("CR","Chapter running-head","proposed",
  "'CHA. III.' in the headline, NT only. Always at the GUTTER side; PN at the fore-edge. Once spelled 'CHAP.' (NT 0705).",
  "Headline strip, gutter corner, reads CHA. + numeral.",
  "ACCEPT — or attribute of RH? The OT's topical headline is the same slot."),
 ("IX","Index entries","proposed",
  "Two equal columns of alphabetical entries with page refs. Six leaves on B. The cascade scores 0 of 10 and 1 of 12 on them: a single-measure frame cannot see two columns.",
  "Two columns of equal width, hanging indents, lines end in numerals, letter-heads between runs.",
  "ACCEPT / treat as MT with a two-column layout flag?"),
 ("TB","Table","proposed",
  "Ruled chronological table (OT2 1088, 1089, 1093) and the NT lectionary table (0781): header row between double rules, vertical rules, cells with dates, names, prose. Cells can be EMPTY.",
  "Vertical rules; text aligned in cells; a header row. An empty cell is a cell.",
  "ACCEPT; needs header/body/cell sub-structure and the empty-cell state (§E)"),
 ("AT","Attestation block","proposed",
  "Signatory lines on the Approbatio: NAME in caps + office in roman, three entries (OT2 0012).",
  "Caps name + office, stacked, after a prose block.",
  "ACCEPT / merge into MT?"),
 ("LR","Liturgical rubric","proposed",
  "Lectionary directions in the NT margin: 'The Gospel vpõ Holy Roode day, Maij 3.', 'LOVV SVNDAY.', 'HOLY weeke.' at the outer head (NT 0254, 0307). Not commentary, not citation: a use note.",
  "Fore-edge margin, opens with 'The Gospel vpõ' or a feast name in caps, dates in the calendar not in scripture.",
  "NEW on B. Own class, or an MN sub-kind?"),
 # C. not text
 ("OR","Ornament","nonpage",
  "Headpiece, tailpiece, type-ornament band, or — new on B — a four-sided BORDER framing the whole title page (OT2 0011) and a cartouche that carries a heading (0012). Contains no text; marks book and section boundaries.",
  "Dense non-glyph ink, symmetric. A frame runs round all four edges; a band runs across; a piece sits above or below the text.",
  "ACCEPT, with the frame and cartouche sub-kinds (§D). A detector that OCRs a border has failed move 1."),
 ("RL","Printed rule","nonpage",
  "Horizontal or vertical rules: annotation/chapter separators, table rules, headline rules. 29 on B.",
  "Thin straight ink, page-wide or column-tall.",
  "ACCEPT — the rule on NT leaves IS the AN/MT boundary"),
 ("MS","Manuscript and library marks","nonpage",
  "Not type: an ink inscription across the title page top, a pencil shelfmark, a dated library stamp and annotations OVER the signatory block (OT2 0011, 0012).",
  "Irregular ink not aligned to any line; or a stamp's uniform impression over type.",
  "Confirm MS covers stamps, shelfmarks and inscriptions as well as pen strokes"),
 ("ST","Show-through","nonpage",
  "Ghost of the other side's ink, mirror-image, faint. On NT 0706 the recto's signature 'Qqqq' and catchword 'THE' show through where a reader might expect this leaf's own.",
  "Faint mirrored text, usually the facing head, signature or catchword.",
  "ACCEPT (exclude) — and a reader must not file the ghost as this leaf's SG/CW"),
 ("CT","Crop truncation","nonpage",
  "The last line is clipped at the right and the catchword is off the scan (NT 0119).",
  "Line cut mid-word at the image boundary.",
  "ACCEPT — a leaf flag, not a region"),
]

STATES = [
 ("BL","Blank leaf","state",
  "No type, no rule, no ornament, no mark: paper texture and foxing only (OT2 1140). Recto/verso cannot be decided. Every move after 1 is moot.",
  "Move 1 finds the leaf; moves 2–6 find nothing. The correct output is 'blank leaf', not an empty region list and not a search for text. A detector that returns anything here has hallucinated.",
  "First-class output, or a ?? cause?"),
 ("BP","Blank lower page","state",
  "The text ends and the rest of the page is blank: chapter ends, argument pages, index ends. 20 of 54 B leaves.",
  "Everything below the last line, the signature and the catchword. Reported, not searched.",
  "First-class output, or a ?? cause?"),
 ("EC","Empty table cell","state",
  "Whole columns with no ink inside a ruled table: the 'Scriptures' column on OT2 1089, the right-hand cells on 1088.",
  "A cell bounded by rules with no ink. Reported as empty; the table's structure still counts it.",
  "First-class output (needed by TB), or a ?? cause?"),
]

SUB = [
 ("MN sub-kinds", "summary note (roman prose) · citation note (italic refs) · alternate reading ('* or, …') · Greek note · dating gloss · numbered side-mark ('1.' '2.' keying a list, OT1 0033, 0339) · liturgical rubric (LR, NT 0254, 0307)", "One class + attribute, or several classes? LR is the one B added."),
 ("OR sub-kinds", "headpiece · tailpiece · type-ornament band · four-sided BORDER framing a title page (OT2 0011) · cartouche carrying a heading (OT2 0012)", "Same class with a kind attribute? The frame is the only OR that surrounds text."),
 ("MS scope", "pen inscription (OT2 0011) · shelfmark (0012) · dated library stamp OVER type (0012) · hand foliation", "All MS? The stamp overlays type that still has to be read."),
 ("CH sub-kinds", "chapter head · psalm head ('PSALME. III.') · annotation-section head ('ANNOTATIONS. PSALME. III.') · head + argument with the body overleaf (OT1 0982, NT 0564)", "Same class?"),
 ("DC sub-kinds", "2-line typographic · 6–8-line woodcut · two-sort 'VV' · index-letter 2-line initial (NT 0802, OT2 1116)", "Same class? Detection differs completely."),
 ("RH vs topical headline", "'NVMERI.' (book name, centre) vs 'Creation.' / 'Iacob.' / 'Festiual daies.' (topical, GUTTER side). Gold on 0412 says MN; I say RH. The NT puts CR in that slot.", "Ruling needed; on every OT leaf with one."),
 ("BT sub-kinds", "book title · part title · table age-heading spanning the columns · index letter-head ('F.') · title-page blocks: title, subtitle, description, publisher, imprint, date (OT2 0011)", "Is the title page one BT with parts, or six?"),
 ("SG placement", "at the foot · directly under the last line mid-page (NT 0777) · under a tailpiece (NT 0705)", "Rule = 'below the last line', not 'at the foot'?"),
 ("CW with a leading sort", "'22. Concerning' (NT 0404) · '† Shadowes' (OT1 1138)", "The numeral / cross is part of the catchword?"),
 ("AR chapter vs book", "3-line italic under CHAP. vs a whole italic page", "Same class?"),
 ("MT one vs many", "A prose prelim in several paragraphs: one block or one each?", "Ruling needed for NT 0009, 0011; OT1 0015."),
]

NOT_ON_B = [("FN","End marker","'FINIS.' — the P leaves that carried it map to B table pages"),
            ("XP","Off-page","B is cropped to the leaf; no scanner surround seen"),
            ("AP","Adjacent-page bleed","not seen on the 54 B leaves")]

STATUS_LABEL = {"existing":"in the inventory today","proposed":"proposed — text","nonpage":"proposed — not text","state":"proposed — reportable state"}

# ------------------------------------------------------------------ build exemplars
EX = {}
for code, *_ in C + STATES:
    src = STATE_SRC.get(code, code)
    if code in PICK:
        recs = [(lid, find(lid, pre, src)) for lid, pre in PICK[code]]
    else:
        recs = auto(code)
    EX[code] = [exemplar(lid, r) for lid, r in recs]
    print(f"{code:3} {len(EX[code])} exemplars  {' · '.join(l for l,_ in recs)}")

# ------------------------------------------------------------------ lightbox data
regions = {lid: [{"b": r["box"], "c": r["class"], "w": r["why"][:90]} for r in l["regions"]] for lid, l in LEAVES.items()}
leaf_b64 = {}
for lid in LEAVES:
    im = leaf_img(lid); W, H = im.size
    if W > LEAF_W: im = im.resize((LEAF_W, round(H*LEAF_W/W)), Image.LANCZOS)
    leaf_b64[lid] = b64(im, LEAF_Q)
print(f"{len(leaf_b64)} leaves embedded, {sum(map(len, leaf_b64.values()))/1e6:.1f} MB")

# ------------------------------------------------------------------ levelling survey + gold set
SURVEY = json.load(open(CR.parent / "plates" / "skew-survey-B.json"))
GOLD1 = json.load(open(CR.parent / "plates" / "gold-set-1-proposed.json"))
WARP_SPREAD = 0.5
def volstats(v):
    ks = [abs(r["skew"]) for l, r in SURVEY.items() if l.startswith(v)]
    return len(ks), max(ks), sum(1 for k in ks if k > 0), sum(1 for l, r in SURVEY.items() if l.startswith(v) and r["spread"] > WARP_SPREAD)
FIGS = {}
for lid in ("OT1-1609-B_0409", "OT2-1610-B_0026", "NT-1582-B_0562", "NT-1582-B_0781"):
    FIGS[lid] = base64.b64encode(open(SP / "level-figs" / f"{lid}.jpg", "rb").read()).decode()
def figcap(lid):
    r = SURVEY[lid]; q = r["quarters"]
    qs = " · ".join(f"{k} {('—' if v is None else f'{v:+.2f}°')}" for k, v in q.items())
    return f"page {r['skew']:+.2f}° · quarters {qs} · spread {r['spread']:.2f}°"
levelfigs = "\n".join(f'<figure class="lf"><img src="data:image/jpeg;base64,{b}" alt="{esc(lid)} raw and levelled with per-quarter line angles"><figcaption><b>{esc(lid)}</b> — {esc(figcap(lid))}</figcaption></figure>' for lid, b in FIGS.items())
warped = sorted((l for l, r in SURVEY.items() if r["spread"] > WARP_SPREAD), key=lambda l: -SURVEY[l]["spread"])
warprows = "".join(f"<tr><td class=k>{esc(l)}</td><td>{SURVEY[l]['skew']:+.2f}</td><td>{SURVEY[l]['spread']:.2f}</td><td>{SURVEY[l]['lr']:.2f}</td><td>{SURVEY[l]['tb']:.2f}</td><td class=q>{esc(LEAVES[l].get('kind','')[:80])}</td></tr>" for l in warped)
goldrows = "".join(f"<tr><td class=k>{esc(g['id'])}</td><td>{g['skew']:+.2f}</td><td>{'warp' if g['warp'] else ''}</td><td>{esc(' '.join(g['classes']))}</td><td class=q>{esc(g['kind'][:90])}</td></tr>" for g in GOLD1["leaves"])
vs = {v: volstats(v) for v in ("NT-1582-B", "OT1-1609-B", "OT2-1610-B")}
volrows = "".join(f"<tr><td class=k>{v}</td><td>{n}</td><td>{mx:.2f}°</td><td>{nz}</td><td>{nw}</td></tr>" for v, (n, mx, nz, nw) in vs.items())
MAXSKEW = max(abs(r["skew"]) for r in SURVEY.values())

# ------------------------------------------------------------------ html pieces
def plate(cls):
    out = []
    for r in EX.get(cls, [])[:2]:
        box = ",".join(str(v) for v in r["box"])
        out.append(
f'''<figure class="ex">
  <img class="crop" tabindex="0" role="button" data-leaf="{esc(r["leaf"])}" data-box="{box}" src="data:image/jpeg;base64,{r["crop"]}" alt="{esc(cls)} exemplar on {esc(r["leaf"])} — open full leaf">
  <div class="loc"><img tabindex="0" role="button" data-leaf="{esc(r["leaf"])}" data-box="{box}" src="data:image/jpeg;base64,{r["thumb"]}" alt="locator for {esc(r["leaf"])} — open full leaf">
    <figcaption><b>{esc(r["leaf"])}</b><br>{esc(r["why"])}</figcaption></div>
</figure>''')
    return "\n".join(out)

def section(code, name, status, what, how, ruling):
    n = counts.get(code, 0); nl = len(per_leaf.get(code, ()))
    tally = f"{n} regions on {nl} leaves" if n else "state, recorded under ??"
    if status == "state":
        verdict = f'''<label><input type="radio" name="v-{esc(code)}" value="accept"> first-class output</label>
        <label><input type="radio" name="v-{esc(code)}" value="merge"> keep as a ?? cause</label>
        <label><input type="radio" name="v-{esc(code)}" value="reject"> reject</label>'''
    else:
        verdict = f'''<label><input type="radio" name="v-{esc(code)}" value="accept"> accept</label>
        <label><input type="radio" name="v-{esc(code)}" value="merge"> merge</label>
        <label><input type="radio" name="v-{esc(code)}" value="rename"> rename</label>
        <label><input type="radio" name="v-{esc(code)}" value="reject"> reject</label>'''
    return f'''
<section class="cls {status}" id="c-{esc(code).replace('?','q')}" data-code="{esc(code)}">
  <header class="ch">
    <span class="code">{esc(code)}</span>
    <h3>{esc(name)}</h3>
    <span class="tally">{esc(tally)}</span>
    <span class="status">{esc(STATUS_LABEL[status])}</span>
  </header>
  <div class="body">
    <div class="text">
      <p class="what">{esc(what)}</p>
      <p class="how"><span class="lbl">how a reader decides</span>{esc(how)}</p>
      <p class="ruling"><span class="lbl">ruling needed</span>{esc(ruling)}</p>
      <div class="verdict" role="group" aria-label="verdict for {esc(code)}">
        {verdict}
        <input type="text" class="note" placeholder="note, or merge target / new name" aria-label="note for {esc(code)}">
      </div>
    </div>
    <div class="plates">{plate(code)}</div>
  </div>
</section>'''

rows = "".join(section(*c) for c in C)
staterows = "".join(section(*s) for s in STATES)

subrows = "\n".join(f'''<tr><td class="k">{esc(a)}</td><td>{esc(b)}</td><td class="q">{esc(c)}</td>
<td><select aria-label="ruling for {esc(a)}" data-sub="{esc(a)}"><option value="">—</option><option>one class + attribute</option><option>separate classes</option><option>other (note)</option></select>
<input type="text" class="note" data-sub-note="{esc(a)}" placeholder="note" aria-label="note for {esc(a)}"></td></tr>''' for a, b, c in SUB)

notb = " · ".join(f"<b>{esc(c)}</b> {esc(n)} — {esc(w)}" for c, n, w in NOT_ON_B)

top = counts.most_common()[0][1]
bars = "\n".join(f'<div class="bar"><span class="t">{esc(k)}</span><span class="track"><span class="fill" style="width:{v/top*100:.1f}%"></span></span><span class="v">{v}</span></div>' for k, v in counts.most_common())
jump = "".join(f'<a href="#c-{c[0].replace("?","q")}">{esc(c[0])}</a>' for c in C) + "".join(f'<a href="#c-{s[0]}" class="st">{esc(s[0])}</a>' for s in STATES) + '<a href="#sub">sub-kinds</a><a href="#export">export</a>'

n_existing = sum(1 for c in C if c[2]=="existing"); n_prop = sum(1 for c in C if c[2]=="proposed"); n_non = sum(1 for c in C if c[2]=="nonpage")
vols = collections.Counter(vol(l) for l in LEAVES)

css = (SP / "register.css").read_text()
css += '''
.tally{font-family:var(--mono);font-size:.7rem;color:var(--grey);letter-spacing:.04em}
.cls.state .code{color:var(--olive)}
.jump a.st{border-style:dashed}
.legend i.st{background:var(--olive)}
.lf{margin:0 0 1.2rem;background:var(--plate-bg);padding:.6rem;border-radius:2px}
.lf img{width:100%;display:block}
.lf figcaption{font-family:var(--mono);font-size:.68rem;color:var(--ink-2);margin-top:.4rem;line-height:1.5}
.lvl{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:1.2rem 2rem;align-items:start}
@media (max-width:820px){.lvl{grid-template-columns:1fr}}
.notb{font-family:var(--mono);font-size:.74rem;color:var(--ink-2);line-height:1.6;margin:1rem 0 0}
.notb b{color:var(--grey)}
.changed{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:.9rem 2rem;margin:1rem 0 0;padding:0;list-style:none;font-size:.95rem}
.changed li b{display:block;font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--rubric);margin-bottom:.15rem}
.ex img[role=button]{cursor:zoom-in} .ex img[role=button]:focus{outline:2px solid var(--slate);outline-offset:2px}
.hint{font-family:var(--mono);font-size:.68rem;color:var(--grey);margin:.4rem 0 0}
#lb{position:fixed;inset:0;background:rgba(10,8,6,.94);z-index:50;display:grid;grid-template-rows:auto 1fr;color:#E6E1D6}
#lb .bar{display:flex;gap:1rem;align-items:center;padding:.6rem 1rem;font-family:var(--mono);font-size:.76rem;border-bottom:1px solid #37322C;flex-wrap:wrap}
#lb .bar b{color:#fff} #lb .bar .sp{flex:1}
#lb button{background:transparent;color:#E6E1D6;border:1px solid #8A8377}
#lb .stage{overflow:auto;padding:1rem;display:flex;justify-content:center;align-items:flex-start}
#lb .wrap{position:relative;display:inline-block;line-height:0}
#lb .wrap img{display:block;max-width:none}
#lb svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
#lb rect{fill:none;stroke:#7FA8BC;stroke-width:1.5;vector-effect:non-scaling-stroke}
#lb rect.hi{stroke:#D9695C;stroke-width:3;fill:rgba(217,105,92,.12)}
#lb text{font:11px "IBM Plex Mono",Menlo,monospace;fill:#fff;paint-order:stroke;stroke:#141210;stroke-width:3px}
#lb .keys{font-size:.68rem;color:#8A8377}
'''

page = '''<title>LECTOR Class Register</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
%%CSS%%
</style>
<div class="sheet">
<p class="eyebrow">OriginalDR · LECTOR · rebuilt from the B witness · levelled · 5 September 2026 · for Sir's ruling</p>
<div class="top">
  <div>
    <h1>LECTOR Class Register</h1>
    <p class="lede">Every kind of thing a reader found on <b>54 leaves of the base setting</b> (S09, ~545 ppi, real capture), 18 per volume, drawn from the image alone. <b>%%NREG%% regions, %%NCLS%% classes, 3 reportable states.</b> This replaces the 35-leaf register built on the P surrogate: every class from those rounds recurred here, so the inventory is a property of the printing, not the scan.</p>
    <div class="legend"><span><i style="background:var(--slate)"></i>in the inventory today (%%NEX%%)</span><span><i style="background:var(--rubric)"></i>proposed text class (%%NPROP%%)</span><span><i style="background:var(--amber)"></i>proposed non-text (%%NNON%%)</span><span><i class="st"></i>reportable state (3)</span></div>
    <nav class="jump" aria-label="jump to class"><a href="#level">level</a><a href="#gold1">gold set 1</a>%%JUMP%%</nav>
    <p class="notb">In the P register, not met on B: %%NOTB%%</p>
  </div>
  <div>
    <p class="eyebrow">regions per class, 54 B leaves · NT %%VNT%% · OT1 %%VOT1%% · OT2 %%VOT2%%</p>
    <div class="bars">%%BARS%%</div>
    <p class="cap">MN alone is 28 %% of everything a reader marks. Seven classes appear on one or two leaves — they are real, and the corpus has more of them.</p>
  </div>
</div>

<div class="sechead"><span class="num">WHAT B ADDED</span><h2>The base setting changed the inventory very little</h2></div>
<ul class="changed">
  <li><b>LR liturgical rubric</b>Lectionary directions in the NT margin. Not commentary, not citation. A new class, or a new MN sub-kind — the first new text class since round 2.</li>
  <li><b>Headline rule, now universal</b>Topical title (OT) and CHA. n. (NT) sit at the gutter; the page number at the fore-edge; the book name centred. Recto/verso decides which side is which.</li>
  <li><b>Title page and Approbatio</b>A four-sided type-ornament border, a heading set inside a woodcut cartouche, library stamps over type, a signatory block. Two leaves, five classes stretched.</li>
  <li><b>Blank leaf, blank lower page, empty cell</b>Three things a reader reports rather than searches. Proposed in §E as outputs in their own right, not causes of abstention.</li>
  <li><b>Signature and catchword drift</b>A signature set mid-page under the last line; a catchword carrying the next line's numeral or cross. The rules are relational, not positional.</li>
  <li><b>Show-through of the facing signature</b>A mirror ghost of the recto's Qqqq where this leaf's own would sit. The reader must not file the ghost as SG or CW.</li>
</ul>

<hr class="rule">
<div class="sechead"><span class="num">THE PROCEDURE</span><h2>Six moves, the same order on every leaf</h2></div>
<p class="hint">Click any plate or locator to open the whole leaf at full size with every region I drew on it; the exemplar is red, the rest slate. ← → steps between exemplars on the same leaf.</p>
<p class="lede" style="font-size:1rem">No box is drawn until move 4. This is what LECTOR-as-director has to reproduce; the classes below are what move 5 has to be able to say. On the blank leaf, move 1 is the only move.</p>
<ol class="moves">
  <li><b>What part of the image is the leaf?</b> Discount scanner surround, the facing page's bleed, show-through, a cropped edge. On B the leaf fills the image; show-through and cropping remain.</li>
  <li><b>Orient, then level.</b> Recto or verso, from the page-number corner and whether a signature exists. Then one angle for the whole leaf, from the text lines, so every box that follows is plumb by construction. The angle is a datum in the record; a leaf one angle cannot level is flagged warped.</li>
  <li><b>Name the page kind.</b> Verse numbers at the measure edge → scripture. One prose measure, no numbers → prelim or annotations. Centred CHAP. → break page. Rules, ornaments, two columns → table, index, book opening, title page.</li>
  <li><b>Find the measure from the type, then bound the body.</b> The hard left edge of aligned line-starts. Then place every other class by relation to it.</li>
  <li><b>Read a few words before classifying.</b> "CHAP." is a head because it says so. "Zz" is a signature because it is a letter formula. "The Gospel vpõ" is a rubric because it names a feast.</li>
  <li><b>Check the page against itself; abstain where there is no word.</b> Verse numbers monotone. Blank reported as blank. Empty cells reported as empty. Acrostic markers left unnamed rather than misfiled.</li>
</ol>

<hr class="rule">
<div class="sechead" id="level"><span class="num">LEVEL</span><h2>One angle per leaf, measured on all 54</h2><p>The forme was one rigid body when it was printed, so every block on a leaf shares one skew. Boxes are stored in the levelled frame. Rotating boxes one by one would add a free parameter per region and hide the one case that matters: a leaf that is not rigid.</p></div>
<div class="lvl">
  <div>
    <p class="what">Largest skew in the sample is <b>%%MAXSKEW%%°</b>. The record refuses anything beyond ±6°, a ceiling set so the levelled canvas never clips more than a tenth of its width; the data sits far inside it. The NT witness reads level on every leaf: the archive had already squared it. Both OT witnesses are raw captures and tilt up to two and a third degrees either way.</p>
    <div class="tw"><table><thead><tr><th>witness</th><th>leaves</th><th>max |skew|</th><th>tilted</th><th>warp flagged</th></tr></thead><tbody>%%VOLROWS%%</tbody></table></div>
    <p class="how"><span class="lbl">how the angle is found</span>Trim the scan border, measure ink against the paper, rotate through ±3° and take the angle at which the row-ink profile is spikiest, i.e. the lines are level. Coarse sweep, then 0.02° steps. A confidence below 1.5 means there are no lines to level, and the leaf is left at zero rather than given a number.</p>
    <p class="how"><span class="lbl">how warped is decided</span>The same measurement in each quarter of the leaf. A rigid tilt gives four near-equal angles. If the quarters disagree by more than 0.5° after the page is levelled, one angle cannot enclose every block and the leaf is flagged. Thirteen of 54 trip that threshold; the table names them. Quarters without regular lines, an ornament, a blank foot, interleaved italic, are left out of the spread, which is the method's blind spot.</p>
    <div class="tw"><table><thead><tr><th>leaf</th><th>page °</th><th>spread °</th><th>left–right</th><th>top–bottom</th><th>kind</th></tr></thead><tbody>%%WARPROWS%%</tbody></table></div>
    <p class="ruling"><span class="lbl">the warped leaves: proposed approach</span>Gutter curl is a bend, not a tilt: the local angle changes smoothly with distance from the spine. The fix that keeps boxes axis-aligned is a strip-wise dewarp. Measure the angle in vertical strips across the leaf, fit a smooth curve, and resample the raster so every strip is level. The record stores the curve as the leaf's second datum beside the skew, and the reader applies both, so consumers still score against one canonical raster. Until that exists a warped leaf stays corrected, not accepted, unless its boxes enclose their blocks cleanly on the levelled page. Ruling needed: build the dewarp before the first Gold Set is locked, or lock the rigid leaves first and hold the thirteen.</p>
  </div>
  <div>%%LEVELFIGS%%</div>
</div>

<hr class="rule">
<div class="sechead" id="gold1"><span class="num">GOLD SET 1</span><h2>Nineteen leaves proposed for the first locked set</h2><p>Chosen by class cover: every one of the 27 classes appears at least once, at 6/6/7 per volume. The structural leaves are forced in, the blank leaf, the title page, the Approbatio, the Psalter, the table, the index, the rubric leaf, and the rest are the most tilted rigid leaves so the levelling is exercised. I read them, you correct and accept in the Plate Tool, the reader locks them.</p></div>
<div class="tw"><table><thead><tr><th>leaf</th><th>skew °</th><th></th><th>classes on it</th><th>kind</th></tr></thead><tbody>%%GOLDROWS%%</tbody></table></div>

<hr class="rule">
<div class="sechead"><span class="num">A · B · C</span><h2>The register</h2><p>A: classes already in the inventory, with the rulings they still need. B: text classes that had to be invented on the leaves. C: things in the image that are not text. Every exemplar is a B leaf.</p></div>
%%ROWS%%

<hr class="rule">
<div class="sechead" id="states"><span class="num">E</span><h2>Reportable states</h2><p>Three findings the reader reports rather than searches for. Today they are recorded as ?? with a cause. The question is whether the director's output vocabulary needs them as first-class words.</p></div>
%%STATES%%

<hr class="rule">
<div class="sechead" id="sub"><span class="num">D</span><h2>Sub-kinds a reader distinguishes by content</h2><p>One class with an attribute, or separate classes? The transcription treats them differently; detection differs too.</p></div>
<div class="tw sub"><table>
<thead><tr><th>class</th><th>the kinds seen on B</th><th>the question</th><th>ruling</th></tr></thead>
<tbody>%%SUBROWS%%</tbody></table></div>

<hr class="rule">
<div class="sechead" id="export"><span class="num">EXPORT</span><h2>Your rulings</h2><p>Saved in this browser as you go. Copy the JSON into the repo as <code>witness/cold-read/class-rulings.json</code>; it becomes the inventory the director is held to.</p></div>
<div class="export">
  <div class="row"><button id="copy">Copy JSON</button><button class="quiet" id="clear">Clear all</button><span class="toast" id="toast"></span></div>
  <textarea id="out" readonly aria-label="rulings as JSON"></textarea>
</div>
</div>

<div id="lb" hidden role="dialog" aria-modal="true" aria-label="Leaf at full size with regions">
  <div class="bar"><b id="lb-leaf"></b><span id="lb-n"></span><span class="sp"></span>
    <label><input type="checkbox" id="lb-labels" checked> labels</label>
    <label><input type="checkbox" id="lb-all" checked> all regions</label>
    <button id="lb-zoom">fit ↔ 1:1</button><button id="lb-close">Close &nbsp;Esc</button>
    <span class="keys">← → step exemplars on this leaf · click backdrop to close</span></div>
  <div class="stage"><div class="wrap"><img id="lb-img" alt=""><svg id="lb-svg" viewBox="0 0 1000 1000" preserveAspectRatio="none"></svg></div></div>
</div>
<script id="leaves-data" type="application/json">%%REGIONS%%</script>
<script id="leaves-img" type="application/json">%%LEAFIMG%%</script>
<script>
(function(){
  var R=JSON.parse(document.getElementById('leaves-data').textContent);
  var LEAF_IMG=JSON.parse(document.getElementById('leaves-img').textContent);
  var lb=document.getElementById('lb'),img=document.getElementById('lb-img'),svg=document.getElementById('lb-svg'),
      title=document.getElementById('lb-leaf'),nn=document.getElementById('lb-n'),fit=true,cur=null,last=null;
  function draw(leaf,hiBox){
    var regs=R[leaf]||[],all=document.getElementById('lb-all').checked,labels=document.getElementById('lb-labels').checked;
    var s='';
    regs.forEach(function(r){
      var b=r.b,hi=hiBox&&b.join(',')===hiBox;
      if(!all&&!hi)return;
      s+='<rect class="'+(hi?'hi':'')+'" x="'+(b[0]*1000)+'" y="'+(b[1]*1000)+'" width="'+((b[2]-b[0])*1000)+'" height="'+((b[3]-b[1])*1000)+'"><title>'+r.c+' — '+r.w.replace(/[<&]/g,'')+'</title></rect>';
      if(labels)s+='<text x="'+(b[0]*1000+3)+'" y="'+(b[1]*1000+12)+'">'+r.c+'</text>';
    });
    svg.innerHTML=s;
    nn.textContent=regs.length+' regions'+(hiBox?' · exemplar in red':'');
  }
  function size(){ var w=img.naturalWidth,h=img.naturalHeight; if(!w)return;
    if(fit){var st=lb.querySelector('.stage'),k=Math.min((st.clientWidth-32)/w,(st.clientHeight-32)/h,1);img.style.width=(w*k)+'px';img.style.height=(h*k)+'px';}
    else{img.style.width=w+'px';img.style.height=h+'px';} }
  function open(leaf,box){
    cur={leaf:leaf,box:box}; title.textContent=leaf; img.src=LEAF_IMG[leaf]?'data:image/jpeg;base64,'+LEAF_IMG[leaf]:''; img.alt=leaf;
    img.onload=function(){size();}; draw(leaf,box);
    lb.hidden=false; document.body.style.overflow='hidden'; document.getElementById('lb-close').focus();
  }
  function close(){ lb.hidden=true; document.body.style.overflow=''; if(last){last.focus();last=null;} }
  document.querySelectorAll('.ex img[role=button]').forEach(function(el){
    function go(){ last=el; open(el.dataset.leaf,el.dataset.box); }
    el.addEventListener('click',go); el.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){e.preventDefault();go();} });
  });
  document.getElementById('lb-close').addEventListener('click',close);
  document.getElementById('lb-zoom').addEventListener('click',function(){fit=!fit;size();});
  document.getElementById('lb-all').addEventListener('change',function(){ if(cur)draw(cur.leaf,cur.box); });
  document.getElementById('lb-labels').addEventListener('change',function(){ if(cur)draw(cur.leaf,cur.box); });
  lb.addEventListener('click',function(e){ if(e.target===lb||e.target.classList.contains('stage'))close(); });
  window.addEventListener('resize',size);
  document.addEventListener('keydown',function(e){
    if(lb.hidden)return;
    if(e.key==='Escape')close();
    if(e.key==='ArrowRight'||e.key==='ArrowLeft'){
      var els=Array.prototype.slice.call(document.querySelectorAll('.ex img.crop[role=button][data-leaf="'+cur.leaf+'"]'));
      if(els.length<2)return; var i=els.findIndex(function(x){return x.dataset.box===cur.box});
      var n=els[(i+(e.key==='ArrowRight'?1:els.length-1))%els.length]; open(cur.leaf,n.dataset.box);
    }
  });
})();
</script>
<script>
(function(){
  var KEY='lector-class-rulings-v1';
  function load(){ try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return {}} }
  function save(s){ try{localStorage.setItem(KEY,JSON.stringify(s))}catch(e){} }
  var state=load();
  function render(){
    var out={"_doc":"LECTOR class rulings, from the Class Register artifact (B rebuild)","when":new Date().toISOString(),"classes":{},"subkinds":{}};
    document.querySelectorAll('.cls').forEach(function(sec){
      var code=sec.dataset.code, r=sec.querySelector('input[type=radio]:checked'), n=sec.querySelector('.note').value.trim();
      if(r||n) out.classes[code]={verdict:r?r.value:null,note:n};
    });
    document.querySelectorAll('select[data-sub]').forEach(function(sel){
      var k=sel.dataset.sub, n=document.querySelector('[data-sub-note="'+k+'"]').value.trim();
      if(sel.value||n) out.subkinds[k]={ruling:sel.value||null,note:n};
    });
    document.getElementById('out').value=JSON.stringify(out,null,1);
    return out;
  }
  function persist(){ var o=render(); save({classes:o.classes,subkinds:o.subkinds}); }
  Object.keys(state.classes||{}).forEach(function(code){
    var sec=document.querySelector('.cls[data-code="'+code.replace(/"/g,'')+'"]'); if(!sec)return;
    var v=state.classes[code]; if(v.verdict){var r=sec.querySelector('input[value="'+v.verdict+'"]'); if(r)r.checked=true;}
    sec.querySelector('.note').value=v.note||'';
  });
  Object.keys(state.subkinds||{}).forEach(function(k){
    var sel=document.querySelector('select[data-sub="'+k+'"]'), nt=document.querySelector('[data-sub-note="'+k+'"]'); if(!sel)return;
    sel.value=state.subkinds[k].ruling||''; nt.value=state.subkinds[k].note||'';
  });
  document.addEventListener('change',persist); document.addEventListener('input',persist);
  document.getElementById('copy').addEventListener('click',function(){
    var ta=document.getElementById('out'); ta.select();
    var t=document.getElementById('toast');
    if(navigator.clipboard){navigator.clipboard.writeText(ta.value).then(function(){t.textContent='Copied.'},function(){t.textContent='Select-all in the box and copy.'});}
    else t.textContent='Select-all in the box and copy.';
    setTimeout(function(){t.textContent=''},2500);
  });
  document.getElementById('clear').addEventListener('click',function(){
    document.querySelectorAll('.cls input[type=radio]').forEach(function(r){r.checked=false});
    document.querySelectorAll('.note').forEach(function(n){n.value=''});
    document.querySelectorAll('select[data-sub]').forEach(function(s){s.value=''});
    persist(); document.getElementById('toast').textContent='Cleared.';
  });
  render();
})();
</script>
'''

for k, v in {
    "%%CSS%%": css, "%%NREG%%": str(N_REG), "%%NCLS%%": str(len(C)),
    "%%NEX%%": str(n_existing), "%%NPROP%%": str(n_prop), "%%NNON%%": str(n_non),
    "%%JUMP%%": jump, "%%NOTB%%": notb, "%%BARS%%": bars,
    "%%VNT%%": str(vols["NT-1582-B"]), "%%VOT1%%": str(vols["OT1-1609-B"]), "%%VOT2%%": str(vols["OT2-1610-B"]),
    "%%ROWS%%": rows, "%%STATES%%": staterows, "%%SUBROWS%%": subrows,
    "%%REGIONS%%": json.dumps(regions).replace("</", "<\\/"),
    "%%MAXSKEW%%": f"{MAXSKEW:.2f}", "%%VOLROWS%%": volrows, "%%WARPROWS%%": warprows, "%%GOLDROWS%%": goldrows, "%%LEVELFIGS%%": levelfigs,
    "%%LEAFIMG%%": json.dumps(leaf_b64),
}.items():
    page = page.replace(k, v)
page = page.replace("28 %% of", "28 % of")

out = SP / "lector-class-register-B.html"
out.write_text(page)
print(f"{out.name}: {len(page.encode())/1e6:.1f} MB")
