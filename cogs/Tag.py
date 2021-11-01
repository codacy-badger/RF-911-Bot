from os import getenv

from nextcord import Embed
from nextcord.ext.commands import (Cog, CommandError, command,
                                   has_permissions, is_owner)
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from typing import Optional

from . import del_user_msg


class ExtensionNotloaded(CommandError):
    pass

GC_EMOJI = "<:green_check_mark:882362735969579088>"
X_EMOJI = "❌"


class Tag(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DELETE_AFTER = 45

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.TAG_DB = self.DB['Tag']


    @command(name="tag")
    @has_permissions(manage_guild=True)
    async def tag_command(self, ctx, option: str, tagName: Optional[str], *, tagContent: Optional[str]):
        valid_option = ["create", "edit", "delete"]


        if option.lower() not in valid_option:
            tagContent = f'{tagName} {tagContent}'
            tagName = option
            
            if self.TAG_DB.find_one({"_id": tagName, "Guild ID": ctx.guild.id}) is None:
                try:
                    self.TAG_DB.insert_one({"_id": tagName, "Guild ID": ctx.guild.id, "Added": f"{ctx.author.name}#{ctx.author.discriminator}", "Content": tagContent})
                    embed = Embed(description=f"{GC_EMOJI} Tag `{tagName}` created.", colour=0x2f3136)
                    await ctx.send(embed=embed)
                except DuplicateKeyError:
                    await ctx.send("❌ Tag name already exists.", delete_after=5)
            else:
                tag = self.TAG_DB.find_one({"_id": tagName, "Guild ID": ctx.guild.id})
                author = ctx.guild.get_member_named(tag["Added"])
                embed = Embed(colour=0x2f3136)
                embed.set_author(name=author, icon_url=author.display_avatar)
                embed.add_field(name=tag["_id"], value=tag["Content"])
                await ctx.send(embed=embed)

        elif option.lower() == "create":
            try:
                self.TAG_DB.insert_one({"_id": tagName, "Guild ID": ctx.guild.id, "Added": f"{ctx.author.name}#{ctx.author.discriminator}"})
                embed = Embed(description=f"{GC_EMOJI} Tag `{tagName}` created.", colour=0x2f3136)
                await ctx.send(embed=embed)
            except DuplicateKeyError:
                await ctx.send("❌ Tag name already exists.", delete_after=5)


        elif option.lower() == "edit":
            self.TAG_DB.update_one({"_id": tagName, "Guild ID": ctx.guild.id}, {"$set": {"Content": tagContent}})
            embed = Embed(description=f"{GC_EMOJI} Tag `{tagName}` edited.", colour=0x2f3136)
            await ctx.send(embed=embed)


        elif option.lower() == "delete":
            self.TAG_DB.delete_one({"_id": tagName, "Guild ID": ctx.guild.id})
            embed = Embed(description=f"{GC_EMOJI} Tag `{tagName}` deleted.", colour=0x2f3136)
            await ctx.send(embed=embed)
           


    

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Tag")


def setup(bot):
    bot.add_cog(Tag(bot))
