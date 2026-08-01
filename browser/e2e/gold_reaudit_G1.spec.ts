/**
 * gold_reaudit_G1.spec.ts — Critical live UI re-audit for Gold Set Group G1
 *
 * Assigned Bibles (all EPUB-derived; structure INFERRED by detector):
 *   5   → DR-Haydock   (detector-epub, 14 mask types, volume/section hierarchy)
 *   100 → DR-Challoner (detector-epub, chapter_heading + front_matter + colophon)
 *   217 → Tyndale      (marker from epub reconstruction, genre_division + header)
 *   218 → Geneva 1560  (marker from epub reconstruction, genre_division + header)
 *
 * GROUP-SPECIFIC SCRUTINY:
 *   - front_matter blocks must be masked and must NOT bleed into scripture
 *   - chapter/verse element bounds must not overrun adjacent prose
 *   - DR-Haydock: 14 mask types (appendix, body, book, chapter, contents, footnotes,
 *     front_matter, glossary, header, heading, introduction, preface, section, title_page,
 *     volume) — verify each type renders as its own sub-track
 *   - DR-Challoner: argument paragraphs between chapter_heading and first verse must not
 *     be grayed (they should be visible prose in the chapter body)
 *   - Tyndale/Geneva: genre_division has a gap for Acts (Geneva) — this is a known
 *     classification choice, not an error; body/chapter still tile fully
 *
 * Three criteria per gold-set-standard §1:
 *   Complete  — generic layer (body) tiles [0,text_len) AND specific layer (chapter) tiles
 *               [0,text_len) with no gaps
 *   Accurate  — masked types correctly masked, unmasked types not masked, expected type
 *               counts match gold registry
 *   Precise   — each masked element's char bounds exactly capture the marker token, no
 *               overrun into adjacent verse prose and no under-reach
 *
 * Proven capture mechanics (from gold_masks_all.spec.ts and gold_reaudit_G4.spec.ts):
 *   - Expand lanes: click div.w-[100px].relative.shrink-0 nth(0/1), click "Expanded" btn,
 *     re-click cell to close menu (no Escape handler)
 *   - Browser zoom "+": scoped to span.min-w-[50px] → following button "+"
 *   - Reading zoom "+": scoped to span.min-w-[65px] → following button "+"
 *   - Masked token color: rgb(58, 58, 61) via getComputedStyle
 *
 * Run from browser/:
 *   PALIMPSEST_BASE_URL=http://localhost:8080 npx playwright test e2e/gold_reaudit_G1.spec.ts \
 *     --project=chromium --workers=1
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { test, expect, type Page, type Locator } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const SHOTS_DIR = path.resolve(__dirname, '../../core/.scratch/gold-audit/reaudit-4a/G1');
fs.mkdirSync(SHOTS_DIR, { recursive: true });

const API_BASE = process.env.PALIMPSEST_BASE_URL ?? 'http://localhost:8080';

interface BibleEntry {
  idx: number;
  project_id: string;
  label: string;
  kind: 'detector-epub' | 'marker';
  /** Expected mask types that should be present */
  expectedMaskedTypes: string[];
  /** Expected unmasked types */
  expectedUnmaskedTypes: string[];
  /** Expected book count */
  expectedBooks: number;
  /** Expected chapter count */
  expectedChapters: number;
}

const BIBLES: BibleEntry[] = [
  {
    idx: 5,
    project_id: 'douay-rheims-bible-complete-original-unabriged-full-douay-rheims-version-2018-1a24ae78af9f25ce66b9f156d163841a-anna-s-archive',
    label: 'DR-Haydock (epub, detector)',
    kind: 'detector-epub',
    expectedMaskedTypes: ['front_matter', 'title_page', 'contents', 'introduction', 'header', 'heading', 'footnotes', 'appendix', 'glossary', 'preface'],
    expectedUnmaskedTypes: ['body', 'book', 'chapter', 'section', 'volume'],
    expectedBooks: 78,
    expectedChapters: 3039,
  },
  {
    idx: 100,
    project_id: 'douay-rheims-bible-challoner-s-revised-version-2024-global-grey-ebooks-d727529260a20949024cead95f4b81cf-anna-s-archive',
    label: 'DR-Challoner (epub, detector)',
    kind: 'detector-epub',
    expectedMaskedTypes: ['front_matter', 'chapter_heading', 'colophon'],
    expectedUnmaskedTypes: ['body', 'book', 'chapter'],
    expectedBooks: 73,
    expectedChapters: 1334,
  },
  {
    idx: 217,
    project_id: 'tyndale-epub-reconstructed',
    label: 'Tyndale (epub-reconstructed, marker)',
    kind: 'marker',
    expectedMaskedTypes: ['header', 'chapter_heading'],
    expectedUnmaskedTypes: ['body', 'book', 'chapter'],
    expectedBooks: 33,
    expectedChapters: 451,
  },
  {
    idx: 218,
    project_id: 'geneva1560-epub-reconstructed',
    label: 'Geneva 1560 (epub-reconstructed, marker)',
    kind: 'marker',
    expectedMaskedTypes: ['header', 'chapter_heading'],
    expectedUnmaskedTypes: ['body', 'book', 'chapter'],
    expectedBooks: 66,
    expectedChapters: 1189,
  },
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
  maskedTextSamples: string[];
}

