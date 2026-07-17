"""Redis-outage fallbacks must be distinguishable from real answers.

Two spam/XP counters used to return a falsy sentinel on a Redis error that read
as a valid answer, silently disabling the feature during a blip:
  - check_xp_cooldown returned False ("not on cooldown") -> XP farming.
  - log_message returned 0 ("no spam") -> anti-spam off.
Both now return None on error so the cog falls back to its in-memory counter.
The suite drives coroutines with asyncio.run (no pytest-asyncio), like
tests/test_integration.py.
"""
import asyncio

from core.redis_manager import RedisManager


class _FakeRedis:
    """Stands in for aioredis; `set` returns a canned value or raises."""

    def __init__(self, result=None, boom=False):
        self._result = result
        self._boom = boom
        self.calls = 0

    async def set(self, *args, **kwargs):
        self.calls += 1
        if self._boom:
            raise ConnectionError("redis down")
        return self._result


def _cooldown(result=None, boom=False):
    mgr = RedisManager()
    mgr._redis = _FakeRedis(result=result, boom=boom)
    return asyncio.run(mgr.check_xp_cooldown(1, 2))


def test_first_message_is_not_on_cooldown():
    # SET NX succeeds -> redis returns "OK" -> key did not exist -> not on cooldown.
    assert _cooldown(result="OK") is False


def test_repeat_message_is_on_cooldown():
    # SET NX fails because the key exists -> redis returns None -> on cooldown.
    assert _cooldown(result=None) is True


def test_redis_error_returns_none_not_false():
    # The bug: this used to return False ("not on cooldown"), so a Redis outage
    # removed the cooldown and let XP be farmed. None tells the cog to fall back.
    assert _cooldown(boom=True) is None


class _FakePipeline:
    """Minimal redis pipeline: chains commands, `execute` returns canned results."""

    def __init__(self, results, boom):
        self._results, self._boom = results, boom

    def zremrangebyscore(self, *a, **k):
        return self

    def zadd(self, *a, **k):
        return self

    def zcard(self, *a, **k):
        return self

    def expire(self, *a, **k):
        return self

    async def execute(self):
        if self._boom:
            raise ConnectionError("redis down")
        return self._results


class _PipeRedis:
    def __init__(self, zcard=0, boom=False):
        # log_message reads results[2] (the zcard), so pad the first two.
        self._results = [0, 1, zcard, True]
        self._boom = boom

    def pipeline(self):
        return _FakePipeline(self._results, self._boom)


def _log_message(zcard=0, boom=False):
    mgr = RedisManager()
    mgr._redis = _PipeRedis(zcard=zcard, boom=boom)
    return asyncio.run(mgr.log_message(1, 2, 3))


def test_log_message_returns_count():
    assert _log_message(zcard=4) == 4


def test_log_message_redis_error_returns_none_not_zero():
    # The mirror bug: returning 0 read as "no spam", so a Redis blip silently
    # switched anti-spam off. None tells AutoMod to fall back to in-memory.
    assert _log_message(boom=True) is None
