import { Box, Flex, Text } from '@chakra-ui/react';
import { Fragment, ReactNode } from 'react';
import { feature as view } from '@/config/translations/feature';
import { useFormText } from '@/config/translations/form-text';

/**
 * A lightweight, dependency-free approximation of how the rules message will
 * look once the bot posts it to Discord. It is not a full markdown engine — it
 * renders the two things the default rules text actually uses: **bold** spans
 * and `> ` block quotes. Everything else is shown verbatim with line breaks
 * preserved, so admins can sanity-check length and structure before saving.
 */

function renderInline(line: string): ReactNode {
  // Split on **bold** markers; odd segments are the bolded text.
  const parts = line.split('**');
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <Text as="span" key={i} fontWeight="700">
        {part}
      </Text>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    )
  );
}

function RenderedRules({ message }: { message: string }) {
  const lines = message.split('\n');
  return (
    <>
      {lines.map((raw, idx) => {
        const isQuote = raw.startsWith('> ');
        const content = isQuote ? raw.slice(2) : raw;
        if (isQuote) {
          return (
            <Flex key={idx} gap={2}>
              <Box
                w="3px"
                bg="blackAlpha.300"
                _dark={{ bg: 'whiteAlpha.400' }}
                rounded="full"
                flexShrink={0}
              />
              <Text fontSize="sm" color="TextPrimary">
                {renderInline(content)}
              </Text>
            </Flex>
          );
        }
        return (
          <Text key={idx} fontSize="sm" color="TextPrimary" minH={raw === '' ? '0.5em' : undefined}>
            {renderInline(content)}
          </Text>
        );
      })}
    </>
  );
}

export function RulesPreview({
  message,
  reactionEnabled,
  reactionEmoji,
}: {
  message: string;
  reactionEnabled?: boolean;
  reactionEmoji?: string;
}) {
  const t = view.useTranslations();
  const ft = useFormText();
  const empty = !message.trim();
  return (
    <Box>
      <Text fontSize="sm" color="TextSecondary" mb={2}>
        {t.preview}
      </Text>
      {/* Discord-embed-style card: colored accent bar + body. */}
      <Flex bg="CardBackground" rounded="md" overflow="hidden" border="1px solid" borderColor="CardBorder">
        <Box w="4px" bg="Brand" flexShrink={0} />
        <Box p={4} flex="1" minW={0}>
          <Text fontWeight="700" mb={2}>
            📜 {ft('Server Rules')}
          </Text>
          {empty ? (
            <Text fontSize="sm" color="TextSecondary" fontStyle="italic">
              {ft('Your rules message will appear here as you type…')}
            </Text>
          ) : (
            <Flex direction="column" gap={1}>
              <RenderedRules message={message} />
            </Flex>
          )}
          {reactionEnabled && reactionEmoji?.trim() && (
            <Flex mt={3} align="center" gap={2}>
              <Flex
                align="center"
                gap={1}
                bg="blackAlpha.100"
                _dark={{ bg: 'whiteAlpha.200' }}
                rounded="md"
                px={2}
                py={0.5}
                fontSize="sm"
              >
                <Text as="span">{reactionEmoji}</Text>
                <Text as="span" color="TextSecondary">
                  1
                </Text>
              </Flex>
              <Text fontSize="xs" color="TextSecondary">
                Reacting grants the selected role
              </Text>
            </Flex>
          )}
        </Box>
      </Flex>
    </Box>
  );
}
