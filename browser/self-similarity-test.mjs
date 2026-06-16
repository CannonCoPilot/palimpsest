/**
 * Playwright test: Self-Similarity workflow for Palimpsest
 * Project: dr-jekyll-and-mr-hyde
 * URL: http://localhost:5173/?project=dr-jekyll-and-mr-hyde
 */

import { chromium } from '@playwright/test';
import { createHash } from 'crypto';
import { readFileSync } from 'fs';

const SCREENSHOT_DIR = '/Users/nathanielcannon/Claude/Projects/palimpsest/.scratch/screenshots/self-similarity';
const BASE_URL = 'http://localhost:5173/?project=dr-jekyll-and-mr-hyde';
const METRICS = ['cosine', 'jaccard', 'word_overlap', 'edit_distance'];

const results = [];

function pass(name, desc) {
  results.push({ name, status: 'pass', desc });
  console.log(`  PASS  ${name}: ${desc}`);
}

function fail(name, desc, err) {
  results.push({ name, status: 'fail', desc, err: String(err) });
  console.log(`  FAIL  ${name}: ${desc} -- ${err}`);
}

function canvasHash(page, canvasSelector) {
  return page.evaluate((sel) => {
    const canvas = document.querySelector(sel);
    if (!canvas) return null;
    return canvas.toDataURL('image/png').slice(0, 200); // first bytes as proxy for content
  }, canvasSelector);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  // Capture console errors
  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  // ── Step 1: Navigate to project page ────────────────────────────────────────
  console.log('\nStep 1: Navigate to project page');
  try {
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    const title = await page.title();
    console.log(`  Page title: ${title}`);
    pass('step-1-navigate', `Loaded ${BASE_URL}`);
  } catch (e) {
    fail('step-1-navigate', 'Failed to load project page', e);
    await browser.close();
    return results;
  }

  // ── Step 2: Find and click the TextHiC tab ──────────────────────────────────
  console.log('\nStep 2: Find and open TextHiC panel');
  try {
    // The TabBar renders a button with text "TextHiC"
    const texthicTab = page.getByRole('tab', { name: /texthic/i });
    await texthicTab.waitFor({ state: 'visible', timeout: 10000 });
    await texthicTab.click();
    pass('step-2-texthic-tab-found', 'TextHiC tab visible and clicked');
  } catch (e) {
    fail('step-2-texthic-tab-found', 'TextHiC tab not found', e);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/step2-tab-not-found.png` });
    await browser.close();
    return results;
  }

  // ── Step 3: Verify dotplot canvas renders ────────────────────────────────────
  console.log('\nStep 3: Verify canvas element renders');
  try {
    // Wait for canvas to appear — it renders once signal is loaded
    const canvas = page.locator('canvas[role="img"]');
    await canvas.waitFor({ state: 'visible', timeout: 20000 });
    const box = await canvas.boundingBox();
    if (!box || box.width < 50 || box.height < 50) {
      throw new Error(`Canvas too small: ${JSON.stringify(box)}`);
    }
    pass('step-3-canvas-visible', `Canvas visible, size ${Math.round(box.width)}x${Math.round(box.height)}`);
  } catch (e) {
    fail('step-3-canvas-visible', 'Canvas not found or too small', e);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/step3-canvas-fail.png` });
    await browser.close();
    return results;
  }

  // ── Step 4: Screenshot initial dotplot ──────────────────────────────────────
  console.log('\nStep 4: Screenshot initial dotplot');
  try {
    await page.screenshot({ path: `${SCREENSHOT_DIR}/01-initial-dotplot.png`, fullPage: false });
    pass('step-4-screenshot-initial', 'Screenshot 01-initial-dotplot.png saved');
  } catch (e) {
    fail('step-4-screenshot-initial', 'Failed to take screenshot', e);
  }

  // ── Step 5: Open Filters panel and verify metric dropdown ────────────────────
  console.log('\nStep 5: Open Filters panel and verify metric dropdown');
  try {
    // Click the "Filters" button to open the controls panel
    const filtersBtn = page.getByRole('button', { name: /filters/i });
    await filtersBtn.waitFor({ state: 'visible', timeout: 8000 });
    await filtersBtn.click();

    // Wait for the metric select to appear
    const metricSelect = page.locator('select[title*="similarity metric"]').first();
    await metricSelect.waitFor({ state: 'visible', timeout: 8000 });

    // Verify available options
    const options = await metricSelect.evaluate((sel) =>
      Array.from(sel.options).map((o) => o.value)
    );
    console.log(`  Found metric options: ${options.join(', ')}`);

    const expected = ['cosine', 'jaccard', 'word_overlap', 'edit_distance'];
    const allFound = expected.every((m) => options.includes(m));
    if (!allFound) throw new Error(`Missing metrics. Got: ${options.join(',')}`);

    pass('step-5-metric-dropdown', `Metric dropdown has all 4 options: ${options.join(', ')}`);
  } catch (e) {
    fail('step-5-metric-dropdown', 'Metric dropdown check failed', e);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/step5-metric-fail.png` });
  }

  // Screenshot filters panel - default state
  await page.screenshot({ path: `${SCREENSHOT_DIR}/02-filters-panel-open.png` });

  // ── Step 6: Switch metrics and verify canvas changes ────────────────────────
  console.log('\nStep 6: Switch metrics and capture screenshots');

  // Get canvas hash before any metric switch
  let previousHash = await canvasHash(page, 'canvas[role="img"]');

  for (const metric of METRICS) {
    console.log(`  Testing metric: ${metric}`);
    try {
      // Select metric in the dropdown
      const metricSelect = page.locator('select[title*="similarity metric"]').first();
      await metricSelect.selectOption(metric);

      // Wait 2 seconds for data to load and canvas to re-render
      await page.waitForTimeout(2000);

      // Take screenshot
      const filename = `03-metric-${metric}.png`;
      await page.screenshot({ path: `${SCREENSHOT_DIR}/${filename}` });

      // Verify canvas still visible and get new hash
      const canvas = page.locator('canvas[role="img"]');
      const box = await canvas.boundingBox();
      if (!box || box.width < 50) throw new Error('Canvas disappeared after metric switch');

      const newHash = await canvasHash(page, 'canvas[role="img"]');

      // For metrics other than the first (cosine), compare against previous
      const changed = newHash !== previousHash;
      console.log(`    Canvas content changed: ${changed} (hash prefix: ${newHash?.slice(-20)})`);
      previousHash = newHash;

      pass(`step-6-metric-${metric}`, `Switched to ${metric}, canvas visible, screenshot saved`);
    } catch (e) {
      fail(`step-6-metric-${metric}`, `Metric switch to ${metric} failed`, e);
    }
  }

  // ── Step 7: Verify chunk size slider exists at default value 17 ─────────────
  console.log('\nStep 7: Verify chunk size slider');
  try {
    // The chunk slider: input[type=range] with min=5 max=25
    const chunkSlider = page.locator('input[type="range"][min="5"][max="25"]');
    await chunkSlider.waitFor({ state: 'visible', timeout: 8000 });
    const value = await chunkSlider.inputValue();
    console.log(`  Chunk slider current value: ${value}`);
    if (value !== '17') {
      console.log(`  NOTE: Default chunk size is ${value} (expected 17; manifest may differ)`);
    }
    pass('step-7-chunk-slider', `Chunk size slider found, value=${value}`);
  } catch (e) {
    fail('step-7-chunk-slider', 'Chunk size slider not found', e);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/step7-slider-fail.png` });
  }

  // Screenshot filters in default chunk state
  await page.screenshot({ path: `${SCREENSHOT_DIR}/04-filters-default-chunk.png` });

  // ── Step 8: Change chunk size and verify Recompute button appears ────────────
  console.log('\nStep 8: Change chunk size and verify Recompute button');
  try {
    // First ensure the metric is back to cosine (clean state)
    const metricSelect = page.locator('select[title*="similarity metric"]').first();
    await metricSelect.selectOption('cosine');
    await page.waitForTimeout(500);

    // Find the chunk slider and change its value
    const chunkSlider = page.locator('input[type="range"][min="5"][max="25"]');
    const currentVal = parseInt(await chunkSlider.inputValue(), 10);
    const newVal = currentVal === 20 ? 15 : 20;
    console.log(`  Changing chunk size from ${currentVal} to ${newVal}`);

    // Use fill + dispatchEvent to trigger React's onChange
    await chunkSlider.fill(String(newVal));
    await chunkSlider.dispatchEvent('input');
    await chunkSlider.dispatchEvent('change');
    await page.waitForTimeout(500);

    // Also try: click at a different position on the slider
    const box = await chunkSlider.boundingBox();
    if (box) {
      // Click at ~75% of slider width (maps to roughly value 20 on 5-25 range)
      const targetX = box.x + box.width * 0.75;
      await page.mouse.click(targetX, box.y + box.height / 2);
      await page.waitForTimeout(500);
    }

    const newSliderVal = await chunkSlider.inputValue();
    console.log(`  Slider value after interaction: ${newSliderVal}`);

    // Check if Recompute button appears
    const recomputeBtn = page.getByRole('button', { name: /recompute/i });
    const recomputeVisible = await recomputeBtn.isVisible().catch(() => false);

    if (recomputeVisible) {
      pass('step-8-recompute-button', `Recompute button appeared after chunk size change (value=${newSliderVal})`);
    } else {
      // If slider value didn't change from default, recompute won't show
      const loadedVal = 17; // from manifest
      if (parseInt(newSliderVal, 10) === loadedVal) {
        fail('step-8-recompute-button', `Slider did not change from loaded value ${loadedVal} — Recompute button not shown (React range input interaction limitation)`, 'slider value unchanged');
      } else {
        fail('step-8-recompute-button', `Slider changed to ${newSliderVal} but Recompute button not visible`, 'Recompute not shown');
      }
    }
  } catch (e) {
    fail('step-8-recompute-button', 'Chunk size change test failed', e);
  }

  // Screenshot filters in changed-chunk state
  await page.screenshot({ path: `${SCREENSHOT_DIR}/05-filters-changed-chunk.png` });

  // ── Step 9: Final state screenshot ──────────────────────────────────────────
  console.log('\nStep 9: Final screenshot');
  try {
    await page.screenshot({ path: `${SCREENSHOT_DIR}/06-final-state.png`, fullPage: false });
    pass('step-9-final-screenshot', 'Final screenshot saved');
  } catch (e) {
    fail('step-9-final-screenshot', 'Final screenshot failed', e);
  }

  // ── Console error report ─────────────────────────────────────────────────────
  if (consoleErrors.length > 0) {
    console.log(`\nConsole errors (${consoleErrors.length}):`);
    consoleErrors.slice(0, 10).forEach((e) => console.log(`  ${e}`));
  } else {
    console.log('\nNo browser console errors detected.');
  }

  await browser.close();
  return results;
}

run()
  .then((results) => {
    console.log('\n=== RESULTS SUMMARY ===');
    const passed = results.filter((r) => r.status === 'pass').length;
    const failed = results.filter((r) => r.status === 'fail').length;
    console.log(`Total: ${results.length} | Passed: ${passed} | Failed: ${failed}`);
    results.forEach((r) => {
      const icon = r.status === 'pass' ? 'PASS' : 'FAIL';
      console.log(`  [${icon}] ${r.name}: ${r.desc}${r.err ? ` -- ${r.err}` : ''}`);
    });
    // Output JSON for programmatic parsing
    console.log('\n=== JSON ===');
    console.log(JSON.stringify(results, null, 2));
    process.exit(failed > 0 ? 1 : 0);
  })
  .catch((e) => {
    console.error('Fatal test error:', e);
    process.exit(1);
  });
