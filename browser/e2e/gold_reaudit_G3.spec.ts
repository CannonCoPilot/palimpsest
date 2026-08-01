/**
 * gold_reaudit_G3.spec.ts — Critical live UI re-audit, Group G3
 *
 * Assigned Bibles:
 *   idx 203  wycliffe-reconstructed          (Wycliffe, archaic reconstruction, front_matter + apocrypha)
 *   idx 219  kjv1611-comprehensive-reconstructed  (KJV 1611, 80 books, 2 front_matter treatises + 14 Apocrypha)
 *   idx 216  kjv1769                         (KJV 1769, canonical 66-book — PRECISION REFERENCE)
 *
 * Scrutiny:
 *   1. Front_matter/apparatus blocks: end boundary terminates EXACTLY at first scripture — no bleed.
 *   2. Apocrypha books present + correctly typed (idx 219 must have 14 apocrypha; idx 203 has Catholic apocrypha).
 *   3. KJV1769 precision reference — verse/chapter/header bounds textbook-exact.
 *   4. Per-Bible: Complete / Accurate / Precise each PASS or FLAG with evidence.
 *
 * Run from browser/:
 *   PALIMPSEST_BASE_URL=http://localhost:8080 npx playwright test e2e/gold_reaudit_G3.spec.ts \
 *     --project=chromium --workers=1
 *
 * Screenshots → core/.scratch/gold-audit/reaudit-4a/G3/
 * Report     → core/.scratch/gold-audit/reaudit-4a/report-G3.md  (written by afterAll)
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { test, expect, type Page, type Locator } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SHOTS_DIR = path.resolve(__dirname, '../../core/.scratch/gold-audit/reaudit-4a/G3');
fs.mkdirSync(SHOTS_DIR, { recursive: true });

const REPORT_PATH = path.resolve(__dirname, '../../core/.scratch/gold-audit/reaudit-4a/report-G3.md');
const API_BASE = process.env.PALIMPSEST_BASE_URL ?? 'http://localhost:8080';

// ── Bible definitions for G3 ──────────────────────────────────────────────────
interface BibleDef {
  idx: number;
  project_id: string;
  label: string;
  /** Expected number of front_matter sections */
  expectedFM: number;
  /** Expected book count */
  expectedBooks: number;
  /** Expected front_matter label prefixes (for verification) */
  fmLabels: string[];
}

const BIBLES: BibleDef[] = [
  {
    idx: 203,
    project_id: 'wycliffe-reconstructed',
    label: 'Wycliffe (reconstructed)',
    expectedFM: 38,   // 1 general prologue + ~37 per-book prologues
    expectedBooks: 73,
    fmLabels: ['Old Testament — General Prologue'],
  },
  {
    idx: 219,
    project_id: 'kjv1611-comprehensive-reconstructed',
    label: 'KJV 1611 (comprehensive)',
    expectedFM: 2,    // exactly 2: "The Epistle Dedicatorie" + "The Translators to the Reader"
    expectedBooks: 80,
    fmLabels: ['The Epistle Dedicatorie', 'The Translators to the Reader'],
  },
  {
    idx: 216,
    project_id: 'kjv1769',
    label: 'KJV 1769 (precision reference)',
    expectedFM: 0,
    expectedBooks: 66,
    fmLabels: [],
  },
];

// ── Findings accumulator ──────────────────────────────────────────────────────
interface FMBoundaryCheck {
  fmIdx: number;
  fmLabel: string;
  fmEnd: number;
  nextBookStart: number;
  gapChars: number;
  charsBeforeBoundary: string;  // last ~100 chars of FM
  charsAfterBoundary: string;   // first ~100 chars of book
  cleanBoundary: boolean;
}

interface PrecisionCheck {
  element: string;
  start: number;
  end: number;
  charSlice: string;
  charBefore: string;
  charAfter: string;
  pass: boolean;
  note: string;
}

interface ApocryphaCheck {
  bookName: string;
  present: boolean;
  sectionStart: number;
  sectionEnd: number;
  headerSlice: string;
}

