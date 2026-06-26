import type { NextApiRequest, NextApiResponse } from 'next';
import { getServerSession } from '@/utils/auth/server';

export const config = {
  api: {
    bodyParser: false,
  },
};

const botApiUrl = process.env.BOT_API_URL ?? 'http://localhost:8000';

const ADMINISTRATOR = BigInt(1 << 3); // Discord ADMINISTRATOR permission flag

// Short-lived cache of a user's admin guild ids, keyed by access token, to
// avoid hitting the Discord API (and its rate limits) on every request.
const adminGuildCache = new Map<string, { ids: Set<string>; expires: number }>();
const CACHE_TTL_MS = 60_000;

async function getAdminGuildIds(accessToken: string): Promise<Set<string> | null> {
  const cached = adminGuildCache.get(accessToken);
  if (cached && cached.expires > Date.now()) return cached.ids;

  const resp = await fetch('https://discord.com/api/v10/users/@me/guilds', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!resp.ok) return null;

  const guilds = (await resp.json()) as Array<{ id: string; permissions: string }>;
  const ids = new Set(
    guilds
      .filter((g) => (BigInt(g.permissions) & ADMINISTRATOR) !== BigInt(0))
      .map((g) => g.id)
  );
  adminGuildCache.set(accessToken, { ids, expires: Date.now() + CACHE_TTL_MS });
  return ids;
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

function buildHeaders(req: NextApiRequest, apiKey: string, hasBody: boolean) {
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

  // The bot API holds the static X-API-Key; the proxy is the only thing that
  // reaches it. Require a logged-in user here, and for guild-scoped paths verify
  // the user is an administrator of that guild — otherwise anyone could call the
  // proxy to manage any guild the bot is in.
  const session = getServerSession(req);
  if (!session.success) {
    return res.status(401).json({ detail: 'Not authenticated' });
  }
  const accessToken = session.data.access_token;

  const rawPath = req.query.path;
  const segments = (Array.isArray(rawPath) ? rawPath : [rawPath ?? '']) as string[];
  const guildId = guildIdFromPath(segments);
  if (guildId) {
    const adminGuilds = await getAdminGuildIds(accessToken);
    if (!adminGuilds) {
      return res.status(502).json({ detail: 'Could not verify guild permissions' });
    }
    if (!adminGuilds.has(guildId)) {
      return res.status(403).json({ detail: 'You are not an administrator of this guild' });
    }
  }

  try {
    const method = req.method ?? 'GET';
    const rawBody = method === 'GET' || method === 'HEAD' ? undefined : await readRawBody(req);
    const body = rawBody && rawBody.length > 0 ? rawBody : undefined;
    const upstream = await fetch(buildTargetUrl(req), {
      method,
      headers: buildHeaders(req, apiKey, body != null),
      body: body as any,
    });

    const contentType = upstream.headers.get('content-type');
    if (contentType) res.setHeader('content-type', contentType);

    const responseBody = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status);
    if (responseBody.length === 0) return res.end();
    return res.send(responseBody);
  } catch (error) {
    console.error('Bot API proxy error:', error);
    return res.status(502).json({
      detail: 'Bot API proxy failed',
      error: String((error as { cause?: unknown })?.cause ?? error),
    });
  }
}
