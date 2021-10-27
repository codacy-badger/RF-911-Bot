import asyncio
import datetime as dt
import os
import time
from datetime import datetime
from os import getenv
from re import compile
from typing import Optional

from bs4 import BeautifulSoup
from discord import Embed, Member, TextChannel
from discord.ext.commands import (BucketType, Cog, Greedy, command, cooldown,
                                  has_permissions, is_owner)
from pymongo import MongoClient
from pytz import timezone
from requests import get
from roblox import Client


class Logistics(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roblox = Client()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Logistics")


def setup(bot):
    bot.add_cog(Logistics(bot))