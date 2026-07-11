import { Box, Flex, Text, Icon } from '@chakra-ui/react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { ReactNode } from 'react';
import type { IconType } from 'react-icons';
import {
  MdSmartToy,
  MdSearch,
  MdSpaceDashboard,
  MdGavel,
  MdPeople,
  MdConfirmationNumber,
  MdInsights,
  MdHistory,
  MdSettings,
} from 'react-icons/md';
import { avatarUrl } from '@/api/discord';
import { ServerPicker } from './ServerPicker';
import { useGuildInfoQuery, useSelfUserQuery } from '@/api/hooks';
import { getFeatures } from '@/utils/common';
import { useFeatureMeta } from '@/config/feature-meta';
import { guild as view } from '@/config/translations/guild';
import { OPEN_COMMAND_PALETTE } from '@/components/AppChrome';
import { Params } from '@/pages/guilds/[guild]/features/[feature]';

// Iris sidebar surfaces (from the Claude Design mockup): a slightly-darker
// panel than the cards on dark, plain white on light.
const SIDEBAR_BG = { base: 'white', _dark: '#0D0D18' };

function NavItem({
  href,
  icon,
  label,
  active,
}: {
  href: string;
  icon: IconType;
  label: ReactNode;
  active: boolean;
}) {
  return (
    <Flex
      as={Link}
      href={href}
      align="center"
      gap={3}
      px="11px"
      py="10px"
      rounded="12px"
      position="relative"
      fontSize="14px"
      fontWeight={active ? '600' : '500'}
      color={active ? 'TextPrimary' : 'TextSecondary'}
      bg={active ? 'brandAlpha.100' : 'transparent'}
      transition="background .15s ease, color .15s ease"
      _hover={active ? {} : { bg: 'blackAlpha.50', color: 'TextPrimary', _dark: { bg: 'whiteAlpha.50' } }}
    >
      {active && (
        <Box position="absolute" left="0" top="9px" bottom="9px" w="3px" rounded="3px" bg="Brand" />
      )}
      <Icon
        as={icon as any}
        boxSize="20px"
        color={active ? 'brand.200' : 'inherit'}
        _dark={{ color: active ? 'brand.200' : 'inherit' }}
      />
      {label}
    </Flex>
  );
}

