import discord
from discord.ext import commands
from webserver import keep_alive
import config
import sqlite3
import asyncio
import logging
from datetime import datetime

# Configure logging with more details
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Bot setup with all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Database connection
def get_db():
    db = sqlite3.connect('Pocosultoj.db')
    return db, db.cursor()

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game('Brawl Stars')
    )
    logging.info(f'Bot logged in as {bot.user}')
    print(f'Bot logged in as {bot.user}')

    # Initialize database
    db, cur = get_db()
    cur.execute('''CREATE TABLE IF NOT EXISTS warnings 
                   (userid INTEGER, count INTEGER, guild_id INTEGER)''')
    db.commit()
    db.close()

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != 874752473405988874:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role_name = 'Member' if payload.emoji.name == '✅' else payload.emoji.name
    role = discord.utils.get(guild.roles, name=role_name)

    if role and payload.member:
        await payload.member.add_roles(role)
        log_message = f"Role '{role.name}' added to {payload.member}"
        logging.info(log_message)

        if log_channel := bot.get_channel(1085966600051642568):
            await log_channel.send(log_message)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != 874752473405988874:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role_name = 'Member' if payload.emoji.name == '✅' else payload.emoji.name
    role = discord.utils.get(guild.roles, name=role_name)

    if role:
        if member := await guild.fetch_member(payload.user_id):
            await member.remove_roles(role)
            log_message = f"Role '{role.name}' removed from {member}"
            logging.info(log_message)

            if log_channel := bot.get_channel(1085966600051642568):
                await log_channel.send(log_message)

@bot.event
async def on_member_join(member):
    welcome_message = f'Welcome {member.mention}!'
    await member.send('Welcome to the server!')

    if welcome_channel := discord.utils.get(member.guild.channels, name='велкам-👋'):
        await welcome_channel.send(welcome_message)

@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member, time: int, reason: str):
    mute_role = discord.utils.get(ctx.guild.roles, id=876508795562504252)
    member_role = discord.utils.get(ctx.guild.roles, id=873196004718034964)
    log_channel = bot.get_channel(876507449362898974)

    if not all([mute_role, member_role, log_channel]):
        await ctx.send("Configuration error: Missing roles or channels")
        return

    embed = discord.Embed(color=discord.Color.yellow())
    embed.add_field(name="✅ Muted", value=f"{member.mention} has been muted")
    embed.add_field(name="Administrator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Duration", value=f"{time} minutes", inline=False)

    await member.remove_roles(member_role)
    await member.add_roles(mute_role)
    await log_channel.send(embed=embed)

    await asyncio.sleep(time * 60)

    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await member.add_roles(member_role)
        unmute_embed = discord.Embed(color=discord.Color.green())
        unmute_embed.add_field(name="✅ Unmuted", value=f"{member.mention} has been unmuted")
        await log_channel.send(embed=unmute_embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def unmute(ctx, member: discord.Member):
    channel = bot.get_channel(876507449362898974)
    muterole = discord.utils.get(ctx.guild.roles, id=876508795562504252)
    memberrole = discord.utils.get(ctx.guild.roles, id=873196004718034964)

    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Unmuted", value=f"{member.mention} has been unmuted.")
    emb.add_field(name="Administrator", value=ctx.author.mention, inline=False)

    await member.remove_roles(muterole)
    await member.add_roles(memberrole)
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason):
    channel = bot.get_channel(876507449362898974)
    await member.kick(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Kicked", value=f"{member.mention} has been kicked.")
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason):
    channel = bot.get_channel(876507449362898974)
    await member.ban(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Banned", value=f"{member.mention} has been banned.")
    await channel.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def unban(ctx, *, member):
    channel = bot.get_channel(876507449362898974)
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
    channel = ctx.guild.get_channel(876507449362898974)

    db, cur = get_db()
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
    db.close()

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