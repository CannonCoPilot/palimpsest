#!/usr/bin/env python3
"""harvest_newmode.py — pull the FINAL GT object from each new-mode transcription
subagent's .output transcript, mirroring agg_scan.py's streaming dig so the raw
1.5MB JSONL never hits the caller's context. Writes drafts + a compact summary.

Unlike agg_scan.last_array (which wants an array of {file:...}), each transcription
agent returns a SINGLE GT object shaped like ground-truth/scripture-2esdras-07.json.
"""
import json, os

TASKS = "/private/tmp/claude-501/-Users-nathanielcannon-Claude-Project-Aion/072e6880-0393-407a-8211-b797878f7d5a/tasks"
HERE = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.join(HERE, "ground-truth", ".newmode-drafts")
AGENTS = {  # slug (raster stem) -> agent id
    "proverbs-ch16":    "add83ba314be7e952",
    "colossians-ch3":   "a28e8f8988c33ed94",
    "lectionary-table": "a23f1414fa9d62ac8",
}
GTKEYS = {"body", "locus", "verses_on_page"}


def texts_from(path):
    """yield every assistant text blob in a subagent JSONL transcript (agg_scan pattern)."""
    if not os.path.isfile(path):
        return
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        stack = [rec]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                if o.get("type") == "text" and isinstance(o.get("text"), str):
                    yield o["text"]
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)


def json_blobs(text):
    """yield every balanced top-level JSON value in text via raw_decode scan
    (handles ```json fences, prose wrappers, trailing text)."""
    dec = json.JSONDecoder()
    i, n = 0, len(text)
    while i < n:
        cands = [p for p in (text.find("{", i), text.find("[", i)) if p >= 0]
        if not cands:
            break
        nb = min(cands)
        try:
            obj, end = dec.raw_decode(text, nb)
            yield obj
            i = end
        except json.JSONDecodeError:
            i = nb + 1


def walk_gt(obj):
    """yield every dict at any depth carrying GT keys (handles wrapped results)."""
    if isinstance(obj, dict):
        if GTKEYS & set(obj):
            yield obj
        for v in obj.values():
            yield from walk_gt(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_gt(v)


def last_gt(path):
    """the LAST GT-shaped object found anywhere in the transcript's text blobs."""
    found = None
    for t in texts_from(path):
        for obj in json_blobs(t):
            for gt in walk_gt(obj):
                found = gt
    return found


os.makedirs(DRAFTS, exist_ok=True)
print(f"{'slug':<18} {'found':<6} {'#body':>6} {'#marg':>6} {'#app':>5} {'#unc':>5} {'aligned':<8} mode_tag")
print("-" * 90)
for slug, aid in AGENTS.items():
    path = f"{TASKS}/{aid}.output"
    gt = last_gt(path)
    if not gt:
        print(f"{slug:<18} NONE   (no GT-shaped object found in {aid}.output)")
        continue
    draft = os.path.join(DRAFTS, f"{slug}.json")
    with open(draft, "w", encoding="utf-8") as fh:
        json.dump(gt, fh, ensure_ascii=False, indent=2)
    nb = len(gt.get("body", []) or [])
    nm = len(gt.get("marginalia", []) or [])
    na = len(gt.get("apparatus", []) or [])
    nu = len(gt.get("uncertain", []) or [])
    aligned = "YES" if gt.get("verses_aligned") else "no"
    print(f"{slug:<18} {'ok':<6} {nb:>6} {nm:>6} {na:>5} {nu:>5} {aligned:<8} {gt.get('mode_tag','')}")

# detail block per draft (metadata only, no body dump)
print("\n===== DETAIL (metadata only) =====")
for slug in AGENTS:
    draft = os.path.join(DRAFTS, f"{slug}.json")
    if not os.path.isfile(draft):
        continue
    gt = json.load(open(draft, encoding="utf-8"))
    print(f"\n--- {slug} ---")
    for k in ("locus", "page_index", "ocr_dir", "scan", "raster", "raster_dpi",
              "page_label_printed", "running_header", "mode_tag",
              "glyph_regime_resolved", "confidence", "method", "observer"):
        if k in gt:
            v = gt[k]
            v = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
            print(f"  {k}: {v}")
    vp = gt.get("verses_on_page")
    if vp:
        print(f"  verses_on_page: {vp[0]}..{vp[-1]} ({len(vp)})")
