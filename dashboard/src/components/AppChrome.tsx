import {
  Badge,
  Box,
  Flex,
  Input,
  Kbd,
  Modal,
  ModalContent,
  ModalOverlay,
  Text,
  useDisclosure,
} from '@chakra-ui/react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { useGuilds } from '@/api/hooks';
import { getFeatures } from '@/utils/common';
import { config } from '@/config/common';
import { useText } from '@/config/translations/ui-text';
import { searchSettings } from '@/config/settings-index';

/** Custom event other components can dispatch to open the command palette. */
export const OPEN_COMMAND_PALETTE = 'open-command-palette';

type Command = { id: string; label: string; hint: string; href: string };

/**
 * A thin top progress bar driven by Next route-change events — gives instant
 * feedback that a navigation is happening (Vercel cold starts can lag a moment).
 */
function RouteProgress() {
  const router = useRouter();
  const [state, setState] = useState<'idle' | 'loading' | 'done'>('idle');

  useEffect(() => {
    const start = () => setState('loading');
    const done = () => setState('done');
    router.events.on('routeChangeStart', start);
    router.events.on('routeChangeComplete', done);
    router.events.on('routeChangeError', done);
    return () => {
      router.events.off('routeChangeStart', start);
      router.events.off('routeChangeComplete', done);
      router.events.off('routeChangeError', done);
    };
  }, [router]);

  useEffect(() => {
    if (state !== 'done') return;
    const t = setTimeout(() => setState('idle'), 400);
    return () => clearTimeout(t);
  }, [state]);

  return (
    <Box position="fixed" top={0} left={0} right={0} h="3px" zIndex="modal" pointerEvents="none">
      <Box
        h="full"
        bg="Brand"
        borderRightRadius="full"
        width={state === 'loading' ? '85%' : state === 'done' ? '100%' : '0%'}
        opacity={state === 'idle' ? 0 : 1}
        transition={
          state === 'loading'
            ? 'width 8s cubic-bezier(0.1, 0.7, 0.1, 1)'
            : 'width 0.2s ease, opacity 0.4s ease 0.1s'
        }
      />
    </Box>
  );
}

/**
 * ⌘K / Ctrl+K command palette: jump to the current server's Overview or any
 * feature, switch servers, or go home. Opens on the shortcut or on the
 * `OPEN_COMMAND_PALETTE` window event (e.g. a sidebar search button).
 */
