import { test, expect, type Page } from '@playwright/test';
import { signIn, mockBackend, GUILD_ID } from './fixtures';

/**
 * Renders the product behind the login and asserts on what a human sees.
 *
 * The other spec covers the public surface; everything that makes this a
 * dashboard — the Overview, Moderation, Tickets, feature forms — was never
 * rendered in CI. That is the layer where the bugs nobody notices live: a
 * page that throws on real data, a card that says "Disabled" forever, an
 * untranslated string on the English locale. Backends are mocked (see
 * fixtures.ts), so these run with no bot, no Postgres and no network.
 */

test.beforeEach(async ({ context, page }) => {
  await signIn(context);
  await mockBackend(page);
});

/** Fails the test on any client-side exception or console error. */
function watchForErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    // Discord CDN avatars aren't reachable from the test runner.
    if (/Failed to load resource|net::ERR|404/i.test(text)) return;
    errors.push(`console: ${text}`);
  });
  return errors;
}

const PAGES: Array<{ name: string; path: string; expect: RegExp }> = [
  { name: 'Overview', path: `/guilds/${GUILD_ID}/settings`, expect: /Server health|Здоровье сервера/ },
  { name: 'Moderation', path: `/guilds/${GUILD_ID}/moderation`, expect: /Warnings, punishments|Предупреждения, наказания/ },
  { name: 'Members', path: `/guilds/${GUILD_ID}/members`, expect: /Search & moderation|Поиск и модерация/ },
  { name: 'Tickets', path: `/guilds/${GUILD_ID}/tickets`, expect: /Support|Поддержка/ },
  { name: 'Analytics', path: `/guilds/${GUILD_ID}/analytics`, expect: /Trends & moderation|Тренды и модерация/ },
  { name: 'Audit log', path: `/guilds/${GUILD_ID}/audit`, expect: /Dashboard activity|Активность дашборда/ },
  { name: 'Server picker', path: '/user/home', expect: /Pick a server|Выберите сервер/ },
  { name: 'Profile', path: '/user/profile', expect: /Discord account|Аккаунт Discord/ },
];

for (const p of PAGES) {
  test(`${p.name} renders without client errors`, async ({ page }) => {
    const errors = watchForErrors(page);
    await page.goto(p.path);
    await expect(page.getByText(p.expect).first()).toBeVisible({ timeout: 15_000 });
    // An "Application error" overlay is Next's client-crash screen — the exact
    // failure that shipped when the profile page lost its session guard.
    await expect(page.getByText(/Application error/i)).toHaveCount(0);
    expect(errors, `${p.name} logged client errors`).toEqual([]);
  });
}

// id -> a string the rendered form must show, so a form that silently fails to
// mount can't pass.
const FEATURES: Record<string, RegExp> = {
  'automod': /Dry-run|Пробный режим/,
  'anti-raid': /Join threshold|Порог заходов/,
  'tickets': /Support role|Роль поддержки/,
  'levels': /XP multipliers|Множители опыта/,
  'rules': /Rules Channel|Канал правил/,
  'welcome-message': /Auto-role|Авто-роль/,
  'moderation': /Warning auto-escalation|Авто-эскалация/,
  'logging': /Punishment Log|Канал лога наказаний/,
  'verification': /Verified role|Роль верифицированного/,
  'reaction-menus': /Menu style|Стиль меню|Add menu|Добавить меню/,
  'scheduled-messages': /Add scheduled message|Добавить отложенное/,
};

for (const [feature, marker] of Object.entries(FEATURES)) {
  test(`feature form renders: ${feature}`, async ({ page }) => {
    const errors = watchForErrors(page);
    await page.goto(`/guilds/${GUILD_ID}/features/${feature}`);
    await expect(page.getByText(marker).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Application error/i)).toHaveCount(0);
    expect(errors, `${feature} form logged client errors`).toEqual([]);
  });
}

test('the guild landing redirects to the Overview', async ({ page }) => {
  // /guilds/[id] used to serve a pre-Iris page the redesign never touched.
  await page.goto(`/guilds/${GUILD_ID}`);
  await expect(page).toHaveURL(new RegExp(`/guilds/${GUILD_ID}/settings`));
});

