import type { NextApiRequest, NextApiResponse } from 'next';
import { getFreshSession } from '@/utils/auth/server';

export const config = {
  api: {
    bodyParser: false,
  },
};

const botApiUrl = process.env.BOT_API_URL ?? 'http://localhost:8000';

// In production the proxy forwards the X-API-Key and X-Actor-* headers to the
// bot API, so that hop must be TLS. A plain-http BOT_API_URL to a non-local
// host would send those secrets in the clear — refuse to proxy at all
// (checked per request in the handler), not just log.
const botApiUrlInsecure =
  process.env.NODE_ENV === 'production' &&
  botApiUrl.startsWith('http://') &&
  !/^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:|\/|$)/.test(botApiUrl);
if (botApiUrlInsecure) {
  console.error(
    `[bot-proxy] BOT_API_URL is plain http (${botApiUrl}) in production — refusing ` +
      `to proxy: the API key and actor headers would travel unencrypted. Use https://.`
  );
}

const ADMINISTRATOR = BigInt(1 << 3); // Discord ADMINISTRATOR permission flag

// Short-lived cache of a user's admin guild ids, keyed by access token, to
// avoid hitting the Discord API (and its rate limits) on every request.
const adminGuildCache = new Map<string, { ids: Set<string>; expires: number }>();
const CACHE_TTL_MS = 60_000;

// These caches are keyed by access token; without a bound they'd grow forever
// across distinct sessions. Drop expired entries once a cache gets large.
const MAX_CACHE_ENTRIES = 5_000;
function pruneCache(cache: Map<string, { expires: number }>) {
  if (cache.size < MAX_CACHE_ENTRIES) return;
  const now = Date.now();
  cache.forEach((value, key) => {
    if (value.expires <= now) cache.delete(key);
  });
}

// In-flight Discord calls, so a burst of concurrent proxy requests (a page load
// fires several /api/bot/* at once) shares ONE call instead of each hammering
// Discord before the cache warms — that thundering herd got rate-limited (429),
// getAdminGuildIds returned null, and the request 502'd (which then left the
// dashboard query stuck loading).
const adminGuildInflight = new Map<string, Promise<Set<string> | null>>();

