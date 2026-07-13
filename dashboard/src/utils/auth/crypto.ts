import crypto from 'crypto';
import { ENC_PREFIX } from './session-edge';

// Optional at-rest encryption for the session cookie (AES-256-GCM). When
// SESSION_SECRET is set, the cookie payload (which holds the Discord
// access/refresh tokens) is encrypted so the tokens aren't sitting in
// plaintext in the browser. When it's unset, we fall back to the previous
// plaintext behaviour so existing deployments keep working.

// Without SESSION_SECRET the Discord tokens sit base64-plaintext in the
// cookie — tolerated for legacy deployments, but loudly wrong in production.
if (process.env.NODE_ENV === 'production' && !process.env.SESSION_SECRET) {
  console.error(
    '[auth] SESSION_SECRET is not set in production — session cookies (Discord ' +
      'access/refresh tokens) are stored WITHOUT encryption. Set SESSION_SECRET.'
  );
}

function key(): Buffer | null {
  const secret = process.env.SESSION_SECRET;
  if (!secret) return null;
  return crypto.createHash('sha256').update(secret).digest(); // 32 bytes
}

export function encryptSession(plain: string): string {
  const k = key();
  if (!k) return plain; // no secret configured — store as-is (legacy)
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', k, iv);
  const ct = Buffer.concat([cipher.update(plain, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return ENC_PREFIX + Buffer.concat([iv, tag, ct]).toString('base64url');
}

export function decryptSession(raw: string): string | null {
  if (!raw.startsWith(ENC_PREFIX)) return raw; // legacy plaintext
  const k = key();
  if (!k) return null; // encrypted cookie but no key to read it
  try {
    const buf = Buffer.from(raw.slice(ENC_PREFIX.length), 'base64url');
    const iv = buf.subarray(0, 12);
    const tag = buf.subarray(12, 28);
    const ct = buf.subarray(28);
    const decipher = crypto.createDecipheriv('aes-256-gcm', k, iv);
    decipher.setAuthTag(tag);
    return Buffer.concat([decipher.update(ct), decipher.final()]).toString('utf8');
  } catch {
    return null; // tampered, or the key changed
  }
}
