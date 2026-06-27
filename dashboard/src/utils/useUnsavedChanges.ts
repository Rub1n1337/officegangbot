import { useEffect } from 'react';
import { useRouter } from 'next/router';

const MESSAGE = 'You have unsaved changes. Leave anyway?';

/**
 * Warns the user before leaving the page while `when` is true (e.g. a feature
 * form has unsaved edits) — both on in-app navigation (sidebar links) and on a
 * browser refresh/close.
 */
export function useUnsavedChanges(when: boolean) {
  const router = useRouter();

  useEffect(() => {
    if (!when) return;

    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = MESSAGE;
      return MESSAGE;
    };

    const onRouteChangeStart = (url: string) => {
      if (url === router.asPath) return;
      if (!window.confirm(MESSAGE)) {
        router.events.emit('routeChangeError');
        // Documented Next.js (pages router) way to abort an in-app navigation.
        // eslint-disable-next-line no-throw-literal
        throw 'Route change aborted by the unsaved-changes guard.';
      }
    };

    window.addEventListener('beforeunload', onBeforeUnload);
    router.events.on('routeChangeStart', onRouteChangeStart);
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
      router.events.off('routeChangeStart', onRouteChangeStart);
    };
  }, [when, router]);
}
