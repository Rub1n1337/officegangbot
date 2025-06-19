import asyncio
import discord
from discord.ext import commands
from logs.logger import logger  # Убедись, что этот логгер существует
from utils.server_settings import ServerSettings  # Убедись, что этот класс работает

class GuildSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_settings = ServerSettings()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            if not guild.me.guild_permissions.manage_channels:
                if guild.system_channel:
                    await guild.system_channel.send("❌ I need 'Manage Channels' permission to create required channels!")
                return

            punish_channel = await self.create_punishments_channel(guild)
            setup_channel = await self.create_bot_setup_channel(guild)

            if punish_channel and setup_channel:
                if guild.system_channel:
                    await guild.system_channel.send(
                        "🔧 Required channels created!\n"
                        "Please complete setup within **30 minutes** using the `!setup_done` command in the `bot-setup` channel."
                    )

                # Запускаем фоновую задачу удаления каналов, если не будет подтверждения
                asyncio.create_task(self.auto_delete_unconfirmed_channels(guild, punish_channel, setup_channel))

            else:
                if guild.system_channel:
                    await guild.system_channel.send("⚠️ Failed to create required channels. Please check my permissions.")
        except Exception as e:
            logger.error(f"Error in on_guild_join for {guild.name}: {e}")

    async def create_punishments_channel(self, guild):
        existing_channel = discord.utils.get(guild.channels, name="punishments")
        if not existing_channel:
            try:
                channel = await guild.create_text_channel("punishments")
                logger.info(f"Created 'punishments' channel in {guild.name}")
                return channel
            except Exception as e:
                logger.error(f"Failed to create 'punishments' channel in {guild.name}: {e}")
        return existing_channel

    async def create_bot_setup_channel(self, guild):
        channel_name = "bot-setup"
        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        if existing_channel:
            return existing_channel

        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
            }

            if guild.owner:
                overwrites[guild.owner] = discord.PermissionOverwrite(read_messages=True)

            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True)

            channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
            logger.info(f"Created '{channel_name}' channel in {guild.name}")
            return channel
        except Exception as e:
            logger.error(f"Failed to create '{channel_name}' channel in {guild.name}: {e}")
            return None

    async def auto_delete_unconfirmed_channels(self, guild, punish_channel, setup_channel):
        await asyncio.sleep(30 * 60)  # 30 минут

        if not self.server_settings.is_setup_complete(guild.id):
            try:
                await punish_channel.delete(reason="Setup not completed in time")
                await setup_channel.delete(reason="Setup not completed in time")
                logger.info(f"Deleted setup channels in {guild.name} due to timeout")
            except Exception as e:
                logger.error(f"Failed to delete setup channels in {guild.name}: {e}")

    @commands.command(name="setup_done")
    @commands.has_permissions(administrator=True)
    async def setup_done(self, ctx):
        try:
            guild_id = ctx.guild.id
            if self.server_settings.is_setup_complete(guild_id):
                await ctx.send("✅ Setup was already completed!")
                return

            self.server_settings.set_setup_complete(guild_id)
            await ctx.send("🎉 Setup complete! Thank you.")
            logger.info(f"Setup completed for {ctx.guild.name}")
        except Exception as e:
            logger.error(f"Error in !setup_done command: {e}")
            await ctx.send("❌ An error occurred while completing setup.")
