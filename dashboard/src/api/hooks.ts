import { CustomFeatures, CustomGuildInfo } from '../config/types';
import { QueryClient, useMutation, useQuery } from '@tanstack/react-query';
import { UserInfo, getGuild, getGuilds, fetchUserInfo } from '@/api/discord';
import {
  deleteWarning,
  disableFeature,
  enableFeature,
  fetchGuildChannels,
  fetchGuildEmojis,
  fetchGuildInfo,
  fetchGuildRoles,
  fetchGuildStats,
  fetchMemberDetail,
  fetchModeration,
  getFeature,
  moderateMember,
  searchMembers,
  setGuildLocale,
  updateFeature,
} from '@/api/bot';
import type { ModeratePayload } from '@/api/bot';
import { GuildInfo } from '@/config/types';
import type { MemberDetail, MemberSearchItem, ModerationData } from '@/config/types/custom-types';
import { useAccessToken, useSession } from '@/utils/auth/hooks';
import { useToast } from '@chakra-ui/react';

export const client = new QueryClient({
  defaultOptions: {
    mutations: {
      retry: 0,
    },
    queries: {
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: 0,
    },
  },
});

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

export function useGuilds() {
  const accessToken = useAccessToken();

  return useQuery(['user_guilds'], () => getGuilds(accessToken as string), {
    enabled: accessToken != null,
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
      enabled: status === 'authenticated',
      refetchOnWindowFocus: true,
      retry: false,
      staleTime: 0,
    }
  );
}

export function useFeatureQuery<K extends keyof CustomFeatures>(guild: string, feature: K) {
  const { status, session } = useSession();

  return useQuery(Keys.features(guild, feature), () => getFeature(session!!, guild, feature), {
    enabled: status === 'authenticated',
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
        toast({
          title: 'Settings saved',
          description: 'Your changes have been saved successfully.',
          status: 'success',
          duration: 3000,
          isClosable: true,
          position: 'bottom-right',
        });
      },
      onError() {
        toast({
          title: 'Failed to save settings',
          description: 'An error occurred while saving. Please try again.',
          status: 'error',
          duration: 5000,
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
    enabled: status === 'authenticated',
    refetchOnWindowFocus: true,
    // Live dashboard: re-fetch on an interval so the Overview updates on its own
    // (only while the tab is focused, to stay gentle on the rate limit).
    staleTime: 0,
    refetchInterval: 8_000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}

export function useMemberSearchQuery(guild: string, query: string) {
  const { status, session } = useSession();

  return useQuery<MemberSearchItem[]>(
    ['member_search', guild, query],
    async () => (await searchMembers(session!!, guild, query)).members,
    {
      enabled: status === 'authenticated' && query.trim().length >= 2,
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
      enabled: status === 'authenticated' && userId != null,
      staleTime: 15_000,
      retry: false,
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

export function useModerationQuery(guild: string) {
  const { status, session } = useSession();

  return useQuery<ModerationData>(['moderation', guild], () => fetchModeration(session!!, guild), {
    enabled: status === 'authenticated',
    staleTime: 30_000,
    retry: false,
  });
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
    enabled: status === 'authenticated',
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
