import dynamic from 'next/dynamic';
import { Center, Spinner } from '@chakra-ui/react';
import { useRouter } from 'next/router';
import { useGuildEmojisQuery } from '@/api/hooks';

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

export function EmojiMartPicker({ onSelect }: { onSelect: (value: string) => void }) {
  const guild = useRouter().query.guild as string;
  // The guild's custom emojis (empty/loading until fetched, or [] if the bot
  // can't reach the guild) — the picker still works with the standard set.
  const { data: customEmojis } = useGuildEmojisQuery(guild);

  return <LazyPicker onSelect={onSelect} customEmojis={customEmojis ?? []} />;
}
