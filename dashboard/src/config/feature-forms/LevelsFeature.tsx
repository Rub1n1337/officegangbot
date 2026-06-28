import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Button, Divider, Flex, IconButton, SimpleGrid, Text } from '@chakra-ui/react';
import { MdAdd, MdDelete } from 'react-icons/md';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { InputForm } from '@/components/forms/InputForm';
import type { LevelsFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const rewardSchema = z.object({
  level: z
    .number({ invalid_type_error: 'Enter a level' })
    .int('Whole numbers only')
    .min(1, 'Level must be 1 or higher')
    .max(1000, 'Level is too high'),
  roleId: z.string().min(1, 'Pick a role'),
});

const schema = z.object({
  channel: z.string().optional(),
  rewards: z.array(rewardSchema),
});

type Input = z.infer<typeof schema>;

export const useLevelsFeature: UseFormRender<LevelsFeature> = (data, onSubmit) => {
  const { register, reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      channel: data.channel ?? undefined,
      rewards: (data.rewards ?? []).map((r) => ({
        level: r.level,
        roleId: r.roleId ?? undefined,
      })),
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'rewards' });

  return {
    component: (
      <Flex direction="column" gap={4}>
        <ChannelSelectForm
          control={{
            label: 'Level-up announcement channel',
            description: 'Where to post when a member levels up. Leave unset to announce in the channel they were chatting in.',
          }}
          controller={{ control, name: 'channel' }}
        />

        <Divider />

        <Box>
          <Text fontWeight="600">Role rewards</Text>
          <Text fontSize="sm" color="TextSecondary">
            Automatically grant a role when a member reaches a level.
          </Text>
        </Box>

        <Flex direction="column" gap={3}>
          {fields.length === 0 && (
            <Text color="TextSecondary">No role rewards yet. Add one below.</Text>
          )}
          {fields.map((field, index) => (
            <Box key={field.id} bg="CardBackground" rounded="2xl" p={4} position="relative">
              <Flex justify="space-between" align="center" mb={2}>
                <Text fontWeight="600">Reward #{index + 1}</Text>
                <IconButton
                  aria-label="Remove reward"
                  icon={<MdDelete />}
                  size="sm"
                  variant="danger"
                  onClick={() => remove(index)}
                />
              </Flex>
              <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
                <InputForm
                  control={{
                    label: 'Level',
                    description: 'Reach this level to earn the role',
                    error: formState.errors.rewards?.[index]?.level?.message,
                  }}
                  type="number"
                  min={1}
                  placeholder="5"
                  {...register(`rewards.${index}.level`, { valueAsNumber: true })}
                />
                <RoleSelectForm
                  control={{
                    label: 'Role',
                    description: 'Role to grant at this level',
                  }}
                  controller={{ control, name: `rewards.${index}.roleId` }}
                />
              </SimpleGrid>
            </Box>
          ))}
          <Button
            leftIcon={<MdAdd />}
            variant="action"
            alignSelf="flex-start"
            onClick={() => append({ level: 1, roleId: undefined as unknown as string })}
          >
            Add reward
          </Button>
        </Flex>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({ channel: e.channel, rewards: e.rewards })
      );
      reset({
        ...result,
        channel: result.channel ?? undefined,
        rewards: (result.rewards ?? []).map((r) => ({
          level: r.level,
          roleId: r.roleId ?? undefined,
        })),
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
