import { FaChevronLeft as ChevronLeftIcon } from 'react-icons/fa';
import { Flex, HStack, Text, VStack } from '@chakra-ui/layout';
import { Button, Icon, IconButton, Kbd, Spacer } from '@chakra-ui/react';
import { Fragment } from 'react';
import { HSeparator } from '@/components/layout/Separator';
import { getFeatures } from '@/utils/common';
import { featureCategories } from '@/config/features';
import { OPEN_COMMAND_PALETTE } from '@/components/AppChrome';
import { IoStatsChart, IoSearch } from 'react-icons/io5';
import { useGuildPreview } from '@/api/hooks';
import { sidebarBreakpoint } from '@/theme/breakpoints';
import { guild as view } from '@/config/translations/guild';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { Params } from '@/pages/guilds/[guild]/features/[feature]';
import { SidebarItem } from '../sidebar/SidebarItem';

export function InGuildSidebar() {
  const router = useRouter();
  const { guild: guildId, feature: activeId } = router.query as Params;
  const { guild } = useGuildPreview(guildId);

  const t = view.useTranslations();

  return (
    <Flex direction="column" gap={2} p={3}>
      <HStack as={Link} cursor="pointer" mb={2} href={`/guilds/${guildId}`}>
        <IconButton
          display={{ base: 'none', [sidebarBreakpoint]: 'block' }}
          icon={<Icon verticalAlign="middle" as={ChevronLeftIcon} />}
          aria-label="back"
        />
        <Text fontSize="lg" fontWeight="600">
          {guild?.name}
        </Text>
      </HStack>
      <Button
        size="sm"
        variant="outline"
        justifyContent="flex-start"
        leftIcon={<Icon as={IoSearch} />}
        color="TextSecondary"
        fontWeight="500"
        mb={1}
        onClick={() => window.dispatchEvent(new Event(OPEN_COMMAND_PALETTE))}
      >
        Search…
        <Spacer />
        <Kbd>⌘K</Kbd>
      </Button>
      <VStack align="stretch">
        <SidebarItem
          href={`/guilds/${guildId}/settings`}
          active={router.route === `/guilds/[guild]/settings`}
          icon={<Icon as={IoStatsChart} />}
          name={t.bn.settings}
        />
        {featureCategories.map((cat) => {
          const items = getFeatures().filter((f) => f.category === cat.id);
          if (items.length === 0) return null;
          return (
            <Fragment key={cat.id}>
              <HSeparator>{cat.label}</HSeparator>
              {items.map((feature) => (
                <SidebarItem
                  key={feature.id}
                  name={feature.name}
                  icon={feature.icon}
                  active={activeId === feature.id}
                  href={`/guilds/${guildId}/features/${feature.id}`}
                />
              ))}
            </Fragment>
          );
        })}
      </VStack>
    </Flex>
  );
}
