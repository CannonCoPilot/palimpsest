import sys;import instance_edges, masking_map

# 114 surahs (chapter, SPECIFIC) tile the main body. Each surah body opens with its
# ALL-CAPS name line immediately followed by a "(Revealed before/after Hijrah)" line.
# A literal "(Reveal" scan yields 111; the 3 misses are OCR-garbled descenders of the
# SAME marker. The name-line + "(Rev..." (tolerant) regex recovers all 114.
#   garbled: AS-SAFFAT  "(Reve;led hefi,re l fiirah)"   @ name-line 976908
#            AL-GHASHIYAH "(Revca/ecl hefi1re flijrah)" @ name-line 1317113
#            AL-IN SHIRAH "(Revca/ecl hefi1re flijr:ih)" @ name-line 1327884
# Leading char class includes the apostrophe so 'ABASA (surah 80) is caught.
instance_edges.RULES[107] = [
    {
        "type": "chapter",
        "kind": "regex_in_span",
        "pattern": r"(?m)^['‘’A-Z][^\n]{0,30}\n\(Rev[^\n]{0,40}",
        "at": "start", "tile": True,
        "expected_count": 114,
    },
]

# Front-matter completion (specific layer). The gold singular masks leave thin
# GENERIC_ONLY gaps where no SPECIFIC mask exists: the half-title + title imprint /
# edition-history block before the copyright, the 25c ISBN tail, the "List of Parts
# with Page Numbers" Juz' TOC + alpha-list, the preface->foreword seam, and the
# "Index of Symbols Denoting Pauses" pause-key. All are front matter / contents.
masking_map.SUPPLEMENT[107] = [
    # half-title + title block + imprint/edition-history + ISBN tail + CONTENTS-head
    # + the Juz' Parts TOC + alpha-list, up to the first Foreword. (Overlaps the gold
    # title_page/copyright/contents/preface masks; harmless — both layers are SPECIFIC.)
    {"type": "front_matter", "start_anchor": "<<BOF>>",
     "end_anchor": "In 2004 we published, under the auspices"},
    # front-matter pause-symbols key, between the Foreword end and Surah 1.
    {"type": "front_matter", "start_anchor": "Index of Symbols Denoting\nPauses",
     "end_anchor": "AL-FATIHAH\n(Rev"},
]

a = masking_map.audit(107)
print("coverage:", a["coverage_pct"])
print("counts:", {k: v for k, v in a["type_counts"].items() if v})
print("unresolved:", a["unresolved"])
print("n_sparse_runs:", a["n_sparse_runs"], "sparse_chars:", a["sparse_chars"])
for r in a["sparse_regions"][:12]:
    print(" sparse", r["cls"], r["start"], r["end"], r["len"], repr(r.get("head", "")[:60]))

# count gate
import instance_edges as ie
t = masking_map.project_for(107).reference_text()
for rule in ie.RULES[107]:
    starts = ie.materialize(t, rule)
    print(f"GATE {rule['type']}: {len(starts)} vs {rule['expected_count']} ->",
          "GREEN" if len(starts) == rule["expected_count"] else "RED")
