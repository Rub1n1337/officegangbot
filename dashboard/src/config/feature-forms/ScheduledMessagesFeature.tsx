import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Box,
  Button,
  Flex,
  FormControl,
  FormLabel,
  IconButton,
  Select,
  SimpleGrid,
  Switch,
  Text,
} from '@chakra-ui/react';
import { MdAdd, MdDelete } from 'react-icons/md';
import { ChannelSelectForm } from '@/components/forms/ChannelSelect';
import { InputForm } from '@/components/forms/InputForm';
import { TextAreaForm } from '@/components/forms/TextAreaForm';
import type { ScheduledMessagesFeature, ScheduledMessageItem } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

// The form holds the date/time as a `datetime-local` string in the admin's local
// timezone; we convert to/from the ISO UTC string the bot stores at the edges.
function isoToLocalInput(iso?: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function localInputToIso(local: string): string {
  if (!local) return '';
  const d = new Date(local); // parsed as local time
  return isNaN(d.getTime()) ? '' : d.toISOString();
}

const itemSchema = z.object({
  channelId: z.string().optional(),
  content: z.string().min(1, 'Message is required').max(2000, 'Max 2000 characters'),
  scheduledAt: z.string().min(1, 'Pick a date & time'),
  repeat: z.enum(['none', 'daily', 'weekly']),
  enabled: z.boolean(),
});

const schema = z.object({ items: z.array(itemSchema) });

type Input = z.infer<typeof schema>;

function toFormItems(items: ScheduledMessageItem[] | undefined) {
  return (items ?? []).map((it) => ({
    channelId: it.channelId ?? undefined,
    content: it.content ?? '',
    scheduledAt: isoToLocalInput(it.scheduledAt),
    repeat: it.repeat ?? 'none',
    enabled: it.enabled ?? true,
  }));
}

export const useScheduledMessagesFeature: UseFormRender<ScheduledMessagesFeature> = (data, onSubmit) => {
  const { register, reset, handleSubmit, formState, control, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: { items: toFormItems(data.items) },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'items' });

  return {
    component: (
      <Flex direction="column" gap={3}>
        {fields.length === 0 && (
          <Text color="TextSecondary">
            No scheduled messages yet. Add one to post an announcement at a set time (optionally
            repeating daily or weekly).
          </Text>
        )}
        {fields.map((field, index) => (
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
              <Flex align="center" gap={3}>
                <Text fontWeight="600">Message #{index + 1}</Text>
                <Flex align="center" gap={1}>
                  <Switch
                    isChecked={watch(`items.${index}.enabled`)}
                    onChange={(e) =>
                      setValue(`items.${index}.enabled`, e.target.checked, { shouldDirty: true })
                    }
                  />
                  <Text fontSize="sm" color="TextSecondary">
                    {watch(`items.${index}.enabled`) ? 'Active' : 'Paused'}
                  </Text>
                </Flex>
              </Flex>
              <IconButton
                aria-label="Remove scheduled message"
                icon={<MdDelete />}
                size="sm"
                variant="danger"
                onClick={() => remove(index)}
              />
            </Flex>
            <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
              <ChannelSelectForm
                control={{ label: 'Channel', description: 'Where to post the message' }}
                controller={{ control, name: `items.${index}.channelId` }}
              />
              <InputForm
                control={{
                  label: 'Date & time (your local time)',
                  description: 'When to first post it',
                  error: formState.errors.items?.[index]?.scheduledAt?.message,
                }}
                type="datetime-local"
                {...register(`items.${index}.scheduledAt`)}
              />
            </SimpleGrid>
            <Box mt={3}>
              <TextAreaForm
                control={{
                  label: 'Message',
                  description: 'Up to 2000 characters.',
                  error: formState.errors.items?.[index]?.content?.message,
                }}
                placeholder="📢 Weekly reminder: read the rules and have a great week!"
                {...register(`items.${index}.content`)}
              />
            </Box>
            <Box mt={3} maxW={{ base: 'full', lg: '220px' }}>
              <FormControl>
                <FormLabel fontSize="sm" mb={1}>
                  Repeat
                </FormLabel>
                <Select {...register(`items.${index}.repeat`)}>
                  <option value="none">Once</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </Select>
              </FormControl>
            </Box>
          </Box>
        ))}
        <Button
          leftIcon={<MdAdd />}
          variant="action"
          alignSelf="flex-start"
          onClick={() =>
            append({ channelId: undefined, content: '', scheduledAt: '', repeat: 'none', enabled: true })
          }
        >
          Add scheduled message
        </Button>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          items: e.items.map((it) => ({
            channelId: it.channelId,
            content: it.content,
            scheduledAt: localInputToIso(it.scheduledAt),
            repeat: it.repeat,
            enabled: it.enabled,
          })),
        })
      );
      reset({ items: toFormItems((result?.items ?? []) as ScheduledMessageItem[]) });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
