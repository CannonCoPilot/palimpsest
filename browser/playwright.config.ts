import { defineConfig, devices } from '@playwright/test';

// First E2E harness for the browser app. It drives the *running* dev stack rather than starting
// one, because the golden path needs the Python API (:8080) and its on-disk project store, not just
// the Vite client (:5173). Bring both up first (and, for embedding-based metrics, the MLX embed
// service on :8000 — the bundled golden path deliberately uses a text-only metric to avoid that).
//
//   PALIMPSEST_BASE_URL  client origin   (default http://localhost:5173)
//   PALIMPSEST_API_URL   API origin      (default http://localhost:8080)
export default defineConfig({
  testDir: './e2e',
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.PALIMPSEST_BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
