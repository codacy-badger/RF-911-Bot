from datetime import datetime
from re import compile
from typing import Union

from bs4 import BeautifulSoup
from bs4.element import Tag
from nextcord import Embed, TextChannel
from nextcord.ext.commands import (BucketType, Cog, Context, command, cooldown,
                                   has_permissions)
from nextcord.ext.tasks import loop
from pytz import timezone

from ..bot import RF
from . import delUserMsg


class Daily(Cog):
    def __init__(self, bot: RF):
        self.bot = bot

        # Daily tasks
        self.mission_objective = None
        self.first_msg = True
        # self.dailyChallenges.start()


    @loop(minutes=2)
    async def dailyChallenges(self) -> None:
        db_equal_wiki = await self.checkDB() 

        if not db_equal_wiki or self.first_msg: # If daily changed
            _, wiki_embed, mission_objective = await self.embedMessage()

            self.first_msg = False
            self.mission_objective = mission_objective

            for channelID in await self.getChannel(): # For each channel in pairs with role
                channel = self.bot.get_channel(channelID)
                if channel is not None:
                    await channel.send(embed=wiki_embed)


    @dailyChallenges.before_loop
    async def before_send(self) -> None:
        await self.bot.wait_until_ready()


    async def getChannel(self) -> list:
        return [channel_role['Daily channel'] for channel_role in self.bot.GUILD_DB.find()]


    async def checkDB(self) -> bool:
        daily_board, daily_mission_wiki = await self.getDailyBoard()
        objectives_list_wiki = await self.getObjective(daily_board)

        mission_objective_wiki = f'{daily_mission_wiki} - {objectives_list_wiki}'

        if self.mission_objective is None: # -> None means bot just start -> no daily added
            return False

        if self.mission_objective == mission_objective_wiki: # -> Daily haven't change
            return True
        return False # -> if data is different from wiki


    async def getDailyBoard(self) -> Tag:
        wiki_url = 'https://entry-point.fandom.com/wiki/Entry_Point_Wiki'
        async with self.bot.session.get(wiki_url) as response:
            get_url = await response.text()
            soup = BeautifulSoup(get_url, "lxml")

            daily_board = soup.find(string=compile("daily challenge")).parent.parent.parent # Find daily main parent contain all needed children
            daily_mission = daily_board.find("th", colspan="3").text.strip() # Find daily mission
            
        return daily_board, daily_mission


    @staticmethod
    async def getObjective(daily_board) -> str:
        daily_objective = daily_board.find_all('span', class_= compile("challenge-")) # -> list | Find all challenge's container
        objective_list = [f'{objective.text} - {objective["class"][0][10:]}' for objective in daily_objective] # -> get daily's objective and objective's difficulty and put it in a list

        return objective_list


    @staticmethod
    async def getObjectiveDescription(daily_board) -> list:
        objective_description = daily_board.find_all("td", style="width: 33%;") # -> list Get challenge's description

        return [description.text.strip() for description in objective_description]


    @staticmethod
    async def getTimeleft() -> datetime:
        est = timezone('US/Eastern')
        time_now = datetime.now(tz=est) # Get date and time in EST timezone

        time_hour = f"0{23- time_now.hour}" if 23 - time_now.hour < 10 else f"{23- time_now.hour}"
        time_min = f"0{59- time_now.minute}" if 59 - time_now.minute < 10 else f"{59- time_now.minute}"
        time_sec = f"0{59- time_now.second}" if 59 - time_now.second < 10 else f"{59- time_now.second}"

        return "{}:{}:{}".format(time_hour, time_min, time_sec)


    @staticmethod
    async def getToday() -> datetime:
        est = timezone('US/Eastern') # Get time zone information
        today = datetime.now(tz=est) # Get current time in EST timezone

        return today.strftime("%d-%m-%Y")


    async def embedMessage(self) -> Union[datetime, Embed, str]:
        # Get daily data        
        daily_board, daily_mission = await self.getDailyBoard()
        objective_list = await self.getObjective(daily_board)
        description_list = await self.getObjectiveDescription(daily_board)
        time_left = await self.getTimeleft()
        today = await self.getToday()


        # Set Embedded objects
        embed = Embed(title=f"Daily Challenge {today}",description=f"**{daily_mission}**", colour=0x2f3136)
        embed.set_footer(text=f"The daily challenge changes in: {time_left}")
        embed.set_thumbnail(url='https://t3.rbxcdn.com/aced37b6a698eb54f4efa1d4007fe435')

        # 🟥 🟦 🟩 🟪 Place holder
        # 🔴 🔵 🟢 🟣 Place holder

        mission_objective = f'{daily_mission} - {objective_list}'

        # Adding daily information into embed
        for index in range(len(objective_list)):
            difficulty_color = objective_list[index].split("-")[1].lower().strip() # Get challenge's difficulty color
            difficulty_level = "Easy 🟩" if difficulty_color == "green" else "Medium 🟦" if difficulty_color == "blue" else "Advanced 🟪" if difficulty_color == "purple" else "Hard 🟥"
            # ^ 
            # | Turn color into difficulty
 
            # Set embed
            objective_name = objective_list[index].split("-")[0] # Get challenge's name without difficulty
            description = description_list[index].replace(". ", ".\n") # New line after .
            embed.add_field(name=f"_{objective_name}_ - {difficulty_level}", value=f"{description}", inline=False)

        return today, embed, mission_objective


    @command(name="set-daily-channel", aliases=["sdc"], description="Set Auto Daily Challenges Channel.\nRequired `Administrator` permissions")
    @has_permissions(administrator=True)
    async def setDailyCommand(self, ctx: Context, channels: TextChannel) -> None:
        await delUserMsg(ctx)

        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Daily channel": channels.id}})
        await ctx.send(f'Daily channel set to {channels.mention}', delete_after = 30)


    @command(name="daily", description="Show Entry Point Daily Challenges.")
    @cooldown(3, 60, BucketType.user)
    async def _daily_command(self, ctx: Context) -> None:
        await delUserMsg(ctx)

        msg = await ctx.send("Loading... <a:discord:873909804630933575>")
        _, wiki_embed, _ = await self.embedMessage()
        await msg.edit(content="", embed=wiki_embed, delete_after = 60)


    @Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Daily")


def setup(bot):
    bot.add_cog(Daily(bot))