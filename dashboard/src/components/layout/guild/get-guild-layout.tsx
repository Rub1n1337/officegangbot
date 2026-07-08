import { ReactNode } from 'react';
import IrisGuildLayout from './iris-layout';

// Guild pages use the Iris shell (272px sidebar + header). The `back` flag is
// no longer needed — the Iris sidebar always shows the in-guild nav — but it's
// kept in the signature so existing call sites (getLayout={... back: true})
// don't need to change.
export default function getGuildLayout({ children }: { back?: boolean; children: ReactNode }) {
  return <IrisGuildLayout>{children}</IrisGuildLayout>;
}
