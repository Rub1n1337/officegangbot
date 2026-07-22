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
import { useGuildInfoQuery, useGuildStatsQuery, useSelfUserQuery } from '@/api/hooks';
import { getFeatures } from '@/utils/common';
import { useFeatureMeta } from '@/config/feature-meta';
import { guild as view } from '@/config/translations/guild';
import { useText } from '@/config/translations/ui-text';
import { OPEN_COMMAND_PALETTE } from '@/components/AppChrome';
import { useGuildId } from '@/utils/useGuildId';

// Iris sidebar surfaces (from the Claude Design mockup): a slightly-darker
// panel than the cards on dark, plain white on light.
//
// Grid-refactor pilot: spacing uses the 4px scale tokens (2.5 = 10px is a
// legitimate half-step), and text uses the theme textStyles instead of raw px.
// Element sizes, radii and the accent-bar insets are left as px — they're not
// gutters.
const SIDEBAR_BG = { base: 'white', _dark: '#0D0D18' };

function NavItem({
  href,
  icon,
  label,
  active,
  badge,
}: {
  href?: string;
  icon: IconType;
  label: ReactNode;
  active: boolean;
  badge?: number;
}) {
  return (
    <Flex
      {...(href ? ({ as: Link, href } as object) : {})}
      cursor={href ? 'pointer' : 'default'}
      align="center"
      gap={3}
      px={3}
      py={2.5}
      rounded="12px"
      position="relative"
      textStyle="body"
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
      {badge != null && badge > 0 && (
        <Box
          as="span"
          ml="auto"
          textStyle="micro"
          fontWeight="700"
          rounded="20px"
          px={2}
          py="1px"
          color="brand.200"
          bg="brandAlpha.100"
        >
          {badge}
        </Box>
      )}
    </Flex>
  );
}

export function IrisSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const router = useRouter();
  // From the URL path, so it's correct on the very first render — building
  // these from router.query minted /guilds/undefined/... links during
  // hydration, and an early click navigated there for real.
  const guildId = useGuildId();
  const info = useGuildInfoQuery(guildId ?? '');
  const user = useSelfUserQuery().data;
  const t = view.useTranslations();
  const tt = useText();
  const meta = useFeatureMeta();

  const enabled = new Set(info.data?.enabledFeatures ?? []);
  const enabledFeatures = getFeatures().filter((f) => enabled.has(f.id));

  // Mockup order: Overview, Moderation, Members, Tickets, Audit Log, Analytics.
  // The Tickets badge shows open tickets from the stats query the header
  // already polls — same react-query key, so no extra RPC from here.
  const openTickets = useGuildStatsQuery(guildId ?? '').data?.open_tickets ?? 0;
  // While the id is unknown (build-time render) the items carry no href and
  // render non-clickable, so an early click does nothing instead of navigating
  // to a bogus URL.
  const nav = [
    { href: guildId && `/guilds/${guildId}/settings`, icon: MdSpaceDashboard, label: t.bn.settings, route: '/guilds/[guild]/settings' },
    { href: guildId && `/guilds/${guildId}/moderation`, icon: MdGavel, label: t.bn.moderation, route: '/guilds/[guild]/moderation' },
    { href: guildId && `/guilds/${guildId}/members`, icon: MdPeople, label: t.bn.members, route: '/guilds/[guild]/members' },
    { href: guildId && `/guilds/${guildId}/tickets`, icon: MdConfirmationNumber, label: t.bn.tickets, route: '/guilds/[guild]/tickets', badge: openTickets },
    { href: guildId && `/guilds/${guildId}/audit`, icon: MdHistory, label: t.bn.audit, route: '/guilds/[guild]/audit' },
    { href: guildId && `/guilds/${guildId}/analytics`, icon: MdInsights, label: t.bn.analytics, route: '/guilds/[guild]/analytics' },
  ];

  return (
    <Flex
      direction="column"
      gap={1}
      h="100%"
      px={4}
      py={5}
      overflowY="auto"
      bg={SIDEBAR_BG.base}
      _dark={{ bg: SIDEBAR_BG._dark }}
      borderRight="1px solid"
      borderColor="CardBorder"
      onClick={onNavigate}
    >
      {/* Brand → the public landing (the universal "home" affordance; it was a
          dead, unclickable logo before). */}
      <Flex as={Link} href="/" align="center" gap={3} px={2} pt={2} pb={4} _hover={{ opacity: 0.85 }}>
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
          <Text textStyle="h3" letterSpacing="-0.01em">
            OfficeGangBot
          </Text>
          <Text textStyle="micro" color="TextSecondary">
            {tt('Панель управления')}
          </Text>
        </Box>
      </Flex>

      {/* Server switcher → opens the server picker popover */}
      <ServerPicker guildId={guildId ?? ''} />

      {/* Search */}
      <Flex
        as="button"
        align="center"
        gap={2}
        px={3}
        py={2}
        rounded="12px"
        border="1px solid"
        borderColor="CardBorder"
        color="TextSecondary"
        textStyle="body"
        mt={0.5}
        transition="background .15s ease"
        _hover={{ bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
        onClick={(e) => {
          e.stopPropagation();
          window.dispatchEvent(new Event(OPEN_COMMAND_PALETTE));
        }}
      >
        <Icon as={MdSearch} boxSize="18px" />
        {tt('Поиск…')}
        <Box
          as="span"
          ml="auto"
          textStyle="micro"
          border="1px solid"
          borderColor="CardBorder"
          rounded="6px"
          px={2}
        >
          ⌘K
        </Box>
      </Flex>

      {/* Nav */}
      <Flex direction="column" gap={1} mt={3}>
        {nav.map((n) => (
          <NavItem
            key={n.href}
            href={n.href}
            icon={n.icon}
            label={n.label}
            badge={'badge' in n ? n.badge : undefined}
            active={router.route === n.route}
          />
        ))}
      </Flex>

      {/* Enabled features */}
      {enabledFeatures.length > 0 && (
        <>
          <Text textStyle="overline" color="TextSecondary" mt={4} mx={1} mb={2}>
            {tt('ВКЛЮЧЁННЫЕ ФУНКЦИИ')}
          </Text>
          <Flex direction="column" gap="1px">
            {enabledFeatures.map((f) => (
              <Flex
                key={f.id}
                as={Link}
                href={`/guilds/${guildId}/features/${f.id}`}
                align="center"
                // Same icon box (20px) and gap (12px) as the nav items above, so
                // the icon and the text columns line up down the whole sidebar
                // instead of the feature rows sitting to the left.
                gap={3}
                px={3}
                py={2}
                rounded="11px"
                color="TextSecondary"
                textStyle="body"
                fontWeight="500"
                transition="background .15s ease, color .15s ease"
                _hover={{ bg: 'blackAlpha.50', color: 'TextPrimary', _dark: { bg: 'whiteAlpha.50' } }}
              >
                <Box color="brand.200" display="flex" fontSize="20px">
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
          gap={2.5}
          p={2.5}
          rounded="12px"
          bg="CardBackground"
          border="1px solid"
          borderColor="CardBorder"
          mt={2.5}
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
            <Text textStyle="body" fontWeight="600" noOfLines={1}>
              {user.username}
            </Text>
            <Text textStyle="micro" color="TextSecondary">
              {tt('Администратор')}
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
