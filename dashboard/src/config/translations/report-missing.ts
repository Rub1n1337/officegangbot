/**
 * Makes a missing translation key visible while developing.
 *
 * Both translators fall back to the source string, which is the right
 * behaviour in production — a forgotten key should degrade to the wrong
 * language, never to a blank label or a crash. But it also means the mistake
 * is invisible: "Участники" sat in the English ⌘K palette because the
 * dictionary held the page eyebrow 'УЧАСТНИКИ' and nothing complained about
 * the title-case key the palette asked for.
 *
 * So: shout in dev, stay quiet in production. e2e/i18n-keys.spec.ts is the
 * CI-side half of this — it scans every key statically, because the e2e server
 * runs a production build where this warning is off by design.
 */

const seen = new Set<string>();

export function reportMissingKey(dictionary: 'ui-text' | 'form-text', key: string): void {
  if (process.env.NODE_ENV === 'production') return;
  // Once per key: these run on every render.
  if (seen.has(dictionary + key)) return;
  seen.add(dictionary + key);
  // eslint-disable-next-line no-console
  console.error(
    `[i18n] ${dictionary}.ts has no entry for '${key}' — it will render in the ` +
      `source language. Add the key, or run the i18n-keys e2e check to list every miss.`
  );
}
