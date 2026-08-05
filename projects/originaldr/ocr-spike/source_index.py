#!/usr/bin/env python3
"""Per-source "ought-to-contain" index — the backward-gate E(v) denominator (Phase 0b, 2026-07-08).

QC contract §1.1 backward gate: a locus that fails to reach its expected witness depth E(v) is flagged,
triggering investigation of *every source that ought to contain it*. That requires an authoritative map
of what each witness OUGHT to attest — independent of what OCR happened to localize. This module builds it:

  * Manifest-seeded: each source's declared PHYSICAL coverage (what the volume IS) → skeleton book set +
    apparatus front/back regions. Scan coverage is expressed as book-ordinal spans (OT=1-46, NT=47-73,
    appendix=74-76), the physical fact.
  * Detection-refined: transcription coverage is taken from the actual processed reads/{name}.json book
    set (a transcription's coverage IS what it transcribed) — more precise than a declared span.

E(v) is DERIVED, not assumed: E(v)[locus] = the number of counting witnesses whose ought-to-contain
includes that locus. This reproduces the plan's NT=12 / OT=6..10 targets as a consequence of the roster.

Emits: source-index.json = {sources:{ought per source}, loci_ev:{inverted per-locus expected witnesses},
summary}. Reads the witness roster (counts_as_witness) from master-source-list.json.
"""
from __future__ import annotations
import json
from pathlib import Path

DR = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/imports/Scripture/Bibles/DouayRheims_DR")
SCRATCH = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr")
RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/mask_engine/originaldr_reconstruction")
SKELETON = RECON / "skeleton.json"
MANIFEST = DR / "sources/dr-sources-manifest.json"
MSL = SCRATCH / "ocr-spike/master-source-list.json"
READS = SCRATCH / "reconstruction/reads"
OUT = SCRATCH / "ocr-spike/source-index.json"

# Scan-source declared physical coverage (manifest-seeded). ("range",lo,hi) inclusive ordinal span, or
# ("set",[ordinals]). apparatus = front/back regions the volume carries (per manifest `apparatus`).
ALL_APP = ["ot_front", "ot_back", "nt_front", "nt_back"]
SCAN_COVERAGE = {
    "S1": (("range", 1, 76), ALL_APP),
    "S2": (("range", 1, 20), ["ot_front"]),                       # OT First Tome, Genesis-Job
    "S3": (("set", [*range(1, 47), 74, 75, 76]), ["ot_front", "ot_back"]),  # complete OT + appendix
    "S4": (("range", 47, 73), ["nt_front", "nt_back"]),           # complete NT
    "S5": (("range", 47, 73), ["nt_front"]),
    "S6": (("range", 1, 76), ALL_APP),
    "S8": (("range", 47, 73), ["nt_front"]),
    "S9": (("range", 1, 76), ALL_APP),
    "S10": (("range", 47, 73), ["nt_front"]),
    "S11": (("set", [47]), ["nt_front"]),                         # partial sampler: Matthew + NT front
    "S12": (("set", [1]), ["ot_front"]),                          # Genesis + OT front
    "S13": (("set", [6]), ["ot_front"]),                          # josue
    "S14": (("set", [21]), ["ot_front"]),                         # psalms — PILOT target
    "S15": (("set", [27]), ["ot_front"]),                         # isaie
}
TRANSCRIPTIONS = ["sabates_a", "madueke_b", "s_dismas", "odr_com"]  # madueke_a demoted (not a witness)


def expand(cov) -> set[int]:
    kind = cov[0]
    if kind == "range":
        return set(range(cov[1], cov[2] + 1))
    return set(cov[1])


