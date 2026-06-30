import { test, expect } from '@playwright/test';

// These exercise the public, no-auth surface: rendering, i18n locale routing,
// and the auth middleware redirects. They guard against regressions like the
// i18n config disappearing or the middleware no longer gating private routes.

test('sign-in page renders in English', async ({ page }) => {
  await page.goto('/auth/signin');
  await expect(page.getByText('Login with Discord')).toBeVisible();
});

test('sign-in page renders in Russian under /ru', async ({ page }) => {
  await page.goto('/ru/auth/signin');
  // The whole locale chain works: /ru prefix -> router.locale=ru -> RU strings.
  await expect(page.getByText('Войти через Discord')).toBeVisible();
});

test('unauthenticated guild route is redirected to sign-in', async ({ page }) => {
  await page.goto('/guilds/123456789012345678');
  await expect(page).toHaveURL(/\/auth\/signin/);
});

test('unauthenticated /user/home is redirected to sign-in', async ({ page }) => {
  await page.goto('/user/home');
  await expect(page).toHaveURL(/\/auth\/signin/);
});

test('root redirects toward sign-in when unauthenticated', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/auth\/signin/);
});
