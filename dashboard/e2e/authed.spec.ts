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

test('a feature card enables in place — the core onboarding loop', async ({ page }) => {
  // "Включить" used to be a link to a disabled config form the user had to
  // enable again — the Enable button didn't enable. It now enables from the
  // grid, so the card flips to "Настроить" and the user stays on the overview
  // (the setup banner counts from the same cache, so it ticks up too).
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText('Здоровье сервера').first()).toBeVisible({ timeout: 15_000 });
  const enable = page.getByRole('button', { name: 'Включить' });
  // Wait for the feature grid to render before counting — it loads after the
  // header, so reading the count too early sees zero.
  await expect(enable.first()).toBeVisible({ timeout: 15_000 });
  const before = await enable.count();
  await enable.first().click();
  await expect(enable).toHaveCount(before - 1, { timeout: 5_000 });
  await expect(page).toHaveURL(new RegExp(`/guilds/${GUILD_ID}/settings`)); // stayed put
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

test('keyboard focus is visible (WCAG 2.4.7)', async ({ page }) => {
  // The button theme cleared Chakra's focus shadow and Chakra set a transparent
  // outline, so keyboard users saw no focus anywhere. Tab to a control and
  // assert the focus ring has a real (non-transparent) colour.
  await page.goto(`/ru/guilds/${GUILD_ID}/analytics`);
  await expect(page.getByText('Тренды и модерация').first()).toBeVisible({ timeout: 15_000 });
  for (let i = 0; i < 6; i++) await page.keyboard.press('Tab');
  const ring = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return null;
    const s = getComputedStyle(el);
    // Alpha 0 == invisible. Parse the outline colour's alpha.
    const m = s.outlineColor.match(/rgba?\([^)]*?(?:,\s*([0-9.]+))?\)$/);
    const alpha = m && m[1] !== undefined ? parseFloat(m[1]) : 1;
    return { color: s.outlineColor, width: s.outlineWidth, alpha };
  });
  expect(ring, 'nothing is focused after tabbing').not.toBeNull();
  expect(ring!.alpha, `focus ring is invisible (${ring!.color})`).toBeGreaterThan(0);
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

test('the server picker survives a Discord 429 on a hard reload', async ({ page }) => {
  // /users/@me/guilds is strictly rate-limited and a hard reload wipes the
  // in-memory query cache — so frequent reloaders got 429 and a dead picker,
  // which they "fixed" with another reload (feeding the same rate limit).
  // useGuilds persists the last-known list and serves it as placeholder data.
  await page.goto('/ru/user/home');
  await expect(page.getByText('Trials Gang').first()).toBeVisible({ timeout: 15_000 });
  expect(await page.evaluate(() => localStorage.getItem('cached-user-guilds'))).toContain('Trials Gang');

  await page.route('https://discord.com/api/**', (route) => {
    if (route.request().url().includes('/users/@me/guilds'))
      return route.fulfill({ status: 429, contentType: 'application/json', body: '{"retry_after": 10}' });
    return route.fallback();
  });
  await page.reload();
  await expect(page.getByText('Trials Gang').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/Не удалось загрузить ваши серверы/)).toHaveCount(0);
});

test('nav links are never minted with a bogus guild id', async ({ page }) => {
  // Root cause of the /guilds/undefined storm: during hydration the sidebar
  // rendered hrefs from an empty router.query, and an early click navigated to
  // /guilds/undefined for real (the redirect then dumped the user on
  // /user/home, losing their place). Nav ids now come from the URL path
  // (useGuildId), and while unknown the items carry no href at all.

  // 1) The raw served HTML — exactly what exists before hydration — must have
  // no anchor pointing at a bogus guild. (__NEXT_DATA__ metadata legitimately
  // contains the route pattern as JSON; only href attributes count.)
  const resp = await page.request.get(`/ru/guilds/${GUILD_ID}/settings`);
  const bogus = (await resp.text()).match(/href="[^"]*guilds\/(undefined|\[guild\])[^"]*"/g) ?? [];
  expect(bogus, 'static HTML contains links with a bogus guild id').toEqual([]);

  // 2) Clicking a sidebar link as early as it exists lands on the right page.
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('link', { name: /Модерация/ }).first().click({ timeout: 10_000 });
  await expect(page).toHaveURL(new RegExp(`/guilds/${GUILD_ID}/moderation`), { timeout: 10_000 });
});

