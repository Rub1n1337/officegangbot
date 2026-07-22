import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  Avatar,
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
  Textarea,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import {
  IoSearch,
  IoArrowBack,
  IoWarning,
  IoDocumentText,
  IoFileTrayFull,
  IoChevronForward,
} from 'react-icons/io5';
import { ReactNode, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import {
  useMemberSearchQuery,
  useMemberDetailQuery,
  useModerateMemberMutation,
  useSelfUserQuery,
} from '@/api/hooks';
import { useDebounce } from '@/utils/useDebounce';
import { toRGB } from '@/utils/common';
import type { ModerateAction } from '@/api/bot';
import type { MemberDetail } from '@/config/types/custom-types';
import { provider, type Languages } from '@/config/translations/provider';
import { useText } from '@/config/translations/ui-text';
import { tabularNums } from '@/theme/numeric';

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('ru-RU', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Russian plural: 1 активный страйк, 2 активных страйка, 5 активных страйков.
function pluralStrikes(n: number, lang: Languages): string {
  if (lang !== 'ru') return n === 1 ? 'active strike' : 'active strikes';
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return 'активный страйк';
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return 'активных страйка';
  return 'активных страйков';
}

// Iris "inset" row surface — a defined step below the card.
const INSET = { bg: 'secondaryGray.100', _dark: { bg: 'navy.600' } };

const ACTION_RU: Record<ModerateAction, string> = {
  warn: 'Предупредить',
  mute: 'Мут',
  unmute: 'Снять мут',
  kick: 'Кик',
  ban: 'Бан',
};

// A rounded status pill in one of the Iris tones.
function Pill({ children, color, bg, dark }: { children: ReactNode; color: string; bg: string; dark?: object }) {
  return (
    <Box as="span" fontSize="12px" fontWeight="600" rounded="20px" px={3} py={1} color={color} bg={bg} _dark={dark} sx={tabularNums}>
      {children}
    </Box>
  );
}

// A uppercase section label with an accent-ink icon.
function SectionLabel({ icon, children }: { icon: any; children: ReactNode }) {
  return (
    <Flex align="center" gap={2} mb={2}>
      <Icon as={icon} color="brand.200" boxSize="16px" />
      <Text fontSize="11px" fontWeight="700" textTransform="uppercase" letterSpacing="0.06em" color="TextSecondary">
        {children}
      </Text>
    </Flex>
  );
}

function ModerateBar({
  guild,
  member,
  moderatorId,
  moderatorName,
}: {
  guild: string;
  member: MemberDetail;
  moderatorId?: string;
  moderatorName?: string;
}) {
  const mutation = useModerateMemberMutation();
  const tt = useText();
  const [pending, setPending] = useState<ModerateAction | null>(null);
  const [reason, setReason] = useState('');
  const [minutes, setMinutes] = useState(60);
  const cancelRef = useRef<HTMLButtonElement>(null);

  const open = (act: ModerateAction) => {
    setReason('');
    setMinutes(60);
    setPending(act);
  };
  const danger = pending === 'kick' || pending === 'ban';

  const confirm = () => {
    if (!pending) return;
    mutation.mutate(
      {
        guild,
        userId: member.id,
        body: {
          act: pending,
          reason,
          durationMinutes: pending === 'mute' ? minutes : undefined,
          moderatorId,
          moderatorName,
        },
      },
      { onSettled: () => setPending(null) }
    );
  };

  const safeBtn = {
    size: 'sm' as const,
    rounded: '10px',
    variant: 'outline' as const,
    borderColor: 'CardBorder',
    _hover: { bg: 'blackAlpha.50', borderColor: 'brand.400', _dark: { bg: 'whiteAlpha.50' } },
  };
  const dangerBtn = {
    size: 'sm' as const,
    rounded: '10px',
    variant: 'outline' as const,
    color: 'red.400',
    borderColor: 'red.400',
    _hover: { bg: 'rgba(241,106,106,0.1)' },
  };

  return (
    <Box borderTop="1px solid" borderColor="CardBorder" pt={4}>
      <Text fontSize="11px" fontWeight="700" textTransform="uppercase" letterSpacing="0.06em" color="TextSecondary" mb={2.5}>
        {tt('Действия')}
      </Text>
      <Wrap spacing="8px">
        <WrapItem>
          <Button {...safeBtn} onClick={() => open('warn')} isDisabled={!member.inServer}>
            {tt('Предупредить')}
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...safeBtn} onClick={() => open('mute')} isDisabled={!member.inServer}>
            {tt('Мут')}
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...safeBtn} onClick={() => open('unmute')} isDisabled={!member.inServer}>
            {tt('Снять мут')}
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...dangerBtn} onClick={() => open('kick')} isDisabled={!member.inServer}>
            {tt('Кик')}
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...dangerBtn} onClick={() => open('ban')}>
            {tt('Бан')}
          </Button>
        </WrapItem>
      </Wrap>

      <AlertDialog
        isOpen={pending != null}
        leastDestructiveRef={cancelRef}
        onClose={() => setPending(null)}
        isCentered
      >
        <AlertDialogOverlay>
          <AlertDialogContent bg="CardBackground" mx={4}>
            <AlertDialogHeader>
              {pending ? tt(ACTION_RU[pending]) : ''} — {member.displayName}?
            </AlertDialogHeader>
            <AlertDialogBody>
              {pending !== 'unmute' && (
                <Textarea
                  placeholder={tt('Причина (необязательно)')}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  mb={pending === 'mute' ? 3 : 0}
                />
              )}
              {pending === 'mute' && (
                <Select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
                  <option value={10}>10 {tt('минут')}</option>
                  <option value={60}>1 {tt('час')}</option>
                  <option value={1440}>1 {tt('день')}</option>
                  <option value={10080}>7 {tt('дней')}</option>
                </Select>
              )}
              {danger && (
                <Text fontSize="sm" color="red.400" mt={3}>
                  {tt('Это нельзя отменить из дашборда.')}
                </Text>
              )}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={() => setPending(null)} variant="ghost">
                {tt('Отмена')}
              </Button>
              <Button
                colorScheme={danger ? 'red' : 'brand'}
                ml={3}
                isLoading={mutation.isLoading}
                onClick={confirm}
              >
                {pending ? tt(ACTION_RU[pending]) : ''}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  );
}

