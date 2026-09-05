"""Add full-leaf lightbox with all cold-read boxes drawn to build_register.py."""
import json, base64, io, pathlib
from PIL import Image
SP = pathlib.Path(__file__).parent
CR = pathlib.Path("/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr/ocr-spike/witness/cold-read")
PL = CR.parent / "plates" / "img"

# 1. full-leaf images + regions for all 35 leaves
regions = {}
for f in ("cold-read.json", "cold-read-20.json", "cold-read-10.json"):
    for lid, l in json.load(open(CR / f))["leaves"].items():
        regions[lid] = [{"b": r["box"], "c": r["class"], "w": r["why"][:90]} for r in l["regions"]]
leaves = {}
for lid in regions:
    p = CR / "img" / f"{lid}.jpg"
    if not p.exists(): p = PL / f"{lid}.jpg"
    im = Image.open(p).convert("RGB"); w, h = im.size
    if w > 900: im = im.resize((900, round(h * 900 / w)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=62, optimize=True)
    leaves[lid] = base64.b64encode(b.getvalue()).decode()
tot = sum(len(v) for v in leaves.values())
print(f"{len(leaves)} leaves, {tot/1e6:.2f} MB base64")
json.dump({"leaves": leaves, "regions": regions}, open(SP / "leaves-b64.json", "w"))

# 2. patch the builder
src = (SP / "build_register.py").read_text()
if "LEAVES_JSON" not in src:
    src = src.replace('EX = json.load(open(SP / "exemplars-b64.json"))',
        'EX = json.load(open(SP / "exemplars-b64.json"))\nLV = json.load(open(SP / "leaves-b64.json"))\nLEAVES_JSON = json.dumps(LV["regions"])')
    # crops and thumbs become buttons that open the leaf
    src = src.replace('<img class="crop" src="data:image/jpeg;base64,{r["crop"]}" alt="{esc(cls)} exemplar on {esc(r["leaf"])}">',
        '<img class="crop" tabindex="0" role="button" data-leaf="{esc(r["leaf"])}" data-box="{",".join(str(v) for v in r["box"])}" src="data:image/jpeg;base64,{r["crop"]}" alt="{esc(cls)} exemplar on {esc(r["leaf"])} — open full leaf">')
    src = src.replace('<div class="loc"><img src="data:image/jpeg;base64,{r["thumb"]}" alt="locator for {esc(r["leaf"])}">',
        '<div class="loc"><img tabindex="0" role="button" data-leaf="{esc(r["leaf"])}" data-box="{",".join(str(v) for v in r["box"])}" src="data:image/jpeg;base64,{r["thumb"]}" alt="locator for {esc(r["leaf"])} — open full leaf">')
    # CSS
    src = src.replace('@media (max-width:820px){{.top,.body{{grid-template-columns:1fr}}}}',
'''.ex img[role=button]{{cursor:zoom-in}} .ex img[role=button]:focus{{outline:2px solid var(--slate);outline-offset:2px}}
.hint{{font-family:var(--mono);font-size:.68rem;color:var(--grey);margin:.4rem 0 0}}
#lb{{position:fixed;inset:0;background:rgba(10,8,6,.94);z-index:50;display:grid;grid-template-rows:auto 1fr;color:#E6E1D6}}
#lb .bar{{display:flex;gap:1rem;align-items:center;padding:.6rem 1rem;font-family:var(--mono);font-size:.76rem;border-bottom:1px solid #37322C;flex-wrap:wrap}}
#lb .bar b{{color:#fff}} #lb .bar .sp{{flex:1}}
#lb button{{background:transparent;color:#E6E1D6;border:1px solid #8A8377}}
#lb .stage{{overflow:auto;padding:1rem;display:flex;justify-content:center;align-items:flex-start}}
#lb .wrap{{position:relative;display:inline-block;line-height:0}}
#lb .wrap img{{display:block;max-width:none}}
#lb svg{{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}}
#lb rect{{fill:none;stroke:#7FA8BC;stroke-width:1.5;vector-effect:non-scaling-stroke}}
#lb rect.hi{{stroke:#D9695C;stroke-width:3;fill:rgba(217,105,92,.12)}}
#lb text{{font:11px "IBM Plex Mono",Menlo,monospace;fill:#fff;paint-order:stroke;stroke:#141210;stroke-width:3px}}
#lb .keys{{font-size:.68rem;color:#8A8377}}
@media (max-width:820px){{.top,.body{{grid-template-columns:1fr}}}}''')
    # lightbox markup + script, inserted before the export section's closing </div> of .sheet
    src = src.replace("</div>\n\n<script>\n(function(){{\n  var KEY=",
'''</div>

<div id="lb" hidden role="dialog" aria-modal="true" aria-label="Leaf at full size with regions">
  <div class="bar"><b id="lb-leaf"></b><span id="lb-n"></span><span class="sp"></span>
    <label><input type="checkbox" id="lb-labels" checked> labels</label>
    <label><input type="checkbox" id="lb-all" checked> all regions</label>
    <button id="lb-zoom">fit ↔ 1:1</button><button id="lb-close">Close &nbsp;Esc</button>
    <span class="keys">← → step exemplars on this leaf · click backdrop to close</span></div>
  <div class="stage"><div class="wrap"><img id="lb-img" alt=""><svg id="lb-svg" viewBox="0 0 1000 1000" preserveAspectRatio="none"></svg></div></div>
</div>
<script id="leaves-data" type="application/json">''' + '{LEAVES_JSON}' + '''</script>

<script>
(function(){{
  var R=JSON.parse(document.getElementById('leaves-data').textContent);
  var LEAF_IMG={{}};
''' + "".join(f"  LEAF_IMG[{json.dumps(k)}]=\"data:image/jpeg;base64,{v}\";\n" for k, v in leaves.items()) + '''
  var lb=document.getElementById('lb'),img=document.getElementById('lb-img'),svg=document.getElementById('lb-svg'),
      title=document.getElementById('lb-leaf'),nn=document.getElementById('lb-n'),fit=true,cur=null,last=null;
  function draw(leaf,hiBox){{
    var regs=R[leaf]||[],all=document.getElementById('lb-all').checked,labels=document.getElementById('lb-labels').checked;
    var s='';
    regs.forEach(function(r){{
      var b=r.b,hi=hiBox&&b.join(',')===hiBox;
      if(!all&&!hi)return;
      s+='<rect class="'+(hi?'hi':'')+'" x="'+(b[0]*1000)+'" y="'+(b[1]*1000)+'" width="'+((b[2]-b[0])*1000)+'" height="'+((b[3]-b[1])*1000)+'"><title>'+r.c+' — '+r.w.replace(/[<&]/g,'')+'</title></rect>';
      if(labels)s+='<text x="'+(b[0]*1000+3)+'" y="'+(b[1]*1000+12)+'">'+r.c+'</text>';
    }});
    svg.innerHTML=s;
    nn.textContent=regs.length+' regions'+(hiBox?' · exemplar in red':'');
  }}
  function size(){{ var w=img.naturalWidth,h=img.naturalHeight; if(!w)return;
    if(fit){{var st=lb.querySelector('.stage'),k=Math.min((st.clientWidth-32)/w,(st.clientHeight-32)/h,1);img.style.width=(w*k)+'px';img.style.height=(h*k)+'px';}}
    else{{img.style.width=w+'px';img.style.height=h+'px';}} }}
  function open(leaf,box){{
    cur={{leaf:leaf,box:box}}; title.textContent=leaf; img.src=LEAF_IMG[leaf]||''; img.alt=leaf;
    img.onload=function(){{size();}}; draw(leaf,box);
    lb.hidden=false; document.body.style.overflow='hidden'; document.getElementById('lb-close').focus();
  }}
  function close(){{ lb.hidden=true; document.body.style.overflow=''; if(last){{last.focus();last=null;}} }}
  document.querySelectorAll('.ex img[role=button]').forEach(function(el){{
    function go(){{ last=el; open(el.dataset.leaf,el.dataset.box); }}
    el.addEventListener('click',go); el.addEventListener('keydown',function(e){{ if(e.key==='Enter'||e.key===' '){{e.preventDefault();go();}} }});
  }});
  document.getElementById('lb-close').addEventListener('click',close);
  document.getElementById('lb-zoom').addEventListener('click',function(){{fit=!fit;size();}});
  document.getElementById('lb-all').addEventListener('change',function(){{ if(cur)draw(cur.leaf,cur.box); }});
  document.getElementById('lb-labels').addEventListener('change',function(){{ if(cur)draw(cur.leaf,cur.box); }});
  lb.addEventListener('click',function(e){{ if(e.target===lb||e.target.classList.contains('stage'))close(); }});
  window.addEventListener('resize',size);
  document.addEventListener('keydown',function(e){{
    if(lb.hidden)return;
    if(e.key==='Escape')close();
    if(e.key==='ArrowRight'||e.key==='ArrowLeft'){{
      var els=Array.prototype.slice.call(document.querySelectorAll('.ex img.crop[role=button][data-leaf="'+cur.leaf+'"]'));
      if(els.length<2)return; var i=els.findIndex(function(x){{return x.dataset.box===cur.box}});
      var n=els[(i+(e.key==='ArrowRight'?1:els.length-1))%els.length]; open(cur.leaf,n.dataset.box);
    }}
  }});
}})();
</script>

<script>
(function(){{
  var KEY=''')
    src = src.replace('<p class="lede" style="font-size:1rem">No box is drawn until move 4.',
        '<p class="hint">Click any plate or locator to open the whole leaf at full size with every region I drew on it; the exemplar is red, the rest slate. ← → steps between exemplars on the same leaf.</p>\n<p class="lede" style="font-size:1rem">No box is drawn until move 4.')
    (SP / "build_register.py").write_text(src)
    print("builder patched")
