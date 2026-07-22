import { Avatar, Box, Button, Flex, Heading, Icon, Switch, Text } from '@chakra-ui/react';
import { useColorMode } from '@chakra-ui/react';
import { MdArrowBack, MdLogout } from 'react-icons/md';
import { FaDiscord } from 'react-icons/fa';
import Link from 'next/link';
import { avatarUrl } from '@/api/discord';
import { languages, names, useLang } from '@/config/translations/provider';
import { useSettingsStore } from '@/stores';
import { NextPageWithLayout } from '@/pages/_app';
import IrisUserLayout from '@/components/layout/iris-user-layout';
import { useLogoutMutation } from '@/utils/auth/hooks';
import { useSelfUser } from '@/api/hooks';
import { useText } from '@/config/translations/ui-text';

// Iris profile screen (handoff README §11): back link, avatar header,
// Discord-account card, preferences (appearance + language segmented,
// dev mode toggle), sign out. Appearance drives Chakra color mode; language
// drives the existing i18n provider. The mockup's "compact mode" and "email
// notifications" toggles are omitted — nothing backs them.

const INSET = { bg: 'secondaryGray.100', _dark: { bg: 'navy.600' } };

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <Flex bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="11px" p={1} gap={0.5} flexShrink={0}>
      {options.map((o) => (
        <Button
          key={o.value}
          size="sm"
          rounded="8px"
          fontSize="13px"
          fontWeight={value === o.value ? '600' : '500'}
          onClick={() => value !== o.value && onChange(o.value)}
          {...(value === o.value
            ? { color: 'white', bg: 'Brand', _hover: { bg: 'Brand' } }
            : { variant: 'ghost', color: 'TextSecondary' })}
        >
          {o.label}
        </Button>
      ))}
    </Flex>
  );
}

function PrefRow({
  title,
  desc,
  control,
}: {
  title: string;
  desc: string;
  control: React.ReactNode;
}) {
  return (
    <Flex align="center" justify="space-between" gap={3} rounded="11px" p={4} {...INSET}>
      <Box minW={0}>
        <Text fontSize="14px" fontWeight="600">
          {title}
        </Text>
        <Text fontSize="13px" color="TextSecondary" mt="1px">
          {desc}
        </Text>
      </Box>
      {control}
    </Flex>
  );
}

const ProfilePage: NextPageWithLayout = () => {
  const user = useSelfUser();
  const logout = useLogoutMutation();
  const { colorMode, setColorMode } = useColorMode();
  const { lang, setLang } = useLang();
  const [devMode, setDevMode] = useSettingsStore((s) => [s.devMode, s.setDevMode]);
  const tt = useText();

  return (
    <Flex direction="column" gap={5} maxW="720px" mx="auto" w="full">
      <Flex
        as={Link}
        href="/user/home"
        align="center"
        gap={2}
        fontSize="13px"
        color="TextSecondary"
        _hover={{ color: 'TextPrimary' }}
        w="fit-content"
      >
        <Icon as={MdArrowBack} boxSize="17px" />
        {tt('Назад')}
      </Flex>

      {/* Header */}
      <Flex align="center" gap={4}>
        <Avatar src={avatarUrl(user)} name={user.username} w="72px" h="72px" />
        <Box minW={0}>
          <Heading fontSize="24px" fontWeight="800" letterSpacing="-0.02em">
            {user.username}
          </Heading>
          <Text fontSize="14px" color="TextSecondary" mt={0.5}>
            @{user.username} · {tt('Администратор')}
          </Text>
        </Box>
      </Flex>

      {/* Discord account */}
      <Box bg="CardBackground" rounded="16px" p={5} border="1px solid" borderColor="CardBorder" boxShadow="normal">
        <Text fontSize="15px" fontWeight="700" mb={4}>
          {tt('Аккаунт Discord')}
        </Text>
        <Flex align="center" gap={3} rounded="11px" p={4} {...INSET}>
          <Flex w="40px" h="40px" rounded="11px" align="center" justify="center" bg="#5865F2" color="white" flexShrink={0}>
            <Icon as={FaDiscord} boxSize="22px" />
          </Flex>
          <Box flex="1" minW={0}>
            <Text fontSize="14px" fontWeight="600" noOfLines={1}>
              {user.username}
            </Text>
            <Text fontSize="12px" color="TextSecondary">
              {tt('Подключён')} · ID {user.id}
            </Text>
          </Box>
          <Box
            as="span"
            fontSize="11px"
            fontWeight="700"
            rounded="20px"
            px={2.5}
            py={1}
            color="green.500"
            bg="green.100"
            _dark={{ bg: 'whiteAlpha.100', color: 'green.400' }}
            flexShrink={0}
          >
            {tt('Привязан')}
          </Box>
        </Flex>
      </Box>

      {/* Preferences */}
      <Box bg="CardBackground" rounded="16px" p={5} border="1px solid" borderColor="CardBorder" boxShadow="normal">
        <Text fontSize="15px" fontWeight="700" mb={4}>
          {tt('Настройки')}
        </Text>
        <Flex direction="column" gap={2.5}>
          <PrefRow
            title={tt('Оформление')}
            desc={tt('Тема интерфейса дашборда')}
            control={
              <Segmented
                value={colorMode}
                options={[
                  { value: 'dark', label: tt('Тёмная') },
                  { value: 'light', label: tt('Светлая') },
                ]}
                onChange={(v) => setColorMode(v)}
              />
            }
          />
          <PrefRow
            title={tt('Язык')}
            desc={tt('Язык интерфейса дашборда')}
            control={
              <Segmented
                value={lang}
                options={languages.map((l) => ({ value: l.key, label: names[l.key] }))}
                onChange={(v) => setLang(v)}
              />
            }
          />
          <PrefRow
            title={tt('Режим разработчика')}
            desc={tt('Технические детали для отчётов об ошибках (ответы API и т.п.)')}
            control={<Switch isChecked={devMode} onChange={(e) => setDevMode(e.target.checked)} />}
          />
        </Flex>
      </Box>

      <Button
        alignSelf="flex-start"
        rounded="12px"
        variant="outline"
        color="red.400"
        borderColor="red.400"
        _hover={{ bg: 'rgba(241,106,106,0.1)' }}
        leftIcon={<Icon as={MdLogout} />}
        isLoading={logout.isLoading}
        onClick={() => logout.mutate()}
      >
        {tt('Выйти из аккаунта')}
      </Button>
    </Flex>
  );
};

ProfilePage.getLayout = (p) => <IrisUserLayout>{p}</IrisUserLayout>;

export default ProfilePage;
