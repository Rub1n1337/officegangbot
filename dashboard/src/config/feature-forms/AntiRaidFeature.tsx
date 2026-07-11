import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Flex, Icon, Select, Text } from '@chakra-ui/react';
import { NumberStepper } from '@/components/forms/NumberStepper';
import { MdGroupAdd, MdTimer, MdGavel, MdHourglassBottom } from 'react-icons/md';
import { useFormText } from '@/config/translations/form-text';
import type { AntiRaidFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  joinCount: z.number().int().min(3).max(100),
  joinWindow: z.number().int().min(3).max(300),
  action: z.enum(['timeout', 'kick', 'ban', 'notify']),
  duration: z.number().int().min(60).max(86400),
});

type Input = z.infer<typeof schema>;

function Row({
  icon,
  title,
  description,
  children,
}: {
  icon: typeof MdTimer;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Flex bg="CardBackground" rounded="2xl" p={4} gap={3} align="center" borderWidth="1px" borderColor="CardBorder">
      <Flex flexShrink={0} align="center" justify="center" boxSize="40px" rounded="xl" bg="brandAlpha.100" color="brand.500" _dark={{ color: 'brand.200' }}>
        <Icon as={icon} fontSize="xl" />
      </Flex>
      <Box flex={1} minW={0}>
        <Text fontWeight="600">{title}</Text>
        <Text fontSize="sm" color="TextSecondary">{description}</Text>
      </Box>
      {children}
    </Flex>
  );
}

export const useAntiRaidFeature: UseFormRender<AntiRaidFeature> = (data, onSubmit) => {
  const ft = useFormText();
  const { reset, handleSubmit, formState, control, watch, setValue, register } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      joinCount: data.joinCount ?? 8,
      joinWindow: data.joinWindow ?? 10,
      action: data.action ?? 'timeout',
      duration: data.duration ?? 300,
    },
  });

  const action = watch('action');

  const numberField = (name: 'joinCount' | 'joinWindow' | 'duration', min: number, max: number) => (
    <NumberStepper
      value={watch(name)}
      min={min}
      max={max}
      onChange={(num) => setValue(name, num, { shouldDirty: true })}
    />
  );

  return {
    component: (
      <Flex direction="column" gap={3}>
        <Text fontSize="sm" color="TextSecondary">
          {ft(
            'When this many members join within the time window, raid mode activates: everyone in the wave (and anyone joining while it lasts) gets the chosen action. A raid alert is posted to your punishment log channel.'
          )}
        </Text>
        <Row
          icon={MdGroupAdd}
          title={ft('Join threshold')}
          description={ft('This many joins inside the window triggers raid mode.')}
        >
          {numberField('joinCount', 3, 100)}
        </Row>
        <Row
          icon={MdTimer}
          title={ft('Join window (seconds)')}
          description={ft('Time window the join threshold is measured over.')}
        >
          {numberField('joinWindow', 3, 300)}
        </Row>
        <Row
          icon={MdGavel}
          title={ft('Action on raiders')}
          description={ft('Applied to everyone in the join wave. “Notify only” just posts the alert.')}
        >
          <Select w="150px" flexShrink={0} {...register('action')}>
            <option value="timeout">{ft('Timeout')}</option>
            <option value="kick">{ft('Kick')}</option>
            <option value="ban">{ft('Ban')}</option>
            <option value="notify">{ft('Notify only')}</option>
          </Select>
        </Row>
        <Row
          icon={MdHourglassBottom}
          title={ft('Raid mode duration (seconds)')}
          description={
            action === 'timeout'
              ? ft('How long raid mode stays active — also used as the timeout length.')
              : ft('How long raid mode stays active after triggering.')
          }
        >
          {numberField('duration', 60, 86400)}
        </Row>
        <Text fontSize="sm" color="TextSecondary">
          {ft(
            'Raid alerts require the Logging feature with a punishment log channel. Timeout is the safest default — bans and kicks can hit legitimate newcomers during false positives.'
          )}
        </Text>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          joinCount: e.joinCount,
          joinWindow: e.joinWindow,
          action: e.action,
          duration: e.duration,
        })
      );
      reset({
        joinCount: result.joinCount ?? 8,
        joinWindow: result.joinWindow ?? 10,
        action: result.action ?? 'timeout',
        duration: result.duration ?? 300,
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