export function IrisSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const router = useRouter();
  const { guild: guildId } = router.query as Params;
  const info = useGuildInfoQuery(guildId);
  const user = useSelfUserQuery().data;
  const t = view.useTranslations();
  const meta = useFeatureMeta();

  const enabled = new Set(info.data?.enabledFeatures ?? []);
  const enabledFeatures = getFeatures().filter((f) => enabled.has(f.id));

  const nav = [
    { href: `/guilds/${guildId}/settings`, icon: MdSpaceDashboard, label: t.bn.settings, route: '/guilds/[guild]/settings' },
    { href: `/guilds/${guildId}/moderation`, icon: MdGavel, label: t.bn.moderation, route: '/guilds/[guild]/moderation' },
    { href: `/guilds/${guildId}/members`, icon: MdPeople, label: t.bn.members, route: '/guilds/[guild]/members' },
    { href: `/guilds/${guildId}/tickets`, icon: MdConfirmationNumber, label: t.bn.tickets, route: '/guilds/[guild]/tickets' },
    { href: `/guilds/${guildId}/analytics`, icon: MdInsights, label: t.bn.analytics, route: '/guilds/[guild]/analytics' },
    { href: `/guilds/${guildId}/audit`, icon: MdHistory, label: t.bn.audit, route: '/guilds/[guild]/audit' },
  ];

  return (
    <Flex
      direction="column"
      gap="5px"
      h="100%"
      p="20px 16px"
      overflowY="auto"
      bg={SIDEBAR_BG.base}
      _dark={{ bg: SIDEBAR_BG._dark }}
      borderRight="1px solid"
      borderColor="CardBorder"
      onClick={onNavigate}
    >
      {/* Brand */}
      <Flex align="center" gap="11px" px="8px" pt="6px" pb="16px">
        <Flex
          w="36px"
          h="36px"
          rounded="11px"
          align="center"
          justify="center"
          bgGradient="linear(135deg, #8B7CFF, #6E56F5)"
          boxShadow="0 8px 18px -6px rgba(110,86,245,.6)"
          flexShrink={0}
        >
          <Icon as={MdSmartToy} boxSize="21px" color="white" />
        </Flex>
        <Box lineHeight="1.15">
          <Text fontWeight="700" fontSize="15px" letterSpacing="-0.01em">
            OfficeGangBot
          </Text>
          <Text fontSize="11px" color="TextSecondary">
            Панель управления
          </Text>
        </Box>
      </Flex>

      {/* Server switcher → opens the server picker popover */}
      <ServerPicker guildId={guildId} />

      {/* Search */}
      <Flex
        as="button"
        align="center"
        gap="9px"
        p="9px 11px"
        rounded="12px"
        border="1px solid"
        borderColor="CardBorder"
        color="TextSecondary"
        fontSize="13px"
        mt="2px"
        transition="background .15s ease"
        _hover={{ bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
        onClick={(e) => {
          e.stopPropagation();
          window.dispatchEvent(new Event(OPEN_COMMAND_PALETTE));
        }}
      >
        <Icon as={MdSearch} boxSize="18px" />
        Поиск…
        <Box
          as="span"
          ml="auto"
          fontSize="11px"
          border="1px solid"
          borderColor="CardBorder"
          rounded="6px"
          px="6px"
        >
          ⌘K
        </Box>
      </Flex>

      {/* Nav */}
      <Flex direction="column" gap="3px" mt="12px">
        {nav.map((n) => (
          <NavItem
            key={n.href}
            href={n.href}
            icon={n.icon}
            label={n.label}
            active={router.route === n.route}
          />
        ))}
      </Flex>

      {/* Enabled features */}
      {enabledFeatures.length > 0 && (
        <>
          <Text
            fontSize="10.5px"
            fontWeight="700"
            letterSpacing="0.1em"
            color="TextSecondary"
            m="16px 4px 6px"
          >
            ВКЛЮЧЁННЫЕ ФУНКЦИИ
          </Text>
          <Flex direction="column" gap="1px">
            {enabledFeatures.map((f) => (
              <Flex
                key={f.id}
                as={Link}
                href={`/guilds/${guildId}/features/${f.id}`}
                align="center"
                gap="11px"
                p="8px 11px"
                rounded="11px"
                color="TextSecondary"
                fontWeight="500"
                fontSize="13.5px"
                transition="background .15s ease, color .15s ease"
                _hover={{ bg: 'blackAlpha.50', color: 'TextPrimary', _dark: { bg: 'whiteAlpha.50' } }}
              >
                <Box color="brand.200" display="flex" fontSize="18px">
                  {f.icon}
                </Box>
                {meta.feature(f.id, f.name, '').name}
              </Flex>
            ))}
          </Flex>
        </>
      )}

      <Box flex="1" />

      {/* User card */}
      {user && (
        <Flex
          align="center"
          gap="10px"
          p="10px"
          rounded="12px"
          bg="CardBackground"
          border="1px solid"
          borderColor="CardBorder"
          mt="10px"
        >
          <Box
            as="img"
            src={avatarUrl(user)}
            alt=""
            w="30px"
            h="30px"
            rounded="full"
            objectFit="cover"
            flexShrink={0}
          />
          <Box flex="1" minW={0} lineHeight="1.2">
            <Text fontSize="13px" fontWeight="600" noOfLines={1}>
              {user.username}
            </Text>
            <Text fontSize="11px" color="TextSecondary">
              Администратор
            </Text>
          </Box>
          <Link href="/user/profile" onClick={(e) => e.stopPropagation()}>
            <Icon as={MdSettings} boxSize="18px" color="TextSecondary" _hover={{ color: 'TextPrimary' }} />
          </Link>
        </Flex>
      )}
    </Flex>
  );
}
