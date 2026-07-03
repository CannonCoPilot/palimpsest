/**
 * gold_masks_all.spec.ts — Gold-Set Bible masking visual QA (all 17 versions, one file)
 *
 * Supersedes the flaky gold_masks_{A,B,C,D}.spec.ts group specs. Uses the proven capture
 * sequence from gold_probe.spec.ts:
 *   - expand Structure + Content element-group lanes to "Expanded" (stable label-cell targeting,
 *     menu closed by re-clicking the same cell),
 *   - zoom the Browser viewport to char level (adaptive: zoomAroundCenter until <~700 chars in
 *     view, centered on the document midpoint = mid-scripture, so individual mask elements resolve),
 *   - capture the Reading tab at sentence ("char") zoom with masked markers greyed.
 *
 * Sequential single-worker so afterAll can aggregate one report.
 *
 * Run from browser/:
 *   PALIMPSEST_BASE_URL=http://localhost:8080 npx playwright test e2e/gold_masks_all.spec.ts --project=chromium --workers=1
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { test, expect, type Page, type Locator } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHOTS_DIR = path.resolve(__dirname, '../../core/.scratch/gold-audit/ui-shots/ALL');
fs.mkdirSync(SHOTS_DIR, { recursive: true });
const API_BASE = process.env.PALIMPSEST_BASE_URL ?? 'http://localhost:8080';

interface BibleEntry { idx: number; project_id: string; label: string }

// All 17 gold-set Bibles (idx → project_id verified against the running :8080 workspace).
const BIBLES: BibleEntry[] = [
  { idx: 5,   project_id: 'douay-rheims-bible-complete-original-unabriged-full-douay-rheims-version-2018-1a24ae78af9f25ce66b9f156d163841a-anna-s-archive', label: 'DR-Haydock (epub)' },
  { idx: 100, project_id: 'douay-rheims-bible-challoner-s-revised-version-2024-global-grey-ebooks-d727529260a20949024cead95f4b81cf-anna-s-archive', label: 'DR-Challoner (epub)' },
  { idx: 201, project_id: 'coverdale', label: 'Coverdale 1535' },
  { idx: 202, project_id: 'bishops', label: "Bishops' Bible" },
  { idx: 203, project_id: 'wycliffe-reconstructed', label: 'Wycliffe (reconstructed)' },
  { idx: 208, project_id: 'great', label: 'Great Bible' },
  { idx: 209, project_id: 'matthews', label: "Matthew's Bible" },
  { idx: 210, project_id: 'websters', label: 'Webster 1833' },
  { idx: 211, project_id: 'wessex', label: 'Wessex Gospels' },
  { idx: 212, project_id: 'youngs', label: "Young's Literal" },
  { idx: 213, project_id: 'juliasmith', label: 'Julia Smith 1876' },
  { idx: 214, project_id: 'kjv2016', label: 'KJV2016 (NT)' },
  { idx: 215, project_id: 'emtv', label: 'EMTV (NT)' },
  { idx: 216, project_id: 'kjv1769', label: 'KJV 1769' },
  { idx: 217, project_id: 'tyndale-epub-reconstructed', label: 'Tyndale (epub)' },
  { idx: 218, project_id: 'geneva1560-epub-reconstructed', label: 'Geneva 1560 (epub)' },
  { idx: 219, project_id: 'kjv1611-comprehensive-reconstructed', label: 'KJV 1611 (comprehensive)' },
];

interface Finding {
  idx: number; project_id: string; label: string;
  loaded: boolean; loadError?: string;
  accurate: { pass: boolean; note: string };
  structH: number; contentH: number;
  charsInView: number; rects: number; maskedTokens: number;
  screenshots: string[];
  jsErrors: number;
}
const findings: Finding[] = [];

// ── Helpers (proven in gold_probe.spec.ts) ──────────────────────────────────

async function shot(page: Page, name: string): Promise<string> {
  await page.screenshot({ path: path.join(SHOTS_DIR, `${name}.png`), fullPage: false });
  return `ui-shots/ALL/${name}.png`;
}

/** ElementGroupLane label cells are the only `div.w-[100px].relative.shrink-0` — stable across expansion. */
function laneCell(page: Page, idx: number): Locator {
  return page.locator('div.w-\\[100px\\].relative.shrink-0').nth(idx);
}

