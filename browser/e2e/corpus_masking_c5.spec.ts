import { test, expect, request as pwRequest, type APIRequestContext } from '@playwright/test';

/**
 * Collections tier — C5 cross-text masking, tracks & liftover in-browser proof (FR-29/FR-30/FR-42).
 *
 * Drives the four C5 done-criteria against the live stack:
 *   1. the corpus-repeat layer renders on the Corpus overview (UI);
 *   2. a cross-text mask CHANGES a downstream alignment (mask-effect API);
 *   3. the cross-text conservation track draws on the root lens (UI);
 *   4. a mask lifted A->B lands at aligned blocks and is dropped on unaligned spans (liftover API).
 *
 * Fixture: the `c5-masking-proof` collection — three tiny synthetic members whose paragraphs are
 * token-disjoint except for two verbatim shared blocks (SHARED in all three -> core; REFRAIN in
 * alpha+beta -> shell), engineered so the corpus graph resolves distinct core/shell/singleton
 * components and the conservation lane shows real variation. Set up via .scratch/c5_setup.py against
 * an isolated .scratch/c5-demo workspace (NOT Sir's shared .scratch/demo). beforeAll re-asserts the
 * graph so the run is idempotent.
 *
 *   PALIMPSEST_BASE_URL / PALIMPSEST_API_URL  → point both at the C5 server on :8092 (single origin).
 */

const API = process.env.PALIMPSEST_API_URL ?? 'http://localhost:8092';
const CID = 'c5-masking-proof';

let members: string[] = [];

test.beforeAll(async () => {
  const api: APIRequestContext = await pwRequest.newContext();
  const cols: { id: string; project_ids: string[] }[] = await (await api.get(`${API}/api/collections`)).json();
  const col = cols.find((c) => c.id === CID);
  if (!col) throw new Error(`${CID} not found — run .scratch/c5_setup.py against the c5-demo workspace first`);
  members = col.project_ids;
  // Idempotently assemble the graph so the tab has cross-text layers on first paint.
  await api.post(`${API}/api/collections/${CID}/corpus-graph`);
  await api.dispose();
});

// done-crit 1 + 3: the Corpus tab renders the corpus-repeat lanes and the root-lens conservation lane.
test('corpus repeat lanes and root-lens conservation lane render on the Corpus overview', async ({ page }) => {
  await page.goto(`/?project=${members[0]}`);
  await page.getByRole('tab', { name: 'Corpus' }).click();

  // Select our proof collection (isolated workspace, but stay explicit + deterministic).
  await page.locator('select').filter({ has: page.locator(`option[value="${CID}"]`) }).selectOption(CID);

  // done-crit 1: one corpus-repeat SVG lane per member with repeats, plus a nonzero phrase-count summary.
  await expect(page.getByRole('img', { name: /corpus repeats/i }).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/\b[1-9]\d* phrases? recurring across/i)).toBeVisible();

  // done-crit 3: conservation lane on the root lens (phyletic suggested root = c5-alpha).
  await expect(page.getByRole('img', { name: /conservation on/i })).toBeVisible();
});

// done-crit 2: a cross-text mask CHANGES a downstream alignment (unmasked vs masked matrix differ).
test('a cross-text mask changes a downstream alignment (mask-effect)', async ({ request }) => {
  const res = await request.get(`${API}/api/collections/${CID}/mask-effect?a=c5-alpha&b=c5-beta`);
  expect(res.ok()).toBeTruthy();
  const d = await res.json();
  expect(d.changed).toBe(true);
  expect(d.mask_intervals).toBeGreaterThan(0);
});

// done-crit 4: a mask lifted A->B lands on aligned blocks and is dropped on unaligned spans.
test('liftover projects aligned spans A->B and drops unaligned spans', async ({ request }) => {
  const rt = await (await request.get(`${API}/api/collections/${CID}/root-track?root=c5-alpha`)).json();
  const core = rt.segments.find((s: { classification: string }) => s.classification === 'core');
  const singleton = rt.segments.find((s: { classification: string }) => s.classification === 'singleton');
  expect(core, 'root-track must expose a core segment').toBeTruthy();
  expect(singleton, 'root-track must expose a singleton (unaligned) segment').toBeTruthy();

  // Aligned (core) span lands on beta's corresponding block (block-granular projection).
  const lands = await (await request.post(`${API}/api/collections/${CID}/liftover`, {
    data: { source_id: 'c5-alpha', target_id: 'c5-beta', intervals: [[core.char_start, core.char_end]] },
  })).json();
  expect(lands.lifted.length).toBeGreaterThan(0);
  expect(lands.dropped.length).toBe(0);

  // Unaligned (singleton) span has no pre-image on beta -> honestly reported as dropped.
  const drops = await (await request.post(`${API}/api/collections/${CID}/liftover`, {
    data: { source_id: 'c5-alpha', target_id: 'c5-beta', intervals: [[singleton.char_start, singleton.char_end]] },
  })).json();
  expect(drops.lifted.length).toBe(0);
  expect(drops.dropped.length).toBeGreaterThan(0);
});
