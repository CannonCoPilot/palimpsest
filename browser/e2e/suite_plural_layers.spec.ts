import { test, expect, request as pwRequest, type APIRequestContext } from '@playwright/test';

/**
 * Wave-0 P5 (FR-13) — plural layer-track rendering golden path.
 *
 * The explicit proof of plural-safety: seed two chunk layers (two word sizes) and one embedding
 * layer, then drive the Analysis suite's Explore tab and confirm all coexist as distinct lanes,
 * each drawn purely from its manifest `rendering.track_view` (no per-label code) — then reorder,
 * toggle one off, and overlay the two chunk ribbons.
 *
 * Runs against the live dev stack (API :8080 + Vite :5173); the embedding step also needs the embed
 * service (:8000) and is skipped gracefully if unavailable, leaving the two-chunk plural assertions
 * intact. Seeding is idempotent (artifacts are content-addressed).
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
): Promise<boolean> {
  const q = new URLSearchParams(params).toString();
  const r = await api.post(`${API}/api/projects/${projectId}/analyze/${track}${q ? `?${q}` : ''}`);
  return r.ok();
}

async function trackRow(api: APIRequestContext, projectId: string, track: string):
  Promise<{ status?: string; error?: string; layers?: { label: string }[] } | undefined> {
  const status = await (await api.get(`${API}/api/projects/${projectId}/analysis/status`)).json();
  return status.find((x: { name: string }) => x.name === track);
}

// Wait until a layer-keyed track has at least `minLayers` computed layers (a second chunk size adds
// a second layer, so "computed" alone isn't enough — we wait for the count).
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

// Wait for a non-layer-keyed track (e.g. profile) to reach "computed" — it has no layers[] to count.
async function waitComputed(
  api: APIRequestContext, projectId: string, track: string, timeoutMs = 120_000,
): Promise<void> {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const t = await trackRow(api, projectId, track);
    if (t?.status === 'computed') return;
    if (t?.status === 'failed') throw new Error(`${track} failed: ${t.error}`);
    await new Promise((res) => setTimeout(res, 2000));
  }
  throw new Error(`${track} did not reach "computed" within ${timeoutMs}ms`);
}

let projectId: string;
let embeddingSeeded = false;
let profileSeeded = false;

test.beforeAll(async () => {
  const api = await pwRequest.newContext();
  projectId = await smallestProjectId(api);

  // Two chunk layers (distinct word sizes → two chunk-band layers).
  await startTrack(api, projectId, 'chunking', { chunk_mode: 'word', chunk_size: '200' });
  await waitLayers(api, projectId, 'chunking', 1);
  await startTrack(api, projectId, 'chunking', { chunk_mode: 'word', chunk_size: '120' });
  const chunkLabels = await waitLayers(api, projectId, 'chunking', 2);
  expect(chunkLabels.length).toBeGreaterThanOrEqual(2);

  // One embedding layer bound to the first chunk layer — best-effort (needs the embed service on
  // :8000). Defaults match the running MLX server; override via env for other setups.
  try {
    const ok = await startTrack(api, projectId, 'embedding', {
      chunk_label: chunkLabels[0],
      embed_provider: process.env.PALIMPSEST_EMBED_PROVIDER ?? 'mlx',
      embed_endpoint: process.env.PALIMPSEST_EMBED_ENDPOINT ?? 'http://localhost:8000',
      embed_model: process.env.PALIMPSEST_EMBED_MODEL ?? 'mlx-community/Qwen3-Embedding-4B-4bit-DWQ',
    });
    if (ok) {
      await waitLayers(api, projectId, 'embedding', 1, 180_000);
      embeddingSeeded = true;
    }
  } catch (e) {
    console.warn(`[plural-golden-path] embedding layer not seeded (embed service down?): ${String(e)}`);
  }

  // Text profile (P4) for the Profile dashboard — descriptive stats, no external service.
  try {
    if (await startTrack(api, projectId, 'profile')) {
      await waitComputed(api, projectId, 'profile');
      profileSeeded = true;
    }
  } catch (e) {
    console.warn(`[plural-golden-path] profile not seeded: ${String(e)}`);
  }
  await api.dispose();
});

async function openExplore(page: import('@playwright/test').Page): Promise<void> {
  await page.goto(`/?project=${projectId}`);
  await page.getByRole('tab', { name: 'Analysis' }).click();
  await page.getByRole('tab', { name: /^Explore/ }).click();
}

test('plural chunk + embedding layers coexist as distinct lanes', async ({ page }) => {
  await openExplore(page);
  const stack = page.getByLabel('Lane stack');
  // Two-plus band ribbons (chunk/repeat) render simultaneously, each via its descriptor. These draw
  // from the static signals manifests, so they prove plural rendering against any server version.
  await expect(stack.getByRole('img', { name: /band/i }).first()).toBeVisible({ timeout: 30_000 });
  const bandCount = await stack.getByRole('img', { name: /band/i }).count();
  expect(bandCount).toBeGreaterThanOrEqual(2);
  // The embedding layer renders its colored lane from the P3 /lane endpoint — a third lane kind
  // coexisting with the band ribbons.
  if (embeddingSeeded) {
    await expect(stack.getByRole('img', { name: /embedding .* lane/i }).first()).toBeVisible();
  }
});

test('layer manager toggles a lane off', async ({ page }) => {
  await openExplore(page);
  const stack = page.getByLabel('Lane stack');
  await expect(stack.getByRole('img', { name: /band/i }).first()).toBeVisible({ timeout: 30_000 });
  const before = await stack.getByRole('img', { name: /band/i }).count();
  // Hide a chunk-band layer specifically (its switch is aria-labelled "Toggle chunking …"), so the
  // assertion holds regardless of how the embedding layer orders among the rows.
  await page.getByLabel('Layer manager').getByLabel(/^Toggle chunking/).first().click();
  await expect.poll(async () => stack.getByRole('img', { name: /band/i }).count()).toBeLessThan(before);
});

test('layer manager overlays the two chunk ribbons into one lane', async ({ page }) => {
  await openExplore(page);
  await expect(page.getByLabel('Lane stack').getByRole('img', { name: /band/i }).first())
    .toBeVisible({ timeout: 30_000 });
  const overlayButtons = page.getByLabel('Layer manager').getByRole('button', { name: /^Overlay chunking/ });
  await overlayButtons.nth(0).click();
  await overlayButtons.nth(1).click();
  const overlay = page.getByTestId('overlay-lane');
  await expect(overlay).toBeVisible();
  await expect.poll(async () => overlay.getByRole('img', { name: /band/i }).count()).toBe(2);
});

test('layer manager reorders lanes (pointer drag)', async ({ page }) => {
  await openExplore(page);
  const stack = page.getByLabel('Lane stack');
  await expect(stack.getByRole('img', { name: /band/i }).first()).toBeVisible({ timeout: 30_000 });
  const labelsBefore = await stack.locator('span[title]').allInnerTexts();

  // dnd-kit uses pointer events (not HTML5 drag), so drive raw mouse moves: grab the first row's
  // handle and drop it past the second row. PointerSensor has no activation distance, so a small
  // initial move starts the drag; multiple steps let the sortable collision detection settle.
  const handles = page.getByLabel('Layer manager').getByLabel('Drag to reorder');
  const src = await handles.nth(0).boundingBox();
  const dst = await handles.nth(1).boundingBox();
  if (!src || !dst) throw new Error('drag handles not found');
  await page.mouse.move(src.x + src.width / 2, src.y + src.height / 2);
  await page.mouse.down();
  await page.mouse.move(src.x + src.width / 2, src.y + src.height / 2 + 6);
  await page.mouse.move(dst.x + dst.width / 2, dst.y + dst.height / 2 + 12, { steps: 12 });
  await page.mouse.up();

  await expect.poll(async () => (await stack.locator('span[title]').allInnerTexts()).join('|'))
    .not.toBe(labelsBefore.join('|'));
});

// --- P3/P4-dependent suite views (need the committed backend; verified here against the live API). ---

test('substrate-integrity badge runs the P4 report', async ({ page }) => {
  await page.goto(`/?project=${projectId}`);
  await page.getByRole('tab', { name: 'Analysis' }).click();
  await page.getByLabel('Substrate integrity').click();
  // The badge resolves to a verdict pill (green or violation-count) once GET /integrity returns.
  await expect(page.getByText(/integrity (✓|: \d+ violation)/)).toBeVisible({ timeout: 15_000 });
});

test('Representations tab renders the embedding projection scatter', async ({ page }) => {
  test.skip(!embeddingSeeded, 'no embedding layer to project');
  await page.goto(`/?project=${projectId}`);
  await page.getByRole('tab', { name: 'Analysis' }).click();
  await page.getByRole('tab', { name: /^Representations/ }).click();
  // The scatter is a canvas whose accessible name reports the projected point count.
  await expect(page.getByRole('img', { name: /projection scatter, \d+ points/i }).first())
    .toBeVisible({ timeout: 20_000 });
});

test('Profile tab renders text-level stats + distribution charts', async ({ page }) => {
  test.skip(!profileSeeded, 'no profile computed');
  await page.goto(`/?project=${projectId}`);
  await page.getByRole('tab', { name: 'Analysis' }).click();
  await page.getByRole('tab', { name: /^Profile/ }).click();
  const profile = page.getByLabel('Text profile');
  await expect(profile).toBeVisible({ timeout: 20_000 });
  // At least one distribution histogram (svg drawn from numpy counts) is present.
  await expect(profile.getByRole('img', { name: /distribution, \d+ bins/i }).first()).toBeVisible();
});
