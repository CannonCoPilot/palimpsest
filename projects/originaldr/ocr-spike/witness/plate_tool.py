#!/usr/bin/env python3
"""plate_tool.py — the Plate Tool (prototype, 2026-09-05).

Sir corrects the director's read of a leaf, and every change is WRITTEN TO DISK at once. This is
the answer to SIR-REVIEW-2026-09-01 Finding 5: the old review.html could only download a file
into ~/Downloads, kept no geometry, had no ACCEPT state, and nothing read its export.

  python3 plate_tool.py                          # B read, port 8765, record plates/gold-layout.json
  python3 plate_tool.py --source cold-read/cold-read.json --img cold-read/img --port 8766

Record: plates/gold-layout.json  (format plate-gold/1; read ONLY through plate_gold.py)
Log:    plates/gold-layout.log.jsonl  (append-only; one line per write; the undo/audit trail)

`agent` is the director's claim, verbatim, copied in when a leaf is first touched. `review` is what
Sir made of it: every region carries origin agent|human and, for agent regions, its index in the
claim, so the two are never laundered together. Full-resolution rasters are served from the S09
JPEG-2000 files named in raster-manifest.json, decoded on demand and cached.
"""
import argparse, io, json, os, sys, threading, webbrowser
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import plate_gold as PG

LOCK = threading.Lock()
CFG = {}


# ---------------------------------------------------------------- record
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load_source(path):
    d = json.load(open(path))
    return d["leaves"], PG.sha256(path)

def open_record(out, source_path, sha):
    rel = os.path.relpath(source_path, HERE)
    if out.exists():
        rec = json.load(open(out))
        if rec.get("format") != "plate-gold/1":
            sys.exit(f"refusing: {out} is not a plate-gold/1 record")
        if rec["source"]["sha256"] != sha:
            sys.exit(f"refusing: {out} was written against a different read "
                     f"({rec['source']['path']} {rec['source']['sha256'][:12]}…). "
                     f"The source is now {rel} {sha[:12]}…. Corrections do not transfer between claims; "
                     f"move the old record aside or point --source at the original read.")
        return rec
    rec = {"format": "plate-gold/1",
           "_doc": "Plate Tool record. `agent` = the director's claim verbatim; `review` = Sir's corrections "
                   "with per-region origin. Read only through plate_gold.py. Written on every change.",
           "source": {"path": rel, "sha256": sha},
           "classes": PG.CLASSES, "created": now(), "leaves": {}}
    write_record(out, rec)
    return rec

def write_record(out, rec):
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    os.replace(tmp, out)

