from datetime import datetime, timedelta
from os import getenv
from typing import Optional
from uuid import uuid4
from aiohttp.client import ClientSession

from apscheduler.jobstores.base import JobLookupError
from nextcord import Embed, File, Guild, Member, Message, Webhook, Role
from nextcord.ext.commands import Context, Greedy
from nextcord.ext.commands.errors import CommandError
from nextcord.utils import find, get
from pymongo import MongoClient
from pytz import timezone

from ..bot import RF


class ResponseError(CommandError):
    pass


class Moderation():
    def __init__(self, bot:RF) -> None:
        self.bot = bot
        self.DELETE_AFTER = 6


    async def logSend(self, guild: Guild, embed: Optional[Embed] = None, file: Optional[File] = None) -> None:
        webhook = (self.bot.GUILD_DB.find_one({"_id": guild.id})["Log channel"] if self.bot.GUILD_DB.find_one({"_id": guild.id}) is not None else None)

        if webhook is not None:
            ID, Token = webhook["ID"], webhook["Token"]
            channel = Webhook.from_url(url=f"https://discord.com/api/webhooks/{ID}/{Token}", session=self.bot.session)
            if embed is not None:
                await channel.send(embed=embed)

            elif file is not None:
                with open(f"./RF/cogs/MessageLog/{guild.id}.txt", "rb") as f:
                    await channel.send(file=File(f))
        else:
            return


    async def get_mute_role(self, ctx: Context) -> Role:
        guild_id = self.bot.GUILD_DB.find_one({"_id": ctx.guild.id})

        if guild_id["Mute role"] is None:
            raise ResponseError(message="No mute role specified!")
        else:
            return (ctx.guild.get_role(guild_id["Mute role"]))


    @staticmethod
    async def time_converter(durations: str) -> int:
        timeConverter = {"s":1, "m":60, "h":3600,"d":86400}
        for index, item in enumerate(durations):
            try:
                number, times = int(item), "s"
            except ValueError:
                number, times = durations[:index] , durations[index]
                break
                
        return (int(number)) * timeConverter[times]


    @staticmethod
    async def requirements(ctx: Context, member: Member) -> bool:
        isAdmin = member.guild_permissions.administrator
        isOwner = ctx.author.id == ctx.guild.owner.id

        author = ctx.author.top_role.position
        bot = ctx.guild.me.top_role.position
        mem = member.top_role.position
        
        if (bot > mem) and (isOwner or (author > mem and not isAdmin)):
            return True
        elif bot < mem:
            raise ResponseError(message="I do not have permission to do that.")
        elif author < mem:
            raise ResponseError(message="You do not have permission to do that.")
        elif isAdmin:
            raise ResponseError(message="You do not have permission to mute Administrator.")


    async def kick_members(self, ctx: Context, member: Member, reason:str = "No") -> None:
        if await self.requirements(ctx, member):
            
            await member.kick(reason=reason)
            
            embed = Embed(title=f" Kicked | {member}", colour=0xff470f, timestamp=datetime.utcnow())
            embed.set_footer(text=f"User IDs: {member.id}")

            fields =  [("Member: ", member.mention, True),
                        ("Moderator: ", ctx.author.mention, True),
                        ("Reason: ", reason, True),]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)
            await self.logSend(ctx, embed)


    async def mute_members(self, ctx: Context, member: Member, durations: int, reason: str, auto: bool = False) -> None:
        muteRole = await self.get_mute_role(ctx)

        if muteRole not in member.roles:
            if await self.requirements(ctx, member):
                memberRolesID = [role.id for role in member.roles]
                self.bot.MUTE_DB.insert_one({"Member ID": member.id, "Roles": memberRolesID, "Guild ID": ctx.guild.id})
                await member.edit(roles=[muteRole], reason=f"Muted by {ctx.author}, Reason: {reason}")

                if durations is not None:
                    times = await self.time_converter(durations)
                    expireTime = datetime.now(tz=timezone("Asia/Ho_Chi_Minh")) + timedelta(seconds=times)
                    timeLeft = ((f"{times:,.0f} second(s)") if times < 60 
                                else (f"{times / 60:,.1f} minute(s)") if times < 3600 
                                else (f"{times / 3600:,.1f} hour(s)") if times < 86400
                                else (f"{times / 86400:,.1f} day(s)"))

                    self.bot.scheduler.add_job(self.unmutes_members, id=f"{member.id}-Mute", kwargs={'ctx':ctx, 'member':member, 'isBot':True}, next_run_time=expireTime)
                    self.bot.SCHEDULER.insert_one({"_id": f"{member.id}-Mute", "Guild ID": ctx.guild.id, 
                                                   "Expired": (datetime.now() + timedelta(seconds=times)).strftime('%d-%m-%Y-%H-%M-%S'),})
                else:
                    timeLeft = "Indefinite"

                embed = Embed(title=f"Mute | {member}", colour=0xff470f, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")))
                embed.set_footer(text=f"User ID: {member.id}")

                fields = [("Member: ", member.mention, True),
                          ("Moderator: ", ctx.author.mention if not auto else ctx.guild.me.mention, True),
                          ("Duration: ",timeLeft, False),
                          ("Expire: ", f"<t:{str(expireTime.timestamp()).split('.')[0]}:R>" if durations is not None else timeLeft, True),
                          ("Reason: ", reason, False),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)
                await self.logSend(ctx, embed)
        else:
            await ctx.send("This user have already been mute.", delete_after=self.DELETE_AFTER)


    async def unmutes_members(self, ctx:Context, member:Member, reason:str="Mute time expired.", isBot:bool = False) -> None:
        muteRole = await self.get_mute_role(ctx)
        if muteRole in member.roles:
            userRolesID:list =  self.bot.MUTE_DB.find_one({"Member ID": member.id, "Guild ID": ctx.guild.id})["Roles"]
            userRoles:list = [ctx.guild.get_role(id) for id in userRolesID]

            await member.edit(roles=userRoles, reason=f"Unmutes by {ctx.author}, Reason: {reason}")

            self.bot.MUTE_DB.delete_one({"Member ID": member.id, "Guild ID": ctx.guild.id})
            self.bot.SCHEDULER.delete_one({"_id": f"{member.id}-Mute", "Guild ID": ctx.guild.id})

            try:
                self.bot.scheduler.remove_job(job_id=f"{member.id}-Mute")
            except JobLookupError:
                pass

            embed = Embed(title=f"Unmutes | {member}", colour=0x43b582, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")))
            embed.set_footer(text=f"User ID: {member.id}")

            fields = [("Member: ", member.mention, True),
                      ("Moderator: ", ctx.author.mention if not isBot else ctx.guild.me.mention, True),
                      ("Reason: ", reason, True),]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            if not isBot:
                await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)

            await self.logSend(ctx, embed)
        else:
            await ctx.send("This user haven't been muted.", delete_after=self.DELETE_AFTER)


    async def unban_members(self, ctx: Context, member: Member, reason: str) -> None:
        await ctx.guild.unban(member, reason=reason)

        embed = Embed(title=f"Banned | {member}", colour=0xff470f, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")))
        embed.set_footer(text=f"User ID: {member.id}")

        fields = [("Member: ", member.name, False),
                  ("Moderator: ", ctx.author.mention, False),
                  ("Reason: ", reason, False)]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)
        await self.logSend(ctx, embed)


    async def ban_members(self, ctx: Context, member: Member, reason: str) -> None:
        if await self.requirements(ctx, member):
            await member.ban(reason=reason)

            embed = Embed(title=f"Banned | {member}", colour=0xff470f, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")))
            embed.set_footer(text=f"User IDs: {member.id}")

            fields = [("Member: ", member.name, False),
                      ("Moderator: ", ctx.author.mention, False),
                      ("Reason: ", reason, False)]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)
            await self.logSend(ctx, embed)


    async def warnings(self, ctx: Context, member: Member) -> None:
        warnings =  [[intel["_id"], intel['Moderator'], intel["reason"]] for intel in self.bot.WARN_DB.find({"UserID": member.id, "Guild ID": ctx.guild.id})]
        total_warns = len(warnings)
        if total_warns:
            embed = Embed(colour=0xe86b6b)
            embed.set_author(name = f"{total_warns} warning(s) for {member} ({member.id})" ,icon_url=member.display_avatar)
            for warnID, moderator, reason in warnings:
                moderator = ctx.guild.get_member(moderator)
                embed.add_field(name=f"ID: {warnID} | Moderator: {moderator}", value=reason, inline=False)
        else:
            embed = Embed(title='No warning found for this user', color=0xf3ae06)

        await ctx.send(embed=embed)
            
    
    async def del_warns(self, ctx: Context, warnID: str) -> None:
        warnings = self.bot.WARN_DB.find_one({"_id": warnID, "Guild ID": ctx.guild.id})
        user = ctx.guild.get_member(warnings["UserID"])

        if len(list(warnings)):
            self.WARN_DB.delete_one({"_id": warnID, "Guild ID": ctx.guild.id})
            embed = Embed(color=0x43b582, description=f"Deleted warning `{warnID}` for {user}.")
        else:
            embed = Embed(color=0xff470f, description=f"No warning found with that id.")

        await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)


    async def warns(self, ctx: Context, member: Member, reason: str) -> None:
        warn_id = str(uuid4())
        time = datetime.now().timestamp()
        self.bot.WARN_DB.insert_one({"_id": warn_id, "Guild ID": ctx.guild.id ,"UserID": member.id, "Moderator": ctx.author.id, "reason": f"{reason} <t:{time}:R>"})

        embed = Embed(title=f" Warned | {member}", colour=0xff470f, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")))
        embed.set_footer(text=f"User IDs: {member.id}")

        fields =  [("Member: ", member.mention, True),
                    ("Moderator: ", ctx.author.mention, True),
                    ("Reason: ", reason, True),]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)
        await self.logSend(ctx, embed)