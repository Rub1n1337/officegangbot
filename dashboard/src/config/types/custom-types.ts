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
};

export type CustomFeatures = {
  'rules': RulesFeature;
  'welcome-message': WelcomeMessageFeature;
  'reaction-role': ReactionRoleFeature;
  'moderation': ModerationFeature;
  'logging': LoggingFeature;
};

export type WelcomeMessageFeature = {
  channel?: string | null;
  message: string;
};

export type RulesFeature = {
  channel?: string | null;
  message: string;
};

export type ReactionRoleFeature = {
  messageId?: string | null;
  channelId?: string | null;
  emoji: string;
  roleId?: string | null;
};

export type ModerationFeature = {
  modRoles: string[];
  adminRoles: string[];
  muteRole?: string | null;
};

export type LoggingFeature = {
  logChannel?: string | null;
  events: string[];
};

export const rulesFeatureSchema = z.object({
  channel: z.string().nullable().optional(),
  message: z.string().min(1),
});

export const welcomeFeatureSchema = z.object({
  channel: z.string().nullable().optional(),
  message: z.string().min(1),
});
