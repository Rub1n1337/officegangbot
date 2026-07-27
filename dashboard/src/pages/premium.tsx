import { Box, Flex, Text, Heading, Icon, Button, SimpleGrid, Container, Badge } from '@chakra-ui/react';
import Head from 'next/head';
import {
  MdWorkspacePremium,
  MdAllInclusive,
  MdPalette,
  MdBolt,
  MdAutoAwesome,
  MdCheck,
} from 'react-icons/md';
import { FaDiscord } from 'react-icons/fa';
import type { IconType } from 'react-icons';
import { config } from '@/config/common';
import { useText } from '@/config/translations/ui-text';
import { GRADIENT, MarketingNav, MarketingFooter } from '@/components/marketing/MarketingChrome';

// Marketing price. Billing is not wired yet (the plan ships as "coming soon"),
// so this is the announced launch price — change it in one place when pricing
// is finalized.
const PRICE = '$4.99';

function CheckItem({ children, muted = false }: { children: string; muted?: boolean }) {
  return (
    <Flex align="flex-start" gap={2.5}>
      <Icon
        as={MdCheck}
        boxSize="18px"
        mt={0.5}
        flexShrink={0}
        color={muted ? 'TextSecondary' : 'brand.200'}
      />
      <Text fontSize="14px" color={muted ? 'TextSecondary' : 'TextPrimary'} lineHeight={1.5}>
        {children}
      </Text>
    </Flex>
  );
}

function PerkCard({ icon, title, items }: { icon: IconType; title: string; items: string[] }) {
  return (
    <Box bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="16px" p={6} boxShadow="normal">
      <Flex align="center" gap={3} mb={4}>
        <Flex w="44px" h="44px" rounded="13px" align="center" justify="center" bg="brandAlpha.100" color="brand.200" flexShrink={0}>
          <Icon as={icon} boxSize="24px" />
        </Flex>
        <Heading fontSize="18px" fontWeight="700">
          {title}
        </Heading>
      </Flex>
      <Flex direction="column" gap={2.5}>
        {items.map((it) => (
          <CheckItem key={it}>{it}</CheckItem>
        ))}
      </Flex>
    </Box>
  );
}

