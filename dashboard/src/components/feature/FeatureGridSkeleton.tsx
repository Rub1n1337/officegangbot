import { Box, Card, CardBody, CardFooter, Flex, SimpleGrid, Skeleton } from '@chakra-ui/react';
import { featureCategories } from '@/config/features';

// Mirrors a FeatureItem card so the loading state has the same shape as the
// loaded grid — no spinner-then-pop layout shift on the guild overview.
function CardSkeleton() {
  return (
    <Card variant="primary">
      <CardBody as={Flex} direction="row" gap={3}>
        <Skeleton rounded="xl" w="50px" h="50px" flexShrink={0} />
        <Box flex={1}>
          <Skeleton h="18px" w="55%" rounded="md" />
          <Skeleton h="12px" w="90%" mt={2} rounded="md" />
          <Skeleton h="12px" w="70%" mt={1.5} rounded="md" />
        </Box>
      </CardBody>
      <CardFooter mt={3}>
        <Skeleton h="36px" w="150px" rounded="2xl" />
      </CardFooter>
    </Card>
  );
}

export function FeatureGridSkeleton() {
  return (
    <Flex direction="column" gap={6} mt={3} aria-busy="true">
      {featureCategories.map((cat) => (
        <Flex key={cat.id} direction="column" gap={3}>
          <Skeleton h="12px" w="120px" rounded="md" />
          <SimpleGrid columns={{ base: 1, md: 2, '2xl': 3 }} gap={3}>
            {Array.from({ length: 4 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </SimpleGrid>
        </Flex>
      ))}
    </Flex>
  );
}
