import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useState } from 'react';
import {
  Box,
  Button,
  Divider,
  Flex,
  Icon,
  IconButton,
  Input,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Select,
  Switch,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
} from '@chakra-ui/react';
import {
  MdShield,
  MdAlternateEmail,
  MdLink,
  MdGroupAdd,
  MdTimer,
  MdCampaign,
  MdGavel,
  MdAdd,
  MdDelete,
  MdRule,
  MdScience,
} from 'react-icons/md';
import { FormCardController } from '@/components/forms/Form';
import { ChannelMultiSelectForm } from '@/components/forms/ChannelSelect';
import { RoleMultiSelectForm } from '@/components/forms/RoleSelect';
import { useFormText } from '@/config/translations/form-text';
import type { AutomodFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

const schema = z.object({
  dryRun: z.boolean(),
  ignoredChannels: z.array(z.string()),
  ignoredRoles: z.array(z.string()),
  blockInvites: z.boolean(),
  blockLinks: z.boolean(),
  allowedDomains: z.array(z.string()),
  blockMassMentions: z.boolean(),
  spamCount: z.number().int().min(3).max(20),
  spamWindow: z.number().int().min(1).max(30),
  mentionLimit: z.number().int().min(3).max(30),
  strikesEnabled: z.boolean(),
  strikeExpiryHours: z.number().int().min(0).max(720),
  strikeMuteAt: z.number().int().min(0).max(50),
  strikeKickAt: z.number().int().min(0).max(50),
  strikeBanAt: z.number().int().min(0).max(50),
  rules: z
    .array(
      z.object({
        pattern: z.string().max(200),
        action: z.enum(['delete', 'strike']),
        enabled: z.boolean(),
      })
    )
    .max(25),
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
  const ft = useFormText();
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
        placeholder={ft('e.g. youtube.com — press Enter to add')}
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

function defaultsFrom(data: Partial<AutomodFeature>): Input {
  return {
    dryRun: data.dryRun ?? false,
    ignoredChannels: data.ignoredChannels ?? [],
    ignoredRoles: data.ignoredRoles ?? [],
    blockInvites: data.blockInvites ?? false,
    blockLinks: data.blockLinks ?? false,
    allowedDomains: (data.allowedDomains ?? []).slice().sort(),
    blockMassMentions: data.blockMassMentions ?? false,
    spamCount: data.spamCount ?? 5,
    spamWindow: data.spamWindow ?? 3,
    mentionLimit: data.mentionLimit ?? 5,
    strikesEnabled: data.strikesEnabled ?? false,
    strikeExpiryHours: data.strikeExpiryHours ?? 24,
    strikeMuteAt: data.strikeMuteAt ?? 0,
    strikeKickAt: data.strikeKickAt ?? 0,
    strikeBanAt: data.strikeBanAt ?? 0,
    rules: (data.rules ?? []).map((r) => ({
      pattern: r.pattern ?? '',
      action: r.action === 'strike' ? 'strike' : 'delete',
      enabled: r.enabled ?? true,
    })),
  };
}

export const useAutomodFeature: UseFormRender<AutomodFeature> = (data, onSubmit) => {
  const ft = useFormText();
  const { reset, handleSubmit, control, formState, watch, setValue, register } = useForm<Input>({
    resolver: zodResolver(schema),
    shouldUnregister: false,
    defaultValues: defaultsFrom(data),
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'rules' });
  const blockLinks = watch('blockLinks');
  const strikesEnabled = watch('strikesEnabled');
  const dryRun = watch('dryRun');

  return {
    component: (
      <Flex direction="column" gap={3}>
        <ToggleRule
          icon={MdScience}
          title={ft('Dry-run (test mode)')}
          description={ft(
            'Detect and log violations to your log channel without deleting messages, timing out members or adding strikes. Use it to tune your rules safely before enforcing them.'
          )}
          checked={dryRun}
          onChange={(v) => setValue('dryRun', v, { shouldDirty: true })}
        />
        {dryRun && (
          <Flex
            bg="orange.50"
            _dark={{ bg: 'orange.900', borderColor: 'orange.700' }}
            borderWidth="1px"
            borderColor="orange.200"
            rounded="xl"
            p={3}
            gap={2}
            align="center"
          >
            <Icon as={MdScience} color="orange.500" flexShrink={0} />
            <Text fontSize="sm" color="orange.800" _dark={{ color: 'orange.100' }}>
              {ft(
                'Dry-run is on — AutoMod will only log what it would do (needs the Logging feature and a punishment log channel). No messages are deleted and no strikes are added.'
              )}
            </Text>
          </Flex>
        )}

        <Divider my={1} />

        <Text fontWeight="600">{ft('Exemptions')}</Text>
        <Text fontSize="sm" color="TextSecondary">
          {ft('Channels and roles listed here are ignored by AutoMod entirely.')}
        </Text>
        <ChannelMultiSelectForm
          control={{
            label: ft('Ignored channels'),
            description: ft('AutoMod skips messages in these channels (and their categories).'),
          }}
          controller={{ control, name: 'ignoredChannels' }}
        />
        <RoleMultiSelectForm
          control={{
            label: ft('Ignored roles'),
            description: ft('Members with any of these roles bypass AutoMod.'),
          }}
          controller={{ control, name: 'ignoredRoles' }}
        />

        <Divider my={1} />

        <Text fontWeight="600">{ft('Content filter')}</Text>
        <ToggleRule
          icon={MdGroupAdd}
          title={ft('Block invite links')}
          description={ft('Delete messages containing Discord invite links (discord.gg/…).')}
          checked={watch('blockInvites')}
          onChange={(v) => setValue('blockInvites', v, { shouldDirty: true })}
        />
        <ToggleRule
          icon={MdLink}
          title={ft('Block external links')}
          description={ft('Delete messages that contain links, except to the allowed domains below.')}
          checked={blockLinks}
          onChange={(v) => setValue('blockLinks', v, { shouldDirty: true })}
        />
        {blockLinks && (
          <FormCardController
            control={{
              label: ft('Allowed domains'),
              description: ft('Links to these domains (and their subdomains) are allowed.'),
            }}
            controller={{ control, name: 'allowedDomains' }}
            render={({ field }) => <DomainsInput value={field.value ?? []} onChange={field.onChange} />}
          />
        )}
        <ToggleRule
          icon={MdCampaign}
          title={ft('Block @everyone / @here')}
          description={ft('Delete messages that mention @everyone or @here.')}
          checked={watch('blockMassMentions')}
          onChange={(v) => setValue('blockMassMentions', v, { shouldDirty: true })}
        />

        <Divider my={1} />

        <Text fontWeight="600">{ft('Anti-spam & mentions')}</Text>
        <Text fontSize="sm" color="TextSecondary">
          {ft('These limits run whenever AutoMod is enabled. Tune the thresholds to fit your server.')}
        </Text>
        <NumberRule
          icon={MdShield}
          title={ft('Spam message threshold')}
          description={ft('Messages within the window that trigger a 10-minute timeout.')}
          value={watch('spamCount')}
          onChange={(v) => setValue('spamCount', v, { shouldDirty: true })}
          min={3}
          max={20}
        />
        <NumberRule
          icon={MdTimer}
          title={ft('Spam window (seconds)')}
          description={ft('Time window the spam threshold is measured over.')}
          value={watch('spamWindow')}
          onChange={(v) => setValue('spamWindow', v, { shouldDirty: true })}
          min={1}
          max={30}
        />
        <NumberRule
          icon={MdAlternateEmail}
          title={ft('Mention limit')}
          description={ft('Delete a message with more than this many user/role mentions.')}
          value={watch('mentionLimit')}
          onChange={(v) => setValue('mentionLimit', v, { shouldDirty: true })}
          min={3}
          max={30}
        />

        <Divider my={1} />

        <Text fontWeight="600">{ft('Strike system')}</Text>
        <ToggleRule
          icon={MdGavel}
          title={ft('Enable strikes')}
          description={ft('Every AutoMod violation adds a strike; crossing a threshold escalates the punishment.')}
          checked={strikesEnabled}
          onChange={(v) => setValue('strikesEnabled', v, { shouldDirty: true })}
        />
        {strikesEnabled && (
          <>
            <NumberRule
              icon={MdTimer}
              title={ft('Strike expiry (hours)')}
              description={ft('Strikes older than this stop counting. 0 = never expire.')}
              value={watch('strikeExpiryHours')}
              onChange={(v) => setValue('strikeExpiryHours', v, { shouldDirty: true })}
              min={0}
              max={720}
            />
            <NumberRule
              icon={MdShield}
              title={ft('Mute at (strikes)')}
              description={ft('Timeout the member for 10 minutes at this many strikes. 0 = off.')}
              value={watch('strikeMuteAt')}
              onChange={(v) => setValue('strikeMuteAt', v, { shouldDirty: true })}
              min={0}
              max={50}
            />
            <NumberRule
              icon={MdGroupAdd}
              title={ft('Kick at (strikes)')}
              description={ft('Kick the member at this many strikes. 0 = off.')}
              value={watch('strikeKickAt')}
              onChange={(v) => setValue('strikeKickAt', v, { shouldDirty: true })}
              min={0}
              max={50}
            />
            <NumberRule
              icon={MdGavel}
              title={ft('Ban at (strikes)')}
              description={ft('Ban the member at this many strikes. 0 = off.')}
              value={watch('strikeBanAt')}
              onChange={(v) => setValue('strikeBanAt', v, { shouldDirty: true })}
              min={0}
              max={50}
            />
          </>
        )}

        <Divider my={1} />

        <Flex align="center" justify="space-between" gap={2}>
          <Box>
            <Text fontWeight="600">{ft('Custom filters (regex)')}</Text>
            <Text fontSize="sm" color="TextSecondary">
              {ft(
                'Delete messages matching a pattern. “Strike” also adds a strike (when strikes are on). Up to 25 rules.'
              )}
            </Text>
          </Box>
          <Button
            size="sm"
            leftIcon={<Icon as={MdAdd} />}
            onClick={() => append({ pattern: '', action: 'delete', enabled: true })}
            isDisabled={fields.length >= 25}
            flexShrink={0}
          >
            {ft('Add rule')}
          </Button>
        </Flex>
        {fields.length === 0 ? (
          <Flex
            bg="CardBackground"
            rounded="2xl"
            p={4}
            gap={3}
            align="center"
            borderWidth="1px"
            borderColor="CardBorder"
            color="TextSecondary"
          >
            <Icon as={MdRule} fontSize="xl" />
            <Text fontSize="sm">{ft('No custom filters yet.')}</Text>
          </Flex>
        ) : (
          fields.map((f, i) => (
            <Flex
              key={f.id}
              bg="CardBackground"
              rounded="2xl"
              p={3}
              gap={2}
              align="center"
              borderWidth="1px"
              borderColor="CardBorder"
              wrap="wrap"
            >
              <Switch
                isChecked={watch(`rules.${i}.enabled`)}
                onChange={(e) => setValue(`rules.${i}.enabled`, e.target.checked, { shouldDirty: true })}
                flexShrink={0}
              />
              <Input
                variant="main"
                flex={1}
                minW="180px"
                placeholder={ft('regex pattern, e.g. free\\s*nitro')}
                {...register(`rules.${i}.pattern`)}
              />
              <Select variant="main" w="130px" flexShrink={0} {...register(`rules.${i}.action`)}>
                <option value="delete">{ft('Delete')}</option>
                <option value="strike">{ft('Strike')}</option>
              </Select>
              <IconButton
                aria-label="Remove rule"
                icon={<MdDelete />}
                size="sm"
                variant="ghost"
                colorScheme="red"
                onClick={() => remove(i)}
                flexShrink={0}
              />
            </Flex>
          ))
        )}

        <Text fontSize="sm" color="TextSecondary">
          {ft(
            'Members with “Manage Messages” bypass all AutoMod rules. Actions are recorded in your punishment log when the Logging feature is enabled.'
          )}
        </Text>
      </Flex>
    ),
    onSubmit: handleSubmit(async (e) => {
      const result = await onSubmit(
        JSON.stringify({
          dryRun: e.dryRun,
          ignoredChannels: e.ignoredChannels,
          ignoredRoles: e.ignoredRoles,
          blockInvites: e.blockInvites,
          blockLinks: e.blockLinks,
          allowedDomains: e.allowedDomains,
          blockMassMentions: e.blockMassMentions,
          spamCount: e.spamCount,
          spamWindow: e.spamWindow,
          mentionLimit: e.mentionLimit,
          strikesEnabled: e.strikesEnabled,
          strikeExpiryHours: e.strikeExpiryHours,
          strikeMuteAt: e.strikeMuteAt,
          strikeKickAt: e.strikeKickAt,
          strikeBanAt: e.strikeBanAt,
          // Drop blank patterns client-side; the server also sanitizes.
          rules: e.rules.filter((r) => r.pattern.trim().length > 0),
        })
      );
      reset(defaultsFrom((result ?? {}) as Partial<AutomodFeature>));
    }),
    canSave: formState.isDirty,
    reset: () => reset(control._defaultValues),
  };
};
