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

function buildHeaders(req: NextApiRequest, apiKey: string) {
  const headers = new Headers();
  const blocked = new Set(['host', 'connection', 'content-length', 'accept-encoding']);

  for (const [key, value] of Object.entries(req.headers)) {
    if (value == null || blocked.has(key.toLowerCase())) continue;
    headers.set(key, Array.isArray(value) ? value.join(', ') : value);
  }

  headers.set('X-API-Key', apiKey);
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
    const upstream = await fetch(buildTargetUrl(req), {
      method,
      headers: buildHeaders(req, apiKey),
      body: rawBody && rawBody.length > 0 ? (rawBody as any) : undefined,
    });

    const contentType = upstream.headers.get('content-type');
    if (contentType) res.setHeader('content-type', contentType);

    const responseBody = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status);
    if (responseBody.length === 0) return res.end();
    return res.send(responseBody);
  } catch (error) {
    return res.status(502).json({ detail: 'Bot API proxy failed' });
  }
}
