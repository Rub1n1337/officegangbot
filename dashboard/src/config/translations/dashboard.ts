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
  cn: {
    pricing: '價錢',
    learn_more: '了解更多',
    invite: {
      title: '邀請我們的機器人',
      description: '一鍵試用我們的 Discord 機器人',
      bn: '現在邀請',
    },
    servers: {
      title: '選擇服務器',
      description: '自定義您的服務器',
    },
    vc: {
      create: '創建語音通道',
      'created channels': '已創建語音頻道',
    },
    command: {
      title: '命令使用量',
      description: '使用你的服務器命令使用量',
    },
  },
});
