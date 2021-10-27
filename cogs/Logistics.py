import asyncio
import datetime as dt
import os
import time
from datetime import datetime
from os import getenv
from re import compile
from typing import Optional

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord import Embed, Member, TextChannel
from discord.ext.commands import (BucketType, Cog, Greedy, command, cooldown,
                                  has_permissions, has_role)
from pymongo import MongoClient
from requests import get
from concurrent.futures import ThreadPoolExecutor
from roblox import Client
from dpymenus import Page, PaginatedMenu



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

                friend_ids = [data[i]["id"] for i in range(len(data))]

        return friend_ids


    def auto_page(self, friend):
        url = get(
            f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={friend.id}").json()

        page = Page(title=f"Friends list", colour= 0x2f3136, url=f"https://www.roblox.com/users/{friend.id}/profile")
        page.set_thumbnail(url=url["data"][0]["imageUrl"])

        description = "This user has no description." if friend.description == '' else friend.description.strip()

        fields = [("User Name: ", friend.name, True),
                    ("Display Name: ", friend.display_name, True),
                    ("ID: ", friend.id, False),
                    ("Created at: ", str(friend.created)[:10], True),
                    ("Is banned: ", friend.is_banned, True),
                    ("Description: ", description, False)
        ]

        for name, value, inline in fields:
            page.add_field(name=name, value=value, inline=inline)

        self.PAGE_LIST.append(page)


    @command(name='check-friend', aliases=['cf'], description='Check user\'s friend list. Require ')
    # @has_role("Logistics")
    async def _check_friend(self, ctx, userName: Optional[str] = "roblox"):
        user_name = await self.roblox.get_user_by_username(userName)
        # await self.del_user_msg(ctx)

        if user_name == None:
            await ctx.send("No user found with that username.")
        else:
            friend_ids = await self.get_url(user_name.id)
            user = [await self.roblox.get_user(friend) for friend in friend_ids]

            with ThreadPoolExecutor() as executor:
                executor.map(self.auto_page, user)

            menu = (PaginatedMenu(ctx)
                .set_timeout(60)
                .add_pages(self.PAGE_LIST)
                .show_skip_buttons()
                )
            await menu.open()


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Logistics")


def setup(bot):
    bot.add_cog(Logistics(bot))
