import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useState } from 'react';
import { Box, Flex, Input, SimpleGrid, Tag, TagCloseButton, TagLabel, Text } from '@chakra-ui/react';
import { FormCardController } from '@/components/forms/Form';
import { useFormText } from '@/config/translations/form-text';
import type { FilterFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  words: z.array(z.string()),
});

type Input = z.infer<typeof schema>;

function normalize(raw: string): string[] {
  const out: string[] = [];
  for (const part of raw.split(/[\n,]+/)) {
    const word = part.trim().toLowerCase();
    if (word) out.push(word);
  }
  return out;
}

// Tag/chip input: type a word and press Enter (or comma) to add it as a removable
// chip. Backspace on an empty field removes the last word.
function WordTagsInput({ value, onChange }: { value: string[]; onChange: (next: string[]) => void }) {
  const ft = useFormText();
  const [input, setInput] = useState('');

  const add = (raw: string) => {
    const next = Array.from(new Set([...value, ...normalize(raw)])).sort();
    onChange(next);
    setInput('');
  };
  const remove = (word: string) => onChange(value.filter((w) => w !== word));

  return (
    <Box>
      {value.length > 0 && (
        <Flex wrap="wrap" gap={2} mb={2}>
          {value.map((word) => (
            <Tag key={word} size="md" borderRadius="full" variant="subtle" colorScheme="red">
              <TagLabel>{word}</TagLabel>
              <TagCloseButton onClick={() => remove(word)} />
            </Tag>
          ))}
        </Flex>
      )}
      <Input
        variant="main"
        value={input}
        placeholder={ft('Type a word and press Enter')}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            if (input.trim()) add(input);
          } else if (e.key === 'Backspace' && !input && value.length) {
            remove(value[value.length - 1]);
          }
        }}
        onBlur={() => input.trim() && add(input)}
      />
      <Text fontSize="xs" color="TextSecondary" mt={1}>
        {value.length} word{value.length === 1 ? '' : 's'} in the filter
      </Text>
    </Box>
  );
}

export const useFilterFeature: UseFormRender<FilterFeature> = (
  data: FilterFeature,
  onSubmit: (data: string) => Promise<any>
) => {
  const ft = useFormText();
  const { reset, handleSubmit, control, formState } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      words: (data.words ?? []).slice().sort(),
    },
  });

  return {
    component: (
      <SimpleGrid columns={1} gap={3}>
        <FormCardController
          control={{
            label: ft('Filtered Words'),
            description: ft('Words to automatically delete. Case-insensitive; duplicates are removed.'),
          }}
          controller={{ control, name: 'words' }}
          render={({ field }) => (
            <WordTagsInput value={field.value ?? []} onChange={field.onChange} />
          )}
        />
      </SimpleGrid>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(JSON.stringify({ words: e.words }));
      reset(result);
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
