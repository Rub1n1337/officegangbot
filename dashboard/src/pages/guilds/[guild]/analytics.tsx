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
  useBreakpointValue,
} from '@chakra-ui/react';
import { MdInsights } from 'react-icons/md';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useAnalyticsQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { StyledChart } from '@/components/chart/StyledChart';
import { tabularNums } from '@/theme/numeric';
import type { AnalyticsData, DayCount, ModActionDay } from '@/config/types/custom-types';
import { useText } from '@/config/translations/ui-text';
import { MdDownload } from 'react-icons/md';
import { Button, Icon as ChakraIcon } from '@chakra-ui/react';

const PERIODS = [
  { value: 7, label: 'За 7 дней' },
  { value: 30, label: 'За 30 дней' },
  { value: 90, label: 'За 90 дней' },
];

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const BRAND = '#6E56F5';

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
    <Box
      bg="CardBackground"
      rounded="16px"
      p={5}
      border="1px solid"
      borderColor="CardBorder"
      boxShadow="normal"
      transition="transform .18s ease, border-color .18s ease"
      _hover={{ transform: 'translateY(-4px)', borderColor: 'brand.400' }}
    >
      <Text fontSize="12px" color="TextSecondary" fontWeight="500">
        {label}
      </Text>
      <Text fontSize="28px" fontWeight="800" letterSpacing="-0.02em" lineHeight="1" mt={2} sx={tabularNums}>
        {value}
      </Text>
      {hint && (
        <Text fontSize="11px" color="TextSecondary" mt={2}>
          {hint}
        </Text>
      )}
    </Box>
  );
}

