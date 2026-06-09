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