async function getAdminGuildIds(accessToken: string): Promise<Set<string> | null> {
  const cached = adminGuildCache.get(accessToken);
  if (cached && cached.expires > Date.now()) return cached.ids;

  const existing = adminGuildInflight.get(accessToken);
  if (existing) return existing;

  const request = (async (): Promise<Set<string> | null> => {
    try {
      const resp = await fetch('https://discord.com/api/v10/users/@me/guilds', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      // On a transient Discord failure (e.g. 429), fall back to the last-known
      // (now-expired) value if we have one, rather than returning null and 502-ing.
      // Admin membership rarely changes, so a minute-stale answer is safe here.
      if (!resp.ok) return adminGuildCache.get(accessToken)?.ids ?? null;

      const guilds = (await resp.json()) as Array<{ id: string; permissions: string }>;
      const ids = new Set(
        guilds
          .filter((g) => (BigInt(g.permissions) & ADMINISTRATOR) !== BigInt(0))
          .map((g) => g.id)
      );
      pruneCache(adminGuildCache);
      adminGuildCache.set(accessToken, { ids, expires: Date.now() + CACHE_TTL_MS });
      return ids;
    } finally {
      adminGuildInflight.delete(accessToken);
    }
  })();

  adminGuildInflight.set(accessToken, request);
  return request;
}

// Short-lived cache of the caller's Discord identity, so mutating requests can
// be attributed in the bot's audit trail without a Discord call each time.
type Actor = { id: string; name: string };
const actorCache = new Map<string, { actor: Actor; expires: number }>();
const actorInflight = new Map<string, Promise<Actor | null>>();

async function getActor(accessToken: string): Promise<Actor | null> {
  const cached = actorCache.get(accessToken);
  if (cached && cached.expires > Date.now()) return cached.actor;

  const existing = actorInflight.get(accessToken);
  if (existing) return existing;

  const request = (async (): Promise<Actor | null> => {
    try {
      const resp = await fetch('https://discord.com/api/v10/users/@me', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!resp.ok) return null;
      const u = (await resp.json()) as { id: string; username: string; global_name?: string | null };
      const actor: Actor = { id: u.id, name: u.global_name?.trim() || u.username };
      pruneCache(actorCache);
      actorCache.set(accessToken, { actor, expires: Date.now() + CACHE_TTL_MS });
      return actor;
    } finally {
      actorInflight.delete(accessToken);
    }
  })();

  actorInflight.set(accessToken, request);
  return request;
}

// The guild id, if this is a guild-scoped path (/guilds/{id}/... or /api/guild/{id}).
function guildIdFromPath(segments: string[]): string | null {
  if (segments[0] === 'guilds' && /^\d+$/.test(segments[1] ?? '')) return segments[1];
  if (segments[0] === 'api' && segments[1] === 'guild' && /^\d+$/.test(segments[2] ?? '')) {
    return segments[2];
  }
  return null;
}

function buildTargetUrl(req: NextApiRequest) {
  const rawPath = req.query.path;
  const path = Array.isArray(rawPath) ? rawPath.join('/') : rawPath ?? '';
  const target = new URL(`${botApiUrl.replace(/\/+$/, '')}/${path}`);

  for (const [key, value] of Object.entries(req.query)) {
    if (key === 'path' || value == null) continue;
    if (Array.isArray(value)) {
      for (const item of value) target.searchParams.append(key, item);
    } else {
      target.searchParams.append(key, value);
    }
  }

  return target.toString();
}

function buildHeaders(req: NextApiRequest, apiKey: string, hasBody: boolean, actor?: Actor | null) {
  // Forward only a minimal, safe header set to the bot API. Forwarding the raw
  // browser headers (origin, cookie, sec-fetch-*, transfer-encoding, …) made
  // undici's fetch reject body-less POST/DELETE requests, so enable/disable
  // failed with "Bot API proxy failed".
  const headers = new Headers();
  headers.set('X-API-Key', apiKey);
  headers.set('Accept', 'application/json');
  if (hasBody) {
    const ct = req.headers['content-type'];
    headers.set('Content-Type', (Array.isArray(ct) ? ct[0] : ct) ?? 'application/json');
  }
  // Attribution for the bot's audit trail (server-derived from the session, so
  // the client can't spoof it).
  if (actor) {
    headers.set('X-Actor-Id', actor.id);
    headers.set('X-Actor-Name', encodeURIComponent(actor.name));
  }
  return headers;
}

function readRawBody(req: NextApiRequest): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];

    req.on('data', (chunk) => {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const apiKey = process.env.BOT_API_KEY ?? process.env.API_SECRET_KEY;
  if (!apiKey) {
    return res.status(500).json({ detail: 'BOT_API_KEY is not configured' });
  }
  if (botApiUrlInsecure) {
    return res.status(500).json({ detail: 'BOT_API_URL must be https in production' });
  }

  // The bot API holds the static X-API-Key; the proxy is the only thing that
  // reaches it. Require a logged-in user here, and for guild-scoped paths verify
  // the user is an administrator of that guild — otherwise anyone could call the
  // proxy to manage any guild the bot is in.
  const accessToken = (await getFreshSession(req, res))?.access_token;
  if (!accessToken) {
    return res.status(401).json({ detail: 'Not authenticated' });
  }

  const rawPath = req.query.path;
  const segments = (Array.isArray(rawPath) ? rawPath : [rawPath ?? '']) as string[];

  // Reject path traversal / odd segments so the guild authorized below is exactly
  // the guild the bot receives. Without this, an encoded `..` segment passes the
  // guild-id check on one guild but gets normalized away when the upstream URL is
  // built (`new URL`), landing on a *different* guild — a cross-guild IDOR.
  if (
    segments.some((s) => s === '' || s.includes('/') || s.includes('\\')) ||
    segments.join('/').includes('..')
  ) {
    return res.status(400).json({ detail: 'Invalid path' });
  }

  // Only guild-scoped paths are reachable through the proxy. This enforces the
  // per-guild admin check AND keeps the bot's global endpoints (e.g. /api/guilds,
  // /api/stats) from being callable by any logged-in user.
  const guildId = guildIdFromPath(segments);
  if (!guildId) {
    return res.status(403).json({ detail: 'This endpoint is not accessible' });
  }
  const adminGuilds = await getAdminGuildIds(accessToken);
  if (!adminGuilds) {
    return res.status(502).json({ detail: 'Could not verify guild permissions' });
  }
  if (!adminGuilds.has(guildId)) {
    return res.status(403).json({ detail: 'You are not an administrator of this guild' });
  }

  // Defense in depth: the guild id in the *final* upstream URL must be exactly
  // the guild the admin check above authorized — if URL normalization ever
  // diverged from the segment check, this catches it.
  const targetUrl = buildTargetUrl(req);
  const upstreamGuildId = guildIdFromPath(
    new URL(targetUrl).pathname.split('/').filter(Boolean)
  );
  if (upstreamGuildId !== guildId) {
    return res.status(400).json({ detail: 'Invalid path' });
  }

  try {
    const method = req.method ?? 'GET';
    const rawBody = method === 'GET' || method === 'HEAD' ? undefined : await readRawBody(req);
    const body = rawBody && rawBody.length > 0 ? rawBody : undefined;
    // The actor identity rides on every request: mutations need it for the
    // audit trail, and the bot API keys its rate limiter per admin (X-Actor-Id)
    // — without it all requests share one per-IP bucket behind Vercel. Cached
    // per token for a minute, so this adds no extra Discord calls in practice.
    const actor = await getActor(accessToken);
    const upstream = await fetch(targetUrl, {
      method,
      headers: buildHeaders(req, apiKey, body != null, actor),
      body: body as any,
    });

    const contentType = upstream.headers.get('content-type');
    if (contentType) res.setHeader('content-type', contentType);

    const responseBody = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status);
    if (responseBody.length === 0) return res.end();
    return res.send(responseBody);
  } catch (error) {
    // Log the detail server-side; don't leak internal error / infra detail to the client.
    console.error('Bot API proxy error:', error);
    return res.status(502).json({ detail: 'Bot API proxy failed' });
  }
}
