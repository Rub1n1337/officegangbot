import { Icon } from '@chakra-ui/react';
import { MdMessage, MdSecurity, MdHistory, MdAddReaction, MdPeople } from 'react-icons/md';
import { FeaturesConfig } from './types';
import { useWelcomeMessageFeature } from './example/WelcomeMessageFeature';
import { useRulesFeature } from './example/RulesFeature';

export const features: FeaturesConfig = {
  'rules': {
    name: 'Rules',
    description: 'Configure server rules channel and message',
    icon: <Icon as={MdMessage} />,
    useRender: useRulesFeature,
  },
  'welcome-message': {
    name: 'Welcome Message',
    description: 'Send a welcome message when a user joins the server',
    icon: <Icon as={MdPeople} />,
    useRender: useWelcomeMessageFeature,
  },
  'reaction-role': {
    name: 'Reaction Role',
    description: 'Assign roles when users react to a message',
    icon: <Icon as={MdAddReaction} />,
    useRender() {
      return {
        component: <p style={{color: 'gray'}}>Reaction Role configuration coming soon.</p>,
        onSubmit: () => {},
      };
    },
  },
  'moderation': {
    name: 'Moderation',
    description: 'Configure moderation roles and settings',
    icon: <Icon as={MdSecurity} />,
    useRender() {
      return {
        component: <p style={{color: 'gray'}}>Moderation configuration coming soon.</p>,
        onSubmit: () => {},
      };
    },
  },
  'logging': {
    name: 'Logging',
    description: 'Configure logging channels for moderation events',
    icon: <Icon as={MdHistory} />,
    useRender() {
      return {
        component: <p style={{color: 'gray'}}>Logging configuration coming soon.</p>,
        onSubmit: () => {},
      };
    },
  },
};
