import {
  Badge,
  Box,
  Flex,
  Heading,
  Icon,
  Select,
  SimpleGrid,
  Skeleton,
  Text,
} from '@chakra-ui/react';
import { MdInsights } from 'react-icons/md';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useAnalyticsQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { StyledChart } from '@/components/chart/StyledChart';
import type { AnalyticsData, DayCount, ModActionDay } from '@/config/types/custom-types';

const PERIODS = [
  { value: 7, label: 'Last 7 days' },
  { value: 30, label: 'Last 30 days' },
  { value: 90, label: 'Last 90 days' },
];

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const BRAND = '#4318FF';

function titleCase(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function shortDay(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function sum(rows: { count: number }[]): number {
  return rows.reduce((a, r) => a + r.count, 0);
}

function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Text fontSize="sm" color="TextSecondary">
        {label}
      </Text>
      <Text fontSize="3xl" fontWeight="700" lineHeight="1.2" mt={1}>
        {value}
      </Text>
      {hint && (
        <Text fontSize="xs" color="TextSecondary" mt={1}>
          {hint}
        </Text>
      )}
    </Box>
  );
}

function ChartCard({
  title,
  subtitle,
  isEmpty,
  emptyText,
  children,
}: {
  title: string;
  subtitle?: string;
  isEmpty: boolean;
  emptyText: string;
  children: React.ReactNode;
}) {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Heading size="sm">{title}</Heading>
      {subtitle && (
        <Text fontSize="xs" color="TextSecondary" mt={1}>
          {subtitle}
        </Text>
      )}
      <Box mt={4}>
        {isEmpty ? (
          <Flex align="center" justify="center" py={10}>
            <Text fontSize="sm" color="TextSecondary">
              {emptyText}
            </Text>
          </Flex>
        ) : (
          children
        )}
      </Box>
    </Box>
  );
}

// The heatmap is 7 rows (weekdays) × 24 columns (hours). ApexCharts draws the
// first series at the bottom, so reverse to put Monday on top.
function heatmapSeries(cells: AnalyticsData['heatmap']) {
  const byKey = new Map(cells.map((c) => [c.weekday * 24 + c.hour, c.count]));
  return WEEKDAYS.map((name, wd) => ({
    name,
    data: Array.from({ length: 24 }, (_, h) => ({ x: `${h}`, y: byKey.get(wd * 24 + h) ?? 0 })),
  })).reverse();
}

// Pivot mod actions into one series per action type, aligned to a shared set of
// day categories, for a stacked bar chart.
function pivotActions(rows: ModActionDay[]) {
  const days = Array.from(new Set(rows.map((r) => r.day))).sort();
  const actions = Array.from(new Set(rows.map((r) => r.action))).sort();
  const byKey = new Map(rows.map((r) => [`${r.day}|${r.action}`, r.count]));
  const series = actions.map((a) => ({
    name: titleCase(a),
    data: days.map((d) => byKey.get(`${d}|${a}`) ?? 0),
  }));
  return { categories: days.map(shortDay), series };
}

// Align opened/closed ticket counts to one shared, sorted set of days.
function ticketSeries(opened: DayCount[], closed: DayCount[]) {
  const days = Array.from(new Set([...opened, ...closed].map((r) => r.day))).sort();
  const o = new Map(opened.map((r) => [r.day, r.count]));
  const c = new Map(closed.map((r) => [r.day, r.count]));
  return {
    categories: days.map(shortDay),
    series: [
      { name: 'Opened', data: days.map((d) => o.get(d) ?? 0) },
      { name: 'Closed', data: days.map((d) => c.get(d) ?? 0) },
    ],
  };
}

function AnalyticsSkeleton() {
  return (
    <Flex direction="column" gap={5}>
      <SimpleGrid columns={{ base: 2, md: 4 }} gap={4}>
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} h="96px" rounded="2xl" />
        ))}
      </SimpleGrid>
      <Skeleton h="320px" rounded="2xl" />
      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={5}>
        <Skeleton h="300px" rounded="2xl" />
        <Skeleton h="300px" rounded="2xl" />
      </SimpleGrid>
    </Flex>
  );
}

