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
import { provider } from '@/config/translations/provider';
import { useText } from '@/config/translations/ui-text';
import type { Languages } from '@/config/translations/provider';
import type { AuditEntry } from '@/config/types/custom-types';

// Render this many rows at a time (with a "Show more") rather than mounting the
// full list — cheap windowing without a virtualization dependency.
const PAGE = 50;

const PERIODS: Record<string, { label: string; days: number | null }> = {
  all: { label: 'Всё время', days: null },
  '1': { label: 'За 24 часа', days: 1 },
  '7': { label: 'За 7 дней', days: 7 },
  '30': { label: 'За 30 дней', days: 30 },
};

function matchesSearch(e: AuditEntry, q: string): boolean {
  if (!q) return true;
  const hay = [e.actorName, e.action, e.target, e.detail, describeAudit(e, 'ru'), describeAudit(e, 'en')]
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

function AuditRow({ e, lang }: { e: AuditEntry; lang: Languages }) {
  return (
    <Flex align="flex-start" justify="space-between" gap={3} rounded="11px" p="12px 14px" bg="secondaryGray.100" _dark={{ bg: 'navy.600' }}>
      <Flex gap={3} minW={0} align="flex-start">
        <Badge colorScheme={auditActionColor(e.action)} rounded="20px" px="9px" mt="1px" flexShrink={0}>
          {actionLabel(e.action, lang)}
        </Badge>
        <Box minW={0}>
          <Text fontSize="sm">
            <Text as="span" fontWeight="600">
              {e.actorName ?? 'Someone'}
            </Text>{' '}
            {describeAudit(e, lang)}
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
          {timeAgo(e.createdAt, lang)}
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
  const lang = provider.useLang();
  const tt = useText();

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
          {tt('ЖУРНАЛ')}
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt="3px">
          {tt('Активность дашборда')}
        </Heading>
        <Text fontSize="13.5px" color="TextSecondary" mt="4px">
          {tt('Каждое действие из этого дашборда — модерация, изменения функций и настроек — с автором и временем.')}
        </Text>
      </Box>

      <QueryStatus query={query} loading={<AuditSkeleton />} error="Failed to load the audit log.">
        <Box bg="CardBackground" rounded="16px" p="20px" border="1px solid" borderColor="CardBorder" boxShadow="normal">
          <Flex align="center" gap={3} mb={4} wrap="wrap">
            <InputGroup maxW="260px">
              <InputLeftElement pointerEvents="none">
                <Icon as={MdSearch} color="TextSecondary" />
              </InputLeftElement>
              <Input
                variant="main"
                placeholder={tt('Поиск по автору, действию, деталям…')}
                value={search}
                onChange={(ev) => setSearch(ev.target.value)}
              />
            </InputGroup>

            <Select
              variant="main"
              maxW="220px"
              value={action}
              onChange={(ev) => setAction(ev.target.value)}
            >
              <option value="all">{tt('Все действия')}</option>
              {actionOptions.map((a) => (
                <option key={a} value={a}>
                  {actionLabel(a, lang)}
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
                  {tt(label)}
                </option>
              ))}
            </Select>

            <Text fontSize="sm" color="TextSecondary">
              {filtered.length} {tt('из')} {rows.length}
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
              {tt('Экспорт CSV')}
            </Button>
          </Flex>

          {rows.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              {tt('Действий из дашборда пока нет.')}
            </Text>
          ) : filtered.length === 0 ? (
            <Text fontSize="sm" color="TextSecondary" py={4} textAlign="center">
              {tt('Ничего не найдено по фильтрам.')}
            </Text>
          ) : (
            <Flex direction="column" gap={2}>
              {filtered.slice(0, visible).map((e) => (
                <AuditRow key={e.id} e={e} lang={lang} />
              ))}
              {filtered.length > visible && (
                <Button
                  size="sm"
                  variant="ghost"
                  alignSelf="center"
                  mt={1}
                  onClick={() => setVisible((v) => v + PAGE)}
                >
                  {tt('Показать ещё')} ({filtered.length - visible})
                </Button>
              )}
            </Flex>
          )}

          {filtersActive && filtered.length > 0 && (
            <Text fontSize="xs" color="TextSecondary" mt={3} textAlign="center">
              {tt('В экспорт войдут отфильтрованные записи:')} {filtered.length}.
            </Text>
          )}
        </Box>
      </QueryStatus>
    </Flex>
  );
};

AuditPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default AuditPage;
