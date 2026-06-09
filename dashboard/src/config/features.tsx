import { Icon } from '@chakra-ui/react';
import { BsMusicNoteBeamed } from 'react-icons/bs';
import { FaGamepad } from 'react-icons/fa';
import { IoHappy, IoGameController } from 'react-icons/io5';
import { MdAddReaction, MdMessage } from 'react-icons/md';
import { FeaturesConfig } from './types';
import { provider } from '@/config/translations/provider';
import { createI18n } from '@/utils/i18n';
import { useWelcomeMessageFeature } from './example/WelcomeMessageFeature';
import { useMemeFeature } from './example/MemeFeature';

/**
 * Support i18n (Localization)
 */
const { T } = createI18n(provider, {
  en: {
    music: 'Music Player',
    'music description': 'Play music in Your Discord Server',
    gaming: 'Gaming',
    'gaming description': 'Enjoy playing games with your friends',
    'reaction role': 'Reaction Role',
    'reaction role description': 'Give user a role when clicking on a button',
    memes: 'Memes Time',
    'memes description': 'Send memes everyday',
  },
  cn: {
    music: '音樂播放器',
    'music description': '在您的 Discord 服務器中播放音樂',
    gaming: '遊戲',
    'gaming description': 'Enjoy playing games with your friends',
    'reaction role': '反應角色',
    'reaction role description': '單擊按鈕時為用戶賦予角色',
    memes: '模因時間',
    'memes description': '每天發送模因',
  },
});

/**
 * Define information for each features
 *
 * There is an example:
 */
export const features: FeaturesConfig = {
  // OfficeGangBot core features
  rules: {
    name: 'Rules',
    description: 'Configure server rules and rules channel',
    icon: <Icon as={MdMessage} />,
    useRender: require('@/config/example/RulesFeature').useRulesFeature,
  },
  'welcome-message': {
    name: 'Welcome Message',
    description: 'Send a message when a user joins the server',
    icon: <Icon as={MdMessage} />,
    useRender: useWelcomeMessageFeature,
  },
  'reaction-role': {
    name: <T text="reaction role" />,
    description: <T text="reaction role description" />,
    icon: <Icon as={MdAddReaction} />,
    useRender() {
      return {
        component: <></>, // TODO: Implement reaction role panel
        onSubmit: () => {},
      };
    },
  },
  moderation: {
    name: 'Moderation',
    description: 'Configure moderator and admin roles, mute role, etc.',
    icon: <Icon as={FaGamepad} />,
    useRender() {
      return {
        component: <></>, // TODO: Implement moderation panel
        onSubmit: () => {},
      };
    },
  },
  logging: {
    name: 'Logging',
    description: 'Configure logging channels and events',
    icon: <Icon as={MdMessage} />,
    useRender() {
      return {
        component: <></>, // TODO: Implement logging panel
        onSubmit: () => {},
      };
    },
  },
  // Demo/extra features
  music: {
    name: <T text="music" />,
    description: <T text="music description" />,
    icon: <Icon as={BsMusicNoteBeamed} />,
    useRender() {
      return {
        component: <></>,
        onSubmit: () => {},
      };
    },
  },
  'reaction-role': {
    name: <T text="reaction role" />,
    description: <T text="reaction role description" />,
    icon: <Icon as={MdAddReaction} />,
    useRender() {
      return {
        component: <></>,
        onSubmit: () => {},
      };
    },
  },
  meme: {
    name: <T text="memes" />,
    description: <T text="memes description" />,
    icon: <Icon as={IoHappy} />,
    useRender: useMemeFeature,
  },
};
