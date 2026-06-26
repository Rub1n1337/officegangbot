import { CustomFeatures, CustomGuildInfo } from '../config/types';
import { QueryClient, useMutation, useQuery } from '@tanstack/react-query';
import { UserInfo, getGuild, getGuilds, fetchUserInfo } from '@/api/discord';
import {
  disableFeature,
  enableFeature,
  fetchGuildChannels,
  fetchGuildInfo,
  fetchGuildRoles,
  fetchGuildStats,
  getFeature,
  updateFeature,
} from '@/api/bot';
import { GuildInfo } from '@/config/types';
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
    // Stats are live-ish; let them go stale quickly so a revisit refetches.
    staleTime: 15_000,
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
