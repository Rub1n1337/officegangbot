import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Highlight,
  Icon,
  Input,
  InputGroup,
  InputLeftElement,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Select,
  Skeleton,
  Spinner,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { MdConfirmationNumber, MdSearch, MdDescription } from 'react-icons/md';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useTicketsQuery, useTicketSearchQuery, useTicketTranscriptQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { ErrorPanel } from '@/components/panel/ErrorPanel';
import { timeAgo, formatDateTime } from '@/utils/audit';
import type { Ticket, TicketPriority } from '@/config/types/custom-types';

// Render this many rows at a time (with a "Show more") rather than mounting the
// full list — cheap windowing without a virtualization dependency.
const PAGE = 50;

// Iris "inset" row surface — a defined step below the card.
const INSET = { bg: 'secondaryGray.100', _dark: { bg: 'navy.600' } };

const PRIORITY: Record<TicketPriority, { label: string; color: string }> = {
  low: { label: '🟢 Низкий', color: 'green' },
  medium: { label: '🟡 Средний', color: 'yellow' },
  high: { label: '🟠 Высокий', color: 'orange' },
  urgent: { label: '🔴 Срочный', color: 'red' },
};

function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const p = PRIORITY[priority] ?? PRIORITY.medium;
  return (
    <Badge colorScheme={p.color} rounded="md" flexShrink={0}>
      {p.label}
    </Badge>
  );
}

function TranscriptModal({
  guild,
  ticketId,
  onClose,
}: {
  guild: string;
  ticketId: number | null;
  onClose: () => void;
}) {
  const query = useTicketTranscriptQuery(guild, ticketId);
  const open = ticketId !== null;

  return (
    <Modal isOpen={open} onClose={onClose} size="2xl" scrollBehavior="inside" isCentered>
      <ModalOverlay />
      <ModalContent bg="CardBackground">
        <ModalHeader>Транскрипт тикета</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {query.isLoading && (
            <Flex justify="center" py={8}>
              <Spinner />
            </Flex>
          )}
          {query.isError && (
            <ErrorPanel retry={() => query.refetch()} isRetrying={query.isFetching}>
              Не удалось загрузить транскрипт.
            </ErrorPanel>
          )}
          {query.data && (
            <Flex direction="column" gap={3}>
              <Flex gap={2} wrap="wrap" align="center" fontSize="sm" color="TextSecondary">
                <PriorityBadge priority={query.data.priority} />
                <Text>Открыл {query.data.openerName ?? 'неизвестно'}</Text>
                {query.data.closedByName && <Text>· закрыл {query.data.closedByName}</Text>}
              </Flex>
              {query.data.closeComment && (
                <Box rounded="11px" p={3} {...INSET}>
                  <Text fontSize="xs" color="TextSecondary" mb={1}>
                    Комментарий при закрытии
                  </Text>
                  <Text fontSize="sm">{query.data.closeComment}</Text>
                </Box>
              )}
              <Box
                as="pre"
                fontSize="xs"
                whiteSpace="pre-wrap"
                fontFamily="mono"
                bg="blackAlpha.300"
                _dark={{ bg: 'blackAlpha.400' }}
                rounded="lg"
                p={3}
                maxH="55vh"
                overflowY="auto"
              >
                {query.data.transcript ?? 'Транскрипт для этого тикета не сохранён.'}
              </Box>
            </Flex>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}

function TicketRow({ t, onView }: { t: Ticket; onView: (id: number) => void }) {
  return (
    <Flex align="flex-start" gap="12px" rounded="11px" p="12px 14px" {...INSET}>
      <Flex gap="12px" flex="1" minW={0} align="flex-start">
        <PriorityBadge priority={t.priority} />
        <Box minW={0}>
          <Flex align="center" gap="8px" wrap="wrap">
            <Text fontSize="13.5px" fontWeight="600" isTruncated maxW="100%">
              {t.openerName ?? t.openerId}
            </Text>
            <Badge colorScheme={t.status === 'open' ? 'green' : 'gray'} rounded="20px" px="9px" flexShrink={0}>
              {t.status === 'open' ? 'открыт' : 'закрыт'}
            </Badge>
          </Flex>
          <Text fontSize="11.5px" color="TextSecondary" noOfLines={{ base: 2, sm: 1 }} mt="2px">
            Открыт {timeAgo(t.openedAt)}
            {t.closedAt && ` · закрыт ${timeAgo(t.closedAt)}`}
            {t.closedByName && `, ${t.closedByName}`}
          </Text>
          {t.closeComment && (
            <Text fontSize="12.5px" color="TextSecondary" noOfLines={2} mt="4px">
              «{t.closeComment}»
            </Text>
          )}
        </Box>
      </Flex>
      {t.hasTranscript && (
        <Button
          size="sm"
          rounded="9px"
          variant="outline"
          borderColor="CardBorder"
          onClick={() => onView(t.id)}
          flexShrink={0}
          aria-label="Открыть транскрипт"
          _hover={{ borderColor: 'brand.400' }}
        >
          <Icon as={MdDescription} />
          <Box as="span" display={{ base: 'none', sm: 'inline' }} ml={1.5}>
            Транскрипт
          </Box>
        </Button>
      )}
    </Flex>
  );
}

function TicketsSkeleton() {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Skeleton h="40px" mb={3} rounded="xl" />
      <Flex direction="column" gap={2}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} h="56px" rounded="xl" />
        ))}
      </Flex>
    </Box>
  );
}

