from datetime import datetime
from os import getenv

from discord import Embed
from discord.ext.commands import Cog
from pymongo import MongoClient


class Log(Cog):
    def __init__(self, bot):
        self.bot = bot

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']


    async def log_send(self, guild, embed):
        log_channel_id = self.GUILD_DB.find_one({"_id": guild.id})["Log channel"] if self.GUILD_DB.find_one({"_id": guild.id}) is not None else None

        if log_channel_id is not None:
            await self.bot.get_channel(log_channel_id).send(embed=embed)
        else:
            pass


    @Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            embed = Embed(title="", colour=0x337fd5, timestamp=datetime.utcnow())
            embed.set_author(name=after, icon_url=after.avatar_url)
            embed.set_footer(text=f"Author: {after}, ID: {after.id}")

            fields = [("Before ", ", ".join([r.mention for r in before.roles]), False),
					  ("After ", ", ".join([r.mention for r in after.roles]), False)]
            
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await self.log_send(after.guild, embed)


    @Cog.listener()
    async def on_message_edit(self, before, after):
        if not after.author.bot:
            if before.content != after.content:
                embed = Embed(title='', colour=0x337fd5, timestamp=datetime.utcnow(), description=f"**Message edited in** {after.channel.mention} [Jump to message]({after.jump_url})")
                embed.set_footer(text=f"User ID: {after.author.id}")
                embed.set_author(name=after.author, icon_url=after.author.avatar_url)

                fields = [("Before", before.content, False),
                          ("After", after.content, False)]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.log_send(after.guild, embed)


    @Cog.listener()
    async def on_message_delete(self, message):
        if not message.author.bot:
            embed = Embed(title='', description=f"**Message sent by {message.author.mention} deleted in {message.channel.mention}** \n{message.content}", colour=0xff470f, timestamp=datetime.utcnow())
            embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
            embed.set_author(name=message.author, icon_url=message.author.avatar_url)

            await self.log_send(message.guild, embed)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Log")


def setup(bot):
    bot.add_cog(Log(bot))
