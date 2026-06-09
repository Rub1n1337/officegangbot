import { Flex, Button } from '@chakra-ui/react';

interface SavebarProps {
  isLoading?: boolean;
  result?: { canSave?: boolean };
}

export function Savebar({ isLoading, result }: SavebarProps) {
  return (
    <Flex justify="flex-end" mt={4} gap={2}>
      <Button
        colorScheme="brand"
        type="submit"
        isLoading={isLoading}
        isDisabled={result && !result.canSave}
      >
        Save
      </Button>
    </Flex>
  );
}
