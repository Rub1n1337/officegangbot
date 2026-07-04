import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Flex, Text } from '@chakra-ui/react';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { useFormText } from '@/config/translations/form-text';
import type { VerificationFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  role: z.string().nullable().optional(),
});

type Input = z.infer<typeof schema>;

export const useVerificationFeature: UseFormRender<VerificationFeature> = (data, onSubmit) => {
  const ft = useFormText();
  const { reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      role: data.role ?? undefined,
    },
  });

  return {
    component: (
      <Flex direction="column" gap={3}>
        <Text fontSize="sm" color="TextSecondary">
          {ft(
            'New members click a Verify button and receive the role below — gate your channels on that role so unverified accounts can’t post.'
          )}
        </Text>
        <RoleSelectForm
          control={{
            label: ft('Verified role'),
            description: ft('Granted when a member clicks the Verify button.'),
          }}
          controller={{ control, name: 'role' }}
        />
        <Box bg="CardBackground" rounded="xl" p={4}>
          <Text fontSize="sm" color="TextSecondary">
            {ft('After saving, run')}{' '}
            <Text as="span" fontWeight="600" color="TextPrimary">
              /verify_setup
            </Text>{' '}
            {ft('in Discord to post the Verify panel in the channel of your choice.')}
          </Text>
        </Box>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(JSON.stringify({ role: e.role ?? null }));
      reset({ role: result.role ?? undefined });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
