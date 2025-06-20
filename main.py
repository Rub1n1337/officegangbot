
import discord
from discord.ext import commands
from webserver import keep_alive
import config
import sqlite3
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
import threading
import psutil

# Enhanced logging configuration
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger('BrawlStarsBot')

class ServerSettings:
    """Handles all server-specific settings and configurations"""
    
    def __init__(self, file_path='server_settings.json'):
        self.file_path = Path(file_path)
        self.settings = self._load_settings()
        self.default_prefix = '!'

    def _load_settings(self):
        """Load settings from JSON file"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.error("Error loading settings file, using defaults")
        return {}

    def _save_settings(self):
        """Save settings to JSON file"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def get_guild_settings(self, guild_id):
        """Get all settings for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {
                'prefix': self.default_prefix,
                'setup_complete': False
            }
            self._save_settings()
        return self.settings[guild_id]

    def update_guild_settings(self, guild_id, **kwargs):
        """Update guild settings"""
        guild_id = str(guild_id)
        settings = self.get_guild_settings(guild_id)
        settings.update(kwargs)
        self._save_settings()

    def get_prefix(self, guild_id):
        """Get command prefix for guild"""
        return self.get_guild_settings(guild_id).get('prefix', self.default_prefix)

    def get_channel(self, guild_id, channel_type):
        """Get specific channel ID for guild"""
        return self.get_guild_settings(guild_id).get(f'{channel_type}_channel')

    def is_setup_complete(self, guild_id):
        """Check if guild setup is complete"""
        return self.get_guild_settings(guild_id).get('setup_complete', False)

class HealthMonitor:
    """Monitors bot health and performance"""
    
    def __init__(self, bot, check_interval=300):
        self.bot = bot
        self.check_interval = check_interval
        self.last_heartbeat = time.time()
        self.is_running = True
        
    def start_monitoring(self):
        """Start health monitoring in background thread"""
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Health monitoring started")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self.last_heartbeat = time.time()
                
                if self.bot.is_ready():
                    logger.info(f"Bot health check: OK - {len(self.bot.guilds)} guilds")
                else:
                    logger.warning("Bot health check: Bot not ready")
                    
                # Check memory usage
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 80:
                    logger.warning(f"High memory usage: {memory_percent}%")
                    
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                time.sleep(60)

class EmbedHelper:
    """Helper class for creating consistent embeds"""
    
    @staticmethod
    def create_success_embed(title, description, **fields):
        """Create a success embed"""
        embed = discord.Embed(title=title, description=description, color=discord.Color.green())
        for name, value in fields.items():
            embed.add_field(name=name.replace('_', ' ').title(), value=value, inline=False)
        return embed
    
    @staticmethod
    def create_error_embed(title, description):
        """Create an error embed"""
        return discord.Embed(title=title, description=description, color=discord.Color.red())
    
    @staticmethod
    def create_info_embed(title, description, **fields):
        """Create an info embed"""
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        for name, value in fields.items():
            embed.add_field(name=name.replace('_', ' ').title(), value=value, inline=False)
        return embed

    @staticmethod
    def create_punishment_embed(action, member, moderator, reason, duration=None):
        """Create a punishment logging embed"""
        embed = discord.Embed(color=discord.Color.orange())
        embed.add_field(name=f"✅ {action.title()}", value=f"{member.mention} has been {action.lower()}", inline=False)
        embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        if duration:
            embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
        embed.timestamp = datetime.utcnow()
        return embed

class ModeratorBot(commands.Bot):
    """Main bot class with enhanced functionality"""
    
    def __init__(self):
        intents = discord.Intents.all()
        self.server_settings = ServerSettings()
        
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None  # We'll create a custom help command
        )
        
        self.db_path = 'bot_database.db'
        self.embed_helper = EmbedHelper()
        self.setup_sessions = {}  # Track ongoing setup sessions

    async def _get_prefix(self, bot, message):
        """Dynamic prefix getter"""
        if not message.guild:
            return self.server_settings.default_prefix
        return self.server_settings.get_prefix(message.guild.id)

    async def setup_hook(self):
        """Initialize bot components"""
        self._init_database()
        self.health_monitor = HealthMonitor(self)
        self.health_monitor.start_monitoring()
        logger.info('Bot setup completed')

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            # Ensure database directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path, timeout=30.0) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('PRAGMA synchronous=NORMAL')
                db.execute('PRAGMA cache_size=10000')
                db.execute('PRAGMA temp_store=memory')
                
                # Create warnings table with guild_id
                db.execute('''
                    CREATE TABLE IF NOT EXISTS warnings (
                        user_id INTEGER,
                        guild_id INTEGER,
                        count INTEGER,
                        PRIMARY KEY (user_id, guild_id)
                    )
                ''')
                db.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            # Create a fallback in-memory database
            try:
                self.db_path = ':memory:'
                with sqlite3.connect(self.db_path) as db:
                    db.execute('''
                        CREATE TABLE warnings (
                            user_id INTEGER,
                            guild_id INTEGER,
                            count INTEGER,
                            PRIMARY KEY (user_id, guild_id)
                        )
                    ''')
                    db.commit()
                logger.warning("Using in-memory database as fallback")
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback database: {fallback_error}")

    async def on_ready(self):
        """Bot ready event"""
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game('Moderating servers')
        )
        logger.info(f'Bot ready as {self.user} in {len(self.guilds)} guilds')
        print(f'Bot ready as {self.user}')

    async def on_guild_join(self, guild):
        """Handle joining a new guild"""
        await self._send_welcome_message(guild)

    async def _send_welcome_message(self, guild):
        """Send comprehensive welcome message"""
        # Find appropriate channel
        channel = guild.system_channel
        if not channel or not channel.permissions_for(guild.me).send_messages:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
        
        if not channel:
            logger.error(f"No accessible channel in {guild.name}")
            return

        try:
            # Welcome embed
            welcome_embed = self.embed_helper.create_info_embed(
                "🎉 Welcome to Your New Moderation Bot!",
                f"Hello {guild.owner.mention if guild.owner else 'Server Owner'} and welcome to **{guild.name}**!",
                features="• **Moderation Commands**: Mute, kick, ban, warn members\n"
                        "• **Auto-Moderation**: 3-strike warning system\n"
                        "• **Welcome System**: Customizable welcome messages\n"
                        "• **Server Setup**: Easy configuration system\n"
                        "• **Message Management**: Bulk delete capabilities",
                setup_instructions="1. Use `!setup` to configure the bot\n"
                                  "2. Follow the interactive setup process\n"
                                  "3. Customize settings as needed"
            )
            
            await channel.send(embed=welcome_embed)
            logger.info(f"Welcome message sent to {guild.name}")
            
        except Exception as e:
            logger.error(f"Error sending welcome message to {guild.name}: {e}")

    async def _log_to_channel(self, guild, embed, channel_type='punishment'):
        """Log action to appropriate channel"""
        channel_id = self.server_settings.get_channel(guild.id, channel_type)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to log to {channel_type} channel: {e}")

    # === SETUP COMMANDS ===
    
    @commands.command(name='setup')
    @commands.has_permissions(administrator=True)
    async def start_setup(self, ctx):
        """Start interactive server setup"""
        if ctx.guild.id in self.setup_sessions:
            await ctx.send("⚠️ Setup already in progress!")
            return

        self.setup_sessions[ctx.guild.id] = {
            'step': 'punishment_channel',
            'settings': {}
        }

        embed = self.embed_helper.create_info_embed(
            "🚀 Server Setup",
            "Let's configure your server step by step!",
            step_1="**Punishment Channel Setup**\nWould you like a channel for logging moderation actions?\nReply with `yes` or `no`"
        )
        embed.set_footer(text="Type 'cancel' to stop setup")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle setup process messages"""
        if message.author.bot or not message.guild:
            return
            
        guild_id = message.guild.id
        if guild_id not in self.setup_sessions:
            return
            
        if not message.author.guild_permissions.administrator:
            return

        content = message.content.lower().strip()
        
        if content == 'cancel':
            del self.setup_sessions[guild_id]
            await message.channel.send("❌ Setup cancelled.")
            return

        await self._handle_setup_step(message)

    async def _handle_setup_step(self, message):
        """Handle individual setup steps"""
        session = self.setup_sessions[message.guild.id]
        content = message.content.lower().strip()
        
        try:
            if session['step'] == 'punishment_channel':
                if content in ['yes', 'y']:
                    embed = self.embed_helper.create_info_embed(
                        "Create Punishment Channel",
                        "Please create a channel named `#punishments` then type: `done`"
                    )
                    await message.channel.send(embed=embed)
                    session['step'] = 'confirm_punishment_channel'
                    session['settings']['wants_punishment'] = True
                elif content in ['no', 'n']:
                    session['settings']['wants_punishment'] = False
                    await self._move_to_welcome_setup(message, session)
                else:
                    await message.channel.send("Please reply with `yes` or `no`")
                    
            elif session['step'] == 'confirm_punishment_channel':
                if content == 'done':
                    channel = discord.utils.get(message.guild.channels, name='punishments')
                    if channel:
                        session['settings']['punishment_channel'] = channel.id
                        await message.channel.send("✅ Punishment channel configured!")
                        await self._move_to_welcome_setup(message, session)
                    else:
                        await message.channel.send("❌ Channel `#punishments` not found. Please create it first.")
                        
            elif session['step'] == 'welcome_channel':
                if content in ['yes', 'y']:
                    embed = self.embed_helper.create_info_embed(
                        "Welcome Channel Setup",
                        "Please mention the channel for welcome messages.\nExample: `#general`"
                    )
                    await message.channel.send(embed=embed)
                    session['step'] = 'set_welcome_channel'
                    session['settings']['wants_welcome'] = True
                elif content in ['no', 'n']:
                    session['settings']['wants_welcome'] = False
                    await self._finalize_setup(message, session)
                else:
                    await message.channel.send("Please reply with `yes` or `no`")
                    
            elif session['step'] == 'set_welcome_channel':
                # Extract channel mention
                if message.channel_mentions:
                    channel = message.channel_mentions[0]
                    session['settings']['welcome_channel'] = channel.id
                    await message.channel.send(f"✅ Welcome channel set to {channel.mention}")
                    await self._finalize_setup(message, session)
                else:
                    await message.channel.send("Please mention a channel (e.g., #general)")
                    
        except Exception as e:
            logger.error(f"Setup error: {e}")
            await message.channel.send("❌ An error occurred. Please try again.")

    async def _move_to_welcome_setup(self, message, session):
        """Move to welcome message setup"""
        session['step'] = 'welcome_channel'
        embed = self.embed_helper.create_info_embed(
            "Welcome Messages",
            "Would you like to enable welcome messages for new members?\nReply with `yes` or `no`"
        )
        await message.channel.send(embed=embed)

    async def _finalize_setup(self, message, session):
        """Complete setup process"""
        try:
            settings = session['settings']
            guild_id = message.guild.id
            
            # Update server settings
            updates = {'setup_complete': True}
            if settings.get('punishment_channel'):
                updates['punishment_channel'] = settings['punishment_channel']
            if settings.get('welcome_channel'):
                updates['welcome_channel'] = settings['welcome_channel']
                updates['welcome_enabled'] = True
                updates['welcome_message'] = '{user} Welcome to {server}! Please read the rules.'
            
            self.server_settings.update_guild_settings(guild_id, **updates)
            
            # Create summary
            summary_parts = []
            if settings.get('wants_punishment'):
                summary_parts.append(f"✅ Punishment logging: <#{settings['punishment_channel']}>")
            if settings.get('wants_welcome'):
                summary_parts.append(f"✅ Welcome messages: <#{settings['welcome_channel']}>")
            
            embed = self.embed_helper.create_success_embed(
                "🎉 Setup Complete!",
                "Your server has been successfully configured!",
                configured_features="\n".join(summary_parts) if summary_parts else "Basic setup completed",
                next_steps="• Use `!help` to see all commands\n"
                          "• Use `!prefix <new_prefix>` to change command prefix\n"
                          "• Use `!welcome` commands to customize welcome messages"
            )
            
            await message.channel.send(embed=embed)
            del self.setup_sessions[guild_id]
            logger.info(f"Setup completed for {message.guild.name}")
            
        except Exception as e:
            logger.error(f"Error finalizing setup: {e}")
            await message.channel.send("❌ Error saving settings. Please contact support.")

    # === MODERATION COMMANDS ===
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: int, *, reason: str):
        """Mute a member for specified duration (in minutes)"""
            
        try:
            # Use Discord's built-in timeout feature
            timeout_duration = duration * 60  # Convert to seconds
            await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=timeout_duration), reason=reason)
            
            embed = self.embed_helper.create_punishment_embed(
                "Muted", member, ctx.author, reason, duration
            )
            
            await self._log_to_channel(ctx.guild, embed)
            await ctx.send(f"✅ {member.mention} has been muted for {duration} minutes.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to mute this member.")
        except Exception as e:
            logger.error(f"Mute error: {e}")
            await ctx.send("❌ Failed to mute member.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Remove timeout from a member"""
        try:
            await member.timeout(None)
            
            embed = self.embed_helper.create_punishment_embed(
                "Unmuted", member, ctx.author, "Manual unmute"
            )
            
            await self._log_to_channel(ctx.guild, embed)
            await ctx.send(f"✅ {member.mention} has been unmuted.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unmute this member.")
        except Exception as e:
            logger.error(f"Unmute error: {e}")
            await ctx.send("❌ Failed to unmute member.")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str):
        """Kick a member from the server"""
        try:
            await member.kick(reason=reason)
            
            embed = self.embed_helper.create_punishment_embed(
                "Kicked", member, ctx.author, reason
            )
            
            await self._log_to_channel(ctx.guild, embed)
            await ctx.send(f"✅ {member.mention} has been kicked.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick this member.")
        except Exception as e:
            logger.error(f"Kick error: {e}")
            await ctx.send("❌ Failed to kick member.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str):
        """Ban a member from the server"""
        try:
            await member.ban(reason=reason)
            
            embed = self.embed_helper.create_punishment_embed(
                "Banned", member, ctx.author, reason
            )
            
            await self._log_to_channel(ctx.guild, embed)
            await ctx.send(f"✅ {member.mention} has been banned.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this member.")
        except Exception as e:
            logger.error(f"Ban error: {e}")
            await ctx.send("❌ Failed to ban member.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, member_name: str):
        """Unban a member by username"""
        try:
            banned_users = [entry async for entry in ctx.guild.bans()]
            
            for ban_entry in banned_users:
                user = ban_entry.user
                if str(user).lower() == member_name.lower():
                    await ctx.guild.unban(user)
                    
                    embed = self.embed_helper.create_punishment_embed(
                        "Unbanned", user, ctx.author, "Manual unban"
                    )
                    
                    await self._log_to_channel(ctx.guild, embed)
                    await ctx.send(f"✅ {user} has been unbanned.")
                    return
                    
            await ctx.send("❌ User not found in ban list.")
            
        except Exception as e:
            logger.error(f"Unban error: {e}")
            await ctx.send("❌ Failed to unban user.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str):
        """Warn a member (3 warnings = automatic ban)"""
        try:
            with sqlite3.connect(self.db_path) as db:
                # Get current warning count
                cur = db.execute(
                    'SELECT count FROM warnings WHERE user_id = ? AND guild_id = ?',
                    (member.id, ctx.guild.id)
                )
                result = cur.fetchone()
                
                if result:
                    new_count = result[0] + 1
                    db.execute(
                        'UPDATE warnings SET count = ? WHERE user_id = ? AND guild_id = ?',
                        (new_count, member.id, ctx.guild.id)
                    )
                else:
                    new_count = 1
                    db.execute(
                        'INSERT INTO warnings (user_id, guild_id, count) VALUES (?, ?, ?)',
                        (member.id, ctx.guild.id, new_count)
                    )
                
                db.commit()
                
                embed = self.embed_helper.create_punishment_embed(
                    f"Warning #{new_count}", member, ctx.author, reason
                )
                
                await self._log_to_channel(ctx.guild, embed)
                
                if new_count >= 3:
                    # Auto-ban on 3rd warning
                    await member.ban(reason=f"Auto-ban: 3 warnings reached. Last reason: {reason}")
                    await ctx.send(f"⚠️ {member.mention} has been **banned** for receiving 3 warnings!")
                else:
                    await ctx.send(f"⚠️ {member.mention} has been warned! ({new_count}/3 warnings)")
                
        except Exception as e:
            logger.error(f"Warn error: {e}")
            await ctx.send("❌ Failed to warn member.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10):
        """Clear specified number of messages"""
        if amount > 100:
            await ctx.send("❌ Cannot clear more than 100 messages at once.")
            return
            
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
            await ctx.send(f"✅ Cleared {len(deleted) - 1} messages.", delete_after=3)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages.")
        except Exception as e:
            logger.error(f"Clear error: {e}")
            await ctx.send("❌ Failed to clear messages.")

    # === UTILITY COMMANDS ===
    
    @commands.command()
    async def info(self, ctx, member: discord.Member = None):
        """Show information about a member"""
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"User Information - {member.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Joined Server", 
                       value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", 
                       inline=True)
        embed.add_field(name="Account Created", 
                       value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), 
                       inline=True)
        
        roles = [role.name for role in member.roles[1:]]  # Skip @everyone
        embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx, new_prefix: str = None):
        """View or change the command prefix"""
        if not new_prefix:
            current_prefix = self.server_settings.get_prefix(ctx.guild.id)
            await ctx.send(f"Current prefix: `{current_prefix}`")
            return
            
        self.server_settings.update_guild_settings(ctx.guild.id, prefix=new_prefix)
        await ctx.send(f"✅ Prefix changed to: `{new_prefix}`")

    # === WELCOME SYSTEM ===
    
    @commands.group(name='welcome', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        """Welcome message management"""
        settings = self.server_settings.get_guild_settings(ctx.guild.id)
        
        embed = self.embed_helper.create_info_embed(
            "🎉 Welcome System",
            "Current welcome message configuration:",
            status="✅ Enabled" if settings.get('welcome_enabled') else "❌ Disabled",
            channel=f"<#{settings.get('welcome_channel')}>" if settings.get('welcome_channel') else "Not set",
            message=settings.get('welcome_message', 'Default message'),
            commands="`!welcome enable/disable` - Toggle welcome messages\n"
                    "`!welcome channel #channel` - Set welcome channel\n"
                    "`!welcome message <text>` - Set welcome message\n"
                    "`!welcome test` - Test welcome message"
        )
        
        await ctx.send(embed=embed)

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx):
        """Enable welcome messages"""
        self.server_settings.update_guild_settings(ctx.guild.id, welcome_enabled=True)
        await ctx.send("✅ Welcome messages enabled!")

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        """Disable welcome messages"""
        self.server_settings.update_guild_settings(ctx.guild.id, welcome_enabled=False)
        await ctx.send("❌ Welcome messages disabled!")

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set welcome channel"""
        self.server_settings.update_guild_settings(ctx.guild.id, welcome_channel=channel.id)
        await ctx.send(f"✅ Welcome channel set to {channel.mention}")

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def message(self, ctx, *, message: str):
        """Set welcome message (use {user} for mention, {server} for server name)"""
        self.server_settings.update_guild_settings(ctx.guild.id, welcome_message=message)
        await ctx.send("✅ Welcome message updated!")

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def test(self, ctx):
        """Test the welcome message"""
        settings = self.server_settings.get_guild_settings(ctx.guild.id)
        
        if not settings.get('welcome_enabled'):
            await ctx.send("❌ Welcome messages are disabled.")
            return
            
        message = settings.get('welcome_message', '{user} Welcome to {server}!')
        formatted_message = message.replace('{user}', ctx.author.mention).replace('{server}', ctx.guild.name)
        
        await ctx.send(f"**[TEST]** {formatted_message}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send welcome message to new members"""
        settings = self.server_settings.get_guild_settings(member.guild.id)
        
        if not settings.get('welcome_enabled'):
            return
            
        channel_id = settings.get('welcome_channel')
        if not channel_id:
            return
            
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
            
        try:
            message = settings.get('welcome_message', '{user} Welcome to {server}!')
            formatted_message = message.replace('{user}', member.mention).replace('{server}', member.guild.name)
            await channel.send(formatted_message)
            logger.info(f"Welcome message sent for {member} in {member.guild.name}")
        except Exception as e:
            logger.error(f"Failed to send welcome message: {e}")

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

    @commands.command()
    async def ping(self, ctx):
        """Test if the bot is responding"""
        await ctx.send("🏓 Pong! Bot is working!")

    @commands.command()
    async def test(self, ctx):
        """Test command to verify bot functionality"""
        embed = self.embed_helper.create_success_embed(
            "✅ Bot Test",
            "All systems operational!",
            prefix=f"Current prefix: `{await self._get_prefix(self, ctx.message)}`",
            permissions="Bot has basic permissions",
            database="Database connection: ✅"
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def help(self, ctx, command_name: str = None):
        """Show help information"""
        if command_name:
            # Show help for specific command
            command = self.get_command(command_name)
            if command:
                embed = self.embed_helper.create_info_embed(
                    f"Help: {command.name}",
                    command.help or "No description available",
                    usage=f"`{ctx.prefix}{command.name} {command.signature}`"
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Command not found.")
            return
        
        # Show general help
        embed = self.embed_helper.create_info_embed(
            "🤖 Bot Help",
            "Here are all available commands:",
            moderation_commands="`mute` `unmute` `kick` `ban` `unban` `warn` `clear`",
            utility_commands="`info` `prefix` `help`",
            setup_commands="`setup`",
            welcome_commands="`welcome` (with subcommands)",
            usage_tip=f"Use `{ctx.prefix}help <command>` for detailed help on a specific command"
        )
        
        await ctx.send(embed=embed)

# Create and run bot
bot = ModeratorBot()

# Start webserver and bot
if __name__ == "__main__":
    keep_alive()
    
    try:
        logger.info("Starting Discord bot...")
        bot.run(config.TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("Failed to login - Invalid token!")
    except Exception as e:
        logger.error(f"Bot startup error: {e}")
        import traceback
        logger.error(traceback.format_exc())
