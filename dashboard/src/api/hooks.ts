import { CustomFeatures, CustomGuildInfo } from '../config/types';
import { QueryClient, onlineManager, useMutation, useQuery } from '@tanstack/react-query';
import { Guild, UserInfo, getGuild, getGuilds, fetchUserInfo } from '@/api/discord';
import {
  deleteWarning,
  setBanAppeals,
  decideBanAppeal,
  fetchAnalytics,
  fetchAudit,
  disableFeature,
  enableFeature,
  fetchGuildChannels,
  fetchGuildEmojis,
  fetchGuildInfo,
  fetchGuildRoles,
  fetchGuildStats,
  fetchMemberDetail,
  fetchModeration,
  fetchTickets,
  searchTickets,
  fetchTicketTranscript,
  getFeature,
  moderateMember,
  searchMembers,
  setGuildLocale,
  updateFeature,
} from '@/api/bot';
import type { ModeratePayload } from '@/api/bot';
import { GuildInfo } from '@/config/types';
import type {
  AnalyticsData,
  AuditEntry,
  MemberDetail,
  MemberSearchItem,
  ModerationData,
  Ticket,
  TicketDetail,
} from '@/config/types/custom-types';
import { useAccessToken, useSession } from '@/utils/auth/hooks';
import { useToast } from '@chakra-ui/react';

// Exponential backoff (1s, 2s, 4s … capped at 8s) so a query that failed while
// the bot was restarting retries a few times and recovers on its own instead of
// stranding the user on an error screen until they hit "Try again".
const retryDelay = (attempt: number) => Math.min(1000 * 2 ** attempt, 8000);

export const client = new QueryClient({
  defaultOptions: {
    mutations: {
      retry: 0,
      // Always attempt the request instead of pausing when React Query's
      // onlineManager thinks we're offline (see queries.networkMode below).
      networkMode: 'always',
    },
    queries: {
      refetchOnWindowFocus: false,
      // Reconnecting to the network (or the bot coming back) refetches stale data.
      refetchOnReconnect: true,
      staleTime: Infinity,
      retry: 2,
      retryDelay,
      // Default 'online' mode pauses a query's retry (fetchStatus 'paused') when
      // the onlineManager reports offline. On this always-online app that flag can
      // fall out of sync (esp. after a transient 502 during the page-load burst),
      // leaving the query stuck in 'loading'/'paused' forever — the feature form
      // then shows its skeleton indefinitely with no error. 'always' never pauses:
      // a failed request retries and then either succeeds or surfaces the error
      // panel (with a Try again button) instead of hanging.
      networkMode: 'always',
    },
  },
});

// React Query can still leave a query stuck in fetchStatus:'paused' after a
// transient failure when its online detection is out of sync (this app is always
// online, but navigator.onLine / the online manager can read false-offline in
// some proxied/embedded contexts). A paused query never resolves, so the feature
// form hangs on its skeleton forever — even networkMode:'always' didn't reliably
// prevent it in practice. Force the online manager to always-online, and as a
// safety net reset any query that still ends up paused so it refetches (verified
// to recover a stuck feature query) instead of hanging.
if (typeof window !== 'undefined') {
  onlineManager.setEventListener(() => () => {});
  onlineManager.setOnline(true);

  const resumeGuard = new WeakSet<object>();
  client.getQueryCache().subscribe((event) => {
    const query = event?.query;
    if (!query || query.state.fetchStatus !== 'paused' || query.getObserversCount() === 0) return;
    // Guard so a genuinely-failing request retries at most every few seconds
    // rather than looping tightly.
    if (resumeGuard.has(query)) return;
    resumeGuard.add(query);
    setTimeout(() => resumeGuard.delete(query), 4000);
    void client.resetQueries({ queryKey: query.queryKey, exact: true });
  });
}


// A guild id must be a Discord snowflake. Guarding on `guild != null` let the
// literal string "undefined" through (from a /guilds/undefined URL minted while
// router.query was still hydrating), firing every query at /api/bot/...​/undefined.
export function isValidGuildId(guild: string | undefined | null): boolean {
  return typeof guild === 'string' && /^\d+$/.test(guild);
}

