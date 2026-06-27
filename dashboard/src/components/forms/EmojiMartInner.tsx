import data from '@emoji-mart/data';
import Picker from '@emoji-mart/react';
import { useMemo } from 'react';
import type { GuildEmoji } from '@/api/bot';

/**
 * The actual emoji-mart picker. It touches the DOM and ships a large data file,
 * so it's only ever loaded client-side via the dynamic() wrapper in
 * EmojiMartPicker.tsx (never imported directly).
 *
 * Standard emojis resolve to their native unicode; the guild's custom emojis are
 * shown under a "Server Emojis" category and resolve to the Discord mention form
 * (<:name:id> / <a:name:id> for animated).
 */
export default function EmojiMartInner({
  onSelect,
  customEmojis,
}: {
  onSelect: (value: string) => void;
  customEmojis: GuildEmoji[];
}) {
  const custom = useMemo(() => {
    if (!customEmojis.length) return undefined;
    return [
      {
        id: 'server',
        name: 'Server Emojis',
        emojis: customEmojis.map((e) => ({
          id: e.id,
          name: e.name,
          keywords: [e.name],
          skins: [{ src: e.url }],
        })),
      },
    ];
  }, [customEmojis]);

  const byId = useMemo(
    () => new Map(customEmojis.map((e) => [e.id, e])),
    [customEmojis]
  );

  const handleSelect = (emoji: { id?: string; native?: string }) => {
    // Discord emoji ids are numeric snowflakes, so a hit in byId means a custom
    // server emoji was picked; otherwise it's a standard unicode emoji.
    const ge = emoji.id ? byId.get(emoji.id) : undefined;
    if (ge) {
      onSelect(`<${ge.animated ? 'a' : ''}:${ge.name}:${ge.id}>`);
    } else if (emoji.native) {
      onSelect(emoji.native);
    }
  };

  return (
    <Picker
      data={data}
      custom={custom}
      onEmojiSelect={handleSelect}
      theme="dark"
      previewPosition="none"
      skinTonePosition="none"
      navPosition="top"
      perLine={8}
    />
  );
}
