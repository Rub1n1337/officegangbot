import { deleteCookie, setCookie } from 'cookies-next';
import { NextApiRequest, NextApiResponse } from 'next';
import { NextApiRequestCookies } from 'next/dist/server/api-utils';
import type { OptionsType } from 'cookies-next/lib/types';
import type { IncomingMessage } from 'http';
import {
  TokenCookie,
  tokenSchema,
  safeJsonParse,
} from './session-edge';
import { encryptSession, decryptSession } from './crypto';

export const API_ENDPOINT = 'https://discord.com/api/v10';
export const CLIENT_ID = process.env.BOT_CLIENT_ID ?? '';
export const CLIENT_SECRET = process.env.BOT_CLIENT_SECRET ?? '';

// Re-exported so existing importers of these from '@/utils/auth/server' keep
// working; the definitions live in the edge-safe module.
export type { AccessToken } from './session-edge';
export { middleware_hasServerSession } from './session-edge';
import type { AccessToken } from './session-edge';

const OAuthStateCookie = 'ts-oauth-state';

const DEFAULT_MAX_AGE = 60 * 60 * 24 * 30;

const options: OptionsType = {
  httpOnly: true,
  // Not sent on cross-site requests, so the proxy can't be driven by CSRF; and
  // only over HTTPS in production (localhost stays HTTP for dev).
  sameSite: 'lax',
  secure: process.env.NODE_ENV === 'production',
  maxAge: DEFAULT_MAX_AGE,
};

export function getServerSession(
  req: IncomingMessage & {
    cookies: NextApiRequestCookies;
  }
) {
  const raw = req.cookies[TokenCookie];
  const plain = raw != null ? decryptSession(raw) : undefined;
  return tokenSchema.safeParse(safeJsonParse(plain ?? undefined));
}

export function setServerSession(req: NextApiRequest, res: NextApiResponse, data: AccessToken) {
  // Stamp when we stored it so getFreshSession can tell when the access token is
  // near expiry and refresh it. The cookie itself lives longer than one access
  // token (we refresh in place), so the session survives past a single token's
  // lifetime instead of forcing a re-login every ~7 days.
  const stamped: AccessToken = { ...data, obtained_at: Date.now() };
  // Encrypt at rest when SESSION_SECRET is configured (no-op otherwise).
  setCookie(TokenCookie, encryptSession(JSON.stringify(stamped)), {
    req, res, ...options, maxAge: DEFAULT_MAX_AGE,
  });
}

// Refresh the Discord token near expiry so the session isn't dropped every time
// one access token lapses. Proactive, single-flighted (so a page's burst of
// requests doesn't fire N concurrent refreshes) and non-fatal.
const REFRESH_WINDOW_MS = 1000 * 60 * 60 * 24; // refresh when < 1 day remains
const refreshInflight = new Map<string, Promise<AccessToken | null>>();

async function refreshAccessToken(refreshToken: string): Promise<AccessToken | null> {
  try {
    const resp = await fetch(`${API_ENDPOINT}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
      }),
    });
    if (!resp.ok) return null;
    const parsed = tokenSchema.safeParse(await resp.json());
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}

function refreshOnce(refreshToken: string): Promise<AccessToken | null> {
  const existing = refreshInflight.get(refreshToken);
  if (existing) return existing;
  const p = refreshAccessToken(refreshToken).finally(() => refreshInflight.delete(refreshToken));
  refreshInflight.set(refreshToken, p);
  return p;
}

/**
 * The current session token, refreshing it in place if it's near expiry.
 * Returns null (and clears the cookie) only when there's no usable session left,
 * so callers can treat null as "not authenticated". Refresh failure with a
 * still-valid token falls through with that token — never worse than before.
 */
export async function getFreshSession(
  req: NextApiRequest,
  res: NextApiResponse
): Promise<AccessToken | null> {
  const parsed = getServerSession(req);
  if (!parsed.success) return null;
  const session = parsed.data;

  const now = Date.now();
  const expiresAt = session.obtained_at != null ? session.obtained_at + session.expires_in * 1000 : null;
  const nearExpiry = expiresAt != null && expiresAt - now < REFRESH_WINDOW_MS;

  if (nearExpiry && session.refresh_token) {
    const refreshed = await refreshOnce(session.refresh_token);
    if (refreshed) {
      setServerSession(req, res, refreshed);
      return refreshed;
    }
    // Refresh failed. If the token is already expired there's nothing usable
    // left — clear the session so the user re-logs in cleanly rather than
    // erroring for the cookie's whole lifetime.
    if (expiresAt != null && expiresAt <= now) {
      deleteCookie(TokenCookie, { req, res, ...options });
      return null;
    }
  }
  return session;
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
