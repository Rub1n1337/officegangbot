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
import { provider, type Languages } from '@/config/translations/provider';
import { useText } from '@/config/translations/ui-text';
import { tabularNums } from '@/theme/numeric';
import type {
  AuditEntry,
  ModerationAppeals,
  ModerationPunishment,
  ModerationStrikes,
  ModerationWarning,
} from '@/config/types/custom-types';

// Russian plural: 1 страйк, 2 страйка, 5 страйков. English: strike/strikes.
function pluralStrikes(n: number, lang: Languages): string {
  if (lang !== 'ru') return n === 1 ? 'strike' : 'strikes';
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return 'страйк';
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return 'страйка';
  return 'страйков';
}

function expiresIn(iso: string | null, lang: Languages): string {
  if (!iso) return '';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const ru = lang === 'ru';
  const s = Math.floor((d - Date.now()) / 1000);
  if (s <= 0) return ru ? 'истекает' : 'expiring';
  const m = Math.floor(s / 60);
  if (m < 60) return ru ? `${m}м осталось` : `${m}m left`;
  const h = Math.floor(m / 60);
  if (h < 24) return ru ? `${h}ч осталось` : `${h}h left`;
  const days = Math.floor(h / 24);
  return ru ? `${days}д осталось` : `${days}d left`;
}

// When a user's oldest active strike will drop out of the decay window.
function decayLabel(iso: string | null, lang: Languages): string {
  const ru = lang === 'ru';
  if (!iso) return ru ? 'не истекает' : 'never expires';
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return '';
  const s = Math.floor((d - Date.now()) / 1000);
  if (s <= 0) return ru ? 'истекает' : 'expiring';
  const m = Math.floor(s / 60);
  if (m < 60) return ru ? `~${m}м осталось` : `~${m}m left`;
  const h = Math.floor(m / 60);
  if (h < 24) return ru ? `~${h}ч осталось` : `~${h}h left`;
  const days = Math.floor(h / 24);
  return ru ? `~${days}д осталось` : `~${days}d left`;
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

function policyLabel(s: ModerationStrikes, lang: Languages): string {
  const ru = lang === 'ru';
  const parts: string[] = [];
  if (s.muteAt > 0) parts.push(ru ? `мут при ${s.muteAt}` : `mute at ${s.muteAt}`);
  if (s.kickAt > 0) parts.push(ru ? `кик при ${s.kickAt}` : `kick at ${s.kickAt}`);
  if (s.banAt > 0) parts.push(ru ? `бан при ${s.banAt}` : `ban at ${s.banAt}`);
  return parts.join(' · ');
}

// Iris "inset" row surface — a defined step below the card (visible on both
// themes), unlike the near-invisible whiteAlpha the rows used before.
const INSET = { bg: 'secondaryGray.100', _dark: { bg: 'navy.600' } };

// Soft-tinted status pill (matches the mockup's colored labels).
const PILL_TONE: Record<string, { color: string; bg: string; darkBg?: string }> = {
  red: { color: 'red.400', bg: 'rgba(241,106,106,0.14)' },
  amber: { color: 'orange.400', bg: 'rgba(245,177,76,0.14)' },
  green: { color: 'green.400', bg: 'rgba(63,208,126,0.14)' },
  gray: { color: 'TextSecondary', bg: 'blackAlpha.100', darkBg: 'whiteAlpha.100' },
};

function Pill({ tone, children }: { tone: keyof typeof PILL_TONE; children: ReactNode }) {
  const t = PILL_TONE[tone] ?? PILL_TONE.gray;
  return (
    <Box
      as="span"
      fontSize="11px"
      fontWeight="700"
      rounded="7px"
      px={2.5}
      py={1}
      flexShrink={0}
      color={t.color}
      bg={t.bg}
      _dark={t.darkBg ? { bg: t.darkBg } : undefined}
      sx={tabularNums}
    >
      {children}
    </Box>
  );
}

// Map an AutoMod-strike severity colour name to a pill tone.
function toneFromScheme(scheme: string): keyof typeof PILL_TONE {
  if (scheme === 'red') return 'red';
  if (scheme === 'orange' || scheme === 'yellow') return 'amber';
  if (scheme === 'green') return 'green';
  return 'gray';
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
    <Box bg="CardBackground" rounded="16px" p={5} border="1px solid" borderColor="CardBorder" boxShadow="normal">
      <Flex align="center" gap={2.5} mb={4}>
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
          px={2}
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
  const lang = provider.useLang();
  const tt = useText();
  const shown = showAll ? rows : rows.slice(0, INITIAL_WARNINGS);

  const handleDelete = (w: ModerationWarning) => {
    del.mutate(
      { guild, id: w.id },
      {
        onSuccess: () => {
          toast({
            duration: 6000,
            isClosable: true,
            position: 'bottom',
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
                <Text fontSize="sm">{tt('Предупреждение удалено')}</Text>
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
                  {tt('Вернуть')}
                </Button>
              </Flex>
            ),
          });
        },
      }
    );
  };

  return (
    <Section icon={<Icon as={MdGavel} />} title={tt('Недавние предупреждения')} count={rows.length}>
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          {tt('Предупреждений нет.')}
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {shown.map((w) => (
            <Flex key={w.id} align="center" gap={3} rounded="11px" py={3} px={4} {...INSET}>
              <Box flex="1" minW={0}>
                <Text fontSize="13.5px" fontWeight="600" isTruncated>
                  {w.userName}
                </Text>
                <Text fontSize="12.5px" color="TextSecondary" noOfLines={2}>
                  {w.reason}
                </Text>
                <Text fontSize="11.5px" color="TextSecondary" opacity={0.75} mt={0.5}>
                  {w.moderatorName} · {timeAgo(w.createdAt, lang)}
                </Text>
              </Box>
              <IconButton
                aria-label={tt('Удалить предупреждение')}
                icon={<MdDelete />}
                w="40px"
                h="40px"
                minW="40px"
                rounded="9px"
                variant="outline"
                borderColor="CardBorder"
                color="TextSecondary"
                _hover={{ color: 'red.400', borderColor: 'red.400' }}
                flexShrink={0}
                isLoading={del.isLoading && del.variables?.id === w.id}
                onClick={() => handleDelete(w)}
              />
            </Flex>
          ))}
          {rows.length > INITIAL_WARNINGS && (
            <Button size="sm" variant="ghost" alignSelf="center" onClick={() => setShowAll((v) => !v)}>
              {showAll ? tt('Свернуть') : `${tt('Показать все')} (${rows.length})`}
            </Button>
          )}
        </Flex>
      )}
    </Section>
  );
}

