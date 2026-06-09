# cogs/guild_setup.py
import asyncio
import discord
from discord.ext import commands
from core.logger import logger
from core.settings_manager import SettingsManager
from cogs.utils import reply

DEFAULT_RULES_TEXT = (
    "> 1. **Be respectful** - You must respect all users, regardless of your liking towards them. Treat others the way you want to be treated.\n"
    "> 2. **No Inappropriate Language** - The use of profanity should be kept to a minimum. However, any derogatory language towards any user is prohibited.\n"
    "> 3. **No Spamming** - Do not send a lot of small messages right after each other. Do not disrupt chat by spamming.\n"
    "> 4. **No NSFW Material** - This is a community server and not meant to share pornographic/adult/other NSFW material.\n"
    "> 5. **No Advertisements** - We do not tolerate any kind of advertisements, whether it be for other communities or streams.\n"
    "> 6. **Follow the Discord Community Guidelines** - You can find them here: https://discordapp.com/guidelines\n\n"
    "> **Your presence in this server implies accepting these rules, including all further changes.**"
)
DEFAULT_WELCOME_MESSAGE = "Welcome {user.mention} to **{server.name}**! We're glad to have you."

class SetupCog(commands.Cog, name="🛠️ Server Setup"):
    """Interactive server setup for admins. Guides through prefix and log channel configuration. Uses centralized reply function for all responses and ensures thread safety for concurrent setups."""

    _active_setups = set()
    _setup_lock = asyncio.Lock()

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_manager: SettingsManager = getattr(bot, 'settings_manager', None)
        self._active_setups = set()

    def _check_settings_manager(self):
        if not self.settings_manager:
            logger.error("SettingsManager not available in SetupCog")
            return False
        return True

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined new guild: {guild.name} ({guild.id}).")
        prefix = self.settings_manager.get_setting(guild.id, 'prefix', '!')
        channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        if not channel: return
        embed = discord.Embed(title=f"👋 Hello, {guild.name}!", description="Thank you for adding me! To get started, an administrator needs to run the setup command.", color=discord.Color.blue())
        embed.add_field(name="🚀 Setup Command", value=f"In a channel of your choice, please type:\n```{prefix}setup```", inline=False)
        await channel.send(embed=embed)

    @commands.command(name="setup", description="Interactive server setup.")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def setup(self, ctx: commands.Context):
        """Guides the admin through a multi-stage interactive server setup wizard."""
        guild_id = ctx.guild.id
        async with self._setup_lock:
            if guild_id in self._active_setups:
                await reply(ctx, "A setup is already in progress for this server. Please wait for it to finish or cancel it.")
                return
            self._active_setups.add(guild_id)
        try:
            await reply(ctx, "Welcome to the setup wizard! Type `cancel` at any time to exit.\nYou can also type `back` to return to the previous step.")

            step_data = {}
            step = 1
            total_steps = 10
            while step <= total_steps:
                if step == 1:
                    await reply(ctx, f"**Step 1/{total_steps}: Command Prefix**\nPlease enter a command prefix (1-5 characters, no spaces):")
                    prefix_msg = await self._wait_for_response(ctx)
                    if not prefix_msg or prefix_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if prefix_msg.content.lower() == "back":
                        await reply(ctx, "You are at the first step.")
                        continue
                    prefix = prefix_msg.content.strip()
                    if not (1 <= len(prefix) <= 5) or " " in prefix or not prefix.isprintable():
                        await reply(ctx, "Invalid prefix. Please use 1-5 printable characters, no spaces.")
                        continue
                    step_data['prefix'] = prefix
                    step += 1

                elif step == 2:
                    await reply(ctx,
                        f"**Step 2/{total_steps}: Rules Channel**\n"
                        "> Please mention the channel for posting server rules (e.g., #rules).\n"
                        "> Here is an example rules message you can use or edit:\n"
                        f"{DEFAULT_RULES_TEXT}\n"
                        "> Type `skip` to skip this step or `back` to return to the previous step."
                    )
                    rules_channel_msg = await self._wait_for_response(ctx)
                    if not rules_channel_msg or rules_channel_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if rules_channel_msg.content.lower() == "back":
                        step -= 1
                        continue
                    if rules_channel_msg.content.lower() != "skip":
                        rules_channel = await self._extract_channel(ctx, rules_channel_msg.content)
                        if not rules_channel:
                            await reply(ctx, "> Invalid channel. Please mention a valid text channel.")
                            continue
                        step_data['rules_channel_id'] = rules_channel.id
                        step_data['rules_text'] = DEFAULT_RULES_TEXT
                        # Новый шаг: запрос emoji и роли для реакции
                        await reply(ctx, "> Please enter the emoji to use for accepting the rules (e.g. ✅):")
                        emoji_msg = await self._wait_for_response(ctx)
                        if not emoji_msg or emoji_msg.content.lower() == "cancel":
                            await reply(ctx, "Setup cancelled.")
                            return
                        emoji = emoji_msg.content.strip()
                        await reply(ctx, "> Please mention the role to give when the user reacts (e.g. @Member):")
                        role_msg = await self._wait_for_response(ctx)
                        if not role_msg or role_msg.content.lower() == "cancel":
                            await reply(ctx, "Setup cancelled.")
                            return
                        role = None
                        if role_msg.role_mentions:
                            role = role_msg.role_mentions[0]
                        else:
                            # Try to find by name
                            role_name = role_msg.content.strip().lstrip('@')
                            role = discord.utils.get(ctx.guild.roles, name=role_name)
                        if not role:
                            await reply(ctx, "> Invalid role. Please mention a valid role.")
                            continue
                        step_data['reaction_emoji'] = emoji
                        step_data['reaction_role_id'] = role.id
                        # Публикуем правила и добавляем реакцию
                        rules_message = await rules_channel.send(DEFAULT_RULES_TEXT)
                        await rules_message.add_reaction(emoji)
                        # Сохраняем параметры для reaction_roles_cog
                        await self.settings_manager.update_setting(ctx.guild.id, 'rules_message_id', rules_message.id)
                        await self.settings_manager.update_setting(ctx.guild.id, 'reaction_emoji', emoji)
                        await self.settings_manager.update_setting(ctx.guild.id, 'reaction_role_id', role.id)
                        await reply(ctx, f"> Rules posted in {rules_channel.mention}. Users must react with {emoji} to get {role.mention}.")
                    step += 1

                elif step == 3:
                    await reply(ctx, f"**Step 3/{total_steps}: Welcome Message**\nPlease enter the welcome message template.\nYou can use placeholders like `{{user.mention}}` and `{{server.name}}`.\nType `skip` to use the default message or `back` to return.")
                    welcome_msg = await self._wait_for_response(ctx)
                    if not welcome_msg or welcome_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if welcome_msg.content.lower() == "back":
                        step -= 1
                        continue
                    if welcome_msg.content.lower() != "skip":
                        step_data['welcome_message'] = welcome_msg.content.strip()
                    else:
                        step_data['welcome_message'] = DEFAULT_WELCOME_MESSAGE
                    # Show preview
                    preview = step_data['welcome_message'].replace('{user.mention}', ctx.author.mention).replace('{server.name}', ctx.guild.name)
                    await reply(ctx, f"Preview: {preview}")
                    step += 1

                elif step == 4:
                    admin_roles = [role for role in ctx.guild.roles if role.permissions.administrator]
                    mod_roles = [role for role in ctx.guild.roles if (role.permissions.manage_guild or role.permissions.kick_members or role.permissions.ban_members) and not role.permissions.administrator]
                    admin_roles_str = ", ".join([role.mention for role in admin_roles]) or "None"
                    mod_roles_str = ", ".join([role.mention for role in mod_roles]) or "None"
                    await reply(ctx, f"**Step 4/{total_steps}: Moderation Roles Overview**\nRoles with moderation permissions (manage_guild, kick, ban): {mod_roles_str}\nType `back` to return.")
                    # Save for summary
                    step_data['mod_roles'] = mod_roles_str
                    mod_roles_msg = await self._wait_for_response(ctx)
                    if mod_roles_msg and mod_roles_msg.content.lower() == "back":
                        step -= 1
                        continue
                    step += 1

                elif step == 5:
                    admin_roles = [role for role in ctx.guild.roles if role.permissions.administrator]
                    admin_roles_str = ", ".join([role.mention for role in admin_roles]) or "None"
                    await reply(ctx, f"**Step 5/{total_steps}: Admin Roles Overview**\nRoles with ADMINISTRATOR permission: {admin_roles_str}\nType `back` to return.")
                    step_data['admin_roles'] = admin_roles_str
                    admin_roles_msg = await self._wait_for_response(ctx)
                    if admin_roles_msg and admin_roles_msg.content.lower() == "back":
                        step -= 1
                        continue
                    step += 1

                elif step == 6:
                    await reply(ctx, f"**Step 6/{total_steps}: Punishments Log Channel**\nPlease mention the channel for punishment logs (e.g., #punishments). Type `skip` to skip or `back` to return.")
                    punish_log_msg = await self._wait_for_response(ctx)
                    if not punish_log_msg or punish_log_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if punish_log_msg.content.lower() == "back":
                        step -= 1
                        continue
                    if punish_log_msg.content.lower() != "skip":
                        punish_log_channel = await self._extract_channel(ctx, punish_log_msg.content)
                        if not punish_log_channel:
                            await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                            continue
                        step_data['punishment_log_id'] = punish_log_channel.id
                    step += 1

                elif step == 7:
                    await reply(ctx, f"**Step 7/{total_steps}: Bot Usage Log Channel**\nPlease mention the channel for bot usage logs (e.g., #bot-usage). Type `skip` to skip or `back` to return.")
                    usage_log_msg = await self._wait_for_response(ctx)
                    if not usage_log_msg or usage_log_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if usage_log_msg.content.lower() == "back":
                        step -= 1
                        continue
                    if usage_log_msg.content.lower() != "skip":
                        usage_log_channel = await self._extract_channel(ctx, usage_log_msg.content)
                        if not usage_log_channel:
                            await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                            continue
                        step_data['usage_log_id'] = usage_log_channel.id
                    step += 1

                elif step == 8:
                    await reply(ctx, f"**Step 8/{total_steps}: Edited/Deleted Messages Log Channel**\nPlease mention the channel for edited/deleted messages logs (e.g., #message-logs). Type `skip` to skip or `back` to return.")
                    msg_log_msg = await self._wait_for_response(ctx)
                    if not msg_log_msg or msg_log_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if msg_log_msg.content.lower() == "back":
                        step -= 1
                        continue
                    if msg_log_msg.content.lower() != "skip":
                        msg_log_channel = await self._extract_channel(ctx, msg_log_msg.content)
                        if not msg_log_channel:
                            await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                            continue
                        step_data['message_log_id'] = msg_log_channel.id
                    step += 1

                elif step == 9:
                    await reply(ctx, f"**Step 9/{total_steps}: Leave Notifications Channel**\nPlease mention the channel for leave notifications (e.g., #leaves). Type `skip` to skip or `back` to return.")
                    leave_log_msg = await self._wait_for_response(ctx)
                    if not leave_log_msg or leave_log_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if leave_log_msg.content.lower() == "back":
                        step -= 1
                        continue
                    if leave_log_msg.content.lower() != "skip":
                        leave_log_channel = await self._extract_channel(ctx, leave_log_msg.content)
                        if not leave_log_channel:
                            await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                            continue
                        step_data['leave_log_id'] = leave_log_channel.id
                    step += 1

                elif step == 10:
                    # Summary and confirmation
                    summary = (
                        f"**Prefix:** `{step_data.get('prefix','')}`\n"
                        f"**Rules Channel:** <#{step_data.get('rules_channel_id','Not Set')}>\n"
                        f"**Welcome Message:** `{step_data.get('welcome_message','')}`\n"
                        f"**Moderation Roles:** {step_data.get('mod_roles','None')}\n"
                        f"**Admin Roles:** {step_data.get('admin_roles','None')}\n"
                        f"**Punishment Log:** <#{step_data.get('punishment_log_id','Not Set')}>\n"
                        f"**Usage Log:** <#{step_data.get('usage_log_id','Not Set')}>\n"
                        f"**Message Log:** <#{step_data.get('message_log_id','Not Set')}>\n"
                        f"**Leave Log:** <#{step_data.get('leave_log_id','Not Set')}>\n"
                    )
                    await reply(ctx, f"**Step 10/{total_steps}: Review Settings**\nHere is a summary of your selections:\n{summary}\nType `confirm` to save, `back` to edit previous step, or `cancel` to abort.")
                    confirm_msg = await self._wait_for_response(ctx)
                    if not confirm_msg or confirm_msg.content.lower() == "cancel":
                        await reply(ctx, "Setup cancelled.")
                        return
                    if confirm_msg.content.lower() == "back":
                        step -= 1
                        continue
                    if confirm_msg.content.lower() == "confirm":
                        # Save all settings
                        await self.settings_manager.update_setting(guild_id, 'prefix', step_data.get('prefix'))
                        if step_data.get('rules_channel_id'):
                            await self.settings_manager.update_setting(guild_id, 'rules_channel_id', step_data.get('rules_channel_id'))
                        if step_data.get('welcome_message'):
                            await self.settings_manager.update_setting(guild_id, 'welcome_message', step_data.get('welcome_message'))
                        if step_data.get('punishment_log_id'):
                            await self.settings_manager.update_setting(guild_id, 'punishment_log_id', step_data.get('punishment_log_id'))
                        if step_data.get('usage_log_id'):
                            await self.settings_manager.update_setting(guild_id, 'usage_log_id', step_data.get('usage_log_id'))
                        if step_data.get('message_log_id'):
                            await self.settings_manager.update_setting(guild_id, 'message_log_id', step_data.get('message_log_id'))
                        if step_data.get('leave_log_id'):
                            await self.settings_manager.update_setting(guild_id, 'leave_log_id', step_data.get('leave_log_id'))
                        await reply(ctx, "✅ Setup complete! The bot is now configured for your server.")
                        break
                    else:
                        await reply(ctx, "Invalid response. Type `confirm`, `back`, or `cancel`.")

            
            rules_example = (
                "Be respectful - You must respect all users, regardless of your liking towards them. Treat others the way you want to be treated.\n\n"
                "No Inappropriate Language - The use of profanity should be kept to a minimum. However, any derogatory language towards any user is prohibited.\n\n"
                "No Spamming - Do not send a lot of small messages right after each other. Do not disrupt chat by spamming.\n\n"
                "No NSFW Material - This is a community server and not meant to share pornographic/adult/other NSFW material.\n\n"
                "No Advertisements - We do not tolerate any kind of advertisements, whether it be for other communities or streams.\n\n"
                "No Server Raiding - Raiding or mentions of raiding are not allowed.\n\n"
                "Direct & Indirect Threats - Threats to other users of DDoS, Death, DoX, abuse, and other malicious threats are absolutely prohibited and disallowed.\n\n"
                "Follow the Discord Community Guidelines - You can find them here: https://discordapp.com/guidelines\n\n"
                "Your presence in this server implies accepting these rules, including all further changes. These changes might be done at any time without notice, it is your responsibility to check for them."
            )
            await reply(ctx, f"**Step 2/9: Rules Channel**\nPlease mention the channel for posting server rules (e.g., #rules).\nHere is an example rules message you can use or edit:\n```\n{rules_example}\n```\nType `skip` to skip this step.")
            rules_channel_msg = await self._wait_for_response(ctx)
            if rules_channel_msg is None or rules_channel_msg.content.lower() == "cancel":
                await reply(ctx, "Setup cancelled.")
                return
            if rules_channel_msg.content.lower() != "skip":
                rules_channel = await self._extract_channel(ctx, rules_channel_msg.content)
                if not rules_channel:
                    await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                    return
                await self.settings_manager.update_setting(guild_id, 'rules_channel_id', rules_channel.id)
                await rules_channel.send(rules_example)
                await reply(ctx, f"Rules channel set to {rules_channel.mention} and example rules posted.")
            else:
                await reply(ctx, "Skipped rules channel setup.")

            
            await reply(ctx, "**Step 3/9: Welcome Message**\nPlease enter the welcome message template.\nYou can use placeholders like `{user.mention}` and `{server.name}`.\nType `skip` to use the default message.")
            welcome_msg = await self._wait_for_response(ctx)
            if welcome_msg is None or welcome_msg.content.lower() == "cancel":
                await reply(ctx, "Setup cancelled.")
                return
            if welcome_msg.content.lower() != "skip":
                await self.settings_manager.update_setting(guild_id, 'welcome_message', welcome_msg.content.strip())
                await reply(ctx, "Welcome message set!")
            else:
                await self.settings_manager.update_setting(guild_id, 'welcome_message', DEFAULT_WELCOME_MESSAGE)
                await reply(ctx, "Default welcome message will be used.")

            # 4. Moderation roles overview
            admin_roles = [role for role in ctx.guild.roles if role.permissions.administrator]
            mod_roles = [role for role in ctx.guild.roles if (role.permissions.manage_guild or role.permissions.kick_members or role.permissions.ban_members) and not role.permissions.administrator]
            admin_roles_str = ", ".join([role.mention for role in admin_roles]) or "None"
            mod_roles_str = ", ".join([role.mention for role in mod_roles]) or "None"
            await reply(ctx, f"**Step 4/9: Moderation Roles Overview**\nRoles with ADMINISTRATOR permission: {admin_roles_str}\nRoles with moderation permissions (manage_guild, kick, ban): {mod_roles_str}")

            # 5. Admin roles overview (repeat admin_roles)
            await reply(ctx, f"**Step 5/9: Admin Roles Overview**\nRoles with ADMINISTRATOR permission: {admin_roles_str}")

            # 6. Punishments log channel
            await reply(ctx, "**Step 6/9: Punishments Log Channel**\nPlease mention the channel for punishment logs (e.g., #punishments). Type `skip` to skip.")
            punish_log_msg = await self._wait_for_response(ctx)
            if punish_log_msg is None or punish_log_msg.content.lower() == "cancel":
                await reply(ctx, "Setup cancelled.")
                return
            if punish_log_msg.content.lower() != "skip":
                punish_log_channel = await self._extract_channel(ctx, punish_log_msg.content)
                if not punish_log_channel:
                    await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                    return
                await self.settings_manager.update_setting(guild_id, 'punishment_log_id', punish_log_channel.id)
                await reply(ctx, f"Punishments log channel set to {punish_log_channel.mention}.")
            else:
                await reply(ctx, "Skipped punishments log channel setup.")

            # 7. Usage log channel
            await reply(ctx, "**Step 7/9: Bot Usage Log Channel**\nPlease mention the channel for bot usage logs (e.g., #bot-usage). Type `skip` to skip.")
            usage_log_msg = await self._wait_for_response(ctx)
            if usage_log_msg is None or usage_log_msg.content.lower() == "cancel":
                await reply(ctx, "Setup cancelled.")
                return
            if usage_log_msg.content.lower() != "skip":
                usage_log_channel = await self._extract_channel(ctx, usage_log_msg.content)
                if not usage_log_channel:
                    await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                    return
                await self.settings_manager.update_setting(guild_id, 'usage_log_id', usage_log_channel.id)
                await reply(ctx, f"Bot usage log channel set to {usage_log_channel.mention}.")
            else:
                await reply(ctx, "Skipped bot usage log channel setup.")

            # 8. Edited/deleted messages log channel
            await reply(ctx, "**Step 8/9: Edited/Deleted Messages Log Channel**\nPlease mention the channel for edited/deleted messages logs (e.g., #message-logs). Type `skip` to skip.")
            msg_log_msg = await self._wait_for_response(ctx)
            if msg_log_msg is None or msg_log_msg.content.lower() == "cancel":
                await reply(ctx, "Setup cancelled.")
                return
            if msg_log_msg.content.lower() != "skip":
                msg_log_channel = await self._extract_channel(ctx, msg_log_msg.content)
                if not msg_log_channel:
                    await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                    return
                await self.settings_manager.update_setting(guild_id, 'message_log_id', msg_log_channel.id)
                await reply(ctx, f"Message log channel set to {msg_log_channel.mention}.")
            else:
                await reply(ctx, "Skipped edited/deleted messages log channel setup.")

            # 9. Leave notifications channel
            await reply(ctx, "**Step 9/9: Leave Notifications Channel**\nPlease mention the channel for leave notifications (e.g., #leaves). Type `skip` to skip.")
            leave_log_msg = await self._wait_for_response(ctx)
            if leave_log_msg is None or leave_log_msg.content.lower() == "cancel":
                await reply(ctx, "Setup cancelled.")
                return
            if leave_log_msg.content.lower() != "skip":
                leave_log_channel = await self._extract_channel(ctx, leave_log_msg.content)
                if not leave_log_channel:
                    await reply(ctx, "Invalid channel. Please mention a valid text channel.")
                    return
                await self.settings_manager.update_setting(guild_id, 'leave_log_id', leave_log_channel.id)
                await reply(ctx, f"Leave notifications channel set to {leave_log_channel.mention}.")
            else:
                await reply(ctx, "Skipped leave notifications channel setup.")

            await reply(ctx, "✅ Setup complete! The bot is now configured for your server.")
        except Exception as e:
            await reply(ctx, f"An error occurred during setup: {e}")
        finally:
            self._active_setups.discard(guild_id)

    async def _extract_channel(self, ctx, content):
        """Преобразует ввод пользователя в объект текстового канала Discord."""
        try:
            channel = await commands.TextChannelConverter().convert(ctx, content)
            return channel
        except commands.ChannelNotFound:
            return None

    async def _wait_for_response(self, ctx):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await self.bot.wait_for('message', timeout=120.0, check=check)
            return msg
        except asyncio.TimeoutError:
            await reply(ctx, "⏰ Время ожидания истекло. Попробуйте снова.")
            return None

    async def _configure_logs(self, ctx):
        """Guides the user through setting up various log channels."""
        await reply(ctx, embed=discord.Embed(title="📝 Log Channels Setup", description="Now, let's set up channels for different logs. You can `skip` any of them.", color=discord.Color.orange()))

        log_types = {
            "punishment_log_id": "for **punishment logs** (ban, kick, etc.)",
            "usage_log_id": "for **command usage logs**",
            "message_log_id": "for **edited/deleted message logs**",
            "leave_log_id": "for **user leave notifications**"
        }

        for key, desc in log_types.items():
            channel_id = await self._ask_for(ctx, desc, "e.g., `#bot-logs`", str, is_channel=True, default_value='skip')
            if channel_id is None: raise asyncio.CancelledError

            if channel_id != 'skip':
                await self.settings_manager.update_setting(ctx.guild.id, key, int(channel_id))
                await ctx.send(f"✅ {desc.replace('**','')} will be sent to <#{channel_id}>.")

    async def _ask_for(self, ctx: commands.Context, question: str, guide: str, response_type: type, default_value=None, is_channel=False, is_role=False):
        """A helper function to ask a question and wait for a valid response."""
        embed = discord.Embed(description=f"Please provide {question}.\n*Example: {guide}*\n\nType `skip` to use the default, or `cancel` to stop.", color=discord.Color.blurple())
        prompt_message = await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        while True:
            try:
                msg = await self.bot.wait_for('message', timeout=120.0, check=check)
                content = msg.content.strip()

                if content.lower() == 'cancel':
                    return None
                if content.lower() == 'skip':
                    await ctx.send(f"Skipped.")
                    return 'skip'

                if is_channel:
                    try:
                        channel = await commands.TextChannelConverter().convert(ctx, content)
                        return channel.id
                    except commands.ChannelNotFound:
                        await ctx.send(f"❌ Could not find the channel `{content}`. Please provide a valid channel mention, ID, or exact name.")
                        continue
                elif is_role:
                    try:
                        role = await commands.RoleConverter().convert(ctx, content)
                        return role.id
                    except commands.RoleNotFound:
                        await ctx.send("Invalid role. Please mention the role (e.g., @Member) or provide its ID.")
                        continue
                else:
                    try:
                        return response_type(content)
                    except (ValueError, TypeError):
                        await ctx.send(f"Invalid input. Please provide a valid {response_type.__name__}.")
                        continue

            except asyncio.TimeoutError:
                await prompt_message.edit(content="Setup timed out.", embed=None)
                raise asyncio.TimeoutError

    @setup.error
    async def setup_error(self, ctx, error):
        """Error handler specific to the setup command."""
        self._active_setups.discard(ctx.guild.id)
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have the required permissions to run this command.")
        elif isinstance(error, commands.NoPrivateMessage):
            pass
        elif isinstance(error, (asyncio.TimeoutError, asyncio.CancelledError)):
            pass  # The command itself handles this.
        else:
            logger.error(f"An unexpected error occurred during setup for guild {ctx.guild.id}:", exc_info=error)
            await ctx.send("An unexpected error occurred. The setup has been cancelled.")

async def setup(bot: commands.Bot):
    """This function is required by discord.py to load the cog."""
    await bot.add_cog(SetupCog(bot))
