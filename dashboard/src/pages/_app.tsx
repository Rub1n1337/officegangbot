import { ChakraProvider } from '@chakra-ui/react';
import { AppProps } from 'next/app';
import { theme } from '@/theme/config';
import { QueryClientProvider } from '@tanstack/react-query';
import { client } from '@/api/hooks';
import { NextPage } from 'next';
import { ReactNode, useEffect, useState } from 'react';  // Added imports
import Head from 'next/head';

import '@/styles/global.css';
import 'react-calendar/dist/Calendar.css';
import '@/styles/date-picker.css';

export type NextPageWithLayout = NextPage & {
  getLayout?: (children: ReactNode) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};

export default function App({ Component, pageProps }: AppPropsWithLayout) {
  const [mounted, setMounted] = useState(false);
  const getLayout = Component.getLayout ?? ((c) => c);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Don't render until mounted on client side
  if (!mounted) {
    return (
        <ChakraProvider theme={theme}>
            <QueryClientProvider client={client}>
                <Head><title>OfficeGangBot</title></Head>
            </QueryClientProvider>
        </ChakraProvider>
    );
}

  return (
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={client}>
        <Head>
          <title>OfficeGangBot</title>
        </Head>
        {getLayout(<Component {...pageProps} />)}
      </QueryClientProvider>
    </ChakraProvider>
  );
}