function Punishments({ rows }: { rows: ModerationPunishment[] }) {
  const lang = provider.useLang();
  const tt = useText();
  return (
    <Section icon={<Icon as={MdTimer} />} title={tt('Активные наказания')} count={rows.length}>
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          {tt('Активных мутов и банов нет.')}
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {rows.map((p) => (
            <Flex key={p.userId} align="center" gap={3} rounded="11px" py={3} px={4} {...INSET}>
              <Pill tone={p.type === 'ban' ? 'red' : 'amber'}>{p.type === 'ban' ? tt('бан') : tt('мут')}</Pill>
              <Box flex="1" minW={0}>
                <Text fontSize="13.5px" fontWeight="600" isTruncated>
                  {p.userName}
                </Text>
                {p.reason && (
                  <Text fontSize="12px" color="TextSecondary" opacity={0.85} noOfLines={1}>
                    {p.reason}
                  </Text>
                )}
              </Box>
              <Text fontSize="12px" color="TextSecondary" flexShrink={0}>
                {expiresIn(p.expiresAt, lang)}
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
  const lang = provider.useLang();
  const tt = useText();
  const shown = showAll ? data.users : data.users.slice(0, INITIAL_STRIKES);
  const policy = policyLabel(data, lang);

  return (
    <Section icon={<Icon as={MdShield} />} title={tt('Активные страйки')} count={data.users.length}>
      <Text fontSize="12px" color="TextSecondary" mb={4}>
        {data.enabled ? tt('Страйки вкл') : tt('Страйки выкл')}
        {data.expiryHours > 0
          ? ` · ${tt('затухают через')} ${data.expiryHours}${tt('ч')}`
          : ` · ${tt('не затухают')}`}
        {policy && ` · ${policy}`}
      </Text>
      {/* What the pill colours mean — new moderators shouldn't have to guess. */}
      {data.enabled && data.users.length > 0 && (
        <Flex gap={4} mb={3} fontSize="11.5px" color="TextSecondary" wrap="wrap">
          <Flex align="center" gap={1}><Box w="8px" h="8px" rounded="full" bg="red.400" /> {tt('порог достигнут')}</Flex>
          <Flex align="center" gap={1}><Box w="8px" h="8px" rounded="full" bg="orange.400" /> {tt('1 до порога')}</Flex>
          <Flex align="center" gap={1}><Box w="8px" h="8px" rounded="full" bg="yellow.400" /> {tt('активные')}</Flex>
        </Flex>
      )}
      {data.users.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          {tt('Ни у кого нет активных страйков.')}
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {shown.map((u) => (
            <Flex key={u.userId} align="center" gap={3} rounded="11px" py={3} px={4} {...INSET}>
              <Pill tone={toneFromScheme(strikeColor(u.count, data))}>
                {u.count} {pluralStrikes(u.count, lang)}
              </Pill>
              <Box flex="1" minW={0}>
                <Text fontSize="13.5px" fontWeight="600" isTruncated>
                  {u.userName}
                </Text>
              </Box>
              <Box textAlign="right" flexShrink={0}>
                <Text fontSize="12px" color="TextSecondary">
                  {decayLabel(u.nextDecayAt, lang)}
                </Text>
                {u.lastStrikeAt && (
                  <Text fontSize="11px" color="TextSecondary" opacity={0.7}>
                    {tt('последний:')} {timeAgo(u.lastStrikeAt, lang)}
                  </Text>
                )}
              </Box>
            </Flex>
          ))}
          {data.users.length > INITIAL_STRIKES && (
            <Button size="sm" variant="ghost" alignSelf="center" onClick={() => setShowAll((v) => !v)}>
              {showAll ? tt('Свернуть') : `${tt('Показать все')} (${data.users.length})`}
            </Button>
          )}
        </Flex>
      )}
    </Section>
  );
}

const APPEAL_STATUS: Record<string, { tone: 'green' | 'red' | 'amber' | 'gray'; label: string }> = {
  approved: { tone: 'green', label: 'одобрено' },
  denied: { tone: 'red', label: 'отклонено' },
  pending: { tone: 'amber', label: 'на рассмотрении' },
};

function BanAppeals({ data, guild }: { data: ModerationAppeals; guild: string }) {
  const setEnabled = useSetBanAppealsMutation();
  const decide = useDecideBanAppealMutation();
  const lang = provider.useLang();
  const tt = useText();
  const pendingCount = data.items.filter((a) => a.status === 'pending').length;

  return (
    <Section icon={<Icon as={MdOutlineHowToReg} />} title={tt('Апелляции на бан')} count={pendingCount}>
      <Flex align="center" justify="space-between" gap={3} rounded="11px" py={3} px={4} mb={3} {...INSET}>
        <Text fontSize="13px" color="TextSecondary" flex="1">
          {tt('В бан-DM добавляется кнопка «Апелляция». Заявки появляются здесь на рассмотрение.')}
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
          {data.enabled ? tt('Заявок пока нет.') : tt('Апелляции на бан выключены.')}
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {data.items.map((a) => {
            const st = APPEAL_STATUS[a.status] ?? { tone: 'gray' as const, label: a.status };
            return (
              <Box key={a.id} rounded="11px" py={3} px={4} {...INSET}>
                <Flex align="center" gap={2.5} wrap="wrap">
                  <Pill tone={st.tone}>{tt(st.label)}</Pill>
                  <Text fontSize="13.5px" fontWeight="600" isTruncated>
                    {a.userName ?? a.userId}
                  </Text>
                  <Text fontSize="11.5px" color="TextSecondary" opacity={0.75}>
                    {timeAgo(a.createdAt, lang)}
                  </Text>
                  {a.status === 'pending' && (
                    // Full-width on its own line on a phone (the two buttons
                    // don't fit beside the name under ~360px); inline and
                    // right-aligned from sm up.
                    <Flex
                      gap={2}
                      ml="auto"
                      flexShrink={0}
                      // Side by side the two Russian labels are ~270px, wider
                      // than this row on a small phone, and flex items don't
                      // shrink below their content — so stack them full-width
                      // below ~380px. (A raw media query: responsive prop
                      // objects weren't resolving on this deeply-nested node.)
                      sx={{
                        '@media (max-width: 380px)': {
                          flexDirection: 'column',
                          width: '100%',
                          marginLeft: 0,
                        },
                      }}
                    >
                      <Button
                        size="sm"
                        rounded="9px"
                        color="white"
                        bg="green.500"
                        _hover={{ filter: 'brightness(1.08)' }}
                        isLoading={decide.isLoading && decide.variables?.appealId === a.id}
                        onClick={() => decide.mutate({ guild, appealId: a.id, decision: 'approve' })}
                      >
                        {tt('Одобрить · разбан')}
                      </Button>
                      <Button
                        size="sm"
                        rounded="9px"
                        variant="outline"
                        color="red.400"
                        borderColor="red.400"
                        _hover={{ bg: 'rgba(241,106,106,0.1)' }}
                        isLoading={decide.isLoading && decide.variables?.appealId === a.id}
                        onClick={() => decide.mutate({ guild, appealId: a.id, decision: 'deny' })}
                      >
                        {tt('Отклонить')}
                      </Button>
                    </Flex>
                  )}
                  {a.status !== 'pending' && a.decidedByName && (
                    <Text ml="auto" fontSize="11.5px" color="TextSecondary" flexShrink={0}>
                      {tt('решение:')} {a.decidedByName}
                    </Text>
                  )}
                </Flex>
                {a.reason && (
                  <Text fontSize="12.5px" color="TextSecondary" mt={2} whiteSpace="pre-wrap">
                    {a.reason}
                  </Text>
                )}
              </Box>
            );
          })}
        </Flex>
      )}
    </Section>
  );
}

const INITIAL_AUDIT = 10;

function AuditActivity({ rows }: { rows: AuditEntry[] }) {
  const [showAll, setShowAll] = useState(false);
  const lang = provider.useLang();
  const tt = useText();
  const shown = showAll ? rows : rows.slice(0, INITIAL_AUDIT);

  return (
    <Section icon={<Icon as={MdHistory} />} title={tt('Активность дашборда')} count={rows.length}>
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          {tt('Действий из дашборда пока нет.')}
        </Text>
      ) : (
        <Flex direction="column" gap={2}>
          {shown.map((e) => (
            <Flex key={e.id} align="center" gap={3} rounded="11px" py={3} px={4} {...INSET}>
              <Box flex="1" minW={0}>
                <Text fontSize="13.5px" isTruncated>
                  <Text as="span" fontWeight="600">
                    {e.actorName ?? tt('Кто-то')}
                  </Text>{' '}
                  {describeAudit(e, lang)}
                </Text>
                {isModerationAction(e.action) && e.detail && (
                  <Text fontSize="11.5px" color="TextSecondary" noOfLines={1}>
                    {e.detail}
                  </Text>
                )}
              </Box>
              <Text fontSize="11.5px" color="TextSecondary" flexShrink={0}>
                {timeAgo(e.createdAt, lang)}
              </Text>
            </Flex>
          ))}
          {rows.length > INITIAL_AUDIT && (
            <Button size="sm" variant="ghost" alignSelf="center" onClick={() => setShowAll((v) => !v)}>
              {showAll ? tt('Свернуть') : `${tt('Показать все')} (${rows.length})`}
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
  const tt = useText();
  const query = useModerationQuery(guild);
  const audit = useAuditQuery(guild);

  return (
    <Flex direction="column" gap={4}>
      <Box>
        <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
          {tt('МОДЕРАЦИЯ')}
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt={1}>
          {tt('Предупреждения, наказания и апелляции')}
        </Heading>
      </Box>
      <QueryStatus
        query={query}
        loading={<ModerationSkeleton />}
        error={tt('Не удалось загрузить данные модерации.')}
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
