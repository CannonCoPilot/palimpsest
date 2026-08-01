/**
 * gold_reaudit_G6_websters_acts.spec.ts — focused websters NT/Acts genre_division zoom.
 * Pans the Browser viewport toward the NT (Acts sits at ~3.72M–3.85M of 4.245M) and zooms
 * so the Gospels|Historical(Acts)|Epistles bar transition is legible in the genre_division sub-track.
 */
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { test, type Page, type Locator } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SHOTS_DIR = path.resolve(__dirname, '../../core/.scratch/gold-audit/reaudit-4a/G6');
fs.mkdirSync(SHOTS_DIR, { recursive: true });

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
  if (await expandedBtn.isVisible().catch(() => false)) {
    await expandedBtn.click({ force: true, timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(350);
    await clickable.click({ force: true, timeout: 5_000 }).catch(() => {});
    await expandedBtn.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {});
  }
  await page.waitForTimeout(200);
  return await laneRow.locator('svg').first()
    .evaluate((el) => (el as SVGElement).getBoundingClientRect().height).catch(() => 0);
}
async function charLabel(page: Page): Promise<string> {
  return (await page.locator('span.font-\\[var\\(--font-mono\\)\\]').first().textContent().catch(() => '')) ?? '';
}

test('[G6 JOB B focus] websters NT Acts genre_division zoom', async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto(`/?project=websters`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.getByRole('tab', { name: 'Reading' }).waitFor({ state: 'visible', timeout: 90_000 });
  await page.getByRole('tab', { name: 'Browser' }).click();
  await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 20_000 }).catch(() => {});
  await page.waitForTimeout(1200);
  await expandLane(page, 0);
  await expandLane(page, 1);
  await page.waitForTimeout(400);

  // Strategy: zoom in (recenters on doc midpoint) to a modest window, then PAN RIGHT repeatedly
  // via track drag until the visible window brackets Acts (~3.72M–3.85M of 4.245M).
  const box = await page.locator('svg').first().boundingBox().catch(() => null);
  const cx = box ? box.x + box.width * 0.5 : 640;
  const cy = box ? box.y + 30 : 210;

  // Zoom in ~5 steps (each ×2) → window ~ 4.245M/32 ≈ 130k chars, centered ~2.12M.
  for (let i = 0; i < 5; i++) {
    await page.mouse.move(cx, cy);
    await page.keyboard.down('Control');
    await page.mouse.wheel(0, -240);
    await page.keyboard.up('Control');
    await page.waitForTimeout(150);
  }
  await page.waitForTimeout(300);
  console.log('[G6 B focus] websters after zoom label=', await charLabel(page));

  // Pan right until viewStart passes ~3.72M (Acts start). Drag the track leftwards to move forward.
  const parseStart = async (): Promise<number> => {
    const m = (await charLabel(page)).replace(/,/g, '').match(/(\d+)\s*[–-]\s*(\d+)/);
    return m ? parseInt(m[1], 10) : NaN;
  };
  const ty = box ? box.y + 20 : 200;
  const x0 = box ? box.x + box.width * 0.85 : 1080;
  const x1 = box ? box.x + box.width * 0.15 : 200;
  for (let i = 0; i < 40; i++) {
    const s = await parseStart();
    if (!isNaN(s) && s >= 3700000 && s <= 3800000) break;
    await page.mouse.move(x0, ty);
    await page.mouse.down();
    await page.mouse.move(x1, ty, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(120);
  }
  await page.mouse.move(cx, 520);
  await page.waitForTimeout(500);
  console.log('[G6 B focus] websters after pan-to-Acts label=', await charLabel(page));
  await page.screenshot({ path: path.join(SHOTS_DIR, '14-websters-nt-acts-zoom.png') });

  // One more pan a little further right to catch the Historical→Epistles transition too.
  for (let i = 0; i < 4; i++) {
    await page.mouse.move(x0, ty);
    await page.mouse.down();
    await page.mouse.move(x1, ty, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(120);
  }
  await page.mouse.move(cx, 520);
  await page.waitForTimeout(400);
  console.log('[G6 B focus] websters further-right label=', await charLabel(page));
  await page.screenshot({ path: path.join(SHOTS_DIR, '15-websters-nt-acts-panned.png') });
});
