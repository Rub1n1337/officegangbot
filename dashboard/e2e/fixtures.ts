import type { Page, BrowserContext } from '@playwright/test';

/**
 * Signs a test into the dashboard and serves every backend call from fixtures.
 *
 * The session cookie is plain JSON when SESSION_SECRET is unset (see
 * utils/auth/crypto.ts), which is the case for the e2e build — so a test can
 * mint one directly instead of driving the Discord OAuth flow. Everything the
 * pages fetch (the bot proxy, the guild list, Discord itself) is routed to the
 * fixtures below, so the authed product renders deterministically with no bot,
 * no Postgres and no network.
 */

export const GUILD_ID = '1371294466740326400';

const SESSION = {
  access_token: 'e2e-access-token',
  token_type: 'Bearer',
  expires_in: 604800,
  refresh_token: 'e2e-refresh-token',
  scope: 'identify guilds',
  obtained_at: Date.now(),
};

const USER = {
  id: '1208589864920944681',
  username: 'e2e-admin',
  discriminator: '0',
  avatar: null,
};

const GUILDS = [
  // permissions carries the ADMINISTRATOR bit (0x8) — config.guild.filter keeps
  // only guilds the user administrates.
  { id: GUILD_ID, name: 'Trials Gang', icon: null, owner: true, permissions: '8' },
];

const GUILD_INFO = {
  id: GUILD_ID,
  name: 'Trials Gang',
  icon: null,
  member_count: 7,
  owner_id: '1',
  locale: 'ru',
  settings: {},
  enabledFeatures: ['levels', 'tickets', 'automod', 'logging'],
};

const STATS = {
  id: GUILD_ID,
  name: 'Trials Gang',
  icon: null,
  online: true,
  member_count: 7,
  channel_count: 17,
  text_channels: 13,
  voice_channels: 1,
  role_count: 8,
  latency_ms: 69,
  enabled_feature_count: 4,
  open_tickets: 2,
  history: [
    { day: '2026-07-13', messages: 120, memberCount: 5 },
    { day: '2026-07-14', messages: 180, memberCount: 6 },
    { day: '2026-07-15', messages: 240, memberCount: 7 },
  ],
  top_xp: [{ name: 'alpha', level: 12, xp: 9000 }],
};

const MODERATION = {
  warnings: [
    { id: 1, userId: '555', userName: 'member', reason: 'spam', moderatorName: 'mod', createdAt: '2026-07-14T10:00:00Z' },
  ],
  punishments: [
    { userId: '556', userName: 'muted-one', type: 'mute', reason: 'flood', expiresAt: '2026-07-16T10:00:00Z' },
  ],
  strikes: {
    enabled: true, expiryHours: 24, muteAt: 3, kickAt: 5, banAt: 0,
    users: [{ userId: '557', userName: 'striker', count: 2, lastStrikeAt: '2026-07-15T09:00:00Z', nextDecayAt: '2026-07-16T09:00:00Z' }],
  },
  appeals: {
    enabled: true,
    items: [
      { id: 1, userId: '558', userName: 'appealer', reason: 'sorry', status: 'pending', createdAt: '2026-07-15T08:00:00Z', decidedByName: null },
    ],
  },
};

const TICKETS = [
  {
    id: 1, channelId: '900', openerId: '555', openerName: 'member', priority: 'high',
    subject: 'Cannot access the voice channels', status: 'open',
    openedAt: '2026-07-15T08:00:00Z', closedAt: null, closedById: null, closedByName: null,
    closeComment: null, hasTranscript: false,
  },
  {
    id: 2, channelId: '901', openerId: '556', openerName: 'other', priority: 'low',
    subject: null, status: 'closed',
    openedAt: '2026-07-10T08:00:00Z', closedAt: '2026-07-11T08:00:00Z',
    closedById: '10', closedByName: 'mod', closeComment: 'resolved', hasTranscript: true,
  },
];

const AUDIT = [
  { id: 1, actorId: '10', actorName: 'mod', action: 'ban', target: '555', detail: 'raiding', createdAt: '2026-07-15T10:00:00Z' },
  { id: 2, actorId: '10', actorName: 'mod', action: 'update_feature', target: 'automod', detail: null, createdAt: '2026-07-14T10:00:00Z' },
];

