import itertools
from datetime import datetime, timedelta
from os import getenv
from typing import Optional

from nextcord import Embed, Member
from nextcord.ext.commands import (BucketType, Cog, Greedy, bot_has_permissions,
                                  command, cooldown, has_permissions)
from pymongo import MongoClient

from . import del_user_msg


class Admin(Cog):
    def __init__(self, bot):
        self.bot = bot

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']


    @command(name="prefix", description="Change server prefix, require administrator permissions")
    @has_permissions(administrator=True)
    async def prefix(self, ctx, guild_prefix: Optional[str] = "rf-"):
        await del_user_msg(ctx)

        # Find guild and set prefix for that guild
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"prefix": guild_prefix}})

        # Setting Nickname after change prefix
        old_nickname = ctx.guild.me.display_name if '|' not in ctx.guild.me.display_name else ctx.guild.me.display_name.split("|")[1]
        await ctx.send(f'Prefix have been change to "{guild_prefix}"')
        await ctx.guild.me.edit(nick=f"[{guild_prefix}] | {old_nickname.strip()}")


    @command(name="clear", aliases=["purge"], description="Purge message, require manage messages permissions")
    @bot_has_permissions(manage_messages=True)
    @has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, targets: Greedy[Member], limit: Optional[int] = 1, all: Optional[str] = None):

        def _check(message):
            return not len(targets) or message.author in targets

        if all == 'all':
            limit = 100

        if 0 < limit <= 100:
            with ctx.channel.typing():
                deleted = await ctx.channel.purge(limit=limit+1, after=datetime.utcnow()-timedelta(days=14), check=_check)
                await ctx.send(f"Deleted {len(deleted) - 1:,} messages.", delete_after=1.5)
        else:
            await ctx.send("The limit provided is not within acceptable bounds.")


    @command(name='spam', description="Spam text, require administrator permissions")
    @has_permissions(administrator=True)
    @cooldown(1, 10, BucketType.user)
    async def _spam(self, ctx, amount: int, *, text):
        await del_user_msg(ctx)

        for _ in itertools.repeat(None, amount):
            await ctx.send(f'{text}', delete_after= 120)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Admin")


def setup(bot):
    bot.add_cog(Admin(bot))
