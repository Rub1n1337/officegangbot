import { test, expect } from '@playwright/test';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

/**
 * Every tt()/ft() key must exist in its dictionary.
 *
 * Both translators fall back to the source string when a key is missing, so a
 * forgotten entry doesn't throw or render blank — it renders the *other
 * language*, and looks fine until someone opens that screen in that locale.
 * That is how "Участники" sat in the English ⌘K palette: the dictionary had
 * the page eyebrow 'УЧАСТНИКИ' (upper-case) but not the palette's title-case
 * 'Участники'. Rendering tests miss it too, because the palette is closed
 * until you press the shortcut.
 *
 * This is a static check — no browser needed. It lives in the e2e project only
 * because that is where the dashboard's test runner is.
 */

const SRC = join(__dirname, '..', 'src');
const UI_TEXT = join(SRC, 'config', 'translations', 'ui-text.ts');
const FORM_TEXT = join(SRC, 'config', 'translations', 'form-text.ts');

function sourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      out.push(...sourceFiles(full));
    } else if (/\.tsx?$/.test(entry) && !full.includes(join('config', 'translations'))) {
      out.push(full);
    }
  }
  return out;
}

/** Keys the dictionary defines: 'quoted': or bareWord: at the top level. */
function dictionaryKeys(file: string): Set<string> {
  const src = readFileSync(file, 'utf8');
  const keys = new Set<string>();
  for (const m of src.matchAll(/^\s*'([^']*)':/gm)) keys.add(m[1]);
  for (const m of src.matchAll(/^\s*([A-Za-z][A-Za-z0-9_]*):/gm)) keys.add(m[1]);
  return keys;
}

/** Keys the code asks for: tt('…') / ft('…') with a plain string literal. */
function calledKeys(fn: 'tt' | 'ft'): Map<string, string> {
  const re = new RegExp(String.raw`\b${fn}\(\s*'([^']*)'\s*\)`, 'g');
  const found = new Map<string, string>();
  for (const file of sourceFiles(SRC)) {
    const src = readFileSync(file, 'utf8');
    for (const m of src.matchAll(re)) {
      if (!found.has(m[1])) found.set(m[1], file.replace(SRC, 'src'));
    }
  }
  return found;
}

test('every tt() key has an English translation', () => {
  const dictionary = dictionaryKeys(UI_TEXT);
  const called = calledKeys('tt');
  expect(called.size, 'no tt() calls found — the scan is broken, not the code').toBeGreaterThan(50);

  const missing = [...called].filter(([key]) => !dictionary.has(key));
  expect(
    missing.map(([key, file]) => `${file}: tt('${key}')`),
    'these keys fall back to the Russian source on the English locale'
  ).toEqual([]);
});

test('every ft() key has a Russian translation', () => {
  const dictionary = dictionaryKeys(FORM_TEXT);
  const called = calledKeys('ft');
  expect(called.size, 'no ft() calls found — the scan is broken, not the code').toBeGreaterThan(50);

  const missing = [...called].filter(([key]) => !dictionary.has(key));
  expect(
    missing.map(([key, file]) => `${file}: ft('${key}')`),
    'these keys fall back to the English source on the Russian locale'
  ).toEqual([]);
});

test('the English dictionary has no entry that translates to itself', () => {
  // A copy-pasted entry whose value equals its Russian key would render as
  // Russian on /en while looking "translated" in the file.
  const src = readFileSync(UI_TEXT, 'utf8');
  const selfReferential: string[] = [];
  for (const m of src.matchAll(/^\s*'([^']*)':\s*'([^']*)',/gm)) {
    if (m[1] === m[2] && /[А-Яа-яЁё]/.test(m[1])) selfReferential.push(m[1]);
  }
  expect(selfReferential, 'entries that map Russian to the same Russian').toEqual([]);
});
