import { Box, Flex, Text, Icon } from '@chakra-ui/react';
import { useColorMode } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { flushSync } from 'react-dom';
import type { MouseEvent } from 'react';
import { MdSearch, MdDarkMode, MdLightMode, MdPerson, MdMenu } from 'react-icons/md';
import { NotificationsBell } from './NotificationsPanel';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { iconUrl, avatarUrl } from '@/api/discord';
import { useGuildPreview, useGuildStatsQuery, useSelfUserQuery } from '@/api/hooks';
import { OPEN_COMMAND_PALETTE } from '@/components/AppChrome';
import { useText } from '@/config/translations/ui-text';

const pulse = keyframes`0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}`;

type DocWithVT = Document & { startViewTransition?: (cb: () => void) => unknown };

function IconBtn({
  children,
  onClick,
  title,
}: {
  children: React.ReactNode;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
  title?: string;
}) {
  return (
    <Flex
      as="button"
      title={title}
      onClick={onClick}
      w="38px"
      h="38px"
      rounded="11px"
      border="1px solid"
      borderColor="CardBorder"
      align="center"
      justify="center"
      color="TextSecondary"
      position="relative"
      transition="background .15s ease"
      _hover={{ bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
    >
      {children}
    </Flex>
  );
}

export function IrisHeader({ onOpenSidebar }: { onOpenSidebar?: () => void }) {
  const { guild: guildId } = useRouter().query as { guild: string };
  const { guild } = useGuildPreview(guildId);
  const stats = useGuildStatsQuery(guildId).data;
  const user = useSelfUserQuery().data;
  const { colorMode, toggleColorMode } = useColorMode();
  const tt = useText();

  const online = stats?.online ?? false;

  const onToggleTheme = (e: MouseEvent<HTMLElement>) => {
    const doc = document as DocWithVT;
    const reduce =
      typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!doc.startViewTransition || reduce) {
      toggleColorMode();
      return;
    }
    document.documentElement.style.setProperty('--vt-x', `${e.clientX}px`);
    document.documentElement.style.setProperty('--vt-y', `${e.clientY}px`);
    doc.startViewTransition(() => flushSync(() => toggleColorMode()));
  };

  return (
    <Flex
      align="center"
      gap={{ base: '10px', md: '16px' }}
      px={{ base: '16px', md: '28px' }}
      py="15px"
      borderBottom="1px solid"
      borderColor="CardBorder"
      bg="white"
      _dark={{ bg: '#0D0D18' }}
      flexShrink={0}
    >
      {/* Mobile: open sidebar */}
      <Flex display={{ base: 'flex', xl: 'none' }}>
        <IconBtn onClick={() => onOpenSidebar?.()} title={tt('Меню')}>
          <Icon as={MdMenu} boxSize="19px" />
        </IconBtn>
      </Flex>

      {guild?.icon ? (
        <Box
          as="img"
          src={iconUrl(guild) ?? undefined}
          alt=""
          w="34px"
          h="34px"
          rounded="11px"
          objectFit="cover"
        />
      ) : (
        <Flex
          w="34px"
          h="34px"
          rounded="11px"
          align="center"
          justify="center"
          bgGradient="linear(135deg, #8B7CFF, #6E56F5)"
          color="white"
          fontWeight="700"
          fontSize="13px"
        >
          {(guild?.name ?? 'OG').slice(0, 2).toUpperCase()}
        </Flex>
      )}
      <Box lineHeight="1.25" minW={0} flex="1">
        <Text fontSize="15px" fontWeight="700" noOfLines={1}>
          {guild?.name ?? '—'}
        </Text>
        <Flex align="center" gap="5px" fontSize="11.5px" color="TextSecondary">
          <Box
            w="7px"
            h="7px"
            rounded="full"
            flexShrink={0}
            bg={online ? 'green.400' : 'secondaryGray.500'}
            animation={online ? `${pulse} 2.4s infinite` : undefined}
          />
          {/* noOfLines keeps "7 участников" on one line — it was stacking one
              word per line when the action cluster squeezed this block. */}
          <Text as="span" noOfLines={1}>
            {online
              ? `${(stats?.member_count ?? 0).toLocaleString('ru-RU')} ${tt('участников')}`
              : tt('Бот офлайн')}
          </Text>
        </Flex>
      </Box>

      <Flex ml="auto" align="center" gap={{ base: '6px', md: '10px' }} flexShrink={0}>
        <Flex
          as="button"
          display={{ base: 'none', md: 'flex' }}
          align="center"
          gap="8px"
          px="14px"
          py="8px"
          rounded="11px"
          border="1px solid"
          borderColor="CardBorder"
          color="TextSecondary"
          fontSize="13px"
          minW="180px"
          transition="border-color .15s ease"
          _hover={{ borderColor: 'brand.400' }}
          onClick={() => window.dispatchEvent(new Event(OPEN_COMMAND_PALETTE))}
        >
          <Icon as={MdSearch} boxSize="17px" />
          {tt('Быстрый переход')}
          <Box as="span" ml="auto" fontSize="11px" border="1px solid" borderColor="CardBorder" rounded="6px" px="6px">
            ⌘K
          </Box>
        </Flex>
        {/* Mobile: the wide Quick-jump field is hidden below md — give the
            palette a visible trigger. */}
        <Flex display={{ base: 'flex', md: 'none' }}>
          <IconBtn
            onClick={() => window.dispatchEvent(new Event(OPEN_COMMAND_PALETTE))}
            title={tt('Быстрый переход')}
          >
            <Icon as={MdSearch} boxSize="19px" />
          </IconBtn>
        </Flex>
        <IconBtn onClick={onToggleTheme} title={tt('Сменить тему')}>
          <Icon as={colorMode === 'light' ? MdDarkMode : MdLightMode} boxSize="19px" />
        </IconBtn>
        <NotificationsBell guild={guildId} />
        {/* Avatar → profile (README §11) */}
        <Flex
          as={Link}
          href="/user/profile"
          title={tt('Профиль')}
          w="38px"
          h="38px"
          rounded="full"
          overflow="hidden"
          align="center"
          justify="center"
          bg="blackAlpha.100"
          _dark={{ bg: 'whiteAlpha.100' }}
          color="TextSecondary"
          border="1px solid"
          borderColor="transparent"
          transition="border-color .15s ease"
          _hover={{ borderColor: 'brand.400' }}
        >
          {user ? (
            <Box as="img" src={avatarUrl(user)} alt="" w="full" h="full" objectFit="cover" />
          ) : (
            <Icon as={MdPerson} boxSize="20px" />
          )}
        </Flex>
      </Flex>
    </Flex>
  );
}
