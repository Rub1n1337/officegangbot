
import discord
from discord.ext import commands
import json
import logging

logger = logging.getLogger('BrawlStarsBot')

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_data_file = 'welcome_settings.json'
        self.welcome_settings = self._load_welcome_settings()

    def _load_welcome_settings(self):
        """Load welcome settings from JSON file"""
        try:
            with open(self.welcome_data_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.error("Error reading welcome settings file")
            return {}

    def _save_welcome_settings(self):
        """Save welcome settings to JSON file"""
        try:
            with open(self.welcome_data_file, 'w') as f:
                json.dump(self.welcome_settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving welcome settings: {e}")

    def get_guild_welcome_settings(self, guild_id):
        """Get welcome settings for a specific guild"""
        guild_id = str(guild_id)
        if guild_id not in self.welcome_settings:
            # Set default settings
            self.welcome_settings[guild_id] = {
                'enabled': True,
                'channel_id': None,
                'message': '@user Welcome to the server! Go to #rules.'
            }
            self._save_welcome_settings()
        return self.welcome_settings[guild_id]

    def update_guild_welcome_settings(self, guild_id, **kwargs):
        """Update welcome settings for a specific guild"""
        guild_id = str(guild_id)
        settings = self.get_guild_welcome_settings(guild_id)
        settings.update(kwargs)
        self._save_welcome_settings()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send welcome message when a new member joins"""
        try:
            settings = self.get_guild_welcome_settings(member.guild.id)
            
            # Check if welcome messages are enabled
            if not settings['enabled']:
                return
            
            # Get the welcome channel
            channel_id = settings['channel_id']
            if not channel_id:
                # Try to use system channel or first available text channel
                channel = member.guild.system_channel
                if not channel or not channel.permissions_for(member.guild.me).send_messages:
                    for ch in member.guild.text_channels:
                        if ch.permissions_for(member.guild.me).send_messages:
                            channel = ch
                            break
            else:
                channel = member.guild.get_channel(channel_id)
            
            if not channel:
                logger.warning(f"No welcome channel found for guild {member.guild.name}")
                return
            
            # Format the welcome message
            message = settings['message']
            
            # Replace variables
            message = message.replace('@user', member.mention)
            message = message.replace('{user}', member.mention)
            message = message.replace('{server}', member.guild.name)
            message = message.replace('{member}', member.display_name)
            
            # Send the welcome message
            await channel.send(message)
            logger.info(f"Sent welcome message to {member} in {member.guild.name}")
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    @commands.group(name='welcome', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        """Welcome message management commands"""
        settings = self.get_guild_welcome_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="🎉 Welcome Message Settings",
            color=discord.Color.blue()
        )
        
        # Status
        status = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Channel
        channel_text = "System Channel (Default)" if not settings['channel_id'] else f"<#{settings['channel_id']}>"
        embed.add_field(name="Channel", value=channel_text, inline=True)
        
        # Message preview
        preview_message = settings['message'].replace('@user', ctx.author.mention)
        preview_message = preview_message.replace('{user}', ctx.author.mention)
        preview_message = preview_message.replace('{server}', ctx.guild.name)
        preview_message = preview_message.replace('{member}', ctx.author.display_name)
        
        embed.add_field(name="Current Message", value=preview_message, inline=False)
        
        # Commands help
        commands_help = (
            "`!welcome enable` - Enable welcome messages\n"
            "`!welcome disable` - Disable welcome messages\n"
            "`!welcome setchannel #channel` - Set welcome channel\n"
            "`!welcome setmessage <message>` - Set custom message\n"
            "`!welcome test` - Test the welcome message"
        )
        embed.add_field(name="Available Commands", value=commands_help, inline=False)
        
        # Variables help
        variables_help = (
            "`@user` or `{user}` - Mentions the new member\n"
            "`{server}` - Server name\n"
            "`{member}` - Member's display name"
        )
        embed.add_field(name="Available Variables", value=variables_help, inline=False)
        
        await ctx.send(embed=embed)

    @welcome.command(name='enable')
    @commands.has_permissions(administrator=True)
    async def welcome_enable(self, ctx):
        """Enable welcome messages"""
        self.update_guild_welcome_settings(ctx.guild.id, enabled=True)
        
        embed = discord.Embed(
            title="✅ Welcome Messages Enabled",
            description="New members will now receive welcome messages!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @welcome.command(name='disable')
    @commands.has_permissions(administrator=True)
    async def welcome_disable(self, ctx):
        """Disable welcome messages"""
        self.update_guild_welcome_settings(ctx.guild.id, enabled=False)
        
        embed = discord.Embed(
            title="❌ Welcome Messages Disabled",
            description="New members will no longer receive welcome messages.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @welcome.command(name='setchannel')
    @commands.has_permissions(administrator=True)
    async def welcome_setchannel(self, ctx, channel: discord.TextChannel):
        """Set the welcome message channel"""
        # Check if bot has permission to send messages in the channel
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send("❌ I don't have permission to send messages in that channel!")
            return
        
        self.update_guild_welcome_settings(ctx.guild.id, channel_id=channel.id)
        
        embed = discord.Embed(
            title="✅ Welcome Channel Updated",
            description=f"Welcome messages will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @welcome.command(name='setmessage')
    @commands.has_permissions(administrator=True)
    async def welcome_setmessage(self, ctx, *, message):
        """Set a custom welcome message"""
        if len(message) > 1000:
            await ctx.send("❌ Welcome message is too long! Please keep it under 1000 characters.")
            return
        
        self.update_guild_welcome_settings(ctx.guild.id, message=message)
        
        # Show preview
        preview_message = message.replace('@user', ctx.author.mention)
        preview_message = preview_message.replace('{user}', ctx.author.mention)
        preview_message = preview_message.replace('{server}', ctx.guild.name)
        preview_message = preview_message.replace('{member}', ctx.author.display_name)
        
        embed = discord.Embed(
            title="✅ Welcome Message Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Preview:", value=preview_message, inline=False)
        embed.add_field(
            name="Tip:", 
            value="Use `@user` or `{user}` to mention new members, `{server}` for server name, `{member}` for display name",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @welcome.command(name='reset')
    @commands.has_permissions(administrator=True)
    async def welcome_reset(self, ctx):
        """Reset welcome message to default"""
        default_message = '@user Welcome to the server! Go to #rules.'
        self.update_guild_welcome_settings(ctx.guild.id, message=default_message)
        
        embed = discord.Embed(
            title="🔄 Welcome Message Reset",
            description=f"Welcome message has been reset to default:\n\n{default_message}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @welcome.command(name='test')
    @commands.has_permissions(administrator=True)
    async def welcome_test(self, ctx):
        """Test the welcome message with yourself"""
        settings = self.get_guild_welcome_settings(ctx.guild.id)
        
        if not settings['enabled']:
            await ctx.send("❌ Welcome messages are currently disabled. Enable them first with `!welcome enable`")
            return
        
        # Get the welcome channel
        channel_id = settings['channel_id']
        if not channel_id:
            channel = ctx.channel
        else:
            channel = ctx.guild.get_channel(channel_id)
            if not channel:
                await ctx.send("❌ Welcome channel not found! Please set a valid channel.")
                return
        
        # Format the test message
        message = settings['message']
        message = message.replace('@user', ctx.author.mention)
        message = message.replace('{user}', ctx.author.mention)
        message = message.replace('{server}', ctx.guild.name)
        message = message.replace('{member}', ctx.author.display_name)
        
        # Send test message
        embed = discord.Embed(
            title="🧪 Welcome Message Test",
            description="Here's how the welcome message will look:",
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)
        await channel.send(f"**[TEST]** {message}")

    @welcome_setchannel.error
    async def welcome_setchannel_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Please mention a channel. Example: `!welcome setchannel #general`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid channel. Please mention a valid text channel.")

    @welcome_setmessage.error
    async def welcome_setmessage_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Please provide a message. Example: `!welcome setmessage Welcome to our awesome server!`")

def setup(bot):
    bot.add_cog(WelcomeSystem(bot))
