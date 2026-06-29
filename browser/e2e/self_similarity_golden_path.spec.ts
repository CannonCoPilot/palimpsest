import { test, expect, request as pwRequest, type APIRequestContext } from '@playwright/test';

/**
 * Wave-0 P7 (C6) — self_similarity layer-consumer golden path.
 *
 * Proves the C5 surface end-to-end against the live stack: the redesigned consumer no longer chunks
 * or embeds inline, so the user must (1) produce layers, then (2) bind them through the new
 * layer-picker (fed by GET …/self_similarity/inputs) and run. This test seeds the prerequisite
 * layers via the API, then drives the UI: open the picker, pick a text-only metric + the chunk
 * layer's repeat_mask, run, and confirm the heatmap renders.
 *
 * It uses word_overlap (a text-only metric) so it needs NO embedding service — only chunk +
 * repeat_mask layers. The embedding path (cosine/jaccard) is covered by backend tests.
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

async function startTrack(
  api: APIRequestContext, projectId: string, track: string, params: Record<string, string> = {},
): Promise<void> {
  const q = new URLSearchParams(params).toString();
  const r = await api.post(`${API}/api/projects/${projectId}/analyze/${track}${q ? `?${q}` : ''}`);
  expect(r.ok(), `start ${track}`).toBeTruthy();
}

async function waitComputed(
  api: APIRequestContext, projectId: string, track: string, timeoutMs = 120_000,
): Promise<void> {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const status = await (await api.get(`${API}/api/projects/${projectId}/analysis/status`)).json();
    const t = status.find((x: { name: string }) => x.name === track);
    if (t?.status === 'computed' && (t.layers?.length ?? 1) > 0) return;
    if (t?.status === 'failed') throw new Error(`${track} failed: ${t.error}`);
    await new Promise((res) => setTimeout(res, 2000));
  }
  throw new Error(`${track} did not reach "computed" within ${timeoutMs}ms`);
}

let projectId: string;

test.beforeAll(async () => {
  const api = await pwRequest.newContext();
  projectId = await smallestProjectId(api);
  // Seed the text-only bundle prerequisites (idempotent: artifacts are content-addressed).
  await startTrack(api, projectId, 'chunking', { chunk_mode: 'word', chunk_size: '200' });
  await waitComputed(api, projectId, 'chunking');
  await startTrack(api, projectId, 'repeats');
  await waitComputed(api, projectId, 'repeats');
  await startTrack(api, projectId, 'repeat_mask');
  await waitComputed(api, projectId, 'repeat_mask');

  // Sanity: the discovery endpoint now reports at least one bundle-ready chunk layer.
  const inputs = await (await api.get(`${API}/api/projects/${projectId}/self_similarity/inputs`)).json();
  expect(inputs.chunk_layers.some((c: { bundle_ready: boolean }) => c.bundle_ready)).toBeTruthy();
  await api.dispose();
});

test('layer-picker → run word_overlap → heatmap renders', async ({ page }) => {
  await page.goto(`/?project=${projectId}`);
  await expect(page.getByRole('tab', { name: 'Analysis' })).toBeVisible();
  await page.getByRole('tab', { name: 'Analysis' }).click();

  // Open the self_similarity layer-picker. A never-run consumer is "pending" → "Configure…".
  const ssRow = page.locator('tr', { hasText: 'self_similarity' }).first();
  await ssRow.getByRole('button', { name: /Configure|Reconfigure|Re-run/ }).click();
  await expect(page.getByText('Self-Similarity Inputs')).toBeVisible();

  // Text-only run: drop the embedding-based metrics, keep word_overlap.
  for (const m of ['cosine', 'jaccard']) {
    const cb = page.locator('label', { hasText: new RegExp(`^${m}`) }).getByRole('checkbox');
    if (await cb.isChecked()) await cb.uncheck();
  }

  // Include the chunk layer (its sole repeat_mask is pre-selected by the dialog).
  const chunkLabel = page.locator('label', { hasText: /^size / }).first();
  await chunkLabel.getByRole('checkbox').check();

  await page.getByRole('button', { name: 'Run Selected' }).click();

  // The run lands asynchronously; confirm via the API before viewing.
  const api = await pwRequest.newContext();
  await waitComputed(api, projectId, 'self_similarity');
  await api.dispose();

  // The heatmap view renders the matrix on a canvas.
  await page.getByRole('tab', { name: 'TextHiC' }).click();
  await expect(page.locator('canvas').first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('Self-Similarity Matrix')).toBeVisible();
});
