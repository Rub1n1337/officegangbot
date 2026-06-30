import { Button, Center, Icon, Text, VStack } from '@chakra-ui/react';
import { BsExclamationTriangle } from 'react-icons/bs';

/**
 * Shared error state for failed queries. Most failures here are transient (the
 * bot is restarting / briefly unreachable), so this is intentionally calm — a
 * neutral icon, a clear message, the likely cause, and a retry — rather than an
 * alarming all-red panel.
 */
export function ErrorPanel({
  children,
  retry,
  hint = 'The bot may be starting up or temporarily unreachable.',
  isRetrying = false,
}: {
  children: string;
  retry: () => void;
  hint?: string;
  isRetrying?: boolean;
}) {
  return (
    <Center w="full" h="full" py={10}>
      <VStack spacing={2} textAlign="center" maxW="sm" px={4}>
        <Icon as={BsExclamationTriangle} boxSize="44px" color="TextSecondary" />
        <Text fontWeight="600" fontSize="lg">
          {children}
        </Text>
        <Text color="TextSecondary" fontSize="sm">
          {hint}
        </Text>
        <Button mt={2} variant="action" rounded="full" px={6} onClick={retry} isLoading={isRetrying}>
          Try again
        </Button>
      </VStack>
    </Center>
  );
}
