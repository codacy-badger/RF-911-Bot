from asyncio import sleep
from datetime import datetime, timedelta, date
from os import getenv
from typing import Optional
from uuid import uuid4

from nextcord import Embed, Member, NotFound, Object, Role, TextChannel
from nextcord.ext.commands import (BadArgument, CheckFailure, Cog, Converter,
                                  Greedy, bot_has_permissions, command,
                                  has_permissions)
from nextcord.utils import find, get
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from . import del_user_msg


class BannedUser(Converter):
    async def convert(self, ctx, arg):
        if ctx.guild.me.guild_permissions.ban_members:
            if arg.isdigit():
                try:
                    return (await ctx.guild.fetch_ban(Object(id=int(arg)))).user
                except NotFound:
                    raise BadArgument

        banned = [e.user for e in await ctx.guild.bans()]
        if banned:
            if (user := find(lambda u: str(u) == arg, banned)) is not None:
                return user
            else:
                raise BadArgument    


class Mod(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DELETE_AFTER = 15

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.MUTE_DB = self.DB["Mute"]
        self.CASE_DB = self.DB["Case"]
        self.WARN_DB = self.DB["Warns"]
        self.BANNED_USER_DB = self.DB["Banned User"]


    async def log_send(self, ctx, embed):
        log_channel_id = self.GUILD_DB.find_one({"_id": ctx.guild.id})["Log channel"] if self.GUILD_DB.find_one({"_id": ctx.guild.id}) is not None else None

        if log_channel_id is not None:
            await self.bot.get_channel(log_channel_id).send(embed=embed)


    def time_converter(self, times):
        if times is not None:
            time_convert = {"s":1, "m":60, "h":3600,"d":86400}
            return int(times[:-1]) * time_convert[times[-1]]
        return None


    async def get_mute_role(self, ctx):
        guild_id = self.GUILD_DB.find_one({"_id": ctx.guild.id})

        if guild_id["Mute role"] is None:
            await ctx.channel.send("No mute role specified!", delete_after = self.DELETE_AFTER)
        else:
            return (get(self.bot.get_guild(ctx.guild.id).roles, id= guild_id["Mute role"]))


    def check_role(self, ctx, target):
        author_role, bot_role, target_role, owner_ids, author_ids, is_admins = self.get_roles(ctx, target)

        if ((owner_ids == author_ids and bot_role > target_role)
            or (author_role > target_role and bot_role > target_role and not is_admins)):
            return True
        return False

    
    async def response(self, ctx, target):
        author_role, bot_role, target_role, owner_ids, author_ids, is_admins = self.get_roles(ctx, target)

        if (author_role <= target_role and owner_ids != author_ids):
            await ctx.channel.send("Sorry but you don't have enough permission to do that", delete_after = 5)
        elif (bot_role <= target_role):
            await ctx.channel.send("Sorry but i don't have enough permission to do that", delete_after = 5)
        elif is_admins:
            await ctx.channel.send("Sorry but you can't kick/ban/mute administrators", delete_after = 5)


    def get_roles(self, ctx, target):
        author_role = ctx.author.top_role.position
        bot_role = ctx.guild.me.top_role.position
        target_role = target.top_role.position
        owner_ids = ctx.guild.owner.id
        author_ids = ctx.author.id
        is_admins = target.guild_permissions.administrator

        return author_role,bot_role,target_role,owner_ids,author_ids,is_admins
    

    async def lockdown_start(self, ctx, channel):
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)


    async def lockdown_end(self, ctx, channel):
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)


    @command(name="set-lockdown-channel", aliases=["sldc"], description="Specify list of channel to lockdown. Required administrator permissions.")
    @has_permissions(administrator=True)
    async def add_lockdown_command(self, ctx, *, channel):

        lockdown_channel_ids = [int(channel_id.replace("<#", '').replace(">", '')) for channel_id in channel.split(',')]
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Lockdown channel": lockdown_channel_ids}})

        await ctx.send(f"Added {channel} to lockdown channels", delete_after = self.DELETE_AFTER)


    @command(name="lockdown" , description="Lockdown channels. Required administrator permissions.")
    @bot_has_permissions(administrator=True)
    @has_permissions(administrator=True)
    async def lockdown_command(self, ctx, option: Optional[str] = "start"):
        lockdown_channel = self.GUILD_DB.find_one({"_id": ctx.guild.id})["Lockdown channel"]

        if "end" in option.lower():
            for channel_id in lockdown_channel:
                channel = self.bot.get_channel(channel_id)
                await self.lockdown_end(ctx, channel)
            await ctx.send("Unlocked all selected channels")

        elif "start" in option.lower():
            for channel_id in lockdown_channel:
                channel = self.bot.get_channel(channel_id)
                await self.lockdown_start(ctx, channel)
            await ctx.send("Locked down all selected channels")


    async def warn_members(self, ctx, targets, reason):
        for target in targets:
            warn_id = str(uuid4())
            time = date.today().strftime("%b %d %Y")
            self.WARN_DB.insert_one({"_id": warn_id, "Guild ID": ctx.guild.id ,"user": target.id, "Moderator": ctx.author.id, "reason": f"{reason} {time}"})

            embed = Embed(title=f" Warned | {target.name}#{target.discriminator}", colour=0xff470f, timestamp=datetime.utcnow())
            embed.set_footer(text=f"User IDs: {target.id}")

            fields =  [("Member: ", target.mention, True),
                        ("Moderator: ", ctx.author.mention, True),
                        ("Reason: ", reason, True),]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await ctx.channel.send(embed=embed, delete_after = 30)
            await self.log_send(ctx, embed)


    @command(name="warn", description="Warn the specified user. Required administrator permissions.")
    @has_permissions(administrator=True)
    async def warn_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "No reason provided."):
        
        if not len(targets):
            await ctx.send("One or more required arguments are missing.")
        else:
            await self.warn_members(ctx, targets, reason)


    @command(name="del-warn", aliases=['remove-warn'], description="Delete a warn for specified user. Required administrator permissions.")
    @has_permissions(administrator=True)
    async def del_warn_command(self, ctx, warnings_id):
        
        if not len(warnings_id):
            await ctx.send("One or more required arguments are missing.")
        else:
            warnings = self.WARN_DB.find_one({"_id": warnings_id, "Guild ID": ctx.guild.id})
            user = self.bot.get_user(warnings["user"])

            if len(list(warnings)):
                self.WARN_DB.delete_one({"_id": str(warnings_id), "Guild ID": ctx.guild.id})
                embed = Embed(title='',  color=0x43b582, description=f"Deleted warning `{warnings_id}` for {user}.", delete_after=self.DELETE_AFTER)
                await ctx.send(embed=embed)
            else:
                embed = Embed(title='',  color=0xff470f, description=f"No warning found with that id.", delete_after=self.DELETE_AFTER)
                await ctx.send(embed=embed)

    
    @command(name="warnings", description="Warn the specified user. Required administrator permissions.")
    @has_permissions(administrator=True)
    async def warnings_command(self, ctx, targets: Greedy[Member]):

        targetID = (target.id for target in targets).__next__()

        if not len(targets):
            await ctx.send("One or more required arguments are missing.")
        else:
            warnings =  [[intel["_id"], intel['Moderator'], intel["reason"]] for intel in self.WARN_DB.find({"user": targetID, "Guild ID": ctx.guild.id})]
            total_warns = len(warnings)
            user = self.bot.get_user(targetID)
            if total_warns:
                embed = Embed(title = '', colour=0xe86b6b)
                embed.set_author(name = f"{total_warns} warning(s) for {user.name}#{user.discriminator} ({targetID})" ,icon_url=user.display_avatar)
                for warnID, moderator, reason in warnings:
                    moderator = self.bot.get_user(moderator)
                    embed.add_field(name=f"ID: {warnID} | Moderator: {moderator.name}#{moderator.discriminator}", value=reason, inline=False)

                await ctx.send(embed=embed)
            else:
                embed = Embed(title='No warning found for this user', color=0xf3ae06)
                await ctx.send(embed=embed)


    async def kick_members(self, ctx, targets, reason):
        for target in targets:
            pass_required = self.check_role(ctx, target)
            if pass_required:

                await target.kick(reason=reason)
                
                embed = Embed(title=f" Kicked | {target.name}#{target.discriminator}", colour=0xff470f, timestamp=datetime.utcnow())
                embed.set_footer(text=f"User IDs: {target.id}")

                fields =  [("Member: ", target.mention, True),
                          ("Moderator: ", ctx.author.mention, True),
                          ("Reason: ", reason, True),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await ctx.channel.send(embed=embed, delete_after = 30)
                await self.log_send(ctx, embed)

            else:
                await self.response(ctx, target)


    @command(name="kick", description="Kick the specified user. Required administrator permissions.")
    @bot_has_permissions(kick_members=True)
    @has_permissions(administrator=True)
    async def kick_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "No reason provided."):

        if not len(targets):
            await ctx.send("One or more required arguments are missing.")
        else:
            await self.kick_members(ctx, targets, reason)

    
    @command(name='banned',InvokeWithoutCommand=True, description='Show currently banned users list. Required administrator permissions.')
    @bot_has_permissions(manage_roles=True, ban_members=True)
    @has_permissions(administrator=True)
    async def _banned(self, ctx):
        '''Show banned user, require ban member permissions'''

        banned_users = await ctx.guild.bans()

        author = ctx.message.author
        embed = Embed(name="", color=0xDD2222)
        embed.set_author(name="Banned users:")

        if banned_users != []:
            for ban_entry in banned_users:
                user = ban_entry.user
                embed.add_field(name=f"User: ", value=f"{user}\n ID : {user.id}", inline=False)
        else:
            embed.add_field(name=f"No one have been banned.",value=f"|| ||", inline=False)

        await ctx.channel.send(embed=embed)


    async def ban_members(self, ctx, targets, reason):
        for target in targets:
            pass_required = self.check_role(ctx, target)
            if pass_required:

                await target.ban(reason=reason)
                
                embed = Embed(title=f" Banned | {target.name}#{target.discriminator}", colour=0xff470f, timestamp=datetime.utcnow())
                embed.set_footer(text=f"User IDs: {target.id}")

                fields = [("Member: ", target.mention, True),
                          ("Moderator: ", ctx.author.mention, True),
                          ("Reason: ", reason, True),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await ctx.channel.send(embed=embed, delete_after = 30)
                await self.log_send(ctx, embed)

            else:
                await self.response(ctx, target)


    @command(name="ban", description="Ban the specified user. Required administrator permissions.")
    @bot_has_permissions(ban_members=True)
    @has_permissions(administrator=True)
    async def ban_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "No reason provided."):

        if not len(targets):
            await ctx.send("One or more required arguments are missing.")
        else:
            await self.ban_members(ctx, targets, reason)

    
    @command(name="unban", description="Unban the specified user. Required administrator permissions.")
    @bot_has_permissions(ban_members=True)
    @has_permissions(administrator=True)
    async def unban_command(self, ctx, targets: Greedy[BannedUser], *, reason: Optional[str] = "No reason provided."):
        if not len(targets):
            await ctx.send("One or more required arguments are missing.")

        else:
            for target in targets:
                await ctx.guild.unban(target, reason=reason)

                embed = Embed(title=f" Banned | {target.name}#{target.discriminator}", colour=0xff470f, timestamp=datetime.utcnow())
                embed.set_footer(text=f"User IDs: {target.id}")

                fields = [("Member", target.name, False),
                          ("Actioned by", ctx.author.display_name, False),
                          ("Reason", reason, False)]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await ctx.send(embed=embed, delete_after = 30)
                await self.log_send(ctx, embed)


    async def mute_members(self, ctx, targets, durations, reason, auto=False):
        unmutes = []
        mute_role = await self.get_mute_role(ctx) # Get mute role
        tempmute = self.time_converter(durations) # Get duration

        for target in targets:
            if not mute_role in target.roles: # If user havent been muted 
                pass_required = self.check_role(ctx, target)
                if pass_required or auto:
                    
                    role_ids = ",".join([str(r.id) for r in target.roles]) # Get all user's roles
                    end_time = datetime.utcnow() + timedelta(seconds=tempmute) if tempmute else None # Calculate end time
                    attr = getattr(end_time, "isoformat", lambda: None)() # Get end time

                    self.MUTE_DB.insert_one({"_id": target.id, "role_ids": role_ids,"end time": attr, "Guild ID": ctx.guild.id})
                    await target.edit(roles=[mute_role])

                    if durations is not None:
                        duration = (f"{int(tempmute)} second(s)") if tempmute < 60 else (f"{int(tempmute) / 60} minute(s)") if tempmute < 3600 else (f"{int(tempmute) / 3600} hour(s)") if tempmute < 86400 else (f"{int(tempmute) / 86400} day(s)")
                    else:
                        duration, tempmute = "Indefinite", None

                    embed = Embed(title=f" Mute | {target.name}#{target.discriminator}", colour=0xff470f, timestamp=datetime.utcnow())
                    embed.set_footer(text=f"User IDs: {target.id}")

                    fields = [("Member: ", target.mention, True),
                              ("Moderator: ", ctx.author.mention if not auto else ctx.guild.me.mention, True),
                              ("Duration: ",f"{duration}", True),
                              ("Reason: ", reason, True),]

                    for name, value, inline in fields:
                        embed.add_field(name=name, value=value, inline=inline)

                    await ctx.channel.send(embed=embed, delete_after = self.DELETE_AFTER)
                    await self.log_send(ctx, embed)
                    
                else:
                    await self.response(ctx, target)

                if tempmute: # If user not be muted permanent
                    unmutes.append(target)

            else:
                await ctx.channel.send("This user already muted")

        return unmutes


    @command(name="mute", description="Mute the specified user. Required administrator permissions.")
    @bot_has_permissions(manage_roles=True)
    @has_permissions(administrator=True)
    async def mute_command(self, ctx, targets: Greedy[Member], durations: Optional[str], *,
                                 reason: Optional[str] = "No reason provided."):

        if not len(targets):
            await ctx.send("One or more required arguments are missing.")
        else:     
            unmutes = await self.mute_members(ctx, targets, durations, reason)
            tempmute = self.time_converter(durations)

            if len(unmutes):
                await sleep(tempmute)
                await self.unmute_members(ctx, ctx.guild, targets)


    @mute_command.error
    async def mute_command_error(self, ctx, exc):
        if isinstance(exc, CheckFailure):
            await ctx.send("Insufficient permissions to perform that task.")


    async def unmute_members(self, ctx, guild, targets, *, reason="Mute time expired.", auto = False):
        mute_role = await self.get_mute_role(ctx)
        for target in targets:
            if mute_role in target.roles:
                before_mute_roles = self.MUTE_DB.find_one({"_id": target.id})

                role_ids = before_mute_roles["role_ids"]
                roles = [guild.get_role(int(role_id)) for role_id in role_ids.split(",") if len(role_ids)]

                self.MUTE_DB.delete_one({"_id": target.id, "Guild ID": ctx.guild.id})

                await target.edit(roles=roles)

                embed = Embed(title=f" Unmute | {target.name}#{target.discriminator}", colour=0x43b582, timestamp=datetime.utcnow())
                embed.set_footer(text=f"User IDs: {target.id}")

                fields = [("Member: ", target.mention, True),
                          ("Moderator: ", ctx.author.mention if not auto else ctx.guild.me.mention, True),
                          ("Reason: ", reason, True),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await ctx.channel.send(embed=embed,delete_after = self.DELETE_AFTER)
                await self.log_send(ctx, embed)

            else:
                await ctx.channel.send("Sorry but this user haven't been muted")
    

    @command(name="unmute", description="Unmute the specified user. Required administrator permissions.")
    @bot_has_permissions(manage_roles=True)
    @has_permissions(administrator=True)
    async def unmute_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "No reason provided."):
        if not len(targets):
            await ctx.send("One or more required arguments is missing.")
        else:
            await self.unmute_members(ctx ,ctx.guild, targets, reason=reason)


    @command(name="set-mute-role", aliases=['smr'], description='Set mute role. Required administrator permissions.')
    @has_permissions(administrator=True)
    async def _set_mute_role(self, ctx, roles: Greedy[Role]):
        await del_user_msg(ctx)

        role_id = (role.id for role in roles).__next__()
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Mute role": role_id}})

        for channel in ctx.guild.channels:
            await channel.set_permissions(ctx.guild.get_role(role_id), send_messages=False)

        await ctx.send(content=f"Mute role have been set/update to <@&{role_id}>", delete_after = self.DELETE_AFTER)


    @command(name='set-log-channel', aliases=['slc'], description="Set log channel for logging. Required administrator permissions.")
    @bot_has_permissions(administrator=True)
    async def _logchannel(self, ctx, channel: Greedy[TextChannel]):
        await del_user_msg(ctx)

        channel_id = (channel.id for channel in channel).__next__()
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Log channel": channel_id}})

        await ctx.channel.send(f'Log channel has been added/updated <#{channel_id}>',delete_after = self.DELETE_AFTER)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Mod")


def setup(bot):
    bot.add_cog(Mod(bot))