# bot.py
# This is the main application file for the Discord Bot. It's the "brain" of the operation.

import os
import datetime
from typing import Optional
from pathlib import Path

# Dependencies are managed via requirements.txt and the virtual environment.

# --- Bot Imports ---
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import uvicorn
from core.logger import logger
from config import load_config
# from core.webserver import keep_alive

from core.health_monitor import HealthMonitor
from core.db_manager import DatabaseManager
from core.redis_manager import RedisManager
from core.moderation_actions import perform_moderation
from core.member_queries import search_guild_members, build_member_profile
from core.reaction_sync import plan_reaction_changes
from core.permissions import role_is_assignable
from api_server import app as fastapi_app, set_bot_instance

# --- Bot Initialization ---

DEFAULT_RULES_TEXT = (
    "> 1. **Be respectful** - You must respect all users, regardless of your liking towards them. Treat others the way you want to be treated.\n"
    "> 2. **No Inappropriate Language** - The use of profanity should be kept to a minimum. However, any derogatory language towards any user is prohibited.\n"
    "> 3. **No Spamming** - Do not send a lot of small messages right after each other. Do not disrupt chat by spamming.\n"
    "> 4. **No NSFW Material** - This is a community server and not meant to share pornographic/adult/other NSFW material.\n"
    "> 5. **No Advertisements** - We do not tolerate any kind of advertisements, whether it be for other communities or streams.\n"
    "> 6. **Follow the Discord Community Guidelines** - You can find them here: https://discordapp.com/guidelines\n\n"
    "> **Your presence in this server implies accepting these rules, including all further changes.**"
)


def _validate_discord_id(value) -> int:
    """Validates and converts a value to a Discord snowflake (positive 64-bit int).
    Raises ValueError on anything else, so callers can return a clean error
    instead of letting a bare int() blow up the RPC handler."""
    try:
        id_int = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid Discord ID: {value}")
    if id_int <= 0:
        raise ValueError(f"Invalid Discord ID: {value}")
    return id_int


