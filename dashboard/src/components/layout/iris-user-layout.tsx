import { Box, Flex, Icon, Text, useColorMode } from '@chakra-ui/react';
import { ReactNode } from 'react';
import Link from 'next/link';
import { MdSmartToy, MdDarkMode, MdLightMode, MdPerson } from 'react-icons/md';
import { avatarUrl } from '@/api/discord';
import { useSelfUserQuery } from '@/api/hooks';
import { useText } from '@/config/translations/ui-text';

// Iris shell for the /user pages (server picker, profile). The mockup shows
// these without the guild sidebar — a slim top bar (logo, theme toggle,
// avatar) over a centered content column. Replaces the legacy template
// AppLayout that still rendered the old "Pages / Dashboard" sidebar around
// the redesigned screens.
export default function IrisUserLayout({ children }: { children: ReactNode }) {
  const { colorMode, toggleColorMode } = useColorMode();
  const user = useSelfUserQuery().data;
  const tt = useText();

  return (
    <Flex direction="column" minH="100vh" bg="MainBackground">
      <Flex
        align="center"
        gap="12px"
        px={{ base: '16px', md: '28px' }}
        py="14px"
        borderBottom="1px solid"
        borderColor="CardBorder"
        bg="white"
        _dark={{ bg: '#0D0D18' }}
      >
        <Flex as={Link} href="/user/home" align="center" gap="11px">
          <Flex
            w="34px"
            h="34px"
            rounded="11px"
            align="center"
            justify="center"
            bgGradient="linear(135deg, #8B7CFF, #6E56F5)"
            boxShadow="0 8px 18px -6px rgba(110,86,245,.6)"
            flexShrink={0}
          >
            <Icon as={MdSmartToy} boxSize="20px" color="white" />
          </Flex>
          <Box lineHeight="1.15">
            <Text fontWeight="700" fontSize="15px" letterSpacing="-0.01em">
              OfficeGangBot
            </Text>
            <Text fontSize="11px" color="TextSecondary">
              {tt('Панель управления')}
            </Text>
          </Box>
        </Flex>

        <Flex ml="auto" align="center" gap="10px">
          <Flex
            as="button"
            title={tt('Сменить тему')}
            onClick={toggleColorMode}
            w="38px"
            h="38px"
            rounded="11px"
            border="1px solid"
            borderColor="CardBorder"
            align="center"
            justify="center"
            color="TextSecondary"
            transition="background .15s ease"
            _hover={{ bg: 'blackAlpha.50', _dark: { bg: 'whiteAlpha.50' } }}
          >
            <Icon as={colorMode === 'light' ? MdDarkMode : MdLightMode} boxSize="19px" />
          </Flex>
          <Flex
            as={Link}
            href="/user/profile"
            title={tt('Профиль')}
            w="38px"
            h="38px"
            rounded="full"
            overflow="hidden"
            align="center"
            justify="center"
            bg="blackAlpha.100"
            _dark={{ bg: 'whiteAlpha.100' }}
            color="TextSecondary"
            border="1px solid"
            borderColor="transparent"
            transition="border-color .15s ease"
            _hover={{ borderColor: 'brand.400' }}
          >
            {user ? (
              <Box as="img" src={avatarUrl(user)} alt="" w="full" h="full" objectFit="cover" />
            ) : (
              <Icon as={MdPerson} boxSize="20px" />
            )}
          </Flex>
        </Flex>
      </Flex>

      <Box flex="1" overflowY="auto">
        <Box maxW="1080px" mx="auto" px={{ base: '20px', md: '28px' }} py={{ base: '22px', md: '26px' }}>
          {children}
        </Box>
      </Box>
    </Flex>
  );
}
