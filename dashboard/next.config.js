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
      // The guild landing is the Iris Overview (settings); the old index page
      // (Getting Started banner + legacy feature grid) is removed. ':guild'
      // matches a single segment, so /guilds/:guild/settings etc. are untouched.
      { source: '/guilds/:guild', destination: '/guilds/:guild/settings', permanent: false },
    ];
  },
  // Baseline security headers, applied to every route. Deliberately excludes a
  // full Content-Security-Policy — Chakra/emotion inline styles, Next's own
  // scripts and the charting/emoji libraries need a carefully tuned allow-list,
  // which is a separate, browser-tested change.
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          // Disallow framing the dashboard (clickjacking).
          { key: 'X-Frame-Options', value: 'DENY' },
          // Don't let browsers MIME-sniff responses into a different type.
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          // Send the origin (not the full path/query) on cross-origin navigations.
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          // The dashboard uses none of these device features — deny them.
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), browsing-topics=()',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;