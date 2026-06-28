import {
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
  Skeleton,
  Text,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { IoSearch, IoArrowBack, IoWarning } from 'react-icons/io5';
import { useState } from 'react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useMemberSearchQuery, useMemberDetailQuery } from '@/api/hooks';
import { useDebounce } from '@/utils/useDebounce';
import { toRGB } from '@/utils/common';
import type { MemberDetail } from '@/config/types/custom-types';

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function DetailCard({ data, onBack }: { data: MemberDetail; onBack: () => void }) {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
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
    </Box>
  );
}

const MembersPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const debounced = useDebounce(query, 300);

  const search = useMemberSearchQuery(guild, debounced);
  const detail = useMemberDetailQuery(guild, selected);
  const hasQuery = debounced.trim().length >= 2;

  return (
    <Flex direction="column" gap={5}>
      <Heading fontSize="2xl" fontWeight="600">
        Members
      </Heading>

      <InputGroup maxW={{ base: 'full', sm: 'md' }}>
        <InputLeftElement pointerEvents="none">
          <Icon as={IoSearch} color="TextSecondary" />
        </InputLeftElement>
        <Input
          variant="main"
          placeholder="Search members by name…"
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
          <DetailCard data={detail.data} onBack={() => setSelected(null)} />
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
              align="center"
              gap={3}
              p={3}
              rounded="xl"
              cursor="pointer"
              bg="CardBackground"
              transition="background 0.12s ease"
              _hover={{ bg: 'blackAlpha.100', _dark: { bg: 'whiteAlpha.100' } }}
              onClick={() => setSelected(m.id)}
            >
              <Avatar src={m.avatar} name={m.displayName} size="sm" />
              <Box minW={0}>
                <Text fontWeight="600" isTruncated>
                  {m.displayName}
                </Text>
                <Text fontSize="xs" color="TextSecondary" isTruncated>
                  @{m.name}
                </Text>
              </Box>
            </Flex>
          ))}
        </Flex>
      )}
    </Flex>
  );
};

MembersPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default MembersPage;
