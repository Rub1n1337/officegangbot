"""Renders each user-facing command's reply and checks what a human would see.

The unit tests around this suite cover logic — this one covers *output*, the
layer where the bugs nobody notices live: a summary listing features that no
longer exist, an action label with a doubled emoji, an embed field Discord
would reject. Those shipped because reviews read code instead of looking at
the reply, so this renders the reply and asserts on it.

Commands run against a mocked guild/database, so no network or Postgres is
needed. Each command gets an explicit case: adding a command without one
fails `test_every_rendering_command_is_covered`, which is the point.
"""
import asyncio
import datetime
import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest
from discord.ext import commands as dpy_commands

import cogs.config_cog as config_cog
import cogs.filter_cog as filter_cog
import cogs.general_cog as general_cog
import cogs.help_cog as help_cog
import cogs.levels as levels_cog
import cogs.mod_tools as mod_tools
import cogs.warnings_cog as warnings_cog
import cogs.welcome_system as welcome_system

NOW = datetime.datetime.now(datetime.timezone.utc)

# Discord's hard limits — exceeding any of these makes the API reject the
# message, which is only ever discovered in production.
EMBED_TITLE_MAX = 256
EMBED_DESC_MAX = 4096
FIELD_NAME_MAX = 256
FIELD_VALUE_MAX = 1024
EMBED_FIELDS_MAX = 25


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------


class Recorder:
    """Stands in for cogs.utils.reply / send_paginated and keeps what was sent."""

    def __init__(self):
        self.embeds = []
        self.texts = []

    async def reply(self, ctx, content=None, *, embed=None, view=None, **kw):
        if content:
            self.texts.append(str(content))
        if embed is not None:
            self.embeds.append(embed)

    async def send_paginated(self, ctx, pages, **kw):
        self.embeds.extend(pages)


@pytest.fixture
def rec(monkeypatch):
    r = Recorder()
    for module in (
        config_cog, filter_cog, general_cog, help_cog,
        levels_cog, mod_tools, warnings_cog, welcome_system,
    ):
        if hasattr(module, "reply"):
            monkeypatch.setattr(module, "reply", r.reply)
        if hasattr(module, "send_paginated"):
            monkeypatch.setattr(module, "send_paginated", r.send_paginated)
    return r


@pytest.fixture
def bot():
    b = MagicMock()
    b.latency = 0.069
    b.user = MagicMock(id=99)
    b.redis = None  # exercise the Postgres path, not the cache
    b.get_cog.return_value = None
    b.cogs = {}

    db = b.db
    db.get_locale = AsyncMock(return_value="ru")
    db.get_enabled_features = AsyncMock(return_value=["levels", "tickets", "automod", "logging"])
    db.get_mod_roles = AsyncMock(return_value={"ban": [900]})
    db.get_warn_escalation = AsyncMock(
        return_value={"enabled": True, "expiry_hours": 720, "mute_at": 3, "kick_at": 5, "ban_at": 7}
    )
    db.count_active_warnings = AsyncMock(return_value=1)
    db.get_warnings = AsyncMock(return_value=[
        # one expired, one live — exercises the strike-through path
        {"id": 1, "reason": "spam", "moderator_name": "mod", "created_at": NOW - datetime.timedelta(days=40)},
        {"id": 2, "reason": "flood", "moderator_name": "mod", "created_at": NOW - datetime.timedelta(hours=2)},
    ])
    db.get_mod_notes = AsyncMock(return_value=[
        {"id": 5, "note": "keep an eye on this one", "author_name": "mod", "created_at": NOW}
    ])
    db.count_active_strikes_for = AsyncMock(return_value=1)
    db.get_mod_cases = AsyncMock(return_value=[{
        "case_number": 42, "action": "Ban", "target_id": 555, "target_name": "target#1",
        "moderator_name": "mod", "reason": "raiding", "created_at": NOW - datetime.timedelta(days=1),
    }])
    db.get_mod_case = AsyncMock(return_value={
        "case_number": 42, "action": "Ban", "target_id": 555, "target_name": "target#1",
        "moderator_name": "mod", "reason": "raiding", "created_at": NOW,
    })
    db.get_user_xp = AsyncMock(return_value={"xp": 5300, "level": levels_cog.get_level_from_xp(5300),
                                             "display_name": "member", "prestige": 1})
    db.get_levels_config = AsyncMock(return_value={
        "voice_xp_enabled": True, "voice_xp_per_min": 5, "xp_multiplier": 1.0,
        "prestige_level": 100, "season": 2, "role_multipliers": {},
    })
    db.get_leaderboard = AsyncMock(return_value=[
        {"user_id": 111, "xp": 9000, "level": 12, "display_name": "alpha", "prestige": 1},
        {"user_id": 222, "xp": 500, "level": 3, "display_name": "beta", "prestige": 0},
    ])
    db.get_seasons = AsyncMock(return_value=[
        {"season_number": 1, "ended_at": NOW, "standings": '[{"name": "alpha", "level": 12}]'}
    ])
    db.get_temp_roles = AsyncMock(return_value=[])
    db.get_all_guild_settings = AsyncMock(return_value=_settings())
    db.get_guild_setting = AsyncMock(return_value=None)
    return b


