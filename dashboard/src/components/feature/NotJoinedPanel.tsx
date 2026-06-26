import { Button, Center, Icon, Text } from '@chakra-ui/react';
import { BsMailbox } from 'react-icons/bs';
import { FaRobot } from 'react-icons/fa';
import { config } from '@/config/common';
import { guild as view } from '@/config/translations/guild';

/**
 * Shown when the bot isn't a member of the guild: a friendly prompt to invite
 * it, instead of a raw error. Reused by the guild overview pages.
 */
export function NotJoinedPanel({ guild }: { guild: string }) {
  const t = view.useTranslations();

  return (
    <Center flexDirection="column" gap={3} h="full" p={5}>
      <Icon as={BsMailbox} w={50} h={50} />
      <Text fontSize="xl" fontWeight="600">
        {t.error['not found']}
      </Text>
      <Text textAlign="center" color="TextSecondary">
        {t.error['not found description']}
      </Text>
      <Button
        variant="action"
        leftIcon={<FaRobot />}
        px={6}
        as="a"
        href={`${config.inviteUrl}&guild_id=${guild}`}
        target="_blank"
      >
        {t.bn.invite}
      </Button>
    </Center>
  );
}
