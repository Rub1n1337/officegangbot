import { Flex, Text, IconButton, Icon } from '@chakra-ui/react';
import { MdRemove, MdAdd } from 'react-icons/md';

// Iris numeric stepper (handoff §3, control type "stepper"): [−] value [+]
// in an inset group. Clamps to [min, max]; step defaults to 1.
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
      gap="2px"
      rounded="11px"
      p="3px"
      bg="secondaryGray.100"
      _dark={{ bg: 'navy.600' }}
      border="1px solid"
      borderColor="blackAlpha.200"
      sx={{ _dark: { borderColor: 'whiteAlpha.200' } }}
      flexShrink={0}
    >
      <IconButton
        aria-label="Меньше"
        icon={<Icon as={MdRemove} boxSize="16px" />}
        size="xs"
        w="28px"
        h="28px"
        rounded="8px"
        variant="ghost"
        color="TextSecondary"
        isDisabled={value <= min}
        onClick={() => set(value - step)}
      />
      <Text fontSize="13.5px" fontWeight="700" minW="34px" textAlign="center">
        {value}
        {suffix ?? ''}
      </Text>
      <IconButton
        aria-label="Больше"
        icon={<Icon as={MdAdd} boxSize="16px" />}
        size="xs"
        w="28px"
        h="28px"
        rounded="8px"
        variant="ghost"
        color="TextSecondary"
        isDisabled={value >= max}
        onClick={() => set(value + step)}
      />
    </Flex>
  );
}
