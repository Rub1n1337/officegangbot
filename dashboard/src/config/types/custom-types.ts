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

export type ModerationStrikeUser = {
  userId: string;
  userName: string;
  count: number;
  nextDecayAt: string | null;
  lastStrikeAt: string | null;
};

export type ModerationStrikes = {
  enabled: boolean;
  expiryHours: number;
  muteAt: number;
  kickAt: number;
  banAt: number;
  users: ModerationStrikeUser[];
};

export type BanAppeal = {
  id: number;
  userId: string;
  userName: string | null;
  reason: string | null;
  status: 'pending' | 'approved' | 'denied';
  decidedByName: string | null;
  createdAt: string | null;
  decidedAt: string | null;
};

export type ModerationAppeals = {
  enabled: boolean;
  items: BanAppeal[];
};

export type ModerationData = {
  warnings: ModerationWarning[];
  punishments: ModerationPunishment[];
  leaderboard: ModerationLeaderItem[];
  strikes: ModerationStrikes;
  appeals: ModerationAppeals;
};

export type HeatmapCell = { weekday: number; hour: number; count: number };
export type DayCount = { day: string; count: number };
export type ModActionDay = { day: string; action: string; count: number };
export type TopModerator = { name: string; count: number };

export type AnalyticsData = {
  days: number;
  heatmap: HeatmapCell[];
  modActionsByDay: ModActionDay[];
  automodByDay: DayCount[];
  ticketsOpenedByDay: DayCount[];
  ticketsClosedByDay: DayCount[];
  avgTicketResolutionHours: number | null;
  topModerators: TopModerator[];
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
  'reaction-menus': ReactionMenusFeature;
};

export type ReactionMenuItemConfig = {
  emoji: string;
  roleId?: string | null;
};

export type ReactionMenuConfig = {
  id?: number | null;
  channelId?: string | null;
  title: string;
  description: string;
  exclusive?: boolean;
  items: ReactionMenuItemConfig[];
};

export type ReactionMenusFeature = {
  menus: ReactionMenuConfig[];
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
  autoCloseHours?: number;
};

export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';

export type Ticket = {
  id: number;
  channelId: string;
  openerId: string;
  openerName: string | null;
  priority: TicketPriority;
  status: 'open' | 'closed';
  openedAt: string | null;
  closedAt: string | null;
  closedById: string | null;
  closedByName: string | null;
  closeComment: string | null;
  hasTranscript: boolean;
  // Only present on transcript-search results: text around the first match.
  snippet?: string | null;
};

export type TicketDetail = {
  id: number;
  openerName: string | null;
  priority: TicketPriority;
  status: 'open' | 'closed';
  openedAt: string | null;
  closedAt: string | null;
  closedByName: string | null;
  closeComment: string | null;
  transcript: string | null;
};

export type AutomodRule = {
  pattern: string;
  action: 'delete' | 'strike';
  enabled: boolean;
};

export type AutomodFeature = {
  dryRun: boolean;
  blockInvites: boolean;
  blockLinks: boolean;
  allowedDomains: string[];
  blockMassMentions: boolean;
  spamCount: number;
  spamWindow: number;
  mentionLimit: number;
  strikesEnabled: boolean;
  strikeExpiryHours: number;
  strikeMuteAt: number;
  strikeKickAt: number;
  strikeBanAt: number;
  rules: AutomodRule[];
};

export type WelcomeMessageFeature = {
  channel?: string | null;
  message: string;
  autorole?: string | null;
};

export type LevelRewardItem = {
  level: number;
  roleId?: string | null;
};

export type LevelMultiplierItem = {
  roleId?: string | null;
  multiplier: number;
};

export type LevelsFeature = {
  channel?: string | null;
  rewards: LevelRewardItem[];
  voiceXpEnabled: boolean;
  voiceXpPerMin: number;
  xpMultiplier: number;
  prestigeLevel: number;
  season: number;
  roleMultipliers: LevelMultiplierItem[];
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
