import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  Icon,
  Input,
  InputGroup,
  InputLeftElement,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  SimpleGrid,
  Skeleton,
  Switch,
  Text,
} from '@chakra-ui/react';
import { useRouter } from 'next/router';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { MdSearch, MdTune } from 'react-icons/md';
import getGuildLayout from '@/components/layout/guild/get-guild-layout';
import { NextPageWithLayout } from '@/pages/_app';
import { useCommandsQuery, useSetCommandOverrideMutation } from '@/api/hooks';
import { QueryStatus } from '@/components/panel/QueryPanel';
import { ChannelMultiSelectForm } from '@/components/forms/ChannelSelect';
import { RoleMultiSelectForm } from '@/components/forms/RoleSelect';
import { useText } from '@/config/translations/ui-text';
import { useFormText } from '@/config/translations/form-text';
import type { CommandInfo, CommandOverride } from '@/api/bot';

const DEFAULT_OVERRIDE: CommandOverride = {
  enabled: true,
  allowed_channels: [],
  ignored_channels: [],
  allowed_roles: [],
  ignored_roles: [],
};

function CommandCard({
  guild,
  cmd,
  override,
  onEdit,
}: {
  guild: string;
  cmd: CommandInfo;
  override: CommandOverride;
  onEdit: () => void;
}) {
  const tt = useText();
  const mutation = useSetCommandOverrideMutation();
  // # = channels, @ = roles — Discord's own shorthand, so the pill reads at a
  // glance in any language without a plural rule.
  const chCount = override.allowed_channels.length + override.ignored_channels.length;
  const roleCount = override.allowed_roles.length + override.ignored_roles.length;

  const toggle = () =>
    mutation.mutate({
      guild,
      command: cmd.name,
      enabled: !override.enabled,
      allowedChannels: override.allowed_channels.map(String),
      ignoredChannels: override.ignored_channels.map(String),
      allowedRoles: override.allowed_roles.map(String),
      ignoredRoles: override.ignored_roles.map(String),
    });

  const pill = {
    variant: 'subtle',
    colorScheme: 'purple',
    rounded: 'full',
    px: 2,
    fontSize: '11px',
    flexShrink: 0,
  } as const;

  return (
    <Box bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="16px" p={4}>
      <Flex align="center" gap={2}>
        <Text
          fontWeight="700"
          fontSize="15px"
          isTruncated
          minW={0}
          color={override.enabled ? undefined : 'TextSecondary'}
        >
          /{cmd.name}
        </Text>
        {chCount > 0 && (
          <Badge {...pill} title={tt('Каналы')}>
            #{chCount}
          </Badge>
        )}
        {roleCount > 0 && (
          <Badge {...pill} title={tt('Роли')}>
            @{roleCount}
          </Badge>
        )}
        <Switch
          ml="auto"
          aria-label={`/${cmd.name}`}
          isChecked={override.enabled}
          onChange={toggle}
          isDisabled={mutation.isLoading}
          colorScheme="brand"
        />
      </Flex>
      {cmd.description && (
        <Text fontSize="13px" color="TextSecondary" mt={1} noOfLines={2}>
          {cmd.description}
        </Text>
      )}
      <Button
        size="xs"
        variant="outline"
        borderColor="CardBorder"
        leftIcon={<Icon as={MdTune} />}
        mt={2}
        onClick={onEdit}
      >
        {tt('Права')}
      </Button>
    </Box>
  );
}

