import { provider } from './provider';
import { createI18n } from '@/utils/i18n';

export const guild = createI18n(provider, {
  en: {
    features: 'Features',
    banner: {
      title: 'Getting Started',
      description: 'Create your bot and type something',
    },
    error: {
      'not found': 'Where is it?',
      'not found description': "The bot can't access the server, let's invite him!",
      load: 'Failed to load guild',
    },
    bn: {
      'enable feature': 'Enable',
      'config feature': 'Config',
      invite: 'Invite bot',
      settings: 'Overview',
      moderation: 'Moderation',
      members: 'Members',
      tickets: 'Tickets',
      audit: 'Audit log',
      analytics: 'Analytics',
    },
  },
  ru: {
    features: 'Функции',
    banner: {
      title: 'Начало работы',
      description: 'Настройте бота за пару кликов',
    },
    error: {
      'not found': 'Где же он?',
      'not found description': 'Бот не на сервере — давайте пригласим его!',
      load: 'Не удалось загрузить сервер',
    },
    bn: {
      'enable feature': 'Включить',
      'config feature': 'Настроить',
      invite: 'Пригласить бота',
      settings: 'Обзор',
      moderation: 'Модерация',
      members: 'Участники',
      tickets: 'Тикеты',
      audit: 'Журнал',
      analytics: 'Аналитика',
    },
  },
});
