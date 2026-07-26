import { Badge, Box, Flex, Icon, SimpleGrid, Text } from '@chakra-ui/react';
import { MdTune, MdCheck } from 'react-icons/md';
import { useFormText } from '@/config/translations/form-text';

// §5 progressive-disclosure pilot (Beta): a one-click preset selector for a
// feature form. Each preset is just a bundle of field values the caller applies
// via setValue — no backend concept — so a "Resident" gets sensible settings
// without tuning every field, while the detailed controls stay below for anyone
// who wants them. Shared across forms (AutoMod, Anti-Raid, …).
export type Preset<K extends string> = { key: K; name: string; desc: string };

export function PresetPicker<K extends string>({
  presets,
  active,
  onPick,
}: {
  presets: ReadonlyArray<Preset<K>>;
  active: K | null;
  onPick: (key: K) => void;
}) {
  const ft = useFormText();
  return (
    <Box bg="brandAlpha.100" border="1px solid" borderColor="brand.400" rounded="16px" p={4}>
      <Flex align="center" gap={2} mb={1}>
        <Icon as={MdTune} color="brand.200" />
        <Text fontWeight="700">{ft('Quick setup')}</Text>
        <Badge colorScheme="purple" rounded="full" px={2}>
          {ft('Beta')}
        </Badge>
      </Flex>
      <Text fontSize="sm" color="TextSecondary" mb={3}>
        {ft('One click applies sensible settings — tweak anything after.')}
      </Text>
      <SimpleGrid columns={{ base: 1, md: 3 }} gap={2}>
        {presets.map((p) => (
          <Box
            as="button"
            key={p.key}
            type="button"
            onClick={() => onPick(p.key)}
            textAlign="left"
            bg="CardBackground"
            border="1px solid"
            borderColor={active === p.key ? 'brand.400' : 'CardBorder'}
            rounded="12px"
            p={3}
            transition="border-color .15s ease"
            _hover={{ borderColor: 'brand.400' }}
          >
            <Flex align="center" gap={1.5}>
              <Text fontWeight="700" fontSize="sm">
                {p.name}
              </Text>
              {active === p.key && <Icon as={MdCheck} color="brand.200" boxSize="15px" />}
            </Flex>
            <Text fontSize="12px" color="TextSecondary" mt={1} lineHeight={1.4}>
              {p.desc}
            </Text>
          </Box>
        ))}
      </SimpleGrid>
      {active && (
        <Text fontSize="sm" color="brand.200" fontWeight="600" mt={3}>
          {ft('Applied — review below and Save.')}
        </Text>
      )}
    </Box>
  );
}
