import { test, expect, request as pwRequest, type APIRequestContext } from '@playwright/test';

/**
 * Collections tier — C2 pairwise dotplot golden path (FR-33/FR-36/FR-40).
 *
 * Drives the Compare tab end to end against the live stack: load a primary text, pick a second,
 * run a (text-only) word-overlap alignment, open the Dotplot sub-view, and exercise the three C2
 * controls — palette switcher, score-threshold slider (the dotplot's empirical cutoff), and PAF
 * export. Uses two Douay-Rheims appendix sub-texts (one a superset of the other) so the matrix and
 * alignment records are real and dense. Word overlap needs no embedding service.
 *
 *   PALIMPSEST_BASE_URL / PALIMPSEST_API_URL  → point both at the C2 server (single origin).
 */

const API = process.env.PALIMPSEST_API_URL ?? 'http://localhost:8080';

let queryId: string;
let targetId: string;

test.beforeAll(async () => {
  const api: APIRequestContext = await pwRequest.newContext();
  const projects: { id: string }[] = await (await api.get(`${API}/api/projects`)).json();
  const ids = projects.map((p) => p.id);
  // Primary is the superset (…appendix-0002-appendix-0003) — it belongs to no collection, so the
  // picker's scope stays "All texts" and the subset target is selectable. Target is …appendix-0002.
  queryId = ids.find((i) => i.endsWith('-appendix-0002-appendix-0003'))!;
  targetId = ids.find((i) => i.endsWith('-appendix-0002') && !i.endsWith('-appendix-0003'))!;
  if (!queryId || !targetId) throw new Error('DR appendix fixture pair not found in workspace');
  await api.dispose();
});

test('dotplot: heatmap renders with palette switch, score-threshold cutoff, and PAF export', async ({ page }) => {
  await page.goto(`/?project=${queryId}`);
  await page.getByRole('tab', { name: 'Compare' }).click();

  // Pick the second text. The picker scopes to a collection containing the primary by default, and
  // the superset target isn't in it — widen to "All texts", then select by id (titles collide).
  const scope = page.locator('select[title="Scope to a collection"]');
  if (await scope.count()) await scope.selectOption('');
  const picker = page.locator('select').filter({ has: page.locator(`option[value="${targetId}"]`) });
  await picker.selectOption(targetId);

  // Run a word-overlap alignment (no embedding service needed).
  await page.locator('select').filter({ has: page.locator('option[value="word"]') }).selectOption('word');
  await page.getByRole('button', { name: 'Align', exact: true }).click();

  // Records loaded → header shows the count. The 34×37 word matrix completes quickly.
  await expect(page.getByText(/\d+ alignments?/)).toBeVisible({ timeout: 60_000 });

  await page.getByRole('tab', { name: 'Dotplot' }).click();

  // Heatmap canvas renders (real Chromium has a 2D context, unlike jsdom).
  const heatmap = page.getByRole('img', { name: /Cross-similarity heatmap/i });
  await expect(heatmap).toBeVisible({ timeout: 30_000 });

  // Palette switcher: blues → viridis.
  const palette = page.getByRole('combobox', { name: /palette/i });
  await expect(palette).toBeVisible();
  await palette.selectOption('viridis');
  await expect(palette).toHaveValue('viridis');

  // Score-threshold slider: raising the cutoff hides low-scoring alignments (FR-40).
  const slider = page.getByRole('slider');
  await expect(slider).toBeVisible();
  const countText = page.locator('span').filter({ hasText: /^\d+\/\d+$/ }).first();
  const before = await countText.innerText();           // e.g. "100/100" at threshold 0
  const total = Number(before.split('/')[1]);
  const max = await slider.getAttribute('max');
  await slider.fill(String(max));                        // cutoff = max score → only the top scorers
  await expect(countText).not.toHaveText(before);
  const after = await countText.innerText();
  expect(Number(after.split('/')[0])).toBeLessThan(total);

  // PAF export link points at the export.paf endpoint (thresholded once the slider is above the floor).
  const paf = page.getByRole('link', { name: 'PAF' });
  await expect(paf).toBeVisible();
  const href = await paf.getAttribute('href');
  expect(href).toContain(`/api/alignment/${queryId}/${targetId}/export.paf`);
  expect(href).toContain('min_score=');
});
