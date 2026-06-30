import { Badge, Button, ButtonGroup, Flex, Heading, SimpleGrid, Text } from '@chakra-ui/react';
import { useState } from 'react';
import { FeatureGridSkeleton } from '@/components/feature/FeatureGridSkeleton';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { guild as view } from '@/config/translations/guild';
import { useGuildInfoQuery } from '@/api/hooks';
import { useRouter } from 'next/router';
import { getFeatures } from '@/utils/common';
import { featureCategories } from '@/config/features';
import { Banner } from '@/components/GuildBanner';
import { FeatureItem } from '@/components/feature/FeatureItem';
import { NotJoinedPanel } from '@/components/feature/NotJoinedPanel';
import type { CustomGuildInfo } from '@/config/types/custom-types';
import { NextPageWithLayout } from '@/pages/_app';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';

const GuildPage: NextPageWithLayout = () => {
  const t = view.useTranslations();
  const guild = useRouter().query.guild as string;
  const query = useGuildInfoQuery(guild);

  return (
    <QueryStatus query={query} loading={<FeatureGridSkeleton />} error={t.error.load}>
      {query.data != null ? (
        <GuildPanel guild={guild} info={query.data} />
      ) : (
        <NotJoinedPanel guild={guild} />
      )}
    </QueryStatus>
  );
};

type FeatureFilter = 'all' | 'enabled' | 'disabled';

function GuildPanel({ guild: id, info }: { guild: string; info: CustomGuildInfo }) {
  const t = view.useTranslations();
  const [filter, setFilter] = useState<FeatureFilter>('all');

  const all = getFeatures();
  const enabledSet = new Set(info.enabledFeatures ?? []);
  const enabledCount = all.filter((f) => enabledSet.has(f.id)).length;
  const shown = all.filter((f) => {
    if (filter === 'enabled') return enabledSet.has(f.id);
    if (filter === 'disabled') return !enabledSet.has(f.id);
    return true;
  });

  return (
    <Flex direction="column" gap={5}>
      <Banner />
      <Flex direction="column" gap={4} mt={3}>
        <Flex align="center" justify="space-between" gap={3} wrap="wrap">
          <Flex align="center" gap={3} wrap="wrap">
            <Heading size="md">{t.features}</Heading>
            <Badge colorScheme="green" rounded="md" px={2} py={1} fontSize="0.75em">
              {enabledCount} / {all.length} enabled
            </Badge>
          </Flex>
          <ButtonGroup size="sm" isAttached variant="outline">
            {(['all', 'enabled', 'disabled'] as const).map((key) => (
              <Button
                key={key}
                onClick={() => setFilter(key)}
                textTransform="capitalize"
                {...(filter === key
                  ? { variant: 'solid', colorScheme: 'brand' }
                  : { variant: 'outline' })}
              >
                {key}
              </Button>
            ))}
          </ButtonGroup>
        </Flex>
        {shown.length === 0 ? (
          <Text color="TextSecondary">No {filter} features.</Text>
        ) : (
          <Flex direction="column" gap={6}>
            {featureCategories.map((cat) => {
              const items = shown.filter((f) => f.category === cat.id);
              if (items.length === 0) return null;
              return (
                <Flex key={cat.id} direction="column" gap={3}>
                  <Text
                    fontSize="xs"
                    fontWeight="700"
                    textTransform="uppercase"
                    letterSpacing="wide"
                    color="TextSecondary"
                  >
                    {cat.label}
                  </Text>
                  <SimpleGrid columns={{ base: 1, md: 2, '2xl': 3 }} gap={3}>
                    {items.map((feature) => (
                      <FeatureItem
                        key={feature.id}
                        guild={id}
                        feature={feature}
                        enabled={enabledSet.has(feature.id)}
                      />
                    ))}
                  </SimpleGrid>
                </Flex>
              );
            })}
          </Flex>
        )}
      </Flex>
    </Flex>
  );
}

GuildPage.getLayout = (c) => getGuildLayout({ children: c });
export default GuildPage;
