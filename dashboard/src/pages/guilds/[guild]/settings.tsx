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
  Progress,
  SkeletonText,
  Spacer,
  Text,
  usePrefersReducedMotion,
  useToast,
  useToken,
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { StyledChart } from '@/components/chart/StyledChart';
import {
  MdPeople,
  MdTag,
  MdMic,
  MdShield,
  MdSpeed,
  MdToggleOn,
  MdDownload,
  MdUpload,
} from 'react-icons/md';
import { FaCrown } from 'react-icons/fa';
import { IoCheckmarkCircle, IoArrowForward } from 'react-icons/io5';
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
import type { CustomFeatures, GuildStats, GuildStatsTopXp } from '@/config/types/custom-types';

function StatCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <Flex bg="CardBackground" rounded="2xl" p={5} direction="column" gap={2}>
      <Flex align="center" gap={2} color="TextSecondary">
        {icon}
        <Text fontSize="sm">{label}</Text>
      </Flex>
      <Text fontSize="3xl" fontWeight="700" lineHeight="1.1">
        {value}
      </Text>
      {hint && (
        <Text fontSize="xs" color="TextSecondary">
          {hint}
        </Text>
      )}
    </Flex>
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

function Overview({ stats }: { stats: GuildStats }) {
  return (
    <Flex direction="column" gap={4}>
      <SimpleGrid columns={{ base: 1, sm: 2, lg: 3 }} gap={3}>
        <StatCard
          icon={<Icon as={MdPeople} />}
          label="Members"
          value={stats.member_count.toLocaleString()}
        />
        <StatCard
          icon={<Icon as={MdTag} />}
          label="Text channels"
          value={stats.text_channels}
          hint={`${stats.channel_count} channels total`}
        />
        <StatCard
          icon={<Icon as={MdMic} />}
          label="Voice channels"
          value={stats.voice_channels}
        />
        <StatCard icon={<Icon as={MdShield} />} label="Roles" value={stats.role_count} />
        <StatCard
          icon={<Icon as={MdToggleOn} />}
          label="Enabled features"
          value={stats.enabled_feature_count}
        />
        <StatCard
          icon={<Icon as={MdSpeed} />}
          label="Bot latency"
          value={`${Math.round(stats.latency_ms)} ms`}
        />
      </SimpleGrid>
      <TopXp rows={stats.top_xp} />
    </Flex>
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
// checklist shouldn't push admins to enable all of them.
const CORE_SETUP_FEATURES = ['moderation', 'logging', 'automod', 'welcome-message'];

// A gentle setup nudge over the core features only, ticked off once enabled.
// Hidden when the essentials are configured, or dismissed (per guild, sticky).
function OnboardingChecklist({ guild, enabledFeatures }: { guild: string; enabledFeatures: string[] }) {
  const all = getFeatures().filter((f) => CORE_SETUP_FEATURES.includes(f.id));
  const enabled = new Set(enabledFeatures);
  const done = all.filter((f) => enabled.has(f.id)).length;

  // Dismissal is per guild and read after mount (localStorage isn't available
  // during SSR; the brief flash is acceptable for a dismissable banner).
  const dismissKey = `onboarding-hidden-${guild}`;
  const [hidden, setHidden] = useState(true);
  useEffect(() => {
    setHidden(localStorage.getItem(dismissKey) === '1');
  }, [dismissKey]);

  if (hidden || done === all.length) return null;

  const pct = Math.round((done / all.length) * 100);

  return (
    <Box bg="CardBackground" rounded="2xl" p={5}>
      <Flex align="center" justify="space-between" gap={3} mb={2} wrap="wrap">
        <Heading size="sm">Finish setting up</Heading>
        <Flex align="center" gap={3}>
          <Text fontSize="sm" color="TextSecondary">
            {done} / {all.length} configured
          </Text>
          <Button
            size="xs"
            variant="ghost"
            onClick={() => {
              localStorage.setItem(dismissKey, '1');
              setHidden(true);
            }}
          >
            Hide
          </Button>
        </Flex>
      </Flex>
      <Progress value={pct} size="sm" rounded="full" colorScheme="brand" mb={4} />
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={2}>
        {all.map((feature) => {
          const isDone = enabled.has(feature.id);
          return (
            <Flex
              key={feature.id}
              as={Link}
              href={`/guilds/${guild}/features/${feature.id}`}
              align="center"
              gap={3}
              px={3}
              py={2.5}
              rounded="xl"
              bg="blackAlpha.200"
              _dark={{ bg: 'whiteAlpha.50' }}
              _hover={{ bg: 'blackAlpha.300', _dark: { bg: 'whiteAlpha.100' } }}
              opacity={isDone ? 0.65 : 1}
            >
              {isDone ? (
                <Icon as={IoCheckmarkCircle} color="green.400" boxSize={5} />
              ) : (
                <Box color="Brand" display="flex">
                  {feature.icon}
                </Box>
              )}
              <Text
                flex={1}
                fontWeight={isDone ? '400' : '600'}
                textDecoration={isDone ? 'line-through' : 'none'}
                isTruncated
              >
                {feature.name}
              </Text>
              {!isDone && <Icon as={IoArrowForward} color="TextSecondary" />}
            </Flex>
          );
        })}
      </SimpleGrid>
    </Box>
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

  return (
    <Flex direction="column" gap={5}>
      <Flex align="center" gap={3} wrap="wrap">
        <Heading fontSize="2xl" fontWeight="600">
          Overview
        </Heading>
        {statsQuery.data?.online ? (
          <LiveIndicator updatedAt={statsQuery.dataUpdatedAt} />
        ) : statsQuery.data ? (
          <Badge colorScheme="red" rounded="md" px={2}>
            Bot offline
          </Badge>
        ) : null}
        <Spacer />
        {infoQuery.data && <BotLanguage guild={guild} locale={infoQuery.data.locale ?? 'en'} />}
      </Flex>
      {infoQuery.data && (
        <OnboardingChecklist
          guild={guild}
          enabledFeatures={infoQuery.data.enabledFeatures ?? []}
        />
      )}
      <QueryStatus query={statsQuery} loading={<OverviewSkeleton />} error="Failed to load guild stats.">
        {statsQuery.data && <Overview stats={statsQuery.data} />}
      </QueryStatus>
      <ConfigTransfer guild={guild} />
    </Flex>
  );
};

GuildOverviewPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default GuildOverviewPage;
