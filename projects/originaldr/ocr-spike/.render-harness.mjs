// Headless DOM-stub harness for reocr-report.html — exercises the full render
// pipeline + every interactive entrypoint against the REAL embedded DATA.
// Run: node .render-harness.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));
// target the built artifact; default to the current pilot report, override with argv[1]
const target = process.argv[2] || 'reocr-report-pilot.html';
const html = fs.readFileSync(path.isAbsolute(target) ? target : path.join(DIR, target), 'utf8');
const m = html.match(/<script\b[^>]*>([\s\S]*?)<\/script>/);
if (!m) { console.error('no <script> found'); process.exit(1); }
let js = m[1];

// strip the trailing auto-run so WE control init() inside a try/catch
js = js.replace(/\n\s*init\(\);\s*$/, '\n');

// ---- minimal DOM stub ----
function makeNode(tag = 'div') {
  const node = {
    tagName: (tag || 'div').toUpperCase(), nodeName: (tag || 'div').toUpperCase(),
    children: [], childNodes: [], attributes: {}, style: {}, dataset: {},
    _html: '', _text: '', className: '', value: '', onclick: null,
    classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
    setAttribute(k, v) { this.attributes[k] = v; },
    getAttribute(k) { return this.attributes[k]; },
    removeAttribute(k) { delete this.attributes[k]; },
    appendChild(c) { this.children.push(c); this.childNodes.push(c); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); return c; },
    append(...cs) { cs.forEach(c => this.appendChild(c)); },
    remove() {}, addEventListener() {}, removeEventListener() {},
    querySelector() { return makeNode(); }, querySelectorAll() { return []; },
    getContext() { return null; },
    get firstChild() { return this.children[0] || null; },
    get lastChild() { return this.children[this.children.length - 1] || null; },
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = String(v); this.children = []; this.childNodes = []; },
    get textContent() { return this._text; },
    set textContent(v) { this._text = v == null ? '' : String(v); },
    get innerText() { return this._text; }, set innerText(v) { this._text = String(v); },
  };
  return node;
}

const byId = new Map();
const documentEl = makeNode('html');
globalThis.document = {
  documentElement: documentEl,
  body: makeNode('body'),
  head: makeNode('head'),
  getElementById(id) { if (!byId.has(id)) byId.set(id, makeNode()); return byId.get(id); },
  createElement(t) { return makeNode(t); },
  createElementNS(_ns, t) { return makeNode(t); },
  createDocumentFragment() { return makeNode('#fragment'); },
  createTextNode(t) { const n = makeNode('#text'); n._text = String(t); return n; },
  querySelector() { return makeNode(); }, querySelectorAll() { return []; },
  addEventListener() {},
};
globalThis.window = {
  innerWidth: 1280, innerHeight: 900,
  addEventListener() {}, matchMedia() { return { matches: false, addEventListener() {} }; },
};
globalThis.getComputedStyle = () => ({ getPropertyValue: () => '#334455' });
globalThis.requestAnimationFrame = (fn) => fn();

// ---- driver appended after the report's own definitions ----
const driver = `
;(function testDriver(){
  const results = [];
  function step(name, fn){ try { fn(); results.push(['OK ', name]); } catch(e){ results.push(['ERR', name + ' :: ' + (e && e.stack ? e.stack.split('\\n').slice(0,3).join(' | ') : e)]); } }

  step('init()', () => init());
  ['modern','both','archaic'].forEach(g => step('setGate('+g+')', () => setGate(g)));
  ['__all__', ...DATA.meta.scope_books].forEach(b => step('setBook('+b+')', () => setBook(b)));

  // drillChapter across each book, first available source + a scan id
  const byBook = {};
  DATA.chapters.forEach(c => { if(!byBook[c.book]) byBook[c.book]=c; });
  Object.values(byBook).forEach(c => {
    const sid = Object.keys(c.sources)[0];
    step('drillChapter('+c.locus+','+sid+')', () => drillChapter(c, sid));
    const scan = DATA.scan_ids.find(s => c.sources[s]);
    if (scan) step('drillChapter('+c.locus+','+scan+') [scan]', () => drillChapter(c, scan));
  });

  // zoomHist for a scan source (mod/arch = small numeric arrays)
  const scanSrc = DATA.sources.find(s => s.kind === 'scan') || DATA.sources[0];
  ['OT','NT'].forEach(t => step('zoomHist('+scanSrc.id+','+t+')',
    () => zoomHist(scanSrc, [0.72,0.81,0.9,0.95], [0.7,0.78,0.88], t)));

  // zoomScatter per book (V2 popout)
  DATA.meta.scope_books.forEach(b => step('zoomScatter('+b+')', () => zoomScatter(b)));

  // re-render under each gate after drill (state interplay)
  ['archaic','modern','both'].forEach(g => step('re-renderAll@'+g, () => { setGate(g); renderAll(); }));

  const errs = results.filter(r => r[0] === 'ERR');
  results.forEach(r => console.log(r[0] + '  ' + r[1]));
  console.log('\\n=== ' + (results.length - errs.length) + '/' + results.length + ' steps OK, ' + errs.length + ' errors ===');
  if (errs.length) process.exit(2);
})();
`;

// run report defs + driver in one script scope so driver sees DATA/functions
const vm = await import('node:vm');
vm.runInThisContext(js + '\n' + driver, { filename: 'reocr-report.inline.js' });
