import type { NextApiRequest, NextApiResponse } from 'next';

export const config = {
  api: {
    bodyParser: false,
  },
};

const botApiUrl = process.env.BOT_API_URL ?? 'http://localhost:8000';

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
