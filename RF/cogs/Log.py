from datetime import datetime
from typing import List
from json import load, dump
from os.path import exists

from nextcord import Embed, Member, Message
from nextcord.ext.commands import Cog, Context
from pytz import timezone

from ..bot import RF
from ..utils import Moderation


class Log(Cog):
    def __init__(self, bot: RF):
        self.bot = bot
        self.Moderation = Moderation(bot)


    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        if before.roles != after.roles:
            if len(after.roles) < len(before.roles):  # Remove roles
                filter_role = list(filter(lambda r: r not in after.roles, before.roles))

                if len(filter_role) > 1:
                    sorted_roles = sorted(filter_role, key=lambda r: r.position, reverse=True)
                    roles = ", ".join([role.mention for role in sorted_roles])
                    description = f"{after.mention} was removed from the roles:\n{roles}"
                else:
                    description = f"{after.mention} was removed from {filter_role[0].mention}"

            else:  # Receive roles
                filter_role = list(filter(lambda r: r not in before.roles, after.roles))

                if len(filter_role) > 1:
                    sorted_roles = sorted(filter_role, key=lambda r: r.position, reverse=True)
                    roles = ", ".join([role.mention for role in sorted_roles])
                    description = f"{after.mention} was given the roles:\n{roles}"
                else:
                    description = f"{after.mention} was given the {filter_role[0].mention} role"

            embed = Embed(colour=0xFF470F,timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),description=f"**{description}**",)
            embed.set_author(name=after, icon_url=after.display_avatar)
            embed.set_footer(text=f"Author: {after}, ID: {after.id}")

            await self.Moderation.logSend(after.guild, embed=embed)


    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message) -> None:
        if not after.author.bot:
            if before.content != after.content:
                embed = Embed(colour=0x337FD5, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")), description=f"**Message edited in** {after.channel.mention} [Jump to message]({after.jump_url})",)
                embed.set_footer(text=f"User ID: {after.author.id}")
                embed.set_author(name=after.author, icon_url=after.author.display_avatar)

                fields = [("Before", before.content, False), ("After", after.content, False),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.Moderation.logSend(after.guild, embed=embed)
                
    
    def sniperUser(self, message: Message):
        filePath = f"./RF/cogs/MessageLog/{message.guild.id}-sniper.json"
        

        def logMessage(message: Message):
            with open(filePath, "r+") as f:
                data = load(f)
                data[str(message.author.id)] = message.content
                data[str(message.guild.id)] = {message.author.id: message.content}

                f.seek(0)
                dump(data, f, indent=4)
                f.truncate()

        if not exists(filePath):
            with open(filePath, "w") as f:
                f.write("{}")
                
            logMessage(message)
        else:
            logMessage(message)


    @Cog.listener()
    async def on_message_delete(self, message: Message) -> None:
        if not message.author.bot:
            embed = Embed(description=f"**Message sent by {message.author.mention} deleted in {message.channel.mention}** \n{message.content}", colour=0xFF470F, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
            embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
            embed.set_author(name=message.author, icon_url=message.author.display_avatar)
            
            self.sniperUser(message)

            await self.Moderation.logSend(message.guild, embed=embed)


    @Cog.listener()
    async def on_command_completion(self, ctx: Context) -> None:
        embed = Embed(colour=0x2F3136, description=f"Used `{ctx.command}` command in {ctx.channel.mention} \n{ctx.message.content}", timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)

        await self.Moderation.logSend(ctx.guild, embed=embed)


    @Cog.listener()
    async def on_bulk_message_delete(self, messages: List[Message]) -> None:
        with open(f"./RF/cogs/MessageLog/{messages[0].guild.id}.txt", "w") as f:
            f.write(f"{len(messages)} messages deleted in #{messages[0].channel.name}:\n\n\n")
            for message in messages:
                f.write(f"{message.author} (User ID: {message.author.id} Message ID: {message.id})\n{message.content}\n\n\n")

        await self.Moderation.logSend(messages[0].guild, file=f)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Log")


def setup(bot):
    bot.add_cog(Log(bot))
