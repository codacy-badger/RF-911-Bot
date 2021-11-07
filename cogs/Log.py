from datetime import datetime
from os import getenv

from nextcord import Embed, File
from nextcord.ext.commands import Cog
from pymongo import MongoClient
from typing import Optional


class Log(Cog):
    def __init__(self, bot):
        self.bot = bot

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']


    async def log_send(self, guild, embed : Optional[Embed] = None, file: Optional[File] = None) -> None: 
        log_channel_id = self.GUILD_DB.find_one({"_id": guild.id})["Log channel"] if self.GUILD_DB.find_one({"_id": guild.id}) is not None else None
        channel = self.bot.get_channel(log_channel_id)

        if log_channel_id is not None:
            if embed is not None:
                await channel.send(embed=embed)
            elif file is not None:
                with open("./message.txt", 'rb') as f:
                    await channel.send(file=File(f))
        else:
            pass


    @Cog.listener()
    async def on_member_update(self, before, after) -> None:
        if before.roles != after.roles:
            if len(after.roles) < len(before.roles): # Remove roles
                removed_roles = list(before.roles)
                [removed_roles.remove(role) for role in after.roles]
                roles = ", ".join([role.mention for role in removed_roles])
                embed = Embed(title="", colour=0xff470f, timestamp=datetime.utcnow(), description=f"**{after.mention} was removed from {roles}**")
            else: # Receive roles
                given_roles = list(after.roles)
                [given_roles.remove(role) for role in before.roles]
                roles = ", ".join([role.mention for role in given_roles])
                embed = Embed(title="", colour=0x337fd5, timestamp=datetime.utcnow(), description=f'**{after.mention} was given roles {roles}**')

            embed.set_author(name=after, icon_url=after.display_avatar)
            embed.set_footer(text=f"Author: {after}, ID: {after.id}")

            await self.log_send(after.guild, embed=embed)


    @Cog.listener()
    async def on_message_edit(self, before, after) -> None:
        if not after.author.bot:
            if before.content != after.content:
                embed = Embed(title='', colour=0x337fd5, timestamp=datetime.utcnow(), description=f"**Message edited in** {after.channel.mention} [Jump to message]({after.jump_url})")
                embed.set_footer(text=f"User ID: {after.author.id}")
                embed.set_author(name=after.author, icon_url=after.author.display_avatar)

                fields = [("Before", before.content, False),
                          ("After", after.content, False)]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.log_send(after.guild, embed=embed)


    @Cog.listener()
    async def on_message_delete(self, message) -> None:
        if not message.author.bot:
            embed = Embed(title='', description=f"**Message sent by {message.author.mention} deleted in {message.channel.mention}** \n{message.content}", colour=0xff470f, timestamp=datetime.utcnow())
            embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
            embed.set_author(name=message.author, icon_url=message.author.display_avatar)

            await self.log_send(message.guild, embed=embed)

    
    @Cog.listener()
    async def on_command_completion(self, ctx) -> None:
        embed = Embed(title="", colour=0x2f3136, description=f"Used `{ctx.command}` command in {ctx.channel.mention} \n{ctx.message.content}", timestamp=datetime.utcnow())
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)

        await self.log_send(ctx.guild, embed=embed)


    @Cog.listener()
    async def on_bulk_message_delete(self, messages) -> None:
        with open("message.txt", 'w') as f:
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
