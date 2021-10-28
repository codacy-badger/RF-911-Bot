from os import getenv
from typing import Optional

from aiohttp import ClientSession
from discord.ext.commands import (Cog, command, has_role)
from discord.ext.commands.errors import MissingRole
from pymongo import MongoClient
from roblox import Client
from dpymenus import Page, PaginatedMenu

from . import del_user_msg


class Logistics(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roblox = Client()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']

        self.PAGE_LIST = []


    @staticmethod
    async def get_url(userID):
        URL = f"https://friends.roblox.com/v1/users/{userID}/friends?userSort=Alphabetical"

        async with ClientSession() as session:
            async with session.get(URL) as response:
                url = await response.json()
                data = url["data"]

                friend_ids = [[data[i]["name"], data[i]["displayName"], data[i]["id"], str(data[i]["isOnline"])] for i in range(len(data))]

        return friend_ids


    def auto_page(self, friend, target, page_index):
        page = Page(title=f"{target.name}'s friends list", colour= 0x2f3136)
        page.set_footer(text=page_index)

        for name, displayname, friendID, is_online in friend:
            page.add_field(name=f"Name: {name}", value=f"Display name: {displayname}\nIDs: {friendID}\nOnline: {is_online}\n[Link](https://www.roblox.com/users/{friendID}/profile)\n-----------------------------", inline=False)

        self.PAGE_LIST.append(page)


    @command(name='check-friend', aliases=['cf'], description='Check user\'s friend list. Require ')
    @has_role("Logistics")
    async def _check_friend(self, ctx, userName: Optional[str] = "roblox"):
        await del_user_msg(ctx)

        user_name = await self.roblox.get_user_by_username(userName)
        if user_name == None:
            await ctx.send("No user found with that username.")
        else:
            friend_ids = await self.get_url(user_name.id)
            if len(friend_ids):
                self.PAGE_LIST = []
                index, page, per_page = 0, 1, 6
                while index < len(friend_ids):
                    page_index = f" {page} - {(len(friend_ids)//per_page + 1) if len(friend_ids)%per_page else len(friend_ids)//per_page} in {len(friend_ids)} friends."
                    self.auto_page(friend_ids[index:index + per_page ], user_name, page_index)
                    index += 6; page += 1

                menu = (PaginatedMenu(ctx)
                            .set_timeout(60)
                            .add_pages(self.PAGE_LIST)
                            .show_skip_buttons()
                       )
                await menu.open()
            else:
                await ctx.send("This user has no friends")


    @_check_friend.error
    async def _load_error(self, ctx, exc):
        if isinstance(exc, MissingRole):
            await ctx.send(content=exc, delete_after = 20)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Logistics")


def setup(bot):
    bot.add_cog(Logistics(bot))