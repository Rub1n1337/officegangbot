# 🤖 OfficeGangBot

A feature-rich Discord bot for server management — moderation, leveling, content
filtering, reaction roles, logging, and automation — with a companion **web
dashboard** for point-and-click configuration.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Discord library | discord.py 2.5+ (slash / hybrid commands) |
| Database | PostgreSQL (Supabase) via `asyncpg` |
| Cache & cooldowns | Redis (Upstash) |
| REST API | FastAPI + Uvicorn (`api_server.py`), in-process with the bot |
| RPC transport | Redis (dashboard ⇆ bot) |
| Dashboard | Next.js + Chakra UI (Discord OAuth) |
| Hosting | Bot → Railway · Dashboard → Vercel |

> The bot is **slash-only** — commands are invoked with `/` (or by mentioning the
> bot). There is no message-prefix system.

---

## 🚀 Local Setup (bot)

### 1. Clone & enter
```bash
git clone https://github.com/Rub1n1337/officegangbot.git
cd officegangbot
```

### 2. Virtual environment
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt          # runtime
pip install -r requirements-dev.txt       # + pytest & ruff (for tests/lint)
```

### 4. Configure environment
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

| Variable | Required | Purpose |
|----------|:--------:|---------|
| `DISCORD_TOKEN` | ✅ | Bot token |
| `BOT_OWNER_ID` | ✅ | Your Discord user ID (owner bypass) |
| `APPLICATION_ID` | ✅ | Application ID for slash-command sync |
| `API_SECRET_KEY` | ✅ | Shared `X-API-Key` secret for the dashboard ⇆ API |
| `DATABASE_URL` | ✅ | PostgreSQL DSN (Supabase) |
| `REDIS_URL` | ✅ | Redis URL (Upstash) — caching, cooldowns, RPC |
| `BOT_LOG_LEVEL` | ⬜ | `INFO` (default) / `DEBUG` / `WARNING` … |
| `DASHBOARD_URL` | ⬜ | Allowed CORS origin for the API |
| `PORT` | ⬜ | Port for the keep-alive web server |

> The PostgreSQL schema in `scripts/init_db.sql` is **idempotent** and applied
> automatically on startup — no manual migration step.

### 5. Run
```bash
python main.py   # with auto-restart
# or
python bot.py    # direct
```

---

## 📋 Commands

All commands are **slash commands**. Run `/help` in your server for a live,
always-up-to-date list with an interactive category menu.

### ⚙️ Setup & Config
| Command | Description |
|---------|-------------|
| `/setup` | Interactive server setup wizard |
| `/config role <level> <role>` | Grant a role a permission level (config/kick/ban/…) |
| `/config logs <type> <channel>` | Set logging channels |
| `/settings` | View current server settings |

### 🛡️ Moderation
| Command | Description |
|---------|-------------|
| `/kick <member> [reason]` | Kick a member |
| `/ban <member> [reason]` | Ban a member (with confirmation) |
| `/mute <member> [reason]` | Mute a member |
| `/warn <member> [reason]` | Issue a warning |
| `/warnings <member>` | View warnings for a member |
| `/clearwarnings <member>` | Clear all warnings for a member |
| `/clear <amount>` | Bulk-delete messages (1–100) |

### ⭐ Levels
| Command | Description |
|---------|-------------|
| `/rank [member]` | Show level, XP and progress |
| `/leaderboard` | Top members by XP |
| `/setlevelrole <level> <role>` | Reward a role at a given level |

### 🚫 Filter
| Command | Description |
|---------|-------------|
| `/filter toggle` | Enable/disable the word filter |
| `/filter add <word>` | Add a banned word |
| `/filter remove <word>` | Remove a banned word (autocompletes existing words) |
| `/filter list` | List all filtered words |

### 🛠️ Utility & Help
| Command | Description |
|---------|-------------|
| `/userinfo [member]` · `/serverinfo` · `/ping` | Info & latency |
| `/help [category\|command]` | Interactive help with a category dropdown |

> Welcome messages, reaction roles, the rules message and logging are configured
> from the **dashboard** (and partly via `/setup`).

---

## 🖥️ Dashboard

A Next.js app (in `dashboard/`) deployed to Vercel. Admins sign in with Discord,
and each guild gets feature panels (Rules, Reaction Role, Moderation, Logging,
Word Filter, Welcome Message) that can be toggled on/off and configured.

- Browser → `dashboard/src/pages/api/bot/[...path].ts` proxy → FastAPI (`X-API-Key`).
- The proxy verifies the signed-in user is an **administrator of that guild**
  before forwarding any guild-scoped request.

```bash
cd dashboard
npm install        # or pnpm install
npm run dev
```

---

## 🧪 Tests & Linting

```bash
pytest -q                                  # unit tests (level math, SQL whitelist, permissions)
ruff check . --select E,F --ignore E501    # lint
```

Both run in CI on every push / PR (`.github/workflows/deploy.yml`); deploys to
Railway are gated on them passing.

---

## 📁 Project Structure

```
officegangbot/
├── bot.py                 # Bot entrypoint, FastAPI/RPC wiring, auto-defer
├── main.py                # Runner with auto-restart
├── api_server.py          # FastAPI REST API for the dashboard
├── config.py              # Configuration loader
├── requirements.txt       # Runtime dependencies
├── requirements-dev.txt   # + pytest, ruff
├── core/
│   ├── db_manager.py       # Async PostgreSQL (asyncpg) manager
│   ├── redis_manager.py    # Redis cache / cooldowns / RPC
│   ├── permissions.py      # has_permission() check
│   ├── health_monitor.py   # Health monitoring
│   ├── command_blocker.py  # Command gating helpers
│   └── logger.py           # Rotating file logger
├── cogs/                  # moderation, levels, filter, reaction_roles,
│   └── …                  # warnings, welcome, tickets, logging, automod, …
├── scripts/
│   ├── init_db.sql         # Idempotent schema (applied on startup)
│   └── migrate_json_to_pg.py
├── tests/                 # pytest suite
└── dashboard/             # Next.js web dashboard
```

---

## 🔒 Security

- Secrets live only in `.env` (git-ignored) / host secret stores — never in code.
- Dashboard ⇆ API protected by an `X-API-Key`; the proxy additionally enforces
  **per-guild admin** authorization.
- Guild-setting column names are validated against an allowlist before being
  interpolated into SQL (SQL-injection guard).
- PostgreSQL tables use row-level-security deny-all (access is via the bot only).
- A lock file prevents double bot startup.
