"""Tests for _redact_url() in core/redis_manager.py — credentials must never be
logged when a Redis connection fails."""
import pytest

pytest.importorskip("redis")  # core.redis_manager imports redis.asyncio at module load
from core.redis_manager import _redact_url  # noqa: E402


def test_redacts_upstash_style_credentials():
    out = _redact_url("rediss://default:supersecret@fly-upstash.upstash.io:6379")
    assert "supersecret" not in out
    assert "default" not in out
    assert "fly-upstash.upstash.io:6379" in out
    assert out.startswith("rediss://")


def test_redacts_password_only():
    out = _redact_url("redis://:p4ssw0rd@host:6380")
    assert "p4ssw0rd" not in out
    assert "host:6380" in out


def test_passes_through_url_without_credentials():
    url = "redis://localhost:6379"
    assert _redact_url(url) == url


def test_never_raises_on_garbage():
    # Whatever happens, the function must return a string and not leak/raise.
    assert isinstance(_redact_url("not a url"), str)