function CommandPalette() {
  const router = useRouter();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const guilds = useGuilds();
  const inputRef = useRef<HTMLInputElement>(null);
  const guildId = (router.query.guild as string) || undefined;
  const [q, setQ] = useState('');
  const [idx, setIdx] = useState(0);
  const tt = useText();

  const commands = useMemo<Command[]>(() => {
    const list: Command[] = [];
    if (guildId) {
      list.push({ id: 'overview', label: tt('Обзор'), hint: tt('Статистика'), href: `/guilds/${guildId}/settings` });
      list.push({ id: 'moderation', label: tt('Модерация'), hint: tt('Панель'), href: `/guilds/${guildId}/moderation` });
      list.push({ id: 'analytics', label: tt('Аналитика'), hint: tt('Тренды'), href: `/guilds/${guildId}/analytics` });
      list.push({ id: 'members', label: tt('Участники'), hint: tt('Поиск'), href: `/guilds/${guildId}/members` });
      for (const f of getFeatures()) {
        list.push({
          id: `f-${f.id}`,
          label: String(f.name),
          hint: tt('Функция'),
          href: `/guilds/${guildId}/features/${f.id}`,
        });
      }
    }
    list.push({ id: 'home', label: tt('Сменить сервер'), hint: tt('Главная'), href: '/user/home' });
    for (const g of guilds.data ?? []) {
      if (config.guild.filter(g) && g.id !== guildId) {
        list.push({ id: `g-${g.id}`, label: g.name, hint: tt('Сервер'), href: `/guilds/${g.id}` });
      }
    }
    return list;
  }, [guildId, guilds.data, tt]);

  const needle = q.trim().toLowerCase();
  // Individual settings only surface when the admin is typing — they'd clutter
  // the default list. Deduped so a settings hit doesn't repeat a feature link
  // already matched by name.
  const settingHits = useMemo<Command[]>(() => {
    if (!guildId || !needle) return [];
    return searchSettings(needle).map((s, i) => ({
      id: `s-${s.feature}-${i}`,
      label: s.label,
      hint: tt('Настройка'),
      href: `/guilds/${guildId}/features/${s.feature}`,
    }));
  }, [guildId, needle, tt]);
  // Recently visited pages (persisted per browser) lead the default list, so
  // reopening the palette jumps straight back to where the admin just was.
  const [recent, setRecent] = useState<string[]>([]);
  useEffect(() => {
    try {
      setRecent(JSON.parse(localStorage.getItem('palette-recent') ?? '[]'));
    } catch {
      setRecent([]);
    }
  }, [isOpen]);
  useEffect(() => {
    const path = router.asPath;
    if (!path.startsWith('/guilds/')) return;
    try {
      const prev: string[] = JSON.parse(localStorage.getItem('palette-recent') ?? '[]');
      const next = [path, ...prev.filter((p) => p !== path)].slice(0, 3);
      localStorage.setItem('palette-recent', JSON.stringify(next));
    } catch {
      /* private mode — recents just won't persist */
    }
  }, [router.asPath]);

  const recentCommands = useMemo<Command[]>(
    () =>
      recent
        .filter((p) => p !== router.asPath)
        .map((p) => {
          const match = commands.find((c) => c.href === p);
          return match ? { ...match, id: `r-${p}`, hint: tt('НЕДАВНИЕ') } : null;
        })
        .filter((c): c is Command => c != null),
    [recent, commands, router.asPath, tt]
  );

  const filtered = needle
    ? [...commands.filter((c) => c.label.toLowerCase().includes(needle)), ...settingHits]
    : [...recentCommands, ...commands.filter((c) => !recentCommands.some((r) => r.href === c.href))];

  // Open on ⌘K / Ctrl+K, or on the custom event.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpen();
      }
    };
    const onEvent = () => onOpen();
    window.addEventListener('keydown', onKey);
    window.addEventListener(OPEN_COMMAND_PALETTE, onEvent);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener(OPEN_COMMAND_PALETTE, onEvent);
    };
  }, [onOpen]);

  useEffect(() => {
    if (isOpen) {
      setQ('');
      setIdx(0);
    }
  }, [isOpen]);
  useEffect(() => setIdx(0), [q]);

  const go = (href: string) => {
    onClose();
    router.push(href);
  };

  const onInputKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setIdx((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const c = filtered[idx];
      if (c) go(c.href);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered initialFocusRef={inputRef}>
      <ModalOverlay />
      <ModalContent bg="CardBackground" rounded="2xl" overflow="hidden" mx={4}>
        <Box p={3} borderBottomWidth="1px" borderColor="whiteAlpha.200">
          <Input
            ref={inputRef}
            variant="unstyled"
            px={2}
            placeholder={tt('Перейти к серверу или функции…')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onInputKey}
          />
        </Box>
        <Box maxH="340px" overflowY="auto" py={2}>
          {filtered.length === 0 ? (
            <Text px={5} py={3} color="TextSecondary" fontSize="sm">
              {tt('Ничего не найдено.')}
            </Text>
          ) : (
            filtered.map((c, i) => (
              <Flex
                key={c.id}
                mx={2}
                px={3}
                py={2}
                rounded="lg"
                cursor="pointer"
                align="center"
                justify="space-between"
                gap={3}
                bg={i === idx ? 'blackAlpha.200' : 'transparent'}
                _dark={{ bg: i === idx ? 'whiteAlpha.100' : 'transparent' }}
                onMouseEnter={() => setIdx(i)}
                onClick={() => go(c.href)}
              >
                <Text isTruncated>{c.label}</Text>
                <Badge flexShrink={0} rounded="md" colorScheme="gray" textTransform="none">
                  {c.hint}
                </Badge>
              </Flex>
            ))
          )}
        </Box>
        <Flex
          px={4}
          py={2}
          borderTopWidth="1px"
          borderColor="whiteAlpha.200"
          color="TextSecondary"
          fontSize="xs"
          gap={3}
        >
          <Flex gap={1} align="center">
            <Kbd>↑</Kbd>
            <Kbd>↓</Kbd>
            to navigate
          </Flex>
          <Flex gap={1} align="center">
            <Kbd>↵</Kbd>
            to open
          </Flex>
          <Flex gap={1} align="center">
            <Kbd>esc</Kbd>
            to close
          </Flex>
        </Flex>
      </ModalContent>
    </Modal>
  );
}

/** Global UI chrome mounted once in _app: route progress bar + command palette. */
export function AppChrome() {
  return (
    <>
      <RouteProgress />
      <CommandPalette />
    </>
  );
}
