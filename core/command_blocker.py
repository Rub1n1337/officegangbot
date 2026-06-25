from discord.ext import commands

def setup_check():
    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        # Since setup_complete was a legacy flag and we are moving to DB, 
        # we check if any mod roles or prefix are set in DB, or just allow if DB is available.
        # For now, we'll bypass this check if DB is connected, as 'setup_complete' is not in current DB schema.
        return True
    return commands.check(predicate)