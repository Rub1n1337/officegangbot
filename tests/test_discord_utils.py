"""Tests for core/discord_utils: safe_send and themed_embed."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from core.discord_utils import safe_send, themed_embed


def test_safe_send_returns_message_on_success():
    target = AsyncMock()
    sentinel = object()
    target.send.return_value = sentinel
    assert asyncio.run(safe_send(target, "hi", delete_after=5)) is sentinel
    target.send.assert_awaited_once_with("hi", delete_after=5)


def test_safe_send_swallows_forbidden():
    target = AsyncMock()
    resp = SimpleNamespace(status=403, reason="Forbidden")
    target.send.side_effect = discord.Forbidden(resp, "no perms")
    assert asyncio.run(safe_send(target, "hi")) is None


def test_safe_send_swallows_httpexception():
    target = AsyncMock()
    resp = SimpleNamespace(status=500, reason="Server Error")
    target.send.side_effect = discord.HTTPException(resp, "boom")
    assert asyncio.run(safe_send(target, "hi")) is None


def test_themed_embed_defaults():
    e = themed_embed("Title", "Desc")
    assert e.title == "Title"
    assert e.description == "Desc"
    assert e.color == discord.Color.blurple()
    assert e.timestamp is not None


def test_themed_embed_custom_color_no_timestamp():
    e = themed_embed(color=discord.Color.red(), timestamp=False)
    assert e.color == discord.Color.red()
    assert e.timestamp is None
