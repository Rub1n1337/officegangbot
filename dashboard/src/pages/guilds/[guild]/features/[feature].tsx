import { Icon } from '@chakra-ui/react';
import { Center, Heading, Text } from '@chakra-ui/layout';
import { Button } from '@chakra-ui/react';
import { FeatureFormSkeleton } from '@/components/feature/FeatureFormSkeleton';
import { features } from '@/config/features';
import { CustomFeatures, FeatureConfig } from '@/config/types';
import { BsSearch, BsExclamationTriangle } from 'react-icons/bs';
import { useFeatureQuery } from '@/api/hooks';
import { UpdateFeaturePanel } from '@/components/feature/UpdateFeaturePanel';
import { feature as view } from '@/config/translations/feature';
import { useRouter } from 'next/router';
import { NextPageWithLayout } from '@/pages/_app';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';

export type Params = {
  guild: string;
  feature: keyof CustomFeatures;
};

export type UpdateFeatureValue<K extends keyof CustomFeatures> = Partial<CustomFeatures[K]>;

const FeaturePage: NextPageWithLayout = () => {
  const { feature, guild } = useRouter().query as Params;

  const query = useFeatureQuery(guild, feature);
  const featureConfig = features[feature] as FeatureConfig<typeof feature>;
  const skeleton = featureConfig?.useSkeleton?.();

  if (featureConfig == null) return <NotFound />;
  if (query.isLoading) return skeleton != null ? <>{skeleton}</> : <FeatureFormSkeleton />;
  // The feature settings load regardless of enabled state, so an error here means
  // a real failure (bot offline / unreachable / no access) — not "feature off".
  // The disabled state is shown by UpdateFeaturePanel's greyed overlay instead.
  if (query.isError) return <LoadError onRetry={() => query.refetch()} isRetrying={query.isFetching} />;
  return <UpdateFeaturePanel key={feature} feature={query.data} config={featureConfig} />;
};

function LoadError({ onRetry, isRetrying }: { onRetry: () => void; isRetrying: boolean }) {
  return (
    <Center flexDirection="column" gap={2} h="full" textAlign="center" px={4}>
      <Icon as={BsExclamationTriangle} w="44px" h="44px" color="TextSecondary" />
      <Heading size="md">Couldn&apos;t load this feature</Heading>
      <Text color="TextSecondary" maxW="sm">
        The bot may be offline or temporarily unreachable. Please try again in a moment.
      </Text>
      <Button mt={2} variant="action" px={6} onClick={onRetry} isLoading={isRetrying}>
        Retry
      </Button>
    </Center>
  );
}

function NotFound() {
  const t = view.useTranslations();

  return (
    <Center flexDirection="column" gap={2} h="full">
      <Icon as={BsSearch} w="50px" h="50px" />
      <Heading size="lg">{t.error['not found']}</Heading>
      <Text color="TextSecondary">{t.error['not found description']}</Text>
    </Center>
  );
}

FeaturePage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default FeaturePage;
