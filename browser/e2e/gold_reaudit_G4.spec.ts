/**
 * gold_reaudit_G4.spec.ts — Critical live UI re-audit for Gold Set Group G4
 *
 * Assigned Bibles:
 *   210 → websters   (Webster 1833)
 *   212 → youngs     (Young's Literal Translation)
 *   213 → juliasmith (Julia Smith 1876)
 *
 * These are self-marked 66-book TXT marker Bibles. Unusual wording (Young's/Julia Smith)
 * is expected content — DO NOT flag it. Verify STRUCTURAL masking: book headers, chapter
 * headings, verse-number rendering. Check greying starts/ends precisely at markers with no
 * overrun into adjacent verse prose.
 *
 * Three criteria per gold-set-standard §1:
 *   Complete  — body tiles [0,text_len) AND chapter tiles [0,text_len) — two independent layers
 *   Accurate  — header + chapter_heading masked; chapter/body/book NOT masked; correct types
 *   Precise   — each masked element's char bounds exactly capture the marker token, no overrun
 *
 * Run from browser/:
 *   PALIMPSEST_BASE_URL=http://localhost:8080 npx playwright test e2e/gold_reaudit_G4.spec.ts \
 *     --project=chromium --workers=1
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { test, expect, type Page, type Locator } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const SHOTS_DIR = path.resolve(__dirname, '../../core/.scratch/gold-audit/reaudit-4a/G4');
fs.mkdirSync(SHOTS_DIR, { recursive: true });

const API_BASE = process.env.PALIMPSEST_BASE_URL ?? 'http://localhost:8080';

interface BibleEntry { idx: number; project_id: string; label: string }

const BIBLES: BibleEntry[] = [
  { idx: 210, project_id: 'websters',   label: 'Webster 1833' },
  { idx: 212, project_id: 'youngs',     label: "Young's Literal Translation" },
  { idx: 213, project_id: 'juliasmith', label: 'Julia Smith 1876' },
];

// ── Types ────────────────────────────────────────────────────────────────────

interface CriterionResult { pass: boolean; evidence: string }

interface BibleFinding {
  idx: number; project_id: string; label: string;
  loaded: boolean; loadError?: string;
  complete:  CriterionResult;
  accurate:  CriterionResult;
  precise:   CriterionResult;
  structH: number; contentH: number;
  charsInView: number; rects: number; maskedTokens: number;
  browserZoomed: boolean;
  readingZoomed: boolean;
  screenshots: string[];
  jsErrors: string[];
  defects: Array<{ severity: 'blocker'|'major'|'minor'; description: string }>;
}

const findings: BibleFinding[] = [];

// ── Helpers (reused from gold_masks_all.spec.ts proven mechanics) ─────────────

async function shot(page: Page, name: string): Promise<string> {
  const fname = `${name}.png`;
  await page.screenshot({ path: path.join(SHOTS_DIR, fname), fullPage: false });
  return fname;
}

/** ElementGroupLane label cells: only `div.w-[100px].relative.shrink-0` in the Browser track */
function laneCell(page: Page, idx: number): Locator {
  return page.locator('div.w-\\[100px\\].relative.shrink-0').nth(idx);
}

