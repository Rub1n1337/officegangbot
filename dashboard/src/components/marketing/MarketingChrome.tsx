import { Box, Button, Container, Flex, Icon, Text } from '@chakra-ui/react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { MdSmartToy, MdTranslate, MdWorkspacePremium } from 'react-icons/md';
import { FaDiscord } from 'react-icons/fa';
import { config } from '@/config/common';
import { useText } from '@/config/translations/ui-text';

// Shared chrome for the public marketing pages (landing + premium). Kept in one
// place so the nav, footer and brand mark stay identical across both.
export const GRADIENT = 'linear(135deg, #8B7CFF, #6E56F5)';

// The dashboard entry point — the server picker.
const DASH = '/user/home';

// The brand mark. Always a link home, matching the "logo returns home
// everywhere" convention (the legal pages rely on this too).
export function Logo() {
  return (
    <Flex as={Link} href="/" align="center" gap={3} _hover={{ opacity: 0.85 }}>
      <Flex
        w="38px"
        h="38px"
        rounded="11px"
        align="center"
        justify="center"
        bgGradient={GRADIENT}
        boxShadow="0 8px 18px -6px rgba(110,86,245,.6)"
        flexShrink={0}
      >
        <Icon as={MdSmartToy} boxSize="22px" color="white" />
      </Flex>
      <Text fontSize="18px" fontWeight="800" letterSpacing="-0.01em">
        {config.name}
      </Text>
    </Flex>
  );
}

export function MarketingNav() {
  const tt = useText();
  const router = useRouter();
  const other = router.locale === 'ru' ? 'en' : 'ru';

  return (
    <Flex
      as="header"
      position="sticky"
      top={0}
      zIndex="banner"
      align="center"
      gap={4}
      px={{ base: 5, md: 10 }}
      py={4}
      borderBottom="1px solid"
      borderColor="CardBorder"
      bg="MainBackground"
      sx={{ backdropFilter: 'saturate(180%) blur(8px)' }}
    >
      <Logo />
      <Flex ml="auto" align="center" gap={{ base: 2, md: 3 }}>
        <Button
          as={Link}
          href="/premium"
          variant="ghost"
          size="sm"
          leftIcon={<Icon as={MdWorkspacePremium} boxSize="16px" />}
          display={{ base: 'none', md: 'inline-flex' }}
        >
          {tt('Премиум')}
        </Button>
        <Button
          as={Link}
          href={router.asPath}
          locale={other}
          variant="ghost"
          size="sm"
          leftIcon={<Icon as={MdTranslate} boxSize="16px" />}
          display={{ base: 'none', md: 'inline-flex' }}
        >
          {other.toUpperCase()}
        </Button>
        <Button as={Link} href={DASH} variant="ghost" size="sm" display={{ base: 'none', md: 'inline-flex' }}>
          {tt('Открыть панель')}
        </Button>
        <Button
          as="a"
          href={config.inviteUrl}
          target="_blank"
          rel="noreferrer"
          size="sm"
          color="white"
          bgGradient={GRADIENT}
          _hover={{ opacity: 0.92 }}
          leftIcon={<Icon as={FaDiscord} boxSize="16px" />}
        >
          {tt('Добавить на сервер')}
        </Button>
      </Flex>
    </Flex>
  );
}

export function MarketingFooter() {
  const tt = useText();
  const links: Array<[string, string]> = [
    ['/premium', tt('Премиум')],
    ['/privacy', tt('Конфиденциальность')],
    ['/terms', tt('Условия')],
    [DASH, tt('Панель')],
  ];
  return (
    <Box borderTop="1px solid" borderColor="CardBorder">
      <Container maxW="6xl" px={{ base: 5, md: 8 }} py={8}>
        <Flex direction={{ base: 'column', md: 'row' }} align={{ base: 'flex-start', md: 'center' }} gap={4}>
          <Logo />
          <Flex ml={{ md: 'auto' }} gap={6} fontSize="14px" color="TextSecondary" wrap="wrap">
            {links.map(([href, label]) => (
              <Box key={href} as={Link} href={href} _hover={{ color: 'TextPrimary' }}>
                {label}
              </Box>
            ))}
          </Flex>
        </Flex>
        <Text fontSize="13px" color="TextSecondary" mt={5}>
          © {new Date().getFullYear()} {config.name}
        </Text>
      </Container>
    </Box>
  );
}