export const Keys = {
  login: ['login'],
  guild_info: (guild: string) => ['guild_info', guild],
  features: (guild: string, feature: string) => ['feature', guild, feature],
  guildRoles: (guild: string) => ['gulid_roles', guild],
  guildChannels: (guild: string) => ['gulid_channel', guild],
  guildStats: (guild: string) => ['guild_stats', guild],
  guildEmojis: (guild: string) => ['guild_emojis', guild],
};

export const Mutations = {
  updateFeature: (guild: string, id: string) => ['feature', guild, id],
};

export function useGuild(id: string) {
  const accessToken = useAccessToken();

  return useQuery(['guild', id], () => getGuild(accessToken as string, id), {
    enabled: accessToken != null,
  });
}

// Last-known guild list, persisted so a hard reload doesn't depend on Discord
// answering. /users/@me/guilds is strictly rate-limited, and every hard reload
// wipes the in-memory query cache — so users who reload often hit 429 and saw
// a broken picker/palette until yet another reload. Cleared on logout.
export const GUILDS_CACHE_KEY = 'cached-user-guilds';

function readCachedGuilds(): Guild[] | undefined {
  try {
    if (typeof window === 'undefined') return undefined;
    const raw = localStorage.getItem(GUILDS_CACHE_KEY);
    const parsed = raw ? JSON.parse(raw) : undefined;
    return Array.isArray(parsed) ? (parsed as Guild[]) : undefined;
  } catch {
    return undefined;
  }
}

export function useGuilds() {
  const accessToken = useAccessToken();

  return useQuery(['user_guilds'], () => getGuilds(accessToken as string), {
    enabled: accessToken != null,
    // Serve the cached list instantly while the real fetch runs (or fails).
    placeholderData: readCachedGuilds,
    onSuccess: (data) => {
      try {
        localStorage.setItem(GUILDS_CACHE_KEY, JSON.stringify(data));
      } catch {
        /* quota/private mode — cache just won't persist */
      }
    },
    // On 429, quick retries burn more of the same rate-limit window. Back off
    // at 5s/10s instead of the default 1s/2s (bounded, so a cold-cache failure
    // still surfaces the error panel in ~15s rather than hanging).
    retry: 2,
    retryDelay: (attempt, error) =>
      (error as { status?: number })?.status === 429
        ? 5000 * (attempt + 1)
        : retryDelay(attempt),
  });
}

export type MyBotGuild = { id: string; member_count: number };
export type MyBotGuildsResult = { botReachable: boolean; guilds: MyBotGuild[] };

/**
 * Which of the user's admin guilds the bot is actually in (+ member counts).
 * Backed by the server-side `/api/me/guilds` route so the bot's full guild list
 * never reaches the browser.
 */
export function useMyBotGuilds() {
  const accessToken = useAccessToken();

  return useQuery<MyBotGuildsResult>(
    ['me_bot_guilds'],
    async () => {
      const res = await fetch('/api/me/guilds');
      if (!res.ok) throw new Error('Failed to load bot guilds');
      return res.json();
    },
    {
      enabled: accessToken != null,
      staleTime: 60_000,
      retry: 1,
      retryDelay: 1000,
      // A cold serverless start can briefly degrade to botReachable:false (the
      // route returns 200, so this isn't an error). Poll until the bot is
      // reachable so the presence badges appear without a manual reload, then
      // stop refetching.
      refetchInterval: (data) => (data && data.botReachable === false ? 4000 : false),
    }
  );
}

export function useSelfUserQuery() {
  const accessToken = useAccessToken();

  return useQuery<UserInfo>(['users', 'me'], () => fetchUserInfo(accessToken!!), {
    enabled: accessToken != null,
    staleTime: Infinity,
  });
}

