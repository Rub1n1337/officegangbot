import { Flex, Icon } from '@chakra-ui/react';
import { IoMenuOutline } from 'react-icons/io5';
import { usePageStore } from '@/stores';
import { sidebarBreakpoint } from '@/theme/breakpoints';

export function SidebarTrigger() {
  const setOpen = usePageStore((s) => s.setSidebarIsOpen);

  return (
    <Flex display={{ base: 'flex', [sidebarBreakpoint]: 'none' }} alignItems="center">
      <Flex
        as="button"
        type="button"
        aria-label="Open menu"
        w="max-content"
        h="max-content"
        onClick={() => setOpen(true)}
        cursor="pointer"
      >
        <Icon
          as={IoMenuOutline}
          color="gray.400"
          _dark={{
            color: 'white',
          }}
          my="auto"
          w="20px"
          h="20px"
          me="10px"
        />
      </Flex>
    </Flex>
  );
}
