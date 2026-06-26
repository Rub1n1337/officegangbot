import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { SimpleGrid } from '@chakra-ui/react';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import type { LoggingFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  logChannel: z.string().optional(),
  usageChannel: z.string().optional(),
  messagesChannel: z.string().optional(),
  leaveChannel: z.string().optional(),
});

type Input = z.infer<typeof schema>;

export const useLoggingFeature: UseFormRender<LoggingFeature> = (data: LoggingFeature, onSubmit: (data: string) => Promise<any>) => {
  const { reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      logChannel: data.logChannel ?? undefined,
      usageChannel: data.usageChannel ?? undefined,
      messagesChannel: data.messagesChannel ?? undefined,
      leaveChannel: data.leaveChannel ?? undefined,
    },
  });

  return {
    component: (
      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
        <ChannelSelectForm
          control={{
            label: 'Punishment Log Channel',
            description: 'Bans, kicks, mutes, warns and filtered messages',
          }}
          controller={{ control, name: 'logChannel' }}
        />
        <ChannelSelectForm
          control={{
            label: 'Command Usage Log Channel',
            description: 'Logs every bot command that is run',
          }}
          controller={{ control, name: 'usageChannel' }}
        />
        <ChannelSelectForm
          control={{
            label: 'Message Log Channel',
            description: 'Edited and deleted messages',
          }}
          controller={{ control, name: 'messagesChannel' }}
        />
        <ChannelSelectForm
          control={{
            label: 'Leave Log Channel',
            description: 'Notifications when a member leaves',
          }}
          controller={{ control, name: 'leaveChannel' }}
        />
      </SimpleGrid>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          logChannel: e.logChannel,
          usageChannel: e.usageChannel,
          messagesChannel: e.messagesChannel,
          leaveChannel: e.leaveChannel,
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
