import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { SimpleGrid } from '@chakra-ui/react';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import type { LoggingFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  logChannel: z.string().optional(),
});

type Input = z.infer<typeof schema>;

export const useLoggingFeature: UseFormRender<LoggingFeature> = (data: LoggingFeature, onSubmit: (data: string) => Promise<any>) => {
  const { reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      logChannel: data.logChannel ?? undefined,
    },
  });

  return {
    component: (
      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
        <ChannelSelectForm
          control={{
            label: 'Punishment Log Channel',
            description: 'Select the channel for moderation and punishment logs',
          }}
          controller={{ control, name: 'logChannel' }}
        />
      </SimpleGrid>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          logChannel: e.logChannel,
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
