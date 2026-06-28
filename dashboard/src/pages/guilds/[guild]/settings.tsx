import {
  Badge,
  Box,
  Flex,
  Heading,
  Icon,
  SimpleGrid,
  Skeleton,
  Progress,
  SkeletonText,
  Text,
  useToken,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { StyledChart } from '@/components/chart/StyledChart';
import {
  MdPeople,
  MdTag,
  MdMic,
  MdShield,
  MdSpeed,
  MdToggleOn,
} from 'react-icons/md';
import { FaCrown } from 'react-icons/fa';
import { IoCheckmarkCircle, IoArrowForward } from 'react-icons/io5';
import { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useGuildInfoQuery, useGuildStatsQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { NotJoinedPanel } from '@/components/feature/NotJoinedPanel';
import { getFeatures } from '@/utils/common';
import type { GuildStats, GuildStatsTopXp } from '@/config/types/custom-types';

function StatCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <Flex bg="CardBackground" rounded="2xl" p={5} direction="column" gap={2}>
      <Flex align="center" gap={2} color="TextSecondary">
        {icon}
        <Text fontSize="sm">{label}</Text>
      </Flex>
      <Text fontSize="3xl" fontWeight="700" lineHeight="1.1">
        {value}
      </Text>
      {hint && (
        <Text fontSize="xs" color="TextSecondary">
          {hint}
        </Text>
      )}
    </Flex>
  );
}

function XpBarChart({ rows }: { rows: GuildStatsTopXp[] }) {
  const medals = ['🥇', '🥈', '🥉'];
  const [brand] = useToken('colors', ['brand.500']);

  const series = [{ name: 'XP', data: rows.map((r) => r.xp) }];
  const options: ApexCharts.ApexOptions = {
    chart: { type: 'bar', sparkline: { enabled: false } },
    colors: [brand],
    plotOptions: {
      bar: { horizontal: true, borderRadius: 6, barHeight: '68%' },
    },
    dataLabels: {
      enabled: true,
      // Show the member's level inside the bar; the bar length is their XP.
      formatter: (_val, opts) => `Lvl ${rows[opts.dataPointIndex].level}`,
      style: { colors: ['#fff'], fontWeight: '700' },
    },
    xaxis: {
      categories: rows.map((r, i) => `${medals[i] ?? `#${i + 1}`} ${r.name}`),
    },
    tooltip: {
      y: { formatter: (val: number) => `${val.toLocaleString()} XP` },
    },
  };

  return (
    <StyledChart
      type="bar"
      series={series}
      options={options}
      height={Math.max(160, rows.length * 46)}
    />
  );
}

function TopXp({ rows }: { rows: GuildStatsTopXp[] }) {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Flex align="center" gap={2} mb={4}>
        <Icon as={FaCrown} color="Brand" />
        <Heading size="sm">Top members by XP</Heading>
      </Flex>
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No XP data yet. Enable the Levels feature and let members chat to populate the leaderboard.
        </Text>
      ) : (
        <XpBarChart rows={rows} />
      )}
    </Box>
  );
}

function Overview({ stats }: { stats: GuildStats }) {
  return (
    <Flex direction="column" gap={4}>
      <SimpleGrid columns={{ base: 1, sm: 2, lg: 3 }} gap={3}>
        <StatCard
          icon={<Icon as={MdPeople} />}
          label="Members"
          value={stats.member_count.toLocaleString()}
        />
        <StatCard
          icon={<Icon as={MdTag} />}
          label="Text channels"
          value={stats.text_channels}
          hint={`${stats.channel_count} channels total`}
        />
        <StatCard
          icon={<Icon as={MdMic} />}
          label="Voice channels"
          value={stats.voice_channels}
        />
        <StatCard icon={<Icon as={MdShield} />} label="Roles" value={stats.role_count} />
        <StatCard
          icon={<Icon as={MdToggleOn} />}
          label="Enabled features"
          value={stats.enabled_feature_count}
        />
        <StatCard
          icon={<Icon as={MdSpeed} />}
          label="Bot latency"
          value={`${Math.round(stats.latency_ms)} ms`}
        />
      </SimpleGrid>
      <TopXp rows={stats.top_xp} />
    </Flex>
  );
}

function OverviewSkeleton() {
  return (
    <Flex direction="column" gap={4}>
      <SimpleGrid columns={{ base: 1, sm: 2, lg: 3 }} gap={3}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Box key={i} bg="CardBackground" rounded="2xl" p={5}>
            <Skeleton h="14px" w="55%" mb={3} rounded="md" />
            <Skeleton h="28px" w="40%" rounded="md" />
          </Box>
        ))}
      </SimpleGrid>
      <Box bg="CardBackground" rounded="2xl" p={5}>
        <Skeleton h="16px" w="40%" mb={4} rounded="md" />
        <SkeletonText noOfLines={3} spacing={3} skeletonHeight={3} />
      </Box>
    </Flex>
  );
}

