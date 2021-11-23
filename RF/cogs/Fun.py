import time
from datetime import datetime, timedelta
from platform import python_version
from time import time
from typing import Optional

from nextcord import ButtonStyle, Embed, Member
from nextcord import __version__ as nextcord_version
from nextcord import ui
from nextcord.ext.commands import (BucketType, Cog, Context, command,
                                   cooldown)
from psutil import Process, virtual_memory
from pytz import timezone
from roblox import Client

from ..bot import RF
from . import del_user_msg


DND_EMOJI = "<:dnd:903269917854400532>"
IDLE_EMOJI = "<:idle:903269440911724564> "
ONLINE_EMOJI = "<:online:903269917963468821>"
OFFLINE_EMOJI = "<:offline:903269494544298014>"
CREATOR_ID = 188903265931362304


class Invite(ui.View):
    def __init__(self) -> None:
        super().__init__()
        # we need to quote the query string to make a valid url. Discord will raise an error if it isn't valid.

        RF_WEBSITE = "https://website.raid-force-911.repl.co/"
        INVITE = "https://discord.com/api/oauth2/authorize?client_id=902485667232235591&permissions=534689345271&scope=bot"
        RF_WAREHOUSE = "https://discord.gg/ZZGM8PD3fW"

        # Link buttons cannot be made with the decorator
        # Therefore we have to manually create one.
        # We add the quoted url to the button, and add the button to the view.
        self.add_item(ui.Button(style=ButtonStyle.link, label="RF Website", url=RF_WEBSITE))
        self.add_item(ui.Button(style=ButtonStyle.link, label="RF WareHouse", url=RF_WAREHOUSE))


