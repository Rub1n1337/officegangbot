import {
  Box, Flex, Text, Icon, Popover, PopoverTrigger, PopoverContent,
  PopoverBody, Portal, useDisclosure,
} from '@chakra-ui/react';
import { MdUnfoldMore, MdCheck, MdAddCircleOutline } from 'react-icons/md';
import { useRouter } from 'next/router';
import { useMemo } from 'react';
import { useGuilds, useMyBotGuilds } from '@/api/hooks';
import { iconUrl } from '@/api/discord';
import { config } from '@/config/common';
import { useText } from '@/config/translations/ui-text';

// Server-switcher popover (Iris): lists the admin guilds from the existing
// guilds hook and routes to /guilds/[id]. Replaces the plain link the sidebar
// switcher used before. Outside-click closes it (Chakra Popover).
export function ServerPicker({ guildId }: { guildId: string }) {
  const router = useRouter();
  const guilds = useGuilds();
  const botGuilds = useMyBotGuilds();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const tt = useText();

  // Which of these servers the bot is actually in — the list deliberately
  // shows ALL the user's admin servers (that's how you invite the bot to a new
  // one), but without a marker they all looked identical and picking a botless
  // one felt like a bug. Indicators only render when the bot answered, so an
  // unreachable bot doesn't mislabel every server as botless.
  const knowPresence = botGuilds.data?.botReachable === true;
  const present = useMemo(
    () => new Set((botGuilds.data?.guilds ?? []).map((g) => g.id)),
    [botGuilds.data]
  );

  const list = useMemo(
    () => (guilds.data ?? []).filter((g) => config.guild.filter(g)),
    [guilds.data]
  );
  const current = list.find((g) => g.id === guildId);

  const go = (id: string) => {
    onClose();
    if (id !== guildId) router.push(`/guilds/${id}`);
  };

  const initials = (name?: string) => (name ?? 'OG').slice(0, 2).toUpperCase();

  return (
    <Popover isOpen={isOpen} onOpen={onOpen} onClose={onClose} placement="bottom-start" gutter={6} isLazy>
      <PopoverTrigger>
        <Flex
          as="button"
          align="center"
          gap={2.5}
          py={2} px={2.5}
          rounded="12px"
          bg="CardBackground"
          border="1px solid"
          borderColor="CardBorder"
          transition="border-color .15s ease"
          _hover={{ borderColor: 'brand.400' }}
          w="full"
          textAlign="left"
        >
          {current?.icon ? (
            <Box as="img" src={iconUrl(current) ?? undefined} alt="" w="28px" h="28px" rounded="8px" objectFit="cover" flexShrink={0} />
          ) : (
            <Flex w="28px" h="28px" rounded="8px" align="center" justify="center" bgGradient="linear(135deg, #8B7CFF, #6E56F5)" color="white" fontSize="11px" fontWeight="700" flexShrink={0}>
              {initials(current?.name)}
            </Flex>
          )}
          <Box flex="1" minW={0} lineHeight="1.2">
            <Text fontSize="13px" fontWeight="600" noOfLines={1}>{current?.name ?? '—'}</Text>
            <Text fontSize="11px" color="TextSecondary">{tt('Сменить сервер')}</Text>
          </Box>
          <Icon as={MdUnfoldMore} boxSize="18px" color="TextSecondary" />
        </Flex>
      </PopoverTrigger>
      <Portal>
        <PopoverContent
          w="258px"
          maxW="calc(100vw - 24px)"
          bg="CardBackground"
          border="1px solid"
          borderColor="CardBorder"
          rounded="14px"
          boxShadow="normal"
          _focusVisible={{ outline: 'none', boxShadow: 'normal' }}
        >
          <PopoverBody p={2}>
            <Text fontSize="10.5px" fontWeight="700" letterSpacing="0.1em" color="TextSecondary" px={2.5} pt={2} pb={1}>
              {tt('ВАШИ СЕРВЕРЫ')}
            </Text>
            <Box maxH="300px" overflowY="auto">
              {list.map((g) => {
                const active = g.id === guildId;
                return (
                  <Flex
                    key={g.id}
                    as="button"
                    onClick={() => go(g.id)}
                    align="center"
                    gap={2.5}
                    w="full"
                    textAlign="left"
                    py={2} px={2.5}
                    rounded="10px"
                    bg={active ? 'brandAlpha.100' : 'transparent'}
                    _hover={active ? {} : { bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
                  >
                    {g.icon ? (
                      <Box as="img" src={iconUrl(g) ?? undefined} alt="" w="30px" h="30px" rounded="9px" objectFit="cover" flexShrink={0} />
                    ) : (
                      <Flex
                        w="30px" h="30px" rounded="9px" align="center" justify="center" flexShrink={0}
                        fontSize="11px" fontWeight="700"
                        {...(active
                          ? { bgGradient: 'linear(135deg, #8B7CFF, #6E56F5)', color: 'white' }
                          : { bg: 'secondaryGray.100', color: 'TextSecondary', _dark: { bg: 'navy.600' } })}
                      >
                        {initials(g.name)}
                      </Flex>
                    )}
                    <Text flex="1" minW={0} fontSize="13px" fontWeight={active ? '600' : '500'} noOfLines={1}>
                      {g.name}
                    </Text>
                    {knowPresence && !present.has(g.id) && (
                      <Text fontSize="10.5px" color="TextSecondary" flexShrink={0}>
                        {tt('нет бота')}
                      </Text>
                    )}
                    {knowPresence && present.has(g.id) && !active && (
                      <Box w="7px" h="7px" rounded="full" bg="green.400" flexShrink={0} />
                    )}
                    {active && <Icon as={MdCheck} boxSize="17px" color="brand.200" flexShrink={0} />}
                  </Flex>
                );
              })}
            </Box>
            <Box borderTop="1px solid" borderColor="CardBorder" mt={1} pt={1}>
              {/* The real Discord invite (server picker inside Discord) — this
                  used to link to /user/home, which just dumped the user on the
                  start page instead of adding the bot anywhere. */}
              <Flex
                as="a"
                href={config.inviteUrl}
                target="_blank"
                rel="noreferrer"
                align="center"
                gap={2.5}
                py={2} px={2.5}
                rounded="10px"
                color="TextSecondary"
                fontSize="13px"
                _hover={{ bg: 'blackAlpha.50', color: 'TextPrimary', _dark: { bg: 'whiteAlpha.50' } }}
                onClick={onClose}
              >
                <Icon as={MdAddCircleOutline} boxSize="18px" />
                {tt('Добавить на другой сервер')}
              </Flex>
            </Box>
          </PopoverBody>
        </PopoverContent>
      </Portal>
    </Popover>
  );
}