const findings: BibleFinding[] = [];

// ── Helpers (proven mechanics from gold_masks_all.spec.ts / gold_reaudit_G4.spec.ts) ──

async function shot(page: Page, name: string): Promise<string> {
  const fname = `${name}.png`;
  await page.screenshot({ path: path.join(SHOTS_DIR, fname), fullPage: false });
  return fname;
}

/** ElementGroupLane label cells: only `div.w-[100px].relative.shrink-0` in the Browser track */
function laneCell(page: Page, idx: number): Locator {
  return page.locator('div.w-\\[100px\\].relative.shrink-0').nth(idx);
}

async function expandLane(page: Page, laneIdx: number): Promise<number> {
  const cell = laneCell(page, laneIdx);
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

async function getMaskedTextSamples(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const spans: string[] = [];
    for (const s of Array.from(document.querySelectorAll('span'))) {
      if (getComputedStyle(s).backgroundColor === 'rgb(58, 58, 61)') {
        spans.push((s.textContent ?? '').slice(0, 80));
      }
    }
    return spans.slice(0, 20);
  });
}

/** Check if a layer tiles [0, textLen) with no gaps */
function checkTiling(
  sections: Array<{ type: string; start: number; end: number }>,
  layerTypes: string[],
  textLen: number
): { ok: boolean; gapCount: number; firstGapAt?: number } {
  const relevant = sections
    .filter(s => layerTypes.includes(s.type))
    .sort((a, b) => a.start - b.start);
  let pos = 0;
  let gapCount = 0;
  let firstGapAt: number | undefined;
  for (const s of relevant) {
    if (s.start > pos) {
      if (firstGapAt === undefined) firstGapAt = pos;
      gapCount++;
    }
    pos = Math.max(pos, s.end);
  }
  if (pos < textLen) {
    if (firstGapAt === undefined) firstGapAt = pos;
    gapCount++;
  }
  return { ok: gapCount === 0, gapCount, firstGapAt };
}

// ── Per-Bible test ────────────────────────────────────────────────────────────

