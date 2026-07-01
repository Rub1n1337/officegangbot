import {
  Badge,
  Box,
  Flex,
  Heading,
  Icon,
  Input,
  InputGroup,
  InputLeftElement,
  Skeleton,
  Text,
} from '@chakra-ui/react';
import { MdHistory, MdSearch } from 'react-icons/md';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useAuditQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import {
  actionLabel,
  auditActionColor,
  describeAudit,
  formatDateTime,
  timeAgo,
} from '@/utils/audit';
import type { AuditEntry } from '@/config/types/custom-types';

function matches(e: AuditEntry, q: string): boolean {
  if (!q) return true;
  const hay = [e.actorName, e.action, e.target, e.detail, describeAudit(e)]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return hay.includes(q);
}

function AuditRow({ e }: { e: AuditEntry }) {
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
      <Flex gap={3} minW={0} align="flex-start">
        <Badge colorScheme={auditActionColor(e.action)} rounded="md" mt="2px" flexShrink={0}>
          {actionLabel(e.action)}
        </Badge>
        <Box minW={0}>
          <Text fontSize="sm">
            <Text as="span" fontWeight="600">
              {e.actorName ?? 'Someone'}
            </Text>{' '}
            {describeAudit(e)}
          </Text>
          {e.detail && (
            <Text fontSize="xs" color="TextSecondary" noOfLines={2}>
              {e.detail}
            </Text>
          )}
        </Box>
      </Flex>
      <Box textAlign="right" flexShrink={0}>
        <Text fontSize="xs" color="TextSecondary">
          {timeAgo(e.createdAt)}
        </Text>
        <Text fontSize="xs" color="TextSecondary" opacity={0.7}>
          {formatDateTime(e.createdAt)}
        </Text>
      </Box>
    </Flex>
  );
}

function AuditSkeleton() {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Skeleton h="40px" mb={3} rounded="xl" />
      <Flex direction="column" gap={2}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} h="52px" rounded="xl" />
        ))}
      </Flex>
    </Box>
  );
}

const AuditPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const query = useAuditQuery(guild);
  const [search, setSearch] = useState('');

  const rows = useMemo(() => query.data ?? [], [query.data]);
  const q = search.trim().toLowerCase();
  const filtered = useMemo(() => rows.filter((e) => matches(e, q)), [rows, q]);

  return (
    <Flex direction="column" gap={5}>
      <Flex align="center" gap={2}>
        <Icon as={MdHistory} fontSize="2xl" color="Brand" />
        <Heading fontSize="2xl" fontWeight="600">
          Audit log
        </Heading>
      </Flex>
      <Text fontSize="sm" color="TextSecondary" mt={-3}>
        Every action taken from this dashboard — moderation, feature changes and settings — with who
        did it and when.
      </Text>

      <QueryStatus query={query} loading={<AuditSkeleton />} error="Failed to load the audit log.">
        <Box bg="CardBackground" rounded="2xl" p={5}>
          <Flex align="center" justify="space-between" gap={3} mb={4} wrap="wrap">
            <InputGroup maxW="320px">
              <InputLeftElement pointerEvents="none">
                <Icon as={MdSearch} color="TextSecondary" />
              </InputLeftElement>
              <Input
                variant="main"
                placeholder="Search actor, action or detail…"
                value={search}
                onChange={(ev) => setSearch(ev.target.value)}
              />
            </InputGroup>
            <Text fontSize="sm" color="TextSecondary">
              {filtered.length} of {rows.length} entr{rows.length === 1 ? 'y' : 'ies'}
            </Text>
          </Flex>

          {rows.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              No dashboard actions recorded yet.
            </Text>
          ) : filtered.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              No entries match “{search}”.
            </Text>
          ) : (
            <Flex direction="column" gap={2}>
              {filtered.map((e) => (
                <AuditRow key={e.id} e={e} />
              ))}
            </Flex>
          )}
        </Box>
      </QueryStatus>
    </Flex>
  );
};

AuditPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default AuditPage;
