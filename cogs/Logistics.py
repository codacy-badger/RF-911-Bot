from os import getenv
from typing import Optional

from nextcord import Embed
from aiohttp import ClientSession
from nextcord.ext.commands import Cog, command, has_role
from nextcord.ext.commands.errors import MissingRole
from pymongo import MongoClient
from roblox import Client
from nextcord.ext.menus import ListPageSource, MenuPages
from requests import get

from . import del_user_msg


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data, userName):
        self.ctx = ctx
        self.userName = userName

        super().__init__(data, per_page=6)


    async def write_page(self, menu, fields=[]):
        offset = (menu.current_page*self.per_page) + 1
        len_data = len(self.entries)

        # url = get(
        #         f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={self.userName.id}").json()

        embed = Embed(title=f"{self.userName}'s friends list", colour=0x2f3136)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} commands.")
        # embed.set_thumbnail(url=url["data"][0]["imageUrl"]) 


        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed


    async def format_page(self, menu, entries):
        fields = [(f"Username: {name}", f"Display name: {displayName} \nID: {userID}", False) for name, displayName, userID in entries]

        return await self.write_page(menu, fields)


class Logistics(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roblox = Client()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']


    @staticmethod
    async def get_url(userID):
        URL = f"https://friends.roblox.com/v1/users/{userID}/friends?userSort=Alphabetical"

        async with ClientSession() as session:
            async with session.get(URL) as response:
                url = await response.json()
                data = url["data"]
                friend_ids = [[data[i]["name"], data[i]["displayName"], data[i]["id"]] for i in range(len(data))]


        return friend_ids


    @command(name='check-friend', aliases=['cf'], description='Check user\'s friend list. Require ')
    @has_role("Logistics")
    async def _check_friend(self, ctx, userName: Optional[str] = "roblox"):
        await del_user_msg(ctx)

        username = await self.roblox.get_user_by_username(userName)
        if username == None:
            await ctx.send("No user found with that username.")
        else:
            friend_ids = await self.get_url(username.id)
            if len(friend_ids):
                menu = MenuPages(source=HelpMenu(ctx, friend_ids, username),
                             clear_reactions_after=True,
                             timeout=60.0)
                await menu.start(ctx)

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
