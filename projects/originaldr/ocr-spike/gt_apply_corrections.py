#!/usr/bin/env python3
"""gt_apply_corrections.py — fold Sir's reviewed corrections into a ground-truth transcription.

Reusable per-locus. Reads ground-truth/<slug>.json + ground-truth/corrections/<slug>.corrections.json,
verifies each correction's `original` against the current line (drift guard — never blind-apply),
writes the corrected text, and:
  * empty-corrected line  -> role='excluded'; if it's the LAST body line and short (<=3 words),
    role='catchword' (reader-convenience word duplicated atop the next page; excluded from concat).
  * resolves any `uncertain` entry the reviewer touched into `resolved_uncertain`.
Backs up the pre-review GT, records a `review` provenance block, then prints a dual-track re-score
of the corrected GT vs the existing diplomatic OCR and vs s_dismas.

Usage: ocr-venv/bin/python ocr-spike/gt_apply_corrections.py <slug>
"""
from __future__ import annotations
import json, re, shutil, sys
from pathlib import Path

SPIKE = Path(__file__).resolve().parent
ROOT = SPIKE.parent
GT_DIR = SPIKE / "ground-truth"
CORR_DIR = GT_DIR / "corrections"
sys.path.insert(0, str(SPIKE))
from char_identity import edit_ratio, fold_archaic  # noqa: E402


def body_concat(gt: dict) -> str:
    """Scripture body as a single string: corrected line text, excluded/catchword lines dropped,
    line-end hyphens joined."""
    parts = [L["text"] for L in gt["body"] if L.get("role") not in ("excluded", "catchword")]
    s = " ".join(parts)
    return re.sub(r"-\s+", "", s)  # join hyphenated line-ends


def rescore(gt: dict) -> None:
    # scripture single-page re-score only (OCR vs GT + s_dismas on-page span). Matter / multi-page sections
    # have no single-page verse reference and a list page_index (which the :04d OCR glob can't format) — skip.
    if not isinstance(gt.get("page_index"), int):
        print(f"\n=== re-score skipped (matter/multi-page section '{gt.get('locus')}' — "
              f"no single-page verse reference) ===")
        return
    raw = re.sub(r"⟨([^?⟩]+)\?⟩", r"\1", body_concat(gt))
    # existing OCR for genesis (archive-ot1-1609 p99) — generalize later per-locus via gt['ocr_dir']
    ocr_glob = list((ROOT / "sources/our-ocr-diplomatic" / gt["ocr_dir"]).glob(f"*_{gt['page_index']:04d}.json"))
    strip_vnum = lambda t: re.sub(r"^\s*\d{1,3}\s*", "", t).strip()
    print(f"\n=== re-score (corrected GT, ſ={raw.count('ſ')}, chars={len(raw)}) ===")
    if ocr_glob:
        oc = json.loads(ocr_glob[0].read_text())["lines"]
        ocr = " ".join(strip_vnum(l["text"]) for l in oc if l["text"].strip())
        print(f"  existing-OCR ſ={ocr.count('ſ')}")
        print(f"  OCR vs corrected-GT   fold_arc={edit_ratio(fold_archaic(ocr), fold_archaic(raw)):.4f}"
              f"   raw={edit_ratio(ocr, raw):.4f}   ſ delta(ocr-gt)={ocr.count('ſ')-raw.count('ſ'):+d}")
    # s_dismas on-page span (scripture loci only; matter/front-matter pages have no verse reference)
    loc_parts = gt["locus"].split("/")
    if len(loc_parts) < 2:
        return
    book = loc_parts[1]
    reads = json.loads((ROOT / "reconstruction/reads/s_dismas.json").read_text())["reads"]
    a_ref = {r["skeleton_id"]: r["surface"] for r in reads
             if r.get("skeleton_id", "").startswith(f"scripture/{book}/") and r.get("present") and r.get("surface")}
    # derive on-page verse span from verses_on_page
    ch_verses = []
    for vp in gt.get("verses_on_page", []):
        m = re.match(r"(\d+):(\d+)", vp)
        if m:
            ch_verses.append((int(m.group(1)), int(m.group(2))))
    if ch_verses:
        ch = ch_verses[0][0]
        vlo, vhi = min(v for _, v in ch_verses), max(v for _, v in ch_verses)
        keys = [f"scripture/{book}/{ch}/{v}" for v in range(vlo, vhi + 1) if f"scripture/{book}/{ch}/{v}" in a_ref]
        sref = " ".join(a_ref[k] for k in keys)
        print(f"  s_dismas [{book} {ch}:{vlo}-{vhi}] ſ={sref.count('ſ')}")
        print(f"  s_dismas vs corrected-GT  fold_arc={edit_ratio(fold_archaic(raw), fold_archaic(sref)):.4f}"
              f"   raw={edit_ratio(raw, sref):.4f}   ſ delta(gt-ref)={raw.count('ſ')-sref.count('ſ'):+d}")