function CommandSettingsModal({
  guild,
  cmd,
  override,
  onClose,
}: {
  guild: string;
  cmd: CommandInfo;
  override: CommandOverride;
  onClose: () => void;
}) {
  const tt = useText();
  const mutation = useSetCommandOverrideMutation();
  const { control, handleSubmit } = useForm({
    defaultValues: {
      allowedChannels: override.allowed_channels.map(String),
      ignoredChannels: override.ignored_channels.map(String),
      allowedRoles: override.allowed_roles.map(String),
      ignoredRoles: override.ignored_roles.map(String),
    },
  });

  const save = handleSubmit((v) => {
    mutation.mutate({ guild, command: cmd.name, enabled: override.enabled, ...v });
    onClose();
  });

  return (
    <Modal isOpen onClose={onClose} isCentered size="lg">
      <ModalOverlay />
      <ModalContent bg="CardBackground" mx={4} rounded="16px">
        <ModalHeader>
          {tt('Права команды')} · <Text as="span" color="brand.200">/{cmd.name}</Text>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <Flex direction="column" gap={3}>
            <ChannelMultiSelectForm
              control={{ label: tt('Разрешённые каналы') }}
              controller={{ control, name: 'allowedChannels' }}
            />
            <ChannelMultiSelectForm
              control={{ label: tt('Игнорируемые каналы') }}
              controller={{ control, name: 'ignoredChannels' }}
            />
            <RoleMultiSelectForm
              control={{ label: tt('Разрешённые роли') }}
              controller={{ control, name: 'allowedRoles' }}
            />
            <RoleMultiSelectForm
              control={{ label: tt('Игнорируемые роли') }}
              controller={{ control, name: 'ignoredRoles' }}
            />
            <Text fontSize="xs" color="TextSecondary">
              {tt('Администраторы всегда обходят эти ограничения.')}
            </Text>
          </Flex>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" onClick={onClose}>
            {tt('Отмена')}
          </Button>
          <Button colorScheme="brand" ml={3} onClick={save} isLoading={mutation.isLoading}>
            {tt('Сохранить')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

const CommandsPage: NextPageWithLayout = () => {
  const guild = useRouter().query.guild as string;
  const query = useCommandsQuery(guild);
  const tt = useText();
  const ft = useFormText();
  const [category, setCategory] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<CommandInfo | null>(null);

  const commands = useMemo(() => query.data?.commands ?? [], [query.data]);
  const overrides = query.data?.overrides ?? {};
  const categories = useMemo(
    () => Array.from(new Set(commands.map((c) => c.category))),
    [commands]
  );
  const active = category ?? categories[0] ?? null;

  // A query searches every command by name/description; an empty query falls
  // back to the active category tab.
  const q = search.trim().toLowerCase();
  const searching = q.length > 0;
  const shown = commands.filter((c) =>
    searching
      ? c.name.toLowerCase().includes(q) || (c.description ?? '').toLowerCase().includes(q)
      : c.category === active
  );

  return (
    <Flex direction="column" gap={5}>
      <Box>
        <Text fontSize="11px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
          {tt('КОМАНДЫ')}
        </Text>
        <Heading fontSize="26px" fontWeight="800" letterSpacing="-0.02em" mt={1}>
          {tt('Команды')}
        </Heading>
        <Text fontSize="14px" color="TextSecondary" mt={1}>
          {tt('Включайте, выключайте и ограничивайте команды по каналам и ролям.')}
        </Text>
      </Box>

      <InputGroup maxW={{ base: 'full', md: '320px' }}>
        <InputLeftElement pointerEvents="none">
          <Icon as={MdSearch} color="TextSecondary" />
        </InputLeftElement>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={tt('Поиск команды…')}
          bg="CardBackground"
        />
      </InputGroup>

      {!searching && categories.length > 0 && (
        <Flex gap={2} wrap="wrap">
          {categories.map((c) => (
            <Button
              key={c}
              size="sm"
              variant={c === active ? 'solid' : 'outline'}
              colorScheme={c === active ? 'brand' : undefined}
              borderColor="CardBorder"
              onClick={() => setCategory(c)}
            >
              {ft(c)}
            </Button>
          ))}
        </Flex>
      )}

      <QueryStatus
        query={query}
        error={tt('Не удалось загрузить команды.')}
        loading={
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} h="110px" rounded="16px" />
            ))}
          </SimpleGrid>
        }
      >
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
          {shown.map((cmd) => (
            <CommandCard
              key={cmd.name}
              guild={guild}
              cmd={cmd}
              override={overrides[cmd.name] ?? DEFAULT_OVERRIDE}
              onEdit={() => setEditing(cmd)}
            />
          ))}
        </SimpleGrid>
        {shown.length === 0 && (
          <Text fontSize="sm" color="TextSecondary">
            {searching ? tt('Ничего не найдено.') : tt('Команд пока нет.')}
          </Text>
        )}
      </QueryStatus>

      {editing && (
        <CommandSettingsModal
          guild={guild}
          cmd={editing}
          override={overrides[editing.name] ?? DEFAULT_OVERRIDE}
          onClose={() => setEditing(null)}
        />
      )}
    </Flex>
  );
};

CommandsPage.getLayout = (c) => getGuildLayout({ children: c, back: true });
export default CommandsPage;
