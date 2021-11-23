from datetime import datetime, timedelta
from os import getenv
from typing import Optional
from uuid import uuid4

from apscheduler.jobstores.base import JobLookupError
from dotenv import load_dotenv
from nextcord import Embed, Member, Role, TextChannel, User
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


    async def log_send(self, ctx: Context, embed: Embed) -> None:
        Guild = self.bot.GUILD_DB.find_one({"_id": ctx.guild.id})
        log_channel_id = Guild["Log channel"] if Guild is not None else None

        if log_channel_id is not None:
            await self.bot.get_channel(log_channel_id).send(embed=embed)


    async def get_mute_role(self, ctx: Context) -> Role:
        guild_id = self.bot.GUILD_DB.find_one({"_id": ctx.guild.id})

        if guild_id["Mute role"] is None:
            await ctx.send("No mute role specified!", delete_after=self.DELETE_AFTER)
        else:
            return (ctx.guild.get_role(guild_id["Mute role"]))


    @staticmethod
    async def time_converter(durations: str) -> int:
        timeConverter = {"s":1, "m":60, "h":3600,"d":86400}
        for index, item in enumerate(durations):
            try:
                int(item)
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
            raise ResponseError(message="Insufficient permissions for me to perform that task.")
        elif author < mem:
            raise ResponseError(message="Insufficient permissions to perform that task.")
        elif isAdmin:
            raise ResponseError(message="Administrator is immune to this task.")


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
            await self.log_send(ctx, embed)


    async def mute_members(self, ctx: Context, member: Member, durations: int, reason: str, auto: bool = False) -> None:
        muteRole = await self.get_mute_role(ctx)

        if muteRole not in member.roles:
            if await self.requirements(ctx, member):
                memberRolesID = [role.id for role in member.roles]
                self.bot.MUTE_DB.insert_one({"Member ID": member.id, "Roles": memberRolesID, "Guild ID": ctx.guild.id})
                await member.edit(roles=[muteRole], reason=f"Muted by {ctx.author}, Reason: {reason}")

                if durations is not None:
                    duration = await self.time_converter(durations)
                    expireTime = datetime.now(tz=timezone("Asia/Ho_Chi_Minh")) + timedelta(seconds=duration)
                    timeLeft = ((f"{duration:,.0f} second(s)") if duration < 60 
                                else (f"{duration / 60:,.0f} minute(s)") if duration < 3600 
                                else (f"{duration / 3600:,.0f} hour(s)") if duration < 86400
                                else (f"{duration / 86400:,.0f} day(s)"))

                    self.bot.scheduler.add_job(self.unmutes_members, id=f"{member.id}-Mute", kwargs={'ctx':ctx, 'member':member, 'isBot':True}, next_run_time=expireTime)
                    self.bot.SCHEDULER.insert_one({"_id": f"{member.id}-Mute", 
                                          "Expired": (datetime.now() + timedelta(seconds=duration)).strftime('%d-%m-%Y-%H-%M-%S'),
                                          "Guild ID": ctx.guild.id,})
                else:
                    timeLeft = "Indefinite"

                embed = Embed(title=f"Mute | {member}", colour=0xff470f, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")))
                embed.set_footer(text=f"User ID: {member.id}")

                fields = [("Member: ", member.mention, True),
                          ("Moderator: ", ctx.author.mention if not auto else ctx.guild.me.mention, True),
                          ("Duration: ",timeLeft, False),
                          ("Expire: ", f"<t:{str(expireTime.timestamp()).split('.')[0]}:R>" if duration is not None else timeLeft, True),
                          ("Reason: ", reason, False),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await ctx.send(embed=embed, delete_after=self.DELETE_AFTER)
                await self.log_send(ctx, embed)
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

            await self.log_send(ctx, embed)
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
        await self.log_send(ctx, embed)


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
            await self.log_send(ctx, embed)


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
        await self.log_send(ctx, embed)