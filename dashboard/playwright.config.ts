import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config. Tests live in ./e2e and run against a locally-served production
 * build (the same `next start` Vercel runs).
 *
 * smoke.spec.ts covers the public surface (sign-in, i18n routing, auth
 * redirects). authed.spec.ts renders the product behind the login: it mints a
 * session cookie and serves every backend call from e2e/fixtures.ts, so the
 * real pages and feature forms render deterministically with no bot, no
 * Postgres and no network.
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