async function expandLane(page: Page, idx: number): Promise<number> {
  const cell = laneCell(page, idx);
  if ((await cell.count()) === 0) return 0;
  await cell.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
  const laneRow = cell.locator('xpath=..');
  const clickable = cell.locator(':scope > div').first();
  await clickable.click({ force: true, timeout: 5_000 }).catch(() => {});
  await page.waitForTimeout(250);
  const expandedBtn = cell.getByRole('button', { name: 'Expanded' });
  const vis = await expandedBtn.isVisible().catch(() => false);
  if (vis) {
    await expandedBtn.click({ force: true, timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(350);
    await clickable.click({ force: true, timeout: 5_000 }).catch(() => {}); // re-click closes menu
    await expandedBtn.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {});
  }
  await page.waitForTimeout(200);
  return await laneRow.locator('svg').first()
    .evaluate((el) => (el as SVGElement).getBoundingClientRect().height).catch(() => 0);
}

/** Browser viewport zoom-in "+" (scoped away from the always-present reading-zoom "+"). */
function browserZoomIn(page: Page): Locator {
  return page.locator('span.min-w-\\[50px\\]').locator('xpath=following::button[normalize-space(.)="+"][1]');
}

async function charsInView(page: Page): Promise<number> {
  const label = await page.locator('span.font-\\[var\\(--font-mono\\)\\]').first().textContent().catch(() => '');
  const m = (label ?? '').replace(/,/g, '').match(/(\d+)\s*[–-]\s*(\d+)/);
  return m ? parseInt(m[2], 10) - parseInt(m[1], 10) : NaN;
}

/** Count masked tokens: spans whose computed background is MASKED_BG (#3a3a3d = rgb(58,58,61)). */
async function countMaskedTokens(page: Page): Promise<number> {
  return await page.evaluate(() => {
    let n = 0;
    for (const s of Array.from(document.querySelectorAll('span'))) {
      if (getComputedStyle(s).backgroundColor === 'rgb(58, 58, 61)') n++;
    }
    return n;
  });
}

interface SectionsData { genericFound: string[]; specificFound: string[]; maskedTypes: string[]; sectionCount: number }
async function probeSections(page: Page, projectId: string): Promise<SectionsData | null> {
  try {
    const resp = await page.request.get(`${API_BASE}/api/projects/${encodeURIComponent(projectId)}/sections`);
    if (!resp.ok()) return null;
    const data = await resp.json();
    const types = new Set<string>((data.sections ?? []).map((s: { type: string }) => s.type));
    const mb: Record<string, boolean> = data.mask_by_type ?? {};
    const GENERIC = ['body', 'volume', 'book', 'part', 'section'];
    const SPECIFIC = ['chapter', 'header', 'heading', 'chapter_heading', 'front_matter', 'genre_division', 'verse'];
    return {
      genericFound: GENERIC.filter((t) => types.has(t)),
      specificFound: SPECIFIC.filter((t) => types.has(t)),
      maskedTypes: Object.entries(mb).filter(([, v]) => v).map(([k]) => k).slice(0, 12),
      sectionCount: (data.sections ?? []).length,
    };
  } catch { return null; }
}

// ── Test per Bible ──────────────────────────────────────────────────────────

for (const bible of BIBLES) {
  test(`[idx ${bible.idx}] ${bible.label} (${bible.project_id})`, async ({ page }) => {
    test.setTimeout(150_000);
    const errors: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

    const f: Finding = {
      idx: bible.idx, project_id: bible.project_id, label: bible.label,
      loaded: false, accurate: { pass: false, note: '' },
      structH: 0, contentH: 0, charsInView: NaN, rects: 0, maskedTokens: 0,
      screenshots: [], jsErrors: 0,
    };
    findings.push(f);

    // 1. Load
    try {
      await page.goto(`/?project=${encodeURIComponent(bible.project_id)}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await page.getByRole('tab', { name: 'Reading' }).waitFor({ state: 'visible', timeout: 75_000 });
      f.loaded = true;
    } catch (e) {
      f.loadError = String(e).slice(0, 200);
      f.screenshots.push(await shot(page, `${bible.idx}-load-failure`));
      return;
    }

    // 2. Accuracy (sections API)
    const sec = await probeSections(page, bible.project_id);
    if (sec) {
      f.accurate = {
        pass: sec.genericFound.length > 0 && (sec.specificFound.length > 0 || sec.maskedTypes.length > 0),
        note: `generic:[${sec.genericFound.join(',')}] specific:[${sec.specificFound.join(',')}] `
            + `masked:[${sec.maskedTypes.join(',')}] sections:${sec.sectionCount}`,
      };
    } else {
      f.accurate = { pass: false, note: 'sections API probe failed' };
    }

    // 3. Browser tab + overview
    await page.getByRole('tab', { name: 'Browser' }).click();
    await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 20_000 });
    await page.waitForTimeout(1200);
    f.screenshots.push(await shot(page, `${bible.idx}-browser-overview`));

    // 4. Expand both element-group lanes
    f.structH = await expandLane(page, 0);
    f.contentH = await expandLane(page, 1);
    f.screenshots.push(await shot(page, `${bible.idx}-browser-expanded-fulldoc`));

    // 5. Zoom to char level (adaptive, centered on document midpoint = mid-scripture)
    const zoomIn = browserZoomIn(page);
    let civ = await charsInView(page);
    for (let i = 0; i < 16 && (isNaN(civ) || civ > 700); i++) {
      await zoomIn.click({ force: true, timeout: 4_000 }).catch(() => {});
      await page.waitForTimeout(60);
      civ = await charsInView(page);
    }
    await page.mouse.move(640, 520); // move off buttons so no tooltip overlaps the capture
    await page.waitForTimeout(400);
    f.charsInView = await charsInView(page);
    f.rects = await page.locator('svg rect').count().catch(() => 0);
    f.screenshots.push(await shot(page, `${bible.idx}-browser-tracks-zoomed`));

    // 6. Reading tab at sentence ("char") zoom
    await page.getByRole('tab', { name: 'Reading' }).click();
    await page.waitForTimeout(1000);
    const readingZoomIn = page.locator('span.min-w-\\[65px\\]').locator('xpath=following::button[normalize-space(.)="+"][1]');
    await readingZoomIn.click({ timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(900);
    f.maskedTokens = await countMaskedTokens(page);
    f.screenshots.push(await shot(page, `${bible.idx}-reading-sentence`));

    f.jsErrors = errors.filter((e) => !e.includes('favicon') && !e.includes('ResizeObserver') && !e.includes('ERR_ABORTED')).length;
    console.log(`[idx ${bible.idx}] ${bible.label}: structH=${f.structH} contentH=${f.contentH} `
      + `chars=${f.charsInView} rects=${f.rects} masked=${f.maskedTokens} jsErr=${f.jsErrors}`);

    expect.soft(f.loaded, `[${bible.idx}] loaded`).toBe(true);
    expect.soft(f.structH, `[${bible.idx}] Structure lane expanded`).toBeGreaterThan(30);
    expect.soft(f.charsInView, `[${bible.idx}] zoomed to char level`).toBeLessThan(1500);
    expect.soft(f.rects, `[${bible.idx}] track elements render at char zoom`).toBeGreaterThan(0);
  });
}

// ── Report ────────────────────────────────────────────────────────────────

test.afterAll(async () => {
  const sorted = [...new Map(findings.map((f) => [f.idx, f])).values()].sort((a, b) => a.idx - b.idx);
  const L: string[] = [
    '# UI Verification Report — Gold Set Bible Masking Maps (all 17)',
    '',
    `**Date**: ${new Date().toISOString().slice(0, 19)}Z`,
    '**Spec**: browser/e2e/gold_masks_all.spec.ts',
    '**Server**: ' + API_BASE,
    `**Bibles audited**: ${sorted.length} / 17`,
    '**Screenshots dir**: core/.scratch/gold-audit/ui-shots/ALL/',
    '',
    'Per Bible, four captures: `-browser-overview` (full-doc lanes), `-browser-expanded-fulldoc`',
    '(Structure+Content lanes in Expanded mode), `-browser-tracks-zoomed` (char-level zoom — the KEY',
    'deliverable, individual mask elements distinguishable), `-reading-sentence` (Reading tab at',
    'sentence zoom, structural markers greyed / prose visible).',
    '',
    '| idx | Bible | Load | Accurate | struct/content H | chars in view | rects | masked toks | JS err |',
    '|----:|-------|:----:|:--------:|:----------------:|:-------------:|------:|------------:|:------:|',
  ];
  for (const f of sorted) {
    const ok = f.loaded && f.accurate.pass && f.structH > 30 && f.charsInView < 1500 && f.rects > 0;
    L.push(`| ${f.idx} | ${f.label} | ${f.loaded ? 'OK' : 'FAIL'} | ${f.accurate.pass ? 'OK' : 'FLAG'} `
      + `| ${f.structH}/${f.contentH} | ${f.charsInView} | ${f.rects} | ${f.maskedTokens} | ${f.jsErrors} | ${ok ? '' : ' ⚠'}`);
  }
  L.push('', '---', '', '## Per-Bible detail', '');
  for (const f of sorted) {
    const ok = f.loaded && f.accurate.pass && f.structH > 30 && f.charsInView < 1500 && f.rects > 0;
    L.push(`### [idx ${f.idx}] ${f.label} — ${ok ? 'PASS' : (f.loaded ? 'FLAG' : 'LOAD FAILED')}`, '');
    if (!f.loaded) L.push(`> LOAD ERROR: ${f.loadError}`, '');
    L.push(`- **Accurate**: ${f.accurate.pass ? 'PASS' : 'FLAG'} — ${f.accurate.note}`);
    L.push(`- **Lanes expanded**: Structure svg=${f.structH}px, Content svg=${f.contentH}px (ribbon baseline 28px)`);
    L.push(`- **Char zoom**: ${f.charsInView} chars in view, ${f.rects} SVG track rects, ${f.maskedTokens} masked tokens (reading)`);
    L.push(`- **JS errors**: ${f.jsErrors}`);
    L.push(`- **Screenshots**: ${f.screenshots.map((s) => '`' + s + '`').join(', ')}`);
    L.push('');
  }
  const pass = sorted.filter((f) => f.loaded && f.accurate.pass && f.structH > 30 && f.charsInView < 1500 && f.rects > 0);
  L.push('---', '', `## Aggregate: ${pass.length} / ${sorted.length} PASS`, '');
  fs.writeFileSync(path.resolve(__dirname, '../../core/.scratch/gold-audit/ui-report-ALL.md'), L.join('\n'));
});
