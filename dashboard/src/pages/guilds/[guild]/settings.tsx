import {
  Badge,
  Box,
  Button,
  ButtonGroup,
  Flex,
  Heading,
  Icon,
  SimpleGrid,
  Skeleton,
  SkeletonText,
  Spacer,
  Text,
  usePrefersReducedMotion,
  useToast,
  useToken,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { StyledChart } from '@/components/chart/StyledChart';
import { MdBolt, MdTune, MdAdd, MdArrowForward, MdDownload, MdUpload } from 'react-icons/md';
import { FaCrown } from 'react-icons/fa';
import { ReactNode, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { client, useGuildInfoQuery, useGuildStatsQuery, useSetLocaleMutation } from '@/api/hooks';
import { getFeature, updateFeature } from '@/api/bot';
import { useSession } from '@/utils/auth/hooks';
import { buildExport, parseImport, TRANSFER_FEATURES } from '@/utils/config-transfer';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { NotJoinedPanel } from '@/components/feature/NotJoinedPanel';
import { getFeatures } from '@/utils/common';
import { featureCategories } from '@/config/features';
import { useFeatureMeta } from '@/config/feature-meta';
import type { CustomFeatures, GuildStats, GuildStatsTopXp } from '@/config/types/custom-types';

// Iris metric card: label, big value, optional hint. Soft surface with a
// hover lift, matching the mockup's overview stat tiles.
function IrisStat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Box
      bg="CardBackground"
      border="1px solid"
      borderColor="CardBorder"
      rounded="16px"
      p="16px"
      boxShadow="normal"
      transition="transform .18s ease, border-color .18s ease"
      _hover={{ transform: 'translateY(-4px)', borderColor: 'brand.400' }}
    >
      <Text fontSize="12px" color="TextSecondary" fontWeight="500">
        {label}
      </Text>
      <Text fontSize="27px" fontWeight="800" letterSpacing="-0.02em" lineHeight="1" mt="9px">
        {value}
      </Text>
      {hint && (
        <Text fontSize="11px" color="TextSecondary" mt="6px">
          {hint}
        </Text>
      )}
    </Box>
  );
}

function XpBarChart({ rows }: { rows: GuildStatsTopXp[] }) {
  const medals = ['🥇', '🥈', '🥉'];
  const [brand] = useToken('colors', ['brand.500']);

  const series = [{ name: 'XP', data: rows.map((r) => r.xp) }];
  const options: ApexCharts.ApexOptions = {
    chart: { type: 'bar', sparkline: { enabled: false } },
    colors: [brand],
    plotOptions: {
      bar: { horizontal: true, borderRadius: 6, barHeight: '68%' },
    },
    dataLabels: {
      enabled: true,
      // Show the member's level inside the bar; the bar length is their XP.
      formatter: (_val, opts) => `Lvl ${rows[opts.dataPointIndex].level}`,
      style: { colors: ['#fff'], fontWeight: '700' },
    },
    xaxis: {
      categories: rows.map((r, i) => `${medals[i] ?? `#${i + 1}`} ${r.name}`),
    },
    tooltip: {
      y: { formatter: (val: number) => `${val.toLocaleString()} XP` },
    },
  };

  return (
    <StyledChart
      type="bar"
      series={series}
      options={options}
      height={Math.max(160, rows.length * 46)}
    />
  );
}

function TopXp({ rows }: { rows: GuildStatsTopXp[] }) {
  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Flex align="center" gap={2} mb={4}>
        <Icon as={FaCrown} color="Brand" />
        <Heading size="sm">Top members by XP</Heading>
      </Flex>
      {rows.length === 0 ? (
        <Text fontSize="sm" color="TextSecondary">
          No XP data yet. Enable the Levels feature and let members chat to populate the leaderboard.
        </Text>
      ) : (
        <XpBarChart rows={rows} />
      )}
    </Box>
  );
}

