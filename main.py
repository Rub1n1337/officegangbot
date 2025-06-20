import discord
from discord.ext import commands
from webserver import keep_alive
import config
import sqlite3
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from guild_setup import GuildSetup
from welcome_system import WelcomeSystem
from health_monitor import HealthMonitor

# Enhanced logging configuration
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger('BrawlStarsBot')

# Constants
MUTE_ROLE_ID = 876508795562504252
MEMBER_ROLE_ID = 873196004718034964
LOG_CHANNEL_ID = 876507449362898974
WELCOME_CHANNEL_NAME = 'велкам-👋'
REACTION_MESSAGE_ID = 874752473405988874

class ServerSettings:
    def __init__(self, file_path='server_setups.json'):
        self.file_path = Path(file_path)
        self.settings = self._load_settings()
        self.default_prefix = '!'

    def _load_settings(self):
        if self.file_path.exists():
            with open(self.file_path, 'r') as f:
                return json.load(f)
        return {}

    def save_settings(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def set_server_channels(self, guild_id, channels):
        guild_id = str(guild_id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {'prefix': self.default_prefix}
        self.settings[guild_id].update(channels)
        self.save_settings()

    def get_prefix(self, guild_id):
        guild_settings = self.settings.get(str(guild_id), {})
        return guild_settings.get('prefix', self.default_prefix)

    def set_prefix(self, guild_id, prefix):
        guild_id = str(guild_id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id]['prefix'] = prefix
        self.save_settings()

    def get_server_channels(self, guild_id):
        return self.settings.get(str(guild_id), {})

    def get_punishment_channel(self, guild_id):
        channels = self.get_server_channels(guild_id)
        return channels.get('punishments')

    def get_setup_channel(self, guild_id):
        channels = self.get_server_channels(guild_id)
        return channels.get('bot-setup')

    def is_setup_complete(self, guild_id):
        channels = self.get_server_channels(guild_id)
        return all(key in channels for key in ['punishments', 'bot-setup'])

class BrawlStarsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        self.server_settings = ServerSettings()

        async def get_prefix(bot, message):
            if not message.guild:
                return '!'  # DM messages use default prefix
            return bot.server_settings.get_prefix(message.guild.id)

        super().__init__(command_prefix=get_prefix, intents=intents)
        self.db_path = 'Pocosultoj.db'

    def _requires_setup(self, guild_id):
        """Check if a guild requires setup completion"""
        if not guild_id:
            return False
        return not self.server_settings.is_setup_complete(guild_id)

    async def _send_setup_required_message(self, ctx):
        """Send setup required message"""
        embed = discord.Embed(
            title="⚠️ Bot Not Configured!",
            description="This server hasn't completed the bot setup yet.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="🔧 Setup Required",
            value="Please ask the **server owner** to:\n"
                  "1️⃣ Create a channel named `#bot-setup`\n"
                  "2️⃣ Run `!botsetup` in that channel\n"
                  "3️⃣ Complete the guided setup process",
            inline=False
        )
        embed.add_field(
            name="👑 Server Owner",
            value=f"Server Owner: {ctx.guild.owner.mention if ctx.guild.owner else 'Unknown'}",
            inline=False
        )
        embed.set_footer(text="💡 Setup only takes a few minutes!")
        await ctx.send(embed=embed)

    async def setup_hook(self):
        self.init_database()
        await self.add_cog(GuildSetup(self))
        await self.add_cog(WelcomeSystem(self))

        # Start health monitoring
        self.health_monitor = HealthMonitor(self)
        self.health_monitor.start_monitoring()

        logger.info('Database initialized, cogs loaded, and health monitoring started')

    def init_database(self):
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as db:
                db.execute('PRAGMA journal_mode=WAL')  # Better concurrency
                db.execute('PRAGMA synchronous=NORMAL')  # Better performance
                db.execute('PRAGMA cache_size=10000')  # Increase cache
                db.execute('PRAGMA temp_store=memory')  # Use memory for temp

                cur = db.cursor()
                cur.execute('''CREATE TABLE IF NOT EXISTS warnings 
                              (userid INTEGER, count INTEGER, guild_id INTEGER)''')
                db.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    async def on_ready(self):
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game('Brawl Stars')
        )
        logger.info(f'Bot logged in as {self.user}')
        print(f'Bot logged in as {self.user}')

        # Send welcome message to all guilds on startup
        for guild in self.guilds:
            await self.send_welcome_message(guild)

    def generate_help_embed(self):
        embed = discord.Embed(
            title="Bot Help Guide",
            description="Welcome! Here's a complete guide to using this bot.",
            color=discord.Color.blue()
        )

        # Commands section
        commands_info = {
            "!mute @user time reason": "Mutes a user for specified time (in minutes)",
            "!unmute @user": "Unmutes a user",
            "!kick @user reason": "Kicks a user from the server",
            "!ban @user reason": "Bans a user from the server",
            "!unban username": "Unbans a user",
            "!warn @user reason": "Warns a user (3 warnings = ban)",
            "!clear [amount]": "Clears specified amount of messages",
            "!info @user": "Shows user information",
            "!setup_channels": "Creates required channels",
        }

        embed.add_field(
            name="📋 Available Commands",
            value="\n".join(f"`{cmd}`: {desc}" for cmd, desc in commands_info.items()),
            inline=False
        )

        # Required channels section
        channels_info = (
            "**Required Channels:**\n"
            "• `punishments`: Logs all moderation actions\n"
            "• `bot setup`: Configuration channel (visible only to admins)\n"
            "\n**Required Roles:**\n"
            "• Mute role (ID: 876508795562504252)\n"
            "• Member role (ID: 873196004718034964)"
        )
        embed.add_field(name="⚙️ Server Setup", value=channels_info, inline=False)

        # Bot permissions section
        permissions_info = (
            "The bot needs these permissions:\n"
            "• Manage Channels\n"
            "• Manage Roles\n"
            "• Kick Members\n"
            "• Ban Members\n"
            "• Send Messages\n"
            "• Manage Messages"
        )
        embed.add_field(name="🔒 Required Permissions", value=permissions_info, inline=False)

        return embed

    async def send_welcome_message(self, guild):
        target_channel = guild.system_channel
        if not target_channel or not target_channel.permissions_for(guild.me).send_messages:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        if target_channel:
            try:
                # Main welcome embed
                welcome_embed = discord.Embed(
                    title="🎉 Hi! Thanks for adding me!",
                    description=f"Hello {guild.owner.mention if guild.owner else 'Server Owner'} and welcome to **{guild.name}**!\n\nI'm here to help you moderate your server effectively.",
                    color=discord.Color.blue()
                )

                # Setup instructions
                setup_embed = discord.Embed(
                    title="🔧 Quick Setup Required",
                    description="To get started, please follow these simple steps:",
                    color=discord.Color.green()
                )

                setup_embed.add_field(
                    name="📝 Step 1: Create Setup Channel",
                    value="Create a text channel named `#bot-setup`\n*(Only server owner/admins should have access)*",
                    inline=False
                )

                setup_embed.add_field(
                    name="⚙️ Step 2: Start Configuration", 
                    value="In the `#bot-setup` channel, type:\n`!bot_setup` or `!botsetup`",
                    inline=False
                )

                setup_embed.add_field(
                    name="👑 Important Note",
                    value="**Only the server owner or administrators should run the setup!**",
                    inline=False
                )

                # Permissions embed
                perms_embed = discord.Embed(
                    title="🔒 Required Permissions",
                    description="For the bot to function properly, please ensure I have these permissions:",
                    color=discord.Color.orange()
                )

                permissions_list = [
                    "• **Manage Channels** - Create required channels",
                    "• **Manage Roles** - Handle mute/member roles", 
                    "• **Kick Members** - Moderation actions",
                    "• **Ban Members** - Moderation actions",
                    "• **Send Messages** - Bot communication",
                    "• **Manage Messages** - Message moderation",
                    "• **Read Message History** - Command processing"
                ]

                perms_embed.add_field(
                    name="📋 Permission List",
                    value="\n".join(permissions_list),
                    inline=False
                )

                # Warning embed
                warning_embed = discord.Embed(
                    title="⚠️ Important Notice",
                    description="**The bot will not respond to commands until the initial setup is complete!**\n\nAfter setup, all moderation commands will be available.",
                    color=discord.Color.red()
                )

                # Send all embeds
                await target_channel.send(embed=welcome_embed)
                await target_channel.send(embed=setup_embed)
                await target_channel.send(embed=perms_embed)
                await target_channel.send(embed=warning_embed)

                logger.info(f"Sent welcome message to {guild.name} in #{target_channel.name}")
            except Exception as e:
                logger.error(f"Failed to send welcome message in {guild.name}: {e}")

    def get_channel_id(self, guild_id, channel_name):
        channels = self.server_settings.get_server_channels(guild_id)
        return channels.get(channel_name)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_done(self, ctx):
        """Verify and save channel setup"""
        if ctx.author != ctx.guild.owner:
            await ctx.send("❌ Only the server owner can complete the setup!")
            return

        required_channels = {
            "punishments": None,
            "bot-setup": None
        }

        # Verify channels exist
        for channel in ctx.guild.channels:
            if channel.name in required_channels:
                required_channels[channel.name] = channel.id

        # Check if any channels are missing
        missing = [name for name, id in required_channels.items() if id is None]
        if missing:
            await ctx.send(f"❌ Missing required channels: {', '.join(missing)}\nPlease create them and try again.")
            return

        # Save channel IDs
        self.server_settings.set_server_channels(ctx.guild.id, required_channels)
        await ctx.send("✅ Setup completed successfully! Bot is now fully configured for this server.")

    async def on_guild_join(self, guild):
        try:
            # Check if bot has necessary permissions
            if not guild.me.guild_permissions.manage_channels:
                if guild.system_channel:
                    await guild.system_channel.send("I need 'Manage Channels' permission to create required channels!")
                return

            # Create channels
            await self.create_punishments_channel(guild)
            await self.create_bot_setup_channel(guild)

            # Notify about successful creation
            if guild.system_channel:
                await guild.system_channel.send("Required channels have been created!")

        except Exception as e:
            logger.error(f"Error in on_guild_join for {guild.name}: {e}")
            if guild.system_channel:
                await guild.system_channel.send("Failed to create required channels. Please check bot permissions.")

    # Force create channels command
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_channels(self, ctx):
        """Force create/check required channels"""
        await self.create_punishments_channel(ctx.guild)
        await self.create_bot_setup_channel(ctx.guild)
        await ctx.send("Channels setup completed!")

    async def create_punishments_channel(self, guild):
        existing_channel = discord.utils.get(guild.channels, name="punishments")
        if not existing_channel:
            try:
                await guild.create_text_channel("punishments")
                logger.info(f"Created 'punishments' channel in {guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to create 'punishments' channel in {guild.name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to create 'punishments' channel in {guild.name}: {e}")
        else:
            logger.info(f"'punishments' channel already exists in {guild.name}")

    async def create_bot_setup_channel(self, guild):
        channel_name = "bot setup"
        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        channel_number = 1

        while existing_channel:
            channel_name = f"bot setup {channel_number}"
            existing_channel = discord.utils.get(guild.channels, name=channel_name)
            channel_number += 1

        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.owner: discord.PermissionOverwrite(read_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }

            # Give administrator role permissions
            for role in guild.roles:
                if role.permissions.administrator:
                     overwrites[role] = discord.PermissionOverwrite(read_messages=True)

            channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
            logger.info(f"Created '{channel_name}' channel in {guild.name}")

        except discord.Forbidden:
            logger.error(f"Missing permissions to create '{channel_name}' channel in {guild.name}")
        except discord.HTTPException as e:
            logger.error(f"Failed to create '{channel_name}' channel in {guild.name}: {e}")

    @commands.command(aliases=['botsetup', 'bot_setup'])
    async def help(self, ctx, command_name: str = None):
        """Show help information or start bot setup"""
        # If called as botsetup/bot_setup, redirect to setup
        if ctx.invoked_with in ['botsetup', 'bot_setup']:
            if ctx.channel.name == 'bot-setup' and ctx.author.guild_permissions.administrator:
                # This would typically call the setup function from GuildSetup cog
                await ctx.send("🔧 **Setup system is being prepared...** Please make sure you have the GuildSetup cog loaded for the full setup experience!")
                return
            elif ctx.channel.name != 'bot-setup':
                await ctx.send("❌ Setup commands can only be used in the `#bot-setup` channel!")
                return
            elif not ctx.author.guild_permissions.administrator:
                await ctx.send("❌ Only administrators can run setup commands!")
                return

        # Check if setup is complete for regular help
        if self._requires_setup(ctx.guild.id) and ctx.invoked_with == 'help':
            await self._send_setup_required_message(ctx)
            return

        """Show help information"""


bot = BrawlStarsBot()

# Register setup_done command
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_done(ctx):
    """Verify and save channel setup"""
    if ctx.author != ctx.guild.owner:
        await ctx.send("❌ Only the server owner can complete the setup!")
        return

    required_channels = {
        "punishments": None,
        "bot-setup": None
    }

    # Verify channels exist
    for channel in ctx.guild.channels:
        if channel.name in required_channels:
            required_channels[channel.name] = channel.id

    # Check if any channels are missing
    missing = [name for name, id in required_channels.items() if id is None]
    if missing:
        await ctx.send(f"❌ Missing required channels: {', '.join(missing)}\nPlease create them and try again.")
        return

    # Save channel IDs
    bot.server_settings.set_server_channels(ctx.guild.id, required_channels)

    # Send success message with configuration instructions
    setup_channel = ctx.guild.get_channel(required_channels["bot-setup"])
    if setup_channel:
        embed = discord.Embed(
            title="✅ Setup Complete",
            description="The bot has been successfully configured for this server!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Next Steps",
            value="Use these commands to customize the bot:\n"
                  "`!set_prefix <prefix>` - Change command prefix\n"
                  "`!set_autorole <role>` - Set role for new members\n"
                  "`!set_punishment_rules` - Configure auto-punishment rules",
            inline=False
        )
        await setup_channel.send(embed=embed)

    await ctx.send("✅ Setup completed successfully! Check the bot-setup channel for configuration instructions.")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != REACTION_MESSAGE_ID:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role_name = 'Member' if payload.emoji.name == '✅' else payload.emoji.name
    if role := discord.utils.get(guild.roles, name=role_name):
        await payload.member.add_roles(role)
        await log_action(guild, f"Role '{role.name}' added to {payload.member}")

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != REACTION_MESSAGE_ID:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild or not (member := await guild.fetch_member(payload.user_id)):
        return

    role_name = 'Member' if payload.emoji.name == '✅' else payload.emoji.name
    if role := discord.utils.get(guild.roles, name=role_name):
        await member.remove_roles(role)
        await log_action(guild, f"Role '{role.name}' removed from {member}")

async def log_action(guild, message):
    if log_channel := bot.get_channel(LOG_CHANNEL_ID):
        await log_channel.send(message)
    logger.info(message)

# Welcome messages are now handled by the WelcomeSystem cog

@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member, time: int, reason: str):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    mute_role = discord.utils.get(ctx.guild.roles, id=MUTE_ROLE_ID)
    member_role = discord.utils.get(ctx.guild.roles, id=MEMBER_ROLE_ID)
    channel = discord.utils.get(ctx.guild.channels, name='punishments') or bot.get_channel(LOG_CHANNEL_ID)

    if not all([mute_role, member_role, channel]):
        await ctx.send("Configuration error: Missing roles or channels")
        return

    embed = create_embed(
        "✅ Muted",
        member.mention,
        ctx.author.mention,
        reason,
        time
    )

    await member.remove_roles(member_role)
    await member.add_roles(mute_role)
    await channel.send(embed=embed)

    await asyncio.sleep(time * 60)

    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await member.add_roles(member_role)
        await channel.send(embed=create_unmute_embed(member))

