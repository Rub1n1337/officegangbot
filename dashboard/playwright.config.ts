import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config. Tests live in ./e2e and run against a locally-served production
 * build (the same `next start` Vercel runs). They cover the public surface —
 * the sign-in page, i18n routing and auth redirects — which needs no backend,
 * so they catch routing/build/i18n regressions without a live bot or session.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'pnpm start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
