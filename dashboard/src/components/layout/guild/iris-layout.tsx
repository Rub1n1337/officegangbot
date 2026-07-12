import { Box, Drawer, DrawerBody, DrawerContent, DrawerOverlay, Flex, usePrefersReducedMotion } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { ReactNode } from 'react';
import { useRouter } from 'next/router';
import { usePageStore } from '@/stores';
import { IrisSidebar } from './iris-sidebar';
import { IrisHeader } from './iris-header';

// Full-height Iris shell: a fixed 272px sidebar + a main column with a sticky
// header and its own scroll area. Below xl the sidebar collapses into a drawer
// opened from the header's menu button. Scoped to guild pages so the /user
// pages keep the original layout.
// Screen-enter motion from the mockup: fade + 6px rise, 0.25s ease. Re-runs on
// every route change via the key below.
const screenIn = keyframes`from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}`;

export default function IrisGuildLayout({ children }: { children: ReactNode }) {
  const [isOpen, setOpen] = usePageStore((s) => [s.sidebarIsOpen, s.setSidebarIsOpen]);
  const route = useRouter().asPath;
  const reduceMotion = usePrefersReducedMotion();

  return (
    <Box
      h="100vh"
      display="grid"
      gridTemplateColumns={{ base: '1fr', xl: '272px 1fr' }}
      overflow="hidden"
      bg="MainBackground"
    >
      {/* Desktop sidebar */}
      <Box display={{ base: 'none', xl: 'block' }} h="100%" overflow="hidden">
        <IrisSidebar />
      </Box>

      {/* Mobile sidebar drawer */}
      <Drawer isOpen={isOpen} placement="left" onClose={() => setOpen(false)}>
        <DrawerOverlay />
        <DrawerContent maxW="272px" w="272px">
          <DrawerBody p={0}>
            <IrisSidebar onNavigate={() => setOpen(false)} />
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Main */}
      <Flex direction="column" overflow="hidden" h="100%">
        <IrisHeader onOpenSidebar={() => setOpen(true)} />
        <Box flex="1" overflowY="auto">
          <Box
            key={route}
            maxW="1240px"
            mx="auto"
            px={{ base: '20px', md: '28px' }}
            py={{ base: '22px', md: '26px' }}
            animation={reduceMotion ? undefined : `${screenIn} .25s ease`}
          >
            {children}
          </Box>
        </Box>
      </Flex>
    </Box>
  );
}
