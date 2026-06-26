import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { SimpleGrid } from '@chakra-ui/react';
import { InputForm } from '@/components/forms/InputForm';
import type { FilterFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  words: z.string().optional(),
});

type Input = z.infer<typeof schema>;

// Parse the comma/newline separated text into a normalised word list.
function parseWords(value: string | undefined): string[] {
  if (!value) return [];
  const seen = new Set<string>();
  for (const part of value.split(/[\n,]+/)) {
    const word = part.trim().toLowerCase();
    if (word) seen.add(word);
  }
  return Array.from(seen).sort();
}

export const useFilterFeature: UseFormRender<FilterFeature> = (
  data: FilterFeature,
  onSubmit: (data: string) => Promise<any>
) => {
  const { register, reset, handleSubmit, formState, control } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      words: (data.words ?? []).join(', '),
    },
  });

  return {
    component: (
      <SimpleGrid columns={1} gap={3}>
        <InputForm
          control={{
            label: 'Filtered Words',
            description:
              'Comma-separated list of words to delete. Case-insensitive; duplicates are removed on save.',
            error: formState.errors.words?.message,
          }}
          placeholder="word1, word2, word3"
          {...register('words')}
        />
      </SimpleGrid>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          words: parseWords(e.words),
        })
      );
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
