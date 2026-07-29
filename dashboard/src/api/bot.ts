import {
  AnalyticsData,
  AuditEntry,
  CustomFeatures,
  CustomGuildInfo,
  GuildStats,
  MemberDetail,
  MemberSearchItem,
  ModerationData,
  Ticket,
  TicketDetail,
} from '@/config/types/custom-types';
import type { AccessToken } from '@/utils/auth/server';
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

/** Activity heatmap + moderation/ticket trends for a guild over the last `days`. */
export async function fetchAnalytics(
  session: AccessToken,
  guild: string,
  days: number
): Promise<AnalyticsData> {
  return await callReturn<AnalyticsData>(
    `/api/guild/${guild}/analytics?days=${days}`,
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

/** The guild's support tickets (open first, then most recent). */
export async function fetchTickets(session: AccessToken, guild: string): Promise<{ tickets: Ticket[] }> {
  return await callReturn<{ tickets: Ticket[] }>(
    `/api/guild/${guild}/tickets`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

/** Searches inside closed-ticket transcripts and closing comments. */
export async function searchTickets(
  session: AccessToken,
  guild: string,
  query: string
): Promise<{ tickets: Ticket[] }> {
  return await callReturn<{ tickets: Ticket[] }>(
    `/api/guild/${guild}/tickets?q=${encodeURIComponent(query)}`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

/** A single ticket's metadata plus its full transcript. */
export async function fetchTicketTranscript(
  session: AccessToken,
  guild: string,
  ticketId: number
): Promise<TicketDetail> {
  return await callReturn<TicketDetail>(
    `/api/guild/${guild}/tickets/${ticketId}`,
    botRequest(session, {
      request: {
        method: 'GET',
      },
    })
  );
}

/** Enables/disables the ban-appeal flow for a guild. */
export async function setBanAppeals(session: AccessToken, guild: string, enabled: boolean) {
  return await callDefault(
    `/api/guild/${guild}/appeals/config`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      },
    })
  );
}

/** Approves (unbans) or denies a pending ban appeal. */
export async function decideBanAppeal(
  session: AccessToken,
  guild: string,
  appealId: number,
  decision: 'approve' | 'deny'
): Promise<{ success?: boolean; status?: string; error?: string }> {
  const res = await callReturn<{ success?: boolean; status?: string; error?: string }>(
    `/api/guild/${guild}/appeals/${appealId}`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      },
    })
  );
  if (res?.error) throw new Error(res.error);
  return res;
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

/** Premium: sets the guild's custom embed accent colour (0xRRGGBB, or null to clear). */
export async function setGuildEmbedColor(session: AccessToken, guild: string, color: number | null) {
  return await callDefault(
    `/api/guild/${guild}/embed-color`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color }),
      },
    })
  );
}

/** Premium: sets the guild's custom embed footer text (empty/null to clear). */
export async function setGuildFooterText(session: AccessToken, guild: string, text: string | null) {
  return await callDefault(
    `/api/guild/${guild}/footer`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      },
    })
  );
}

export type CustomCommand = { name: string; response: string };

/** The guild's premium custom /tag commands. */
export async function fetchCustomCommands(session: AccessToken, guild: string) {
  return await callReturn<{ commands: CustomCommand[] }>(
    `/api/guild/${guild}/custom-commands`,
    botRequest(session, { request: { method: 'GET' } })
  );
}

/** Premium: replaces the guild's custom /tag commands. */
export async function setCustomCommands(session: AccessToken, guild: string, commands: CustomCommand[]) {
  return await callDefault(
    `/api/guild/${guild}/custom-commands`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ commands }),
      },
    })
  );
}

export type ConfigBackup = { id: number; kind: string; createdAt: string };

/** Premium: metadata for the guild's config backups (newest first). */
export async function fetchConfigBackups(session: AccessToken, guild: string) {
  return await callReturn<{ backups: ConfigBackup[] }>(
    `/api/guild/${guild}/backups`,
    botRequest(session, { request: { method: 'GET' } })
  );
}

/** Premium: the full snapshot for one backup (feature -> payload). */
export async function fetchConfigBackup(session: AccessToken, guild: string, id: number) {
  return await callReturn<{ data: Record<string, Record<string, unknown>> }>(
    `/api/guild/${guild}/backups/${id}`,
    botRequest(session, { request: { method: 'GET' } })
  );
}

/** Premium: take a manual config backup. */
export async function createConfigBackup(session: AccessToken, guild: string) {
  return await callDefault(
    `/api/guild/${guild}/backups`,
    botRequest(session, { request: { method: 'POST' } })
  );
}

export type CommandInfo = { name: string; category: string; description: string };
export type CommandOverride = {
  enabled: boolean;
  allowed_channels: number[];
  ignored_channels: number[];
  allowed_roles: number[];
  ignored_roles: number[];
};
export type CommandsData = { commands: CommandInfo[]; overrides: Record<string, CommandOverride> };

/** The command registry + this guild's per-command overrides. */
export async function fetchCommands(session: AccessToken, guild: string) {
  return await callReturn<CommandsData>(
    `/api/guild/${guild}/commands`,
    botRequest(session, { request: { method: 'GET' } })
  );
}

/** Set one command's override (enable/disable + channel/role gates). */
export async function setCommandOverride(
  session: AccessToken,
  guild: string,
  body: {
    command: string;
    enabled: boolean;
    allowedChannels: string[];
    ignoredChannels: string[];
    allowedRoles: string[];
    ignoredRoles: string[];
  }
) {
  return await callDefault(
    `/api/guild/${guild}/commands`,
    botRequest(session, {
      request: {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
    })
  );
}

/**
 * Applies a set of feature payloads to a guild, merging each over the guild's
 * current config so unspecified id fields are preserved. Returns the ids of
 * features that failed. Shared by config import, multi-server sync and backup
 * restore.
 */
export async function applyFeaturesToGuild(
  session: AccessToken,
  guild: string,
  features: Record<string, Record<string, unknown>>
): Promise<string[]> {
  const failed: string[] = [];
  for (const [feature, subset] of Object.entries(features)) {
    try {
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
  return failed;
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
