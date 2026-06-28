import {
  Badge,
  Box,
  Flex,
  Heading,
  Icon,
  IconButton,
  Skeleton,
  Text,
} from '@chakra-ui/react';
import { MdDelete, MdGavel, MdTimer } from 'react-icons/md';
import { FaCrown } from 'react-icons/fa';
import { ReactNode } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useModerationQuery, useDeleteWarningMutation } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import type {
  ModerationLeaderItem,
  ModerationPunishment,
  ModerationWarning,
} from '@/config/types/custom-types';

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const s = Math.max(0, Math.floor((Date.now() - d) / 1000));
  if (s < 60) return 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function expiresIn(iso: string | null): string {
  if (!iso) return '';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const s = Math.floor((d - Date.now()) / 1000);
  if (s <= 0) return 'expiring';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m left`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h left`;
  return `${Math.floor(h / 24)}d left`;
}

function Section({
  icon,
  title,
  count,
  children,
}: {
  icon: ReactNode;
  title: string;
  count: number;
  children: ReactNode;
}) {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Flex align="center" gap={2} mb={4}>
        {icon}
        <Heading size="sm">{title}</Heading>
        <Badge rounded="md" colorScheme="gray">
          {count}
        </Badge>
      </Flex>
      {children}
    </Box>
  );
}

function Warnings({ rows, guild }: { rows: ModerationWarning[]; guild: string }) {
  const del = useDeleteWarningMutation();
  return (
    <Section icon={<Icon as={MdGavel} color="Brand" />} title="Recent warnings" count={rows.length}>
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No warnings on record.
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {rows.map((w) => (
            <Flex
              key={w.id}
              align="center"
              justify="space-between"
              gap={3}
              p={3}
              rounded="xl"
              bg="blackAlpha.200"
              _dark={{ bg: 'whiteAlpha.50' }}
            >
              <Box minW={0}>
                <Flex align="center" gap={2} wrap="wrap">
                  <Text fontWeight="600" isTruncated>
                    {w.userName}
                  </Text>
                  <Text fontSize="xs" color="TextSecondary">
                    by {w.moderatorName} · {timeAgo(w.createdAt)}
                  </Text>
                </Flex>
                <Text fontSize="sm" color="TextSecondary" noOfLines={2}>
                  {w.reason}
                </Text>
              </Box>
              <IconButton
                aria-label="Delete warning"
                icon={<MdDelete />}
                size="sm"
                variant="ghost"
                colorScheme="red"
                isLoading={del.isLoading && del.variables?.id === w.id}
                onClick={() => del.mutate({ guild, id: w.id })}
              />
            </Flex>
          ))}
        </Flex>
      )}
    </Section>
  );
}

function Punishments({ rows }: { rows: ModerationPunishment[] }) {
  return (
    <Section
      icon={<Icon as={MdTimer} color="Brand" />}
      title="Active timed punishments"
      count={rows.length}
    >
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No active mutes or temp-bans.
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {rows.map((p) => (
            <Flex
              key={p.userId}
              align="center"
              justify="space-between"
              gap={3}
              p={3}
              rounded="xl"
              bg="blackAlpha.200"
              _dark={{ bg: 'whiteAlpha.50' }}
            >
              <Box minW={0}>
                <Flex align="center" gap={2} wrap="wrap">
                  <Badge colorScheme={p.type === 'ban' ? 'red' : 'orange'} rounded="md">
                    {p.type}
                  </Badge>
                  <Text fontWeight="600" isTruncated>
                    {p.userName}
                  </Text>
                </Flex>
                {p.reason && (
                  <Text fontSize="sm" color="TextSecondary" noOfLines={1}>
                    {p.reason}
                  </Text>
                )}
              </Box>
              <Text fontSize="sm" color="TextSecondary" flexShrink={0}>
                {expiresIn(p.expiresAt)}
              </Text>
            </Flex>
          ))}
        </Flex>
      )}
    </Section>
  );
}

function Leaderboard({ rows }: { rows: ModerationLeaderItem[] }) {
  const medals = ['🥇', '🥈', '🥉'];
  return (
    <Section
      icon={<Icon as={FaCrown} color="Brand" />}
      title="XP leaderboard"
      count={rows.length}
    >
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No XP data yet.
        </Text>
      ) : (
        <Flex direction="column" gap={1}>
          {rows.map((r, i) => (
            <Flex key={r.userId} align="center" justify="space-between" gap={3} py={1.5}>
              <Flex align="center" gap={3} minW={0}>
                <Text fontSize="sm" w="1.8em" textAlign="center" color="TextSecondary">
                  {medals[i] ?? `#${i + 1}`}
                </Text>
                <Text fontWeight="600" isTruncated>
                  {r.name}
                </Text>
              </Flex>
              <Flex align="center" gap={3} flexShrink={0}>
                <Badge colorScheme="purple" rounded="md">
                  Lvl {r.level}
                </Badge>
                <Text fontSize="sm" color="TextSecondary">
                  {r.xp.toLocaleString()} XP
                </Text>
              </Flex>
            </Flex>
          ))}
        </Flex>
      )}
    </Section>
  );
}

function ModerationSkeleton() {
  return (
    <Flex direction="column" gap={5}>
      {Array.from({ length: 3 }).map((_, i) => (
        <Box key={i} bg="CardBackground" rounded="2xl" p={5}>
          <Skeleton h="18px" w="40%" mb={4} rounded="md" />
          <Skeleton h="48px" mb={2} rounded="xl" />
          <Skeleton h="48px" rounded="xl" />
        </Box>
      ))}
    </Flex>
  );
}

const ModerationPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const query = useModerationQuery(guild);

  return (
    <Flex direction="column" gap={5}>
      <Heading fontSize="2xl" fontWeight="600">
        Moderation
      </Heading>
      <QueryStatus
        query={query}
        loading={<ModerationSkeleton />}
        error="Failed to load moderation data."
      >
        {query.data && (
          <Flex direction="column" gap={5}>
            <Warnings rows={query.data.warnings} guild={guild} />
            <Punishments rows={query.data.punishments} />
            <Leaderboard rows={query.data.leaderboard} />
          </Flex>
        )}
      </QueryStatus>
    </Flex>
  );
};

ModerationPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default ModerationPage;
