// Searchable index of individual settings for the ⌘K palette: typing a term
// like "slowmode", "strike" or "приветствие" jumps to the feature form that
// owns it. Keywords are matched case-insensitively and include Russian
// synonyms, since the labels themselves are compile-time strings we can't
// enumerate at runtime.

export type SettingEntry = {
  feature: string; // feature id — the target page is /guilds/{id}/features/{feature}
  label: string; // shown in the palette
  keywords: string[];
};

export const SETTINGS_INDEX: SettingEntry[] = [
  // AutoMod
  { feature: 'automod', label: 'Block invite links', keywords: ['invite', 'discord.gg', 'инвайт', 'приглашен'] },
  { feature: 'automod', label: 'Block external links', keywords: ['link', 'url', 'domain', 'ссылк', 'домен'] },
  { feature: 'automod', label: 'Anti-spam thresholds', keywords: ['spam', 'flood', 'спам', 'флуд'] },
  { feature: 'automod', label: 'Mention limit', keywords: ['mention', 'ping', 'меншен', 'упоминан'] },
  { feature: 'automod', label: 'Strike system', keywords: ['strike', 'escalation', 'страйк', 'эскалац'] },
  { feature: 'automod', label: 'Custom regex filters', keywords: ['regex', 'pattern', 'filter', 'регекс', 'фильтр'] },
  { feature: 'automod', label: 'AutoMod dry-run', keywords: ['dry', 'test mode', 'пробн'] },
  { feature: 'automod', label: 'AutoMod exemptions', keywords: ['exempt', 'ignore', 'bypass', 'исключен', 'игнор'] },
  // Moderation
  { feature: 'moderation', label: 'Moderator roles', keywords: ['permission', 'mod role', 'права', 'роли модератор'] },
  { feature: 'moderation', label: 'Warning auto-escalation', keywords: ['warn', 'warning', 'предупрежден', 'варн'] },
  // Anti-raid
  { feature: 'anti-raid', label: 'Anti-raid thresholds', keywords: ['raid', 'join spike', 'рейд', 'заход'] },
  // Verification
  { feature: 'verification', label: 'Verified role', keywords: ['verify', 'verification', 'gate', 'верифиц', 'верифика'] },
  // Welcome
  { feature: 'welcome-message', label: 'Welcome message', keywords: ['welcome', 'greeting', 'приветств'] },
  { feature: 'welcome-message', label: 'Autorole', keywords: ['autorole', 'auto role', 'авторол'] },
  // Levels
  { feature: 'levels', label: 'Level-up channel & rewards', keywords: ['level', 'xp', 'rank', 'уров', 'опыт'] },
  { feature: 'levels', label: 'Voice XP & multipliers', keywords: ['voice', 'multiplier', 'голосов', 'множител'] },
  { feature: 'levels', label: 'Prestige & seasons', keywords: ['prestige', 'season', 'престиж', 'сезон'] },
  // Tickets
  { feature: 'tickets', label: 'Ticket support role & category', keywords: ['ticket', 'support', 'тикет', 'поддержк'] },
  { feature: 'tickets', label: 'Ticket auto-close', keywords: ['auto-close', 'autoclose', 'inactive', 'автозакрыт'] },
  // Logging
  { feature: 'logging', label: 'Log channels', keywords: ['log', 'audit channel', 'лог', 'журнал'] },
  // Filter
  { feature: 'filter', label: 'Banned words', keywords: ['word', 'banned', 'blacklist', 'слов', 'мат'] },
  // Role menus
  { feature: 'reaction-menus', label: 'Role menus (style, roles)', keywords: ['role menu', 'button', 'dropdown', 'reaction', 'меню ролей', 'кнопк', 'реакц'] },
  { feature: 'reaction-role', label: 'Single reaction role', keywords: ['reaction role', 'роль за реакц'] },
  // Rules / scheduled
  { feature: 'rules', label: 'Rules channel & message', keywords: ['rules', 'правил'] },
  { feature: 'scheduled-messages', label: 'Scheduled messages', keywords: ['schedule', 'announce', 'расписан', 'отложен', 'анонс'] },
];

/** Entries whose label or any keyword contains the query (case-insensitive). */
export function searchSettings(query: string): SettingEntry[] {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];
  return SETTINGS_INDEX.filter(
    (e) => e.label.toLowerCase().includes(q) || e.keywords.some((k) => k.includes(q))
  );
}