function AnalyticsBody({ data }: { data: AnalyticsData }) {
  const heatmap = useMemo(() => heatmapSeries(data.heatmap), [data.heatmap]);
  const actions = useMemo(() => pivotActions(data.modActionsByDay), [data.modActionsByDay]);
  const tickets = useMemo(
    () => ticketSeries(data.ticketsOpenedByDay, data.ticketsClosedByDay),
    [data.ticketsOpenedByDay, data.ticketsClosedByDay]
  );

  const totalMod = sum(data.modActionsByDay);
  const totalAutomod = sum(data.automodByDay);
  const totalOpened = sum(data.ticketsOpenedByDay);
  const heatmapEmpty = data.heatmap.every((c) => c.count === 0) || data.heatmap.length === 0;
  const maxMods = Math.max(1, ...data.topModerators.map((m) => m.count));

  return (
    <Flex direction="column" gap={5}>
      <SimpleGrid columns={{ base: 2, md: 4 }} gap={4}>
        <StatCard label="Moderation actions" value={totalMod.toLocaleString()} hint={`last ${data.days} days`} />
        <StatCard label="AutoMod violations" value={totalAutomod.toLocaleString()} hint={`last ${data.days} days`} />
        <StatCard label="Tickets opened" value={totalOpened.toLocaleString()} hint={`last ${data.days} days`} />
        <StatCard
          label="Avg ticket resolution"
          value={data.avgTicketResolutionHours != null ? `${data.avgTicketResolutionHours}h` : '—'}
          hint={data.avgTicketResolutionHours != null ? 'open → closed' : 'no closed tickets'}
        />
      </SimpleGrid>

      <ChartCard
        title="Activity heatmap"
        subtitle="Messages by weekday and hour (UTC). Aggregate counts only — no message content is stored."
        isEmpty={heatmapEmpty}
        emptyText="No activity recorded yet. Counts start accumulating from now on."
      >
        <StyledChart
          type="heatmap"
          height={320}
          series={heatmap}
          options={{
            chart: { toolbar: { show: false } },
            dataLabels: { enabled: false },
            colors: [BRAND],
            legend: { show: false },
            plotOptions: { heatmap: { radius: 2, enableShades: true, shadeIntensity: 0.55 } },
            xaxis: {
              type: 'category',
              tickAmount: 12,
              labels: { rotate: 0 },
            },
            tooltip: { y: { formatter: (v: number) => `${v} messages` } },
          }}
        />
      </ChartCard>

      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={5}>
        <ChartCard
          title="Moderation actions over time"
          subtitle="From the numbered moderation cases, stacked by action type."
          isEmpty={actions.series.length === 0}
          emptyText="No moderation cases in this period."
        >
          <StyledChart
            type="bar"
            height={300}
            series={actions.series}
            options={{
              chart: { stacked: true, toolbar: { show: false } },
              plotOptions: { bar: { borderRadius: 3, columnWidth: '60%' } },
              dataLabels: { enabled: false },
              xaxis: { categories: actions.categories },
              legend: { show: true, position: 'top' },
            }}
          />
        </ChartCard>

        <ChartCard
          title="Tickets opened vs closed"
          subtitle="Daily open/close volume over the period."
          isEmpty={tickets.series[0].data.length === 0}
          emptyText="No ticket activity in this period."
        >
          <StyledChart
            type="bar"
            height={300}
            series={tickets.series}
            options={{
              chart: { toolbar: { show: false } },
              colors: [BRAND, '#39B8FF'],
              plotOptions: { bar: { borderRadius: 3, columnWidth: '60%' } },
              dataLabels: { enabled: false },
              xaxis: { categories: tickets.categories },
              legend: { show: true, position: 'top' },
            }}
          />
        </ChartCard>
      </SimpleGrid>

      <Box bg="CardBackground" rounded="2xl" p={5}>
        <Heading size="sm" mb={4}>
          Top moderators
        </Heading>
        {data.topModerators.length === 0 ? (
          <Text fontSize="sm" color="TextSecondary">
            No moderation cases in this period.
          </Text>
        ) : (
          <Flex direction="column" gap={3}>
            {data.topModerators.map((m, i) => (
              <Flex key={m.name} align="center" gap={3}>
                <Text fontSize="sm" w="1.5em" color="TextSecondary" textAlign="center">
                  {i + 1}
                </Text>
                <Text fontSize="sm" fontWeight="600" minW="120px" isTruncated>
                  {m.name}
                </Text>
                <Box flex={1} bg="blackAlpha.200" _dark={{ bg: 'whiteAlpha.100' }} rounded="full" h="8px">
                  <Box bg="Brand" rounded="full" h="8px" w={`${(m.count / maxMods) * 100}%`} />
                </Box>
                <Badge rounded="md" colorScheme="purple" flexShrink={0}>
                  {m.count}
                </Badge>
              </Flex>
            ))}
          </Flex>
        )}
      </Box>
    </Flex>
  );
}

const AnalyticsPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const [days, setDays] = useState(30);
  const query = useAnalyticsQuery(guild, days);

  return (
    <Flex direction="column" gap="18px">
      <Flex align="flex-end" justify="space-between" gap="12px" wrap="wrap">
        <Box>
          <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
            АНАЛИТИКА
          </Text>
          <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt="3px">
            Тренды и модерация
          </Heading>
          <Text fontSize="13.5px" color="TextSecondary" mt="4px">
            Тренды активности и модерации. Хитмап использует только агрегатные счётчики сообщений —
            содержимое, автор и время не хранятся.
          </Text>
        </Box>
        <Select
          bg="CardBackground"
          border="1px solid"
          borderColor="CardBorder"
          rounded="11px"
          w="auto"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          {PERIODS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </Select>
      </Flex>

      <QueryStatus query={query} loading={<AnalyticsSkeleton />} error="Failed to load analytics.">
        {query.data && <AnalyticsBody data={query.data} />}
      </QueryStatus>
    </Flex>
  );
};

AnalyticsPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default AnalyticsPage;
