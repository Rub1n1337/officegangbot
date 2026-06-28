import type { NextApiRequest, NextApiResponse } from 'next';
import { getServerSession } from '@/utils/auth/server';

const botApiUrl = process.env.BOT_API_URL ?? 'http://localhost:8000';
const ADMINISTRATOR = BigInt(1 << 3); // Discord ADMINISTRATOR permission flag

type BotGuild = { id: string; member_count: number };

/**
 * Returns the bot-present guilds among the *user's own admin guilds*, with member
 * counts — so the home picker can show "Active" vs "Add bot" without N requests.
 *
 * The bot's full guild list (`/api/guilds`) is fetched server-side with the API
 * key and intersected with the caller's admin guilds here; it is never sent to
 * the browser. Without this, exposing `/api/guilds` through the proxy would let
 * any logged-in user enumerate every server the bot is in.
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = getServerSession(req);
  if (!session.success) {
    return res.status(401).json({ detail: 'Not authenticated' });
  }
  const apiKey = process.env.BOT_API_KEY ?? process.env.API_SECRET_KEY;
  if (!apiKey) {
    return res.status(500).json({ detail: 'BOT_API_KEY is not configured' });
  }
  const accessToken = session.data.access_token;

  // The caller's admin guild ids (Discord).
  const discordResp = await fetch('https://discord.com/api/v10/users/@me/guilds', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!discordResp.ok) {
    return res.status(502).json({ detail: 'Could not load your servers' });
  }
  const userGuilds = (await discordResp.json()) as Array<{ id: string; permissions: string }>;
  const adminIds = new Set(
    userGuilds
      .filter((g) => (BigInt(g.permissions) & ADMINISTRATOR) !== BigInt(0))
      .map((g) => g.id)
  );

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
