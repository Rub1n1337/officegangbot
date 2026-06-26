import {
  Box,
  Button,
  Input,
  InputGroup,
  InputRightElement,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverContent,
  PopoverTrigger,
  SimpleGrid,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { forwardRef } from 'react';
import { useController } from 'react-hook-form';
import { ControlledInput } from './types';
import { FormCard } from './Form';

// A small, curated set of unicode emojis covering the common reaction-role /
// rules use cases. Dependency-free on purpose — the field stays a plain text
// input, so pasting a custom server emoji (e.g. <:name:id>) still works.
const EMOJI_GROUPS: { label: string; emojis: string[] }[] = [
  { label: 'Common', emojis: ['✅', '❌', '👍', '👎', '⭐', '🎉', '🔥', '💯', '❤️', '🙏', '👀', '🚀'] },
  { label: 'Roles', emojis: ['🛡️', '⚔️', '👑', '🎮', '🎨', '🎵', '💻', '📚', '🏆', '🥇', '🔔', '📌'] },
  { label: 'Faces', emojis: ['😀', '😎', '🥳', '😇', '🤖', '👻', '🤝', '🫡', '😴', '🤔', '🙌', '🫶'] },
  { label: 'Symbols', emojis: ['🟢', '🔴', '🟡', '🔵', '🟣', '⚪', '⚫', '♻️', '⚠️', '🆗', '🔒', '🔓'] },
];

export type EmojiInputProps = {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

export const EmojiInput = forwardRef<HTMLInputElement, EmojiInputProps>(
  ({ value, onChange, placeholder }, ref) => {
    const { isOpen, onToggle, onClose } = useDisclosure();
    return (
      <InputGroup>
        <Input
          variant="main"
          ref={ref}
          value={value ?? ''}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          pr="3rem"
        />
        <InputRightElement width="3rem">
          <Popover isOpen={isOpen} onClose={onClose} placement="bottom-end" isLazy>
            <PopoverTrigger>
              <Button
                size="sm"
                variant="ghost"
                fontSize="lg"
                onClick={onToggle}
                aria-label="Pick an emoji"
              >
                😀
              </Button>
            </PopoverTrigger>
            <PopoverContent w="auto" maxW="300px">
              <PopoverArrow />
              <PopoverBody>
                {EMOJI_GROUPS.map((group) => (
                  <Box key={group.label} mb={2}>
                    <Text fontSize="xs" color="TextSecondary" mb={1}>
                      {group.label}
                    </Text>
                    <SimpleGrid columns={6} spacing={1}>
                      {group.emojis.map((emoji) => (
                        <Button
                          key={emoji}
                          size="sm"
                          variant="ghost"
                          fontSize="lg"
                          aria-label={`Use ${emoji}`}
                          onClick={() => {
                            onChange(emoji);
                            onClose();
                          }}
                        >
                          {emoji}
                        </Button>
                      ))}
                    </SimpleGrid>
                  </Box>
                ))}
              </PopoverBody>
            </PopoverContent>
          </Popover>
        </InputRightElement>
      </InputGroup>
    );
  }
);
EmojiInput.displayName = 'EmojiInput';

export const EmojiPickerInput: ControlledInput<Omit<EmojiInputProps, 'value' | 'onChange'>> = ({
  control,
  controller,
  ...props
}) => {
  const { fieldState, field } = useController(controller);

  return (
    <FormCard {...control} error={fieldState?.error?.message}>
      <EmojiInput {...field} {...props} />
    </FormCard>
  );
};
