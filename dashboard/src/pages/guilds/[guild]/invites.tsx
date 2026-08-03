import {
  Avatar,
  Box,
  Flex,
  Heading,
  Skeleton,
  Text,
} from '@chakra-ui/react';
import { useRouter } from 'next/router';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useInvitesQuery, useSetInviteLogMutation } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { ChannelSelect } from '@/components/forms/ChannelSelect';
import { useText } from '@/config/translations/ui-text';

const RANK_COLOR = ['#F5C043', '#C9CDD6', '#CD8544']; // gold / silver / bronze for 1–3

const InvitesPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const query = useInvitesQuery(guild);
  const setLog = useSetInviteLogMutation();
  const tt = useText();
  const data = query.data;

  return (
    <Flex direction="column" gap={5}>
      <Box>
        <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
          {tt('ИНВАЙТ-ТРЕКЕР')}
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt={1}>
          {tt('Инвайт-трекер')}
        </Heading>
        <Text fontSize="14px" color="TextSecondary" mt={1}>
          {tt('Кто приводит людей на сервер — и куда постить анонсы о заходах.')}
        </Text>
      </Box>

      <Box bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="20px" p={{ base: 5, md: 6 }}>
        <Text fontWeight="700" fontSize="15px">
          {tt('Канал анонсов заходов')}
        </Text>
        <Text fontSize="13px" color="TextSecondary" mt={1} mb={3}>
          {tt('Каждый заход постится сюда с указанием пригласившего.')}
        </Text>
        <ChannelSelect
          value={data?.logChannelId ?? undefined}
          onChange={(v) => setLog.mutate({ guild, channelId: v })}
          isDisabled={setLog.isLoading}
        />
      </Box>

      <QueryStatus
        query={query}
        error={tt('Не удалось загрузить инвайты.')}
        loading={
          <Box bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="20px" p={{ base: 5, md: 6 }}>
            <Flex direction="column" gap={3}>
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} h="44px" rounded="12px" />
              ))}
            </Flex>
          </Box>
        }
      >
        <Box bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="20px" p={{ base: 5, md: 6 }}>
          <Text fontSize="11px" fontWeight="700" letterSpacing="0.1em" color="TextSecondary" mb={3}>
            {tt('Топ пригласивших')}
          </Text>
          <Flex direction="column" gap={2}>
            {(data?.leaderboard ?? []).map((e, i) => (
              <Flex
                key={e.inviterId}
                align="center"
                gap={3}
                bg="blackAlpha.50"
                _dark={{ bg: 'whiteAlpha.50' }}
                rounded="12px"
                px={3}
                py={2}
              >
                <Text
                  fontWeight="800"
                  fontSize="14px"
                  w="22px"
                  textAlign="center"
                  color={RANK_COLOR[i] ?? 'TextSecondary'}
                  flexShrink={0}
                >
                  {i + 1}
                </Text>
                <Avatar size="sm" name={e.name} src={e.avatar ?? undefined} />
                <Box minW={0}>
                  <Text fontWeight="600" fontSize="14px" isTruncated>
                    {e.name}
                  </Text>
                  <Text fontSize="12px" color="TextSecondary">
                    {e.joined} {tt('зашло')} · {e.left} {tt('ушло')}
                  </Text>
                </Box>
                <Box ml="auto" textAlign="right" flexShrink={0}>
                  <Text fontWeight="800" fontSize="18px" lineHeight="1.1">
                    {e.net}
                  </Text>
                  <Text fontSize="10px" color="TextSecondary" textTransform="uppercase" letterSpacing="0.06em">
                    {tt('инвайтов')}
                  </Text>
                </Box>
              </Flex>
            ))}
          </Flex>
          {data && data.leaderboard.length === 0 && (
            <Text fontSize="sm" color="TextSecondary">
              {tt('Пока никого не отследили.')}
            </Text>
          )}
        </Box>
      </QueryStatus>
    </Flex>
  );
};

InvitesPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default InvitesPage;
