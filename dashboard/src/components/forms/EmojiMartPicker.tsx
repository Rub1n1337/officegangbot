import dynamic from 'next/dynamic';
import { Center, Spinner } from '@chakra-ui/react';

// emoji-mart's Picker is client-only and its data file is large, so load both
// lazily with no SSR — keeps them code-split out of the main bundle and avoids
// SSR "document is not defined" errors.
const LazyPicker = dynamic(() => import('./EmojiMartInner'), {
  ssr: false,
  loading: () => (
    <Center w="352px" h="435px">
      <Spinner />
    </Center>
  ),
});

export function EmojiMartPicker({ onSelect }: { onSelect: (native: string) => void }) {
  return <LazyPicker onSelect={onSelect} />;
}
