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

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('ru-RU', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Russian plural for warnings: 1 предупреждение, 2 предупреждения, 5 предупреждений.
function pluralStrikes(n: number): string {
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
    <Box as="span" fontSize="12px" fontWeight="600" rounded="20px" px="12px" py="5px" color={color} bg={bg} _dark={dark}>
      {children}
    </Box>
  );
}

// A uppercase section label with an accent-ink icon.
function SectionLabel({ icon, children }: { icon: any; children: ReactNode }) {
  return (
    <Flex align="center" gap="8px" mb="8px">
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
    <Box borderTop="1px solid" borderColor="CardBorder" pt="16px">
      <Text fontSize="11px" fontWeight="700" textTransform="uppercase" letterSpacing="0.06em" color="TextSecondary" mb="10px">
        Действия
      </Text>
      <Wrap spacing="8px">
        <WrapItem>
          <Button {...safeBtn} onClick={() => open('warn')} isDisabled={!member.inServer}>
            Предупредить
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...safeBtn} onClick={() => open('mute')} isDisabled={!member.inServer}>
            Мут
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...safeBtn} onClick={() => open('unmute')} isDisabled={!member.inServer}>
            Снять мут
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...dangerBtn} onClick={() => open('kick')} isDisabled={!member.inServer}>
            Кик
          </Button>
        </WrapItem>
        <WrapItem>
          <Button {...dangerBtn} onClick={() => open('ban')}>
            Бан
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
              {pending ? ACTION_RU[pending] : ''} — {member.displayName}?
            </AlertDialogHeader>
            <AlertDialogBody>
              {pending !== 'unmute' && (
                <Textarea
                  placeholder="Причина (необязательно)"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  mb={pending === 'mute' ? 3 : 0}
                />
              )}
              {pending === 'mute' && (
                <Select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
                  <option value={10}>10 минут</option>
                  <option value={60}>1 час</option>
                  <option value={1440}>1 день</option>
                  <option value={10080}>7 дней</option>
                </Select>
              )}
              {danger && (
                <Text fontSize="sm" color="red.400" mt={3}>
                  Это нельзя отменить из дашборда.
                </Text>
              )}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={() => setPending(null)} variant="ghost">
                Отмена
              </Button>
              <Button
                colorScheme={danger ? 'red' : 'brand'}
                ml={3}
                isLoading={mutation.isLoading}
                onClick={confirm}
              >
                {pending ? ACTION_RU[pending] : ''}
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
  return (
    <Flex
      direction="column"
      gap="18px"
      bg="CardBackground"
      rounded="18px"
      p="22px"
      border="1px solid"
      borderColor="CardBorder"
      boxShadow="normal"
    >
      <Flex align="center" gap="14px">
        <Avatar src={data.avatar ?? undefined} name={data.displayName} size="lg" />
        <Box flex="1" minW={0}>
          <Heading fontSize="20px" fontWeight="700" isTruncated>
            {data.displayName}
          </Heading>
          <Text fontSize="13px" color="TextSecondary">
            @{data.name}
            {data.inServer && ` · присоединился ${fmtDate(data.joinedAt)}`}
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
          Назад
        </Button>
      </Flex>

      <Flex gap="10px" wrap="wrap">
        <Pill color="brand.200" bg="brandAlpha.100">
          Уровень {data.level} · {data.xp.toLocaleString('ru-RU')} XP
        </Pill>
        {(data.activeStrikes ?? 0) > 0 && (
          <Pill color="orange.400" bg="rgba(245,177,76,0.14)">
            {data.activeStrikes} {pluralStrikes(data.activeStrikes)}
          </Pill>
        )}
        {!data.inServer && (
          <Pill color="TextSecondary" bg="blackAlpha.100" dark={{ bg: 'whiteAlpha.100' }}>
            Не на сервере
          </Pill>
        )}
      </Flex>

      {data.roles.length > 0 && (
        <Box>
          <Text fontSize="11px" fontWeight="700" textTransform="uppercase" letterSpacing="0.06em" color="TextSecondary" mb="8px">
            Роли
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
                    px="11px"
                    py="4px"
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
        <SectionLabel icon={IoWarning}>Предупреждения ({data.warnings.length})</SectionLabel>
        {data.warnings.length === 0 ? (
          <Text fontSize="13px" color="TextSecondary">
            Предупреждений нет.
          </Text>
        ) : (
          <Flex direction="column" gap="8px">
            {data.warnings.map((w) => (
              <Box key={w.id} rounded="11px" p="11px 13px" {...INSET}>
                <Text fontSize="13.5px">{w.reason}</Text>
                <Text fontSize="11.5px" color="TextSecondary" mt="2px">
                  {w.moderatorName} · {fmtDate(w.createdAt)}
                </Text>
              </Box>
            ))}
          </Flex>
        )}
      </Box>

      <Box>
        <SectionLabel icon={IoDocumentText}>Заметки модераторов ({data.notes?.length ?? 0})</SectionLabel>
        {!data.notes || data.notes.length === 0 ? (
          <Text fontSize="13px" color="TextSecondary">
            Заметок нет. Добавьте через /note в Discord — участник их не видит.
          </Text>
        ) : (
          <Flex direction="column" gap="8px">
            {data.notes.map((n) => (
              <Box key={n.id} rounded="11px" p="11px 13px" {...INSET}>
                <Text fontSize="13.5px" whiteSpace="pre-wrap">{n.note}</Text>
                <Text fontSize="11.5px" color="TextSecondary" mt="2px">
                  #{n.id} · {n.authorName ?? '—'} · {fmtDate(n.createdAt)}
                </Text>
              </Box>
            ))}
          </Flex>
        )}
      </Box>

      <Box>
        <SectionLabel icon={IoFileTrayFull}>Недавние кейсы ({data.cases?.length ?? 0})</SectionLabel>
        {!data.cases || data.cases.length === 0 ? (
          <Text fontSize="13px" color="TextSecondary">
            Кейсов модерации нет.
          </Text>
        ) : (
          <Flex direction="column" gap="8px">
            {data.cases.map((c) => (
              <Flex key={c.caseNumber} align="center" justify="space-between" gap="10px" rounded="11px" p="11px 13px" {...INSET}>
                <Box minW={0}>
                  <Text fontSize="13.5px" fontWeight="600" isTruncated textTransform="capitalize">
                    #{c.caseNumber} · {c.action}
                  </Text>
                  <Text fontSize="11.5px" color="TextSecondary" noOfLines={1}>
                    {c.reason ?? 'Без причины'} · {c.moderatorName ?? '—'}
                  </Text>
                </Box>
                <Text fontSize="11.5px" color="TextSecondary" flexShrink={0}>
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
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const debounced = useDebounce(query, 300);

  const self = useSelfUserQuery();
  const moderatorName = self.data ? self.data.username : undefined;
  const moderatorId = self.data?.id;

  const search = useMemberSearchQuery(guild, debounced);
  const detail = useMemberDetailQuery(guild, selected);
  const hasQuery = debounced.trim().length >= 2;

  return (
    <Flex direction="column" gap="18px">
      <Box>
        <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
          УЧАСТНИКИ
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt="3px">
          Поиск и модерация
        </Heading>
      </Box>

      <InputGroup maxW={{ base: 'full', sm: '420px' }}>
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
          placeholder="Поиск по имени или @нику…"
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
          <Text color="TextSecondary">Не удалось загрузить участника.</Text>
        )
      ) : !hasQuery ? (
        <Text color="TextSecondary">Введите минимум 2 символа для поиска.</Text>
      ) : search.isLoading ? (
        <Flex direction="column" gap={2}>
          <Skeleton h="56px" rounded="xl" />
          <Skeleton h="56px" rounded="xl" />
          <Skeleton h="56px" rounded="xl" />
        </Flex>
      ) : (search.data?.length ?? 0) === 0 ? (
        <Text color="TextSecondary">Никого не найдено по «{debounced}».</Text>
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
              gap="13px"
              p="12px 14px"
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
