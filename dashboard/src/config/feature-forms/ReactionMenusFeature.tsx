import { useForm, useFieldArray, Control } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Box, Button, Divider, Flex, IconButton, SimpleGrid, Switch, Text } from '@chakra-ui/react';
import { MdAdd, MdDelete } from 'react-icons/md';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { RoleSelectForm } from '@/components/forms/RoleSelect';
import { InputForm } from '@/components/forms/InputForm';
import { TextAreaForm } from '@/components/forms/TextAreaForm';
import { EmojiPickerInput } from '@/components/forms/EmojiPickerInput';
import { useFormText } from '@/config/translations/form-text';
import type { ReactionMenusFeature, ReactionMenuConfig } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const itemSchema = z.object({
  emoji: z.string().min(1, 'Emoji is required'),
  roleId: z.string().optional(),
});

const menuSchema = z.object({
  id: z.number().nullable().optional(),
  channelId: z.string().optional(),
  title: z.string().min(1, 'Give the menu a title').max(256, 'Title is too long'),
  description: z.string().max(2000, 'Description is too long'),
  exclusive: z.boolean(),
  items: z.array(itemSchema),
});

const schema = z.object({ menus: z.array(menuSchema) });

type Input = z.infer<typeof schema>;

function toFormMenus(menus: ReactionMenuConfig[] | undefined) {
  return (menus ?? []).map((m) => ({
    id: m.id ?? null,
    channelId: m.channelId ?? undefined,
    title: m.title ?? 'Role Menu',
    description: m.description ?? '',
    exclusive: m.exclusive ?? false,
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

export const useReactionMenusFeature: UseFormRender<ReactionMenusFeature> = (data, onSubmit) => {
  const ft = useFormText();
  const { register, reset, handleSubmit, formState, control, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: { menus: toFormMenus(data.menus) },
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
            append({ id: null, channelId: undefined, title: 'Role Menu', description: '', exclusive: false, items: [] })
          }
        >
          {ft('Add menu')}
        </Button>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(JSON.stringify({ menus: e.menus }));
      reset({ menus: toFormMenus((result?.menus ?? []) as ReactionMenuConfig[]) });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
