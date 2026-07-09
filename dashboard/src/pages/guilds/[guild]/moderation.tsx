import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Icon,
  IconButton,
  Skeleton,
  Switch,
  Text,
  useToast,
} from '@chakra-ui/react';
import { MdDelete, MdGavel, MdTimer, MdHistory, MdShield, MdOutlineHowToReg } from 'react-icons/md';
import { ReactNode, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import {
  useModerationQuery,
  useDeleteWarningMutation,
  useModerateMemberMutation,
  useSetBanAppealsMutation,
  useDecideBanAppealMutation,
  useAuditQuery,
} from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { timeAgo, describeAudit, isModerationAction } from '@/utils/audit';
import type {
  AuditEntry,
  ModerationAppeals,
  ModerationPunishment,
  ModerationStrikes,
  ModerationWarning,
} from '@/config/types/custom-types';

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

// When a user's oldest active strike will drop out of the decay window.
function decayLabel(iso: string | null): string {
  if (!iso) return 'never expires';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const s = Math.floor((d - Date.now()) / 1000);
  if (s <= 0) return 'expiring now';
  const m = Math.floor(s / 60);
  if (m < 60) return `~${m}m left`;
  const h = Math.floor(m / 60);
  if (h < 24) return `~${h}h left`;
  return `~${Math.floor(h / 24)}d left`;
}

// Colour a strike count by how close it is to the first enabled escalation tier.
function strikeColor(count: number, s: ModerationStrikes): string {
  const tiers = [s.muteAt, s.kickAt, s.banAt].filter((t) => t > 0).sort((a, b) => a - b);
  if (tiers.length === 0) return 'gray';
  const lowest = tiers[0];
  if (count >= lowest) return 'red';
  if (count >= lowest - 1) return 'orange';
  return 'yellow';
}

function policyLabel(s: ModerationStrikes): string {
  const parts: string[] = [];
  if (s.muteAt > 0) parts.push(`mute at ${s.muteAt}`);
  if (s.kickAt > 0) parts.push(`kick at ${s.kickAt}`);
  if (s.banAt > 0) parts.push(`ban at ${s.banAt}`);
  return parts.join(' · ');
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
    <Box bg="CardBackground" rounded="16px" p="20px" border="1px solid" borderColor="CardBorder" boxShadow="normal">
      <Flex align="center" gap="10px" mb="14px">
        <Box color="brand.200" display="flex" fontSize="20px">
          {icon}
        </Box>
        <Heading fontSize="15px" fontWeight="700">
          {title}
        </Heading>
        <Badge
          rounded="20px"
          bg="blackAlpha.100"
          _dark={{ bg: 'whiteAlpha.100' }}
          color="TextSecondary"
          px="9px"
          fontSize="12px"
        >
          {count}
        </Badge>
      </Flex>
      {children}
    </Box>
  );
}

const INITIAL_WARNINGS = 12;

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
    <Section icon={<Icon as={MdGavel} />} title="Recent warnings" count={rows.length}>
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
      icon={<Icon as={MdTimer} />}
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

const INITIAL_STRIKES = 12;

function Strikes({ data }: { data: ModerationStrikes }) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? data.users : data.users.slice(0, INITIAL_STRIKES);
  const policy = policyLabel(data);

  return (
    <Section
      icon={<Icon as={MdShield} />}
      title="Active strikes"
      count={data.users.length}
    >
      <Text fontSize="xs" color="TextSecondary" mb={3}>
        {data.enabled ? 'Strikes on' : 'Strikes off'}
        {data.expiryHours > 0 ? ` · decay after ${data.expiryHours}h` : ' · never decay'}
        {policy && ` · ${policy}`}
      </Text>
      {data.users.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No members have active strikes.
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {shown.map((u) => (
            <Flex
              key={u.userId}
              align="center"
              justify="space-between"
              gap={3}
              p={3}
              rounded="xl"
              bg="blackAlpha.200"
              _dark={{ bg: 'whiteAlpha.50' }}
            >
              <Flex align="center" gap={3} minW={0}>
                <Badge colorScheme={strikeColor(u.count, data)} rounded="md" flexShrink={0}>
                  {u.count} {u.count === 1 ? 'strike' : 'strikes'}
                </Badge>
                <Text fontWeight="600" isTruncated>
                  {u.userName}
                </Text>
              </Flex>
              <Box textAlign="right" flexShrink={0}>
                <Text fontSize="sm" color="TextSecondary">
                  {decayLabel(u.nextDecayAt)}
                </Text>
                {u.lastStrikeAt && (
                  <Text fontSize="xs" color="TextSecondary" opacity={0.7}>
                    last {timeAgo(u.lastStrikeAt)}
                  </Text>
                )}
              </Box>
            </Flex>
          ))}
          {data.users.length > INITIAL_STRIKES && (
            <Button size="sm" variant="ghost" alignSelf="center" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Show less' : `Show all ${data.users.length}`}
            </Button>
          )}
        </Flex>
      )}
    </Section>
  );
}

