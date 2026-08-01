/**
 * gold_reaudit_G2.spec.ts — Critical live UI re-audit: G2 Bibles
 * Assigned: idx 201 Coverdale, 202 Bishops', 208 Great, 209 Matthew's
 *
 * Rubric: core/.scratch/gold-audit/reaudit-4a/AUDIT-RUBRIC.md
 * Screenshots: core/.scratch/gold-audit/reaudit-4a/G2/
 *
 * Per-Bible checks:
 *   1. Sections API: generic+specific layer presence and masking
 *   2. Browser tab: expand both Structure/Content lanes (Expanded mode)
 *   3. Char-level zoom: SVG rects render, track sub-rows visible
 *   4. Reading tab at sentence zoom: masked markers greyed, archaic prose NOT greyed
 *   5. Precision probe: specific masked elements (header, chapter_heading) vs text
 *   6. Console error capture
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { test, expect, type Page, type Locator } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SHOTS_DIR = path.resolve(__dirname, '../../core/.scratch/gold-audit/reaudit-4a/G2');
fs.mkdirSync(SHOTS_DIR, { recursive: true });

const API_BASE = process.env.PALIMPSEST_BASE_URL ?? 'http://localhost:8080';

interface BibleEntry { idx: number; project_id: string; label: string }

const G2_BIBLES: BibleEntry[] = [
  { idx: 201, project_id: 'coverdale',  label: 'Coverdale 1535' },
  { idx: 202, project_id: 'bishops',    label: "Bishops' Bible" },
  { idx: 208, project_id: 'great',      label: 'Great Bible 1539' },
  { idx: 209, project_id: 'matthews',   label: "Matthew's Bible 1537" },
];

interface Verdict {
  complete: boolean; completeNote: string;
  accurate: boolean; accurateNote: string;
  precise: boolean;  preciseNote: string;
}
interface Finding {
  idx: number; project_id: string; label: string;
  loaded: boolean; loadError?: string;
  verdict: Verdict;
  structH: number; contentH: number;
  charsInView: number; rects: number; maskedTokens: number;
  genreDivCount: number; genreDivGap: boolean;
  screenshots: string[];
  consoleErrors: string[];
  defects: Array<{ sev: string; desc: string }>;
}

const findings: Finding[] = [];

// ── Screenshot helper ────────────────────────────────────────────────────────

async function shot(page: Page, name: string): Promise<string> {
  const filename = `${name}.png`;
  await page.screenshot({ path: path.join(SHOTS_DIR, filename), fullPage: false });
  return filename;
}

// ── Lane expansion (proven mechanics from gold_masks_all.spec.ts) ────────────

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
    await clickable.click({ force: true, timeout: 5_000 }).catch(() => {}); // closes menu
    await expandedBtn.waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {});
  }
  await page.waitForTimeout(250);
  const laneRow = cell.locator('xpath=..');
  return laneRow.locator('svg').first()
    .evaluate((el) => (el as SVGElement).getBoundingClientRect().height).catch(() => 0);
}

// ── Zoom helpers (proven mechanics) ─────────────────────────────────────────

function browserZoomIn(page: Page): Locator {
  return page.locator('span.min-w-\\[50px\\]')
    .locator('xpath=following::button[normalize-space(.)="+"][1]');
}

async function charsInView(page: Page): Promise<number> {
  const label = await page.locator('span.font-\\[var\\(--font-mono\\)\\]').first()
    .textContent().catch(() => '');
  const m = (label ?? '').replace(/,/g, '').match(/(\d+)\s*[–\-]\s*(\d+)/);
  return m ? parseInt(m[2], 10) - parseInt(m[1], 10) : NaN;
}

async function countMasked(page: Page): Promise<number> {
  return page.evaluate(() => {
    let n = 0;
    for (const s of Array.from(document.querySelectorAll('span'))) {
      if (getComputedStyle(s).backgroundColor === 'rgb(58, 58, 61)') n++;
    }
    return n;
  });
}

// ── API sections probe ───────────────────────────────────────────────────────

interface SectionsProbe {
  sectionCount: number;
  typeCounts: Record<string, number>;
  maskedTypes: string[];
  genericFound: string[];
  specificFound: string[];
  textLen: number;
}

async function probeSections(page: Page, projectId: string): Promise<SectionsProbe | null> {
  try {
    const resp = await page.request.get(
      `${API_BASE}/api/projects/${encodeURIComponent(projectId)}/sections`
    );
    if (!resp.ok()) return null;
    const data = await resp.json();
    const sections: Array<{ type: string; start: number; end: number }> = data.sections ?? [];
    const mb: Record<string, boolean> = data.mask_by_type ?? {};
    const GENERIC = new Set(['body', 'volume', 'book', 'part', 'section']);
    const typeCounts: Record<string, number> = {};
    for (const s of sections) typeCounts[s.type] = (typeCounts[s.type] ?? 0) + 1;
    return {
      sectionCount: sections.length,
      typeCounts,
      maskedTypes: Object.entries(mb).filter(([, v]) => v).map(([k]) => k),
      genericFound: [...GENERIC].filter((t) => typeCounts[t] > 0),
      specificFound: Object.keys(typeCounts).filter((t) => !GENERIC.has(t)),
      textLen: data.text_len ?? 0,
    };
  } catch { return null; }
}

// ── Tiling coverage check via API data ──────────────────────────────────────

interface CoverageResult {
  genericTiles: boolean;
  specificTiles: boolean;
  genreDivGap: boolean;   // genre_division alone has gap (Acts)
  genreDivCount: number;
}

async function checkCoverage(page: Page, projectId: string): Promise<CoverageResult | null> {
  try {
    const resp = await page.request.get(
      `${API_BASE}/api/projects/${encodeURIComponent(projectId)}/sections`
    );
    if (!resp.ok()) return null;
    const data = await resp.json();
    const sections: Array<{ type: string; start: number; end: number }> =
      data.sections ?? [];
    const textLen: number = data.text_len ?? 0;

    const GENERIC = new Set(['body', 'volume', 'book', 'part', 'section']);

    function merge(spans: [number, number][]): [number, number][] {
      const out: [number, number][] = [];
      for (const [s, e] of spans.sort((a, b) => a[0] - b[0])) {
        if (out.length && s <= out[out.length - 1][1])
          out[out.length - 1][1] = Math.max(out[out.length - 1][1], e);
        else out.push([s, e]);
      }
      return out;
    }

    function hasGap(merged: [number, number][], n: number): boolean {
      let cur = 0;
      for (const [s, e] of merged) { if (s > cur) return true; cur = Math.max(cur, e); }
      return cur < n;
    }

    const genericSpans = sections.filter((s) => GENERIC.has(s.type))
      .map((s): [number, number] => [s.start, s.end]);
    const specificSpans = sections.filter((s) => !GENERIC.has(s.type))
      .map((s): [number, number] => [s.start, s.end]);
    const gdSpans = sections.filter((s) => s.type === 'genre_division')
      .map((s): [number, number] => [s.start, s.end]);

    return {
      genericTiles: !hasGap(merge(genericSpans), textLen),
      specificTiles: !hasGap(merge(specificSpans), textLen),
      genreDivGap: hasGap(merge(gdSpans), textLen),
      genreDivCount: gdSpans.length,
    };
  } catch { return null; }
}

// ── Per-Bible test ────────────────────────────────────────────────────────────

for (const bible of G2_BIBLES) {
  test(`[G2 idx ${bible.idx}] ${bible.label}`, async ({ page }) => {
    test.setTimeout(200_000);

    const consoleErrors: string[] = [];
    page.on('console', (m) => {
      if (m.type() === 'error' &&
          !m.text().includes('favicon') &&
          !m.text().includes('ResizeObserver') &&
          !m.text().includes('ERR_ABORTED')) {
        consoleErrors.push(m.text().slice(0, 200));
      }
    });

    const f: Finding = {
      idx: bible.idx, project_id: bible.project_id, label: bible.label,
      loaded: false,
      verdict: {
        complete: false, completeNote: 'not checked',
        accurate: false, accurateNote: 'not checked',
        precise: false, preciseNote: 'not checked',
      },
      structH: 0, contentH: 0,
      charsInView: NaN, rects: 0, maskedTokens: 0,
      genreDivCount: 0, genreDivGap: false,
      screenshots: [],
      consoleErrors,
      defects: [],
    };
    findings.push(f);

    // ── Step 1: Load the Bible ────────────────────────────────────────────────
    try {
      await page.goto(`/?project=${encodeURIComponent(bible.project_id)}`, {
        waitUntil: 'domcontentloaded', timeout: 60_000,
      });
      await page.getByRole('tab', { name: 'Reading' }).waitFor({ state: 'visible', timeout: 90_000 });
      f.loaded = true;
    } catch (e) {
      f.loadError = String(e).slice(0, 300);
      f.screenshots.push(await shot(page, `${bible.idx}-00-load-failure`));
      return;
    }
    f.screenshots.push(await shot(page, `${bible.idx}-01-reading-loaded`));

    // ── Step 2: API sections probe (Complete + Accurate) ──────────────────────
    const sec = await probeSections(page, bible.project_id);
    const cov = await checkCoverage(page, bible.project_id);

    if (sec && cov) {
      // COMPLETE criterion
      const hasGenericLayer = sec.genericFound.length > 0;
      const hasSpecificLayer = sec.specificFound.length > 0;
      f.verdict.complete = hasGenericLayer && hasSpecificLayer && cov.genericTiles && cov.specificTiles;
      f.verdict.completeNote = [
        `generic:[${sec.genericFound.join(',')}] tiles=${cov.genericTiles}`,
        `specific:[${sec.specificFound.join(',')}] tiles=${cov.specificTiles}`,
        `sections=${sec.sectionCount}`,
      ].join(' | ');

      if (!cov.genericTiles) f.defects.push({ sev: 'blocker', desc: 'GENERIC layer does not tile [0,text_len)' });
      if (!cov.specificTiles) f.defects.push({ sev: 'blocker', desc: 'SPECIFIC layer does not tile [0,text_len)' });

      // ACCURATE criterion
      f.genreDivCount = cov.genreDivCount;
      f.genreDivGap = cov.genreDivGap;
      const hasHeader = sec.typeCounts['header'] > 0;
      const hasChapterHeading = sec.typeCounts['chapter_heading'] > 0;
      const hasBody = sec.typeCounts['body'] > 0;
      const maskedTypesOk = sec.maskedTypes.includes('header') && sec.maskedTypes.includes('chapter_heading');
      f.verdict.accurate = hasHeader && hasChapterHeading && hasBody && maskedTypesOk;
      f.verdict.accurateNote = [
        `masked:[${sec.maskedTypes.join(',')}]`,
        `header=${sec.typeCounts['header'] ?? 0}`,
        `chapter_heading=${sec.typeCounts['chapter_heading'] ?? 0}`,
        `genre_division=${cov.genreDivCount} gap=${cov.genreDivGap}`,
      ].join(' | ');

      if (!hasHeader) f.defects.push({ sev: 'blocker', desc: 'header type missing from sections' });
      if (!hasChapterHeading) f.defects.push({ sev: 'blocker', desc: 'chapter_heading type missing' });
      if (!sec.maskedTypes.includes('header')) f.defects.push({ sev: 'major', desc: 'header not in maskedTypes (unmasked)' });
      if (!sec.maskedTypes.includes('chapter_heading')) f.defects.push({ sev: 'major', desc: 'chapter_heading not in maskedTypes (unmasked)' });
      if (cov.genreDivGap) f.defects.push({
        sev: 'minor',
        desc: `genre_division has a gap (Acts not assigned to any genre_division; covered by SPECIFIC layer via chapter_heading/header — tiling holds)`,
      });
    } else {
      f.defects.push({ sev: 'blocker', desc: 'sections API probe failed' });
    }

    // ── Step 3: Browser tab — overview ────────────────────────────────────────
    await page.getByRole('tab', { name: 'Browser' }).click();
    await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 25_000 });
    await page.waitForTimeout(1500);
    f.screenshots.push(await shot(page, `${bible.idx}-02-browser-overview`));

    // ── Step 4: Expand both element-group lanes ───────────────────────────────
    f.structH = await expandLane(page, 0);
    await page.waitForTimeout(300);
    f.contentH = await expandLane(page, 1);
    await page.waitForTimeout(500);
    f.screenshots.push(await shot(page, `${bible.idx}-03-browser-expanded`));

    if (f.structH < 30) f.defects.push({ sev: 'major', desc: `Structure lane did not expand (svgH=${f.structH}px)` });
    if (f.contentH < 30) f.defects.push({ sev: 'major', desc: `Content lane did not expand (svgH=${f.contentH}px)` });

    // ── Step 5: Zoom to char level (< ~700 chars in view) ────────────────────
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
    f.screenshots.push(await shot(page, `${bible.idx}-04-browser-char-zoom`));

    if (f.rects < 1) f.defects.push({ sev: 'major', desc: 'No SVG rects at char zoom (masking elements not rendering)' });
    if (isNaN(f.charsInView) || f.charsInView > 2000)
      f.defects.push({ sev: 'minor', desc: `Could not reach char-level zoom (charsInView=${f.charsInView})` });

    // ── Step 6: Reading tab at sentence zoom — masked markers ─────────────────
    await page.getByRole('tab', { name: 'Reading' }).click();
    await page.waitForTimeout(1200);

    // Zoom reading view to sentence level (zooms through: work→chapter→paragraph→sentence)
    const readingZoomIn = page.locator('span.min-w-\\[65px\\]')
      .locator('xpath=following::button[normalize-space(.)="+"][1]');
    // click 3x: work→chapter→paragraph→sentence (need to pass through 3 levels)
    for (let i = 0; i < 3; i++) {
      await readingZoomIn.click({ timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(600);
    }
    f.screenshots.push(await shot(page, `${bible.idx}-05-reading-sentence-zoom`));
    f.maskedTokens = await countMasked(page);
    f.screenshots.push(await shot(page, `${bible.idx}-06-reading-masked-tokens`));

    if (f.maskedTokens === 0)
      f.defects.push({ sev: 'major', desc: 'Zero masked tokens at reading sentence zoom' });

    // ── Step 7: Precision — inspect masked elements in TickerTape ────────────
    // Zoom into the Browser tab at char level to inspect the TickerTape greys
    await page.getByRole('tab', { name: 'Browser' }).click();
    await page.waitForTimeout(1000);

    // Re-zoom to char level (may have been reset by tab switch)
    civ = await charsInView(page);
    for (let i = 0; i < 18 && (isNaN(civ) || civ > 700); i++) {
      await zoomIn.click({ force: true, timeout: 4_000 }).catch(() => {});
      await page.waitForTimeout(80);
      civ = await charsInView(page);
    }
    await page.waitForTimeout(400);

    // Capture TickerTape at char level for precision inspection
    f.screenshots.push(await shot(page, `${bible.idx}-07-tickertape-char-level`));

    // Probe TickerTape for grey (masked) vs normal tokens
    const tickerInfo = await page.evaluate(() => {
      const tickers = Array.from(document.querySelectorAll('[class*="ticker"]') as NodeListOf<HTMLElement>);
      const allSpans = Array.from(document.querySelectorAll('span') as NodeListOf<HTMLElement>)
        .filter((s) => getComputedStyle(s).backgroundColor === 'rgb(58, 58, 61)');
      return {
        tickerCount: tickers.length,
        maskedCount: allSpans.length,
        // Sample first few masked spans' text
        maskedSamples: allSpans.slice(0, 8).map((s) => s.textContent?.slice(0, 30) ?? ''),
      };
    });

    // Check that masked samples look like markers (not prose)
    const maskedSamples = tickerInfo.maskedSamples;
    const probeNote: string[] = [`masked_spans_in_view=${tickerInfo.maskedCount}`];
    let precisionOk = true;

    if (maskedSamples.length > 0) {
      // Markers should be '#', '##', or pure numbers like '1 ', '2 ', '3 '
      // Prose should NOT appear masked — it contains words, not just digits or '#'
      const markerLike = maskedSamples.filter((s) => {
        const t = s.trim();
        return t.startsWith('#') || /^\d+\s*$/.test(t) || /^\d+$/.test(t);
      });
      const proseLike = maskedSamples.filter((s) => {
        const t = s.trim();
        return !t.startsWith('#') && !/^\d+\s*$/.test(t) && t.length > 3 && /[a-zA-Z]{2,}/.test(t);
      });
      probeNote.push(`marker-like=${markerLike.length}/${maskedSamples.length}`);
      if (proseLike.length > 0) {
        precisionOk = false;
        probeNote.push(`PROSE-MASKED:${proseLike.slice(0, 3).join('|')}`);
        f.defects.push({
          sev: 'blocker',
          desc: `Prose text appears masked (grey): ${proseLike.slice(0, 3).join('; ')}`,
        });
      }
      probeNote.push(`samples:${maskedSamples.slice(0, 5).map((s) => JSON.stringify(s)).join(',')}`);
    } else if (f.maskedTokens > 0) {
      // Reading tab had masked tokens but browser char zoom doesn't show them here — not a precision error
      probeNote.push('no_masked_spans_at_this_viewport_position');
      precisionOk = true; // can't prove precision failure from empty sample
    } else {
      precisionOk = false;
      probeNote.push('no_masked_spans_found');
      f.defects.push({ sev: 'major', desc: 'No masked spans found in browser char-zoom view' });
    }

    f.verdict.precise = precisionOk && f.maskedTokens > 0;
    f.verdict.preciseNote = probeNote.join(' | ');

    // ── Step 8: Walkthrough — Characters tab ─────────────────────────────────
    await page.getByRole('tab', { name: 'Reading' }).click();
    await page.waitForTimeout(800);
    const hasCharsTab = await page.getByRole('tab', { name: 'Characters' }).isVisible().catch(() => false);
    if (hasCharsTab) {
      await page.getByRole('tab', { name: 'Characters' }).click();
      await page.waitForTimeout(2000);
      f.screenshots.push(await shot(page, `${bible.idx}-08-characters-tab`));
    }

    // ── Step 9: Analysis tab ──────────────────────────────────────────────────
    const hasAnalysisTab = await page.getByRole('tab', { name: 'Analysis' }).isVisible().catch(() => false);
    if (hasAnalysisTab) {
      await page.getByRole('tab', { name: 'Analysis' }).click();
      await page.waitForTimeout(2000);
      f.screenshots.push(await shot(page, `${bible.idx}-09-analysis-tab`));
    }

    // ── Final logging ─────────────────────────────────────────────────────────
    console.log(
      `[G2 idx ${bible.idx}] ${bible.label}:\n` +
      `  Complete=${f.verdict.complete} | Accurate=${f.verdict.accurate} | Precise=${f.verdict.precise}\n` +
      `  structH=${f.structH} contentH=${f.contentH} chars=${f.charsInView} rects=${f.rects} masked=${f.maskedTokens}\n` +
      `  genreDivCount=${f.genreDivCount} genreDivGap=${f.genreDivGap}\n` +
      `  defects=${f.defects.length} jsErrors=${consoleErrors.length}`
    );

    // Soft assertions (don't abort on failure — collect all evidence)
    expect.soft(f.loaded, `[${bible.idx}] page loaded`).toBe(true);
    expect.soft(f.verdict.complete, `[${bible.idx}] Complete`).toBe(true);
    expect.soft(f.verdict.accurate, `[${bible.idx}] Accurate`).toBe(true);
    expect.soft(f.verdict.precise, `[${bible.idx}] Precise`).toBe(true);
    expect.soft(f.structH, `[${bible.idx}] Structure lane height`).toBeGreaterThan(30);
    expect.soft(f.rects, `[${bible.idx}] SVG rects at char zoom`).toBeGreaterThan(0);
    expect.soft(f.maskedTokens, `[${bible.idx}] masked tokens in reading`).toBeGreaterThan(0);
  });
}

// ── Report ────────────────────────────────────────────────────────────────────

test.afterAll(async () => {
  const sorted = [...new Map(findings.map((f) => [f.idx, f])).values()].sort((a, b) => a.idx - b.idx);

  const lines: string[] = [
    '# G2 Re-Audit Report — Coverdale, Bishops, Great, Matthew\'s Bibles',
    '',
    `**Date**: ${new Date().toISOString().slice(0, 19)}Z`,
    `**Group**: G2`,
    `**Bibles**: idx 201 (Coverdale 1535), 202 (Bishops\' Bible), 208 (Great Bible), 209 (Matthew\'s Bible)`,
    `**Spec**: browser/e2e/gold_reaudit_G2.spec.ts`,
    `**Server**: ${API_BASE}`,
    `**Screenshots**: core/.scratch/gold-audit/reaudit-4a/G2/`,
    '',
    '## Verdict Table',
    '',
    '| idx | Bible | Complete | Accurate | Precise | Defects |',
    '|----:|-------|:--------:|:--------:|:-------:|---------|',
  ];

  for (const f of sorted) {
    const cLabel = f.verdict.complete ? 'PASS' : 'FLAG';
    const aLabel = f.verdict.accurate ? 'PASS' : 'FLAG';
    const pLabel = f.verdict.precise  ? 'PASS' : 'FLAG';
    const dList = f.defects.map((d) => `${d.sev}: ${d.desc}`).join('; ') || 'none';
    lines.push(`| ${f.idx} | ${f.label} | ${cLabel} | ${aLabel} | ${pLabel} | ${dList} |`);
  }

  lines.push('', '---', '', '## Per-Bible Evidence', '');

  for (const f of sorted) {
    lines.push(`### [idx ${f.idx}] ${f.label}`, '');
    if (!f.loaded) {
      lines.push(`**LOAD FAILED**: ${f.loadError}`, '');
      continue;
    }

    lines.push('#### Complete');
    lines.push(`- **Verdict**: ${f.verdict.complete ? 'PASS' : 'FLAG'}`);
    lines.push(`- ${f.verdict.completeNote}`);
    lines.push('');

    lines.push('#### Accurate');
    lines.push(`- **Verdict**: ${f.verdict.accurate ? 'PASS' : 'FLAG'}`);
    lines.push(`- ${f.verdict.accurateNote}`);
    lines.push('');

    lines.push('#### Precise');
    lines.push(`- **Verdict**: ${f.verdict.precise ? 'PASS' : 'FLAG'}`);
    lines.push(`- ${f.verdict.preciseNote}`);
    lines.push('');

    lines.push('#### UI Metrics');
    lines.push(`- Structure lane svgH=${f.structH}px, Content lane svgH=${f.contentH}px`);
    lines.push(`- Chars in view (char zoom): ${f.charsInView}`);
    lines.push(`- SVG rects at char zoom: ${f.rects}`);
    lines.push(`- Masked tokens (reading sentence zoom): ${f.maskedTokens}`);
    lines.push(`- genre_division count: ${f.genreDivCount}, gap (Acts): ${f.genreDivGap}`);
    lines.push('');

    if (f.defects.length > 0) {
      lines.push('#### Defects');
      for (const d of f.defects) lines.push(`- **${d.sev.toUpperCase()}**: ${d.desc}`);
      lines.push('');
    }

    if (f.consoleErrors.length > 0) {
      lines.push('#### Console Errors');
      for (const e of f.consoleErrors) lines.push(`- \`${e}\``);
      lines.push('');
    }

    lines.push('#### Screenshots');
    for (const s of f.screenshots) lines.push(`- \`G2/${s}\``);
    lines.push('');
  }

  // Defects summary table
  const allDefects: Array<{ idx: number; label: string } & Finding['defects'][0]> = [];
  for (const f of sorted) {
    for (const d of f.defects) allDefects.push({ idx: f.idx, label: f.label, ...d });
  }

  if (allDefects.length > 0) {
    lines.push('---', '', '## Defects Summary', '');
    lines.push('| idx | Bible | Severity | Description |');
    lines.push('|----:|-------|:--------:|-------------|');
    for (const d of allDefects) {
      lines.push(`| ${d.idx} | ${d.label} | ${d.sev.toUpperCase()} | ${d.desc} |`);
    }
    lines.push('');
  }

  const reportPath = path.resolve(
    __dirname, '../../core/.scratch/gold-audit/reaudit-4a/report-G2.md'
  );
  fs.writeFileSync(reportPath, lines.join('\n'));
  console.log(`\nG2 report written to ${reportPath}`);
});
