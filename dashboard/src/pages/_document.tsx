// pages/_document.js

import { ColorModeScript } from '@chakra-ui/react';
import { Html, Head, Main, NextScript } from 'next/document';
import { theme } from '@/theme/config';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* Brand favicon (the sidebar's robot mark on the brand gradient).
            Without an icon link the browser auto-requests /favicon.ico and 404s. */}
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </Head>
      <body>
        <ColorModeScript initialColorMode={theme.config.initialColorMode} />
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
