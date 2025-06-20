
import asyncio
import discord
from discord.ext import commands
import logging
from utils.server_settings import ServerSettings

# Setup logging
logger = logging.getLogger('BrawlStarsBot')

class GuildSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_settings = ServerSettings()
        self.setup_sessions = {}  # Track ongoing setup sessions

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Send comprehensive welcome message when bot joins a server"""
        try:
            # Find the best channel to send the welcome message
            target_channel = guild.system_channel
            if not target_channel or not target_channel.permissions_for(guild.me).send_messages:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break

            if not target_channel:
                logger.error(f"No accessible text channel found in {guild.name}")
                return

            # Create welcome embed
            welcome_embed = discord.Embed(
                title="🎉 Welcome to Your New Moderation Bot!",
                description=f"Hello {guild.owner.mention if guild.owner else 'Server Owner'} and all members of **{guild.name}**!",
                color=discord.Color.blue()
            )

            welcome_embed.add_field(
                name="🤖 What I Do",
                value="I'm a comprehensive moderation bot designed to help manage your server efficiently and keep your community safe!",
                inline=False
            )

            welcome_embed.add_field(
                name="✨ Main Features",
                value="• **Moderation Commands**: Mute, kick, ban, warn members\n"
                      "• **Auto-Moderation**: Automatic punishments and logging\n"
                      "• **Server Setup**: Easy configuration system\n"
                      "• **Warning System**: 3-strike system with auto-ban\n"
                      "• **Message Management**: Bulk delete and content filtering\n"
                      "• **User Information**: Detailed member profiles\n"
                      "• **Custom Prefixes**: Personalize command prefixes",
                inline=False
            )

            # Setup instructions
            setup_embed = discord.Embed(
                title="🔧 Getting Started",
                description="Let's get your server set up! Follow these simple steps:",
                color=discord.Color.green()
            )

            setup_embed.add_field(
                name="Step 1: Create Setup Channel",
                value="Create a text channel named `#bot-setup` (only admins should have access)",
                inline=False
            )

            setup_embed.add_field(
                name="Step 2: Start Setup",
                value="In the `#bot-setup` channel, type either:\n`!bot-setup` or `!botsetup`",
                inline=False
            )

            setup_embed.add_field(
                name="Step 3: Follow the Guide",
                value="I'll guide you through each step of the configuration process!",
                inline=False
            )

            setup_embed.set_footer(text="💡 Only server administrators can run the setup commands")

            await target_channel.send(embed=welcome_embed)
            await target_channel.send(embed=setup_embed)
            
            logger.info(f"Sent welcome message to {guild.name}")
            
        except Exception as e:
            logger.error(f"Error sending welcome message to {guild.name}: {e}")

    @commands.command(name="bot-setup", aliases=["botsetup"])
    @commands.has_permissions(administrator=True)
    async def start_setup(self, ctx):
        """Start the step-by-step server setup process"""
        if ctx.channel.name != "bot-setup":
            await ctx.send("❌ This command can only be used in the `#bot-setup` channel!")
            return

        if ctx.guild.id in self.setup_sessions:
            await ctx.send("⚠️ A setup session is already in progress! Please complete it first.")
            return

        # Initialize setup session
        self.setup_sessions[ctx.guild.id] = {
            'step': 'punishments_channel',
            'channel': ctx.channel,
            'settings': {}
        }

        embed = discord.Embed(
            title="🚀 Server Setup Started!",
            description="I'll guide you through setting up your server step by step.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Step 1: Punishments Channel",
            value="Would you like to enable a punishments channel? This channel will log all moderation actions (mutes, kicks, bans, warnings).\n\n"
                  "**Reply with:** `yes` or `no`",
            inline=False
        )

        embed.set_footer(text="You can cancel the setup at any time by typing 'cancel'")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle setup process messages"""
        if message.author.bot:
            return
            
        guild_id = message.guild.id
        if guild_id not in self.setup_sessions:
            return
            
        session = self.setup_sessions[guild_id]
        if message.channel != session['channel']:
            return
            
        if not message.author.guild_permissions.administrator:
            return

        content = message.content.lower().strip()
        
        if content == 'cancel':
            del self.setup_sessions[guild_id]
            await message.channel.send("❌ Setup cancelled. You can restart it anytime with `!bot-setup`")
            return

        await self.handle_setup_step(message, session)

    async def handle_setup_step(self, message, session):
        """Handle individual setup steps"""
        step = session['step']
        content = message.content.lower().strip()
        guild = message.guild

        # Prevent duplicate processing
        if session.get('processing_message', False):
            return
        session['processing_message'] = True

        try:
            if step == 'punishments_channel':
                if content in ['yes', 'y']:
                    embed = discord.Embed(
                        title="✅ Punishments Channel - Yes",
                        description="Great! Let's set up your punishments channel.",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Instructions:",
                        value="1. Create a text channel named `#punishments`\n"
                              "2. Once created, type: `!set-punishment-channel #punishments`",
                        inline=False
                    )
                    await message.channel.send(embed=embed)
                    session['step'] = 'set_punishment_channel'
                    session['settings']['wants_punishments'] = True
                    
                elif content in ['no', 'n']:
                    session['settings']['wants_punishments'] = False
                    await self.move_to_next_step(message, session, 'logging_channel')
                else:
                    await message.channel.send("Please reply with `yes` or `no`")

            elif step == 'set_punishment_channel':
                if content.startswith('!set-punishment-channel'):
                    channel_mention = message.content.split()[-1]
                    if channel_mention.startswith('<#') and channel_mention.endswith('>'):
                        channel_id = int(channel_mention[2:-1])
                        channel = guild.get_channel(channel_id)
                        if channel:
                            session['settings']['punishments_channel'] = channel_id
                            await message.channel.send(f"✅ Punishments channel set to {channel.mention}")
                            await self.move_to_next_step(message, session, 'logging_channel')
                        else:
                            await message.channel.send("❌ Channel not found. Please try again.")
                    else:
                        await message.channel.send("❌ Please mention the channel like this: `!set-punishment-channel #punishments`")
                else:
                    await message.channel.send("Please use the command: `!set-punishment-channel #punishments`")

            elif step == 'logging_channel':
                if content in ['yes', 'y']:
                    embed = discord.Embed(
                        title="✅ Logging Channel - Yes",
                        description="Perfect! This will help you keep track of all bot activities.",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Instructions:",
                        value="1. Create a text channel named `#bot-logs`\n"
                              "2. Once created, type: `!set-log-channel #bot-logs`",
                        inline=False
                    )
                    await message.channel.send(embed=embed)
                    session['step'] = 'set_log_channel'
                    session['settings']['wants_logging'] = True
                    
                elif content in ['no', 'n']:
                    session['settings']['wants_logging'] = False
                    await self.move_to_next_step(message, session, 'auto_roles')
                else:
                    await message.channel.send("Please reply with `yes` or `no`")

            elif step == 'set_log_channel':
                if content.startswith('!set-log-channel'):
                    channel_mention = message.content.split()[-1]
                    if channel_mention.startswith('<#') and channel_mention.endswith('>'):
                        channel_id = int(channel_mention[2:-1])
                        channel = guild.get_channel(channel_id)
                        if channel:
                            session['settings']['log_channel'] = channel_id
                            await message.channel.send(f"✅ Log channel set to {channel.mention}")
                            await self.move_to_next_step(message, session, 'auto_roles')
                        else:
                            await message.channel.send("❌ Channel not found. Please try again.")
                    else:
                        await message.channel.send("❌ Please mention the channel like this: `!set-log-channel #bot-logs`")
                else:
                    await message.channel.send("Please use the command: `!set-log-channel #bot-logs`")

            elif step == 'auto_roles':
                if content in ['yes', 'y']:
                    embed = discord.Embed(
                        title="✅ Auto Roles - Yes",
                        description="Great! Auto roles will be given to new members automatically.",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Instructions:",
                        value="What role should be given to new members when they join?\n"
                              "Type: `!set-auto-role @RoleName` (mention the role)",
                        inline=False
                    )
                    await message.channel.send(embed=embed)
                    session['step'] = 'set_auto_role'
                    session['settings']['wants_auto_roles'] = True
                    
                elif content in ['no', 'n']:
                    session['settings']['wants_auto_roles'] = False
                    await self.finalize_setup(message, session)
                else:
                    await message.channel.send("Please reply with `yes` or `no`")

            elif step == 'set_auto_role':
                if content.startswith('!set-auto-role'):
                    role_mention = message.content.split(maxsplit=1)[-1]
                    if role_mention.startswith('<@&') and role_mention.endswith('>'):
                        role_id = int(role_mention[3:-1])
                        role = guild.get_role(role_id)
                        if role:
                            session['settings']['auto_role'] = role_id
                            await message.channel.send(f"✅ Auto role set to {role.mention}")
                            await self.finalize_setup(message, session)
                        else:
                            await message.channel.send("❌ Role not found. Please try again.")
                    else:
                        await message.channel.send("❌ Please mention the role like this: `!set-auto-role @Member`")
                else:
                    await message.channel.send("Please use the command: `!set-auto-role @RoleName`")

        except Exception as e:
            logger.error(f"Error in setup step {step}: {e}")
            await message.channel.send("❌ An error occurred. Please try again or contact support.")
        finally:
            session['processing_message'] = False

    async def move_to_next_step(self, message, session, next_step):
        """Move to the next step in setup"""
        session['step'] = next_step
        
        if next_step == 'logging_channel':
            embed = discord.Embed(
                title="Step 2: Logging Channel",
                description="Would you like to enable a logging channel? This will log general bot activities and events.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Reply with:",
                value="`yes` or `no`",
                inline=False
            )
            await message.channel.send(embed=embed)
            
        elif next_step == 'auto_roles':
            embed = discord.Embed(
                title="Step 3: Auto Roles",
                description="Would you like to enable auto roles? New members will automatically receive a specified role when they join.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Reply with:",
                value="`yes` or `no`",
                inline=False
            )
            await message.channel.send(embed=embed)

    @commands.command(name="set-punishment-channel")
    @commands.has_permissions(administrator=True)
    async def set_punishment_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the punishment channel for this server"""
        guild_id = ctx.guild.id
        
        # Check if this is being used during setup - if so, skip command processing
        if guild_id in self.setup_sessions:
            session = self.setup_sessions[guild_id]
            if session['step'] == 'set_punishment_channel' and session.get('processing', False):
                return  # Already being processed by message handler
        
        # If no channel provided, try to parse from message content
        if channel is None:
            # Extract channel mention from message content
            parts = ctx.message.content.split()
            if len(parts) >= 2:
                channel_mention = parts[-1]
                if channel_mention.startswith('<#') and channel_mention.endswith('>'):
                    try:
                        channel_id = int(channel_mention[2:-1])
                        channel = ctx.guild.get_channel(channel_id)
                    except ValueError:
                        pass
            
            if channel is None:
                await ctx.send("❌ Please provide a valid channel. Usage: `!set-punishment-channel #channel-name`")
                return
        
        # Check if this is being used during setup (normal flow)
        if guild_id in self.setup_sessions:
            session = self.setup_sessions[guild_id]
            if session['step'] == 'set_punishment_channel':
                # This will be handled by the message handler, don't process here
                return
        
        # Regular usage outside of setup
        settings = self.server_settings.get_settings(guild_id)
        settings['punishments'] = channel.id
        self.server_settings.set_settings(guild_id, settings)
        await ctx.send(f"✅ Punishments channel updated to {channel.mention}")

    @commands.command(name="set-log-channel")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the log channel for this server"""
        guild_id = ctx.guild.id
        
        # If no channel provided, try to parse from message content
        if channel is None:
            # Extract channel mention from message content
            parts = ctx.message.content.split()
            if len(parts) >= 2:
                channel_mention = parts[-1]
                if channel_mention.startswith('<#') and channel_mention.endswith('>'):
                    try:
                        channel_id = int(channel_mention[2:-1])
                        channel = ctx.guild.get_channel(channel_id)
                    except ValueError:
                        pass
            
            if channel is None:
                await ctx.send("❌ Please provide a valid channel. Usage: `!set-log-channel #channel-name`")
                return
        
        # Check if this is being used during setup
        if guild_id in self.setup_sessions:
            session = self.setup_sessions[guild_id]
            if session['step'] == 'set_log_channel':
                session['settings']['log_channel'] = channel.id
                await ctx.send(f"✅ Log channel set to {channel.mention}")
                await self.move_to_next_step(ctx.message, session, 'auto_roles')
                return
        
        # Regular usage outside of setup
        settings = self.server_settings.get_settings(guild_id)
        settings['bot-logs'] = channel.id
        self.server_settings.set_settings(guild_id, settings)
        await ctx.send(f"✅ Log channel updated to {channel.mention}")

    @commands.command(name="set-auto-role")
    @commands.has_permissions(administrator=True)
    async def set_auto_role(self, ctx, role: discord.Role = None):
        """Set the auto role for new members"""
        guild_id = ctx.guild.id
        
        # If no role provided, try to parse from message content
        if role is None:
            # Extract role mention from message content
            parts = ctx.message.content.split()
            if len(parts) >= 2:
                role_mention = parts[-1]
                if role_mention.startswith('<@&') and role_mention.endswith('>'):
                    try:
                        role_id = int(role_mention[3:-1])
                        role = ctx.guild.get_role(role_id)
                    except ValueError:
                        pass
            
            if role is None:
                await ctx.send("❌ Please provide a valid role. Usage: `!set-auto-role @role-name`")
                return
        
        # Check if this is being used during setup
        if guild_id in self.setup_sessions:
            session = self.setup_sessions[guild_id]
            if session['step'] == 'set_auto_role':
                session['settings']['auto_role'] = role.id
                await ctx.send(f"✅ Auto role set to {role.mention}")
                await self.finalize_setup(ctx.message, session)
                return
        
        # Regular usage outside of setup
        settings = self.server_settings.get_settings(guild_id)
        settings['auto_role'] = role.id
        self.server_settings.set_settings(guild_id, settings)
        await ctx.send(f"✅ Auto role updated to {role.mention}")

    async def finalize_setup(self, message, session):
        """Complete the setup process"""
        try:
            # Save all settings
            settings = session['settings']
            guild_id = message.guild.id
            
            # Save to server settings using the correct methods
            saved_settings = {
                'bot-setup': message.channel.id,
                'setup_complete': True
            }
            
            if settings.get('punishments_channel'):
                saved_settings['punishments'] = settings['punishments_channel']
            if settings.get('log_channel'):
                saved_settings['bot-logs'] = settings['log_channel']
            if settings.get('auto_role'):
                saved_settings['auto_role'] = settings['auto_role']
            
            # Use the server_settings instance to save
            self.server_settings.set_server_channels(guild_id, saved_settings)
            
            # Create final summary
            embed = discord.Embed(
                title="🎉 Setup Complete!",
                description="Your server has been successfully configured!",
                color=discord.Color.gold()
            )
            
            summary = []
            if settings.get('wants_punishments') and settings.get('punishments_channel'):
                summary.append(f"✅ Punishments channel: <#{settings['punishments_channel']}>")
            if settings.get('wants_logging') and settings.get('log_channel'):
                summary.append(f"✅ Logging channel: <#{settings['log_channel']}>")
            if settings.get('wants_auto_roles') and settings.get('auto_role'):
                summary.append(f"✅ Auto role: <@&{settings['auto_role']}>")
                
            if summary:
                embed.add_field(
                    name="Configured Features:",
                    value="\n".join(summary),
                    inline=False
                )
            
            embed.add_field(
                name="Next Steps:",
                value="• Try using `!help` to see all available commands\n"
                      "• Use `!setprefix <prefix>` to change the command prefix\n"
                      "• Test moderation commands like `!mute`, `!warn`, `!kick`\n"
                      "• Check the documentation for advanced features",
                inline=False
            )
            
            embed.set_footer(text="Thank you for choosing our moderation bot! 🚀")
            await message.channel.send(embed=embed)
            
            # Clean up session
            del self.setup_sessions[guild_id]
            logger.info(f"Setup completed for {message.guild.name}")
            
        except Exception as e:
            logger.error(f"Error finalizing setup: {e}")
            await message.channel.send("❌ An error occurred while saving settings. Please contact support.")

    @commands.command(name="set_punishment_rules", aliases=["set-punishment-rules"])
    @commands.has_permissions(administrator=True)
    async def set_punishment_rules(self, ctx):
        """Configure automatic punishment rules"""
        embed = discord.Embed(
            title="⚙️ Punishment Rules Configuration",
            description="Current punishment rules are set to default:\n\n"
                       "• **1st Warning**: Warning logged\n"
                       "• **2nd Warning**: Warning logged\n"
                       "• **3rd Warning**: Automatic ban\n\n"
                       "These rules are automatically enforced when using the `!warn` command.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Future Features",
            value="Custom punishment rules will be available in a future update. "
                  "For now, the 3-strike warning system is active.",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name="setup-status")
    @commands.has_permissions(administrator=True)
    async def setup_status(self, ctx):
        """Check the current setup status"""
        if self.server_settings.is_setup_complete(ctx.guild.id):
            embed = discord.Embed(
                title="✅ Setup Status",
                description="Your server setup is complete!",
                color=discord.Color.green()
            )
            
            settings = self.server_settings.get_server_channels(ctx.guild.id)
            if settings:
                config_list = []
                for key, value in settings.items():
                    if key == 'punishments' and value:
                        config_list.append(f"• Punishments: <#{value}>")
                    elif key == 'bot-logs' and value:
                        config_list.append(f"• Logging: <#{value}>")
                    elif key == 'auto_role' and value:
                        config_list.append(f"• Auto Role: <@&{value}>")
                        
                if config_list:
                    embed.add_field(
                        name="Current Configuration:",
                        value="\n".join(config_list),
                        inline=False
                    )
        else:
            embed = discord.Embed(
                title="⚠️ Setup Incomplete",
                description="Your server setup is not complete. Use `!bot-setup` to start the configuration process.",
                color=discord.Color.orange()
            )
            
        await ctx.send(embed=embed)
