import { test, expect } from '@playwright/test';

test('premium page renders in EN with no untranslated Russian', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/premium'); // EN, clean URL
  await expect(page.getByRole('heading', { name: /active servers/i })).toBeVisible({ timeout: 15_000 });
  // Add-to-Server CTA points at the real Discord invite.
  const invite = page.getByRole('link', { name: /Add to Server/i }).first();
  await expect(invite).toBeVisible();
  expect(await invite.getAttribute('href')).toContain('discord.com/api/oauth2/authorize');
  // EN locale must have no leftover Russian.
  const text = await page.locator('body').innerText();
  expect(text.match(/[А-Яа-яЁё]/), 'untranslated Russian on the EN premium page').toBeNull();
  expect(errors, 'premium page logged client errors').toEqual([]);
});

test('premium page renders localized in Russian', async ({ page }) => {
  await page.goto('/ru/premium');
  await expect(page.getByText('активных серверов')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Самое популярное')).toBeVisible();
});

test('landing links to the premium page', async ({ page }) => {
  await page.goto('/');
  const link = page.getByRole('link', { name: /Premium/i }).first();
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(/\/premium/);
});
