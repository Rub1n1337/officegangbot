import { Box, Container, Heading, Text } from '@chakra-ui/react';
import Head from 'next/head';
import { ReactNode } from 'react';

// Shared shell for the public legal pages (/terms, /privacy). Deliberately
// layout-free: these pages must be reachable without login (Discord app
// verification reviewers open them anonymously).
export function LegalPage({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: ReactNode;
}) {
  return (
    <>
      <Head>
        <title>{`${title} — OfficeGangBot`}</title>
        <meta name="robots" content="index,follow" />
      </Head>
      <Container maxW="3xl" py={12} px={6}>
        <Heading as="h1" size="lg" mb={1}>
          {title}
        </Heading>
        <Text fontSize="sm" color="TextSecondary" mb={8}>
          Last updated: {updated}
        </Text>
        <Box
          sx={{
            h2: { fontSize: 'xl', fontWeight: 700, mt: 8, mb: 3 },
            h3: { fontSize: 'md', fontWeight: 700, mt: 5, mb: 2 },
            p: { mb: 3, lineHeight: 1.7 },
            ul: { pl: 6, mb: 3 },
            li: { mb: 1.5, lineHeight: 1.6 },
            a: { color: 'Brand', textDecoration: 'underline' },
          }}
        >
          {children}
        </Box>
      </Container>
    </>
  );
}

export const LEGAL_CONTACT_EMAIL = 'rubn7228@gmail.com';
