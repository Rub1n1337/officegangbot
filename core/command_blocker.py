from discord.ext import commands

def setup_check():
    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        settings = ctx.bot.settings_manager
        if not settings.get_setting(ctx.guild.id, 'setup_complete'):
            raise commands.CheckFailure("Please complete bot setup first")
        return True
    return commands.check(predicate)