test('a /guilds/undefined URL redirects home without hammering the API', async ({ page }) => {
  // During hydration the sidebar briefly renders hrefs from an empty
  // router.query, so an early click landed on /guilds/undefined/... — a dead
  // page whose every query 403'd on /api/bot/.../undefined (seen live in the
  // user's console), and the palette persisted it under "recents". Three
  // layers now stop it: query gates validate the id, the layout redirects, and
  // recents only keep real guild paths.
  const bad: string[] = [];
  page.on('request', (r) => {
    if (r.url().includes('/api/bot/') && r.url().includes('/undefined')) bad.push(r.url());
  });
  await page.goto('/ru/guilds/undefined/moderation');
  await page.waitForURL(/\/user\/home/, { timeout: 15_000 });
  await page.waitForTimeout(1000);
  expect(bad, 'API requests fired with an undefined guild id').toEqual([]);
});

test('sidebar: nav and enabled-feature icons share one optical column', async ({ page }) => {
  // The nav icons are 20px; the enabled-feature icons below were 18px with a
  // different gap, so the icon and text columns drifted ~3px apart mid-sidebar.
  // They now share the 20px box and 12px gap.
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText('Здоровье сервера').first()).toBeVisible({ timeout: 15_000 });
  const navIcon = await page.getByRole('link', { name: /Модерация/ }).first()
    .evaluate((el) => (el.firstElementChild as HTMLElement).getBoundingClientRect().width);
  const featIcon = await page.getByRole('link', { name: /Уровни/ }).first()
    .evaluate((el) => (el.firstElementChild as HTMLElement).getBoundingClientRect().width);
  expect(Math.abs(navIcon - featIcon), 'sidebar icon boxes are different sizes').toBeLessThanOrEqual(2);
});

test('the number stepper is a comfortable tap target', async ({ page }) => {
  // The +/- buttons were 28px — hard to hit on a phone. An invisible ::after
  // hit-zone can't help here (the feature-form cards clip overflow:hidden and
  // the value label paints over any inward extension), so the buttons are now a
  // real 36px. Compensation for imperfect aim, done reliably.
  await page.goto(`/guilds/${GUILD_ID}/features/anti-raid`);
  await expect(page.getByText(/Join threshold|Порог заходов/).first()).toBeVisible({ timeout: 15_000 });
  const box = (await page.locator('button[aria-label="decrease"]').first().boundingBox())!;
  expect(Math.round(box.width), 'stepper button too small to tap').toBeGreaterThanOrEqual(36);
  expect(Math.round(box.height), 'stepper button too small to tap').toBeGreaterThanOrEqual(36);
});

test('palette: arrow keys autoscroll the active row into view', async ({ page }) => {
  // The palette list is a 340px overflow box with ~16 default commands. Arrow
  // keys moved the highlight but never scrolled, so past the fold you navigated
  // blind. The active row now scrollIntoViews (with scroll-padding so it never
  // sticks to the edge).
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText('Здоровье сервера').first()).toBeVisible({ timeout: 15_000 });
  await page.keyboard.press('Control+k');
  const input = page.getByPlaceholder(/Перейти к серверу/);
  await expect(input).toBeVisible();
  await input.click();
  await page.mouse.move(20, 20); // cursor well away from the list
  for (let i = 0; i < 14; i++) await input.press('ArrowDown');
  await page.waitForTimeout(250);
  const res = await page.evaluate(() => {
    const modal = document.querySelector('.chakra-modal__content')!;
    const scroller = Array.from(modal.querySelectorAll('*')).find((e) => getComputedStyle(e).overflowY === 'auto') as HTMLElement;
    const rows = Array.from(scroller.children) as HTMLElement[];
    const active = rows.find((r) => getComputedStyle(r).backgroundColor !== 'rgba(0, 0, 0, 0)');
    if (!active) return { visible: false, scrollTop: 0 };
    const sr = scroller.getBoundingClientRect(), ar = active.getBoundingClientRect();
    return { visible: ar.top >= sr.top - 1 && ar.bottom <= sr.bottom + 1, scrollTop: Math.round(scroller.scrollTop) };
  });
  expect(res.visible, 'active row scrolled out of view').toBeTruthy();
  expect(res.scrollTop, 'list did not autoscroll to follow the arrows').toBeGreaterThan(0);
});

