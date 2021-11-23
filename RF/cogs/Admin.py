from datetime import datetime, timedelta
from itertools import repeat
from typing import Optional

from nextcord import Member
from nextcord.ext.commands import (BucketType, Cog, Context, Greedy,
                                   bot_has_permissions, command, cooldown,
                                   has_permissions)
from pytz import timezone

from ..bot import RF
from . import del_user_msg


class Admin(Cog):
    def __init__(self, bot: RF):
        self.bot = bot


    @command(name="prefix", description="Change server prefix.\nRequire `Administrator` permissions",)
    @has_permissions(administrator=True)
    async def prefix(self, ctx:Context, prefix: Optional[str] = "rf-"):
        await del_user_msg(ctx)

        # Find guild and set prefix for that guild
        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"prefix": prefix}})

        # Setting Nickname after change prefix
        old_nickname = (ctx.guild.me.display_name if "|" not in ctx.guild.me.display_name else ctx.guild.me.display_name.split("|")[1])
        await ctx.send(f'Prefix have been change to "{prefix}"')
        await ctx.guild.me.edit(nick=f"[{prefix}] | {old_nickname.strip()}")


    @command(name="purge", aliases=["clear"], description="Purge message.\nRequire `Manage Messages` permissions",)
    @bot_has_permissions(manage_messages=True)
    @has_permissions(manage_messages=True)
    async def clear_messages(self, ctx:Context, targets: Greedy[Member], limit: Optional[int] = 1):
        def _check(message):
            return not len(targets) or message.author in targets

        with ctx.channel.typing():
            total = 0
            while limit > 100:
                total += len(await ctx.channel.purge(limit=100, after=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")) - timedelta(days=14), check=_check,))
                limit -= 100
            else:
                total += len(await ctx.channel.purge(limit=limit, after=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")) - timedelta(days=14), check=_check,))
            await ctx.send(f"Deleted {total:,} messages.", delete_after=1.5)


    @command(name="spam", description="Spam text.\nRequire `Administrator` permissions")
    @has_permissions(administrator=True)
    @cooldown(1, 10, BucketType.user)
    async def _spam(self, ctx:Context, amount:int, *, text:str):
        await del_user_msg(ctx)

        for _ in repeat(None, amount):
            await ctx.send(f"{text}", delete_after=60)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Admin")


def setup(bot):
    bot.add_cog(Admin(bot))
