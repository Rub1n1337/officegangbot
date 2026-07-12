import { provider } from './provider';
import { createI18n } from '@/utils/i18n';

export const auth = createI18n(provider, {
  en: {
    login: 'Sign in',
    'login description': 'Login and start using our bot today',
    login_bn: 'Login with Discord',
  },
  ru: {
    login: 'Вход',
    'login description': 'Войдите и начните пользоваться ботом',
    login_bn: 'Войти через Discord',
  },
});
