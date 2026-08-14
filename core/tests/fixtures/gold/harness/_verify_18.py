import sys
import instance_edges, masking_map

IDX = 18

instance_edges.RULES[IDX] = [
    {   # GENERIC tiling layer: 3 top-level parts (Tertullian's 3 classes), tiled over the
        # whole main matter. Header form: "\n\nPart First.|Second.|Third.". tile=True ⇒ each
        # part spans to the next part start (last → EOF). Generic layer (body already covers,
        # but part matches the gold hierarchy volume→part→treatise→chapter).
        "type": "part",
        "kind": "regex_in_span",
        "pattern": r"(?m)^Part (?:First|Second|Third)\.",
        "at": "start", "tile": True,
        "expected_count": 3,
    },
    {   # PRIMARY SPECIFIC tiling layer: 23 translated treatises, each opening with a
        # bracketed translator credit "[Translated by <name>.]". tile=True ⇒ each treatise
        # spans to the next credit (last → EOF), tiling all main matter from the first credit
        # to document end. This is the body's SPECIFIC layer the detector grades.
        "type": "translation",
        "kind": "regex_in_span",
        "pattern": r"\[Translated by",
        "at": "start", "tile": True,
        "expected_count": 23,
    },
    {   # SPECIFIC markers: 743 in-body chapter headings ("Chapter <roman>.", em-dash title or
        # bare-then-prose). Negative lookaheads exclude the per-treatise chapter-CONTENTS-LIST
        # echoes (consecutive "Chapter I.\n\nChapter II." runs and their tails before
        # Elucidations / a treatise roman-number). tile=False ⇒ thin markers over the
        # translation tile, NOT swallowing the prose body.
        "type": "chapter",
        "kind": "regex_in_span",
        "pattern": r"(?m)^Chapter [IVXLC]+\.(?!\n\nChapter [IVXLC]+\.)(?!\n\nElucidations\.)(?!\n\n[IVXLC]+\.\n\n)",
        "at": "start", "tile": False,
        "expected_count": 743,
    },
    {   # PRIMARY masked apparatus: 6280 numbered footnote lines of the form
        # "\n<n>\xa0\xa0\xa0 <text>" (newline + number + three nbsp + space + text), interleaved
        # after each chapter. tile=False ⇒ each note is a bounded marker (spans to next \n\n),
        # overlaid ON TOP of the chapter/translation tile as its own typed footnotes element.
        "type": "footnotes",
        "kind": "regex_in_span",
        "pattern": r"(?m)^\d+\xa0\xa0\xa0 ",
        "at": "start", "tile": False,
        "expected_count": 6280,
    },
    {   # SPECIFIC apparatus (mask=False commentary): 13 "Elucidations" appendix blocks — the
        # American Editor's first-person critical essays appended after individual treatises.
        # Block form: "Elucidations.\n\n———…—\n\n<Roman>.\n\n(". tile=False ⇒ marker on top of
        # the translation tile. Excludes the ~bare "Elucidations." forward-refs in contents lists.
        "type": "commentary",
        "kind": "regex_in_span",
        "pattern": r"(?m)^Elucidations\.\n\n[—–-]{3,}\n\n[IVXLC]+\.\n\n\(",
        "at": "start", "tile": False,
        "expected_count": 13,
    },
    {   # SPECIFIC apparatus (mask=True introduction): 5 "Introductory Notice"-titled editorial
        # notices heading specific treatises. tile=False ⇒ marker over the translation tile.
        "type": "introduction",
        "kind": "regex_in_span",
        "pattern": r"Introductory Notice",
        "at": "start", "tile": False,
        "expected_count": 5,
    },
]

masking_map.SUPPLEMENT[IDX] = [
    # ── Front-matter seam bridges: the gold singular end_anchors mark the START of the next
    # block, so the heading/tail text BETWEEN consecutive singulars is left bare. Each bridge
    # closes one seam, typed as the tail-owner of the block it belongs to.
    {   # [104,128) "Ethical.\n\nIntroduction\n\n": tail of the top-level Table of Contents
        # (last entry) + the "Introduction" heading line → contents.
        "type": "contents",
        "start_anchor": "Ethical.\n\nIntroduction\n\n",
        "end_anchor": "Originally printed in 1885, the ten-volume set, Ante-Nicene Fathers",
    },
    {   # [1105,1136) "Tim Perrine CCEL Staff Writer\n\n": signature tail of the CCEL set
        # introduction → introduction.
        "type": "introduction",
        "start_anchor": "Tim Perrine CCEL Staff Writer",
        "end_anchor": "The Writings of the Fathers Down to A.D. 325\n\nANTE-NICENE FATHERS",
    },
    {   # [1635,1679) "The Nicene Council\n\nPreface.\n\n———\n\n": Nicene-Council motto tail of
        # the title page + the Preface heading line → title_page.
        "type": "title_page",
        "start_anchor": "The Nicene Council\n\nPreface.",
        "end_anchor": "We present a volume widely differing, in its contents",
    },
    {   # [4409,4444) "may be found not less acceptable.\n\n": closing clause tail of the
        # volume Preface → preface.
        "type": "preface",
        "start_anchor": "may be found not less acceptable.",
        "end_anchor": "Apologetic.\n\nTitle Page.\n\nIntroductory Note.\n\nApology.\n\nOn Idolatry.",
    },
    {   # Part-First contents list [4442,4697): the "Apologetic. / Title Page. / ..." treatise
        # list printed between the volume Preface and the Part First header. Typed `contents`
        # (a part-level table of contents), giving the specific layer for this strip.
        "type": "contents",
        "start_anchor": "Apologetic.\n\nTitle Page.\n\nIntroductory Note.\n\nApology.\n\nOn Idolatry.\n\nThe Shows, or De Spectaculis.",
        "end_anchor": "Part First.\n\nIntroductory Note.",
    },
    {   # Part-First editorial framing block [4697,57915): "Part First. / Introductory Note. /
        # [a.d.145–220] …" — the editor's biographical Introductory Note essay plus the Holmes
        # Introductory Notice and the Apology chapter-contents list, all BEFORE the first
        # translation credit (the translation tile starts at 57915). Typed `commentary` (the
        # Part First Introductory Note is editorial commentary per the gold part exemplar); the
        # footnotes / introduction markers overlay ON TOP. This is the specific tile bridging
        # the front-matter singulars to the translation tile (no gap).
        "type": "commentary",
        "start_anchor": "Part First.\n\nIntroductory Note.\n\n————————————\n\n[ a.d. 145–220.] When our Lord repulsed",
        "end_anchor": "[Translated by the Rev. S. Thelwall, Late Scholar of Christ's College, Cantab.]",
    },
]

a = masking_map.audit(IDX)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("n_sparse_runs:", a["n_sparse_runs"], "sparse_chars:", a["sparse_chars"])
for r in a["sparse_regions"][:15]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:70]))

# Count-gate verification
import instance_edges as ie
from harness import project_for
t = project_for(IDX).reference_text()
print("\n--- COUNT GATES ---")
for rule in ie.RULES[IDX]:
    got = len(ie.materialize(t, rule))
    print(f"GATE {rule['type']:<12}: {got} == {rule['expected_count']} -> {'GREEN' if got==rule['expected_count'] else 'RED'}")
