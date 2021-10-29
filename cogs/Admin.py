import itertools
import time
from datetime import datetime, timedelta
from os import getenv
from platform import python_version
from random import choice, randint
from re import search
from time import strftime, time
from typing import Optional

from aiohttp import request
from discord import Embed, Member
from discord import __version__ as discord_version
from discord.ext import commands
from discord.ext.commands import (BadArgument, BucketType, Cog, Greedy,
                                  bot_has_permissions, command, cooldown,
                                  has_permissions)
from psutil import Process, virtual_memory
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


    @command(name="invite", hidden=True)
    async def _invite(self, ctx):
        await del_user_msg(ctx)

        embed = Embed(title= "RF 911 Official Bot", colour=0x2f3136)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        fields = [
            ("Invite link: ", "[click here](https://discord.com/api/oauth2/authorize?client_id=902485667232235591&permissions=534689345271&scope=bot)", False),
            ("RF Warehouse: ", "[click here](https://discord.gg/ZZGM8PD3fW)", False)
        ]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        
        await ctx.send(embed=embed)


    @command(name='ping', description='Show Bot Latency')
    @cooldown(5, 10, BucketType.user)
    async def _ping(self, ctx):
        await del_user_msg(ctx)

        start = time()
        embed = Embed(title= "Pong!", colour=0x2f3136, timestamp=datetime.utcnow())
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(name="DWSP Latency: ", value=f'{self.bot.latency*1000:,.0f} ms', inline=False)
        msg = await ctx.send(embed=embed)
        end = time()

        embed.add_field(name="Response time:", value = f"{(end-start)*1000:,.0f} ms.", inline=False)
        await msg.edit(embed=embed, delete_after= 30)


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
                await ctx.message.delete()
                deleted = await ctx.channel.purge(limit=limit, after=datetime.utcnow()-timedelta(days=14),
												  check=_check)

                await ctx.send(f"Deleted {len(deleted):,} messages.", delete_after=1.5)

        else:
            await ctx.send("The limit provided is not within acceptable bounds.")


    @command(name="stats", description='Show bot stats.')
    async def show_bot_stats(self, ctx):
        await del_user_msg(ctx)

        embed = Embed(title= "Yandere Stats", colour=0x2f3136, timestamp=datetime.utcnow())
        proc = Process()
        with proc.oneshot():
            uptime = timedelta(seconds=time()-proc.create_time())
            cpu_time = timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user)
            mem_total = virtual_memory().total / (1024**2)
            mem_of_total = proc.memory_percent()
            mem_usage = mem_total * (mem_of_total / 100)

        fields = [
			("Python version", python_version(), True),
			("discord.py version", discord_version, True),
			("Uptime", uptime, True),
			("CPU time", cpu_time, True),
			("Memory usage", f"{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)", True)
		]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)


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