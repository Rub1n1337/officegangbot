import { Box, Flex, SimpleGrid, Text } from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { CategorySelectForm } from '@/components/forms/CategorySelect';
import type { TicketsFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  supportRole: z.string().optional(),
  category: z.string().optional(),
});

type Input = z.infer<typeof schema>;

export const useTicketsFeature: UseFormRender<TicketsFeature> = (data, onSubmit) => {
  const { reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      supportRole: data.supportRole ?? undefined,
      category: data.category ?? undefined,
    },
  });

  return {
    component: (
      <Flex direction="column" gap={3}>
        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
          <RoleSelectForm
            control={{
              label: 'Support role',
              description: 'Role that can see and respond to ticket channels',
            }}
            controller={{ control, name: 'supportRole' }}
          />
          <CategorySelectForm
            control={{
              label: 'Ticket category',
              description: 'New ticket channels are created under this category',
            }}
            controller={{ control, name: 'category' }}
          />
        </SimpleGrid>
        <Box bg="CardBackground" rounded="xl" p={4}>
          <Text fontSize="sm" color="TextSecondary">
            After saving, run{' '}
            <Text as="span" fontWeight="600" color="TextPrimary">
              /ticket_setup
            </Text>{' '}
            in Discord to post the “Open Ticket” panel in the channel of your choice.
          </Text>
        </Box>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({ supportRole: e.supportRole, category: e.category })
      );
      reset({
        ...result,
        supportRole: result.supportRole ?? undefined,
        category: result.category ?? undefined,
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
