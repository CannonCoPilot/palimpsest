#!/usr/bin/env python3
"""agg_scan.py — combine the 8 batch-scan subagent outputs into sample-scan-results.json + summary.
Reads each agent's transcript, extracts the FINAL JSON array (the classification), flattens. Prints
only a summary so the raw transcripts never hit the caller's context."""
import json, re, os
from collections import Counter

TASKS = "/private/tmp/claude-501/-Users-nathanielcannon-Claude-Project-Aion/072e6880-0393-407a-8211-b797878f7d5a/tasks"
AGENTS = {0:"a3bd782a3043c5d13",1:"acffc18e11beeca39",2:"a36e3c5ebb31d1a8d",3:"a43f2eac7dc383bcf",
          4:"a8fbec281e1481d81",5:"ae67eb1b3f8abdc2b",6:"a803df3f11268bbbe",7:"a44e4dd229d0235ff"}

def texts_from(path):
    """yield every assistant text blob in a subagent JSONL transcript."""
    if not os.path.isfile(path): return
    for line in open(path, encoding="utf-8", errors="ignore"):
        line=line.strip()
        if not line: continue
        try: rec=json.loads(line)
        except json.JSONDecodeError: continue
        # dig for any {"type":"text","text":...} anywhere in the record
        stack=[rec]
        while stack:
            o=stack.pop()
            if isinstance(o,dict):
                if o.get("type")=="text" and isinstance(o.get("text"),str): yield o["text"]
                stack.extend(o.values())
            elif isinstance(o,list): stack.extend(o)

def last_array(path):
    """the LAST text blob that parses as a JSON array of {file:...} objects."""
    found=None
    for t in texts_from(path):
        m=re.search(r'\[\s*\{.*\}\s*\]', t, re.S)
        if not m: continue
        try:
            arr=json.loads(m.group(0))
        except json.JSONDecodeError: continue
        if isinstance(arr,list) and arr and isinstance(arr[0],dict) and "file" in arr[0]:
            found=arr
    return found

results=[]; missing=[]
for b,aid in AGENTS.items():
    arr=last_array(f"{TASKS}/{aid}.output")
    if arr: results.extend({**r,"batch":b} for r in arr)
    else: missing.append(b)

json.dump({"n":len(results),"missing_batches":missing,"results":results},
          open("diag-reocr/sample/sample-scan-results.json","w"), indent=1)

print(f"aggregated {len(results)} classifications from {8-len(missing)}/8 batches",
      f"(missing: {missing})" if missing else "(all present)")
pm=Counter(r.get("primary_mode") for r in results)
sm=Counter(r.get("secondary_mode") for r in results if r.get("secondary_mode"))
sq=Counter(r.get("scan_quality") for r in results)
anom=[r for r in results if r.get("anomaly")]
print("\nPRIMARY mode:", dict(pm.most_common()))
print("SECONDARY mode:", dict(sm.most_common()))
print("scan_quality:", dict(sq.most_common()))
print(f"\nanomaly flags: {len(anom)}/{len(results)}")
# cluster anomaly descriptions by keyword to surface NEW mode families
KW={"drop-cap":"drop-cap/initial","argument":"chapter-argument","genealog":"name-list","census":"name-list",
    "name-list":"name-list","tabular":"table/index","table":"table/index","lectionary":"table/index",
    "index":"table/index","greek":"mixed-script","hebrew":"mixed-script","poetry":"running-poetry",
    "aphorism":"running-poetry","per-line":"running-poetry","per-verse":"running-poetry","display":"display-title",
    "title":"display-title","masthead":"display-title","colophon":"display-title","blank":"blank-leaf",
    "engraving":"plate","plate":"plate","mismatch":"misregistration","misregist":"misregistration",
    "not ":"misregistration","latin":"non-english"}
fam=Counter()
for a in anom:
    d=(a.get("anomaly_desc") or "").lower()+" "+(a.get("notes") or "").lower()
    hit=set()
    for k,v in KW.items():
        if k in d: hit.add(v)
    for v in (hit or {"other"}): fam[v]+=1
print("\nanomaly families (by keyword):")
for f,c in fam.most_common(): print(f"   {f}: {c}")
