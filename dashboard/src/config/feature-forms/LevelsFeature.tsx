import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Badge,
  Box,
  Button,
  Divider,
  Flex,
  Icon,
  IconButton,
  Progress,
  SimpleGrid,
  Switch,
  Text,
} from '@chakra-ui/react';
import { MdAdd, MdDelete, MdMic, MdBolt } from 'react-icons/md';
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

const multiplierSchema = z.object({
  roleId: z.string().min(1, 'Pick a role'),
  multiplier: z
    .number({ invalid_type_error: 'Enter a multiplier' })
    .min(0.1, 'Min 0.1x')
    .max(10, 'Max 10x'),
});

const schema = z.object({
  channel: z.string().optional(),
  rewards: z.array(rewardSchema),
  voiceXpEnabled: z.boolean(),
  voiceXpPerMin: z.number().int().min(0).max(100),
  xpMultiplier: z.number().min(0.1).max(10),
  prestigeLevel: z.number().int().min(0).max(1000),
  roleMultipliers: z.array(multiplierSchema),
});

type Input = z.infer<typeof schema>;

function defaultsFrom(data: Partial<LevelsFeature>): Input {
  return {
    channel: data.channel ?? undefined,
    rewards: (data.rewards ?? []).map((r) => ({
      level: r.level,
      roleId: r.roleId ?? (undefined as unknown as string),
    })),
    voiceXpEnabled: data.voiceXpEnabled ?? false,
    voiceXpPerMin: data.voiceXpPerMin ?? 5,
    xpMultiplier: data.xpMultiplier ?? 1,
    prestigeLevel: data.prestigeLevel ?? 100,
    roleMultipliers: (data.roleMultipliers ?? []).map((r) => ({
      roleId: r.roleId ?? (undefined as unknown as string),
      multiplier: r.multiplier ?? 1,
    })),
  };
}

