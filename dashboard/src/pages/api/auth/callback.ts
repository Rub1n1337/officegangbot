import { NextApiRequest, NextApiResponse } from 'next';
import {
  AccessToken,
  API_ENDPOINT,
  CLIENT_ID,
  CLIENT_SECRET,
  clearOAuthState,
  getOAuthState,
  setServerSession,
} from '@/utils/auth/server';
import { i18n } from 'next.config';
import { z } from 'zod';
import { getAbsoluteUrl } from '@/utils/get-absolute-url';

async function exchangeToken(code: string): Promise<AccessToken> {
  const data = {
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
    grant_type: 'authorization_code',
    code: code,
    redirect_uri: `${getAbsoluteUrl()}/api/auth/callback`,
  };

  const headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
  };

  const response = await fetch(`${API_ENDPOINT}/oauth2/token`, {
    headers,
    method: 'POST',
    body: new URLSearchParams(data),
  });

  if (response.ok) {
    return (await response.json()) as AccessToken;
  } else {
    throw new Error('Failed to exchange token');
  }
}

const querySchema = z.object({
  code: z.string(),
  state: z.string().optional(),
});

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const query = querySchema.safeParse(req.query);

  if (!query.success) {
    return res.status(400).json('Invalid query param');
  }

  const { code, state } = query.data;

  // CSRF: the state must carry the nonce we set (in an httpOnly cookie) when the
  // flow started. Reject a missing/mismatched nonce — that's a forged or replayed
  // callback (login CSRF), not a real login we initiated.
  const cookieNonce = getOAuthState(req);
  const [nonce, rawLocale] = (state ?? '').split(':');
  clearOAuthState(req, res);
  if (!cookieNonce || !nonce || nonce !== cookieNonce) {
    return res.status(400).json('Invalid OAuth state');
  }

  // Only trust a locale we actually support for the post-login redirect.
  const locale = i18n?.locales.find((l) => l === rawLocale);

  let token: AccessToken;
  try {
    token = await exchangeToken(code);
  } catch (err) {
    // Don't 500 on a Discord token-exchange failure — send the user back to a
    // page instead of a stack trace.
    console.error('OAuth token exchange failed:', err);
    return res.redirect('/?error=auth');
  }

  setServerSession(req, res, token);
  res.redirect(locale ? `/${locale}/user/home` : `/user/home`);
}
