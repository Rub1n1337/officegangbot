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
  Switch,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
} from '@chakra-ui/react';
import { MdShield, MdAlternateEmail, MdLink, MdGroupAdd } from 'react-icons/md';
import { FormCardController } from '@/components/forms/Form';
import type { AutomodFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  blockInvites: z.boolean(),
  blockLinks: z.boolean(),
  allowedDomains: z.array(z.string()),
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

function InfoRule({ icon, title, description }: { icon: typeof MdShield; title: string; description: string }) {
  return (
    <Flex bg="CardBackground" rounded="2xl" p={4} gap={3} align="flex-start" borderWidth="1px" borderColor="CardBorder">
      <Flex flexShrink={0} align="center" justify="center" boxSize="40px" rounded="xl" bg="brandAlpha.100" color="brand.500" _dark={{ color: 'brand.200' }}>
        <Icon as={icon} fontSize="xl" />
      </Flex>
      <Box>
        <Text fontWeight="600">{title}</Text>
        <Text fontSize="sm" color="TextSecondary">{description}</Text>
      </Box>
    </Flex>
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

export const useAutomodFeature: UseFormRender<AutomodFeature> = (data, onSubmit) => {
  const { reset, handleSubmit, control, formState, watch, setValue } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: {
      blockInvites: data.blockInvites ?? false,
      blockLinks: data.blockLinks ?? false,
      allowedDomains: (data.allowedDomains ?? []).slice().sort(),
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

        <Divider my={1} />

        <Text fontWeight="600">Always-on rules</Text>
        <Text fontSize="sm" color="TextSecondary">
          These anti-raid rules run whenever AutoMod is enabled and can&apos;t be turned off individually.
        </Text>
        <InfoRule icon={MdShield} title="Anti-spam" description="5+ messages in 3 seconds → 10-minute timeout." />
        <InfoRule icon={MdAlternateEmail} title="Anti-mention-spam" description="5+ user/role mentions in a message → deleted." />

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
        })
      );
      reset({
        blockInvites: result?.blockInvites ?? false,
        blockLinks: result?.blockLinks ?? false,
        allowedDomains: (result?.allowedDomains ?? []).slice().sort(),
      });
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