export function useGuildInfoQuery(guild: string) {
  const { status, session } = useSession();

  return useQuery<CustomGuildInfo | null>(
    Keys.guild_info(guild),
    () => fetchGuildInfo(session!!, guild),
    {
      enabled: status === 'authenticated' && isValidGuildId(guild),
      refetchOnWindowFocus: true,
      // Retry transient failures (e.g. a slow RPC / the bot restarting) with
      // backoff so the overview recovers without a manual "Try again".
      retry: 3,
      retryDelay,
      staleTime: 0,
    }
  );
}

export function useFeatureQuery<K extends keyof CustomFeatures>(guild: string, feature: K) {
  const { status, session } = useSession();

  return useQuery(Keys.features(guild, feature), () => getFeature(session!!, guild, feature), {
    enabled: status === 'authenticated' && isValidGuildId(guild),
    // Recover from a transient failure (bot restarting) without a manual retry.
    retry: 2,
    retryDelay,
  });
}

export type EnableFeatureOptions = { guild: string; feature: string; enabled: boolean };
export function useEnableFeatureMutation() {
  const { session } = useSession();
  const toast = useToast();

  return useMutation(
    async ({ enabled, guild, feature }: EnableFeatureOptions) => {
      if (enabled) return enableFeature(session!!, guild, feature);
      return disableFeature(session!!, guild, feature);
    },
    {
      async onSuccess(_, { guild, feature, enabled }) {
        await client.invalidateQueries(Keys.features(guild, feature));
        client.invalidateQueries(['audit', guild]);
        client.setQueryData<GuildInfo | null>(Keys.guild_info(guild), (prev) => {
          if (prev == null) return null;

          if (enabled) {
            return {
              ...prev,
              enabledFeatures: prev.enabledFeatures.includes(feature)
                ? prev.enabledFeatures
                : [...prev.enabledFeatures, feature],
            };
          } else {
            return {
              ...prev,
              enabledFeatures: prev.enabledFeatures.filter((f) => f !== feature),
            };
          }
        });
        toast({
          title: enabled ? 'Feature enabled' : 'Feature disabled',
          description: enabled
            ? 'The feature has been successfully enabled.'
            : 'The feature has been successfully disabled.',
          status: 'success',
          duration: 3000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
      onError(_err, { enabled }) {
        toast({
          title: enabled ? 'Failed to enable feature' : 'Failed to disable feature',
          description: 'An error occurred. Please try again.',
          status: 'error',
          duration: 5000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
    }
  );
}

export type UpdateFeatureOptions = {
  guild: string;
  feature: keyof CustomFeatures;
  options: FormData | string;
};
export function useUpdateFeatureMutation() {
  const { session } = useSession();
  const toast = useToast();

  return useMutation(
    (options: UpdateFeatureOptions) =>
      updateFeature(session!!, options.guild, options.feature, options.options),
    {
      onSuccess(updated, options) {
        const key = Keys.features(options.guild, options.feature);
        client.setQueryData(key, updated);
        client.invalidateQueries(['audit', options.guild]);
        toast({
          title: 'Settings saved',
          description: 'Your changes have been saved successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
      onError(error: unknown) {
        // Show the server's reason (e.g. a rejected AutoMod regex) instead of a
        // generic message, so the user can actually fix the problem.
        const description =
          error instanceof Error && error.message
            ? error.message
            : 'An error occurred while saving. Please try again.';
        toast({
          title: 'Failed to save settings',
          description,
          status: 'error',
          duration: 6000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
    }
  );
}

export function useGuildStatsQuery(guild: string) {
  const { status, session } = useSession();

  return useQuery(Keys.guildStats(guild), () => fetchGuildStats(session!!, guild), {
    enabled: status === 'authenticated' && isValidGuildId(guild),
    refetchOnWindowFocus: true,
    // Live dashboard: re-fetch on an interval so the Overview updates on its own
    // (only while the tab is focused, to stay gentle on the rate limit).
    staleTime: 0,
    refetchInterval: 8_000,
    refetchIntervalInBackground: false,
    // Recover from a transient failure (slow RPC / bot restart) on its own.
    retry: 3,
    retryDelay,
  });
}

export function useMemberSearchQuery(guild: string, query: string) {
  const { status, session } = useSession();

  return useQuery<MemberSearchItem[]>(
    ['member_search', guild, query],
    async () => (await searchMembers(session!!, guild, query)).members,
    {
      enabled: status === 'authenticated' && isValidGuildId(guild) && query.trim().length >= 2,
      keepPreviousData: true,
      staleTime: 30_000,
      retry: false,
    }
  );
}

export function useMemberDetailQuery(guild: string, userId: string | null) {
  const { status, session } = useSession();

  return useQuery<MemberDetail>(
    ['member_detail', guild, userId],
    () => fetchMemberDetail(session!!, guild, userId!!),
    {
      enabled: status === 'authenticated' && isValidGuildId(guild) && userId != null,
      staleTime: 15_000,
      retry: 2,
      retryDelay,
    }
  );
}

export function useModerateMemberMutation() {
  const { session } = useSession();
  const toast = useToast();

  return useMutation(
    ({ guild, userId, body }: { guild: string; userId: string; body: ModeratePayload }) =>
      moderateMember(session!!, guild, userId, body),
    {
      onSuccess(res, { guild, userId }) {
        client.invalidateQueries(['member_detail', guild, userId]);
        client.invalidateQueries(['moderation', guild]);
        client.invalidateQueries(['audit', guild]);
        toast({
          title: res?.message ?? 'Action applied',
          status: 'success',
          duration: 2500,
          isClosable: true,
          position: 'bottom-right',
        });
      },
      onError(err) {
        toast({
          title: 'Action failed',
          description: (err as Error).message,
          status: 'error',
          duration: 5000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
    }
  );
}

export function useSetLocaleMutation() {
  const { session } = useSession();
  const toast = useToast();

  return useMutation(
    ({ guild, locale }: { guild: string; locale: string }) =>
      setGuildLocale(session!!, guild, locale),
    {
      onSuccess(_, { guild, locale }) {
        client.setQueryData<CustomGuildInfo | null>(Keys.guild_info(guild), (prev) =>
          prev ? { ...prev, locale } : prev
        );
        client.invalidateQueries(['audit', guild]);
        toast({
          title: 'Bot language updated',
          status: 'success',
          duration: 2500,
          isClosable: true,
          position: 'bottom-right',
        });
      },
      onError() {
        toast({
          title: 'Failed to update language',
          status: 'error',
          duration: 4000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
    }
  );
}

export function useAuditQuery(guild: string) {
  const { status, session } = useSession();

  return useQuery<AuditEntry[]>(
    ['audit', guild],
    async () => (await fetchAudit(session!!, guild)).entries,
    {
      enabled: status === 'authenticated' && isValidGuildId(guild),
      staleTime: 20_000,
      retry: 2,
      retryDelay,
    }
  );
}

export function useTicketsQuery(guild: string) {
  const { status, session } = useSession();

  return useQuery<Ticket[]>(
    ['tickets', guild],
    async () => (await fetchTickets(session!!, guild)).tickets,
    {
      enabled: status === 'authenticated' && isValidGuildId(guild),
      staleTime: 20_000,
      retry: 2,
      retryDelay,
    }
  );
}

// Searches inside closed-ticket transcripts. Enabled only once the (debounced)
// query is at least 2 characters, so typing doesn't fire a request per keystroke.
export function useTicketSearchQuery(guild: string, query: string) {
  const { status, session } = useSession();
  const q = query.trim();

  return useQuery<Ticket[]>(
    ['ticket_search', guild, q],
    async () => (await searchTickets(session!!, guild, q)).tickets,
    {
      enabled: status === 'authenticated' && isValidGuildId(guild) && q.length >= 2,
      keepPreviousData: true,
      staleTime: 20_000,
      retry: 2,
      retryDelay,
    }
  );
}

export function useTicketTranscriptQuery(guild: string, ticketId: number | null) {
  const { status, session } = useSession();

  return useQuery<TicketDetail>(
    ['ticket', guild, ticketId],
    async () => fetchTicketTranscript(session!!, guild, ticketId as number),
    {
      enabled: status === 'authenticated' && isValidGuildId(guild) && ticketId !== null,
      staleTime: 60_000,
      retry: 2,
      retryDelay,
    }
  );
}

export function useModerationQuery(guild: string) {
  const { status, session } = useSession();

  return useQuery<ModerationData>(['moderation', guild], () => fetchModeration(session!!, guild), {
    enabled: status === 'authenticated' && isValidGuildId(guild),
    staleTime: 30_000,
    retry: 2,
    retryDelay,
  });
}

export function useSetBanAppealsMutation() {
  const { session } = useSession();
  const toast = useToast();

  return useMutation(
    ({ guild, enabled }: { guild: string; enabled: boolean }) =>
      setBanAppeals(session!!, guild, enabled),
    {
      onSuccess(_, { guild }) {
        client.invalidateQueries(['moderation', guild]);
      },
      onError() {
        toast({
          title: 'Failed to update ban appeals',
          status: 'error',
          duration: 4000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
    }
  );
}

export function useDecideBanAppealMutation() {
  const { session } = useSession();
  const toast = useToast();

  return useMutation(
    ({ guild, appealId, decision }: { guild: string; appealId: number; decision: 'approve' | 'deny' }) =>
      decideBanAppeal(session!!, guild, appealId, decision),
    {
      onSuccess(_, { guild, decision }) {
        client.invalidateQueries(['moderation', guild]);
        client.invalidateQueries(['audit', guild]);
        toast({
          title: decision === 'approve' ? 'Appeal approved — user unbanned' : 'Appeal denied',
          status: 'success',
          duration: 4000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
      onError(error: unknown) {
        toast({
          title: 'Failed to decide appeal',
          description: error instanceof Error ? error.message : undefined,
          status: 'error',
          duration: 5000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
    }
  );
}

export function useAnalyticsQuery(guild: string, days: number) {
  const { status, session } = useSession();

  return useQuery<AnalyticsData>(
    ['analytics', guild, days],
    () => fetchAnalytics(session!!, guild, days),
    {
      enabled: status === 'authenticated' && isValidGuildId(guild),
      keepPreviousData: true,
      staleTime: 60_000,
      retry: 2,
      retryDelay,
    }
  );
}

export function useDeleteWarningMutation() {
  const { session } = useSession();
  const toast = useToast();

  return useMutation(
    ({ guild, id }: { guild: string; id: number }) => deleteWarning(session!!, guild, id),
    {
      onSuccess(_, { guild, id }) {
        // Optimistically drop it from the cached list. The success toast (with
        // an Undo action) is shown by the caller, which has the warning's data.
        client.setQueryData<ModerationData>(['moderation', guild], (prev) =>
          prev ? { ...prev, warnings: prev.warnings.filter((w) => w.id !== id) } : prev
        );
        // The same warning may be shown on a member's card — refetch member
        // details for this guild so they don't show a stale warning.
        client.invalidateQueries(['member_detail', guild]);
        client.invalidateQueries(['audit', guild]);
      },
      onError() {
        toast({
          title: 'Failed to remove warning',
          status: 'error',
          duration: 4000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
    }
  );
}

export function useGuildEmojisQuery(guild: string) {
  const { status, session } = useSession();

  return useQuery(Keys.guildEmojis(guild), () => fetchGuildEmojis(session!!, guild), {
    enabled: status === 'authenticated' && isValidGuildId(guild),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useGuildRolesQuery(guild: string) {
  const { session } = useSession();

  return useQuery(Keys.guildRoles(guild), () => fetchGuildRoles(session!!, guild));
}

export function useGuildChannelsQuery(guild: string) {
  const { session } = useSession();

  return useQuery(Keys.guildChannels(guild), () => fetchGuildChannels(session!!, guild));
}

export function useSelfUser(): UserInfo {
  return useSelfUserQuery().data!!;
}

export function useGuildPreview(guild: string) {
  const query = useGuilds();

  return {
    guild: query.data?.find((g) => g.id === guild),
    query,
  };
}
