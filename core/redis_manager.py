# core/redis_manager.py
"""
Async Redis manager using redis.asyncio connection pool.
Handles caching (XP, cooldowns, filter patterns, automod)
and RPC communication between bot and API server via Pub/Sub.
"""

import redis.asyncio as aioredis
import os
import json
import asyncio
import uuid
from typing import Any, Optional
from core.logger import logger


class RedisManager:
    """
    Async Redis manager with connection pool.
    Initialize via connect(), close via close().
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None

    async def connect(self) -> None:
        """Creates Redis connection pool. Call in bot.setup_hook() and api_server startup."""
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self._redis = await aioredis.from_url(
                url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
            await self._redis.ping()
            logger.info("Redis connection established successfully.")
        except Exception as e:
            logger.critical(f"Failed to connect to Redis: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """Closes the Redis connection."""
        if self._redis:
            await self._redis.aclose()
            logger.info("Redis connection closed.")

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
            encoded = json.dumps(value)
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

    async def check_xp_cooldown(self, guild_id: int, user_id: int) -> bool:
        """
        Returns True if user is on XP cooldown (sent message < 60s ago).
        Uses Redis SET NX with TTL for atomic cooldown check.
        """
        try:
            key = f"xp_cooldown:{guild_id}:{user_id}"
            result = await self.redis.set(key, "1", nx=True, ex=60)
            return result is None  # None = key existed = on cooldown
        except Exception as e:
            logger.error(f"Redis XP cooldown error: {e}")
            return False

    # -------------------------
    # AutoMod message log
    # -------------------------

    async def log_message(self, guild_id: int, user_id: int) -> int:
        """
        Records a message timestamp for spam detection.
        Returns count of messages in the last 3 seconds.
        Uses Redis sorted set with timestamp as score.
        """
        try:
            key = f"msg_log:{guild_id}:{user_id}"
            now = asyncio.get_event_loop().time()
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - 3)   # remove entries older than 3s
            pipe.zadd(key, {str(uuid.uuid4()): now})  # add current message
            pipe.zcard(key)                            # count messages in window
            pipe.expire(key, 10)                       # auto-cleanup after 10s
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
    # RPC via Pub/Sub
    # -------------------------

    async def publish(self, channel: str, message: dict) -> None:
        """Publishes a message to a Redis channel."""
        try:
            await self.redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Redis PUBLISH error on channel '{channel}': {e}")

    async def rpc_request(self, channel: str, payload: dict, timeout: float = 5.0) -> Optional[dict]:
        """
        Sends an RPC request and waits for a response via Redis Pub/Sub.
        Returns the response dict or None on timeout.

        Usage (from API server):
            result = await redis.rpc_request("bot:rpc", {"action": "get_guild_info", "guild_id": 123})
        """
        request_id = str(uuid.uuid4())
        response_channel = f"rpc:response:{request_id}"

        # Subscribe to response channel before publishing request
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(response_channel)

        try:
            payload["request_id"] = request_id
            payload["response_channel"] = response_channel
            await self.publish(channel, payload)

            # Wait for response with timeout
            deadline = asyncio.get_event_loop().time() + timeout
            async for message in pubsub.listen():
                if asyncio.get_event_loop().time() > deadline:
                    logger.warning(f"RPC timeout for request {request_id}")
                    return None
                if message["type"] == "message":
                    try:
                        return json.loads(message["data"])
                    except json.JSONDecodeError:
                        return None
            return None
        except asyncio.TimeoutError:
            logger.warning(f"RPC timeout for request {request_id}")
            return None
        finally:
            await pubsub.unsubscribe(response_channel)
            await pubsub.aclose()

    async def start_rpc_listener(self, channel: str, handler) -> None:
        """
        Starts listening for RPC requests with auto-reconnect.
        Handles Upstash idle connection timeouts gracefully.
        """
        logger.info(f"Redis RPC listener started on channel '{channel}'")

        async def listen():
            while True:
                pubsub = None
                try:
                    pubsub = self.redis.pubsub()
                    await pubsub.subscribe(channel)

                    async for message in pubsub.listen():
                        if message["type"] != "message":
                            continue
                        try:
                            payload = json.loads(message["data"])
                            request_id = payload.get("request_id")
                            response_channel = payload.get("response_channel")

                            if not request_id or not response_channel:
                                continue

                            result = await handler(payload)
                            await self.publish(response_channel, {
                                "request_id": request_id,
                                "data": result
                            })
                        except Exception as e:
                            logger.error(f"RPC handler error: {e}", exc_info=True)

                except Exception as e:
                    logger.warning(f"RPC listener disconnected ({e}), reconnecting in 3s...")
                    await asyncio.sleep(3)
                finally:
                    if pubsub:
                        try:
                            await pubsub.aclose()
                        except Exception:
                            pass

        asyncio.create_task(listen())
