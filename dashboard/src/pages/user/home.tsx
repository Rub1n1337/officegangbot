import {
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  CardHeader,
  Flex,
  Heading,
  Icon,
  Input,
  InputGroup,
  InputLeftElement,
  SimpleGrid,
  Skeleton,
  Text,
} from '@chakra-ui/react';
import { IoSearch, IoAddCircleOutline } from 'react-icons/io5';
import { useState } from 'react';
import { config } from '@/config/common';
import { useGuilds, useMyBotGuilds } from '@/api/hooks';
import { NextPageWithLayout } from '@/pages/_app';
import AppLayout from '@/components/layout/app';
import { iconUrl } from '@/api/discord';
import { ErrorPanel } from '@/components/panel/ErrorPanel';
import Link from 'next/link';

const HomePage: NextPageWithLayout = () => {
  return <GuildSelect />;
};

export function GuildSelect() {
  const guilds = useGuilds();
  const botGuilds = useMyBotGuilds();
  const [search, setSearch] = useState('');

  if (guilds.status === 'error')
    return (
      <ErrorPanel
        retry={() => guilds.refetch()}
        isRetrying={guilds.isFetching}
        hint="Couldn't reach Discord — check your connection and try again."
      >
        Couldn&apos;t load your servers
      </ErrorPanel>
    );

  if (guilds.status === 'loading')
    return (
      <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={3}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} minH="80px" rounded="2xl" />
        ))}
      </SimpleGrid>
    );

  const present = new Set((botGuilds.data?.guilds ?? []).map((g) => g.id));
  const memberCounts = new Map((botGuilds.data?.guilds ?? []).map((g) => [g.id, g.member_count]));
  const botReachable = botGuilds.data?.botReachable ?? false;

  const manageable = (guilds.data ?? []).filter((guild) => config.guild.filter(guild));

  // No servers where the user is an admin — point them at the invite instead of
  // an empty grid.
  if (manageable.length === 0)
    return (
      <Flex direction="column" align="center" gap={3} py={16} textAlign="center">
        <Icon as={IoAddCircleOutline} boxSize={10} color="TextSecondary" />
        <Heading size="md">No servers to manage yet</Heading>
        <Text color="TextSecondary" maxW="sm">
          You need the Administrator permission on a server to configure the bot there. Invite it to
          a server you own to get started.
        </Text>
        <Button as="a" href={config.inviteUrl} target="_blank" variant="action" mt={1}>
          Invite the bot
        </Button>
      </Flex>
    );

  const query = search.trim().toLowerCase();
  const filtered = manageable
    .filter((guild) => guild.name.toLowerCase().includes(query))
    .sort((a, b) => {
      // Bot-present servers first, then alphabetical.
      const ap = present.has(a.id) ? 0 : 1;
      const bp = present.has(b.id) ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return a.name.localeCompare(b.name);
    });

  return (
    <Flex direction="column" gap={4}>
      <InputGroup maxW={{ base: 'full', sm: 'sm' }}>
        <InputLeftElement pointerEvents="none">
          <Icon as={IoSearch} color="TextSecondary" />
        </InputLeftElement>
        <Input
          variant="main"
          pl="2.75rem"
          placeholder="Search servers…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </InputGroup>

      {filtered.length === 0 ? (
        <Text color="TextSecondary">No servers match “{search}”.</Text>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={3}>
          {filtered.map((guild) => {
            const isPresent = present.has(guild.id);
            return (
              <Card
                key={guild.id}
                variant="primary"
                as={Link}
                href={`/guilds/${guild.id}`}
                transition="transform 0.15s ease, box-shadow 0.15s ease"
                _hover={{ transform: 'translateY(-2px)', shadow: 'md' }}
                _focusVisible={{
                  outline: '2px solid',
                  outlineColor: 'Brand',
                  outlineOffset: '2px',
                }}
              >
                <CardHeader as={Flex} flexDirection="row" align="center" gap={3}>
                  <Avatar src={iconUrl(guild)} name={guild.name} size="md" />
                  <Box flex={1} minW={0}>
                    <Text fontWeight="600" isTruncated>
                      {guild.name}
                    </Text>
                    {botReachable && isPresent && (
                      <Text fontSize="xs" color="TextSecondary">
                        {memberCounts.get(guild.id)?.toLocaleString()} members
                      </Text>
                    )}
                  </Box>
                  {botReachable && (
                    <Badge
                      colorScheme={isPresent ? 'green' : 'gray'}
                      rounded="md"
                      flexShrink={0}
                      textTransform="none"
                    >
                      {isPresent ? 'Active' : 'Add bot'}
                    </Badge>
                  )}
                </CardHeader>
              </Card>
            );
          })}
        </SimpleGrid>
      )}
    </Flex>
  );
}

HomePage.getLayout = (c) => <AppLayout>{c}</AppLayout>;
export default HomePage;
