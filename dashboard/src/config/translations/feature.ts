import { provider } from './provider';
import { createI18n } from '@/utils/i18n';

export const feature = createI18n(provider, {
  en: {
    unsaved: 'Save Changes',
    error: {
      'not enabled': 'Not Enabled',
      'not enabled description': 'Try enable this feature?',
      'not found': 'Not Found',
      'not found description': "Hmm... Weird we can't find it",
    },
    bn: {
      enable: 'Enable Feature',
      disable: 'Disable',
      save: 'Save',
      discard: 'Discard',
    },
  },
  ru: {
    unsaved: 'Сохранить изменения',
    error: {
      'not enabled': 'Не включено',
      'not enabled description': 'Включить эту функцию?',
      'not found': 'Не найдено',
      'not found description': 'Хм... странно, не можем это найти',
    },
    bn: {
      enable: 'Включить функцию',
      disable: 'Выключить',
      save: 'Сохранить',
      discard: 'Отменить',
    },
  },
});
