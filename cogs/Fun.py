import time
from datetime import datetime, timedelta
from os import getenv
from platform import python_version
from time import time
from typing import Optional

from nextcord import Embed, Member
from nextcord import __version__ as nextcord_version
from nextcord.ext.commands import BucketType, Cog, Greedy, command, cooldown
from psutil import Process, virtual_memory
from pymongo import MongoClient
from requests import get

from . import del_user_msg

DND_EMOJI = "<:dnd:903269917854400532>"
IDLE_EMOJI = "<:9231idle:903269440911724564>"
ONLINE_EMOJI = "<:online:903269917963468821>"
OFFLINE_EMOJI = "<:offline:903269494544298014>"
CREATOR_ID = 188903265931362304


class Fun(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DELETE_AFTER = 180

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.BANNED_DB = self.DB['Banned']
        self.GUILD_DB = self.DB['Guild']
        
    
    @command(name="invite", hidden=True)
    async def _invite(self, ctx):
        await del_user_msg(ctx)

        embed = Embed(title= "RF 911 Official Bot", colour=0x2f3136)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
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
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.add_field(name="DWSP Latency: ", value=f'{self.bot.latency*1000:,.0f} ms', inline=False)
        msg = await ctx.send(embed=embed)
        end = time()

        embed.add_field(name="Response time:", value = f"{(end-start)*1000:,.0f} ms.", inline=False)
        await msg.edit(embed=embed, delete_after= 30)


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
			("nextcord.py version", nextcord_version, True),
			("Uptime", str(uptime)[:-7], True),
			("CPU time", cpu_time, True),
			("Memory usage", f"{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)", True)
		]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)


    @command(name="userinfo", aliases=["memberinfo", "ui", "mi"])
    async def user_info(self, ctx, target: Optional[Member]):
        await del_user_msg(ctx)

        target = target or ctx.author
        embed = Embed(title="User information", colour=0x2f3136, timestamp=datetime.utcnow())
        embed.set_thumbnail(url=target.display_avatar)

        fields = [("Name", str(target), True),
                  ("ID", target.id, True),
                  ("Bot?", target.bot, True),
                  ("Top role", target.top_role.mention, True),
                  ("Status", str(target.status).title(), True),
                  ("Activity", f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''}", True),
                  ("Created at", target.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
                  ("Joined at", target.joined_at.strftime("%d/%m/%Y %H:%M:%S"), True),
                  ("Boosted", bool(target.premium_since), True)]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, delete_after= self.DELETE_AFTER)


    @command(name="serverinfo", aliases=["guildinfo", "si", "gi"])
    async def server_info(self, ctx):
        await del_user_msg(ctx)

        embed = Embed(title="Server information", colour=0x2f3136)
        embed.set_thumbnail(url=ctx.guild.icon)

        statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]

        fields = [("ID", ctx.guild.id, True),
                  ("Owner", ctx.guild.owner, True),
                  ("Region", ctx.guild.region, True),
                  ("Created at", ctx.guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
                  ("Members", len(ctx.guild.members), True),
                  ("Humans", len(list(filter(lambda m: not m.bot, ctx.guild.members))), True),
                  ("Bots", len(list(filter(lambda m: m.bot, ctx.guild.members))), True),
                  ("Banned members", len(await ctx.guild.bans()), True),
                  ("Statuses", f"{ONLINE_EMOJI} {statuses[0]} {IDLE_EMOJI} {statuses[1]} {DND_EMOJI} {statuses[2]} {OFFLINE_EMOJI} {statuses[3]}", True),
                  ("Text channels", len(ctx.guild.text_channels), True),
                  ("Voice channels", len(ctx.guild.voice_channels), True),
                  ("Categories", len(ctx.guild.categories), True),
                  ("Roles", len(ctx.guild.roles), True),
                  ("Invites", len(await ctx.guild.invites()), True),
                  ("\u200b", "\u200b", True)]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, delete_after= self.DELETE_AFTER)

    
    @command(name="av")
    async def av_command(self, ctx, targets: Greedy[Member] = None):
        await del_user_msg(ctx)

        target_id = (target.id for target in targets).__next__() if targets is not None else ctx.author.id
        user = self.bot.get_user(target_id)

        embed = Embed(title='Avatar',color=0x2f3136)
        embed.set_author(name=f"{user}", icon_url=user.display_avatar)
        embed.set_image(url=user.display_avatar)
        
        await ctx.send(embed=embed, delete_after = self.DELETE_AFTER)

    
    @command(name='info')
    async def info_command(self, ctx):
        await del_user_msg(ctx)

        owner = self.bot.get_user(CREATOR_ID)
        created_at = self.bot.user.created_at.strftime("%d/%m/%Y")
        
        embed = Embed(color=0x2f3136, title='')
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        fields = [
            ('Created by ', owner, True),
            ('Created at ', created_at, True),
            ('RF 911 Website ', "[Link](https://website.raid-force-911.repl.co/)", True)
        ]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, delete_after= self.DELETE_AFTER)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Fun")


def setup(bot):
    bot.add_cog(Fun(bot))
