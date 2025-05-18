import discord
from discord.ext import commands
from webserver import keep_alive
import config
import sqlite3
import time
import asyncio
import logging
from datetime import datetime

logging.basicConfig(filename='logging.log', level=logging.INFO)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game('Brawl Stars'))
    print('Logged in as', bot.user)

    global base, cur
    base = sqlite3.connect('Pocosultoj.db')
    cur = base.cursor()
    if base:
        print('Database connected successfully.')

# Add role on reaction
@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == 874752473405988874:
        guild = discord.utils.find(lambda g: g.id == payload.guild_id, bot.guilds)
        role = discord.utils.get(guild.roles, name='Member' if payload.emoji.name == '✅' else payload.emoji.name)

        if role:
            member = payload.member
            if member:
                await member.add_roles(role)
                log_message = f"Role '{role.name}' added to {member.name}#{member.discriminator} (ID: {member.id}) at {datetime.now()}"
                logging.info(log_message)
                print(log_message)
                log_channel = bot.get_channel(1085966600051642568)
                await log_channel.send(log_message)
        else:
            print("Role not found.")

# Remove role on reaction remove
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id == 874752473405988874:
        guild = discord.utils.find(lambda g: g.id == payload.guild_id, bot.guilds)
        role = discord.utils.get(guild.roles, name='Member' if payload.emoji.name == '✅' else payload.emoji.name)

        if role:
            member = await guild.fetch_member(payload.user_id)
            if member:
                await member.remove_roles(role)
                log_message = f"Role '{role.name}' removed from {member.name}#{member.discriminator} (ID: {member.id}) at {datetime.now()}"
                logging.info(log_message)
                print(log_message)
                log_channel = bot.get_channel(1085966600051642568)
                await log_channel.send(log_message)

# Welcome message
@bot.event
async def on_member_join(member):
    await member.send('Welcome to the server!')
    for ch in bot.get_guild(member.guild.id).channels:
        if ch.name == 'велкам-👋':
            await bot.get_channel(ch.id).send(f'Welcome {member.mention}!')

# Mute command
@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member, time: int, reason):
    channel = bot.get_channel(876507449362898974)
    muterole = discord.utils.get(ctx.guild.roles, id=876508795562504252)
    memberrole = discord.utils.get(ctx.guild.roles, id=873196004718034964)

    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Muted", value=f"{member.mention} has been muted.")
    emb.add_field(name="Administrator", value=ctx.author.mention, inline=False)
    emb.add_field(name="Reason", value=reason, inline=False)

    embunmute = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    embunmute.add_field(name="✅ Unmuted", value=f"{member.mention} has been unmuted.")
    embunmute.add_field(name="Reason", value='Mute duration expired.')

    await member.remove_roles(memberrole)
    await member.add_roles(muterole)
    await channel.send(embed=emb)
    await asyncio.sleep(time * 60)
    await member.remove_roles(muterole)
    await member.add_roles(memberrole)
    await channel.send(embed=embunmute)

# Unmute command
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

# Kick command
@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason):
    channel = bot.get_channel(876507449362898974)
    await member.kick(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Kicked", value=f"{member.mention} has been kicked.")
    await channel.send(embed=emb)

# Ban command
@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, days, reason):
    channel = bot.get_channel(876507449362898974)
    await member.ban(reason=reason)
    emb = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="✅ Banned", value=f"{member.mention} has been banned.")
    await channel.send(embed=emb)

# Unban command
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

# Warn command
@bot.command()
async def warn(ctx, member: discord.Member, *, reason):
    guild_name = "PocoSUltojBrawlStars"
    channel = ctx.guild.get_channel(876507449362898974)

    base.execute(f'CREATE TABLE IF NOT EXISTS {guild_name} (userid INT, count INT)')
    base.commit()

    warning = cur.execute(f'SELECT * FROM {guild_name} WHERE userid={member.id}').fetchone()

    embed = discord.Embed(color=discord.Colour.from_rgb(225, 225, 0))
    embed.add_field(name="✅ Warned", value=f"{member.mention} has received a warning.", inline=False)
    embed.add_field(name="Administrator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    if warning is None:
        cur.execute(f'INSERT INTO {guild_name} VALUES ({member.id}, 1)')
        base.commit()
        await channel.send(embed=embed)
    elif warning[1] == 1:
        cur.execute(f'UPDATE {guild_name} SET count=2 WHERE userid={member.id}')
        base.commit()
        await channel.send(embed=embed)
    elif warning[1] == 2:
        cur.execute(f'UPDATE {guild_name} SET count=3 WHERE userid={member.id}')
        base.commit()
        await channel.send(embed=embed)
        await member.ban(reason=reason)

# Clear messages
@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx, amount=100):
    await ctx.channel.purge(limit=amount)

# User info
@bot.command()
async def info(ctx, member: discord.Member):
    emb = discord.Embed(title="✅ User Information", color=discord.Colour.from_rgb(225, 225, 0))
    emb.add_field(name="Join Date:", value=member.joined_at, inline=False)
    emb.add_field(name="Display Name:", value=member.display_name, inline=False)
    emb.add_field(name="User ID:", value=member.id, inline=False)
    emb.add_field(name="Account Created:", value=member.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
    emb.set_thumbnail(url=member.avatar.url if member.avatar else None)
    emb.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=emb)

# Test command
@bot.command()
async def test(ctx):
    await ctx.send('Test command executed successfully.')

keep_alive()
bot.run(config.TOKEN)
