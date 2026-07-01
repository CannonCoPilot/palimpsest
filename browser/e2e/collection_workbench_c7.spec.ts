import { test, expect, request as pwRequest, type Page } from '@playwright/test';

/**
 * Collections tier — C7 workbench in-browser proof (FR-24/25/31/35/39).
 *
 * Drives the full collection workbench against the live stack on the standing Matthew-Mark validation
 * collection (word-method, NO embeddings): sub-tabs render with backing capabilities; the metric-congruence
 * badge flags cosine as INCONGRUENT (no shared embedding layer) — the honest FR-39 demo; the Members tab
 * re-coordinates the root; the Analyses tab renders corpus analyses with the non-directional caveat; the
 * Sweep tab pre-estimates, prunes on Run, and lists the run; and the Probe tab fails LOUD (honest) rather
 * than silently on an embedding-free collection.
 *
 *   PALIMPSEST_BASE_URL / PALIMPSEST_API_URL  → point both at the isolated C7 server (single origin, :8092).
 *   Fixture: the `matthew-mark-validation` collection in .scratch/validation-mm (word-method, 2 members).
 */

const API = process.env.PALIMPSEST_API_URL ?? 'http://localhost:8092';
const CID = 'matthew-mark-validation';

let members: string[] = [];

test.beforeAll(async () => {
  const api = await pwRequest.newContext();
  const cols: { id: string; project_ids: string[] }[] = await (await api.get(`${API}/api/collections`)).json();
  const col = cols.find((c) => c.id === CID);
  if (!col) throw new Error(`${CID} not found in ${API} workspace — build the validation collection first`);
  members = col.project_ids;
  // Idempotently assemble the graph so Overview/Analyses/Corpus have data on first paint.
  await api.post(`${API}/api/collections/${CID}/corpus-graph`);
  await api.dispose();
});

// CorpusView is conditionally rendered → a fresh goto + select per test keeps each flow independent.
async function openWorkbench(page: Page): Promise<void> {
  await page.goto(`/?project=${members[0]}`);
  await page.getByRole('tab', { name: 'Corpus' }).click();
  await page.locator('select').filter({ has: page.locator(`option[value="${CID}"]`) }).selectOption(CID);
  await expect(page.getByRole('tab', { name: 'Members' })).toBeVisible({ timeout: 30_000 });
}

test('congruence badge flags incongruent cosine on the word-method collection (FR-39)', async ({ page }) => {
  await openWorkbench(page);
  await expect(page.getByRole('status', { name: /incongruent/i })).toBeVisible({ timeout: 30_000 });
});

test('Members tab lists members and a role toggle re-coordinates the root (FR-24/25)', async ({ page }) => {
  await openWorkbench(page);
  await page.getByRole('tab', { name: 'Members' }).click();
  const firstRow = page.locator('tbody tr').first();
  const roleBtn = firstRow.getByRole('button', { name: /^(member|root)$/ });
  await expect(roleBtn).toBeVisible({ timeout: 30_000 });
  const before = (await roleBtn.textContent())?.trim();
  await roleBtn.click();
  await expect(firstRow.getByRole('button', { name: before === 'root' ? 'member' : 'root' })).toBeVisible();
});

test('Analyses tab renders corpus analyses with the non-directional caveat (FR-31)', async ({ page }) => {
  await openWorkbench(page);
  await page.getByRole('tab', { name: 'Analyses' }).click();
  await expect(page.getByText(/Spread across the corpus/i)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/breadth across members|undirected|not.*influence/i).first()).toBeVisible();
});

test('Sweep tab: pre-run estimate, Run prunes the pair space, run manager lists it (FR-35)', async ({ page }) => {
  test.setTimeout(120_000);
  await openWorkbench(page);
  await page.getByRole('tab', { name: 'Sweep' }).click();
  await expect(page.getByText(/member pairs? to sweep/i)).toBeVisible();
  await page.getByRole('button', { name: /run sweep/i }).click();
  // result readout reports pruned counts; the run manager then lists the persisted run
  await expect(page.getByText(/pruned/i).first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/Run manager/i)).toBeVisible();
});

test('Probe tab fails loud (honest) on the embedding-free collection (FR-31)', async ({ page }) => {
  await openWorkbench(page);
  await page.getByRole('tab', { name: 'Probe' }).click();
  await page.getByRole('button', { name: /run probe/i }).click();
  await expect(page.getByRole('alert')).toBeVisible({ timeout: 30_000 });
});
