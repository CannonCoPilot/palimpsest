#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builder for the Gold Transcript of "An Historical Table" (OT2 1610 back matter).
Emits ocr-spike/ground-truth/matter-ot2-historical-table.json.

Model: the section is a 24-page synoptic chronological table (printed pp. 1073-1096)
organised by the Six Ages of the World. Columns FLOW INDEPENDENTLY top-to-bottom;
the only cross-column linkage is the keying letter (a..z, resetting) shared by the
Anni-mundi column and the sacred-historie column. Reading order chosen per page is
COLUMN BY COLUMN (col1 fully, then col2, ...). Body = logical cell-entries (each the
full de-hyphenated diplomatic text of one element, tagged with column + role + letter).
Intervals = the canonical scoreable rows (1 per content body entry; display title and
age dividers grouped as title_block/heading). Apparatus = running headers, page
numbers, quire signatures, ornament, frame rules.
"""
import json, unicodedata
from pathlib import Path

OUT = Path("ocr-spike/ground-truth/matter-ot2-historical-table.json")

body = []            # every element, entry-grained
intervals = []       # canonical scoreable rows
apparatus = []       # running headers, page numbers, signatures, ornaments
pages_meta = []      # per-page metadata
uncertain = []       # flagged ambiguous glyphs/readings

_ctx = {}

def page(pi, label, source, cols, rh=None, note=None):
    """Begin a page. rh = (left,center,right) running header, or None for the title page."""
    _ctx["pi"] = pi; _ctx["label"] = label; _ctx["source"] = source
    pages_meta.append({
        "page_index": pi, "page_label_printed": label, "scan_source": source,
        "columns_printed": cols, "running_header": rh, "note": note,
    })

def _add(role, text, column=None, letter=None, hyph=False, note=None, unc=False,
         as_interval=True, kind="table_row"):
    li = len(body)
    e = {"line_index": li, "page_index": _ctx["pi"], "page_label": _ctx["label"],
         "scan_source": _ctx["source"], "column": column, "role": role, "text": text}
    if letter is not None: e["letter"] = letter
    if note: e["note"] = note
    if unc: e["has_uncertain"] = True
    body.append(e)
    if as_interval:
        iv = {"idx": len(intervals), "kind": kind, "column": column,
              "page_index": _ctx["pi"], "text": text, "lines": [li]}
        if letter is not None: iv["letter"] = letter
        intervals.append(iv)
    return li

# convenience wrappers -------------------------------------------------------
def title(text):        return _add("title_display", text, column=None, as_interval=True, kind="title_block")
def divider(text):      return _add("age_divider", text, column=None, as_interval=True, kind="heading")
def anni(letter, text, note=None, unc=False): return _add("year_entry", text, column="anni", letter=letter, note=note, unc=unc)
def g1(text, note=None, unc=False):  return _add("genealogy", text, column=_ctx["g1col"], note=note, unc=unc)
def g2(text, note=None, unc=False):  return _add("genealogy", text, column=_ctx["g2col"], note=note, unc=unc)
def hist(letter, text, note=None, unc=False): return _add("historie_entry", text, column="historie", letter=letter, note=note, unc=unc)
def schis(text, letter=None, note=None, unc=False): return _add("schismes_text", text, column="schismes", letter=letter, note=note, unc=unc)
def scrip(text, letter=None, note=None, unc=False):  return _add("scriptures_text", text, column="scriptures", letter=letter, note=note, unc=unc)

def gcols(c1, c2=None):
    _ctx["g1col"] = c1; _ctx["g2col"] = c2

def header_line(text):
    # column-header text captured as apparatus (structural label, not a scoreable row)
    apparatus.append({"kind": "column_headers", "page_index": _ctx["pi"], "text": text})

def sig(text):
    apparatus.append({"kind": "quire_signature", "page_index": _ctx["pi"], "text": text,
                      "note": "quire/gathering signature (binder's mark) at foot; excluded from text concatenation"})

def runhead(left, center, right):
    apparatus.append({"kind": "running_header", "page_index": _ctx["pi"],
                      "left": left, "center": center, "right": right})

def unc(page_index, span, note):
    uncertain.append({"page_index": page_index, "span": span, "note": note})

# ============================ PAGES ============================

# ---- printed 1073 (index 1077, S1) : FIRST AGE opens ----
page(1077, "1073", "S1", ["Anni mundi.", "Patriarches.",
     "Eſpecial pointes of the ſacred hiſtorie of Gods Church euer viſible.",
     "Schiſmes and infidelitie.", "Canonical Scriptures."],
     rh=("", "", "1073"),
     note="Section-opening leaf: horizontal band of printer's-flower ornaments, then the display title. Page number top-right 1073; no running-header words on this leaf.")
runhead("", "", "1073")
header_line("Anni mundi. | Patriarches. | Eſpecial pointes of the ſacred hiſtorie of Gods Church euer viſible. | Schiſmes and infidelitie. | Canonical Scriptures.")
gcols("patriarches")
title("AN HISTORICAL TABLE OF THE")
title("TIMES, SPECIAL PERSONS, MOST")
title("NOTABLE THINGES, AND CANONICAL")
title("BOOKES OF THE OLD TESTAMENT.")
anni("a", "The firſt yeare & firſt weeke.")
anni("b", "130.")
anni("c", "235.")
anni("d", "325.")
anni("e", "395.")
anni("f", "460.")
g1("Adam the firſt man, of whom al mankind is propagated.")
g1("Seth borne.")
g1("Enos borne.")
g1("Cainan")
g1("Malaleel")
g1("Iared,")
hist("a", "Creation of heauen and earth, and al thinges therin, in ſix dayes. Gen. 1.")
hist(None, "Man laſt created was made lord of al corporal creatures of this lower world, & placed in paradiſe. Gen. 2.")
hist(None, "For tranſgreſſing Gods commandment Adam and Eue were caſt out of paradiſe. But by Gods grace repenting had promiſe of a Redemer. Gen. 3.")
hist("¶", "Cain the firſt borne became, a husbandman, Abel next borne, a ſhepheard. Gen. 4.")
hist(None, "God reſpecting Abels ſacrifice, and not Cains, Cain killed Abel. Gen. 4.")
hist(None, "Seths children and other faythful were called the ſonnes of God to diſtinguiſh the true Church from the wicked citie begune by Cain. Gen. 6.")
hist(None, "In the dayes of Enos begane publique prayers of manie aſſembling together ( beſides Sacrifice, which was before ) Gen. 4. v. 26.")
schis("Cain went forth from the face of our Lord ; begane a new city oppoſite to the Citie of God. Gen. 4. v. 16.")
schis("His generations in the right line to Lamech, who ſlew him, are theſe, without notice of time when they")
scrip("Geneſis conteyneth the hiſtorie of the viſible Church, from the beginning of the world to the death of Ioſeph in the yeare of the world. 2340.")
sig("Ppppp")

# ---- printed 1074 (index 1078, S1) : FIRST AGE cont. (Enoch..Noe) ----
page(1078, "1074", "S1", ["Anni mundi.", "Patriar-ches.", "The ſacred Hiſtorie.",
     "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; Scriptures column blank on this leaf.")
runhead("1074", "AN HISTORICAL TABLE", "")
gcols("patriarches")
anni("g", "622.", note="at 4x the digits after '6' render like thin strokes (≈611); transcribed 622 — the value forced by the clear h 687 (=622+65) and the Iared→Enoch chronology (460+162)", unc=True)
anni("h", "687.")
anni("i", "874.")
anni("k", "930.")
anni("l", "987.")
anni("m", "1042.")
anni("n", "1056.")
anni("o", "1140.")
anni("p", "1265.")
anni("q", "1290")
anni("r", "1422.")
anni("s", "1536.")
anni("t", "1556.")
anni("v", "1651.")
anni("w", "1656.")
g1("Enoch,")
g1("Mathuſala.")
g1("Lamech.")
g1("Noe bor.")
g1("Sem bor.")
g1("And the next two yeares Cham, & Iaphet.", note="italic note under 'Sem bor.'")
hist(None, "Enoch a Prophet pleaſed God in al his wayes. None borne in the earth like to Enoch. Eccli. 49. v. 16.")
hist("k", "Adam dyed at the age of 930. yeares. Gen. 5. v. 5. To whom Seth ſucceded chief Patriarch. And ſo in the reſt.")
hist("l", "Enoch in the yeare of his age 365. was ſene no more : becauſe God tooke him. Gen. 5. v. 24. Enoch was tranſlated that he ſhould not ſee death. Heb. 11. v. 5.", note="closing sentence 'Enoch was tranſlated...death.' set in italic")
hist("m", "Seth dyed in the yeare of his age. 912.")
hist("o", "Enos dyed anno ætatis; 905.")
hist("p", "Cainan dyed, an. æt 980.")
hist("q", "Malaleel dyed, an. æt. 895.")
hist("r", "Iared dyed, an. æt. 962.")
hist("s", "Noe the preacher of iuſtice, forewarned al men that except they repented, God would deſtroy them with a floud.")
hist(None, "And by Gods commandement built an Arke ( or ſhippe ) wherin himſelf, & his familie, with other liuing creatures, were preſerued from drowning.")
hist("v", "Lamech dyed ( before his father ) in the yeare of his age, 777.")
hist("w", "Mathuſala dyed, an. æt. 969. immediatly before the")
schis("were borne or dyed : Enoch, Irad, Mauiael, Mathuſael, Lamech. Gen. 4. v. 17.")
schis("Some declining from God, and matchĩg in mariage with Cains race begate thoſe monſtruous men huge of ſtature, moſt wicked & cruel called giantes. Gen. 6. v. 4.")

# ---- printed 1075 (index 1079, S1) : END OF 1st AGE / BEGINNING OF 2nd ----
page(1079, "1075", "S1", ["Anni mundi.", "Patriarches.", "The ſacred Hiſtorie.",
     "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto; contains the first age-divider rule.")
runhead("", "OF THE OLD TESTAMENT.", "1075")
gcols("patriarches")
anni("x", "1656.")
anni("y", "1658.")
anni("z", "1693.")
anni("a", "1713.")
anni("b", "1753.")
anni("c", "1787.")
anni("d", "1817.")
anni("e", "1850.")
anni("f", "1879.")
anni("g", "1908.")
hist("w", "floud, as ſemeth moſt probable.")
hist("x", "The ſame yeare of the world, 1656. the 17. day of the ſecond moneth Noe with his three ſonnes his wife, and their wiues, in al eight perſons, and ſeuen payres of euerie kinde of cleane liuing creatures, and two payres of vncleane entered into the Arke. And preſently it rayned fourtie dayes and nightes together. Wherby al liuing creatures on the earth out of the arke were drowned. Gen. 7.")
schis("Al Cains race, with other wicked infideles were vtterly deſtroyed, by the flould. Gen. 7.", note="'flould' printed for 'floud' (intrusive l) — preserved", unc=True)
divider("THE END OF THE FIRST AGE, AND BEGINNING OF THE SECOND.")
g1("Arphaxad borne the ſonne of Sem.", note="'the ſonne of Sem' in italic")
g1("Cainan.")
g1("Sale,")
g1("Heber,")
g1("Phaleg.")
g1("Reu.")
g1("Sarug.")
g1("Nachor,")
g1("Thare,")
hist(None, "The whole earth being couered with water, Noe with his familie, and other liuing creatures remained in the arke twelue monethes and ten dayes ( a iuſt yeare of the ſunne ) then coming forth built an altar and offered ſacrifice. Which God accepting bleſſed them for new increaſe. Gen. 8. & 9.")
hist("c", "Heber conſented not to the building of Babel. And therfore his familie kept ſtil their former language, which thenceforth for diſtinction ſake, was called")
schis("Nemrod the ſonne of Chus, and nephew to Cham, about three ſcore yeares after the")
scrip("* Not affirming but ſuppoſing that Cainan was the ſonne of Arphaxad, we place him here : and Sale 30. yeares after.", note="italic marginal note keyed by * ; refers to Cainan (2nd) genealogy entry")
sig("Ppppp 2")

# ---- printed 1076 (index 1080, S1) : END OF 2nd AGE / BEGINNING OF 3rd ----
page(1080, "1076", "S1", ["Anni mundi.", "Patriar-ches.", "The ſacred Hiſtorie.",
     "Schiſmes and infidelitie."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; only 4 columns printed on this leaf (Scriptures column omitted/blank).")
runhead("1076", "AN HISTORICAL TABLE", "")
gcols("patriarches")
anni("h", "1979.")
anni("i", "2054.")
g1("Abraham borne.")
hist(None, "the Hebrew tongue. He liued to ſee Abrahams father. And Noe, Sem, Arphaxad, Phaleg, and other moſt godlie men liued ſome part of Abrahams time ; who was neuer corrupted in fayth, nor religion.")
hist("i", "By Gods commandment, Abraham at the age 75. yeares hauing bene much perſecuted for religiõ, went forth of his countrie Chaldea. Wherupon his father Thare went as farre as Haran, in the confines of Meſopotamia. And Lot went further with him into Chanaan. Which countrie God then promiſed to geue him, and to multiplie his ſeede, and therin to bleſſe al nations. Gen. 11. v. 31. & 12. v. 1. & 7.")
schis("floud, by force and ſutteltie drawing manie folowers, begane a new ſect of infidels. And afterwardes was the principal auctor of building the towre of Babel. Where the tongues of the builders were confounded, & ſo they were ſeparated into manie nations, about 130. yeares after the floud. Gen. 10. v. 25.")
schis("After Nemrod his ſonne Belus reigned in Babylon, about the yeare of the world. 1871. which was 215. yeares after the floud.")
schis("And after him his ſonne Ninus beginning to reigne about the yeare 1936. ſet vp idolatrie, cauſing his father to be honored as the great God, called Belus Iuppiter : & his grandfather Nemrod, otherwiſe called Saturnus, or Sator deorum, the father of goddes.", note="'Belus Iuppiter', 'Saturnus', 'Sator deorum' in italic")
divider("THE END OF THE SECOND AGE, AND BEGINNING OF THE THIRD.")
anni("k", "2055.")
anni("l", "2056.")
hist("k", "By occaſion of famine in Chanaan, Abraham went into Ægypt with his wife, and Lot. Gen. 12. v. 10.")
hist("l", "They returned into Chanaan, became very rich : and God renewed his great promiſes to Abraham. Gen. 13.")
hist("m", "Lot [amongſt others] be-")

# ---- printed 1077 (S9 index 1089) : RECOVERED (absent in S1) ; 3rd AGE cont. ----
page(1089, "1077", "S9", ["Anni mundi.", "Patriarches.", "The ſacred Hiſtorie.",
     "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="RECOVERED from S9 (archive-holiebible-ot2 jp2 index 1089) — this leaf is ABSENT from the S1 scan (see gap_recovery). Same 1610 typesetting. Scriptures column blank.")
runhead("", "OF THE OLD TESTAMENT.", "1077")
gcols("patriarches")
anni("n", "2064.")
anni("o", "2065.")
anni("p", "2078.")
anni("q", "2079.")
anni("r", "2104.")
anni("s", "2116.")
anni("t", "2119.")
anni("v", "2139.")
anni("w", "2154.")
g1("Iſaac, borne.")
g1("Iacob & Eſau borne.")
hist("m", "ing taken captiue, Abraham with three hundred and eightene men reſcued them al. Wherupon Melchiſedech offered ſacrifice in bread & wine : bleſſed Abraham, & receiued tithes of him. Gen. 14.")
hist("n", "Sara long barren perſwaded Abraham to take her handmaid Agar to wife.")
hist("p", "Circumciſion was inſtituted, that Abraham, and his ſonnes, & al the men of his familie might be diſtinguiſhed from others. Gen. 17.")
hist(None, "Sodom and Gomorrha with other cities were burnt with brimſtone. From whence Lot was deliuered by Angeles. Gen. 19.")
hist("q", "Sara conceiued and bare a ſonne called Iſaac, Gen. 21.")
hist("r", "Abraham by Gods commandement was readie to offer Iſaac in ſacrifice, but was ſtayed by an Angel. And former promiſes were renewed. Gen. 22.")
hist("s", "After the death of Sara, Abraham maried Cetura, by whom he had ſix ſonnes. Gen. 25.")
hist("t", "Iſaac maried Rebecca the daughter of Bathuel, ſonne of Nachor Abrahams brother. Gen. 24.")
hist("w", "Abraham dyed at the age")
schis("Agar conceiued & brought forth a ſonne, who was named Iſmael. Gen. 16.", letter="o")
schis("Iſmael attempting to corrupt Iſaac in maners ( which S. Paul calleth perſecution. Gal. 4. ) was caſt out of Abrahãs houſe together with his mother. Gen. 21. v. 19. And neuertheles had twelue ſonnes, al dukes before Iſaac had anie")
sig("Ppppp 3")

# ---- printed 1078 (index 1081, S1) : 3rd AGE cont. (Isaac/Iacob/Ioſeph) ----
page(1081, "1078", "S1", ["Anni mundi.", "Patriar-ches.", "The ſacred Hiſtorie.",
     "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; Scriptures column blank. NB the S1 scan images this printed leaf TWICE (jp2 indices 1081 and 1082 are byte-identical); printed 1077 is the leaf that was dropped.")
runhead("1078", "AN HISTORICAL TABLE", "")
gcols("patriarches")
anni("x", "2216.")
anni("y", "2217.")
anni("z", "2224.")
anni("a", "2225.")
anni("b", "2226.")
anni("c", "2227.")
anni("d", "2230.")
anni("e", "2236.")
anni("f", "2246.")
anni("g", "2247.")
anni("h", "2259.")
anni("i", "2260.")
g1("Ruben.")
g1("Simeon.")
g1("Leui.")
g1("Iudas.")
g1("Dan.", note="a printer's brace '[' with 'li.' abuts Dan/Nephtha (grouping mark; not fully resolved)")
g1("Nephtha")
g1("Gad.")
g1("Aſer.")
g1("Iſſachar.")
g1("Zabulon.")
g1("Ioſeph:b.")
g1("Beniamin.bor.")
hist("w", "of 175. yeares. Gen. 25.")
hist("x", "Iſaac bleſſed Iacob thincking him to be Eſau. Gen 27.")
hist("y", "Iacob going into Meſopotamia to flye the danger of his brothers threates, ſaw in ſleepe a ladder reaching from the earth to heauen. Ge. 28. And being there he ſerued his vncle Laban ſeuen yeares for his younger daughter Rachael, receiued Lia the elder ; and ſerued other ſeuen for Rachael. And ſix more for certaine fruict of the flockes. Gen. 29. & 30.")
hist("e", "Iacob returning from Meſopotamia wreſtled with an Angel, & was called Iſrael. Gen. 32. & 35. v. 10.")
hist("f", "Rachael dyed, and was buried in Bethleem. Gen. 35. v. 18. & 19.")
hist("g", "Ioſeph was ſold, and caried into Ægypt ; & ſhortly after caſt into priſon, where he interpreted the dreames of two Eunuches. Gen. 37. 39. & 40.")
hist("h", "Iſaac dyed, at the age of 180. yeares.")
hist("i", "Ioſeph interpreting king Pharao his dreames, and geuing wiſe counſel to prouide for the ſcarſitie to come, was made ruler of Ægypt. He then maried, &")
schis("iſſue, Which S. Paul noteth. 1. Cor. 15. v. 46, Firſt that is natural, afterward that which is ſpiritual.", note="'Which S. Paul noteth...ſpiritual.' in italic")
schis("Eſau alſo had much iſſue, and proſpered in the world. But his progenie, as alſo Iſmaels, & al Abrahams ofſpring by his laſt wife Cetura were excluded from the promiſed enheritance, & other bleſſinges. Gen. 25. v. 5. & 6. & ch. 28. v. 4. & 14.")
schis("Apis king of Argiues, of Iupiters race, going into Ægypt, taught the people to plant vines, and make wine, to plow with oxen, and to ſow & reape corne, was made their king and after his death honored in the forme of")

# ---- printed 1079 (index 1083, S1) : 3rd AGE ; genealogy splits (Leui / Iudas) ----
page(1083, "1079", "S1", ["Anni mundi.", "The line of Leui.", "The line of Iudas.",
     "The ſacred hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto; genealogy now two columns: 'The line of Leui' + 'The line of Iudas'.")
runhead("", "OF THE OLD TESTAMENT.", "1079")
gcols("line_of_leui", "line_of_iudas")
anni("l", "2269.")
anni("m", "2286.")
anni("o", "2340.")
g1("Caath.")
g1("Amrã.")
g2("Phares.")
g2("Eſron.")
hist("i", "had two ſonnes Manaſſes, and Ephraim in the ſeuen yeares of plentie. Gen. 41.")
hist("k", "Iacob ſent his tenne ſónes into Ægypt to bye corne. Where they were threatned as ſuſpected ſpies, and one was kept in priſon, til they ſhould bring their brother Beniamin. Gen. 42.")
hist("l", "They returning into Ægypt with Beniamin in their companie, Ioſeph firſt terrified them, afterwards manifeſted himſelf vnto them. And ſending for his father and whole kinred, they al went into Ægypt. Gen. 43. 44. 45. & 46.")
hist("m", "Iacob bleſſed and adopted the two ſonnes of Ioſeph, preferring Ephraim the younger before Manaſſes. Gen. 48. propheſied of al his twelue ſonnes ; and in Iudas of Chriſt. Gen. 49. v. 10. And then dyed.")
hist("n", "Ioſeph buried his father in Chanaan, and nouriſhed his bretheren with their families, as their patron & ſuperior. Gen. 50. v. 18.")
hist("o", "He dyed at the age of 110. yeares. Gen. 50.")
hist(None, "After his death the Superioritie of the children of Iſrael deſcended not to his")
schis("an oxe, for their great god. S. Aug. li. 18. c. 5. de ciuit.", note="italic reference tail")
schis("As people increaſed, ſo idolatrie was multiplied, and innumerable goddes feaned and ſerued with ſuperſticious rites in al heathen nations. Amongſt which firſt the Aſſirians, and at laſt the Romanes held the principality, others in reſpect of them were of leſſe powre, or of ſhorter time, & as it were dependentes of them : as S. Auguſtin obſerueth. li. 18. c. 2. de ciuit.")
schis("About this time was Atlas the great Aſtrono-")
scrip("Iob either of the progenie of Nachor, or as ſemeth more probable of Eſau, liued the ſame time ; in which the children of Iſrael were preſſed with ſeruitude in Ægypt. Himſelfe writte the hiſtorie of his affliction in the Arabian tongue which Moyſes tranſlated into Hebrew.")
scrip("The booke of Exodus conteyneth")

# ---- printed 1080 (index 1084, S1) : END OF THE THIRD AGE ----
page(1084, "1080", "S1", ["Anni mundi.", "The line of Leui.", "The line of Iudas.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; ends with the third-age divider.")
runhead("1080", "AN HISTORICAL TABLE", "")
gcols("line_of_leui", "line_of_iudas")
anni("p", "2401.")
anni("q", "2404.")
anni("s", "2444.")
anni("t", "2484.", note="2484 clear at 4x; a '?'-like mark is printed/foxed immediately after the figure (possible compositor uncertainty mark)", unc=True)
g1("Aaron. borne.")
g1("Moyſes borne.")
g2("Aram.")
g2("Aminadab.")
hist(None, "ſonnes, but to his bretheren and reſted in Leui the third brother liuing longeſt of al the twelue, to the age of 137. yeares. Exodi. 6. v. 16. whoſe genealogie is there declared to ſhew the deſcent of Aaron and Moyſes.")
hist("r", "Moyſes an infant of three monethes was put in a basket on the water, & taken thence by Pharaos daughter, nurced by his owne mother, and brought vp in Pharaos court. Exod. 2.")
hist("s", "At the age of fourty yeares he went to his bretheren to comfort them.")
hist(None, "Where killing an Ægyptian that oppreſſed an Iſraelite, he was forced to flee into Madian. Exod. 2.")
hist("t", "After other fourtie yeares God appeared to Moyſes in a bush burning & not waſting. Sent him into Ægypt with powre to worke miracles, & to bring the children of Iſrael out of that bondage.")
hist("v", "Pharao and the Ægyptians reſiſting were plaged with tenne ſundrie afflictions. At laſt the Iſraelites were deliuered, and Pharao with al his armie drowned. Exo. 3. 10. 15.")
schis("mer brother of Prometheus, grandfather to Mercurius the elder, whoſe nephew Mercurius, otherwiſe called Triſmegiſtus, the maiſter of moral philoſophie, muſt nedes be a good while after Moyſes. S. Aug. li. 18. c. 39. de ciuit. Alſo Cecrops the firſt king and builder of Athens, was in Moyſes time, after him Cadmus built Thebes, and the firſt that brought letters into Grece, more ancient then manie Panimes goddes S. Aug. li. 18. c. 8. &c.")
scrip("the affliction and deliuerie of the children of Iſrael, & precepts of Gods law.")
divider("THE END OF THE THIRD AGE.")

# ---- printed 1081 (index 1085, S1) : BEGINNING OF THE FOVRTH AGE ----
page(1085, "1081", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Iudas.",
     "The ſacred hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto; opens with the fourth-age divider; genealogy = 'High-prieſts' + 'The line of Iudas'.")
runhead("", "OF THE OLD TESTAMENT.", "1081")
gcols("highpriests", "line_of_iudas")
divider("THE BEGINNING OF THE FOVRTH AGE.")
anni("x", "2485.")
anni("b", "2523.")
anni("c", "2524.")
g1("Aaron.")
g1("Eleazar")
hist("w", "The law was geuen in Mount Sina the fifteth day after their going out of Ægypt. Exod. 19. 20.")
hist("x", "The tabernacle, with al thinges perteyning therto, was prepared in the firſt yeare, and erected the firſt day of the ſecond yeare of their abode in the deſert. Exod. 40.")
hist("y", "In the ſame ſecond yeare Aaron was conſecrated Highprieſt, and his ſonnes Prieſtes, for an ordinarie ſucceſſion : Moyſes remayning Superior extraordinarie during his life. Leuit. 8.")
hist("z", "Balaam a ſorcerer hyred by Balac king of Moab to curſe the Iſraelites, was forced by Gods powre to prophecy good things of them. Num. 21. 23. 24.")
hist("a", "Moyſes and Aaron doubting that God would not geue water out of a rock to the murmuring people, were foretold that they ſhould dye in the deſert, and not enter into the promiſed land. Num. 20.")
hist("b", "Aaron dyed in the mount Hor, and his ſonne Eleazar was made Highprieſt. Num. 20.")
hist("c", "Moyſes repeted the law,")
schis("In the abſence of Moyſes the people forcing Aaron to conſent, made & adored a golden calfe for God. Exod. 32.")
schis("Nadab & Abiu offered ſtrange fire in ſacrifice and were burnt to death. Leuit. 10.")
schis("Chore, Dathan, & Abiron with manie others murmuring & rebellĩg againſt Moyſes & Aaron were partly ſwalowed aliue into the earth others burnt with fire from heauen. Num. 16.")
scrip("Leuiticus conteyneth the Rites of Sacrifices, Prieſtes, Feaſtes, Faſtes, and Vowes.")
scrip("Numeri, ſo called becauſe in it are numbered the men of twelue tribes able to beare armes, alſo the Leuites deputed to Gods ſeruice about the tabernacle, and the manſions of the people in the deſert with other thinges hapening in the 40. yeares of their abode there")
sig("Qqqqq")

# ---- printed 1082 (index 1086, S1) : 4th AGE (Ioſue) ----
page(1086, "1082", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Iudas.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso.")
runhead("1082", "AN HISTORICAL TABLE", "")
gcols("highpriests", "line_of_iudas")
anni("f", "2531.")
anni("g", "2533.")
anni("h", "2556.")
g2("Naaſſon.")
hist("c", "commending it earneſtly to the people. Then dyed, and was ſecretly buried by Angels in the valley of Moab. Deut. 34.")
hist(None, "To whom Ioſue ſucceeded in temporal gouernment his ſpiritual remayning in the Highprieſt Nu. 27. v. 20.")
hist("d", "Al the children of Iſrael that came forth of Ægypt aboue the age of twentie yeares dyed in the deſert except two, Ioſue & Caleb. Num. 26. v. 64. 65.")
hist("e", "Preſently after Moyſes death Ioſue brought the people ouer Iordan into Chanaan. Ioſue. 3. And in the ſpace of ſeuen yeares conquered the land. Ioſue. 6. &c.")
hist("f", "And diuided the ſame amongſt the tribes. Ioſue. 13.")
hist("g", "The tribes of Ruben Gad and half Manaſſes hauing receiued enheritance on the other ſide of Iordan, Num. 32. v. 33. and now returning thither made an altar by the riuer ſide, which the other tribes ſuſpecting to be for ſacrifice, and ſo to make a ſchiſme, prepared to fight againſt them : but they anſwering that it was only for a monument ; al were ſatiſfied, Ioſue 22.")
hist("h", "Ioſue at the age of 110.")
schis("Al nations generally beſides the Iewes, ſeruing many falſe goddes, thoſe thought themſelues moſt religious that were moſt ſuperſticious, & ſtudious of art Magike, Nigromancy & the like. And euerie countrie yea almoſt euerie towne & village had their peculiar imagined goddes. as S. Athanaſius diſcourſeth, orat. contra idola.")
schis("The Romanes, otherwiſe moſt prudent accoũted al inuenters of artes, conqueroures of countries, & al atchiuers of great explotes at leaſt after their deathes to")
scrip("Deuteronomie is an abridgement and repetition of the law, conteyned more largely in the former bookes.")
scrip("The booke of Ioſue, is the firſt of thoſe which are properly called Hiſtorical, declaring how the Iſraelits conquered & poſſeſſed the land of Chanaan, it conteyneth the hiſtorie of 32. yeares.")

# ---- printed 1083 (index 1087, S1) : 4th AGE (Iudges begin) ----
page(1087, "1083", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Iudas.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto.")
runhead("", "OF THE OLD TESTAMENT.", "1083")
gcols("highpriests", "line_of_iudas")
anni("i", "2556.")
anni("l", "2564.")
anni("m", "2588.")
g1("Phinees.")
hist("h", "yeares dyed. Ioſue. 24. v. 29. & had no proper ſucceſſor.")
hist("i", "Eleazarus the Highprieſt dyed the ſame yeare, Ioſue. 24. v. 33. And his ſonne Phinees ſucceeded.")
hist("k", "After the death of Ioſue the people were afflicted by forreine nations, God ſo permitting for their ſinnes, but repenting he raiſed vp certaine captaines, who were called Iudges, of diuers tribes without ordinarie ſucceſſion, to deliuer & defend the countrie from inuaſions. Theſe were in al fourtenne in the ſpace of nere 300. yeares.")
hist("l", "Othoniel the firſt Iudge, of the tribe of Iuda, deliuered the Iſraelites from moleſtation of the king of Syria. He gouerned ( comprehending alſo the intermiſſion ) fourtie yeares, Iudic. 3. v. 11.")
hist("m", "Aod of the tribe of Beniamin the ſecond Iudge, killed Eglon king of Moab, and ſo deliuered Iſrael, and ſlew tenne thouſand Moabites. Iud. 3. v. 20. 29.")
hist("n", "Samgar a husbandman the third Iudge, killing ſix hundred Philiſthimes with the culter of a plough defended Iſrael. Iudic. 3. v. 31. He with")
schis("be goddes. And not only men, but alſo manie other thinges were held for goddes.")
schis("Neither did it ſuffice their phancies to cōmend themſelues and their goodes. to the protection of few goddes but diuers thinges : yea and the ſame thinges according to diuers ſtate to diuers goddes, and goddeſſes. As S. Auguſtin noteth. li. 4. c. 8.")
scrip("The booke of Iudges ſheweth the ſtate of the people of God the ſpace of nere three hundred yeares after the death of Ioſue, when they had ſometimes temporal gouerners of diuers tribes, ſometimes none.")
sig("Qqqqq 2")

# ---- printed 1084 (index 1088, S1) : 4th AGE (Iudges cont.) ----
page(1088, "1084", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Iuda.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso.")
runhead("1084", "AN HISTORICAL TABLE", "")
gcols("highpriests", "line_of_iudas")
anni("o", "2663.")
anni("p", "2701.")
anni("q", "2741.")
anni("r", "2744.")
anni("s", "2767.")
anni("t", "2789.")
g1("Abiſue.")
g1("Bocci.")
g2("Salmon.")
g2("Booz.")
hist("n", "Aod, and the times, wanting iudges, gouerned ſeuentie fiue yeares.")
hist("o", "Barach by direction of Debora a propheteſſe, fighting againſt Siſara, chiefe captaine, of Iabin king of Aſor, Iahil a ſtout woman ſlew the ſame captaine, ſtriking a naile in his head, Iud. 4. They gouerned 38. yeares.")
hist("p", "Gedeon confirmed by miracles that he was ſent of God ouerthrew the Madianites, and deliuered Iſrael, gouerning fourtie yeares. Iudic. 6. 7. 8.")
hist("q", "Abimelech the baſe ſonne of Gedeon vniuſtly vſurping auctoritie, killed his ſeuenty bretheren one only eſcaping, but within three yeares was hated of his folowers, and ſlaine by a woman. Iud 9.")
hist("r", "Thola defended the countrie from inuaſion of enimies three yeares. Iud. 10.")
hist("s", "Iair a potent noble man defended the people twentie two yeares. Iud. 10. v. 3.")
hist("t", "Iepte firſt reiected but afterwards intreated by the ancientes of the people, fought for them and ouerthrew the enemies. And vpon an vndiſcrete vow offered his daughter in ſacrifice. Iud. 11.")
schis("de ciuit. that they thought it not ſufficient to cōmend their landes & poſſeſſions to one god, or goddeſſe, but the fieldes to one, moũtaines to an other, litle hilles to an other, valleys, or medowes to an other. Likewiſe their corne not al to one, but the ſede newly ſowne to one, beginning to brewerd to an other, when it riſeth & beginneth to haue knottes to an other, when it bladeth to an other, when the eare ſpringeth to an other, when it is ripe readie to be reaped to an other. And ſo without end more and more vaine goddes were imagined by the diuels ſuggeſtion,", note="'brewerd' as printed (obscure; ? for 'brerd'/sprout) — preserved", unc=True)

# ---- printed 1085 (index 1089, S1) : 4th AGE (Ruth, Samuel) ----
page(1089, "1085", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Iudas.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto.")
runhead("", "OF THE OLD TESTAMENT.", "1085")
gcols("highpriests", "line_of_iudas")
anni("w", "2795.")
anni("x", "2802.")
anni("y", "2812.")
anni("z", "2820.")
anni("a", "2840.")
anni("b", "2880.")
g1("Ozi.")
g1("Hei, otherwiſe Zaraias.")
g2("Obed.")
g2("Iſai, or Ieſſe.")
hist(None, "He killed in ciuil warre fourtie two thouſand Ephraimites, and gouerned ſix yeares. Iud. 12.")
hist("w", "Abeſan a fortunate good man ruled in peace ſeuen yeares. Iudic. 12. v. 9.")
hist(None, "About this time Booz of the tribe of Iuda maried Ruth a Moabite : by whom the right line of Iudas deſcended by Phares to Dauid. Ruth. 4. v. 18. &c.")
hist("x", "Ahialon gouerned likewiſe in peace tenne yeares. Iud. 12. v. 11.")
hist("y", "Abdon an other nobleman gouerned eight yeares. Iud. 12. v. 13.")
hist("z", "Samſon from his birth a Nazareite of admirable ſtreingth did manie heroical actes, killed manie Philiſtimes in his life, & more by his owne death. He gouerned twentie yeares. Iud. 13. v. 5. &c. ch. 16. v. 31.")
hist("a", "Heli of the ſtocke of Aaron by the line of Ithamar was Highprieſt and gouerned Iſrael fourtie yeares. 1. Reg. 4. v. 18.")
hist("b", "Samuel ( whoſe mother being long barren had preſented him an infant in the temple, according to her vow ) was a Nazareite and a prophet from a child : 1.")
schis("who ſo deluding men brought them to eternal ruine.")
schis("The people in this time of peace fel againe to idolatrie. For which God ſuffered the Philiſtimes to afflict them. Iud. 13.")
schis("The tribe of Dan, ſet vp idolatrie, Iud. 18.")
schis("A hainous crime being committed in the tribe of Beniamin and not puniſhed, the other Iſraelites made battle againſt them & being themſelues alſo great ſinners loſt manie men in two conflictes, but in the third the tribe of Beniamin was almoſt deſtroyed. Iud. 19. v. 20.")
scrip("The booke of Ruth amongſt other myſteries ſheweth the genealogie of Dauid, of whoſe ſede Chriſt was borne.")
scrip("The foure bookes of kings ſhew the ſtate of the Church from the")
sig("Qqqqq 3")

# ---- printed 1086 (index 1090, S1) : END OF THE FOVRTH AGE ----
page(1090, "1086", "S1", ["Anni mūdi.", "High-prieſts.", "Kinges of Iuda.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; genealogy col.3 now 'Kinges of Iuda' (Dauid, Salomon); ends with the fourth-age divider.")
runhead("1086", "AN HISTORICAL TABLE", "")
gcols("highpriests", "kinges_of_iuda")
anni("c", "1900.", note="printed '1900' is a compositor error for 2900 (sequence requires b 2880 < c < d 2920); preserved diplomatically as printed", unc=True)
anni("d", "2920.")
anni("e", "2960.")
anni("f", "2964.")
g1("Maraioth.")
g1("Achimelech or Amarias.")
g1("Abiathar, or Achitob.")
g1("Sadoc.")
g2("Dauid b.")
g2("Dauid king.")
g2("Salomon.")
hist("b", "Reg. 1. & 3. And after the death of Heli, gouerned the people of Iſrael before Saul twentie yeares. And with him twentie yeares more.")
hist("c", "By the importunitie of the people to haue a king, God appointed Samuel to annoint Saul. 1. Reg. 10. who at firſt gouerned wel, but afterwards declining from God was depoſed, & Dauid annointed by the ſame prophet Samuel. 1. Reg. 16. Yet Saul was not actually depriued of the ſcepter ſo long as he liued. 1. Reg. 31.")
hist("d", "Dauid king & prophet ruled his kingdom as a right parterne of al good kinges : made the booke of Pſalmes ful of al diuine knowlege, prepared meanes for building the temple, ordained diuers ſortes of muſitians, and reigned fourtie yeares. 2. Reg. totus. 2. Par. 23. &c.")
hist("e", "Salomon excelling in wiſdom, proſpered in this world. 3. Reg. 3. &c.")
hist("f", "He built the temple and adorned the ſame with al excellent furniture requiſite for Gods ſeruice : diſpoſing al in order, as Dauid had ordained.")
schis("About the yeare of the world. 2830. Troy was taken and deſtroyed by the Grecians. In which battel were Agamemnon, Vliſſes, Achilles, Neſtor, & many others not in dede ſo renowmed for anie vertues or factes of their owne, as Homer, Horace, Virgil, Ouid, & others by poetical libertie & flatterie ſette them forth. But moſt follie appeareth in that the citie of Rome was afterwards commended to thoſe goddes, which were taken in Troy, not able to defend them ſelues from inuaſion and ſpoile. S. Aug. li. 1. c. 3. ciuit.")
scrip("firſt kinges of Gods people to their captiuitie. And the two bookes of Paralipomenon do repete briefly ſome thinges writen before, partly adde thinges omitted in other bookes.")
scrip("The pſalmes written by Dauid, a ſummarie of al holie Scriptures.")
divider("THE END OF THE FOVRTH AGE.")

# ---- printed 1087 (index 1091, S1) : BEGINNING OF THE FIFTH AGE ----
page(1091, "1087", "S1", ["Anni mūdi.", "High-prieſts.", "kinges of Iuda.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto; opens with the fifth-age divider.")
runhead("", "OF THE OLD TESTAMENT.", "1087")
gcols("highpriests", "kinges_of_iuda")
divider("THE BEGINNING OF THE FIFTH AGE.")
anni("g", "2972.")
anni("h", "3000.")
anni("i", "3017.")
anni("k", "3020.")
anni("l", "3061.")
g1("Achimaas.")
g1("Azarias")
g1("Iohanam.")
g2("Roboam.")
g2("Abias.")
g2("Aſa.")
g2("Ioſaphat.")
hist("g", "The temple being finiſhed in ſeuen yeares, was then dedicated moſt ſolemnly, with exceding deuotion of the king, and al the people with abũdance of ſacrifices.")
hist(None, "And afterwardes the ſame king Salomon writte three ſapiential bookes. The Prouerbes, Eccleſiaſtes & the Cãticle of Canticles.")
hist(None, "But in his old age fel from God, and it is vncertaine whether he dyed penitent or no. He reigned fourtie yeares. 3. Reg. 11.")
hist("h", "King Roboam leauing the aduiſe of ancientes and folowing young counſelers, offended the people : and his ſeruant Ieroboam was made king of tenne tribes : only Iuda & Beniamin remayning to him. He reigned ſeuentene yeares. 3. Reg. 14. v. 21.")
hist("i", "His ſonne Abias reigned wickedly three yeares. 3. Reg. 15. v. 2.")
hist("k", "Aſa a good king deſtroyed idolatrie, and reigned 41. yeares. 3. Reg. 15. v. 10.")
hist("l", "Ioſaphat gouerned the kingdom wel 25. yeares, 3. Reg. 22. v. 42. & 43. ſauing that he ioyned affinitie with Achab king of Iſrael,")
schis("Ieroboam the firſt king of the tenne tribes made a wicked ſchiſme, ſetting vp two golden calues in Bethel and Dan : which moſt of the people ſerued as their goddes. He reigned 22. yeares. 3. Reg. 12.")
schis("After him were theſe kinges of diuerſe families of the ſame tenne tribes. Nadab ſonne of Ieroboam reigned two yeares 3. Reg. 14. Baſa of the tribe of Iſſachar reigned 24. yeares. 3. Reg. 15. Ela two yeares. 3. Reg. 16. Zambri but ſeuen dayes. 3. Reg. 16. v. 15. Amri 12. yeares wherof Thebni reigned in ciuil warre againſt him three yeares. v. 22. Achab")
scrip("The Prouerbes. Eccleſiaſtes. Canticle of Canticles.")

# ---- printed 1088 (index 1092 degraded -> S9 index 1100) : 5th AGE (kings of Israel/Iuda) ----
page(1092, "1088", "S9", ["Anni mūdi.", "High-prieſts.", "Kinges of Iuda.",
     "The ſacred hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; S1 leaf (jp2 index 1092) is bleached/illegible — text read from the identical S9 typesetting (archive-holiebible-ot2 jp2 index 1100).")
runhead("1088", "AN HISTORICAL TABLE", "")
gcols("highpriests", "kinges_of_iuda")
anni("m", "3086.")
anni("n", "3094.")
anni("o", "3095.")
anni("p", "3101.")
anni("q", "3142.")
g1("Ioiada.")
g1("Zacharias.")
g1("Sadoc. or Ioathan.")
g1("Sellum")
g2("Ioram.")
g2("Ochozias.")
g2("Ioas.")
g2("Amaſias.")
hist("l", "and with Iezabel. 2. Paral. 18. v. 1.")
hist("m", "Ioram reigned wickedly eight yeares. 4. Reg. 8. v. 17. & 18. 2. Paral. 21. v. 5. & 6. The three next are omitted by S. Mathew.")
hist("n", "By the euil counſel of his mother Athalia, Ochozias gouerned wickedly one yeare, & was ſlaine by Iehu together with Ioram king of Iſrael. 4. Reg. 8. v. 27. & ch. 9. v. 27. 2. Paral. 22. v 3. & 9.")
hist("o", "Quene Athalia murthering the children of her owne ſonne the late king, vſurped the kingdom ſix yeares. 4. Reg. 11. v. 1.")
hist("p", "The youngeſt ſonne of Ochozias called Ioas being ſaued from the ſlaughter, was made king by meanes of Ioiada Highprieſt, and Athalia ſlaine 4. Reg. 11. v. 4. He gouerned wel during the life of Ioiada. But afterwards fel to idolatrie, & cauſed Zacharias the Highprieſt and ſonne of Ioiada to be ſlaine. 2. Paral. 24. v. 22. And ſhortly after the ſame king was trecherouſly ſlaine when he had reigned 41. yeares. 4. Reg. 12. v. 20. & 2. Paral. 24. v. 25.")
hist("q", "Amaſias beginning wel did ſome good thinges, 4.")
schis("maried Iezabel a Sidonian, and ſerued Baal, reigning 21. yeares. 3. Reg. 10. &c.")
schis("Ochozias reigned two yeares. 3. Reg. 22. v 52.")
schis("Ioram twelue yeares. 4. Reg. 3. Iehu killed Ioram and Iezabel, deſtroying the whole houſe of Achab reigned 8. yeares. 4. Reg. 9. & 10.")
schis("Ioachaz reigned. 17. yeares. 4. Reg. 13.")
schis("Ioas reigned ſixtene yeares. 4. Reg. 13. v. 10.")
schis("Ieroboam 41. yeares. 4 Reg 14. v. 23.")
schis("Zacharias reigned but ſix monethes. 4. Reg. 15. v. 8.")
schis("Sellum but one moneth. 4. Reg. 15. v. 15.")
schis("Manahem reigned 10. yeares. 4. Reg. 15. v. 17.")
schis("Phaceia two")
scrip("Elias Elizeus and diuers other Prophetes preached, & did manie miracles in the kingodm of Iuda and Iſrael, not writing any particular bookes.", note="'kingodm' as printed (metathesis for 'kingdom') — preserved", unc=True)

# ---- printed 1089 (index 1093 degraded -> S9 index 1101) : 5th AGE (Ozias..Ezechias) ----
page(1093, "1089", "S9", ["Anni mūdi.", "High-prieſts.", "Kinges of Iuda.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto; S1 leaf (jp2 index 1093) is faint/degraded — text read from the identical S9 typesetting (archive-holiebible-ot2 jp2 index 1101).")
runhead("", "OF THE OLD TESTAMENT.", "1089")
gcols("highpriests", "kinges_of_iuda")
anni("r", "3171.")
anni("s", "3223.")
anni("t", "3239.")
anni("v", "3255.")
g1("Helcias")
g1("Azarias")
g1("Vrias.")
g2("Ozias, or Aſarias.")
g2("Ioathan.")
g2("Achaz.")
g2("Ezechias.")
hist("q", "Reg. 14. v. 3. But after the ſpoile of the Idumeans he worshipped their idols. 2. Paral. 25. v. 14. And reigned 29. yeares. ibidem.")
hist("r", "Ozias ſometime reigned wel, 4. Reg. 15. v. 3. but afterwards preſuming to offer incenſe on the altar was repelled by the Highprieſt, & preſently ſtrooken with leproſie, and caſt out of the temple and citie. He liued after that he was king. 52. yeares. 2. Par. 26. v. 16.")
hist("s", "Ioathan a godlie king gouerned a great part of his fathers time, and after his death ſixtene yeares. 4. Reg. 15. 2. Par. 27.")
hist("t", "Achaz a wicked king, after manie benefits receiued from God, fel to idolatrie, reigning ſixtene yeares, deſtroyed holie thinges, ſhut vp the temple, and peruerted manie of the people, 4. Reg. 16. 2. Paral. 28.")
hist("v", "Ezechias a moſt godlie king aduanced true religiõ, which was much decayed. He recouered health being mortally ſicke, which was confirmed by miracle in the ſunne returning backe : and made a Canticle of praiſe with thankes to God, and reigned 29. yeares. 4. Reg. 18.")
schis("yeares. 4. Reg. 15. v. 23.")
schis("Phacee reigned 20. yeares. 4. Reg. 15. v. 27.")
schis("Oſee reigned nine yeares. 4. Reg. 17.")
schis("The kingdom of Iſrael hauing ſtood aboue two hundred and fiſetie yeares was ſubdued by the Aſſirians & much people caried captiue into Aſſyria. 4. Reg. 17. v. 6.")
schis("The Grecians euerie fourth yeare ſet forth enterludes in honour of Iupiter Olimpius, wherof begane the count of Olimpias, about the yeare of the world 3247. And after ſix Olimpiades, that is, 24. yeares. Rome was built.")
schis("New inhabitantes being ſent from Aſſi-")
scrip("In the dayes of king Ozias was Iſaias the Prophet. Likewiſe Oſee : Ioel : Amos : Abdias : and Ionas.")
scrip("Micheas propheſied in the reigne of Ioathan : the former prophetes yet liuing.")
scrip("Nahum and Habacuc propheſied after the captiuitie of the tenne tribes.")
sig("Rrrrr")

# ---- printed 1090 (index 1094, S1) : 5th AGE (captivity begins) ----
page(1094, "1090", "S1", ["Anni mūdi.", "High-prieſts.", "Kinges of Iuda.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso.")
runhead("1090", "AN HISTORICAL TABLE", "")
gcols("highpriests", "kinges_of_iuda")
anni("w", "3284.")
anni("x", "3339.")
anni("y", "3341.")
anni("z", "3372.")
g1("Zaraias", note="single high-priest name low in col.2; column assignment (High-prieſts vs Kinges) slightly ambiguous on the foxed leaf", unc=True)
g2("Manaſſes")
g2("Amon.")
g2("Ioſias.")
g2("Ioachaz, or Iechonias.")
hist("v", "2. Paral. 29. 30. 31. 32.")
hist("w", "Manaſſes for his great ſinnes was caried captiue into Babylon, where he repented and was reſtored to his kingdom : he reigned & liued in captiuitie 55. yeares. 4. Reg. 21. 2. Par. 33.")
hist("x", "Amon reigned euil two yeares. 4. Reg. 21. 2. Par. 33.")
hist("y", "Ioſias a very good king purged the Church of idolatrie, repayred the temple, celebrated a moſt ſolemne Paſch, was ſlaine in battel by the king of Ægypt, ( which al the people much lamented, eſpecially Ieremie the prophet ) when he had reigned 31. yeares. 4. Reg. 22. 23. 2. Par. 34. 35.")
hist("z", "Ioachaz otherwiſe called Iechonias, reigning but three monethes was caried into Ægypt ( where afterwards he dyed 4. Reg. 23. v. 34. ) and Eliakim, otherwiſe called Ioakim, his brother was made king : Who in the third yeare of his reigne was caried into Babylon, 4. Reg. 23. v. 34. 2. Par. 36. v. 4. 5. and with him Daniel, and the other three children. Dan. 1.")
hist(None, "Shortly after which time happened the hiſtorie of Suſanna. Dan. 13.")
schis("ria into Iurie, mixed their paganiſme with the Iſraelites religion, made manie wicked, and deteſtable Sectes. 4. Reg. 17. v. 29.")
schis("In the time of Numa the ſecond king of the Romanes, Pithagoras taught tranſmigratiõ of ſoules from one bodie to an other.")
scrip("About this time happened the hiſtorie of Tobie, who liued in al 102. yeares. Tob. 14. v. 2.")
scrip("Sophonias propheſied in the reigne of Ioſias king of Iuda.")
scrip("Ieremie alſo begane to prophecie being a child in the dayes of Ioſias, & continued in the captiuity of the two tribes. Baruch was his Scribe and alſo a Prophet.")
scrip("Daniel begane to prophecie alſo verie young in Babylon, and continued after")

# ---- printed 1091 (index 1095, S1) : END OF THE FIFTH AGE ----
page(1095, "1091", "S1", ["Anni.", "High-prieſts.", "Kinges of Iuda.",
     "The ſacred hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto; ends with the fifth-age divider.")
runhead("", "OF THE OLD TESTAMENT.", "1091")
gcols("highpriests", "kinges_of_iuda")
anni("a", "3383.")
anni("b", "3394.")
g1("Ioſedech.")
g2("Ioachin, otherwiſe Iechonias,")
hist(None, "And the ſame Ioakim after his reigne of three yeares, liued other eight yeares in captiuitie. 4. Reg. 24. v. 1. 2. Par. 36. v. 4. & 5.")
hist("a", "Ioachin called alſo Iechonias, ſonne of the former Iechonias, or Ioachaz, reigned but three monethes & was caried into Babylon & with him Ezechiel the Prophet and others.")
hist(None, "And his vncle Matthanias, otherwiſe named Sedecias was made king who reigned eleuen yeares. 4. Reg. 24. 2. Paral. 36.")
hist("b", "In the eleuenth yeare of Sedecias when king Iechonias the younger was priſoner in Babylon, Ieruſalem was taken, the Temple deſtroyed, and the people caried captiue into Babylon. 4. Reg. 25. 1. Paral. 36.")
hist(None, "In the meane time Daniel was in ſingular great eſtimatiõ both with the faithful people, and Paganes, and was aduanced to auctoritie as alſo by his meanes the other children, for which they were enuied and perſecuted but were miraculouſly protected. Dan. 1. ad 7. & 13. 14.")
schis("the relaxation from captiuitie.")
schis("A certaine captaine picking a quarel apprehended Ieremie and by conſent of principal men, caſt him into a dungeon the king not knowing therof. 4. Reg. 25. Iere. 37. 38.")
schis("Iſmael killed Godolias the gouernour, and others. 4. Reg. 25. Iere. 41.")
schis("Manie Iewes fled into Ægypt and fel to idolatrie, reſiſting & contemning Ieremies admonitions to the contrarie. Iere. 42. 43. 44.")
scrip("Ezechiel propheſied alſo in the captiuitie, in the countrie nere to Babylon.")
scrip("Eſdras write the relexation of the Iewes from captiuitie. And Nehemias the reparation of Ieruſalem.")
divider("THE END OF THE FIFTH AGE.")
sig("Rrrrr 2")

# ---- printed 1092 (index 1096, S1) : BEGINNING OF THE SIXTH AGE ----
page(1096, "1092", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Dauid.",
     "The ſacred hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; opens with the sixth-age divider; genealogy col.3 now 'The line of Dauid'.")
runhead("1092", "AN HISTORICAL TABLE", "")
gcols("highpriests", "line_of_dauid")
divider("THE BEGINNING OF THE SIXTH AGE.")
anni("c", "3418.")
anni("d", "3420.")
anni("e", "3464.")
anni("f", "3465.")
anni("g", "3466.")
anni("h", "3469.")
g1("Ieſus ſonne of Ioſedech.")
g1("Ioachin.")
g2("From the captiuitie, the Iewes had no kinges: but the line of Dauid continued in theſe perſons from Iechonias to Chriſt.", note="italic explanatory rubric heading the 'line of Dauid' column")
g2("Salathiel.")
g2("Zorobabel.")
g2("Abiud.")
hist("c", "In the captiuitie by diligence of the prophetes, manie Iewes had great zele in true religion. And about the 24. yeare of the captiuitie Aſſuerus otherwiſe called Aſtiages, made Eſther Quene, and wicked Aman ſeeking to deſtroy al the Iewes in thoſe partes, was himſelf hanged on the gallowes which he had prepared for Mardocheus. Eſther. 7. &c.")
hist("d", "Euilmerodach deliuered Iechonias (or Ioachin) from priſon, and enterteyned him as a prince. 4. Reg. 25. v. 27.")
hist("e", "Baltazar being ſlaine, Darius king of Medes & Perſians poſſeſſed Babylon : & Cyrus ſucceding Darius, releaſed the Iewes from captiuitie, and gaue licence to Zorobabel, & Ieſus to reduce the people into Iurie. 2. Paral. 36. v. 22. 1. Eſd. 1.")
hist("f", "The Iewes being returned into Ieruſalem ſette vp an altar and offered ſacrifice. 1. Eſd. 3. v. 2.")
hist("g", "The next yeare they begane to build the temple. 1. Eſd. 3. v. 8.")
hist("h", "Artaxerxes ( otherwiſe called Cambyſes, alſo Aſſuerus ) forbade to perfect the")
schis("When the Monarchie came to the Chaldees by the powre of Nabuchodonoſor king of Babylon, there was greateſt confuſion of manie goddes, and of al kindes of idolatrie.")
schis("And great diſſention among the more lerned Grecians. For the Pithagorians put their chief happines, or Summum bonum, in the immortalitie of the ſoule. The Stoiks in moral vertues. The Achademikes cõceiued much")
scrip("The hiſtorie of Eſther Mardocheus and Aman written in the booke of Eſther in the captiuitie.")
scrip("Eſdras write the relexation of the Iewes from captiuitie. And Nehemias the reparation of Ieruſalem.")

# ---- printed 1093 (index 1097, S1) : 6th AGE cont. ----
page(1097, "1093", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Dauid.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto.")
runhead("", "OF THE OLD TESTAMENT.", "1093")
gcols("highpriests", "line_of_dauid")
anni("i", "3470.")
anni("k", "3490.")
anni("l", "3500.")
anni("m", "3502.")
anni("n", "3508.")
anni("o", "3509.")
anni("p", "3530.")
g1("Eliaſib.")
g1("Eliacim.")
g2("Azor.")
g2("Ioiada.")
hist("h", "temple. And Ieſus the Highprieſt returned into Babylon. 1. Eſd. 4. v. 7.")
hist("i", "Daniel vnderſtood by viſion, that Chriſt ſhould come within ſeuentie wekes which make 490. yeares from the perfecting of the temple, & the walles of Ieruſalem. Dan. 9. v. 25.")
hist("k", "Aggeus & Zacharias the prophets exhorted to build the temple. 1. Eſd. 5.")
hist("l", "Iudith killed Holofernes, either about this time, or in the dayes of Manaſſes before the captiuitie. Præfat. Iudith.")
hist("m", "The temple being perfected Malachias ( who is ſuppoſed to be Eſdras ) exhorted to offer ſacrifice with ſinceritie. Mal. 1. & 2.")
hist("n", "And Nehemias brought the kings Edict for the reparation of Ieruſalem. 2. Eſd. 2.")
hist("o", "Eſdras, Nehemias and others labored in repayring Ieruſalem, but were often interrupted. 2. Eſd. 3.")
hist("p", "About this time the citie was wel repayted with three walles. 2. Eſd. 3. & 7.", note="'repayted' as printed (for 'repayred') — preserved", unc=True)
hist(None, "And ſo by the iudgemẽt of ſome expoſiters, the count of ſeuentie wekes begane,")
schis("of pure ſpirites, as Angels, but could affirme nothing. The Peripatetikes placed the conſummation of al, in the aggregation of ſpiritual, corporal, and worldlie proſperitie.")
schis("The ſchiſmatical Samaritanes oppoſed againſt the building of the temple. 1. Eſd. 4.")
schis("The Saduces acknowleging only the fiue bookes of Moyſes reiected al other Scriptures, and denied the reſurrection.")
schis("The Scribes expounded holie Scriptures ſophiſtically.")
schis("The Phariſes were preciſe in the letter corrupting the ſenſe, making large hemmes")
scrip("Aggeus. Zacharias.")
scrip("Iudith, either here, or before the captiuitie.")
scrip("Malachias.")
sig("Rrrrr 3")

# ---- printed 1094 (index 1098, S1) : 6th AGE cont. (Alexander, Machabees, LXX) ----
page(1098, "1094", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Dauid.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso.")
runhead("1094", "AN HISTORICAL TABLE", "")
gcols("highpriests", "line_of_dauid")
anni("q", "3594.")
anni("r", "3644.")
anni("s", "3689.")
anni("t", "3700.")
anni("v", "3720.")
anni("w", "3750.")
anni("x", "3810.")
g1("Ionathan.")
g1("Iaddus.")
g1("Onias.")
g1("Simon. Priſcus.")
g1("Eleazarus.")
g1("Manaſſes an Apoſtata.", note="'Manaſſes an Apoſtata' in italic")
g1("Onias.")
g1("Simon.")
g1("Onias.")
g2("Sadoc.")
g2("Achim.")
g2("Eliud.")
g2("Eleazar.")
hist("p", "according to the prophecie of Daniel. ch. 9. v. 26.")
hist("q", "Nehemias returning from Perſia ( or Chaldea ) into Iurie found thicke water, for the fire, which Ieremie had hid in a deepe caue. 2. Mach. 1. v. 20. & 23.")
hist("r", "Alexander the great honored Iaddus the Highprieſt. Ioſeph. li. 11. c. 8. Antiq.")
hist("s", "Onias a moſt zelous godlie Highprieſt. 2. Mach. 4. was perſecuted by Simon a churchwarden, ſlaine by Andronicus a courtly minion, v. 34. And after his death prayed for al the people. ch. 15. v. 12.")
hist("t", "Ieſus the ſonne of Sirach writte the booke of Eccleſiaſticus in the time of this Simon Highprieſt, as ſemeth ch. 50. v. 24. & 25.")
hist("v", "The ſeuentie two Interpreters being ſent by Eleazarus Highprieſt to Ptolomeus Philadelphus king of Ægypt tranſlated the Hebrew Scriptures into Greke.")
hist("w", "An other Ieſus (Nephew of the former ) tranſlated Eccleſiaſticus into Greke. Prolog. Eccli:")
hist("x", "Philo the elder writte the booke of wiſdom in Greke. S. Ierom in pref.")
schis("of their garments, often waſhing themſelues, and the like.")
schis("Sanaballat a Grecian obtayned licence for his ſonne in law Manaſſes, the Apoſtata highprieſt, to build a temple in Garizim. Ioſeph. li. 11. c. 8. Antiq.")
schis("Ananias an other falſe pretender built an other ſchiſmatical temple in Ægypt.")
schis("In the time of Onias the ſe-")
scrip("Eccleſiaſticus conteyneth manie moral precepts, and is a ſtorehouſe of vertues : and holie myſteries.")
scrip("The booke of wiſdom is alſo reple-")

# ---- printed 1095 (index 1099, S1) : 6th AGE cont. (Machabees, Pompey) ----
page(1099, "1095", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Dauid.",
     "The ſacred Hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "OF THE OLD TESTAMENT.", ""),
     note="recto.")
runhead("", "OF THE OLD TESTAMENT.", "1095")
gcols("highpriests", "line_of_dauid")
anni("y", "3825.")
anni("z", "3846.")
anni("a", "3847.")
anni("b", "3853.")
anni("c", "3869.")
anni("d", "3878.")
anni("e", "⟨…?⟩", note="Pompey's capture of Ieruſalem: no Anni figure legibly recoverable for this (e) row on the heavily-foxed S1 leaf; not invented", unc=True)
anni("f", "4000.")
g1("Mathathias.")
g1("Iudas. Machabeus.")
g1("Ionathas.")
g1("Simon.")
g1("Ioanes. Hyrcanus.")
g1("Ariſtobulus.")
g1("Alexander.")
g1("Hyrcanus.")
g2("Mathan.")
g2("Iacob.")
g2("Ioſeph the husband of the moſt B. Virgin. Marie.", note="italic; the line of Dauid reaching Ioſeph/Marie")
hist("y", "Antiochus Epiphanes perſecuted the Church moſt cruelly, like as Antichriſt wil doe nere the end of the world. 1. Mach. 1. v. 11. & 2. Mach. 5. 6. 7.")
hist("z", "In defence of the Church Mathathias and his ſonnes with others made warres, killed, and ouerthrew al their enemies, aduanced religion, clenſed the tẽple, & deliuered the people from perſecution. 1. Mach. 2. &c. 1. Mach. 8. & ſeq.")
hist("d", "After the warres, the Iewes in Ieruſalem writte to the Iewes in Ægypt, exhorting them to kepe the feaſtes, and other rites, as they were obſerued in Iurie 2. Mach. 1. & 2.")
hist("e", "Pompeius the great taking Ieruſalem ſubdued the Iewes to the Romanes. He entered into the holy place, called Sancta Sanctorum, there prophaned holie thinges, caried away Ariſtobulus (who had bene Highprieſt) priſoner, & confirmed Hyrcanus in his place. After whom Caſſius alſo ſpoyled the temple. S. Aug. li. 18. c. 45. de ciuit.")
hist("f", "S. Iohn Baptiſt was borne of Elizabeth, who had bene long barren.")
schis("cond, his brother Iaſon obtayned for money to be highprieſt.")
schis("Antiochus ſet vp the abomination of deſolation wherof Daniel prophecied. ch. 9.")
schis("After Iaſon folowed more vſurpers of the Highprieſthood. Menelaus. Liſimachus. Alcimus.")
scrip("niſhed with much doctrine of vertue, and of diuine myſteries.")
scrip("The bookes of Machabees conteine the hiſtorie of the Iewes from Alexander the great to the time of Ioannes Hyrcanus highprieſt, aboue two hundred yeares.")

# ---- printed 1096 (index 1100, S1) : END OF THE SIXTH AGE AND OF THE OLD TESTAMENT ----
page(1100, "1096", "S1", ["Anni mūdi.", "High-prieſts.", "The line of Dauid.",
     "The ſacred hiſtorie.", "Schiſmes and infidelitie.", "Scriptures."],
     rh=("", "AN HISTORICAL TABLE", ""),
     note="verso; final leaf, ends the section with the italic closing rule.")
runhead("1096", "AN HISTORICAL TABLE", "")
gcols("highpriests", "line_of_dauid")
anni("g", "4001.")
anni("h", "4006.")
anni("i", "4012.")
anni("k", "4030.")
anni("l", "4034.")
g1("Antigonus")
g1("Anaelus.")
g1("Ariſtobulus.")
g1("Ioſue.")
g1("Simon.")
g1("Mathias")
g1("Ioſephus.")
g1("Iozarus.")
g1("Eleazar")
g1("Ioſue.")
g1("Annas")
g1("Iſmael.")
g1("Eleazar")
g1("Simon.")
g1("Caiphas.")
g2("IESVS CHRIST.", note="display capitals; the line of Dauid culminates in Christ")
hist(None, "And ſix monethes after, Chriſt our SAVIOVR was borne, of the B. Virgin Marie, in Bethleem ; circumciſed, adored by the Sages, and preſented in the Temple. When king Herod had reigned in Iudea.")
hist("g", "Ioſeph fled with the child & his mother into Ægypt, and Herod murthered the innocent infantes.")
hist("h", "Returning from Ægypt they dwelt in Nazareth.")
hist("i", "Chriſt at the age of twelue yeares remayning in Ieruſalem vnknowen to his parentes was found the third day in the temple amongſt the Doctors.")
hist("k", "S. Iohn Baptiſt preached and baptized in Iordan.")
hist(None, "Of whom Chriſt amongſt others, was baptized, and faſted in the deſert fourtie dayes.")
hist("l", "Chriſt crucified, redemed mankind ; aroſe from death ; aſcended to heauen ; & ſending the Holie Ghoſt planted his perpetual viſible Church.")
schis("Herodians held opinion that Herod was Chriſt, the Meſſias, whom the Iewes had long expected.")
schis("But Chriſt the Sonne of God coming into this world out of al theſe, & other old ſectes. And from time to time cutteth of al hæreſies, that riſe againſt his Church.", note="set in italic")
scrip("The firſt holie Scripture of the new Teſtament was S. Mathewes Goſpel writen about the yeare of Chriſt 41. And the laſt was S. Iohns Goſpel the yeare 99.")
divider("The end of the ſixth age, and of the old Teſtament.")

# ============================ UNCERTAIN ============================
unc(1078, "g 622.", "Anni figure: at 4x the two digits after '6' read like thin strokes (≈611); transcribed 622, forced by the clearly-printed h 687 (=622+65, Enoch begat Mathuſala at 65) and Iared→Enoch at 162 (460+162=622).")
unc(1079, "flould", "Schiſmes col.: printed 'flould' for 'floud' (intrusive l) — preserved diplomatically.")
unc(1084, "t 2484.", "Anni figure 2484 is clear at 4x; a '?'-shaped mark is printed/foxed immediately after it — possibly a compositor uncertainty mark (this age boundary is disputed).")
unc(1088, "brewerd", "Schiſmes col.: obscure 'beginning to brewerd to an other' (of sprouting corn); possibly for 'brerd'/'breard' (to sprout) — preserved as printed.")
unc(1090, "c 1900.", "Anni figure PRINTED as '1900.', a compositor error for 2900 (the row is Saul's appointment; sequence b 2880 < c < d 2920 requires 2900). Preserved as printed per diplomatic rule; corrected value noted.")
unc(1092, "kingodm", "Scriptures col.: printed 'kingodm' (metathesis for 'kingdom'); leaf read from S9 (S1 leaf illegible) — preserved as printed.")
unc(1094, "Zaraias", "single genealogy name low in col.2 (High-prieſts); High-prieſts vs Kinges-of-Iuda column assignment is slightly ambiguous on the foxed leaf.")
unc(1093, "repayted", "Historie col. (p-row): printed 'repayted' for 'repayred' — preserved as printed.")
unc(1095, "e-row Anni (Pompey)", "No Anni figure legibly recoverable for the Pompey (e) row on the heavily-foxed S1 leaf; recorded ⟨…?⟩ rather than invented. Historically ≈AM 3941/3947, but not asserted from the print.")
unc(None, "long-ſ / round-s micro-decisions", "Across ~560 diplomatic entries, ſ/s was applied at reading resolution by the roman fount's standard medial-initial-ſ / final-round-s behaviour, NOT per-instance 5x-zoom-adjudicated. Per this edition's known mixed 'sh'/'ſh' usage, individual ſh-cluster calls (diſtinguiſh, worſhipped, etc.) carry residual ambiguity; the ſ-count is an estimate, not a per-glyph audit.")
unc(None, "w vs vv", "No 'vv' was observed anywhere in this table; the roman body and the small italic Schiſmes/Scriptures apparatus both use a real single 'w' sort. Consistent with the OT roman-body prior; the genuine-'vv' minority (small OT annotation fount) does not surface in this section.")
unc(None, "French spacing / point placement", "The edition sometimes sets a space before high punctuation (: ; ? !) and the leaves are foxed; interior point placement inside references (e.g. 'v. 22. 23.') and space-before-punctuation were transcribed as seen but not every instance was individually adjudicated.")

# __PAGES__

# ============================ EMIT ============================
def finalize():
    # long-s count over all diplomatic text fields
    ls = sum(t.count("ſ") for t in (e["text"] for e in body))
    gt = {
        "locus": "matter/ot2/historical-table",
        "page_kind": "table",
        "title_display": "AN HISTORICAL TABLE OF THE TIMES, SPECIAL PERSONS, MOST NOTABLE THINGES, AND CANONICAL BOOKES OF THE OLD TESTAMENT.",
        "page_index": list(range(1077, 1101)),
        "page_labels_printed": [str(n) for n in range(1073, 1097)],
        "ocr_dir": "archive-ot2-1610",
        "scan": "S1",
        "raster": "jp2 native (3334x4684 per leaf); read via ocr-spike/jp2_page.py",
        "gap_recovery": {
            "printed_1077": "ABSENT from S1 scan: raw jp2 _1081.jp2 and _1082.jp2 are byte-identical (md5 2abf198b...), both imaging printed p.1078; printed p.1077 leaf was not captured (duplicate substituted). Recovered from the SAME 1610 edition/typesetting via scan S9 (archive-holiebible-ot2, jp2 index 1089, printed 1077). Continuity verified: S9 p.1077 ends 'w Abraham dyed at the age' -> S1 p.1078 resumes 'of 175. yeares. Gen. 25.'",
            "printed_1088": "S1 leaf (jp2 index 1092) is severely bleached/degraded and largely illegible; text read from S9 (archive-holiebible-ot2 jp2 index 1100, printed 1088), identical typesetting.",
            "printed_1089": "S1 leaf (jp2 index 1093) is faint/degraded; text confirmed from S9 (archive-holiebible-ot2 jp2 index 1101, printed 1089), identical typesetting.",
            "witness_equivalence": "S9 verified to be the SAME 1610 typesetting as S1 (identical wording, line breaks and Anni-mundi figures on printed p.1078: S1 index1081 == S9 index1090). Diplomatic text is therefore scan-independent for the recovered leaves.",
        },
        "page_label_printed": "1073-1096 (24 leaves; see page_labels_printed for the list)",
        "running_header": {"left": "", "center": "AN HISTORICAL TABLE (verso) / OF THE OLD TESTAMENT. (recto)",
                           "right": "printed page number (recto top-right / verso top-left)",
                           "note": "per-leaf running_header values are recorded in pages[]"},
        "layout_note": (
            "Six-Ages synoptic chronological table across 24 printed leaves (pp.1073-1096). Each leaf is a "
            "multi-column grid whose columns FLOW INDEPENDENTLY top-to-bottom (they are NOT row-aligned across "
            "columns); the only cross-column tie is the resetting key-letter a..z shared by the Anni-mundi column "
            "and the Historie column (and occasionally the Schiſmes column, e.g. 'o' on p.1077). Reading order in "
            "this GT is per leaf, column by column, each column de-hyphenated internally. See structure_note for "
            "the column-set evolution and age dividers."),
        "structure_note": (
            "Six-Ages synoptic chronological table. 5 columns on the 1st-3rd-age opening leaves "
            "(Anni mundi | Patriarches | The sacred Historie | Schismes and infidelitie | Scriptures) "
            "expanding to 6 columns once the genealogy splits: pp.1075-1076 use 'The line of Leui' + "
            "'The line of Iudas'; pp.1081-1091 use 'High-priests' + 'The line of Iudas' (5th age heads it "
            "'Kinges of Iuda'); pp.1092-1096 (6th age) use 'High-priests' + 'The line of Dauid'. Columns "
            "flow INDEPENDENTLY; cross-column tie is the resetting key-letter (a..z) shared by the Anni "
            "and Historie columns. Age dividers are full-width rules: END OF 1st/BEGINNING OF 2nd (p.1075), "
            "END OF 2nd/BEGINNING OF 3rd (p.1076), END OF THIRD AGE (p.1080), BEGINNING OF THE FOVRTH AGE "
            "(p.1081), END OF THE FOVRTH AGE (p.1086), BEGINNING OF THE FIFTH AGE (p.1087), END OF THE FIFTH "
            "AGE (p.1091), BEGINNING OF THE SIXTH AGE (p.1092), and 'The end of the sixth age, and of the old "
            "Testament.' (p.1096). Running header verso 'AN HISTORICAL TABLE', recto 'OF THE OLD TESTAMENT.' "
            "Quire signatures at feet: Ppppp / Ppppp2 / Ppppp3 (1st gathering), Qqqqq / Qqqqq2 / Qqqqq3, "
            "Rrrrr / Rrrrr2 / Rrrrr3."),
        "reading_order": "per page, column by column (Anni; genealogy col(s); Historie; Schismes; Scriptures); each column de-hyphenated internally.",
        "glyph_regime_resolved": (
            "Roman body founts throughout, set with real single 'w' sort (NO 'vv' anywhere in this table's "
            "body/italic apparatus that was observed). long-ſ applied per the roman fount's standard "
            "medial/initial behaviour visible in the high-res rasters; word-final round-s. u/v and i/j swaps "
            "preserved as printed (vpon, vnderstand, geue, haue, euer, liued, gouerned, Iacob, Ioseph, Iudas). "
            "Latin abbreviations (Gen. Reg. Par. Paral. Exod. Num. Deut. Eccli. Iud. Iudic. li. c. v. an. æt.) "
            "kept as printed; 'æ'/'Œ' kept; ampersand '&' as printed; nasal-macron abbreviations kept "
            "(cō-, remembŕing->set as printed). Figures/dates transcribed as printed."),
        "body": body,
        "intervals": intervals,
        "apparatus": apparatus,
        "pages": pages_meta,
        "uncertain": uncertain,
        "glyph_counts": {"long_s_count_transcribed": ls,
                         "note": "recompute by counting U+017F across body[].text; page has real single 'w' only."},
        "observer": "agent:historical-table",
        "observed_at": "2026-07-20",
        "method": (
            "Visual-multimodal read of the full-resolution jp2 rasters (S1 archive-ot2-1610, indices 1077-1100), "
            "page by page, with column-band crop+contrast-enhancement for the degraded S1 leaves. VALIDATIONS: "
            "(1) Localization - display title 'AN HISTORICAL TABLE OF THE TIMES...' on p.1073 (index1077) and "
            "closing rule 'The end of the sixth age, and of the old Testament.' on p.1096 (index1100); running "
            "headers AN HISTORICAL TABLE / OF THE OLD TESTAMENT confirm the section throughout. (2) Identity - "
            "1610 OT2 (S1 'archive-ot2-1610'); preceding section (Table of Epistles, 'Deo Gratias', p.1072) and "
            "the Six-Ages content confirm placement in the 1610 Second Tome back matter; recovered leaves taken "
            "from the SAME 1610 typesetting (S9) not a different edition. (3) Placement - printed labels 1073-1096, "
            "running headers and quire signatures recorded per page. (4) Completeness - all 24 printed leaves "
            "transcribed; the S1 scan-defect (printed 1077 absent, 1088/1089 degraded) recovered from the identical "
            "S9 typesetting and flagged in gap_recovery; no page silently dropped. janvier/DR used only as a "
            "content sanity-check on which biblical events fall where, never as a spelling oracle."),
        "confidence": (
            "HIGH on localization/identity/placement/completeness and on structure (columns, ages, dividers, "
            "key-letters, figures). HIGH-MEDIUM on the roman-body wording. MEDIUM on per-glyph long-ſ/round-s "
            "micro-decisions (applied at reading resolution by standard fount behaviour, not per-instance 5x "
            "adjudicated across ~800 entries) and on the smallest italic Schismes/Scriptures type on the foxed "
            "S1 leaves; specific worn figures/words are flagged in uncertain[]. No 'vv' observed; body uses a real 'w'."),
    }
    OUT.write_text(json.dumps(gt, ensure_ascii=False, indent=1), encoding="utf-8")
    # sanity
    for e in body:
        core = unicodedata.normalize("NFC", e["text"])
    print("WROTE", OUT)
    print("body entries:", len(body), "| intervals:", len(intervals),
          "| apparatus:", len(apparatus), "| pages:", len(pages_meta),
          "| uncertain:", len(uncertain), "| long_s:", ls)

if __name__ == "__main__":
    finalize()
