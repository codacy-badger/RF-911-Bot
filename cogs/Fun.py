import time
from datetime import datetime, timedelta
from os import getenv
from platform import python_version
from time import time
from typing import Optional

from nextcord import ButtonStyle, Embed, Member
from nextcord import __version__ as nextcord_version
from nextcord import ui
from nextcord.ext.commands import BucketType, Cog, Greedy, command, cooldown
from psutil import Process, virtual_memory
from pymongo import MongoClient
from roblox import Client

from . import del_user_msg

DND_EMOJI = "<:dnd:903269917854400532>"
IDLE_EMOJI = "<:9231idle:903269440911724564>"
ONLINE_EMOJI = "<:online:903269917963468821>"
OFFLINE_EMOJI = "<:offline:903269494544298014>"
CREATOR_ID = 188903265931362304


class Invite(ui.View):
    def __init__(self):
        super().__init__()
        # we need to quote the query string to make a valid url. Discord will raise an error if it isn't valid.

        RF_WEBSITE = "https://website.raid-force-911.repl.co/"
        INVITE = 'https://discord.com/api/oauth2/authorize?client_id=902485667232235591&permissions=534689345271&scope=bot'
        RF_WAREHOUSE = "https://discord.gg/ZZGM8PD3fW"

        # Link buttons cannot be made with the decorator
        # Therefore we have to manually create one.
        # We add the quoted url to the button, and add the button to the view.
        self.add_item(ui.Button(style=ButtonStyle.link, label='RF Website', url=RF_WEBSITE))
        # self.add_item(ui.Button(style=ButtonStyle.link, label='RF Bot Invite', url=INVITE))
        self.add_item(ui.Button(style=ButtonStyle.link, label='RF WareHouse', url=RF_WAREHOUSE))


class Fun(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DELETE_AFTER = 180
        self.roblox = Client()
        
        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.ROBLOX_DB = self.DB['Roblox']

    
    @command(name='ping', description='Show Bot Latency.')
    @cooldown(2, 10, BucketType.user)
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
    @cooldown(2, 10, BucketType.user)
    async def show_bot_stats(self, ctx):
        await del_user_msg(ctx)

        embed = Embed(title= "RF Bot Stats", colour=0x2f3136, timestamp=datetime.utcnow())
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
			("CPU time", str(cpu_time)[:-7], True),
			("Memory usage", f"{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)", True)
		]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)


    async def get_roblox_info(self, ctx, user):
        thumbnail = await self.roblox.thumbnails.get_user_avatars([user.id], size="720x720")
        thumbnail_url = thumbnail[0].image_url

        embed = Embed(title="Roblox User Info", colour= 0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
        embed.set_thumbnail(url=thumbnail_url)

        description = "This user has no description." if user.description == '' else user.description.strip()

        fields = [("User Name: ", user.name, True),
                      ("Display Name: ", user.display_name, True),
                      ("ID: ", user.id, False),
                      ("Created at: ", str(user.created)[:10], True),
                      ("Is banned: ", user.is_banned, True),
                      ("Description: ", description, False)
            ]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)


    @command(name="roblox-info", aliases=['robloxinfo', 'rbinfo'], description="Get information about user or roblox.")
    @cooldown(2, 10, BucketType.user)
    async def roblox_info_command(self, ctx, users: Optional[Member] = None, *, name: Optional[str] = None):
        await del_user_msg(ctx)

        if users is not None:
            if self.ROBLOX_DB.find_one({"_id": users.id}) is None:
                await ctx.send("Can't find roblox account linked with this user")
            else:
                user = self.ROBLOX_DB.find_one({"_id": users.id})
                userID = user["Roblox ID"]
                roblox = await self.roblox.get_user(userID)
                await self.get_roblox_info(ctx, roblox)
        elif name is not None:
            user_name = await self.roblox.get_user_by_username(name)
            if user_name == None:
                await ctx.send("No user found with that username.")
            else:
                user = await self.roblox.get_user(user_name.id)
                await self.get_roblox_info(ctx, user)
        else:
            if self.ROBLOX_DB.find_one({"_id": ctx.author.id}) is None:
                await ctx.send("You haven't sign in.")
            else:
                user = self.ROBLOX_DB.find_one({"_id": ctx.author.id})
                roblox = await self.roblox.get_user(user["Roblox ID"])
                await self.get_roblox_info(ctx, roblox)


    @command(name="userinfo", aliases=["memberinfo", "ui", "mi"], description="Get information about member.")
    @cooldown(2, 10, BucketType.user)
    async def user_info(self, ctx, target: Optional[Member] = None):
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


    @command(name="serverinfo", aliases=["guildinfo", "si", "gi"], description="Get information about server.")
    @cooldown(2, 10, BucketType.user)
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

    
    @command(name="av", aliases=['avatar'] ,description="Get member avatar.")
    @cooldown(2, 10, BucketType.user)
    async def av_command(self, ctx, targets: Greedy[Member] = None):
        await del_user_msg(ctx)

        target_id = (target.id for target in targets).__next__() if targets is not None else ctx.author.id
        user = self.bot.get_user(target_id)

        embed = Embed(title='Avatar',color=0x2f3136)
        embed.set_author(name=f"{user}", icon_url=user.display_avatar)
        embed.set_image(url=user.display_avatar)
        
        await ctx.send(embed=embed, delete_after = self.DELETE_AFTER)

    
    @command(name='info', description='Get Bot information')
    @cooldown(2, 10, BucketType.user)
    async def info_command(self, ctx):
        await del_user_msg(ctx)

        owner = self.bot.get_user(CREATOR_ID)
        created_at = self.bot.user.created_at.strftime("%d/%m/%Y")
        uptime = timedelta(seconds=time()-Process().create_time())
        
        embed = Embed(color=0xe1cc04, title='')
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        embed.set_footer(text=(f"Uptime: {str(uptime)[:-7]} "))
        fields = [
            ('Created by ', owner, True),
            ('Created at ', created_at, True),
            ('Version ', self.bot.VERSION, True),
        ]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, view=Invite())


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Fun")


def setup(bot):
    bot.add_cog(Fun(bot))
