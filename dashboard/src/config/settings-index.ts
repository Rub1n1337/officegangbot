// Searchable index of individual settings for the ⌘K palette: typing a term
// like "slowmode", "strike" or "приветствие" jumps to the feature form that
// owns it. Keywords are matched case-insensitively and include both languages,
// since the labels themselves are compile-time strings we can't enumerate at
// runtime.
//
// Labels are written in Russian and translated through ui-text.ts, like the
// rest of the UI — they used to be English-only and rendered raw, so a Russian
// admin searching "страйк" got an English "Strike system" back.

export type SettingEntry = {
  feature: string; // feature id — the target page is /guilds/{id}/features/{feature}
  label: string; // shown in the palette, via tt()
  keywords: string[];
};

export const SETTINGS_INDEX: SettingEntry[] = [
  // AutoMod
  { feature: 'automod', label: 'Блокировка инвайтов', keywords: ['invite', 'discord.gg', 'инвайт', 'приглашен'] },
  { feature: 'automod', label: 'Блокировка внешних ссылок', keywords: ['link', 'url', 'domain', 'ссылк', 'домен'] },
  { feature: 'automod', label: 'Пороги анти-спама', keywords: ['spam', 'flood', 'спам', 'флуд'] },
  { feature: 'automod', label: 'Лимит упоминаний', keywords: ['mention', 'ping', 'меншен', 'упоминан'] },
  { feature: 'automod', label: 'Система страйков', keywords: ['strike', 'escalation', 'страйк', 'эскалац'] },
  { feature: 'automod', label: 'Свои regex-фильтры', keywords: ['regex', 'pattern', 'filter', 'регекс', 'фильтр'] },
  { feature: 'automod', label: 'Пробный режим AutoMod', keywords: ['dry', 'test mode', 'пробн'] },
  { feature: 'automod', label: 'Исключения AutoMod', keywords: ['exempt', 'ignore', 'bypass', 'исключен', 'игнор'] },
  // Moderation
  { feature: 'moderation', label: 'Роли модераторов', keywords: ['permission', 'mod role', 'права', 'роли модератор'] },
  { feature: 'moderation', label: 'Авто-эскалация предупреждений', keywords: ['warn', 'warning', 'предупрежден', 'варн'] },
  // Anti-raid
  { feature: 'anti-raid', label: 'Пороги анти-рейда', keywords: ['raid', 'join spike', 'рейд', 'заход'] },
  // Verification
  { feature: 'verification', label: 'Роль верифицированного', keywords: ['verify', 'verification', 'gate', 'верифиц', 'верифика'] },
  // Welcome
  { feature: 'welcome-message', label: 'Приветственное сообщение', keywords: ['welcome', 'greeting', 'приветств'] },
  { feature: 'welcome-message', label: 'Авто-роль', keywords: ['autorole', 'auto role', 'авторол'] },
  // Levels
  { feature: 'levels', label: 'Канал и награды за уровни', keywords: ['level', 'xp', 'rank', 'уров', 'опыт'] },
  { feature: 'levels', label: 'Голосовой опыт и множители', keywords: ['voice', 'multiplier', 'голосов', 'множител'] },
  { feature: 'levels', label: 'Престиж и сезоны', keywords: ['prestige', 'season', 'престиж', 'сезон'] },
  // Tickets
  { feature: 'tickets', label: 'Роль поддержки и категория тикетов', keywords: ['ticket', 'support', 'тикет', 'поддержк'] },
  { feature: 'tickets', label: 'Автозакрытие тикетов', keywords: ['auto-close', 'autoclose', 'inactive', 'автозакрыт'] },
  // Logging
  { feature: 'logging', label: 'Каналы логов', keywords: ['log', 'audit channel', 'лог', 'журнал'] },
  // Banned words (merged into AutoMod)
  { feature: 'automod', label: 'Запрещённые слова', keywords: ['word', 'banned', 'blacklist', 'filter', 'слов', 'мат', 'фильтр'] },
  // Role menus
  { feature: 'reaction-menus', label: 'Меню ролей (стиль, роли)', keywords: ['role menu', 'button', 'dropdown', 'reaction', 'меню ролей', 'кнопк', 'реакц'] },
  { feature: 'reaction-menus', label: 'Реакция на существующем сообщении', keywords: ['reaction role', 'existing message', 'роль за реакц', 'существующ'] },
  // Rules / scheduled
  { feature: 'rules', label: 'Канал и текст правил', keywords: ['rules', 'правил'] },
  { feature: 'scheduled-messages', label: 'Отложенные сообщения', keywords: ['schedule', 'announce', 'расписан', 'отложен', 'анонс'] },
];

/**
 * Entries whose label — in either language — or any keyword contains the query.
 *
 * `translate` is required, not defaulted: the label is stored in Russian, so an
 * English admin searching "threshold" only finds it through the translation.
 * A default would let a caller silently drop half the index.
 */
export function searchSettings(query: string, translate: (label: string) => string): SettingEntry[] {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];
  return SETTINGS_INDEX.filter(
    (e) =>
      e.label.toLowerCase().includes(q) ||
      translate(e.label).toLowerCase().includes(q) ||
      e.keywords.some((k) => k.includes(q))
  );
}
