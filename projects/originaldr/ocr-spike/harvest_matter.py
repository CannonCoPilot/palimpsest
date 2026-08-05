#!/usr/bin/env python3
"""harvest_matter.py — harvest a matter transcription agent's final GT from its .output, clean it,
write to ground-truth/<matter-vol-slug>.json, and print a structural QC (no raster needed).

Usage: ocr-venv/bin/python ocr-spike/harvest_matter.py <agent_id> [<agent_id> ...]
"""
import sys, os, json, re, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_newmode import last_gt

TASKS = "/private/tmp/claude-501/-Users-nathanielcannon-Claude-Project-Aion/072e6880-0393-407a-8211-b797878f7d5a/tasks"
GT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ground-truth")
SCORE_KINDS = {"paragraph", "table_row", "list_item", "heading", "subtitle", "title_block", "colophon_line"}


def unescape(o):
    if isinstance(o, str):
        return html.unescape(o)
    if isinstance(o, dict):
        return {k: unescape(v) for k, v in o.items()}
    if isinstance(o, list):
        return [unescape(v) for v in o]
    return o


def toks(s):
    return re.findall(r"\S+", s or "")


for aid in sys.argv[1:]:
    p = f"{TASKS}/{aid}.output"
    gt = last_gt(p) if os.path.isfile(p) else None
    if not gt:
        print(f"{aid}: NO GT object found (agent may have died mid-transcription)")
        continue
    gt = unescape(gt)
    loc = gt.get("locus", "")
    m = re.match(r"matter/([^/]+)/(.+)$", loc)
    if m:
        fn = f"matter-{m.group(1).replace('-','')}-{m.group(2).replace('/','-')}".replace("matter-ot1back", "matter-ot1")
        # normalize vol token: ot1/ot2/nt (strip any -back/-front the agent put in the vol slot)
        vol = m.group(1).split("-")[0]
        fn = f"matter-{vol}-{m.group(2).replace('/','-')}"
    else:
        fn = re.sub(r"[^a-z0-9-]", "-", loc.lower()) or aid
    path = f"{GT}/{fn}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gt, f, ensure_ascii=False, indent=1)
    body = gt.get("body", []) or []
    ivs = gt.get("intervals", []) or []
    nsc = sum(1 for iv in ivs if iv.get("kind") in SCORE_KINDS)
    npar = sum(1 for iv in ivs if iv.get("kind") == "paragraph")
    # token conservation: prose/latin body vs paragraph intervals (should be ~equal)
    pbody = " ".join(L.get("text", "") for L in body if (L.get("role") in ("prose", "latin")))
    pint = " ".join(iv.get("text", "") for iv in ivs if iv.get("kind") == "paragraph")
    tb, ti = len(toks(pbody)), len(toks(pint))
    cons = "OK" if (tb == 0 or abs(tb - ti) / max(tb, 1) < 0.08) else f"DRIFT {tb}vs{ti}"
    valid = "VALIDATION" in (gt.get("method") or "") or "Localization" in (gt.get("method") or "")
    nunc = len(gt.get("uncertain", []) or [])
    print(f"✓ {fn}.json  body={len(body)} intervals={len(ivs)}(scoreable={nsc},para={npar}) "
          f"pages={gt.get('page_index')} prose-conserv={cons} uncertain={nunc} self-validated={valid}")
