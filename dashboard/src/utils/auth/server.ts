import { deleteCookie, setCookie } from 'cookies-next';
import { NextApiRequest, NextApiResponse } from 'next';
import { NextApiRequestCookies } from 'next/dist/server/api-utils';
import { NextRequest } from 'next/server';
import { z } from 'zod';
import type { OptionsType } from 'cookies-next/lib/types';
import type { IncomingMessage } from 'http';

export const API_ENDPOINT = 'https://discord.com/api/v10';
export const CLIENT_ID = process.env.BOT_CLIENT_ID ?? '';
export const CLIENT_SECRET = process.env.BOT_CLIENT_SECRET ?? '';

const TokenCookie = 'ts-token';
const OAuthStateCookie = 'ts-oauth-state';

const tokenSchema = z.object({
  access_token: z.string(),
  token_type: z.literal('Bearer'),
  expires_in: z.number(),
  refresh_token: z.string(),
  scope: z.string(),
});

const DEFAULT_MAX_AGE = 60 * 60 * 24 * 30;

const options: OptionsType = {
  httpOnly: true,
  // Not sent on cross-site requests, so the proxy can't be driven by CSRF; and
  // only over HTTPS in production (localhost stays HTTP for dev).
  sameSite: 'lax',
  secure: process.env.NODE_ENV === 'production',
  maxAge: DEFAULT_MAX_AGE,
};

export type AccessToken = z.infer<typeof tokenSchema>;

// A malformed cookie (truncated / tampered) must be treated as "no session",
// not crash the handler with a JSON.parse error.
function safeJsonParse(raw: string | undefined): unknown {
  if (raw == null) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}

export function middleware_hasServerSession(req: NextRequest) {
  const raw = req.cookies.get(TokenCookie)?.value;

  return raw != null && tokenSchema.safeParse(safeJsonParse(raw)).success;
}

export function getServerSession(
  req: IncomingMessage & {
    cookies: NextApiRequestCookies;
  }
) {
  return tokenSchema.safeParse(safeJsonParse(req.cookies[TokenCookie]));
}

export function setServerSession(req: NextApiRequest, res: NextApiResponse, data: AccessToken) {
  // Tie the cookie lifetime to the Discord token's own lifetime so it can't
  // outlive a token we don't refresh (a stale token otherwise fails the guild
  // permission lookup and surfaces as a 502 on every dashboard call).
  const maxAge = data.expires_in > 0 ? data.expires_in : DEFAULT_MAX_AGE;
  setCookie(TokenCookie, data, { req, res, ...options, maxAge });
}

// --- OAuth CSRF state ---
// A random nonce set when the login flow starts and verified on the callback,
// so a forged/replayed callback (login CSRF) is rejected. Must be SameSite=Lax
// (not Strict) so the browser still sends it on the top-level redirect back
// from discord.com.
const stateOptions: OptionsType = {
  httpOnly: true,
  sameSite: 'lax',
  secure: process.env.NODE_ENV === 'production',
  maxAge: 60 * 10, // 10 minutes to complete the OAuth round-trip
};

export function setOAuthState(req: NextApiRequest, res: NextApiResponse, value: string) {
  setCookie(OAuthStateCookie, value, { req, res, ...stateOptions });
}

export function getOAuthState(req: NextApiRequest): string | undefined {
  const v = req.cookies[OAuthStateCookie];
  return typeof v === 'string' ? v : undefined;
}

export function clearOAuthState(req: NextApiRequest, res: NextApiResponse) {
  deleteCookie(OAuthStateCookie, { req, res, ...stateOptions });
}

export async function removeSession(req: NextApiRequest, res: NextApiResponse) {
  const session = getServerSession(req);

  if (session.success) {
    deleteCookie(TokenCookie, { req, res, ...options });
    await revokeToken(session.data.access_token);
  }
}

async function revokeToken(accessToken: string) {
  const data = {
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
    token: accessToken,
  };

  const headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
  };

  await fetch(`https://discord.com/api/oauth2/token/revoke`, {
    headers,
    body: new URLSearchParams(data),
    method: 'POST',
  });
}