function OverviewMetrics({ stats }: { stats: GuildStats }) {
  return (
    <Box
      display="grid"
      gridTemplateColumns="repeat(auto-fit, minmax(200px, 1fr))"
      gap="16px"
    >
      <IrisStat label="Участников" value={stats.member_count.toLocaleString('ru-RU')} />
      <IrisStat
        label="Каналов"
        value={stats.channel_count}
        hint={`${stats.text_channels} текстовых · ${stats.voice_channels} голосовых`}
      />
      <IrisStat label="Ролей" value={stats.role_count} />
      <IrisStat label="Функций включено" value={stats.enabled_feature_count} />
      <IrisStat label="Задержка бота" value={`${Math.round(stats.latency_ms)} мс`} />
    </Box>
  );
}

function OverviewSkeleton() {
  return (
    <Flex direction="column" gap={4}>
      <SimpleGrid columns={{ base: 1, sm: 2, lg: 3 }} gap={3}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Box key={i} bg="CardBackground" rounded="2xl" p={5}>
            <Skeleton h="14px" w="55%" mb={3} rounded="md" />
            <Skeleton h="28px" w="40%" rounded="md" />
          </Box>
        ))}
      </SimpleGrid>
      <Box bg="CardBackground" rounded="2xl" p={5}>
        <Skeleton h="16px" w="40%" mb={4} rounded="md" />
        <SkeletonText noOfLines={3} spacing={3} skeletonHeight={3} />
      </Box>
    </Flex>
  );
}

const pulse = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.7); }
  70% { box-shadow: 0 0 0 7px rgba(72, 187, 120, 0); }
  100% { box-shadow: 0 0 0 0 rgba(72, 187, 120, 0); }
