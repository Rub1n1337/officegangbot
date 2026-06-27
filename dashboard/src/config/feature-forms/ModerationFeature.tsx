import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Flex, SimpleGrid, Text } from '@chakra-ui/react';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import type { ModerationFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  config: z.string().nullable().optional(),
  kick: z.string().nullable().optional(),
  ban: z.string().nullable().optional(),
  mute: z.string().nullable().optional(),
  warn: z.string().nullable().optional(),
  clear: z.string().nullable().optional(),
});

type Input = z.infer<typeof schema>;

const PERMISSIONS: { name: keyof Input; label: string; description: string }[] = [
  { name: 'config', label: 'Config', description: 'Can use /config and /setup' },
  { name: 'kick', label: 'Kick', description: 'Can use /kick' },
  { name: 'ban', label: 'Ban', description: 'Can use /ban and /unban' },
  { name: 'mute', label: 'Mute', description: 'Can use /mute and /unmute' },
  { name: 'warn', label: 'Warn', description: 'Can use /warn, /warnings, /clearwarnings' },
  { name: 'clear', label: 'Clear', description: 'Can use /clear (bulk-delete)' },
];

export const useModerationFeature: UseFormRender<ModerationFeature> = (
  data: ModerationFeature,
  onSubmit: (data: string) => Promise<any>
) => {
  const { reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      config: data.config ?? undefined,
      kick: data.kick ?? undefined,
      ban: data.ban ?? undefined,
      mute: data.mute ?? undefined,
      warn: data.warn ?? undefined,
      clear: data.clear ?? undefined,
    },
  });

  return {
    component: (
      <Flex direction="column" gap={3}>
        <Text fontSize="sm" color="TextSecondary">
          Grant roles access to each moderation command. Server administrators always have full access.
        </Text>
        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
        {PERMISSIONS.map((perm) => (
          <RoleSelectForm
            key={perm.name}
            control={{
              label: perm.label,
              description: perm.description,
            }}
            controller={{ control, name: perm.name }}
          />
        ))}
        </SimpleGrid>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          config: e.config ?? null,
          kick: e.kick ?? null,
          ban: e.ban ?? null,
          mute: e.mute ?? null,
          warn: e.warn ?? null,
          clear: e.clear ?? null,
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
