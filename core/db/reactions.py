# core/db/reactions.py
"""Reaction roles and role menus (mixin for DatabaseManager)."""
from typing import List, Dict, Any


class _ReactionsMixin:

    # -------------------------
    # Reaction roles
    # -------------------------

    async def get_reaction_roles(self, guild_id: int, source: str = None) -> List[Dict[str, Any]]:
        """Returns reaction-role mappings for a guild, optionally filtered by source."""
        async with self.pool.acquire() as conn:
            if source is None:
                rows = await conn.fetch(
                    "SELECT channel_id, message_id, emoji, role_id, source "
                    "FROM reaction_roles WHERE guild_id = $1 ORDER BY id",
                    guild_id
                )
            else:
                rows = await conn.fetch(
                    "SELECT channel_id, message_id, emoji, role_id, source "
                    "FROM reaction_roles WHERE guild_id = $1 AND source = $2 ORDER BY id",
                    guild_id, source
                )
            return [dict(r) for r in rows]

    async def get_message_reaction_roles(self, guild_id: int, message_id: int) -> List[Dict[str, Any]]:
        """Returns reaction-role mappings on a specific message (emoji matched in
        Python). For role-menu messages, `exclusive` reflects whether the menu is
        single-select."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT rr.emoji, rr.role_id, rr.source, "
                "COALESCE(rm.exclusive, FALSE) AS exclusive "
                "FROM reaction_roles rr "
                "LEFT JOIN reaction_menus rm "
                "  ON rm.guild_id = rr.guild_id AND rm.message_id = rr.message_id "
                "  AND rr.source = 'menu' "
                "WHERE rr.guild_id = $1 AND rr.message_id = $2",
                guild_id, message_id
            )
            return [dict(r) for r in rows]

    async def replace_reaction_roles(self, guild_id: int, source: str, rows: List[Dict[str, Any]]) -> None:
        """Replaces all reaction roles of a given source for a guild with `rows`.
        Each row needs channel_id, message_id, emoji, role_id."""
        await self.ensure_guild(guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM reaction_roles WHERE guild_id = $1 AND source = $2",
                    guild_id, source
                )
                for r in rows:
                    await conn.execute(
                        """
                        INSERT INTO reaction_roles
                            (guild_id, channel_id, message_id, emoji, role_id, source)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (guild_id, message_id, emoji) DO UPDATE
                            SET role_id = EXCLUDED.role_id,
                                channel_id = EXCLUDED.channel_id,
                                source = EXCLUDED.source
                        """,
                        guild_id, int(r["channel_id"]), int(r["message_id"]),
                        str(r["emoji"]), int(r["role_id"]), source
                    )

    # --- Role menus --------------------------------------------------------

    async def get_reaction_menus(self, guild_id: int) -> List[Dict[str, Any]]:
        """Returns the guild's role menus, each with its emoji->role items
        (resolved from reaction_roles where source='menu')."""
        async with self.pool.acquire() as conn:
            menus = await conn.fetch(
                "SELECT id, channel_id, message_id, title, description, exclusive, style "
                "FROM reaction_menus WHERE guild_id = $1 ORDER BY id",
                guild_id,
            )
            items = await conn.fetch(
                "SELECT message_id, emoji, role_id FROM reaction_roles "
                "WHERE guild_id = $1 AND source = 'menu'",
                guild_id,
            )
        by_msg: Dict[int, List[Dict[str, Any]]] = {}
        for it in items:
            by_msg.setdefault(it["message_id"], []).append(
                {"emoji": it["emoji"], "role_id": it["role_id"]}
            )
        result = []
        for m in menus:
            md = dict(m)
            md["items"] = by_msg.get(m["message_id"], []) if m["message_id"] else []
            result.append(md)
        return result

    VALID_MENU_STYLES = ("reactions", "buttons", "dropdown")

    async def create_reaction_menu(
        self, guild_id: int, channel_id: int, title: str, description: str,
        exclusive: bool = False, style: str = "reactions",
    ) -> int:
        """Inserts a role menu (message not posted yet) and returns its id."""
        await self.ensure_guild(guild_id)
        if style not in self.VALID_MENU_STYLES:
            style = "reactions"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO reaction_menus (guild_id, channel_id, title, description, exclusive, style) "
                "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
                guild_id, int(channel_id), str(title)[:256], str(description), bool(exclusive), style,
            )
        return row["id"]

    async def update_reaction_menu(
        self, menu_id: int, channel_id: int, title: str, description: str, message_id,
        exclusive: bool = False, style: str = "reactions",
    ) -> None:
        """Updates a role menu's channel/title/description, exclusive flag, style
        and posted message id."""
        if style not in self.VALID_MENU_STYLES:
            style = "reactions"
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE reaction_menus SET channel_id = $1, title = $2, description = $3, "
                "message_id = $4, exclusive = $5, style = $6 WHERE id = $7",
                int(channel_id), str(title)[:256], str(description),
                int(message_id) if message_id else None, bool(exclusive), style, menu_id,
            )

    async def delete_reaction_menu(self, menu_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM reaction_menus WHERE id = $1", menu_id)

    async def replace_message_reaction_roles(self, guild_id: int, message_id: int, source: str, rows: List[Dict[str, Any]]) -> None:
        """Replaces the reaction roles on a single message (used by role menus,
        which have many messages per guild — unlike replace_reaction_roles, which
        clears a whole source)."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM reaction_roles WHERE guild_id = $1 AND message_id = $2 AND source = $3",
                    guild_id, int(message_id), source,
                )
                for r in rows:
                    await conn.execute(
                        """
                        INSERT INTO reaction_roles
                            (guild_id, channel_id, message_id, emoji, role_id, source)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (guild_id, message_id, emoji) DO UPDATE
                            SET role_id = EXCLUDED.role_id,
                                channel_id = EXCLUDED.channel_id,
                                source = EXCLUDED.source
                        """,
                        guild_id, int(r["channel_id"]), int(r["message_id"]),
                        str(r["emoji"]), int(r["role_id"]), source,
                    )