function DetailCard({
  data,
  onBack,
  guild,
  moderatorId,
  moderatorName,
}: {
  data: MemberDetail;
  onBack: () => void;
  guild: string;
  moderatorId?: string;
  moderatorName?: string;
}) {
  const lang = provider.useLang();
  const tt = useText();
  return (
    <Flex
      direction="column"
      gap={5}
      bg="CardBackground"
      rounded="18px"
      p={6}
      border="1px solid"
      borderColor="CardBorder"
      boxShadow="normal"
    >
      <Flex align="center" gap={4}>
        <Avatar src={data.avatar ?? undefined} name={data.displayName} size="lg" />
        <Box flex="1" minW={0}>
          <Heading fontSize="20px" fontWeight="700" isTruncated>
            {data.displayName}
          </Heading>
          <Text fontSize="13px" color="TextSecondary">
            @{data.name}
            {data.inServer && ` · ${tt('присоединился')} ${fmtDate(data.joinedAt)}`}
          </Text>
        </Box>
        <Button
          size="sm"
          variant="outline"
          rounded="10px"
          borderColor="CardBorder"
          color="TextSecondary"
          leftIcon={<Icon as={IoArrowBack} />}
          onClick={onBack}
          _hover={{ bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
        >
          {tt('Назад')}
        </Button>
      </Flex>

      <Flex gap={2.5} wrap="wrap">
        <Pill color="brand.200" bg="brandAlpha.100">
          {tt('Уровень')} {data.level} · {data.xp.toLocaleString('ru-RU')} XP
        </Pill>
        {(data.activeStrikes ?? 0) > 0 && (
          <Pill color="orange.400" bg="rgba(245,177,76,0.14)">
            {data.activeStrikes} {pluralStrikes(data.activeStrikes, lang)}
          </Pill>
        )}
        {!data.inServer && (
          <Pill color="TextSecondary" bg="blackAlpha.100" dark={{ bg: 'whiteAlpha.100' }}>
            {tt('Не на сервере')}
          </Pill>
        )}
      </Flex>

      {data.roles.length > 0 && (
        <Box>
          <Text fontSize="11px" fontWeight="700" textTransform="uppercase" letterSpacing="0.06em" color="TextSecondary" mb={2}>
            {tt('Роли')}
          </Text>
          <Wrap>
            {data.roles.map((r) => {
              const colored = r.color !== 0;
              return (
                <WrapItem key={r.id}>
                  <Box
                    fontSize="12px"
                    fontWeight="500"
                    rounded="8px"
                    px={3}
                    py={1}
                    border="1px solid"
                    borderColor="CardBorder"
                    {...INSET}
                    {...(colored ? { color: toRGB(r.color) } : {})}
                  >
                    {r.name}
                  </Box>
                </WrapItem>
              );
            })}
          </Wrap>
        </Box>
      )}

      <Box>
        <SectionLabel icon={IoWarning}>{tt('Предупреждения')} ({data.warnings.length})</SectionLabel>
        {data.warnings.length === 0 ? (
          <Text fontSize="13px" color="TextSecondary">
            {tt('Предупреждений нет.')}
          </Text>
        ) : (
          <Flex direction="column" gap={2}>
            {data.warnings.map((w) => (
              <Box key={w.id} rounded="11px" py={3} px={3} {...INSET}>
                <Text fontSize="14px">{w.reason}</Text>
                <Text fontSize="12px" color="TextSecondary" mt={0.5}>
                  {w.moderatorName} · {fmtDate(w.createdAt)}
                </Text>
              </Box>
            ))}
          </Flex>
        )}
      </Box>

      <Box>
        <SectionLabel icon={IoDocumentText}>{tt('Заметки модераторов')} ({data.notes?.length ?? 0})</SectionLabel>
        {!data.notes || data.notes.length === 0 ? (
          <Text fontSize="13px" color="TextSecondary">
            {tt('Заметок нет. Добавьте через /note в Discord — участник их не видит.')}
          </Text>
        ) : (
          <Flex direction="column" gap={2}>
            {data.notes.map((n) => (
              <Box key={n.id} rounded="11px" py={3} px={3} {...INSET}>
                <Text fontSize="14px" whiteSpace="pre-wrap">{n.note}</Text>
                <Text fontSize="12px" color="TextSecondary" mt={0.5}>
                  #{n.id} · {n.authorName ?? '—'} · {fmtDate(n.createdAt)}
                </Text>
              </Box>
            ))}
          </Flex>
        )}
      </Box>

      <Box>
        <SectionLabel icon={IoFileTrayFull}>{tt('Недавние кейсы')} ({data.cases?.length ?? 0})</SectionLabel>
        {!data.cases || data.cases.length === 0 ? (
          <Text fontSize="13px" color="TextSecondary">
            {tt('Кейсов модерации нет.')}
          </Text>
        ) : (
          <Flex direction="column" gap={2}>
            {data.cases.map((c) => (
              <Flex key={c.caseNumber} align="center" justify="space-between" gap={2.5} rounded="11px" py={3} px={3} {...INSET}>
                <Box minW={0}>
                  <Text fontSize="14px" fontWeight="600" isTruncated textTransform="capitalize">
                    #{c.caseNumber} · {c.action}
                  </Text>
                  <Text fontSize="12px" color="TextSecondary" noOfLines={1}>
                    {c.reason ?? tt('Без причины')} · {c.moderatorName ?? '—'}
                  </Text>
                </Box>
                <Text fontSize="12px" color="TextSecondary" flexShrink={0}>
                  {fmtDate(c.createdAt)}
                </Text>
              </Flex>
            ))}
          </Flex>
        )}
      </Box>

      <ModerateBar
        guild={guild}
        member={data}
        moderatorId={moderatorId}
        moderatorName={moderatorName}
      />
    </Flex>
  );
}

const MembersPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const tt = useText();
  const router = useRouter();
  const [query, setQuery] = useState('');
  // The selected member lives in the URL (?user=…): the detail view is
  // shareable, survives refresh, and the browser Back button closes it.
  const selected = (router.query.user as string) ?? null;
  const setSelected = (userId: string | null) => {
    const q = { ...router.query };
    if (userId) q.user = userId;
    else delete q.user;
    void router.push({ pathname: router.pathname, query: q }, undefined, { shallow: true });
  };
  const debounced = useDebounce(query, 300);

  const self = useSelfUserQuery();
  const moderatorName = self.data ? self.data.username : undefined;
  const moderatorId = self.data?.id;

  const search = useMemberSearchQuery(guild, debounced);
  const detail = useMemberDetailQuery(guild, selected);
  const hasQuery = debounced.trim().length >= 2;

  return (
    <Flex direction="column" gap={5}>
      <Box>
        <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
          {tt('УЧАСТНИКИ')}
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt={1}>
          {tt('Поиск и модерация')}
        </Heading>
      </Box>

      <InputGroup maxW={{ base: 'full', md: '420px' }}>
        <InputLeftElement pointerEvents="none" h="full">
          <Icon as={IoSearch} color="TextSecondary" />
        </InputLeftElement>
        <Input
          bg="CardBackground"
          border="1px solid"
          borderColor="CardBorder"
          rounded="12px"
          pl="2.75rem"
          h="46px"
          placeholder={tt('Поиск по имени или @нику…')}
          _hover={{ borderColor: 'brand.400' }}
          _focusVisible={{ borderColor: 'brand.400', boxShadow: 'none' }}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelected(null);
          }}
        />
      </InputGroup>

      {selected ? (
        detail.isLoading ? (
          <Skeleton h="220px" rounded="2xl" />
        ) : detail.data ? (
          <DetailCard
            data={detail.data}
            onBack={() => setSelected(null)}
            guild={guild}
            moderatorId={moderatorId}
            moderatorName={moderatorName}
          />
        ) : (
          <Text color="TextSecondary">{tt('Не удалось загрузить участника.')}</Text>
        )
      ) : !hasQuery ? (
        // Before a search this page was a bare grey line in a sea of empty
        // space. A centered prompt fills it and says what the page is for.
        <Flex direction="column" align="center" textAlign="center" py={14} gap={4}>
          <Flex w="58px" h="58px" rounded="18px" bg="brandAlpha.100" align="center" justify="center">
            <Icon as={IoSearch} boxSize="27px" color="brand.200" />
          </Flex>
          <Box>
            <Text fontWeight="700" fontSize="16px">
              {tt('Найдите участника')}
            </Text>
            <Text color="TextSecondary" fontSize="14px" mt={1} maxW="380px" lineHeight="1.5">
              {tt('Введите имя или @ник, чтобы открыть историю, предупреждения и заметки — и применить меры.')}
            </Text>
          </Box>
        </Flex>
      ) : search.isLoading ? (
        <Flex direction="column" gap={2}>
          <Skeleton h="56px" rounded="xl" />
          <Skeleton h="56px" rounded="xl" />
          <Skeleton h="56px" rounded="xl" />
        </Flex>
      ) : (search.data?.length ?? 0) === 0 ? (
        <Text color="TextSecondary">{tt('Никого не найдено по')} «{debounced}».</Text>
      ) : (
        <Flex direction="column" gap={2}>
          {search.data!.map((m) => (
            <Flex
              key={m.id}
              as="button"
              type="button"
              textAlign="left"
              w="full"
              aria-label={`View ${m.displayName}`}
              align="center"
              gap={3}
              py={3} px={4}
              rounded="14px"
              cursor="pointer"
              bg="CardBackground"
              border="1px solid"
              borderColor="CardBorder"
              transition="border-color .15s ease, transform .15s ease"
              _hover={{ borderColor: 'brand.400', transform: 'translateY(-2px)' }}
              _focusVisible={{ outline: '2px solid', outlineColor: 'Brand', outlineOffset: '2px' }}
              onClick={() => setSelected(m.id)}
            >
              <Avatar src={m.avatar} name={m.displayName} size="sm" />
              <Box minW={0} flex="1">
                <Text fontWeight="600" isTruncated>
                  {m.displayName}
                </Text>
                <Text fontSize="xs" color="TextSecondary" isTruncated>
                  @{m.name}
                </Text>
              </Box>
              <Icon as={IoChevronForward} color="TextSecondary" boxSize="18px" />
            </Flex>
          ))}
        </Flex>
      )}
    </Flex>
  );
};

MembersPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default MembersPage;
