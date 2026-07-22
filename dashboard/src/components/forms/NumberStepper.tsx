import { Flex, Text, IconButton, Icon } from '@chakra-ui/react';
import { MdRemove, MdAdd } from 'react-icons/md';

// Iris numeric stepper (handoff §3, control type "stepper"): [−] value [+]
// in an inset group. Clamps to [min, max]; step defaults to 1.
//
// The buttons are 36px: a real, comfortable tap target ("compensation for
// imperfection"). An invisible ::after hit-area was tried first but can't work
// here — the feature-form cards clip overflow:hidden, and the value label
// paints over any inward extension — so the honest fix is a genuinely larger
// button, not a phantom zone the container would swallow.
export function NumberStepper({
  value,
  onChange,
  min = 0,
  max = 999,
  step = 1,
  suffix,
}: {
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
}) {
  const set = (next: number) => onChange(Math.min(max, Math.max(min, next)));
  return (
    <Flex
      align="center"
      gap={0.5}
      rounded="12px"
      p={1}
      bg="secondaryGray.100"
      _dark={{ bg: 'navy.600' }}
      border="1px solid"
      borderColor="blackAlpha.200"
      sx={{ _dark: { borderColor: 'whiteAlpha.200' } }}
      flexShrink={0}
    >
      <IconButton
        aria-label="decrease"
        icon={<Icon as={MdRemove} boxSize="16px" />}
        size="xs"
        w="36px"
        h="36px"
        minW="36px"
        rounded="9px"
        variant="ghost"
        color="TextSecondary"
        isDisabled={value <= min}
        onClick={() => set(value - step)}
      />
      <Text fontSize="14px" fontWeight="700" minW="34px" textAlign="center">
        {value}
        {suffix ?? ''}
      </Text>
      <IconButton
        aria-label="increase"
        icon={<Icon as={MdAdd} boxSize="16px" />}
        size="xs"
        w="36px"
        h="36px"
        minW="36px"
        rounded="9px"
        variant="ghost"
        color="TextSecondary"
        isDisabled={value >= max}
        onClick={() => set(value + step)}
      />
    </Flex>
  );
}
