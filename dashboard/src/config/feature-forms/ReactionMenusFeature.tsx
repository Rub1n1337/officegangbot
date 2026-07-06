import { useForm, useFieldArray, Control } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Button, Divider, Flex, Heading, IconButton, Select, SimpleGrid, Switch, Text } from '@chakra-ui/react';
import { MdAdd, MdDelete } from 'react-icons/md';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { InputForm } from '@/components/forms/InputForm';
import { TextAreaForm } from '@/components/forms/TextAreaForm';
import { EmojiPickerInput } from '@/components/forms/EmojiPickerInput';
import { useFormText } from '@/config/translations/form-text';
import type { ReactionMenusFeature, ReactionMenuConfig, ReactionRoleItem } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const itemSchema = z.object({
  emoji: z.string().min(1, 'Emoji is required'),
  roleId: z.string().optional(),
});

// A reaction role attached to an *existing* message (the former standalone
// Reaction Role feature, merged into this card).
const standaloneSchema = z.object({
  channelId: z.string().optional(),
  messageId: z
    .string()
    .optional()
    .refine((v) => !v || /^\d{17,20}$/.test(v.trim()), {
      message: 'Message ID must be 17–20 digits (Developer Mode → right-click message → Copy Message ID).',
    }),
  emoji: z.string().min(1, 'Emoji is required'),
  roleId: z.string().optional(),
});

const menuSchema = z.object({
  id: z.number().nullable().optional(),
  channelId: z.string().optional(),
  title: z.string().min(1, 'Give the menu a title').max(256, 'Title is too long'),
  description: z.string().max(2000, 'Description is too long'),
  exclusive: z.boolean(),
  style: z.enum(['reactions', 'buttons', 'dropdown']),
  items: z.array(itemSchema),
});

const schema = z.object({
  menus: z.array(menuSchema),
  standalone: z.array(standaloneSchema).max(100),
});

type Input = z.infer<typeof schema>;

function toFormStandalone(items: ReactionRoleItem[] | undefined) {
  return (items ?? []).map((it) => ({
    channelId: it.channelId ?? undefined,
    messageId: it.messageId ?? undefined,
    emoji: it.emoji || '✅',
    roleId: it.roleId ?? undefined,
  }));
}

function toFormMenus(menus: ReactionMenuConfig[] | undefined) {
  return (menus ?? []).map((m) => ({
    id: m.id ?? null,
    channelId: m.channelId ?? undefined,
    title: m.title ?? 'Role Menu',
    description: m.description ?? '',
    exclusive: m.exclusive ?? false,
    style: m.style ?? ('reactions' as const),
    items: (m.items ?? []).map((it) => ({ emoji: it.emoji || '✅', roleId: it.roleId ?? undefined })),
  }));
}

// The emoji->role rows for a single menu (nested field array).
function MenuRoles({ control, menuIndex }: { control: Control<Input>; menuIndex: number }) {
  const ft = useFormText();
  const { fields, append, remove } = useFieldArray({ control, name: `menus.${menuIndex}.items` });
  return (
    <Box>
      <Text fontSize="sm" fontWeight="600" mb={2}>
        {ft('Roles')}
      </Text>
      <Flex direction="column" gap={2}>
        {fields.length === 0 && (
          <Text fontSize="sm" color="TextSecondary">
            {ft('No roles yet. Add an emoji → role pair below.')}
          </Text>
        )}
        {fields.map((field, i) => (
          <Flex key={field.id} gap={2} align="flex-start">
            <Box w={{ base: '40%', md: '160px' }} flexShrink={0}>
              <EmojiPickerInput
                control={{ label: '' }}
                controller={{ control, name: `menus.${menuIndex}.items.${i}.emoji` }}
                placeholder="✅"
              />
            </Box>
            <Box flex={1} minW={0}>
              <RoleSelectForm
                control={{ label: '' }}
                controller={{ control, name: `menus.${menuIndex}.items.${i}.roleId` }}
              />
            </Box>
            <IconButton
              aria-label="Remove role"
              icon={<MdDelete />}
              size="sm"
              variant="danger"
              mt={1}
              onClick={() => remove(i)}
            />
          </Flex>
        ))}
      </Flex>
      <Button
        leftIcon={<MdAdd />}
        size="sm"
        variant="action"
        alignSelf="flex-start"
        mt={2}
        onClick={() => append({ emoji: '✅', roleId: undefined as unknown as string })}
      >
        {ft('Add role')}
      </Button>
    </Box>
  );
}

