import { Button, Center, Icon, Text, VStack } from '@chakra-ui/react';
import { BsExclamationTriangle } from 'react-icons/bs';
import { useText } from '@/config/translations/ui-text';

/**
 * Shared error state for failed queries. Most failures here are transient (the
 * bot is restarting / briefly unreachable), so this is intentionally calm — a
 * neutral icon, a clear message, the likely cause, and a retry — rather than an
 * alarming all-red panel.
 *
 * The hint and the button were hardcoded English, so on /ru a failed page
 * showed an English error state (invisible until the API actually fails). They
 * go through tt() now; the main message (`children`) is the caller's job.
 */
export function ErrorPanel({
  children,
  retry,
  hint,
  isRetrying = false,
}: {
  children: string;
  retry: () => void;
  hint?: string;
  isRetrying?: boolean;
}) {
  const tt = useText();
  return (
    <Center w="full" h="full" py={10}>
      <VStack spacing={2} textAlign="center" maxW="sm" px={4}>
        <Icon as={BsExclamationTriangle} boxSize="44px" color="TextSecondary" />
        <Text fontWeight="600" fontSize="lg">
          {children}
        </Text>
        <Text color="TextSecondary" fontSize="sm">
          {hint ?? tt('Бот запускается или временно недоступен.')}
        </Text>
        <Button mt={2} variant="action" rounded="full" px={6} onClick={retry} isLoading={isRetrying}>
          {tt('Повторить')}
        </Button>
      </VStack>
    </Center>
  );
}