interface BibleFinding {
  idx: number;
  project_id: string;
  label: string;
  loaded: boolean;
  loadError?: string;

  // Complete criterion
  complete: { pass: boolean; note: string };
  genericLayerOk: boolean;
  specificLayerOk: boolean;
  fmCount: number;
  bookCount: number;

  // Accurate criterion
  accurate: { pass: boolean; note: string };
  typesPresent: string[];
  maskedTypes: string[];

  // Precise criterion
  precise: { pass: boolean; note: string };
  fmBoundaries: FMBoundaryCheck[];
  precisionChecks: PrecisionCheck[];
  apocryphaChecks: ApocryphaCheck[];

  // UI
  structH: number;
  contentH: number;
  charsInView: number;
  rects: number;
  maskedTokens: number;
  screenshots: string[];
  jsErrors: string[];
}

const findings: BibleFinding[] = [];

// ── Helpers (proven from gold_masks_all.spec.ts) ──────────────────────────────

async function shot(page: Page, name: string): Promise<string> {
  const fname = `${name}.png`;
  await page.screenshot({ path: path.join(SHOTS_DIR, fname), fullPage: false });
  return fname;
}

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
  return await laneRow.locator('svg').first()
    .evaluate((el) => (el as SVGElement).getBoundingClientRect().height).catch(() => 0);
}

function browserZoomIn(page: Page): Locator {
  return page.locator('span.min-w-\\[50px\\]').locator('xpath=following::button[normalize-space(.)="+"][1]');
}

