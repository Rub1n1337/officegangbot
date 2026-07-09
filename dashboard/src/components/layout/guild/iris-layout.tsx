import { Box, Drawer, DrawerBody, DrawerContent, DrawerOverlay, Flex } from '@chakra-ui/react';
import { ReactNode } from 'react';
import { usePageStore } from '@/stores';
import { IrisSidebar } from './iris-sidebar';
import { IrisHeader } from './iris-header';

// Full-height Iris shell: a fixed 272px sidebar + a main column with a sticky
// header and its own scroll area. Below xl the sidebar collapses into a drawer
// opened from the header's menu button. Scoped to guild pages so the /user
// pages keep the original layout.
export default function IrisGuildLayout({ children }: { children: ReactNode }) {
  const [isOpen, setOpen] = usePageStore((s) => [s.sidebarIsOpen, s.setSidebarIsOpen]);

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
          <Box maxW="1240px" mx="auto" px={{ base: '20px', md: '28px' }} py={{ base: '22px', md: '26px' }}>
            {children}
          </Box>
        </Box>
      </Flex>
    </Box>
  );
}
