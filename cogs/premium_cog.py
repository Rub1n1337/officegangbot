"""Discord monetization → premium status.

Premium is sold as a per-guild **App Subscription** (SKU ``DISCORD_PREMIUM_SKU_ID``).
Discord runs the checkout, tax and refunds; the bot only reacts to entitlement
events and mirrors them into the ``guild_premium`` table (which ``is_premium``
already reads). Everything no-ops safely when the SKU env is unset, so this is
safe to ship before the SKU exists / the app passes monetization eligibility.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.logger import logger
from core.entitlements import premium_sku_id, entitlement_guild_state

RECONCILE_HOURS = 6


class PremiumCog(commands.Cog, name="💎 Premium"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._reconcile.start()

    def cog_unload(self):
        self._reconcile.cancel()

    async def _sync(self, entitlement: discord.Entitlement) -> None:
        """Mirror one entitlement into guild_premium (only our guild-sub SKU)."""
        state = entitlement_guild_state(entitlement, premium_sku_id())
        if state is None or not self.bot.db:
            return
        guild_id, active, ends_at = state
        try:
            await self.bot.db.set_premium(
                guild_id,
                active=active,
                plan="premium",
                current_period_end=ends_at,
                provider="discord",
                provider_subscription_id=str(entitlement.id),
            )
            logger.info(f"Premium entitlement synced: guild={guild_id} active={active}")
        except Exception:
            logger.exception(f"Failed to sync premium entitlement for guild {guild_id}")

    @commands.Cog.listener()
    async def on_entitlement_create(self, entitlement: discord.Entitlement):
        await self._sync(entitlement)

    @commands.Cog.listener()
    async def on_entitlement_update(self, entitlement: discord.Entitlement):
        # Fires on renewal and on cancel (ends_at gets set) — re-sync either way.
        await self._sync(entitlement)

    @commands.Cog.listener()
    async def on_entitlement_delete(self, entitlement: discord.Entitlement):
        # A delete is a refund/chargeback — revoke immediately.
        sku = premium_sku_id()
        if sku is None or entitlement.sku_id != sku or not self.bot.db:
            return
        guild_id = entitlement.guild_id
        if guild_id:
            try:
                await self.bot.db.set_premium(int(guild_id), active=False, provider="discord")
                logger.info(f"Premium entitlement deleted: guild={guild_id} revoked")
            except Exception:
                logger.exception(f"Failed to revoke premium for guild {guild_id}")

    @tasks.loop(hours=RECONCILE_HOURS)
    async def _reconcile(self):
        """Re-sync guild_premium with Discord's live entitlements — catches
        events missed while the bot was offline, and revokes guilds whose
        subscription has lapsed."""
        sku = premium_sku_id()
        if sku is None or not self.bot.db:
            return
        try:
            active_now: set[int] = set()
            async for e in self.bot.entitlements(skus=[discord.Object(sku)], exclude_ended=True):
                state = entitlement_guild_state(e, sku)
                if state and state[1]:
                    gid, _, ends = state
                    active_now.add(gid)
                    await self.bot.db.set_premium(
                        gid, active=True, plan="premium",
                        current_period_end=ends, provider="discord",
                        provider_subscription_id=str(e.id),
                    )
            # Revoke Discord-granted premium that no longer has a live entitlement.
            for gid in await self.bot.db.list_active_premium_guilds(provider="discord"):
                if gid not in active_now:
                    await self.bot.db.set_premium(gid, active=False, provider="discord")
            logger.info(f"Premium reconcile: {len(active_now)} active guild subscription(s)")
        except Exception:
            logger.exception("Premium entitlement reconcile failed")

    @_reconcile.before_loop
    async def _before_reconcile(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="premium", description="Upgrade this server to Premium.")
    @app_commands.guild_only()
    async def premium(self, interaction: discord.Interaction):
        """Shows the native Discord subscribe button for the premium SKU."""
        sku = premium_sku_id()
        if sku is None:
            await interaction.response.send_message(
                "Premium isn’t available yet — check back soon.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="OfficeGangBot Premium",
            description=(
                "Unlock higher limits, custom embed colour & footer, and more for "
                "this server. Subscribe below — billing is handled by Discord."
            ),
            color=discord.Color.blurple(),
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(sku_id=sku))  # native premium button
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PremiumCog(bot))