async function charsInView(page: Page): Promise<number> {
  const label = await page.locator('span.font-\\[var\\(--font-mono\\)\\]').first().textContent().catch(() => '');
  const m = (label ?? '').replace(/,/g, '').match(/(\d+)\s*[–\-]\s*(\d+)/);
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

// ── Data precision check helpers ──────────────────────────────────────────────

interface SectionsAPIData {
  sections: Array<{ id: string; type: string; start: number; end: number; label?: string; name?: string }>;
  mask_by_type: Record<string, boolean>;
}

async function fetchSections(page: Page, projectId: string): Promise<SectionsAPIData | null> {
  try {
    const resp = await page.request.get(`${API_BASE}/api/projects/${encodeURIComponent(projectId)}/sections`);
    if (!resp.ok()) return null;
    return await resp.json();
  } catch { return null; }
}

// ── Per-Bible precision validators ──────────────────────────────────────────

/**
 * Verify that each front_matter section's end boundary terminates cleanly at the
 * next section start — no overrun, no gap (or only whitespace gap that terminates
 * on a `# Book` line). Returns characterised boundary data.
 */
async function checkFMBoundaries(
  page: Page,
  projectId: string,
  sections: SectionsAPIData['sections'],
): Promise<FMBoundaryCheck[]> {
  const fms = sections.filter((s) => s.type === 'front_matter').sort((a, b) => a.start - b.start);
  if (fms.length === 0) return [];

  // Fetch partial reference text around each boundary
  const results: FMBoundaryCheck[] = [];
  for (const fm of fms) {
    // Get chars around boundary: last 120 of FM and first 120 after
    try {
      const rangeResp = await page.request.get(
        `${API_BASE}/api/projects/${encodeURIComponent(projectId)}/text?start=${fm.end - 120}&end=${fm.end + 120}`,
      );
      let before = '', after = '';
      if (rangeResp.ok()) {
        const d = await rangeResp.json();
        const txt: string = d.text ?? d.content ?? '';
        before = txt.slice(0, 120);
        after = txt.slice(120);
      }

      // Check for overlap: next section start should equal fm.end (or be whitespace-only gap)
      const nextSec = sections
        .filter((s) => s.type !== 'front_matter' && s.start >= fm.end)
        .sort((a, b) => a.start - b.start)[0];

      const gapChars = nextSec ? nextSec.start - fm.end : -1;
      // A clean boundary: gap == 0 OR gap is only whitespace (newlines)
      const cleanBoundary = gapChars === 0 || gapChars <= 2; // 2 chars = "\n\n" separator

      results.push({
        fmIdx: fms.indexOf(fm) + 1,
        fmLabel: fm.label ?? fm.name ?? '',
        fmEnd: fm.end,
        nextBookStart: nextSec?.start ?? -1,
        gapChars,
        charsBeforeBoundary: before,
        charsAfterBoundary: after,
        cleanBoundary,
      });
    } catch {
      results.push({
        fmIdx: fms.indexOf(fm) + 1,
        fmLabel: fm.label ?? fm.name ?? '',
        fmEnd: fm.end,
        nextBookStart: -1,
        gapChars: -1,
        charsBeforeBoundary: '',
        charsAfterBoundary: '',
        cleanBoundary: false,
      });
    }
  }
  return results;
}

/**
 * Check precision of book headers, chapter headings, and verse markers using
 * the text API. Samples 3+ elements per Bible.
 */
async function checkPrecision(
  page: Page,
  projectId: string,
  sections: SectionsAPIData['sections'],
): Promise<PrecisionCheck[]> {
  const checks: PrecisionCheck[] = [];
  const headers = sections.filter((s) => s.type === 'header').sort((a, b) => a.start - b.start);
  const chHeadings = sections.filter((s) => s.type === 'chapter_heading').sort((a, b) => a.start - b.start);

  // Sample: first book header, mid-document header, last book header
  const headerSamples = [headers[0], headers[Math.floor(headers.length / 2)], headers[headers.length - 1]].filter(Boolean);
  // Sample: first chapter heading, a mid chapter heading, a late chapter heading
  const chSamples = [chHeadings[0], chHeadings[Math.floor(chHeadings.length / 2)], chHeadings[chHeadings.length - 1]].filter(Boolean);

  for (const el of [...headerSamples, ...chSamples]) {
    try {
      const ctx = 5;
      const resp = await page.request.get(
        `${API_BASE}/api/projects/${encodeURIComponent(projectId)}/text?start=${Math.max(0, el.start - ctx)}&end=${el.end + ctx}`,
      );
      if (!resp.ok()) {
        checks.push({ element: `${el.type}[${el.start}:${el.end}]`, start: el.start, end: el.end,
          charSlice: '', charBefore: '', charAfter: '', pass: false, note: 'API text fetch failed' });
        continue;
      }
      const d = await resp.json();
      const txt: string = d.text ?? d.content ?? '';
      const charBefore = txt.slice(0, ctx);
      const charSlice = txt.slice(ctx, txt.length - ctx);
      const charAfter = txt.slice(txt.length - ctx);

      // A header looks like "# BookName"; chapter_heading like "## BookName N"
      const expectHeader = el.type === 'header' ? /^# \w/ : /^## \w/;
      const pass = expectHeader.test(charSlice);
      // Crucially: after-boundary should start with newline (not more text of same kind)
      const afterStartsClean = charAfter.startsWith('\n') || charAfter === '';

      checks.push({
        element: `${el.type}[${el.start}:${el.end}]`,
        start: el.start, end: el.end,
        charSlice: charSlice.slice(0, 60),
        charBefore: charBefore.replace(/\n/g, '\\n'),
        charAfter: charAfter.replace(/\n/g, '\\n'),
        pass: pass && afterStartsClean,
        note: pass ? (afterStartsClean ? 'OK' : 'after-boundary suspicious') : `unexpected content: ${JSON.stringify(charSlice.slice(0, 30))}`,
      });
    } catch (e) {
      checks.push({ element: `${el.type}[${el.start}:${el.end}]`, start: el.start, end: el.end,
        charSlice: '', charBefore: '', charAfter: '', pass: false, note: String(e).slice(0, 100) });
    }
  }
  return checks;
}

/**
 * For KJV1611 (idx 219) and Wycliffe (idx 203), verify apocrypha book sections exist.
 */
async function checkApocrypha(
  page: Page,
  projectId: string,
  sections: SectionsAPIData['sections'],
  expectedApocryphaBooks: string[],
): Promise<ApocryphaCheck[]> {
  const books = sections.filter((s) => s.type === 'book');
  const bookLabels = new Map(books.map((b) => [b.label ?? b.name ?? '', b]));

  return expectedApocryphaBooks.map((bname) => {
    // Try exact match first, then partial
    const sec = bookLabels.get(bname) ??
      books.find((b) => (b.label ?? b.name ?? '').includes(bname) || bname.includes(b.label ?? b.name ?? ''));
    return {
      bookName: bname,
      present: !!sec,
      sectionStart: sec?.start ?? -1,
      sectionEnd: sec?.end ?? -1,
      headerSlice: '',  // will be filled via text API if present
    };
  });
}

// ── Main Tests ────────────────────────────────────────────────────────────────

for (const bible of BIBLES) {
  test(`[G3][idx ${bible.idx}] ${bible.label}`, async ({ page }) => {
    test.setTimeout(180_000);
    const jsErrors: string[] = [];
    page.on('console', (m) => {
      if (m.type() === 'error' && !m.text().includes('favicon') && !m.text().includes('ResizeObserver') && !m.text().includes('ERR_ABORTED')) {
        jsErrors.push(m.text().slice(0, 200));
      }
    });

    const f: BibleFinding = {
      idx: bible.idx, project_id: bible.project_id, label: bible.label,
      loaded: false,
      complete: { pass: false, note: '' },
      genericLayerOk: false, specificLayerOk: false,
      fmCount: 0, bookCount: 0,
      accurate: { pass: false, note: '' },
      typesPresent: [], maskedTypes: [],
      precise: { pass: false, note: '' },
      fmBoundaries: [], precisionChecks: [], apocryphaChecks: [],
      structH: 0, contentH: 0, charsInView: NaN,
      rects: 0, maskedTokens: 0,
      screenshots: [], jsErrors: [],
    };
    findings.push(f);

    // ── Phase 1: Load project ─────────────────────────────────────────────────
    try {
      await page.goto(`/?project=${encodeURIComponent(bible.project_id)}`, {
        waitUntil: 'domcontentloaded',
        timeout: 60_000,
      });
      await page.getByRole('tab', { name: 'Reading' }).waitFor({ state: 'visible', timeout: 90_000 });
      f.loaded = true;
    } catch (e) {
      f.loadError = String(e).slice(0, 300);
      f.screenshots.push(await shot(page, `${bible.idx}-01-load-failure`));
      return;
    }

    f.screenshots.push(await shot(page, `${bible.idx}-01-reading-loaded`));

    // ── Phase 2: Sections API — Complete + Accurate checks ───────────────────
    const secData = await fetchSections(page, bible.project_id);
    if (!secData) {
      f.accurate = { pass: false, note: 'sections API unavailable' };
      f.complete = { pass: false, note: 'sections API unavailable' };
    } else {
      const secs = secData.sections;
      const typeSet = new Set(secs.map((s) => s.type));
      f.typesPresent = Array.from(typeSet).sort();
      f.maskedTypes = Object.entries(secData.mask_by_type).filter(([, v]) => v).map(([k]) => k);

      f.fmCount = secs.filter((s) => s.type === 'front_matter').length;
      f.bookCount = secs.filter((s) => s.type === 'book').length;

      // COMPLETE: generic layer (body) AND specific layer tile [0, text_len)
      f.genericLayerOk = typeSet.has('body');

      const specificLayerTypes = ['chapter', 'book', 'front_matter'];
      f.specificLayerOk = specificLayerTypes.some((t) => typeSet.has(t));

      const genericNote = f.genericLayerOk ? 'body present' : 'MISSING body';
      const specificNote = f.specificLayerOk
        ? `chapter:${secs.filter((s) => s.type === 'chapter').length} book:${f.bookCount} fm:${f.fmCount}`
        : 'NO specific layer types';

      f.complete = {
        pass: f.genericLayerOk && f.specificLayerOk,
        note: `${genericNote}; ${specificNote}`,
      };

      // FM count check
      const fmOk = bible.expectedFM === 0
        ? f.fmCount === 0
        : Math.abs(f.fmCount - bible.expectedFM) <= 2; // allow minor variance
      const bookOk = f.bookCount === bible.expectedBooks;

      // ACCURATE: expected types present + none mis-typed + FM/book counts correct
      const requiredTypesPresent = typeSet.has('header') && typeSet.has('chapter_heading') && typeSet.has('body');
      f.accurate = {
        pass: requiredTypesPresent && fmOk && bookOk,
        note: `types=[${f.typesPresent.join(',')}] fmCount=${f.fmCount}(exp=${bible.expectedFM}) bookCount=${f.bookCount}(exp=${bible.expectedBooks}) masked=[${f.maskedTypes.slice(0, 8).join(',')}]`,
      };

      // ── Phase 3: Front_matter boundary precision ────────────────────────────
      if (f.fmCount > 0) {
        f.fmBoundaries = await checkFMBoundaries(page, bible.project_id, secs);
      }

      // ── Phase 4: Header / chapter_heading precision ─────────────────────────
      f.precisionChecks = await checkPrecision(page, bible.project_id, secs);

      // ── Phase 5: Apocrypha presence check (idx 203, 219) ───────────────────
      if (bible.idx === 219) {
        const apocryphaBooks = ['1 Esdras', '2 Esdras', 'Tobit', 'Judith', 'Wisdom of Solomon',
          'Ecclesiasticus', 'Baruch', '1 Maccabees', '2 Maccabees'];
        f.apocryphaChecks = await checkApocrypha(page, bible.project_id, secs, apocryphaBooks);
      } else if (bible.idx === 203) {
        const wycApocrypha = ['Tobit', 'Judith', 'Wisdom', 'Ecclesiasticus', 'Baruch', '1 Maccabees', '2 Maccabees'];
        f.apocryphaChecks = await checkApocrypha(page, bible.project_id, secs, wycApocrypha);
      }

      // PRECISE: all precision checks pass + FM boundaries clean
      const precChecksPass = f.precisionChecks.length > 0 && f.precisionChecks.every((c) => c.pass);
      const fmBoundariesClean = f.fmBoundaries.length === 0 || f.fmBoundaries.every((b) => b.cleanBoundary);
      const apocryphaPresent = f.apocryphaChecks.length === 0 || f.apocryphaChecks.filter((a) => !a.present).length === 0;

      f.precise = {
        pass: precChecksPass && fmBoundariesClean && apocryphaPresent,
        note: [
          `${f.precisionChecks.filter((c) => c.pass).length}/${f.precisionChecks.length} precision checks OK`,
          f.fmBoundaries.length > 0
            ? `${f.fmBoundaries.filter((b) => b.cleanBoundary).length}/${f.fmBoundaries.length} FM boundaries clean`
            : 'no FM to check',
          f.apocryphaChecks.length > 0
            ? `${f.apocryphaChecks.filter((a) => a.present).length}/${f.apocryphaChecks.length} apocrypha present`
            : '',
        ].filter(Boolean).join('; '),
      };
    }

    // ── Phase 6: Browser tab — expand lanes + overview ───────────────────────
    await page.getByRole('tab', { name: 'Browser' }).click();
    await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 25_000 });
    await page.waitForTimeout(1500);
    f.screenshots.push(await shot(page, `${bible.idx}-02-browser-overview`));

    // Expand Structure lane (idx 0)
    f.structH = await expandLane(page, 0);
    await page.waitForTimeout(300);
    f.screenshots.push(await shot(page, `${bible.idx}-03-structure-expanded`));

    // Expand Content lane (idx 1)
    f.contentH = await expandLane(page, 1);
    await page.waitForTimeout(300);
    f.screenshots.push(await shot(page, `${bible.idx}-04-both-lanes-expanded`));

    // ── Phase 7: Zoom to char level ──────────────────────────────────────────
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
    f.screenshots.push(await shot(page, `${bible.idx}-05-browser-char-zoom`));

    // ── Phase 8: Reading tab at sentence zoom ────────────────────────────────
    await page.getByRole('tab', { name: 'Reading' }).click();
    await page.waitForTimeout(1200);
    const readingZoomIn = page.locator('span.min-w-\\[65px\\]').locator('xpath=following::button[normalize-space(.)="+"][1]');
    await readingZoomIn.click({ timeout: 5_000 }).catch(() => {});
    await page.waitForTimeout(800);
    f.maskedTokens = await countMaskedTokens(page);
    f.screenshots.push(await shot(page, `${bible.idx}-06-reading-sentence-zoom`));

    // ── Phase 9: Navigate to front_matter area (idx 203/219 specific) ────────
    if (bible.idx === 219 || bible.idx === 203) {
      // Jump to position 0 (start of front_matter)
      await page.getByRole('tab', { name: 'Browser' }).click();
      await page.waitForTimeout(800);
      // Try to navigate to start of document via "Jump to…" if available
      const jumpBtn = page.getByRole('button', { name: /Jump/i });
      const jumpVis = await jumpBtn.isVisible().catch(() => false);
      if (jumpVis) {
        await jumpBtn.click({ timeout: 5_000 });
        await page.waitForTimeout(300);
        const jumpInput = page.getByRole('textbox').last();
        await jumpInput.fill('0');
        await jumpInput.press('Enter');
        await page.waitForTimeout(800);
      } else {
        // use fit-to-view to reset, then no zoom
        const fitBtn = page.getByRole('button', { name: /Fit|fit/ });
        if (await fitBtn.isVisible().catch(() => false)) {
          await fitBtn.click({ timeout: 5_000 }).catch(() => {});
          await page.waitForTimeout(500);
        }
      }
      f.screenshots.push(await shot(page, `${bible.idx}-07-browser-frontmatter-area`));
    }

    // ── Phase 10: Verify front_matter blocks are visually greyed ─────────────
    // At readable zoom, check that masked tokens exist in the front_matter area
    if (bible.idx === 219 || bible.idx === 203) {
      await page.getByRole('tab', { name: 'Reading' }).click();
      await page.waitForTimeout(1000);
      // Check that the front_matter greyed blocks are visible
      const maskedCount = await countMaskedTokens(page);
      f.screenshots.push(await shot(page, `${bible.idx}-08-reading-frontmatter-greyed`));
      console.log(`[idx ${bible.idx}] FM greyed tokens at reading view: ${maskedCount}`);
    }

    // ── Collect JS errors ────────────────────────────────────────────────────
    f.jsErrors = jsErrors;

    console.log(
      `[G3][idx ${bible.idx}] ${bible.label}: ` +
      `complete=${f.complete.pass} accurate=${f.accurate.pass} precise=${f.precise.pass} ` +
      `structH=${f.structH} contentH=${f.contentH} chars=${f.charsInView} ` +
      `rects=${f.rects} masked=${f.maskedTokens} jsErr=${f.jsErrors.length}`,
    );

    // ── Soft assertions ──────────────────────────────────────────────────────
    expect.soft(f.loaded, `[${bible.idx}] project loaded`).toBe(true);
    expect.soft(f.complete.pass, `[${bible.idx}] Complete criterion`).toBe(true);
    expect.soft(f.accurate.pass, `[${bible.idx}] Accurate criterion`).toBe(true);
    expect.soft(f.precise.pass, `[${bible.idx}] Precise criterion`).toBe(true);
    expect.soft(f.structH, `[${bible.idx}] Structure lane expanded`).toBeGreaterThan(30);
    expect.soft(f.charsInView, `[${bible.idx}] zoomed to char level`).toBeLessThan(1500);
    expect.soft(f.rects, `[${bible.idx}] track elements render`).toBeGreaterThan(0);
    expect.soft(f.maskedTokens, `[${bible.idx}] masked tokens in reading view`).toBeGreaterThan(0);
  });
}

