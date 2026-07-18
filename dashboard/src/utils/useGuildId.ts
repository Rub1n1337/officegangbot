import { useRouter } from 'next/router';

/**
 * The current guild id, available from the very first client render.
 *
 * `router.query` is empty until Next hydrates the route params, so components
 * that build hrefs from `router.query.guild` briefly rendered links like
 * /guilds/undefined/moderation — an early click navigated there for real, and
 * the escape-hatch redirect then dumped the user on /user/home, losing their
 * place. The path in `router.asPath` is correct immediately, so parse the id
 * from it as the fallback; while neither source has a valid id (build-time
 * render), callers should render nav as non-clickable rather than guess.
 */
export function guildIdFromAsPath(asPath: string): string | undefined {
  const m = asPath.match(/^(?:\/[a-z]{2}(?:-[A-Za-z]{2})?)?\/guilds\/(\d+)(?:[/?#]|$)/);
  return m?.[1];
}

export function useGuildId(): string | undefined {
  const router = useRouter();
  const q = router.query.guild;
  if (typeof q === 'string' && /^\d+$/.test(q)) return q;
  return guildIdFromAsPath(router.asPath);
}
