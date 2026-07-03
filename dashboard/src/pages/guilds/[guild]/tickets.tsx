import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
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
import { useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useTicketsQuery, useTicketTranscriptQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { ErrorPanel } from '@/components/panel/ErrorPanel';
import { timeAgo, formatDateTime } from '@/utils/audit';
import type { Ticket, TicketPriority } from '@/config/types/custom-types';

// Render this many rows at a time (with a "Show more") rather than mounting the
// full list — cheap windowing without a virtualization dependency.
const PAGE = 50;

const PRIORITY: Record<TicketPriority, { label: string; color: string }> = {
  low: { label: '🟢 Low', color: 'green' },
  medium: { label: '🟡 Medium', color: 'yellow' },
  high: { label: '🟠 High', color: 'orange' },
  urgent: { label: '🔴 Urgent', color: 'red' },
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
        <ModalHeader>Ticket transcript</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {query.isLoading && (
            <Flex justify="center" py={8}>
              <Spinner />
            </Flex>
          )}
          {query.isError && (
            <ErrorPanel retry={() => query.refetch()} isRetrying={query.isFetching}>
              Failed to load this transcript.
            </ErrorPanel>
          )}
          {query.data && (
            <Flex direction="column" gap={3}>
              <Flex gap={2} wrap="wrap" align="center" fontSize="sm" color="TextSecondary">
                <PriorityBadge priority={query.data.priority} />
                <Text>Opened by {query.data.openerName ?? 'unknown'}</Text>
                {query.data.closedByName && <Text>· closed by {query.data.closedByName}</Text>}
              </Flex>
              {query.data.closeComment && (
                <Box bg="blackAlpha.200" _dark={{ bg: 'whiteAlpha.50' }} rounded="lg" p={3}>
                  <Text fontSize="xs" color="TextSecondary" mb={1}>
                    Closing comment
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
                {query.data.transcript ?? 'No transcript was captured for this ticket.'}
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
    <Flex
      align="flex-start"
      justify="space-between"
      gap={3}
      p={3}
      rounded="xl"
      bg="blackAlpha.200"
      _dark={{ bg: 'whiteAlpha.50' }}
    >
      <Flex gap={3} flex="1" minW={0} align="flex-start">
        <PriorityBadge priority={t.priority} />
        <Box minW={0}>
          <Flex align="center" gap={2} wrap="wrap">
            <Text fontWeight="600" isTruncated maxW="100%">
              {t.openerName ?? t.openerId}
            </Text>
            <Badge colorScheme={t.status === 'open' ? 'green' : 'gray'} rounded="md" flexShrink={0}>
              {t.status}
            </Badge>
          </Flex>
          <Text fontSize="xs" color="TextSecondary" noOfLines={{ base: 2, sm: 1 }}>
            Opened {timeAgo(t.openedAt)}
            {t.closedAt && ` · closed ${timeAgo(t.closedAt)}`}
            {t.closedByName && ` by ${t.closedByName}`}
          </Text>
          {t.closeComment && (
            <Text fontSize="sm" color="TextSecondary" noOfLines={2} mt={1}>
              “{t.closeComment}”
            </Text>
          )}
        </Box>
      </Flex>
      {t.hasTranscript && (
        <Button
          size="xs"
          variant="outline"
          onClick={() => onView(t.id)}
          flexShrink={0}
          aria-label="View transcript"
        >
          <Icon as={MdDescription} />
          <Box as="span" display={{ base: 'none', sm: 'inline' }} ml={1.5}>
            Transcript
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

const TicketsPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const query = useTicketsQuery(guild);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<'all' | 'open' | 'closed'>('all');
  const [selected, setSelected] = useState<number | null>(null);
  const [visible, setVisible] = useState(PAGE);
  const { onClose } = useDisclosure();

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

  return (
    <Flex direction="column" gap={5}>
      <Flex align="center" gap={2}>
        <Icon as={MdConfirmationNumber} fontSize="2xl" color="Brand" />
        <Heading fontSize="2xl" fontWeight="600">
          Tickets
        </Heading>
        {openCount > 0 && (
          <Badge colorScheme="green" rounded="md">
            {openCount} open
          </Badge>
        )}
      </Flex>
      <Text fontSize="sm" color="TextSecondary" mt={-3}>
        Support tickets with priority, closing comments and full transcripts of closed conversations.
      </Text>

      <QueryStatus query={query} loading={<TicketsSkeleton />} error="Failed to load tickets.">
        <Box bg="CardBackground" rounded="2xl" p={5}>
          <Flex align="center" justify="space-between" gap={3} mb={4} wrap="wrap">
            <Flex gap={3} wrap="wrap" flex={1} w={{ base: 'full', sm: 'auto' }}>
              <InputGroup maxW={{ base: 'full', sm: '280px' }}>
                <InputLeftElement pointerEvents="none">
                  <Icon as={MdSearch} color="TextSecondary" />
                </InputLeftElement>
                <Input
                  variant="main"
                  placeholder="Search opener or comment…"
                  value={search}
                  onChange={(ev) => setSearch(ev.target.value)}
                />
              </InputGroup>
              <Select
                variant="main"
                maxW={{ base: 'full', sm: '160px' }}
                value={status}
                onChange={(ev) => setStatus(ev.target.value as 'all' | 'open' | 'closed')}
              >
                <option value="all">All statuses</option>
                <option value="open">Open</option>
                <option value="closed">Closed</option>
              </Select>
            </Flex>
            <Text fontSize="sm" color="TextSecondary">
              {filtered.length} of {rows.length}
            </Text>
          </Flex>

          {rows.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              No tickets have been opened yet.
            </Text>
          ) : filtered.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              No tickets match your filters.
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
                  Show more ({filtered.length - visible})
                </Button>
              )}
            </Flex>
          )}
        </Box>
      </QueryStatus>

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
