import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Divider, Flex, SimpleGrid, Text } from '@chakra-ui/react';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { TextAreaForm } from '@/components/forms/TextAreaForm';
import { EmojiPickerInput } from '@/components/forms/EmojiPickerInput';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { SwitchFieldForm } from '@/components/forms/SwitchField';
import { RulesPreview } from '@/components/feature/RulesPreview';
import type { RulesFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  channel: z.string().optional(),
  message: z
    .string()
    .min(10, 'Rules message must be at least 10 characters')
    .max(4000, 'Rules message is too long (max 4000 characters)'),
  reactionEnabled: z.boolean(),
  reactionEmoji: z.string().optional(),
  reactionRole: z.string().optional(),
});

type Input = z.infer<typeof schema>;

export const useRulesFeature: UseFormRender<RulesFeature> = (data: RulesFeature, onSubmit: (data: string) => Promise<any>) => {
  const { register, reset, handleSubmit, formState, control, watch } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      channel: data.channel ?? undefined,
      message: data.message || '',
      reactionEnabled: data.reactionEnabled ?? false,
      reactionEmoji: data.reactionEmoji || '✅',
      reactionRole: data.reactionRole ?? undefined,
    },
  });

  const reactionEnabled = watch('reactionEnabled');
  const message = watch('message');
  const reactionEmoji = watch('reactionEmoji');

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
        <Box>
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
          <Flex justify="flex-end" mt={1}>
            <Text fontSize="xs" color={(message?.length ?? 0) > 4000 ? 'red.400' : 'TextSecondary'}>
              {(message?.length ?? 0).toLocaleString()} / 4,000
            </Text>
          </Flex>
        </Box>
        <Divider my={1} />
        <SwitchFieldForm
          control={{
            label: 'Reaction Role',
            description: 'Add a reaction to the rules message that grants a role when clicked',
          }}
          controller={{ control, name: 'reactionEnabled' }}
        />
        {reactionEnabled && (
          <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
            <EmojiPickerInput
              control={{
                label: 'Reaction Emoji',
                description: 'Emoji members react with to accept the rules',
              }}
              controller={{ control, name: 'reactionEmoji' }}
              placeholder="✅"
            />
            <RoleSelectForm
              control={{
                label: 'Reaction Role',
                description: 'Role granted when a member reacts',
              }}
              controller={{ control, name: 'reactionRole' }}
            />
          </SimpleGrid>
        )}
        <Divider my={1} />
        <RulesPreview
          message={message ?? ''}
          reactionEnabled={reactionEnabled}
          reactionEmoji={reactionEmoji}
        />
      </SimpleGrid>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          message: e.message,
          channel: e.channel,
          reactionEnabled: e.reactionEnabled ?? false,
          reactionEmoji: e.reactionEmoji,
          reactionRole: e.reactionRole ?? null,
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
