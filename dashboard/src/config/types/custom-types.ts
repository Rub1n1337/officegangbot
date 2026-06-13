/***
 * Custom types that should be configured by developer
 ***/

import { z } from 'zod';
import { GuildInfo } from './types';

export type CustomGuildInfo = GuildInfo & {
  id: string;
  name: string;
  icon?: string;
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
  channel?: string;
  message: string;
};

export type RulesFeature = {
  channel?: string;
  message: string;
};

export type ReactionRoleFeature = {
  messageId?: string;
  channelId?: string;
  emoji: string;
  roleId?: string;
};

export type ModerationFeature = {
  modRoles: string[];
  adminRoles: string[];
  muteRole?: string;
};

export type LoggingFeature = {
  logChannel?: string;
  events: string[];
};

export const rulesFeatureSchema = z.object({
  channel: z.string().optional(),
  message: z.string().min(1),
});

export const welcomeFeatureSchema = z.object({
  channel: z.string().optional(),
  message: z.string().min(1),
});
