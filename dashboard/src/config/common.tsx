import { createIcon } from '@chakra-ui/react';
import { PermissionFlags } from '@/api/discord';
import { AppConfig } from './types';

const BotIcon = createIcon({
  displayName: 'OfficeGangBotLogo',
  viewBox: '0 0 512 512',
  path: (
    <g>
      <path
        d="m494.6,241.1l-50.1-47c-50.5-47.3-117.4-73.3-188.5-73.3-71.1,0-138,26-188.4,73.3l-50.1,47c-12.1,12.9-4.3,26.5 0,29.8l50.1,47c50.4,47.3 117.3,73.3 188.4,73.3 71.1,0 138-26 188.4-73.3l50.1-47c4.7-3.9 12.2-17.6 0.1-29.8zm-238.6,74.9c-33.1,0-60-26.9-60-60 0-33.1 26.9-60 60-60 33.1,0 60,26.9 60,60 0,33.1-26.9,60-60,60zm-194.7-60l34.3-32.1c32-30 72-49.9 115.5-58.1-33.1,16.6-55.8,50.8-55.8,90.2 0,39.4 22.8,73.7 55.8,90.2-43.5-8.1-83.5-28.1-115.5-58.1l-34.3-32.1zm355.2,32.1c-32,30-72,50-115.5,58.1 33.1-16.6 55.8-50.8 55.8-90.2 0-39.4-22.8-73.6-55.8-90.2 43.5,8.1 83.5,28.1 115.5,58.1l34.3,32.1-34.3,32.1z"
        fill="currentColor"
      />
    </g>
  ),
});

export const config: AppConfig = {
  name: 'OfficeGangBot',
  icon: BotIcon,
  inviteUrl:
    'https://discord.com/api/oauth2/authorize?client_id=1220462982384058370&permissions=8&scope=bot%20applications.commands&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fapi%2Fauth%2Fcallback&response_type=code',
  guild: {
    filter: (guild) => (Number(guild.permissions) & PermissionFlags.ADMINISTRATOR) !== 0,
  },
};
