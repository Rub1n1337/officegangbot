# 🤖 OfficeGangBot

A feature-rich Discord bot for server management — moderation, configuration, logging, content filtering, and automation.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Discord Library | discord.py 2.3+ |
| REST API | FastAPI + Uvicorn |
| Keep-alive | Flask |
| Settings Storage | JSON (guild_settings.json) |
| Monitoring | psutil |
| Configuration | python-dotenv |

---

## 🚀 Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/Rub1n1337/officegangbot.git
cd officegangbot
```

### 2. Create a virtual environment
```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

`.env` contents:
```
DISCORD_TOKEN=your_bot_token
BOT_OWNER_ID=your_discord_user_id
APPLICATION_ID=your_application_id
API_SECRET_KEY=your_random_secret_key
BOT_LOG_LEVEL=INFO
```

### 5. Run the bot
```bash
# With auto-restart:
python main.py

# Direct:
python bot.py
```

---

## 📋 Commands

### ⚙️ Setup & Config
| Command | Description |
|---------|-------------|
| `!setup` | Interactive server setup wizard |
| `/config prefix <prefix>` | Change the bot prefix |
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
| `/clear <amount>` | Delete messages (1-100) |

### 🛠️ Utility
| Command | Description |
|---------|-------------|
| `/userinfo [member]` | Show member information |
| `/serverinfo` | Show server information |
| `/ping` | Check bot latency |
| `/help [command]` | Show help for commands |

### 👋 Welcome System
| Command | Description |
|---------|-------------|
| `/welcome toggle` | Enable/disable welcome messages |
| `/welcome channel <channel>` | Set the welcome channel |
| `/welcome message <text>` | Set the welcome message |
| `/welcome autorole <role>` | Set auto-role on member join |

### 🚫 Filter
| Command | Description |
|---------|-------------|
| `/filter toggle` | Enable/disable the word filter |
| `/filter add <word>` | Add a word to the filter |
| `/filter remove <word>` | Remove a word from the filter |
| `/filter list` | List all filtered words |

---

## 📁 Project Structure

```
officegangbot/
├── bot.py              # Main bot file
├── main.py             # Runner with auto-restart
├── config.py           # Configuration loader
├── api_server.py       # FastAPI REST for dashboard
├── requirements.txt    # Dependencies
├── .env.example        # Environment variable template
├── core/
│   ├── settings_manager.py  # Settings Singleton
│   ├── permissions.py       # Permission decorators
│   ├── health_monitor.py    # Health monitoring
│   ├── logger.py            # Rotating file logger
│   └── webserver.py         # Flask keep-alive
├── cogs/
│   ├── moderation.py        # Moderation commands
│   ├── warnings_cog.py      # Warning system
│   ├── utility_cog.py       # Utility commands
│   ├── welcome_system.py    # Welcome system
│   ├── filter_cog.py        # Message filter
│   ├── guild_setup.py       # Setup wizard
│   ├── config_cog.py        # Configuration
│   ├── help_cog.py          # Help system
│   └── ...
└── data/
    └── guild_settings.json  # Per-guild settings
```

---

## 🔒 Security

- Bot token stored only in `.env` (never in code)
- `.env` is listed in `.gitignore` 
- REST API protected via `X-API-Key` header
- Lock file prevents double bot startup
