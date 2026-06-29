# Troubleshooting Log

This document tracks major errors encountered during the development of the OfficeGangBot and the solutions implemented to resolve them.

---

### 1. `PermissionError: [Errno 13] Permission denied: 'data/guild_settings.json'`

-   **Symptom:** The bot crashed whenever it tried to save settings for a new server or update existing ones. The logs showed a `PermissionError` because the `data` directory did not exist.
-   **Root Cause:** The `SettingsManager` did not ensure the `data/` directory existed before attempting to write the `guild_settings.json` file.
-   **Solution:**
    1.  The `SettingsManager` was refactored into a singleton to prevent multiple instances and ensure a single source of truth for settings.
    2.  Crucially, `os.makedirs(os.path.dirname(self.file_path), exist_ok=True)` was added to the `_load` and `_save` methods. This ensures the `data` directory is created automatically if it doesn't exist before any read or write operation, permanently resolving the permission error.

---

### 2. `discord.errors.NotFound: 404 Not Found (error code: 10062): Unknown interaction`

-   **Symptom:** Commands that took longer than 3 seconds to execute, like `/filter add_defaults`, would fail with an "Unknown Interaction" error.
-   **Root Cause:** Discord interactions must be acknowledged within 3 seconds. If a command's logic takes longer, the initial interaction token expires, and any attempt to respond fails.
-   **Solution:**
    1.  For long-running commands, the response is now deferred using `await ctx.defer(ephemeral=True)`. This tells Discord "I've received the command, I'm working on it," which extends the time limit to 15 minutes.
    2.  After deferring, subsequent messages must be sent using `await ctx.followup.send(...)` instead of `await ctx.send(...)`.
    3.  The `cog_command_error` handler was updated to check if an interaction was already responded to or deferred (`ctx.interaction.response.is_done()`) before attempting to send an error message, preventing further "Interaction has already been acknowledged" errors.

---

### 3. `AttributeError: 'Context' object has no attribute 'followup'`

