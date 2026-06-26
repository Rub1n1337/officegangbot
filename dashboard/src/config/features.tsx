import { Icon } from '@chakra-ui/react';
import { MdMessage, MdSecurity, MdHistory, MdAddReaction, MdPeople, MdBlock } from 'react-icons/md';
import { FeaturesConfig } from './types';
import { useWelcomeMessageFeature } from './feature-forms/WelcomeMessageFeature';
import { useRulesFeature } from './feature-forms/RulesFeature';
import { useReactionRoleFeature } from './feature-forms/ReactionRoleFeature';
import { useLoggingFeature } from './feature-forms/LoggingFeature';
import { useModerationFeature } from './feature-forms/ModerationFeature';
import { useFilterFeature } from './feature-forms/FilterFeature';

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
