import { useMemo, type ReactNode } from 'react';
import { provider } from '@/config/translations/provider';

// Russian overrides for feature names/descriptions and category labels. These
// live in the static `features` config (English) and aren't in the createI18n
// system, so we override them at render time when the locale is ru and fall back
// to the original English otherwise. (No cn here — it falls back to English.)
type Meta = { name: string; description: string };

const RU_FEATURES: Record<string, Meta> = {
  rules: { name: 'Правила', description: 'Канал и сообщение с правилами сервера' },
  'welcome-message': { name: 'Приветствие', description: 'Отправлять приветствие при входе участника' },
  'reaction-menus': { name: 'Меню ролей', description: 'Роли через меню (реакции, кнопки, дропдаун) или реакции на существующих сообщениях' },
  levels: { name: 'Уровни', description: 'Опыт, анонсы повышения уровня и награды-роли' },
  'scheduled-messages': { name: 'Отложенные сообщения', description: 'Разовые или повторяющиеся анонсы по расписанию' },
  moderation: { name: 'Настройки модерации', description: 'Права команд по ролям и авто-эскалация предупреждений' },
  logging: { name: 'Логирование', description: 'Каналы для логов событий модерации' },
  automod: { name: 'Авто-модерация', description: 'Анти-спам, запрещённые слова, блокировка инвайтов/ссылок и страйки' },
  tickets: { name: 'Тикеты', description: 'Система тикетов поддержки с кнопкой «Открыть тикет»' },
  'anti-raid': { name: 'Анти-рейд', description: 'Обнаружение всплеска заходов и автоматические меры против рейдеров' },
  verification: { name: 'Верификация', description: 'Кнопка «Верифицироваться», выдающая новым участникам роль' },
};

const RU_CATEGORIES: Record<string, string> = {
  engagement: 'Вовлечённость',
  safety: 'Модерация и безопасность',
};

export function useFeatureMeta() {
  const lang = provider.useLang();
  // Stable per language, so callers can list it in hook deps.
  return useMemo(
    () => ({
      feature(id: string, name: ReactNode, description: ReactNode): { name: ReactNode; description: ReactNode } {
        if (lang === 'ru' && RU_FEATURES[id]) return RU_FEATURES[id];
        return { name, description };
      },
      category(id: string, label: string): string {
        if (lang === 'ru' && RU_CATEGORIES[id]) return RU_CATEGORIES[id];
        return label;
      },
    }),
    [lang]
  );
}
