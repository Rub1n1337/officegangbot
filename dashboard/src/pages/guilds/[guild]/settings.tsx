import { Badge, Box, Flex, Heading, Icon, SimpleGrid, Skeleton, SkeletonText, Text } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import {
  MdPeople,
  MdTag,
  MdMic,
  MdShield,
  MdSpeed,
  MdToggleOn,
} from 'react-icons/md';
import { FaCrown } from 'react-icons/fa';
import { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useGuildInfoQuery, useGuildStatsQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { NotJoinedPanel } from '@/components/feature/NotJoinedPanel';
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

function TopXp({ rows }: { rows: GuildStatsTopXp[] }) {
  const medals = ['🥇', '🥈', '🥉'];
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
        <Flex direction="column" gap={2}>
          {rows.map((row, i) => (
            <Flex key={i} align="center" justify="space-between" gap={3}>
              <Flex align="center" gap={3} minW={0}>
                <Text fontSize="lg" w="1.5em" textAlign="center">
                  {medals[i] ?? `#${i + 1}`}
                </Text>
                <Text fontWeight="600" isTruncated>
                  {row.name}
                </Text>
              </Flex>
              <Flex align="center" gap={3} flexShrink={0}>
                <Badge colorScheme="purple" rounded="md">
                  Lvl {row.level}
                </Badge>
                <Text fontSize="sm" color="TextSecondary">
                  {row.xp.toLocaleString()} XP
                </Text>
              </Flex>
            </Flex>
          ))}
        </Flex>
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
      <QueryStatus query={statsQuery} loading={<OverviewSkeleton />} error="Failed to load guild stats.">
        {statsQuery.data && <Overview stats={statsQuery.data} />}
      </QueryStatus>
    </Flex>
  );
};

GuildOverviewPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default GuildOverviewPage;
