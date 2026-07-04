import { randomUUID } from 'crypto';
import { NextApiRequest, NextApiResponse } from 'next';
import { CLIENT_ID, setOAuthState } from '@/utils/auth/server';
import { getAbsoluteUrl } from '@/utils/get-absolute-url';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const { locale } = req.query as {
    locale?: string;
  };

  // Random anti-CSRF nonce, stored in a short-lived httpOnly cookie and echoed
  // in the OAuth `state`; the callback rejects the flow unless they match. The
  // locale is packed after the nonce so it survives the round-trip (a colon
  // can't appear in a UUID or a locale code).
  const nonce = randomUUID();
  setOAuthState(req, res, nonce);

  const url =
    'https://discord.com/api/oauth2/authorize?' +
    new URLSearchParams({
      client_id: CLIENT_ID,
      redirect_uri: `${getAbsoluteUrl()}/api/auth/callback`,
      response_type: 'code',
      scope: 'identify guilds',
      state: `${nonce}:${locale ?? ''}`,
    });

  res.redirect(302, url);
}
