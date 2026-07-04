import { NextRequest } from 'next/server';
import { z } from 'zod';

// Edge-safe session helpers: the cookie name/schema and the middleware login
// check. Kept free of node:crypto so the (edge-runtime) middleware and the
// client bundle never pull in the Node crypto used by server.ts.

export const TokenCookie = 'ts-token';
// Encrypted cookie values are prefixed so a reader can tell them apart from
// legacy plaintext JSON (and so the edge middleware can recognise them).
export const ENC_PREFIX = 'enc:';

export const tokenSchema = z.object({
  access_token: z.string(),
  token_type: z.literal('Bearer'),
  expires_in: z.number(),
  refresh_token: z.string(),
  scope: z.string(),
  // When we stored the token (ms epoch). Stamped by setServerSession; absent on
  // legacy cookies, in which case we don't proactively refresh.
  obtained_at: z.number().optional(),
});

export type AccessToken = z.infer<typeof tokenSchema>;

// A malformed cookie (truncated / tampered) must be treated as "no session",
// not crash the handler with a JSON.parse error.
export function safeJsonParse(raw: string | undefined): unknown {
  if (raw == null) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}

export function middleware_hasServerSession(req: NextRequest) {
  const raw = req.cookies.get(TokenCookie)?.value;
  if (raw == null || raw === '') return false;
  // Encrypted sessions can't be decrypted at the edge (no key here). The
  // authoritative validation runs server-side (getServerSession) on every API
  // call, so presence is enough to gate page navigation.
  if (raw.startsWith(ENC_PREFIX)) return true;
  return tokenSchema.safeParse(safeJsonParse(raw)).success;
}