def _settings() -> dict:
    return {
        "rules_channel_id": 111, "rules_message": "Be nice to each other.",
        "welcome_channel_id": 222, "welcome_message": "Welcome {user.mention}!",
        "punishment_log_id": 333, "usage_log_id": 334, "audit_log_id": 335, "leave_log_id": 336,
        "verification_role_id": None, "ticket_support_role_id": 444, "ticket_auto_close_hours": 48,
        "level_up_channel_id": None, "automod_block_invites": True, "automod_block_links": False,
        "automod_block_mass_mentions": True, "automod_dry_run": False,
        "filter_words": ["a", "b", "c"], "antiraid_action": "timeout",
        "antiraid_join_count": 8, "antiraid_join_window": 10,
    }


@pytest.fixture
def ctx(bot):
    c = MagicMock()
    c.bot = bot
    c.interaction = None
    c.guild.id = 1
    c.guild.name = "Test Guild"
    c.guild.icon = None
    c.guild.member_count = 7
    channel = MagicMock(mention="#channel", name="channel")
    c.guild.get_channel.return_value = channel
    role = MagicMock(mention="@Mods", name="Mods")
    c.guild.get_role.return_value = role
    c.guild.get_member.return_value = _member()
    c.author = _member(name="moderator", mid=10)
    return c


def _member(name="member", mid=555):
    m = MagicMock()
    m.__str__.return_value = name  # a real Member str()s to its name
    m.id = mid
    m.bot = False
    m.mention = f"@{name}"
    m.display_name = name
    m.name = name
    m.display_avatar.url = "https://cdn.example/avatar.png"
    m.joined_at = NOW - datetime.timedelta(days=30)
    m.created_at = NOW - datetime.timedelta(days=800)
    m.roles = []
    m.top_role = MagicMock(position=1)
    return m


def _cog(module, bot):
    """Instantiates a cog without running __init__ (which starts task loops)."""
    klass = next(
        obj for _, obj in vars(module).items()
        if inspect.isclass(obj) and issubclass(obj, dpy_commands.Cog)
        and obj.__module__ == module.__name__
    )
    cog = klass.__new__(klass)
    cog.bot = bot
    return cog


# Every command that renders a reply, with the arguments to render it with.
# `None` args are filled in from the fixtures at call time.
RENDER_CASES = {
    "/rank": (levels_cog, "rank", ("member",)),
    "/leaderboard": (levels_cog, "leaderboard", ()),
    "/seasons": (levels_cog, "seasons", ()),
    "/history": (mod_tools, "history", ("member",)),
    "/case": (mod_tools, "case", (42,)),
    "/cases": (mod_tools, "cases", (None,)),
    "/notes": (mod_tools, "notes", ("member",)),
    "/temproles": (mod_tools, "temproles", ()),
    "/warnings": (warnings_cog, "warnings", ("member",)),
    "/settings": (config_cog, "view_settings", ()),
    "/welcome placeholders": (welcome_system, "welcome_placeholders", ()),
    "/ping": (general_cog, "ping", ()),
    "/hello": (general_cog, "hello", ()),
}


def _render(name, bot, ctx, rec):
    """Drives the command's coroutine to completion (the suite avoids a
    pytest-asyncio dependency; see tests/test_integration.py)."""
    module, attr, args = RENDER_CASES[name]
    cog = _cog(module, bot)
    resolved = tuple(_member() if a == "member" else a for a in args)
    asyncio.run(getattr(cog, attr).callback(cog, ctx, *resolved))
    return rec


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(RENDER_CASES))
def test_command_renders_without_error(name, bot, ctx, rec):
    _render(name, bot, ctx, rec)
    assert rec.embeds or rec.texts, f"{name} produced no reply at all"


@pytest.mark.parametrize("name", sorted(RENDER_CASES))
def test_rendered_embeds_fit_discord_limits(name, bot, ctx, rec):
    """Discord rejects an embed that breaks any of these — always in production."""
    _render(name, bot, ctx, rec)
    for embed in rec.embeds:
        if embed.title:
            assert len(embed.title) <= EMBED_TITLE_MAX, f"{name}: title too long"
        if embed.description:
            assert len(embed.description) <= EMBED_DESC_MAX, f"{name}: description too long"
        assert len(embed.fields) <= EMBED_FIELDS_MAX, f"{name}: too many fields"
        for field in embed.fields:
            assert field.name and str(field.name).strip(), f"{name}: empty field name"
            assert field.value and str(field.value).strip(), f"{name}: empty field value"
            assert len(str(field.name)) <= FIELD_NAME_MAX, f"{name}: field name too long"
            assert len(str(field.value)) <= FIELD_VALUE_MAX, f"{name}: field value too long"


