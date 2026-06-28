import { Box, Flex, Icon, Text } from '@chakra-ui/react';
import { MdShield, MdAlternateEmail } from 'react-icons/md';
import type { AutomodFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

function Rule({
  icon,
  title,
  description,
}: {
  icon: typeof MdShield;
  title: string;
  description: string;
}) {
  return (
    <Flex bg="CardBackground" rounded="2xl" p={4} gap={3} align="flex-start">
      <Flex
        flexShrink={0}
        align="center"
        justify="center"
        boxSize="40px"
        rounded="xl"
        bg="brandAlpha.100"
        color="brand.500"
        _dark={{ color: 'brand.200' }}
      >
        <Icon as={icon} fontSize="xl" />
      </Flex>
      <Box>
        <Text fontWeight="600">{title}</Text>
        <Text fontSize="sm" color="TextSecondary">
          {description}
        </Text>
      </Box>
    </Flex>
  );
}

// AutoMod's rules are fixed, so the "form" is an explanation of what it does;
// the enable/disable toggle is the only control.
export const useAutomodFeature: UseFormRender<AutomodFeature> = () => {
  return {
    component: (
      <Flex direction="column" gap={3}>
        <Text color="TextSecondary">
          AutoMod watches messages and acts automatically — there&apos;s nothing to configure, just
          switch it on.
        </Text>
        <Rule
          icon={MdShield}
          title="Anti-spam"
          description="Members who send 5+ messages in 3 seconds are timed out for 10 minutes."
        />
        <Rule
          icon={MdAlternateEmail}
          title="Anti-mention-spam"
          description="Messages containing 5 or more user/role mentions are deleted."
        />
        <Text fontSize="sm" color="TextSecondary">
          Actions are recorded in your punishment log when the Logging feature is enabled.
        </Text>
      </Flex>
    ),
    onSubmit: () => {},
    canSave: false,
  };
};
