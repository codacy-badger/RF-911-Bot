from datetime import datetime, timedelta
from os import getenv

from aiohttp import ClientSession
from nextcord import Embed
from nextcord.ext.commands import Cog, command, has_role
from nextcord.ext.commands.errors import MissingRole
from nextcord.ext.menus import ListPageSource
from pymongo import MongoClient
from requests import get
from roblox import Client

from . import CustomButtonMenuPages, del_user_msg


class FriendMenu(ListPageSource):
    def __init__(self, ctx, data, userName):
        self.ctx = ctx
        self.userName = userName

        super().__init__(data, per_page=18)


    async def write_page(self, menu, fields=[]):
        current_page = menu.current_page + 1
        max_page = round(len(self.entries) / self.per_page) + 1

        url = get(f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={self.userName.id}").json()

        embed = Embed(title=f"{self.userName.name.capitalize()}'s friends list", 
                      colour=0x2f3136, 
                      description=f"User Name: {self.userName.name}\nDisplay Name: {self.userName.display_name}\nID: {self.userName.id}"
                      )
        embed.set_footer(text=f"Page {current_page}/{max_page}.")
        embed.set_thumbnail(url=url["data"][0]["imageUrl"])

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=True)

        return embed

    async def format_page(self, menu, entries):
        fields = [(f"Username: \n{name}", f"Display name: \n{displayName} \nID: {userID}", False) for name, displayName, userID in entries]
        
        return await self.write_page(menu, fields)


class Logistics(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roblox = Client()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']

    
    async def get_hitlist(self, ctx):
        HITLIST = self.GUILD_DB.find_one({"_id": ctx.guild.id})
        
        if HITLIST is None:
            return None
        else:
            CHANNEL = self.bot.get_channel(HITLIST["Hitlist"])
            return CHANNEL


    @staticmethod
    async def get_url(userID):
        URL = f"https://friends.roblox.com/v1/users/{userID}/friends?userSort=Alphabetical"

        async with ClientSession() as session:
            async with session.get(URL) as response:
                url = await response.json()
                data = url["data"]
                friend_ids = [[data[i]["name"], data[i]["displayName"], data[i]["id"]] for i in range(len(data))]


        return friend_ids


    @command(name='check-friend', aliases=['cf'], description='Check user\'s friend list. Require `Logistics` Role')
    @has_role("Logistics")
    async def check_friend_command(self, ctx, userName: str):
        await del_user_msg(ctx)

        username = await self.roblox.get_user_by_username(userName)
        if username == None:
            await ctx.send("No user found with that username.")
        else:
            friend_ids = await self.get_url(username.id)
            if len(friend_ids):
                menu = CustomButtonMenuPages(source=FriendMenu(ctx, friend_ids, username),
                             timeout=120.0)
                await menu.start(ctx)

            else:
                await ctx.send("This user has no friends")

    
    @command(name='host-bounty', aliases=['hb'], description='Host bounty without submission. Require `Logistics` Role')
    @has_role("Logistics")
    async def host_bounty_command(self, ctx, userName: str, *,reason: str):
        await del_user_msg(ctx)

        user_name = await self.roblox.get_user_by_username(userName)
        if user_name == None:
            await ctx.send("No user found with that username.")
        else:
            user = await self.roblox.get_user(user_name.id)
            url = get(
                f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={user_name.id}").json()
            expired_time = datetime.now() + timedelta(days=5)

            embed = Embed(title=f"{user.name} profiles", color=0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile", timestamp=datetime.utcnow())
            embed.set_author(name=f"Host by {ctx.author}", icon_url=f'{ctx.author.display_avatar}')
            embed.set_image(url=url["data"][0]["imageUrl"])
            embed.set_footer(text=f"Expired: {expired_time.strftime('%d-%m-%Y')}")

            fields = [("User Name: ", user.name, True),
                        ("Display Name: ", user.display_name, True),
                        ("Created at: ", str(user.created)[:10], True),
                        ("Reason: ", reason, False),]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            hitlist = await self.get_hitlist(ctx)
            await hitlist.send(embed=embed)


    @check_friend_command.error
    async def _load_error(self, ctx, exc):
        if isinstance(exc, MissingRole):
            await ctx.send(content=exc, delete_after = 20)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Logistics")


def setup(bot):
    bot.add_cog(Logistics(bot))
