import { provider } from './provider';
import { createI18n } from '@/utils/i18n';

export const dashboard = createI18n(provider, {
  en: {
    pricing: 'Pricing',
    learn_more: 'Learn More',
    invite: {
      title: 'Invite our Bot',
      description: 'Try our discord bot with one-click',
      bn: 'Invite now',
    },
    servers: {
      title: 'Select Server',
      description: 'Select the server to configure',
    },
    vc: {
      create: 'Create a voice channel',
      'created channels': 'Created Voice channels',
    },
    command: {
      title: 'Command Usage',
      description: 'Use of commands of your server',
    },
  },
  ru: {
    pricing: 'Тарифы',
    learn_more: 'Подробнее',
    invite: {
      title: 'Пригласить бота',
      description: 'Подключите Discord-бота в один клик',
      bn: 'Пригласить',
    },
    servers: {
      title: 'Выбор сервера',
      description: 'Выберите сервер для настройки',
    },
    vc: {
      create: 'Создать голосовой канал',
      'created channels': 'Созданные голосовые каналы',
    },
    command: {
      title: 'Использование команд',
      description: 'Использование команд на сервере',
    },
  },
});
