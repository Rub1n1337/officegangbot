// Per-plan resource caps — mirrors core/limits.py on the bot. Free keeps the
// original ceilings; premium raises them (additive only). Keep in sync with the
// Python side.
export const FREE_LIMITS = {
  level_rewards: 100,
  scheduled_messages: 50,
  automod_rules: 25,
  banned_words: 500,
  role_menus: 25,
  reaction_roles: 100,
  level_multipliers: 50,
  custom_commands: 0,
} as const;

export const PREMIUM_LIMITS = {
  level_rewards: 300,
  scheduled_messages: 200,
  automod_rules: 100,
  banned_words: 2000,
  role_menus: 100,
  reaction_roles: 400,
  level_multipliers: 150,
  custom_commands: 15,
} as const;

export type LimitResource = keyof typeof FREE_LIMITS;

export function limitFor(resource: LimitResource, premium: boolean): number {
  return (premium ? PREMIUM_LIMITS : FREE_LIMITS)[resource];
}
