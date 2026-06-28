import { useEffect, useRef, useState } from 'react';
import { RiErrorWarningFill as WarningIcon } from 'react-icons/ri';
import { Box, Flex, Heading, Spacer, Text } from '@chakra-ui/layout';
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  ButtonGroup,
  Button,
  Icon,
  Switch,
} from '@chakra-ui/react';
import { SlideFade } from '@chakra-ui/react';
import { FeatureConfig, UseFormRenderResult, CustomFeatures } from '@/config/types';
import { IoSave, IoLockClosed, IoChevronForward, IoPower } from 'react-icons/io5';
import {
  useEnableFeatureMutation,
  useGuildInfoQuery,
  useGuildPreview,
  useUpdateFeatureMutation,
} from '@/api/hooks';
import { Params } from '@/pages/guilds/[guild]/features/[feature]';
import { feature as view } from '@/config/translations/feature';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useUnsavedChanges } from '@/utils/useUnsavedChanges';

export function UpdateFeaturePanel({
  feature,
  config,
}: {
  feature: CustomFeatures[keyof CustomFeatures];
  config: FeatureConfig<keyof CustomFeatures>;
}) {
  const t = view.useTranslations();
  const { guild, feature: featureId } = useRouter().query as Params;
  const mutation = useUpdateFeatureMutation();
  const enableMutation = useEnableFeatureMutation();
  const guildQuery = useGuildInfoQuery(guild);
  const { guild: guildPreview } = useGuildPreview(guild);
  const enabled = guildQuery.data?.enabledFeatures?.includes(featureId) ?? false;

  const result = config.useRender(feature, (data) => {
    return mutation.mutateAsync({
      guild,
      feature: featureId,
      options: data,
    });
  });

  const onToggle = (next: boolean) => {
    enableMutation.mutate({ enabled: next, guild, feature: featureId });
  };

  // Disabling a feature stops it working server-wide, so confirm first.
  // Enabling is harmless and stays instant.
  const [confirmingDisable, setConfirmingDisable] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const onSwitch = (next: boolean) => {
    if (!next && enabled) setConfirmingDisable(true);
    else onToggle(next);
  };

  // Warn before navigating away with unsaved edits.
  useUnsavedChanges(enabled && Boolean(result.canSave));

  // Ctrl/Cmd+S saves the form when there are unsaved changes.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (enabled && result.canSave) result.onSubmit();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, result]);

  return (
    <Flex as="form" direction="column" gap={5} w="full" h="full">
      <Breadcrumb
        mx={{ '3sm': 5 }}
        fontSize="sm"
        color="TextSecondary"
        separator={<Icon as={IoChevronForward} fontSize="0.7em" />}
      >
        <BreadcrumbItem>
          <BreadcrumbLink as={Link} href={`/guilds/${guild}`}>
            {guildPreview?.name ?? 'Server'}
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbItem isCurrentPage>
          <BreadcrumbLink fontWeight="600" color="TextPrimary">
            {config.name}
          </BreadcrumbLink>
        </BreadcrumbItem>
      </Breadcrumb>

      <Flex direction={{ base: 'column', md: 'row' }} mx={{ '3sm': 5 }} justify="space-between" gap={3}>
        <Box>
          <Heading fontSize="2xl" fontWeight="600">
            {config.name}
          </Heading>
          <Text color="TextSecondary">{config.description}</Text>
        </Box>
        <Flex align="center" gap={3} mt={{ base: 2, md: 0 }}>
          <Text fontWeight="600" color={enabled ? 'green.400' : 'TextSecondary'}>
            {enabled ? 'Enabled' : 'Disabled'}
          </Text>
          <Switch
            variant="main"
            size="lg"
            aria-label={`${enabled ? 'Disable' : 'Enable'} ${config.name}`}
            isChecked={enabled}
            isDisabled={enableMutation.isLoading || guildQuery.isLoading}
            onChange={(e) => onSwitch(e.target.checked)}
          />
        </Flex>
      </Flex>

      <Box position="relative">
        <Box
          opacity={enabled ? 1 : 0.4}
          pointerEvents={enabled ? 'auto' : 'none'}
          filter={enabled ? 'none' : 'grayscale(1)'}
          transition="opacity 0.2s ease, filter 0.2s ease"
          aria-disabled={!enabled}
        >
          {result.component}
        </Box>

        {/* When the feature is off the form is greyed and non-interactive, which
            on its own looks broken. This overlay explains why and offers the
            one action that unblocks it. */}
        {!enabled && (
          <Flex
            position="absolute"
            inset={0}
            align="flex-start"
            justify="center"
            pt={{ base: 8, md: 16 }}
            pointerEvents="none"
          >
            <Flex
              pointerEvents="auto"
              direction="column"
              align="center"
              textAlign="center"
              gap={3}
              maxW="sm"
              mx={4}
              px={8}
              py={6}
              bg="CardBackground"
              rounded="2xl"
              shadow="lg"
              borderWidth="1px"
              borderColor="whiteAlpha.200"
            >
              <Icon as={IoLockClosed} boxSize={7} color="TextSecondary" />
              <Text fontWeight="600" fontSize="lg">
                This feature is off
              </Text>
              <Text color="TextSecondary" fontSize="sm">
                Enable it to configure and save its settings.
              </Text>
              <Button
                variant="action"
                rounded="full"
                leftIcon={<IoPower />}
                isLoading={enableMutation.isLoading}
                onClick={() => onToggle(true)}
              >
                {t.bn.enable}
              </Button>
            </Flex>
          </Flex>
        )}
      </Box>

      {enabled && <Savebar isLoading={mutation.isLoading} result={result} />}

      <AlertDialog
        isOpen={confirmingDisable}
        leastDestructiveRef={cancelRef}
        onClose={() => setConfirmingDisable(false)}
        isCentered
      >
        <AlertDialogOverlay>
          <AlertDialogContent bg="CardBackground" mx={4}>
            <AlertDialogHeader>Disable {config.name}?</AlertDialogHeader>
            <AlertDialogBody>
              This stops {config.name} working across the server. Your settings are kept, so you can
              re-enable it any time.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} variant="ghost" onClick={() => setConfirmingDisable(false)}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                ml={3}
                isLoading={enableMutation.isLoading}
                onClick={() => {
                  onToggle(false);
                  setConfirmingDisable(false);
                }}
              >
                Disable
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Flex>
  );
}

