/**
 * Tabular (fixed-width) figures for the dashboard's numeric surfaces.
 *
 * Two reasons, both from the Notion "vertical rhythm is sacred" principle:
 *  - KPI tiles live-poll every 8s; with proportional digits a value changing
 *    from e.g. "69 мс" to "112 мс" shifts everything after it sideways. Tabular
 *    digits are all the same width, so the number stays put as it updates.
 *  - Numbers stacked in a column (XP leaderboard, strike counts, "N of M")
 *    only line up when their digits share a width.
 *
 * One token, spread as `sx={tabularNums}`, rather than the value scattered
 * across every call site.
 */
export const tabularNums = { fontVariantNumeric: 'tabular-nums' } as const;
