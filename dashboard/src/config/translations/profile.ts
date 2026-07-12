import { createI18n } from '@/utils/i18n';
import { common } from './common';
import { provider } from './provider';

export const profile = createI18n(provider, {
  en: {
    logout: common.translations.en.logout,
    language: 'Language',
    'language description': 'Select your language',
    settings: 'Settings',
    'dark mode': 'Dark Mode',
    'dark mode description': 'Enables dark theme in order to protect your eyes',
    'dev mode': 'Developer Mode',
    'dev mode description': 'Used for debugging and testing',
  },
  ru: {
    logout: common.translations.ru.logout,
    language: 'Язык',
    'language description': 'Выберите язык',
    settings: 'Настройки',
    'dark mode': 'Тёмная тема',
    'dark mode description': 'Включает тёмную тему, чтобы беречь глаза',
    'dev mode': 'Режим разработчика',
    'dev mode description': 'Для отладки и тестирования',
  },
});
