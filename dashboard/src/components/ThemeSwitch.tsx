import { Button, Icon, useColorMode } from '@chakra-ui/react';
import { IoMdMoon, IoMdSunny } from 'react-icons/io';
import { flushSync } from 'react-dom';
import type { MouseEvent } from 'react';

type DocWithVT = Document & {
  startViewTransition?: (cb: () => void) => unknown;
};

export function ThemeSwitch({ secondary }: { secondary?: boolean }) {
  const { colorMode, toggleColorMode } = useColorMode();

  const onToggle = (e: MouseEvent<HTMLButtonElement>) => {
    const doc = document as DocWithVT;
    const reduce =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!doc.startViewTransition || reduce) {
      toggleColorMode();
      return;
    }

    // Reveal originates from the toggle itself (top-right of the header).
    document.documentElement.style.setProperty('--vt-x', `${e.clientX}px`);
    document.documentElement.style.setProperty('--vt-y', `${e.clientY}px`);
    // flushSync so the new colour scheme is in the DOM before the API snapshots it.
    doc.startViewTransition(() => {
      flushSync(() => toggleColorMode());
    });
  };

  return (
    <Button
      variant="no-hover"
      bg="transparent"
      p="0px"
      minW="unset"
      minH="unset"
      h="18px"
      w="max-content"
      onClick={onToggle}
      aria-label="Toggle color mode"
    >
      <Icon
        me="10px"
        h="18px"
        w="18px"
        color={secondary ? 'gray.400' : 'TextPrimary'}
        _dark={{
          color: 'TextPrimary',
        }}
        as={colorMode === 'light' ? IoMdMoon : IoMdSunny}
      />
    </Button>
  );
}
