import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Button, Flex, IconButton, SimpleGrid, Text } from '@chakra-ui/react';
import { MdAdd, MdDelete } from 'react-icons/md';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { InputForm } from '@/components/forms/InputForm';
import type { ReactionRoleFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const itemSchema = z.object({
  channelId: z.string().optional(),
  messageId: z.string().optional(),
  emoji: z.string().min(1, 'Emoji is required'),
  roleId: z.string().optional(),
});

const schema = z.object({
  items: z.array(itemSchema),
});

type Input = z.infer<typeof schema>;

export const useReactionRoleFeature: UseFormRender<ReactionRoleFeature> = (
  data: ReactionRoleFeature,
  onSubmit: (data: string) => Promise<any>
) => {
  const { register, reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      items: (data.items ?? []).map((it) => ({
        channelId: it.channelId ?? undefined,
        messageId: it.messageId ?? undefined,
        emoji: it.emoji || '✅',
        roleId: it.roleId ?? undefined,
      })),
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'items' });

  return {
    component: (
      <Flex direction="column" gap={3}>
        {fields.length === 0 && (
          <Text color="TextSecondary">
            No reaction roles yet. Add one to grant a role when a member reacts to a message.
          </Text>
        )}
        {fields.map((field, index) => (
          <Box key={field.id} bg="CardBackground" rounded="2xl" p={4} position="relative">
            <Flex justify="space-between" align="center" mb={2}>
              <Text fontWeight="600">Reaction role #{index + 1}</Text>
              <IconButton
                aria-label="Remove reaction role"
                icon={<MdDelete />}
                size="sm"
                variant="danger"
                onClick={() => remove(index)}
              />
            </Flex>
            <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
              <ChannelSelectForm
                control={{ label: 'Channel', description: 'Channel containing the message' }}
                controller={{ control, name: `items.${index}.channelId` }}
              />
              <InputForm
                control={{
                  label: 'Message ID',
                  description: 'ID of the message to watch',
                  error: formState.errors.items?.[index]?.messageId?.message,
                }}
                placeholder="123456789012345678"
                {...register(`items.${index}.messageId`)}
              />
              <InputForm
                control={{
                  label: 'Emoji',
                  description: 'Emoji members react with',
                  error: formState.errors.items?.[index]?.emoji?.message,
                }}
                placeholder="✅"
                {...register(`items.${index}.emoji`)}
              />
              <RoleSelectForm
                control={{ label: 'Role', description: 'Role to grant on reaction' }}
                controller={{ control, name: `items.${index}.roleId` }}
              />
            </SimpleGrid>
          </Box>
        ))}
        <Button
          leftIcon={<MdAdd />}
          variant="action"
          alignSelf="flex-start"
          onClick={() => append({ channelId: undefined, messageId: '', emoji: '✅', roleId: undefined })}
        >
          Add reaction role
        </Button>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(JSON.stringify({ items: e.items }));
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
