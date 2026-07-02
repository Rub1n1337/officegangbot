import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { SimpleGrid } from '@chakra-ui/react';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { useFormText } from '@/config/translations/form-text';
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
  const ft = useFormText();
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
            label: ft('Punishment Log Channel'),
            description: ft('Bans, kicks, mutes, warns and filtered messages'),
          }}
          controller={{ control, name: 'logChannel' }}
        />
        <ChannelSelectForm
          control={{
            label: ft('Command Usage Log Channel'),
            description: ft('Logs every bot command that is run'),
          }}
          controller={{ control, name: 'usageChannel' }}
        />
        <ChannelSelectForm
          control={{
            label: ft('Message Log Channel'),
            description: ft('Edited and deleted messages'),
          }}
          controller={{ control, name: 'messagesChannel' }}
        />
        <ChannelSelectForm
          control={{
            label: ft('Leave Log Channel'),
            description: ft('Notifications when a member leaves'),
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
