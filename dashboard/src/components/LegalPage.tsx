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

// Contact shown on the legal pages. Set NEXT_PUBLIC_CONTACT_EMAIL in the
// dashboard's environment (e.g. on Vercel) — no address is committed to the
// repository. Without it, a neutral Discord-based contact line is shown.
const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL;

export function ContactLink() {
  if (CONTACT_EMAIL) {
    return <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>;
  }
  return <>the developer via the OfficeGangBot support server on Discord</>;
}
