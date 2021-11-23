from datetime import datetime
from typing import Optional

from nextcord import Embed, File
from nextcord.ext.commands import Cog
from pytz import timezone

from ..bot import RF


class Log(Cog):
    def __init__(self, bot: RF):
        self.bot = bot


    async def log_send(
        self, guild, embed: Optional[Embed] = None, file: Optional[File] = None) -> None:
        log_channel_id = (self.bot.GUILD_DB.find_one({"_id": guild.id})["Log channel"] if self.bot.GUILD_DB.find_one({"_id": guild.id}) is not None else None)
        channel = self.bot.get_channel(log_channel_id)

        if log_channel_id is not None:
            if embed is not None:
                await channel.send(embed=embed)
            elif file is not None:
                with open("./cogs/message.txt", "rb") as f:
                    await channel.send(file=File(f))
        else:
            pass


    @Cog.listener()
    async def on_member_update(self, before, after) -> None:
        if before.roles != after.roles:
            
            
            if len(after.roles) < len(before.roles):  # Remove roles
                filter_role = list(filter(lambda r: r not in after.roles, before.roles))

                if len(filter_role) > 1:
                    sorted_roles = sorted(filter_role, key=lambda r: r.position, reverse=True)
                    roles = ", ".join([role.mention for role in sorted_roles])
                    description = (f"{after.mention} was removed from the roles:\n{roles}")
                else:
                    description = (f"{after.mention} was removed from {filter_role[0].mention}")

                embed = Embed(colour=0xFF470F,timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),description=f"**{description}**",)
            else:  # Receive roles
                filter_role = list(filter(lambda r: r not in before.roles, after.roles))

                if len(filter_role) > 1:
                    sorted_roles = sorted(filter_role, key=lambda r: r.position, reverse=True)
                    roles = ", ".join([role.mention for role in sorted_roles])
                    description = f"{after.mention} was given the roles:\n{roles}"
                else:
                    description = (f"{after.mention} was given the {filter_role[0].mention} role")

                embed = Embed(title="",colour=0xFF470F,timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),description=f"**{description}**",)

            embed.set_author(name=after, icon_url=after.display_avatar)
            embed.set_footer(text=f"Author: {after}, ID: {after.id}")

            await self.log_send(after.guild, embed=embed)


    @Cog.listener()
    async def on_message_edit(self, before, after) -> None:
        if not after.author.bot:
            if before.content != after.content:
                embed = Embed(colour=0x337FD5, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")), description=f"**Message edited in** {after.channel.mention} [Jump to message]({after.jump_url})",)
                embed.set_footer(text=f"User ID: {after.author.id}")
                embed.set_author(name=after.author, icon_url=after.author.display_avatar)

                fields = [("Before", before.content, False), ("After", after.content, False),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.log_send(after.guild, embed=embed)


    @Cog.listener()
    async def on_message_delete(self, message) -> None:
        if not message.author.bot:
            embed = Embed(description=f"**Message sent by {message.author.mention} deleted in {message.channel.mention}** \n{message.content}", colour=0xFF470F, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
            embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
            embed.set_author(name=message.author, icon_url=message.author.display_avatar)

            await self.log_send(message.guild, embed=embed)


    @Cog.listener()
    async def on_command_completion(self, ctx) -> None:
        embed = Embed(colour=0x2F3136, description=f"Used `{ctx.command}` command in {ctx.channel.mention} \n{ctx.message.content}", timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)

        await self.log_send(ctx.guild, embed=embed)


    @Cog.listener()
    async def on_bulk_message_delete(self, messages) -> None:
        with open("./cogs/message.txt", "w") as f:
            f.write(f"{len(messages)} messages deleted in #{messages[0].channel.name}:\n\n\n")
            for message in messages:
                f.write(f"{message.author} (User ID: {message.author.id} Message ID: {message.id})\n{message.content}\n\n\n")

        await self.log_send(messages[0].guild, file=f)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Log")


def setup(bot):
    bot.add_cog(Log(bot))
