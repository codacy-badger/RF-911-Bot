from typing import Optional

from nextcord import Member, NotFound, Object, Role, TextChannel, User
from nextcord.ext.commands import (BadArgument, Cog, Context, Converter,
                                   bot_has_permissions, command,
                                   has_permissions)
from nextcord.utils import find

from ..bot import RF
from ..utils.Moderation import Moderation
from . import del_user_msg


class BannedUser(Converter):
    async def convert(self, ctx: Context, arg) -> User:
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
    def __init__(self, bot: RF) -> None:
        self.bot = bot
        self.DELETE_AFTER = 15
        self.Moderation = Moderation(bot)
  

    @command(name="warn", description="Warn the specified user.\nRequired `Administrator`permissions.")
    @has_permissions(administrator=True)
    async def kick_command(self, ctx: Context, member: Member, 
                              *, reason: Optional[str] = "No reason provided.") -> None:
        
        await self.Moderation.warns(ctx, member, reason)
        
    
    @command(name="delwarn", description="Delete a warn for specified user.\nRequired `Administrator`permissions.")
    @has_permissions(administrator=True)
    async def kick_command(self, ctx: Context, *, warnID: str) -> None:
        
        await self.Moderation.del_warns(ctx, warnID)
        
    
    @command(name="warnings", description="Show all warnings for specified user.\nRequired `Administrator`permissions.")
    @has_permissions(administrator=True)
    async def kick_command(self, ctx: Context, member: Member) -> None:
        
        await self.Moderation.warnings(ctx, member)


    @command(name="kick", description="Kick the specified user.\nRequired `Administrator`permissions.")
    @bot_has_permissions(kick_members=True)
    @has_permissions(kick_members=True, manage_guild=True)
    async def kick_command(self, ctx: Context, member: Member, 
                              *, reason: Optional[str] = "No reason provided.") -> None:
        
        await self.Moderation.kick_members(ctx, member, reason)


    @command(name="unban", description="Unban the specified user.\nRequired `Administrator`permissions.")
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True, manage_guild=True)
    async def unban_command(self, ctx, member: BannedUser, 
                               *, reason: Optional[str] = "No reason provided."):
        
        await self.Moderation.unban_members(ctx, member, reason)


    @command(name="mute", description="Mute the specified user.\nRequired `Administrator`permissions.")
    @bot_has_permissions(manage_roles=True)
    @has_permissions(administrator=True)
    async def mute_command(self, ctx: Context, member: Member, durations: Optional[str], *,
                                 reason: Optional[str] = "No reason provided.") -> None:
        
        await self.Moderation.mute_members(ctx, member, durations, reason)


    @command(name="unmute", description="Unmutes the specified user.\nRequired `Administrator`permissions.")
    @bot_has_permissions(manage_roles=True)
    @has_permissions(administrator=True)
    async def unmutes_command(self, ctx: Context, member: Member, 
                                 *, reason: Optional[str] = "No reason provided.") -> None:

        await self.Moderation.unmutes_members(ctx, member, reason)


    @command(name="set-mute-role", aliases=['smr'], description='Set mute role.\nRequired `Administrator`permissions.')
    @has_permissions(administrator=True)
    async def _set_mute_role(self, ctx: Context, role: Role) -> None:
        await del_user_msg(ctx)

        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Mute role": role.id}})

        for channel in ctx.guild.channels:
            await channel.set_permissions(ctx.guild.get_role(role), send_messages=False)

        await ctx.send(content=f"Mute role have been set/update to {role.mention}>", delete_after = self.DELETE_AFTER)


    @command(name='set-log-channel', aliases=['slc'], description="Set log channel for logging.\nRequired `Administrator`permissions.")
    @has_permissions(administrator=True)
    async def _logchannel(self, ctx: Context, channel: TextChannel) -> None:
        await del_user_msg(ctx)

        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Log channel": channel.id}})

        await ctx.send(f'Log channel has been added/updated {channel.mention}',delete_after = self.DELETE_AFTER)


    @Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Mod")


def setup(bot):
    bot.add_cog(Mod(bot))