function Savebar({
  result: { canSave, onSubmit, reset },
  isLoading,
}: {
  result: UseFormRenderResult;
  isLoading: boolean;
}) {
  const t = view.useTranslations();
  const breakpoint = '3sm';

  return (
    <Flex
      as={SlideFade}
      in={canSave}
      bg="CardBackground"
      rounded="3xl"
      zIndex="sticky"
      pos="sticky"
      bottom={{ base: 2, [breakpoint]: '10px' }}
      w="full"
      p={{ base: 1, [breakpoint]: '15px' }}
      shadow="normal"
      alignItems="center"
      flexDirection={{ base: 'column', [breakpoint]: 'row' }}
      gap={{ base: 1, [breakpoint]: 2 }}
      mt="auto"
    >
      <Icon
        display={{ base: 'none', [breakpoint]: 'block' }}
        as={WarningIcon}
        _light={{ color: 'orange.400' }}
        _dark={{ color: 'orange.300' }}
        w="30px"
        h="30px"
      />
      <Text fontSize={{ base: 'md', [breakpoint]: 'lg' }} fontWeight="600">
        {t.unsaved}
      </Text>
      <Spacer />
      <ButtonGroup isDisabled={isLoading} size={{ base: 'sm', [breakpoint]: 'md' }}>
        <Button
          type="submit"
          variant="action"
          rounded="full"
          leftIcon={<IoSave />}
          isLoading={isLoading}
          onClick={onSubmit}
        >
          {t.bn.save}
        </Button>
        <Button rounded="full" onClick={reset}>
          {t.bn.discard}
        </Button>
      </ButtonGroup>
    </Flex>
  );
}
