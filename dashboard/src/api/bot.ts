import {
  AuditEntry,
  CustomFeatures,
  CustomGuildInfo,
  GuildStats,
  MemberDetail,
  MemberSearchItem,
  ModerationData,
} from '@/config/types/custom-types';
import { AccessToken } from '@/utils/auth/server';
import { callDefault, callReturn } from '@/utils/fetch/core';
import { botRequest } from '@/utils/fetch/requests';
import { ChannelTypes } from './discord';

export type Role = {
  id: string;
  name: string;
  color: number;
  position: number;
  icon?: {
    iconUrl?: string;
    emoji?: string;
  };
};

export type GuildChannel = {
  id: string;
  name: string;
  type: ChannelTypes;
  /**
   * parent category of the channel
   */
  category?: string | null;
};

/**
 * Get custom guild info on from backend
 *
 * @param guild Guild ID
 * @return Guild info, or null if bot hasn't joined the guild
 */
export async function fetchGuildInfo(
  session: AccessToken,
  guild: string
): Promise<CustomGuildInfo | null> {
  return await callReturn<CustomGuildInfo | null>(
    `/guilds/${guild}`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
      allowed: {
        404: () => null,
      },
    })
  );
}

/**
 * Live overview stats for a guild (member/channel/role counts, latency, top XP).
 * @param guild Guild ID
 */
export async function fetchGuildStats(session: AccessToken, guild: string): Promise<GuildStats> {
  return await callReturn<GuildStats>(
    `/api/guild/${guild}/stats`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

/** Moderation panel data: recent warnings, active timed punishments, leaderboard. */
export async function fetchModeration(session: AccessToken, guild: string): Promise<ModerationData> {
  return await callReturn<ModerationData>(
    `/api/guild/${guild}/moderation`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

/** The dashboard audit trail: who did what (moderation, settings) via the web. */
export async function fetchAudit(session: AccessToken, guild: string): Promise<{ entries: AuditEntry[] }> {
  return await callReturn<{ entries: AuditEntry[] }>(
    `/api/guild/${guild}/audit`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

export async function deleteWarning(session: AccessToken, guild: string, warningId: number) {
  return await callDefault(
    `/api/guild/${guild}/warnings/${warningId}`,
    botRequest(session, {
      request: {
        method: 'DELETE',
      },
    })
  );
}

/** Searches the guild's members by name/id (max 25 results). */
export async function searchMembers(
  session: AccessToken,
  guild: string,
  query: string
): Promise<{ members: MemberSearchItem[] }> {
  return await callReturn<{ members: MemberSearchItem[] }>(
    `/api/guild/${guild}/members?q=${encodeURIComponent(query)}`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

/** A member's profile: roles, level/XP and warnings. */
export async function fetchMemberDetail(
  session: AccessToken,
  guild: string,
  userId: string
): Promise<MemberDetail> {
  return await callReturn<MemberDetail>(
    `/api/guild/${guild}/members/${userId}`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

export type ModerateAction = 'warn' | 'mute' | 'unmute' | 'kick' | 'ban';
export type ModeratePayload = {
  act: ModerateAction;
  reason?: string;
  durationMinutes?: number;
  moderatorId?: string;
  moderatorName?: string;
};

/** Performs a moderation action on a member. Throws with the bot's message on failure. */
export async function moderateMember(
  session: AccessToken,
  guild: string,
  userId: string,
  body: ModeratePayload
): Promise<{ success?: boolean; message?: string }> {
  const res = await callReturn<{ success?: boolean; message?: string; error?: string }>(
    `/api/guild/${guild}/members/${userId}/moderate`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
    })
  );
  if (res?.error) throw new Error(res.error);
  return res;
}

/** Sets the guild's bot language ('en' / 'ru'). */
export async function setGuildLocale(session: AccessToken, guild: string, locale: string) {
  return await callDefault(
    `/api/guild/${guild}/locale`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locale }),
      },
    })
  );
}

export type GuildEmoji = {
  id: string;
  name: string;
  animated: boolean;
  url: string;
};

/**
 * The guild's custom emojis, for the dashboard emoji picker. Returns [] if the
 * bot can't reach the guild (older bot build, not joined, etc.) so the picker
 * still works with the standard emoji set.
 */
export async function fetchGuildEmojis(session: AccessToken, guild: string): Promise<GuildEmoji[]> {
  return await callReturn<GuildEmoji[]>(
    `/api/guild/${guild}/emojis`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
      allowed: {
        404: () => [],
      },
    })
  );
}

export async function enableFeature(session: AccessToken, guild: string, feature: string) {
  return await callDefault(
    `/guilds/${guild}/features/${feature}`,
    botRequest(session, {
      request: {
        method: 'POST',
      },
    })
  );
}

export async function disableFeature(session: AccessToken, guild: string, feature: string) {
  return await callDefault(
    `/guilds/${guild}/features/${feature}`,
    botRequest(session, {
      request: {
        method: 'DELETE',
      },
    })
  );
}

export async function getFeature<K extends keyof CustomFeatures>(
  session: AccessToken,
  guild: string,
  feature: K
): Promise<CustomFeatures[K]> {
  return await callReturn<CustomFeatures[K]>(
    `/guilds/${guild}/features/${feature}`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

export async function updateFeature<K extends keyof CustomFeatures>(
  session: AccessToken,
  guild: string,
  feature: K,
  options: FormData | string
): Promise<CustomFeatures[K]> {
  const isForm = options instanceof FormData;

  return await callReturn<CustomFeatures[K]>(
    `/guilds/${guild}/features/${feature}`,
    botRequest(session, {
      request: {
        method: 'PATCH',
        headers: isForm
          ? {}
          : {
              'Content-Type': 'application/json',
            },
        body: options,
      },
    })
  );
}

/**
 * Used for custom forms
 *
 * The dashboard itself doesn't use it
 * @returns Guild roles
 */
export async function fetchGuildRoles(session: AccessToken, guild: string) {
  return await callReturn<Role[]>(
    `/guilds/${guild}/roles`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

/**
 * @returns Guild channels
 */
export async function fetchGuildChannels(session: AccessToken, guild: string) {
  return await callReturn<GuildChannel[]>(
    `/guilds/${guild}/channels`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}