def main() -> int:
    sk = json.loads(SKELETON.read_text())
    books = sk["books"]
    by_ord = {b["ordinal"]: b for b in books}
    by_slug = {b["slug"]: b for b in books}
    refdocs = sk["reference_docs"]
    region_slots: dict[str, list[str]] = {}
    for r in refdocs:
        region_slots.setdefault(r["region"], []).append(r["slot_id"])

    msl = json.loads(MSL.read_text())
    counting = {w["source"] for w in msl["witnesses"] if w.get("counts_as_witness")}

    sources: dict[str, dict] = {}

    # ---- scan sources: manifest-seeded ordinal spans ----
    for sid, (cov, apps) in SCAN_COVERAGE.items():
        if sid not in counting:
            continue
        ords = sorted(expand(cov))
        bk = [by_ord[o] for o in ords if o in by_ord]
        slots = [s for region in apps for s in region_slots.get(region, [])]
        sources[sid] = {
            "kind": "scan", "seed": "manifest",
            "books": {b["slug"]: {"testament": b["testament"], "chapters": b["chapters"],
                                  "is_appendix": b["is_appendix"], "argument_id": b["argument_id"]}
                      for b in bk},
            "front_back_matter": slots,
            "n_books": len(bk), "n_chapters": sum(b["chapters"] for b in bk),
        }

    # ---- transcriptions: detection-refined from actual reads book set ----
    for name in TRANSCRIPTIONS:
        if name not in counting:
            continue
        p = READS / f"{name}.json"
        if not p.exists():
            sources[name] = {"kind": "transcription", "seed": "reads", "status": "MISSING"}
            continue
        d = json.loads(p.read_text())
        slugs = {r["skeleton_id"].split("/")[1] for r in d.get("reads", [])
                 if r.get("skeleton_id", "").startswith("scripture/")}
        bk = [by_slug[s] for s in slugs if s in by_slug]
        sources[name] = {
            "kind": "transcription", "seed": "reads (detection-refined)",
            "books": {b["slug"]: {"testament": b["testament"], "chapters": b["chapters"],
                                  "is_appendix": b["is_appendix"], "argument_id": b["argument_id"]}
                      for b in bk},
            "front_back_matter": [],  # transcription apparatus tracked separately (Phase 4)
            "n_books": len(bk), "n_chapters": sum(b["chapters"] for b in bk),
        }

    # ---- invert → per-locus E(v) denominator ----
    scripture_books: dict[str, dict] = {}
    book_arguments: dict[str, dict] = {}
    for b in books:
        attest = sorted(s for s, v in sources.items() if b["slug"] in v.get("books", {}))
        scripture_books[b["slug"]] = {
            "testament": b["testament"], "n_chapters": b["chapters"],
            "expected_witnesses": attest, "E_v": len(attest),
        }
        # book_argument attested by sources that cover the book AND carry apparatus (scans w/ front/back,
        # or madueke_b which is apparatus-rich); transcriptions w/o apparatus reads excluded.
        arg_attest = sorted(s for s in attest
                            if (sources[s]["kind"] == "scan" and sources[s]["front_back_matter"])
                            or s == "madueke_b")
        book_arguments[b["slug"]] = {"expected_witnesses": arg_attest, "E_v": len(arg_attest)}

    front_back: dict[str, dict] = {}
    for r in refdocs:
        slot = r["slot_id"]
        attest = sorted(s for s, v in sources.items() if slot in v.get("front_back_matter", []))
        front_back[slot] = {"region": r["region"], "testament": r["testament"],
                            "expected_witnesses": attest, "E_v": len(attest)}

    out = {
        "_doc": "Per-source ought-to-contain index — backward-gate E(v) denominator (Phase 0b, 2026-07-08). "
                "E(v) is DERIVED per-locus from source coverage, not assumed. Scripture chapters inherit "
                "their book's E(v). Supersedes flat NT=12/OT=6 assumption (which it reproduces).",
        "framework": "locus-level QC (sparkling §0′)",
        "counting_witnesses": sorted(counting),
        "sources": sources,
        "loci_ev": {
            "scripture_books": scripture_books,   # chapter loci inherit book E(v)
            "book_arguments": book_arguments,
            "front_back_matter": front_back,
        },
        "summary": {
            "n_counting_witnesses": len(counting),
            "n_books_total": len(books),
            "ev_scripture_min": min(v["E_v"] for v in scripture_books.values()),
            "ev_scripture_max": max(v["E_v"] for v in scripture_books.values()),
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    # ---- console report ----
    print("=== SOURCE INDEX — ought-to-contain / backward-gate E(v) denominator (2026-07-08) ===\n")
    print(f"Counting witnesses ({len(counting)}): {', '.join(sorted(counting))}\n")
    print("PER-SOURCE ought-to-contain:")
    for sid, v in sources.items():
        print(f"  {sid:<12} {v['kind']:<14} books={v.get('n_books', 0):>3} chapters={v.get('n_chapters', 0):>4} "
              f"front/back={len(v.get('front_back_matter', []))}  [{v.get('seed')}]")
    print("\nDERIVED E(v) — scripture books (min/typical/max across 76 books):")
    ots = [v["E_v"] for v in scripture_books.values() if v["testament"] == "OT"]
    nts = [v["E_v"] for v in scripture_books.values() if v["testament"] == "NT"]
    apx = [v["E_v"] for v in scripture_books.values() if v["testament"] == "APPENDIX"]
    print(f"  OT  E(v): min={min(ots)} max={max(ots)}  (plan baseline 6, range 6..10)")
    print(f"  NT  E(v): min={min(nts)} max={max(nts)}  (plan target 12)")
    print(f"  APX E(v): min={min(apx)} max={max(apx)}")
    print("\n  sample loci:")
    for slug in ["genesis", "psalms", "isaie", "malachie", "matthew", "jude", "prayer-of-manasses"]:
        e = scripture_books.get(slug, {})
        print(f"    {slug:<20} E(v)={e.get('E_v'):>2}  {e.get('expected_witnesses')}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