test('palette: a stationary cursor does not steal keyboard selection', async ({ page }) => {
  // Keyboard scroll slides a fresh row under the still cursor, firing mouseEnter.
  // That used to yank the selection back; hover now only counts after a real
  // pointer move.
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText('Здоровье сервера').first()).toBeVisible({ timeout: 15_000 });
  await page.keyboard.press('Control+k');
  const input = page.getByPlaceholder(/Перейти к серверу/);
  await expect(input).toBeVisible();
  await input.click();
  const box = await page.locator('.chakra-modal__content').boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + 200);
  for (let i = 0; i < 10; i++) await input.press('ArrowDown');
  await page.waitForTimeout(150);
  const activeText = await page.evaluate(() => {
    const modal = document.querySelector('.chakra-modal__content')!;
    const scroller = Array.from(modal.querySelectorAll('*')).find((e) => getComputedStyle(e).overflowY === 'auto') as HTMLElement;
    const active = (Array.from(scroller.children) as HTMLElement[]).find((r) => getComputedStyle(r).backgroundColor !== 'rgba(0, 0, 0, 0)');
    return (active?.textContent ?? 'none').replace(/\s+/g, ' ').slice(0, 30);
  });
  expect(activeText, 'hover under a still cursor stole the keyboard selection').not.toMatch(/Обзор|Модерация/);
});

test('analytics charts render through the mount-gate with no NaN geometry', async ({ page }) => {
  // ApexCharts measures its parent on mount; a 0-width container (first client
  // paint, an un-laid-out SimpleGrid column, a device-emulation viewport) made
  // every length compute to NaN, spamming the console with "<svg> width NaN"
  // and "translate(NaN, 0)" on animation frames. StyledChart now gates the
  // mount on a real width and disables the animation. This asserts the charts
  // still mount (the gate can't hide them forever) and that a small→large
  // resize produces no NaN.
  const nan: string[] = [];
  page.on('console', (m) => { if (/NaN/i.test(m.text())) nan.push(m.text().slice(0, 80)); });
  page.on('pageerror', (e) => { if (/NaN/i.test(e.message)) nan.push(e.message.slice(0, 80)); });
  await page.goto(`/ru/guilds/${GUILD_ID}/analytics`);
  await expect(page.getByText(/Тренды и модерация/).first()).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.apexcharts-canvas').first()).toBeVisible({ timeout: 15_000 });
  expect(await page.locator('.apexcharts-canvas svg').count()).toBeGreaterThan(0);
  await page.setViewportSize({ width: 380, height: 900 });
  await page.waitForTimeout(400);
  await page.setViewportSize({ width: 1300, height: 900 });
  await page.waitForTimeout(800);
  expect(nan, 'a chart emitted NaN geometry').toEqual([]);
});

test('a botless guild answers once and offers a real Discord invite', async ({ page }) => {
  // A 404 is a definitive "bot not in this guild": it used to be retried 3x AND
  // polled every 8s by the stats query, filling the console forever on the
  // NotJoined page. And the picker's "Add to another server" linked to
  // /user/home — the Enable-invite path simply didn't exist there.
  const J404 = { status: 404, contentType: 'application/json', body: '{"detail":"Guild not found"}' };
  await page.route('**/api/bot/**', async (route) => {
    const p = new URL(route.request().url()).pathname;
    if (p.endsWith(`/guilds/${GUILD_ID}`) || p.endsWith('/stats')) return route.fulfill(J404);
    return route.fallback();
  });
  let statsHits = 0;
  page.on('request', (r) => { if (r.url().includes('/stats')) statsHits++; });
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  // Old behaviour produced 4+ hits within this window from retries alone.
  await page.waitForTimeout(6_000);
  expect(statsHits, 'a definitive 404 was retried/polled').toBeLessThanOrEqual(2);

  const invite = page.locator('a', { hasText: /Invite|Пригласить/i }).first();
  await expect(invite).toBeVisible({ timeout: 5_000 });
  const href = (await invite.getAttribute('href')) ?? '';
  expect(href).toContain('discord.com/api/oauth2/authorize');
  expect(href).toContain(`guild_id=${GUILD_ID}`);
});

test('the server picker labels botless servers and its add-link opens Discord', async ({ page }) => {
  await page.route('**/api/me/guilds', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ botReachable: true, guilds: [] }) })
  );
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.goto(`/ru/guilds/${GUILD_ID}/settings`);
  await expect(page.getByText(/Здоровье сервера/).first()).toBeVisible({ timeout: 15_000 });
  await page.getByText('Сменить сервер').click();
  await expect(page.getByText('ВАШИ СЕРВЕРЫ')).toBeVisible();
  await expect(page.getByText('нет бота').first()).toBeVisible();
  const href = (await page.locator('a', { hasText: 'Добавить на другой сервер' }).first().getAttribute('href')) ?? '';
  expect(href, 'add-server must invite the bot, not link to /user/home').toContain('discord.com/api/oauth2/authorize');
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
