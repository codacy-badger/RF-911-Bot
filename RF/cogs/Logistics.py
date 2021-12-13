from datetime import datetime, timedelta

from nextcord import Embed, Member, Webhook ,NotFound
from nextcord.ext.commands import Cog, Context, command, has_role
from pytz import timezone

from ..bot import RF
from . import delUserMsg
from .Bounty import Bounty


class Logistics(Cog):
    def __init__(self, bot: RF):
        self.bot = bot


    async def getUrl(self, userID) -> list:
        URL = f"https://friends.roblox.com/v1/users/{userID}/friends?userSort=Alphabetical"

        async with self.bot.session.get(URL) as response:
            url = await response.json()
            data = url["data"]
            friendsID = [[data[i]["name"], data[i]["displayName"], data[i]["id"]] for i in range(len(data))]

        return friendsID


    # @command(name="check-friend", aliases=["cf"], description="Check user's friend list.\nRequire `Logistics` Role")
    # @has_role("Logistics")
    # async def check_friend_command(self, ctx: Context, filters: str, userName: str, loop: int = 3) -> None:

    #     username = await self.bot.roblox.get_user_by_username(userName)
    #     if username == None:
    #         await ctx.send("No user found with that username.")
    #     else:
    #         friend_ids = await self.getUrl(username.id)
    #         if len(friend_ids):
    #             pass
    #         else:
    #             await ctx.send("This user has no friends")


    @command(name="host-bounty", aliases=["hb"], description="Host bounty directly without submission.\nRequired `Logistics` Role",)
    @has_role("Logistics")
    async def hostBounty(self, ctx: Context, userName: str, *, reason: str) -> None:
        await delUserMsg(ctx)

        user_name = await self.bot.roblox.get_user_by_username(userName)
        if user_name == None:
            await ctx.send("No user found with that username.")
        else:
            user = await self.bot.roblox.get_user(user_name.id)

            thumbnail = await self.bot.roblox.thumbnails.get_user_avatar_thumbnails([user.id], size="720x720")
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
    
    
    @command(name="claim", description="Claim a bounty.\nRequired `Logistics` Role")
    @has_role("Logistics")
    async def claimBounty(self, ctx: Context, messageID: int, user: Member) -> None:
        await delUserMsg(ctx)
        
        HITLIST = self.bot.GUILD_DB.find_one({"_id": ctx.guild.id})
        webhook = HITLIST["Hitlist"]
        ID, Token = webhook["ID"], webhook["Token"]

        channel = Webhook.from_url(url=f"https://discord.com/api/webhooks/{ID}/{Token}", session=self.bot.session)

        try:
            message = await channel.fetch_message(messageID)
            await message.edit(content=f"Bounty claimmed by {user.mention}. Authenticated by {ctx.author.mention}")
        except NotFound:
            await ctx.send("No bounty found with provided ID.", delete_after= 10)


    @Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Logistics")


def setup(bot) -> None:
    bot.add_cog(Logistics(bot))