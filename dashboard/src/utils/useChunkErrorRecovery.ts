import { useEffect } from 'react';
import { useRouter } from 'next/router';

/**
 * Reload the page when a JS chunk fails to load, once.
 *
 * The dashboard is a client-rendered SPA: after a deploy, every chunk gets a
 * new content-hashed filename and the previous deploy's files are gone. A tab
 * that was open across the deploy — or one holding a cached HTML shell — then
 * asks for a chunk the server no longer has, gets a 404, and the navigation (or
 * a lazy import) throws. With no handler the page just sits there broken until
 * a hard reload (Ctrl+Shift+R), which is exactly the symptom this fixes.
 *
 * A stale chunk is cured by a *fresh* full load, so we do a hard navigation to
 * the intended URL. A sessionStorage flag guards against a reload loop: if the
 * fresh load still fails (a genuinely broken build, not a stale one), we don't
 * keep reloading forever.
 */

const GUARD_KEY = 'chunk-reload-attempted';

function isChunkError(err: unknown): boolean {
  if (!err) return false;
  const name = (err as { name?: string }).name ?? '';
  const message = (err as { message?: string }).message ?? '';
  return (
    name === 'ChunkLoadError' ||
    /Loading chunk [\w-]+ failed/i.test(message) ||
    /Loading CSS chunk/i.test(message) ||
    /importing a module script failed/i.test(message)
  );
}

function recover(targetUrl?: string): void {
  let alreadyTried = false;
  try {
    alreadyTried = sessionStorage.getItem(GUARD_KEY) === '1';
    sessionStorage.setItem(GUARD_KEY, '1');
  } catch {
    /* private mode — fall through and just reload */
  }
  // If a reload already happened this session and the chunk *still* failed,
  // the build is broken, not stale. Stop, or we'd loop.
  if (alreadyTried) return;
  if (targetUrl) window.location.assign(targetUrl);
  else window.location.reload();
}

export function useChunkErrorRecovery(): void {
  const router = useRouter();

  useEffect(() => {
    // A chunk request that no longer exists is the successful case: once the
    // page loads cleanly, clear the guard so a *future* deploy can recover too.
    try {
      sessionStorage.removeItem(GUARD_KEY);
    } catch {
      /* ignore */
    }

    const onRouteError = (err: Error, url: string) => {
      if (isChunkError(err)) recover(url);
    };
    const onError = (event: ErrorEvent) => {
      if (isChunkError(event.error)) recover();
    };
    const onRejection = (event: PromiseRejectionEvent) => {
      if (isChunkError(event.reason)) recover();
    };

    router.events.on('routeChangeError', onRouteError);
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      router.events.off('routeChangeError', onRouteError);
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onRejection);
    };
  }, [router]);
}
