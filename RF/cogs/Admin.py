from datetime import datetime, timedelta
from itertools import repeat
from typing import Optional

from nextcord import Webhook, TextChannel
from nextcord.ext.commands import (BucketType, Cog, Context, 
                                   bot_has_permissions, command, cooldown,
                                   has_permissions)
from pytz import timezone

from ..bot import RF
from . import delUserMsg


class Admin(Cog):
    def __init__(self, bot: RF):
        self.bot = bot


    @command(name="prefix", description="Change server prefix.\nRequire `Administrator` permissions",)
    @has_permissions(administrator=True)
    async def prefix(self, ctx:Context, prefix: Optional[str] = "rf-"):
        await delUserMsg(ctx)

        # Find guild and set prefix for that guild
        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"prefix": prefix}})

        # Setting Nickname after change prefix
        old_nickname = (ctx.guild.me.display_name if "|" not in ctx.guild.me.display_name else ctx.guild.me.display_name.split("|")[1])
        await ctx.send(f'Prefix have been change to "{prefix}"')
        await ctx.guild.me.edit(nick=f"[{prefix}] | {old_nickname.strip()}")


    @command(name="purge", aliases=["clear"], description="Purge message.\nRequire `Manage Messages` permissions",)
    @bot_has_permissions(manage_messages=True)
    @has_permissions(manage_messages=True)
    async def clear_messages(self, ctx: Context, limit: Optional[int] = 1):
        def _check(message):
            return message.id != ctx.message.id

        with ctx.channel.typing():
            total = 0
            while limit > 100:
                total += len(await ctx.channel.purge(limit=101, after=datetime.utcnow() - timedelta(days=14), check=_check,))
                limit -= 100
            else:
                total += len(await ctx.channel.purge(limit=limit+1, after=datetime.utcnow() - timedelta(days=14), check=_check,))

        await ctx.send(f"Deleted {total} messages.", delete_after=1)
        await ctx.message.delete(delay=1.0)


    @command(name="spam", description="Spam text.\nRequire `Administrator` permissions")
    @has_permissions(administrator=True)
    @cooldown(1, 10, BucketType.user)
    async def _spam(self, ctx: Context, amount: int, *, text: str):
        await delUserMsg(ctx)

        async def delWebhook(webhook: Webhook):
            await webhook.delete(reason="Spam finished.")

        webhook = await ctx.channel.create_webhook(name=ctx.author.display_name, avatar= await ctx.author.avatar.read(), reason=f"Spam started by {ctx.author}" )

        channel = Webhook.from_url(url=webhook.url, session=self.bot.session)

        self.bot.scheduler.add_job(delWebhook, id=f"{ctx.author.id}-Spam", args=[webhook], replace_existing=True,
                                         next_run_time=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")) + timedelta(seconds=60*amount/2),)

        for _ in repeat(None, amount):
            msg = await channel.send(content=text, wait=True)
            await msg.delete(delay=60.0)
            
    
    @command(name='set-log-channel', aliases=['slc'], description="Set log channel for logging.\nRequired `Administrator`permissions.")
    @has_permissions(administrator=True)
    async def _logchannel(self, ctx: Context, channel: TextChannel) -> None:
        await delUserMsg(ctx)
        
        avatar = await ctx.guild.me.avatar.read()
        webhook = await channel.create_webhook(name="Raid Force", reason=f"This channel have been set to log channel by {ctx.author}", avatar=avatar)
        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Log channel": {"ID": webhook.id, "Token": webhook.token}}})

        await ctx.send(f'Log channel has been added/updated {channel.mention}',delete_after = 5)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Admin")


def setup(bot):
    bot.add_cog(Admin(bot))