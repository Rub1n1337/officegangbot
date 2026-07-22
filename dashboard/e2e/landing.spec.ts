import { test, expect } from '@playwright/test';

test('landing renders with the invite CTA and no untranslated EN', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/'); // EN, clean URL — no longer redirects to the dashboard
  await expect(page.getByRole('heading', { name: /autopilot/i })).toBeVisible({ timeout: 15_000 });
  // Add-to-Server CTA points at the real Discord invite.
  const invite = page.getByRole('link', { name: /Add to Server/i }).first();
  await expect(invite).toBeVisible();
  expect(await invite.getAttribute('href')).toContain('discord.com/api/oauth2/authorize');
  // EN locale must have no leftover Russian.
  const text = await page.locator('body').innerText();
  expect(text.match(/[А-Яа-яЁё]/), 'untranslated Russian on the EN landing').toBeNull();
  expect(errors, 'landing logged client errors').toEqual([]);
});

test('landing in Russian renders localized', async ({ page }) => {
  await page.goto('/ru');
  await expect(page.getByText('Добавить на сервер').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('на автопилоте')).toBeVisible();
});

test('legal pages are not dead-ends — the logo returns home', async ({ page }) => {
  await page.goto('/privacy');
  await expect(page.getByRole('heading', { name: /Privacy/i }).first()).toBeVisible({ timeout: 15_000 });
  await page.getByRole('link', { name: /OfficeGangBot/ }).first().click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: /autopilot/i })).toBeVisible({ timeout: 10_000 });
});
