import {
  Box, Flex, Text, Icon, Popover, PopoverTrigger, PopoverContent,
  PopoverBody, Portal, useDisclosure, Button, Spinner,
} from '@chakra-ui/react';
import { MdNotifications, MdConfirmationNumber, MdOutlineHowToReg } from 'react-icons/md';
import { useEffect, useMemo, useState } from 'react';
import { useTicketsQuery, useModerationQuery } from '@/api/hooks';
import { timeAgo } from '@/utils/audit';
import { provider } from '@/config/translations/provider';
import { useText } from '@/config/translations/ui-text';

// Notifications popover (Iris README §10). There is no realtime event feed,
// so the list is derived from real signals we already have per guild:
// open tickets + pending ban appeals. Queries mount lazily — only after the
// bell is first opened — so guild pages don't pay the moderation RPC cost.
// Read-state persists per guild in localStorage.

type Item = {
  id: string; // 't-<ticketId>' | 'a-<appealId>'
  icon: typeof MdNotifications;
  tone: 'accent' | 'amber';
  title: string;
  when: string | null;
};

function readSet(guild: string): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(`notif-read-${guild}`) ?? '[]'));
  } catch {
    return new Set();
  }
}
function saveSet(guild: string, s: Set<string>) {
  try {
    localStorage.setItem(`notif-read-${guild}`, JSON.stringify(Array.from(s)));
  } catch {
    /* quota/priv mode — read-state just won't persist */
  }
}

function PanelContent({
  guild,
  onClose,
  onUnread,
}: {
  guild: string;
  onClose: () => void;
  onUnread: (n: number) => void;
}) {
  const tickets = useTicketsQuery(guild);
  const moderation = useModerationQuery(guild);
  const lang = provider.useLang();
  const tt = useText();
  const [read, setRead] = useState<Set<string>>(() => readSet(guild));

  const items = useMemo<Item[]>(() => {
    const out: Item[] = [];
    for (const t of tickets.data ?? []) {
      if (t.status === 'open')
        out.push({
          id: `t-${t.id}`,
          icon: MdConfirmationNumber,
          tone: 'accent',
          title: `${tt('Новый тикет')} — ${t.openerName ?? t.openerId}`,
          when: t.openedAt,
        });
    }
    for (const a of moderation.data?.appeals.items ?? []) {
      if (a.status === 'pending')
        out.push({
          id: `a-${a.id}`,
          icon: MdOutlineHowToReg,
          tone: 'amber',
          title: `${tt('Апелляция на бан')} — ${a.userName ?? a.userId}`,
          when: a.createdAt,
        });
    }
    return out.sort((x, y) => Date.parse(y.when ?? '') - Date.parse(x.when ?? ''));
  }, [tickets.data, moderation.data, tt]);

  const unread = items.filter((i) => !read.has(i.id)).length;
  useEffect(() => onUnread(unread), [unread, onUnread]);

  const markOne = (id: string) => {
    const s = new Set(read);
    s.add(id);
    setRead(s);
    saveSet(guild, s);
  };
  const markAll = () => {
    const s = new Set(items.map((i) => i.id));
    setRead(s);
    saveSet(guild, s);
  };
  const loading = tickets.isLoading || moderation.isLoading;

  return (
    <>
      <Flex align="center" justify="space-between" p="12px 14px" borderBottom="1px solid" borderColor="CardBorder">
        <Text fontSize="14px" fontWeight="700">
          {tt('Уведомления')}
        </Text>
        <Button size="xs" variant="ghost" color="brand.200" onClick={markAll} isDisabled={unread === 0}>
          {tt('Прочитать всё')}
        </Button>
      </Flex>
      <Box maxH="320px" overflowY="auto" p="6px">
        {loading ? (
          <Flex justify="center" py="24px">
            <Spinner size="sm" />
          </Flex>
        ) : items.length === 0 ? (
          <Text fontSize="13px" color="TextSecondary" textAlign="center" py="20px">
            {tt('Пока тихо — открытых тикетов и апелляций нет.')}
          </Text>
        ) : (
          items.map((n) => (
            <Flex
              key={n.id}
              as="button"
              onClick={() => markOne(n.id)}
              align="center"
              gap="11px"
              w="full"
              textAlign="left"
              p="9px 10px"
              rounded="10px"
              _hover={{ bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
            >
              <Flex
                w="32px"
                h="32px"
                rounded="9px"
                align="center"
                justify="center"
                flexShrink={0}
                color={n.tone === 'amber' ? 'orange.400' : 'brand.200'}
                bg={n.tone === 'amber' ? 'rgba(245,177,76,0.14)' : 'brandAlpha.100'}
              >
                <Icon as={n.icon} boxSize="17px" />
              </Flex>
              <Box flex="1" minW={0}>
                <Text fontSize="13px" fontWeight="600" noOfLines={1}>
                  {n.title}
                </Text>
                <Text fontSize="11.5px" color="TextSecondary">
                  {timeAgo(n.when, lang)}
                </Text>
              </Box>
              {!read.has(n.id) && <Box w="7px" h="7px" rounded="full" bg="Brand" flexShrink={0} />}
            </Flex>
          ))
        )}
      </Box>
      <Flex p="8px" borderTop="1px solid" borderColor="CardBorder" justify="center">
        <Button size="sm" variant="ghost" color="TextSecondary" onClick={onClose}>
          {tt('Закрыть')}
        </Button>
      </Flex>
    </>
  );
}

export function NotificationsBell({ guild }: { guild: string }) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const tt = useText();
  // Queries mount only after the first open, so pages don't pay the RPC cost.
  const [armed, setArmed] = useState(false);
  const [unread, setUnread] = useState(0);

  return (
    <Popover
      isOpen={isOpen}
      onOpen={() => {
        setArmed(true);
        onOpen();
      }}
      onClose={onClose}
      placement="bottom-end"
      gutter={8}
    >
      <PopoverTrigger>
        <Flex
          as="button"
          title={tt('Уведомления')}
          w="38px"
          h="38px"
          rounded="11px"
          border="1px solid"
          borderColor="CardBorder"
          align="center"
          justify="center"
          color="TextSecondary"
          position="relative"
          transition="background .15s ease"
          _hover={{ bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
        >
          <Icon as={MdNotifications} boxSize="19px" />
          {unread > 0 && (
            <Flex
              position="absolute"
              top="4px"
              right="5px"
              minW="15px"
              h="15px"
              px="4px"
              rounded="full"
              bg="red.400"
              color="white"
              fontSize="9.5px"
              fontWeight="700"
              align="center"
              justify="center"
              border="2px solid"
              borderColor="CardBackground"
            >
              {unread > 9 ? '9+' : unread}
            </Flex>
          )}
        </Flex>
      </PopoverTrigger>
      <Portal>
        <PopoverContent
          w="344px"
          bg="CardBackground"
          border="1px solid"
          borderColor="CardBorder"
          rounded="14px"
          boxShadow="normal"
          _focusVisible={{ outline: 'none', boxShadow: 'normal' }}
        >
          <PopoverBody p={0}>
            {armed && <PanelContent guild={guild} onClose={onClose} onUnread={setUnread} />}
          </PopoverBody>
        </PopoverContent>
      </Portal>
    </Popover>
  );
}
