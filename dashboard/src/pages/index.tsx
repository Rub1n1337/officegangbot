import { Box, Flex, Text, Heading, Icon, Button, SimpleGrid, Container } from '@chakra-ui/react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  MdSmartToy,
  MdGavel,
  MdShield,
  MdConfirmationNumber,
  MdTrendingUp,
  MdInsights,
  MdPeople,
  MdCrisisAlert,
  MdVerifiedUser,
  MdArrowForward,
  MdTranslate,
} from 'react-icons/md';
import { FaDiscord } from 'react-icons/fa';
import type { IconType } from 'react-icons';
import { config } from '@/config/common';
import { useText } from '@/config/translations/ui-text';

const GRADIENT = 'linear(135deg, #8B7CFF, #6E56F5)';

function Logo() {
  return (
    <Flex align="center" gap={3}>
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

function FeatureCard({ icon, title, desc }: { icon: IconType; title: string; desc: string }) {
  return (
    <Box
      bg="CardBackground"
      border="1px solid"
      borderColor="CardBorder"
      rounded="16px"
      p={6}
      boxShadow="normal"
      transition="transform .18s ease, border-color .18s ease"
      _hover={{ transform: 'translateY(-4px)', borderColor: 'brand.400' }}
    >
      <Flex
        w="46px"
        h="46px"
        rounded="13px"
        align="center"
        justify="center"
        bg="brandAlpha.100"
        color="brand.200"
        mb={4}
      >
        <Icon as={icon} boxSize="24px" />
      </Flex>
      <Heading fontSize="17px" fontWeight="700" mb={1.5}>
        {title}
      </Heading>
      <Text fontSize="14px" color="TextSecondary" lineHeight={1.6}>
        {desc}
      </Text>
    </Box>
  );
}

export default function Landing() {
  const tt = useText();
  const router = useRouter();
  const other = router.locale === 'ru' ? 'en' : 'ru';

  const features: Array<{ icon: IconType; title: string; desc: string }> = [
    { icon: MdGavel, title: tt('Модерация'), desc: tt('Предупреждения, нумерованные кейсы, временные наказания и апелляции на бан.') },
    { icon: MdShield, title: tt('Авто-модерация'), desc: tt('Анти-спам, фильтры слов, блокировка ссылок и страйки — защита 24/7.') },
    { icon: MdConfirmationNumber, title: tt('Тикеты'), desc: tt('Поддержка с приоритетами, транскриптами и авто-закрытием по неактивности.') },
    { icon: MdTrendingUp, title: tt('Уровни'), desc: tt('XP за активность, роли за уровни, множители и таблица лидеров.') },
    { icon: MdInsights, title: tt('Аналитика'), desc: tt('Тренды активности, хитмап по часам и готовые выводы по данным.') },
    { icon: MdPeople, title: tt('Приветствия'), desc: tt('Тёплая встреча новичков, авто-роли и настраиваемые сообщения.') },
    { icon: MdCrisisAlert, title: tt('Анти-рейд'), desc: tt('Ловит всплески заходов и автоматически применяет меры к волне.') },
    { icon: MdVerifiedUser, title: tt('Верификация'), desc: tt('Гейт для новичков: роль выдаётся только после подтверждения.') },
  ];

  const dash = '/user/home';
  const R = 34;
  const CIRC = 2 * Math.PI * R;

  return (
    <Box minH="100vh" bg="MainBackground">
      <Head>
        <title>{`${config.name} — ${tt('Discord-бот для порядка на сервере')}`}</title>
        <meta name="description" content={tt('Модерация, авто-модерация, тикеты, уровни и аналитика — в одном боте с чистой панелью управления.')} />
        <meta name="robots" content="index,follow" />
      </Head>

      {/* Nav */}
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
            href={router.asPath}
            locale={other}
            variant="ghost"
            size="sm"
            leftIcon={<Icon as={MdTranslate} boxSize="16px" />}
            display={{ base: 'none', md: 'inline-flex' }}
          >
            {other.toUpperCase()}
          </Button>
          <Button as={Link} href={dash} variant="ghost" size="sm" display={{ base: 'none', md: 'inline-flex' }}>
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

      {/* Hero */}
      <Container maxW="6xl" px={{ base: 5, md: 8 }}>
        <Flex direction={{ base: 'column', lg: 'row' }} align="center" gap={{ base: 10, lg: 16 }} py={{ base: 14, md: 24 }}>
          <Box flex="1" minW={0}>
            <Flex
              display="inline-flex"
              align="center"
              gap={2}
              px={3}
              py={1.5}
              rounded="full"
              bg="brandAlpha.100"
              color="brand.200"
              fontSize="12px"
              fontWeight="700"
              letterSpacing="0.02em"
              mb={5}
            >
              <Box w="7px" h="7px" rounded="full" bg="green.400" />
              {tt('Discord-бот для порядка на сервере')}
            </Flex>
            <Heading fontSize={{ base: '36px', md: '52px' }} fontWeight="800" letterSpacing="-0.03em" lineHeight={1.05}>
              {tt('Ваш сервер —')}{' '}
              <Box as="span" bgGradient={GRADIENT} bgClip="text">
                {tt('на автопилоте')}
              </Box>
            </Heading>
            <Text fontSize={{ base: '16px', md: '18px' }} color="TextSecondary" mt={5} maxW="520px" lineHeight={1.6}>
              {tt('Модерация, авто-модерация, тикеты, уровни и аналитика — в одном боте с чистой панелью управления.')}
            </Text>
            <Flex gap={3} mt={8} wrap="wrap">
              <Button
                as="a"
                href={config.inviteUrl}
                target="_blank"
                rel="noreferrer"
                size="lg"
                color="white"
                bgGradient={GRADIENT}
                _hover={{ opacity: 0.92 }}
                leftIcon={<Icon as={FaDiscord} boxSize="20px" />}
              >
                {tt('Добавить на сервер')}
              </Button>
              <Button as={Link} href={dash} size="lg" variant="outline" borderColor="CardBorder" rightIcon={<Icon as={MdArrowForward} />}>
                {tt('Открыть панель')}
              </Button>
            </Flex>
            <Text fontSize="13px" color="TextSecondary" mt={5}>
              {tt('Бесплатно • Русский и English • Настройка за минуты')}
            </Text>
          </Box>

          {/* Hero visual: the Server Pulse card — our signature metric */}
          <Box flex="1" minW={0} w="full" maxW={{ base: '420px', lg: 'none' }}>
            <Box position="relative">
              <Box
                position="absolute"
                inset="-40px"
                bgGradient="radial(closest-side, rgba(110,86,245,.35), transparent)"
                filter="blur(20px)"
                pointerEvents="none"
              />
              <Box
                position="relative"
                bg="CardBackground"
                border="1px solid"
                borderColor="CardBorder"
                rounded="20px"
                p={6}
                boxShadow="0 30px 60px -20px rgba(20,20,40,.45)"
                color="TextSecondary"
              >
                <Flex align="center" gap={5}>
                  <Box position="relative" flexShrink={0} lineHeight={0}>
                    <svg width="88" height="88" viewBox="0 0 88 88" aria-hidden>
                      <circle cx="44" cy="44" r={R} fill="none" strokeWidth="8" stroke="currentColor" opacity={0.14} />
                      <circle
                        cx="44"
                        cy="44"
                        r={R}
                        fill="none"
                        strokeWidth="8"
                        stroke="#22C55E"
                        strokeLinecap="round"
                        strokeDasharray={`${0.86 * CIRC} ${CIRC}`}
                        transform="rotate(-90 44 44)"
                      />
                    </svg>
                    <Flex position="absolute" inset={0} align="center" justify="center">
                      <Text fontSize="26px" fontWeight="800" color="TextPrimary">
                        86
                      </Text>
                    </Flex>
                  </Box>
                  <Box>
                    <Text fontSize="11px" fontWeight="700" letterSpacing="0.1em">
                      {tt('ПУЛЬС СЕРВЕРА')}
                    </Text>
                    <Text fontSize="17px" fontWeight="800" color="#22C55E">
                      {tt('Отлично')}
                    </Text>
                    <Flex gap={3} mt={2} fontSize="12px" wrap="wrap">
                      <Flex align="center" gap={1.5}>
                        <Box w="8px" h="8px" rounded="full" bg="green.400" />
                        {tt('Онлайн')}
                      </Flex>
                      <Flex align="center" gap={1.5}>
                        <Box w="8px" h="8px" rounded="full" bg="green.400" />
                        {tt('Настроен')}
                      </Flex>
                      <Flex align="center" gap={1.5}>
                        <Box w="8px" h="8px" rounded="full" bg="green.400" />
                        {tt('Активность')}
                      </Flex>
                    </Flex>
                  </Box>
                </Flex>
                <SimpleGrid columns={3} gap={3} mt={5}>
                  {[
                    [tt('Участников'), '12 480'],
                    [tt('Сообщения · 7д'), '38 205'],
                    [tt('Открыто тикетов'), '3'],
                  ].map(([label, value]) => (
                    <Box key={label} bg="secondaryGray.100" _dark={{ bg: 'navy.600' }} rounded="12px" p={3}>
                      <Text fontSize="10.5px" fontWeight="600">
                        {label}
                      </Text>
                      <Text fontSize="18px" fontWeight="800" color="TextPrimary" mt={1}>
                        {value}
                      </Text>
                    </Box>
                  ))}
                </SimpleGrid>
              </Box>
            </Box>
          </Box>
        </Flex>
      </Container>

      {/* Features */}
      <Container maxW="6xl" px={{ base: 5, md: 8 }} py={{ base: 8, md: 12 }}>
        <Box textAlign="center" mb={10}>
          <Text fontSize="12px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
            {tt('ВОЗМОЖНОСТИ')}
          </Text>
          <Heading fontSize={{ base: '26px', md: '34px' }} fontWeight="800" letterSpacing="-0.02em" mt={2}>
            {tt('Всё для управления сообществом')}
          </Heading>
        </Box>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={5}>
          {features.map((f) => (
            <FeatureCard key={f.title} {...f} />
          ))}
        </SimpleGrid>
      </Container>

      {/* Final CTA */}
      <Container maxW="6xl" px={{ base: 5, md: 8 }} py={{ base: 12, md: 20 }}>
        <Box
          bgGradient={GRADIENT}
          rounded="24px"
          px={{ base: 8, md: 16 }}
          py={{ base: 12, md: 16 }}
          textAlign="center"
          boxShadow="0 30px 60px -25px rgba(110,86,245,.7)"
        >
          <Heading color="white" fontSize={{ base: '26px', md: '36px' }} fontWeight="800" letterSpacing="-0.02em">
            {tt('Готовы навести порядок?')}
          </Heading>
          <Text color="whiteAlpha.900" fontSize={{ base: '15px', md: '17px' }} mt={3} maxW="560px" mx="auto">
            {tt('Добавьте бота за пару кликов и настройте всё в одной панели.')}
          </Text>
          <Button
            as="a"
            href={config.inviteUrl}
            target="_blank"
            rel="noreferrer"
            size="lg"
            mt={8}
            bg="white"
            color="#6E56F5"
            _hover={{ bg: 'whiteAlpha.900' }}
            leftIcon={<Icon as={FaDiscord} boxSize="20px" />}
          >
            {tt('Добавить на сервер')}
          </Button>
        </Box>
      </Container>

      {/* Footer */}
      <Box borderTop="1px solid" borderColor="CardBorder">
        <Container maxW="6xl" px={{ base: 5, md: 8 }} py={8}>
          <Flex direction={{ base: 'column', md: 'row' }} align={{ base: 'flex-start', md: 'center' }} gap={4}>
            <Logo />
            <Flex ml={{ md: 'auto' }} gap={6} fontSize="14px" color="TextSecondary" wrap="wrap">
              <Box as={Link} href="/privacy" _hover={{ color: 'TextPrimary' }}>
                {tt('Конфиденциальность')}
              </Box>
              <Box as={Link} href="/terms" _hover={{ color: 'TextPrimary' }}>
                {tt('Условия')}
              </Box>
              <Box as={Link} href={dash} _hover={{ color: 'TextPrimary' }}>
                {tt('Панель')}
              </Box>
            </Flex>
          </Flex>
          <Text fontSize="12.5px" color="TextSecondary" mt={5}>
            © {new Date().getFullYear()} {config.name}
          </Text>
        </Container>
      </Box>
    </Box>
  );
}