`;

// Live indicator: a pulsing dot + a ticking "updated Ns ago", driven by the
// stats query's auto-refetch (every 8s).
function LiveIndicator({ updatedAt }: { updatedAt: number }) {
  const [, setTick] = useState(0);
  const reduceMotion = usePrefersReducedMotion();
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const secs = updatedAt ? Math.max(0, Math.round((Date.now() - updatedAt) / 1000)) : 0;
  return (
    <Flex align="center" gap={2}>
      <Box
        w="9px"
        h="9px"
        rounded="full"
        bg="green.400"
        animation={reduceMotion ? undefined : `${pulse} 2s infinite`}
      />
      <Text fontSize="sm" fontWeight="700" color="green.400" letterSpacing="wide">
        LIVE
      </Text>
      <Text fontSize="xs" color="TextSecondary">
        updated {secs}s ago
      </Text>
    </Flex>
  );
}

// The setup essentials — every feature beyond these is optional, so the
// banner only nudges on these.
const CORE_SETUP_FEATURES = ['moderation', 'logging', 'automod', 'welcome-message'];
const GRADIENT = 'linear(135deg, #8B7CFF, #6E56F5)';

// Iris highlight banner: a setup nudge while core features are missing, a
// positive note once they're all on.
function HighlightBanner({ guild, enabledFeatures }: { guild: string; enabledFeatures: string[] }) {
  const enabled = new Set(enabledFeatures);
  const core = getFeatures().filter((f) => CORE_SETUP_FEATURES.includes(f.id));
  const missing = core.filter((f) => !enabled.has(f.id));
  const allDone = missing.length === 0;
  const target = allDone
    ? `/guilds/${guild}/analytics`
    : `/guilds/${guild}/features/${missing[0].id}`;

  return (
    <Flex
      align="center"
      gap="16px"
      bgGradient="linear(90deg, var(--chakra-colors-brandAlpha-100), transparent)"
      border="1px solid"
      borderColor="brandAlpha.100"
      rounded="16px"
      p="16px 20px"
    >
      <Flex w="42px" h="42px" rounded="12px" bg="brandAlpha.100" align="center" justify="center" flexShrink={0}>
        <Icon as={MdBolt} boxSize="22px" color="brand.200" />
      </Flex>
      <Box flex="1" minW={0}>
        <Text fontSize="14.5px" fontWeight="700">
          {allDone
            ? 'Базовые функции настроены'
            : `Базовая настройка: ${core.length - missing.length} из ${core.length}`}
        </Text>
        <Text fontSize="13px" color="TextSecondary" mt="2px">
          {allDone
            ? 'Загляни в аналитику или добавь новые функции ниже.'
            : 'Включи ключевые функции, чтобы бот заработал в полную силу.'}
        </Text>
      </Box>
      <Button
        as={Link}
        href={target}
        flexShrink={0}
        rounded="11px"
        px="16px"
        h="40px"
        color="white"
        bgGradient={GRADIENT}
        boxShadow="0 8px 20px -8px rgba(110,86,245,.7)"
        _hover={{ filter: 'brightness(1.08)' }}
        rightIcon={<Icon as={MdArrowForward} boxSize="17px" />}
      >
        {allDone ? 'Аналитика' : 'Продолжить'}
      </Button>
    </Flex>
  );
}

// One feature card in the overview grid: gradient icon + green dot when on,
// accent-soft icon when off; a Настроить (on) / Включить (off) action that
// opens the feature's config page.
function FeatureCard({
  guild,
  feature,
  on,
  meta,
}: {
  guild: string;
  feature: ReturnType<typeof getFeatures>[number];
  on: boolean;
  meta: ReturnType<typeof useFeatureMeta>;
}) {
  const m = meta.feature(feature.id, feature.name, feature.description);
  return (
    <Flex
      direction="column"
      gap="12px"
      bg="CardBackground"
      border="1px solid"
      borderColor="CardBorder"
      rounded="16px"
      p="16px"
      boxShadow="normal"
      transition="transform .18s ease, border-color .18s ease"
      _hover={{ transform: 'translateY(-4px)', borderColor: 'brand.400' }}
    >
      <Flex align="flex-start" gap="12px">
        <Flex
          w="42px"
          h="42px"
          rounded="12px"
          align="center"
          justify="center"
          flexShrink={0}
          fontSize="22px"
          color={on ? 'white' : 'brand.200'}
          {...(on ? { bgGradient: GRADIENT } : { bg: 'brandAlpha.100' })}
        >
          {feature.icon}
        </Flex>
        <Box flex="1" minW={0}>
          <Flex align="center" gap="7px">
            <Text fontWeight="600" fontSize="14.5px">
              {m.name}
            </Text>
            {on && <Box w="7px" h="7px" rounded="full" bg="green.400" flexShrink={0} />}
          </Flex>
          <Text fontSize="12.5px" color="TextSecondary" mt="4px" lineHeight="1.4" noOfLines={2}>
            {m.description}
          </Text>
        </Box>
      </Flex>
      <Flex justify="flex-end">
        {on ? (
          <Button
            as={Link}
            href={`/guilds/${guild}/features/${feature.id}`}
            size="sm"
            variant="outline"
            rounded="10px"
            leftIcon={<Icon as={MdTune} boxSize="16px" />}
          >
            Настроить
          </Button>
        ) : (
          <Button
            as={Link}
            href={`/guilds/${guild}/features/${feature.id}`}
            size="sm"
            rounded="10px"
            color="white"
            bgGradient={GRADIENT}
            boxShadow="0 6px 16px -7px rgba(110,86,245,.7)"
            _hover={{ filter: 'brightness(1.08)' }}
            leftIcon={<Icon as={MdAdd} boxSize="16px" />}
          >
            Включить
          </Button>
        )}
      </Flex>
    </Flex>
  );
}

// The features grid, grouped by category, with all / enabled / disabled pills.
function FeaturesSection({ guild, enabledFeatures }: { guild: string; enabledFeatures: string[] }) {
  const enabled = new Set(enabledFeatures);
  const meta = useFeatureMeta();
  const [filter, setFilter] = useState<'all' | 'on' | 'off'>('all');
  const all = getFeatures();
  const enabledCount = all.filter((f) => enabled.has(f.id)).length;
  const pass = (id: string) =>
    filter === 'all' ? true : filter === 'on' ? enabled.has(id) : !enabled.has(id);
  const pills: { k: 'all' | 'on' | 'off'; label: string }[] = [
    { k: 'all', label: 'Все' },
    { k: 'on', label: 'Включённые' },
    { k: 'off', label: 'Выключенные' },
  ];

  return (
    <Flex direction="column" gap="14px">
      <Flex align="center" justify="space-between" wrap="wrap" gap="12px">
        <Flex align="center" gap="11px">
          <Heading fontSize="18px" fontWeight="700">
            Функции
          </Heading>
          <Badge color="green.500" bg="green.100" _dark={{ bg: 'whiteAlpha.100', color: 'green.400' }} rounded="20px" px="10px" py="3px" fontSize="12px">
            {enabledCount} включено
          </Badge>
        </Flex>
        <Flex bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="11px" p="3px" gap="2px">
          {pills.map((p) => (
            <Button
              key={p.k}
              size="sm"
              rounded="8px"
              fontSize="13px"
              fontWeight={filter === p.k ? '600' : '500'}
              onClick={() => setFilter(p.k)}
              {...(filter === p.k
                ? { color: 'white', bg: 'Brand' }
                : { variant: 'ghost', color: 'TextSecondary' })}
            >
              {p.label}
            </Button>
          ))}
        </Flex>
      </Flex>
      {featureCategories.map((cat) => {
        const items = all.filter((f) => f.category === cat.id && pass(f.id));
        if (items.length === 0) return null;
        return (
          <Flex key={cat.id} direction="column" gap="14px">
            <Text fontSize="11px" fontWeight="700" letterSpacing="0.08em" color="TextSecondary" textTransform="uppercase">
              {meta.category(cat.id, cat.label)}
            </Text>
            <Box display="grid" gridTemplateColumns="repeat(auto-fill, minmax(290px, 1fr))" gap="14px">
              {items.map((f) => (
                <FeatureCard key={f.id} guild={guild} feature={f} on={enabled.has(f.id)} meta={meta} />
              ))}
            </Box>
          </Flex>
        );
      })}
    </Flex>
  );
}

// Sets the language the *bot* speaks in this server (its Discord replies),
// not the dashboard UI language.
function BotLanguage({ guild, locale }: { guild: string; locale: string }) {
  const mutation = useSetLocaleMutation();
  const current = locale === 'ru' ? 'ru' : 'en';
  return (
    <Flex align="center" gap={2}>
      <Text fontSize="xs" color="TextSecondary">
        Bot language
      </Text>
      <ButtonGroup size="sm" isAttached variant="outline" isDisabled={mutation.isLoading}>
        {(['en', 'ru'] as const).map((l) => (
          <Button
            key={l}
            onClick={() => current !== l && mutation.mutate({ guild, locale: l })}
            textTransform="uppercase"
            {...(current === l
              ? { variant: 'solid', colorScheme: 'brand' }
              : { variant: 'outline' })}
          >
            {l}
          </Button>
        ))}
      </ButtonGroup>
    </Flex>
  );
}

// Export / import of *portable* settings (texts, thresholds, toggles, AutoMod
// rules). Channel/role assignments never transfer — on import the portable
// subset is merged over this guild's current config and saved through the
// normal validated update path, so ids stay untouched.
function ConfigTransfer({ guild }: { guild: string }) {
  const { session } = useSession();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<'export' | 'import' | null>(null);

  const notify = (title: string, status: 'success' | 'error' | 'warning') =>
    toast({ title, status, duration: 5000, isClosable: true, position: 'bottom-right' });

  const doExport = async () => {
    if (!session) return;
    setBusy('export');
    try {
      const entries = await Promise.all(
        TRANSFER_FEATURES.map(async (f) => [
          f,
          await getFeature(session, guild, f as keyof CustomFeatures),
        ] as const)
      );
      const payloads = Object.fromEntries(entries) as Record<string, Record<string, unknown>>;
      const file = buildExport(payloads);
      const blob = new Blob([JSON.stringify(file, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `officegangbot-config-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      notify('Export failed — try again.', 'error');
    } finally {
      setBusy(null);
    }
  };

  const doImport = async (text: string) => {
    if (!session) return;
    const parsed = parseImport(text);
    if (!parsed.ok) {
      notify(parsed.error, 'error');
      return;
    }
    const names = Object.keys(parsed.features).join(', ');
    if (!window.confirm(`Import settings for: ${names}?\nChannel/role assignments are not affected.`)) {
      return;
    }
    setBusy('import');
    const failed: string[] = [];
    for (const [feature, subset] of Object.entries(parsed.features)) {
      try {
        // Merge over the guild's current payload so id fields (channels, roles,
        // exemptions) are preserved exactly as they are.
        const current = await getFeature(session, guild, feature as keyof CustomFeatures);
        await updateFeature(
          session,
          guild,
          feature as keyof CustomFeatures,
          JSON.stringify({ ...(current as Record<string, unknown>), ...subset })
        );
      } catch {
        failed.push(feature);
      }
    }
    client.invalidateQueries(['feature', guild]);
    if (failed.length === 0) {
      notify(`Imported: ${names}.`, 'success');
    } else {
      notify(`Imported with errors — failed: ${failed.join(', ')}.`, 'warning');
    }
    setBusy(null);
  };

  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Heading size="sm">Config export / import</Heading>
      <Text fontSize="sm" color="TextSecondary" mt={1} mb={4}>
        Transfers texts, thresholds, toggles and AutoMod rules between servers. Channel and role
        assignments are never included — they don’t exist on another server.
      </Text>
      <Flex gap={3} wrap="wrap">
        <Button
          size="sm"
          variant="outline"
          leftIcon={<Icon as={MdDownload} />}
          isLoading={busy === 'export'}
          isDisabled={busy != null}
          onClick={doExport}
        >
          Export JSON
        </Button>
        <Button
          size="sm"
          variant="outline"
          leftIcon={<Icon as={MdUpload} />}
          isLoading={busy === 'import'}
          isDisabled={busy != null}
          onClick={() => fileRef.current?.click()}
        >
          Import JSON
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={async (e) => {
            const f = e.target.files?.[0];
            e.target.value = '';
            if (f) await doImport(await f.text());
          }}
        />
      </Flex>
    </Box>
  );
}

const GuildOverviewPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const infoQuery = useGuildInfoQuery(guild);
  const statsQuery = useGuildStatsQuery(guild);

  // Bot isn't a member of this guild — show a friendly invite prompt instead of
  // a raw stats error.
  if (infoQuery.isSuccess && infoQuery.data == null) {
    return <NotJoinedPanel guild={guild} />;
  }

  const enabledFeatures = infoQuery.data?.enabledFeatures ?? [];

  return (
    <Flex direction="column" gap="22px">
      <Flex align="flex-end" justify="space-between" gap="12px" wrap="wrap">
        <Box>
          <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
            ОБЗОР
          </Text>
          <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt="3px">
            Здоровье сервера
          </Heading>
          <Text fontSize="13.5px" color="TextSecondary" mt="4px">
            Ключевые метрики и функции бота — на одном экране.
          </Text>
        </Box>
        <Flex align="center" gap={3}>
          {statsQuery.data?.online ? (
            <LiveIndicator updatedAt={statsQuery.dataUpdatedAt} />
          ) : statsQuery.data ? (
            <Badge colorScheme="red" rounded="md" px={2}>
              Бот офлайн
            </Badge>
          ) : null}
          {infoQuery.data && <BotLanguage guild={guild} locale={infoQuery.data.locale ?? 'en'} />}
        </Flex>
      </Flex>

      <QueryStatus query={statsQuery} loading={<OverviewSkeleton />} error="Failed to load guild stats.">
        {statsQuery.data && <OverviewMetrics stats={statsQuery.data} />}
      </QueryStatus>

      {infoQuery.data && <HighlightBanner guild={guild} enabledFeatures={enabledFeatures} />}
      {infoQuery.data && <FeaturesSection guild={guild} enabledFeatures={enabledFeatures} />}

      {statsQuery.data && statsQuery.data.top_xp.length > 0 && <TopXp rows={statsQuery.data.top_xp} />}
      <ConfigTransfer guild={guild} />
    </Flex>
  );
};

GuildOverviewPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default GuildOverviewPage;
