import {
  Button,
  Input,
  InputGroup,
  InputRightElement,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverContent,
  PopoverTrigger,
  useDisclosure,
} from '@chakra-ui/react';
import { forwardRef } from 'react';
import { useController } from 'react-hook-form';
import { ControlledInput } from './types';
import { FormCard } from './Form';
import { EmojiMartPicker } from './EmojiMartPicker';

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
          {/* Full searchable emoji-mart picker. The field stays a plain input,
              so pasting a custom server emoji (<:name:id>) still works. */}
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
            <PopoverContent
              w="auto"
              maxW="calc(100vw - 1rem)"
              bg="transparent"
              border="none"
              boxShadow="none"
            >
              <PopoverArrow />
              <PopoverBody p={0}>
                <EmojiMartPicker
                  onSelect={(native) => {
                    onChange(native);
                    onClose();
                  }}
                />
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
