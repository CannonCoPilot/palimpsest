#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source_inventory_audit.py — ONE locked-down set of witness volumes; no source counted twice (2026-07-27).

THE RISK SIR NAMED. Several sources exist on disk in BOTH a high-resolution `jp2-*` rendering and a `pdf-*`
one. If both are OCR'd, addressed, localized and scored, the same physical book can enter the audit twice —
once well and once badly — which inflates witness counts, double-weights one edition's idiosyncrasies in any
cross-source alarm, and makes a coverage number mean two different things depending on which volume answered.

THE RULE: **prefer the jp2 where one exists, and never admit both renderings of the same source.**

This audits every stage, not just the audit: the OCR corpus on disk, the registry's declared volumes, the
page-address caches, and the localization caches. A volume present at any stage but not admitted by the
registry is reported as UNREGISTERED — it costs disk and compute and can leak into a later join.

Writes `source-inventory-audit.json` for the report to render, so the reader can confirm the witness set at a
glance rather than taking it on trust.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import reocr_core as core            # noqa: E402
import curated_sources as CS         # noqa: E402
import jp2_page                      # noqa: E402

MSL = json.loads((HERE / "master-source-list.json").read_text())
STORE = core.BASE_OCR_ROOT
_FMT = re.compile(r"^(jp2|pdf|archive|eebo)[-_]")


def rendering(ocr_dir: str) -> str:
    m = _FMT.match(ocr_dir or "")
    return m.group(1) if m else "other"


def source_key(ocr_dir: str) -> str:
    """The physical source a volume renders, independent of HOW it was rendered.

    `jp2-S04` and `pdf-S04` are the same book at two resolutions; they must collapse to one key so a duplicate
    is detectable at all."""
    s = re.sub(r"^(jp2|pdf|archive|eebo)[-_]", "", ocr_dir or "")
    return s.lower()


def audit() -> dict:
    declared, by_source = {}, {}
    for w in MSL["witnesses"]:
        sid = w["source"]
        for v in (w.get("volumes") or []):
            od = v.get("ocr_dir")
            if not od:
                continue
            declared[od] = {"source": sid, "counts_as_witness": bool(w.get("counts_as_witness")),
                            "curated": bool(w.get("curated"))}
            by_source.setdefault(sid, []).append(od)

    on_disk = sorted(p.name for p in STORE.iterdir() if p.is_dir()) if STORE.exists() else []
    addressed = sorted(p.name[len(".page-address-"):-len(".json")] for p in HERE.glob(".page-address-*.json"))
    localized = sorted(p.name[len(".corpus-localize-"):-len(".json")] for p in HERE.glob(".corpus-localize-*.json"))

    # DUPLICATE RENDERINGS: same physical source, more than one rendering present at ANY stage.
    seen: dict = {}
    for od in set(on_disk) | set(addressed) | set(localized) | set(declared):
        seen.setdefault(source_key(od), set()).add(od)
    dupes = {k: sorted(v) for k, v in seen.items() if len({rendering(x) for x in v}) > 1}

    findings = []
    for key, vols in sorted(dupes.items()):
        jp2 = [v for v in vols if rendering(v) == "jp2"]
        others = [v for v in vols if rendering(v) != "jp2"]
        preferred = jp2[0] if jp2 else sorted(others)[0]
        for v in vols:
            if v == preferred:
                continue
            findings.append({
                "duplicate_of": preferred, "volume": v, "source_key": key,
                "declared": v in declared, "addressed": v in addressed, "localized": v in localized,
                "rule": "prefer jp2; never admit two renderings of one source",
            })

    unregistered = sorted(set(addressed) | set(localized) - set(declared))
    unregistered = [v for v in sorted(set(addressed) | set(localized)) if v not in declared]
    # A volume that is declared but never processed is the opposite failure: a witness we claim and do not use.
    unprocessed = [v for v, d in sorted(declared.items())
                   if d["counts_as_witness"] and d["curated"] and v not in localized]

    # IS EACH ADMITTED VOLUME ACTUALLY SERVED FROM jp2? The directory NAME does not answer this: `pdf-S03a`,
    # `pdf-S03b` and `pdf-S09nt` are all mapped to jp2 images despite the prefix, so a name-based audit would
    # report a problem that does not exist AND miss the one that does.
    # R7.5b: this call site only ever wanted the SET of ocr_dirs the project can address, so it takes the
    # registry's key set directly. What the set MEANS has narrowed, and the narrowing is the point: it used
    # to be "this folder has a raster directory", and it is now "this folder names a witness". `jp2-S06` is
    # deliberately absent from it — that identifier spans two settings 53 years apart, so a volume declared
    # under it is not jp2-backed, it is UNADDRESSED, and it should report as such until R7.5a re-keys it.
    jp2_map = set(jp2_page.OCR_DIR_TO_WITNESS)
    jp2_backing = {v: (v in jp2_map) for v in declared}
    no_jp2 = sorted(v for v, d in declared.items()
                    if d["counts_as_witness"] and d["curated"] and v not in jp2_map)
    jp2_available_unused = sorted(v for v in jp2_map if v not in declared)

    admitted = sorted(v for v, d in declared.items()
                      if d["counts_as_witness"] and d["curated"]
                      and not any(f["volume"] == v for f in findings))
    return {
        "rule": "prefer the jp2 rendering where one exists; never admit both renderings of one source",
        "counts": {"on_disk": len(on_disk), "declared": len(declared), "addressed": len(addressed),
                   "localized": len(localized), "admitted_witness_volumes": len(admitted)},
        "admitted": admitted,
        "by_source": {s: sorted(v) for s, v in sorted(by_source.items())},
        "jp2_backing": jp2_backing,
        "admitted_without_jp2_backing": no_jp2,
        "jp2_available_but_not_registered": jp2_available_unused,
        "duplicate_renderings": findings,
        "unregistered_but_processed": unregistered,
        "declared_curated_but_never_localized": unprocessed,
        "on_disk": on_disk, "addressed": addressed, "localized": localized,
        "curated_source_ids": sorted(CS.CURATED) if hasattr(CS, "CURATED") else None,
    }


if __name__ == "__main__":
    a = audit()
    print(json.dumps({k: v for k, v in a.items() if k not in ("on_disk", "addressed", "localized")}, indent=1))
    (HERE / "source-inventory-audit.json").write_text(json.dumps(a, ensure_ascii=False, indent=1))
    bad = (a["duplicate_renderings"] or a["unregistered_but_processed"]
           or a["declared_curated_but_never_localized"] or a["admitted_without_jp2_backing"]
           or a["jp2_available_but_not_registered"])
    print("\nSELF-CHECK:", "CLEAN" if not bad else "DEFECTS FOUND (see above)")
