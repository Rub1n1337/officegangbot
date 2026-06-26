import { Flex, Heading, SimpleGrid } from '@chakra-ui/react';
import { LoadingPanel } from '@/components/panel/LoadingPanel';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { guild as view } from '@/config/translations/guild';
import { useGuildInfoQuery } from '@/api/hooks';
import { useRouter } from 'next/router';
import { getFeatures } from '@/utils/common';
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
    <QueryStatus query={query} loading={<LoadingPanel />} error={t.error.load}>
      {query.data != null ? (
        <GuildPanel guild={guild} info={query.data} />
      ) : (
        <NotJoinedPanel guild={guild} />
      )}
    </QueryStatus>
  );
};

function GuildPanel({ guild: id, info }: { guild: string; info: CustomGuildInfo }) {
  const t = view.useTranslations();

  return (
    <Flex direction="column" gap={5}>
      <Banner />
      <Flex direction="column" gap={5} mt={3}>
        <Heading size="md">{t.features}</Heading>
        <SimpleGrid columns={{ base: 1, md: 2, '2xl': 3 }} gap={3}>
          {getFeatures().map((feature) => (
            <FeatureItem
              key={feature.id}
              guild={id}
              feature={feature}
              enabled={(info.enabledFeatures ?? []).includes(feature.id)}
            />
          ))}
        </SimpleGrid>
      </Flex>
    </Flex>
  );
}

GuildPage.getLayout = (c) => getGuildLayout({ children: c });
export default GuildPage;
