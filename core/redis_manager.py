# core/redis_manager.py
"""
Async Redis manager using redis.asyncio connection pool.
Handles caching (XP, cooldowns, filter patterns, automod)
and RPC communication between bot and API server via Redis Streams.
"""

import redis.asyncio as aioredis
import os
import json
import asyncio
import uuid
import datetime
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit
from core.logger import logger


def _redact_url(url: str) -> str:
    """Strip credentials from a Redis URL so it can be logged safely.
    Upstash URLs look like ``rediss://default:<password>@host:port`` — the
    password must never reach the logs."""
    try:
        parts = urlsplit(url)
        if parts.username or parts.password:
            netloc = parts.hostname or ""
            if parts.port:
                netloc = f"{netloc}:{parts.port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
        return url
    except Exception:
        return "<redacted>"


def _json_default(obj):
    """Fallback serializer for types json.dumps can't handle natively (e.g. asyncpg datetime/Decimal)."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class RedisManager:
    """
    Async Redis manager with connection pool.
    Initialize via connect(), close via close().
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._rpc_tasks: set[asyncio.Task] = set()

    async def connect(self) -> None:
        """Creates Redis connection pool. Call in bot.setup_hook() and api_server startup."""
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self._redis = aioredis.from_url(
    url,
    encoding="utf-8",
    decode_responses=True,
    max_connections=20,
    health_check_interval=30,
    socket_keepalive=True,
)
            await self._redis.ping()
            logger.info("Redis connection established successfully.")
        except Exception as e:
            logger.critical(f"Failed to connect to Redis at {_redact_url(url)}: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """Closes the Redis connection."""
        for task in list(self._rpc_tasks):
            task.cancel()
        if self._rpc_tasks:
            await asyncio.gather(*self._rpc_tasks, return_exceptions=True)
            self._rpc_tasks.clear()

        if self._redis:
            await self._redis.aclose()
            logger.info("Redis connection closed gracefully.")

    @property
    def redis(self) -> aioredis.Redis:
        if not self._redis:
            raise RuntimeError("RedisManager is not connected. Call connect() first.")
        return self._redis

    # -------------------------
    # Generic key-value cache
    # -------------------------

    async def get(self, key: str) -> Optional[Any]:
        """Gets a JSON-decoded value from Redis."""
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value is not None else None
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Sets a JSON-encoded value in Redis with optional TTL in seconds."""
        try:
            encoded = json.dumps(value, default=_json_default)
            if ttl:
                await self.redis.setex(key, ttl, encoded)
            else:
                await self.redis.set(key, encoded)
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")

    async def delete(self, key: str) -> None:
        """Deletes a key from Redis."""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")

    async def exists(self, key: str) -> bool:
        """Checks if a key exists in Redis."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False

    # -------------------------
    # XP Cache
    # -------------------------

    async def get_xp_data(self, guild_id: int, user_id: int) -> Optional[dict]:
        """Returns cached XP data for a user."""
        return await self.get(f"xp:{guild_id}:{user_id}")

    async def set_xp_data(self, guild_id: int, user_id: int, data: dict) -> None:
        """Caches XP data for a user. TTL: 10 minutes."""
        await self.set(f"xp:{guild_id}:{user_id}", data, ttl=600)

    async def delete_xp_data(self, guild_id: int, user_id: int) -> None:
        """Drops a single user's cached XP (used after a prestige reset)."""
        await self.delete(f"xp:{guild_id}:{user_id}")

    async def clear_guild_xp(self, guild_id: int) -> None:
        """Drops all cached XP for a guild (used after a season reset)."""
        try:
            pattern = f"xp:{guild_id}:*"
            keys = [key async for key in self.redis.scan_iter(match=pattern)]
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear_guild_xp error: {e}")

    async def get_dirty_xp_keys(self, guild_id: int) -> list:
        """Returns all dirty XP keys for a guild (marked for DB flush)."""
        try:
            return await self.redis.smembers(f"xp_dirty:{guild_id}")
        except Exception as e:
            logger.error(f"Redis dirty XP keys error: {e}")
            return []

    async def mark_xp_dirty(self, guild_id: int, user_id: int) -> None:
        """Marks a user's XP as needing DB flush. TTL: 5 minutes."""
        try:
            key = f"xp_dirty:{guild_id}"
            await self.redis.sadd(key, str(user_id))
            await self.redis.expire(key, 300)
        except Exception as e:
            logger.error(f"Redis mark_xp_dirty error: {e}")

    async def clear_dirty_xp(self, guild_id: int) -> None:
        """Clears the dirty XP set for a guild after flush."""
        await self.delete(f"xp_dirty:{guild_id}")

    # -------------------------
    # XP Cooldowns
    # -------------------------

    async def check_xp_cooldown(self, guild_id: int, user_id: int) -> Optional[bool]:
        """
        Returns True if the user is on XP cooldown (sent a message < 60s ago),
        False if not (and the cooldown was just set), or **None if Redis
        couldn't answer**. Uses Redis SET NX with TTL for an atomic
        check-and-set.

        The None case matters: returning False on error used to mean "not on
        cooldown", so every message during a Redis blip granted XP with no
        cooldown at all — unbounded XP farming. None lets the caller fall back
        to the in-memory cooldown instead.
        """
        try:
            key = f"xp_cooldown:{guild_id}:{user_id}"
            result = await self.redis.set(key, "1", nx=True, ex=60)
            return result is None  # None = key existed = on cooldown
        except Exception as e:
            logger.error(f"Redis XP cooldown error: {e}")
            return None

    # -------------------------
    # AutoMod message log
    # -------------------------

    async def log_message(self, guild_id: int, user_id: int, window: int = 3) -> int:
        """
        Records a message timestamp for spam detection.
        Returns count of messages in the last `window` seconds.
        Uses Redis sorted set with timestamp as score.
        """
        try:
            window = max(1, int(window))
            key = f"msg_log:{guild_id}:{user_id}"
            now = asyncio.get_event_loop().time()
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)  # remove entries older than the window
            pipe.zadd(key, {str(uuid.uuid4()): now})     # add current message
            pipe.zcard(key)                               # count messages in window
            pipe.expire(key, window + 7)                  # auto-cleanup shortly after window
            results = await pipe.execute()
            return results[2]  # zcard result
        except Exception as e:
            logger.error(f"Redis log_message error: {e}")
            return 0

    async def clear_message_log(self, guild_id: int, user_id: int) -> None:
        """Clears message log for a user after mute."""
        await self.delete(f"msg_log:{guild_id}:{user_id}")

    # -------------------------
    # Filter pattern cache
    # -------------------------

    async def get_filter_pattern(self, guild_id: int) -> Optional[str]:
        """Returns cached regex pattern for guild word filter."""
        return await self.get(f"filter_pattern:{guild_id}")

    async def set_filter_pattern(self, guild_id: int, pattern: str) -> None:
        """Caches compiled regex pattern string for guild word filter. TTL: 1 hour."""
        await self.set(f"filter_pattern:{guild_id}", pattern, ttl=3600)

    async def invalidate_filter_pattern(self, guild_id: int) -> None:
        """Invalidates filter pattern cache when word list changes."""
        await self.delete(f"filter_pattern:{guild_id}")

    # -------------------------
    # RPC via Redis Streams
    # -------------------------

    async def rpc_request(self, channel: str, payload: dict, timeout: float = 12.0) -> Optional[dict]:
        """
        Sends an RPC request via a Redis Stream and waits for the response with a
        blocking pop (BLPOP) rather than a GET poll loop — the bot RPUSHes the
        response, so this returns the moment it's ready, in one round-trip instead
        of polling every 300ms. Streams stay resilient to Upstash idle disconnects.
        """
        request_id = str(uuid.uuid4())
        response_key = f"rpc:response:{request_id}"

        payload["request_id"] = request_id
        payload["response_key"] = response_key

        try:
            await self.redis.xadd(channel, {"data": json.dumps(payload, default=_json_default)}, maxlen=1000)
        except Exception as e:
            logger.error(f"Redis XADD error: {e}")
            return None

        # Block until the bot pushes the response (or we hit the timeout). BLPOP
        # returns (key, value); the bot sets a TTL on the key so a timed-out
        # request can't leak a list.
        try:
            result = await self.redis.blpop(response_key, timeout=timeout)
        except Exception as e:
            logger.warning(f"Redis BLPOP error: {e}")
            return None

        if not result:
            logger.warning(f"RPC timeout for request {request_id}")
            return None
        try:
            return json.loads(result[1])
        except Exception as e:
            logger.exception(f"RPC response decode error for {request_id}: {e}")
            return None

    async def start_rpc_listener(self, channel: str, handler) -> None:
        """
        Starts a Stream consumer that polls for RPC requests.
        Uses XREAD with short blocking intervals instead of Pub/Sub listen(),
        making it resilient to Upstash connection drops.

        Each request is dispatched to its own task (bounded by a semaphore) so a
        single slow handler can't block every other request queued behind it —
        which otherwise cascades into BLPOP timeouts on the API side.
        """
        logger.info(f"Redis Stream RPC listener started on channel '{channel}'")
        last_id = "$"  # Start from new messages only
        sem = asyncio.Semaphore(12)  # cap concurrent handlers (DB pool max is 10)
        inflight: set = set()

        async def handle_one(payload: dict):
            request_id = payload.get("request_id")
            response_key = payload.get("response_key")
            if not request_id or not response_key:
                return
            async with sem:
                try:
                    response = await handler(payload)
                    # Push the response onto a short-lived list that the caller is
                    # BLPOP-ing, so it's delivered immediately.
                    encoded = json.dumps(response, default=_json_default)
                    # One pipeline: a crash between the push and the expire used
                    # to leave the response list without a TTL, so a caller that
                    # had already timed out leaked a key forever.
                    pipe = self.redis.pipeline()
                    pipe.rpush(response_key, encoded)
                    pipe.expire(response_key, 15)
                    await pipe.execute()
                except Exception as e:
                    logger.error(f"RPC handler error: {e}", exc_info=True)

        def spawn(payload: dict):
            # Keep a reference until done so the task isn't GC'd mid-flight.
            task = asyncio.create_task(handle_one(payload))
            inflight.add(task)
            task.add_done_callback(inflight.discard)

        async def listen():
            nonlocal last_id
            while True:
                try:
                    # Short block (2s) instead of infinite listen() - survives disconnects
                    result = await self.redis.xread(
                        {channel: last_id}, count=10, block=2000
                    )
                    if not result:
                        continue

                    for stream_name, messages in result:
                        for message_id, fields in messages:
                            last_id = message_id
                            try:
                                payload = json.loads(fields.get("data", "{}"))
                            except Exception as e:
                                logger.exception(f"RPC payload decode error: {e}")
                                continue
                            spawn(payload)

                except Exception as e:
                    logger.warning(f"Stream read error (reconnecting): {e}")
                    await asyncio.sleep(1)

        asyncio.create_task(listen())

    async def trim_rpc_stream(self, channel: str, maxlen: int = 1000) -> None:
        """Trims the RPC stream to prevent unbounded growth."""
        try:
            await self.redis.xtrim(channel, maxlen=maxlen, approximate=True)
        except Exception as e:
            logger.error(f"Stream trim error: {e}")
