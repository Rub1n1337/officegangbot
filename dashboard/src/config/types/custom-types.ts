/***
 * Custom types that should be configured by developer
 ***/

import { z } from 'zod';
import { GuildInfo } from './types';

export type CustomGuildInfo = GuildInfo & {
  id: string;
  name: string;
  icon?: string | null;
  owner_id: string;
  member_count: number;
  locale?: string;
};

export type GuildStatsTopXp = {
  name: string;
  level: number;
  xp: number;
};

export type ModerationWarning = {
  id: number;
  userId: string;
  userName: string;
  reason: string;
  moderatorName: string;
  createdAt: string | null;
};

export type ModerationPunishment = {
  userId: string;
  userName: string;
  type: 'mute' | 'ban';
  reason?: string | null;
  expiresAt: string | null;
};

export type ModerationLeaderItem = {
  userId: string;
  name: string;
  level: number;
  xp: number;
};

export type ModerationData = {
  warnings: ModerationWarning[];
  punishments: ModerationPunishment[];
  leaderboard: ModerationLeaderItem[];
};

export type AuditEntry = {
  id: number;
  actorId: string | null;
  actorName: string | null;
  action: string;
  target: string | null;
  detail: string | null;
  createdAt: string | null;
};

export type MemberSearchItem = {
  id: string;
  name: string;
  displayName: string;
  avatar: string;
};

export type MemberRole = {
  id: string;
  name: string;
  color: number;
};

export type MemberWarning = {
  id: number;
  reason: string;
  moderatorName: string;
  createdAt: string | null;
};

export type MemberDetail = {
  id: string;
  name: string;
  displayName: string;
  avatar: string | null;
  joinedAt: string | null;
  inServer: boolean;
  roles: MemberRole[];
  level: number;
  xp: number;
  warnings: MemberWarning[];
};

export type GuildStats = {
  id: string;
  name: string;
  icon?: string | null;
  online: boolean;
  member_count: number;
  channel_count: number;
  text_channels: number;
  voice_channels: number;
  role_count: number;
  latency_ms: number;
  enabled_feature_count: number;
  top_xp: GuildStatsTopXp[];
};

export type CustomFeatures = {
  'rules': RulesFeature;
  'welcome-message': WelcomeMessageFeature;
  'reaction-role': ReactionRoleFeature;
  'moderation': ModerationFeature;
  'logging': LoggingFeature;
  'filter': FilterFeature;
  'levels': LevelsFeature;
  'automod': AutomodFeature;
  'tickets': TicketsFeature;
  'scheduled-messages': ScheduledMessagesFeature;
};

export type ScheduledMessageItem = {
  channelId?: string | null;
  content: string;
  scheduledAt: string; // ISO 8601 (UTC)
  repeat: 'none' | 'daily' | 'weekly';
  enabled: boolean;
};

export type ScheduledMessagesFeature = {
  items: ScheduledMessageItem[];
};

export type TicketsFeature = {
  supportRole?: string | null;
  category?: string | null;
};

// AutoMod has no configurable options — its rules are fixed and it's controlled
// purely by the enable/disable toggle. The empty shape keeps it in the feature
// system without a settings form.
export type AutomodFeature = Record<string, never>;

export type WelcomeMessageFeature = {
  channel?: string | null;
  message: string;
  autorole?: string | null;
};

export type LevelRewardItem = {
  level: number;
  roleId?: string | null;
};

export type LevelsFeature = {
  channel?: string | null;
  rewards: LevelRewardItem[];
};

export type RulesFeature = {
  channel?: string | null;
  message: string;
  reactionEnabled?: boolean;
  reactionEmoji?: string;
  reactionRole?: string | null;
};

export type ReactionRoleItem = {
  channelId?: string | null;
  messageId?: string | null;
  emoji: string;
  roleId?: string | null;
};

export type ReactionRoleFeature = {
  items: ReactionRoleItem[];
};

export type ModerationFeature = {
  config?: string | null;
  kick?: string | null;
  ban?: string | null;
  mute?: string | null;
  warn?: string | null;
  clear?: string | null;
};

export type LoggingFeature = {
  logChannel?: string | null;
  usageChannel?: string | null;
  messagesChannel?: string | null;
  leaveChannel?: string | null;
};

export type FilterFeature = {
  words: string[];
};

export const rulesFeatureSchema = z.object({
  channel: z.string().nullable().optional(),
  message: z.string().min(1),
});

export const welcomeFeatureSchema = z.object({
  channel: z.string().nullable().optional(),
  message: z.string().min(1),
});
