import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useState } from 'react';
import {
  Box,
  Divider,
  Flex,
  Icon,
  Input,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Switch,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
} from '@chakra-ui/react';
import { MdShield, MdAlternateEmail, MdLink, MdGroupAdd, MdTimer, MdCampaign } from 'react-icons/md';
import { FormCardController } from '@/components/forms/Form';
import type { AutomodFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  blockInvites: z.boolean(),
  blockLinks: z.boolean(),
  allowedDomains: z.array(z.string()),
  blockMassMentions: z.boolean(),
  spamCount: z.number().int().min(3).max(20),
  spamWindow: z.number().int().min(1).max(30),
  mentionLimit: z.number().int().min(3).max(30),
});

type Input = z.infer<typeof schema>;

// Accepts a domain, a full URL, or several separated by space/comma/newline,
// and reduces each to a bare host (no scheme/path/www).
function normalizeDomains(raw: string): string[] {
  const out: string[] = [];
  for (const part of raw.split(/[\n,\s]+/)) {
    const d = part
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, '')
      .replace(/\/.*$/, '')
      .replace(/^www\./, '');
    if (d) out.push(d);
  }
  return out;
}

function DomainsInput({ value, onChange }: { value: string[]; onChange: (next: string[]) => void }) {
  const [input, setInput] = useState('');
  const add = (raw: string) => {
    onChange(Array.from(new Set([...value, ...normalizeDomains(raw)])).sort());
    setInput('');
  };
  const remove = (d: string) => onChange(value.filter((x) => x !== d));

  return (
    <Box>
      {value.length > 0 && (
        <Flex wrap="wrap" gap={2} mb={2}>
          {value.map((d) => (
            <Tag key={d} size="md" borderRadius="full" variant="subtle" colorScheme="green">
              <TagLabel>{d}</TagLabel>
              <TagCloseButton onClick={() => remove(d)} />
            </Tag>
          ))}
        </Flex>
      )}
      <Input
        variant="main"
        value={input}
        placeholder="e.g. youtube.com — press Enter to add"
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
        {value.length} allowed domain{value.length === 1 ? '' : 's'}
      </Text>
    </Box>
  );
}

function ToggleRule({
  icon,
  title,
  description,
  checked,
  onChange,
}: {
  icon: typeof MdShield;
  title: string;
  description: string;
  checked: boolean;
  onChange: (next: boolean) => void;
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
      <Switch isChecked={checked} onChange={(e) => onChange(e.target.checked)} flexShrink={0} />
    </Flex>
  );
}

function NumberRule({
  icon,
  title,
  description,
  value,
  onChange,
  min,
  max,
}: {
  icon: typeof MdShield;
  title: string;
  description: string;
  value: number;
  onChange: (next: number) => void;
  min: number;
  max: number;
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
      <NumberInput
        value={value}
        min={min}
        max={max}
        onChange={(_, num) => onChange(Number.isNaN(num) ? value : num)}
        w="90px"
        flexShrink={0}
      >
        <NumberInputField />
        <NumberInputStepper>
          <NumberIncrementStepper />
          <NumberDecrementStepper />
        </NumberInputStepper>
      </NumberInput>
    </Flex>
  );
}

export const useAutomodFeature: UseFormRender<AutomodFeature> = (data, onSubmit) => {
  const { reset, handleSubmit, control, formState, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      blockInvites: data.blockInvites ?? false,
      blockLinks: data.blockLinks ?? false,
      allowedDomains: (data.allowedDomains ?? []).slice().sort(),
      blockMassMentions: data.blockMassMentions ?? false,
      spamCount: data.spamCount ?? 5,
      spamWindow: data.spamWindow ?? 3,
      mentionLimit: data.mentionLimit ?? 5,
    },
  });

  const blockLinks = watch('blockLinks');

  return {
    component: (
      <Flex direction="column" gap={3}>
        <Text fontWeight="600">Content filter</Text>
        <ToggleRule
          icon={MdGroupAdd}
          title="Block invite links"
          description="Delete messages containing Discord invite links (discord.gg/…)."
          checked={watch('blockInvites')}
          onChange={(v) => setValue('blockInvites', v, { shouldDirty: true })}
        />
        <ToggleRule
          icon={MdLink}
          title="Block external links"
          description="Delete messages that contain links, except to the allowed domains below."
          checked={blockLinks}
          onChange={(v) => setValue('blockLinks', v, { shouldDirty: true })}
        />
        {blockLinks && (
          <FormCardController
            control={{
              label: 'Allowed domains',
              description: 'Links to these domains (and their subdomains) are allowed.',
            }}
            controller={{ control, name: 'allowedDomains' }}
            render={({ field }) => <DomainsInput value={field.value ?? []} onChange={field.onChange} />}
          />
        )}
        <ToggleRule
          icon={MdCampaign}
          title="Block @everyone / @here"
          description="Delete messages that mention @everyone or @here."
          checked={watch('blockMassMentions')}
          onChange={(v) => setValue('blockMassMentions', v, { shouldDirty: true })}
        />

        <Divider my={1} />

        <Text fontWeight="600">Anti-spam &amp; mentions</Text>
        <Text fontSize="sm" color="TextSecondary">
          These limits run whenever AutoMod is enabled. Tune the thresholds to fit your server.
        </Text>
        <NumberRule
          icon={MdShield}
          title="Spam message threshold"
          description="Messages within the window that trigger a 10-minute timeout."
          value={watch('spamCount')}
          onChange={(v) => setValue('spamCount', v, { shouldDirty: true })}
          min={3}
          max={20}
        />
        <NumberRule
          icon={MdTimer}
          title="Spam window (seconds)"
          description="Time window the spam threshold is measured over."
          value={watch('spamWindow')}
          onChange={(v) => setValue('spamWindow', v, { shouldDirty: true })}
          min={1}
          max={30}
        />
        <NumberRule
          icon={MdAlternateEmail}
          title="Mention limit"
          description="Delete a message with more than this many user/role mentions."
          value={watch('mentionLimit')}
          onChange={(v) => setValue('mentionLimit', v, { shouldDirty: true })}
          min={3}
          max={30}
        />

        <Text fontSize="sm" color="TextSecondary">
          Members with “Manage Messages” bypass all AutoMod rules. Actions are recorded in your
          punishment log when the Logging feature is enabled.
        </Text>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          blockInvites: e.blockInvites,
          blockLinks: e.blockLinks,
          allowedDomains: e.allowedDomains,
          blockMassMentions: e.blockMassMentions,
          spamCount: e.spamCount,
          spamWindow: e.spamWindow,
          mentionLimit: e.mentionLimit,
        })
      );
      reset({
        blockInvites: result?.blockInvites ?? false,
        blockLinks: result?.blockLinks ?? false,
        allowedDomains: (result?.allowedDomains ?? []).slice().sort(),
        blockMassMentions: result?.blockMassMentions ?? false,
        spamCount: result?.spamCount ?? 5,
        spamWindow: result?.spamWindow ?? 3,
        mentionLimit: result?.mentionLimit ?? 5,
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
