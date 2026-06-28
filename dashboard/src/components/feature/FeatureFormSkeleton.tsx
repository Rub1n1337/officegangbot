import { Box, Flex, Skeleton } from '@chakra-ui/react';

/** Generic loading placeholder for a feature config page (header + form cards). */
export function FeatureFormSkeleton() {
  return (
    <Flex direction="column" gap={5} w="full">
      <Skeleton h="14px" w="180px" rounded="md" mx={{ '3sm': 5 }} />
      <Flex
        direction={{ base: 'column', md: 'row' }}
        mx={{ '3sm': 5 }}
        justify="space-between"
        gap={3}
      >
        <Box>
          <Skeleton h="28px" w="200px" mb={2} rounded="md" />
          <Skeleton h="14px" w="280px" rounded="md" />
        </Box>
        <Skeleton h="28px" w="64px" rounded="full" />
      </Flex>
      <Flex direction="column" gap={3}>
        {Array.from({ length: 3 }).map((_, i) => (
          <Box key={i} bg="CardBackground" rounded="2xl" p={4}>
            <Skeleton h="14px" w="40%" mb={3} rounded="md" />
            <Skeleton h="40px" rounded="lg" />
          </Box>
        ))}
      </Flex>
    </Flex>
  );
}
