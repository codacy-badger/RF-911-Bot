from datetime import datetime, timedelta

from nextcord import Embed
from nextcord.ext.commands import Cog, Context, command, has_role
from pytz import timezone

from ..bot import RF
from . import del_user_msg
from .Bounty import Bounty

# class FriendMenu(ListPageSource):
#     def __init__(self, ctx, data, userName):
#         self.ctx = ctx
#         self.userName = userName
#         self.bot.roblox = Client()

#         super().__init__(data, per_page=18)


#     async def write_page(self, menu, fields=[]):
#         current_page = menu.current_page + 1
#         max_page = round(len(self.entries) / self.per_page) + 1

#         thumbnail = await self.bot.roblox.thumbnails.get_user_avatars([self.userName.id], size="720x720")
#         thumbnail_url = (thumbnail[0].image_url if thumbnail[0].image_url is not None else Embed.Empty)

#         embed = Embed(title=f"{self.userName.name.capitalize()}'s friends list", colour=0x2F3136,
#                       description=f"User Name: {self.userName.name}\nDisplay Name: {self.userName.display_name}\nID: {self.userName.id}",)
#         embed.set_footer(text=f"Page {current_page}/{max_page}.")
#         embed.set_thumbnail(url=thumbnail_url)

#         for name, value, inline in fields:
#             embed.add_field(name=name, value=value, inline=True)

#         return embed


#     async def format_page(self, menu, entries):
#         fields = [(f"Username: \n{name}",f"Display name: \n{displayName} \nID: {userID}",False,) for name, displayName, userID in entries]

#         return await self.write_page(menu, fields)


class Logistics(Cog):
    def __init__(self, bot: RF):
        self.bot = bot


    async def get_url(self, userID) -> list:
        URL = f"https://friends.roblox.com/v1/users/{userID}/friends?userSort=Alphabetical"

        async with self.bot.session.get(URL) as response:
            url = await response.json()
            data = url["data"]
            friend_ids = [[data[i]["name"], data[i]["displayName"], data[i]["id"]] for i in range(len(data))]

        return friend_ids


    # @command(name="check-friend", aliases=["cf"], description="Check user's friend list.\nRequire `Logistics` Role")
    # @has_role("Logistics")
    # async def check_friend_command(self, ctx: Context, userName: str) -> None:
    #     await del_user_msg(ctx)

    #     username = await self.bot.roblox.get_user_by_username(userName)
    #     if username == None:
    #         await ctx.send("No user found with that username.")
    #     else:
    #         friend_ids = await self.get_url(username.id)
    #         if len(friend_ids):
    #             menu = CustomButtonMenuPages(source=FriendMenu(ctx, friend_ids, username), timeout=120.0, ctx=ctx)
    #             await menu.start(ctx)

    #         else:
    #             await ctx.send("This user has no friends")


    @command(name="host-bounty", aliases=["hb"], description="Host bounty without submission.\nRequire `Logistics` Role",)
    @has_role("Logistics")
    async def host_bounty_command(self, ctx: Context, userName: str, *, reason: str):
        await del_user_msg(ctx)

        user_name = await self.bot.roblox.get_user_by_username(userName)
        if user_name == None:
            await ctx.send("No user found with that username.")
        else:
            user = await self.bot.roblox.get_user(user_name.id)

            thumbnail = await self.bot.roblox.thumbnails.get_user_avatars([user.id], size="720x720")
            thumbnail_url = (thumbnail[0].image_url if thumbnail[0].image_url is not None else Embed.Empty)
            expired_time = datetime.now() + timedelta(days=7)

            embed = Embed(title=f"{user.name} profiles", color=0x2F3136, url=f"https://www.roblox.com/users/{user.id}/profile", 
                          timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")),)
            embed.set_image(url=thumbnail_url)

            fields = [("User Name: ", user.name, True),
                      ("Display Name: ", user.display_name, True),
                      ("Expired: ", f"<t:{str(expired_time.timestamp()).split('.')[0]}:R>", False),
                      ("Reason: ", reason, False),]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            msg = await Bounty(self.bot).sendHitlist(ctx, embed, ctx.author)

            self.bot.scheduler.add_job(Bounty(self.bot).deleteBounty, id=f"{msg.id}-Bounty", args=[ctx.guild, msg.id], next_run_time=expired_time)
            self.bot.SCHEDULER.insert_one({"_id": f"{msg.id}-Bounty", "Guild ID": ctx.guild.id, "Guild": ctx.guild.name,
                                                    "Expired": expired_time.strftime('%d-%m-%Y-%H-%M-%S'),})       


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Logistics")


def setup(bot):
    bot.add_cog(Logistics(bot))
