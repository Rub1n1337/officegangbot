import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Divider, Flex, Icon, SimpleGrid, Switch, Text } from '@chakra-ui/react';
import { NumberStepper } from '@/components/forms/NumberStepper';
import { MdGavel } from 'react-icons/md';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { useFormText } from '@/config/translations/form-text';
import type { ModerationFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  config: z.string().nullable().optional(),
  kick: z.string().nullable().optional(),
  ban: z.string().nullable().optional(),
  mute: z.string().nullable().optional(),
  warn: z.string().nullable().optional(),
  clear: z.string().nullable().optional(),
  warnEscalationEnabled: z.boolean(),
  warnExpiryHours: z.number().int().min(0).max(8760),
  warnMuteAt: z.number().int().min(0).max(50),
  warnKickAt: z.number().int().min(0).max(50),
  warnBanAt: z.number().int().min(0).max(50),
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
  const ft = useFormText();
  const { reset, handleSubmit, formState, control, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      config: data.config ?? undefined,
      kick: data.kick ?? undefined,
      ban: data.ban ?? undefined,
      mute: data.mute ?? undefined,
      warn: data.warn ?? undefined,
      clear: data.clear ?? undefined,
      warnEscalationEnabled: data.warnEscalationEnabled ?? false,
      warnExpiryHours: data.warnExpiryHours ?? 0,
      warnMuteAt: data.warnMuteAt ?? 0,
      warnKickAt: data.warnKickAt ?? 0,
      warnBanAt: data.warnBanAt ?? 0,
    },
  });

  const escalationOn = watch('warnEscalationEnabled');

  const numberField = (name: 'warnExpiryHours' | 'warnMuteAt' | 'warnKickAt' | 'warnBanAt', max: number) => (
    <NumberStepper
      value={watch(name)}
      min={0}
      max={max}
      onChange={(num) => setValue(name, num, { shouldDirty: true })}
    />
  );

  const row = (label: string, desc: string, field: JSX.Element) => (
    <Flex align="center" gap={3} bg="CardBackground" rounded="xl" p={3} borderWidth="1px" borderColor="CardBorder">
      <Box flex={1} minW={0}>
        <Text fontWeight="600" fontSize="sm">{label}</Text>
        <Text fontSize="xs" color="TextSecondary">{desc}</Text>
      </Box>
      {field}
    </Flex>
  );

  return {
    component: (
      <Flex direction="column" gap={3}>
        <Text fontSize="sm" color="TextSecondary">
          {ft('Grant roles access to each moderation command. Server administrators always have full access.')}
        </Text>
        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
          {PERMISSIONS.map((perm) => (
            <RoleSelectForm
              key={perm.name}
              control={{ label: ft(perm.label), description: ft(perm.description) }}
              controller={{ control, name: perm.name }}
            />
          ))}
        </SimpleGrid>

        <Divider my={1} />

        <Flex align="center" gap={3}>
          <Icon as={MdGavel} color="Brand" fontSize="xl" />
          <Box flex={1}>
            <Text fontWeight="600">{ft('Warning auto-escalation')}</Text>
            <Text fontSize="sm" color="TextSecondary">
              {ft('Automatically mute/kick/ban a member once their warnings reach a threshold.')}
            </Text>
          </Box>
          <Switch
            isChecked={escalationOn}
            onChange={(e) => setValue('warnEscalationEnabled', e.target.checked, { shouldDirty: true })}
          />
        </Flex>

        {escalationOn && (
          <Flex direction="column" gap={2}>
            {row(ft('Mute at (warnings)'), ft('Timeout the member for 10 minutes at this many warnings. 0 = off.'), numberField('warnMuteAt', 50))}
            {row(ft('Kick at (warnings)'), ft('Kick the member at this many warnings. 0 = off.'), numberField('warnKickAt', 50))}
            {row(ft('Ban at (warnings)'), ft('Ban the member at this many warnings. 0 = off.'), numberField('warnBanAt', 50))}
            {row(ft('Warning expiry (hours)'), ft('Warnings older than this stop counting toward escalation. 0 = never expire.'), numberField('warnExpiryHours', 8760))}
          </Flex>
        )}
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
          warnEscalationEnabled: e.warnEscalationEnabled,
          warnExpiryHours: e.warnExpiryHours,
          warnMuteAt: e.warnMuteAt,
          warnKickAt: e.warnKickAt,
          warnBanAt: e.warnBanAt,
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