async function expandLane(page: Page, idx: number): Promise<number> {
  const cell = laneCell(page, idx);
  if ((await cell.count()) === 0) return 0;
  await cell.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
  const clickable = cell.locator(':scope > div').first();
  await clickable.click({ force: true, timeout: 5_000 }).catch(() => {});
  await page.waitForTimeout(300);
  const expandedBtn = cell.getByRole('button', { name: 'Expanded' });
  const vis = await expandedBtn.isVisible().catch(() => false);
  if (vis) {
    await expandedBtn.click({ force: true, timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(400);
    // Re-click the label cell to close the menu (no Escape handler; mousedown outside closes it)
    await clickable.click({ force: true, timeout: 5_000 }).catch(() => {});
    await expandedBtn.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {});
  }
  await page.waitForTimeout(200);
  const laneRow = cell.locator('xpath=..');
  return await laneRow.locator('svg').first()
    .evaluate((el) => (el as SVGElement).getBoundingClientRect().height).catch(() => 0);
}

/** Browser "+" zoom button (scoped away from reading-zoom "+") */
function browserZoomIn(page: Page): Locator {
  return page.locator('span.min-w-\\[50px\\]')
    .locator('xpath=following::button[normalize-space(.)="+"][1]');
}

/** Reading "+" zoom (char/sentence level) */
function readingZoomIn(page: Page): Locator {
  return page.locator('span.min-w-\\[65px\\]')
    .locator('xpath=following::button[normalize-space(.)="+"][1]');
}

async function charsInView(page: Page): Promise<number> {
  const label = await page.locator('span.font-\\[var\\(--font-mono\\)\\]').first()
    .textContent().catch(() => '');
  const m = (label ?? '').replace(/,/g, '').match(/(\d+)\s*[–\-]\s*(\d+)/);
  return m ? parseInt(m[2], 10) - parseInt(m[1], 10) : NaN;
}

async function countMaskedTokens(page: Page): Promise<number> {
  return page.evaluate(() => {
    let n = 0;
    for (const s of Array.from(document.querySelectorAll('span'))) {
      if (getComputedStyle(s).backgroundColor === 'rgb(58, 58, 61)') n++;
    }
    return n;
  });
}

/** Probe sections API for the Bible */
async function probeSections(page: Page, projectId: string) {
  const resp = await page.request.get(
    `${API_BASE}/api/projects/${encodeURIComponent(projectId)}/sections`
  ).catch(() => null);
  if (!resp || !resp.ok()) return null;
  return resp.json().catch(() => null);
}

// ── Per-Bible test ────────────────────────────────────────────────────────────

for (const bible of BIBLES) {
  test(`[G4-idx${bible.idx}] ${bible.label} — Critical Re-Audit`, async ({ page }) => {
    test.setTimeout(200_000);

    const jsErrors: string[] = [];
    page.on('console', (m) => {
      if (m.type() === 'error') jsErrors.push(m.text());
    });

    const f: BibleFinding = {
      idx: bible.idx, project_id: bible.project_id, label: bible.label,
      loaded: false,
      complete:  { pass: false, evidence: '' },
      accurate:  { pass: false, evidence: '' },
      precise:   { pass: false, evidence: '' },
      structH: 0, contentH: 0,
      charsInView: NaN, rects: 0, maskedTokens: 0,
      browserZoomed: false, readingZoomed: false,
      screenshots: [], jsErrors: [],
      defects: [],
    };
    findings.push(f);

    // ── 1. Load ──────────────────────────────────────────────────────────────
    try {
      await page.goto(
        `${API_BASE}/?project=${encodeURIComponent(bible.project_id)}`,
        { waitUntil: 'domcontentloaded', timeout: 45_000 }
      );
      await page.getByRole('tab', { name: 'Reading' })
        .waitFor({ state: 'visible', timeout: 75_000 });
      f.loaded = true;
    } catch (e) {
      f.loadError = String(e).slice(0, 300);
      f.defects.push({ severity: 'blocker', description: `Failed to load project: ${f.loadError}` });
      f.screenshots.push(await shot(page, `G4-${bible.idx}-load-failure`));
      return;
    }

    // ── 2. Programmatic precision: sections API ───────────────────────────────
    const sectionsData = await probeSections(page, bible.project_id);
    if (!sectionsData) {
      f.accurate.evidence = 'sections API probe failed';
      f.defects.push({ severity: 'blocker', description: 'GET /api/projects/{id}/sections failed' });
    } else {
      const sections: Array<{ type: string; start: number; end: number; id: string }> =
        sectionsData.sections ?? [];
      const maskByType: Record<string, boolean> = sectionsData.mask_by_type ?? {};
      const textLen: number = sectionsData.text_len ?? 0;

      // Build type counts
      const typeCounts: Record<string, number> = {};
      for (const s of sections) typeCounts[s.type] = (typeCounts[s.type] ?? 0) + 1;

      // ── COMPLETE check ───────────────────────────────────────────────────
      // Generic layer: body (must tile [0,text_len))
      const bodySecs = sections.filter(s => s.type === 'body').sort((a,b) => a.start - b.start);
      const bodyTiles = bodySecs.length === 1 && bodySecs[0].start === 0 && bodySecs[0].end === textLen;

      // Specific layer: chapter (must tile [0,text_len))
      const chapSecs = sections.filter(s => s.type === 'chapter').sort((a,b) => a.start - b.start);
      let chapterGaps = 0;
      let prev = 0;
      for (const s of chapSecs) {
        if (s.start !== prev) chapterGaps++;
        prev = s.end;
      }
      if (prev !== textLen) chapterGaps++;
      const chapterTiles = chapterGaps === 0;

      // Book tiling
      const bookSecs = sections.filter(s => s.type === 'book').sort((a,b) => a.start - b.start);
      let bookGaps = 0;
      let prevB = 0;
      for (const s of bookSecs) {
        if (s.start !== prevB) bookGaps++;
        prevB = s.end;
      }
      if (prevB !== textLen) bookGaps++;

      f.complete.pass = bodyTiles && chapterTiles;
      f.complete.evidence = [
        `body tiles [0,${textLen}): ${bodyTiles ? 'YES' : `NO (${bodySecs.length} elements)`}`,
        `chapter tiles [0,${textLen}): ${chapterTiles ? 'YES' : `NO gaps=${chapterGaps}`}`,
        `book tiles: ${bookGaps === 0 ? 'YES' : `NO gaps=${bookGaps}`}`,
        `counts: body=${typeCounts.body??0}, book=${typeCounts.book??0}, chapter=${typeCounts.chapter??0}`,
        `        header=${typeCounts.header??0}, chapter_heading=${typeCounts.chapter_heading??0}`,
        `text_len=${textLen}`,
      ].join('; ');

      if (!bodyTiles)
        f.defects.push({ severity: 'blocker', description: `body does not tile [0,${textLen})` });
      if (!chapterTiles)
        f.defects.push({ severity: 'blocker', description: `chapter layer has ${chapterGaps} gap(s) — does not tile [0,${textLen})` });

      // ── ACCURATE check ───────────────────────────────────────────────────
      // Expected masked: header=true, chapter_heading=true
      // Expected NOT masked: body=false, book=false, chapter=false
      const headerMasked        = maskByType['header'] === true;
      const chHeadingMasked     = maskByType['chapter_heading'] === true;
      const bodyNotMasked       = maskByType['body'] !== true;
      const bookNotMasked       = maskByType['book'] !== true;
      const chapterNotMasked    = maskByType['chapter'] !== true;
      const has66Books          = typeCounts.book === 66;
      const has1189Chapters     = typeCounts.chapter === 1189;
      const has66Headers        = typeCounts.header === 66;
      const has1189ChHeadings   = typeCounts.chapter_heading === 1189;

      f.accurate.pass = headerMasked && chHeadingMasked && bodyNotMasked && bookNotMasked
        && chapterNotMasked && has66Books && has1189Chapters;

      f.accurate.evidence = [
        `mask_by_type: header=${maskByType.header}, chapter_heading=${maskByType.chapter_heading}`,
        `              body=${maskByType.body}, book=${maskByType.book}, chapter=${maskByType.chapter}`,
        `counts: book=${typeCounts.book} (expect 66), chapter=${typeCounts.chapter} (expect 1189)`,
        `        header=${typeCounts.header} (expect 66), chapter_heading=${typeCounts.chapter_heading} (expect 1189)`,
        `genre_division=${typeCounts.genre_division??0} (expect 7)`,
      ].join('; ');

      if (!headerMasked)
        f.defects.push({ severity: 'blocker', description: 'header type NOT masked (expected masked=true)' });
      if (!chHeadingMasked)
        f.defects.push({ severity: 'blocker', description: 'chapter_heading type NOT masked (expected masked=true)' });
      if (!bodyNotMasked)
        f.defects.push({ severity: 'major', description: 'body type is MASKED (should be false)' });
      if (!bookNotMasked)
        f.defects.push({ severity: 'major', description: 'book type is MASKED (should be false)' });
      if (!has66Books)
        f.defects.push({ severity: 'blocker', description: `book count=${typeCounts.book??0}, expected 66` });
      if (!has1189Chapters)
        f.defects.push({ severity: 'blocker', description: `chapter count=${typeCounts.chapter??0}, expected 1189` });
      if (!has66Headers)
        f.defects.push({ severity: 'major', description: `header count=${typeCounts.header??0}, expected 66` });
      if (!has1189ChHeadings)
        f.defects.push({ severity: 'major', description: `chapter_heading count=${typeCounts.chapter_heading??0}, expected 1189` });

      // ── PRECISE check (char-slice verification) ──────────────────────────
      // Read reference text via /data endpoint
      const refResp = await page.request.get(
        `${API_BASE}/data/${encodeURIComponent(bible.project_id)}/reference.txt`
      ).catch(() => null);
      if (refResp && refResp.ok()) {
        const refText = await refResp.text();
        const headers     = sections.filter(s => s.type === 'header')
          .sort((a,b) => a.start - b.start);
        const chHeadings  = sections.filter(s => s.type === 'chapter_heading')
          .sort((a,b) => a.start - b.start);

        const preciseProblems: string[] = [];

        // Check ALL headers for precision
        let headerPreciseOk = 0, headerPreciseBad = 0;
        for (const h of headers) {
          const slice = refText.slice(h.start, h.end);
          const beforeChar = h.start > 0 ? refText[h.start - 1] : '';
          const afterChar  = h.end < refText.length ? refText[h.end] : '';
          const ok = slice.startsWith('# ')
            && !slice.endsWith('\n')
            && (h.start === 0 || beforeChar === '\n')
            && (afterChar === '\n' || afterChar === '');
          if (ok) { headerPreciseOk++; }
          else {
            headerPreciseBad++;
            if (headerPreciseBad <= 3) {
              preciseProblems.push(
                `header[${h.start}..${h.end}]=${JSON.stringify(slice.slice(0,30))} ` +
                `before=${JSON.stringify(beforeChar)} after=${JSON.stringify(afterChar)}`
              );
            }
          }
        }

        // Check ALL chapter_headings for precision
        let chPreciseOk = 0, chPreciseBad = 0;
        for (const ch of chHeadings) {
          const slice = refText.slice(ch.start, ch.end);
          const beforeChar = ch.start > 0 ? refText[ch.start - 1] : '';
          const afterChar  = ch.end < refText.length ? refText[ch.end] : '';
          const ok = slice.startsWith('## ')
            && !slice.endsWith('\n')
            && (ch.start === 0 || beforeChar === '\n')
            && (afterChar === '\n' || afterChar === '');
          if (ok) { chPreciseOk++; }
          else {
            chPreciseBad++;
            if (chPreciseBad <= 3) {
              preciseProblems.push(
                `ch_heading[${ch.start}..${ch.end}]=${JSON.stringify(slice.slice(0,40))} ` +
                `before=${JSON.stringify(beforeChar)} after=${JSON.stringify(afterChar)}`
              );
            }
          }
        }

        // Concrete specimens for report (Genesis 1 header, Genesis 1 ch_heading, Revelation 22 ch_heading)
        const specimen_h0   = headers[0];
        const specimen_ch0  = chHeadings[0];
        const specimen_chLast = chHeadings[chHeadings.length - 1];

        const specSlice_h0   = refText.slice(specimen_h0.start, specimen_h0.end);
        const specAfter_h0   = refText.slice(specimen_h0.end, specimen_h0.end + 20);
        const specSlice_ch0  = refText.slice(specimen_ch0.start, specimen_ch0.end);
        const specBefore_ch0 = refText.slice(Math.max(0, specimen_ch0.start - 5), specimen_ch0.start);
        const specAfter_ch0  = refText.slice(specimen_ch0.end, specimen_ch0.end + 30);
        const specSlice_chL  = refText.slice(specimen_chLast.start, specimen_chLast.end);
        const specBefore_chL = refText.slice(Math.max(0, specimen_chLast.start - 10), specimen_chLast.start);
        const specAfter_chL  = refText.slice(specimen_chLast.end, specimen_chLast.end + 30);

        f.precise.pass = headerPreciseBad === 0 && chPreciseBad === 0;
        f.precise.evidence = [
          `header precision: ${headerPreciseOk}/${headers.length} OK, ${headerPreciseBad} BAD`,
          `ch_heading precision: ${chPreciseOk}/${chHeadings.length} OK, ${chPreciseBad} BAD`,
          `SPECIMEN header[0] [${specimen_h0.start},${specimen_h0.end}): ` +
            `${JSON.stringify(specSlice_h0)} → after=${JSON.stringify(specAfter_h0.slice(0,15))}`,
          `SPECIMEN ch_heading[0] [${specimen_ch0.start},${specimen_ch0.end}): ` +
            `${JSON.stringify(specSlice_ch0)} before=${JSON.stringify(specBefore_ch0.slice(-5))} ` +
            `after=${JSON.stringify(specAfter_ch0.slice(0,20))}`,
          `SPECIMEN ch_heading[-1] [${specimen_chLast.start},${specimen_chLast.end}): ` +
            `${JSON.stringify(specSlice_chL)} before=...${JSON.stringify(specBefore_chL.slice(-5))} ` +
            `after=${JSON.stringify(specAfter_chL.slice(0,20))}`,
          ...(preciseProblems.length > 0 ? ['PROBLEMS: ' + preciseProblems.join(' | ')] : []),
        ].join('; ');

        if (headerPreciseBad > 0)
          f.defects.push({ severity: 'blocker',
            description: `${headerPreciseBad} header elements have imprecise char bounds` });
        if (chPreciseBad > 0)
          f.defects.push({ severity: 'blocker',
            description: `${chPreciseBad} chapter_heading elements have imprecise char bounds` });
      } else {
        f.precise.evidence = 'could not load reference.txt for char-slice check';
        f.defects.push({ severity: 'major', description: 'reference.txt unavailable — precise check skipped' });
      }
    }

    // ── 3. Browser tab — expand lanes, screenshot ─────────────────────────────
    await page.getByRole('tab', { name: 'Browser' }).click();
    await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 20_000 });
    await page.waitForTimeout(1200);
    f.screenshots.push(await shot(page, `G4-${bible.idx}-01-browser-overview`));

    // Expand Structure (idx=0) and Content (idx=1) lanes
    f.structH = await expandLane(page, 0);
    await page.waitForTimeout(300);
    f.contentH = await expandLane(page, 1);
    await page.waitForTimeout(400);
    f.screenshots.push(await shot(page, `G4-${bible.idx}-02-browser-expanded`));

    if (f.structH <= 30)
      f.defects.push({ severity: 'major', description: `Structure lane not expanded (svgH=${f.structH})` });
    if (f.contentH <= 30)
      f.defects.push({ severity: 'minor', description: `Content lane not expanded (svgH=${f.contentH})` });

    // ── 4. Browser zoom to char level ─────────────────────────────────────────
    const zoomIn = browserZoomIn(page);
    let civ = await charsInView(page);
    for (let i = 0; i < 18 && (isNaN(civ) || civ > 700); i++) {
      await zoomIn.click({ force: true, timeout: 4_000 }).catch(() => {});
      await page.waitForTimeout(80);
      civ = await charsInView(page);
    }
    await page.mouse.move(640, 520);
    await page.waitForTimeout(500);
    f.charsInView = await charsInView(page);
    f.rects = await page.locator('svg rect').count().catch(() => 0);
    f.browserZoomed = !isNaN(f.charsInView) && f.charsInView < 1500;
    f.screenshots.push(await shot(page, `G4-${bible.idx}-03-browser-zoomed`));

    if (!f.browserZoomed)
      f.defects.push({ severity: 'minor', description: `Could not zoom to char level (civ=${f.charsInView})` });
    if (f.rects === 0)
      f.defects.push({ severity: 'major', description: 'No SVG track rects at char zoom — masking bars missing' });

    // ── 5. Reading tab — sentence/char zoom with masked marker verification ────
    await page.getByRole('tab', { name: 'Reading' }).click();
    await page.waitForTimeout(1000);
    f.screenshots.push(await shot(page, `G4-${bible.idx}-04-reading-default`));

    // Zoom to sentence level (3 clicks of reading zoom)
    const rzIn = readingZoomIn(page);
    for (let i = 0; i < 3; i++) {
      await rzIn.click({ timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(600);
    }
    await page.waitForTimeout(800);
    f.maskedTokens = await countMaskedTokens(page);
    f.readingZoomed = f.maskedTokens > 0;
    f.screenshots.push(await shot(page, `G4-${bible.idx}-05-reading-sentence-zoom`));

    if (f.maskedTokens === 0)
      f.defects.push({ severity: 'major',
        description: 'No masked tokens visible at sentence zoom — chapter headings not greying' });

    // Verify that masked spans look correct: take a closer look at what is greyed
    // Grab text content of masked spans for a quick sanity check
    const maskedTexts = await page.evaluate(() => {
      const spans: string[] = [];
      for (const s of Array.from(document.querySelectorAll('span'))) {
        if (getComputedStyle(s).backgroundColor === 'rgb(58, 58, 61)') {
          spans.push((s.textContent ?? '').slice(0, 60));
        }
      }
      return spans.slice(0, 20); // first 20 for inspection
    });

    // Check: no masked span should be extremely long prose (over-masking)
    const overMaskedSpans = maskedTexts.filter(t => t.length > 50);
    if (overMaskedSpans.length > 0) {
      f.defects.push({ severity: 'major',
        description: `Masked spans appear too long (prose overrun?): ${JSON.stringify(overMaskedSpans.slice(0,3))}` });
    }

    // Add masked text samples to precise evidence for the report
    const maskedSample = maskedTexts.slice(0,10).map(t => JSON.stringify(t)).join(', ');

    // ── 6. Check other tabs briefly (Characters, Analysis) ────────────────────
    // Characters tab
    try {
      await page.getByRole('tab', { name: 'Characters' }).click();
      await page.waitForTimeout(1500);
      f.screenshots.push(await shot(page, `G4-${bible.idx}-06-characters`));
    } catch {}

    // Analysis tab - just check it loads
    try {
      await page.getByRole('tab', { name: 'Analysis' }).click();
      await page.waitForTimeout(1500);
      f.screenshots.push(await shot(page, `G4-${bible.idx}-07-analysis`));
    } catch {}

    // ── 7. JS errors ─────────────────────────────────────────────────────────
    f.jsErrors = jsErrors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('ResizeObserver') &&
      !e.includes('ERR_ABORTED')
    );

    if (f.jsErrors.length > 0) {
      f.defects.push({ severity: 'minor',
        description: `${f.jsErrors.length} JS console errors: ${f.jsErrors.slice(0,2).join(' | ')}` });
    }

    // ── 8. Log and assert ────────────────────────────────────────────────────
    console.log(
      `[G4-idx${bible.idx}] ${bible.label}:\n` +
      `  COMPLETE=${f.complete.pass} ACCURATE=${f.accurate.pass} PRECISE=${f.precise.pass}\n` +
      `  structH=${f.structH} contentH=${f.contentH} chars=${f.charsInView} ` +
      `rects=${f.rects} maskedTok=${f.maskedTokens} jsErr=${f.jsErrors.length}\n` +
      `  maskedSample=[${maskedSample}]`
    );

    expect.soft(f.loaded,          `[idx${bible.idx}] loaded`).toBe(true);
    expect.soft(f.complete.pass,   `[idx${bible.idx}] complete`).toBe(true);
    expect.soft(f.accurate.pass,   `[idx${bible.idx}] accurate`).toBe(true);
    expect.soft(f.precise.pass,    `[idx${bible.idx}] precise`).toBe(true);
    expect.soft(f.structH,         `[idx${bible.idx}] Structure lane expanded`).toBeGreaterThan(30);
    expect.soft(f.rects,           `[idx${bible.idx}] SVG track rects rendered`).toBeGreaterThan(0);
    expect.soft(f.maskedTokens,    `[idx${bible.idx}] masked tokens in Reading view`).toBeGreaterThan(0);
  });
}