export const useLevelsFeature: UseFormRender<LevelsFeature> = (data, onSubmit) => {
  const { register, reset, handleSubmit, formState, control, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: defaultsFrom(data),
  });

  const {
    fields: rewardFields,
    append: appendReward,
    remove: removeReward,
  } = useFieldArray({ control, name: 'rewards' });
  const {
    fields: multFields,
    append: appendMult,
    remove: removeMult,
  } = useFieldArray({ control, name: 'roleMultipliers' });

  const voiceEnabled = watch('voiceXpEnabled');
  const season = data.season ?? 1;

  return {
    component: (
      <Flex direction="column" gap={4}>
        <Box bg="CardBackground" rounded="2xl" p={4}>
          <Flex justify="space-between" align="center" mb={2}>
            <Text fontWeight="600" fontSize="sm">
              How <Text as="span" color="Brand">/rank</Text> looks to members
            </Text>
            <Badge colorScheme="purple" rounded="md">
              Season {season}
            </Badge>
          </Flex>
          <Progress value={62} size="sm" rounded="full" colorScheme="purple" />
          <Text fontSize="xs" color="TextSecondary" mt={1.5}>
            620 / 1,000 XP · 380 to level 6
          </Text>
        </Box>

        <ChannelSelectForm
          control={{
            label: 'Level-up announcement channel',
            description:
              'Where to post when a member levels up. Leave unset to announce in the channel they were chatting in.',
          }}
          controller={{ control, name: 'channel' }}
        />

        <Divider />

        {/* Voice XP */}
        <Flex
          bg="CardBackground"
          rounded="2xl"
          p={4}
          gap={3}
          align="center"
          borderWidth="1px"
          borderColor="CardBorder"
        >
          <Flex
            flexShrink={0}
            align="center"
            justify="center"
            boxSize="40px"
            rounded="xl"
            bg="brandAlpha.100"
            color="brand.500"
            _dark={{ color: 'brand.200' }}
          >
            <Icon as={MdMic} fontSize="xl" />
          </Flex>
          <Box flex={1} minW={0}>
            <Text fontWeight="600">Voice XP</Text>
            <Text fontSize="sm" color="TextSecondary">
              Award XP every minute to members active in a voice channel (not alone, not deafened).
            </Text>
          </Box>
          <Switch
            isChecked={voiceEnabled}
            onChange={(e) => setValue('voiceXpEnabled', e.target.checked, { shouldDirty: true })}
            flexShrink={0}
          />
        </Flex>
        {voiceEnabled && (
          <InputForm
            control={{
              label: 'Voice XP per minute',
              description: 'Base XP granted each minute in voice (before multipliers).',
              error: formState.errors.voiceXpPerMin?.message,
            }}
            type="number"
            min={0}
            max={100}
            placeholder="5"
            {...register('voiceXpPerMin', { valueAsNumber: true })}
          />
        )}

        <Divider />

        {/* Multipliers */}
        <Box>
          <Flex align="center" gap={2}>
            <Icon as={MdBolt} color="Brand" />
            <Text fontWeight="600">XP multipliers</Text>
          </Flex>
          <Text fontSize="sm" color="TextSecondary">
            A member&apos;s XP is multiplied by the global value times their best role multiplier.
          </Text>
        </Box>
        <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
          <InputForm
            control={{
              label: 'Global multiplier',
              description: 'Applies to all XP (e.g. 2 for a double-XP weekend). 0.1–10.',
              error: formState.errors.xpMultiplier?.message,
            }}
            type="number"
            step="0.1"
            min={0.1}
            max={10}
            placeholder="1"
            {...register('xpMultiplier', { valueAsNumber: true })}
          />
          <InputForm
            control={{
              label: 'Prestige level',
              description: 'Members can /prestige at this level. 0 disables prestige.',
              error: formState.errors.prestigeLevel?.message,
            }}
            type="number"
            min={0}
            max={1000}
            placeholder="100"
            {...register('prestigeLevel', { valueAsNumber: true })}
          />
        </SimpleGrid>

        <Box>
          <Flex justify="space-between" align="center">
            <Text fontWeight="600" fontSize="sm">
              Per-role multipliers
            </Text>
            <Button
              size="sm"
              leftIcon={<Icon as={MdAdd} />}
              variant="action"
              onClick={() => appendMult({ roleId: undefined as unknown as string, multiplier: 2 })}
              isDisabled={multFields.length >= 50}
            >
              Add role
            </Button>
          </Flex>
          <Text fontSize="sm" color="TextSecondary">
            Give boosters or supporters bonus XP.
          </Text>
        </Box>
        <Flex direction="column" gap={3}>
          {multFields.map((field, index) => (
            <Box
              key={field.id}
              bg="CardBackground"
              rounded="2xl"
              p={4}
              borderWidth="1px"
              borderColor="CardBorder"
            >
              <Flex justify="space-between" align="center" mb={2}>
                <Text fontWeight="600">Multiplier #{index + 1}</Text>
                <IconButton
                  aria-label="Remove multiplier"
                  icon={<MdDelete />}
                  size="sm"
                  variant="danger"
                  onClick={() => removeMult(index)}
                />
              </Flex>
              <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
                <RoleSelectForm
                  control={{ label: 'Role', description: 'Members with this role' }}
                  controller={{ control, name: `roleMultipliers.${index}.roleId` }}
                />
                <InputForm
                  control={{
                    label: 'Multiplier',
                    description: '0.1–10 (e.g. 2 = double XP)',
                    error: formState.errors.roleMultipliers?.[index]?.multiplier?.message,
                  }}
                  type="number"
                  step="0.1"
                  min={0.1}
                  max={10}
                  placeholder="2"
                  {...register(`roleMultipliers.${index}.multiplier`, { valueAsNumber: true })}
                />
              </SimpleGrid>
            </Box>
          ))}
        </Flex>

        <Divider />

        <Box>
          <Text fontWeight="600">Role rewards</Text>
          <Text fontSize="sm" color="TextSecondary">
            Automatically grant a role when a member reaches a level.
          </Text>
        </Box>

        <Flex direction="column" gap={3}>
          {rewardFields.length === 0 && (
            <Text color="TextSecondary">No role rewards yet. Add one below.</Text>
          )}
          {rewardFields.map((field, index) => (
            <Box
              key={field.id}
              bg="CardBackground"
              rounded="2xl"
              p={4}
              position="relative"
              borderWidth="1px"
              borderColor="CardBorder"
            >
              <Flex justify="space-between" align="center" mb={2}>
                <Text fontWeight="600">Reward #{index + 1}</Text>
                <IconButton
                  aria-label="Remove reward"
                  icon={<MdDelete />}
                  size="sm"
                  variant="danger"
                  onClick={() => removeReward(index)}
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
            onClick={() => appendReward({ level: 1, roleId: undefined as unknown as string })}
          >
            Add reward
          </Button>
        </Flex>

        <Text fontSize="sm" color="TextSecondary">
          End the current season with <Text as="span" color="Brand">/season_reset</Text> — standings
          are archived (see <Text as="span" color="Brand">/seasons</Text>) and everyone&apos;s XP
          resets, keeping prestige.
        </Text>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          channel: e.channel,
          rewards: e.rewards,
          voiceXpEnabled: e.voiceXpEnabled,
          voiceXpPerMin: e.voiceXpPerMin,
          xpMultiplier: e.xpMultiplier,
          prestigeLevel: e.prestigeLevel,
          roleMultipliers: e.roleMultipliers.filter((r) => !!r.roleId),
        })
      );
      reset(defaultsFrom((result ?? {}) as Partial<LevelsFeature>));
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