test('English locale has no Russian left in the shell', async ({ page }) => {
  // The Iris screens were authored in Russian and translated via ui-text.ts;
  // a missing entry falls back to the Russian source, which is invisible until
  // an English speaker opens the page.
  await page.goto(`/en/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText(/Server health/).first()).toBeVisible({ timeout: 15_000 });
  const text = (await page.locator('main, body').first().innerText()).replace(/Trials Gang/g, '');
  expect(text, 'Cyrillic text on the English locale').not.toMatch(/[А-Яа-яЁё]/);
});

test('Russian locale has no untranslated shell strings', async ({ page }) => {
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText(/Здоровье сервера/).first()).toBeVisible({ timeout: 15_000 });
  // The nav is the part that regressed before: it stayed English while the
  // page body was Russian.
  await expect(page.getByRole('link', { name: /Обзор/ }).first()).toBeVisible();
  await expect(page.getByRole('link', { name: /Модерация/ }).first()).toBeVisible();
});

test('overlays are localized too — palette, notifications, server picker', async ({ page }) => {
  // Everything above reads the *page*. Overlays aren't in the DOM until they
  // open, so a Russian string in the English ⌘K palette (which shipped) sailed
  // past every check. Open them and read them.
  await page.goto(`/en/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText(/Server health/).first()).toBeVisible({ timeout: 15_000 });

  const cyrillic = /[А-Яа-яЁё]/;

  // ⌘K command palette. Wait for a guild-scoped entry before reading it: the
  // palette lists only "Switch server" until router.query.guild hydrates, and
  // reading it too early passes vacuously — which is exactly how this test
  // first "passed" against the bug it was written for.
  await page.keyboard.press('Control+k');
  const palette = page.getByPlaceholder(/Jump to a server or feature/);
  await expect(palette).toBeVisible();
  await expect(page.getByText('Stats')).toBeVisible();  // the Overview entry's hint
  const paletteText = (await page.locator('.chakra-modal__content').first().innerText())
    .replace(/Trials Gang/g, '');
  expect(paletteText.length, 'palette read before its commands rendered').toBeGreaterThan(120);
  expect(paletteText, 'Cyrillic in the English command palette').not.toMatch(cyrillic);
  await page.keyboard.press('Escape');

  // Notifications popover
  await page.getByTitle('Notifications').click();
  const notifications = page.getByText(/All quiet|Notifications/).first();
  await expect(notifications).toBeVisible();
  const notifText = await page.locator('.chakra-popover__content').first().innerText();
  expect(notifText, 'Cyrillic in the English notifications popover').not.toMatch(cyrillic);
  await page.keyboard.press('Escape');

  // Server picker
  await page.getByText('Switch server').click();
  await expect(page.getByText('YOUR SERVERS')).toBeVisible();
  const pickerText = (await page.locator('.chakra-popover__content').first().innerText())
    .replace(/Trials Gang/g, '');
  expect(pickerText, 'Cyrillic in the English server picker').not.toMatch(cyrillic);
});

test('the Russian palette is Russian — names, settings and footer', async ({ page }) => {
  // The mirror of the test above, and the one that matters more: the palette
  // read feature names straight from the English config, its setting labels
  // were English-only, and the footer hints were never translated at all. The
  // "no Cyrillic on /en" checks are blind to all three by construction.
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText(/Здоровье сервера/).first()).toBeVisible({ timeout: 15_000 });

  await page.keyboard.press('Control+k');
  await expect(page.getByText('Статистика')).toBeVisible();  // wait out router hydration

  // Read the default list — feature names and the footer — before typing:
  // typing filters the list down and would leave almost nothing to check.
  const text = (await page.locator('.chakra-modal__content').first().innerText())
    // The server's own name and the literal key cap stay as they are.
    .replace(/Trials Gang/g, '')
    .replace(/\besc\b/g, '');
  expect(text.length, 'palette read before its commands rendered').toBeGreaterThan(120);
  expect(text, 'Latin text in the Russian command palette').not.toMatch(/[A-Za-z]/);

  // And a settings hit, which only appears once the admin types.
  await page.keyboard.type('страйк');
  await expect(page.getByText('Система страйков')).toBeVisible();
});

/**
 * Text that is Latin on purpose and must not fail the check below: slash
 * commands, @-mentions, brand names, template tokens, and the fixture's own
 * data (a server name, a banned word, a rules message).
 */
function stripLegitimateLatin(text: string): string {
  return text
    .replace(/\/[a-z_]+/g, ' ')             // /rank, /season_reset
    .replace(/@[a-zA-Z]+/g, ' ')            // @everyone, @here, @NewMember
    .replace(/\{[^}]*\}/g, ' ')             // {user.mention}, {server.name}
    .replace(/https?:\S+|[a-z0-9-]+\.(gg|com|org)/g, ' ')
    .replace(/OfficeGangBot|Trials Gang|e2e-admin|AutoMod|Discord|BOT|XP|ID|regex/g, ' ')
    .replace(/Loading\.\.\./g, ' ');        // Chakra's Spinner sr-only label
}

const RU_FEATURE_FORMS = [
  'automod', 'anti-raid', 'tickets', 'levels', 'rules', 'welcome-message',
  'moderation', 'logging', 'verification', 'reaction-menus', 'scheduled-messages',
];

for (const feature of RU_FEATURE_FORMS) {
  test(`the ${feature} form is Russian on /ru`, async ({ page }) => {
    // The form tests above only assert a marker renders and nothing throws.
    // Nobody checked what language the forms speak, and the answer was: partly
    // English. Every page said "Enabled"/"Disabled", the seven disabled ones
    // said "This feature is off — Enable it to configure and save its
    // settings.", and the counters said "1 banned word".
    await page.goto(`/ru/guilds/${GUILD_ID}/features/${feature}`);
    await expect(page.getByText(/Включено|Выключено/).first()).toBeVisible({ timeout: 15_000 });

    const text = stripLegitimateLatin(await page.locator('main, body').first().innerText());
    expect(text, `English text on the Russian ${feature} form`).not.toMatch(/[A-Za-z]{3}/);
  });
}