function ChartCard({
  title,
  subtitle,
  insight,
  isEmpty,
  emptyText,
  children,
}: {
  title: string;
  subtitle?: string;
  // A one-line takeaway read from the data — interpretation next to the chart,
  // not just the chart. Hidden when there's nothing to show.
  insight?: React.ReactNode;
  isEmpty: boolean;
  emptyText: string;
  children: React.ReactNode;
}) {
  return (
    <Box bg="CardBackground" rounded="16px" p={5} border="1px solid" borderColor="CardBorder" boxShadow="normal">
      <Heading fontSize="15px" fontWeight="700">{title}</Heading>
      {subtitle && (
        <Text fontSize="xs" color="TextSecondary" mt={1}>
          {subtitle}
        </Text>
      )}
      {insight && !isEmpty && (
        <Flex align="center" gap={2} mt={2.5} fontSize="13px" fontWeight="600" color="brand.200" sx={tabularNums}>
          <Icon as={MdInsights} boxSize="15px" flexShrink={0} />
          <Text>{insight}</Text>
        </Flex>
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

// The heatmap is 7 rows (weekdays) × 24 columns (hours). Counters are stored
// in UTC; shift each cell by the browser's UTC offset so the chart reads in
// the viewer's local time. ApexCharts draws the first series at the bottom,
// so reverse to put Monday on top.
function heatmapSeries(cells: AnalyticsData['heatmap'], tt: (ru: string) => string, compact = false) {
  const offsetH = Math.round(-new Date().getTimezoneOffset() / 60);
  const byKey = new Map(
    cells.map((c) => {
      const shifted = c.weekday * 24 + c.hour + offsetH;
      const key = ((shifted % 168) + 168) % 168; // wrap within the week
      return [key, c.count];
    })
  );
  // On a phone, 24 hourly columns squash into unreadable slivers. Fold them into
  // six 4-hour blocks (00–04 … 20–24) so cells stay legible without scrolling.
  const cols = compact ? 6 : 24;
  const span = compact ? 4 : 1;
  return WEEKDAYS.map((name, wd) => ({
    name: tt(name),
    data: Array.from({ length: cols }, (_, i) => {
      const start = i * span;
      let y = 0;
      for (let h = start; h < start + span; h++) y += byKey.get(wd * 24 + h) ?? 0;
      const x = compact ? `${String(start).padStart(2, '0')}–${start + span}` : `${start}`;
      return { x, y };
    }),
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
function ticketSeries(opened: DayCount[], closed: DayCount[], tt: (ru: string) => string) {
  const days = Array.from(new Set([...opened, ...closed].map((r) => r.day))).sort();
  const o = new Map(opened.map((r) => [r.day, r.count]));
  const c = new Map(closed.map((r) => [r.day, r.count]));
  return {
    categories: days.map(shortDay),
    series: [
      { name: tt('Открыто'), data: days.map((d) => o.get(d) ?? 0) },
      { name: tt('Закрыто'), data: days.map((d) => c.get(d) ?? 0) },
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

function analyticsToCsv(data: AnalyticsData): string {
  const esc = (v: unknown) => {
    const s = v == null ? '' : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = ['Section,Day,Key,Count'];
  for (const r of data.modActionsByDay) lines.push(['mod_actions', r.day, r.action, r.count].map(esc).join(','));
  for (const r of data.automodByDay) lines.push(['automod', r.day, '', r.count].map(esc).join(','));
  for (const r of data.ticketsOpenedByDay) lines.push(['tickets_opened', r.day, '', r.count].map(esc).join(','));
  for (const r of data.ticketsClosedByDay) lines.push(['tickets_closed', r.day, '', r.count].map(esc).join(','));
  return '﻿' + lines.join('\r\n');
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

function AnalyticsBody({ data }: { data: AnalyticsData }) {
  const tt = useText();
  // Fold 24 hourly columns into six 4-hour blocks below md, where they'd
  // otherwise be unreadable slivers. useBreakpointValue re-runs on resize.
  const compactHeatmap = useBreakpointValue({ base: true, md: false }) ?? false;
  const heatmap = useMemo(
    () => heatmapSeries(data.heatmap, tt, compactHeatmap),
    [data.heatmap, tt, compactHeatmap]
  );
  const actions = useMemo(() => pivotActions(data.modActionsByDay), [data.modActionsByDay]);
  const tickets = useMemo(
    () => ticketSeries(data.ticketsOpenedByDay, data.ticketsClosedByDay, tt),
    [data.ticketsOpenedByDay, data.ticketsClosedByDay, tt]
  );

  const totalMod = sum(data.modActionsByDay);
  const totalAutomod = sum(data.automodByDay);
  const totalOpened = sum(data.ticketsOpenedByDay);
  const heatmapEmpty = data.heatmap.every((c) => c.count === 0) || data.heatmap.length === 0;
  const maxMods = Math.max(1, ...data.topModerators.map((m) => m.count));

  // Interpretation, not just visualization: read the single takeaway out of the
  // data and put it next to the chart. Peak activity window from the heatmap,
  // shifted to local time the same way the cells are.
  const peakInsight = useMemo(() => {
    let best = { count: 0, wd: -1, hour: 0 };
    const offsetH = Math.round(-new Date().getTimezoneOffset() / 60);
    for (const c of data.heatmap) {
      if (c.count > best.count) {
        const shifted = (((c.weekday * 24 + c.hour + offsetH) % 168) + 168) % 168;
        best = { count: c.count, wd: Math.floor(shifted / 24), hour: shifted % 24 };
      }
    }
    if (best.wd < 0) return null;
    return `${tt('Пик активности')}: ${tt(WEEKDAYS[best.wd])}, ${String(best.hour).padStart(2, '0')}:00`;
  }, [data.heatmap, tt]);

  // Busiest moderation day over the period.
  const modInsight = useMemo(() => {
    const byDay = new Map<string, number>();
    for (const r of data.modActionsByDay) byDay.set(r.day, (byDay.get(r.day) ?? 0) + r.count);
    let best: { day: string; count: number } | null = null;
    for (const [day, count] of Array.from(byDay.entries())) {
      if (!best || count > best.count) best = { day, count };
    }
    return best && best.count > 0 ? `${tt('Активнее всего')}: ${shortDay(best.day)} (${best.count})` : null;
  }, [data.modActionsByDay, tt]);

  return (
    <Flex direction="column" gap={5}>
      <SimpleGrid columns={{ base: 2, md: 4 }} gap={4}>
        <StatCard label={tt('Действия модерации')} value={totalMod.toLocaleString('ru-RU')} hint={`${tt('за')} ${data.days} ${tt('дней')}`} />
        <StatCard label={tt('Нарушения AutoMod')} value={totalAutomod.toLocaleString('ru-RU')} hint={`${tt('за')} ${data.days} ${tt('дней')}`} />
        <StatCard label={tt('Открыто тикетов')} value={totalOpened.toLocaleString('ru-RU')} hint={`${tt('за')} ${data.days} ${tt('дней')}`} />
        <StatCard
          label={tt('Среднее время закрытия')}
          value={data.avgTicketResolutionHours != null ? `${data.avgTicketResolutionHours}${tt('ч')}` : '—'}
          hint={data.avgTicketResolutionHours != null ? tt('открыт → закрыт') : tt('нет закрытых тикетов')}
        />
      </SimpleGrid>

      <ChartCard
        title={tt('Хитмап активности')}
        subtitle={tt('Сообщения по дням недели и часам (ваше местное время). Только агрегатные счётчики — содержимое не хранится.')}
        insight={peakInsight}
        isEmpty={heatmapEmpty}
        emptyText={tt('Активности пока нет. Хитмап считает сообщения по дням недели и часам — первые точки появятся, как только на сервере начнут общаться (обычно в течение часа).')}
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
              tickAmount: compactHeatmap ? 6 : 12,
              labels: { rotate: 0 },
            },
            tooltip: { y: { formatter: (v: number) => `${v} ${tt('сообщений')}` } },
          }}
        />
      </ChartCard>

      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={5}>
        <ChartCard
          title={tt('Действия модерации по времени')}
          subtitle={tt('Из нумерованных кейсов модерации, стопкой по типу действия.')}
          insight={modInsight}
          isEmpty={actions.series.length === 0}
          emptyText={tt('Кейсов модерации за период нет.')}
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
          title={tt('Тикеты: открыто и закрыто')}
          subtitle={tt('Ежедневный объём открытий/закрытий за период.')}
          isEmpty={tickets.series[0].data.length === 0}
          emptyText={tt('Активности по тикетам за период нет.')}
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

      <Box bg="CardBackground" rounded="16px" p={5} border="1px solid" borderColor="CardBorder" boxShadow="normal">
        <Heading fontSize="15px" fontWeight="700" mb={5}>
          {tt('Топ модераторов')}
        </Heading>
        {data.topModerators.length === 0 ? (
          <Text fontSize="sm" color="TextSecondary">
            {tt('Кейсов модерации за период нет.')}
          </Text>
        ) : (
          <Flex direction="column" gap={4}>
            {data.topModerators.map((m) => (
              <Flex key={m.name} align="center" gap={2.5}>
                <Text fontSize="13px" fontWeight="600" minW="90px" isTruncated>
                  {m.name}
                </Text>
                <Box flex={1} bg="secondaryGray.100" _dark={{ bg: 'navy.600' }} rounded="5px" h="8px" overflow="hidden">
                  <Box bgGradient="linear(135deg, #8B7CFF, #6E56F5)" rounded="5px" h="8px" w={`${(m.count / maxMods) * 100}%`} />
                </Box>
                <Text fontSize="12px" fontWeight="700" color="brand.200" minW="20px" textAlign="right" flexShrink={0} sx={tabularNums}>
                  {m.count}
                </Text>
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
  const tt = useText();

  return (
    <Flex direction="column" gap={5}>
      <Flex align="flex-end" justify="space-between" gap={3} wrap="wrap">
        <Box>
          <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
            {tt('АНАЛИТИКА')}
          </Text>
          <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt={1}>
            {tt('Тренды и модерация')}
          </Heading>
          <Text fontSize="14px" color="TextSecondary" mt={1}>
            {tt('Тренды активности и модерации. Хитмап использует только агрегатные счётчики сообщений — содержимое, автор и время не хранятся.')}
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
              {tt(p.label)}
            </option>
          ))}
        </Select>
        <Button
          size="sm"
          variant="outline"
          rounded="10px"
          leftIcon={<ChakraIcon as={MdDownload} />}
          isDisabled={!query.data}
          onClick={() =>
            query.data &&
            downloadCsv(
              `analytics-${guild}-${days}d-${new Date().toISOString().slice(0, 10)}.csv`,
              analyticsToCsv(query.data)
            )
          }
        >
          {tt('Экспорт CSV')}
        </Button>
      </Flex>

      <QueryStatus query={query} loading={<AnalyticsSkeleton />} error={tt('Не удалось загрузить аналитику.')}>
        {query.data && <AnalyticsBody data={query.data} />}
      </QueryStatus>
    </Flex>
  );
};

AnalyticsPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default AnalyticsPage;
