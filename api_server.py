# api_server.py
# REST API for OfficeGangBot dashboard integration (FastAPI, best practices)

from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Optional
import os
import secrets
from dotenv import load_dotenv
load_dotenv()
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from core.logger import logger
from core.redis_manager import RedisManager


# Store bot start time globally
BOT_START_TIME = time.time()

# Redis manager for RPC communication with bot process
_redis: Optional[RedisManager] = None
_redis_last_ok: float = 0.0  # timestamp of last successful RPC call

# Lazy-reconnect bookkeeping (exponential backoff so an outage doesn't make every
# request pay a slow reconnect, and a counter exposed via /health for ops).
_redis_reconnects: int = 0          # successful lazy reconnects since startup
_reconnect_fail_streak: int = 0     # consecutive failed reconnect attempts
_reconnect_retry_after: float = 0.0  # earliest monotonic-ish time to retry
_RECONNECT_BASE_DELAY = 0.5
_RECONNECT_MAX_DELAY = 30.0

# Global bot instance for direct access (when embedded in bot process)
bot_instance = None

def set_bot_instance(bot_obj):
    """Set the global bot instance for direct access."""
    global bot_instance
    bot_instance = bot_obj

# Interactive docs (/docs, /redoc) and the OpenAPI schema are disabled: this
# API sits behind the dashboard proxy and an X-API-Key, so a public schema would
# only leak the endpoint surface to anyone hitting the Railway URL directly.
app = FastAPI(
    title="OfficeGangBot API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Rate limiting (per client IP). Health check is intentionally left unlimited.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
async def startup():
    """Initialize Redis connection on API server startup."""
    global _redis
    _redis = RedisManager()
    try:
        await _redis.connect()
        logger.info("API server Redis connected.")
    except Exception as e:
        logger.warning(f"API Redis unavailable at startup: {e}")
        _redis = None

@app.on_event("shutdown")
async def shutdown():
    """Close Redis connection on shutdown."""
    if _redis:
        await _redis.close()

def _dashboard_origins() -> list[str]:
    raw = os.getenv("DASHBOARD_URL", "http://localhost:3000")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


# Allow the configured dashboard origin only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_dashboard_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# --- API Authentication ---
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    api_secret = os.getenv("API_SECRET_KEY")
    if not api_secret:
        logger.error("API_SECRET_KEY is not configured.")
        raise HTTPException(status_code=503, detail="API key is not configured")
    if not x_api_key or not secrets.compare_digest(x_api_key, api_secret):
        raise HTTPException(status_code=401, detail="Invalid API key")

# --- RPC Helper ---
async def _ensure_redis() -> Optional[RedisManager]:
    """
    Returns the current Redis manager, attempting a reconnect if it is None.
    This handles the case where the initial startup connection failed or
    the connection was lost after startup.
    """
    global _redis, _redis_reconnects, _reconnect_fail_streak, _reconnect_retry_after
    if _redis is not None:
        try:
            await _redis.redis.ping()
            return _redis
        except Exception as e:
            logger.warning(f"Existing Redis connection failed ping check: {e}. Attempting reconnect.")
            _redis = None

    # Exponential backoff: during an outage, reconnecting on every request both
    # slows each request and hammers Redis. Wait out the current backoff window.
    if time.time() < _reconnect_retry_after:
        return None

    logger.warning("Redis is unavailable or connection is stale — attempting lazy reconnect...")
    try:
        new_redis = RedisManager()
        await new_redis.connect()
        _redis = new_redis
        _redis_reconnects += 1
        _reconnect_fail_streak = 0
        _reconnect_retry_after = 0.0
        logger.info(f"Redis lazy reconnect succeeded (total reconnects: {_redis_reconnects}).")
        return _redis
    except Exception as e:
        _reconnect_fail_streak += 1
        delay = min(_RECONNECT_MAX_DELAY, _RECONNECT_BASE_DELAY * (2 ** (_reconnect_fail_streak - 1)))
        _reconnect_retry_after = time.time() + delay
        logger.error(
            f"Redis lazy reconnect failed (streak {_reconnect_fail_streak}, "
            f"next retry in {delay:.1f}s): {e}"
        )
        return None

async def _rpc(action: str, **kwargs) -> Any:
    """Sends an RPC request to the bot via Redis and returns response."""
    global _redis_last_ok
    redis = await _ensure_redis()
    if not redis:
        elapsed = time.time() - _redis_last_ok if _redis_last_ok else None
        logger.error(
            f"_rpc called with action=\'{action}\' but Redis is unavailable. "
            f"Last successful RPC: {f'{elapsed:.1f}s ago' if elapsed else 'never'}. "
            f"_redis object is None after reconnect attempt. Current _redis state: {redis}"
        )
        raise HTTPException(status_code=503, detail="Redis not available")
    try:
        envelope = await redis.rpc_request("bot:rpc", {"action": action, **kwargs})
    except Exception as e:
        logger.error(f"Redis rpc_request raised exception for action='{action}': {e}", exc_info=True)
        # Mark redis as potentially broken so next call will attempt reconnect
        _redis = None
        raise HTTPException(status_code=503, detail="Redis connection error during RPC")
    if envelope is None:
        raise HTTPException(status_code=504, detail="Bot RPC timeout — bot may be offline")
    if isinstance(envelope, dict) and "error" in envelope and "data" not in envelope:
        # Logical errors from the bot handler (e.g. "Guild not found") arrive as a
        # bare {"error": ...} envelope. Map "not found" to 404 so the dashboard can
        # tell "bot isn't in this guild" apart from a real gateway failure (502).
        err = envelope["error"]
        status = 404 if isinstance(err, str) and "not found" in err.lower() else 502
        raise HTTPException(status_code=status, detail=err)

    result = envelope.get("data", envelope) if isinstance(envelope, dict) else envelope
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    _redis_last_ok = time.time()
    return result


# --- API Endpoints ---

@app.get("/guilds/{guild_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_guild_info(request: Request, guild_id: str):
    """Returns guild info via Redis RPC."""
    data = await _rpc("get_guild_info", guild_id=guild_id)
    if not data:
        raise HTTPException(status_code=404, detail="Guild not found")
    return data

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint for uptime monitoring services."""
    if _redis is None:
        return {"status": "starting", "bot": False, "redis_reconnects": _redis_reconnects}
    try:
        data = await _rpc("get_stats")
        return {
            "status": "ok",
            "bot": True,
            "latency_ms": data.get("latency_ms", 0),
            "guilds": data.get("guilds", 0),
            "redis_reconnects": _redis_reconnects,
        }
    except Exception:
        return {"status": "starting", "bot": False, "redis_reconnects": _redis_reconnects}


@app.get("/api/stats", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_bot_stats(request: Request):
    """Returns bot statistics via Redis RPC."""
    data = await _rpc("get_stats")
    # Add uptime since API server doesn't track it
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    data["uptime"] = f"{hours}h {minutes}m {seconds}s"
    data["uptime_seconds"] = uptime_seconds
    data["redis_reconnects"] = _redis_reconnects
    return data


@app.get("/api/guild/{guild_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_guild_settings(request: Request, guild_id: int):
    """Returns guild info and settings via Redis RPC."""
    data = await _rpc("get_guild_info", guild_id=guild_id)
    return data

@app.get("/api/guilds", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_guilds(request: Request):
    """Returns list of all guilds the bot is in via Redis RPC."""
    data = await _rpc("get_guilds")
    return data

@app.get("/api/guild/{guild_id}/stats", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_guild_stats(request: Request, guild_id: int):
    """Returns live overview stats for a guild (members, channels, top XP) via RPC."""
    data = await _rpc("get_guild_stats", guild_id=guild_id)
    return data

@app.get("/api/guild/{guild_id}/emojis", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_guild_emojis(request: Request, guild_id: int):
    """Returns the guild's custom emojis (for the dashboard emoji picker)."""
    data = await _rpc("get_guild_emojis", guild_id=guild_id)
    return data

@app.get("/api/guild/{guild_id}/moderation", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_moderation(request: Request, guild_id: int):
    """Returns recent warnings, active timed punishments and the XP leaderboard."""
    data = await _rpc("get_moderation", guild_id=guild_id)
    return data

@app.delete("/api/guild/{guild_id}/warnings/{warning_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def delete_warning(request: Request, guild_id: int, warning_id: int):
    """Deletes a single warning by id."""
    data = await _rpc("delete_warning", guild_id=guild_id, warning_id=warning_id)
    return data

@app.post("/api/guild/{guild_id}/locale", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def set_locale(request: Request, guild_id: int):
    """Sets the guild's bot language ('en' / 'ru')."""
    body = await request.json()
    data = await _rpc("set_locale", guild_id=guild_id, locale=body.get("locale"))
    return data

@app.get("/api/guild/{guild_id}/members", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
async def search_members(request: Request, guild_id: int, q: str = ""):
    """Searches the guild's members by name/id (max 25 results)."""
    data = await _rpc("search_members", guild_id=guild_id, query=q)
    return data

@app.get("/api/guild/{guild_id}/members/{user_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
async def get_member(request: Request, guild_id: int, user_id: int):
    """Returns a member's profile: roles, level/XP and warnings."""
    data = await _rpc("get_member", guild_id=guild_id, user_id=user_id)
    return data

@app.post("/api/guild/{guild_id}/members/{user_id}/moderate", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def moderate_member(request: Request, guild_id: int, user_id: int):
    """Performs a moderation action (warn/mute/unmute/kick/ban) on a member."""
    body = await request.json()
    data = await _rpc(
        "moderate_member",
        guild_id=guild_id,
        user_id=user_id,
        act=body.get("act"),
        reason=body.get("reason"),
        duration_minutes=body.get("durationMinutes"),
        moderator_id=body.get("moderatorId"),
        moderator_name=body.get("moderatorName"),
    )
    return data

# --- Endpoints required for fuma-nama/discord-bot-dashboard ---

@app.get("/guilds/{guild_id}/roles", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_guild_roles(request: Request, guild_id: str):
    """Returns list of roles for a guild."""
    data = await _rpc("get_guild_roles", guild_id=guild_id)
    return data

@app.get("/guilds/{guild_id}/channels", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_guild_channels(request: Request, guild_id: str):
    """Returns list of channels for a guild."""
    data = await _rpc("get_guild_channels", guild_id=guild_id)
    return data

@app.get("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_feature(request: Request, guild_id: str, feature: str):
    """Returns feature settings for a guild."""
    data = await _rpc("get_feature", guild_id=guild_id, feature=feature)
    return data

@app.post("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def enable_feature(request: Request, guild_id: str, feature: str):
    """Enables a feature for a guild."""
    data = await _rpc("enable_feature", guild_id=guild_id, feature=feature)
    return data

@app.delete("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def disable_feature(request: Request, guild_id: str, feature: str):
    """Disables a feature for a guild."""
    data = await _rpc("disable_feature", guild_id=guild_id, feature=feature)
    return data

@app.patch("/guilds/{guild_id}/features/{feature}", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def update_feature(request: Request, guild_id: str, feature: str):
    """Updates feature settings for a guild."""
    body = await request.json()
    data = await _rpc("update_feature", guild_id=guild_id, feature=feature, options=body)
    return data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
