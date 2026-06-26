import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { SimpleGrid } from '@chakra-ui/react';
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
  { name: 'config', label: 'Config', description: 'Manage bot settings' },
  { name: 'kick', label: 'Kick', description: 'Kick members' },
  { name: 'ban', label: 'Ban', description: 'Ban members' },
  { name: 'mute', label: 'Mute', description: 'Timeout members' },
  { name: 'warn', label: 'Warn', description: 'Warn members' },
  { name: 'clear', label: 'Clear', description: 'Bulk-delete messages' },
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