// The "existing message" rows (nested field array, rendered below the menus).
function StandaloneRoles({ control, register, errors }: { control: Control<Input>; register: any; errors: any }) {
  const ft = useFormText();
  const { fields, append, remove } = useFieldArray({ control, name: 'standalone' });
  return (
    <Box>
      <Heading size="sm">{ft('Reactions on existing messages')}</Heading>
      <Text fontSize="sm" color="TextSecondary" mt={1} mb={3}>
        {ft('Grant a role when members react to any existing message (e.g. your rules post) — no new embed is created.')}
      </Text>
      <Flex direction="column" gap={3}>
        {fields.map((field, i) => (
          <Box key={field.id} bg="CardBackground" rounded="2xl" p={4} borderWidth="1px" borderColor="CardBorder">
            <Flex justify="space-between" align="center" mb={2}>
              <Text fontWeight="600">Reaction role #{i + 1}</Text>
              <IconButton
                aria-label="Remove reaction role"
                icon={<MdDelete />}
                size="sm"
                variant="danger"
                onClick={() => remove(i)}
              />
            </Flex>
            <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
              <ChannelSelectForm
                control={{ label: ft('Channel'), description: ft('Channel containing the message') }}
                controller={{ control, name: `standalone.${i}.channelId` }}
              />
              <InputForm
                control={{
                  label: ft('Message ID'),
                  description: ft('Developer Mode → right-click the message → Copy Message ID.'),
                  tooltip: ft(
                    'Turn on Developer Mode in Discord (User Settings → Advanced). Then right-click (or long-press on mobile) the message and choose “Copy Message ID”. It is an 18–19 digit number.'
                  ),
                  error: errors.standalone?.[i]?.messageId?.message,
                }}
                placeholder="123456789012345678"
                {...register(`standalone.${i}.messageId`)}
              />
              <EmojiPickerInput
                control={{ label: ft('Emoji'), description: ft('Emoji members react with') }}
                controller={{ control, name: `standalone.${i}.emoji` }}
                placeholder="✅"
              />
              <RoleSelectForm
                control={{ label: ft('Role'), description: ft('Role to grant on reaction') }}
                controller={{ control, name: `standalone.${i}.roleId` }}
              />
            </SimpleGrid>
          </Box>
        ))}
      </Flex>
      <Button
        leftIcon={<MdAdd />}
        size="sm"
        variant="action"
        mt={3}
        onClick={() => append({ channelId: undefined, messageId: '', emoji: '✅', roleId: undefined })}
      >
        {ft('Add reaction role')}
      </Button>
    </Box>
  );
}

export const useReactionMenusFeature: UseFormRender<ReactionMenusFeature> = (data, onSubmit) => {
  const ft = useFormText();
  const { register, reset, handleSubmit, formState, control, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: { menus: toFormMenus(data.menus), standalone: toFormStandalone(data.standalone) },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'menus' });

  return {
    component: (
      <Flex direction="column" gap={3}>
        {fields.length === 0 && (
          <Text color="TextSecondary">
            {ft('No role menus yet. Add one and the bot will post an embed members can react to for roles.')}
          </Text>
        )}
        {fields.map((field, index) => (
          <Box
            key={field.id}
            bg="CardBackground"
            rounded="2xl"
            p={4}
            borderWidth="1px"
            borderColor="CardBorder"
          >
            <Flex justify="space-between" align="center" mb={2}>
              <Text fontWeight="600">Menu #{index + 1}</Text>
              <IconButton
                aria-label="Remove menu"
                icon={<MdDelete />}
                size="sm"
                variant="danger"
                onClick={() => remove(index)}
              />
            </Flex>
            <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
              <ChannelSelectForm
                control={{ label: ft('Channel'), description: ft('Where the menu message is posted') }}
                controller={{ control, name: `menus.${index}.channelId` }}
              />
              <InputForm
                control={{
                  label: ft('Title'),
                  description: ft('Heading of the menu embed'),
                  error: formState.errors.menus?.[index]?.title?.message,
                }}
                placeholder={ft('Pick your roles')}
                {...register(`menus.${index}.title`)}
              />
            </SimpleGrid>
            <Box mt={3}>
              <TextAreaForm
                control={{
                  label: ft('Description'),
                  description: ft('Shown above the role list (optional).'),
                  error: formState.errors.menus?.[index]?.description?.message,
                }}
                placeholder={ft('React below to choose your roles.')}
                {...register(`menus.${index}.description`)}
              />
            </Box>
            <Flex align="center" gap={3} mt={3} justify="space-between">
              <Box>
                <Text fontSize="sm" fontWeight="600">
                  {ft('Menu style')}
                </Text>
                <Text fontSize="xs" color="TextSecondary">
                  {ft('Buttons and dropdown are modern components — better on mobile than emoji reactions.')}
                </Text>
              </Box>
              <Select w="170px" flexShrink={0} {...register(`menus.${index}.style`)}>
                <option value="reactions">{ft('Reactions')}</option>
                <option value="buttons">{ft('Buttons')}</option>
                <option value="dropdown">{ft('Dropdown')}</option>
              </Select>
            </Flex>
            <Flex align="center" gap={3} mt={3} justify="space-between">
              <Box>
                <Text fontSize="sm" fontWeight="600">
                  {ft('Single-select (exclusive)')}
                </Text>
                <Text fontSize="xs" color="TextSecondary">
                  {ft('Members can hold only one role from this menu — picking another swaps it.')}
                </Text>
              </Box>
              <Switch
                isChecked={watch(`menus.${index}.exclusive`)}
                onChange={(e) => setValue(`menus.${index}.exclusive`, e.target.checked, { shouldDirty: true })}
                flexShrink={0}
              />
            </Flex>
            <Divider my={3} />
            <MenuRoles control={control} menuIndex={index} />
          </Box>
        ))}
        <Button
          leftIcon={<MdAdd />}
          variant="action"
          alignSelf="flex-start"
          onClick={() =>
            append({ id: null, channelId: undefined, title: 'Role Menu', description: '', exclusive: false, style: 'reactions', items: [] })
          }
        >
          {ft('Add menu')}
        </Button>
        <Divider my={2} />
        <StandaloneRoles control={control} register={register} errors={formState.errors} />
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(JSON.stringify({ menus: e.menus, standalone: e.standalone }));
      reset({
        menus: toFormMenus((result?.menus ?? []) as ReactionMenuConfig[]),
        standalone: toFormStandalone((result?.standalone ?? []) as ReactionRoleItem[]),
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
