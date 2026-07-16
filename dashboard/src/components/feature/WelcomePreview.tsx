import { Badge, Box, Flex, Text } from '@chakra-ui/react';
import { Fragment, ReactNode } from 'react';
import { feature as view } from '@/config/translations/feature';
import { useFormText } from '@/config/translations/form-text';

/**
 * A Discord-style preview of the welcome message, with the placeholders filled
 * in with sample values so admins can see how it will look before saving.
 */
function render(message: string, serverName: string): ReactNode {
  const parts = message.split(/(\{user\.mention\}|\{user\.name\}|\{user\.id\}|\{server\.name\}|\{server\.member_count\})/g);
  return parts.map((part, i) => {
    switch (part) {
      case '{user.mention}':
        return (
          <Text as="span" key={i} bg="blue.500" color="white" px="3px" rounded="sm" fontWeight="500">
            @NewMember
          </Text>
        );
      case '{user.name}':
        return <Fragment key={i}>NewMember</Fragment>;
      case '{user.id}':
        return <Fragment key={i}>123456789012345678</Fragment>;
      case '{server.name}':
        return <Fragment key={i}>{serverName}</Fragment>;
      case '{server.member_count}':
        return <Fragment key={i}>42</Fragment>;
      default:
        return <Fragment key={i}>{part}</Fragment>;
    }
  });
}

export function WelcomePreview({ message, serverName }: { message: string; serverName: string }) {
  const t = view.useTranslations();
  const ft = useFormText();
  return (
    <Box>
      <Text fontSize="sm" color="TextSecondary" mb={2}>
        {t.preview}
      </Text>
      <Flex
        bg="CardBackground"
        rounded="md"
        p={3}
        gap={3}
        align="flex-start"
        border="1px solid"
        borderColor="CardBorder"
      >
        <Box w="40px" h="40px" rounded="full" bg="Brand" flexShrink={0} />
        <Box minW={0}>
          <Flex align="center" gap={2} mb={1}>
            <Text fontWeight="700" fontSize="sm">
              OfficeGangBot
            </Text>
            <Badge colorScheme="blue" fontSize="0.6em" rounded="sm">
              BOT
            </Badge>
          </Flex>
          {message.trim() ? (
            <Text fontSize="sm" whiteSpace="pre-wrap">
              {render(message, serverName)}
            </Text>
          ) : (
            <Text fontSize="sm" color="TextSecondary" fontStyle="italic">
              {ft('Your welcome message will appear here…')}
            </Text>
          )}
        </Box>
      </Flex>
    </Box>
  );
}