const ANALYTICS = {
  days: 30,
  heatmap: [{ weekday: 1, hour: 12, count: 40 }, { weekday: 2, hour: 18, count: 90 }],
  modActionsByDay: [{ day: '2026-07-14', action: 'ban', count: 2 }],
  automodByDay: [{ day: '2026-07-14', count: 5 }],
  ticketsOpenedByDay: [{ day: '2026-07-14', count: 3 }],
  ticketsClosedByDay: [{ day: '2026-07-14', count: 1 }],
  avgTicketResolutionHours: 3.4,
  topModerators: [{ name: 'mod', count: 7 }],
};

const FEATURE_PAYLOADS: Record<string, unknown> = {
  automod: {
    blockInvites: true, blockLinks: false, allowedDomains: ['youtube.com'],
    blockMassMentions: true, spamCount: 5, spamWindow: 3, mentionLimit: 5,
    strikesEnabled: true, strikeExpiryHours: 24, strikeMuteAt: 3, strikeKickAt: 5, strikeBanAt: 0,
    dryRun: false, rules: [], bannedWords: ['плохоеслово'], ignoredChannels: [], ignoredRoles: [],
  },
  'anti-raid': {
    joinCount: 8, joinWindow: 10, action: 'timeout', duration: 300,
    minAccountAgeDays: 0, pingRole: null,
  },
  tickets: { supportRole: null, category: null, autoCloseHours: 48 },
  levels: {
    channel: null, rewards: [], voiceXpEnabled: true, voiceXpPerMin: 5,
    xpMultiplier: 1, prestigeLevel: 100, season: 2, roleMultipliers: [],
  },
  rules: { channel: null, message: 'Будьте вежливы.' },
  'welcome-message': { channel: null, message: 'Привет, {user.mention}!', role: null },
  moderation: {
    config: null, kick: null, ban: null, mute: null, warn: null, clear: null,
    warnEscalationEnabled: true, warnExpiryHours: 720, warnMuteAt: 3, warnKickAt: 5, warnBanAt: 7,
  },
  logging: { logChannel: null, usageChannel: null, messagesChannel: null, leaveChannel: null },
  verification: { role: null },
  'reaction-menus': { menus: [], reactionRoles: [] },
  'scheduled-messages': { items: [] },
};

const json = (body: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(body),
});

export async function signIn(context: BrowserContext) {
  await context.addCookies([{
    name: 'ts-token',
    value: JSON.stringify(SESSION),
    url: 'http://localhost:3000',
    httpOnly: true,
    sameSite: 'Lax',
  }]);
}

export async function mockBackend(page: Page) {
  // Discord, called straight from the browser with the access token.
  await page.route('https://discord.com/api/**', (route) => {
    const url = route.request().url();
    if (url.includes('/users/@me/guilds')) return route.fulfill(json(GUILDS));
    if (url.includes('/users/@me')) return route.fulfill(json(USER));
    return route.fulfill(json({}));
  });

  // Which of the admin's guilds the bot is in (server-side route).
  await page.route('**/api/me/guilds', (route) =>
    route.fulfill(json({ botReachable: true, guilds: [{ id: GUILD_ID, member_count: 7 }] }))
  );

  // The bot proxy. Ordered longest-path-first: /guilds/{id} would otherwise
  // swallow /guilds/{id}/features/{feature}.
  await page.route('**/api/bot/**', (route) => {
    const path = new URL(route.request().url()).pathname;

    if (path.includes('/features/')) {
      const feature = path.split('/features/')[1];
      return route.fulfill(json(FEATURE_PAYLOADS[feature] ?? {}));
    }
    if (path.endsWith('/stats')) return route.fulfill(json(STATS));
    if (path.endsWith('/moderation')) return route.fulfill(json(MODERATION));
    if (path.endsWith('/tickets')) return route.fulfill(json({ tickets: TICKETS }));
    if (path.endsWith('/audit')) return route.fulfill(json({ entries: AUDIT }));
    if (path.includes('/analytics')) return route.fulfill(json(ANALYTICS));
    if (path.includes('/members')) return route.fulfill(json([]));
    if (path.includes('/roles') || path.includes('/channels') || path.includes('/emojis')) {
      return route.fulfill(json([]));
    }
    // /api/bot/guilds/{id} — the guild info payload.
    return route.fulfill(json(GUILD_INFO));
  });
}
