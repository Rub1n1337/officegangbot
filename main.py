import discord
from discord.ext import commands
from webserver import keep_alive
import config
import sqlite3
import asyncio
import logging
from datetime import datetime

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

class BrawlStarsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)
        self.db_path = 'Pocosultoj.db'

    async def setup_hook(self):
        self.init_database()
        logger.info('Database initialized')

    def init_database(self):
        with sqlite3.connect(self.db_path) as db:
            cur = db.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS warnings 
                          (userid INTEGER, count INTEGER, guild_id INTEGER)''')
            db.commit()

    async def on_ready(self):
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game('Brawl Stars')
        )
        logger.info(f'Bot logged in as {self.user}')
        print(f'Bot logged in as {self.user}')

    async def on_guild_join(self, guild):
        await self.create_punishments_channel(guild)
        await self.create_bot_setup_channel(guild)

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


bot = BrawlStarsBot()

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

@bot.event
async def on_member_join(member):
    welcome_message = f'Welcome {member.mention}!'
    await member.send('Welcome to the server!')

    if welcome_channel := discord.utils.get(member.guild.channels, name=WELCOME_CHANNEL_NAME):
        await welcome_channel.send(welcome_message)

@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member, time: int, reason: str):
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
    channel = discord.utils.get(ctx.guild.channels, name='punishments') or bot.get_channel(LOG_CHANNEL_ID)
    await member.kick(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Kicked", value=f"{member.mention} has been kicked.")
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason):
    channel = discord.utils.get(ctx.guild.channels, name='punishments') or bot.get_channel(LOG_CHANNEL_ID)
    await member.ban(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Banned", value=f"{member.mention} has been banned.")
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def unban(ctx, *, member):
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
async def warn(ctx, member: discord.Member, *, reason):
    guild_name = "PocoSUltojBrawlStars"
    channel = ctx.guild.get_channel(LOG_CHANNEL_ID)

    db_path = bot.db_path
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
    await ctx.channel.purge(limit=amount)

@bot.command()
async def info(ctx, member: discord.Member):
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
async def test(ctx):
    await ctx.send('Test command executed successfully.')

# Start the webserver and run the bot
keep_alive()
bot.run(config.TOKEN)