class Fun(Cog):
    def __init__(self, bot: RF) -> None:
        self.bot = bot
        self.DELETE_AFTER = 300
        self.roblox = Client()
        

    @command(name="ping", description="Show Bot Latency.")
    @cooldown(2, 10, BucketType.user)
    async def _ping(self, ctx: Context) -> None:
        await del_user_msg(ctx)

        start = time()
        embed = Embed(title="Pong!", colour=0x2F3136, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.add_field(name="DWSP Latency: ", value=f"{self.bot.latency*1000:,.0f} ms", inline=False,)
        msg = await ctx.send(embed=embed)
        end = time()

        embed.add_field(name="Response time:", value=f"{(end-start)*1000:,.0f} ms", inline=False)
        await msg.edit(embed=embed, delete_after=30)


    @command(name="stats", description="Show bot stats.")
    @cooldown(2, 10, BucketType.user)
    async def show_bot_stats(self, ctx: Context) -> None:
        await del_user_msg(ctx)

        embed = Embed(title="RF Stats", colour=0x2F3136, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
        embed.set_author(name=ctx.guild.me, icon_url=ctx.guild.me.display_avatar)
        embed.set_thumbnail(url=ctx.guild.me.display_avatar)

        proc = Process()
        with proc.oneshot():
            uptime = timedelta(seconds=time() - proc.create_time())
            cpu_time = timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user)
            mem_total = virtual_memory().total / (1024 ** 2)
            mem_of_total = proc.memory_percent()
            mem_usage = mem_total * (mem_of_total / 100)

        fields = [
            ("Version", f"Python: {python_version()}\nNextcord: {nextcord_version}", False,),
            ("Time", f"Uptime: {str(uptime)[:-7]}\nCPU time: {str(cpu_time)[:-7]}", False,),
            ("Memory usage", f"{mem_usage:,.3f} / {mem_total:,.0f} MiB ({mem_of_total:.0f}%)", False,),]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)


    async def get_roblox_info(self, ctx: Context, user: str) -> None:
        thumbnail = await self.roblox.thumbnails.get_user_avatars([user.id], size="720x720")
        thumbnail_url = (thumbnail[0].image_url if thumbnail[0].image_url is not None else Embed.Empty)

        embed = Embed(title="Roblox User Info", colour=0x2F3136, url=f"https://www.roblox.com/users/{user.id}/profile",)
        embed.set_thumbnail(url=thumbnail_url)

        description = ("This user has no description." if user.description == "" else user.description.strip())

        fields = [("Username: ", user.name, True),
                  ("Display Name: ", user.display_name, True),
                  ("ID: ", user.id, False),
                  ("Created at: ", str(user.created)[:10], True),
                  ("Deleted: ", user.is_banned, True),
                  ("Description: ", description, False),]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)


    @command(name="robloxinfo", aliases=["rbinfo"], description="Get information about user or roblox.",)
    @cooldown(2, 10, BucketType.user)
    async def roblox_info_command(self, ctx: Context, member: Optional[Member] = None, *, robloxName: Optional[str] = None) -> None:
        await del_user_msg(ctx)

        if member is not None:
            if self.bot.ROBLOX_DB.find_one({"_id": member.id}) is None:
                await ctx.send("Can't find roblox account linked with this user")
            else:
                user = self.bot.ROBLOX_DB.find_one({"_id": member.id})
                userID = user["Roblox ID"]
                roblox = await self.roblox.get_user(userID)
                await self.get_roblox_info(ctx, roblox)
        elif robloxName is not None:
            user_name = await self.roblox.get_user_by_username(robloxName)
            if user_name == None:
                await ctx.send("No user found with that username.")
            else:
                user = await self.roblox.get_user(user_name.id)
                await self.get_roblox_info(ctx, user)
        else:
            if self.bot.ROBLOX_DB.find_one({"_id": ctx.author.id}) is None:
                await ctx.send("You haven't sign in.")
            else:
                user = self.bot.ROBLOX_DB.find_one({"_id": ctx.author.id})
                roblox = await self.roblox.get_user(user["Roblox ID"])
                await self.get_roblox_info(ctx, roblox)


    @command(name="userinfo", aliases=["memberinfo", "ui", "mi"], description="Get information about member.",)
    @cooldown(2, 10, BucketType.user)
    async def user_info(self, ctx: Context, member: Optional[Member] = None) -> None:
        await del_user_msg(ctx)

        member = member or ctx.author
        embed = Embed(title="User information", description=member.mention, colour=0x2F3136, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
        embed.set_author(name=member, icon_url=member.display_avatar)
        embed.set_thumbnail(url=member.display_avatar)
        embed.set_footer(text=f"ID: {member.id}")
        
        sorted_roles = sorted([role for role in member.roles if "everyone" not in role.name], key=lambda r: (r.position), reverse=True,)
        role_mention = [role.mention for role in sorted_roles]

        isOwner = ctx.guild.owner.id == member.id
        isAdmin = member.guild_permissions.administrator
        
        print(member.guild_permissions.value)
        
        fields = [("Created", member.created_at.strftime("%a, %d %b, %Y \n%I:%M %p"), True),
                  ("Joined", member.joined_at.strftime("%a, %d %b, %Y \n%I:%M %p"), True),
                  (f"Roles [{len(role_mention)}]", " ".join(role_mention), False),
                  ("Status", str(member.status).title(), True),
                  ("Boosted", bool(member.premium_since), True),]
    
        if isOwner or isAdmin:
            embed.insert_field_at(5, name="Acknowledgements", value=f"{'Server Owner' if isOwner else 'Server Admin' if isAdmin else 'None'}", inline=False)

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)


    @command(name="serverinfo", aliases=["guildinfo", "si", "gi"], description="Get information about server.",)
    @cooldown(2, 10, BucketType.user)
    async def server_info(self, ctx) -> None:
        await del_user_msg(ctx)

        embed = Embed(title=f"{ctx.guild.name}", colour=0x2F3136)
        embed.set_thumbnail(url=ctx.guild.icon)
        created_at = ctx.guild.created_at.strftime("%d/%m/%Y")
        embed.set_footer(text=f"ID: {ctx.guild.id} | Server Created: {created_at}")

        statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
                    len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members))),]

        members = len(ctx.guild.members)
        human = len(list(filter(lambda m: not m.bot, ctx.guild.members)))
        bot = len(list(filter(lambda m: m.bot, ctx.guild.members)))

        text_channels = len(ctx.guild.text_channels)
        voice_channels = len(ctx.guild.voice_channels)
        role = len(ctx.guild.roles)
        categories = len(ctx.guild.categories)

        fields = [("Owner", ctx.guild.owner, False), 
                  ("Categories", f"{categories}", True), 
                  ("Roles", f"{role}", True),
                  (f"Members: {members}", f"Human: {human}\nBot: {bot}", False), 
                  (f"Channels: {text_channels + voice_channels}", f"Text: {text_channels}\nVoice: {voice_channels}", True,),  
                  ("Statuses", f"{ONLINE_EMOJI} {statuses[0]} {IDLE_EMOJI} {statuses[1]} {DND_EMOJI} {statuses[2]} {OFFLINE_EMOJI} {statuses[3]}", False,),]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)


    @command(name="av", aliases=["avatar"], description="Get member avatar.")
    @cooldown(2, 10, BucketType.user)
    async def av_command(self, ctx: Context, member: Member = None) -> None:
        await del_user_msg(ctx)
        member = member or ctx.author

        embed = Embed(title="Avatar", color=0x2F3136)
        embed.set_author(name=f"{member}", icon_url=member.display_avatar)
        embed.set_image(url=member.display_avatar)

        await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)


    @command(name="info", description="Get Bot information")
    @cooldown(2, 10, BucketType.user)
    async def info_command(self, ctx: Context) -> None:
        await del_user_msg(ctx)

        owner = self.bot.get_user(CREATOR_ID)
        created_at = self.bot.user.created_at.strftime("%d/%m/%Y")
        uptime = timedelta(seconds=time() - Process().create_time())

        embed = Embed(color=0xE1CC04)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        embed.set_footer(text=(f"Uptime: {str(uptime)[:-7]} "))
        fields = [("Created by", owner, False), 
                  ("Created at", created_at, False), 
                  ("Version", self.bot.VERSION, False),]
        
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, view=Invite())


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Fun")


def setup(bot):
    bot.add_cog(Fun(bot))
