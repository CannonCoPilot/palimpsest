#!/usr/bin/env python3
"""diagnose the .output transcript structure so the harvester can target it."""
import json, os

TASKS = "/private/tmp/claude-501/-Users-nathanielcannon-Claude-Project-Aion/072e6880-0393-407a-8211-b797878f7d5a/tasks"
AGENTS = {"proverbs-ch16": "add83ba314be7e952",
          "colossians-ch3": "a28e8f8988c33ed94",
          "lectionary-table": "a23f1414fa9d62ac8"}
GTKEYS = {"body", "locus", "verses_on_page"}


def texts_from(path):
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


def walk_gt(obj, path="$"):
    """yield (path, dict) for any dict at any depth carrying GT keys."""
    if isinstance(obj, dict):
        if GTKEYS & set(obj):
            yield (path, obj)
        for k, v in obj.items():
            yield from walk_gt(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_gt(v, f"{path}[{i}]")


def json_blobs(text):
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


for slug, aid in AGENTS.items():
    path = f"{TASKS}/{aid}.output"
    print(f"\n===== {slug}  ({aid}) =====")
    if not os.path.isfile(path):
        print("  MISSING")
        continue
    # raw substring signal
    raw = open(path, encoding="utf-8", errors="ignore").read()
    nlines = raw.count("\n") + 1
    print(f"  size={len(raw)}  lines={nlines}  "
          f'substr: locus={raw.count(chr(34)+"locus"+chr(34))} '
          f'body={raw.count(chr(34)+"body"+chr(34))} '
          f'verses_on_page={raw.count(chr(34)+"verses_on_page"+chr(34))} '
          f'mode_tag={raw.count(chr(34)+"mode_tag"+chr(34))}')
    # first + last non-empty line: structure
    lines = [l for l in raw.splitlines() if l.strip()]
    for label, ln in (("FIRST", lines[0]), ("LAST", lines[-1])):
        try:
            rec = json.loads(ln)
            keys = list(rec.keys()) if isinstance(rec, dict) else f"<{type(rec).__name__}>"
            print(f"  {label} line: type={rec.get('type') if isinstance(rec,dict) else '?'} keys={keys} len={len(ln)}")
        except Exception as e:
            print(f"  {label} line: NOT JSON ({e}); head={ln[:120]!r}")
    # text blobs
    blobs = list(texts_from(path))
    print(f"  text_blobs={len(blobs)}  total_text_len={sum(len(b) for b in blobs)}")
    # deep GT search across blobs
    hits = []
    for bi, t in enumerate(blobs):
        for obj in json_blobs(t):
            for p, gt in walk_gt(obj):
                hits.append((bi, p, len(gt.get("body", []) or []), gt.get("locus"), gt.get("mode_tag")))
    print(f"  deep-GT hits across blobs: {len(hits)}")
    for h in hits[-3:]:
        print(f"     blob#{h[0]} path={h[1]} #body={h[2]} locus={h[3]} mode_tag={h[4]}")
    # if no blobs, maybe GT is directly in a non-text record — deep search whole records
    if not hits:
        allrec_hits = []
        for ln in lines:
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            for p, gt in walk_gt(rec):
                allrec_hits.append((p, len(gt.get("body", []) or []), gt.get("locus")))
        print(f"  deep-GT hits in RAW records: {len(allrec_hits)}")
        for h in allrec_hits[-3:]:
            print(f"     path={h[0]} #body={h[1]} locus={h[2]}")
