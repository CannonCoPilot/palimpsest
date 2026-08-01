/**
 * gold_reaudit_G6.spec.ts — Re-audit Group G6
 *   JOB A: Geneva 1599 Bible (idx 6, project=geneva1599) full adversarial live-UI audit.
 *   JOB B: Visual confirmation that Acts now carries a "Historical" genre_division in
 *          websters (full canon) + kjv2016 (NT-only) — no gap between Gospels & Epistles.
 *
 * Reuses proven capture mechanics from gold_masks_all.spec.ts:
 *   - expand Structure(0)+Content(1) ElementGroupLane label cells to "Expanded"
 *   - scoped Browser zoom "+" (span.min-w-[50px] → following button "+"), zoom to <700 chars
 *   - reading sentence zoom "+" scoped to span.min-w-[65px]
 *   - masked-token color = getComputedStyle bg === rgb(58, 58, 61)
 *
 * Run from browser/:
 *   PALIMPSEST_BASE_URL=http://localhost:8080 npx playwright test e2e/gold_reaudit_G6.spec.ts --project=chromium --workers=1
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { test, expect, type Page, type Locator } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHOTS_DIR = path.resolve(__dirname, '../../core/.scratch/gold-audit/reaudit-4a/G6');
fs.mkdirSync(SHOTS_DIR, { recursive: true });
const API_BASE = process.env.PALIMPSEST_BASE_URL ?? 'http://localhost:8080';

async function shot(page: Page, name: string): Promise<string> {
  await page.screenshot({ path: path.join(SHOTS_DIR, `${name}.png`), fullPage: false });
  return `${name}.png`;
}

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
    await clickable.click({ force: true, timeout: 5_000 }).catch(() => {});
    await expandedBtn.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {});
  }
  await page.waitForTimeout(200);
  return await laneRow.locator('svg').first()
    .evaluate((el) => (el as SVGElement).getBoundingClientRect().height).catch(() => 0);
}

function browserZoomIn(page: Page): Locator {
  return page.locator('span.min-w-\\[50px\\]').locator('xpath=following::button[normalize-space(.)="+"][1]');
}
function browserZoomOut(page: Page): Locator {
  return page.locator('span.min-w-\\[50px\\]').locator('xpath=following::button[normalize-space(.)="-"][1]');
}

async function charsInView(page: Page): Promise<number> {
  const label = await page.locator('span.font-\\[var\\(--font-mono\\)\\]').first().textContent().catch(() => '');
  const m = (label ?? '').replace(/,/g, '').match(/(\d+)\s*[–-]\s*(\d+)/);
  return m ? parseInt(m[2], 10) - parseInt(m[1], 10) : NaN;
}

async function countMaskedTokens(page: Page): Promise<number> {
  return await page.evaluate(() => {
    let n = 0;
    for (const s of Array.from(document.querySelectorAll('span'))) {
      if (getComputedStyle(s).backgroundColor === 'rgb(58, 58, 61)') n++;
    }
    return n;
  });
}

// Try to jump the Browser viewport to a specific char offset via the Jump control.
async function jumpToOffset(page: Page, offset: number): Promise<boolean> {
  const jumpBtn = page.getByRole('button', { name: /Jump/i });
  if (!(await jumpBtn.isVisible({ timeout: 3000 }).catch(() => false))) return false;
  await jumpBtn.click().catch(() => {});
  await page.waitForTimeout(400);
  const inp = page.locator('input[placeholder*="offset"], input[placeholder*="char"], input[type="number"], input[type="text"]').first();
  if (!(await inp.isVisible({ timeout: 2000 }).catch(() => false))) return false;
  await inp.fill(String(offset)).catch(() => {});
  await inp.press('Enter').catch(() => {});
  await page.waitForTimeout(800);
  return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// JOB A — Geneva 1599 full audit
// ─────────────────────────────────────────────────────────────────────────────
test('[G6 JOB A] geneva1599 full live-UI audit', async ({ page }) => {
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + String(e)));

  // 1. Load
  await page.goto(`/?project=geneva1599`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.getByRole('tab', { name: 'Reading' }).waitFor({ state: 'visible', timeout: 90_000 });
  await page.waitForTimeout(1200);
  await shot(page, '01-geneva-loaded-reading');

  // 2. Browser tab overview
  await page.getByRole('tab', { name: 'Browser' }).click();
  await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 20_000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await shot(page, '02-geneva-browser-overview');

  // 3. Expand BOTH lanes
  const structH = await expandLane(page, 0);
  const contentH = await expandLane(page, 1);
  await page.waitForTimeout(500);
  await shot(page, '03-geneva-both-lanes-expanded');
  console.log(`[G6 A] geneva structH=${structH} contentH=${contentH}`);

  // 4. Zoom to char-readable level (< ~700 chars)
  const zoomIn = browserZoomIn(page);
  let civ = await charsInView(page);
  for (let i = 0; i < 18 && (isNaN(civ) || civ > 650); i++) {
    await zoomIn.click({ force: true, timeout: 4_000 }).catch(() => {});
    await page.waitForTimeout(70);
    civ = await charsInView(page);
  }
  await page.mouse.move(640, 520);
  await page.waitForTimeout(400);
  const civFinal = await charsInView(page);
  const rects = await page.locator('svg rect').count().catch(() => 0);
  console.log(`[G6 A] geneva char zoom: chars=${civFinal} rects=${rects}`);
  await shot(page, '04-geneva-tracks-charzoom');

  // 5. Jump the browser to front_matter/chapter_heading_1 boundary region (~55053) to see
  //    front_matter -> chapter_heading -> verse prose transitions at char zoom.
  const jumped = await jumpToOffset(page, 55200);
  await page.waitForTimeout(500);
  // re-zoom in case jump reset zoom
  civ = await charsInView(page);
  for (let i = 0; i < 8 && (isNaN(civ) || civ > 650); i++) {
    await zoomIn.click({ force: true, timeout: 4_000 }).catch(() => {});
    await page.waitForTimeout(70);
    civ = await charsInView(page);
  }
  await page.mouse.move(640, 520);
  await page.waitForTimeout(400);
  console.log(`[G6 A] geneva jumped=${jumped} chars@55200=${await charsInView(page)}`);
  await shot(page, '05-geneva-front-matter-heading-region');

  // 6. Reading tab at sentence zoom — masked markers greyed / prose visible
  await page.getByRole('tab', { name: 'Reading' }).click();
  await page.waitForTimeout(1000);
  const readingZoomIn = page.locator('span.min-w-\\[65px\\]').locator('xpath=following::button[normalize-space(.)="+"][1]');
  // work -> chapter -> paragraph -> sentence (3 clicks from default paragraph is 1; click several)
  for (let i = 0; i < 3; i++) {
    await readingZoomIn.click({ timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(800);
  const maskedTokens = await countMaskedTokens(page);
  console.log(`[G6 A] geneva reading-sentence maskedTokens=${maskedTokens}`);
  await shot(page, '06-geneva-reading-sentence-masked');

  const jsErrors = errors.filter((e) => !e.includes('favicon') && !e.includes('ResizeObserver') && !e.includes('ERR_ABORTED'));
  console.log(`[G6 A] geneva jsErrors=${jsErrors.length}` + (jsErrors.length ? ' :: ' + jsErrors.slice(0, 5).join(' | ') : ''));
  fs.writeFileSync(path.join(SHOTS_DIR, 'jobA-console.txt'),
    `structH=${structH} contentH=${contentH} charZoom=${civFinal} rects=${rects} maskedTokens=${maskedTokens}\n`
    + `jsErrors(${jsErrors.length}):\n` + jsErrors.join('\n'));

  expect.soft(structH, 'Structure lane expanded').toBeGreaterThan(30);
  expect.soft(civFinal, 'zoomed to char level').toBeLessThan(1200);
  expect.soft(rects, 'track rects render').toBeGreaterThan(0);
  expect.soft(maskedTokens, 'masked tokens present in reading').toBeGreaterThan(0);
});

// ─────────────────────────────────────────────────────────────────────────────
// JOB B — Acts "Historical" genre_division confirmation
// ─────────────────────────────────────────────────────────────────────────────
interface ActsCase { project_id: string; label: string; actsStart: number; actsEnd: number; }
const ACTS_CASES: ActsCase[] = [
  { project_id: 'websters', label: 'Webster (full canon)', actsStart: 3716141, actsEnd: 3848837 },
  { project_id: 'kjv2016',  label: 'KJV2016 (NT-only)',    actsStart: 451550,  actsEnd: 584459 },
];

for (const c of ACTS_CASES) {
  test(`[G6 JOB B] ${c.project_id} Acts Historical genre_division`, async ({ page }) => {
    test.setTimeout(180_000);
    const errors: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

    await page.goto(`/?project=${c.project_id}`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.getByRole('tab', { name: 'Reading' }).waitFor({ state: 'visible', timeout: 90_000 });
    await page.waitForTimeout(1000);

    // Browser tab
    await page.getByRole('tab', { name: 'Browser' }).click();
    await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 20_000 }).catch(() => {});
    await page.waitForTimeout(1500);
    await shot(page, `10-${c.project_id}-browser-overview`);

    // Expand the lane containing genre_division (Structure lane = index 0).
    const structH = await expandLane(page, 0);
    const contentH = await expandLane(page, 1);
    await page.waitForTimeout(500);
    // Full-document overview of the genre_division sub-track (all bars visible, no zoom).
    await shot(page, `11-${c.project_id}-genre-division-fulldoc`);
    console.log(`[G6 B] ${c.project_id} structH=${structH} contentH=${contentH}`);

    // Zoom around the Acts region so the Gospels|Historical|Epistles bar transition is legible.
    const actsMid = Math.floor((c.actsStart + c.actsEnd) / 2);
    await jumpToOffset(page, actsMid);
    await page.waitForTimeout(500);
    // Zoom in a few steps for a clear look at the transition around Acts.
    const zoomIn = browserZoomIn(page);
    for (let i = 0; i < 4; i++) {
      await zoomIn.click({ force: true, timeout: 4_000 }).catch(() => {});
      await page.waitForTimeout(80);
    }
    await page.mouse.move(640, 520);
    await page.waitForTimeout(400);
    await shot(page, `12-${c.project_id}-genre-division-acts-zoom`);
    console.log(`[G6 B] ${c.project_id} acts-zoom chars=${await charsInView(page)}`);

    // Reading view near Acts 1 for corroboration.
    await page.getByRole('tab', { name: 'Reading' }).click();
    await page.waitForTimeout(1000);
    const readingZoomIn = page.locator('span.min-w-\\[65px\\]').locator('xpath=following::button[normalize-space(.)="+"][1]');
    for (let i = 0; i < 2; i++) {
      await readingZoomIn.click({ timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(400);
    }
    await page.waitForTimeout(600);
    await shot(page, `13-${c.project_id}-reading-near-acts`);

    const jsErrors = errors.filter((e) => !e.includes('favicon') && !e.includes('ResizeObserver') && !e.includes('ERR_ABORTED'));
    console.log(`[G6 B] ${c.project_id} jsErrors=${jsErrors.length}`);
    expect.soft(structH, `${c.project_id} Structure lane expanded`).toBeGreaterThan(30);
  });
}
