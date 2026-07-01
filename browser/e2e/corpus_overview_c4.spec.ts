import { test, expect, request as pwRequest, type APIRequestContext } from '@playwright/test';

/**
 * Collections tier — C4 collection overview golden path (FR-33/FR-38).
 *
 * Drives the Corpus tab against the live stack: pick a multi-text collection, assemble its
 * reference-free corpus graph, and render the three linked overview surfaces (Mauve block-map,
 * all-pairs shared-component matrix, phyletic dendrogram). Then exercise the click-through zoom tiers:
 * a matrix cell → that pair's dotplot on Compare, a member → its single-text browser. Also overrides
 * the phyletic root and confirms the tree re-projects.
 *
 * Fixture: the `c4-overview-proof` collection (three nested Douay-Rheims appendix sub-texts, mutually
 * word-overlap aligned) set up via scripts/c4_setup.py against the same workspace. beforeAll ensures
 * the graph is built so the run is idempotent.
 *
 *   PALIMPSEST_BASE_URL / PALIMPSEST_API_URL  → point both at the C4 server (single origin).
 */

const API = process.env.PALIMPSEST_API_URL ?? 'http://localhost:8092';
const CID = 'c4-overview-proof';

let members: string[] = [];

test.beforeAll(async () => {
  const api: APIRequestContext = await pwRequest.newContext();
  const cols: { id: string; project_ids: string[] }[] = await (await api.get(`${API}/api/collections`)).json();
  const col = cols.find((c) => c.id === CID);
  if (!col) throw new Error(`${CID} not found — run scripts/c4_setup.py against the workspace first`);
  members = col.project_ids;
  // Idempotently assemble the graph so the tab has data on first paint.
  await api.post(`${API}/api/collections/${CID}/corpus-graph`);
  await api.dispose();
});

test('corpus overview renders block-map, all-pairs matrix, and phyletic tree; root override re-projects', async ({ page }) => {
  await page.goto(`/?project=${members[0]}`);
  await page.getByRole('tab', { name: 'Corpus' }).click();

  // Select our proof collection (there are several collections in the demo workspace).
  const collectionSelect = page.locator('select').filter({ has: page.locator(`option[value="${CID}"]`) });
  await collectionSelect.selectOption(CID);

  // Pangenome summary badge shows the core count from the assembled graph.
  await expect(page.getByText(/\bcore\b/).first()).toBeVisible({ timeout: 30_000 });

  // Block-map: one lane per member (SVG role=img "<member> block map").
  const lanes = page.getByRole('img', { name: /block map/i });
  await expect(lanes.first()).toBeVisible({ timeout: 30_000 });
  expect(await lanes.count()).toBe(members.length);

  // Phyletic tree renders and offers a root override; the suggested root is marked.
  await expect(page.getByRole('img', { name: 'Phyletic tree' })).toBeVisible();
  const rootSelect = page.locator('select').filter({ has: page.locator('option', { hasText: '(suggested)' }) });
  await expect(rootSelect).toBeVisible();
  const before = await rootSelect.inputValue();
  const other = members.find((m) => m !== before)!;
  await rootSelect.selectOption(other);
  await expect(rootSelect).toHaveValue(other); // tree re-fetched with the chosen root
});

// Each zoom-tier click is its own test: navigating away re-mounts CorpusView (it is conditionally
// rendered), so a fresh goto + collection select keeps each flow independent and deterministic.
async function openCorpus(page: import('@playwright/test').Page): Promise<void> {
  await page.goto(`/?project=${members[0]}`);
  await page.getByRole('tab', { name: 'Corpus' }).click();
  await page.locator('select').filter({ has: page.locator(`option[value="${CID}"]`) }).selectOption(CID);
  await expect(page.getByRole('img', { name: 'Phyletic tree' })).toBeVisible({ timeout: 30_000 });
}

test('click-through: an all-pairs matrix cell opens that pair on the Compare dotplot', async ({ page }) => {
  await openCorpus(page);
  // Target an enabled cell (a pair that actually shares a component); 0-share cells are disabled.
  await page.locator('button[title*="open dotplot"]:not([disabled])').first().click();
  await expect(page.getByRole('tab', { name: 'Compare' })).toHaveAttribute('aria-selected', 'true');
});

test('click-through: a block-map member label opens its single-text browser', async ({ page }) => {
  await openCorpus(page);
  await page.locator('button[title*="single-text browser"]').first().click();
  await expect(page.getByRole('tab', { name: 'Browser' })).toHaveAttribute('aria-selected', 'true');
});