def main() -> int:
    slug = sys.argv[1]
    gt_path = GT_DIR / f"{slug}.json"
    corr_path = CORR_DIR / f"{slug}.corrections.json"
    gt = json.loads(gt_path.read_text())
    corr = json.loads(corr_path.read_text())
    body = {L["line_index"]: L for L in gt["body"]}
    # only body-line uncertains are keyed here; apparatus/global uncertains (no line_index) pass through
    unc = {u["line_index"]: u for u in gt.get("uncertain", []) if "line_index" in u}
    unc_other = [u for u in gt.get("uncertain", []) if "line_index" not in u]
    applied, excluded, skipped, resolved, deferred = [], [], [], [], []
    # multi-page section? A 'not-on-page' marking on a LATER page pre-dates the 2026-07-23 multi-page raster
    # fix (the reviewer then saw only the first page) → it is ambiguous and must NOT silently exclude valid
    # later-page content (No Silent Degradation). Such deletions are deferred for re-review with all pages shown.
    _pages = gt.get("page_index")
    multi_page = isinstance(_pages, list) and len(_pages) > 1

    for c in corr.get("corrections", []):
        li = c["line_index"]
        L = body.get(li)
        if L is None:
            skipped.append((li, "no-such-line")); continue
        if c.get("original") is not None and L["text"] != c["original"]:
            # idempotent re-run: if the line already holds the corrected text, count it as
            # applied, not a drift-skip (keeps the review-block counts honest across re-runs)
            if L.get("reviewed") and c.get("corrected", "") != "" and L["text"] == c["corrected"]:
                applied.append(li)
            else:
                skipped.append((li, "original-mismatch"))
            continue
        if c.get("deleted") or c.get("corrected", "") == "":
            # Guard: on a MULTI-PAGE section a 'not-on-page' marking on a non-first page is ambiguous — before
            # the multi-page raster fix the reviewer saw only the first page, so later-page lines were mis-marked
            # off-page. Defer (never silently exclude) for re-review with all pages visible.
            L_page = L.get("page")
            if multi_page and L_page is not None and L_page != _pages[0]:
                L["review_status"] = "needs_rereview_multipage"
                L["review_note"] = ((c.get("note") or "").strip() + f" [DEFERRED: 'not-on-page' predates the "
                    f"multi-page raster fix; this line is on page {L_page}, not the first page then shown — "
                    "re-review with all pages visible before excluding]").strip()
                deferred.append(li)
                continue
            L["role"] = "excluded"
            L["excluded_reason"] = c.get("note") or "reviewer removed (empty correction)"
            excluded.append(li)
        else:
            L["_pre_review"] = L["text"]
            L["text"] = c["corrected"]
            L["reviewed"] = True
            applied.append(li)
        if li in unc:
            resolved.append({**unc.pop(li), "resolved_to": c.get("corrected", ""), "resolved_by": "sir"})

    # catchword heuristic: last body line, excluded, <=3 words -> role='catchword'
    # (apparatus/marginalia-only pages have empty body -> skip; nothing to promote)
    if gt["body"]:
        last = gt["body"][-1]
        if last.get("role") == "excluded" and len((last.get("_pre_review") or last["text"]).split()) <= 3:
            last["role"] = "catchword"
            last["catchword_note"] = ("reader-convenience catchword duplicating the first word(s) of the "
                                      "next page; excluded from body concat (Sir, 2026-07-12)")

    for c in corr.get("marginalia_corrections", []):
        i = c["index"]
        if 0 <= i < len(gt.get("marginalia", [])):
            gt["marginalia"][i]["_pre_review"] = gt["marginalia"][i]["text"]
            if c.get("corrected") is not None:
                gt["marginalia"][i]["text"] = c["corrected"]
            if c.get("note"):
                gt["marginalia"][i]["review_note"] = c["note"]

    for c in corr.get("apparatus_corrections", []):
        i = c["index"]
        if 0 <= i < len(gt.get("apparatus", [])):
            ap = gt["apparatus"][i]
            if c.get("corrected") is not None and c["corrected"] != ap.get("text"):
                ap["_pre_review"] = ap["text"]; ap["text"] = c["corrected"]; applied.append(f"ap{i}")
            if c.get("gloss_corrected") is not None and c["gloss_corrected"] != ap.get("gloss"):
                ap["_pre_review_gloss"] = ap.get("gloss"); ap["gloss"] = c["gloss_corrected"]; applied.append(f"ap{i}.gloss")
            if c.get("note"):
                ap["review_note"] = c["note"]

    # structural heading fields (book_title / chapter_heading are strings; argument is {text:...})
    for c in corr.get("field_corrections", []):
        fld = c.get("field")
        if fld not in ("book_title", "chapter_heading", "argument"):
            skipped.append((fld, "unknown-field")); continue
        cur = gt.get(fld)
        cur_text = cur if isinstance(cur, str) else (cur.get("text", "") if isinstance(cur, dict) else "")
        if c.get("original") is not None and cur_text != c["original"]:
            skipped.append((f"field:{fld}", "field-original-mismatch")); continue
        new = c.get("corrected", cur_text)
        if isinstance(cur, dict):
            cur["_pre_review"] = cur.get("text"); cur["text"] = new
        else:
            gt[f"_pre_review_{fld}"] = cur_text; gt[fld] = new
        if c.get("note"):
            gt.setdefault("field_review_notes", {})[fld] = c["note"]
        applied.append(f"field:{fld}")

    cwc = corr.get("catchword_correction")
    if cwc and gt.get("catchword"):
        if cwc.get("corrected") is not None and cwc["corrected"] != gt["catchword"].get("text"):
            gt["catchword"]["_pre_review"] = gt["catchword"]["text"]
            gt["catchword"]["text"] = cwc["corrected"]; applied.append("catchword")
        if cwc.get("note"):
            gt["catchword"]["review_note"] = cwc["note"]

    for a in corr.get("added_lines", []):
        gt["body"].append({"line_index": max(body, default=-1) + 1 + len(applied), "verse": "?",
                           "text": a.get("text", ""), "role": "added_by_reviewer",
                           "note": a.get("note", ""), "after_line_index": a.get("after_line_index")})

    gt["uncertain"] = unc_other + list(unc.values())
    gt["resolved_uncertain"] = gt.get("resolved_uncertain", []) + resolved
    gt["review"] = {"reviewer": corr.get("reviewer", "sir"), "reviewed_at": corr.get("submitted_at"),
                    "n_applied": len(applied), "n_excluded": len(excluded), "n_skipped": len(skipped),
                    "n_deferred": len(deferred), "corrections_source": str(corr_path.relative_to(SPIKE))}
    if corr.get("global_note"):
        gt["review"]["global_note"] = corr["global_note"]

    shutil.copy(gt_path, gt_path.with_suffix(".json.pre-review"))
    gt_path.write_text(json.dumps(gt, ensure_ascii=False, indent=2))
    print(f"applied={applied}\nexcluded={excluded}\nskipped={skipped}\n"
          f"deferred(multi-page not-on-page → needs re-review)={deferred}\n"
          f"resolved_uncertain={[r['span'] for r in resolved]}")
    rescore(gt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
