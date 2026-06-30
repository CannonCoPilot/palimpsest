import { test, expect, request as pwRequest, type APIRequestContext, type Page } from '@playwright/test';

/**
 * Wave-0 P6 (FR-14) — per-layer stats panel golden path.
 *
 * From any layer, one click to its summary statistics, distributions, and a selectable set of
 * visualizations. Drives the Analysis suite's Explore tab: opens a chunk layer's stats panel from a
 * lane action and switches across all four chunk views (length histogram / ECDF / by-element violin
 * / boundary-alignment bar), then an embedding layer's panel across its five P3-backed views, then
 * opens two panels side by side for compare, and confirms one-click open from a manager row.
 *
 * Runs against the live dev stack (API :8080). The chunk views need the P6 backend endpoint
 * (/chunking/{label}/stats); the embedding views reuse the P3 endpoints. The embedding panel is
 * skipped gracefully when no embedding layer is seeded (needs the embed service on :8000).
 */

const API = process.env.PALIMPSEST_API_URL ?? 'http://localhost:8080';

async function smallestProjectId(api: APIRequestContext): Promise<string> {
  const projects = await (await api.get(`${API}/api/projects`)).json();
  let best: { id: string; wc: number } | null = null;
  for (const p of projects) {
    const m = await api.get(`${API}/data/${p.id}/metadata.json`);
    if (!m.ok()) continue;
    const wc = (await m.json()).word_count ?? Number.MAX_SAFE_INTEGER;
    if (!best || wc < best.wc) best = { id: p.id, wc };
  }
  if (!best) throw new Error('no ingested projects available to test against');
  return best.id;
}

async function trackRow(api: APIRequestContext, projectId: string, track: string):
  Promise<{ status?: string; error?: string; layers?: { label: string }[] } | undefined> {
  const status = await (await api.get(`${API}/api/projects/${projectId}/analysis/status`)).json();
  return status.find((x: { name: string }) => x.name === track);
}

async function waitLayers(
  api: APIRequestContext, projectId: string, track: string, minLayers = 1, timeoutMs = 120_000,
): Promise<string[]> {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const t = await trackRow(api, projectId, track);
    if (t?.status === 'failed') throw new Error(`${track} failed: ${t.error}`);
    const labels = (t?.layers ?? []).map((l) => l.label);
    if (t?.status === 'computed' && labels.length >= minLayers) return labels;
    await new Promise((res) => setTimeout(res, 2000));
  }
  throw new Error(`${track} did not reach ${minLayers} layer(s) within ${timeoutMs}ms`);
}

let projectId: string;
let embeddingSeeded = false;

test.beforeAll(async () => {
  const api = await pwRequest.newContext();
  projectId = await smallestProjectId(api);

  // Ensure at least two chunk layers exist (a second backs the side-by-side compare).
  await api.post(`${API}/api/projects/${projectId}/analyze/chunking?chunk_mode=word&chunk_size=200`);
  await waitLayers(api, projectId, 'chunking', 1);
  await api.post(`${API}/api/projects/${projectId}/analyze/chunking?chunk_mode=word&chunk_size=120`);
  await waitLayers(api, projectId, 'chunking', 2);

  const emb = await trackRow(api, projectId, 'embedding');
  embeddingSeeded = (emb?.layers ?? []).length > 0;
  await api.dispose();
});

async function openExplore(page: Page): Promise<void> {
  await page.goto(`/?project=${projectId}`);
  await page.getByRole('tab', { name: 'Analysis' }).click();
  await page.getByRole('tab', { name: /^Explore/ }).click();
  await expect(page.getByLabel('Lane stack').getByRole('img', { name: /band/i }).first())
    .toBeVisible({ timeout: 30_000 });
}

test('chunk layer: stats panel opens from a lane action and switches all four views', async ({ page }) => {
  await openExplore(page);
  // Open from the track-lane "stats" action (one of the two one-click entry points).
  await page.getByLabel(/^Open stats for chunking/).first().click();
  const panel = page.getByTestId('layer-stats-panel').first();
  await expect(panel).toBeVisible();
  await expect(panel.getByLabel('instant stats summary')).toBeVisible();

  // Default view: word + char length histograms (from /chunking/{label}/stats).
  await expect(panel.getByRole('img', { name: /words \/ chunk histogram/i })).toBeVisible({ timeout: 15_000 });
  await expect(panel.getByRole('img', { name: /chars \/ chunk histogram/i })).toBeVisible();

  await panel.getByRole('tab', { name: 'ECDF' }).click();
  await expect(panel.getByRole('img', { name: /words \/ chunk ECDF/i })).toBeVisible();

  await panel.getByRole('tab', { name: 'by-element violin' }).click();
  await expect(panel.getByRole('img', { name: /by element type/i })).toBeVisible();

  await panel.getByRole('tab', { name: 'boundary alignment' }).click();
  await expect(panel.getByRole('img', { name: /chunk→struct/i })).toBeVisible();
});

test('embedding layer: stats panel switches across the P3-backed views', async ({ page }) => {
  test.skip(!embeddingSeeded, 'no embedding layer seeded (embed service down?)');
  await openExplore(page);
  await page.getByLabel(/^Open stats for embedding/).first().click();
  const panel = page.getByTestId('layer-stats-panel').first();
  await expect(panel).toBeVisible();

  // Default scatter (P3 projection).
  await expect(panel.getByRole('img', { name: /projection scatter, \d+ points/i })).toBeVisible({ timeout: 20_000 });

  await panel.getByRole('tab', { name: 'pairwise dist' }).click();
  await expect(panel.getByRole('img', { name: /pairwise cosine distance histogram/i })).toBeVisible({ timeout: 15_000 });

  await panel.getByRole('tab', { name: 'NN dist' }).click();
  await expect(panel.getByRole('img', { name: /nearest-neighbour distance histogram/i })).toBeVisible();

  await panel.getByRole('tab', { name: 'similarity heatmap' }).click();
  await expect(panel.getByRole('img', { name: /similarity heatmap, \d+ by \d+/i })).toBeVisible({ timeout: 15_000 });

  await panel.getByRole('tab', { name: 'clusters' }).click();
  await expect(panel.getByRole('img', { name: /\d+ clusters/i })).toBeVisible();
});

test('two stats panels open side by side for compare (one-click from manager rows)', async ({ page }) => {
  await openExplore(page);
  // The manager-row "stats →" buttons are the second one-click entry point.
  const rowButtons = page.getByLabel('Layer manager').getByRole('button', { name: 'stats →' });
  await rowButtons.nth(0).click();
  await rowButtons.nth(1).click();
  const panels = page.getByTestId('stats-panels');
  await expect(panels).toBeVisible();
  await expect(panels.getByTestId('layer-stats-panel')).toHaveCount(2);
});