export default function Premium() {
  const tt = useText();

  const perks: Array<{ icon: IconType; title: string; items: string[] }> = [
    {
      icon: MdAllInclusive,
      title: tt('Выше лимиты'),
      items: [
        tt('Безлимитные меню ролей'),
        tt('Больше отложенных сообщений'),
        tt('Больше правил авто-модерации'),
        tt('Длинная история транскриптов'),
      ],
    },
    {
      icon: MdPalette,
      title: tt('Оформление и бренд'),
      items: [
        tt('Свои цвета эмбедов'),
        tt('Свой ник и аватар бота'),
        tt('Убрать «powered by»'),
        tt('Свои фоны для карточек рангов'),
      ],
    },
    {
      icon: MdBolt,
      title: tt('Приоритет и поддержка'),
      items: [
        tt('Приоритетная обработка команд'),
        tt('Быстрее обновление статистики'),
        tt('Премиум-канал поддержки'),
        tt('Ранний доступ к бета-функциям'),
      ],
    },
    {
      icon: MdAutoAwesome,
      title: tt('Продвинутые функции'),
      items: [
        tt('Расширенная аналитика и экспорт'),
        tt('ИИ-помощь в авто-модерации'),
        tt('Синхронизация настроек между серверами'),
        tt('Свои слэш-команды'),
      ],
    },
  ];

  const faq: Array<[string, string]> = [
    [tt('Когда запуск Премиума?'), tt('Скоро. Оплата ещё не подключена — страница показывает, что войдёт в план.')],
    [tt('Текущие функции станут платными?'), tt('Нет. Всё, что работает сейчас, остаётся бесплатным. Премиум — это только дополнительные возможности.')],
    [tt('Как можно будет оплатить?'), tt('Способы оплаты появятся к запуску. Следите за обновлениями в панели и на сервере поддержки.')],
  ];

  return (
    <Box minH="100vh" bg="MainBackground">
      <Head>
        <title>{`${config.name} Premium — ${tt('больше возможностей для сообщества')}`}</title>
        <meta
          name="description"
          content={tt('Премиум добавляет лимиты, оформление, приоритет и продвинутые функции. Все текущие возможности остаются бесплатными.')}
        />
        <meta name="robots" content="index,follow" />
      </Head>

      <MarketingNav />

      {/* Hero */}
      <Container maxW="4xl" px={{ base: 5, md: 8 }} textAlign="center" pt={{ base: 14, md: 20 }} pb={{ base: 8, md: 10 }}>
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
          letterSpacing="0.08em"
          mb={5}
        >
          <Icon as={MdWorkspacePremium} boxSize="15px" />
          {tt('ПРЕМИУМ')}
          <Badge colorScheme="purple" rounded="full" px={2} textTransform="none" letterSpacing="normal">
            {tt('Скоро')}
          </Badge>
        </Flex>
        <Heading fontSize={{ base: '34px', md: '48px' }} fontWeight="800" letterSpacing="-0.03em" lineHeight={1.08}>
          {tt('Больше возможностей для')}{' '}
          <Box as="span" bgGradient={GRADIENT} bgClip="text">
            {tt('активных серверов')}
          </Box>
        </Heading>
        <Text fontSize={{ base: '16px', md: '18px' }} color="TextSecondary" mt={5} maxW="620px" mx="auto" lineHeight={1.6}>
          {tt('Премиум расширяет то, что уже работает: выше лимиты, своё оформление, приоритет и продвинутые инструменты.')}
        </Text>
        <Text fontSize="14px" color="TextSecondary" mt={4} maxW="560px" mx="auto">
          {tt('Все текущие функции остаются бесплатными — Премиум добавляет мощности, а не забирает их.')}
        </Text>
      </Container>

      {/* Pricing */}
      <Container maxW="4xl" px={{ base: 5, md: 8 }} py={{ base: 6, md: 10 }}>
        <SimpleGrid columns={{ base: 1, md: 2 }} gap={5} alignItems="stretch">
          {/* Free */}
          <Flex
            direction="column"
            bg="CardBackground"
            border="1px solid"
            borderColor="CardBorder"
            rounded="20px"
            p={{ base: 6, md: 8 }}
          >
            <Text fontSize="14px" fontWeight="700" color="TextSecondary" letterSpacing="0.04em">
              {tt('Бесплатно')}
            </Text>
            <Flex align="baseline" gap={2} mt={2}>
              <Text fontSize="40px" fontWeight="800" letterSpacing="-0.02em">
                0
              </Text>
              <Text fontSize="15px" color="TextSecondary">
                {tt('навсегда')}
              </Text>
            </Flex>
            <Flex direction="column" gap={2.5} mt={6} flex="1">
              <CheckItem>{tt('Все основные функции')}</CheckItem>
              <CheckItem>{tt('Модерация, тикеты, уровни, аналитика')}</CheckItem>
              <CheckItem>{tt('Русский и English')}</CheckItem>
              <CheckItem>{tt('Без ограничений по времени')}</CheckItem>
            </Flex>
            <Button
              as="a"
              href={config.inviteUrl}
              target="_blank"
              rel="noreferrer"
              mt={7}
              variant="outline"
              borderColor="CardBorder"
              leftIcon={<Icon as={FaDiscord} boxSize="18px" />}
            >
              {tt('Добавить на сервер')}
            </Button>
          </Flex>

          {/* Premium */}
          <Flex
            direction="column"
            position="relative"
            bg="CardBackground"
            border="2px solid"
            borderColor="brand.400"
            rounded="20px"
            p={{ base: 6, md: 8 }}
            boxShadow="0 30px 60px -30px rgba(110,86,245,.55)"
          >
            <Flex
              position="absolute"
              top={0}
              right={6}
              transform="translateY(-50%)"
              align="center"
              gap={1.5}
              px={3}
              py={1}
              rounded="full"
              bgGradient={GRADIENT}
              color="white"
              fontSize="11px"
              fontWeight="700"
              letterSpacing="0.02em"
              boxShadow="0 8px 18px -6px rgba(110,86,245,.6)"
            >
              <Icon as={MdWorkspacePremium} boxSize="13px" />
              {tt('Самое популярное')}
            </Flex>
            <Flex align="center" gap={2}>
              <Text fontSize="14px" fontWeight="700" color="brand.200" letterSpacing="0.04em">
                {tt('Премиум')}
              </Text>
              <Badge colorScheme="purple" rounded="full" px={2} textTransform="none">
                {tt('Скоро')}
              </Badge>
            </Flex>
            <Flex align="baseline" gap={2} mt={2}>
              <Text fontSize="40px" fontWeight="800" letterSpacing="-0.02em">
                {PRICE}
              </Text>
              <Text fontSize="15px" color="TextSecondary">
                {tt('/мес')}
              </Text>
            </Flex>
            <Text fontSize="13px" fontWeight="700" color="TextSecondary" mt={6} mb={0.5}>
              {tt('Всё из «Бесплатно», плюс:')}
            </Text>
            <Flex direction="column" gap={2.5} mt={2} flex="1">
              <CheckItem>{tt('Выше лимиты на всё')}</CheckItem>
              <CheckItem>{tt('Своё оформление и бренд')}</CheckItem>
              <CheckItem>{tt('Приоритет и ранний доступ')}</CheckItem>
              <CheckItem>{tt('Продвинутая аналитика и ИИ')}</CheckItem>
            </Flex>
            <Button mt={7} isDisabled color="white" bgGradient={GRADIENT} _disabled={{ opacity: 0.7, cursor: 'not-allowed' }} leftIcon={<Icon as={MdWorkspacePremium} boxSize="18px" />}>
              {tt('Скоро')}
            </Button>
          </Flex>
        </SimpleGrid>
      </Container>

      {/* Perks */}
      <Container maxW="6xl" px={{ base: 5, md: 8 }} py={{ base: 10, md: 14 }}>
        <Box textAlign="center" mb={10}>
          <Text fontSize="12px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
            {tt('ЧТО ВХОДИТ В ПРЕМИУМ')}
          </Text>
        </Box>
        <SimpleGrid columns={{ base: 1, md: 2 }} gap={5}>
          {perks.map((p) => (
            <PerkCard key={p.title} {...p} />
          ))}
        </SimpleGrid>
      </Container>

      {/* FAQ */}
      <Container maxW="3xl" px={{ base: 5, md: 8 }} py={{ base: 6, md: 10 }}>
        <Box textAlign="center" mb={8}>
          <Text fontSize="12px" fontWeight="700" letterSpacing="0.12em" color="brand.200">
            {tt('ВОПРОСЫ')}
          </Text>
        </Box>
        <Flex direction="column" gap={3}>
          {faq.map(([q, a]) => (
            <Box key={q} bg="CardBackground" border="1px solid" borderColor="CardBorder" rounded="14px" p={5}>
              <Text fontWeight="700" fontSize="15px" mb={1.5}>
                {q}
              </Text>
              <Text fontSize="14px" color="TextSecondary" lineHeight={1.6}>
                {a}
              </Text>
            </Box>
          ))}
        </Flex>
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
            {tt('Пока — начните бесплатно')}
          </Heading>
          <Text color="whiteAlpha.900" fontSize={{ base: '15px', md: '17px' }} mt={3} maxW="560px" mx="auto">
            {tt('Добавьте бота и настройте всё уже сегодня. Премиум подключится позже.')}
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

      <MarketingFooter />
    </Box>
  );
}