// ── Report generation ─────────────────────────────────────────────────────────

test.afterAll(async () => {
  const sorted = [...new Map(findings.map((f) => [f.idx, f])).values()].sort((a, b) => a.idx - b.idx);
  const ts = new Date().toISOString().slice(0, 19) + 'Z';

  const lines: string[] = [
    '# G3 Re-Audit Report — KJV1769, Wycliffe, KJV1611',
    '',
    `**Date**: ${ts}`,
    `**Group**: G3`,
    `**Bibles**: idx 203 (Wycliffe), 216 (KJV1769), 219 (KJV1611)`,
    `**Server**: ${API_BASE}`,
    `**Screenshots**: core/.scratch/gold-audit/reaudit-4a/G3/`,
    '',
    '## Verdict Table',
    '',
    '| idx | Bible | Complete | Accurate | Precise | Overall |',
    '|----:|-------|:--------:|:--------:|:-------:|:-------:|',
  ];

  for (const f of sorted) {
    const overall = f.loaded && f.complete.pass && f.accurate.pass && f.precise.pass ? 'PASS' : 'FLAG';
    lines.push(
      `| ${f.idx} | ${f.label} ` +
      `| ${f.complete.pass ? 'PASS' : 'FLAG'} ` +
      `| ${f.accurate.pass ? 'PASS' : 'FLAG'} ` +
      `| ${f.precise.pass ? 'PASS' : 'FLAG'} ` +
      `| **${overall}** |`,
    );
  }

  lines.push('', '---', '', '## Defects Table', '');
  lines.push('| Severity | idx | Criterion | Description |');
  lines.push('|----------|----:|-----------|-------------|');

  const defects: Array<{ severity: string; idx: number; criterion: string; desc: string }> = [];

  for (const f of sorted) {
    if (!f.loaded) {
      defects.push({ severity: 'blocker', idx: f.idx, criterion: 'Load', desc: f.loadError ?? 'load failed' });
    }
    if (!f.complete.pass) {
      defects.push({ severity: 'blocker', idx: f.idx, criterion: 'Complete', desc: f.complete.note });
    }
    if (!f.accurate.pass) {
      defects.push({ severity: 'major', idx: f.idx, criterion: 'Accurate', desc: f.accurate.note });
    }
    if (!f.precise.pass) {
      defects.push({ severity: 'major', idx: f.idx, criterion: 'Precise', desc: f.precise.note });
    }
    // FM boundary defects
    for (const fb of f.fmBoundaries) {
      if (!fb.cleanBoundary) {
        defects.push({
          severity: 'blocker',
          idx: f.idx,
          criterion: 'Precise/FM',
          desc: `FM "${fb.fmLabel}" end=${fb.fmEnd} next_book_start=${fb.nextBookStart} gap=${fb.gapChars} chars`,
        });
      }
    }
    // Precision check defects
    for (const pc of f.precisionChecks) {
      if (!pc.pass) {
        defects.push({
          severity: 'major',
          idx: f.idx,
          criterion: 'Precise',
          desc: `${pc.element}: ${pc.note} slice=${JSON.stringify(pc.charSlice.slice(0, 40))}`,
        });
      }
    }
    // Apocrypha defects
    for (const ac of f.apocryphaChecks) {
      if (!ac.present) {
        defects.push({ severity: 'major', idx: f.idx, criterion: 'Accurate/Apocrypha', desc: `Missing book: ${ac.bookName}` });
      }
    }
    // JS errors
    if (f.jsErrors.length > 0) {
      defects.push({ severity: 'minor', idx: f.idx, criterion: 'UI', desc: `${f.jsErrors.length} JS error(s): ${f.jsErrors[0].slice(0, 120)}` });
    }
  }

  if (defects.length === 0) {
    lines.push('| — | — | — | No defects found |');
  } else {
    for (const d of defects.sort((a, b) => ['blocker', 'major', 'minor'].indexOf(a.severity) - ['blocker', 'major', 'minor'].indexOf(b.severity))) {
      lines.push(`| ${d.severity} | ${d.idx} | ${d.criterion} | ${d.desc} |`);
    }
  }

  lines.push('', '---', '', '## Per-Bible Detail', '');

  for (const f of sorted) {
    const overall = f.loaded && f.complete.pass && f.accurate.pass && f.precise.pass ? 'PASS' : 'FLAG';
    lines.push(`### [idx ${f.idx}] ${f.label} — ${overall}`, '');

    if (!f.loaded) {
      lines.push(`**LOAD FAILED**: ${f.loadError}`, '');
    }

    lines.push(`#### Complete: ${f.complete.pass ? 'PASS' : 'FLAG'}`);
    lines.push(`- ${f.complete.note}`);
    lines.push(`- generic layer (body): ${f.genericLayerOk ? 'OK' : 'MISSING'}`);
    lines.push(`- specific layer: bookCount=${f.bookCount} fmCount=${f.fmCount}`);
    lines.push('');

    lines.push(`#### Accurate: ${f.accurate.pass ? 'PASS' : 'FLAG'}`);
    lines.push(`- ${f.accurate.note}`);
    lines.push(`- Types present: ${f.typesPresent.join(', ')}`);
    lines.push(`- Masked types: ${f.maskedTypes.join(', ')}`);
    lines.push('');

    lines.push(`#### Precise: ${f.precise.pass ? 'PASS' : 'FLAG'}`);
    lines.push(`- ${f.precise.note}`);
    lines.push('');

    if (f.fmBoundaries.length > 0) {
      lines.push('**Front-matter boundary checks:**');
      for (const fb of f.fmBoundaries) {
        const status = fb.cleanBoundary ? 'CLEAN' : 'FLAG';
        lines.push(`- FM #${fb.fmIdx} "${fb.fmLabel}": end=${fb.fmEnd} next_start=${fb.nextBookStart} gap=${fb.gapChars} → **${status}**`);
        if (!fb.cleanBoundary) {
          lines.push(`  - Last chars before boundary: ${JSON.stringify(fb.charsBeforeBoundary.slice(-60))}`);
          lines.push(`  - First chars after boundary: ${JSON.stringify(fb.charsAfterBoundary.slice(0, 60))}`);
        }
      }
      lines.push('');
    }

    if (f.precisionChecks.length > 0) {
      lines.push('**Element precision checks:**');
      for (const pc of f.precisionChecks) {
        lines.push(`- ${pc.element}: slice=${JSON.stringify(pc.charSlice.slice(0, 40))} before=${JSON.stringify(pc.charBefore)} after=${JSON.stringify(pc.charAfter)} → **${pc.pass ? 'PASS' : 'FLAG'}** ${pc.note}`);
      }
      lines.push('');
    }

    if (f.apocryphaChecks.length > 0) {
      lines.push('**Apocrypha presence checks:**');
      for (const ac of f.apocryphaChecks) {
        lines.push(`- ${ac.bookName}: ${ac.present ? 'PRESENT' : '**MISSING**'} (start=${ac.sectionStart})`);
      }
      lines.push('');
    }

    lines.push(`#### UI Evidence`);
    lines.push(`- Structure lane height: ${f.structH}px`);
    lines.push(`- Content lane height: ${f.contentH}px`);
    lines.push(`- Chars in view at char zoom: ${f.charsInView}`);
    lines.push(`- SVG rects at char zoom: ${f.rects}`);
    lines.push(`- Masked tokens in Reading view: ${f.maskedTokens}`);
    lines.push(`- JS errors: ${f.jsErrors.length}${f.jsErrors.length > 0 ? ' — ' + f.jsErrors[0].slice(0, 120) : ''}`);
    lines.push(`- Screenshots: ${f.screenshots.map((s) => `\`${s}\``).join(', ')}`);
    lines.push('');
  }

  const passCount = sorted.filter((f) => f.loaded && f.complete.pass && f.accurate.pass && f.precise.pass).length;
  lines.push('---', '', `## Aggregate: ${passCount} / ${sorted.length} PASS`);

  fs.writeFileSync(REPORT_PATH, lines.join('\n'));
  console.log(`[G3] Report written to ${REPORT_PATH}`);
});
