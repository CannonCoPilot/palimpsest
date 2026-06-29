import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [tailwindcss(), react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // Unit tests live under src/; Playwright owns e2e/ (see playwright.config.ts).
    // Without this, vitest's default glob would try to collect the e2e .spec files.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/**/*.d.ts',
        'src/main.tsx',
        'src/vite-env.d.ts',
      ],
      // Ratchet, not a target: frontend coverage is currently low (the React
      // components need a dedicated testing effort). These floors only prevent
      // regression — raise them as coverage improves.
      thresholds: {
        statements: 2,
        branches: 0.8,
        functions: 2,
        lines: 2,
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
      '/data': 'http://localhost:8080',
    },
  },
});
