export type ReturnOptions<T> = Options & {
  /**
   * Map result if status code is not equal to 200
   * @param status
   */
  allowed?: {
    [status: number]: (res: Response) => T | Promise<T>;
  };
};

export type Options = {
  /**
   * specify the origin url
   */
  origin?: string;

  /**
   * throw an error if status code is not equal to 200
   *
   * default: true
   */
  errorOnFail?: boolean;

  request: RequestInit;
};

export async function callDefault(url: string, init: Options) {
  const options = await parseOptions(url, init);

  return fetch(options.url, options.request).then((r) => handleError(r, init));
}

export async function callReturn<T>(url: string, init: ReturnOptions<T>): Promise<T> {
  const options = await parseOptions(url, init);

  const res = await fetch(options.url, options.request);

  if (!res.ok) {
    if (init.allowed?.[res.status] != null) {
      return await init.allowed[res.status](res);
    } else {
      await handleError(res, options);
    }
  }

  return await res.json();
}

/** throw error if condition matches */
async function handleError(res: Response, options: Options) {
  if (!res.ok && (options.errorOnFail ?? true)) {
    // Surface the API's `{ detail: "..." }` (or a string body) as the Error
    // message. Previously this threw `new Error(rawObject)`, whose message became
    // the useless "[object Object]" — so callers couldn't show why a save failed.
    let message = `Request failed (${res.status})`;
    try {
      const raw = await res.json();
      if (raw && typeof raw.detail === 'string') message = raw.detail;
      else if (typeof raw === 'string' && raw) message = raw;
    } catch {
      /* non-JSON body — keep the status message */
    }
    throw new Error(message);
  }
}

async function parseOptions<T extends Options>(url: string, options: T) {
  return {
    url: options.origin == null ? url : `${options.origin}${url}`,
    request: options.request,
  };
}