-   **Symptom:** Hybrid commands (like `!filter add_defaults`) failed when invoked with a prefix. The error occurred because the code tried to use `ctx.followup`, which only exists for slash command interactions.
-   **Root Cause:** The command logic did not differentiate between a `discord.Interaction` (from a slash command) and a `commands.Context` (from a prefix command). `commands.Context` does not have `defer` or `followup` methods directly.
-   **Solution:**
    1.  The command logic was updated to check for the presence of `ctx.interaction`.
    2.  If `ctx.interaction` exists (it's a slash command), use `await ctx.defer()` and `await ctx.followup.send()`.
    3.  If `ctx.interaction` is `None` (it's a prefix command), send a simple "working on it" message with `await ctx.send(...)` and then send the final result with another `ctx.send(...)`. This provides a good user experience for both command types.

---
---
### 4. SyntaxError: unterminated f-string literal in cogs/guild_setup.py (rules step)

- **Symptom:**
  - Bot fails to load `cogs.guild_setup` with `SyntaxError: unterminated f-string literal (detected at line 89)` (or similar line number).
  - Traceback points to a multi-line f-string with triple backticks (```) and variable interpolation.
- **Root Cause:**
  - The f-string was split across lines or the triple backticks were not properly closed within the same string literal.
  - Python does not allow f-strings or triple-quoted strings to be split incorrectly or left unterminated.
- **Solution:**
  - Always keep the f-string and triple backticks on the same logical line or within a single string literal.
  - Do not concatenate f-strings and regular strings across lines unless each is properly closed.
  - After every edit to a multi-line string or f-string, check for unterminated string errors and ensure all parentheses and quotes are closed.
- **Checklist before commit:**
  - [ ] All f-strings are closed and not split across lines.
  - [ ] Triple backticks are always paired and not left open.
  - [ ] Run linter or syntax check after modifying multi-line strings.

---
### 5. Bot went offline (~11 min, 502) after rapid dashboard merges

- **Symptom:** "Application failed to respond" (502) on the bot's Railway URL right after a burst of dashboard-only PRs were merged; the bot recovered only after a while.
- **Root Cause:** The deploy workflow ran `railway up` on *every* push to `main`, including dashboard/docs-only changes that don't touch the bot. Several merges in a row each kicked off a new build, churning the deployment and leaving the bot unreachable between restarts even though its code hadn't changed.
- **Solution:** Added a `changes` job to `.github/workflows/deploy.yml` that diffs `HEAD^..HEAD` and only sets `bot=true` when bot files changed (`bot|main|api_server|config.py`, `cogs/`, `core/`, `scripts/`, `requirements.txt`). The `deploy` job now `needs: [lint, test, changes]` and runs only when `bot == 'true'`. Dashboard/doc PRs no longer restart the bot.

---
### 6. Emoji picker shrank to ~181px on desktop (width regression)

- **Symptom:** After a "mobile responsiveness" change, the emoji-mart picker popover became cramped (~181px wide) on desktop instead of its natural ~320–350px.
- **Root Cause:** A `dynamicWidth` prop made the picker fill its popover, but the popover (`PopoverContent`) resolved much narrower than intended.
- **Solution:** Reverted to the picker's natural width — `w="auto"` with only a `maxW="calc(100vw - 1rem)"` cap so it never exceeds the viewport on small screens. Caught by re-measuring `em-emoji-picker` width live after deploy; the lesson is to verify "responsive" tweaks on desktop too, not just narrow widths.

---
### 7. `/setup` welcome step configured nothing usable

- **Symptom:** Running `/setup` and entering a welcome message did not produce any welcome messages for new members.
- **Root Cause:** The welcome system (`cogs/welcome_system.py`) needs three things to fire — the `welcome-message` feature in `enabled_features`, a `welcome_channel_id`, and the message text — but the `/setup` wizard only saved the message. No channel was collected and the feature was never enabled.
- **Solution:** The Welcome step now opens a sub-panel with a channel picker and an "Edit message" button; on Save it persists `welcome_channel_id` and, when a channel was chosen, enables the `welcome-message` feature. Added the `welcome_channel_id` column mapping.

---
### 8. Dashboard server picker badges never rendered (`/api/me/guilds` 502)

- **Symptom:** The home server picker never showed the "Active / Add bot" badges or member counts in production, even though the data was correct when queried manually.
- **Root Cause:** The Next.js route `/api/me/guilds` fetched the user's Discord guilds without a try/catch. On the home page the browser's own `useGuilds` call hits the same Discord endpoint with the same token a moment earlier, so this request raced into a 429 / threw — crashing the handler with a 502. The `useMyBotGuilds` hook then errored and `botReachable` fell back to `false`, hiding the badges.
- **Solution:** The route now retries the Discord call briefly on 429 and **always responds 200**, degrading to `botReachable: false` (badges hidden) on hard failure instead of erroring. A follow-up made the hook **poll while degraded** so a cold-serverless-start degrade self-heals without a manual reload. Security note: the bot's full guild list is intersected with the caller's admin guilds **server-side**, never sent to the browser.

---
### 9. `/filter add_defaults` had no permission check (security)

- **Symptom:** Any member could run `/filter add_defaults` and flood the server's word filter with the default profanity list.
- **Root Cause:** Every other `filter` subcommand (`add`/`remove`/`toggle`/`list`) carries `@has_permission("config")`, but `add_defaults` had none — and group-level checks don't reliably cascade to hybrid/slash subcommands.
- **Solution:** Added `@has_permission("config")` to `filter_add_defaults`.

---
### 10. FastAPI interactive docs were public

- **Symptom:** `/docs`, `/redoc` and `/openapi.json` were reachable on the bot's public Railway URL with no auth.
- **Root Cause:** `FastAPI()` enables them by default; the per-endpoint `X-API-Key` dependency doesn't cover the docs routes.
- **Solution:** Constructed the app with `docs_url=None, redoc_url=None, openapi_url=None`. The API sits behind the dashboard proxy + API key, so a public schema only leaked the endpoint surface.

---
### 11. A bug in an RPC handler caused an 8-second hang → 504

- **Symptom:** When a bot RPC handler threw an unexpected exception, the dashboard request hung for ~8 seconds and then failed with a 504.
- **Root Cause:** The Redis RPC listener caught the exception (so the bot never crashed) but wrote **no response**, so the API server polled until its timeout and returned 504.
- **Solution:** `_handle_rpc_request` now wraps `_dispatch_rpc` in a try/except and returns a clean `{"error": "Internal bot error"}` immediately on any unhandled exception.

---
### 12. `get_enabled_features` hit Postgres on every message (performance)

- **Symptom:** Potential DB load spike on busy servers — automod, the word filter and the levels cog all call `get_enabled_features` in `on_message`.
- **Root Cause:** The method queried Postgres each call with no caching, so every message in every channel was a DB round-trip.
- **Solution:** Added an in-memory per-guild cache in `DatabaseManager` (mirroring the locale cache), invalidated in `set_feature_enabled`. Both slash-command and dashboard toggles go through `set_feature_enabled`, so the cache stays correct.

---
### 13. `testing_cog` (with `/testall`) was auto-loaded in production

- **Symptom:** A dev-only cog whose `/testall` command invokes every command was loaded on the production bot.
- **Root Cause:** The cog loader iterates every `.py` in `cogs/` with no allow/deny list.
- **Solution:** The loader now skips `testing_cog.py` unless `LOAD_TESTING_COG=1` is set.

---
### 14. New `dashboard_audit` table was missing RLS

- **Symptom:** The audit table wasn't covered by the deny-all Row Level Security block, unlike every other table.
- **Root Cause:** Forgot to add the new table to the RLS section of `scripts/init_db.sql`.
- **Solution:** Added `ALTER TABLE dashboard_audit ENABLE ROW LEVEL SECURITY;`. The bot connects as `postgres` and bypasses RLS, so its reads/writes are unaffected; the change only closes the Supabase/PostgREST anon path.

---
### 15. Dashboard moderation actions were invisible to Discord moderators

- **Symptom:** Banning/warning a member from the web dashboard left no trace in the server's `punishment_log` channel, so Discord-side moderators couldn't see web-initiated actions.
- **Root Cause:** The `moderate_member` RPC applied the action and wrote the DB but never posted to the punishment-log channel like the slash commands do.
- **Solution:** Added `_log_dashboard_action`, called for each dashboard moderation action, which posts a "Target / Moderator (via dashboard) / Reason" embed when Logging is enabled — plus a `dashboard_audit` row attributed to the acting admin (resolved server-side from the proxy session, not a spoofable client field).

---
### 16. Light/dark theme contrast bugs (invisible text and card edges)

- **Symptom:** (a) The rules-message **Preview** text was invisible on the **light** theme; (b) the boundaries between cards/blocks (Reaction Role rows, Level reward rows, form fields) were invisible on the **dark** theme.
- **Root Cause:** (a) `RulesPreview` rendered Discord block-quote lines (the default rules all start with `> `) using a hardcoded `color="whiteAlpha.900"` — white, invisible on a white card. (b) Nested cards all used `bg="CardBackground"` with only a `boxShadow`, which disappears on the dark background, so same-colour cards blended together.
- **Solution:** (a) Quote/regular preview text now uses the theme-aware `TextPrimary`, and the quote bar / emoji pill / card borders use `_dark` variants. (b) Added a `CardBorder` semantic token (`blackAlpha.200` light / `whiteAlpha.200` dark) and applied a 1px `CardBorder` to `FormCard` and the Reaction-Role / Level-reward row cards so nested cards are delineated on both themes. **Lesson:** never hardcode `whiteAlpha.*` / `blackAlpha.*` for text or borders — use semantic tokens (`TextPrimary`, `CardBorder`) or `_dark` variants so both themes stay legible.

---
### 17. Search icon overlapped the placeholder text

- **Symptom:** On the home and Members search inputs, the magnifying-glass icon sat on top of the placeholder text.
- **Root Cause:** The `main` Input variant sets `p: '20px'`, which overrode the left padding that `InputGroup` injects for an `InputLeftElement`.
- **Solution:** Added an explicit `pl` to those inputs so the text clears the icon.

---
### 18. Emoji picker slipped under the next card on mobile

- **Symptom:** On narrow screens the emoji picker popover rendered *behind* the following form card.
- **Root Cause:** The Chakra `Popover` wasn't portaled and had no z-index, so it stayed within the card's stacking context.
- **Solution:** Wrapped `PopoverContent` in `<Portal>` and gave it a `popover` z-index so it floats above sibling cards.

---
### 19. Failed CDN request for icon-less servers

- **Symptom:** The home picker fired a 404/503 request per server that had no icon (URL ended in `/null`).
- **Root Cause:** `iconUrl(guild)` built `.../icons/<id>/<icon>` even when `guild.icon` was `null`.
- **Solution:** `iconUrl` returns `undefined` when there's no icon, so `<Avatar src>` skips the request and uses its initials fallback; `Guild.icon` typed as `string | null`.

---
### 20. Malformed API bodies surfaced as 502/404 instead of 422

- **Symptom:** Posting an invalid body (e.g. an unknown moderation `act`, or `locale` outside en/ru) returned a confusing 502/404 from deep inside the bot.
- **Root Cause:** Mutating FastAPI endpoints read raw `request.json()` and deferred validation to the RPC handler.
- **Solution:** Added Pydantic request models (`ModeratePayload` with `act` as a `Literal` of the five actions; `LocalePayload` with `locale` `Literal["en","ru"]`) so FastAPI rejects bad input with a clean 422 at the edge.

---

## Process notes (lessons, not bugs)

- **Always branch before editing.** A few changes were accidentally started on `main`; recovered each time with `git branch <name>` then `git reset --hard origin/main`. Create the feature branch first.
- **`keyframes` comes from `@emotion/react`,** not `@chakra-ui/react`, in this Chakra version.
- **Verify changes live, not just by build.** Live re-checks caught the 181px emoji-picker regression (#6), the `/api/me/guilds` 502 (#8), and the deploy-churn outage (#5) — none of which a green build would have revealed.
- **The DB schema auto-applies:** `setup_hook` → `DatabaseManager._init_schema()` runs `scripts/init_db.sql` on every startup, so migrations go there as idempotent `CREATE TABLE IF NOT EXISTS` / `ALTER ... IF EXISTS` and apply on the next Railway redeploy.