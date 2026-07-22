import { test, expect } from '@playwright/test';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

// Phase 3 guard for the grid refactor: keeps the spacing on the 4px scale and
// the type scale free of half-pixels once they've been cleaned up. A pure
// source scan (no browser) — fails the moment someone reintroduces a raw-px
// gutter or a N.5px font size.
function walkTsx(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walkTsx(p));
    else if (p.endsWith('.tsx')) out.push(p);
  }
  return out;
}

test('grid: spacing stays on the scale and font sizes have no half-pixels', () => {
  const files = walkTsx('src');
  // gap / padding / margin props with a raw px value. 1px is allowed (hairlines).
  const spacing = /\b(?:gap|p|px|py|pt|pb|pl|pr|m|mt|mb|ml|mr|mx|my)="(\d+)px"/g;
  const halfPx = /fontSize="\d+\.5px"/;
  const bad: string[] = [];

  for (const f of files) {
    const src = readFileSync(f, 'utf8');
    if (halfPx.test(src)) bad.push(`${f}: half-pixel fontSize (use an integer / textStyle)`);
    let m: RegExpExecArray | null;
    while ((m = spacing.exec(src)) !== null) {
      if (m[1] !== '1') bad.push(`${f}: raw-px gutter ${m[0]} (use a 4px scale token, e.g. {3}=12px)`);
    }
  }

  expect(bad, `off-grid values:\n${bad.join('\n')}`).toEqual([]);
});

test('no bare /guilds/:id navigation — always route to a sub-page', () => {
  // Pushing/linking the bare /guilds/:id relied on the next.config redirect,
  // which on a client-side navigation could hang on the page-less route instead
  // of loading (reported live when switching servers). Every guild link must
  // carry a sub-route (/settings, /features/..., etc.).
  const bare = /`\/guilds\/\$\{[^}]+\}`/; // template ending right after ${...}
  const bad: string[] = [];
  for (const f of walkTsx('src')) {
    const src = readFileSync(f, 'utf8');
    if (bare.test(src)) bad.push(f);
  }
  expect(bad, `bare /guilds/:id navigation (append a sub-route like /settings): ${bad.join(', ')}`).toEqual([]);
});

test('no {base, sm} two-key responsive props — sm is 320px, use md for mobile/desktop', () => {
  // The theme sets sm=320px, so a two-key {base, sm} applies the sm value on
  // every phone and the base value never shows — the exact landmine that made
  // the ticket filters render at fixed narrow widths on mobile. Mobile-vs-
  // desktop must use {base, md}.
  const twoKey = /\{\s*base:[^,{}]+,\s*sm:[^,{}]+\}/;
  const bad: string[] = [];
  for (const f of walkTsx('src')) {
    if (twoKey.test(readFileSync(f, 'utf8'))) bad.push(f);
  }
  expect(bad, `two-key {base, sm} responsive props (use {base, md}): ${bad.join(', ')}`).toEqual([]);
});
