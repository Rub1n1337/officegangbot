import { SimpleGrid, Text } from '@chakra-ui/react';
import type { ModerationFeature } from '@/config/types/custom-types';
import type { UseFormRender } from '@/config/types/types';

export const useModerationFeature: UseFormRender<ModerationFeature> = (_data: ModerationFeature, _onSubmit: (data: string) => Promise<any>) => {
  return {
    component: (
      <SimpleGrid columns={1} gap={3}>
        <Text color="TextSecondary">
          Moderation settings are currently managed via Discord commands. 
          Role-based permissions can be viewed using <b>/settings</b>.
          Dashboard configuration for moderation is coming soon.
        </Text>
      </SimpleGrid>
    ),
    onSubmit: async () => {},
    canSave: false,
    reset: () => {},
  };
};
