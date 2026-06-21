import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { SimpleGrid } from '@chakra-ui/react';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { InputForm } from '@/components/forms/InputForm';
import type { ReactionRoleFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  channelId: z.string().optional(),
  messageId: z.string().optional(),
  emoji: z.string().min(1, 'Emoji is required'),
  roleId: z.string().optional(),
});

type Input = z.infer<typeof schema>;

export const useReactionRoleFeature: UseFormRender<ReactionRoleFeature> = (data: ReactionRoleFeature, onSubmit: (data: string) => Promise<any>) => {
  const { register, reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      channelId: data.channelId ?? undefined,
      messageId: data.messageId ?? undefined,
      emoji: data.emoji || '✅',
      roleId: data.roleId ?? undefined,
    },
  });

  return {
    component: (
      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
        <ChannelSelectForm
          control={{
            label: 'Channel',
            description: 'Select the channel containing the message',
          }}
          controller={{ control, name: 'channelId' }}
        />
        <InputForm
          control={{
            label: 'Message ID',
            description: 'Enter the ID of the message for reactions',
            error: formState.errors.messageId?.message,
          }}
          placeholder="123456789012345678"
          {...register('messageId')}
        />
        <InputForm
          control={{
            label: 'Emoji',
            description: 'The emoji to react with',
            error: formState.errors.emoji?.message,
          }}
          placeholder="✅"
          {...register('emoji')}
        />
        <RoleSelectForm
          control={{
            label: 'Role',
            description: 'The role to assign on reaction',
          }}
          controller={{ control, name: 'roleId' }}
        />
      </SimpleGrid>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          channelId: e.channelId,
          messageId: e.messageId,
          emoji: e.emoji,
          roleId: e.roleId,
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
