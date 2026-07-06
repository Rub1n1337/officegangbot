import { Icon } from '@chakra-ui/react';
import {
  MdMessage,
  MdSecurity,
  MdHistory,
  MdAddReaction,
  MdPeople,
  MdTrendingUp,
  MdGppGood,
  MdConfirmationNumber,
  MdSchedule,
  MdList,
  MdCrisisAlert,
  MdVerifiedUser,
} from 'react-icons/md';
import { FeaturesConfig } from './types';
import { useWelcomeMessageFeature } from './feature-forms/WelcomeMessageFeature';
import { useRulesFeature } from './feature-forms/RulesFeature';
import { useReactionRoleFeature } from './feature-forms/ReactionRoleFeature';
import { useLoggingFeature } from './feature-forms/LoggingFeature';
import { useModerationFeature } from './feature-forms/ModerationFeature';
import { useLevelsFeature } from './feature-forms/LevelsFeature';
import { useAutomodFeature } from './feature-forms/AutomodFeature';
import { useTicketsFeature } from './feature-forms/TicketsFeature';
import { useScheduledMessagesFeature } from './feature-forms/ScheduledMessagesFeature';
import { useReactionMenusFeature } from './feature-forms/ReactionMenusFeature';
import { useAntiRaidFeature } from './feature-forms/AntiRaidFeature';
import { useVerificationFeature } from './feature-forms/VerificationFeature';

// Ordered feature categories, used to group the feature grid and the sidebar.
export const featureCategories: { id: string; label: string }[] = [
  { id: 'engagement', label: 'Engagement' },
  { id: 'safety', label: 'Moderation & Safety' },
];

export const features: FeaturesConfig = {
  'rules': {
    name: 'Rules',
    description: 'Configure server rules channel and message',
    icon: <Icon as={MdMessage} />,
    category: 'engagement',
    useRender: useRulesFeature,
  },
  'welcome-message': {
    name: 'Welcome Message',
    description: 'Send a welcome message when a user joins the server',
    icon: <Icon as={MdPeople} />,
    category: 'engagement',
    useRender: useWelcomeMessageFeature,
  },
  'reaction-role': {
    name: 'Reaction Role',
    description: 'Assign roles when users react to a message',
    icon: <Icon as={MdAddReaction} />,
    category: 'engagement',
    useRender: useReactionRoleFeature,
  },
  'reaction-menus': {
    name: 'Role Menus',
    description: 'Post an embed members react to for roles',
    icon: <Icon as={MdList} />,
    category: 'engagement',
    useRender: useReactionMenusFeature,
  },
  'levels': {
    name: 'Levels',
    description: 'XP, level-up announcements and role rewards',
    icon: <Icon as={MdTrendingUp} />,
    category: 'engagement',
    useRender: useLevelsFeature,
  },
  'scheduled-messages': {
    name: 'Scheduled Messages',
    description: 'Post one-off or recurring announcements at a set time',
    icon: <Icon as={MdSchedule} />,
    category: 'engagement',
    useRender: useScheduledMessagesFeature,
  },
  'moderation': {
    name: 'Moderator Roles',
    description: 'Which roles can use each moderation command',
    icon: <Icon as={MdSecurity} />,
    category: 'safety',
    useRender: useModerationFeature,
  },
  'logging': {
    name: 'Logging',
    description: 'Configure logging channels for moderation events',
    icon: <Icon as={MdHistory} />,
    category: 'safety',
    useRender: useLoggingFeature,
  },
  'automod': {
    name: 'AutoMod',
    description: 'Anti-spam, banned words, invite/link blocking and strikes',
    icon: <Icon as={MdGppGood} />,
    category: 'safety',
    useRender: useAutomodFeature,
  },
  'tickets': {
    name: 'Tickets',
    description: 'Support ticket system with an Open Ticket button',
    icon: <Icon as={MdConfirmationNumber} />,
    category: 'safety',
    useRender: useTicketsFeature,
  },
  'anti-raid': {
    name: 'Anti-Raid',
    description: 'Detect join spikes and act on the raiders automatically',
    icon: <Icon as={MdCrisisAlert} />,
    category: 'safety',
    useRender: useAntiRaidFeature,
  },
  'verification': {
    name: 'Verification',
    description: 'A Verify button that grants new members a role',
    icon: <Icon as={MdVerifiedUser} />,
    category: 'safety',
    useRender: useVerificationFeature,
  },
};
