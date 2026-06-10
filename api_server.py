# api_server.py
# REST API for OfficeGangBot dashboard integration (FastAPI, best practices)

from fastapi import FastAPI, HTTPException, Path, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
import threading
import time
import psutil

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'guild_settings.json')
_settings_lock = threading.Lock()

# Store bot start time globally
BOT_START_TIME = time.time()

# Store bot instance globally
bot_instance = None

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot

app = FastAPI(title="OfficeGangBot API", version="1.0.0")

# Allow dashboard dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RulesFeatureModel(BaseModel):
    channel: Optional[str] = None
    message: str

# --- API Authentication ---
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")

# --- Utility functions ---
def load_guild_settings():
    with _settings_lock:
        if not os.path.exists(DATA_PATH):
            return {}
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

def save_guild_settings(settings):
    with _settings_lock:
        tmp_path = DATA_PATH + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, DATA_PATH)

# --- API Endpoints ---
@app.get("/guilds/{guild_id}/features/rules", response_model=RulesFeatureModel, dependencies=[Depends(verify_api_key)])
def get_rules_feature(guild_id: str):
    settings = load_guild_settings()
    guild = settings.get(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    return {
        "channel": str(guild.get("rules_channel_id")) if guild.get("rules_channel_id") else None,
        "message": guild.get("rules_message", "")
    }

@app.patch("/guilds/{guild_id}/features/rules", response_model=RulesFeatureModel, dependencies=[Depends(verify_api_key)])
def update_rules_feature(guild_id: str, body: RulesFeatureModel):
    settings = load_guild_settings()
    guild = settings.setdefault(guild_id, {})
    if body.channel:
        guild["rules_channel_id"] = body.channel
    if body.message:
        guild["rules_message"] = body.message
    save_guild_settings(settings)
    return {
        "channel": body.channel,
        "message": body.message
    }

@app.get("/guilds/{guild_id}", dependencies=[Depends(verify_api_key)])
async def get_guild_info(guild_id: str):
    settings = load_guild_settings()
    guild_data = settings.get(guild_id, {})

    # Transform to match CustomGuildInfo type
    return {
        "id": guild_id,
        "name": guild_data.get("name", "OfficeGang Server"),
        "icon": guild_data.get("icon"),
        "owner_id": guild_data.get("owner_id", "0"),
        "features": {
            "rules": {
                "channel": str(guild_data.get("rules_channel_id", "")) or None,
                "message": ""  # Rules message is not stored in the current format
            },
            "welcome-message": {
                "channel": None,  # Not in current settings
                "message": guild_data.get("welcome_message", "Welcome {user.mention} to **{server.name}**!")
            },
            "reaction-role": {
                "messageId": str(guild_data.get("rules_message_id", "")) or None,
                "channelId": str(guild_data.get("rules_channel_id", "")) or None,
                "emoji": guild_data.get("reaction_emoji", ""),
                "roleId": str(guild_data.get("reaction_role_id", "")) or None
            },
            "moderation": {
                "modRoles": [],
                "adminRoles": [],
                "muteRole": None
            },
            "logging": {
                "logChannel": str(guild_data.get("punishment_log_id", "")) or None,
                "events": []
            }
        },
        "permissions": 0
    }

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def get_bot_stats():
    """
    Returns general bot statistics:
    uptime, CPU/RAM usage, total guilds and users.
    """
    if bot_instance is None:
        raise HTTPException(status_code=503, detail="Bot is not connected")

    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    total_users = sum(g.member_count for g in bot_instance.guilds)

    # Use interval=None to avoid blocking the event loop
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()

    return {
        "status": "online",
        "uptime": uptime_str,
        "uptime_seconds": uptime_seconds,
        "guilds": len(bot_instance.guilds),
        "total_users": total_users,
        "latency_ms": round(bot_instance.latency * 1000, 2),
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_used_mb": round(ram.used / 1024 / 1024, 2),
    }


@app.get("/api/guild/{guild_id}", dependencies=[Depends(verify_api_key)])
async def get_guild_settings(guild_id: int):
    """
    Returns the full settings for a specific guild from SettingsManager.
    """
    if bot_instance is None:
        raise HTTPException(status_code=503, detail="Bot is not connected")

    guild = bot_instance.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found or bot is not a member")

    settings = bot_instance.settings_manager.get_all_settings(guild_id)

    return {
        "guild_id": guild_id,
        "guild_name": guild.name,
        "member_count": guild.member_count,
        "settings": settings
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
