/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Locale routing for the dashboard UI language. Default locale (en) keeps clean
  // URLs; other locales get a path prefix (/ru, /cn). API routes are not prefixed.
  // localeDetection off so visitors aren't auto-redirected by Accept-Language.
  i18n: {
    locales: ['en', 'cn', 'ru'],
    defaultLocale: 'en',
    localeDetection: false,
  },
  async redirects() {
    return [
      { source: '/auth', destination: '/auth/signin', permanent: false },
      { source: '/user', destination: '/user/home', permanent: false },
      { source: '/', destination: '/user/home', permanent: false },
    ];
  },
};

module.exports = nextConfig;