// ── Report ─────────────────────────────────────────────────────────────────────

test.afterAll(async () => {
  const byIdx = new Map(findings.map(f => [f.idx, f]));
  const sorted = [...byIdx.values()].sort((a, b) => a.idx - b.idx);

  const verdict = (f: BibleFinding) =>
    f.complete.pass && f.accurate.pass && f.precise.pass
      ? 'PASS' : (f.loaded ? 'FLAG' : 'LOAD FAILED');

  const L: string[] = [];
  L.push('# Gold Re-Audit Report — Group G4 (Bibles 210, 212, 213)');
  L.push('');
  L.push(`**Date**: ${new Date().toISOString().slice(0, 19)}Z`);
  L.push('**Group**: G4');
  L.push('**Assigned**: Webster 1833 (210), Young\'s Literal (212), Julia Smith 1876 (213)');
  L.push('**Server**: ' + API_BASE);
  L.push('**Spec**: browser/e2e/gold_reaudit_G4.spec.ts');
  L.push('**Screenshots**: core/.scratch/gold-audit/reaudit-4a/G4/');
  L.push('');
  L.push('## Verdict Table');
  L.push('');
  L.push('| idx | Bible | Complete | Accurate | Precise | Overall |');
  L.push('|----:|-------|:--------:|:--------:|:-------:|:-------:|');
  for (const f of sorted) {
    L.push(
      `| ${f.idx} | ${f.label} ` +
      `| ${f.complete.pass ? 'PASS' : 'FLAG'} ` +
      `| ${f.accurate.pass ? 'PASS' : 'FLAG'} ` +
      `| ${f.precise.pass  ? 'PASS' : 'FLAG'} ` +
      `| ${verdict(f)} |`
    );
  }
  L.push('');

  // Defects table
  const allDefects: Array<{ idx: number; label: string } & BibleFinding['defects'][0]> = [];
  for (const f of sorted) {
    for (const d of f.defects)
      allDefects.push({ idx: f.idx, label: f.label, ...d });
  }
  if (allDefects.length > 0) {
    L.push('## Defects Found');
    L.push('');
    L.push('| idx | Bible | Severity | Description |');
    L.push('|----:|-------|:--------:|-------------|');
    for (const d of allDefects)
      L.push(`| ${d.idx} | ${d.label} | ${d.severity} | ${d.description} |`);
    L.push('');
  } else {
    L.push('## Defects Found');
    L.push('');
    L.push('_None found._');
    L.push('');
  }

  // Per-Bible detailed evidence
  L.push('---');
  L.push('');
  L.push('## Per-Bible Detailed Evidence');
  L.push('');

  for (const f of sorted) {
    L.push(`### [idx ${f.idx}] ${f.label} — ${verdict(f)}`);
    L.push('');
    L.push(`**Load**: ${f.loaded ? 'OK' : `FAILED — ${f.loadError}`}`);
    L.push('');

    L.push('#### Complete');
    L.push(`- **Result**: ${f.complete.pass ? 'PASS' : 'FLAG'}`);
    L.push(`- **Evidence**: ${f.complete.evidence}`);
    L.push('');

    L.push('#### Accurate');
    L.push(`- **Result**: ${f.accurate.pass ? 'PASS' : 'FLAG'}`);
    L.push(`- **Evidence**: ${f.accurate.evidence}`);
    L.push('');

    L.push('#### Precise');
    L.push(`- **Result**: ${f.precise.pass ? 'PASS' : 'FLAG'}`);
    L.push(`- **Evidence**: ${f.precise.evidence}`);
    L.push('');

    L.push('#### Live UI');
    L.push(`- Structure lane height: ${f.structH}px | Content lane height: ${f.contentH}px`);
    L.push(`- Browser char zoom: ${f.charsInView} chars in view, ${f.rects} SVG rects`);
    L.push(`- Reading masked tokens (sentence zoom): ${f.maskedTokens}`);
    L.push(`- JS errors: ${f.jsErrors.length}${f.jsErrors.length > 0 ? ' — ' + f.jsErrors.slice(0,3).join('; ') : ''}`);
    L.push('');

    if (f.defects.length > 0) {
      L.push('#### Defects');
      for (const d of f.defects)
        L.push(`- **${d.severity.toUpperCase()}**: ${d.description}`);
      L.push('');
    }

    L.push('#### Screenshots');
    for (const s of f.screenshots)
      L.push(`- \`G4/${s}\``);
    L.push('');
  }

  const reportPath = path.resolve(
    __dirname, '../../core/.scratch/gold-audit/reaudit-4a/report-G4.md'
  );
  fs.writeFileSync(reportPath, L.join('\n'));
  console.log(`\nG4 report written to: ${reportPath}`);
});