const APPEAL_STATUS: Record<string, string> = {
  approved: 'green',
  denied: 'red',
  pending: 'yellow',
};

function BanAppeals({ data, guild }: { data: ModerationAppeals; guild: string }) {
  const setEnabled = useSetBanAppealsMutation();
  const decide = useDecideBanAppealMutation();
  const pendingCount = data.items.filter((a) => a.status === 'pending').length;

  return (
    <Section
      icon={<Icon as={MdOutlineHowToReg} />}
      title="Ban appeals"
      count={pendingCount}
    >
      <Flex align="center" justify="space-between" gap={3} mb={4}>
        <Text fontSize="sm" color="TextSecondary">
          When on, ban DMs include an “Appeal” button. Appeals show up here for review.
        </Text>
        <Switch
          isChecked={data.enabled}
          isDisabled={setEnabled.isLoading}
          onChange={(e) => setEnabled.mutate({ guild, enabled: e.target.checked })}
          flexShrink={0}
        />
      </Flex>

      {data.items.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          {data.enabled ? 'No appeals submitted yet.' : 'Ban appeals are off.'}
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {data.items.map((a) => (
            <Box key={a.id} p={3} rounded="xl" bg="blackAlpha.200" _dark={{ bg: 'whiteAlpha.50' }}>
              <Flex align="center" justify="space-between" gap={3} wrap="wrap">
                <Flex align="center" gap={2} minW={0}>
                  <Badge colorScheme={APPEAL_STATUS[a.status] ?? 'gray'} rounded="md" flexShrink={0}>
                    {a.status}
                  </Badge>
                  <Text fontWeight="600" isTruncated>
                    {a.userName ?? a.userId}
                  </Text>
                  <Text fontSize="xs" color="TextSecondary">
                    {timeAgo(a.createdAt)}
                  </Text>
                </Flex>
                {a.status === 'pending' && (
                  <Flex gap={2} flexShrink={0}>
                    <Button
                      size="xs"
                      colorScheme="green"
                      isLoading={decide.isLoading && decide.variables?.appealId === a.id}
                      onClick={() => decide.mutate({ guild, appealId: a.id, decision: 'approve' })}
                    >
                      Approve &amp; unban
                    </Button>
                    <Button
                      size="xs"
                      variant="outline"
                      colorScheme="red"
                      isLoading={decide.isLoading && decide.variables?.appealId === a.id}
                      onClick={() => decide.mutate({ guild, appealId: a.id, decision: 'deny' })}
                    >
                      Deny
                    </Button>
                  </Flex>
                )}
                {a.status !== 'pending' && a.decidedByName && (
                  <Text fontSize="xs" color="TextSecondary" flexShrink={0}>
                    by {a.decidedByName}
                  </Text>
                )}
              </Flex>
              {a.reason && (
                <Text fontSize="sm" color="TextSecondary" mt={2} whiteSpace="pre-wrap">
                  {a.reason}
                </Text>
              )}
            </Box>
          ))}
        </Flex>
      )}
    </Section>
  );
}

const INITIAL_AUDIT = 10;

function AuditActivity({ rows }: { rows: AuditEntry[] }) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? rows : rows.slice(0, INITIAL_AUDIT);

  return (
    <Section
      icon={<Icon as={MdHistory} />}
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
                {isModerationAction(e.action) && e.detail && (
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
    <Flex direction="column" gap="16px">
      <Box>
        <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
          МОДЕРАЦИЯ
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt="3px">
          Предупреждения, наказания и апелляции
        </Heading>
      </Box>
      <QueryStatus
        query={query}
        loading={<ModerationSkeleton />}
        error="Failed to load moderation data."
      >
        {query.data && (
          <Flex direction="column" gap={5}>
            <Warnings rows={query.data.warnings} guild={guild} />
            <Punishments rows={query.data.punishments} />
            <Strikes data={query.data.strikes} />
            <BanAppeals data={query.data.appeals} guild={guild} />
          </Flex>
        )}
      </QueryStatus>
      {audit.data && <AuditActivity rows={audit.data} />}
    </Flex>
  );
};

ModerationPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default ModerationPage;