// 320px is the narrowest phone still in use (iPhone SE 1st gen, small Android).
// A page wider than its viewport scrolls sideways — the classic mobile break —
// and it's invisible at the 375px the design targets: a fixed 344px popover, or
// two buttons that won't wrap, only spill once the screen is under their width.
const MOBILE_PAGES: Array<[string, string]> = [
  ['Overview', `/guilds/${GUILD_ID}/settings`],
  ['Moderation', `/guilds/${GUILD_ID}/moderation`],
  ['Members', `/guilds/${GUILD_ID}/members`],
  ['Tickets', `/guilds/${GUILD_ID}/tickets`],
  ['Analytics', `/guilds/${GUILD_ID}/analytics`],
  ['Audit', `/guilds/${GUILD_ID}/audit`],
  ['Profile', '/user/profile'],
  ['Form: automod', `/guilds/${GUILD_ID}/features/automod`],
  ['Form: levels', `/guilds/${GUILD_ID}/features/levels`],
];

for (const [name, path] of MOBILE_PAGES) {
  test(`no sideways scroll at 320px — ${name}`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 780 });
    await page.goto(`/ru${path}`);
    await page.waitForTimeout(1500);
    const { scrollW, clientW } = await page.evaluate(() => ({
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
    }));
    expect(scrollW, `${name} scrolls sideways at 320px (something is wider than the screen)`).toBeLessThanOrEqual(
      clientW + 1
    );
  });
}

test('audit rows do not crush their text to a sliver on a phone', async ({ page }) => {
  // The sideways-scroll check above is blind to this: a fixed date column and a
  // wide action badge squeezed the actor+description text to ~40px, so it wrapped
  // one character per line — tall, not wide, no overflow. Assert the text block
  // that carries "<actor> <action>" is a readable width at phone size.
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`/ru/guilds/${GUILD_ID}/audit`);
  const line = page.getByText(/изменил настройки/).first();
  await expect(line).toBeVisible({ timeout: 15_000 });
  const box = await line.boundingBox();
  expect(box, 'audit description has no box').not.toBeNull();
  // Crushed-to-a-column is ~40px; a healthy line on a 375px screen is 200px+.
  expect(box!.width, 'audit text is crushed into a narrow column on mobile').toBeGreaterThan(150);
});

test('Tickets list shows the subject, not just the opener', async ({ page }) => {
  await page.goto(`/ru/guilds/${GUILD_ID}/tickets`);
  await expect(page.getByText('Cannot access the voice channels')).toBeVisible({ timeout: 15_000 });
});

test('Moderation surfaces a pending appeal with its decision buttons', async ({ page }) => {
  await page.goto(`/ru/guilds/${GUILD_ID}/moderation`);
  await expect(page.getByText('appealer')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: /Одобрить/ })).toBeVisible();
});

test('a stale chunk after a deploy self-recovers instead of needing a hard reload', async ({ page }) => {
  // The dashboard is a client-rendered SPA; a deploy renames every chunk and
  // deletes the old ones, so a tab open across the deploy asks for a chunk that
  // 404s and sits broken until Ctrl+Shift+R. useChunkErrorRecovery reloads once.
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText(/Здоровье сервера/).first()).toBeVisible({ timeout: 15_000 });

  await page.evaluate(() => ((window as unknown as { __alive: boolean }).__alive = true));
  await page.evaluate(() => {
    const err = Object.assign(new Error('Loading chunk 42 failed'), { name: 'ChunkLoadError' });
    window.dispatchEvent(
      new PromiseRejectionEvent('unhandledrejection', { promise: Promise.reject(err), reason: err })
    );
  });
  await page.waitForTimeout(1200);
  // A reload wipes the window tag; an unrelated error would have left it set.
  expect(
    await page.evaluate(() => (window as unknown as { __alive?: boolean }).__alive),
    'the page did not reload itself on a chunk-load error'
  ).toBeUndefined();

  // And an unrelated rejection must NOT reload, or the app would thrash.
  await expect(page.getByText(/Здоровье сервера/).first()).toBeVisible({ timeout: 15_000 });
  await page.evaluate(() => ((window as unknown as { __alive: boolean }).__alive = true));
  await page.evaluate(() => {
    const err = new Error('an unrelated runtime error');
    window.dispatchEvent(
      new PromiseRejectionEvent('unhandledrejection', { promise: Promise.reject(err), reason: err })
    );
  });
  await page.waitForTimeout(800);
  expect(
    await page.evaluate(() => (window as unknown as { __alive?: boolean }).__alive),
    'an unrelated error should not trigger a reload'
  ).toBe(true);
});
