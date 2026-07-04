import type { NextApiRequest, NextApiResponse } from 'next';
import { getFreshSession } from '@/utils/auth/server';

const botApiUrl = process.env.BOT_API_URL ?? 'http://localhost:8000';
const ADMINISTRATOR = BigInt(1 << 3); // Discord ADMINISTRATOR permission flag

type BotGuild = { id: string; member_count: number };

/**
 * Fetch the user's Discord guilds, retrying briefly on 429. On the home page
 * the browser's own `useGuilds` call hits the same endpoint with the same
 * token a moment earlier, so this request can race into a rate limit; a short
 * backoff clears it. Returns null on any hard/network failure (caller degrades).
 */
async function fetchUserGuilds(accessToken: string): Promise<Response | null> {
  for (let attempt = 0; attempt < 3; attempt++) {
    let resp: Response;
    try {
      resp = await fetch('https://discord.com/api/v10/users/@me/guilds', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
    } catch {
      return null; // network error — don't crash the handler
    }
    if (resp.ok) return resp;
    if (resp.status === 429) {
      const retryAfter = Number(resp.headers.get('retry-after')) || 1;
      await new Promise((r) => setTimeout(r, Math.min(retryAfter, 2) * 1000 + 100));
      continue;
    }
    return resp; // other non-ok — caller treats as failure
  }
  return null;
}

/**
 * Returns the bot-present guilds among the *user's own admin guilds*, with member
 * counts — so the home picker can show "Active" vs "Add bot" without N requests.
 *
 * The bot's full guild list (`/api/guilds`) is fetched server-side with the API
 * key and intersected with the caller's admin guilds here; it is never sent to
 * the browser. Without this, exposing `/api/guilds` through the proxy would let
 * any logged-in user enumerate every server the bot is in.
 *
 * Always responds 200 with `{ botReachable, guilds }`; if Discord or the bot are
 * unavailable it degrades to `botReachable: false` (badges hidden) rather than
 * erroring, so a transient hiccup never breaks the picker.
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const accessToken = (await getFreshSession(req, res))?.access_token;
  if (!accessToken) {
    return res.status(401).json({ detail: 'Not authenticated' });
  }
  const apiKey = process.env.BOT_API_KEY ?? process.env.API_SECRET_KEY;
  if (!apiKey) {
    return res.status(500).json({ detail: 'BOT_API_KEY is not configured' });
  }

  // The caller's admin guild ids (Discord). Without these we can't safely
  // intersect, so degrade to "no badges" rather than failing the request.
  const discordResp = await fetchUserGuilds(accessToken);
  if (!discordResp || !discordResp.ok) {
    return res.status(200).json({ botReachable: false, guilds: [] });
  }
  let adminIds: Set<string>;
  try {
    const userGuilds = (await discordResp.json()) as Array<{ id: string; permissions: string }>;
    adminIds = new Set(
      userGuilds
        .filter((g) => (BigInt(g.permissions) & ADMINISTRATOR) !== BigInt(0))
        .map((g) => g.id)
    );
  } catch {
    return res.status(200).json({ botReachable: false, guilds: [] });
  }

  // The bot's guilds (server-side, with the API key — never exposed to the client).
  let botReachable = true;
  let botGuilds: BotGuild[] = [];
  try {
    const botResp = await fetch(`${botApiUrl.replace(/\/+$/, '')}/api/guilds`, {
      headers: { 'X-API-Key': apiKey, Accept: 'application/json' },
    });
    if (botResp.ok) {
      const data = (await botResp.json()) as { guilds?: BotGuild[] };
      botGuilds = data.guilds ?? [];
    } else {
      botReachable = false;
    }
  } catch {
    botReachable = false;
  }

  // Intersection only — never leak guilds the caller can't manage.
  const guilds = botGuilds
    .filter((g) => adminIds.has(g.id))
    .map((g) => ({ id: g.id, member_count: g.member_count }));

  return res.status(200).json({ botReachable, guilds });
}
