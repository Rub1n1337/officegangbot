import { Box, Flex, FormControl, FormLabel, SimpleGrid, Text } from '@chakra-ui/react';
import { NumberStepper } from '@/components/forms/NumberStepper';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { CategorySelectForm } from '@/components/forms/CategorySelect';
import { useFormText } from '@/config/translations/form-text';
import type { TicketsFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  supportRole: z.string().optional(),
  category: z.string().optional(),
  autoCloseHours: z.number().int().min(0).max(720),
});

type Input = z.infer<typeof schema>;

export const useTicketsFeature: UseFormRender<TicketsFeature> = (data, onSubmit) => {
  const ft = useFormText();
  const { reset, handleSubmit, formState, control, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      supportRole: data.supportRole ?? undefined,
      category: data.category ?? undefined,
      autoCloseHours: data.autoCloseHours ?? 0,
    },
  });

  const autoCloseHours = watch('autoCloseHours');

  return {
    component: (
      <Flex direction="column" gap={3}>
        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
          <RoleSelectForm
            control={{
              label: ft('Support role'),
              description: ft('Role that can see and respond to ticket channels'),
            }}
            controller={{ control, name: 'supportRole' }}
          />
          <CategorySelectForm
            control={{
              label: ft('Ticket category'),
              description: ft('New ticket channels are created under this category'),
            }}
            controller={{ control, name: 'category' }}
          />
        </SimpleGrid>
        <FormControl>
          <FormLabel fontSize="sm" mb={1}>
            {ft('Auto-close after inactivity (hours)')}
          </FormLabel>
          <Flex align="center" gap={3}>
            <NumberStepper
              value={autoCloseHours}
              min={0}
              max={720}
              onChange={(num) => setValue('autoCloseHours', num, { shouldDirty: true })}
            />
            <Text fontSize="sm" color="TextSecondary">
              {autoCloseHours > 0
                ? ft('Idle tickets close automatically after this many hours.')
                : ft('0 = never auto-close.')}
            </Text>
          </Flex>
        </FormControl>
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
        JSON.stringify({
          supportRole: e.supportRole,
          category: e.category,
          autoCloseHours: e.autoCloseHours,
        })
      );
      reset({
        ...result,
        supportRole: result.supportRole ?? undefined,
        category: result.category ?? undefined,
        autoCloseHours: result.autoCloseHours ?? 0,
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
