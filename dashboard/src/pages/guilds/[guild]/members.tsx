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
import { useRef, useState } from 'react';
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
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
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

  return (
    <Box mt={4}>
      <Text fontSize="xs" fontWeight="700" textTransform="uppercase" color="TextSecondary" mb={2}>
        Actions
      </Text>
      <Wrap>
        <WrapItem>
          <Button size="sm" onClick={() => open('warn')} isDisabled={!member.inServer}>
            Warn
          </Button>
        </WrapItem>
        <WrapItem>
          <Button size="sm" onClick={() => open('mute')} isDisabled={!member.inServer}>
            Mute
          </Button>
        </WrapItem>
        <WrapItem>
          <Button size="sm" variant="outline" onClick={() => open('unmute')} isDisabled={!member.inServer}>
            Unmute
          </Button>
        </WrapItem>
        <WrapItem>
          <Button
            size="sm"
            colorScheme="orange"
            variant="outline"
            onClick={() => open('kick')}
            isDisabled={!member.inServer}
          >
            Kick
          </Button>
        </WrapItem>
        <WrapItem>
          <Button size="sm" colorScheme="red" onClick={() => open('ban')}>
            Ban
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
            <AlertDialogHeader textTransform="capitalize">
              {pending} {member.displayName}?
            </AlertDialogHeader>
            <AlertDialogBody>
              {pending !== 'unmute' && (
                <Textarea
                  placeholder="Reason (optional)"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  mb={pending === 'mute' ? 3 : 0}
                />
              )}
              {pending === 'mute' && (
                <Select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
                  <option value={10}>10 minutes</option>
                  <option value={60}>1 hour</option>
                  <option value={1440}>1 day</option>
                  <option value={10080}>7 days</option>
                </Select>
              )}
              {danger && (
                <Text fontSize="sm" color="red.400" mt={3}>
                  This can’t be undone from the dashboard.
                </Text>
              )}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={() => setPending(null)} variant="ghost">
                Cancel
              </Button>
              <Button
                colorScheme={danger ? 'red' : 'brand'}
                ml={3}
                isLoading={mutation.isLoading}
                onClick={confirm}
                textTransform="capitalize"
              >
                {pending}
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
    <Box bg="CardBackground" rounded="18px" p="22px" border="1px solid" borderColor="CardBorder" boxShadow="normal">
      <Flex align="center" gap={4} mb={4}>
        <Avatar src={data.avatar ?? undefined} name={data.displayName} size="lg" />
        <Box minW={0}>
          <Heading size="md" isTruncated>
            {data.displayName}
          </Heading>
          <Text fontSize="sm" color="TextSecondary">
            @{data.name} · {data.id}
          </Text>
        </Box>
        <Button ml="auto" size="sm" variant="ghost" leftIcon={<Icon as={IoArrowBack} />} onClick={onBack}>
          Back
        </Button>
      </Flex>

      <Flex gap={3} wrap="wrap" mb={4}>
        <Badge colorScheme="purple" rounded="md" px={2} py={1}>
          Level {data.level} · {data.xp.toLocaleString()} XP
        </Badge>
        <Badge colorScheme={data.inServer ? 'green' : 'gray'} rounded="md" px={2} py={1}>
          {data.inServer ? `Joined ${fmtDate(data.joinedAt)}` : 'Not in server'}
        </Badge>
        {(data.activeStrikes ?? 0) > 0 && (
          <Badge colorScheme="orange" rounded="md" px={2} py={1}>
            {data.activeStrikes} active strike{data.activeStrikes === 1 ? '' : 's'}
          </Badge>
        )}
      </Flex>

      {data.roles.length > 0 && (
        <Box mb={4}>
          <Text fontSize="xs" fontWeight="700" textTransform="uppercase" color="TextSecondary" mb={2}>
            Roles
          </Text>
          <Wrap>
            {data.roles.map((r) => {
              const colored = r.color !== 0;
              return (
                <WrapItem key={r.id}>
                  <Badge
                    rounded="md"
                    variant="subtle"
                    {...(colored
                      ? { color: toRGB(r.color), borderWidth: '1px', borderColor: toRGB(r.color) }
                      : {})}
                  >
                    {r.name}
                  </Badge>
                </WrapItem>
              );
            })}
          </Wrap>
        </Box>
      )}

      <Box>
        <Flex align="center" gap={2} mb={2}>
          <Icon as={IoWarning} color="Brand" />
          <Text fontSize="xs" fontWeight="700" textTransform="uppercase" color="TextSecondary">
            Warnings ({data.warnings.length})
          </Text>
        </Flex>
        {data.warnings.length === 0 ? (
          <Text fontSize="sm" color="TextSecondary">
            No warnings on record.
          </Text>
        ) : (
          <Flex direction="column" gap={2}>
            {data.warnings.map((w) => (
              <Box key={w.id} p={3} rounded="xl" bg="blackAlpha.200" _dark={{ bg: 'whiteAlpha.50' }}>
                <Text fontSize="sm">{w.reason}</Text>
                <Text fontSize="xs" color="TextSecondary">
                  by {w.moderatorName} · {fmtDate(w.createdAt)}
                </Text>
              </Box>
            ))}
          </Flex>
        )}
      </Box>

      <Box>
        <Flex align="center" gap={2} mb={2}>
          <Icon as={IoDocumentText} color="Brand" />
          <Text fontSize="xs" fontWeight="700" textTransform="uppercase" color="TextSecondary">
            Mod notes ({data.notes?.length ?? 0})
          </Text>
        </Flex>
        {!data.notes || data.notes.length === 0 ? (
          <Text fontSize="sm" color="TextSecondary">
            No notes. Add one with /note in Discord — the member never sees them.
          </Text>
        ) : (
          <Flex direction="column" gap={2}>
            {data.notes.map((n) => (
              <Box key={n.id} p={3} rounded="xl" bg="blackAlpha.200" _dark={{ bg: 'whiteAlpha.50' }}>
                <Text fontSize="sm" whiteSpace="pre-wrap">{n.note}</Text>
                <Text fontSize="xs" color="TextSecondary">
                  #{n.id} · by {n.authorName ?? '—'} · {fmtDate(n.createdAt)}
                </Text>
              </Box>
            ))}
          </Flex>
        )}
      </Box>

      <Box>
        <Flex align="center" gap={2} mb={2}>
          <Icon as={IoFileTrayFull} color="Brand" />
          <Text fontSize="xs" fontWeight="700" textTransform="uppercase" color="TextSecondary">
            Recent cases ({data.cases?.length ?? 0})
          </Text>
        </Flex>
        {!data.cases || data.cases.length === 0 ? (
          <Text fontSize="sm" color="TextSecondary">
            No moderation cases on record.
          </Text>
        ) : (
          <Flex direction="column" gap={2}>
            {data.cases.map((c) => (
              <Flex
                key={c.caseNumber}
                align="center"
                justify="space-between"
                gap={3}
                p={3}
                rounded="xl"
                bg="blackAlpha.200"
                _dark={{ bg: 'whiteAlpha.50' }}
              >
                <Box minW={0}>
                  <Text fontSize="sm" fontWeight="600" isTruncated>
                    #{c.caseNumber} · {c.action}
                  </Text>
                  <Text fontSize="xs" color="TextSecondary" noOfLines={1}>
                    {c.reason ?? 'No reason provided'} · by {c.moderatorName ?? '—'}
                  </Text>
                </Box>
                <Text fontSize="xs" color="TextSecondary" flexShrink={0}>
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
    </Box>
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
          <Text color="TextSecondary">Couldn’t load this member.</Text>
        )
      ) : !hasQuery ? (
        <Text color="TextSecondary">Type at least 2 characters to search.</Text>
      ) : search.isLoading ? (
        <Flex direction="column" gap={2}>
          <Skeleton h="56px" rounded="xl" />
          <Skeleton h="56px" rounded="xl" />
          <Skeleton h="56px" rounded="xl" />
        </Flex>
      ) : (search.data?.length ?? 0) === 0 ? (
        <Text color="TextSecondary">No members match “{debounced}”.</Text>
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
