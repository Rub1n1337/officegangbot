import { Badge, Box, Flex, Heading, Icon, SimpleGrid, Text } from '@chakra-ui/react';
import {
  MdPeople,
  MdTag,
  MdMic,
  MdShield,
  MdSpeed,
  MdToggleOn,
} from 'react-icons/md';
import { FaCrown } from 'react-icons/fa';
import { ReactNode } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useGuildStatsQuery } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { LoadingPanel } from '@/components/panel/LoadingPanel';
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

const GuildOverviewPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const query = useGuildStatsQuery(guild);

  return (
    <Flex direction="column" gap={5}>
      <Flex align="center" gap={3}>
        <Heading fontSize="2xl" fontWeight="600">
          Overview
        </Heading>
        {query.data?.online && (
          <Badge colorScheme="green" rounded="md" px={2}>
            Bot online
          </Badge>
        )}
      </Flex>
      <QueryStatus query={query} loading={<LoadingPanel />} error="Failed to load guild stats.">
        {query.data && <Overview stats={query.data} />}
      </QueryStatus>
    </Flex>
  );
};

GuildOverviewPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default GuildOverviewPage;