def append_log(logp, entry):
    with open(logp, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def fresh_review(agent):
    return {"verdict": None, "note": "", "side": agent.get("side"), "kind": agent.get("kind"),
            "measure": agent.get("measure"), "skew_deg": 0.0, "skew_source": None, "warped": False,
            "regions": [{"box": list(r["box"]), "class": r["class"], "why": r.get("why", ""),
                         "origin": "agent", "agent_index": i} for i, r in enumerate(agent.get("regions", []))],
            "proposed_classes": []}

def leaf_entry(rec, lid):
    if lid not in rec["leaves"]:
        agent = CFG["source"][lid]
        w, n = lid.rsplit("_", 1)
        rec["leaves"][lid] = {"witness": w, "leaf": int(n), "agent": agent, "review": fresh_review(agent),
                              "touched": now(), "updated": None}
    return rec["leaves"][lid]

def check_review(rv):
    if rv.get("verdict") not in (None,) + PG.VERDICTS:
        raise ValueError(f"bad verdict {rv.get('verdict')!r}")
    sk = rv.get("skew_deg", 0) or 0
    if not isinstance(sk, (int, float)) or abs(sk) > PG.SKEW_MAX:
        raise ValueError(f"skew {sk!r} outside ±{PG.SKEW_MAX}° — that is a capture defect: tick 'warped' and leave the leaf as defect")
    classes = PG.all_classes(CFG["rec"])
    for i, r in enumerate(rv.get("regions", [])):
        if not PG._box_ok(r.get("box")): raise ValueError(f"region {i}: bad box")
        if r.get("class") != PG.ABSTAIN and r.get("class") not in classes:
            raise ValueError(f"region {i}: class {r.get('class')!r} not in the register")
        if r.get("origin") not in ("agent", "human"): raise ValueError(f"region {i}: bad origin")
    if rv.get("verdict") == "accept":
        if any(r["class"] == PG.ABSTAIN for r in rv["regions"]):
            raise ValueError("cannot ACCEPT while a region is still '??' — name it, make it a state, or leave the leaf as corrected")
        if not rv["regions"]:
            raise ValueError("cannot ACCEPT with zero regions — a blank leaf is BL")


# ---------------------------------------------------------------- rasters
def hires_path(lid):
    """Resolve a leaf id to its S09 JPEG-2000 file via raster-manifest.json."""
    m = CFG.get("manifest")
    if not m: return None
    w, n = lid.rsplit("_", 1)
    leaves = m.get("witnesses", {}).get(w, {}).get("leaves", {})
    for key, v in leaves.items():
        stem = key[:-8]  # strip _NNNN.jp2
        cand = f"{stem}{int(n):04d}.jp2"
        if cand in leaves: return Path(leaves[cand]["path"])
        break
    return None

def hires_jpeg(lid):
    cache = CFG["cache"]; cache.mkdir(exist_ok=True)
    out = cache / f"{lid}.jpg"
    if out.exists(): return out.read_bytes()
    p = hires_path(lid)
    if not p or not p.exists(): return None
    from PIL import Image
    im = Image.open(p).convert("RGB")
    b = io.BytesIO(); im.save(b, "JPEG", quality=88, optimize=True)
    out.write_bytes(b.getvalue()); return b.getvalue()

_rot_cache = {}
def rotated(raw, key, deg):
    """JPEG bytes levelled by deg through plate_gold.deskew — the same call every consumer makes."""
    if not deg: return raw
    k = (key, round(deg, 2))
    if k in _rot_cache: return _rot_cache[k]
    from PIL import Image
    im = PG.deskew(Image.open(io.BytesIO(raw)).convert("RGB"), deg)
    b = io.BytesIO(); im.save(b, "JPEG", quality=85); out = b.getvalue()
    if len(_rot_cache) > 6: _rot_cache.pop(next(iter(_rot_cache)))
    _rot_cache[k] = out; return out

def rot_param(path):
    q = parse_qs(urlparse(path).query).get("rot", ["0"])[0]
    try: return max(-PG.SKEW_MAX, min(PG.SKEW_MAX, float(q)))
    except ValueError: return 0.0


# ---------------------------------------------------------------- http
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)): body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        p = unquote(self.path.split("?")[0])
        rec = CFG["rec"]
        if p == "/": return self.send(200, APP, "text/html; charset=utf-8")
        if p == "/api/state":
            src = CFG["source"]
            rows = []
            for lid in src:
                L = rec["leaves"].get(lid); rv = (L or {}).get("review") or {}
                rows.append({"id": lid, "verdict": rv.get("verdict"), "n_agent": len(src[lid].get("regions", [])),
                             "n_review": len(rv.get("regions", [])) if L else None,
                             "open": sum(1 for r in rv.get("regions", []) if r["class"] == PG.ABSTAIN) if L else
                                     sum(1 for r in src[lid].get("regions", []) if r["class"] == PG.ABSTAIN),
                             "changed": bool(L and (any(r["origin"] == "human" or r.get("moved") for r in rv["regions"])
                                                    or len(rv["regions"]) != len(src[lid].get("regions", []))))})
            return self.send(200, {"record": os.path.relpath(CFG["out"], HERE), "source": rec["source"],
                                   "classes": {"text": PG.TEXT, "nontext": PG.NONTEXT, "states": PG.STATES,
                                               "added": rec.get("classes_added", [])}, "skew_max": PG.SKEW_MAX,
                                   "hires": CFG["manifest"] is not None, "leaves": rows})
        if p.startswith("/api/leaf/"):
            lid = p[10:]
            if lid not in CFG["source"]: return self.send(404, {"error": "no such leaf in the source read"})
            with LOCK:
                L = rec["leaves"].get(lid)
                agent = CFG["source"][lid]
                rv = L["review"] if L else fresh_review(agent)
                return self.send(200, {"id": lid, "agent": agent, "review": rv, "touched": bool(L),
                                       "px": CFG["px"].get(lid)})
        if p.startswith("/api/skew/"):
            f = CFG["img"] / (p[10:] + ".jpg")
            if not f.exists(): return self.send(404, {"error": "no image"})
            from PIL import Image
            return self.send(200, {"skew_deg": PG.estimate_skew(Image.open(f))})
        if p.startswith("/img/"):
            f = CFG["img"] / (p[5:] + ".jpg")
            if not f.exists(): return self.send(404, {"error": "no image"})
            return self.send(200, rotated(f.read_bytes(), "img:" + p[5:], rot_param(self.path)), "image/jpeg")
        if p.startswith("/hires/"):
            try: b = hires_jpeg(p[7:])
            except Exception as e: return self.send(500, {"error": f"hires decode failed: {e}"})
            if b is None: return self.send(404, {"error": "no full-resolution raster for this leaf in raster-manifest.json"})
            return self.send(200, rotated(b, "hires:" + p[7:], rot_param(self.path)), "image/jpeg")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        p = unquote(self.path.split("?")[0])
        if p == "/api/class":
            import re
            n = int(self.headers.get("Content-Length", 0))
            try: body = json.loads(self.rfile.read(n))
            except Exception: return self.send(400, {"error": "bad json"})
            code, meaning = (body.get("code") or "").strip().upper(), (body.get("meaning") or "").strip()
            if not re.match(PG.CODE_RE, code): return self.send(422, {"error": "code must be 2-3 capitals, e.g. AC"})
            if not meaning: return self.send(422, {"error": "a meaning is required — one line, what a reader sees"})
            with LOCK:
                rec = CFG["rec"]
                if code in PG.all_classes(rec) or code == PG.ABSTAIN: return self.send(422, {"error": f"{code} already exists"})
                rec.setdefault("classes_added", []).append({"code": code, "meaning": meaning, "when": now()})
                write_record(CFG["out"], rec)
                append_log(CFG["log"], {"t": now(), "class_added": code, "meaning": meaning})
            return self.send(200, {"ok": True, "added": rec["classes_added"]})
        if not p.startswith("/api/leaf/"): return self.send(404, {"error": "not found"})
        lid = p[10:]
        if lid not in CFG["source"]: return self.send(404, {"error": "no such leaf"})
        n = int(self.headers.get("Content-Length", 0))
        try: body = json.loads(self.rfile.read(n))
        except Exception: return self.send(400, {"error": "bad json"})
        rv = body.get("review")
        if not isinstance(rv, dict): return self.send(422, {"error": "body must be {review: {...}}"})
        try: check_review(rv)
        except ValueError as e: return self.send(422, {"error": str(e)})
        with LOCK:
            rec = CFG["rec"]; L = leaf_entry(rec, lid)
            L["review"] = rv; L["updated"] = now()
            write_record(CFG["out"], rec)
            append_log(CFG["log"], {"t": L["updated"], "leaf": lid, "verdict": rv.get("verdict"),
                                    "n": len(rv["regions"]), "review": rv})
            done = sum(1 for x in rec["leaves"].values() if (x.get("review") or {}).get("verdict"))
        self.send(200, {"ok": True, "written": L["updated"], "record": os.path.relpath(CFG["out"], HERE),
                        "verdicts_on_disk": done})


