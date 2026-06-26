import { Icon } from '@chakra-ui/react';
import { MdMessage, MdSecurity, MdHistory, MdAddReaction, MdPeople, MdBlock } from 'react-icons/md';
import { FeaturesConfig } from './types';
import { useWelcomeMessageFeature } from './example/WelcomeMessageFeature';
import { useRulesFeature } from './example/RulesFeature';
import { useReactionRoleFeature } from './example/ReactionRoleFeature';
import { useLoggingFeature } from './example/LoggingFeature';
import { useModerationFeature } from './example/ModerationFeature';
import { useFilterFeature } from './example/FilterFeature';

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
    useRender: useReactionRoleFeature,
  },
  'moderation': {
    name: 'Moderation',
    description: 'Configure moderation roles and settings',
    icon: <Icon as={MdSecurity} />,
    useRender: useModerationFeature,
  },
  'logging': {
    name: 'Logging',
    description: 'Configure logging channels for moderation events',
    icon: <Icon as={MdHistory} />,
    useRender: useLoggingFeature,
  },
  'filter': {
    name: 'Word Filter',
    description: 'Automatically delete messages containing banned words',
    icon: <Icon as={MdBlock} />,
    useRender: useFilterFeature,
  },
};
