import { Flex, Icon, Text } from '@chakra-ui/react';
import { FaCrown } from 'react-icons/fa';
import { MdArrowForward } from 'react-icons/md';

// A small, reusable "this is a Premium perk" nudge. Links to the public pricing
// page in a new tab so an in-progress form isn't lost. The label is passed in
// already translated (callers use ft()), so this stays i18n-agnostic.
export function PremiumUpsell({ label, href = '/premium' }: { label: string; href?: string }) {
  return (
    <Flex
      as="a"
      href={href}
      target="_blank"
      rel="noreferrer"
      align="center"
      gap={1.5}
      display="inline-flex"
      w="fit-content"
      px={2.5}
      py={1}
      rounded="full"
      bg="brandAlpha.100"
      color="brand.200"
      fontSize="13px"
      fontWeight="600"
      transition="opacity .15s ease"
      _hover={{ opacity: 0.85 }}
    >
      <Icon as={FaCrown} boxSize="12px" />
      <Text>{label}</Text>
      <Icon as={MdArrowForward} boxSize="14px" />
    </Flex>
  );
}
