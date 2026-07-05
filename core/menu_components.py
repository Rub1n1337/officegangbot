# core/menu_components.py
"""Component-style role menus: buttons / dropdown instead of emoji reactions.

The components are stateless DynamicItems — the role id (button) or menu id
(select) rides in the custom_id, so they keep working after a restart without
any re-binding beyond bot.add_dynamic_items(). The select's options live in the
posted message itself, and exclusivity is resolved at click time from the
message's stored mappings (get_message_reaction_roles), so no extra state is
needed anywhere.
"""
from typing import List, Dict, Any, Optional

import discord

from core.i18n import t
from core.logger import logger

MAX_COMPONENTS = 25  # Discord's cap for view children and select options alike.


def _partial_emoji(raw: str) -> Optional[discord.PartialEmoji]:
    """Stored emoji string (unicode or <a:name:id>) → PartialEmoji, or None."""
    try:
        emoji = discord.PartialEmoji.from_str(str(raw).strip())
        return emoji if (emoji.is_unicode_emoji() or emoji.id) else None
    except Exception:
        return None


async def _menu_context(interaction: discord.Interaction):
    """Shared preamble for menu component clicks: (db, locale, mappings) or
    None after replying, when the feature is off / message unmapped."""
    bot = interaction.client
    guild = interaction.guild
    if guild is None or not getattr(bot, "db", None):
        return None
    loc = await bot.db.get_locale(guild.id)
    enabled = await bot.db.get_enabled_features(guild.id)
    if "reaction-menus" not in enabled:
        await interaction.response.send_message(t(loc, "rolemenu.disabled"), ephemeral=True)
        return None
    mappings = await bot.db.get_message_reaction_roles(guild.id, interaction.message.id)
    return bot.db, loc, mappings


class RoleMenuButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"rolemenu:(?P<role>\d+)",
):
    """One role-toggle button. Clicking adds the role (clearing the menu's other
    roles when the menu is exclusive) or removes it if already held."""

    def __init__(self, role_id: int, label: str = "", emoji: Optional[str] = None):
        self.role_id = int(role_id)
        super().__init__(
            discord.ui.Button(
                label=(label or "")[:80] or None,
                emoji=_partial_emoji(emoji) if emoji else None,
                style=discord.ButtonStyle.secondary,
                custom_id=f"rolemenu:{role_id}",
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["role"]))

    async def callback(self, interaction: discord.Interaction):
        ctx = await _menu_context(interaction)
        if ctx is None:
            return
        _, loc, mappings = ctx
        guild = interaction.guild
        member = interaction.user
        role = guild.get_role(self.role_id)
        if role is None:
            return await interaction.response.send_message(t(loc, "rolemenu.error"), ephemeral=True)
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Role menu (button)")
                return await interaction.response.send_message(
                    t(loc, "rolemenu.removed", role=role.name), ephemeral=True
                )
            await member.add_roles(role, reason="Role menu (button)")
            # Exclusive menu: adding one role drops the member's other roles
            # from the same menu message.
            if any(m.get("exclusive") and int(m["role_id"]) == self.role_id for m in mappings):
                others = [
                    r for m in mappings
                    if int(m["role_id"]) != self.role_id
                    and (r := guild.get_role(int(m["role_id"]))) and r in member.roles
                ]
                if others:
                    await member.remove_roles(*others, reason="Exclusive role menu (button)")
            await interaction.response.send_message(
                t(loc, "rolemenu.granted", role=role.name), ephemeral=True
            )
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Role-menu button: couldn't toggle {self.role_id} for {member}: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(t(loc, "rolemenu.error"), ephemeral=True)


class RoleMenuSelect(
    discord.ui.DynamicItem[discord.ui.Select],
    template=r"rolemenusel:(?P<menu>\d+)",
):
    """Dropdown role menu. The selection is reconciled against the menu's role
    set: picked roles are granted, unpicked menu roles are removed."""

    def __init__(self, menu_id: int, options: Optional[List[discord.SelectOption]] = None,
                 max_values: int = 1, placeholder: Optional[str] = None):
        self.menu_id = int(menu_id)
        super().__init__(
            discord.ui.Select(
                custom_id=f"rolemenusel:{menu_id}",
                placeholder=(placeholder or None),
                min_values=0,
                max_values=max(1, max_values),
                options=options or [discord.SelectOption(label="…", value="0")],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["menu"]))

    async def callback(self, interaction: discord.Interaction):
        ctx = await _menu_context(interaction)
        if ctx is None:
            return
        _, loc, mappings = ctx
        guild = interaction.guild
        member = interaction.user
        selected = {int(v) for v in interaction.data.get("values", []) if str(v).isdigit()}
        menu_role_ids = {int(m["role_id"]) for m in mappings}
        # Never grant a role that isn't part of this menu, whatever the payload says.
        selected &= menu_role_ids
        to_add = [
            r for rid in selected
            if (r := guild.get_role(rid)) and r not in member.roles
        ]
        to_remove = [
            r for rid in (menu_role_ids - selected)
            if (r := guild.get_role(rid)) and r in member.roles
        ]
        try:
            if to_add:
                await member.add_roles(*to_add, reason="Role menu (dropdown)")
            if to_remove:
                await member.remove_roles(*to_remove, reason="Role menu (dropdown)")
            await interaction.response.send_message(t(loc, "rolemenu.updated"), ephemeral=True)
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Role-menu select: couldn't update roles for {member}: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(t(loc, "rolemenu.error"), ephemeral=True)


def build_menu_view(
    style: str,
    menu_id: int,
    items: List[Dict[str, Any]],
    exclusive: bool,
    placeholder: Optional[str] = None,
) -> Optional[discord.ui.View]:
    """A persistent view for a component-style menu, or None for the legacy
    reactions style. `items` is a list of {emoji, role_id, label}."""
    if style not in ("buttons", "dropdown") or not items:
        return None
    items = items[:MAX_COMPONENTS]
    view = discord.ui.View(timeout=None)
    if style == "buttons":
        for it in items:
            view.add_item(RoleMenuButton(int(it["role_id"]), it.get("label") or "", it.get("emoji")))
        return view
    options = [
        discord.SelectOption(
            label=(it.get("label") or str(it["role_id"]))[:100],
            value=str(int(it["role_id"])),
            emoji=_partial_emoji(it.get("emoji") or "") or None,
        )
        for it in items
    ]
    view.add_item(
        RoleMenuSelect(
            menu_id,
            options=options,
            max_values=1 if exclusive else len(options),
            placeholder=placeholder,
        )
    )
    return view
