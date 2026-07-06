import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Divider, Flex, SimpleGrid, Text } from '@chakra-ui/react';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { TextAreaForm } from '@/components/forms/TextAreaForm';
import { RulesPreview } from '@/components/feature/RulesPreview';
import { useFormText } from '@/config/translations/form-text';
import type { RulesFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  channel: z.string().optional(),
  message: z
    .string()
    .min(10, 'Rules message must be at least 10 characters')
    .max(4000, 'Rules message is too long (max 4000 characters)'),
});

type Input = z.infer<typeof schema>;

export const useRulesFeature: UseFormRender<RulesFeature> = (data: RulesFeature, onSubmit: (data: string) => Promise<any>) => {
  const ft = useFormText();
  const { register, reset, handleSubmit, formState, control, watch } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      channel: data.channel ?? undefined,
      message: data.message || '',
    },
  });

  const message = watch('message');

  return {
    component: (
      <SimpleGrid columns={1} gap={3}>
        <ChannelSelectForm
          control={{
            label: ft('Rules Channel'),
            description: ft('Select the channel where rules will be posted'),
          }}
          controller={{ control, name: 'channel' }}
        />
        <Box>
          <TextAreaForm
            control={{
              label: ft('Rules Message'),
              description: ft('Enter the server rules. A scrollbar appears when the text is longer than the box.'),
              error: formState.errors.message?.message,
            }}
            placeholder={ft('Be respectful...')}
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
        <Text fontSize="sm" color="TextSecondary">
          {ft(
            'Want a role for accepting the rules? Add a reaction on the rules message under Role Menus → “Reactions on existing messages”, or use the Verification feature.'
          )}
        </Text>
        <Divider my={1} />
        <RulesPreview message={message ?? ''} />
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
