from nextcord.ext.commands import Cog


async def del_user_msg(ctx):
    delete_user_msg = await ctx.channel.fetch_message(ctx.message.id)
    await delete_user_msg.delete()


class __init__(Cog):
    def __init__(self, bot):
        self.bot = bot


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("__init__")


def setup(bot):
    bot.add_cog(__init__(bot))
