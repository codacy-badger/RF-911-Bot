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
from pytz import timezone
from requests import get
from roblox import Client


class Bounty(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roblox = Client()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        

    async def check_channel(self, ctx):
        BOUNTY_SUBMISSIONS = self.GUILD_DB.find_one({"_id": ctx.guild.id})['Bounty submission']

        if ctx.channel.id != BOUNTY_SUBMISSIONS:
            return False
        return True


    async def del_user_msg(self, ctx):
        msg = await ctx.channel.fetch_message(ctx.message.id)
        await msg.delete()


    @command(name="set-bounty-channel", aliases=["sbc"], description="Set Bounty Submissions Channel")
    @has_permissions(administrator=True)
    async def _set_daily(self, ctx, channels : Greedy[TextChannel]):

        channel_id = (channel.id for channel in channels).__next__()
        
        await self.del_user_msg(ctx)
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Bounty submission": channel_id}})

        await ctx.send(f'Bounty Submissions channel set/update to <#{channel_id}>', delete_after = 30)


    @command(name='robloxinfo', aliases=['rbinfo'])
    async def get_robloxinfo(self, ctx, name: Optional[str] = 'Roblox'):

        user_name = await self.roblox.get_user_by_username(name)
        await self.del_user_msg(ctx)

        if user_name == None:
            await ctx.send("No user found with that username.")
        else:
            url = get(
                f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={user_name.id}").json()

            user = await self.roblox.get_user(user_name.id)
            embed = Embed(title="Roblox User Info", colour= 0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
            embed.set_thumbnail(url=url["data"][0]["imageUrl"])

            description = "This user has no description." if user.description == '' else user.description.strip()

            fields = [("User Name: ", user.name, True),
                      ("Display Name: ", user.display_name, True),
                      ("ID: ", user.id, False),
                      ("Created at: ", str(user.created)[:10], True),
                      ("Is banned: ", user.is_banned, True),
                      ("Description: ", description, False)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await ctx.send(embed= embed)


    @command(name="submit-bounty", aliases=['sb'])
    @cooldown(rate=4, per=7200, type=BucketType.user)
    @has_role("Bounty Hunter")
    async def _bounty(self, ctx, target: Optional[str], *, reason: Optional[str] = "No reason provided."):
        CHECK_CHANNEL = await self.check_channel(ctx)
        await self.del_user_msg(ctx)

        if CHECK_CHANNEL:
            user_name = await self.roblox.get_user_by_username(target)

            if user_name == None:
                await ctx.send("No user found with that username.")
            else:
                user = await self.roblox.get_user(user_name.id)
                url = get(
                    f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={user_name.id}").json()

                embed = Embed(title="***TARGET INFO***", color=0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
                embed.set_author(name=f"Resquested by {ctx.author}", icon_url=f'{ctx.author.avatar_url}')
                embed.set_image(url=url["data"][0]["imageUrl"])

                fields = [("User Name: ", user.name, True),
                            ("Display Name: ", user.display_name, True),
                            ("Created at: ", str(user.created)[:10], True),
                            ("Reason: ", reason, False),
                         ]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"Wrong channel to submit bounty {ctx.author.mention}", delete_after=30)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Bounty")


def setup(bot):
    bot.add_cog(Bounty(bot))