const pulse = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.7); }
  70% { box-shadow: 0 0 0 7px rgba(72, 187, 120, 0); }
  100% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0); }
`;

// Live indicator: a pulsing dot + a ticking "updated Ns ago", driven by the
// stats query's auto-refetch (every 8s).
function LiveIndicator({ updatedAt }: { updatedAt: number }) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const secs = updatedAt ? Math.max(0, Math.round((Date.now() - updatedAt) / 1000)) : 0;
  return (
    <Flex align="center" gap={2}>
      <Box w="9px" h="9px" rounded="full" bg="green.400" animation={`${pulse} 2s infinite`} />
      <Text fontSize="sm" fontWeight="700" color="green.400" letterSpacing="wide">
        LIVE
      </Text>
      <Text fontSize="xs" color="TextSecondary">
        updated {secs}s ago
      </Text>
    </Flex>
  );
}

// A gentle setup nudge: each feature is a step, ticked off once it's enabled.
// Hidden once everything is configured. Doubles as quick links into each
// feature's settings.
function OnboardingChecklist({ guild, enabledFeatures }: { guild: string; enabledFeatures: string[] }) {
  const all = getFeatures();
  const enabled = new Set(enabledFeatures);
  const done = all.filter((f) => enabled.has(f.id)).length;

  if (done === all.length) return null;

  const pct = Math.round((done / all.length) * 100);

  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Flex align="center" justify="space-between" gap={3} mb={2} wrap="wrap">
        <Heading size="sm">Finish setting up</Heading>
        <Text fontSize="sm" color="TextSecondary">
          {done} / {all.length} configured
        </Text>
      </Flex>
      <Progress value={pct} size="sm" rounded="full" colorScheme="brand" mb={4} />
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={2}>
        {all.map((feature) => {
          const isDone = enabled.has(feature.id);
          return (
            <Flex
              key={feature.id}
              as={Link}
              href={`/guilds/${guild}/features/${feature.id}`}
              align="center"
              gap={3}
              px={3}
              py={2.5}
              rounded="xl"
              bg="blackAlpha.200"
              _dark={{ bg: 'whiteAlpha.50' }}
              _hover={{ bg: 'blackAlpha.300', _dark: { bg: 'whiteAlpha.100' } }}
              opacity={isDone ? 0.65 : 1}
            >
              {isDone ? (
                <Icon as={IoCheckmarkCircle} color="green.400" boxSize={5} />
              ) : (
                <Box color="Brand" display="flex">
                  {feature.icon}
                </Box>
              )}
              <Text
                flex={1}
                fontWeight={isDone ? '400' : '600'}
                textDecoration={isDone ? 'line-through' : 'none'}
                isTruncated
              >
                {feature.name}
              </Text>
              {!isDone && <Icon as={IoArrowForward} color="TextSecondary" />}
            </Flex>
          );
        })}
      </SimpleGrid>
    </Box>
  );
}

const GuildOverviewPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const infoQuery = useGuildInfoQuery(guild);
  const statsQuery = useGuildStatsQuery(guild);

  // Bot isn't a member of this guild — show a friendly invite prompt instead of
  // a raw stats error.
  if (infoQuery.isSuccess && infoQuery.data == null) {
    return <NotJoinedPanel guild={guild} />;
  }

  return (
    <Flex direction="column" gap={5}>
      <Flex align="center" gap={3} wrap="wrap">
        <Heading fontSize="2xl" fontWeight="600">
          Overview
        </Heading>
        {statsQuery.data?.online ? (
          <LiveIndicator updatedAt={statsQuery.dataUpdatedAt} />
        ) : statsQuery.data ? (
          <Badge colorScheme="red" rounded="md" px={2}>
            Bot offline
          </Badge>
        ) : null}
      </Flex>
      {infoQuery.data && (
        <OnboardingChecklist
          guild={guild}
          enabledFeatures={infoQuery.data.enabledFeatures ?? []}
        />
      )}
      <QueryStatus query={statsQuery} loading={<OverviewSkeleton />} error="Failed to load guild stats.">
        {statsQuery.data && <Overview stats={statsQuery.data} />}
      </QueryStatus>
    </Flex>
  );
};

GuildOverviewPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default GuildOverviewPage;