# ---------------------------------------------------------------- app
APP = r'''<!doctype html><html><head><meta charset="utf-8"><title>Plate Tool</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--paper:#E9E6DE;--paper-2:#E1DDD3;--ink:#1A1714;--ink-2:#4A443C;--grey:#8C877C;--rule:#C9C3B6;
--rubric:#A32B22;--slate:#3A5A6B;--olive:#5A6B3A;--amber:#8A6A20;--stage:#2A2622;
--serif:"Newsreader","Iowan Old Style",Palatino,Georgia,serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:15px;display:grid;
grid-template-columns:16rem 1fr 22rem;grid-template-rows:auto 1fr auto;height:100vh;overflow:hidden}
header{grid-column:1/4;display:flex;gap:1rem;align-items:baseline;padding:.5rem 1rem;border-bottom:1px solid var(--rule);background:var(--paper-2)}
header h1{font-size:1.1rem;font-weight:600;margin:0}
header .src{font-family:var(--mono);font-size:.7rem;color:var(--grey)}
header .sp{flex:1}
#status{font-family:var(--mono);font-size:.72rem;color:var(--olive)}
#status.err{color:var(--rubric);font-weight:500}
aside{overflow:auto;border-right:1px solid var(--rule);font-family:var(--mono);font-size:.72rem}
aside .filt{display:flex;flex-wrap:wrap;gap:.25rem;padding:.5rem;border-bottom:1px solid var(--rule);position:sticky;top:0;background:var(--paper)}
aside .filt button{font:inherit;font-size:.66rem;padding:.15rem .4rem;border:1px solid var(--rule);background:transparent;color:var(--ink-2);cursor:pointer}
aside .filt button.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
aside .row{display:grid;grid-template-columns:1fr auto;gap:.4rem;padding:.3rem .6rem;cursor:pointer;border-bottom:1px solid var(--paper-2)}
aside .row:hover{background:var(--paper-2)} aside .row.cur{background:var(--ink);color:var(--paper)}
aside .row .m{color:var(--grey)} aside .row.cur .m{color:var(--rule)}
.pill{display:inline-block;padding:0 .35rem;border-radius:2px;font-size:.62rem;letter-spacing:.04em;text-transform:uppercase}
.pill.accept{background:var(--olive);color:#fff}.pill.corrected{background:var(--slate);color:#fff}.pill.defect{background:var(--rubric);color:#fff}
.pill.open{background:var(--amber);color:#fff}
#stage{overflow:auto;background:var(--stage);position:relative}
#wrap{position:relative;display:inline-block;line-height:0;margin:1rem}
#wrap img{display:block;user-select:none;-webkit-user-drag:none}
#wrap.adding{cursor:crosshair}
.box{position:absolute;border:1.5px solid var(--c);background:transparent;cursor:move}
.box.sel{border-width:2.5px;background:color-mix(in srgb,var(--c) 12%,transparent);z-index:5}
.box .lab{position:absolute;left:-1.5px;top:-1.1rem;font:600 .62rem var(--mono);background:var(--c);color:#fff;padding:0 .25rem;line-height:1rem;white-space:nowrap;pointer-events:none}
.box.sel .lab{font-size:.68rem}
.h{position:absolute;width:10px;height:10px;background:#fff;border:1.5px solid var(--c);display:none}
.box.sel .h{display:block}
.h.nw{left:-6px;top:-6px;cursor:nwse-resize}.h.n{left:calc(50% - 5px);top:-6px;cursor:ns-resize}.h.ne{right:-6px;top:-6px;cursor:nesw-resize}
.h.e{right:-6px;top:calc(50% - 5px);cursor:ew-resize}.h.se{right:-6px;bottom:-6px;cursor:nwse-resize}.h.s{left:calc(50% - 5px);bottom:-6px;cursor:ns-resize}
.h.sw{left:-6px;bottom:-6px;cursor:nesw-resize}.h.w{left:-6px;top:calc(50% - 5px);cursor:ew-resize}
#rubber{position:absolute;border:1.5px dashed #fff;display:none;pointer-events:none}
.pane{overflow:auto;border-left:1px solid var(--rule);padding:.8rem;display:flex;flex-direction:column;gap:.8rem;font-size:.9rem}
.pane h2{font-family:var(--mono);font-size:.64rem;letter-spacing:.12em;text-transform:uppercase;color:var(--grey);margin:0 0 .3rem}
.pane label{display:block;font-family:var(--mono);font-size:.64rem;color:var(--grey);margin:.35rem 0 .1rem}
.pane input[type=text],.pane textarea,.pane select{width:100%;font:inherit;font-size:.82rem;padding:.3rem .4rem;border:1px solid var(--rule);background:#fff;color:var(--ink);border-radius:2px}
.pane textarea{min-height:3.5rem;resize:vertical;font-family:var(--serif)}
.pane .grp{padding:.6rem;background:var(--paper-2);border-radius:2px}
.btns{display:flex;flex-wrap:wrap;gap:.35rem}
button.b{font:500 .74rem var(--mono);padding:.35rem .6rem;border:1px solid var(--rule);background:#fff;color:var(--ink);cursor:pointer;border-radius:2px}
button.b:hover{border-color:var(--ink)} button.b.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
button.b.acc.on{background:var(--olive);border-color:var(--olive)} button.b.cor.on{background:var(--slate);border-color:var(--slate)} button.b.def.on{background:var(--rubric);border-color:var(--rubric)}
button.b:disabled{opacity:.4;cursor:not-allowed}
.why{font-size:.82rem;color:var(--ink-2)}
.agent{font-family:var(--mono);font-size:.66rem;color:var(--grey);line-height:1.5}
.origin{font-family:var(--mono);font-size:.62rem;letter-spacing:.06em;text-transform:uppercase}
.origin.human{color:var(--rubric)} .origin.agent{color:var(--slate)}
footer{grid-column:1/4;display:flex;gap:1.2rem;flex-wrap:wrap;padding:.4rem 1rem;border-top:1px solid var(--rule);background:var(--paper-2);font-family:var(--mono);font-size:.66rem;color:var(--ink-2)}
footer b{color:var(--ink)}
.meta{display:grid;grid-template-columns:1fr 1fr;gap:.4rem}
.meta .full{grid-column:1/3}
.warn{color:var(--rubric);font-family:var(--mono);font-size:.7rem}
.skew{display:grid;grid-template-columns:1fr 4.2rem auto;gap:.4rem;align-items:center}
.skew input[type=range]{width:100%;accent-color:var(--slate)}
.skew input[type=number]{font:inherit;font-size:.78rem;font-family:var(--mono);padding:.25rem .3rem;border:1px solid var(--rule);background:#fff;border-radius:2px;width:100%}
.chk{font-family:var(--mono);font-size:.68rem;color:var(--ink-2);display:flex;gap:.3rem;align-items:center;margin-top:.3rem}
.ksrc{font-family:var(--mono);font-size:.62rem;color:var(--grey)}
</style></head><body>
<header><h1>Plate Tool</h1><span class="src" id="src"></span><span class="sp"></span><span id="status">…</span></header>
<aside>
  <div class="filt">
    <button data-f="all" class="on">all</button><button data-f="unreviewed">unreviewed</button><button data-f="open">has ??</button>
    <button data-f="accept">accepted</button><button data-f="corrected">corrected</button><button data-f="defect">defect</button>
  </div>
  <div id="list"></div>
</aside>
<div id="stage"><div id="wrap"><img id="img" alt=""><div id="rubber"></div></div></div>
<div class="pane">
  <div class="grp">
    <h2>Leaf <span id="lid" style="color:var(--ink)"></span></h2>
    <div class="btns">
      <button class="b" id="prev" title="←">← prev</button><button class="b" id="next" title="→">next →</button>
      <button class="b" id="nextu" title="N">next unreviewed</button>
      <button class="b" id="zo" title="-">−</button><button class="b" id="zi" title="+">+</button><button class="b" id="fit">fit</button>
      <button class="b" id="hires" title="H">full res</button>
    </div>
    <div class="meta">
      <div><label>side</label><select id="side"><option>recto</option><option>verso</option><option>unknown</option></select></div>
      <div><label>measure (x0, x1)</label><input type="text" id="measure" placeholder="0.16, 0.82"></div>
      <div class="full"><label>page kind</label><input type="text" id="kind"></div>
      <div class="full"><label>level the page · skew ° <span class="ksrc" id="ksrc"></span></label>
        <div class="skew"><input type="range" id="skewr" min="-4" max="4" step="0.02" value="0"><input type="number" id="skewn" step="0.02" min="-6" max="6" value="0"><button class="b" id="skewa" title="estimate from the text lines">auto</button></div>
        <label class="chk"><input type="checkbox" id="warped"> warped — cannot be levelled by one angle (gutter curl, cockle)</label>
      </div>
    </div>
  </div>
  <div class="grp">
    <h2>Verdict</h2>
    <div class="btns"><button class="b acc" data-v="accept">accept</button><button class="b cor" data-v="corrected">corrected</button><button class="b def" data-v="defect">defect</button><button class="b" data-v="">clear</button></div>
    <div class="warn" id="vwarn"></div>
    <label>note</label><textarea id="note"></textarea>
  </div>
  <div class="grp" id="regp">
    <h2>Region <span id="rsel" style="color:var(--ink)"></span></h2>
    <div id="rnone" class="why">Click a box. <b>A</b> then drag to add one. <b>Delete</b> removes. <b>Ctrl-Z</b> undoes. Drag any edge or corner to resize.</div>
    <div id="rform" hidden>
      <span class="origin" id="rorig"></span>
      <label>class</label><select id="rclass"></select>
      <label>why</label><textarea id="rwhy"></textarea>
      <div class="agent" id="ragent"></div>
      <div class="btns" style="margin-top:.5rem"><button class="b" id="rdel">delete region</button><button class="b" id="rrevert">revert to claim</button></div>
      <label>propose a class for this region</label>
      <div style="display:flex;gap:.3rem"><input type="text" id="rprop" placeholder="code · meaning"><button class="b" id="rpropb">file</button></div>
      <div class="agent" id="rprops"></div>
    </div>
  </div>
  <div class="grp">
    <h2>New class</h2>
    <div style="display:grid;grid-template-columns:4rem 1fr auto;gap:.3rem"><input type="text" id="ncode" placeholder="AC" maxlength="3" style="font-family:var(--mono);text-transform:uppercase"><input type="text" id="nmean" placeholder="meaning — what a reader sees"><button class="b" id="nadd">add</button></div>
    <div class="agent" id="nlist"></div>
  </div>
</div>
<footer><span><b id="cnt"></b> leaves in the read</span><span><b id="done"></b> verdicts on disk</span><span><b id="acc"></b> accepted</span><span>record <b id="recp"></b></span><span id="hint"></span></footer>
<script>
const $=q=>document.querySelector(q);
const S={list:[],i:-1,leaf:null,rv:null,sel:-1,z:1,hires:false,undo:[],filter:'all',classes:null,dirty:null,adding:false};
const COL=c=>S.classes.text.includes(c)?'#3A5A6B':S.classes.nontext.includes(c)?'#8A6A20':S.classes.states.includes(c)?'#5A6B3A':S.classes.added.some(a=>a.code===c)?'#6B3A5A':'#A32B22';
// the same transform as plate_gold.transform_box: rotate the centre about the canvas centre, keep the size
function tbox(b,w,h,d){ if(!d)return b.slice(); const t=d*Math.PI/180,c=Math.cos(t),s=Math.sin(t);
  const cx=(b[0]+b[2])/2*w-w/2, cy=(b[1]+b[3])/2*h-h/2, nx=cx*c+cy*s+w/2, ny=-cx*s+cy*c+h/2, bw=(b[2]-b[0])*w, bh=(b[3]-b[1])*h;
  const cl=(v,m)=>Math.max(0,Math.min(1,v/m)); return [cl(nx-bw/2,w),cl(ny-bh/2,h),cl(nx+bw/2,w),cl(ny+bh/2,h)].map(v=>+v.toFixed(4)); }
function classSelect(){
  const sel=$('#rclass'); const keep=sel.value; sel.innerHTML='';
  const og=(n,arr)=>{if(!arr.length)return;const g=document.createElement('optgroup');g.label=n;arr.forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;g.appendChild(o)});sel.appendChild(g)};
  og('text',S.classes.text);og('not text',S.classes.nontext);og('states',S.classes.states);og('provisional (this record)',S.classes.added.map(a=>a.code));og('abstain',['??']);
  if(keep)sel.value=keep;
  $('#nlist').innerHTML=S.classes.added.map(a=>`<b>${a.code}</b> ${a.meaning}`).join('<br>');
}
function status(t,err){const s=$('#status');s.textContent=t;s.classList.toggle('err',!!err);}

async function boot(){
  const st=await (await fetch('/api/state')).json();
  S.classes=st.classes; S.list=st.leaves; S.hiresOK=st.hires;
  $('#src').textContent=st.source.path+' · '+st.source.sha256.slice(0,12); $('#recp').textContent=st.record;
  $('#hires').disabled=!st.hires;
  classSelect(); renderList(); counts();
  $('#skewr').oninput=e=>setSkew(+e.target.value,'human',false); $('#skewr').onchange=e=>setSkew(+e.target.value,'human',true);
  $('#skewn').onchange=e=>setSkew(+e.target.value,'human',true);
  $('#skewa').onclick=autoSkew;
  $('#warped').onchange=e=>{S.rv.warped=e.target.checked;save();};
  $('#nadd').onclick=addClass;
  document.querySelectorAll('.filt button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.filt button').forEach(x=>x.classList.remove('on'));b.classList.add('on');S.filter=b.dataset.f;renderList();});
  $('#prev').onclick=()=>go(S.i-1); $('#next').onclick=()=>go(S.i+1); $('#nextu').onclick=nextUnreviewed;
  $('#zi').onclick=()=>zoom(S.z*1.25); $('#zo').onclick=()=>zoom(S.z/1.25); $('#fit').onclick=()=>fit();
  $('#hires').onclick=()=>{S.hires=!S.hires;$('#hires').classList.toggle('on',S.hires);loadImg();};
  document.querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>setVerdict(b.dataset.v||null));
  $('#note').oninput=e=>{S.rv.note=e.target.value;save();};
  $('#side').onchange=e=>{S.rv.side=e.target.value;save();};
  $('#kind').oninput=e=>{S.rv.kind=e.target.value;save();};
  $('#measure').onchange=e=>{const m=e.target.value.split(',').map(s=>parseFloat(s)).filter(x=>!isNaN(x));S.rv.measure=m.length===2?m:null;save();};
  $('#rclass').onchange=e=>{push();S.rv.regions[S.sel].class=e.target.value;save();draw();};
  $('#rwhy').oninput=e=>{S.rv.regions[S.sel].why=e.target.value;save();};
  $('#rdel').onclick=delRegion; $('#rrevert').onclick=revertRegion; $('#rpropb').onclick=propose;
  addEventListener('keydown',k=>{
    const tag=k.target.tagName; if(tag==='TEXTAREA'||tag==='INPUT'||tag==='SELECT'){if(k.key==='Escape')k.target.blur();return;}
    if(k.key==='ArrowRight'){k.preventDefault();go(S.i+1)} if(k.key==='ArrowLeft'){k.preventDefault();go(S.i-1)}
    if(k.key==='n'||k.key==='N')nextUnreviewed();
    if(k.key==='a'||k.key==='A'){S.adding=true;$('#wrap').classList.add('adding');$('#hint').textContent='drag on the leaf to add a region · Esc cancels';}
    if(k.key==='Escape'){S.adding=false;$('#wrap').classList.remove('adding');$('#hint').textContent='';select(-1);}
    if(k.key==='Delete'||k.key==='Backspace'){if(S.sel>=0){k.preventDefault();delRegion();}}
    if((k.metaKey||k.ctrlKey)&&k.key==='z'){k.preventDefault();undo();}
    if(k.key==='+'||k.key==='=')zoom(S.z*1.25); if(k.key==='-')zoom(S.z/1.25); if(k.key==='0')fit();
    if(k.key==='h'||k.key==='H')$('#hires').click();
    if(k.key==='1')setVerdict('accept'); if(k.key==='2')setVerdict('corrected'); if(k.key==='3')setVerdict('defect');
  });
  const first=S.list.findIndex(l=>!l.verdict); go(first<0?0:first);
}
function visible(){return S.list.filter(l=>S.filter==='all'||(S.filter==='unreviewed'&&!l.verdict)||(S.filter==='open'&&l.open>0)||l.verdict===S.filter);}
function renderList(){
  const v=visible();
  $('#list').innerHTML=v.map(l=>`<div class="row${S.list[S.i]&&S.list[S.i].id===l.id?' cur':''}" data-id="${l.id}"><span>${l.id}${l.changed?' <span style="color:var(--rubric)">•</span>':''}</span><span class="m">${l.verdict?`<span class="pill ${l.verdict}">${l.verdict}</span>`:''}${l.open?` <span class="pill open">${l.open} ??</span>`:''} ${l.n_review??l.n_agent}</span></div>`).join('');
  document.querySelectorAll('#list .row').forEach(r=>r.onclick=()=>go(S.list.findIndex(l=>l.id===r.dataset.id)));
  const c=$('#list .row.cur'); if(c)c.scrollIntoView({block:'nearest'});
}
function counts(){$('#cnt').textContent=S.list.length;$('#done').textContent=S.list.filter(l=>l.verdict).length;$('#acc').textContent=S.list.filter(l=>l.verdict==='accept').length;}
function nextUnreviewed(){const n=S.list.length;for(let k=1;k<=n;k++){const j=(S.i+k)%n;if(!S.list[j].verdict){go(j);return;}}status('every leaf has a verdict');}
async function go(i){
  if(!S.list.length)return; i=(i+S.list.length)%S.list.length;
  await flush();
  S.i=i; const d=await (await fetch('/api/leaf/'+S.list[i].id)).json();
  S.leaf=d; S.rv=d.review; S.sel=-1; S.undo=[]; S.adding=false; $('#wrap').classList.remove('adding');
  $('#lid').textContent=d.id; $('#note').value=S.rv.note||''; $('#side').value=S.rv.side||'unknown'; $('#kind').value=S.rv.kind||'';
  $('#measure').value=S.rv.measure?S.rv.measure.join(', '):'';
  $('#warped').checked=!!S.rv.warped; skewUI();
  renderList(); loadImg(); draw(); verdictUI();
  if(!d.touched && !S.rv.skew_source) autoSkew();
}
function skewUI(){const k=S.rv.skew_deg||0;$('#skewr').value=k;$('#skewn').value=k.toFixed(2);$('#ksrc').textContent=S.rv.skew_source?('· '+S.rv.skew_source):'';}
// rotating the canvas moves every box: carry them across by the delta, exactly as the reader would
function setSkew(k,source,commit){
  k=Math.max(-6,Math.min(6,+k||0)); const old=S.rv.skew_deg||0, d=k-old;
  if(!d&&commit){ if(source==='auto'&&!S.rv.skew_source){S.rv.skew_source='auto';} skewUI(); return; }
  const img=$('#img'), px=S.leaf.px||[img.naturalWidth||1100,img.naturalHeight||1500], w=px[0], h=px[1];
  if(commit)push();
  S.rv.regions.forEach(r=>{r.box=tbox(r.box,w,h,d); if(r.origin==='agent'&&d)r.moved=true;});
  S.rv.skew_deg=+k.toFixed(2); S.rv.skew_source=source; skewUI(); draw();
  if(commit){save(); loadImg();}
}
async function autoSkew(){
  $('#skewa').disabled=true; $('#ksrc').textContent='· estimating…';
  try{ const j=await (await fetch('/api/skew/'+S.leaf.id)).json(); if(j.skew_deg===undefined)throw new Error(j.error);
       setSkew(j.skew_deg,'auto',true); }
  catch(e){ status('skew estimate failed: '+e.message,true); }
  $('#skewa').disabled=false;
}
async function addClass(){
  const code=$('#ncode').value.trim().toUpperCase(), meaning=$('#nmean').value.trim();
  const r=await fetch('/api/class',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code,meaning})});
  const j=await r.json(); if(!r.ok){status('class not added: '+j.error,true);return;}
  S.classes.added=j.added; classSelect(); $('#ncode').value='';$('#nmean').value=''; status('class '+code+' added to the record');
  if(S.sel>=0){push();S.rv.regions[S.sel].class=code;save();draw();}
}
function loadImg(){
  const img=$('#img'); const url=(S.hires?'/hires/':'/img/')+S.leaf.id+'?rot='+(S.rv.skew_deg||0);
  img.onload=()=>{fit();}; img.onerror=()=>{if(S.hires){status('no full-resolution raster for this leaf',true);S.hires=false;$('#hires').classList.remove('on');loadImg();}};
  img.src=url;
}
function zoom(z){S.z=Math.max(.1,Math.min(8,z));const img=$('#img');img.style.width=(img.naturalWidth*S.z)+'px';}
function fit(){const img=$('#img'),st=$('#stage');if(!img.naturalWidth)return;S.z=Math.min((st.clientWidth-32)/img.naturalWidth,(st.clientHeight-32)/img.naturalHeight);zoom(S.z);}
function verdictUI(){
  document.querySelectorAll('[data-v]').forEach(b=>b.classList.toggle('on',(b.dataset.v||null)===S.rv.verdict));
  const open=S.rv.regions.filter(r=>r.class==='??').length;
  $('#vwarn').textContent=open?`${open} region${open>1?'s':''} still ?? — accept is blocked until each is named or made a state`:'';
  document.querySelector('[data-v=accept]').disabled=open>0||!S.rv.regions.length;
}
function draw(){
  const w=$('#wrap'); w.querySelectorAll('.box').forEach(b=>b.remove());
  S.rv.regions.forEach((r,i)=>{
    const b=r.box, d=document.createElement('div'); d.className='box'+(i===S.sel?' sel':''); d.dataset.i=i;
    d.style.cssText=`--c:${COL(r.class)};left:${b[0]*100}%;top:${b[1]*100}%;width:${(b[2]-b[0])*100}%;height:${(b[3]-b[1])*100}%`;
    d.innerHTML=`<span class="lab">${r.class}${r.origin==='human'?' +':r.moved?' ~':''}</span>`+['nw','n','ne','e','se','s','sw','w'].map(h=>`<div class="h ${h}" data-h="${h}"></div>`).join('');
    d.onpointerdown=e=>{if(S.adding)return;e.stopPropagation();select(i);startDrag(e,i,e.target.dataset.h||'move');};
    w.appendChild(d);
  });
  regionUI(); verdictUI();
}
function select(i){S.sel=i;document.querySelectorAll('.box').forEach(b=>b.classList.toggle('sel',+b.dataset.i===i));regionUI();}
function regionUI(){
  const f=$('#rform'),n=$('#rnone'); if(S.sel<0||!S.rv.regions[S.sel]){f.hidden=true;n.hidden=false;$('#rsel').textContent='';return;}
  const r=S.rv.regions[S.sel]; f.hidden=false;n.hidden=true; $('#rsel').textContent='#'+S.sel;
  $('#rorig').className='origin '+r.origin; $('#rorig').textContent=r.origin==='human'?'added by hand':('director claim #'+r.agent_index+(r.moved?' · moved':''));
  $('#rclass').value=r.class; $('#rwhy').value=r.why||'';
  const a=r.origin==='agent'?S.leaf.agent.regions[r.agent_index]:null;
  $('#ragent').textContent=a?`claim: ${a.class} [${a.box.map(v=>v.toFixed(3)).join(', ')}] — ${a.why}`:'';
  $('#rrevert').disabled=!a;
  $('#rprops').innerHTML=(S.rv.proposed_classes||[]).filter(p=>p.region===S.sel).map(p=>'filed: '+p.text).join('<br>');
}
// ---- geometry editing
function frac(e){const img=$('#img'),r=img.getBoundingClientRect();return [(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height];}
const cl=v=>Math.max(0,Math.min(1,v));
function startDrag(e,i,mode){
  push(); const r=S.rv.regions[i], b0=r.box.slice(), p0=frac(e); let moved=false;
  const mv=ev=>{const p=frac(ev),dx=p[0]-p0[0],dy=p[1]-p0[1]; let b=b0.slice();
    if(mode==='move'){b=[cl(b0[0]+dx),cl(b0[1]+dy),cl(b0[2]+dx),cl(b0[3]+dy)];}
    else{ if(mode.includes('w'))b[0]=cl(b0[0]+dx); if(mode.includes('e'))b[2]=cl(b0[2]+dx); if(mode.includes('n'))b[1]=cl(b0[1]+dy); if(mode.includes('s'))b[3]=cl(b0[3]+dy); }
    if(b[2]-b[0]<0.004||b[3]-b[1]<0.003)return;
    r.box=b.map(v=>+v.toFixed(4)); moved=true; place(i);};
  const up=()=>{removeEventListener('pointermove',mv);removeEventListener('pointerup',up); if(moved){if(r.origin==='agent')r.moved=true;save();draw();}else S.undo.pop();};
  addEventListener('pointermove',mv); addEventListener('pointerup',up);
}
function place(i){const d=document.querySelector(`.box[data-i="${i}"]`),b=S.rv.regions[i].box;d.style.left=b[0]*100+'%';d.style.top=b[1]*100+'%';d.style.width=(b[2]-b[0])*100+'%';d.style.height=(b[3]-b[1])*100+'%';}
$('#wrap').onpointerdown=e=>{
  if(!S.adding){select(-1);return;}
  const p0=frac(e),rb=$('#rubber'); rb.style.display='block';
  const mv=ev=>{const p=frac(ev);const x0=Math.min(p0[0],p[0]),y0=Math.min(p0[1],p[1]),x1=Math.max(p0[0],p[0]),y1=Math.max(p0[1],p[1]);rb.style.cssText=`display:block;left:${x0*100}%;top:${y0*100}%;width:${(x1-x0)*100}%;height:${(y1-y0)*100}%`;rb.b=[x0,y0,x1,y1];};
  const up=()=>{removeEventListener('pointermove',mv);removeEventListener('pointerup',up);rb.style.display='none';S.adding=false;$('#wrap').classList.remove('adding');$('#hint').textContent='';
    const b=rb.b; if(!b||b[2]-b[0]<0.004||b[3]-b[1]<0.003)return; push();
    S.rv.regions.push({box:b.map(v=>+cl(v).toFixed(4)),class:'??',why:'',origin:'human'}); S.sel=S.rv.regions.length-1; save(); draw(); $('#rclass').focus();};
  addEventListener('pointermove',mv); addEventListener('pointerup',up);
};
function delRegion(){if(S.sel<0)return;push();S.rv.regions.splice(S.sel,1);S.sel=-1;save();draw();}
function revertRegion(){const r=S.rv.regions[S.sel];if(!r||r.origin!=='agent')return;push();const a=S.leaf.agent.regions[r.agent_index];r.box=a.box.slice();r.class=a.class;r.why=a.why;delete r.moved;save();draw();}
function propose(){const t=$('#rprop').value.trim();if(!t)return;S.rv.proposed_classes=S.rv.proposed_classes||[];S.rv.proposed_classes.push({region:S.sel,text:t,when:new Date().toISOString()});$('#rprop').value='';save();regionUI();}
function setVerdict(v){if(v==='accept'&&document.querySelector('[data-v=accept]').disabled){status('accept blocked: resolve every ?? first',true);return;}S.rv.verdict=v;save();verdictUI();}
// ---- undo
function push(){S.undo.push(JSON.stringify(S.rv));if(S.undo.length>100)S.undo.shift();}
function undo(){if(!S.undo.length)return;const k0=S.rv.skew_deg||0;S.rv=JSON.parse(S.undo.pop());S.sel=-1;$('#note').value=S.rv.note||'';$('#warped').checked=!!S.rv.warped;skewUI();save();draw();if((S.rv.skew_deg||0)!==k0)loadImg();}
// ---- persistence: every change is POSTed; the server writes the record before answering
let timer=null;
function save(){clearTimeout(timer);S.dirty=S.leaf.id;status('unsaved…');timer=setTimeout(flush,250);}
async function flush(){
  if(!S.dirty)return; clearTimeout(timer); const id=S.dirty, rv=S.rv; S.dirty=null;
  try{
    const r=await fetch('/api/leaf/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({review:rv})});
    const j=await r.json();
    if(!r.ok){status('NOT SAVED: '+j.error,true);return;}
    status('written '+j.written.slice(11,19)+'Z → '+j.record);
    const row=S.list.find(l=>l.id===id); if(row){row.verdict=rv.verdict;row.n_review=rv.regions.length;row.open=rv.regions.filter(x=>x.class==='??').length;row.changed=rv.regions.some(x=>x.origin==='human'||x.moved)||rv.regions.length!==row.n_agent;}
    renderList(); counts();
  }catch(e){status('NOT SAVED: server unreachable',true);S.dirty=id;}
}
addEventListener('beforeunload',e=>{if(S.dirty){flush();e.preventDefault();e.returnValue='';}});
boot();
</script></body></html>'''


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Plate Tool — correct the director's read; every change written to disk")
    ap.add_argument("--source", default=str(HERE / "cold-read" / "cold-read-B.json"), help="the director's read (cold-read JSON)")
    ap.add_argument("--img", default=str(HERE / "cold-read" / "img-B"), help="review images <id>.jpg")
    ap.add_argument("--out", default=str(HERE / "plates" / "gold-layout.json"), help="the record (plate-gold/1)")
    ap.add_argument("--manifest", default=str(HERE / "raster-manifest.json"), help="raster-manifest.json for full-res JPEG-2000")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    src, sha = load_source(a.source)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    CFG.update(source=src, img=Path(a.img), out=out, log=out.with_suffix(".log.jsonl"),
               cache=out.parent / "hires-cache", manifest=None, px={})
    if Path(a.manifest).exists():
        CFG["manifest"] = json.load(open(a.manifest))
    sample = Path(a.source).parent / "sample-B.json"
    if sample.exists():
        CFG["px"] = {l["id"]: l.get("px") for l in json.load(open(sample)).get("leaves", [])}
    CFG["rec"] = open_record(out, a.source, sha)

    missing = [lid for lid in src if not (CFG["img"] / f"{lid}.jpg").exists()]
    if missing:
        print(f"warning: {len(missing)} leaves have no review image under {CFG['img']}: {missing[:5]}…")
    n_done = sum(1 for x in CFG["rec"]["leaves"].values() if (x.get("review") or {}).get("verdict"))
    print(f"Plate Tool · {len(src)} leaves from {os.path.relpath(a.source, HERE)} · {n_done} verdicts on disk\n"
          f"record {out}\nhttp://localhost:{a.port}/   (Ctrl-C to stop)")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://localhost:{a.port}/")).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\nstopped; record is on disk")


if __name__ == "__main__":
    main()
