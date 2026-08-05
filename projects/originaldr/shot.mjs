import { chromium } from '@playwright/test';
const base = '/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/mask_engine/originaldr_reconstruction/originaldr-brief.html';
const outdir = '/Users/nathanielcannon/Claude/Projects/palimpsest/core/.scratch/originaldr-project';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1060, height: 900 }, deviceScaleFactor: 2 });
await p.goto('file://' + base);
const figs = await p.locator('svg.fig').all();
const names = ['ideogram', 'depth', 'ci', 'glyph'];
for (let i = 0; i < figs.length; i++) {
  await figs[i].screenshot({ path: `${outdir}/fig-${names[i]}.png` });
  console.log('shot', names[i]);
}
await b.close();
