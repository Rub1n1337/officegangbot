import data from '@emoji-mart/data';
import Picker from '@emoji-mart/react';

/**
 * The actual emoji-mart picker. It touches the DOM and ships a large data file,
 * so it's only ever loaded client-side via the dynamic() wrapper in
 * EmojiMartPicker.tsx (never imported directly).
 */
export default function EmojiMartInner({ onSelect }: { onSelect: (native: string) => void }) {
  return (
    <Picker
      data={data}
      onEmojiSelect={(emoji: { native: string }) => onSelect(emoji.native)}
      theme="dark"
      previewPosition="none"
      skinTonePosition="none"
      navPosition="top"
      perLine={8}
    />
  );
}