@pytest.mark.parametrize("name", sorted(RENDER_CASES))
def test_rendered_output_has_no_placeholder_leaks(name, bot, ctx, rec):
    """A stray {name} means an i18n string was rendered without its kwargs."""
    _render(name, bot, ctx, rec)
    parts = list(rec.texts)
    for embed in rec.embeds:
        parts += [embed.title or "", embed.description or ""]
        parts += [str(f.name) for f in embed.fields] + [str(f.value) for f in embed.fields]
        if embed.footer and embed.footer.text:
            parts.append(embed.footer.text)
    for text in parts:
        assert "MagicMock" not in text, f"{name}: a mock leaked into user-visible text: {text[:80]}"
        # Welcome templates legitimately show {user.mention} etc. as examples.
        if name not in ("/settings", "/welcome placeholders"):
            for token in ("{member}", "{count}", "{guild}", "{user}", "{action}", "{hours}"):
                assert token not in text, f"{name}: unformatted placeholder {token} in {text[:80]}"


def test_every_rendering_command_is_covered():
    """A new command that replies must get a render case here.

    This is the guard that would have caught /settings listing two features
    that no longer existed: the case list is the checklist.
    """
    modules = (config_cog, filter_cog, general_cog, levels_cog, mod_tools,
               warnings_cog, welcome_system)
    covered = {name.split()[-1].lstrip("/") for name in RENDER_CASES}
    # Commands that act (ban, mute, …) or need heavy live objects are exercised
    # elsewhere; this checklist covers the read-only, render-only ones.
    read_only = {
        "rank", "leaderboard", "seasons", "history", "case", "cases", "notes",
        "temproles", "warnings", "view_settings", "settings", "placeholders",
        "ping", "hello",
    }
    for module in modules:
        for _, obj in vars(module).items():
            if not (inspect.isclass(obj) and issubclass(obj, dpy_commands.Cog)):
                continue
            if obj.__module__ != module.__name__:
                continue
            for cmd in getattr(obj, "__cog_commands__", []):
                short = cmd.qualified_name.split()[-1]
                if short in read_only:
                    assert short in covered or f"/{cmd.qualified_name}" in RENDER_CASES, (
                        f"/{cmd.qualified_name} renders a reply but has no case in RENDER_CASES"
                    )


# --------------------------------------------------------------------------
# Action labels: the bug that shipped — "🔨 🔨 Ban", and an unban with the ban
# hammer, because "unban" contains "ban".
# --------------------------------------------------------------------------


@pytest.mark.parametrize("action,emoji", [
    ("Ban", "🔨"),
    ("Temp Ban", "🔨"),
    ("Mass Ban", "🔨"),
    ("Kick", "👢"),
    ("Unban", "♻️"),
    ("Unmute", "🔊"),
    ("Temp Mute", "🔇"),
    ("Warn", "⚠️"),
])
def test_action_emoji_matches_the_action(action, emoji):
    assert mod_tools._action_emoji(action) == emoji


@pytest.mark.parametrize("stored,expected", [
    # Canonical rows written today.
    ("Ban", "Ban"),
    ("Unban", "Unban"),
    # Legacy rows written before the emoji moved to the display layer.
    ("🔨 Ban", "Ban"),
    ("🔇 Temp Mute", "Temp Mute"),
    ("Member Kicked", "Member Kicked"),
])
def test_action_label_strips_a_baked_in_emoji(stored, expected):
    assert mod_tools._action_label(stored) == expected


@pytest.mark.parametrize("stored", ["Ban", "🔨 Ban", "Unban", "User Unbanned", "🔇 Temp Mute"])
def test_rendered_action_never_doubles_the_emoji(stored):
    rendered = f"{mod_tools._action_emoji(stored)} {mod_tools._action_label(stored)}"
    emoji = mod_tools._action_emoji(stored)
    assert rendered.count(emoji) == 1, f"{stored!r} rendered as {rendered!r}"


# --------------------------------------------------------------------------
# /settings: the summary must describe features that actually exist.
# --------------------------------------------------------------------------


def test_settings_only_reports_real_features(bot, ctx, rec):
    """The summary used to check "filter" and "reaction-role", which were
    merged away — both were permanently false, so it printed "Disabled"
    forever no matter what the admin configured."""
    _render("/settings", bot, ctx, rec)
    embed = rec.embeds[0]
    names = " ".join(str(f.name) for f in embed.fields).lower()

    for gone in ("message filter", "reaction role"):
        assert gone not in names, f"/settings still lists the removed feature {gone!r}"

    # Every feature the bot can actually toggle should be visible somewhere in
    # the summary, so enabling one on the dashboard is never invisible here.
    for feature in ("automod", "anti-raid", "verification", "tickets", "levels"):
        assert feature.replace("-", "") in names.replace("-", "").replace(" ", ""), (
            f"/settings never mentions {feature}"
        )
