from asyncio import sleep
from datetime import datetime, timedelta, date
from os import getenv
from typing import Optional
from uuid import uuid4

from nextcord import Embed, Member, NotFound, Object, Role, TextChannel, ButtonStyle
from nextcord.ext.commands import (BadArgument, CheckFailure, Cog, Converter,
                                  Greedy, bot_has_permissions, command,
                                  has_permissions)
from nextcord.utils import find, get
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from nextcord.ext.menus import ListPageSource, MenuPages, ButtonMenuPages 
    

class IgnoreMenu(ListPageSource):
    def __init__(self, ctx, data, total):
        self.ctx = ctx
        self.total = total

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.MUTE_DB = self.DB["Mute"]
        self.CASE_DB = self.DB["Case"]
        self.WARN_DB = self.DB["Warns"]
        self.BANNED_USER_DB = self.DB["Banned User"]

        super().__init__(data, per_page=6)


    async def write_page(self, menu, fields=[]):
        offset = (menu.current_page*self.per_page) + 1
        len_data = len(self.entries)

        embed = Embed(title=f"Ignore list",
                    description=f"Total is {self.total}",
                    colour =0x2f3136)

        embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} ignored.")

        for name, value in fields:
            embed.add_field(name=f"{name}", value=value, inline=False)

        return embed


    async def get_author(self, ids):
        return self.BANNED_USER_DB.find_one({"_id": ids})["Added"]

        
    async def format_page(self, menu, entries):
        fields = []
        
        for entry in entries:
            author_id = await self.get_author(entry)
            author = self.ctx.guild.get_member(author_id)

            data = self.BANNED_USER_DB.find_one({"_id": entry})
            
            if data["Type"] == "user":
                data = f"<@!{data['_id']}>"
            elif data["Type"] == "channel":
                data = f"<#{data['_id']}>"
        
            
            fields.append((f"Added By: {author.name}#{author.discriminator}" ,data))

        return await self.write_page(menu, fields)


class Ignore(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DELETE_AFTER = 10

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.MUTE_DB = self.DB["Mute"]
        self.CASE_DB = self.DB["Case"]
        self.WARN_DB = self.DB["Warns"]
        self.BANNED_USER_DB = self.DB["Banned User"]
    

    @command(name="add-ignore", description="Add channel/role/user into database")
    @has_permissions(administrator=True)
    async def add_ignore_command(self, ctx, options: str, add_user: Greedy[Member] = None, channels: Greedy[TextChannel] = None):

        try:
            if "user" in options.lower():
                user_id = (user.id for user in add_user).__next__()
                self.BANNED_USER_DB.insert_one({"_id": user_id, "Guild ID": ctx.guild.id, "Type": options.lower(), "Added": ctx.author.id})
                embed = Embed(title="Added user to ignore user successfully:", description=f"<@!{user_id}>", colour=0x2f3136)

                await ctx.reply(embed=embed, mention_author=False, delete_after=self.DELETE_AFTER)

            elif "channel" in options.lower():
                channel_id = (channel.id for channel in channels).__next__()
                self.BANNED_USER_DB.insert_one({"_id": channel_id, "Guild ID": ctx.guild.id, "Type": options.lower(), "Added": ctx.author.id})
                embed = Embed(title="Added channel to ignore channel successfully:", description=f"<#{channel_id}>", colour=0x2f3136)

                await ctx.reply(embed=embed, mention_author=False, delete_after=self.DELETE_AFTER)

            else:
                await ctx.reply("Invalid option, must be either `user` or `channel`", mention_author=False, delete_after=self.DELETE_AFTER)

        except DuplicateKeyError:
            await ctx.reply(f"{options.capitalize()} already in ignored")


    @staticmethod
    async def set_up_menu_page(ctx, data, total_data):
        menu = ButtonMenuPages(source=IgnoreMenu(ctx, data, total_data),
                            clear_reactions_after=True,
                            delete_message_after=True,
                            style=ButtonStyle.primary,
                            timeout=60.0)
        await menu.start(ctx)


    @command(name="show-ignore", description="Show all roles/users/quotes on database")
    @has_permissions(administrator=True)
    async def show_ignore_command(self, ctx, option: Optional[str]):

        
        ignore = [quote["_id"] for quote in self.BANNED_USER_DB.find({"Guild ID": ctx.guild.id})]
        total_ignore = len(ignore)

        if total_ignore >= 1:
            await self.set_up_menu_page(ctx, ignore, total_ignore)
        else:
            await ctx.reply("No ignore have been specified", mention_author=True, delete_after=self.DELETE_AFTER)


    async def delete_all_data(self, ctx):
        self.BANNED_USER_DB.delete_many({"Guild ID": ctx.guild.id})

        
    @command(name="del-all-ignore",aliases=["remove-all"], description="Remove all quotes/users/roles on database")
    @has_permissions(administrator=True)
    async def del_all_ignore_command(self, ctx):

        a = ["y", "yes"]
        b = ["n", "no"]

        # Ask user for confirmnation
        await ctx.send(f'Do you want to remove all? y/n\nThis action can\'t not be reverse')
        msg = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

        # If user confirmed yes
        if msg.content in a:
            await self.delete_all_data(ctx)
            await ctx.reply(f"All ignore have been removed", delete_after=self.DELETE_AFTER)

        # If user confirmed no
        elif msg.content in b:
            await ctx.reply(f'Action was terminated, nothing were removed', delete_after=self.DELETE_AFTER)

        # If user give no proper response
        else:
            await ctx.reply(f"No proper response was given, action was terminated", delete_after=self.DELETE_AFTER)


    @command(name="del-ignore", aliases=["remove"], description="Remove channel/user from database, required Helpers role")
    @has_permissions(administrator=True)
    async def del_ignore_command(self, ctx, options: str, add_user: Greedy[Member], channels: Greedy[TextChannel] = None):

        if options.lower() == 'user':
            user_id = (user.id for user in add_user).__next__()
            self.BANNED_USER_DB.delete_one({"_id": user_id, "Guild ID": ctx.guild.id})

            embed = Embed(title="Removed user from database successfully:", description=f"<@!{user_id}>", colour=0x2f3136)
            await ctx.reply(embed=embed, mention_author=False, delete_after=self.DELETE_AFTER)

        elif options.lower() == "channel":
            channel_id = (channel.id for channel in add_user).__next__()
            self.BANNED_USER_DB.delete_one({"_id": channel_id, "Guild ID": ctx.guild.id})

            embed = Embed(title="Removed channel from database successfully:", description=f"<#{channel_id}>", colour=0x2f3136)
            await ctx.reply(embed=embed, mention_author=False, delete_after=self.DELETE_AFTER)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Ignore")


def setup(bot):
    bot.add_cog(Ignore(bot))