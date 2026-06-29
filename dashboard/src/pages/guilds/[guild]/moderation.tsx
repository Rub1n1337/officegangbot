import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Icon,
  IconButton,
  Skeleton,
  Text,
  useToast,
} from '@chakra-ui/react';
import { MdDelete, MdGavel, MdTimer, MdHistory } from 'react-icons/md';
import { FaCrown } from 'react-icons/fa';
import { ReactNode, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import {
  useModerationQuery,
  useDeleteWarningMutation,
  useModerateMemberMutation,
  useAuditQuery,
} from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import type {
  AuditEntry,
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

const INITIAL_WARNINGS = 12;
const INITIAL_LEADERS = 10;

function Warnings({ rows, guild }: { rows: ModerationWarning[]; guild: string }) {
  const del = useDeleteWarningMutation();
  const undo = useModerateMemberMutation();
  const toast = useToast();
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? rows : rows.slice(0, INITIAL_WARNINGS);

  const handleDelete = (w: ModerationWarning) => {
    del.mutate(
      { guild, id: w.id },
      {
        onSuccess: () => {
          toast({
            duration: 6000,
            isClosable: true,
            position: 'bottom-right',
            render: ({ onClose }) => (
              <Flex
                bg="CardBackground"
                rounded="lg"
                shadow="md"
                p={3}
                align="center"
                gap={3}
                borderWidth="1px"
                borderColor="whiteAlpha.200"
              >
                <Text fontSize="sm">Warning removed</Text>
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => {
                    undo.mutate({
                      guild,
                      userId: w.userId,
                      body: { act: 'warn', reason: w.reason, moderatorName: w.moderatorName },
                    });
                    onClose();
                  }}
                >
                  Undo
                </Button>
              </Flex>
            ),
          });
        },
      }
    );
  };

  return (
    <Section icon={<Icon as={MdGavel} color="Brand" />} title="Recent warnings" count={rows.length}>
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No warnings on record.
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {shown.map((w) => (
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
                onClick={() => handleDelete(w)}
              />
            </Flex>
          ))}
          {rows.length > INITIAL_WARNINGS && (
            <Button size="sm" variant="ghost" alignSelf="center" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Show less' : `Show all ${rows.length}`}
            </Button>
          )}
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
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? rows : rows.slice(0, INITIAL_LEADERS);
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
          {shown.map((r, i) => (
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
          {rows.length > INITIAL_LEADERS && (
            <Button size="sm" variant="ghost" alignSelf="center" mt={1} onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Show less' : `Show all ${rows.length}`}
            </Button>
          )}
        </Flex>
      )}
    </Section>
  );
}

const AUDIT_LABEL: Record<string, (e: AuditEntry) => string> = {
  warn: () => 'warned a member',
  mute: () => 'muted a member',
  unmute: () => 'removed a timeout',
  kick: () => 'kicked a member',
  ban: () => 'banned a member',
  enable_feature: (e) => `enabled ${e.target ?? 'a feature'}`,
  disable_feature: (e) => `disabled ${e.target ?? 'a feature'}`,
  update_feature: (e) => `updated ${e.target ?? 'a feature'} settings`,
  set_locale: (e) => `set the bot language to ${e.detail ?? ''}`.trim(),
  delete_warning: () => 'deleted a warning',
};

function describeAudit(e: AuditEntry): string {
  const f = AUDIT_LABEL[e.action];
  return f ? f(e) : e.action;
}

const INITIAL_AUDIT = 10;

function AuditActivity({ rows }: { rows: AuditEntry[] }) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? rows : rows.slice(0, INITIAL_AUDIT);
  const isModeration = (a: string) => ['warn', 'mute', 'unmute', 'kick', 'ban'].includes(a);

  return (
    <Section
      icon={<Icon as={MdHistory} color="Brand" />}
      title="Dashboard activity"
      count={rows.length}
    >
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No dashboard actions recorded yet.
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {shown.map((e) => (
            <Flex
              key={e.id}
              align="center"
              justify="space-between"
              gap={3}
              p={3}
              rounded="xl"
              bg="blackAlpha.200"
              _dark={{ bg: 'whiteAlpha.50' }}
            >
              <Box minW={0}>
                <Text fontSize="sm" isTruncated>
                  <Text as="span" fontWeight="600">
                    {e.actorName ?? 'Someone'}
                  </Text>{' '}
                  {describeAudit(e)}
                </Text>
                {isModeration(e.action) && e.detail && (
                  <Text fontSize="xs" color="TextSecondary" noOfLines={1}>
                    {e.detail}
                  </Text>
                )}
              </Box>
              <Text fontSize="xs" color="TextSecondary" flexShrink={0}>
                {timeAgo(e.createdAt)}
              </Text>
            </Flex>
          ))}
          {rows.length > INITIAL_AUDIT && (
            <Button size="sm" variant="ghost" alignSelf="center" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Show less' : `Show all ${rows.length}`}
            </Button>
          )}
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
  const audit = useAuditQuery(guild);

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
      {audit.data && <AuditActivity rows={audit.data} />}
    </Flex>
  );
};

ModerationPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default ModerationPage;
