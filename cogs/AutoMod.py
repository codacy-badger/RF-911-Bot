from asyncio import sleep
from datetime import datetime, timedelta
from os import getenv
from typing import Optional

from nextcord import Embed, Member, NotFound, Object, Role, TextChannel
from nextcord.ext.commands import (BadArgument, CheckFailure, Cog, Converter,
                                  Greedy, bot_has_permissions, command,
                                  has_permissions)
from nextcord.utils import find, get
from pymongo import MongoClient
from . import del_user_msg


class AutoMod(Cog):
    def __init__(self, bot):
        self.bot = bot

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.BANNED_DB = self.DB['Banned']
        self.GUILD_DB = self.DB['Guild']


    def get_mute_role(self, ctx):
        get_mute = self.GUILD_DB.find_one({"_ids": ctx.guild.id})
        return get_mute["Mute role"] if get_mute is not None else None


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("AutoMod")


def setup(bot):
    bot.add_cog(AutoMod(bot))