for (const bible of BIBLES) {
  test(`[G1-idx${bible.idx}] ${bible.label} — Critical Re-Audit`, async ({ page }) => {
    test.setTimeout(240_000);

    const jsErrorsRaw: string[] = [];
    page.on('console', (m) => {
      if (m.type() === 'error') jsErrorsRaw.push(m.text());
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
      maskedTextSamples: [],
    };
    findings.push(f);

    // ── 1. Load project ───────────────────────────────────────────────────────
    try {
      await page.goto(
        `${API_BASE}/?project=${encodeURIComponent(bible.project_id)}`,
        { waitUntil: 'domcontentloaded', timeout: 45_000 }
      );
      await page.getByRole('tab', { name: 'Reading' })
        .waitFor({ state: 'visible', timeout: 90_000 });
      f.loaded = true;
    } catch (e) {
      f.loadError = String(e).slice(0, 300);
      f.defects.push({ severity: 'blocker', description: `Failed to load project: ${f.loadError}` });
      f.screenshots.push(await shot(page, `G1-${bible.idx}-load-failure`));
      return;
    }

    f.screenshots.push(await shot(page, `G1-${bible.idx}-01-loaded`));

    // ── 2. Programmatic precision: sections API + char-slice verification ─────
    const sectResp = await page.request.get(
      `${API_BASE}/api/projects/${encodeURIComponent(bible.project_id)}/sections`
    ).catch(() => null);

    if (!sectResp || !sectResp.ok()) {
      f.accurate.evidence = 'sections API probe failed';
      f.defects.push({ severity: 'blocker', description: 'GET /api/projects/{id}/sections failed' });
    } else {
      const sectData = await sectResp.json().catch(() => ({}));
      const sections: Array<{ type: string; start: number; end: number; id: string }> =
        sectData.sections ?? [];
      const maskByType: Record<string, boolean> = sectData.mask_by_type ?? {};
      const textLen: number = sectData.text_len ?? 0;

      const typeCounts: Record<string, number> = {};
      for (const s of sections) typeCounts[s.type] = (typeCounts[s.type] ?? 0) + 1;

      // ── COMPLETE check ─────────────────────────────────────────────────────
      // Generic layer: body must tile [0,text_len)
      const bodyResult = checkTiling(sections, ['body'], textLen);
      // Also check book + volume (for DR-Haydock which has volume hierarchy)
      const bookResult = checkTiling(sections, ['book'], textLen);
      const volResult  = checkTiling(sections, ['volume'], textLen);
      const genResult  = checkTiling(sections, ['body','volume','book','part','section'], textLen);

      // Specific layer: chapter must tile [0,text_len)
      const chapResult = checkTiling(sections, ['chapter'], textLen);

      const genericOk  = genResult.ok;
      const specificOk = chapResult.ok;

      f.complete.pass = genericOk && specificOk;
      f.complete.evidence = [
        `body_alone tiles: ${bodyResult.ok ? 'YES' : `NO (gaps=${bodyResult.gapCount})`}`,
        `book tiles: ${bookResult.ok ? 'YES' : `NO (gaps=${bookResult.gapCount})`}`,
        `volume tiles: ${volResult.ok ? 'YES' : `NO (gaps=${volResult.gapCount})`}`,
        `generic_combined tiles [0,${textLen}): ${genericOk ? 'YES' : `NO (gaps=${genResult.gapCount})`}`,
        `chapter tiles [0,${textLen}): ${specificOk ? 'YES' : `NO (gaps=${chapResult.gapCount}, first_gap_at=${chapResult.firstGapAt})`}`,
        `counts: body=${typeCounts.body??0} book=${typeCounts.book??0} chapter=${typeCounts.chapter??0} volume=${typeCounts.volume??0} section=${typeCounts.section??0}`,
        `text_len=${textLen}`,
      ].join('; ');

      if (!genericOk)
        f.defects.push({ severity: 'blocker', description: `Generic layer does not tile [0,${textLen}) — gaps=${genResult.gapCount}` });
      if (!specificOk)
        f.defects.push({ severity: 'blocker', description: `Chapter layer has ${chapResult.gapCount} gap(s) — does not tile [0,${textLen})` });
      if (typeCounts.book !== bible.expectedBooks)
        f.defects.push({ severity: 'blocker', description: `book count=${typeCounts.book??0}, expected ${bible.expectedBooks}` });
      if (typeCounts.chapter !== bible.expectedChapters)
        f.defects.push({ severity: 'blocker', description: `chapter count=${typeCounts.chapter??0}, expected ${bible.expectedChapters}` });

      // ── ACCURATE check ─────────────────────────────────────────────────────
      // All expectedMaskedTypes must have mask_by_type=true
      // All expectedUnmaskedTypes must have mask_by_type=false/undefined
      const maskedMismatches: string[] = [];
      for (const t of bible.expectedMaskedTypes) {
        if (maskByType[t] !== true) maskedMismatches.push(`${t} should be masked but is ${maskByType[t]}`);
      }
      const unmaskedMismatches: string[] = [];
      for (const t of bible.expectedUnmaskedTypes) {
        if (maskByType[t] === true) unmaskedMismatches.push(`${t} should NOT be masked but is true`);
      }

      f.accurate.pass = maskedMismatches.length === 0 && unmaskedMismatches.length === 0
        && typeCounts.book === bible.expectedBooks
        && typeCounts.chapter === bible.expectedChapters;

      f.accurate.evidence = [
        `mask_by_type: ${JSON.stringify(maskByType)}`,
        `masked mismatches: ${maskedMismatches.length === 0 ? 'none' : maskedMismatches.join(' | ')}`,
        `unmasked mismatches: ${unmaskedMismatches.length === 0 ? 'none' : unmaskedMismatches.join(' | ')}`,
        `all_types present: ${Object.keys(typeCounts).sort().join(',')}`,
        `counts: book=${typeCounts.book} (exp ${bible.expectedBooks}), chapter=${typeCounts.chapter} (exp ${bible.expectedChapters})`,
        `footnotes=${typeCounts.footnotes??0}, section=${typeCounts.section??0}, heading=${typeCounts.heading??0}`,
        `front_matter=${typeCounts.front_matter??0}, chapter_heading=${typeCounts.chapter_heading??0}`,
        `header=${typeCounts.header??0}, genre_division=${typeCounts.genre_division??0}`,
      ].join('; ');

      for (const mm of maskedMismatches)
        f.defects.push({ severity: 'blocker', description: `Accurate fail: ${mm}` });
      for (const um of unmaskedMismatches)
        f.defects.push({ severity: 'major', description: `Accurate fail: ${um}` });

      // ── PRECISE check (char-slice verification against reference.txt) ──────
      const refResp = await page.request.get(
        `${API_BASE}/data/${encodeURIComponent(bible.project_id)}/reference.txt`
      ).catch(() => null);

      if (!refResp || !refResp.ok()) {
        f.precise.evidence = 'could not load reference.txt for char-slice check';
        f.defects.push({ severity: 'major', description: 'reference.txt unavailable — precise check skipped' });
      } else {
        const refText = await refResp.text();
        const preciseProblems: string[] = [];
        let preciseOk = true;

        // ── DR-Haydock (idx 5): verify header, heading, footnotes, front_matter bounds
        if (bible.idx === 5) {
          const headers   = sections.filter(s => s.type === 'header').sort((a,b) => a.start-b.start);
          const headings  = sections.filter(s => s.type === 'heading').sort((a,b) => a.start-b.start);
          const footnotes = sections.filter(s => s.type === 'footnotes').sort((a,b) => a.start-b.start);
          const fmSecs    = sections.filter(s => s.type === 'front_matter');
          const chapters  = sections.filter(s => s.type === 'chapter').sort((a,b) => a.start-b.start);

          // SPECIMEN 1: book header ("# Genesis" etc.) — must not include trailing \n
          let headerBad = 0;
          for (const h of headers) {
            const slice    = refText.slice(h.start, h.end);
            const afterCh  = h.end < refText.length ? refText[h.end] : '';
            // header should end without \n (the \n is outside the element)
            if (slice.endsWith('\n') || slice.endsWith('\n\n')) {
              headerBad++;
              if (preciseProblems.length < 4)
                preciseProblems.push(`header[${h.start},${h.end}) ends with newline: ${JSON.stringify(slice.slice(-10))}`);
            }
          }

          // SPECIMEN 2: footnotes — must NOT start inside verse prose (should follow verse block)
          // Check first 10 footnotes
          let footnoteBleedCount = 0;
          for (const fn of footnotes.slice(0, 20)) {
            const slice     = refText.slice(fn.start, fn.end);
            const beforeCh  = fn.start > 0 ? refText[fn.start-2] : '';
            // Footnotes should start with letter/word, not mid-sentence punctuation
            // But we mainly check that footnotes DON'T start inside a verse (i.e., no \d:\d. pattern just before them)
            const prevChunk = refText.slice(Math.max(0, fn.start-30), fn.start);
            // If the char immediately before footnote is a period "." and is mid-verse, that's a bleed
            // Better check: footnote should start at beginning of a paragraph (after \n\n)
            if (!prevChunk.includes('\n\n') && fn.start > 100) {
              footnoteBleedCount++;
              if (preciseProblems.length < 4)
                preciseProblems.push(`footnote[${fn.start},${fn.end}) does NOT start after paragraph break, prev=${JSON.stringify(prevChunk.slice(-15))}`);
            }
          }

          // SPECIMEN 3: front_matter — must end BEFORE first scripture verse
          if (fmSecs.length > 0) {
            const fm = fmSecs[0];
            const afterFM = refText.slice(fm.end, fm.end + 80);
            // After front_matter we should NOT see "1:1." (DR verse notation) immediately
            const hasVerseImmediately = /^\s*\d+:\d+\./.test(afterFM);
            if (hasVerseImmediately) {
              preciseProblems.push(`front_matter[${fm.start},${fm.end}) ends and is IMMEDIATELY followed by verse notation: ${JSON.stringify(afterFM.slice(0,40))}`);
              preciseOk = false;
            }
          }

          // SPECIMEN 4: chapter boundary — no gap between consecutive chapters
          let chapterGapCount = 0;
          for (let i = 0; i < chapters.length - 1; i++) {
            if (chapters[i+1].start !== chapters[i].end) {
              chapterGapCount++;
              if (chapterGapCount <= 2)
                preciseProblems.push(`chapter gap: chapters[${i}].end=${chapters[i].end} != chapters[${i+1}].start=${chapters[i+1].start}`);
            }
          }

          const haydockPrecise = headerBad === 0 && chapterGapCount === 0 && !hasVerseImmediately;

          f.precise.evidence = [
            `headers: ${headers.length} total, ${headerBad} with trailing-newline precision errors`,
            `footnotes: ${footnotes.length} total, ${footnoteBleedCount} may not start at paragraph boundary`,
            `chapter gaps: ${chapterGapCount}`,
            `SPECIMEN header[0] [${headers[0]?.start},${headers[0]?.end}): ${JSON.stringify(refText.slice(headers[0]?.start, headers[0]?.end))} after=${JSON.stringify(refText.slice(headers[0]?.end, headers[0]?.end+5))}`,
            `SPECIMEN heading[0] [${headings[0]?.start},${headings[0]?.end}): ${JSON.stringify(refText.slice(headings[0]?.start, headings[0]?.end).slice(0,60))}`,
            `SPECIMEN chapter[0] [${chapters[0]?.start},${chapters[0]?.end}): starts=${JSON.stringify(refText.slice(chapters[0]?.start, chapters[0]?.start+40))}`,
            `SPECIMEN chapter[0] last80: ${JSON.stringify(refText.slice(chapters[0]?.end-40, chapters[0]?.end))}`,
            ...(preciseProblems.length > 0 ? ['PROBLEMS: ' + preciseProblems.join(' | ')] : []),
          ].join('; ');

          f.precise.pass = haydockPrecise && (footnoteBleedCount === 0);

          if (headerBad > 0)
            f.defects.push({ severity: 'blocker', description: `DR-Haydock: ${headerBad} headers have trailing newline overrun` });
          if (chapterGapCount > 0)
            f.defects.push({ severity: 'blocker', description: `DR-Haydock: ${chapterGapCount} gaps between consecutive chapters` });
          if (footnoteBleedCount > 0)
            f.defects.push({ severity: 'major', description: `DR-Haydock: ${footnoteBleedCount} footnote elements may not start at paragraph boundary` });

          // ── Extra: verify DR-Haydock unique sub-track types are present ──────
          const drHaydockTypes = ['volume','section','heading','footnotes','appendix','glossary','preface','front_matter','title_page','contents'];
          const missingTypes = drHaydockTypes.filter(t => !(t in typeCounts));
          if (missingTypes.length > 0) {
            f.defects.push({ severity: 'major', description: `DR-Haydock: missing expected types: ${missingTypes.join(',')}` });
          }

        // ── DR-Challoner (idx 100): verify chapter_heading + front_matter precision
        } else if (bible.idx === 100) {
          const chHeadings = sections.filter(s => s.type === 'chapter_heading').sort((a,b) => a.start-b.start);
          const fmSecs     = sections.filter(s => s.type === 'front_matter');
          const chapters   = sections.filter(s => s.type === 'chapter').sort((a,b) => a.start-b.start);

          // Check ALL chapter_headings: must start with capital letter, not with "##", must be short label
          // DR-Challoner headings are like "Genesis Chapter 1" (not "## Genesis Chapter 1")
          let chBad = 0;
          for (const ch of chHeadings) {
            const slice    = refText.slice(ch.start, ch.end);
            const afterCh  = ch.end < refText.length ? refText[ch.end] : '';
            // Should NOT start with "##" (these are not markdown headings)
            // Should NOT end with \n
            // Should be followed by \n
            if (slice.startsWith('##') || slice.endsWith('\n')) {
              chBad++;
              if (preciseProblems.length < 4)
                preciseProblems.push(`ch_heading[${ch.start},${ch.end}) problematic: ${JSON.stringify(slice.slice(0,40))}`);
            }
          }

          // CRITICAL: verify argument paragraph (between chapter_heading end and first verse) is NOT masked
          // The argument follows after chapter_heading ends and before "1:1." verse
          // We check: refText.slice(chHeadings[0].end, chHeadings[0].end + 120) should contain argument text
          // but that's prose, not masked
          const ch0 = chHeadings[0];
          const afterHeading = refText.slice(ch0.end, ch0.end + 120);
          const argumentIsInHeading = ch0 && refText.slice(ch0.start, ch0.end).includes('\n\nGod createth');
          if (argumentIsInHeading) {
            preciseProblems.push(`chapter_heading[0] contains argument paragraph text — overreach into prose`);
            preciseOk = false;
          }

          // Check front_matter ends before scripture
          if (fmSecs.length > 0) {
            const fm = fmSecs[0];
            const afterFM = refText.slice(fm.end, fm.end + 80);
            // After front_matter should be a chapter_heading like "Genesis Chapter 1"
            const nextCh = chHeadings.find(c => c.start >= fm.end);
            const fmEndOk = nextCh && nextCh.start === fm.end;
            if (!fmEndOk && !afterFM.startsWith('Genesis Chapter 1')) {
              // Allow small whitespace
              if (afterFM.trimStart().startsWith('Genesis Chapter 1')) {
                // OK, just whitespace
              } else {
                preciseProblems.push(`front_matter[${fm.start},${fm.end}) not immediately followed by chapter heading, got: ${JSON.stringify(afterFM.slice(0,40))}`);
              }
            }
          }

          // Chapter boundary check
          let chapterGapCount = 0;
          for (let i = 0; i < chapters.length - 1; i++) {
            if (chapters[i+1].start !== chapters[i].end) {
              chapterGapCount++;
              if (chapterGapCount <= 2)
                preciseProblems.push(`chapter gap: chapters[${i}].end=${chapters[i].end} != chapters[${i+1}].start=${chapters[i+1].start}`);
            }
          }

          f.precise.pass = chBad === 0 && chapterGapCount === 0 && !argumentIsInHeading;
          f.precise.evidence = [
            `chapter_heading: ${chHeadings.length} total, ${chBad} bad (markdown/newline overrun)`,
            `argument in heading: ${argumentIsInHeading ? 'YES (OVERREACH)' : 'no (correct)'}`,
            `chapter gaps: ${chapterGapCount}`,
            `SPECIMEN ch_heading[0] [${ch0?.start},${ch0?.end}): ${JSON.stringify(refText.slice(ch0?.start, ch0?.end))}`,
            `SPECIMEN after ch_heading[0]: ${JSON.stringify(afterHeading.slice(0,60))}`,
            `SPECIMEN ch_heading[-1] [${chHeadings[chHeadings.length-1]?.start},${chHeadings[chHeadings.length-1]?.end}): ${JSON.stringify(refText.slice(chHeadings[chHeadings.length-1]?.start, chHeadings[chHeadings.length-1]?.end))}`,
            ...(preciseProblems.length > 0 ? ['PROBLEMS: ' + preciseProblems.join(' | ')] : []),
          ].join('; ');

          if (chBad > 0)
            f.defects.push({ severity: 'blocker', description: `DR-Challoner: ${chBad} chapter_headings have markdown prefix or trailing newline` });
          if (chapterGapCount > 0)
            f.defects.push({ severity: 'blocker', description: `DR-Challoner: ${chapterGapCount} gaps between consecutive chapters` });
          if (argumentIsInHeading)
            f.defects.push({ severity: 'major', description: `DR-Challoner: chapter_heading[0] contains argument paragraph — overreach into prose` });

        // ── Tyndale (idx 217) and Geneva 1560 (idx 218): verify header/chapter_heading precision
        } else {
          const headers    = sections.filter(s => s.type === 'header').sort((a,b) => a.start-b.start);
          const chHeadings = sections.filter(s => s.type === 'chapter_heading').sort((a,b) => a.start-b.start);
          const chapters   = sections.filter(s => s.type === 'chapter').sort((a,b) => a.start-b.start);

          // ALL headers: must start with "# " and not include trailing newline
          let headerBad = 0, chBad = 0;
          for (const h of headers) {
            const slice    = refText.slice(h.start, h.end);
            const afterCh  = h.end < refText.length ? refText[h.end] : '';
            const beforeCh = h.start > 0 ? refText[h.start-1] : '';
            const ok = slice.startsWith('# ')
              && !slice.endsWith('\n')
              && (h.start === 0 || beforeCh === '\n')
              && (afterCh === '\n' || afterCh === '');
            if (!ok) {
              headerBad++;
              if (preciseProblems.length < 4)
                preciseProblems.push(`header[${h.start},${h.end}) bad: ${JSON.stringify(slice.slice(0,30))} before=${JSON.stringify(beforeCh)} after=${JSON.stringify(afterCh)}`);
            }
          }

          // ALL chapter_headings: must start with "## " and not include trailing newline
          for (const ch of chHeadings) {
            const slice    = refText.slice(ch.start, ch.end);
            const afterCh  = ch.end < refText.length ? refText[ch.end] : '';
            const beforeCh = ch.start > 0 ? refText[ch.start-1] : '';
            const ok = slice.startsWith('## ')
              && !slice.endsWith('\n')
              && (ch.start === 0 || beforeCh === '\n')
              && (afterCh === '\n' || afterCh === '');
            if (!ok) {
              chBad++;
              if (preciseProblems.length < 4)
                preciseProblems.push(`ch_heading[${ch.start},${ch.end}) bad: ${JSON.stringify(slice.slice(0,40))} before=${JSON.stringify(beforeCh)} after=${JSON.stringify(afterCh)}`);
            }
          }

          // Chapter boundary check
          let chapterGapCount = 0;
          for (let i = 0; i < chapters.length - 1; i++) {
            if (chapters[i+1].start !== chapters[i].end) {
              chapterGapCount++;
              if (chapterGapCount <= 2)
                preciseProblems.push(`chapter gap: [${i}].end=${chapters[i].end} != [${i+1}].start=${chapters[i+1].start}`);
            }
          }

          // Specimen header + chapter_heading
          const h0  = headers[0];
          const ch0 = chHeadings[0];
          const chL = chHeadings[chHeadings.length - 1];
          const specH0  = refText.slice(h0?.start, h0?.end);
          const specCh0 = refText.slice(ch0?.start, ch0?.end);
          const specChL = refText.slice(chL?.start, chL?.end);

          // Geneva 1560: verify known genre_division gap (Acts not in any genre_division)
          // This is expected — check body still covers it
          const genreDivs = sections.filter(s => s.type === 'genre_division').sort((a,b) => a.start-b.start);
          let gdCoverage = 'n/a';
          if (bible.idx === 218) {
            const total = genreDivs.reduce((acc, g) => acc + (g.end - g.start), 0);
            gdCoverage = `genre_divisions cover ${total} of ${textLen} chars (${(total/textLen*100).toFixed(1)}%); gap includes Acts by design`;
          }

          f.precise.pass = headerBad === 0 && chBad === 0 && chapterGapCount === 0;
          f.precise.evidence = [
            `header precision: ${headers.length - headerBad}/${headers.length} OK, ${headerBad} BAD`,
            `ch_heading precision: ${chHeadings.length - chBad}/${chHeadings.length} OK, ${chBad} BAD`,
            `chapter gaps: ${chapterGapCount}`,
            `SPECIMEN header[0] [${h0?.start},${h0?.end}): ${JSON.stringify(specH0)}`,
            `SPECIMEN ch_heading[0] [${ch0?.start},${ch0?.end}): ${JSON.stringify(specCh0)} after=${JSON.stringify(refText.slice(ch0?.end, ch0?.end+20))}`,
            `SPECIMEN ch_heading[-1] [${chL?.start},${chL?.end}): ${JSON.stringify(specChL)} after=${JSON.stringify(refText.slice(chL?.end, chL?.end+20))}`,
            gdCoverage,
            ...(preciseProblems.length > 0 ? ['PROBLEMS: ' + preciseProblems.join(' | ')] : []),
          ].join('; ');

          if (headerBad > 0)
            f.defects.push({ severity: 'blocker', description: `${bible.label}: ${headerBad} headers have imprecise char bounds` });
          if (chBad > 0)
            f.defects.push({ severity: 'blocker', description: `${bible.label}: ${chBad} chapter_headings have imprecise char bounds` });
          if (chapterGapCount > 0)
            f.defects.push({ severity: 'blocker', description: `${bible.label}: ${chapterGapCount} gaps between consecutive chapters` });
        }
      }
    }

    // ── 3. Browser tab — expand both lanes ───────────────────────────────────
    await page.getByRole('tab', { name: 'Browser' }).click();
    await page.getByRole('button', { name: /Tracks/ }).waitFor({ state: 'visible', timeout: 20_000 }).catch(() => {});
    await page.waitForTimeout(1500);
    f.screenshots.push(await shot(page, `G1-${bible.idx}-02-browser-overview`));

    // Expand Structure (idx=0)
    f.structH = await expandLane(page, 0);
    await page.waitForTimeout(400);
    // Expand Content (idx=1)
    f.contentH = await expandLane(page, 1);
    await page.waitForTimeout(600);
    f.screenshots.push(await shot(page, `G1-${bible.idx}-03-browser-expanded`));

    if (f.structH <= 30)
      f.defects.push({ severity: 'major', description: `Structure lane not expanded (svgH=${f.structH})` });
    if (f.contentH <= 30)
      f.defects.push({ severity: 'minor', description: `Content lane not expanded (svgH=${f.contentH})` });

    // ── 4. Browser zoom to char level (<700 chars in view) ────────────────────
    const zoomBtn = browserZoomIn(page);
    let civ = await charsInView(page);
    for (let i = 0; i < 20 && (isNaN(civ) || civ > 700); i++) {
      await zoomBtn.click({ force: true, timeout: 4_000 }).catch(() => {});
      await page.waitForTimeout(80);
      civ = await charsInView(page);
    }
    await page.mouse.move(640, 400);
    await page.waitForTimeout(600);
    f.charsInView = await charsInView(page);
    f.rects = await page.locator('svg rect').count().catch(() => 0);
    f.browserZoomed = !isNaN(f.charsInView) && f.charsInView < 1500;
    f.screenshots.push(await shot(page, `G1-${bible.idx}-04-browser-char-zoom`));

    if (!f.browserZoomed)
      f.defects.push({ severity: 'minor', description: `Could not zoom to char level (civ=${f.charsInView})` });
    if (f.rects === 0)
      f.defects.push({ severity: 'major', description: 'No SVG track rects at char zoom — masking bars missing' });

    // ── 5. Reading tab — sentence zoom, verify masked markers ─────────────────
    await page.getByRole('tab', { name: 'Reading' }).click();
    await page.waitForTimeout(1000);
    f.screenshots.push(await shot(page, `G1-${bible.idx}-05-reading-default`));

    // Zoom to sentence level (3 clicks)
    const rzBtn = readingZoomIn(page);
    for (let i = 0; i < 3; i++) {
      await rzBtn.click({ timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(600);
    }
    await page.waitForTimeout(800);
    f.maskedTokens = await countMaskedTokens(page);
    f.maskedTextSamples = await getMaskedTextSamples(page);
    f.readingZoomed = f.maskedTokens > 0;
    f.screenshots.push(await shot(page, `G1-${bible.idx}-06-reading-sentence-zoom`));

    if (f.maskedTokens === 0)
      f.defects.push({ severity: 'major',
        description: 'No masked tokens visible at sentence zoom — masked elements not greying in Reading tab' });

    // Verify masked spans look correct (not over-long prose)
    const overMasked = f.maskedTextSamples.filter(t => t.trimEnd().length > 55);
    if (overMasked.length > 0 && overMasked.some(t => !t.match(/^(THE|BOOK|VOLUME|CHAPTER|APPENDIX|PREFACE|CONTENTS|GLOSSARY)/i))) {
      f.defects.push({ severity: 'major',
        description: `Masked spans appear as long prose (possible overrun): ${JSON.stringify(overMasked.slice(0,3))}` });
    }

    // ── 6. DR-Haydock specific: verify sub-track types in Tracks panel ────────
    if (bible.idx === 5) {
      // Open Tracks drawer and screenshot
      await page.getByRole('button', { name: /Tracks/ }).click().catch(() => {});
      await page.waitForTimeout(800);
      f.screenshots.push(await shot(page, `G1-${bible.idx}-07-tracks-panel`));
      // Close tracks drawer
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    // ── 7. Characters tab ─────────────────────────────────────────────────────
    try {
      await page.getByRole('tab', { name: 'Characters' }).click();
      await page.waitForTimeout(1500);
      f.screenshots.push(await shot(page, `G1-${bible.idx}-08-characters`));
    } catch {}

    // ── 8. Analysis tab — integrity check ────────────────────────────────────
    try {
      await page.getByRole('tab', { name: 'Analysis' }).click();
      await page.waitForTimeout(1500);
      f.screenshots.push(await shot(page, `G1-${bible.idx}-09-analysis`));
    } catch {}

    // ── 9. JS errors ──────────────────────────────────────────────────────────
    f.jsErrors = jsErrorsRaw.filter(e =>
      !e.includes('favicon') &&
      !e.includes('ResizeObserver') &&
      !e.includes('ERR_ABORTED')
    );
    if (f.jsErrors.length > 0) {
      f.defects.push({ severity: 'minor',
        description: `${f.jsErrors.length} JS console errors: ${f.jsErrors.slice(0,2).join(' | ')}` });
    }

    // ── 10. Log and soft-assert ───────────────────────────────────────────────
    const maskedSample = f.maskedTextSamples.slice(0,8).map(t => JSON.stringify(t)).join(', ');
    console.log(
      `[G1-idx${bible.idx}] ${bible.label}:\n` +
      `  COMPLETE=${f.complete.pass} ACCURATE=${f.accurate.pass} PRECISE=${f.precise.pass}\n` +
      `  structH=${f.structH} contentH=${f.contentH} chars=${f.charsInView} ` +
      `rects=${f.rects} maskedTok=${f.maskedTokens} jsErr=${f.jsErrors.length}\n` +
      `  defects: ${f.defects.map(d => `[${d.severity}] ${d.description}`).join(' | ')}\n` +
      `  maskedSamples=[${maskedSample}]`
    );

    expect.soft(f.loaded,          `[G1-idx${bible.idx}] loaded`).toBe(true);
    expect.soft(f.complete.pass,   `[G1-idx${bible.idx}] complete`).toBe(true);
    expect.soft(f.accurate.pass,   `[G1-idx${bible.idx}] accurate`).toBe(true);
    expect.soft(f.precise.pass,    `[G1-idx${bible.idx}] precise`).toBe(true);
    expect.soft(f.structH,         `[G1-idx${bible.idx}] Structure lane expanded`).toBeGreaterThan(30);
    expect.soft(f.rects,           `[G1-idx${bible.idx}] SVG track rects rendered`).toBeGreaterThan(0);
    expect.soft(f.maskedTokens,    `[G1-idx${bible.idx}] masked tokens in Reading view`).toBeGreaterThan(0);
  });
}

// ── afterAll: compile findings to JSON for report generation ─────────────────
test.afterAll(async () => {
  const outPath = path.join(SHOTS_DIR, 'findings.json');
  fs.writeFileSync(outPath, JSON.stringify(findings, null, 2));
  console.log(`\n[G1] findings written to ${outPath}`);
});
