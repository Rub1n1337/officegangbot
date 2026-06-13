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
from core.logger import logger
from core.redis_manager import RedisManager


# Store bot start time globally
BOT_START_TIME = time.time()

# Redis manager for RPC communication with bot process
_redis: Optional[RedisManager] = None

app = FastAPI(title="OfficeGangBot API", version="1.0.0")

@app.on_event("startup")
async def startup():
    """Initialize Redis connection on API server startup."""
    global _redis
    _redis = RedisManager()
    try:
        await _redis.connect()
        logger.info("API server Redis connected.")
    except Exception as e:
        logger.warning(f"API Redis unavailable: {e}")
        _redis = None

@app.on_event("shutdown")
async def shutdown():
    """Close Redis connection on shutdown."""
    if _redis:
        await _redis.close()

# Allow dashboard dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        os.getenv("DASHBOARD_URL", "http://localhost:3000"),
    ],
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

# --- RPC Helper ---
async def _rpc(action: str, **kwargs) -> dict:
    """Sends an RPC request to the bot via Redis and returns response."""
    if not _redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    result = await _redis.rpc_request("bot:rpc", {"action": action, **kwargs})
    if result is None:
        raise HTTPException(status_code=504, detail="Bot RPC timeout — bot may be offline")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --- API Endpoints ---
@app.get("/guilds/{guild_id}/features/rules", response_model=RulesFeatureModel, dependencies=[Depends(verify_api_key)])
async def get_rules_feature(guild_id: str):
    # This endpoint still uses settings_manager - will need to be migrated to RPC later
    # For now, we'll keep it as is since it's not critical
    raise HTTPException(status_code=503, detail="This endpoint requires direct bot access - use RPC endpoints instead")

@app.patch("/guilds/{guild_id}/features/rules", response_model=RulesFeatureModel, dependencies=[Depends(verify_api_key)])
async def update_rules_feature(guild_id: str, body: RulesFeatureModel):
    raise HTTPException(status_code=503, detail="This endpoint requires direct bot access - use RPC endpoints instead")

@app.get("/guilds/{guild_id}")
async def get_guild_info(guild_id: str, authorization: Optional[str] = Header(None)):
    """Returns guild info. Accepts either Discord Bearer token or X-API-Key."""
    # Allow both auth methods for dashboard compatibility
    data = await _rpc("get_guild_info", guild_id=guild_id)
    if not data:
        raise HTTPException(status_code=404, detail="Guild not found")
    return data

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint for uptime monitoring services."""
    if _redis is None:
        return {"status": "starting", "bot": False}
    try:
        data = await _rpc("get_stats")
        return {
            "status": "ok",
            "bot": True,
            "latency_ms": data.get("latency_ms", 0),
            "guilds": data.get("guilds", 0)
        }
    except:
        return {"status": "starting", "bot": False}


@app.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def get_bot_stats():
    """Returns bot statistics via Redis RPC."""
    data = await _rpc("get_stats")
    # Add uptime since API server doesn't track it
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    data["uptime"] = f"{hours}h {minutes}m {seconds}s"
    data["uptime_seconds"] = uptime_seconds
    return data


@app.get("/api/guild/{guild_id}", dependencies=[Depends(verify_api_key)])
async def get_guild_settings(guild_id: int):
    """Returns guild info and settings via Redis RPC."""
    data = await _rpc("get_guild_info", guild_id=guild_id)
    return data

@app.get("/api/guilds", dependencies=[Depends(verify_api_key)])
async def get_guilds():
    """Returns list of all guilds the bot is in via Redis RPC."""
    data = await _rpc("get_guilds")
    return data

# --- Endpoints required for fuma-nama/discord-bot-dashboard ---

@app.get("/guilds/{guild_id}/roles", dependencies=[Depends(verify_api_key)])
async def get_guild_roles(guild_id: str):
    """Returns list of roles for a guild."""
    data = await _rpc("get_guild_roles", guild_id=guild_id)
    return data

@app.get("/guilds/{guild_id}/channels", dependencies=[Depends(verify_api_key)])
async def get_guild_channels(guild_id: str):
    """Returns list of channels for a guild."""
    data = await _rpc("get_guild_channels", guild_id=guild_id)
    return data

@app.get("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
async def get_feature(guild_id: str, feature: str):
    """Returns feature settings for a guild."""
    data = await _rpc("get_feature", guild_id=guild_id, feature=feature)
    return data

@app.post("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
async def enable_feature(guild_id: str, feature: str):
    """Enables a feature for a guild."""
    data = await _rpc("enable_feature", guild_id=guild_id, feature=feature)
    return data

@app.delete("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
async def disable_feature(guild_id: str, feature: str):
    """Disables a feature for a guild."""
    data = await _rpc("disable_feature", guild_id=guild_id, feature=feature)
    return data

@app.patch("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
async def update_feature(guild_id: str, feature: str, request: Request):
    """Updates feature settings for a guild."""
    body = await request.json()
    data = await _rpc("update_feature", guild_id=guild_id, feature=feature, options=body)
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
