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
  Select,
  Skeleton,
  Text,
} from '@chakra-ui/react';
import { MdHistory, MdSearch, MdDownload } from 'react-icons/md';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useAuditQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import {
  actionLabel,
  auditActionColor,
  auditToCsv,
  describeAudit,
  formatDateTime,
  timeAgo,
} from '@/utils/audit';
import type { AuditEntry } from '@/config/types/custom-types';

// Render this many rows at a time (with a "Show more") rather than mounting the
// full list — cheap windowing without a virtualization dependency.
const PAGE = 50;

const PERIODS: Record<string, { label: string; days: number | null }> = {
  all: { label: 'All time', days: null },
  '1': { label: 'Last 24 hours', days: 1 },
  '7': { label: 'Last 7 days', days: 7 },
  '30': { label: 'Last 30 days', days: 30 },
};

function matchesSearch(e: AuditEntry, q: string): boolean {
  if (!q) return true;
  const hay = [e.actorName, e.action, e.target, e.detail, describeAudit(e)]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return hay.includes(q);
}

function withinPeriod(e: AuditEntry, days: number | null): boolean {
  if (days == null) return true;
  if (!e.createdAt) return false;
  const t = Date.parse(e.createdAt);
  return !Number.isNaN(t) && t >= Date.now() - days * 86_400_000;
}

function downloadCsv(filename: string, csv: string) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
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
  const [action, setAction] = useState('all');
  const [period, setPeriod] = useState('all');
  const [visible, setVisible] = useState(PAGE);

  const rows = useMemo(() => query.data ?? [], [query.data]);
  // The distinct action types present, so the dropdown only offers real values.
  const actionOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.action))).sort(),
    [rows]
  );

  const q = search.trim().toLowerCase();
  const days = PERIODS[period]?.days ?? null;
  const filtered = useMemo(
    () =>
      rows.filter(
        (e) =>
          matchesSearch(e, q) &&
          (action === 'all' || e.action === action) &&
          withinPeriod(e, days)
      ),
    [rows, q, action, days]
  );

  const filtersActive = q !== '' || action !== 'all' || period !== 'all';

  return (
    <Flex direction="column" gap="18px">
      <Box>
        <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
          ЖУРНАЛ
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt="3px">
          Активность дашборда
        </Heading>
        <Text fontSize="13.5px" color="TextSecondary" mt="4px">
          Каждое действие из этого дашборда — модерация, изменения функций и настроек — с автором и
          временем.
        </Text>
      </Box>

      <QueryStatus query={query} loading={<AuditSkeleton />} error="Failed to load the audit log.">
        <Box bg="CardBackground" rounded="2xl" p={5}>
          <Flex align="center" gap={3} mb={4} wrap="wrap">
            <InputGroup maxW="260px">
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

            <Select
              variant="main"
              maxW="200px"
              value={action}
              onChange={(ev) => setAction(ev.target.value)}
            >
              <option value="all">All actions</option>
              {actionOptions.map((a) => (
                <option key={a} value={a}>
                  {actionLabel(a)}
                </option>
              ))}
            </Select>

            <Select
              variant="main"
              maxW="160px"
              value={period}
              onChange={(ev) => setPeriod(ev.target.value)}
            >
              {Object.entries(PERIODS).map(([key, { label }]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </Select>

            <Text fontSize="sm" color="TextSecondary">
              {filtered.length} of {rows.length}
            </Text>

            <Button
              size="sm"
              variant="outline"
              leftIcon={<Icon as={MdDownload} />}
              ml="auto"
              isDisabled={filtered.length === 0}
              onClick={() =>
                downloadCsv(
                  `audit-${guild}-${new Date().toISOString().slice(0, 10)}.csv`,
                  auditToCsv(filtered)
                )
              }
            >
              Export CSV
            </Button>
          </Flex>

          {rows.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              No dashboard actions recorded yet.
            </Text>
          ) : filtered.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              No entries match your filters.
            </Text>
          ) : (
            <Flex direction="column" gap={2}>
              {filtered.slice(0, visible).map((e) => (
                <AuditRow key={e.id} e={e} />
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

          {filtersActive && filtered.length > 0 && (
            <Text fontSize="xs" color="TextSecondary" mt={3} textAlign="center">
              Export includes the {filtered.length} filtered {filtered.length === 1 ? 'entry' : 'entries'}.
            </Text>
          )}
        </Box>
      </QueryStatus>
    </Flex>
  );
};

AuditPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default AuditPage;
