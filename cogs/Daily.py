from datetime import datetime
from os import getenv
from re import compile

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord import Embed, TextChannel
from discord.ext.commands import (BucketType, Cog, Greedy, command, cooldown,
                                  has_permissions)
from discord.ext.tasks import loop
from pymongo import MongoClient
from pytz import timezone
from . import del_user_msg


class Daily(Cog):
    def __init__(self, bot):
        self.bot = bot

        # MongoDB
        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']

        # Daily tasks
        self.mission_objective = None
        self.first_msg = True
        self.daily_task.start()


    @loop(minutes=1)
    async def daily_task(self):
        db_equal_wiki = await self.check_db() 
        await self.get_channel_role()

        if any(self.channel_role): # Check if any channel paired with role in it

            if not db_equal_wiki or self.first_msg: # If daily changed
                _, wiki_embed, mission_objective = await self.embed_daily_challenge()

                self.first_msg = False
                self.mission_objective = mission_objective

                for channel_id in self.channel_role: # For each channel in pairs with role
                    channel = self.bot.get_channel(channel_id)
                    await channel.send(embed=wiki_embed)


    @daily_task.before_loop
    async def before_send(self):
        await self.bot.wait_until_ready()


    async def get_channel_role(self):
        self.channel_role = [channel_role['daily channel'] for channel_role in self.GUILD_DB.find()]


    async def check_db(self):
        daily_board, daily_mission_wiki = await self.get_daily_board()
        objectives_list_wiki = await self.get_objective(daily_board)

        mission_objective_wiki = f'{daily_mission_wiki} - {objectives_list_wiki}'

        if self.mission_objective is None: # -> None means bot just start -> no daily added
            return False

        if self.mission_objective == mission_objective_wiki: # -> Daily havent change
            return True
        return False # -> if data is different from wiki


    @staticmethod
    async def get_daily_board():
        wiki_url = 'https://entry-point.fandom.com/wiki/Entry_Point_Wiki'
        async with ClientSession() as session:
            async with session.get(wiki_url) as response:
                get_url = await response.text()
                soup = BeautifulSoup(get_url, "lxml")

                daily_board = soup.find(string=compile("The daily challenge")).parent.parent # Find daily main parent contain all needed childrens
                daily_mission = daily_board.find("th", colspan="3").text.strip() # Find daily mission

        return daily_board, daily_mission


    @staticmethod
    async def get_objective(daily_board):
        daily_objective = daily_board.find_all('span', class_= compile("challenge-")) # -> list | Find all challenge's container
        objective_list = [f'{objective.text} - {objective["class"][0][10:]}' for objective in daily_objective] # -> get daily's objective and objective's difficulty and put it in a list

        return objective_list


    @staticmethod
    async def get_objective_description(daily_board):
        objective_description = daily_board.find_all("td", style="width: 33%;") # -> list Get challenge's description

        return [description.text.strip() for description in objective_description]


    @staticmethod
    async def get_time_left():
        est = timezone('US/Eastern')
        time_now = datetime.now(tz=est) # Get date and time in EST timezone

        time_hour = f"0{23- time_now.hour}" if 23 - time_now.hour < 10 else f"{23- time_now.hour}"
        time_min = f"0{59- time_now.minute}" if 59 - time_now.minute < 10 else f"{59- time_now.minute}"
        time_sec = f"0{59- time_now.second}" if 59 - time_now.second < 10 else f"{59- time_now.second}"

        return "{}:{}:{}".format(time_hour, time_min, time_sec)


    @staticmethod
    async def get_today():
        est = timezone('US/Eastern') # Get time zone information
        today = datetime.now(tz=est) # Get current time in EST timezone

        return today.strftime("%d-%m-%Y")


    async def embed_daily_challenge(self):

        # Get daily data        
        daily_board, daily_mission = await self.get_daily_board()
        objective_list = await self.get_objective(daily_board)
        description_list = await self.get_objective_description(daily_board)
        time_left = await self.get_time_left()
        today = await self.get_today()


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


    @command(name="set-daily-channel", aliases=["sdc"], description="Set Auto Daily Challenges Channel")
    @has_permissions(administrator=True)
    async def _set_daily(self, ctx, channels : Greedy[TextChannel]):

        channel_id = (channel.id for channel in channels).__next__()
        
        await del_user_msg(ctx)
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"daily channel": channel_id}})

        await ctx.send(f'Daily channel set to <#{channel_id}>', delete_after = 30)


    @command(name="daily", description="Show Entry Point Daily Challenges")
    @cooldown(3, 30, BucketType.user)
    async def _daily_command(self, ctx):
        await del_user_msg(ctx)

        msg = await ctx.send("Loading... <a:discord:873909804630933575>")

        _, wiki_embed, _ = await self.embed_daily_challenge()
        await msg.edit(content="", embed=wiki_embed, delete_after = 30)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Daily")


def setup(bot):
    bot.add_cog(Daily(bot))