function TranscriptHits({
  hits,
  query,
  isLoading,
  onView,
}: {
  hits: Ticket[];
  query: string;
  isLoading: boolean;
  onView: (id: number) => void;
}) {
  if (query.length < 2) return null;
  return (
    <Box bg="CardBackground" rounded="16px" p="20px" border="1px solid" borderColor="CardBorder" boxShadow="normal">
      <Flex align="center" gap="10px" mb="14px">
        <Icon as={MdSearch} color="brand.200" boxSize="20px" />
        <Heading fontSize="15px" fontWeight="700">Найдено в транскриптах</Heading>
        {hits.length > 0 && (
          <Box as="span" fontSize="12px" fontWeight="700" rounded="20px" px="9px" color="TextSecondary" bg="blackAlpha.100" _dark={{ bg: 'whiteAlpha.100' }}>
            {hits.length}
          </Box>
        )}
      </Flex>
      {isLoading ? (
        <Flex justify="center" py={4}>
          <Spinner size="sm" />
        </Flex>
      ) : hits.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          В транскриптах нет совпадений по «{query}».
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {hits.map((t) => (
            <Flex key={t.id} align="flex-start" gap="12px" rounded="11px" p="12px 14px" {...INSET}>
              <Flex gap="12px" flex="1" minW={0} align="flex-start">
                <PriorityBadge priority={t.priority} />
                <Box minW={0}>
                  <Text fontSize="13.5px" fontWeight="600" isTruncated maxW="100%">
                    {t.openerName ?? t.openerId}
                  </Text>
                  {t.snippet && (
                    <Text fontSize="11.5px" color="TextSecondary" noOfLines={2} mt={0.5}>
                      …
                      <Highlight
                        query={query}
                        styles={{ px: '0.5', bg: 'yellow.200', color: 'black', rounded: 'sm' }}
                      >
                        {t.snippet}
                      </Highlight>
                      …
                    </Text>
                  )}
                </Box>
              </Flex>
              {t.hasTranscript && (
                <Button
                  size="sm"
                  rounded="9px"
                  variant="outline"
                  borderColor="CardBorder"
                  onClick={() => onView(t.id)}
                  flexShrink={0}
                  aria-label="Открыть транскрипт"
                  _hover={{ borderColor: 'brand.400' }}
                >
                  <Icon as={MdDescription} />
                  <Box as="span" display={{ base: 'none', sm: 'inline' }} ml={1.5}>
                    Транскрипт
                  </Box>
                </Button>
              )}
            </Flex>
          ))}
        </Flex>
      )}
    </Box>
  );
}

const TicketsPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const query = useTicketsQuery(guild);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<'all' | 'open' | 'closed'>('all');
  const [selected, setSelected] = useState<number | null>(null);
  const [visible, setVisible] = useState(PAGE);
  const { onClose } = useDisclosure();

  // Debounce the transcript-search request so it doesn't fire on every keystroke.
  const [debounced, setDebounced] = useState('');
  useEffect(() => {
    const id = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(id);
  }, [search]);
  const searchQuery = useTicketSearchQuery(guild, debounced);

  const rows = useMemo(() => query.data ?? [], [query.data]);
  const q = search.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      rows.filter((t) => {
        if (status !== 'all' && t.status !== status) return false;
        if (!q) return true;
        const hay = [t.openerName, t.openerId, t.priority, t.status, t.closedByName, t.closeComment]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return hay.includes(q);
      }),
    [rows, q, status]
  );

  const openCount = rows.filter((t) => t.status === 'open').length;

  // Transcript matches that aren't already visible in the metadata list above,
  // and only for the closed-status view (open tickets have no transcript yet).
  const shownIds = useMemo(() => new Set(filtered.map((t) => t.id)), [filtered]);
  const transcriptHits = useMemo(
    () =>
      (searchQuery.data ?? []).filter(
        (t) => !shownIds.has(t.id) && (status === 'all' || t.status === status)
      ),
    [searchQuery.data, shownIds, status]
  );

  return (
    <Flex direction="column" gap="18px">
      <Box>
        <Flex align="center" gap="12px" wrap="wrap">
          <Box>
            <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
              ТИКЕТЫ
            </Text>
            <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt="3px">
              Поддержка
            </Heading>
          </Box>
          {openCount > 0 && (
            <Badge color="green.500" bg="green.100" _dark={{ bg: 'whiteAlpha.100', color: 'green.400' }} rounded="20px" px="11px" py="4px" fontSize="12px">
              {openCount} открыто
            </Badge>
          )}
        </Flex>
        <Text fontSize="13.5px" color="TextSecondary" mt="4px">
          Тикеты поддержки с приоритетом, комментариями при закрытии и полными транскриптами
          закрытых обращений.
        </Text>
      </Box>

      <QueryStatus query={query} loading={<TicketsSkeleton />} error="Failed to load tickets.">
        <Box bg="CardBackground" rounded="16px" p="20px" border="1px solid" borderColor="CardBorder" boxShadow="normal">
          <Flex align="center" justify="space-between" gap={3} mb={4} wrap="wrap">
            <Flex gap={3} wrap="wrap" flex={1} w={{ base: 'full', sm: 'auto' }}>
              <InputGroup maxW={{ base: 'full', sm: '280px' }}>
                <InputLeftElement pointerEvents="none">
                  <Icon as={MdSearch} color="TextSecondary" />
                </InputLeftElement>
                <Input
                  variant="main"
                  placeholder="Поиск по тикетам и транскриптам…"
                  value={search}
                  onChange={(ev) => setSearch(ev.target.value)}
                />
              </InputGroup>
              <Select
                variant="main"
                maxW={{ base: 'full', sm: '170px' }}
                value={status}
                onChange={(ev) => setStatus(ev.target.value as 'all' | 'open' | 'closed')}
              >
                <option value="all">Все статусы</option>
                <option value="open">Открытые</option>
                <option value="closed">Закрытые</option>
              </Select>
            </Flex>
            <Text fontSize="sm" color="TextSecondary">
              {filtered.length} из {rows.length}
            </Text>
          </Flex>

          {rows.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              Тикеты ещё не открывались.
            </Text>
          ) : filtered.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              Ничего не найдено по фильтрам.
            </Text>
          ) : (
            <Flex direction="column" gap={2}>
              {filtered.slice(0, visible).map((t) => (
                <TicketRow key={t.id} t={t} onView={setSelected} />
              ))}
              {filtered.length > visible && (
                <Button
                  size="sm"
                  variant="ghost"
                  alignSelf="center"
                  mt={1}
                  onClick={() => setVisible((v) => v + PAGE)}
                >
                  Показать ещё ({filtered.length - visible})
                </Button>
              )}
            </Flex>
          )}
        </Box>
      </QueryStatus>

      <TranscriptHits
        hits={transcriptHits}
        query={debounced}
        isLoading={searchQuery.isFetching}
        onView={setSelected}
      />

      <TranscriptModal
        guild={guild}
        ticketId={selected}
        onClose={() => {
          setSelected(null);
          onClose();
        }}
      />
    </Flex>
  );
};

TicketsPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default TicketsPage;
