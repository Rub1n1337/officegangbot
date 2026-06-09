/***
 * Custom types that should be configured by developer
 ***/

import { z } from 'zod';
import { GuildInfo } from './types';

export type CustomGuildInfo = GuildInfo & {};

/**
 * Define feature ids and it's option types
 */
export type CustomFeatures = {
  // OfficeGangBot core features
  'rules': RulesFeature;
  'welcome-message': WelcomeMessageFeature;
  'reaction-role': ReactionRoleFeature;
  'moderation': ModerationFeature;
  'logging': LoggingFeature;
  // Demo/extra features
  music: {};
  gaming: {};
  meme: MemeFeature;
};

/** example only */
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
  roleId: string;
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

export const memeFeatureSchema = z.object({
  channel: z.string().optional(),
  source: z.enum(['youtube', 'twitter', 'discord']).optional(),
});

export type MemeFeature = z.infer<typeof memeFeatureSchema>;