class MyBot(commands.Bot):
    """Custom Bot class to handle setup, cogs, and command tree."""
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True

        config = load_config()
        owner_id = config.get('OWNER_ID', 0)

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
            application_id=config.get('APPLICATION_ID', 0),
            owner_id=owner_id
        )

        self.db = None
        self.redis = None

        # Set up the global error handler for slash commands
        self.tree.on_error = self.on_app_command_error

        # Acknowledge every slash interaction early (see _auto_defer) so slow
        # DB work in a command body can't blow Discord's 3-second ACK window.
        self.before_invoke(self._auto_defer)

    async def _auto_defer(self, ctx: commands.Context):
        """Defer the interaction before the command body runs.

        Commands do DB work (e.g. get_enabled_features) before their first
        reply(), and reply() only defers when it is finally called — by then
        the 3s window may have passed, surfacing "The application did not
        respond" even though the command succeeds. Deferring here acks
        immediately. Deferred ephemerally so the hidden "thinking" placeholder
        never leaks content; reply() still controls each followup's visibility.

        Skipped for prefix invocations and for commands that send their own
        initial interaction response (marked extras["manages_own_response"],
        e.g. /ban which shows a confirmation view)."""
        interaction = ctx.interaction
        if interaction is None or interaction.response.is_done():
            return
        if ctx.command and ctx.command.extras.get("manages_own_response"):
            return
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            pass

    async def close(self):
        if hasattr(self, '_uvicorn_server'):
            self._uvicorn_server.should_exit = True
            if hasattr(self, '_api_task'):
                try:
                    await asyncio.wait_for(self._api_task, timeout=5)
                except asyncio.TimeoutError:
                    self._api_task.cancel()
            logger.info("FastAPI server stopped")
        if hasattr(self, 'health_monitor') and self.health_monitor:
            self.health_monitor.stop()
        if hasattr(self, 'db') and self.db:
            await self.db.close()
        if hasattr(self, 'redis') and self.redis:
            await self.redis.close()
        await super().close()

    async def setup_hook(self):
        """This is called once when the bot logs in, to load cogs."""
        # Initialize database
        self.db = DatabaseManager()
        try:
            await self.db.connect()
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}")
            # Bot continues with JSON fallback if DB is unavailable
            self.db = None

        # Initialize Redis
        self.redis = RedisManager()
        try:
            await self.redis.connect()
            # Start RPC listener for API server requests
            await self.redis.start_rpc_listener("bot:rpc", self._handle_rpc_request)
            logger.info("Redis RPC listener started.")
        except Exception as e:
            logger.warning(f"Redis unavailable, continuing without it: {e}")
            self.redis = None

        # Start FastAPI server as a background task within the same process
        port = int(os.getenv("PORT", 8080))
        config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            loop="asyncio"
        )
        self._uvicorn_server = uvicorn.Server(config)
        self._api_task = asyncio.create_task(self._uvicorn_server.serve())
        logger.info(f"FastAPI server starting on port {port} (embedded in bot process)")

        # Start background health monitor (logs latency/guilds/memory periodically)
        self.health_monitor = HealthMonitor(self)
        self.health_monitor.start()
        logger.info("Health monitor started.")

        logger.info("--- Loading Cogs ---")
        cogs_dir = Path(__file__).parent / "cogs"
        # testing_cog (owner-only /testall, which invokes every command) is a
        # dev tool; never load it in production. Set LOAD_TESTING_COG=1 locally
        # to enable it.
        skip_cogs = {"utils.py"}
        if os.getenv("LOAD_TESTING_COG") != "1":
            skip_cogs.add("testing_cog.py")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__") and filename not in skip_cogs:
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    logger.info(f"Successfully loaded cog: {cog_name}")
                except Exception as e:
                    logger.error(f"Failed to load cog: {cog_name}", exc_info=e)
        logger.info("--- Cogs Loaded ---")

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the server"))
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')

        # Perform an initial sync to ensure commands are registered with Discord.
        # This is crucial for the first run or after commands have been cleared.
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} commands on startup.")
        except Exception as e:
            logger.error("Failed to sync commands on startup.", exc_info=e)

        logger.info('Bot is ready and listening for commands.')
        logger.warning("Manual command syncing via /sync is now the primary method.")

    @staticmethod
    def _snowflake_or_none(value) -> Optional[str]:
        return str(value) if value else None

    def _unassignable_roles(self, guild, role_ids):
        """Of the given role ids, return [(id, label)] for roles the bot cannot
        grant: unknown/deleted, managed, or at/above the bot's top role. Used to
        reject auto-grant configs (autorole, level/reaction roles) at save time
        instead of letting them silently fail later."""
        if not guild or not guild.me:
            return []
        bot_top = guild.me.top_role.position
        bad = []
        for rid in role_ids:
            try:
                rid_int = int(rid)
            except (TypeError, ValueError):
                continue
            role = guild.get_role(rid_int)
            if role is None:
                bad.append((rid_int, f"`{rid_int}`"))
            elif not role_is_assignable(
                role_managed=role.managed, role_position=role.position, bot_top_role_pos=bot_top
            ):
                bad.append((rid_int, f"@{role.name}"))
        return bad

    async def _get_feature_payload(self, guild_id: int, feature: str) -> dict:
        if not self.db:
            return {"error": "Database unavailable"}
        settings = await self.db.get_all_guild_settings(guild_id)
        mod_roles = await self.db.get_mod_roles(guild_id)
        reaction_roles = await self.db.get_reaction_roles(guild_id)
        level_roles = await self.db.get_level_roles(guild_id)
        scheduled = await self.db.get_scheduled_messages(guild_id)

        def _first_role(perm: str):
            ids = mod_roles.get(perm) or []
            return str(ids[0]) if ids else None

        standalone_rr = [
            {
                "channelId": str(r["channel_id"]),
                "messageId": str(r["message_id"]),
                "emoji": r["emoji"],
                "roleId": str(r["role_id"]),
            }
            for r in reaction_roles if r["source"] == "reaction-role"
        ]
        rules_rr = next((r for r in reaction_roles if r["source"] == "rules"), None)

        feature_data = {
            "rules": {
                "channel": self._snowflake_or_none(settings.get("rules_channel_id")),
                "message": settings.get("rules_message") or DEFAULT_RULES_TEXT,
                "reactionEnabled": rules_rr is not None,
                "reactionEmoji": rules_rr["emoji"] if rules_rr else "✅",
                "reactionRole": str(rules_rr["role_id"]) if rules_rr else None,
            },
            "welcome-message": {
                "channel": self._snowflake_or_none(settings.get("welcome_channel_id")),
                "message": str(settings.get("welcome_message") or "Welcome {user.mention} to **{server.name}**!"),
                "autorole": self._snowflake_or_none(settings.get("autorole_id")),
            },
            "reaction-role": {
                "items": standalone_rr,
            },
            "scheduled-messages": {
                "items": [
                    {
                        "channelId": str(s["channel_id"]),
                        "content": s["content"],
                        "scheduledAt": s["scheduled_at"].isoformat() if s["scheduled_at"] else None,
                        "repeat": s["repeat"],
                        "enabled": s["enabled"],
                    }
                    for s in scheduled
                ],
            },
            "moderation": {
                "config": _first_role("config"),
                "kick": _first_role("kick"),
                "ban": _first_role("ban"),
                "mute": _first_role("mute"),
                "warn": _first_role("warn"),
                "clear": _first_role("clear"),
            },
            "logging": {
                "logChannel": self._snowflake_or_none(settings.get("punishment_log_id")),
                "usageChannel": self._snowflake_or_none(settings.get("usage_log_id")),
                "messagesChannel": self._snowflake_or_none(settings.get("audit_log_id")),
                "leaveChannel": self._snowflake_or_none(settings.get("leave_log_id")),
            },
            "filter": {
                "words": settings.get("filter_words") or [],
            },
            "levels": {
                "channel": self._snowflake_or_none(settings.get("level_up_channel_id")),
                "rewards": [
                    {"level": lvl, "roleId": str(rid)}
                    for lvl, rid in sorted(level_roles.items())
                ],
            },
            "tickets": {
                "supportRole": self._snowflake_or_none(settings.get("ticket_support_role_id")),
                "category": self._snowflake_or_none(settings.get("ticket_category_id")),
            },
            "automod": {
                "blockInvites": bool(settings.get("automod_block_invites")),
                "blockLinks": bool(settings.get("automod_block_links")),
                "allowedDomains": list(settings.get("automod_allowed_domains") or []),
            },
        }
        return feature_data.get(feature, {})

    async def _log_dashboard_action(
        self, guild, action: str, target_id: int, moderator_name: str, reason: str, **extra
    ) -> None:
        """Mirror a dashboard moderation action into the guild's punishment-log
        channel, so Discord-side moderators see actions taken from the web too.
        No-ops when logging is off or no log channel is configured."""
        if not self.db:
            return
        try:
            enabled = await self.db.get_enabled_features(guild.id)
            if "logging" not in enabled:
                return
            log_channel_id = await self.db.get_guild_setting(guild.id, "punishment_log_id")
            if not log_channel_id:
                return
            channel = guild.get_channel(int(log_channel_id))
            if not channel:
                return
            embed = discord.Embed(
                title=action, color=discord.Color.orange(), timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Target", value=f"<@{target_id}> (`{target_id}`)", inline=False)
            embed.add_field(name="Moderator", value=f"{moderator_name} (via dashboard)", inline=False)
            embed.add_field(name="Reason", value=f"```{reason}```", inline=False)
            for key, value in extra.items():
                embed.add_field(name=key.replace("_", " ").title(), value=value, inline=True)
            await channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass
        except Exception as e:
            logger.warning(f"Dashboard action log failed for guild {guild.id}: {e}")

    async def _record_audit(self, guild_id: int, payload: dict, action: str, target=None, detail=None) -> None:
        """Record a dashboard action in the audit trail. The actor is derived
        server-side (proxy → headers → payload); best-effort, never raises."""
        if not self.db:
            return
        try:
            actor_id = int(payload.get("actor_id")) if payload.get("actor_id") else None
        except (TypeError, ValueError):
            actor_id = None
        await self.db.add_dashboard_audit(
            guild_id,
            actor_id=actor_id,
            actor_name=payload.get("actor_name"),
            action=action,
            target=target,
            detail=detail,
        )

    async def _handle_rpc_request(self, payload: dict) -> dict:
        """Top-level RPC entrypoint: dispatches and converts any unhandled
        exception into a clean error response, so a handler bug returns an
        immediate error instead of letting the API caller wait out an 8s
        timeout (504)."""
        try:
            return await self._dispatch_rpc(payload)
        except Exception as e:
            logger.error(
                f"Unhandled error in RPC action '{payload.get('action')}': {e}",
                exc_info=True,
            )
            return {"error": "Internal bot error"}

    async def _dispatch_rpc(self, payload: dict) -> dict:
        """Handles RPC requests from the API server via Redis Streams."""
        action = payload.get("action")

        # Validate guild_id once for every action that carries one, so a bad
        # value yields a clean error instead of a 504 from a crashed handler.
        guild_id = None
        if payload.get("guild_id") is not None:
            try:
                guild_id = _validate_discord_id(payload.get("guild_id"))
            except ValueError as e:
                return {"error": str(e)}

        _needs_guild = {
            "get_guild_info", "get_guild_stats", "get_guild_roles", "get_guild_channels",
            "get_guild_emojis", "get_feature", "enable_feature", "disable_feature", "update_feature",
            "get_moderation", "delete_warning", "set_locale",
            "search_members", "get_member", "moderate_member", "get_audit",
        }
        if action in _needs_guild and guild_id is None:
            return {"error": "Missing or invalid guild_id"}

        if action == "get_guild_info":
            guild = self.get_guild(guild_id) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}
            if not self.db:
                return {"error": "Database unavailable"}
            settings = await self.db.get_all_guild_settings(guild_id)
            # Snowflake ids are BIGINTs that exceed JS's safe-integer range, so
            # serialize every *_id as a string — otherwise a JSON consumer (the
            # dashboard, etc.) silently loses precision on the last few digits.
            settings = {
                k: (str(v) if (k.endswith("_id") and isinstance(v, int)) else v)
                for k, v in settings.items()
            }
            enabled_features = await self.db.get_enabled_features(guild_id)
            return {
                "id": str(guild.id),
                "name": guild.name,
                "icon": str(guild.icon) if guild.icon else None,
                "member_count": guild.member_count,
                "owner_id": str(guild.owner_id),
                "locale": settings.get("locale") or "en",
                "settings": settings,
                "enabledFeatures": enabled_features,
            }

        if action == "get_guild_stats":
            guild = self.get_guild(guild_id) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}

            # Channel and role counts come straight from the cached guild object
            # (always available). member_count is reliable; per-member iteration
            # is avoided since the members intent/cache may be incomplete.
            text_channels = sum(1 for ch in guild.channels if isinstance(ch, discord.TextChannel))
            voice_channels = sum(1 for ch in guild.channels if isinstance(ch, discord.VoiceChannel))

            enabled_features = []
            top_xp = []
            if self.db:
                enabled_features = await self.db.get_enabled_features(guild_id)
                try:
                    rows = await self.db.get_leaderboard(guild_id, limit=5)
                    for row in rows:
                        member = guild.get_member(row["user_id"])
                        name = (
                            member.display_name if member
                            else (row.get("display_name") or f"User {row['user_id']}")
                        )
                        top_xp.append({"name": name, "level": row["level"], "xp": row["xp"]})
                except Exception as e:
                    logger.warning(f"get_guild_stats leaderboard failed for {guild_id}: {e}")

            return {
                "id": str(guild.id),
                "name": guild.name,
                "icon": str(guild.icon) if guild.icon else None,
                "online": True,
                "member_count": guild.member_count,
                "channel_count": len(guild.channels),
                "text_channels": text_channels,
                "voice_channels": voice_channels,
                "role_count": len(guild.roles),
                "latency_ms": round(self.latency * 1000, 2),
                "enabled_feature_count": len(enabled_features),
                "top_xp": top_xp,
            }

        if action == "get_stats":
            import psutil
            return {
                "status": "online",
                "guilds": len(self.guilds),
                "total_users": sum(g.member_count for g in self.guilds),
                "latency_ms": round(self.latency * 1000, 2),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_percent": psutil.virtual_memory().percent,
                "ram_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 2),
            }

        if action == "get_guilds":
            return {
                "guilds": [
                    {
                        "id": str(g.id),
                        "name": g.name,
                        "icon": str(g.icon) if g.icon else None,
                        "member_count": g.member_count
                    }
                    for g in self.guilds
                ]
            }

        if action == "get_guild_roles":
            guild = self.get_guild(guild_id) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}
            return [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "color": role.color.value,
                    "position": role.position,
                }
                for role in guild.roles
                if not role.is_default()
            ]

        if action == "get_guild_channels":
            guild = self.get_guild(guild_id) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}
            return [
                {
                    "id": str(ch.id),
                    "name": ch.name,
                    "type": ch.type.value,
                    "category": str(ch.category_id) if ch.category_id else None,
                }
                for ch in guild.channels
            ]

        if action == "get_guild_emojis":
            guild = self.get_guild(guild_id) if guild_id else None
            if not guild:
                return {"error": "Guild not found"}
            return [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "animated": e.animated,
                    "url": str(e.url),
                }
                for e in guild.emojis
            ]

        if action == "get_feature":
            feature = payload.get("feature")
            if not self.db:
                return {"error": "Database unavailable"}
            # Return the settings regardless of enabled state — the dashboard
            # shows the config form (greyed out) for disabled features and reads
            # the enabled flag from the guild info query, not from here.
            return await self._get_feature_payload(guild_id, feature)

        if action == "get_moderation":
            if not self.db:
                return {"error": "Database unavailable"}
            guild = self.get_guild(guild_id)

            def _member_name(uid):
                m = guild.get_member(int(uid)) if guild else None
                return m.display_name if m else f"User {uid}"

            warnings = await self.db.get_recent_warnings(guild_id, 50)
            punishments = await self.db.get_timed_punishments(guild_id)
            leaderboard = await self.db.get_leaderboard(guild_id, 25)
            return {
                "warnings": [
                    {
                        "id": w["id"],
                        "userId": str(w["user_id"]),
                        "userName": _member_name(w["user_id"]),
                        "reason": w["reason"],
                        "moderatorName": w["moderator_name"],
                        "createdAt": w["created_at"].isoformat() if w["created_at"] else None,
                    }
                    for w in warnings
                ],
                "punishments": [
                    {
                        "userId": str(p["user_id"]),
                        "userName": _member_name(p["user_id"]),
                        "type": p["punishment_type"],
                        "reason": p.get("reason"),
                        "expiresAt": p["expires_at"].isoformat() if p["expires_at"] else None,
                    }
                    for p in punishments
                ],
                "leaderboard": [
                    {
                        "userId": str(r["user_id"]),
                        "name": r["display_name"] or _member_name(r["user_id"]),
                        "level": r["level"],
                        "xp": r["xp"],
                    }
                    for r in leaderboard
                ],
            }

        if action == "get_audit":
            if not self.db:
                return {"error": "Database unavailable"}
            entries = await self.db.get_dashboard_audit(guild_id, 50)
            return {
                "entries": [
                    {
                        "id": e["id"],
                        "actorId": str(e["actor_id"]) if e["actor_id"] else None,
                        "actorName": e["actor_name"],
                        "action": e["action"],
                        "target": e["target"],
                        "detail": e["detail"],
                        "createdAt": e["created_at"].isoformat() if e["created_at"] else None,
                    }
                    for e in entries
                ]
            }

        if action == "delete_warning":
            if not self.db:
                return {"error": "Database unavailable"}
            try:
                warning_id = int(payload.get("warning_id"))
            except (TypeError, ValueError):
                return {"error": "Invalid warning id"}
            removed = await self.db.delete_warning(guild_id, warning_id)
            if removed:
                await self._record_audit(guild_id, payload, "delete_warning", target=str(warning_id))
            return {"success": removed}

        if action == "set_locale":
            if not self.db:
                return {"error": "Database unavailable"}
            locale = payload.get("locale")
            if locale not in ("en", "ru"):
                return {"error": "Unsupported locale"}
            await self.db.set_locale(guild_id, locale)
            await self._record_audit(guild_id, payload, "set_locale", detail=locale)
            return {"success": True, "locale": locale}

        if action == "search_members":
            guild = self.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}
            return search_guild_members(guild, payload.get("query"))

        if action == "get_member":
            if not self.db:
                return {"error": "Database unavailable"}
            try:
                user_id = _validate_discord_id(payload.get("user_id"))
            except ValueError:
                return {"error": "Invalid user id"}
            guild = self.get_guild(guild_id)
            return await build_member_profile(guild, self.db, guild_id, user_id)

        if action == "moderate_member":
            if not self.db:
                return {"error": "Database unavailable"}
            try:
                user_id = _validate_discord_id(payload.get("user_id"))
            except ValueError:
                return {"error": "Invalid user id"}
            guild = self.get_guild(guild_id)
            if not guild:
                return {"error": "Guild not found"}
            try:
                mod_id = int(payload.get("moderator_id")) if payload.get("moderator_id") else 0
            except (TypeError, ValueError):
                mod_id = 0
            result = await perform_moderation(
                db=self.db,
                guild=guild,
                bot_user_id=self.user.id,
                user_id=user_id,
                act=payload.get("act"),
                reason=payload.get("reason"),
                mod_name=payload.get("moderator_name"),
                mod_id=mod_id,
                duration_minutes=payload.get("duration_minutes"),
                log_action=self._log_dashboard_action,
            )
            if isinstance(result, dict) and result.get("success"):
                await self._record_audit(
                    guild_id,
                    {"actor_id": payload.get("moderator_id"), "actor_name": payload.get("moderator_name")},
                    payload.get("act") or "moderate",
                    target=str(user_id),
                    detail=payload.get("reason"),
                )
            return result

        if action == "enable_feature":
            feature = payload.get("feature")
            if not self.db:
                return {"error": "Database unavailable"}
            await self.db.set_feature_enabled(guild_id, feature, True)
            enabled_features = await self.db.get_enabled_features(guild_id)
            await self._record_audit(guild_id, payload, "enable_feature", target=feature)
            return {"success": True, "enabled_features": enabled_features}

        if action == "disable_feature":
            feature = payload.get("feature")
            if not self.db:
                return {"error": "Database unavailable"}
            await self.db.set_feature_enabled(guild_id, feature, False)
            enabled_features = await self.db.get_enabled_features(guild_id)
            await self._record_audit(guild_id, payload, "disable_feature", target=feature)
            return {"success": True, "enabled_features": enabled_features}

        if action == "update_feature":
            feature = payload.get("feature")
            options = payload.get("options", {})
            if not self.db:
                return {"error": "Database unavailable"}
            await self._record_audit(guild_id, payload, "update_feature", target=feature)

            # Moderation permission roles live in the mod_roles table, not in
            # guilds columns, so they are handled separately from the column
            # mapping below. Each level holds one role from the dashboard;
            # setting a role replaces that level (matches /config role).
            if feature == "moderation":
                for perm in ("config", "kick", "ban", "mute", "warn", "clear"):
                    if perm not in options:
                        continue
                    await self.db.remove_mod_role(guild_id, perm)
                    raw = options.get(perm)
                    if raw:
                        try:
                            role_id = _validate_discord_id(raw)
                        except ValueError:
                            return {"error": f"Invalid role id for {perm}: {raw}"}
                        await self.db.set_mod_role(guild_id, role_id, perm)
                return await self._get_feature_payload(guild_id, feature)

            # Level role rewards live in the level_roles table (one role per
            # level), not in guilds columns, so they are reconciled separately:
            # set/replace the levels present and drop the ones removed. The
            # level-up announce channel is a normal column.
            if feature == "levels":
                if "channel" in options and options.get("channel") is not None:
                    try:
                        await self.db.set_guild_setting(
                            guild_id, "level_up_channel_id", int(options["channel"])
                        )
                    except (TypeError, ValueError):
                        return {"error": "Invalid level-up channel id"}
                rewards = options.get("rewards")
                if isinstance(rewards, list):
                    if len(rewards) > 100:
                        return {"error": "Too many level rewards (max 100)."}
                    desired: dict[int, int] = {}
                    for r in rewards:
                        lvl_raw, role_raw = r.get("level"), r.get("roleId")
                        if lvl_raw in (None, "") or not role_raw:
                            continue
                        try:
                            lvl = int(lvl_raw)
                            role_id = _validate_discord_id(role_raw)
                        except (TypeError, ValueError):
                            return {"error": "Invalid level reward (level must be a number, role a valid id)"}
                        if lvl < 1:
                            continue
                        desired[lvl] = role_id
                    bad = self._unassignable_roles(self.get_guild(guild_id), list(desired.values()))
                    if bad:
                        labels = ", ".join(label for _, label in bad)
                        return {"error": f"I can't grant {labels} — move my role above it (and it can't be a managed role)."}
                    current = await self.db.get_level_roles(guild_id)
                    for lvl in current:
                        if lvl not in desired:
                            await self.db.remove_level_role(guild_id, lvl)
                    for lvl, role_id in desired.items():
                        await self.db.set_level_role(guild_id, lvl, role_id)
                return await self._get_feature_payload(guild_id, feature)

            # Filter word list is a TEXT[] column and feeds a cached compiled
            # regex, so it is handled separately: normalise the list and
            # invalidate the filter cog's pattern cache so changes apply at once.
            if feature == "filter":
                words = options.get("words")
                if isinstance(words, list):
                    # Cap word length (and overall count) so a bad payload can't
                    # bloat the TEXT[] column or the compiled filter regex.
                    cleaned = sorted({str(w).strip().lower()[:100] for w in words if str(w).strip()})
                    if len(cleaned) > 500:
                        return {"error": "Too many filter words (max 500)."}
                    await self.db.set_guild_setting(guild_id, "filter_words", cleaned)
                    filter_cog = self.get_cog("🚫 Filter")
                    if filter_cog:
                        await filter_cog._invalidate_pattern(guild_id)
                return await self._get_feature_payload(guild_id, feature)

            # Reaction roles live in the reaction_roles table (many per guild).
            # Replace the standalone set and best-effort add each reaction to its
            # message so members can click it.
            if feature == "reaction-role":
                items = options.get("items")
                if isinstance(items, list):
                    if len(items) > 100:
                        return {"error": "Too many reaction roles (max 100)."}
                    rows = []
                    for it in items:
                        ch, msg = it.get("channelId"), it.get("messageId")
                        emoji = (it.get("emoji") or "").strip()
                        role = it.get("roleId")
                        if not (ch and msg and emoji and role):
                            continue
                        try:
                            rows.append({
                                "channel_id": _validate_discord_id(ch),
                                "message_id": _validate_discord_id(msg),
                                "emoji": emoji,
                                "role_id": _validate_discord_id(role),
                            })
                        except ValueError:
                            return {"error": "Invalid reaction-role entry (ids must be numeric)"}
                    bad = self._unassignable_roles(self.get_guild(guild_id), [r["role_id"] for r in rows])
                    if bad:
                        labels = ", ".join(label for _, label in bad)
                        return {"error": f"I can't grant {labels} — move my role above it (and it can't be a managed role)."}
                    old_rows = await self.db.get_reaction_roles(guild_id, "reaction-role")
                    await self.db.replace_reaction_roles(guild_id, "reaction-role", rows)
                    await self._sync_reactions(guild_id, rows, old_rows)
                # Return the freshly-persisted payload so the dashboard re-syncs its
                # form state (otherwise the Save button stays enabled and edits look
                # like they didn't apply).
                return await self._get_feature_payload(guild_id, feature)

            # Scheduled / recurring announcements live in the scheduled_messages
            # table (many per guild); replace the set like reaction roles.
            if feature == "scheduled-messages":
                items = options.get("items")
                if isinstance(items, list):
                    if len(items) > 50:
                        return {"error": "Too many scheduled messages (max 50)."}
                    rows = []
                    for it in items:
                        ch = it.get("channelId")
                        content = (it.get("content") or "").strip()[:2000]
                        sched = it.get("scheduledAt")
                        repeat = it.get("repeat") or "none"
                        enabled = bool(it.get("enabled", True))
                        if not (ch and content and sched):
                            continue
                        if repeat not in ("none", "daily", "weekly"):
                            repeat = "none"
                        try:
                            channel_id = _validate_discord_id(ch)
                            scheduled_at = datetime.datetime.fromisoformat(str(sched).replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            return {"error": "Invalid scheduled message (check the channel and time)."}
                        if scheduled_at.tzinfo is None:
                            scheduled_at = scheduled_at.replace(tzinfo=datetime.timezone.utc)
                        rows.append({
                            "channel_id": channel_id,
                            "content": content,
                            "scheduled_at": scheduled_at,
                            "repeat": repeat,
                            "enabled": enabled,
                        })
                    await self.db.replace_scheduled_messages(guild_id, rows)
                return await self._get_feature_payload(guild_id, feature)

            # AutoMod content-filter config (invite/link blocking) lives in guilds
            # columns but is cached, so it goes through set_automod_config.
            if feature == "automod":
                block_invites = bool(options.get("blockInvites", False))
                block_links = bool(options.get("blockLinks", False))
                domains_raw = options.get("allowedDomains") or []
                domains = sorted({str(d).strip().lower() for d in domains_raw if str(d).strip()})[:50]
                await self.db.set_automod_config(guild_id, block_invites, block_links, domains)
                return await self._get_feature_payload(guild_id, feature)

            # Settings keys that map to BIGINT columns in Postgres and need int conversion
            BIGINT_SETTINGS = {
                "rules_channel_id", "rules_message_id", "welcome_channel_id",
                "autorole_id", "level_up_channel_id",
                "ticket_support_role_id", "ticket_category_id",
                "reaction_role_id", "punishment_log_id",
                "usage_log_id", "audit_log_id", "leave_log_id",
                "config_role_id", "kick_role_id", "ban_role_id",
                "mute_role_id", "warn_role_id", "clear_role_id",
            }

            # Map feature options to settings keys
            mapping = {
                "rules": {
                    "channel": "rules_channel_id",
                    "message": "rules_message",
                },
                "welcome-message": {
                    "channel": "welcome_channel_id",
                    "message": "welcome_message",
                    "autorole": "autorole_id",
                },
                "logging": {
                    "logChannel": "punishment_log_id",
                    "usageChannel": "usage_log_id",
                    "messagesChannel": "audit_log_id",
                    "leaveChannel": "leave_log_id",
                },
                "tickets": {
                    "supportRole": "ticket_support_role_id",
                    "category": "ticket_category_id",
                },
            }

            # The welcome autorole is granted to every new member, so reject one
            # the bot can't assign (above its role / managed) up front instead of
            # letting it fail silently on each join.
            if feature == "welcome-message" and options.get("autorole"):
                bad = self._unassignable_roles(self.get_guild(guild_id), [options["autorole"]])
                if bad:
                    labels = ", ".join(label for _, label in bad)
                    return {"error": f"I can't grant {labels} as the autorole — move my role above it (and it can't be a managed role)."}

            if feature in mapping:
                for option_key, setting_key in mapping[feature].items():
                    if option_key not in options:
                        continue
                    value = options[option_key]
                    if value is None:
                        # Explicit null means the admin cleared an optional
                        # channel/role in the dashboard — unset the column.
                        await self.db.set_guild_setting(guild_id, setting_key, None)
                        continue
                    if setting_key in BIGINT_SETTINGS:
                        try:
                            value = int(value)
                        except (TypeError, ValueError):
                            return {"error": f"Invalid value for {option_key}: must be a numeric Discord ID"}
                    await self.db.set_guild_setting(guild_id, setting_key, value)
                
                # --- E2E Sync: Rules ---
                if feature == "rules":
                    logger.info(f"Starting Rules E2E sync for guild {guild_id}")
                    guild = self.get_guild(guild_id)
                    if not guild:
                        try:
                            guild = await self.fetch_guild(guild_id)
                            logger.info(f"Guild {guild_id} fetched from API (not in cache)")
                        except discord.NotFound:
                            logger.error(f"Guild {guild_id} not found during Rules sync")
                            return {"error": "Guild not found"}
                    
                    if guild:
                        channel_id = options.get("channel")
                        rules_text = options.get("message")
                        logger.info(f"Sync details: channel={channel_id}, text_len={len(rules_text) if rules_text else 0}")
                        
                        if channel_id and rules_text:
                            try:
                                channel_id_int = int(channel_id)
                                channel = guild.get_channel(channel_id_int)
                                if not channel:
                                    try:
                                        channel = await guild.fetch_channel(channel_id_int)
                                        logger.info(f"Channel {channel_id_int} fetched from API")
                                    except discord.NotFound:
                                        logger.error(f"Channel {channel_id_int} not found")
                                        return {"error": "Channel not found"}
                                
                                if channel and isinstance(channel, discord.TextChannel):
                                    # Check for existing message ID to edit
                                    message_id = await self.db.get_guild_setting(guild_id, "rules_message_id")
                                    if message_id:
                                        try:
                                            msg = await channel.fetch_message(int(message_id))
                                            await msg.edit(content=rules_text)
                                            logger.info(f"Rules message {message_id} edited successfully")
                                        except (discord.NotFound, discord.Forbidden, ValueError):
                                            # If not found or can't edit, post new one
                                            new_msg = await channel.send(content=rules_text)
                                            await self.db.set_guild_setting(guild_id, "rules_message_id", new_msg.id)
                                            logger.info(f"Rules message not found/editable, posted new: {new_msg.id}")
                                    else:
                                        new_msg = await channel.send(content=rules_text)
                                        await self.db.set_guild_setting(guild_id, "rules_message_id", new_msg.id)
                                        logger.info(f"No previous rules message, posted new: {new_msg.id}")
                            except Exception as e:
                                logger.error(f"Error during Rules E2E sync: {e}", exc_info=True)
                                return {"error": f"Failed to sync with Discord: {str(e)}"}

                        # Rules reaction-role (one mapping on the rules message)
                        rules_msg_id = await self.db.get_guild_setting(guild_id, "rules_message_id")
                        rules_ch_id = await self.db.get_guild_setting(guild_id, "rules_channel_id")
                        old_rules = await self.db.get_reaction_roles(guild_id, "rules")
                        if options.get("reactionEnabled") and options.get("reactionRole") and rules_msg_id and rules_ch_id:
                            try:
                                rr = {
                                    "channel_id": int(rules_ch_id),
                                    "message_id": int(rules_msg_id),
                                    "emoji": (options.get("reactionEmoji") or "✅").strip(),
                                    "role_id": _validate_discord_id(options.get("reactionRole")),
                                }
                            except ValueError:
                                return {"error": "Invalid rules reaction role id"}
                            await self.db.replace_reaction_roles(guild_id, "rules", [rr])
                            await self._sync_reactions(guild_id, [rr], old_rules)
                        else:
                            await self.db.replace_reaction_roles(guild_id, "rules", [])
                            # Remove the bot's stale reaction if the rules role was turned off.
                            await self._sync_reactions(guild_id, [], old_rules)

                return await self._get_feature_payload(guild_id, feature)

        return {"error": "Unknown action"}

    async def _sync_reactions(self, guild_id: int, rows: list, old_rows: Optional[list] = None) -> None:
        """Best-effort reconcile of the bot's own reactions on each mapped message:
        add the current mapping's emoji, and remove the bot's reaction for emojis
        that are no longer mapped on that message (e.g. after the admin changes the
        emoji on a reaction role). Members' own reactions are left untouched; a bad
        emoji or missing message just logs."""
        guild = self.get_guild(guild_id)
        if not guild:
            return
        plan = plan_reaction_changes(rows, old_rows)
        for mid, change in plan.items():
            ch_id = change["channel_id"]
            if ch_id is None:
                continue
            try:
                channel = guild.get_channel(ch_id) or await guild.fetch_channel(ch_id)
                msg = await channel.fetch_message(mid)
            except Exception as e:
                logger.warning(f"Reaction sync: could not load message {mid}: {e}")
                continue
            # Remove the bot's own reaction for emojis no longer mapped on this message.
            for emoji in change["remove"]:
                try:
                    await msg.remove_reaction(emoji, self.user)
                except Exception as e:
                    logger.warning(f"Could not remove stale reaction {emoji} from message {mid}: {e}")
            # Add the current emojis (no-op if the bot already reacted).
            for emoji in change["add"]:
                try:
                    await msg.add_reaction(emoji)
                except Exception as e:
                    logger.warning(f"Could not add reaction {emoji} to message {mid}: {e}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Global error handler for slash commands."""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ Command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have the required permissions to use this command.", ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await interaction.response.send_message(f"❌ I'm missing the following permissions: `{perms}`", ephemeral=True)
        else:
            logger.error(f"Unhandled slash command error: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("🐞 An unexpected error occurred.", ephemeral=True)
            else:
                await interaction.followup.send("🐞 An unexpected error occurred.", ephemeral=True)

async def main():
    bot = MyBot()
    set_bot_instance(bot) # Share bot instance with FastAPI app
    
    config = load_config()
    token = config.get('DISCORD_TOKEN')
    
    if not token:
        logger.critical("DISCORD_TOKEN not found in environment variables.")
        return

    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