def create_embed(title, member_mention, admin_mention, reason, duration=None):
    embed = discord.Embed(color=discord.Color.yellow())
    embed.add_field(name=title, value=f"{member_mention} has been {title.lower()}")
    embed.add_field(name="Administrator", value=admin_mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    if duration:
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=False)
    return embed

def create_unmute_embed(member):
    embed = discord.Embed(color=discord.Color.green())
    embed.add_field(name="✅ Unmuted", value=f"{member.mention} has been unmuted")
    return embed

@bot.command()
@commands.has_permissions(administrator=True)
async def unmute(ctx, member: discord.Member):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    channel = discord.utils.get(ctx.guild.channels, name='punishments') or bot.get_channel(LOG_CHANNEL_ID)
    muterole = discord.utils.get(ctx.guild.roles, id=MUTE_ROLE_ID)
    memberrole = discord.utils.get(ctx.guild.roles, id=MEMBER_ROLE_ID)

    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Unmuted", value=f"{member.mention} has been unmuted.")
    emb.add_field(name="Administrator", value=ctx.author.mention, inline=False)

    await member.remove_roles(muterole)
    await member.add_roles(memberrole)
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    channel = discord.utils.get(ctx.guild.channels, name='punishments') or bot.get_channel(LOG_CHANNEL_ID)
    await member.kick(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Kicked", value=f"{member.mention} has been kicked.")
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    channel = discord.utils.get(ctx.guild.channels, name='punishments') or bot.get_channel(LOG_CHANNEL_ID)
    await member.ban(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Banned", value=f"{member.mention} has been banned.")
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def unban(ctx, *, member):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    channel = discord.utils.get(ctx.guild.channels, name='punishments') or bot.get_channel(LOG_CHANNEL_ID)
    banned_users = await ctx.guild.bans()

    for ban_entry in banned_users:
        user = ban_entry.user
        if str(user) == member:
            await ctx.guild.unban(user)
            emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
            emb.add_field(name="✅ Unbanned", value=f"{member} has been unbanned.")
            await channel.send(embed=emb)
            return

@bot.command()
async def warn(ctx, member: discord.Member, *, reason=None):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    # Check if reason is provided
    if reason is None:
        await ctx.send("❌ Please provide a reason for the warning.\n**Usage:** `!warn @user <reason>`\n**Example:** `!warn @user spamming in chat`")
        return

    # Get server-specific punishment channel
    punishment_channel_id = bot.server_settings.get_punishment_channel(ctx.guild.id)
    if not punishment_channel_id:
        await ctx.send("❌ Server not properly configured. Please ask the server owner to run !setup_done")
        return

    channel = ctx.guild.get_channel(punishment_channel_id)
    if not channel:
        await ctx.send("❌ Punishment channel not found. Please contact the server owner.")
        return

    db_path = bot.db_path
    guild_name = f"warnings_{ctx.guild.id}"
    with sqlite3.connect(db_path) as db:
        cur = db.cursor()
        cur.execute(f'CREATE TABLE IF NOT EXISTS {guild_name} (userid INT, count INT)')
        db.commit()

        warning = cur.execute(f'SELECT * FROM {guild_name} WHERE userid={member.id}').fetchone()

        embed = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
        embed.add_field(name="✅ Warned", value=f"{member.mention} has received a warning.", inline=False)
        embed.add_field(name="Administrator", value=ctx.author.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        if warning is None:
            cur.execute(f'INSERT INTO {guild_name} VALUES ({member.id}, 1)')
            db.commit()
            await channel.send(embed=embed)
        elif warning[1] == 1:
            cur.execute(f'UPDATE {guild_name} SET count=2 WHERE userid={member.id}')
            db.commit()
            await channel.send(embed=embed)
        elif warning[1] == 2:
            cur.execute(f'UPDATE {guild_name} SET count=3 WHERE userid={member.id}')
            db.commit()
            await channel.send(embed=embed)
            await member.ban(reason=reason)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx, amount=100):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    await ctx.channel.purge(limit=amount)

@bot.command()
async def info(ctx, member: discord.Member):
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    embed = discord.Embed(
        title="User Information",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )

    fields = {
        "Display Name": member.display_name,
        "ID": member.id,
        "Joined Server": member.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "Account Created": member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "Roles": ", ".join(role.name for role in member.roles[1:])
    }

    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix):
    """Change the command prefix for this server"""
    if bot._requires_setup(ctx.guild.id):
        await bot._send_setup_required_message(ctx)
        return
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Only administrators can change the prefix!")
        return

    bot.server_settings.set_prefix(ctx.guild.id, new_prefix)
    await ctx.send(f"✅ Command prefix changed to: `{new_prefix}`")

@bot.command()
async def test(ctx):
    await ctx.send('Test command executed successfully.')

@bot.command()
@commands.has_permissions(administrator=True)
async def send_welcome(ctx):
    """Resends the welcome message with bot information"""
    await bot.send_welcome_message(ctx.guild)
    await ctx.message.add_reaction('✅')

@bot.event
async def on_command_error(self, ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `{ctx.prefix}help {ctx.command}` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `{ctx.prefix}help {ctx.command}` for usage.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have the required permissions to execute this command.")
    else:
        logger.error(f"Command error in {ctx.command}: {error}")
        await ctx.send("❌ An error occurred while executing the command.")

# Start the webserver and run the bot
keep_alive()

# Enhanced bot startup with error handling
if __name__ == "__main__":
    try:
        logger.info("Starting Discord bot...")
        bot.run(config.TOKEN, log_handler=None)  # Disable discord.py's default logging
    except discord.LoginFailure:
        logger.error("Failed to login - Invalid token!")
    except discord.ConnectionClosed:
        logger.error("Connection to Discord was closed!")
    except Exception as e:
        logger.error(f"Unexpected error starting bot: {e}")
        import traceback
        logger.error(traceback.format_exc())