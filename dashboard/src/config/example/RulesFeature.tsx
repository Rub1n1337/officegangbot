import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { SimpleGrid } from '@chakra-ui/react';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { TextAreaForm } from '@/components/forms/TextAreaForm';
import type { RulesFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  channel: z.string().optional(),
  message: z.string().min(10, 'Rules message must be at least 10 characters'),
});

type Input = z.infer<typeof schema>;

export const useRulesFeature: UseFormRender<RulesFeature> = (data: RulesFeature, onSubmit: (data: string) => Promise<any>) => {
  const { register, reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      channel: data.channel ?? undefined,
      message: data.message || '',
    },
  });

  return {
    component: (
      <SimpleGrid columns={1} gap={3}>
        <ChannelSelectForm
          control={{
            label: 'Rules Channel',
            description: 'Select the channel where rules will be posted',
          }}
          controller={{ control, name: 'channel' }}
        />
        <TextAreaForm
          control={{
            label: 'Rules Message',
            description: 'Enter the server rules. A scrollbar appears when the text is longer than the box.',
            error: formState.errors.message?.message,
          }}
          placeholder="Be respectful..."
          h="260px"
          resize="vertical"
          overflowY="auto"
          {...register('message')}
        />
      </SimpleGrid>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          message: e.message,
          channel: e.channel,
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
